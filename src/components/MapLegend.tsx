import { RISK_COLORS } from "@/data/types";

const LEVELS: Array<{ key: keyof typeof RISK_COLORS; label: string }> = [
  { key: "low", label: "Low" },
  { key: "high", label: "High" },
];

export function MapLegend() {
  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-border/40 shadow-md"
      style={{
        background: "hsl(var(--card) / 0.7)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
      }}
    >
      <span className="text-[9px] uppercase tracking-widest text-muted-foreground/80 font-semibold">
        RFII
      </span>
      <div className="flex items-center gap-1.5">
        {LEVELS.map((l) => (
          <div key={l.key} className="flex items-center gap-1">
            <span
              className="w-2.5 h-2.5 rounded-sm"
              style={{ background: RISK_COLORS[l.key], boxShadow: `0 0 4px ${RISK_COLORS[l.key]}80` }}
            />
            <span className="text-[9px] text-foreground/80">{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
