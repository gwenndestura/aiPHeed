import { regionsData } from "@/data/mockData";
import { RISK_COLORS } from "@/data/types";
import { AlertTriangle, TrendingUp } from "lucide-react";

export function EmphasisAlerts() {
  const severeRegions = regionsData
    .filter((r) => r.riskLevel === "high")
    .sort((a, b) => b.riskScore - a.riskScore);
  
  const topMoM = regionsData
    .filter((r) => r.momChange > 3)
    .sort((a, b) => b.momChange - a.momChange)
    .slice(0, 3);

  return (
    <div className="space-y-2.5 w-[260px]">
      {/* Severe alert */}
      {severeRegions.length > 0 && (
        <div className="bg-card/85 backdrop-blur-md border border-destructive/20 rounded-xl px-3.5 py-3 shadow-2xl shadow-destructive/5">
          <div className="flex items-center gap-2 mb-2.5">
            <div className="emphasis-blink-square" />
            <span className="text-[9px] font-bold uppercase tracking-widest text-destructive/90">Severe Alert</span>
          </div>
          <div className="space-y-1">
            {severeRegions.map((r) => (
              <div key={r.id} className="flex items-center justify-between py-1 px-1.5 rounded-md hover:bg-destructive/5 transition-colors">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-3 w-3 text-destructive/70" />
                  <span className="text-[10px] font-medium text-foreground/90">{r.name}</span>
                </div>
                <span className="text-[10px] font-bold tabular-nums text-destructive">{r.riskScore.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rising trends */}
      {topMoM.length > 0 && (
        <div className="bg-card/85 backdrop-blur-md border border-risk-high/20 rounded-xl px-3.5 py-3 shadow-2xl shadow-risk-high/5">
          <div className="flex items-center gap-2 mb-2.5">
            <div className="emphasis-pulse-circle" />
            <span className="text-[9px] font-bold uppercase tracking-widest text-risk-high/90">Rising Trends</span>
          </div>
          <div className="space-y-1">
            {topMoM.map((r) => (
              <div key={r.id} className="flex items-center justify-between py-1 px-1.5 rounded-md hover:bg-risk-high/5 transition-colors">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-3 w-3 text-risk-high/70" />
                  <span className="text-[10px] font-medium text-foreground/90">{r.name}</span>
                </div>
                <span className="text-[10px] font-bold tabular-nums text-risk-high">+{r.momChange}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="bg-card/70 backdrop-blur-md border border-border/30 rounded-xl px-3.5 py-2 shadow-lg">
        <div className="flex items-center gap-4">
          {([
            { level: "high" as const, label: "High (≥0.50)" },
            { level: "low" as const, label: "Low (<0.50)" },
          ]).map(({ level, label }) => (
            <div key={level} className="flex items-center gap-1.5 text-[9px] text-foreground/60">
              <span className="w-2 h-2 rounded-full ring-1 ring-offset-1 ring-offset-transparent" style={{ backgroundColor: RISK_COLORS[level], boxShadow: `0 0 4px ${RISK_COLORS[level]}40` }} />
              <span>{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
