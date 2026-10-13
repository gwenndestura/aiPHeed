import { X } from "lucide-react";

const TERMS: Array<{ term: string; def: string }> = [
  { term: "Risk Level", def: "A composite score from 0 to 1 forecasting the likelihood of food insecurity in a province or municipality. Higher values indicate greater risk. Formerly referred to as RFII (Regional Food Insecurity Index)." },
  { term: "SHAP", def: "SHapley Additive exPlanations. A method that explains how each feature contributed to the model's prediction. Positive values increase risk; negative values are protective." },
  { term: "Engel Coefficient", def: "The proportion of household income spent on food. Higher values indicate lower income and greater food vulnerability." },
  { term: "FPSI Price Stress", def: "Food Price Stress Index. Measures pressure from rising food retail prices on household food access." },
  { term: "Fish Kill", def: "Mass mortality of fish in inland or coastal waters due to pollution, algal blooms, or oxygen depletion. Disrupts local protein supply and livelihoods, directly elevating food insecurity risk in affected communities." },
  { term: "Dependency Rate", def: "The ratio of non-working household members to working members. Higher rates increase economic vulnerability." },
  { term: "Income Decile", def: "Household income ranking from lowest (1) to highest (10). Lower deciles face greater food insecurity risk." },
  { term: "Baseline (φ₀)", def: "The average Risk Level across all areas before feature contributions are applied." },
  { term: "Impact", def: "The total change from baseline caused by all feature contributions combined." },
  { term: "QoQ Change", def: "Quarter-over-Quarter Change. The percentage shift in the Risk Level score compared to the previous quarter. Positive values indicate worsening conditions." },
  { term: "Forecast Quarter", def: "A future quarter for which the model has generated a risk prediction based on current signals." },
  { term: "IPC/CH Phase", def: "Integrated Food Security Phase Classification. International standard for measuring acute food insecurity severity." },
];

export function GlossaryPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <div className="absolute inset-0 z-[1200] animate-fade-in">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <aside
        className="absolute top-0 right-0 h-full w-full border-l border-border/40 shadow-2xl animate-slide-in-right overflow-y-auto"
        style={{
          background: "hsl(var(--card) / 0.92)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
        }}
      >
        <div className="sticky top-0 flex items-center justify-between px-4 py-3 border-b border-border/40 bg-card/80 backdrop-blur-sm">
          <h3 className="text-sm font-bold tracking-tight">Glossary</h3>
          <button onClick={onClose} className="p-1 rounded-md hover:bg-secondary/60" aria-label="Close glossary">
            <X className="h-4 w-4" />
          </button>
        </div>
        <ul className="px-4 py-3 space-y-3">
          {TERMS.map((t) => (
            <li key={t.term}>
              <p className="text-[11px] font-bold text-primary">{t.term}</p>
              <p className="text-[11px] text-muted-foreground leading-relaxed mt-0.5">{t.def}</p>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
