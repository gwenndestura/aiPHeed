// src/components/AuthCard.tsx
// -----------------------------
// The account pages' card, field, button and messages, shared by sign-in,
// request access, verify email and forgot / reset password, so they all
// look the same.
//
// Flat on purpose: a solid card with a 1px border, no glows or blurs.
// Secondary text uses the foreground colour at reduced opacity rather than
// the muted grey, which falls short of WCAG AA contrast on the dark card.

import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Eye, EyeOff, type LucideIcon } from "lucide-react";
import logoIcon from "@/assets/logo-icon.png";

export const PASSWORD_RULES =
  "At least 12 characters, and not a commonly used password. A few unrelated words make a strong passphrase that is easy to remember.";

export const DOMAIN_HINT = "Use your @calabarzon.da.gov.ph email address.";

/** Links on the account pages: 13px, readable, with a visible keyboard focus ring. */
export const authLinkClass =
  "text-[13px] compact:inline-flex compact:items-center compact:min-h-11 text-foreground/90 underline underline-offset-2 hover:text-foreground rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card";

/** A row of secondary links under the form. */
export const authLinksRowClass = "mt-5 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-[13px] text-foreground/80";

/** Logo, product name and the agency line, at the top of the card. */
export function AuthBrand() {
  return (
    <div className="flex items-center gap-3">
      <img src={logoIcon} alt="" className="h-10 w-10 object-contain shrink-0" />
      <div className="min-w-0">
        <p className="text-[15px] font-semibold leading-tight">aiPHeed</p>
        <p className="text-[12px] text-foreground/75 leading-snug">Department of Agriculture · Regional Field Office IV-A</p>
      </div>
    </div>
  );
}

export function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  /** Only when it tells the reader something the title does not. */
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen w-full bg-background flex items-center justify-center px-4 py-8 sm:p-6">
      <div className="w-full max-w-sm bg-card border edge-faint rounded-xl shadow-lg p-6 sm:p-7">
        <Link to="/dashboard" className={authLinkClass + " no-underline hover:underline"}>
          ← Back to map
        </Link>
        <div className="mt-5">
          <AuthBrand />
        </div>
        <h1 className="mt-6 text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-[13px] text-foreground/80 leading-snug">{subtitle}</p>}
        <div className="mt-5">{children}</div>
      </div>
    </div>
  );
}

interface FieldProps {
  id: string;
  label: string;
  icon: LucideIcon;
  value: string;
  onChange: (v: string) => void;
  type?: "text" | "email" | "password";
  autoComplete?: string;
  maxLength?: number;
  required?: boolean;
  /** Small text under the field (e.g. the password rules). */
  hint?: ReactNode;
  /** Something on the label's line, right-aligned (e.g. "Forgot password?"). */
  aside?: ReactNode;
}

export function AuthField({ id, label, icon: Icon, value, onChange, type = "text", autoComplete, maxLength = 200, required = true, hint, aside }: FieldProps) {
  const [show, setShow] = useState(false);
  const isPassword = type === "password";
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-[13px] font-medium text-foreground">
          {label}
        </label>
        {aside}
      </div>
      <div className="relative mt-1.5">
        <Icon className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-foreground/60" aria-hidden />
        <input
          id={id}
          type={isPassword && show ? "text" : type}
          required={required}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          maxLength={maxLength}
          placeholder=""
          autoComplete={autoComplete}
          aria-describedby={hint ? `${id}-hint` : undefined}
          className={`w-full h-10 compact:h-11 compact:text-[16px] pl-9 ${isPassword ? "pr-10 compact:pr-12" : "pr-3"} text-[13px] bg-background border border-border/20 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus:border-primary/60`}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            aria-label={show ? "Hide password" : "Show password"}
            aria-pressed={show}
            title={show ? "Hide password" : "Show password"}
            className="absolute right-1.5 compact:right-0 top-1/2 -translate-y-1/2 p-1.5 compact:min-h-11 compact:min-w-11 flex items-center justify-center rounded-md text-foreground/70 hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {show ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>
      {hint && (
        <p id={`${id}-hint`} className="mt-1.5 text-[12px] compact:text-[14px] text-foreground/75 leading-snug">
          {hint}
        </p>
      )}
    </div>
  );
}

export function AuthSubmit({ loading, label, loadingLabel }: { loading: boolean; label: string; loadingLabel: string }) {
  // Near-black on amber in both themes, as on the landing page's amber button:
  // the light theme's white primary-foreground is only 2.3:1 on amber (WCAG AA needs 4.5).
  return (
    <button
      type="submit"
      disabled={loading}
      className="w-full h-10 compact:h-11 compact:text-[14px] rounded-md bg-primary text-[#0D0F14] text-[13px] font-semibold hover:bg-primary/90 transition-colors disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card"
    >
      {loading ? loadingLabel : label}
    </button>
  );
}

/** A problem with what was just submitted, inside the form, announced to screen readers. */
export function AuthAlert({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="border-l-2 border-destructive pl-2.5 text-[13px] text-foreground leading-snug">
      {children}
    </p>
  );
}

/** "Need access? Request access" under the sign-in button. */
export function AccessPrompt({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <p className="mt-5 text-center text-[13px] text-foreground/80">
      Need access?{" "}
      <Link to="/signup" onClick={onNavigate} className={authLinkClass}>
        Request access
      </Link>
    </p>
  );
}
