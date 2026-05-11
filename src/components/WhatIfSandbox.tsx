import { useState, useCallback } from "react";
import { RegionData } from "@/data/types";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Slider } from "@/components/ui/slider";

interface Props {
  region: RegionData;
}

export function WhatIfSandbox({ region }: Props) {
  const [features, setFeatures] = useState(region.whatIfFeatures.map((f) => ({ ...f })));

  const baseScore = region.riskScore;
  const simulated = baseScore + features.reduce((acc, f, i) => {
    const original = region.whatIfFeatures[i];
    const diff = (f.value - original.value) / (original.max - original.min);
    return acc + diff * 0.08;
  }, 0);
  const delta = simulated - baseScore;

  const handleReset = useCallback(() => {
    setFeatures(region.whatIfFeatures.map((f) => ({ ...f })));
  }, [region]);

  return (
    <div className="bg-card/90 backdrop-blur-md border border-border/50 rounded-xl p-4 shadow-2xl">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-primary" />
          <h3 className="text-[11px] font-bold uppercase tracking-wider">What-If Sandbox</h3>
        </div>
        <button onClick={handleReset} className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors">
          <RotateCcw className="h-3 w-3" /> Reset
        </button>
      </div>
      <p className="text-[10px] text-muted-foreground/70 mb-4">
        Adjust features to simulate RFII changes for {region.name}
      </p>

      {/* Score cards */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <ScoreCard label="Base" value={baseScore.toFixed(2)} color="text-primary" />
        <ScoreCard label="Simulated" value={simulated.toFixed(2)} color="text-primary" />
        <ScoreCard label="Delta" value={delta >= 0 ? `+${delta.toFixed(3)}` : delta.toFixed(3)} color={delta > 0 ? "text-destructive" : delta < 0 ? "text-risk-low" : "text-foreground"} />
      </div>

      {/* Sliders */}
      <div className="space-y-3.5">
        {features.map((f, i) => (
          <div key={f.feature}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-muted-foreground">{f.feature}</span>
              <span className="text-[10px] font-mono font-bold tabular-nums">{f.value}{f.unit}</span>
            </div>
            <div className="relative">
              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "linear-gradient(90deg, hsl(var(--risk-low)), hsl(var(--risk-severe)))" }} />
              <Slider
                value={[f.value]}
                min={f.min}
                max={f.max}
                step={f.step}
                onValueChange={([v]) => {
                  const next = [...features];
                  next[i] = { ...next[i], value: v };
                  setFeatures(next);
                }}
                className="absolute inset-0 [&_[role=slider]]:h-3 [&_[role=slider]]:w-3"
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScoreCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-secondary/40 rounded-lg p-2.5 text-center border border-border/30">
      <div className="text-[8px] text-muted-foreground uppercase tracking-widest font-semibold">{label}</div>
      <div className={`text-lg font-extrabold mt-0.5 tabular-nums ${color}`}>{value}</div>
    </div>
  );
}
