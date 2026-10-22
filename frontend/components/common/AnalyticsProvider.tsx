"use client";

import { useEffect, useRef } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { initAnalytics, setEventContext, track } from "@/lib/analytics/client";
import { pageEventFor } from "@/lib/analytics/events";

type Props = {
  isAuthenticated: boolean;
  isDemo: boolean;
};

export default function AnalyticsProvider({ isAuthenticated, isDemo }: Props) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const hasProject = searchParams.has("projectId");
  const lastViewed = useRef<string | null>(null);

  useEffect(() => {
    initAnalytics();
  }, []);

  useEffect(() => {
    setEventContext({ is_authenticated: isAuthenticated, is_demo: isDemo });
  }, [isAuthenticated, isDemo]);

  useEffect(() => {
    const event = pageEventFor(pathname);
    if (!event) return;

    const key = `${pathname}|${hasProject}`;
    if (lastViewed.current === key) return;
    lastViewed.current = key;

    track(event, pathname === "/dashboard" ? { has_project: hasProject } : {});
  }, [pathname, hasProject]);

  return null;
}
