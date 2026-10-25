import { cn } from "@/lib/utils";

export type RiskLevelKey = "low" | "moderate" | "high" | "severe";
export type StatusTone = "low" | "moderate" | "high" | "positive" | "neutral";

/** The words a risk badge shows. "Severe" has no band of its own: it reads as high. */
export const RISK_BADGE_TEXT: Record<RiskLevelKey, string> = {
  low: "Low priority",
  moderate: "Moderate priority",
  high: "High priority",
  severe: "High priority",
};

const TONE_CLASS: Record<StatusTone, string> = {
  low: "bg-risk-low-bg text-risk-low-text border-risk-low-border",
  moderate: "bg-risk-moderate-bg text-risk-moderate-text border-risk-moderate-border",
  high: "bg-risk-high-bg text-risk-high-text border-risk-high-border",
  positive: "bg-status-positive-bg text-status-positive-text border-status-positive-border",
  neutral: "bg-status-neutral-bg text-status-neutral-text border-status-neutral-border",
};

const SWATCH_CLASS: Record<StatusTone, string> = {
  low: "bg-risk-low",
  moderate: "bg-risk-moderate",
  high: "bg-risk-high",
  positive: "bg-value-success",
  neutral: "bg-ink-muted",
};

const toneOf = (level: RiskLevelKey): StatusTone => (level === "severe" ? "high" : level);

interface Props {
  /** A risk band: the badge text ("Low risk", …) follows from it. */
  level?: RiskLevelKey | null;
  /** Any other status (e.g. a review state), with its text as children. */
  tone?: StatusTone;
  /** An 8px flat swatch before the text, in the band's map colour. */
  swatch?: "square" | "circle";
  bordered?: boolean;
  title?: string;
  className?: string;
  children?: React.ReactNode;
}

/**
 * A small status rectangle: tinted background, same-hue darker text,
 * always with words, so meaning never rests on colour alone.
 */
export function StatusBadge({ level, tone, swatch, bordered = true, title, className, children }: Props) {
  const t: StatusTone = level ? toneOf(level) : tone ?? "neutral";
  const text = children ?? (level ? RISK_BADGE_TEXT[level] : null);
  return (
    <span
      title={title}
      className={cn(
        "ui-badge inline-flex items-center gap-1.5 px-2 py-0.5 text-label font-medium whitespace-nowrap",
        bordered ? "border" : "border border-transparent",
        TONE_CLASS[t],
        className,
      )}
    >
      {swatch && (
        <span
          aria-hidden
          className={cn("inline-block h-2 w-2 shrink-0", swatch === "circle" && "rounded-full", SWATCH_CLASS[t])}
        />
      )}
      {text}
    </span>
  );
}
