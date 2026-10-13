import { regionsData } from "@/data/mockData";
import { useMemo } from "react";

export function AnimatedStatWidgets() {
  const severeCount = useMemo(
    () => regionsData.filter((r) => r.riskLevel === "severe" || r.riskLevel === "high").length,
    []
  );

  return (
    <div className="flex flex-col items-center">
      <div className="stat-circle-container">
        <svg className="stat-circle-ring" viewBox="0 0 100 100">
          {/* Subtle bg track */}
          <circle cx="50" cy="50" r="42" fill="none" stroke="hsl(var(--muted))" strokeWidth="2" opacity="0.15" />
          {/* Arc 1 - main spin */}
          <circle
            cx="50" cy="50" r="42"
            fill="none"
            stroke="hsl(var(--risk-low))"
            strokeWidth="3"
            strokeDasharray="90 174"
            strokeLinecap="round"
            className="stat-circle-spin"
          />
          {/* Arc 2 - secondary */}
          <circle
            cx="50" cy="50" r="42"
            fill="none"
            stroke="hsl(var(--risk-low) / 0.3)"
            strokeWidth="2"
            strokeDasharray="40 224"
            strokeLinecap="round"
            className="stat-circle-spin-reverse"
          />
          {/* Arc 3 - accent */}
          <circle
            cx="50" cy="50" r="36"
            fill="none"
            stroke="hsl(var(--risk-low) / 0.15)"
            strokeWidth="1.5"
            strokeDasharray="60 166"
            strokeLinecap="round"
            className="stat-circle-spin"
            style={{ animationDuration: '7s' }}
          />
        </svg>
        <div className="stat-circle-content">
          <span className="text-3xl font-extrabold tracking-tight">{severeCount}</span>
        </div>
      </div>
      <p className="text-[9px] text-center text-muted-foreground/70 leading-tight mt-2 max-w-[110px]">
        CALABARZON provinces with high levels of food insecurity
      </p>
    </div>
  );
}
