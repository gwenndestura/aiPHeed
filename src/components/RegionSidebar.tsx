import { RegionData, RISK_COLORS, RISK_LABELS } from "@/data/types";
import { X, MapPin, TrendingUp, BarChart3 } from "lucide-react";

interface Props {
  region: RegionData | null;
  previewRegion: RegionData | null;
  onClose: () => void;
}

export function RegionSidebar({ region, previewRegion, onClose }: Props) {
  const data = region || previewRegion;

  if (!data) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-sm p-6 text-center">
        <div>
          <MapPin className="h-8 w-8 mx-auto mb-3 opacity-40" />
          <p className="font-medium mb-1">No region selected</p>
          <p className="text-xs">Click any region to explore food insecurity data</p>
        </div>
      </div>
    );
  }

  const isLocked = !!region;
  const riskColor = RISK_COLORS[data.riskLevel];
  const momPositive = data.momChange > 0;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <MapPin className="h-5 w-5 text-primary mt-0.5 shrink-0" />
          <div>
            <h2 className="text-base font-bold leading-tight">{data.name}</h2>
            <p className="text-xs text-muted-foreground">Regional Food Insecurity Detail</p>
          </div>
        </div>
        {isLocked && (
          <button onClick={onClose} className="p-1 rounded hover:bg-accent transition-colors">
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        )}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-muted/50 rounded-lg px-3 py-3 border border-border">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">RFII SCORE</div>
          <div className="text-2xl font-bold mt-1">{data.riskScore.toFixed(2)}</div>
          <div className="h-1 rounded-full mt-2 bg-muted overflow-hidden">
            <div className="h-full rounded-full" style={{ width: `${data.riskScore * 100}%`, backgroundColor: riskColor }} />
          </div>
        </div>
        <div className="bg-muted/50 rounded-lg px-3 py-3 border border-border">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">FPSI</div>
          <div className="text-2xl font-bold mt-1 text-destructive">{data.fpsi}%</div>
          <div className="text-[10px] text-muted-foreground mt-1">Food Price Stress Index</div>
        </div>
        <div className="bg-muted/50 rounded-lg px-3 py-3 border border-border">
          <div className="flex items-center gap-1.5">
            <Users className="h-3 w-3 text-muted-foreground" />
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">HH AT RISK</span>
          </div>
          <div className="text-2xl font-bold mt-1">
            {data.householdsAtRisk >= 1000000
              ? (data.householdsAtRisk / 1e6).toFixed(1) + "M"
              : (data.householdsAtRisk / 1e3).toFixed(0) + "K"}
          </div>
        </div>
        <div className="bg-muted/50 rounded-lg px-3 py-3 border border-border">
          <div className="flex items-center gap-1.5">
            <TrendingUp className="h-3 w-3 text-muted-foreground" />
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">MOM CHANGE</span>
          </div>
          <div className={`text-2xl font-bold mt-1 ${momPositive ? "text-destructive" : "text-risk-low"}`}>
            {momPositive ? "+" : ""}{data.momChange}%
          </div>
        </div>
      </div>

      {/* Population */}
      <div className="bg-muted/50 rounded-lg px-3 py-2 border border-border flex items-center justify-between">
        <div>
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">POPULATION</div>
          <div className="text-sm font-bold mt-0.5">{data.population.toLocaleString()}</div>
        </div>
        <BarChart3 className="h-4 w-4 text-muted-foreground" />
      </div>

      {/* AI Narrative */}
      <div className="bg-card rounded-lg border p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-sm">🤖</span>
            <h3 className="text-xs font-bold">AI Narrative</h3>
          </div>
          <span className="text-primary text-sm">💡</span>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          {data.name} is classified as {data.riskLevel === "high" || data.riskLevel === "severe" ? "Elevated" : "Moderate"} (RFII: {data.riskScore.toFixed(2)}), primarily driven by Engel Coefficient, FPSI (Price Stress), Dependency Ratio. Protective factors include Income Decile and Income Sources, which partially offset risk.
        </p>
      </div>

      {/* SHAP Waterfall */}
      <div className="bg-card rounded-lg border p-3">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm">⚙️</span>
          <h3 className="text-xs font-bold">
            SHAP Waterfall — <span className="text-primary">{data.name}</span>
          </h3>
        </div>
        <p className="text-[10px] text-muted-foreground mb-3">
          Cumulative feature contributions from base score (0.30) → predicted RFII ({data.riskScore.toFixed(2)})
        </p>
        <div className="space-y-2">
          {data.shapValues.map((sv) => (
            <div key={sv.feature} className="flex items-center gap-2">
              <span className="text-[10px] text-muted-foreground w-20 text-right shrink-0 truncate">{sv.feature}</span>
              <div className="flex-1 h-4 relative">
                <div
                  className="absolute h-full rounded-sm"
                  style={{
                    backgroundColor: sv.value > 0 ? RISK_COLORS.severe : RISK_COLORS.low,
                    width: `${Math.min(Math.abs(sv.value) * 400, 100)}%`,
                    left: sv.value > 0 ? "0" : undefined,
                    right: sv.value < 0 ? "0" : undefined,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between mt-3 text-[10px]">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-destructive" /> Increases risk
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: RISK_COLORS.low }} /> Decreases risk
            </span>
          </div>
          <span className="text-muted-foreground font-mono">Final: <strong className="text-foreground">{data.riskScore.toFixed(3)}</strong></span>
        </div>
      </div>

      {/* Model Performance */}
      <div className="bg-card rounded-lg border p-3">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm">⚡</span>
          <h3 className="text-xs font-bold">Model Performance</h3>
        </div>
        <p className="text-[10px] text-muted-foreground mb-3">LightGBM + SMOTE + Optuna (100 trials, 5-fold CV)</p>
        <div className="space-y-3">
          <MetricBar label="Weighted F1" value={0.82} target={0.75} color="hsl(45, 93%, 47%)" />
          <MetricBar label="ROC-AUC" value={0.87} target={0.80} color="hsl(200, 80%, 50%)" />
          <MetricBar label="SUS Score" value={78} target={70} color="hsl(142, 71%, 40%)" max={100} />
        </div>
        <div className="flex items-center gap-2 mt-3 text-[10px] text-muted-foreground">
          <span>🔬</span>
          <span>Benchmarked against Logistic Regression, CatBoost, and Random Forest</span>
        </div>
      </div>
    </div>
  );
}

function MetricBar({ label, value, target, color, max = 1 }: { label: string; value: number; target: number; color: string; max?: number }) {
  const pct = (value / max) * 100;
  const targetPct = (target / max) * 100;
  const displayValue = max === 1 ? value.toFixed(2) : String(value);
  const displayTarget = max === 1 ? target.toFixed(2) : String(target);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-muted-foreground flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
          {label}
        </span>
        <span className="text-xs font-bold">
          {displayValue} <span className="text-muted-foreground font-normal">/ {displayTarget}</span>
        </span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden relative">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

function Users(props: React.SVGProps<SVGSVGElement> & { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}
