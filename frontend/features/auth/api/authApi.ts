"use server";
import { cookies } from "next/headers";
import { jwtDecode } from "jwt-decode";

import { getApiBaseUrl, getClientHeaders } from "@/lib/api";
import { ActionResult, getErrorMessage, parseResponse } from "@/lib/apiUtils";
import { AuthResponse } from "../types";

const DEFAULT_COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

function getSecondsUntilExpiry(token: string) {
  try {
    const { exp } = jwtDecode<{ exp?: number }>(token);
    if (exp) return Math.max(exp - Math.floor(Date.now() / 1000), 0);
  } catch {}
  return DEFAULT_COOKIE_MAX_AGE;
}

async function saveCookie(token: string, maxAge = DEFAULT_COOKIE_MAX_AGE) {
  const cookieStore = await cookies();

  cookieStore.set("access_token", token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge,
    path: "/",
  });
}

async function authenticate(
  path: "/api/auth/login" | "/api/auth/register" | "/api/auth/demo",
  body?: Record<string, string>,
): Promise<ActionResult> {
  try {
    const response = await fetch(`${await getApiBaseUrl()}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(await getClientHeaders()),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    const result = await parseResponse<AuthResponse>(response);

    if (!result.success) return result;

    await saveCookie(
      result.data.access_token,
      path === "/api/auth/demo"
        ? getSecondsUntilExpiry(result.data.access_token)
        : undefined,
    );

    return { success: true };
  } catch {
    return {
      success: false,
      message: getErrorMessage(null),
      details: null,
    };
  }
}

export async function login(
  email: string,
  password: string,
): Promise<ActionResult> {
  return authenticate("/api/auth/login", { email, password });
}

export async function register(
  email: string,
  password: string,
  username: string,
): Promise<ActionResult> {
  return authenticate("/api/auth/register", { email, password, username });
}

export async function startDemo(): Promise<ActionResult> {
  return authenticate("/api/auth/demo");
}

export async function logout() {
  const cookieStore = await cookies();
  cookieStore.delete("access_token");
}
