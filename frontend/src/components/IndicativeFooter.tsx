/**
 * Spec Rule 5 — Persistent indicative-not-absolute disclaimer.
 * Sticky thin strip visible on every forecast view.
 */
export function IndicativeFooter() {
  return (
    <div className="pointer-events-none select-none px-3 py-1 rounded-full glass border border-border/50 shadow-md">
      <p className="text-[9px] text-muted-foreground/90 italic font-medium tracking-wide whitespace-nowrap">
        Indicative estimate — not an official food insecurity classification.
      </p>
    </div>
  );
}
