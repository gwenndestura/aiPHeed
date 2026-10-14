/**
 * E29 DA brief (schema 4). Adds, above the E28 brief:
 *  - the official regional hunger observation, shown ONCE and marked as one Balance Luzon value shared by all five
 *    provinces (never five local measurements);
 *  - per province, an evidence table that labels every item MEASURED / EXPERIMENTAL / UNAVAILABLE with its geographic
 *    level, the observed price pressure (price pressure, not food insecurity), and a MONITORING ONLY suitability.
 */
import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import { E28Record, PROVINCE_ORDER, ProvinceBrief } from "@/lib/e28Record";
import { E28BriefView } from "@/pages/E28Brief";

export interface EvidenceItem { item: string; kind: string; level: string; value: string }
export type E29Province = ProvinceBrief & {
  observed_price_pressure: { text: string; direction: string; relative_food_inflation_pp: number[]; quarters: string[] };
  evidence_table: EvidenceItem[];
  would_help_validate: string[];
  suitability: string;
};
export type E29Record = E28Record & {
  schema: 4;
  regional_observation: {
    what: string; kind: string; geographic_level: string; note: string; change_last_two_pp: number;
    rounds: { quarter: string; round: string; hunger_pct: number; published: string; date_type: string }[];
  };
  forecast_quarter: E28Record["forecast_quarter"] & { provinces: Record<string, E29Province> };
};

export function E29BriefView({ rec }: { rec: E29Record }) {
  const ro = rec.regional_observation;
  return (
    <div>
      <div className="p-4 space-y-4 max-w-6xl mx-auto">
        <section data-testid="regional-observation" className="border-2 border-slate-500 p-2 text-[12px]">
          <h2 className="font-semibold">Official regional hunger ({ro.kind.toLowerCase()})</h2>
          <div data-testid="regional-level">{ro.what}. {ro.geographic_level}.</div>
          <table className="text-[11px]">
            <thead><tr><th>Quarter</th><th>Round</th><th>Hunger %</th><th>Published</th></tr></thead>
            <tbody>{ro.rounds.map((o) => (
              <tr key={o.round}><td>{o.quarter}</td><td>{o.round}</td><td>{o.hunger_pct}</td>
                <td>{o.published}{o.date_type.startsWith("unverified") ? " (upper bound)" : ""}</td></tr>))}</tbody>
          </table>
          <div className="italic">{ro.note}</div>
        </section>
        <section className="grid md:grid-cols-2 gap-2">
          {PROVINCE_ORDER.filter((c) => rec.forecast_quarter.provinces[c]).map((c) => {
            const b = rec.forecast_quarter.provinces[c];
            return (
              <div key={c} data-testid={`evidence-${c}`} className="border border-slate-400 p-2 text-[11px]">
                <div className="font-semibold">{b.province}: what is measured vs estimated</div>
                <table><tbody>{b.evidence_table.map((e) => (
                  <tr key={e.item} data-kind={e.kind}><td>{e.item}</td><td className="font-semibold">{e.kind}</td>
                    <td>{e.level}</td><td>{e.value}</td></tr>))}</tbody></table>
                <div data-testid={`price-${c}`}>{b.observed_price_pressure.text}</div>
                <div className="font-semibold" data-testid={`suitability-${c}`}>{b.suitability}</div>
                <div>Would help validate: {b.would_help_validate.join("; ")}</div>
              </div>
            );
          })}
        </section>
        <a className="underline text-[11px]" href={`${API_BASE_URL}/quarterly/e29/brief.pdf`}>E29 PDF</a>
      </div>
      <E28BriefView rec={rec} />
    </div>
  );
}

export default function E29Brief() {
  const [rec, setRec] = useState<E29Record | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API_BASE_URL}/quarterly/e29/brief`);
        if (r.ok) return setRec((await r.json()) as E29Record);
      } catch { /* fall back to the identical static copy */ }
      const s = await fetch("/e29_da_brief_record.json");
      setRec((await s.json()) as E29Record);
    })().catch((e) => setErr(String(e)));
  }, []);
  if (err) return <div className="p-4">Could not load the DA brief: {err}</div>;
  if (!rec) return <div className="p-4">Loading…</div>;
  return <E29BriefView rec={rec} />;
}
