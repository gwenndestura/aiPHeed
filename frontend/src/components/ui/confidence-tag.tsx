import { cn } from "@/lib/utils";
import { ExplainTip } from "@/components/ui/explain-tip";

interface Props {
  /** The tag text, e.g. "Limited data" or "Low confidence". */
  children?: React.ReactNode;
  /** Why the tag applies: a tooltip on hover and keyboard focus, a popover on a tap (ExplainTip). */
  explanation?: string;
  className?: string;
}

/**
 * A plain-text caveat on a figure: secondary colour, no icon, no chip.
 * With an explanation it is focusable and underlined to show it has one.
 */
export function ConfidenceTag({ children = "Limited data", explanation, className }: Props) {
  const base = "text-label text-ink-secondary whitespace-nowrap";
  if (!explanation) return <span className={cn(base, className)}>{children}</span>;
  return (
    <ExplainTip explanation={explanation}>
      <span
        tabIndex={0}
        className={cn(
          base,
          "cursor-help underline decoration-dotted underline-offset-2 rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
          className,
        )}
      >
        {children}
      </span>
    </ExplainTip>
  );
}
