import { useEffect, useMemo, useState } from "react";
import { TopNavbar } from "@/components/TopNavbar";
import { eligibleArticles, fmt, goalMet, periodsConsistent, PROVINCES, statusText, type E23Data } from "@/lib/e23";

const ORDER = ["FINAL_E24F", "PROPOSED_lgbm_combined", "B1_naive_persistence", "B2_lr_combined", "B3_lr_gov_only",
  "B4_lr_nlp_only", "B5_lgbm_gov_only", "B6_lgbm_nlp_only", "MAJ_training_majority"];
const CRIT: Record<string, string> = {
  C1_accuracy_gt_75: "C1 Accuracy > 75%", C2_beats_strongest: "C2 Beats the strongest baseline (p < 0.05)",
  C3_not_HIGH_dominance: "C3 Not explained by predicting HIGH", C4_defensible_across_folds: "C4 Holds across quarters",
  C5_info_beyond_persistence: "C5 Information beyond persistence", C6_reliability_rule: "C6 Reliability rule",
  C9_generalizes_unseen: "C9 Generalizes to unseen quarters",
};

export function ForecastPeriodView({ d }: { d: E23Data }) {
  const [lead, setLead] = useState(1);
  const [target, setTarget] = useState<"T1" | "T2">("T1");
  const [prov, setProv] = useState<string>("all");
  const rows = useMemo(() => d.rankings.rows.filter((r) => prov === "all" || r.province === PROVINCES[prov]), [d, prov]);
  const ok = periodsConsistent(d);
  const ev = d.evaluation[target].find((r) => r.lead === lead);
  const arts = eligibleArticles(d);
  const pdf = `/aiPHeed_forecast_report_${d.period.target_quarter}.pdf`;
  return (
    <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      <section aria-label="forecast period" className="rounded border p-4 space-y-1">
        <h1 className="text-2xl font-semibold" data-testid="target">{d.labels.target}</h1>
        <p data-testid="news">{d.labels.news}</p>
        <p className="text-sm">{d.labels.cutoff}{d.cutoff_reached ? "" : " — not yet reached"}</p>
        <p className={`font-medium ${d.status === "READY" ? "text-green-700" : "text-amber-700"}`} data-testid="status">
          {statusText(d)} ({d.status})</p>
        {!ok && <p className="text-red-700" data-testid="mismatch">Period mismatch detected between the record and its labels.</p>}
        <p className="text-xs text-muted-foreground">{d.labels.caveat}</p>
        <a className="text-sm underline" href={pdf} download>Download the PDF report ({d.period.target_quarter})</a>
      </section>
      {d.forecast === null && (
        <section aria-label="missing inputs" className="rounded border p-4">
          <h2 className="font-semibold mb-2">Why there is no forecast</h2>
          <ul className="list-disc pl-5 text-sm">{d.missing.map((m) => <li key={m}>{m}</li>)}</ul>
        </section>)}
      <section aria-label="supporting news" className="rounded border p-4 space-y-2">
        <h2 className="font-semibold">Supporting news — {d.period.news_display}{!d.supporting_news.quarter_complete && " (incomplete quarter)"}</h2>
        <p className="text-sm">Eligible articles: <b data-testid="article-count">{arts.length}</b>. Articles published after the cutoff are never used.</p>
        <table className="text-sm"><tbody>{Object.entries(PROVINCES).map(([c, n]) => (
          <tr key={c}><td className="pr-4">{n}</td><td className="pr-4">{d.supporting_news.by_province[c] ?? 0}</td>
            <td>{d.supporting_news.limited_signal[c] ? "LIMITED_SIGNAL" : "OK"}</td></tr>))}</tbody></table>
      </section>
      <section aria-label="evaluation" className="rounded border p-4 space-y-2">
        <h2 className="font-semibold">Back-test evaluation (development quarters — not an untouched holdout)</h2>
        <div className="flex gap-4 text-sm">
          <label>Lead time <select aria-label="lead" className="border bg-background" value={lead} onChange={(e) => setLead(Number(e.target.value))}>
            {d.evaluation[target].map((r) => <option key={r.lead} value={r.lead}>{r.lead}</option>)}</select></label>
          <label>Target <select aria-label="target" className="border bg-background" value={target} onChange={(e) => setTarget(e.target.value as "T1" | "T2")}>
            <option value="T1">Approved composite label (Chapter I)</option>
            <option value="T2">Exploratory: relative food-price pressure (not food insecurity)</option></select></label>
        </div>
        {!ev ? <p className="text-sm">No origin had enough training data at this lead.</p> : (<>
          <p className="text-sm">{ev.n_origins} test quarters · HIGH {ev.HIGH} / LOW {ev.LOW} · {ev.evaluable ? "evaluable" : "NOT evaluable"} · strongest baseline: {ev.strongest_baseline}</p>
          <table className="text-xs w-full"><thead><tr className="text-left"><th>Model</th><th>Accuracy</th><th>Balanced acc.</th>
            <th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th><th>Brier</th><th>TP/FP/FN/TN</th></tr></thead>
            <tbody>{ORDER.map((m) => { const x = ev.models![m]; return (
              <tr key={m}><td>{x.name}</td><td>{fmt(x.accuracy)}</td><td>{fmt(x.balanced_accuracy ?? null)}</td><td>{fmt(x.precision)}</td>
                <td>{fmt(x.recall)}</td><td>{fmt(x.F1)}</td><td>{fmt(x.ROC_AUC)}</td><td>{fmt(x.Brier)}</td>
                <td>{x.TP}/{x.FP}/{x.FN}/{x.TN}</td></tr>); })}</tbody></table>
          <h3 className="font-medium text-sm mt-2">Forecasting goal — all criteria must hold</h3>
          <ul className="text-sm" data-testid="criteria">{Object.entries(ev.criteria ?? {}).map(([k, v]) => (
            <li key={k}>{CRIT[k] ?? k}: <b>{v === true ? "met" : v === false ? "not met" : String(v)}</b></li>))}</ul>
          <p className="text-sm font-semibold" data-testid="goal">{goalMet(ev) ? "Goal met" : "Goal NOT met"}</p>
        </>)}
      </section>
      <section aria-label="rankings" className="rounded border p-4 space-y-2">
        <h2 className="font-semibold">City and municipality rankings</h2>
        <p className="text-sm text-amber-700">{d.rankings.for_target_quarter}. Example shown: {d.rankings.quarter}.</p>
        <p className="text-xs">{d.caveats[2]}</p>
        <label className="text-sm">Province <select aria-label="province" className="border bg-background" value={prov} onChange={(e) => setProv(e.target.value)}>
          <option value="all">All 142</option>{Object.entries(PROVINCES).map(([c, n]) => <option key={c} value={c}>{n}</option>)}</select></label>
        <div className="max-h-96 overflow-auto"><table className="text-xs w-full"><thead><tr className="text-left">
          <th>Rank</th><th>LGU</th><th>Province</th><th>Risk index</th><th>Poverty value used</th><th>Kind</th></tr></thead>
          <tbody data-testid="ranking-rows">{rows.map((r) => <tr key={r.lgu_code}><td>{Number(r.rank_region)}</td><td>{r.lgu_name}</td>
            <td>{r.province}</td><td>{r.risk_index === "" ? "unavailable" : Number(r.risk_index).toFixed(4)}</td>
            <td>{Number(r.poverty_value_used).toFixed(1)}</td><td>{r.poverty_value_kind}</td></tr>)}</tbody></table></div>
      </section>
    </main>);
}

export default function ForecastPeriodPage() {
  const [d, setD] = useState<E23Data | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    fetch("/e24_dashboard.json").then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setD).catch((e) => setErr(String(e)));
  }, []);
  if (err) return <div className="p-6 text-red-700">Forecast record unavailable: {err}</div>;
  if (!d) return <div className="p-6">Loading forecast record…</div>;
  return <div className="min-h-screen bg-background text-foreground"><TopNavbar /><ForecastPeriodView d={d} /></div>;
}
