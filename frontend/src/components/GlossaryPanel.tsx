import { X } from "lucide-react";

const TERMS: Array<{ term: string; def: string }> = [
  { term: "Risk Level", def: "A score from 0 to 1. For a province it is the forecast probability of the Chapter I food-insecurity risk class (regional SWS hunger above 11.3% together with unusually fast provincial food-price rises), not a measured provincial hunger rate. For a city or municipality it is a priority ranking derived from the province's value with poverty and population density, not a measured or forecast municipal rate. Higher values indicate greater risk. Formerly referred to as RFII (Regional Food Insecurity Index)." },
  { term: "High / Low risk", def: "The band a Risk Level falls in. It is judged on the score as shown, rounded to two decimals: 0.50 and above is High, below 0.50 is Low. A score of 0.4982 reads 0.50, so it is High." },
  { term: "Active alert", def: "A stricter flag for anticipatory action, raised when the risk probability is at or above 0.60. Every active alert is High risk, but not every High risk area has an active alert." },
  { term: "Observed quarter", def: "A quarter PSA has already published data for, scored from that quarter's own data (a nowcast). The newest one is marked as the current quarter. Shown with a solid line on the timeline." },
  { term: "Forecast Quarter", def: "A quarter beyond the newest published PSA data. Its risk is forecast from information published before the quarter began. Shown with a dashed line on the timeline." },
  { term: "No data", def: "A quarter on the timeline with no forecast, shown in gray. Either the model has no input data for it, or PSA has not published its data yet and the forecast does not reach it. Select the quarter to see which." },
  { term: "Limited data", def: "Fewer than 5 news articles about the province were found for the quarter, so its score rests on less evidence. The tag carries over to every municipality in that province." },
  { term: "Quarter-on-quarter change", def: "The percentage shift in the risk probability compared to the previous quarter. Positive values indicate worsening conditions." },
  { term: "SHAP", def: "SHapley Additive exPlanations. A method that splits one model prediction into the contributions of its inputs. The dashboard sums these into five driver groups and shows each group's share of the model's push, rescaled to 100%. A driver either pushes the estimate up or pulls it down. The shares describe what the model relied on, not the percentage of food insecurity caused by each factor; in the Chapter I forecast they explain the food-price part, and each driver's note gives the regional hunger condition that is not among them." },
  { term: "Market / Prices", def: "Food retail prices, including rice, and how fast they are rising. Higher prices make it harder for households to afford enough food." },
  { term: "Climate Stress", def: "Typhoons, heavy rain, flooding and other weather that damage farms and disrupt food supply." },
  { term: "Fish Kill", def: "Mass mortality of fish in inland or coastal waters due to pollution, algal blooms, or oxygen depletion. Disrupts local protein supply and livelihoods, directly elevating food insecurity risk in affected communities." },
  { term: "Employment", def: "How many people have jobs. Rising unemployment leaves households with less income for food." },
  { term: "OFW Remittance", def: "Money sent home by relatives working abroad (Overseas Filipino Workers). A drop leaves families with less to spend on food." },
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
