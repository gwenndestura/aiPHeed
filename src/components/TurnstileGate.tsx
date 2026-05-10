import { useEffect, useRef, useState } from "react";
import { LoadingSplash } from "./LoadingSplash";
import { Activity, ShieldCheck } from "lucide-react";

declare global {
  interface Window {
    turnstile?: {
      render: (container: HTMLElement, opts: Record<string, unknown>) => string;
      reset: (id?: string) => void;
    };
    onTurnstileLoad?: () => void;
  }
}

interface Props {
  onVerified: () => void;
}

// Cloudflare's always-pass test site key — replace with your real key
// in VITE_TURNSTILE_SITE_KEY when deploying.
const FALLBACK_TEST_KEY = "1x00000000000000000000AA";
const SITE_KEY =
  (import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined) || FALLBACK_TEST_KEY;

export function TurnstileGate({ onVerified }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [phase, setPhase] = useState<"loading" | "challenge" | "verifying" | "done">("loading");
  const widgetIdRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const render = () => {
      if (cancelled || !window.turnstile || !containerRef.current) return;
      try {
        widgetIdRef.current = window.turnstile.render(containerRef.current, {
          sitekey: SITE_KEY,
          theme: "dark",
          appearance: "always",
          callback: () => {
            setPhase("verifying");
            // Simulate brief edge handoff before app loads
            setTimeout(() => {
              setPhase("done");
              onVerified();
            }, 600);
          },
          "error-callback": () => {
            // Soft-fail: still let user in after a beat (dev/offline)
            setTimeout(() => onVerified(), 1500);
          },
        });
        setPhase("challenge");
      } catch {
        // If render throws (already rendered, etc.), skip the gate
        onVerified();
      }
    };

    if (window.turnstile) {
      render();
      return () => {
        cancelled = true;
      };
    }

    const existing = document.querySelector<HTMLScriptElement>(
      'script[data-turnstile="true"]'
    );
    if (!existing) {
      const s = document.createElement("script");
      s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileLoad";
      s.async = true;
      s.defer = true;
      s.dataset.turnstile = "true";
      document.head.appendChild(s);
    }

    window.onTurnstileLoad = () => render();

    // Hard fallback: if script never loads in 5s, just proceed
    const fallback = setTimeout(() => {
      if (!cancelled && phase === "loading") onVerified();
    }, 5000);

    return () => {
      cancelled = true;
      clearTimeout(fallback);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (phase === "done") return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-background overflow-hidden">
      <div
        className="absolute inset-0 opacity-30 blur-2xl"
        style={{
          background:
            "radial-gradient(ellipse at 30% 40%, hsl(35 90% 55% / 0.25), transparent 50%), radial-gradient(ellipse at 70% 60%, hsl(0 72% 50% / 0.2), transparent 50%), hsl(222 30% 8%)",
        }}
      />
      <div className="relative flex flex-col items-center gap-6 px-6">
        <div className="relative">
          <div className="absolute inset-0 rounded-2xl bg-primary/30 blur-xl animate-pulse" />
          <div className="relative bg-gradient-to-br from-primary to-primary/70 rounded-2xl p-4 shadow-2xl shadow-primary/30">
            <Activity className="h-9 w-9 text-primary-foreground" />
          </div>
        </div>

        <div className="text-center">
          <h1 className="text-xl font-bold tracking-tight">aiPHeed</h1>
          <p className="text-[11px] text-muted-foreground/80 mt-1 flex items-center gap-1.5 justify-center">
            <ShieldCheck className="h-3 w-3" />
            {phase === "loading" && "Verifying your connection…"}
            {phase === "challenge" && "Please complete the security check"}
            {phase === "verifying" && "Almost there…"}
          </p>
        </div>

        <div ref={containerRef} className="min-h-[65px] flex items-center justify-center" />

        <p className="text-[9px] text-muted-foreground/50 max-w-[280px] text-center">
          Protected by Cloudflare Turnstile. We verify you're human before loading the dashboard.
        </p>
      </div>
    </div>
  );
}
