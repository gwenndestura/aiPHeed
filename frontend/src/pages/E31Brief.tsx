/**
 * E31 DA brief (/da-brief). What DA Region IV-A sees for the quarter under way and the next one, from the ONE E31
 * record: mode (nowcast / forecast) with its information cutoff and news window, the estimate with its interval and
 * exact drivers, the measured price pressure, the news evidence status, the scored 2026-Q3, model validation
 * (including the 75% question), the LGU top five and the limitations. No HIGH/LOW category is shown for an estimate
 * whose lead time is not validated.
 */
import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import { E31Record, isE36, loadE31, MODE_TEXT, pct, PROVINCE_ORDER, ProvinceEstimate, ServedRecord } from "@/lib/e31Record";
import { E36BriefView } from "@/pages/E36Brief";

function Estimate({ e, testid }: { e: ProvinceEstimate; testid: string }) {
  return (
    <div data-testid={testid}>
      <div className="text-lg font-semibold">{pct(e.p_high)} <span className="text-[11px] font-normal">({e.signal})</span></div>
      <div className="text-[11px]">S1 estimate {e.S1_forecast?.toFixed(1)}; 80% interval {e.S1_80pct_interval?.map((x) => x.toFixed(1)).join(" to ")}</div>
      <table className="text-[11px] mt-1">
        <tbody>
          {(e.drivers || []).map((d) => (
            <tr key={d.key} data-testid={`${testid}-driver-${d.key}`}>
              <td className="pr-2">{d.factor}</td>
              <td className={d.contribution >= 0 ? "text-red-700" : "text-green-700"}>
                {d.contribution >= 0 ? "+" : ""}{d.contribution.toFixed(2)}
              </td>
              <td className="pl-2 italic">{d.kind}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function E31BriefView({ rec }: { rec: E31Record }) {
  const now = rec.quarters.find((q) => q.mode === "NOWCAST")!;
  const fc = rec.quarters.find((q) => q.mode === "FORECAST")!;
  const q3 = rec.quarters.find((q) => q.mode === "RETROSPECTIVE_BLIND");
  const rh = rec.regional_hunger;
  const ho = rec.validation.news_relevance.holdout.gates["R1"];
  return (
    <div className="p-4 space-y-4 max-w-6xl mx-auto text-[12px]">
      <header>
        <h1 className="text-xl font-semibold">{rec.title}</h1>
        <div data-testid="cutoff">Information cutoff {rec.information_cutoff}. Data {rec.data_authorization}.</div>
        <div className="border border-amber-600 bg-amber-50 text-amber-950 p-2 mt-1" data-testid="disclaimer">{rec.disclaimer}</div>
      </header>

      <section className="border-2 border-slate-500 p-2" data-testid="regional-hunger">
        <h2 className="font-semibold">Official regional hunger ({rh.kind.toLowerCase()})</h2>
        <div>{rh.what}. {rh.geographic_level}.</div>
        <table className="text-[11px]"><thead><tr><th>Quarter</th><th>Round</th><th>Hunger %</th><th>Posted</th></tr></thead>
          <tbody>{rh.rounds.slice(-4).map((o) => (
            <tr key={o.round}><td>{o.quarter}</td><td>{o.round}</td><td>{o.hunger_pct}</td><td>{o.published}</td></tr>))}</tbody>
        </table>
      </section>

      <section className="grid md:grid-cols-2 gap-2" data-testid="modes">
        {[now, fc].map((q) => (
          <div key={q.mode} className="border p-2" data-testid={`mode-${q.mode}`}>
            <div className="font-semibold">{q.quarter}: {MODE_TEXT[q.mode]} (lead {q.lead})</div>
            <div>Information cutoff {q.information_cutoff}; {q.status}.</div>
            {q.provenance && (
              <div data-testid={`window-${q.mode}`}>
                Supporting news: {q.provenance.news_evidence_window.evidence_quarter} articles published
                {" "}{q.provenance.news_evidence_window.window_start_ph.slice(0, 10)} to {q.provenance.news_evidence_window.information_cutoff_ph.slice(0, 10)}
                {" "}({q.provenance.news_evidence_window.coverage}, {q.provenance.news_evidence_window.days_covered} of {q.provenance.news_evidence_window.days_in_quarter} days).
                {" "}Generated {q.provenance.generated_at.slice(0, 16)}. The engine itself uses no news ({q.provenance.n_articles_used_by_model} articles).
              </div>
            )}
          </div>
        ))}
      </section>

      <section className="grid md:grid-cols-2 gap-2">
        {PROVINCE_ORDER.map((c) => {
          const b = rec.provinces_now[c];
          const nq = b.news_2026Q4_to_cutoff;
          return (
            <div key={c} className="border border-slate-400 p-2" data-testid={`province-${c}`}>
              <div className="font-semibold text-[13px]">{b.province}</div>
              <div className="grid grid-cols-2 gap-2">
                <div><div className="text-[11px] uppercase">2026-Q4 nowcast</div><Estimate e={b.nowcast_2026Q4} testid={`now-${c}`} /></div>
                <div><div className="text-[11px] uppercase">2027-Q1 forecast</div><Estimate e={b.forecast_2027Q1} testid={`fc-${c}`} /></div>
              </div>
              <div data-testid={`price-${c}`}>{b.price_pressure_text}</div>
              <div data-testid={`news-${c}`}>News, 1–14 Oct 2026: {nq?.admitted_after_dedup ?? 0} validated of {nq?.province_attributed ?? 0} province-attributed articles ({(nq?.evidence_status_v2 ?? "NO_USABLE_EVIDENCE").replace(/_/g, " ").toLowerCase()}).</div>
              <div className="font-semibold">{b.attention}.</div>
              <div>{b.suggested_use}</div>
              <div className="mt-1 text-[11px]">Top LGUs (relative position only): {rec.lgu_ranking.rows
                .filter((r) => r.province_code === c && r.rank_in_province != null)
                .sort((a, z) => (a.rank_in_province ?? 0) - (z.rank_in_province ?? 0)).slice(0, 5)
                .map((r) => r.lgu_name).join(", ")}</div>
            </div>
          );
        })}
      </section>

      {q3 && (
        <section className="border p-2" data-testid="q3">
          <h2 className="font-semibold">2026-Q3: forecast frozen before the outcome was released, then scored</h2>
          <table className="text-[11px]"><thead><tr><th>Province</th><th>P frozen 1 Jul</th><th>Observed S1</th><th>Observed</th></tr></thead>
            <tbody>{PROVINCE_ORDER.map((c) => { const v = q3.provinces[c]; return (
              <tr key={c}><td>{v.province}</td><td>{pct(v.p_high)}</td><td>{v.observed_S1?.toFixed(1)}</td><td>{v.observed_label}</td></tr>); })}</tbody>
          </table>
          <div className="italic">{rec.validation.unseen_quarter_2026Q3.caveat}</div>
        </section>
      )}

      <section className="border p-2" data-testid="validation">
        <h2 className="font-semibold">How reliable is this?</h2>
        <div data-testid="threshold-verdict">{rec.validation.threshold_75pct.verdict}</div>
        <table className="text-[11px]"><thead><tr><th>Approach</th><th>Accuracy, lead 1</th><th>Above 75%</th></tr></thead>
          <tbody>{rec.validation.threshold_75pct.rows.map((r) => (
            <tr key={r.arm}><td>{r.arm}</td><td>{r.accuracy_lead1.toFixed(3)}</td><td>{r.above_75pct ? "yes" : "no"}</td></tr>))}</tbody>
        </table>
        <div>News relevance rule (blind holdout): precision {ho.precision}, recall {ho.recall}. {rec.validation.news_relevance.deployed_rule}.</div>
      </section>

      <section className="border p-2" data-testid="limitations">
        <h2 className="font-semibold">Limitations</h2>
        <ul className="list-disc pl-5">{rec.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
      </section>
      <div className="flex gap-4">
        <a className="underline" href={`${API_BASE_URL}/api/v1/quarterly/e31/report.pdf`}>Download the PDF assessment report</a>
        <a className="underline" href="/news">News evidence</a>
        <span className="text-[10px]">Record {rec.content_sha256.slice(0, 16)}…</span>
      </div>
    </div>
  );
}

export default function E31Brief() {
  const [rec, setRec] = useState<ServedRecord | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { loadE31().then(setRec).catch((e) => setErr(String(e))); }, []);
  if (err) return <div className="p-4">Could not load the assessment: {err}</div>;
  if (!rec) return <div className="p-4">Loading…</div>;
  return isE36(rec) ? <E36BriefView rec={rec} /> : <E31BriefView rec={rec} />;
}
