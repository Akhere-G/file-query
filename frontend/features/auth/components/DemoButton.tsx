"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/lib/apiUtils";
import { startDemo } from "../api/authApi";
import { track } from "@/lib/analytics/client";

interface DemoButtonProps {
  className?: string;
  variant?: "default" | "outline" | "ghost";
  label?: string;
}

export default function DemoButton({
  className,
  variant = "outline",
  label = "Try demo",
}: DemoButtonProps) {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function onClick() {
    setIsPending(true);
    setError(null);

    try {
      const result = await startDemo();

      if (!result.success) {
        setError(result.message ?? getErrorMessage(null));
        return;
      }

      track("demo_started");
      router.push("/dashboard");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <Button
        type="button"
        variant={variant}
        className={className}
        disabled={isPending}
        onClick={onClick}
      >
        {isPending ? "Starting demo..." : label}
      </Button>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
