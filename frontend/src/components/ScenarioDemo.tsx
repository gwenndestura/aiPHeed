// src/components/ScenarioDemo.tsx
// -------------------------------
// Scenario / Demo mode (E178 Part A, docs/e178/PROTOCOL.md): synthetic inputs
// run through the frozen E168 procedure, to show the panel how the system
// responds. Reads only /api/v1/demo/scenarios; it never touches the real
// outlook, and every view carries the SYNTHETIC banner.

import { useMemo, useState } from "react";
import { AlertTriangle, FlaskConical } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useDemoScenario, useDemoScenarios } from "@/lib/queries";
import { SYNTHETIC_LABEL } from "@/lib/demoMode";
import type { DemoRow, DemoS1, DemoS2, DemoS3, DemoS4, DemoS5Row, DemoScenario } from "@/lib/demoTypes";

const TABS = ["S0", "S1", "S2", "S3", "S4", "S5"] as const;
type Tab = (typeof TABS)[number];

const EXPLAIN: Record<Tab, string> = {
  S0: "What happens with the real latest inputs? This is the reference point: the same numbers the public dashboard shows today, recomputed by the frozen E168 procedure.",
  S1: "What happens when one group of inputs moves a little? Each trigger group is moved by one or two standard deviations toward stress (+) or relief (−), one group at a time, and then all groups get random noise together. Small changes in the output mean the forecast is stable.",
  S2: "What happens when data is missing? A random 25 %, 50 % or 75 % of each province's trigger inputs are removed, then all of them, then the latest survey round (ENNS 2021). The model treats a missing input as missing; the table also lists what the system does and does not warn about.",
  S3: "What happens under a severe shock? Inputs move from today's values toward the worst value seen in the historical data (t = 1) and beyond it (t up to 1.5, extrapolated). Each shock is applied alone and then all together, to all five provinces at once.",
  S4: "What does the system do when a province turns HIGH? The first shock that makes a province HIGH is passed through the same alert, explanation, ranking and report code the live system uses. Nothing is written to the database or published.",
  S5: "Which cities and municipalities come out highest in a HIGH province? These are the province's probability re-weighted by poverty and population density: a ranking inside the province, not a municipal forecast.",
};

const GROUP_LABEL: Record<string, string> = {
  weather_farm: "Weather and farm",
  food_prices: "Food prices",
  jobs: "Jobs",
  remittances: "Remittances",
  fish_catch: "Fish catch",
};
const DRIVER_LABEL: Record<string, string> = {
  market: "Market / prices",
  climate: "Climate",
  employment: "Employment",
  ofw_remittance: "OFW remittance",
  fish_kill: "Fish catch",
};
const SHOCK_COLORS = ["#2563eb", "#f59e0b", "#dc2626", "#7c3aed", "#059669", "#0891b2", "#111827"];

const f3 = (x: number | null | undefined) => (x == null ? "–" : x.toFixed(3));
const f1 = (x: number | null | undefined) => (x == null ? "–" : x.toFixed(1));

export function SyntheticBanner({ className = "" }: { className?: string }) {
  return (
    <div
      role="status"
      data-testid="synthetic-banner"
      className={`w-full bg-amber-400 text-black text-center text-[11px] font-extrabold uppercase tracking-[0.18em] py-1.5 px-3 ${className}`}
    >
      {SYNTHETIC_LABEL}
    </div>
  );
}

function Table({ head, rows }: { head: string[]; rows: (string | number | JSX.Element)[][] }) {
  return (
    <div className="overflow-x-auto thin-scrollbar">
      <table className="w-full text-[11px] border-collapse">
        <thead>
          <tr className="text-left text-muted-foreground border-b border-border/50">
            {head.map((h) => (
              <th key={h} className="py-1.5 pr-3 font-semibold whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-border/20">
              {r.map((c, j) => (
                <td key={j} className="py-1 pr-3 whitespace-nowrap tabular-nums">{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ClassTag({ c }: { c: string }) {
  const high = c === "HIGH" || c === "high" || c === "High";
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${high ? "bg-red-600 text-white" : "bg-secondary text-foreground"}`}>
      {high ? "HIGH" : "LOW"}
    </span>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="bg-card/80 border border-border/50 rounded-xl p-4 space-y-3">
      <h3 className="text-[12px] font-bold uppercase tracking-wider">{title}</h3>
      {children}
    </section>
  );
}

function LeadPicker({ lead, setLead }: { lead: number; setLead: (l: number) => void }) {
  return (
    <div className="flex items-center gap-1 text-[11px]" role="group" aria-label="Forecast lead">
      <span className="text-muted-foreground mr-1">Lead</span>
      {[1, 2, 3].map((l) => (
        <button
          key={l}
          onClick={() => setLead(l)}
          aria-pressed={lead === l}
          className={`px-2 py-0.5 rounded border ${lead === l ? "bg-primary text-primary-foreground border-primary" : "border-border/60"}`}
        >
          {l}
        </button>
      ))}
    </div>
  );
}

function S0View({ rows, lead }: { rows: DemoRow[]; lead: number }) {
  const r = rows.filter((x) => x.lead === lead);
  return (
    <>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={r}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="province" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
            <Tooltip />
            <ReferenceLine y={0.5} stroke="#dc2626" strokeDasharray="4 4" label={{ value: "HIGH at 0.50", fontSize: 10 }} />
            <Bar dataKey="probability" name="P(HIGH)">
              {r.map((x) => <Cell key={x.province} fill={x.probability >= 0.5 ? "#dc2626" : "#2563eb"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Table
        head={["Province", "Quarter", "Share food insecure", "90 % range", "P(HIGH)", "Class", "Top drivers"]}
        rows={r.map((x) => [x.province, x.quarter, `${f1(x.score_pct)} %`, `${f1(x.range90_low)}–${f1(x.range90_high)} %`, f3(x.probability), <ClassTag key="c" c={x.class} />, [x.top_driver_1, x.top_driver_2, x.top_driver_3].map((d) => DRIVER_LABEL[d] ?? d).join(", ")])}
      />
    </>
  );
}

function S1View({ d, lead }: { d: DemoS1; lead: number }) {
  const provinces = Array.from(new Set(d.shifts.map((x) => x.province))).sort();
  const groups = Object.keys(GROUP_LABEL);
  const noise = d.noise.filter((x) => x.lead === lead);
  const cell = (p: string, g: string, k: number) => d.shifts.find((x) => x.province === p && x.group === g && x.param === k && x.lead === lead);
  const s0 = (p: string) => noise.find((x) => x.province === p)?.p_s0;
  return (
    <>
      <Table
        head={["Province", "Group", "−2 SD", "−1 SD", "Real", "+1 SD", "+2 SD"]}
        rows={provinces.flatMap((p) => groups.map((g) => [p, GROUP_LABEL[g], f3(cell(p, g, -2)?.probability), f3(cell(p, g, -1)?.probability), f3(s0(p)), f3(cell(p, g, 1)?.probability), f3(cell(p, g, 2)?.probability)]))}
      />
      <p className="text-[11px] text-muted-foreground">P(HIGH) after moving one group; "+" is toward stress. Random noise on all groups together (100 draws):</p>
      <Table
        head={["Province", "Real P(HIGH)", "Noise mean", "5th–95th percentile", "Share food insecure 5th–95th", "Draws HIGH"]}
        rows={noise.map((x) => [x.province, f3(x.p_s0), f3(x.p_mean), `${f3(x.p_p05)}–${f3(x.p_p95)}`, `${f1(x.score_p05)}–${f1(x.score_p95)} %`, `${x.n_high} / 100`])}
      />
    </>
  );
}

function S2View({ d, lead }: { d: DemoS2; lead: number }) {
  const m = d.masks.filter((x) => x.lead === lead);
  const chart = useMemo(() => {
    const ps = Array.from(new Set(m.map((x) => x.province))).sort();
    return ps.map((p) => ({
      province: p,
      real: m.find((x) => x.province === p)?.p_s0,
      ...Object.fromEntries(m.filter((x) => x.province === p).map((x) => [`${Math.round(x.masked_share * 100)} % missing`, x.p_mean])),
    }));
  }, [m]);
  const keys = ["25 % missing", "50 % missing", "75 % missing"];
  return (
    <>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chart}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="province" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            <Bar dataKey="real" name="Real inputs" fill="#111827" />
            {keys.map((k, i) => <Bar key={k} dataKey={k} fill={SHOCK_COLORS[i]} />)}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Table
        head={["Province", "Missing", "P(HIGH) mean (min–max)", "Real P(HIGH)", "90 % range width", "Real width"]}
        rows={m.map((x) => [x.province, `${Math.round(x.masked_share * 100)} %`, `${f3(x.p_mean)} (${f3(x.p_min)}–${f3(x.p_max)})`, f3(x.p_s0), `${f1(x.range90_width_mean)} pts`, `${f1(x.range90_width_s0)} pts`])}
      />
      <p className="text-[11px] font-semibold">Latest survey round (ENNS 2021) missing</p>
      <Table
        head={["Province", "P(HIGH)", "Real P(HIGH)", "90 % range", "Width", "Real width", "Quarters since survey", "Real"]}
        rows={d.latest_missing.filter((x) => x.lead === lead).map((x) => [x.province, f3(x.probability), f3(x.p_s0), `${f1(x.range90_low)}–${f1(x.range90_high)} %`, `${f1(x.range90_width_pts)} pts`, `${f1(x.range90_width_s0)} pts`, x.gap_q, x.gap_q_s0])}
      />
      <ul className="text-[11px] list-disc pl-5 space-y-1">
        {Object.entries(d.what_the_system_warns).map(([k, v]) => <li key={k}>{v}</li>)}
      </ul>
    </>
  );
}

function S3View({ d, lead, shocks }: { d: DemoS3; lead: number; shocks: Record<string, { label: string }> }) {
  const lad = d.ladder.filter((x) => x.lead === lead && x.scenario_id === "S3");
  const ts = Array.from(new Set(lad.map((x) => x.param))).sort((a, b) => a - b);
  const names = Object.keys(shocks);
  const chart = ts.map((t) => ({ t, ...Object.fromEntries(names.map((s) => [s, lad.find((x) => x.shock === s && x.param === t)?.max_p])) }));
  const b = d.ladder.filter((x) => x.lead === lead && x.scenario_id === "S3-B");
  return (
    <>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chart}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="t" tick={{ fontSize: 11 }} label={{ value: "shock intensity t (1 = historical extreme)", fontSize: 10, position: "insideBottom", offset: -2 }} />
            <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            <ReferenceLine y={0.5} stroke="#dc2626" strokeDasharray="4 4" />
            <ReferenceLine x={1} stroke="#6b7280" strokeDasharray="2 2" />
            {names.map((s, i) => <Line key={s} dataKey={s} name={shocks[s].label} stroke={SHOCK_COLORS[i % SHOCK_COLORS.length]} dot={false} strokeWidth={s === "combined" ? 3 : 1.5} />)}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[11px]">
        Highest P(HIGH) among the five provinces. First HIGH: <b>{d.first_high.province}</b> under <b>{d.first_high.variant}</b>
        {d.s3b_used ? " (needed a hypothetical worse survey baseline, S3-B)" : ""}.
      </p>
      <Table
        head={["Shock", "t", "Highest province", "Max P(HIGH)", "HIGH provinces", "Extrapolated"]}
        rows={lad.map((x) => [shocks[x.shock]?.label ?? x.shock, x.param, x.highest_province, f3(x.max_p), x.high_provinces.join(", ") || "–", x.extrapolated ? "yes" : "no"])}
      />
      {b.length > 0 && (
        <Table
          head={["Combined shock + baseline raised by (logit)", "Highest province", "Max P(HIGH)", "HIGH provinces"]}
          rows={b.map((x) => [x.param, x.highest_province, f3(x.max_p), x.high_provinces.join(", ") || "–"])}
        />
      )}
    </>
  );
}

function S4View({ d }: { d: DemoS4 }) {
  const quarters = Object.keys(d.ranking).sort();
  const q = quarters[0];
  return (
    <>
      <p className="text-[11px]">Source: <b>{d.source_variant}</b>. HIGH: {d.high_rows.map((r) => `${r.province} ${r.quarter}`).join(", ") || "none"}.</p>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={d.ranking[q] ?? []}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="province" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
            <Tooltip />
            <ReferenceLine y={0.5} stroke="#dc2626" strokeDasharray="4 4" />
            <Bar dataKey="p_high" name={`P(HIGH) ${q}`}>
              {(d.ranking[q] ?? []).map((x) => <Cell key={x.province} fill={x.p_high >= 0.5 ? "#dc2626" : "#2563eb"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Card title="1. Early-warning alert candidates (staged, not published)">
        <p className="text-[11px] text-muted-foreground">{d.alert_rule}</p>
        <Table head={["Quarter", "Province", "Lead", "P(HIGH)", "Share food insecure"]} rows={d.alerts.map((a) => [a.quarter, a.province_code, a.evidence.lead, f3(a.evidence.p_high), `${f1(a.evidence.score_pct)} %`])} />
      </Card>
      <Card title="2. Admin review flow">
        <ol className="text-[11px] list-decimal pl-5 space-y-1">{d.review_flow.map((s, i) => <li key={i}>{s}</li>)}</ol>
      </Card>
      {d.explanations.map((e) => (
        <Card key={`${e.province}-${e.quarter}`} title={`3. Explanation: ${e.province}, ${e.quarter} (Lead ${e.lead})`}>
          <p className="text-[11px]">{e.statement}</p>
          <Table head={["Driver group", "Contribution (log-odds)", "Direction"]} rows={e.drivers.map((x) => [x.driver_label, x.group_shap.toFixed(4), x.direction.replace("_", " ")])} />
          <ul className="text-[11px] list-disc pl-5 space-y-1">
            {Object.entries(e.plain_evidence).filter(([, v]) => !!v).map(([k, v]) => <li key={k}><b>{DRIVER_LABEL[k] ?? k}:</b> {v}</li>)}
          </ul>
          <p className="text-[10px] text-muted-foreground">{e.evidence_note}</p>
        </Card>
      ))}
      <Card title="4. Report text (as the PDF report would word it)">
        {Object.entries(d.report_text).map(([k, v]) => (
          <div key={k} className="space-y-1">
            <p className="text-[11px] font-semibold">{k}</p>
            {v.map((t, i) => <p key={i} className="text-[11px]">{t}</p>)}
          </div>
        ))}
      </Card>
    </>
  );
}

function S5View({ rows }: { rows: DemoS5Row[] }) {
  return (
    <>
      <p className="text-[11px] text-muted-foreground">{rows[0]?.disaggregation_label}</p>
      <Table
        head={["Province", "Quarter", "Rank", "City / municipality", "Index", "Colour", "Province P(HIGH)", "Poverty %", "Note"]}
        rows={rows.map((r) => [r.province, r.quarter, r.rank_in_province, r.municipality, f3(r.risk_index), r.risk_level, f3(r.province_p_high), r.poverty_rate == null ? "–" : f1(r.poverty_rate), r.note])}
      />
    </>
  );
}

export function ScenarioDemo() {
  const index = useDemoScenarios();
  const [tab, setTab] = useState<Tab>("S0");
  const [lead, setLead] = useState(1);
  const sc = useDemoScenario<unknown>(tab);
  const s: DemoScenario<unknown> | undefined = sc.data;

  return (
    <div className="min-h-full">
      <SyntheticBanner className="sticky top-0 z-10" />
      <div className="px-6 compact:px-4 py-5 space-y-4 max-w-6xl">
        <div className="flex items-start gap-3">
          <FlaskConical className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
          <div>
            <h1 className="text-lg font-bold tracking-tight">Scenario / Demo mode</h1>
            <p className="text-[11px] text-muted-foreground">{index.data?.notice ?? "Synthetic scenarios for presentations."}</p>
            {index.data && (
              <p className="text-[10px] text-muted-foreground mt-1">
                Starts from the approved issue {index.data.production.folder} ({index.data.production.model_id}, data before {index.data.production.cutoff}). The public outlook is unchanged.
              </p>
            )}
          </div>
        </div>
        {index.isError && (
          <div className="flex items-center gap-2 text-[12px] text-red-600"><AlertTriangle className="h-4 w-4" /> Scenario data is not available on this server.</div>
        )}
        <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Scenarios">
          {TABS.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={`px-3 py-1 rounded-md text-[11px] font-semibold border ${tab === t ? "bg-primary text-primary-foreground border-primary" : "border-border/60 hover:bg-secondary"}`}
            >
              {t}
            </button>
          ))}
          {["S0", "S1", "S2", "S3"].includes(tab) && <div className="ml-auto"><LeadPicker lead={lead} setLead={setLead} /></div>}
        </div>
        <Card title={`${tab} · ${s?.title ?? ""}`}>
          <SyntheticBanner className="rounded" />
          <p className="text-[12px]">{EXPLAIN[tab]}</p>
          {sc.isLoading && <p className="text-[11px] text-muted-foreground">Loading…</p>}
          {s && tab === "S0" && <S0View rows={s.data as DemoRow[]} lead={lead} />}
          {s && tab === "S1" && <S1View d={s.data as DemoS1} lead={lead} />}
          {s && tab === "S2" && <S2View d={s.data as DemoS2} lead={lead} />}
          {s && tab === "S3" && <S3View d={s.data as DemoS3} lead={lead} shocks={s.meta.shocks} />}
          {s && tab === "S4" && <S4View d={s.data as DemoS4} />}
          {s && tab === "S5" && <S5View rows={s.data as DemoS5Row[]} />}
        </Card>
      </div>
    </div>
  );
}
