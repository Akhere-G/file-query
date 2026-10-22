"use client";
import { startDemo } from "@/features/auth/api/authApi";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";
import { useEffect, useState } from "react";

export default function DemoPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<null | string>(null);
  useEffect(() => {
    async function start() {
      const res = await startDemo();
      if (!res.success) {
        setError(res.message ?? "Could not start demo");
      } else {
        setLoading(false);
        redirect("/dashboard");
      }
    }
    start();
  }, []);

  if (loading) {
    return (
      <div className="container text-center justify-center items-center w-full flex flex-col gap-4">
        <h2 className="title">Loading demo...</h2>
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container text-center justify-center items-center w-full flex flex-col gap-4">
        <h2 className="title">{error ?? "Sorry, something went wrong...."}</h2>
        <Link href="/">Return home?</Link>
      </div>
    );
  }
  return (
    <div className="container text-center justify-center items-center w-full flex flex-col gap-4">
      <h2 className="title">Starting demo </h2>
      <Loader2 className="animate-spin" />
    </div>
  );
}
