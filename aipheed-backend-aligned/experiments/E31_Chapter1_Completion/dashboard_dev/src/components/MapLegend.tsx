import { RISK_COLORS } from "@/data/types";

const LEVELS: Array<{ key: keyof typeof RISK_COLORS; label: string }> = [
  { key: "low", label: "Below 50%" },
  { key: "high", label: "50% or more" },
];

export function MapLegend() {
  return (
    <div className="qt-panel qt-bar gap-3 whitespace-nowrap">
      <span className="font-medium" title="Estimated probability that the food-stress composite is above its threshold. An unvalidated band, not an official classification.">Estimate (unvalidated)</span>
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
