import { beforeEach, describe, expect, it, vi } from "vitest";

const posthog = vi.hoisted(() => ({
  capture: vi.fn(),
  get_explicit_consent_status: vi.fn(),
  init: vi.fn(),
  opt_in_capturing: vi.fn(),
  opt_out_capturing: vi.fn(),
  register: vi.fn(),
  startSessionRecording: vi.fn(),
  stopSessionRecording: vi.fn(),
}));

vi.mock("posthog-js", () => ({ default: posthog }));

describe("analytics consent", () => {
  beforeEach(() => {
    vi.resetModules();
    posthog.capture.mockReset();
    posthog.get_explicit_consent_status.mockReset();
    posthog.init.mockReset();
    posthog.opt_in_capturing.mockReset();
    posthog.opt_out_capturing.mockReset();
    posthog.register.mockReset();
    posthog.startSessionRecording.mockReset();
    posthog.stopSessionRecording.mockReset();
    posthog.get_explicit_consent_status.mockReturnValue("pending");
  });

  it("starts PostHog cookieless and opted out of persistence", async () => {
    const { initAnalytics } = await import("./client");

    initAnalytics();

    expect(posthog.init).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        cookieless_mode: "on_reject",
        opt_out_capturing_by_default: true,
        opt_out_persistence_by_default: true,
        persistence: "localStorage+cookie",
        person_profiles: "never",
        disable_session_recording: false,
        session_recording: expect.objectContaining({
          maskAllInputs: true,
          maskTextSelector: "*",
          maskAllElementAttributes: true,
          recordBody: false,
          recordHeaders: false,
          captureCanvas: { recordCanvas: false },
        }),
      }),
    );
  });

  it("turns persistent tracking on and off from consent choices", async () => {
    const { setAnalyticsConsent } = await import("./client");

    setAnalyticsConsent(true);
    setAnalyticsConsent(false);

    expect(posthog.opt_in_capturing).toHaveBeenCalledWith({
      captureEventName: false,
    });
    expect(posthog.opt_out_capturing).toHaveBeenCalledOnce();
    expect(posthog.startSessionRecording).toHaveBeenCalledOnce();
    expect(posthog.stopSessionRecording).toHaveBeenCalledOnce();
  });

  it("resumes session replay for a returning visitor who granted consent", async () => {
    posthog.get_explicit_consent_status.mockReturnValue("granted");
    const { initAnalytics } = await import("./client");

    initAnalytics();

    expect(posthog.startSessionRecording).toHaveBeenCalledOnce();
  });
});
