import { regionsData } from "@/data/mockData";
import { RISK_COLORS } from "@/data/types";
import { ChevronRight, ChevronLeft } from "lucide-react";

interface Props {
  side: "left" | "right";
  onExpand: () => void;
}

export function SidebarPeek({ side, onExpand }: Props) {
  const avg = regionsData.reduce((s, r) => s + r.riskScore, 0) / regionsData.length;
  const sorted = [...regionsData].sort((a, b) => b.riskScore - a.riskScore);

  if (side === "left") {
    return (
      <button
        onClick={onExpand}
        className="h-full w-full flex flex-col items-center py-4 gap-3 hover:bg-secondary/40 transition-colors group"
        title="Open panel"
        aria-label="Open left panel"
      >
        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground group-hover:text-foreground" />
        <div className="font-mono-num text-[11px] font-bold text-primary writing-vertical" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}>
          RFII {avg.toFixed(2)}
        </div>
        <div className="flex flex-col gap-1.5 mt-2">
          {sorted.map((r) => (
            <span
              key={r.id}
              className="w-2 h-2 rounded-full"
              style={{
                backgroundColor: RISK_COLORS[r.riskLevel],
                boxShadow: `0 0 5px ${RISK_COLORS[r.riskLevel]}`,
              }}
              title={r.name}
            />
          ))}
        </div>
      </button>
    );
  }

  // right peek: mini donut + 2 mini bars
  const top2 = sorted.slice(0, 2);
  const C = 2 * Math.PI * 14;
  return (
    <button
      onClick={onExpand}
      className="h-full w-full flex flex-col items-center py-4 gap-3 hover:bg-secondary/40 transition-colors group"
      title="Open panel"
      aria-label="Open right panel"
    >
      <ChevronLeft className="h-3.5 w-3.5 text-muted-foreground group-hover:text-foreground" />
      <svg viewBox="0 0 36 36" className="w-9 h-9 -rotate-90">
        <circle cx="18" cy="18" r="14" fill="none" stroke="hsl(var(--secondary))" strokeWidth="4" />
        <circle
          cx="18"
          cy="18"
          r="14"
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={`${avg * C} ${C}`}
          style={{ filter: "drop-shadow(0 0 4px hsl(var(--primary)/0.7))" }}
        />
      </svg>
      <span className="font-mono-num text-[10px] font-bold text-primary tabular-nums">{avg.toFixed(2)}</span>
      <div className="flex flex-col gap-1.5 mt-1 px-2 w-full">
        {top2.map((r) => (
          <div key={r.id} className="flex flex-col items-center gap-0.5">
            <span className="text-[8px] uppercase tracking-wider text-muted-foreground/70 truncate w-full text-center">
              {r.name.slice(0, 4)}
            </span>
            <div className="h-1 w-full bg-secondary/40 rounded-full overflow-hidden">
              <div className="h-full" style={{ width: `${r.riskScore * 100}%`, background: RISK_COLORS[r.riskLevel] }} />
            </div>
          </div>
        ))}
      </div>
    </button>
  );
}
