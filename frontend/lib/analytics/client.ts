import posthog from "posthog-js";
import type { AnalyticsEvent, AnalyticsProperties } from "./events";

const KEY =
  process.env.NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN ??
  "phc_qfHerWar58zqtbrpFJx4ydWd7tzdGr4WVRBZTzjY5KJJ";
const HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://eu.i.posthog.com";

let ready = false;

export type AnalyticsConsent = "pending" | "granted" | "denied";

function redactReplayRequest<T extends { name: string }>(request: T): T {
  try {
    const url = new URL(request.name, window.location.origin);
    return { ...request, name: `${url.origin}${url.pathname}` };
  } catch {
    return request;
  }
}

// Cookieless mode must also be enabled in the PostHog project settings.
export function initAnalytics() {
  if (ready || typeof window === "undefined" || !KEY) return;

  try {
    posthog.init(KEY, {
      api_host: HOST,
      cookieless_mode: "on_reject",
      persistence: "localStorage+cookie",
      opt_out_capturing_by_default: true,
      opt_out_persistence_by_default: true,
      person_profiles: "never",
      autocapture: false,
      capture_pageview: false,
      capture_pageleave: false,
      disable_session_recording: false,
      session_recording: {
        maskAllInputs: true,
        maskTextSelector: "*",
        maskAllElementAttributes: true,
        blockSelector: 'input[type="file"], [data-posthog-block]',
        recordBody: false,
        recordHeaders: false,
        captureCanvas: { recordCanvas: false },
        captureJsonLd: false,
        maskCapturedNetworkRequestFn: redactReplayRequest,
      },
      disable_surveys: true,
      advanced_disable_flags: true,
    });
    ready = true;

    if (posthog.get_explicit_consent_status() === "granted") {
      posthog.startSessionRecording();
    }
  } catch {
    ready = false;
  }
}

export function getAnalyticsConsent(): AnalyticsConsent {
  initAnalytics();
  if (!ready) return "pending";

  try {
    return posthog.get_explicit_consent_status();
  } catch {
    return "pending";
  }
}

export function setAnalyticsConsent(enabled: boolean) {
  initAnalytics();
  if (!ready) return;

  try {
    if (enabled) {
      posthog.opt_in_capturing({ captureEventName: false });
      posthog.startSessionRecording();
    } else {
      posthog.stopSessionRecording();
      posthog.opt_out_capturing();
    }
  } catch {}
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
