import { useFoodInsecurityStatus, useForecastPeriod } from "@/lib/queries";
import { isLoadFailure } from "@/lib/loadError";

/**
 * The official food-insecurity forecast area. It reads only GET /api/v1/final/food-insecurity/outlook, which serves a
 * model the release gate has approved and otherwise answers `validation_pending` with no forecast values. Nothing here
 * falls back to a candidate, a placeholder or another model.
 */
const qLabel = (q?: string | null) => (q ? `${q.slice(5)} ${q.slice(0, 4)}` : "");
const day = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "Asia/Manila" }) : "";

/** The forecasting period from the backend (GET /api/v1/forecast-period): current quarter, issue, freshness, next issue. */
export function ForecastPeriodLines() {
  const { data: p } = useForecastPeriod();
  if (!p) return null;
  return (
    <div className="space-y-0.5 text-[10px] leading-snug text-muted-foreground" data-testid="forecast-period">
      <p>
        <span className="font-semibold text-foreground">Now: {qLabel(p.current_quarter)}</span>
        {p.served_issue_quarter && <> · forecast issued {p.served_issue_label ?? qLabel(p.served_issue_quarter)}{p.served_generated_utc ? `, made ${day(p.served_generated_utc)}` : ""}</>}
      </p>
      {p.stale && p.stale_reason && (
        <p className="text-foreground" data-testid="forecast-period-stale">{p.stale_reason}.</p>
      )}
      <p>
        {p.latest_data_update_utc ? `Data sources last updated ${day(p.latest_data_update_utc)} · ` : ""}next forecast {day(p.next_issue_date)}
      </p>
    </div>
  );
}

export function FoodInsecurityStatusCardBody() {
  const { data, error, isLoading } = useFoodInsecurityStatus();

  if (isLoading) return <p className="text-[10px] text-muted-foreground py-2">Loading forecast status…</p>;
  if (error || !data) {
    return (
      <div className="space-y-1" data-testid="fi-status-unavailable">
        <h3 className="text-[13px] font-semibold leading-tight">Food-insecurity forecast</h3>
        <p className="text-[10px] text-muted-foreground">
          {isLoadFailure(error) ? "The forecast status could not be loaded." : "Unavailable."} No forecast is shown.
        </p>
      </div>
    );
  }

  if (data.status !== "approved") {
    return (
      <div className="space-y-2" data-testid="fi-status-pending">
        <div className="flex items-center gap-2">
          <h3 className="text-[13px] font-semibold leading-tight">Food-insecurity forecast</h3>
          <span className="ml-auto px-1.5 py-0.5 rounded-md bg-muted text-muted-foreground text-[9px] font-bold uppercase tracking-wider">
            not yet approved
          </span>
        </div>
        <p className="text-[10px] leading-snug">{data.message}</p>
        <p className="text-[9px] text-muted-foreground leading-snug">
          Until a forecast is approved, no food-insecurity forecast numbers are shown here.
        </p>
        {data.candidates.length > 0 && (
          <p className="text-[9px] text-muted-foreground leading-snug" data-testid="fi-status-candidates">
            Models under evaluation:{" "}
            {data.candidates
              .map((c) => `${c.model_id} (${c.status}; ${c.failed_checks.length} of ${c.checks_total ?? data.acceptance_checks_total} checks not yet passed)`)
              .join("; ")}
            .
          </p>
        )}
      </div>
    );
  }

  // An approved model exists: say in plain words what it is and how often it was right in past tests.
  const acc = data.accuracy_by_lead?.["1"]?.accuracy;
  const approved = data.production?.approved_utc?.slice(0, 10);
  // the publication cut-off (the newest period of each source is listed below); a month name here read as "data for November"
  const through = data.data_through
    ? new Date(`${data.data_through}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })
    : null;
  return (
    <div className="space-y-2" data-testid="fi-status-approved">
      <h3 className="text-[13px] font-semibold leading-tight">About this forecast</h3>
      <p className="text-[10px] leading-snug">
        Forecast share of food-insecure households per province.
        {typeof acc === "number" && ` Right ${Math.round(acc * 100)}% of the time in past tests (2018–2021 surveys).`}
      </p>
      {through && (
        <p className="text-[10px] leading-snug text-muted-foreground" data-testid="fi-status-cutoff">
          <span className="font-semibold text-foreground">Data published up to {through}</span> · all quarters of this forecast use the same data
        </p>
      )}
      {data.data_used && data.data_used.length > 0 && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[10px] leading-snug" data-testid="fi-status-data-used">
          {data.data_used.map((d) => (
            <div key={d.name} className="contents" title={`${d.name}: ${d.period} (${d.source})`}>
              <dt className="text-muted-foreground">{d.label ?? d.name}</dt>
              <dd className="text-right font-mono-num">{d.when ?? d.period}</dd>
            </div>
          ))}
        </dl>
      )}
      {data.issue_note && (
        <p className="text-[9px] text-muted-foreground leading-snug" data-testid="fi-status-issue-note">{data.issue_note}</p>
      )}
      <ForecastPeriodLines />
      <p className="text-[9px] text-muted-foreground">
        Model {data.production?.model_id}{approved ? `, approved ${approved}` : ""}.
      </p>
    </div>
  );
}
