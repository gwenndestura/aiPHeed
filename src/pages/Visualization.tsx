import { useMemo, useState } from "react";
import { TopNavbar } from "@/components/TopNavbar";
import {
  PROVINCE_QUARTER_DATA,
  getShapForProvince,
  ALERT_THRESHOLD,
  RISK_DISPLAY_CUTOFF,
} from "@/data/quarterData";
import { municipalitiesByProvince } from "@/data/mockData";
import { X, ImageIcon, FileText, BarChart3, LineChart as LineIcon } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
  LabelList,
  Legend,
  BarChart,
  Bar,
  Cell,
} from "recharts";

const PROVINCES = ["Cavite", "Laguna", "Batangas", "Rizal", "Quezon"];
const PROVINCE_IDS: Record<string, string> = {
  Cavite: "cavite",
  Laguna: "laguna",
  Batangas: "batangas",
  Rizal: "rizal",
  Quezon: "quezon",
};
const QUARTERS = ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2"];
const PROVINCE_COLORS: Record<string, string> = {
  Cavite: "#6366f1",
  Laguna: "#22c55e",
  Batangas: "#f59e0b",
  Rizal: "#06b6d4",
  Quezon: "#ef4444",
};

type Tab = "trend" | "shap";

export default function VisualizationPage() {
  const [tab, setTab] = useState<Tab>("trend");

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden">
      <TopNavbar active="viz" />

      <main className="flex-1 overflow-auto">
        <div className="p-4 sm:p-6 max-w-6xl mx-auto">
          {/* Sub-tabs */}
          <div className="flex items-center gap-2 mb-4">
            <SubTab active={tab === "trend"} onClick={() => setTab("trend")} icon={<LineIcon className="h-3.5 w-3.5" />}>
              Province RFII Trend
            </SubTab>
            <SubTab active={tab === "shap"} onClick={() => setTab("shap")} icon={<BarChart3 className="h-3.5 w-3.5" />}>
              Feature Contribution Breakdown
            </SubTab>
          </div>

          {tab === "trend" ? <TrendView /> : <ShapView />}
        </div>
      </main>
    </div>
  );
}

function SubTab({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-colors ${
        active
          ? "bg-primary text-primary-foreground"
          : "bg-card border border-border/50 text-muted-foreground hover:text-foreground"
      }`}
    >
      {icon}
      {children}
    </button>
  );
}

/* ─── Sub-tab A — Province RFII Trend ─── */
function TrendView() {
  const [province, setProvince] = useState<string>("All");
  const [municipality, setMunicipality] = useState<string>("All");
  const [from, setFrom] = useState<string>(QUARTERS[0]);
  const [to, setTo] = useState<string>(QUARTERS[QUARTERS.length - 1]);
  const [generated, setGenerated] = useState<{ province: string; municipality: string; from: string; to: string } | null>(null);

  // Reset municipality when province changes / not single province
  const munisForProvince = useMemo(() => {
    if (province === "All") return [];
    const id = PROVINCE_IDS[province];
    return id ? municipalitiesByProvince(id).map((m) => m.name) : [];
  }, [province]);

  const provinceList = useMemo(() => (generated ? (generated.province === "All" ? PROVINCES : [generated.province]) : []), [generated]);

  const data = useMemo(() => {
    if (!generated) return [];
    const fromIdx = QUARTERS.indexOf(generated.from);
    const toIdx = QUARTERS.indexOf(generated.to);
    if (fromIdx < 0 || toIdx < 0 || toIdx < fromIdx) return [];
    const range = QUARTERS.slice(fromIdx, toIdx + 1);
    // Municipality view = single series scaled from its province trend (mock derivation)
    const isMuni = generated.province !== "All" && generated.municipality !== "All";
    return range.map((q) => {
      const row: Record<string, number | string> = { quarter: q.replace("-", " ") };
      if (isMuni) {
        const provScore = PROVINCE_QUARTER_DATA.find((r) => r.id === PROVINCE_IDS[generated.province])?.scoresByQuarter[q] ?? 0;
        // Deterministic per-municipality jitter so the chart varies per city
        const seed = generated.municipality.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
        const offset = ((seed % 17) - 8) / 100; // ±0.08
        row[generated.municipality] = Number(Math.max(0, Math.min(1, provScore + offset)).toFixed(2));
      } else {
        provinceList.forEach((p) => {
          const score = PROVINCE_QUARTER_DATA.find((r) => r.id === PROVINCE_IDS[p])?.scoresByQuarter[q] ?? 0;
          row[p] = Number(score.toFixed(2));
        });
      }
      return row;
    });
  }, [generated, provinceList]);

  const seriesKeys = generated && generated.province !== "All" && generated.municipality !== "All"
    ? [generated.municipality]
    : provinceList;

  const handleGenerate = () => setGenerated({ province, municipality, from, to });
  const handleClear = () => {
    setProvince("All");
    setMunicipality("All");
    setFrom(QUARTERS[0]);
    setTo(QUARTERS[QUARTERS.length - 1]);
    setGenerated(null);
  };

  return (
    <div>
      <div className="rounded-t-2xl bg-card/80 border border-border/50 px-5 sm:px-6 py-4">
        <h1 className="text-base sm:text-lg font-bold tracking-tight">Province / Municipality RFII Trend</h1>
        <p className="text-[11px] text-muted-foreground mt-0.5 uppercase tracking-widest">
          RFII time series across selected province, municipality, and quarters
        </p>
      </div>

      <div className="rounded-b-2xl bg-secondary/20 border border-t-0 border-border/50 px-5 sm:px-6 py-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <FloatingSelect
            label="Province"
            value={province}
            onChange={(v) => { setProvince(v); setMunicipality("All"); }}
            options={["All", ...PROVINCES]}
          />
          <FloatingSelect
            label="Municipality / City"
            value={municipality}
            onChange={setMunicipality}
            options={["All", ...munisForProvince]}
          />
          <FloatingSelect label="From" value={from} onChange={setFrom} options={QUARTERS} />
          <FloatingSelect label="To" value={to} onChange={setTo} options={QUARTERS} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={handleGenerate}
            className="h-12 rounded-lg bg-primary text-primary-foreground text-[12px] font-bold uppercase tracking-wider hover:opacity-90 transition-opacity"
          >
            Generate Chart
          </button>
          <button
            onClick={handleClear}
            className="h-12 rounded-lg border border-primary/40 text-primary text-[12px] font-bold uppercase tracking-wider hover:bg-primary/10 transition-colors flex items-center justify-center gap-2"
          >
            <X className="h-3.5 w-3.5" /> Clear Filters
          </button>
        </div>

        <div className="flex items-center justify-between pt-2">
          <button className="flex items-center gap-2 text-[12px] font-bold uppercase tracking-wider text-risk-low hover:opacity-80 transition-opacity">
            <ImageIcon className="h-4 w-4" /> Download PNG
          </button>
          <button className="flex items-center gap-2 text-[12px] font-bold uppercase tracking-wider text-risk-high hover:opacity-80 transition-opacity">
            <FileText className="h-4 w-4" /> Download PDF
          </button>
        </div>
      </div>

      <div className="mt-4 bg-card border border-border/50 rounded-2xl p-4 sm:p-6">
        {!generated || data.length === 0 ? (
          <div className="h-[360px] flex items-center justify-center text-[12px] text-muted-foreground italic">
            Select a province and quarter range to view the trend.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border)/.4)" />
              <XAxis dataKey="quarter" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis
                domain={[0, 1]}
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                label={{ value: "RFII Score", angle: -90, position: "insideLeft", fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  borderRadius: 8,
                  background: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceLine
                y={ALERT_THRESHOLD}
                stroke="hsl(var(--risk-high))"
                strokeDasharray="5 4"
                label={{ value: "Alert Threshold (0.60)", position: "right", fontSize: 9, fill: "hsl(var(--risk-high))" }}
              />
              <ReferenceLine
                y={RISK_DISPLAY_CUTOFF}
                stroke="hsl(var(--risk-moderate))"
                strokeDasharray="5 4"
                label={{ value: "High Risk (0.50)", position: "right", fontSize: 9, fill: "hsl(var(--risk-moderate))" }}
              />
              {seriesKeys.map((p) => (
                <Line
                  key={p}
                  type="monotone"
                  dataKey={p}
                  stroke={PROVINCE_COLORS[p] ?? "hsl(var(--primary))"}
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                >
                  <LabelList dataKey={p} position="top" fontSize={9} fill="hsl(var(--foreground))" />
                </Line>
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

/* ─── Sub-tab B — Feature Contribution Breakdown ─── */
function ShapView() {
  const [province, setProvince] = useState<string>("Quezon");
  const [quarter, setQuarter] = useState<string>("2026-Q2");
  const [generated, setGenerated] = useState<{ province: string; quarter: string } | null>(null);

  const data = useMemo(() => {
    if (!generated) return [];
    const id = PROVINCE_IDS[generated.province];
    const shap = getShapForProvince(id);
    return [...shap].sort((a, b) => b.value - a.value);
  }, [generated]);

  const handleGenerate = () => setGenerated({ province, quarter });
  const handleClear = () => {
    setProvince("Quezon");
    setQuarter("2026-Q2");
    setGenerated(null);
  };

  return (
    <div>
      <div className="rounded-t-2xl bg-card/80 border border-border/50 px-5 sm:px-6 py-4">
        <h1 className="text-base sm:text-lg font-bold tracking-tight">Feature Contribution Breakdown</h1>
        <p className="text-[11px] text-muted-foreground mt-0.5 uppercase tracking-widest">
          SHAP values by province and quarter
        </p>
      </div>

      <div className="rounded-b-2xl bg-secondary/20 border border-t-0 border-border/50 px-5 sm:px-6 py-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FloatingSelect label="Province" value={province} onChange={setProvince} options={PROVINCES} />
          <FloatingSelect label="Quarter" value={quarter} onChange={setQuarter} options={QUARTERS} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={handleGenerate}
            className="h-12 rounded-lg bg-primary text-primary-foreground text-[12px] font-bold uppercase tracking-wider hover:opacity-90 transition-opacity"
          >
            Generate Chart
          </button>
          <button
            onClick={handleClear}
            className="h-12 rounded-lg border border-primary/40 text-primary text-[12px] font-bold uppercase tracking-wider hover:bg-primary/10 transition-colors flex items-center justify-center gap-2"
          >
            <X className="h-3.5 w-3.5" /> Clear Filters
          </button>
        </div>
      </div>

      <div className="mt-4 bg-card border border-border/50 rounded-2xl p-4 sm:p-6">
        {!generated || data.length === 0 ? (
          <div className="h-[360px] flex items-center justify-center text-[12px] text-muted-foreground italic">
            Select a province and quarter to view feature contributions.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={data} layout="vertical" margin={{ top: 10, right: 40, left: 80, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border)/.4)" />
              <XAxis
                type="number"
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                domain={[-0.25, 0.25]}
              />
              <YAxis
                type="category"
                dataKey="feature"
                tick={{ fontSize: 11, fill: "hsl(var(--foreground))" }}
                width={140}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  borderRadius: 8,
                  background: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                }}
                formatter={(v: number) => [v.toFixed(3), "SHAP"]}
              />
              <ReferenceLine x={0} stroke="hsl(var(--border))" strokeWidth={1.5} label={{ value: "Baseline", position: "top", fontSize: 9, fill: "hsl(var(--muted-foreground))" }} />
              <Bar dataKey="value" radius={[3, 3, 3, 3]}>
                {data.map((d, i) => (
                  <Cell key={i} fill={d.value >= 0 ? "hsl(var(--risk-high))" : "hsl(var(--risk-low))"} />
                ))}
                <LabelList dataKey="value" position="right" fontSize={10} fill="hsl(var(--foreground))" formatter={(v: number) => (v >= 0 ? `+${v.toFixed(3)}` : v.toFixed(3))} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

function FloatingSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="relative block">
      <span className="absolute -top-2 left-3 px-1 bg-background text-[10px] uppercase tracking-wider text-muted-foreground/80">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-12 rounded-lg bg-card border border-border/50 px-3 text-[12px] font-medium focus:outline-none focus:border-primary/60 transition-colors"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}
