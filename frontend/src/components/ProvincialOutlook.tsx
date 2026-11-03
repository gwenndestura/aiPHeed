import { useProvincialOutlook } from "@/lib/queries";

/**
 * FI10 provincial outlook card: one row per province, exactly as returned by GET /api/v1/fi10/provinces.
 * Keeps three things apart: the measured provincial food-price pressure outlook (direct, provisional), the province's
 * poverty and priority (context), and the regional hunger outlook (shared reference, not provincial).
 */
export function ProvincialOutlookCardBody() {
  const { data, error, isLoading } = useProvincialOutlook();

  if (isLoading) return <p className="text-[10px] text-muted-foreground py-2">Loading provincial outlook…</p>;
  if (error || !data) {
    return (
      <div className="space-y-1" data-testid="fi10-unavailable">
        <h3 className="text-[13px] font-semibold leading-tight">Provincial food-price outlook</h3>
        <p className="text-[10px] text-muted-foreground">Unavailable: not issued for the current quarter yet.</p>
      </div>
    );
  }

  const tq = data.provinces[0]?.lead1.target_quarter;
  return (
    <div className="space-y-2" data-testid="fi10-outlook">
      <div className="flex items-center gap-2">
        <h3 className="text-[13px] font-semibold leading-tight">Provincial food-price outlook</h3>
        <span className="ml-auto px-1.5 py-0.5 rounded-md bg-muted text-muted-foreground text-[9px] font-bold uppercase tracking-wider">
          provisional
        </span>
      </div>
      <p className="text-[9px] text-muted-foreground leading-snug">
        For {tq}: will each province's food inflation be unusually high? This is measured for each province (PSA food CPI). It is a
        driver of food access, not a measure of food insecurity.
      </p>

      <table className="w-full text-[10px]" data-testid="fi10-table">
        <thead>
          <tr className="text-muted-foreground text-left">
            <th className="font-normal">Province</th>
            <th className="font-normal">Outlook</th>
            <th className="font-normal text-right">Chance</th>
            <th className="font-normal text-right">Food infl.</th>
            <th className="font-normal text-right">Poverty</th>
          </tr>
        </thead>
        <tbody>
          {data.provinces.map((p) => {
            const high = p.lead1.class === "HIGH";
            return (
              <tr key={p.province} data-testid={`fi10-row-${p.province}`}>
                <td>{p.province}</td>
                <td>
                  <span className={`px-1 rounded font-bold font-mono-num ${high ? "bg-risk-high/15 text-risk-high" : "bg-risk-low/15 text-risk-low"}`}>
                    {p.lead1.class}
                  </span>
                </td>
                <td className="text-right font-mono-num">{Math.round(p.lead1.p_high * 100)}%</td>
                <td className="text-right font-mono-num" title={`Latest ${p.lead1.latest_food_inflation_pct}% (${p.lead1.latest_cpi_month}); unusually high above ${p.lead1.province_high_line_pct}%`}>
                  {p.lead1.projected_food_inflation_pct}%
                </td>
                <td className="text-right font-mono-num">{p.poverty_incidence_pct}%</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="text-[9px] text-muted-foreground leading-snug">
        HIGH is shown when the chance reaches {Math.round((data.provinces[0]?.lead1.decision_threshold ?? 0) * 100)}% (set in training to
        balance missed and false alerts). Food infl. = projected food inflation for {tq}.
      </p>

      <details className="text-[9px] text-muted-foreground leading-snug">
        <summary className="cursor-pointer">Track record, two quarters ahead, poverty view and regional hunger</summary>
        <div className="space-y-1 pt-1">
          <ul className="space-y-0.5" data-testid="fi10-track">
            {data.provinces.map((p) => (
              <li key={p.province}>
                <span className="font-semibold">{p.province}:</span> caught {p.lead1.track_record.high_caught} of{" "}
                {p.lead1.track_record.n_high} high-inflation quarters, {p.lead1.track_record.false_high} false alerts in{" "}
                {p.lead1.track_record.n_low} ({p.lead1.track_record.period}; balanced accuracy {p.lead1.track_record.balanced_accuracy}).
                Two quarters ahead ({p.lead2.target_quarter}): {p.lead2.class} ({Math.round(p.lead2.p_high * 100)}%). Priority rank{" "}
                {p.priority_rank}. Food-access pressure view: {p.food_access_pressure_view}.
                {p.lead1.drivers.length > 0 && <> Main drivers: {p.lead1.drivers.map((d) => d.group).join(", ")}.</>}
              </li>
            ))}
          </ul>
          <p>{data.lead_status["1"]}. Three and four quarters ahead: {data.lead_status["3"]}.</p>
          <p>{data.food_access_pressure_note}</p>
          <p>
            Regional reference ({data.regional_hunger_reference.area}): hunger outlook {data.regional_hunger_reference.class} for{" "}
            {data.regional_hunger_reference.target_quarter}. This is not a provincial result.
          </p>
        </div>
      </details>
    </div>
  );
}
