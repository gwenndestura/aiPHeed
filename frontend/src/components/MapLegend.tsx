import { RISK_COLORS } from "@/data/types";

const LEVELS: Array<{ key: keyof typeof RISK_COLORS; label: string }> = [
  { key: "low", label: "Low" },
  { key: "high", label: "High" },
];

export function MapLegend() {
  return (
    <div className="qt-panel qt-bar gap-3 whitespace-nowrap">
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
