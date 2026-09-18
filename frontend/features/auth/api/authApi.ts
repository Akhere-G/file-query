"use server";
import { baseUrl } from "@/lib/api";
import { cookies } from "next/headers";

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
export async function login(email: string, password: string) {
  const response = await fetch(`${baseUrl}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail);
  }
  await saveCookie(data.access_token);
  return { success: true };
}

export async function register(
  email: string,
  password: string,
  username: string,
) {
  const response = await fetch(`${baseUrl}/api/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password, username }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail);
  }
  await saveCookie(data.access_token);

  return { success: true };
}
