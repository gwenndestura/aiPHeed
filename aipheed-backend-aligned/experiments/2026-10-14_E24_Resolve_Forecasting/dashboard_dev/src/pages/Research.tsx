import { useEffect, useMemo, useState } from "react";
import { TopNavbar } from "@/components/TopNavbar";
import { constructedLabel, dColor, fmt, rankByD, type ResearchData } from "@/lib/research";

const ARM_NAMES: Record<string, string> = {
  P_persistence: "Naive persistence (Ch. I baseline I)",
  B2_psa_lr: "PSA-only indicator LR (Ch. I baseline II)",
  B3_nlp_sentiment_lr: "NLP-only sentiment LR (Ch. I baseline III)",
  B4_lr_all: "Logistic regression, all inputs (Ch. I baseline IV)",
  S5_lgbm_gov_only: "LightGBM government-only (SOP)",
  S6_lgbm_nlp_only: "LightGBM NLP-only (SOP)",
  M_governing_lgbm: "Current LightGBM (MODEL-B2)",
  N1_structural_rule: "N1 structural rule",
  N2_structural_shrink: "N2 structural + shrinkage",
  N3_structural_lr: "N3 structural LR",
  N4_lgbm_constrained_tuned: "N4 constrained, tuned LightGBM",
  MAJ_majority: "Training majority (reference)",
};

type Tab = "layers" | "forecast" | "evaluation";

export default function ResearchPage() {
  const [data, setData] = useState<ResearchData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("layers");
  const [qIdx, setQIdx] = useState<number>(-1);
  const [h, setH] = useState<number>(3);

  useEffect(() => {
    fetch("/e18_dashboard.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d: ResearchData) => {
        setData(d);
        setQIdx(d.history.length - 1);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const q = data && qIdx >= 0 ? data.history[qIdx] : null;
  const ranked = useMemo(() => (q ? rankByD(q.provinces) : []), [q]);

  if (error) return <div className="p-6 text-red-700">Research data unavailable: {error}</div>;
  if (!data || !q) return <div className="p-6">Loading research outputs…</div>;

  const fc = data.forecast_2027Q1;
  const sel = data.classification_selection[`h${h}|A`];
  const cls = data.classification_metrics.filter((r) => r.h === h && r.set === "A");
  const con = data.continuous_metrics.filter((r) => r.h === h);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <TopNavbar />
      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold">Research results (E18, development)</h1>
          <p className="text-sm text-muted-foreground" data-testid="status">{data.status} Source run: {data.generated_from_run}.</p>
          <ul className="text-xs text-muted-foreground list-disc pl-5" aria-label="caveats">
            {data.caveats.map((c) => <li key={c}>{c}</li>)}
          </ul>
        </header>

        <nav className="flex gap-2" aria-label="sections">
          {(["layers", "forecast", "evaluation"] as Tab[]).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded border text-sm ${tab === t ? "bg-primary text-primary-foreground" : ""}`}>
              {t === "layers" ? "Measured layers" : t === "forecast" ? "2027-Q1 research forecast" : "Evaluation & lead time"}
            </button>
          ))}
        </nav>

        {tab === "layers" && (
          <section className="space-y-4">
            <label className="text-sm">Quarter:{" "}
              <select value={qIdx} onChange={(e) => setQIdx(Number(e.target.value))} className="border rounded px-2 py-1 bg-background text-foreground">
                {data.history.map((x, i) => <option key={x.quarter} value={i}>{x.quarter}</option>)}
              </select>
            </label>
            <div className="border rounded p-4">
              <h2 className="font-medium">Regional hunger — SWS Balance Luzon (shown once; not provincial)</h2>
              <p className="text-3xl font-semibold" data-testid="hunger">
                {q.hunger_balance_luzon === null ? "No SWS round" : `${fmt(q.hunger_balance_luzon, 1)}%`}
              </p>
            </div>
            <div className="border rounded p-4 overflow-x-auto">
              <h2 className="font-medium mb-2">Provincial food inflation and relative food-price pressure</h2>
              {!q.complete_five && <p className="text-sm text-amber-700">Insufficient data: a province is missing, so D and the ranking are not shown.</p>}
              <table className="text-sm w-full">
                <thead><tr className="text-left"><th>Rank by D</th><th>Province</th><th>Food inflation F (%)</th><th>Relative pressure D (pts)</th><th>Constructed label (legacy, not validated)</th></tr></thead>
                <tbody>
                  {(ranked.length ? ranked : q.provinces.map((p) => ({ ...p, rank: NaN }))).map((p) => (
                    <tr key={p.code} className="border-t">
                      <td>{Number.isNaN(p.rank) ? "—" : p.rank}</td>
                      <td>{p.name}</td>
                      <td>{fmt(p.F)}</td>
                      <td><span className="inline-block w-3 h-3 rounded-sm mr-2 align-middle" style={{ background: dColor(p.D) }} />{fmt(p.D)}</td>
                      <td>{constructedLabel(p.S1) ?? "Insufficient data"}{p.S1 !== null ? ` (S1 ${fmt(p.S1)})` : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {tab === "forecast" && (
          <section className="space-y-4" data-testid="forecast">
            <p className="text-sm">Target 2027-Q1 · horizon {fc.horizon} quarters · information through {fc.information_cutoff}. Exploratory research outputs; uncertainty not quantified.</p>
            <div className="border rounded p-4">
              <h2 className="font-medium">{fc.H.label}</h2>
              <p className="text-2xl font-semibold">{fmt(fc.H.forecast, 1)}% <span className="text-sm font-normal">({fc.H.selected})</span></p>
            </div>
            {(["F", "D"] as const).map((k) => (
              <div key={k} className="border rounded p-4">
                <h2 className="font-medium">{fc[k].label}</h2>
                <p className="text-xs text-muted-foreground">Selected by the frozen rule: {fc[k].selected}</p>
                <ul className="text-sm">{Object.entries(fc[k].forecast as Record<string, number>).map(([code, v]) => (
                  <li key={code}>{data.history[0].provinces.find((p) => p.code === code)?.name}: {fmt(v)}</li>))}
                </ul>
              </div>
            ))}
            <div className="border rounded p-4">
              <h2 className="font-medium">{fc.constructed_label.label}</h2>
              <p className="text-sm">Rule outcome: {fc.constructed_label.selected_by_rule} (news-based models unavailable for 2026 inputs).</p>
              <ul className="text-sm">{Object.entries(fc.constructed_label.persistence_2026Q2_label as Record<string, string>).map(([code, v]) => (
                <li key={code}>{data.history[0].provinces.find((p) => p.code === code)?.name}: {v}</li>))}
              </ul>
            </div>
          </section>
        )}

        {tab === "evaluation" && (
          <section className="space-y-4" data-testid="evaluation">
            <label className="text-sm">Horizon h (quarters between latest data and target):{" "}
              <select value={h} onChange={(e) => setH(Number(e.target.value))} className="border rounded px-2 py-1 bg-background text-foreground">
                {[1, 2, 3, 4, 5].map((x) => <option key={x} value={x}>{x}{x === 3 ? " (2027-Q1)" : ""}</option>)}
              </select>
            </label>
            <div className="border rounded p-4 text-sm">
              <p><strong>Maximum supported lead time:</strong> {data.lead_time.max_supported ?? "none"} — {data.lead_time.note}</p>
              {sel && <p>At h={h}: {sel.quarters} test quarters ({sel.test_HIGH} HIGH / {sel.test_LOW} LOW); {sel.insufficient ? "insufficient evidence; " : ""}selected: {sel.selected}; supported: {sel.supported ? "yes" : "no"}.</p>}
            </div>
            <div className="border rounded p-4 overflow-x-auto">
              <h2 className="font-medium mb-2">Constructed label — model vs Chapter I baselines (set A)</h2>
              <table className="text-sm w-full">
                <thead><tr className="text-left"><th>Arm</th><th>Acc.</th><th>Bal. acc.</th><th>F1</th><th>AUC</th><th>TP/FP/FN/TN</th></tr></thead>
                <tbody>{cls.map((r) => (
                  <tr key={r.arm} className="border-t"><td>{ARM_NAMES[r.arm] ?? r.arm}</td><td>{fmt(r.accuracy, 3)}</td><td>{fmt(r.balanced_accuracy, 3)}</td><td>{fmt(r.F1_HIGH, 3)}</td><td>{fmt(r.ROC_AUC, 3)}</td><td>{r.TP}/{r.FP}/{r.FN}/{r.TN}</td></tr>))}
                </tbody>
              </table>
            </div>
            <div className="border rounded p-4 overflow-x-auto">
              <h2 className="font-medium mb-2">Continuous targets — MAE by candidate (★ = kept by frozen rule)</h2>
              <table className="text-sm w-full">
                <thead><tr className="text-left"><th>Target</th><th>Candidate</th><th>Origins</th><th>MAE</th><th>RMSE</th><th>Bias</th></tr></thead>
                <tbody>{con.map((r) => (
                  <tr key={r.target + r.candidate} className="border-t"><td>{r.target}</td><td>{r.selected ? "★ " : ""}{r.candidate}</td><td>{r.origins}</td><td>{fmt(r.MAE)}</td><td>{fmt(r.RMSE)}</td><td>{fmt(r.bias)}</td></tr>))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
