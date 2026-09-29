"use server";
import { cookies } from "next/headers";

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
