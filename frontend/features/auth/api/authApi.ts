"use server";
import { cookies } from "next/headers";

import { getApiBaseUrl } from "@/lib/api";
import { ActionResult, getErrorMessage, parseResponse } from "@/lib/apiUtils";
import { AuthResponse } from "../types";

async function saveCookie(token: string) {
  const cookieStore = await cookies();

  cookieStore.set("access_token", token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 7,
    path: "/",
  });
}

async function authenticate(
  path: "/api/auth/login" | "/api/auth/register",
  body: Record<string, string>,
): Promise<ActionResult> {
  try {
    const response = await fetch(`${await getApiBaseUrl()}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const result = await parseResponse<AuthResponse>(response);

    if (!result.success) return result;

    await saveCookie(result.data.access_token);

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

export async function logout() {
  const cookieStore = await cookies();
  cookieStore.delete("access_token");
}
