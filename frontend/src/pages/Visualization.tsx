import { useMemo, useRef, useState } from "react";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import { TopNavbar } from "@/components/TopNavbar";
import { toast } from "@/hooks/use-toast";
import { useConfig, useQuarters, useTimeseries, useMunicipalities, useExplainability } from "@/lib/queries";
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
const PROVINCE_COLORS: Record<string, string> = {
  Cavite: "#6366f1",
  Laguna: "#22c55e",
  Batangas: "#f59e0b",
  Rizal: "#06b6d4",
  Quezon: "#ef4444",
};

type Tab = "trend" | "shap";

async function captureChartCanvas(node: HTMLElement) {
  return html2canvas(node, {
    backgroundColor: null,
    scale: 2,
    useCORS: true,
  });
}

function downloadCanvasAsPng(canvas: HTMLCanvasElement, filename: string) {
  const link = document.createElement("a");
  link.download = filename;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

function downloadCanvasAsPdf(canvas: HTMLCanvasElement, filename: string, title: string, subtitle: string) {
  const imgData = canvas.toDataURL("image/png");
  const pdf = new jsPDF({
    orientation: canvas.width >= canvas.height ? "landscape" : "portrait",
    unit: "pt",
    format: "a4",
  });
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const margin = 32;

  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(14);
  pdf.setTextColor(20);
  pdf.text(title, margin, margin);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(9);
  pdf.setTextColor(120);
  pdf.text(subtitle, margin, margin + 14);
  pdf.setTextColor(0);

  const availW = pageW - margin * 2;
  const availH = pageH - margin * 2 - 40;
  const ratio = Math.min(availW / canvas.width, availH / canvas.height);
  const w = canvas.width * ratio;
  const h = canvas.height * ratio;
  const x = margin + (availW - w) / 2;
  const y = margin + 40;
  pdf.addImage(imgData, "PNG", x, y, w, h);
  pdf.save(filename);
}

function useChartExport(chartRef: React.RefObject<HTMLElement>, canExport: boolean) {
  const guard = () => {
    if (!canExport || !chartRef.current) {
      toast({
        title: "No chart to export",
        description: "Generate a chart first.",
        variant: "destructive",
      });
      return null;
    }
    return chartRef.current;
  };

  const downloadPng = async (filename: string) => {
    const node = guard();
    if (!node) return;
    const canvas = await captureChartCanvas(node);
    downloadCanvasAsPng(canvas, filename);
  };

  const downloadPdf = async (filename: string, title: string, subtitle: string) => {
    const node = guard();
    if (!node) return;
    const canvas = await captureChartCanvas(node);
    downloadCanvasAsPdf(canvas, filename, title, subtitle);
  };

  return { downloadPng, downloadPdf };
}

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
              Province Risk Level Trend
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

/* ─── Sub-tab A — Province Risk Level Trend ─── */
function TrendView() {
  const { data: config } = useConfig();
  const { data: quartersRes } = useQuarters("nowcast");
  const QUARTERS = useMemo(() => (quartersRes?.quarters ?? []).map((q) => q.id), [quartersRes]);
  const alertThreshold = config?.thresholds.alertThreshold ?? 0.6;
  const displayCutoff = config?.thresholds.riskDisplayCutoff ?? 0.5;

  const [province, setProvince] = useState<string>("All");
  const [municipality, setMunicipality] = useState<string>("All");
  const [from, setFrom] = useState<string>("");
  const [to, setTo] = useState<string>("");
  const [generated, setGenerated] = useState<{ province: string; municipality: string; from: string; to: string } | null>(null);

  // Keep from/to defaulted to the real range once quarters load.
  useMemo(() => {
    if (!from && QUARTERS.length) setFrom(QUARTERS[0]);
    if (!to && QUARTERS.length) setTo(QUARTERS[QUARTERS.length - 1]);
  }, [QUARTERS, from, to]);

  const provinceId = province !== "All" ? PROVINCE_IDS[province] : null;
  const { data: muniList } = useMunicipalities(provinceId);
  const munisForProvince = useMemo(() => (muniList?.data ?? []).map((m) => m.name), [muniList]);
  const municipalityId = useMemo(
    () => muniList?.data.find((m) => m.name === municipality)?.id ?? null,
    [muniList, municipality]
  );

  const isAllProvinces = !!generated && generated.province === "All";
  const isSingleProvince = !!generated && generated.province !== "All" && generated.municipality === "All";
  const isMuni = !!generated && generated.province !== "All" && generated.municipality !== "All";

  const genFrom = generated?.from;
  const genTo = generated?.to;

  // A fixed-size set of hook calls (React requires hook call count to stay
  // constant): each is enabled only when that mode is the active one.
  const caviteTs = useTimeseries("province", isAllProvinces ? "cavite" : "", genFrom, genTo);
  const lagunaTs = useTimeseries("province", isAllProvinces ? "laguna" : "", genFrom, genTo);
  const batangasTs = useTimeseries("province", isAllProvinces ? "batangas" : "", genFrom, genTo);
  const rizalTs = useTimeseries("province", isAllProvinces ? "rizal" : "", genFrom, genTo);
  const quezonTs = useTimeseries("province", isAllProvinces ? "quezon" : "", genFrom, genTo);
  const allSeries: Record<string, typeof caviteTs.data> = {
    Cavite: caviteTs.data, Laguna: lagunaTs.data, Batangas: batangasTs.data, Rizal: rizalTs.data, Quezon: quezonTs.data,
  };

  const singleProvinceTs = useTimeseries("province", isSingleProvince ? (provinceId ?? "") : "", genFrom, genTo);
  const muniTs = useTimeseries("municipality", isMuni ? (municipalityId ?? "") : "", genFrom, genTo);

  const seriesKeys = isMuni ? [generated!.municipality] : isSingleProvince ? [generated!.province] : isAllProvinces ? PROVINCES : [];

  const data = useMemo(() => {
    if (!generated) return [];
    if (isMuni) {
      return (muniTs?.data?.series ?? []).map((p) => ({ quarter: p.quarter.replace("-", " "), [generated.municipality]: p.riskScore }));
    }
    if (isSingleProvince) {
      return (singleProvinceTs?.data?.series ?? []).map((p) => ({ quarter: p.quarter.replace("-", " "), [generated.province]: p.riskScore }));
    }
    if (isAllProvinces) {
      const merged = new Map<string, Record<string, number | string>>();
      PROVINCES.forEach((p) => {
        (allSeries[p]?.series ?? []).forEach((pt) => {
          const key = pt.quarter.replace("-", " ");
          const row = merged.get(key) ?? { quarter: key };
          row[p] = pt.riskScore;
          merged.set(key, row);
        });
      });
      return Array.from(merged.values());
    }
    return [];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generated, isMuni, isSingleProvince, isAllProvinces, muniTs, singleProvinceTs, caviteTs, lagunaTs, batangasTs, rizalTs, quezonTs]);

  const handleGenerate = () => setGenerated({ province, municipality, from, to });
  const handleClear = () => {
    setProvince("All");
    setMunicipality("All");
    setFrom(QUARTERS[0] ?? "");
    setTo(QUARTERS[QUARTERS.length - 1] ?? "");
    setGenerated(null);
  };

  const chartRef = useRef<HTMLDivElement>(null);
  const hasChart = !!generated && data.length > 0;
  const { downloadPng, downloadPdf } = useChartExport(chartRef, hasChart);

  const trendExplanation = useMemo(() => {
    if (!generated || data.length < 2) return "";
    const first = data[0] as Record<string, number | string>;
    const last = data[data.length - 1] as Record<string, number | string>;
    const range = `${generated.from.replace("-", " ")}–${generated.to.replace("-", " ")}`;
    const parts = seriesKeys.map((k) => {
      const a = Number(first[k] ?? 0);
      const b = Number(last[k] ?? 0);
      const d = b - a;
      const dir = d > 0.005 ? "rose" : d < -0.005 ? "fell" : "held flat";
      return `${k} ${dir} from ${a.toFixed(2)} to ${b.toFixed(2)} (${d >= 0 ? "+" : ""}${d.toFixed(2)})`;
    });
    const endHigh = seriesKeys.filter((k) => Number(last[k] ?? 0) >= displayCutoff);
    const tail =
      endHigh.length === 0
        ? `None end above the ${displayCutoff.toFixed(2)} high-risk line.`
        : `${endHigh.join(", ")} ${endHigh.length === 1 ? "ends" : "end"} above the ${displayCutoff.toFixed(2)} high-risk line${
            seriesKeys.some((k) => Number(last[k] ?? 0) >= alertThreshold)
              ? `, and past the ${alertThreshold.toFixed(2)} alert threshold`
              : ""
          }.`;
    return `Across ${range}, ${parts.join("; ")}. ${tail} Values are AI forecasts recomputed each quarter, not official measurements.`;
  }, [generated, data, seriesKeys, displayCutoff, alertThreshold]);

  const exportLabel = generated
    ? `${generated.province === "All" ? "all-provinces" : generated.province}${
        generated.municipality !== "All" ? `-${generated.municipality}` : ""
      }_${generated.from}_to_${generated.to}`
    : "trend";
  const exportSubtitle = generated
    ? `${generated.province === "All" ? "All provinces" : generated.province}${
        generated.municipality !== "All" ? ` — ${generated.municipality}` : ""
      } · ${generated.from} to ${generated.to}`
    : "";

  const handleDownloadPng = () => downloadPng(`aipheed_trend_${exportLabel}.png`);
  const handleDownloadPdf = () =>
    downloadPdf(
      `aipheed_trend_${exportLabel}.pdf`,
      "Province / Municipality Risk Level Trend",
      exportSubtitle
    );

  return (
    <div>
      <div className="rounded-t-2xl bg-card/80 border border-border/50 px-5 sm:px-6 py-4">
        <h1 className="text-base sm:text-lg font-bold tracking-tight">Province / Municipality Risk Level Trend</h1>
        <p className="text-[11px] text-muted-foreground mt-0.5 uppercase tracking-widest">
          Risk Level time series across selected province, municipality, and quarters
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
          <button
            onClick={handleDownloadPng}
            disabled={!hasChart}
            className="flex items-center gap-2 text-[12px] font-bold uppercase tracking-wider text-risk-low hover:opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:opacity-40"
          >
            <ImageIcon className="h-4 w-4" /> Download PNG
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={!hasChart}
            className="flex items-center gap-2 text-[12px] font-bold uppercase tracking-wider text-risk-high hover:opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:opacity-40"
          >
            <FileText className="h-4 w-4" /> Download PDF
          </button>
        </div>
      </div>

      <div ref={chartRef} className="mt-4 bg-card border border-border/50 rounded-2xl p-4 sm:p-6">
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
                label={{ value: "Risk Level Score", angle: -90, position: "insideLeft", fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  borderRadius: 0,
                  background: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceLine
                y={alertThreshold}
                stroke="hsl(var(--risk-high))"
                strokeDasharray="5 4"
                label={{ value: `Alert Threshold (${alertThreshold.toFixed(2)})`, position: "right", fontSize: 9, fill: "hsl(var(--risk-high))" }}
              />
              <ReferenceLine
                y={displayCutoff}
                stroke="hsl(var(--risk-moderate))"
                strokeDasharray="5 4"
                label={{ value: `High Risk (${displayCutoff.toFixed(2)})`, position: "right", fontSize: 9, fill: "hsl(var(--risk-moderate))" }}
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
        {generated && data.length > 0 && trendExplanation && (
          <div className="mt-4 rounded-xl border border-border/50 bg-secondary/20 px-4 py-3">
            <div className="flex items-center gap-2 mb-1.5">
              <LineIcon className="h-3.5 w-3.5 text-primary" />
              <span className="text-[11px] font-bold uppercase tracking-wider">What this shows</span>
            </div>
            <p className="text-[11px] leading-relaxed text-muted-foreground">{trendExplanation}</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Sub-tab B — Feature Contribution Breakdown ─── */
function ShapView() {
  const { data: config } = useConfig();
  const { data: quartersRes } = useQuarters("nowcast");
  const QUARTERS = useMemo(() => (quartersRes?.quarters ?? []).map((q) => q.id), [quartersRes]);
  const redCutoff = config?.thresholds.triggerRedCutoff ?? 20;

  const [province, setProvince] = useState<string>("Quezon");
  const [quarter, setQuarter] = useState<string>("");
  const [generated, setGenerated] = useState<{ province: string; quarter: string } | null>(null);

  useMemo(() => {
    if (!quarter && quartersRes?.current) setQuarter(quartersRes.current);
  }, [quarter, quartersRes]);

  const { data: explain } = useExplainability(
    "province",
    generated ? PROVINCE_IDS[generated.province] : "",
    generated?.quarter
  );
  const triggers = explain?.triggers ?? [];

  const data = useMemo(
    () =>
      triggers
        .map((t) => ({
          feature: t.label,
          pct: t.pct,
          color: t.color === "red" ? "hsl(var(--risk-high))" : t.color === "green" ? "hsl(var(--risk-low))" : "hsl(var(--risk-moderate))",
        }))
        .sort((a, b) => b.pct - a.pct),
    [triggers]
  );

  const handleGenerate = () => setGenerated({ province, quarter });
  const handleClear = () => {
    setProvince("Quezon");
    setQuarter(quartersRes?.current ?? "");
    setGenerated(null);
  };

  const chartRef = useRef<HTMLDivElement>(null);
  const hasChart = !!generated && data.length > 0;
  const { downloadPng, downloadPdf } = useChartExport(chartRef, hasChart);

  const exportLabel = generated ? `${generated.province}_${generated.quarter}` : "shap";
  const exportSubtitle = generated ? `${generated.province} · ${generated.quarter}` : "";

  const handleDownloadPng = () => downloadPng(`aipheed_shap_${exportLabel}.png`);
  const handleDownloadPdf = () =>
    downloadPdf(`aipheed_shap_${exportLabel}.pdf`, "SHAP Explainability — Driver Groups", exportSubtitle);

  return (
    <div>
      <div className="rounded-t-2xl bg-card/80 border border-border/50 px-5 sm:px-6 py-4">
        <h1 className="text-base sm:text-lg font-bold tracking-tight">SHAP Explainability — Driver Groups</h1>
        <p className="text-[11px] text-muted-foreground mt-0.5 uppercase tracking-widest">
          Per-group contribution to the risk forecast, by province and quarter
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

        <div className="flex items-center justify-between pt-2">
          <button
            onClick={handleDownloadPng}
            disabled={!hasChart}
            className="flex items-center gap-2 text-[12px] font-bold uppercase tracking-wider text-risk-low hover:opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:opacity-40"
          >
            <ImageIcon className="h-4 w-4" /> Download PNG
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={!hasChart}
            className="flex items-center gap-2 text-[12px] font-bold uppercase tracking-wider text-risk-high hover:opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:opacity-40"
          >
            <FileText className="h-4 w-4" /> Download PDF
          </button>
        </div>
      </div>

      <div ref={chartRef} className="mt-4 bg-card border border-border/50 rounded-2xl p-4 sm:p-6">
        {!generated || data.length === 0 ? (
          <div className="h-[360px] flex items-center justify-center text-[12px] text-muted-foreground italic">
            Select a province and quarter to view the trigger contributions.
          </div>
        ) : (
          <>
            <div className="mb-3 flex items-baseline justify-between gap-3 flex-wrap">
              <h2 className="text-[13px] font-bold tracking-tight">
                {generated.province} · {generated.quarter.replace("-", " ")} — trigger contributions
              </h2>
              <span className="text-[10px] text-muted-foreground uppercase tracking-widest">SHAP explainability</span>
            </div>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={data} layout="vertical" margin={{ top: 10, right: 48, left: 20, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border)/.4)" />
                <XAxis
                  type="number"
                  tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                  domain={[0, 50]}
                  tickFormatter={(v: number) => `${v}%`}
                />
                <YAxis
                  type="category"
                  dataKey="feature"
                  tick={{ fontSize: 11, fill: "hsl(var(--foreground))" }}
                  width={120}
                />
                <Tooltip
                  contentStyle={{
                    fontSize: 11,
                    borderRadius: 0,
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                  }}
                  formatter={(v: number) => [`${v}% of total risk`, "Contribution"]}
                />
                <ReferenceLine
                  x={redCutoff}
                  stroke="hsl(var(--risk-high))"
                  strokeDasharray="4 4"
                  label={{ value: `${redCutoff}% even share`, position: "top", fontSize: 8.5, fill: "hsl(var(--risk-high))" }}
                />
                <Bar dataKey="pct" radius={[0, 0, 0, 0]}>
                  {data.map((d, i) => (
                    <Cell key={i} fill={d.color} />
                  ))}
                  <LabelList dataKey="pct" position="right" fontSize={10} fill="hsl(var(--foreground))" formatter={(v: number) => `${v}%`} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>

            <div className="mt-4 rounded-xl border border-border/50 bg-secondary/20 px-4 py-3">
              <div className="flex items-center gap-2 mb-1.5">
                <BarChart3 className="h-3.5 w-3.5 text-primary" />
                <span className="text-[11px] font-bold uppercase tracking-wider">What this shows</span>
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                {explain?.narrative ?? ""}
              </p>
              <div className="mt-2 flex flex-wrap gap-3 text-[9px] uppercase tracking-wider text-muted-foreground">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm" style={{ background: "hsl(var(--risk-high))" }} /> Above {redCutoff}% even share</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm" style={{ background: "hsl(var(--risk-moderate))" }} /> At or below {redCutoff}%</span>
              </div>
            </div>
          </>
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
