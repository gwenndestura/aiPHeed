import { X } from "lucide-react";

// Plain words, in the order a visitor meets them on the dashboard. Each term is the label the dashboard shows.
const TERMS: Array<{ term: string; def: string }> = [
  { term: "Food insecurity risk", def: "The forecast share of a province's households that will be moderately or severely food insecure (FNRI Household Food Insecurity Access Scale, HFIAS), shown as a percentage. 25% means about one household in four. On the CALABARZON card it is the average of the five provinces. It is a forecast, not a measured provincial rate." },
  { term: "High risk / Low risk", def: "A food insecurity risk of 50% or more (half or more of households food insecure) is High risk; below 50% is Low risk." },
  { term: "Active alert", def: "A stronger warning, shown when the food insecurity risk is 60% or more." },
  { term: "Forecast quarter", def: "The three-month period being forecast (Q1 = January to March, and so on). Each quarter the dashboard forecasts only as many quarters ahead as the model passed in testing (now two), using only data published before the forecast was made." },
  { term: "Change from last quarter", def: "How much the food insecurity risk moved compared with the previous quarter's forecast, in percentage points (26.8% to 26.6% is −0.2 points). Up means more risk, down means less. The line below it shows both values." },
  { term: "Why is this at risk?", def: "What pushed the forecast up or down, as shares that add to 100%, biggest first. The model's output is split into the contribution of each input (SHAP, a method that splits one model prediction into its inputs). The shares show what the forecast relied on, not the percentage of food insecurity caused by each factor. They explain the forecast's change from the province's latest survey level, which the bars do not include. Each card says whether the factor raised or lowered the risk, and whether slightly, moderately or greatly; \"No effect this time\" means it hardly changed this forecast." },
  { term: "Market / Prices", def: "Food and rice price inflation (PSA consumer price index), local wholesale rice, farmgate palay and fish prices and farmers' terms of trade (PSA price surveys), and news about food prices. Higher prices make it harder for families to buy enough food." },
  { term: "Climate Stress", def: "Rainfall and soil moisture compared with normal (NASA POWER), typhoons that passed near the province in the past year (NOAA IBTrACS), and news about weather and disasters. The card also notes El Niño or La Niña (NOAA Oceanic Niño Index) as context; it is not a model input, so a strong El Niño may make the actual risk higher than forecast." },
  { term: "Agricultural Production", def: "The province's rice (palay) and corn output compared with a year earlier and with its 3-year average, and output per person (PSA crop production). Smaller harvests mean less local food and farm income." },
  { term: "Employment", def: "The national unemployment rate (PSA Labor Force Survey), regional household spending growth (PSA regional accounts), and news about jobs and income." },
  { term: "Regional Economy", def: "CALABARZON's economic growth and its output compared with the national level (PSA regional accounts, GRDP), the same for all five provinces. Shown only when the forecast used it." },
  { term: "Poverty and Vulnerability", def: "Official poverty and subsistence incidence and the poverty gap (PSA official poverty statistics), population density (PSA census), and news about poverty and hardship. It is always listed with its true contribution; 0% means this forecast did not use it. The card still gives the latest poverty and density figures, which are also used to rank towns and cities." },
  { term: "Hunger & Food Stress", def: "The latest hunger survey signal (Social Weather Stations) and news about hunger, food shortages and food stress in the province, Luzon and the whole country." },
  { term: "Other factors", def: "The time since the province's last FNRI survey: the longer the gap, the more the forecast relies on how food insecurity usually changes over time. Shown as \"Time since the last survey\" in the full list and on the Visualization page." },
  { term: "News reports used", def: "The news stories the forecast read: those published in the three months before the forecast was made, about the province, CALABARZON, Luzon or the whole country, checked by DA. Off-topic stories are removed. News feeds into the groups above; it is not a separate bar. Every forecast quarter shown uses the same stories. When a province had no story of its own in that window, its province news counts as 'no change from usual' (see LIMITED_SIGNAL)." },
  { term: "LIMITED_SIGNAL", def: "Fewer than 5 news stories were about the province itself, so its forecast rests on less local news. It does not mean the risk is low." },
  { term: "Latest data used", def: "The newest month or period of each source the forecast used, listed under \"About this forecast\". Only complete months are used: in November, the newest data is October." },
  { term: "Updated quarterly", def: "A new forecast is made automatically each quarter, on the first day of its second month (1 February, 1 May, 1 August, 1 November), from the data published before that day. The data sources are checked daily. Earlier forecasts are kept in the forecast history, never replaced." },
  { term: "Forecast history", def: "Every forecast made so far, with its forecast share, its chance of reaching High risk and its class. When a new FNRI survey is published, the actual result is added next to the forecast so they can be compared." },
  { term: "Towns and cities", def: "Towns and cities ranked by priority within their province: the province's food insecurity risk weighted by poverty (60%) and population density (40%), each as a percentile of the 142 towns and cities. They are not separate forecasts." },
  { term: "Priority within the province / Rank", def: "A town's priority score and its rank among the towns and cities of its province (1 = highest priority). Towns with the same score share a rank (tied)." },
  { term: "Report (PDF)", def: "The Download PDF button on the Visualization page makes a printable report with the same numbers and explanations as the dashboard, the forecast period, the towns and cities ranking, how well the model did on past surveys, and its limitations." },
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
