/**
 * News evidence (/news). The genuine, traceable articles behind the news signal, from the ONE E31 record:
 * filter by province, quarter and relevance class; the funnel from collected to province-quarter sufficiency is shown
 * for the same selection. Titles only: the source supplies no lead text, so no description is invented.
 */
import { useEffect, useMemo, useState } from "react";
import { E31Record, loadE31 } from "@/lib/e31Record";

const STATUS_TEXT: Record<string, string> = {
  SUFFICIENT: "sufficient (5+ validated articles)",
  LIMITED_SIGNAL: "limited (1–4 validated articles)",
  NO_USABLE_EVIDENCE: "no usable evidence",
};

export function NewsEvidenceView({ rec }: { rec: E31Record }) {
  const quarters = useMemo(() => Array.from(new Set(rec.news.by_province_quarter.map((r) => r.quarter))).sort().reverse(), [rec]);
  const provinces = useMemo(() => Array.from(new Set(rec.news.by_province_quarter.map((r) => r.province))).sort(), [rec]);
  const [province, setProvince] = useState("all");
  const [quarter, setQuarter] = useState(quarters[0] ?? "all");
  const [relevance, setRelevance] = useState("all");
  const rows = rec.news.by_province_quarter.filter((r) => (province === "all" || r.province === province)
    && (quarter === "all" || r.quarter === quarter));
  const sum = (k: keyof (typeof rows)[number]) => rows.reduce((a, r) => a + (Number(r[k]) || 0), 0);
  const arts = rec.news.articles.filter((a) => (province === "all" || a.province === province)
    && (quarter === "all" || a.quarter === quarter) && (relevance === "all" || a.relevance === relevance));
  const t = rec.news.totals;
  return (
    <div className="p-4 space-y-3 max-w-6xl mx-auto text-[12px]">
      <h1 className="text-xl font-semibold">News evidence</h1>
      <div>{rec.news.source}. Relevance rule {rec.news.relevance_rule}: an article counts only when its title reports
        a food-insecurity condition or response (DIRECT) or a food-system stress such as losses, disease, supply or staple
        prices (INDIRECT). General agriculture, weather and business news are not counted.</div>
      <div className="flex flex-wrap gap-2" data-testid="filters">
        <label>Province <select className="bg-background text-foreground border rounded px-1" data-testid="f-province" value={province} onChange={(e) => setProvince(e.target.value)}>
          <option value="all">All five</option>{provinces.map((p) => <option key={p}>{p}</option>)}</select></label>
        <label>Quarter <select className="bg-background text-foreground border rounded px-1" data-testid="f-quarter" value={quarter} onChange={(e) => setQuarter(e.target.value)}>
          <option value="all">All quarters</option>{quarters.map((q) => <option key={q}>{q}</option>)}</select></label>
        <label>Relevance <select className="bg-background text-foreground border rounded px-1" data-testid="f-relevance" value={relevance} onChange={(e) => setRelevance(e.target.value)}>
          <option value="all">Direct and indirect</option><option value="DIRECT">Direct only</option>
          <option value="INDIRECT">Indirect only</option></select></label>
      </div>
      <table className="text-[11px] border" data-testid="funnel">
        <tbody>
          <tr><td>Collected by the province queries</td><td data-testid="n-collected">{sum("collected_by_province_queries")}</td></tr>
          <tr><td>Attributed to a province (title geocoding)</td><td data-testid="n-attributed">{sum("province_attributed")}</td></tr>
          <tr><td>Classified food-insecurity relevant</td><td data-testid="n-relevant">{sum("relevant_R1")}</td></tr>
          <tr><td>Contributing to the FSSI (after removing syndicated copies)</td><td data-testid="n-fssi">{sum("admitted_after_dedup")}</td></tr>
          <tr><td>Province-quarters with sufficient evidence</td><td data-testid="n-sufficient">
            {rows.filter((r) => r.evidence_status_v2 === "SUFFICIENT").length} of {rows.length}</td></tr>
        </tbody>
      </table>
      <div className="text-[11px]">Whole corpus 2021-01-01 to 2026-10-14: {t.collected} collected, {t.province_attributed} province-attributed,
        {" "}{t.admitted_to_FSSI_v2} validated; {t.province_quarters_sufficient_v2} province-quarters sufficient,
        {" "}{t.province_quarters_limited_v2} limited, {t.province_quarters_none_v2} without usable evidence.</div>
      {quarter !== "all" && province !== "all" && rows[0] && (
        <div data-testid="pq-status">{province} {quarter}: {STATUS_TEXT[rows[0].evidence_status_v2] ?? rows[0].evidence_status_v2}.
          {" "}Limited or missing news is never read as low risk.</div>
      )}
      <ul className="space-y-1" data-testid="articles">
        {arts.length === 0 && <li data-testid="empty">No validated article for this selection.</li>}
        {arts.map((a) => (
          <li key={a.article_key} className="border-b pb-1" data-testid="article">
            <a className="underline" href={a.link} target="_blank" rel="noreferrer">{a.title}</a>
            <div className="text-[11px]">{a.outlet} · {a.published_ph.slice(0, 10)} · {a.province} · {a.quarter} ·
              {" "}<span data-testid="relevance">{a.relevance === "DIRECT" ? "Direct report" : "Food-system stress"}</span></div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function NewsEvidence() {
  const [rec, setRec] = useState<E31Record | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { loadE31().then(setRec).catch((e) => setErr(String(e))); }, []);
  if (err) return <div className="p-4">Could not load the news evidence: {err}</div>;
  if (!rec) return <div className="p-4">Loading…</div>;
  return <NewsEvidenceView rec={rec} />;
}
