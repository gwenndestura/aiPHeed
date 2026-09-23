import { RegionData } from "@/data/types";
import { Cloud, AlertTriangle, Users, Sparkles } from "lucide-react";

interface Props {
  regions: RegionData[];
}

export function DashboardOverview({ regions }: Props) {
  const highRiskCount = regions.filter((r) => r.riskLevel === "high" || r.riskLevel === "severe").length;
  const avgScore = regions.reduce((s, r) => s + r.riskScore, 0) / regions.length;
  const totalHouseholds = regions.reduce((s, r) => s + r.householdsAtRisk, 0);

  const stats = [
    { label: "National Risk Level", value: avgScore.toFixed(2), icon: Cloud },
    { label: "High-Risk", value: `${highRiskCount}/${regions.length}`, icon: AlertTriangle },
    { label: "HH at Risk", value: (totalHouseholds / 1e6).toFixed(1) + "M", icon: Users },
    { label: "F1 / AUC", value: "0.82 / 0.87", icon: Sparkles },
  ];

  return (
    <div className="flex items-center gap-1 bg-card/90 backdrop-blur-sm border border-border/50 rounded-lg px-2 py-1.5 shadow-lg">
      {stats.map((s, i) => (
        <div key={s.label} className="flex items-center gap-1.5 px-2.5 py-1">
          <s.icon className="h-3.5 w-3.5 text-primary shrink-0" />
          <div>
            <div className="text-[9px] text-muted-foreground uppercase tracking-wider leading-none">{s.label}</div>
            <div className="text-sm font-bold text-foreground leading-tight">{s.value}</div>
          </div>
          {i < stats.length - 1 && <div className="w-px h-6 bg-border/50 ml-2" />}
        </div>
      ))}
    </div>
  );
}
