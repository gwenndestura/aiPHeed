// src/components/ProvinceRanking.tsx
// -----------------------------------
// Province ranking, read from /api/v1/ranking.
//
// Everything shown comes straight from the served model: the risk probability,
// its order, the gap to the next province down, and the SHAP contributions
// (Equation 7) that separate a province from the next one. Provinces with the
// same probability are shown as tied rather than ordered arbitrarily.

import { useState } from "react";
import { ChevronDown, Info } from "lucide-react";
import type { RegionData } from "@/data/types";
import { RISK_COLORS } from "@/data/types";
import { useRanking } from "@/lib/queries";
import type { RankingRow } from "@/lib/apiTypes";

const pts = (v: number) => `${v >= 0 ? "+" : ""}${Math.round(v * 100)} pts`;

function Row({ row, onClick, expanded, onToggle }: {
  row: RankingRow; onClick: () => void; expanded: boolean; onToggle: () => void;
}) {
  const color = RISK_COLORS[row.riskLevel as keyof typeof RISK_COLORS] ?? "#888";
  return (
    <div className="px-1 py-1.5 rounded-md hover:bg-secondary/40 transition-colors">
      <button onClick={onClick} className="w-full text-left">
        <div className="flex items-center justify-between text-[10px] mb-1 gap-2">
          <span className="font-semibold flex items-center gap-1.5 min-w-0">
            <span className="font-mono-num text-muted-foreground w-3">{row.rank}</span>
            <span className="truncate">{row.name}</span>
          </span>
          <span className="flex items-center gap-2 shrink-0">
            {row.qoqChange != null && (
              <span className={`text-[9px] ${row.qoqChange > 0 ? "text-destructive" : row.qoqChange < 0 ? "text-risk-low" : "text-muted-foreground"}`}>
                {pts(row.qoqChange)} QoQ
              </span>
            )}
            <span className="font-mono-num font-bold tabular-nums" style={{ color }}>
              {Math.round(row.riskScore * 100)}%
            </span>
          </span>
        </div>
        <div className="relative h-2 bg-secondary/40 rounded-full" aria-hidden>
          <div className="h-full rounded-full" style={{ width: `${row.riskScore * 100}%`, backgroundColor: color }} />
          <div className="absolute top-0 h-full w-px bg-foreground/30" style={{ left: "50%" }} title="0.50 HIGH/LOW line" />
        </div>
      </button>
      {row.nextLowerId && (
        row.tiedWithNextLower ? (
          <p className="mt-1 text-[9px] text-muted-foreground">Same probability as the next province: tied.</p>
        ) : (
          <button
            onClick={onToggle}
            className="mt-1 text-[9px] text-primary flex items-center gap-1 hover:underline"
            aria-expanded={expanded}
          >
            <ChevronDown className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`} />
            Why {row.gapToNextLower != null ? pts(row.gapToNextLower) : ""} above the next province
          </button>
        )
      )}
      {expanded && (
        <ul className="mt-1 ml-4 space-y-0.5">
          {row.whyAboveNextLower.map((d) => (
            <li key={d.feature} className="text-[9px] text-muted-foreground flex justify-between gap-2">
              <span className="truncate">{d.label}</span>
              <span className={`font-mono-num ${d.difference >= 0 ? "text-destructive" : "text-risk-low"}`}>
                {pts(d.difference)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ProvinceRankingCardBody({
  quarterId, regionsData, onRegionClick,
}: {
  quarterId: string; regionsData: RegionData[]; onRegionClick: (r: RegionData) => void;
}) {
  const { data, isLoading, isError } = useRanking(quarterId || undefined);
  const [open, setOpen] = useState<string | null>(null);
  const [showMethod, setShowMethod] = useState(false);

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <div className="w-1 h-4 rounded-full bg-primary" />
        <h3 className="text-[11px] font-bold uppercase tracking-wider">Province Ranking</h3>
        <button
          onClick={() => setShowMethod((v) => !v)}
          className="ml-auto text-muted-foreground hover:text-foreground"
          aria-label="How the ranking is made"
        >
          <Info className="h-3.5 w-3.5" />
        </button>
      </div>
      {showMethod && data && (
        <p className="text-[9px] text-muted-foreground leading-snug mb-2 border-l-2 border-primary/40 pl-2">
          {data.method}
        </p>
      )}
      {isLoading && <p className="text-[10px] text-muted-foreground">Loading ranking…</p>}
      {isError && <p className="text-[10px] text-muted-foreground">Ranking is unavailable for this quarter.</p>}
      {data && (
        <div className="space-y-1">
          {data.data.map((row) => (
            <Row
              key={row.id}
              row={row}
              expanded={open === row.id}
              onToggle={() => setOpen((v) => (v === row.id ? null : row.id))}
              onClick={() => {
                const r = regionsData.find((x) => x.id === row.id);
                if (r) onRegionClick(r);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
