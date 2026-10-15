/**
 * E27 forecast timeline (Q1 2025 - Q1 2027), read from the single E27 record.
 *  - Experimental estimates use one neutral style: no amber/blue "high/low" colouring and no HIGH/LOW word unless a
 *    lead is VALIDATED by the prospective ledger and the adviser-approved rule.
 *  - Regional hunger (measured, one value for the region), the constructed provincial price-pressure indicator and
 *    the official anchor are separate rows/sections, never mixed into the risk cell.
 *  - The operational quarter lists every missing dependency and the forecast period it blocks; the sealed earlier-
 *    information estimate is shown as an experimental estimate, never as the operational forecast.
 */
import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import {
  E27Record,
  PROVINCE_CODES,
  QuarterRow,
  RiskView,
  loadE27Record,
  riskWording,
} from "@/lib/e27Record";

const pct = (x: number | null | undefined) => (x == null ? "—" : `${Math.round(x * 100)}%`);

function RiskBlock({ r, testId }: { r: RiskView; testId: string }) {
  const w = riskWording(r);
  const validated = r.evidence.status === "VALIDATED";
  return (
    <div
      data-testid={testId}
      data-evidence={r.evidence.status}
      className={`border-2 rounded p-1 text-[11px] ${validated ? "border-emerald-600 bg-emerald-50" : "border-slate-400 bg-white"}`}
    >
      <div className="font-semibold">{w.headline}</div>
      {r.S1_80pct_interval && (
        <div>
          S1 80% interval {r.S1_80pct_interval[0]} to {r.S1_80pct_interval[1]}
          {r.threshold != null && <> · threshold {r.threshold}</>}
        </div>
      )}
      <div className="italic">
        lead {r.lead_quarters}, information to {(r.information_cutoff ?? "—").slice(0, 10)}
      </div>
      <div className={validated ? "text-emerald-800" : "text-slate-700 font-semibold"}>
        {validated ? "VALIDATED forecast" : "EXPERIMENTAL — not validated"}
      </div>
      {r.approved_label_measured !== undefined && (
        <div>measured label: <b>{r.approved_label_measured ?? "no label"}</b></div>
      )}
    </div>
  );
}

function Cell({ q, code }: { q: QuarterRow; code: string }) {
  const d = q.provinces[code];
  const id = `cell-${q.quarter}-${code}`;
  if (q.state === "MISSING_INPUTS") {
    return (
      <div data-testid={id} className="space-y-1">
        <div
          className="border-2 border-dashed border-slate-500 rounded p-1 text-[11px] text-slate-800"
          style={{ backgroundImage: "repeating-linear-gradient(45deg,#e2e8f0 0 6px,#f8fafc 6px 12px)" }}
        >
          <div className="font-semibold">MISSING INPUTS</div>
          <div>No operational forecast. This is not a low-risk state.</div>
        </div>
        {d.experimental_estimate && (
          <div className="text-[10px]">
            <div className="font-semibold">Earlier-information estimate (not the operational forecast):</div>
            <RiskBlock r={d.experimental_estimate} testId={`exp-${q.quarter}-${code}`} />
          </div>
        )}
      </div>
    );
  }
  if (d.risk) {
    return (
      <div data-testid={id}>
        {q.state === "SEALED_PENDING" && <div className="text-[10px] font-semibold text-violet-800">SEALED · outcome pending</div>}
        <RiskBlock r={d.risk} testId={`risk-${q.quarter}-${code}`} />
      </div>
    );
  }
  if (q.state === "SEALED_PENDING") {
    return (
      <div data-testid={id} className="border-2 border-dashed border-violet-500 bg-violet-50 rounded p-1 text-[11px]">
        <div className="font-semibold">SEALED · outcome pending</div>
        <div>{(d.sealed ?? []).length} sealed arm(s) from an earlier seal; no FINAL estimate for this quarter</div>
      </div>
    );
  }
  return (
    <div
      data-testid={id}
      className="border-2 border-dashed border-slate-400 rounded p-1 text-[11px] text-slate-700"
      style={{ backgroundImage: "repeating-linear-gradient(45deg,#f1f5f9 0 6px,#ffffff 6px 12px)" }}
    >
      <div className="font-semibold">NO LABEL / NO FORECAST</div>
      <div>{d.risk_state ?? "no forecast"}</div>
    </div>
  );
}

export function E27TimelineView({ rec }: { rec: E27Record }) {
  const op = rec.quarters.find((q) => q.state === "MISSING_INPUTS" || q.state === "READY");
  const names = Object.fromEntries(PROVINCE_CODES.map((c) => [c, rec.quarters[0].provinces[c].province]));
  return (
    <div className="p-4 space-y-3 text-slate-900">
      <h1 className="text-xl font-bold">aiPHeed forecast timeline, Q1 2025 to Q1 2027</h1>
      <section data-testid="evidence-banner" className="border-2 border-slate-700 rounded p-2 bg-slate-50">
        <div className="font-bold">Evidence status: {rec.evidence_summary.status}</div>
        <p className="text-sm">{rec.evidence_summary.statement}</p>
        <p className="text-xs">{rec.evidence_summary.accuracy_note}</p>
      </section>
      <p className="text-sm" data-testid="constructed-note">{rec.score_is_constructed}</p>
      <p className="text-xs">
        Record SHA-256: <code data-testid="record-hash">{rec.content_sha256}</code>
      </p>
      <div className="overflow-x-auto">
        <table className="border-collapse text-xs">
          <thead>
            <tr>
              <th className="p-1 text-left">Layer / province</th>
              {rec.quarters.map((q) => (
                <th key={q.quarter} className="p-1 align-bottom" data-testid={`col-${q.quarter}`}>
                  <div>{q.display}</div>
                  <div className="font-normal text-[10px]">{q.kind}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="p-1 font-semibold">Regional hunger, measured (SWS Balance Luzon; one value for all provinces)</td>
              {rec.quarters.map((q) => (
                <td key={q.quarter} className="p-1 text-[11px]" data-testid={`regional-${q.quarter}`}>
                  {q.regional_layer.measured_pct != null ? `${q.regional_layer.measured_pct}%` : <i>{q.regional_layer.status ?? "—"}</i>}
                </td>
              ))}
            </tr>
            {PROVINCE_CODES.map((code) => (
              <tr key={code}>
                <td className="p-1 font-semibold">{names[code]}: risk (approved label S1)</td>
                {rec.quarters.map((q) => (
                  <td key={q.quarter} className="p-1 align-top min-w-[160px]">
                    <Cell q={q} code={code} />
                  </td>
                ))}
              </tr>
            ))}
            {PROVINCE_CODES.map((code) => (
              <tr key={`pp-${code}`} className="bg-stone-50">
                <td className="p-1">{names[code]}: price pressure (CONSTRUCTED indicator, not food insecurity)</td>
                {rec.quarters.map((q) => {
                  const pp = q.provinces[code].price_pressure;
                  return (
                    <td key={q.quarter} className="p-1 text-[10px]" data-testid={`pp-${q.quarter}-${code}`}>
                      {pp ? `P(D>0) ${pct(pp.p_above_regional_mean)} · measured ${pp.measured_direction}` : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {op && (
        <section className="border border-slate-400 rounded p-2" data-testid="op-dependencies">
          <h2 className="font-semibold">
            {op.display}: {op.status} — information cutoff {op.information_cutoff}
          </h2>
          <p className="text-sm">The operational forecast is produced automatically as soon as every blocking input below is authorized and the cutoff has passed.</p>
          <table className="text-xs border-collapse mt-1">
            <thead>
              <tr>
                <th className="p-1 text-left">Needed</th>
                <th className="p-1 text-left">Blocks the forecast?</th>
                <th className="p-1 text-left">Status</th>
                <th className="p-1 text-left">Supplier</th>
                <th className="p-1 text-left">Normally released</th>
              </tr>
            </thead>
            <tbody>
              {(op.dependencies ?? []).map((d) => (
                <tr key={d.id} data-testid={`dep-${d.id}`}>
                  <td className="p-1">{d.needs}</td>
                  <td className="p-1">{d.blocking ? "yes" : "no (display context only)"}</td>
                  <td className="p-1">{d.status}</td>
                  <td className="p-1">{d.supplier}</td>
                  <td className="p-1">{d.normal_release}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <section className="border border-slate-300 rounded p-2 text-xs" data-testid="official-anchor">
        <h2 className="font-semibold text-sm">Official anchor: {rec.official_anchor.what}</h2>
        <p>{rec.official_anchor.use}</p>
        <table className="border-collapse">
          <thead>
            <tr><th className="p-1 text-left">Province</th><th className="p-1">2021 % (CV)</th><th className="p-1">2023 % (CV)</th></tr>
          </thead>
          <tbody>
            {PROVINCE_CODES.map((c) => (
              <tr key={c}>
                <td className="p-1">{names[c]}</td>
                <td className="p-1">{rec.official_anchor.values[c]["2021"].pct} ({rec.official_anchor.values[c]["2021"].cv_pct}%)</td>
                <td className="p-1">{rec.official_anchor.values[c]["2023"].pct} ({rec.official_anchor.values[c]["2023"].cv_pct}%)</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <p className="text-xs" data-testid="local-note">{rec.layers.local}</p>
      <a className="underline text-sm" data-testid="pdf-link" href={new URL("/api/v1/quarterly/timeline.pdf", API_BASE_URL).toString()}>
        PDF report (rendered from this record)
      </a>
    </div>
  );
}

export default function E27Timeline() {
  const [rec, setRec] = useState<E27Record | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    loadE27Record().then(setRec).catch((e) => setErr(String(e)));
  }, []);
  if (err) return <div className="p-4">Forecast record unavailable: {err}</div>;
  if (!rec) return <div className="p-4">Loading forecast record…</div>;
  return <E27TimelineView rec={rec} />;
}
