// src/components/AuthCard.tsx
// -----------------------------
// The sign-in page's card, field and button, shared by every account page
// (sign-in, sign-up, verify email, forgot / reset password) so they all look
// the same. The classes are the sign-in page's own, unchanged.

import { useState, type ReactNode } from "react";
import { Eye, EyeOff, ArrowRight, type LucideIcon } from "lucide-react";
import logoIcon from "@/assets/logo-icon.png";

export function AuthCard({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="min-h-screen w-full bg-background flex items-center justify-center p-6 relative overflow-hidden">
      {/* Decorative gradient orbs */}
      <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-primary/15 blur-3xl" />
      <div className="absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-risk-severe/10 blur-3xl" />

      <div className="relative w-full max-w-sm bg-card/95 backdrop-blur-md border border-border/50 rounded-2xl shadow-2xl shadow-primary/10 p-7">
        <div className="flex flex-col items-center text-center mb-6">
          <img src={logoIcon} alt="aiPHeed" className="h-20 w-20 object-contain mb-3 drop-shadow-[0_0_24px_rgba(232,69,60,0.35)]" />
          <h1 className="text-lg font-bold tracking-tight">{title}</h1>
          <p className="text-[11px] text-muted-foreground mt-1">{subtitle}</p>
        </div>
        {children}
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
}

export function AuthField({ id, label, icon: Icon, value, onChange, type = "text", autoComplete, maxLength = 200, required = true, hint }: FieldProps) {
  const [show, setShow] = useState(false);
  const isPassword = type === "password";
  return (
    <div>
      <label htmlFor={id} className="text-[10px] uppercase tracking-wider text-muted-foreground/70 font-semibold">
        {label}
      </label>
      <div className="relative mt-1">
        <Icon className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60" />
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
          className={`w-full h-10 pl-9 ${isPassword ? "pr-10" : "pr-3"} text-[12px] bg-secondary/50 border border-border/40 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus:border-primary/50 focus:bg-secondary/80 placeholder:text-muted-foreground/50`}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            aria-label={show ? "Hide password" : "Show password"}
            aria-pressed={show}
            title={show ? "Hide password" : "Show password"}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-muted-foreground hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {show ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>
      {hint && (
        <p id={`${id}-hint`} className="text-[10px] text-muted-foreground mt-1 leading-snug">
          {hint}
        </p>
      )}
    </div>
  );
}

export function AuthSubmit({ loading, label, loadingLabel }: { loading: boolean; label: string; loadingLabel: string }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="w-full h-10 mt-2 flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground text-[12px] font-bold hover:bg-primary/90 transition-colors shadow-md shadow-primary/20 disabled:opacity-60"
    >
      {loading ? loadingLabel : label}
      {!loading && <ArrowRight className="h-3.5 w-3.5" />}
    </button>
  );
}

/** The small underlined links under the card ("Back to public map" style). */
export const authLinkClass = "hover:text-foreground underline underline-offset-2";
export const authLinksRowClass = "text-center text-[10px] text-muted-foreground mt-4 flex flex-wrap items-center justify-center gap-x-3 gap-y-1";

export const PASSWORD_RULES =
  "At least 12 characters, and not a commonly used password. A few unrelated words make a strong passphrase that is easy to remember.";
