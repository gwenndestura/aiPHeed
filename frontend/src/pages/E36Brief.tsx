/**
 * E36 DA brief (/da-brief when the served record is schema e36/1). What DA Region IV-A sees for the next quarter: the
 * one-quarter-ahead LightGBM forecast with its origin and information cutoff, the exact TreeSHAP drivers in plain
 * language, the latest backtest next to its observed outcome, the measured price pressure, the news evidence status,
 * the evaluation against the six Chapter I baselines (including the 75% question), the LGU top five and the
 * limitations. The band shown is always called an estimate.
 */
import { API_BASE_URL } from "@/lib/api";
import { E36Record, MODE_TEXT, pct, PROVINCE_ORDER, ProvinceEstimate } from "@/lib/e31Record";

const f3 = (x: number | null | undefined) => (x == null ? "–" : x.toFixed(3));

function Drivers({ e, testid }: { e: ProvinceEstimate; testid: string }) {
  return (
    <table className="text-[11px] mt-1">
      <tbody>
        {(e.drivers || []).slice(0, 5).map((d) => (
          <tr key={d.key} data-testid={`${testid}-driver-${d.key}`}>
            <td className="pr-2">{d.factor}</td>
            <td className={d.contribution >= 0 ? "text-red-700" : "text-green-700"}>
              {d.contribution >= 0 ? "raises" : "lowers"} ({d.contribution >= 0 ? "+" : ""}{d.contribution.toFixed(2)})
            </td>
            <td className="pl-2 italic">{d.kind}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function E36BriefView({ rec }: { rec: E36Record }) {
  const fc = rec.quarters.find((q) => q.mode === "FORECAST")!;
  const last = rec.quarters.filter((q) => q.mode === "BACKTEST").slice(-1)[0];
  const rh = rec.regional_hunger;
  const ev = rec.validation.model_evaluation;
  const ho = rec.validation.news_relevance.holdout.gates["R1"];
  const se = rec.served_engine;
  return (
    <div className="p-4 space-y-4 max-w-6xl mx-auto text-[12px]">
      <header>
        <h1 className="text-xl font-semibold">{rec.title}</h1>
        <div data-testid="model">Model {se.name}, version {se.version}. {se.evidence_status}.</div>
        <div data-testid="cutoff">Data {rec.data_authorization}.</div>
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

      <section className="border p-2" data-testid="mode-FORECAST">
        <div className="font-semibold">{fc.quarter}: {MODE_TEXT[fc.mode]} (lead {fc.lead})</div>
        <div>Issued at {fc.origin} using only information published before it ({fc.information_cutoff}); {fc.status}.</div>
        {fc.provenance && (
          <div data-testid="window-FORECAST">
            News used: {fc.provenance.news_evidence_window.evidence_quarter} articles published
            {" "}{fc.provenance.news_evidence_window.window_start_ph.slice(0, 10)} to {fc.provenance.news_evidence_window.information_cutoff_ph.slice(0, 10)}
            {" "}({fc.provenance.n_articles_used_by_model} validated articles in the five provinces).
          </div>
        )}
      </section>

      <section className="grid md:grid-cols-2 gap-2">
        {PROVINCE_ORDER.map((c) => {
          const b = rec.provinces_now[c];
          const ne = b.news_evidence;
          return (
            <div key={c} className="border border-slate-400 p-2" data-testid={`province-${c}`}>
              <div className="font-semibold text-[13px]">{b.province}</div>
              <div className="grid grid-cols-2 gap-2">
                <div data-testid={`fc-${c}`}>
                  <div className="text-[11px] uppercase">{b.forecast_quarter} forecast</div>
                  <div className="text-lg font-semibold">{pct(b.forecast.p_high)} <span className="text-[11px] font-normal">({b.forecast.signal})</span></div>
                  <div className="text-[11px]">Estimated {b.forecast.p_high >= 0.5 ? "high" : "low"} (model estimate, not validated)</div>
                </div>
                <div data-testid={`bt-${c}`}>
                  <div className="text-[11px] uppercase">{b.latest_backtest.quarter} backtest</div>
                  <div className="text-lg font-semibold">{pct(b.latest_backtest.p_high)}</div>
                  <div className="text-[11px]">Observed afterwards: {b.latest_backtest.observed_label}</div>
                </div>
              </div>
              <div data-testid={`why-${c}`} className="mt-1">{b.explanation_text}</div>
              <Drivers e={b.forecast} testid={`fc-${c}`} />
              <div data-testid={`price-${c}`}>{b.price_pressure_text}</div>
              <div data-testid={`news-${c}`}>News, {b.news_evidence_quarter}: {ne?.admitted_after_dedup ?? 0} validated of {ne?.province_attributed ?? 0} province-attributed articles ({(ne?.evidence_status_v2 ?? "NO_USABLE_EVIDENCE").replace(/_/g, " ").toLowerCase()}).</div>
              <div className="font-semibold">{b.attention}.</div>
              <div>{b.suggested_use}</div>
              <div className="mt-1 text-[11px]">Top LGUs within the province (relative position only): {rec.lgu_ranking.rows
                .filter((r) => r.province_code === c && r.rank_in_province != null)
                .sort((a, z) => (a.rank_in_province ?? 0) - (z.rank_in_province ?? 0)).slice(0, 5)
                .map((r) => r.lgu_name).join(", ")}</div>
            </div>
          );
        })}
      </section>

      <section className="border p-2" data-testid="validation">
        <h2 className="font-semibold">How reliable is this? One quarter ahead, {ev.dates.length} development quarters</h2>
        <div data-testid="threshold-verdict">{rec.validation.threshold_75pct.verdict}</div>
        <table className="text-[11px]" data-testid="baselines">
          <thead><tr><th>Approach</th><th>Correct</th><th>Accuracy (95% CI)</th><th>Bal. acc.</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th><th>Brier</th></tr></thead>
          <tbody>{ev.rows.map((r) => (
            <tr key={r.key} data-testid={`row-${r.key}`}>
              <td>{r.arm}</td><td>{r.correct}/{r.n}</td><td>{f3(r.accuracy_lead1)} ({f3(r.accuracy_ci95[0])}–{f3(r.accuracy_ci95[1])})</td>
              <td>{f3(r.balanced_accuracy)}</td><td>{f3(r.precision)}</td><td>{f3(r.recall)}</td><td>{f3(r.f1)}</td><td>{f3(r.roc_auc)}</td><td>{f3(r.brier)}</td>
            </tr>))}</tbody>
        </table>
        <div className="italic">{ev.basis}. Prospective test: {rec.validation.prospective_2026Q4.status}.</div>
        <div>News relevance rule (blind holdout): precision {ho.precision}, recall {ho.recall}. {rec.validation.news_relevance.deployed_rule}.</div>
      </section>

      {last && (
        <section className="border p-2" data-testid="last-backtest">
          <h2 className="font-semibold">{last.quarter}: backtest next to the observed outcome</h2>
          <table className="text-[11px]"><thead><tr><th>Province</th><th>Estimate</th><th>Observed</th></tr></thead>
            <tbody>{PROVINCE_ORDER.map((c) => { const v = last.provinces[c]; return (
              <tr key={c}><td>{v.province}</td><td>{pct(v.p_high)}</td><td>{v.observed_label}</td></tr>); })}</tbody>
          </table>
        </section>
      )}

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
