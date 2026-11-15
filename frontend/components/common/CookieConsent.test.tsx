import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  CookieConsentProvider,
  CookiePreferencesButton,
} from "./CookieConsent";

const analytics = vi.hoisted(() => ({
  consent: "pending" as "pending" | "granted" | "denied",
  initAnalytics: vi.fn(),
  setAnalyticsConsent: vi.fn(),
}));

vi.mock("@/lib/analytics/client", () => ({
  getAnalyticsConsent: () => analytics.consent,
  initAnalytics: analytics.initAnalytics,
  setAnalyticsConsent: analytics.setAnalyticsConsent,
}));

describe("CookieConsentProvider", () => {
  beforeEach(() => {
    analytics.consent = "pending";
    analytics.initAnalytics.mockReset();
    analytics.setAnalyticsConsent.mockReset();
  });

  it("offers an accept action and saves analytics consent", async () => {
    const user = userEvent.setup();
    render(
      <CookieConsentProvider>
        <div>App</div>
      </CookieConsentProvider>,
    );

    expect(await screen.findByLabelText("Cookie consent")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Accept cookies" }));

    expect(analytics.setAnalyticsConsent).toHaveBeenCalledWith(true);
    expect(screen.queryByLabelText("Cookie consent")).not.toBeInTheDocument();
  });

  it("lets a visitor reject optional cookies from the options modal", async () => {
    const user = userEvent.setup();
    render(
      <CookieConsentProvider>
        <div>App</div>
      </CookieConsentProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Choose options" }),
    );
    expect(screen.getByRole("dialog", { name: "Cookie options" })).toBeVisible();

    await user.click(
      screen.getByRole("button", { name: "Reject optional cookies" }),
    );

    expect(analytics.setAnalyticsConsent).toHaveBeenCalledWith(false);
    expect(screen.queryByLabelText("Cookie consent")).not.toBeInTheDocument();
  });

  it("reopens saved preferences and allows analytics to be withdrawn", async () => {
    analytics.consent = "granted";
    const user = userEvent.setup();
    render(
      <CookieConsentProvider>
        <CookiePreferencesButton />
      </CookieConsentProvider>,
    );

    expect(screen.queryByLabelText("Cookie consent")).not.toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Cookie settings" }));
    await user.click(
      screen.getByRole("checkbox", { name: /^Analytics cookies/ }),
    );
    await user.click(screen.getByRole("button", { name: "Save choices" }));

    expect(analytics.setAnalyticsConsent).toHaveBeenCalledWith(false);
  });
});
