import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const cookieStore = { get: vi.fn() };
const headerStore = { get: vi.fn() };

vi.mock("next/headers", () => ({
  cookies: async () => cookieStore,
  headers: async () => headerStore,
}));

import { attachToken, getApiBaseUrl, getClientHeaders, getToken } from "./api";

beforeEach(() => {
  cookieStore.get.mockReset();
  headerStore.get.mockReset();
});
afterEach(() => vi.unstubAllEnvs());

describe("getApiBaseUrl", () => {
  it("returns BASE_URL", async () => {
    vi.stubEnv("BASE_URL", "http://api.test");

    expect(await getApiBaseUrl()).toBe("http://api.test");
  });

  it("fails loudly when BASE_URL is missing", async () => {
    vi.stubEnv("BASE_URL", "");

    await expect(getApiBaseUrl()).rejects.toThrow("BASE_URL is undefined");
  });
});

describe("attachToken", () => {
  it("builds a bearer header from the access_token cookie", async () => {
    cookieStore.get.mockReturnValue({ value: "abc" });

    expect(await attachToken()).toBe("Bearer abc");
    expect(cookieStore.get).toHaveBeenCalledWith("access_token");
  });

  it("refuses to call the API without a session", async () => {
    cookieStore.get.mockReturnValue(undefined);

    await expect(attachToken()).rejects.toThrow("You must log in to continue");
  });

  it("getToken returns the raw token or undefined", async () => {
    cookieStore.get.mockReturnValueOnce({ value: "abc" }).mockReturnValueOnce(undefined);

    expect(await getToken()).toBe("abc");
    expect(await getToken()).toBeUndefined();
  });
});

describe("getClientHeaders", () => {
  it("forwards the first client IP together with the shared secret", async () => {
    vi.stubEnv("INTERNAL_API_SECRET", "s3cret");
    headerStore.get.mockReturnValue("203.0.113.7, 10.0.0.1");

    expect(await getClientHeaders()).toEqual({
      "X-Client-IP": "203.0.113.7",
      "X-Internal-Secret": "s3cret",
    });
  });

  it("sends nothing when the secret is not configured, so the IP cannot be spoofed", async () => {
    vi.stubEnv("INTERNAL_API_SECRET", "");
    headerStore.get.mockReturnValue("203.0.113.7");

    expect(await getClientHeaders()).toEqual({});
  });

  it("sends nothing when there is no forwarded IP", async () => {
    vi.stubEnv("INTERNAL_API_SECRET", "s3cret");
    headerStore.get.mockReturnValue(null);

    expect(await getClientHeaders()).toEqual({});
  });
});
