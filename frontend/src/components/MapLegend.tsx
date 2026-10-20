import { NO_DATA_COLOR, RISK_COLORS } from "@/data/types";
import { useConfig } from "@/lib/queries";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

/** What each colour on the map means, with the cutoff from the server's config. */
function useMeanings() {
  const { data: config } = useConfig();
  const cutoff = (config?.thresholds.riskDisplayCutoff ?? 0.5).toFixed(2);
  return {
    high: `High risk: a score of ${cutoff} or more, on a scale from 0 to 1`,
    low: `Low risk: a score below ${cutoff}`,
    none: "No forecast: withheld by DA or not enough data this quarter",
  };
}

/**
 * The map's risk legend.
 *
 * Tablets and desktops: a 32px column the width of the map buttons, placed by
 * the map page at the bottom right; one block per colour, each explained in a
 * tooltip. `compact`: phones' slim box in the top-left corner.
 */
export function MapLegend({ compact = false }: { compact?: boolean }) {
  const meanings = useMeanings();
  const label = `Risk level legend. Red: ${meanings.high}. Yellow: ${meanings.low}. Grey: ${meanings.none}.`;

  if (compact) {
    const items = [
      { color: RISK_COLORS.low, text: "Low" },
      { color: RISK_COLORS.high, text: "High" },
      { color: NO_DATA_COLOR, text: "No forecast" },
    ];
    return (
      <div role="group" aria-label={label} className="qt-panel qt-bar-compact gap-3 whitespace-nowrap">
        <span aria-hidden className="font-medium">Risk level</span>
        <ul aria-hidden className="flex items-center gap-3">
          {items.map((l) => (
            <li key={l.text} className="flex items-center gap-1.5">
              <span className="qt-swatch" style={{ background: l.color }} />
              <span className="qt-muted">{l.text}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  // Text on each colour meets WCAG AA (4.5:1) at 10px: near-black on red
  // (5.1:1; white is only 3.8:1 on this red) and on yellow, white on grey.
  const blocks = [
    { key: "high", color: RISK_COLORS.high, text: "High", ink: "#0D0F14", tip: meanings.high, name: undefined },
    { key: "low", color: RISK_COLORS.low, text: "Low", ink: "#0D0F14", tip: meanings.low, name: undefined },
    { key: "none", color: NO_DATA_COLOR, text: "—", ink: "#FFFFFF", tip: meanings.none, name: "No forecast" },
  ];
  return (
    <div
      role="group"
      aria-label={label}
      className="w-8 flex flex-col items-stretch surface-float rounded-md overflow-hidden border"
    >
      <span aria-hidden className="text-[10px] leading-4 py-0.5 text-center text-muted-foreground">Risk</span>
      {/* Plain-text tooltips: nothing to hover inside them, so moving off a
          block (even towards its tooltip) closes it and the next one opens. */}
      {blocks.map((b) => (
        <Tooltip key={b.key} disableHoverableContent>
          <TooltipTrigger asChild>
            <span
              tabIndex={0}
              aria-label={b.name}
              className="h-7 flex items-center justify-center text-[10px] font-semibold leading-none cursor-help focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
              style={{ background: b.color, color: b.ink }}
            >
              {b.text}
            </span>
          </TooltipTrigger>
          <TooltipContent side="left">{b.tip}</TooltipContent>
        </Tooltip>
      ))}
    </div>
  );
}
