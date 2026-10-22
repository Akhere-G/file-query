"use server";
import { cookies, headers } from "next/headers";

export async function getApiBaseUrl() {
  const baseUrl = process.env.BASE_URL;
  if (!baseUrl) {
    throw new Error("BASE_URL is undefined");
  }

  return baseUrl;
}

export async function attachToken() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (token) {
    return `Bearer ${token}`;
  }
  throw new Error("You must log in to continue");
}

export async function getToken() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  return token;
}

export async function getClientHeaders(): Promise<Record<string, string>> {
  const secret = process.env.INTERNAL_API_SECRET;
  const ip = (await headers()).get("x-forwarded-for")?.split(",")[0]?.trim();
  if (!secret || !ip) return {};

  return { "X-Client-IP": ip, "X-Internal-Secret": secret };
}
