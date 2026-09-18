"use server";
import { cookies } from "next/headers";

export const baseUrl: string = process.env.BASE_URL!;

if (!baseUrl) {
  throw new Error("Base URL is undefined");
}

export async function attachToken() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (token) {
    return `Bearer ${token}`;
  }
  return undefined;
}
