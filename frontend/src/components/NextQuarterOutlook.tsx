import { useNextQuarterOutlook, useProvincialMeasurements } from "@/lib/queries";
import { isLoadFailure } from "@/lib/loadError";

/**
 * FI9 Lead-1 outlook card: the next calendar quarter's food-insecurity outlook for Balance Luzon, exactly as
 * returned by GET /api/v1/fi9/outlook (no value is recomputed here). It sits beside, and does not replace, the
 * existing province map. A stale or unavailable forecast (503) is shown as unavailable, never as current.
 * The details keep four things apart: the regional outlook, historical provincial measurements (FNRI 2015),
 * the LGU priority on the map, and food-price indicators.
 */
// The project's five trigger groups (News and NLP is listed from news_context, not from the domain indicators).
const TRIGGER_GROUPS: [string, string[]][] = [
  ["Market and prices", ["market"]],
  ["Climate stress", ["climate"]],
  ["Employment and remittances", ["employment", "remittance"]],
  ["Poverty and social vulnerability", ["poverty"]],
];

export function NextQuarterOutlookCardBody() {
  const { data, isLoading, error } = useNextQuarterOutlook();
  const { data: prov } = useProvincialMeasurements(!!data);

  if (isLoading) {
    return <p className="text-[10px] text-muted-foreground py-2">Loading next-quarter outlook…</p>;
  }
  if (error || !data) {
    return (
      <div className="space-y-1" data-testid="fi9-outlook-unavailable">
        <h3 className="text-[13px] font-semibold leading-tight">Next-quarter outlook</h3>
        <p className="text-[10px] text-muted-foreground leading-snug">
          {isLoadFailure(error)
            ? "The outlook could not be loaded."
            : "Unavailable: no forecast has been issued for the current quarter yet."}
        </p>
      </div>
    );
  }

  const f = data.forecast;
  const high = f.class === "HIGH";
  const modSev = (prov?.fnri_2015_hfias ?? []).filter((r) => r.geography !== "CALABARZON");
  const byProv = new Map<string, number>();
  modSev.forEach((r) => {
    if (r.category === "moderately_food_insecure" || r.category === "severely_food_insecure") {
      byProv.set(r.geography, (byProv.get(r.geography) ?? 0) + r.percent);
    }
  });
  return (
    <div className="space-y-2" data-testid="fi9-outlook">
      <div className="flex items-center gap-2">
        <h3 className="text-[13px] font-semibold leading-tight">Next-quarter outlook</h3>
        <span className="ml-auto px-1.5 py-0.5 rounded-md bg-muted text-muted-foreground text-[9px] font-bold uppercase tracking-wider">
          {data.status}
        </span>
      </div>
      <p className="text-[9px] text-muted-foreground leading-snug">
        Regional outlook for Balance Luzon (Luzon outside Metro Manila; CALABARZON is about a third of it), not a CALABARZON figure.
      </p>

      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px]">
        <span className="text-muted-foreground">Current quarter</span>
        <span className="font-mono-num text-right" data-testid="fi9-current">{data.current_quarter}</span>
        <span className="text-muted-foreground">Forecast for</span>
        <span className="font-mono-num text-right font-bold" data-testid="fi9-target">{data.target_quarter}</span>
        <span className="text-muted-foreground">Horizon</span>
        <span className="text-right">{data.horizon}</span>
        <span className="text-muted-foreground">Issued</span>
        <span className="font-mono-num text-right">{data.issue_date}</span>
        <span className="text-muted-foreground">Data up to</span>
        <span className="font-mono-num text-right">SWS {data.latest_observation_quarter}</span>
      </div>

      <div className="flex items-center gap-2">
        <span
          data-testid="fi9-class"
          className={`px-1.5 py-0.5 rounded-md font-bold font-mono-num text-[11px] ${high ? "bg-risk-high/15 text-risk-high" : "bg-risk-low/15 text-risk-low"}`}
        >
          {f.class}
        </span>
        <span className="text-[10px] text-muted-foreground leading-snug">
          {f.p_high !== null ? (
            <>
              About <span className="font-mono-num text-foreground" data-testid="fi9-p">{Math.round(f.p_high * 100)}%</span> chance
              that hunger will be significantly above normal (approximate)
            </>
          ) : (
            "Probability not calibrated; class only"
          )}
        </span>
      </div>

      {data.p_low !== undefined && f.p_high !== null && (
        <p className="text-[10px] text-muted-foreground leading-snug" data-testid="fi9-p-low">
          Chance of LOW (not significantly above normal): <span className="font-mono-num text-foreground">{Math.round(data.p_low * 100)}%</span>
        </p>
      )}

      {data.class_performance && (
        <p className="text-[10px] leading-snug" data-testid="fi9-track-record">
          <span className="font-semibold">Track record:</span>{" "}
          <span className="text-muted-foreground">
            caught {data.class_performance.high_caught} of {data.class_performance.n_high} HIGH quarters (
            {Math.round(data.class_performance.high_recall * 100)}%), {data.class_performance.false_high} false alarms in{" "}
            {data.class_performance.n_low} LOW quarters (LOW correctly identified {Math.round(data.class_performance.low_recall * 100)}%);
            balanced accuracy {data.class_performance.balanced_accuracy.toFixed(2)}. It misses too many HIGH quarters to meet the
            project's requirement.
          </span>
        </p>
      )}

      <p className="text-[10px] leading-snug">
        Projected hunger <span className="font-mono-num font-semibold" data-testid="fi9-level">{f.projected_hunger_pct}%</span>{" "}
        <span className="text-muted-foreground">
          (likely range <span data-testid="fi9-range">{f.projected_hunger_interval95_pct[0]}–{f.projected_hunger_interval95_pct[1]}%</span>;
          significance line {f.significance_line_pct}%; latest reading {data.latest_reading_pct}%)
        </span>
      </p>
      {data.baseline_comparison && (
        <p className="text-[10px] leading-snug" data-testid="fi9-baseline">
          <span className="font-semibold">Compared with simply repeating the latest reading:</span>{" "}
          <span className="text-muted-foreground">{data.baseline_comparison.statement}</span>
        </p>
      )}
      <p className="text-[10px] text-muted-foreground leading-snug">{data.explanation}</p>

      <details className="text-[9px] text-muted-foreground leading-snug">
        <summary className="cursor-pointer">Limitations, scope and data</summary>
        <div className="space-y-1 pt-1">
          <ul className="list-disc pl-3 space-y-0.5" data-testid="fi9-limitations">
            {data.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
          {data.survey_design_note && <p>{data.survey_design_note}</p>}
          <p>{f.class_rule}. {f.probability_note}</p>
          {f.interval_note && <p>{f.interval_note}</p>}
          <p>
            Model {data.model} ({data.model_version}); training data to {data.training_data_cutoff}; latest SWS release{" "}
            {data.latest_observation_published}; latest input {data.latest_data_publication_date ?? "–"}.
          </p>
          <p className="font-semibold pt-1">Food-price and other indicators (context, not inputs)</p>
          <p>{data.domain_context.note}</p>
          <ul className="space-y-0.5" data-testid="fi9-trigger-groups">
            {TRIGGER_GROUPS.map(([label, keys]) => (
              <li key={label}>
                <span className="font-semibold">{label}:</span>{" "}
                {keys
                  .flatMap((k) => data.domain_context.domains[k] ?? [])
                  .map((x) => `${x.indicator} ${x.value ?? "n/a"} ${x.unit} (${x.geographic_level})`)
                  .join("; ")}
              </li>
            ))}
            {data.news_context && (
              <li>
                <span className="font-semibold">News and NLP:</span> stress index{" "}
                {data.news_context.news_stress_index_z ?? "n/a"} (z). {data.news_context.status}
              </li>
            )}
          </ul>
          {byProv.size > 0 && (
            <>
              <p className="font-semibold pt-1">Measured by survey, by province (FNRI 2015, HFIAS; historical, not a forecast)</p>
              <ul className="space-y-0.5" data-testid="fi9-provincial-2015">
                {[...byProv.entries()].map(([p, v]) => (
                  <li key={p}>
                    {p}: {v.toFixed(1)}% of households moderately or severely food insecure
                  </li>
                ))}
              </ul>
            </>
          )}
          <p>Province and LGU colours on the map are a separate priority layer, not this forecast and not measured hunger.</p>
        </div>
      </details>
    </div>
  );
}
