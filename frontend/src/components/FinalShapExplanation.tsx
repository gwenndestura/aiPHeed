// "Why this forecast?": the exact SHAP explanation of the official FINAL (RATE + MIND) LightGBM forecast.
// Province view: official result first, then a waterfall from the survey starting point to the forecast (log-odds), the inputs that
// raised and lowered the model output with the values the model used, and every input used. "Overall model" tab: global importance
// (mean |SHAP| on past test forecasts). Supporting context and inputs FINAL does not use are listed apart, never in a SHAP chart.
// Colours: the existing risk tokens only (raises = --risk-high, lowers = --risk-low, neutral = muted).
import { fmtPct } from "@/lib/risk";
import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { Note } from "@/components/ui/note";
import { isLoadFailure, LOAD_ERROR_MESSAGE } from "@/lib/loadError";
import {
  useFinalShap, useFinalShapContext, useFinalShapGlobal,
  type ShapContributor, type ShapProvince,
} from "@/lib/finalShap";

const UP = "hsl(var(--risk-high))";
const DOWN = "hsl(var(--risk-low))";
const MUTED = "hsl(var(--muted-foreground))";
const colorOf = (d: ShapContributor["direction"]) => (d === "raises" ? UP : d === "lowers" ? DOWN : MUTED);
const signed = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(3)}`;
const dirWord = (d: ShapContributor["direction"]) =>
  d === "raises" ? "pushed the output higher" : d === "lowers" ? "pushed the output lower" : "little influence";

export function FinalShapExplanation({ id, quarterId, compact = false }: { id: string; quarterId?: string; compact?: boolean }) {
  const [tab, setTab] = useState<"forecast" | "global">("forecast");
  const { data, isLoading, error } = useFinalShap(id, quarterId);
  if (isLoading) return <p className="text-[10px] text-muted-foreground">Loading the model explanation…</p>;
  if (isLoadFailure(error)) return <Note label={null}>{LOAD_ERROR_MESSAGE}</Note>;
  if (!data) return null;
  if (!data.available) {
    return (
      <Note label="Explanation unavailable">
        {data.reason ?? "No exact SHAP explanation exists for this selection."} No substitute explanation is shown.
      </Note>
    );
  }
  return (
    <div data-testid="final-shap" className="space-y-2">
      {!compact && (
        <div className="flex gap-1 text-[10px]" role="tablist">
          {(["forecast", "global"] as const).map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
              className={`px-2 py-0.5 rounded-md border ${tab === t ? "border-border bg-secondary/60 font-semibold" : "border-transparent text-muted-foreground hover:bg-secondary/40"}`}>
              {t === "forecast" ? (data.scope === "region" ? "These forecasts" : "This forecast") : "Overall model"}
            </button>
          ))}
        </div>
      )}
      {tab === "global" && !compact ? <GlobalImportance /> : data.scope === "region" ? <RegionView data={data} compact={compact} /> : <ProvinceView data={data} />}
      {!compact && <ContextSection quarterId={quarterId} />}
    </div>
  );
}

function ProvinceView({ data }: { data: ShapProvince }) {
  const c = data.contributors ?? [];
  const up = c.filter((x) => x.direction === "raises").slice(0, 5);
  const down = c.filter((x) => x.direction === "lowers").slice(0, 5);
  const o = data.official!;
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-1.5">
        <StatusBadge level={o.class === "HIGH" ? "high" : "low"} />
        <span className="text-[10px] text-foreground/90">
          Probability of HIGH <span className="font-mono-num font-bold">{o.pHigh < 0.001 ? "<0.1%" : fmtPct(o.pHigh * 100)}</span> · forecast share{" "}
          <span className="font-mono-num font-bold">{fmtPct(o.sharePct)}</span> (HIGH at {o.highAtSharePct}%)
        </span>
      </div>
      <p className="text-[10px] text-muted-foreground leading-snug">
        Province-specific SHAP of the FINAL forecast issued in {data.issue ?? "the served issue"}. Explained output: {data.explainedOutput}
      </p>
      <Waterfall data={data} />
      <FactorList heading="Inputs that pushed the output higher" items={up} empty="None this time." />
      <FactorList heading="Inputs that pushed the output lower" items={down} empty="None this time." />
      <Collapsible title={`All ${data.inputsUsed} inputs this forecast used, with their values`}>
        <AllInputs items={c} nearZero={data.nearZeroLogOdds} />
      </Collapsible>
      <Collapsible title="RATE, MIND and the probability of HIGH">
        <p className="text-[10px] text-muted-foreground leading-snug">{data.rateMind}</p>
        <p className="text-[10px] text-muted-foreground leading-snug mt-1">{data.probabilityNote}</p>
      </Collapsible>
      <p className="text-[9px] text-muted-foreground/80 leading-snug">
        SHAP shows how each input moved this model's forecast. It does not show that the input caused food insecurity.
      </p>
    </div>
  );
}

function RegionView({ data, compact }: { data: ShapProvince; compact: boolean }) {
  const c = (data.contributors ?? []).filter((x) => x.direction !== "near zero");
  const up = c.filter((x) => x.direction === "raises").slice(0, compact ? 3 : 5);
  const down = c.filter((x) => x.direction === "lowers").slice(0, compact ? 3 : 5);
  return (
    <div className="space-y-2">
      <p className="text-[10px] text-muted-foreground leading-snug">
        SHAP of the five official province forecasts, averaged (log-odds of the forecast share). Select a province for its own explanation and
        the values its forecast used.
      </p>
      {data.provinces && !compact && (
        <div className="grid grid-cols-5 gap-1 text-center">
          {data.provinces.map((p) => (
            <div key={p.province} className="inner-box px-1 py-1">
              <p className="text-[9px] truncate">{p.province}</p>
              <p className="text-[10px] font-mono-num font-bold">{fmtPct(p.sharePct)}</p>
              <p className="text-[9px] text-muted-foreground">{p.class}</p>
            </div>
          ))}
        </div>
      )}
      <FactorList heading="On average, pushed the output higher" items={up} empty="None." compact />
      <FactorList heading="On average, pushed the output lower" items={down} empty="None." compact />
    </div>
  );
}

/** Horizontal waterfall in log-odds: starting point → model's average change → largest inputs → other inputs → forecast. */
function Waterfall({ data }: { data: ShapProvince }) {
  const w = data.waterfall!;
  const c = data.contributors ?? [];
  const top = c.filter((x) => x.direction !== "near zero").slice(0, 6);
  const rest = c.reduce((s, x) => s + x.shapLogOdds, 0) - top.reduce((s, x) => s + x.shapLogOdds, 0);
  type Step = { label: string; from: number; to: number; color: string; value: string; title?: string };
  const steps: Step[] = [];
  steps.push({ label: "Starting point (survey anchor)", from: 0, to: w.anchorLogOdds, color: MUTED, value: fmtPct(w.anchorSharePct ?? 0), title: w.anchorText });
  let cur = w.anchorLogOdds;
  steps.push({ label: "Model's average change", from: cur, to: cur + w.expectedLogOdds, color: MUTED, value: signed(w.expectedLogOdds), title: w.expectedText });
  cur += w.expectedLogOdds;
  for (const x of top) {
    steps.push({ label: x.name, from: cur, to: cur + x.shapLogOdds, color: colorOf(x.direction), value: signed(x.shapLogOdds), title: x.explanation });
    cur += x.shapLogOdds;
  }
  steps.push({ label: `Other ${c.length - top.length} inputs`, from: cur, to: cur + rest, color: MUTED, value: signed(rest) });
  cur += rest;
  steps.push({ label: "Forecast", from: 0, to: w.forecastLogOdds, color: "hsl(var(--foreground))", value: fmtPct(w.forecastSharePct ?? 0) });
  const vals = steps.flatMap((s) => [s.from, s.to]).concat([0]);
  const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.06 || 0.1;
  const W = 300, L = 128, R = 44, rowH = 15, H = steps.length * rowH + 16;
  const x = (v: number) => L + ((v - (lo - pad)) / (hi - lo + 2 * pad)) * (W - L - R);
  return (
    <figure className="inner-box px-2 py-1.5" aria-label="SHAP waterfall of this forecast">
      <figcaption className="text-[10px] font-semibold mb-0.5">From the starting point to the forecast (log-odds)</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img">
        <line x1={x(0)} x2={x(0)} y1={0} y2={H - 12} stroke={UP} strokeDasharray="2 2" strokeWidth={0.8} />
        <text x={x(0)} y={H - 3} fontSize={7} textAnchor="middle" fill={MUTED}>0 = HIGH cut-off (50%)</text>
        {steps.map((s, i) => {
          const y = i * rowH + 2;
          return (
            <g key={i}>
              <title>{s.title ?? s.label}</title>
              <text x={L - 4} y={y + 9} fontSize={7.5} textAnchor="end" fill="currentColor">{s.label.length > 30 ? s.label.slice(0, 29) + "…" : s.label}</text>
              <rect x={Math.min(x(s.from), x(s.to))} y={y + 2} width={Math.max(1, Math.abs(x(s.to) - x(s.from)))} height={rowH - 5} fill={s.color} opacity={0.85} rx={1} />
              <text x={W - 2} y={y + 9} fontSize={7.5} textAnchor="end" fill={s.color} className="font-mono-num">{s.value}</text>
            </g>
          );
        })}
      </svg>
      <p className="text-[9px] text-muted-foreground leading-snug">
        Grey: the survey starting point and the change any province with this much time since its survey gets; these are not input effects.
        Red pushes the output toward HIGH; the low-risk colour (as on the map) pushes it away. Hover a row for its explanation. Starting point + average change + all inputs
        = the forecast exactly.
      </p>
    </figure>
  );
}

function FactorList({ heading, items, empty, compact = false }: { heading: string; items: ShapContributor[]; empty: string; compact?: boolean }) {
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-semibold text-foreground/90">{heading}</p>
      {items.length === 0 ? <p className="text-[10px] text-muted-foreground">{empty}</p> : items.map((x) => (
        <div key={x.feature} className="inner-box px-2 py-1.5" title={`${x.measures ?? ""} Source: ${x.source}. Period: ${x.period}.`}>
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] font-bold text-foreground/90 truncate">{x.name}</span>
            <span className="text-[10px] font-mono-num font-bold shrink-0" style={{ color: colorOf(x.direction) }}>{signed(x.shapLogOdds)}</span>
          </div>
          {!compact && x.valueText !== undefined && (
            <p className="text-[10px] text-foreground/80">Value used: <span className="font-mono-num">{x.valueText}</span> · {x.period} · {x.source}</p>
          )}
          <p className="text-[10px] text-muted-foreground leading-snug">{compact ? `${x.group}. ${dirWord(x.direction)}.` : x.explanation}</p>
        </div>
      ))}
    </div>
  );
}

function AllInputs({ items, nearZero }: { items: ShapContributor[]; nearZero: number }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[9px]">
        <thead>
          <tr className="text-muted-foreground text-left">
            <th className="font-semibold pr-1">Indicator</th><th className="font-semibold pr-1">Value used</th>
            <th className="font-semibold pr-1 text-right">SHAP</th><th className="font-semibold">Period · source</th>
          </tr>
        </thead>
        <tbody>
          {items.map((x) => (
            <tr key={x.feature} className="border-t border-border/30 align-top" title={x.explanation}>
              <td className="pr-1">{x.name}<span className="text-muted-foreground"> ({x.kind === "MIND missing flag" ? "MIND" : x.group})</span></td>
              <td className="pr-1 font-mono-num">{x.valueText}</td>
              <td className="pr-1 text-right font-mono-num" style={{ color: colorOf(x.direction) }}>{signed(x.shapLogOdds)}</td>
              <td className="text-muted-foreground">{x.period} · {x.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[9px] text-muted-foreground mt-1">
        SHAP in log-odds of the forecast share; |SHAP| below {nearZero} = little influence. Values are on the model's own scale (some are
        log-odds or relative values); the typical training value is in each row's explanation.
      </p>
    </div>
  );
}

function GlobalImportance() {
  const { data, isLoading } = useFinalShapGlobal();
  if (isLoading) return <p className="text-[10px] text-muted-foreground">Loading…</p>;
  if (!data?.available) return <Note label="Unavailable">{data?.reason ?? "Global importance is not available."}</Note>;
  const items = data.items!.slice(0, 15);
  const max = Math.max(...items.map((i) => i.meanAbsShapLogOdds), 1e-6);
  return (
    <div className="space-y-1.5" data-testid="final-shap-global">
      <p className="text-[10px] text-muted-foreground leading-snug">
        Overall model importance: how much FINAL relies on each input in general (mean |SHAP|, log-odds). It is not the reason any one province
        got its forecast. Reference: {data.reference}
      </p>
      {items.map((i) => (
        <div key={i.feature} className="grid grid-cols-[14px_1fr_40px] items-center gap-1.5" title={i.interpretation}>
          <span className="text-[9px] text-muted-foreground font-mono-num">{i.rank}</span>
          <div>
            <p className="text-[10px] truncate">{i.name} <span className="text-muted-foreground">· {i.group}</span></p>
            <div className="h-1.5 bg-secondary/40 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-muted-foreground/60" style={{ width: `${(100 * i.meanAbsShapLogOdds) / max}%` }} />
            </div>
          </div>
          <span className="text-[9px] font-mono-num text-right">{i.meanAbsShapLogOdds.toFixed(3)}</span>
        </div>
      ))}
    </div>
  );
}

function ContextSection({ quarterId }: { quarterId?: string }) {
  const { data } = useFinalShapContext(quarterId);
  if (!data) return null;
  return (
    <>
      <Collapsible title="Supporting context (not model contributors)">
        <ul className="space-y-1">
          {data.supportingContext.map((c) => (
            <li key={c.indicator} className="text-[10px]"><span className="font-semibold">{c.indicator}</span>: <span className="text-muted-foreground">{c.role}</span></li>
          ))}
        </ul>
      </Collapsible>
      <Collapsible title={`Not used by FINAL (${data.notInModel.length + data.notUsed.length})`}>
        <ul className="space-y-1">
          {data.notInModel.map((c) => (
            <li key={c.name} className="text-[10px]"><span className="font-semibold">{c.name}</span>: <span className="text-muted-foreground">{c.reason}</span></li>
          ))}
          {data.notUsed.map((c) => (
            <li key={c.feature} className="text-[10px] text-muted-foreground">{c.name} ({c.group}): {c.reason}</li>
          ))}
        </ul>
      </Collapsible>
    </>
  );
}

function Collapsible({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="inner-box px-2 py-1.5">
      <button className="w-full flex items-center gap-1 text-[10px] font-semibold text-left" onClick={() => setOpen(!open)} aria-expanded={open}>
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />} {title}
      </button>
      {open && <div className="mt-1">{children}</div>}
    </div>
  );
}
