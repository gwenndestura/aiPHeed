import { cn } from "@/lib/utils";

/**
 * An 8px flat dot: solid fill, no glow, no animation. Decorative — put
 * the meaning in adjacent text.
 */
export function StatusDot({ color, className }: { color: string; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn("inline-block h-2 w-2 shrink-0 rounded-full", className)}
      style={{ background: color }}
    />
  );
}
