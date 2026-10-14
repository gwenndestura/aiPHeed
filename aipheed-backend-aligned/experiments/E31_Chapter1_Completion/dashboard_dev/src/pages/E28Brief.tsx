/**
 * E28 DA brief, read from the single E28 record.
 *  - Each province brief states target, scope, origin, lead, estimate with interval, signal, drivers (the forecast's
 *    own additive decomposition), data coverage, evidence sufficiency, validation status, limitations and a
 *    proportionate suggested use. No HIGH/LOW category unless the lead is VALIDATED; neutral styling otherwise.
 *  - The operational quarter shows its missing inputs and no estimate.
 *  - The 142-LGU ranking is shown as a relative position, never a band, with the substitute poverty values marked.
 */
import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import { E28Record, PROVINCE_ORDER, ProvinceBrief, estimateWording, loadE28Record } from "@/lib/e28Record";

function BriefCard({ b, testId }: { b: ProvinceBrief; testId: string }) {
  const w = estimateWording(b);
  return (
    <div data-testid={testId} data-evidence={b.evidence_status}
         className="border-2 border-slate-400 bg-white rounded p-2 text-[12px] space-y-1">
      <div className="font-semibold" data-testid={`${testId}-estimate`}>{b.province}: {w.text}</div>
      {b.estimate?.S1_80pct_interval && (
        <div>S1 80% interval {b.estimate.S1_80pct_interval[0]} to {b.estimate.S1_80pct_interval[1]} · threshold {b.estimate.tau}</div>
      )}
      {b.signal && <div>Signal: {b.signal.toLowerCase()}</div>}
      <div className="italic">{b.target_quarter} · lead {b.lead_quarters} · information to {String(b.information_cutoff).slice(0, 10)}</div>
      <div className="text-slate-700 font-semibold">
        {b.evidence_status === "VALIDATED" ? "VALIDATED forecast" : "EXPERIMENTAL — not validated"}
      </div>
      {b.category_withheld_reason && <div className="text-[11px]">{b.category_withheld_reason}</div>}
      {b.drivers.length > 0 && (
        <ul className="list-disc ml-4" data-testid={`${testId}-drivers`}>
          {b.drivers.map((d) => (
            <li key={d.factor}>{d.factor}: {d.direction} ({d.contribution > 0 ? "+" : ""}{d.contribution.toFixed(2)}) — {d.explanation}</li>
          ))}
        </ul>
      )}
      {b.missing_inputs.length > 0 && (
        <div data-testid={`${testId}-missing`}>
          <div className="font-semibold">Missing inputs (no estimate; this is not a low-risk state):</div>
          <ul className="list-disc ml-4">{b.missing_inputs.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
      )}
      <div>Data: {Object.entries(b.data_coverage).filter(([k]) => ["hunger", "prices", "news"].includes(k)).map(([, v]) => String(v)).join(" · ")}</div>
      <div>Evidence: {b.evidence_sufficiency}</div>
      <div className="font-semibold" data-testid={`${testId}-use`}>Suggested use ({b.attention.replace(/_/g, " ").toLowerCase()}): {b.suggested_use}</div>
    </div>
  );
}

export function E28BriefView({ rec }: { rec: E28Record }) {
  const fq = rec.forecast_quarter;
  const oq = rec.operational_quarter;
  const ev = rec.evaluation["T1_A"]?.rows ?? [];
  return (
    <div className="p-4 space-y-4 max-w-6xl mx-auto">
      <h1 className="text-xl font-bold">{rec.title}</h1>
      <div data-testid="status-banner" className="border-2 border-slate-600 bg-slate-50 p-2 text-sm">{rec.status_banner}</div>
      <div className="text-[11px]">Record SHA-256: <span data-testid="record-hash">{rec.content_sha256}</span> ·{" "}
        <a className="underline" href={`${API_BASE_URL}/api/v1/quarterly/e28/brief.pdf`}>PDF</a></div>

      <section>
        <h2 className="font-semibold">{fq.quarter}: {fq.kind}</h2>
        <div className="grid md:grid-cols-2 gap-2">
          {PROVINCE_ORDER.filter((c) => fq.provinces[c]).map((c) => (
            <BriefCard key={c} b={fq.provinces[c]} testId={`brief-${c}`} />
          ))}
        </div>
      </section>

      <section data-testid="operational">
        <h2 className="font-semibold">{oq.quarter}: {oq.status}</h2>
        <BriefCard b={oq.provinces[PROVINCE_ORDER[0]]} testId="brief-operational" />
      </section>

      <section>
        <h2 className="font-semibold">Reliability and baselines (development evidence)</h2>
        <table className="text-[11px]" data-testid="eval-table">
          <thead><tr><th>Arm</th><th>Lead-1 accuracy</th><th>Lead-1 Brier</th><th>Lead-1 AUC</th><th>Furthest reliable lead</th></tr></thead>
          <tbody>
            {ev.map((r) => (
              <tr key={r.arm}><td>{r.arm}</td><td>{r.lead1_accuracy.toFixed(3)}</td><td>{r.lead1_brier.toFixed(3)}</td>
                <td>{r.lead1_auc == null ? "not estimable" : `${r.lead1_auc.toFixed(3)}${r.lead1_auc_flag === "OK" ? "" : ` (${r.lead1_auc_flag.toLowerCase()})`}`}</td>
                <td>{String(r.furthest_reliable_horizon)}</td></tr>
            ))}
          </tbody>
        </table>
        <ul className="list-disc ml-4 text-[11px]">
          {rec.target_validity.what_it_cannot_support.map((x) => <li key={x}>Cannot support: {x}</li>)}
        </ul>
      </section>

      <section data-testid="news-coverage">
        <h2 className="font-semibold">News coverage {rec.news_coverage.quarters[0]}–{rec.news_coverage.quarters[1]}</h2>
        <div className="text-[11px]">{Object.entries(rec.news_coverage.coverage_status_counts).map(([k, v]) => `${k}: ${v}`).join(" · ")}</div>
        <div className="text-[11px] italic">{rec.news_coverage.note}</div>
      </section>

      <section data-testid="lgu-ranking">
        <h2 className="font-semibold">City and municipal ranking ({rec.lgu_ranking.rows.length} LGUs) — relative position, EXPERIMENTAL</h2>
        <p className="text-[11px]">{rec.lgu_ranking.meaning}</p>
        <ul className="list-disc ml-4 text-[11px]">{rec.lgu_ranking.does_not_mean.map((x) => <li key={x}>{x}</li>)}</ul>
        <table className="text-[11px]">
          <thead><tr><th>Rank</th><th>LGU</th><th>Province</th><th>Index</th><th>Rank in province</th><th>Poverty used</th></tr></thead>
          <tbody>
            {rec.lgu_ranking.rows.map((r) => (
              <tr key={r.lgu_code} data-testid="lgu-row" data-kind={r.poverty_lgu_estimate == null ? "substitute" : "sae"}>
                <td>{r.rank_region ?? "—"}{r.tied ? " (tie)" : ""}</td><td>{r.lgu_name}</td><td>{r.province}</td>
                <td>{r.risk_index == null ? "no estimate" : r.risk_index.toFixed(4)}</td><td>{r.rank_in_province ?? "—"}</td>
                <td>{r.poverty_value_used}{r.poverty_lgu_estimate == null ? " (province substitute)" : " (PSA SAE)"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <p className="text-[11px]">{rec.disclaimer}</p>
    </div>
  );
}

export default function E28Brief() {
  const [rec, setRec] = useState<E28Record | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    loadE28Record().then(setRec).catch((e) => setErr(String(e)));
  }, []);
  if (err) return <div className="p-4">Could not load the DA brief: {err}</div>;
  if (!rec) return <div className="p-4">Loading…</div>;
  return <E28BriefView rec={rec} />;
}
