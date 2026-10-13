import { useEffect, useMemo, useState } from "react";
import { TopNavbar } from "@/components/TopNavbar";
import { eligibleArticles, fmt, periodsConsistent, PROVINCES, statusText, type E23Data } from "@/lib/e23";

const ORDER = ["PROPOSED_lgbm_combined", "B1_naive_persistence", "B2_lr_combined", "B3_lr_gov_only",
  "B4_lr_nlp_only", "B5_lgbm_gov_only", "B6_lgbm_nlp_only", "S_lr_psa_only"];

export default function ForecastPeriodPage() {
  const [d, setD] = useState<E23Data | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [lead, setLead] = useState(1);
  const [mode, setMode] = useState<"origin" | "fixed">("origin");
  const [prov, setProv] = useState<string>("all");

  useEffect(() => {
    fetch("/e23_dashboard.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setD).catch((e) => setErr(String(e)));
  }, []);

  const rows = useMemo(() => (d ? d.rankings.rows.filter((r) => prov === "all" || r.province_code === prov) : []), [d, prov]);
  if (err) return <div className="p-6 text-red-700">Forecast record unavailable: {err}</div>;
  if (!d) return <div className="p-6">Loading forecast record…</div>;
  const ok = periodsConsistent(d);
  const ev = d.evaluation[mode].find((r) => r.lead === lead);
  const arts = eligibleArticles(d);
  const pdf = `/aiPHeed_forecast_report_${d.period.target_quarter}.pdf`;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopNavbar />
      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        <section aria-label="forecast period" className="rounded border p-4 space-y-1">
          <h1 className="text-2xl font-semibold" data-testid="target">{d.labels.target}</h1>
          <p data-testid="news">{d.labels.news}</p>
          <p className="text-sm">{d.labels.cutoff}{d.cutoff_reached ? "" : " — not yet reached"}</p>
          <p className={`font-medium ${d.status === "READY" ? "text-green-700" : "text-amber-700"}`} data-testid="status">
            {statusText(d)} ({d.status})
          </p>
          {!ok && <p className="text-red-700">Period mismatch detected between the record and its labels.</p>}
          <p className="text-xs text-muted-foreground">{d.labels.caveat}</p>
          <a className="text-sm underline" href={pdf} download>Download the PDF report ({d.period.target_quarter})</a>
        </section>

        {d.forecast === null && (
          <section aria-label="missing inputs" className="rounded border p-4">
            <h2 className="font-semibold mb-2">Why there is no forecast</h2>
            <ul className="list-disc pl-5 text-sm">{d.missing.map((m) => <li key={m}>{m}</li>)}</ul>
          </section>
        )}

        <section aria-label="supporting news" className="rounded border p-4 space-y-2">
          <h2 className="font-semibold">Supporting news — {d.period.news_display}
            {!d.supporting_news.quarter_complete && " (incomplete quarter)"}</h2>
          <p className="text-sm">Eligible articles published {d.period.news_window_start.slice(0, 10)} to {d.period.news_window_end.slice(0, 10)} (PHT): <b>{arts.length}</b>. Articles published after the cutoff are never used.</p>
          <table className="text-sm"><tbody>
            {Object.entries(PROVINCES).map(([c, n]) => (
              <tr key={c}><td className="pr-4">{n}</td><td className="pr-4">{d.supporting_news.by_province[c] ?? 0}</td>
                <td>{d.supporting_news.limited_signal[c] ? "LIMITED_SIGNAL" : "OK"}</td></tr>))}
          </tbody></table>
        </section>

        <section aria-label="evaluation" className="rounded border p-4 space-y-2">
          <h2 className="font-semibold">Back-test evaluation (development origins, not an untouched holdout)</h2>
          <div className="flex gap-4 text-sm">
            <label>Lead time <select className="border bg-background" value={lead} onChange={(e) => setLead(Number(e.target.value))}>
              {d.evaluation.origin.map((r) => <option key={r.lead} value={r.lead}>{r.lead}</option>)}</select></label>
            <label>Target <select className="border bg-background" value={mode} onChange={(e) => setMode(e.target.value as "origin" | "fixed")}>
              <option value="origin">Primary: training-window median</option>
              <option value="fixed">Sensitivity: fixed 14.6</option></select></label>
          </div>
          {!ev || !ev.n_origins ? <p className="text-sm">No origin had enough training data at this lead.</p> : (
            <>
              <p className="text-sm">{ev.n_origins} origins · test rows HIGH {ev.HIGH} / LOW {ev.LOW} · {ev.evaluable ? "evaluable" : "NOT evaluable (needs ≥ 8 origins and ≥ 5 HIGH and ≥ 5 LOW)"} · reliable: {ev.reliable ? "yes" : "no"}</p>
              <table className="text-xs w-full"><thead><tr className="text-left">
                <th>Model</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th><th>Brier</th><th>TP/FP/FN/TN</th></tr></thead>
                <tbody>{ORDER.map((m) => { const x = ev.models![m]; return (
                  <tr key={m}><td>{x.name}</td><td>{fmt(x.accuracy)}</td><td>{fmt(x.precision)}</td><td>{fmt(x.recall)}</td>
                    <td>{fmt(x.F1)}</td><td>{fmt(x.ROC_AUC)}</td><td>{fmt(x.Brier)}</td><td>{x.TP}/{x.FP}/{x.FN}/{x.TN}</td></tr>); })}
                </tbody></table>
              {ev.improved && <p className="text-sm">E23-B improved model: accuracy {fmt(ev.improved.accuracy)} (always-HIGH {fmt(ev.improved.always_HIGH_accuracy)}); strongest baseline {ev.improved.strongest_baseline} {fmt(ev.improved.strongest_baseline_accuracy)}; beats it: {ev.improved.beats_strongest ? "yes" : "no"}.</p>}
            </>)}
          <p className="text-sm">Maximum reliable lead time: <b>{d.max_reliable_lead ?? "none"}</b></p>
        </section>

        <section aria-label="hypotheses" className="rounded border p-4">
          <h2 className="font-semibold mb-2">Null hypotheses (primary decisions)</h2>
          <ul className="text-sm list-disc pl-5">{Object.entries(d.hypotheses).map(([h, v]) =>
            <li key={h}><b>{h}</b>: {v.decision}{v.why ? ` — ${v.why}` : ""}</li>)}</ul>
        </section>

        <section aria-label="rankings" className="rounded border p-4 space-y-2">
          <h2 className="font-semibold">City and municipality rankings</h2>
          <p className="text-sm text-amber-700">{d.rankings.for_target_quarter}. The table shows a back-test example: {d.rankings.quarter}.</p>
          <p className="text-xs">{d.caveats[2]}</p>
          <label className="text-sm">Province <select className="border bg-background" value={prov} onChange={(e) => setProv(e.target.value)}>
            <option value="all">All 142</option>{Object.entries(PROVINCES).map(([c, n]) => <option key={c} value={c}>{n}</option>)}</select></label>
          <div className="max-h-96 overflow-auto"><table className="text-xs w-full"><thead><tr className="text-left">
            <th>Rank</th><th>LGU</th><th>Province</th><th>Risk index</th><th>Vulnerability</th><th>Poverty source</th></tr></thead>
            <tbody>{rows.map((r) => <tr key={r.lgu_code}><td>{r.rank_region}</td><td>{r.lgu_name}</td><td>{r.province}</td>
              <td>{Number(r.risk_index).toFixed(4)}</td><td>{Number(r.vulnerability_index).toFixed(3)}</td>
              <td>{r.poverty_is_province_fallback === "True" ? "province mean" : "LGU estimate"}</td></tr>)}</tbody></table></div>
        </section>

        <section aria-label="face validity" className="rounded border p-4 text-sm">
          <h2 className="font-semibold mb-1">Face-validity anchor (DOST-FNRI 2023 NNS)</h2>
          <p>CALABARZON moderate-to-severe household food insecurity {d.face_validity.calabarzon_2023_moderate_severe_pct}% (95% CI {d.face_validity.calabarzon_2023_ci95.join("–")}); national {d.face_validity.national_2023_moderate_severe_pct}%. {d.face_validity.use}</p>
          <p className="text-xs text-muted-foreground">2019: {d.face_validity.nns_2019_calabarzon}</p>
        </section>
      </main>
    </div>
  );
}
