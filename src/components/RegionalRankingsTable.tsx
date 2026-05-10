import { regionsData } from "@/data/mockData";
import { RISK_COLORS, RegionData } from "@/data/types";
import { ChevronRight, TrendingUp } from "lucide-react";

interface Props {
  onSelectRegion: (r: RegionData) => void;
}

export function RegionalRankingsTable({ onSelectRegion }: Props) {
  const sorted = [...regionsData].sort((a, b) => b.riskScore - a.riskScore);

  return (
    <div className="bg-card border rounded-lg p-4">
      <div className="mb-4">
        <h3 className="text-sm font-bold">Regional Risk Rankings</h3>
        <p className="text-xs text-muted-foreground">Sorted by RFII score — click a region for details</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold text-left py-2 px-2 w-10">#</th>
              <th className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold text-left py-2 px-2">REGION</th>
              <th className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold text-left py-2 px-2">RFII</th>
              <th className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold text-left py-2 px-2">TREND</th>
              <th className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold text-left py-2 px-2">RISK</th>
              <th className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold text-right py-2 px-2">HH AT RISK</th>
              <th className="py-2 px-2 w-6"></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((region, i) => (
              <tr
                key={region.id}
                onClick={() => onSelectRegion(region)}
                className="border-b border-border/50 hover:bg-muted/30 cursor-pointer transition-colors"
              >
                <td className="py-3 px-2 text-xs text-muted-foreground font-mono">
                  {String(i + 1).padStart(2, "0")}
                </td>
                <td className="py-3 px-2 text-sm font-semibold">{region.name}</td>
                <td className="py-3 px-2">
                  <span className="text-sm font-bold" style={{ color: RISK_COLORS[region.riskLevel] }}>
                    {region.riskScore.toFixed(2)}
                  </span>
                </td>
                <td className="py-3 px-2">
                  <span className={`text-xs flex items-center gap-1 ${region.momChange > 0 ? "text-destructive" : "text-risk-low"}`}>
                    <TrendingUp className="h-3 w-3" />
                    {region.momChange > 0 ? "+" : ""}{region.momChange}%
                  </span>
                </td>
                <td className="py-3 px-2">
                  <span
                    className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full"
                    style={{
                      backgroundColor: RISK_COLORS[region.riskLevel] + "20",
                      color: RISK_COLORS[region.riskLevel],
                    }}
                  >
                    {region.riskLevel}
                  </span>
                </td>
                <td className="py-3 px-2 text-right text-sm font-medium">
                  {region.householdsAtRisk >= 1000000
                    ? (region.householdsAtRisk / 1e6).toFixed(1) + "M"
                    : (region.householdsAtRisk / 1e3).toFixed(0) + "K"}
                </td>
                <td className="py-3 px-2">
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
