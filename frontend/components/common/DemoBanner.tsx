import Link from "next/link";
import { jwtDecode } from "jwt-decode";
import { getToken } from "@/lib/api";

// UI hint only: the backend decides what a demo user may do from the database.
export async function isDemoSession() {
  const token = await getToken();
  if (!token) return false;

  try {
    return jwtDecode<{ demo?: boolean }>(token).demo === true;
  } catch {
    return false;
  }
}

export default async function DemoBanner() {
  if (!(await isDemoSession())) return null;

  return (
    <div
      role="status"
      className="border-b bg-primary/10 px-4 py-2 text-center text-sm text-foreground"
    >
      You&apos;re exploring the shared FileQuery demo. Anyone using the demo can
      see and change what&apos;s here, so please don&apos;t upload private
      files.{" "}
    </div>
  );
}
