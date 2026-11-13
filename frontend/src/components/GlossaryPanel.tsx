import { X } from "lucide-react";

// Plain words, in the order a visitor meets them on the dashboard. Each term is the label the dashboard shows.
const TERMS: Array<{ term: string; def: string }> = [
  { term: "Food insecurity risk", def: "A score from 0 to 1: the forecast share of a province's households that will be moderately or severely food insecure (FNRI Household Food Insecurity Access Scale, HFIAS). 0.25 means about one household in four. On the CALABARZON card it is the average of the five provinces. It is a forecast, not a measured provincial rate." },
  { term: "Range", def: "The span the forecast is expected to fall within 9 times out of 10 (90% range), for example 0.14 to 0.38. A wider range means a less certain forecast." },
  { term: "Chance of reaching HIGH", def: "The forecast chance, from 0 to 1, that the share of food-insecure households reaches 0.50 or more, shown to three decimals. A small chance means the forecast level is well below 0.50, not that there is no food insecurity." },
  { term: "Low confidence", def: "The province's last FNRI provincial survey is older than any survey gap the model was tested on, so its forecast rests on an old starting level. The forecast is still shown; treat it with more caution." },
  { term: "High risk / Low risk", def: "A food insecurity risk of 0.50 and above (half or more of households food insecure) is High risk; below 0.50 is Low risk." },
  { term: "Active alert", def: "A stronger warning, shown when the food insecurity risk is 0.60 or higher." },
  { term: "Forecast quarter", def: "The three-month period being forecast (Q1 = January to March, and so on). Each quarter the dashboard forecasts only as many quarters ahead as the model passed in testing (now two), using only data published before the forecast was made." },
  { term: "Change from last quarter", def: "How much the food insecurity risk moved compared with the previous quarter's forecast, in points (0.27 to 0.26 is −1 pt). Up means more risk, down means less. The line below it shows both values." },
  { term: "Why is this at risk?", def: "What pushed the forecast up or down, as shares that add to 100%. The model's output is split into the contribution of each input (SHAP, a method that splits one model prediction into its inputs). The shares show what the forecast relied on, not the percentage of food insecurity caused by each factor. They explain the forecast's change from the province's latest survey level, which the bars do not include." },
  { term: "Food prices", def: "How much food and rice prices rose compared with a year earlier, by province (PSA consumer price index). Higher prices make it harder for families to buy enough food." },
  { term: "Weather and farm supply", def: "Typhoons passing nearby, El Niño or La Niña, rainfall, soil moisture and farm output. Bad weather and poor harvests can cut food supply and income." },
  { term: "Local rice and palay prices", def: "Wholesale rice and farmgate palay prices in the province compared with a year before, and the province's rice price level compared with other provinces (PSA). Higher local rice prices make food harder to afford." },
  { term: "Dry spells and typhoons", def: "Months with less than half the usual rain in the past six months and strong typhoons that passed near the province in the past year (NASA POWER, NOAA IBTrACS)." },
  { term: "Rice and corn harvests", def: "The province's rice (palay) and corn output in the latest four published quarters compared with the four before (PSA). Smaller harvests mean less local food and farm income." },
  { term: "Regional economy (regional figures)", def: "Output per person in CALABARZON (regional GRDP at constant 2018 prices, PSA), the same for all five provinces. A year's figure is used from the third quarter of the next year, when PSA has published it." },
  { term: "Jobs (national figures)", def: "The national unemployment rate and its change from a year earlier (PSA Labor Force Survey). The same figure for every province." },
  { term: "Other factors", def: "Inputs outside the groups above: how poor and how crowded the province is, and how far ahead the forecast looks." },
  { term: "News reports used", def: "The news stories the forecast read: those published in the three months before the forecast was made, about the province, CALABARZON, Luzon or the whole country. Off-topic stories are removed. News feeds into the groups above; it is not a separate bar. Every forecast quarter shown uses the same stories. When a province had no story of its own in that window, its province news counts as 'no change from usual' (see LIMITED_SIGNAL)." },
  { term: "LIMITED_SIGNAL", def: "Fewer than 5 news stories were about the province itself, so its forecast rests on less local news. It does not mean the risk is low." },
  { term: "Latest data used", def: "The newest month or period of each source the forecast used. Only complete months are used: in November, the newest data is October." },
  { term: "Updated quarterly", def: "A new forecast is made automatically each quarter, on the first day of its second month (1 February, 1 May, 1 August, 1 November), from the data published before that day. The data sources are checked daily. Earlier forecasts are kept in the forecast history, never replaced." },
  { term: "Towns and cities", def: "Towns and cities ranked by priority within their province: the province's food insecurity risk weighted by poverty (60%) and population density (40%), each as a percentile of the 142 towns and cities. They are not separate forecasts." },
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
