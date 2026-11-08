import { cn } from "@/lib/utils";

/** The label over a figure: sentence case, spelled out, no icon. */
export function MetricLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("text-label text-ink-secondary", className)}>{children}</div>;
}

export type ValueTone = "neutral" | "danger" | "success";

const TONE_CLASS: Record<ValueTone, string> = {
  neutral: "text-ink",
  danger: "text-value-danger",
  success: "text-value-success",
};

/**
 * The figure under a MetricLabel, in tabular numbers. Colour it only when
 * the colour means something (see changeTone), never for decoration.
 */
export function MetricValue({
  children,
  size = "key",
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  size?: "key" | "emphasis" | "body";
  tone?: ValueTone;
  className?: string;
}) {
  const sizeClass = size === "key" ? "text-key font-semibold" : size === "emphasis" ? "text-emphasis font-medium" : "text-body font-medium";
  return <div className={cn(sizeClass, "tabular-nums", TONE_CLASS[tone], className)}>{children}</div>;
}

/**
 * A signed figure with a real minus sign: "+4.2%", "−1.8 pts", "0.0%".
 * `unit` is appended as given, so pass " pts" with its space.
 */
export function formatSigned(value: number, digits = 1, unit = ""): string {
  const abs = Math.abs(value).toFixed(digits);
  if (Number(abs) === 0) return `${abs}${unit}`;
  return `${value > 0 ? "+" : "−"}${abs}${unit}`;
}

/** For a change in risk: an increase is a danger, a decrease a success. */
export function changeTone(value: number | null | undefined, epsilon = 0): ValueTone {
  if (value == null) return "neutral";
  if (value > epsilon) return "danger";
  if (value < -epsilon) return "success";
  return "neutral";
}
