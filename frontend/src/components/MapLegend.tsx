import { RISK_COLORS } from "@/data/types";

const LEVELS: Array<{ key: keyof typeof RISK_COLORS; label: string }> = [
  { key: "low", label: "Low" },
  { key: "high", label: "High" },
];

/** `compact`: a slimmer box, for the phone layout's top-left corner. */
export function MapLegend({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`qt-panel ${compact ? "qt-bar-compact" : "qt-bar"} gap-3 whitespace-nowrap`}>
      <span className="font-medium">Risk level</span>
      <ul className="flex items-center gap-3">
        {LEVELS.map((l) => (
          <li key={l.key} className="flex items-center gap-1.5">
            <span aria-hidden className="qt-swatch" style={{ background: RISK_COLORS[l.key] }} />
            <span className="qt-muted">{l.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
