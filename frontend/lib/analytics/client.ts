import posthog from "posthog-js";
import type { AnalyticsEvent, AnalyticsProperties } from "./events";

// Analytics stay off when the token is not set at build time.
const KEY = process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN;
const HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://eu.i.posthog.com";

let ready = false;

// Cookieless mode must also be enabled in the PostHog project settings.
export function initAnalytics() {
  if (ready || typeof window === "undefined" || !KEY) return;

  try {
    posthog.init(KEY, {
      api_host: HOST,
      cookieless_mode: "always",
      persistence: "memory",
      person_profiles: "identified_only",
      autocapture: false,
      capture_pageview: false,
      capture_pageleave: false,
      disable_session_recording: true,
      disable_surveys: true,
      advanced_disable_flags: true,
    });
    ready = true;
  } catch {
    ready = false;
  }
}

export function track(
  event: AnalyticsEvent,
  properties?: AnalyticsProperties,
  options?: { sendInstantly?: boolean },
) {
  if (!ready) return;

  try {
    posthog.capture(event, properties, {
      send_instantly: options?.sendInstantly,
    });
  } catch {}
}

export function setEventContext(properties: AnalyticsProperties) {
  if (!ready) return;

  try {
    posthog.register(properties);
  } catch {}
}
