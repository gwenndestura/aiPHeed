import { X } from "lucide-react";

// Plain words, in the order a visitor meets them on the dashboard. Each term is the label the dashboard shows.
const TERMS: Array<{ term: string; def: string }> = [
  { term: "Chance of high food insecurity", def: "A score from 0 to 1. For a province it is the forecast chance that half or more of its households will not have enough food (moderately or severely food insecure, FNRI survey measure). It is a forecast, not a measured provincial rate. For a town or city it is a priority ranking (the province's chance weighted by poverty and population), not its own forecast." },
  { term: "High risk / Low risk", def: "0.50 and above is High risk; below 0.50 is Low risk." },
  { term: "Active alert", def: "A stronger warning, shown when the chance is 0.60 or higher." },
  { term: "Forecast quarter", def: "The three-month period being forecast (Q1 = January to March, and so on). The dashboard forecasts the next three quarters, using only data published before the forecast was made." },
  { term: "Change from last quarter", def: "How much the chance moved compared with the previous quarter's forecast, in points (0.076 to 0.064 is −1.2 pts). Up means more risk, down means less. The line below it shows both values." },
  { term: "Why is this at risk?", def: "What pushed the forecast up or down, as shares that add to 100%. The model's output is split into the contribution of each input (SHAP, a method that splits one model prediction into its inputs). The shares show what the forecast relied on, not the percentage of food insecurity caused by each factor. They explain the forecast's change from the province's latest survey level, which the bars do not include." },
  { term: "Food prices", def: "How much food and rice prices rose compared with a year earlier, by province (PSA consumer price index). Higher prices make it harder for families to buy enough food." },
  { term: "Weather and farm supply", def: "Typhoons passing nearby, El Niño or La Niña, rainfall, soil moisture and the rice and corn harvest. Bad weather and poor harvests can cut food supply and income." },
  { term: "Jobs (national figures)", def: "The national unemployment rate and its change from a year earlier (PSA Labor Force Survey). The same figure for every province." },
  { term: "Money sent home by OFWs (national figures)", def: "The yearly change in money sent home by Filipinos working abroad (BSP). The same figure for every province." },
  { term: "Fish production", def: "The province's total fish production (commercial, municipal and aquaculture) compared with the year before (PSA). Lower production means less fish to eat and less income for fishing families." },
  { term: "Other factors", def: "Inputs outside the five groups: how poor and how crowded the province is, and how far ahead the forecast looks." },
  { term: "News reports used", def: "The news stories the forecast read: those published in the three months before the forecast was made, about the province, CALABARZON, Luzon or the whole country. Off-topic stories are removed. News feeds into the five groups above; it is not a separate bar." },
  { term: "LIMITED_SIGNAL", def: "Fewer than 5 news stories were about the province itself, so its forecast rests on less local news. It does not mean the risk is low." },
  { term: "Latest data used", def: "The newest month or period of each source the forecast used. Only complete months are used: in November, the newest data is October." },
  { term: "Updated monthly", def: "On the 10th of each month the system downloads the newest public figures and news and updates the forecast if anything new came out." },
  { term: "Towns and cities", def: "Towns and cities ranked by priority within their province, using the province's chance, poverty and population. They are not separate forecasts." },
  { term: "No data", def: "A quarter shown in gray has no forecast. It does not mean the risk is low." },
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
