/**
 * E25 forecast timeline: 2025-Q1 .. 2027-Q1 on one page.
 *  - 2025-Q1 .. 2026-Q2: actual labels and back-test forecasts (development evidence), measured SWS and provincial
 *    price values;
 *  - 2026-Q3, 2026-Q4: sealed forecasts, "outcome pending";
 *  - 2027-Q1: the operational forecast only if every required input is authorized and available at the cutoff,
 *    otherwise exactly which inputs are missing.
 * A cell without a forecast has its own MISSING / NO LABEL style and never looks like low risk.
 */
import { useEffect, useState } from "react";
import { E25Record, QuarterEntry, loadE25Record, pct, tileState } from "@/lib/e25Record";

const PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"];

const riskStyle = (p: number) =>
  p >= 0.5 ? "bg-amber-100 border-amber-500 text-amber-950" : "bg-sky-100 border-sky-500 text-sky-950";

function Cell({ q, code }: { q: QuarterEntry; code: string }) {
  const s = tileState(q, code);
  if (s.kind === "BACKTEST") {
    const f = s.f;
    const pp = q.provinces[code]?.price_pressure_forecast;
    return (
      <div data-testid={`cell-${q.quarter}-${code}`} className={`border-2 rounded p-1 text-[11px] ${riskStyle(f.p_high)}`}>
        <div className="font-semibold">P(HIGH) {pct(f.p_high)} · {f.signal}</div>
        <div>S1 80%: {f.S1_80pct_interval[0]} to {f.S1_80pct_interval[1]}</div>
        <div>regional {f.regional_part_H_minus_tau >= 0 ? "+" : ""}{f.regional_part_H_minus_tau} · provincial {f.provincial_part_2D >= 0 ? "+" : ""}{f.provincial_part_2D}</div>
        <div>actual: <b>{s.actual ?? "—"}</b> {f.correct ? "✓" : "✗"}</div>
        <div className="italic">lead {f.lead_quarters}, cutoff {f.information_cutoff.slice(0, 10)} · indicative only</div>
        {pp && <div>price pressure P(D&gt;0) {pct(pp.p_above_regional_mean)} (exploratory) · actual {pp.actual}</div>}
      </div>
    );
  }
  if (s.kind === "SEALED_PENDING") {
    const fin = s.sealed.find((x) => x.FINAL_T1);
    return (
      <div data-testid={`cell-${q.quarter}-${code}`} className="border-2 border-dashed border-violet-500 bg-violet-50 rounded p-1 text-[11px]">
        <div className="font-semibold">SEALED · outcome pending</div>
        {fin && (
          <div>
            FINAL P(HIGH) {pct(fin.p)} · {fin.signal} (lead {fin.lead})
            {fin.S1_80pct_interval && <div>S1 80%: {fin.S1_80pct_interval[0]} to {fin.S1_80pct_interval[1]}</div>}
          </div>
        )}
        <div>cutoff {(fin ?? s.sealed[0])?.information_cutoff?.slice(0, 10) ?? "—"} · {s.sealed.length} sealed arm(s); indicative only</div>
      </div>
    );
  }
  if (s.kind === "MISSING_INPUTS") {
    return (
      <div data-testid={`cell-${q.quarter}-${code}`}
        className="border-2 border-dashed border-slate-500 rounded p-1 text-[11px] text-slate-800"
        style={{ backgroundImage: "repeating-linear-gradient(45deg,#e2e8f0 0 6px,#f8fafc 6px 12px)" }}>
        <div className="font-semibold">MISSING INPUTS</div>
        <div>No forecast. This is not a low-risk state.</div>
      </div>
    );
  }
  return (
    <div data-testid={`cell-${q.quarter}-${code}`}
      className="border-2 border-dashed border-slate-400 rounded p-1 text-[11px] text-slate-700"
      style={{ backgroundImage: "repeating-linear-gradient(45deg,#f1f5f9 0 6px,#ffffff 6px 12px)" }}>
      <div className="font-semibold">NO LABEL / NO FORECAST</div>
      <div>{s.reason}</div>
    </div>
  );
}

export function E25TimelineView({ rec }: { rec: E25Record }) {
  const op = rec.quarters.find((q) => q.kind.startsWith("OPERATIONAL"));
  return (
    <div className="p-4 space-y-3 text-slate-900">
      <h1 className="text-xl font-bold">aiPHeed forecast timeline, Q1 2025 to Q1 2027</h1>
      <p className="text-sm" data-testid="constructed-note">{rec.score_is_constructed}</p>
      <p className="text-sm font-semibold" data-testid="indicative-note">{rec.indicative_only_reason}</p>
      <p className="text-xs">Signal: {rec.signal_rule}. Record SHA-256: <code data-testid="record-hash">{rec.content_sha256}</code></p>
      <div className="overflow-x-auto">
        <table className="border-collapse text-xs">
          <thead>
            <tr>
              <th className="p-1 text-left">Province</th>
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
              <td className="p-1 font-semibold">Regional SWS hunger (measured, Balance Luzon)</td>
              {rec.quarters.map((q) => (
                <td key={q.quarter} className="p-1 text-[11px]" data-testid={`sws-${q.quarter}`}>
                  {q.measured_regional?.sws_hunger_balance_luzon_pct != null ? (
                    <span>
                      {q.measured_regional.sws_hunger_balance_luzon_pct}%{" "}
                      {q.measured_regional.approx_95ci_n600_srs && (
                        <span>(≈95% {q.measured_regional.approx_95ci_n600_srs[0]}–{q.measured_regional.approx_95ci_n600_srs[1]})</span>
                      )}
                    </span>
                  ) : (
                    <span className="italic">{q.measured_regional?.status ?? q.status}</span>
                  )}
                </td>
              ))}
            </tr>
            {PROVS.map((code) => (
              <tr key={code}>
                <td className="p-1 font-semibold">{rec.quarters[0].provinces[code]?.province}</td>
                {rec.quarters.map((q) => (
                  <td key={q.quarter} className="p-1 align-top min-w-[150px]">
                    <Cell q={q} code={code} />
                    {q.provinces[code]?.measured && (
                      <div className="text-[10px] mt-0.5">
                        PSA food CPI YoY {q.provinces[code].measured!.food_cpi_yoy_pct}% · D {q.provinces[code].measured!.D_relative_food_inflation_pp} pp
                        <div className="italic">{q.provinces[code].measured!.ci}</div>
                      </div>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {op && (
        <section className="border border-slate-400 rounded p-2" data-testid="op-missing">
          <h2 className="font-semibold">{op.display}: {op.status}</h2>
          <p className="text-sm">Information cutoff {op.information_cutoff}. Missing inputs:</p>
          <ul className="list-disc ml-5 text-sm">
            {(op.missing_inputs ?? []).map((m) => <li key={m}>{m}</li>)}
          </ul>
          <p className="text-sm mt-1">Who must supply them:</p>
          <ul className="list-disc ml-5 text-sm">
            {Object.entries(op.who_supplies ?? {}).map(([k, v]) => <li key={k}>{k}: {v}</li>)}
          </ul>
        </section>
      )}
      <a className="underline text-sm" href="/aiPHeed_E25_forecast_report.pdf">PDF report (same record)</a>
    </div>
  );
}

export default function E25Timeline() {
  const [rec, setRec] = useState<E25Record | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    loadE25Record().then(setRec).catch((e) => setErr(String(e)));
  }, []);
  if (err) return <div className="p-4">Forecast record unavailable: {err}</div>;
  if (!rec) return <div className="p-4">Loading forecast record…</div>;
  return <E25TimelineView rec={rec} />;
}
