// @vitest-environment node
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { proxy } from "./proxy";

const base64url = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");

// jwtDecode does not verify signatures, so an unsigned token is enough here.
const tokenExpiringIn = (seconds: number | undefined) =>
  `${base64url({ alg: "HS256", typ: "JWT" })}.${base64url(
    seconds === undefined ? {} : { exp: Math.floor(Date.now() / 1000) + seconds },
  )}.sig`;

const request = (path: string, token?: string) =>
  new NextRequest(`http://localhost:3000${path}`, {
    headers: token ? { cookie: `access_token=${token}` } : {},
  });

const location = (response: Response) => response.headers.get("location");
const clearsCookie = (response: Response) =>
  (response.headers.get("set-cookie") ?? "").includes("access_token=;");

describe("proxy: signed-out visitors", () => {
  it.each(["/dashboard", "/dashboard/anything", "/settings"])(
    "redirects %s to the login page and remembers where they were going",
    (path) => {
      const response = proxy(request(path));

      expect(response.status).toBe(307);
      expect(location(response)).toBe(
        `http://localhost:3000/login?callbackUrl=${encodeURIComponent(path)}`,
      );
    },
  );

  it.each(["/", "/login", "/register", "/demo", "/privacy", "/terms"])(
    "lets them see %s",
    (path) => {
      const response = proxy(request(path));

      expect(location(response)).toBeNull();
    },
  );

  it("does not treat look-alike paths as protected", () => {
    expect(location(proxy(request("/dashboardx")))).toBeNull();
  });
});

describe("proxy: signed-in users", () => {
  it.each(["/login", "/register", "/demo"])("sends them from %s to the dashboard", (path) => {
    const response = proxy(request(path, tokenExpiringIn(3600)));

    expect(location(response)).toBe("http://localhost:3000/dashboard");
  });

  it.each(["/dashboard", "/settings"])("lets them into %s", (path) => {
    expect(location(proxy(request(path, tokenExpiringIn(3600))))).toBeNull();
  });
});

describe("proxy: bad tokens", () => {
  it.each([
    ["expired", tokenExpiringIn(-10)],
    ["missing an expiry", tokenExpiringIn(undefined)],
    ["malformed", "not-a-jwt"],
  ])("treats an %s token as signed out and clears the cookie", (_, token) => {
    const response = proxy(request("/dashboard", token));

    expect(location(response)).toContain("/login?callbackUrl=%2Fdashboard");
    expect(clearsCookie(response)).toBe(true);
  });

  it("lets an expired-token visitor reach the login page and still clears the cookie", () => {
    const response = proxy(request("/login", tokenExpiringIn(-10)));

    expect(location(response)).toBeNull();
    expect(clearsCookie(response)).toBe(true);
  });
});
