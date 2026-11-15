"use client";

import Link from "next/link";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  getAnalyticsConsent,
  setAnalyticsConsent,
  type AnalyticsConsent,
} from "@/lib/analytics/client";

type CookieConsentContextValue = {
  consent: AnalyticsConsent;
  openPreferences: () => void;
};

const CookieConsentContext = createContext<CookieConsentContextValue | null>(
  null,
);

const subscribeNever = () => () => {};

export function CookieConsentProvider({ children }: { children: ReactNode }) {
  const mounted = useSyncExternalStore(
    subscribeNever,
    () => true,
    () => false,
  );
  const [consent, setConsent] = useState<AnalyticsConsent>(() =>
    typeof window === "undefined" ? "pending" : getAnalyticsConsent(),
  );
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [analyticsEnabled, setAnalyticsEnabled] = useState(false);

  const saveConsent = useCallback((enabled: boolean) => {
    setAnalyticsConsent(enabled);
    setConsent(enabled ? "granted" : "denied");
    setAnalyticsEnabled(enabled);
    setPreferencesOpen(false);
  }, []);

  const openPreferences = useCallback(() => {
    setAnalyticsEnabled(consent === "granted");
    setPreferencesOpen(true);
  }, [consent]);

  const contextValue = useMemo(
    () => ({ consent, openPreferences }),
    [consent, openPreferences],
  );

  return (
    <CookieConsentContext.Provider value={contextValue}>
      {children}

      {mounted && consent === "pending" && (
        <aside
          aria-label="Cookie consent"
          className="fixed inset-x-4 bottom-4 z-40 mx-auto max-w-4xl border border-border bg-card p-5 text-card-foreground shadow-xl md:p-6"
        >
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div className="max-w-2xl space-y-2">
              <h2 className="font-heading text-lg font-semibold tracking-wide uppercase">
                Your cookie choices
              </h2>
              <p className="text-sm leading-relaxed text-muted-foreground">
                We use required cookies to run FileQuery. With your permission,
                we also use PostHog analytics cookies to understand how the
                service is used. Until you accept, PostHog runs without cookies.
                Read our{" "}
                <Link href="/privacy" className="underline hover:text-foreground">
                  privacy policy
                </Link>
                .
              </p>
            </div>
            <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
              <Button variant="outline" onClick={openPreferences}>
                Choose options
              </Button>
              <Button onClick={() => saveConsent(true)}>Accept cookies</Button>
            </div>
          </div>
        </aside>
      )}

      <Dialog open={preferencesOpen} onOpenChange={setPreferencesOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cookie options</DialogTitle>
            <DialogDescription>
              Choose which optional cookies FileQuery may use. You can change
              this choice at any time. See our <Link href="/privacy">privacy policy</Link>.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div className="flex items-start gap-3 border border-border p-4">
              <Checkbox
                id="required-cookies"
                aria-label="Required cookies"
                checked
                disabled
              />
              <label htmlFor="required-cookies" className="space-y-1">
                <span className="block text-sm font-semibold">Required cookies</span>
                <span className="block text-sm leading-relaxed text-muted-foreground">
                  Keep you signed in, remember essential interface state, and
                  store your cookie choice. These cannot be switched off.
                </span>
              </label>
            </div>

            <div className="flex items-start gap-3 border border-border p-4">
              <Checkbox
                id="analytics-cookies"
                aria-label="Analytics cookies"
                checked={analyticsEnabled}
                onCheckedChange={setAnalyticsEnabled}
              />
              <label
                htmlFor="analytics-cookies"
                className="cursor-pointer space-y-1"
              >
                <span className="block text-sm font-semibold">Analytics cookies</span>
                <span className="block text-sm leading-relaxed text-muted-foreground">
                  Let PostHog recognize the same browser across visits so we can
                  measure page views, whether product features succeed, and
                  record privacy-masked session replays.
                </span>
              </label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => saveConsent(false)}>
              Reject optional cookies
            </Button>
            <Button onClick={() => saveConsent(analyticsEnabled)}>
              Save choices
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </CookieConsentContext.Provider>
  );
}

export function CookiePreferencesButton({
  className,
  variant = "outline",
}: {
  className?: string;
  variant?: "outline" | "link";
}) {
  const context = useContext(CookieConsentContext);

  if (!context) {
    throw new Error(
      "CookiePreferencesButton must be used inside CookieConsentProvider",
    );
  }

  return (
    <Button
      type="button"
      variant={variant}
      className={className}
      onClick={context.openPreferences}
    >
      Cookie settings
    </Button>
  );
}
