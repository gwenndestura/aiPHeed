import { useEffect, useMemo, useState } from "react";
import { TopNavbar } from "@/components/TopNavbar";
import { evidenceText, fmt, goalText, periodsConsistent, statusText, type V2Data } from "@/lib/e24v2";

const CRIT: Record<string, string> = {
  C1_accuracy_gt_75: "C1 Accuracy > 75%", C2_beats_strongest: "C2 Beats the strongest baseline (p < 0.05)",
  C3_not_HIGH_dominance: "C3 Not explained by predicting HIGH", C4_defensible_across_folds: "C4 Holds across quarters",
  C5_info_beyond_persistence: "C5 Information beyond persistence", C6_reliability_rule: "C6 Reliability rule",
  C9_generalizes_unseen: "C9 Generalizes to unseen quarters",
};
const HYP: Record<string, string> = {
  HB1: "Label-history model has a better Brier score than calibrated persistence",
  HB2: "Label-history model is more accurate than persistence",
  HB3: "Price nowcast model has a better Brier score than calibrated persistence",
  HB4: "Price nowcast model is more accurate than persistence",
};
const SIGNAL_CLS: Record<string, string> = { STRONG: "font-semibold", MODERATE: "", UNCERTAIN: "text-muted-foreground" };

export function ForecastV2View({ d }: { d: V2Data }) {
  const [prov, setProv] = useState("all");
  const live = d.live, rep = d.replay;
  const k1 = rep.forecast?.leads["1"];
  const rows = useMemo(() => (rep.forecast?.lgu_ranking ?? []).filter((r) => prov === "all" || r.province === prov),
    [rep, prov]);
  const pdfLive = `/aiPHeed_forecast_report_${live.period.target_quarter}_v2.pdf`;
  const pdfRep = `/aiPHeed_forecast_report_${rep.period.target_quarter}_replay.pdf`;
  const sub = d.provincial_validity["Subsistence Incidence"];
  const pov = d.provincial_validity["Poverty Incidence"];
  return (
    <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      <section aria-label="current cycle" className="rounded border p-4 space-y-1">
        <h1 className="text-2xl font-semibold" data-testid="target">{live.labels.target}</h1>
        <p data-testid="news">{live.labels.news}</p>
        <p className="text-sm">{live.labels.cutoff}{live.cutoff_reached ? "" : " — not yet reached"}</p>
        <p className={`font-medium ${live.status === "READY" ? "text-green-700" : "text-amber-700"}`} data-testid="status">
          {statusText(live)} ({live.status})</p>
        {!periodsConsistent(live) && <p className="text-red-700" data-testid="mismatch">Period mismatch detected.</p>}
        {live.forecast === null && (<>
          <h2 className="font-semibold pt-2">Why there is no forecast</h2>
          <ul className="list-disc pl-5 text-sm" data-testid="missing">{live.missing.map((m) => <li key={m}>{m}</li>)}</ul>
          {live.context_missing.length > 0 && <p className="text-xs">{live.context_missing.join("; ")}</p>}
        </>)}
        <p className="text-xs text-muted-foreground">{live.labels.caveat}</p>
        <a className="text-sm underline" href={pdfLive} download>Download the PDF report ({live.period.target_quarter})</a>
      </section>

      <section aria-label="how to read" className="rounded border p-4 text-sm space-y-1">
        <h2 className="font-semibold">How to read this page</h2>
        <p><b>Measured</b> values are official PSA or SWS figures as published. <b>Model</b> values are aiPHeed
          estimates; they are not official food-insecurity classifications.</p>
        <p>The risk forecast estimates whether the approved composite label (regional SWS hunger + 2 × provincial
          relative food inflation) will be above its threshold. Regional hunger is one value shared by all five provinces;
          only the price term differs between provinces.</p>
        <p>Signal: STRONG (probability ≤ 0.20 or ≥ 0.80), MODERATE, UNCERTAIN (0.35–0.65). Evidence tells you whether
          that lead has been validated on quarters the model never saw.</p>
      </section>

      {k1 && (
        <section aria-label="replay forecast" className="rounded border p-4 space-y-2">
          <h2 className="font-semibold" data-testid="replay-title">Worked example — {rep.labels.target} ({rep.mode})</h2>
          <p className="text-sm text-amber-700" data-testid="replay-mode">{rep.labels.mode}</p>
          <p className="text-sm">{statusText(rep)}. Threshold {fmt(rep.forecast!.threshold, 2)}. Regional hunger component
            (model: filtered SWS level) {fmt(k1.H.mu_H, 1)}; latest SWS round used: {k1.H.last_round_quarter}
            ({k1.H.gap_quarters} quarters before the target).</p>
          <table className="text-xs w-full"><thead><tr className="text-left">
            <th>Province</th><th>P(HIGH)</th><th>Signal</th><th>S1 80% interval</th><th>Regional H</th><th>Provincial 2D</th>
            <th>Risk evidence</th><th>Price pressure P(above mean)</th><th>Signal</th><th>Price evidence</th></tr></thead>
            <tbody data-testid="province-rows">{Object.entries(k1.provinces).map(([c, v]) => (
              <tr key={c}><td>{v.province}</td><td>{fmt(v.risk.p_high, 2)}</td>
                <td className={SIGNAL_CLS[v.risk.signal]}>{v.risk.signal}</td>
                <td>{fmt(v.risk.S1_80pct_interval[0], 1)} to {fmt(v.risk.S1_80pct_interval[1], 1)}</td>
                <td>{fmt(v.risk.components.regional_hunger_H.contribution, 1)}</td>
                <td>{fmt(v.risk.components.provincial_price_pressure_2D.contribution, 1)}</td>
                <td data-testid="risk-evidence">{evidenceText(v.risk.evidence)}</td>
                <td>{fmt(v.price_pressure.p_above_regional_mean, 2)}</td>
                <td className={SIGNAL_CLS[v.price_pressure.signal]}>{v.price_pressure.signal}</td>
                <td>{evidenceText(v.price_pressure.evidence)}</td></tr>))}</tbody></table>
          <a className="text-sm underline" href={pdfRep} download>Download the replay PDF ({rep.period.target_quarter})</a>
        </section>)}

      <section aria-label="evidence" className="rounded border p-4 space-y-2">
        <h2 className="font-semibold">Is the forecast reliable? Evidence</h2>
        <p className="text-sm">{d.goal.target}: {d.goal.n_test_quarters} development quarters, HIGH {d.goal.HIGH} / LOW {d.goal.LOW}.
          PCF accuracy {fmt(d.goal.metrics.FINAL_V2_PCF.accuracy)}, persistence {fmt(d.goal.metrics.B1_naive_persistence.accuracy)},
          always-HIGH {fmt(d.goal.always_HIGH_accuracy)}.</p>
        <ul className="text-sm" data-testid="criteria">{Object.entries(d.goal.criteria).map(([k, v]) => (
          <li key={k}>{CRIT[k] ?? k}: <b>{v === true ? "met" : v === false ? "not met" : String(v)}</b></li>))}</ul>
        <p className="text-sm font-semibold" data-testid="goal">{goalText(d)}</p>
        <h3 className="font-medium text-sm pt-2">Provincial price pressure: test on {d.backcast_quarters} unseen quarters (1997–2020)</h3>
        <table className="text-xs"><thead><tr className="text-left"><th>Pre-registered hypothesis</th><th>Effect</th>
          <th>Holm p</th><th>Both halves</th><th>Supported</th></tr></thead>
          <tbody data-testid="confirmatory">{Object.entries(d.confirmatory).map(([h, c]) => (
            <tr key={h}><td>{h}: {HYP[h] ?? h}</td><td>{fmt(c.effect)}</td><td>{c.p_holm < 1e-4 ? "< 0.0001" : fmt(c.p_holm, 4)}</td>
              <td>{c.stable_both_halves ? "yes" : "no"}</td><td>{c.supported ? "yes" : "no"}</td></tr>))}</tbody></table>
        <p className="text-sm">Reliable lead for provincial price pressure: up to
          {" "}{d.backcast_lead_time.B1_naive_persistence.furthest_reliable_lead} quarters (E23 rule);
          {" "}{d.backcast_lead_time.B1p_calibrated_persistence.furthest_reliable_lead} under the stricter rule.
          Accuracy on those quarters: {fmt(d.backcast_lead1.M4_pcf_D_now.accuracy)} (persistence
          {" "}{fmt(d.backcast_lead1.B1_naive_persistence.accuracy)}).</p>
        <p className="text-xs">{d.evidence._rule}</p>
      </section>

      <section aria-label="prospective seals" className="rounded border p-4 space-y-1">
        <h2 className="font-semibold">Blind prospective forecasts (sealed before outcomes)</h2>
        <ul className="text-sm" data-testid="seals">{d.seals.map((s) => (
          <li key={s.seal_id}>{s.seal_id}: origin {s.origin}; targets {s.targets.join(", ")}; SHA-256
            {" "}<code>{s.sha256.slice(0, 16)}…</code>; <b>{s.status}</b></li>))}</ul>
        <p className="text-xs">These are the first genuinely unseen test of the approved composite forecast. They are scored
          only after the outcome files are authorized.</p>
      </section>

      <section aria-label="provincial food poverty" className="rounded border p-4 space-y-1">
        <h2 className="font-semibold">Measured provincial food poverty (PSA, with 95% confidence intervals)</h2>
        <table className="text-xs"><thead><tr className="text-left"><th>Province</th><th>Year</th>
          <th>Subsistence incidence % (CI)</th><th>Poverty incidence % (CI)</th></tr></thead>
          <tbody data-testid="psa-rows">{sub.map((r) => {
            const p = pov.find((x) => x.province === r.province && x.year === r.year);
            return (<tr key={`${r.province}-${r.year}`}><td>{r.province}</td><td>{r.year}</td>
              <td>{fmt(r.value, 1)} ({fmt(r.ci_low, 1)}–{fmt(r.ci_high, 1)})</td>
              <td>{p ? `${fmt(p.value, 1)} (${fmt(p.ci_low, 1)}–${fmt(p.ci_high, 1)})` : "—"}</td></tr>);
          })}</tbody></table>
        <p className="text-xs">Measured, not modelled. Provincial differences in subsistence incidence overlap within their
          confidence intervals in 2023; the composite forecast does not measure provincial food poverty.</p>
      </section>

      <section aria-label="rankings" className="rounded border p-4 space-y-2">
        <h2 className="font-semibold">City and municipality rankings (worked example, {rep.period.target_quarter})</h2>
        <p className="text-xs">{d.caveats[2]} {d.caveats[3]}</p>
        <label className="text-sm">Province <select aria-label="province" className="border bg-background" value={prov}
          onChange={(e) => setProv(e.target.value)}><option value="all">All 142</option>
          {["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>
        <div className="max-h-96 overflow-auto"><table className="text-xs w-full"><thead><tr className="text-left">
          <th>Rank</th><th>LGU</th><th>Province</th><th>Risk index</th><th>Poverty value used</th><th>Basis</th></tr></thead>
          <tbody data-testid="ranking-rows">{rows.map((r) => <tr key={r.lgu_code}><td>{r.rank_region}</td><td>{r.lgu_name}</td>
            <td>{r.province}</td><td>{r.risk_index === null ? "unavailable" : fmt(r.risk_index, 4)}</td>
            <td>{fmt(r.poverty_value_used, 1)}</td><td>{r.poverty_value_kind}</td></tr>)}</tbody></table></div>
      </section>
      <section aria-label="caveats" className="text-xs text-muted-foreground"><ul className="list-disc pl-5">
        {d.caveats.map((c) => <li key={c}>{c}</li>)}</ul></section>
    </main>);
}

export default function ForecastV2Page() {
  const [d, setD] = useState<V2Data | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    fetch("/e24v2_dashboard.json").then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setD).catch((e) => setErr(String(e)));
  }, []);
  if (err) return <div className="p-6 text-red-700">Forecast record unavailable: {err}</div>;
  if (!d) return <div className="p-6">Loading forecast record…</div>;
  return <div className="min-h-screen bg-background text-foreground"><TopNavbar /><ForecastV2View d={d} /></div>;
}
