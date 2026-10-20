import { useEffect, useMemo, useRef, useState } from "react";
import { TopNavbar } from "@/components/TopNavbar";
import { VizTour } from "@/components/PageTours";
import { TOUR_LAYOUT_EVENT, type TourLayout } from "@/lib/tour";
import { toast } from "@/hooks/use-toast";
import { useConfig, useQuarters, useTimeseries, useMunicipalities, useExplainability } from "@/lib/queries";
import { selectableQuarters } from "@/lib/quarters";
import type { QuartersResponse } from "@/lib/apiTypes";
import { api, ApiError } from "@/lib/api";
import { captureLightFigure, renderReportPdf, toAscii, type ReportPayload } from "@/lib/chartReport";
import { X, ImageIcon, FileText } from "lucide-react";
import { isLoadFailure, LOAD_ERROR_MESSAGE } from "@/lib/loadError";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { COMPACT_QUERY } from "@/lib/breakpoints";
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

// Room right of the trend plot for "Alert Threshold (0.60)" at 9px.
const THRESHOLD_LABEL_W = 124;

type QuarterOption = { value: string; label: string };

/** "2027-Q1" -> "Q1 2027 (forecast)". */
function forecastQuarterLabel(id: string): string {
  const m = id.match(/^(\d{4})-Q([1-4])$/);
  return m ? `Q${m[2]} ${m[1]} (forecast)` : `${id} (forecast)`;
}

/**
 * The quarters the report selectors offer: the map's selectable quarters that
 * have a score (observed, current or forecast), so the lists end at the same
 * quarter as the map. Quarters with no score ("unavailable") are left out.
 * Forecast quarters are labelled "Q1 2027 (forecast)".
 */
function reportQuarterOptions(res?: Pick<QuartersResponse, "quarters" | "calendarQuarter">): QuarterOption[] {
  return selectableQuarters(res?.quarters ?? [], res?.calendarQuarter)
    .filter((q) => q.state === "actual" || q.state === "current" || q.state === "forecast")
    .map((q) => ({ value: q.id, label: q.state === "forecast" ? forecastQuarterLabel(q.id) : q.id }));
}

/** The dataKey of a series' dashed forecast segment, and of its forecast-only value labels. */
const forecastKey = (k: string) => `${k}__forecast`;
const forecastLabelKey = (k: string) => `${k}__forecastLabel`;
type TrendRow = Record<string, number | string | boolean>;

/**
 * Splits each series into an observed part (solid) and a forecast part
 * (dashed). The forecast part starts at the last observed point so the two
 * segments join; the forecast value labels skip that shared point.
 */
function splitForecast(rows: TrendRow[], keys: string[]): TrendRow[] {
  const firstForecast = rows.findIndex((r) => r.forecast === true);
  return rows.map((r, i) => {
    const out: TrendRow = { ...r };
    for (const k of keys) {
      const v = r[k];
      if (typeof v !== "number") continue;
      if (r.forecast === true) {
        delete out[k];
        out[forecastKey(k)] = v;
        out[forecastLabelKey(k)] = v;
      } else if (firstForecast > 0 && i === firstForecast - 1) {
        out[forecastKey(k)] = v;
      }
    }
    return out;
  });
}

/** The map timeline's key: a solid line for observed quarters, a dashed one for forecast quarters. */
function ObservedForecastKey() {
  return (
    <div data-testid="trend-key" className="qt-muted mt-2 flex items-center justify-center gap-4 text-[10px] leading-[14px]">
      <span className="flex items-center gap-1.5">
        <span aria-hidden className="qt-key qt-line-observed" />
        Observed
      </span>
      <span className="flex items-center gap-1.5">
        <span aria-hidden className="qt-key qt-line-forecast" />
        Forecast
      </span>
    </div>
  );
}

/**
 * Chart text size: the desktop size, and at least 12px on phones (the chart
 * text is drawn by Recharts, so the page's CSS rule cannot reach it).
 */
function useChartFont() {
  const compact = useMediaQuery(COMPACT_QUERY);
  return { compact, fs: (desktop: number) => (compact ? Math.max(12, desktop) : desktop) };
}

function downloadCanvasAsPng(canvas: HTMLCanvasElement, filename: string) {
  const link = document.createElement("a");
  link.download = filename;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

// The PNG is `pngRef` -- the chart and its colour legend, nothing else --
// captured in the light theme on white. The PDF is the formal report the
// backend composes at /api/v1/report/data, laid out by renderReportPdf(); the
// page supplies only the selection, never any of the report's content.
function useChartExport(pngRef: React.RefObject<HTMLElement>, canExport: boolean) {
  const [pdfBusy, setPdfBusy] = useState(false);
  const guard = (ref: React.RefObject<HTMLElement>) => {
    if (!canExport || !ref.current) {
      toast({
        title: "No chart to export",
        description: "Generate a chart first.",
        variant: "destructive",
      });
      return null;
    }
    return ref.current;
  };

  const downloadPng = async (filename: string) => {
    const node = guard(pngRef);
    if (!node) return;
    const canvas = await captureLightFigure(node);
    downloadCanvasAsPng(canvas, filename);
  };

  const downloadPdf = async (params: Record<string, string | undefined>, filename: string) => {
    if (!guard(pngRef) || pdfBusy) return;
    setPdfBusy(true);
    try {
      const report = await api.get<ReportPayload>("/api/v1/report/data", params, { auth: false });
      renderReportPdf(report).save(filename);
    } catch (err) {
      toast({
        title: "Report could not be generated",
        description: err instanceof ApiError ? err.message : "The report service did not respond.",
        variant: "destructive",
      });
    } finally {
      setPdfBusy(false);
    }
  };

  return { downloadPng, downloadPdf, pdfBusy };
}

export default function VisualizationPage() {
  const [tab, setTab] = useState<Tab>("trend");

  // The guided tour (VizTour) explains the trend tab.
  useEffect(() => {
    const onTourLayout = (e: Event) => {
      const { vizTab } = (e as CustomEvent<TourLayout>).detail;
      if (vizTab) setTab(vizTab);
    };
    window.addEventListener(TOUR_LAYOUT_EVENT, onTourLayout);
    return () => window.removeEventListener(TOUR_LAYOUT_EVENT, onTourLayout);
  }, []);

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden">
      <TopNavbar active="viz" />

      <main className="flex-1 overflow-auto">
        <div className="p-4 sm:p-6 max-w-6xl mx-auto">
          {/* Sub-tabs */}
          <div className="flex items-center gap-2 mb-4" data-tour="viz-tabs">
            <SubTab active={tab === "trend"} onClick={() => setTab("trend")}>
              Province Risk Level Trend
            </SubTab>
            <SubTab active={tab === "shap"} onClick={() => setTab("shap")}>
              Feature Contribution Breakdown
            </SubTab>
          </div>

          {tab === "trend" ? <TrendView /> : <ShapView />}
        </div>
      </main>
      {/* First-visit guide for public visitors (also "Take the tour" in the menu). */}
      <VizTour />
    </div>
  );
}

function SubTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center px-3 py-2 compact:min-h-11 seg-option text-[11px] font-bold transition-colors ${
        active ? "seg-on" : "border text-muted-foreground hover:text-foreground"
      }`}
    >
      {children}
    </button>
  );
}

/* ─── Sub-tab A — Province Risk Level Trend ─── */
function TrendView() {
  const { data: config } = useConfig();
  const { compact, fs } = useChartFont();
  const { data: quartersRes, error: quartersError } = useQuarters("nowcast");
  // The same quarters as the map, forecast ones included (see reportQuarterOptions).
  const quarterOptions = useMemo(() => reportQuarterOptions(quartersRes), [quartersRes]);
  const QUARTERS = useMemo(() => quarterOptions.map((q) => q.value), [quarterOptions]);
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

  // A failed fetch is not "nothing selected": say so in the chart area.
  const loadFailed = [quartersError, caviteTs.error, lagunaTs.error, batangasTs.error, rizalTs.error,
    quezonTs.error, singleProvinceTs.error, muniTs.error].some(isLoadFailure);

  const seriesKeys = isMuni ? [generated!.municipality] : isSingleProvince ? [generated!.province] : isAllProvinces ? PROVINCES : [];

  const data = useMemo(() => {
    if (!generated) return [];
    // A point is a forecast when the series says so (isForecast) or the quarter list marks it "forecast".
    const forecastIds = new Set((quartersRes?.quarters ?? []).filter((q) => q.state === "forecast").map((q) => q.id));
    const isForecast = (pt: { quarter: string; isForecast?: boolean }) => pt.isForecast === true || forecastIds.has(pt.quarter);
    let rows: TrendRow[] = [];
    if (isMuni) {
      rows = (muniTs?.data?.series ?? []).map((p) => ({ quarter: p.quarter.replace("-", " "), forecast: isForecast(p), [generated.municipality]: p.riskScore }));
    } else if (isSingleProvince) {
      rows = (singleProvinceTs?.data?.series ?? []).map((p) => ({ quarter: p.quarter.replace("-", " "), forecast: isForecast(p), [generated.province]: p.riskScore }));
    } else if (isAllProvinces) {
      const merged = new Map<string, TrendRow>();
      PROVINCES.forEach((p) => {
        (allSeries[p]?.series ?? []).forEach((pt) => {
          const key = pt.quarter.replace("-", " ");
          const row = merged.get(key) ?? { quarter: key, forecast: false };
          row[p] = pt.riskScore;
          if (isForecast(pt)) row.forecast = true;
          merged.set(key, row);
        });
      });
      rows = Array.from(merged.values());
    }
    return splitForecast(rows, seriesKeys);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generated, isMuni, isSingleProvince, isAllProvinces, muniTs, singleProvinceTs, caviteTs, lagunaTs, batangasTs, rizalTs, quezonTs, quartersRes]);

  const handleGenerate = () => setGenerated({ province, municipality, from, to });

  // The tour's chart step draws the chart for the current choices if there is none yet.
  const tourGenerate = useRef<() => void>();
  tourGenerate.current = () => {
    if (!generated && from && to) handleGenerate();
  };
  useEffect(() => {
    const onTourLayout = (e: Event) => {
      if ((e as CustomEvent<TourLayout>).detail.generate) tourGenerate.current?.();
    };
    window.addEventListener(TOUR_LAYOUT_EVENT, onTourLayout);
    return () => window.removeEventListener(TOUR_LAYOUT_EVENT, onTourLayout);
  }, []);

  const handleClear = () => {
    setProvince("All");
    setMunicipality("All");
    setFrom(QUARTERS[0] ?? "");
    setTo(QUARTERS[QUARTERS.length - 1] ?? "");
    setGenerated(null);
  };

  // The trend chart's legend is part of the Recharts figure, so the PNG and
  // the PDF figure capture the same node.
  const figureRef = useRef<HTMLDivElement>(null);
  const hasChart = !loadFailed && !!generated && data.length > 0;
  const { downloadPng, downloadPdf, pdfBusy } = useChartExport(figureRef, hasChart);


  const exportLabel = generated
    ? `${generated.province === "All" ? "all-provinces" : generated.province}${
        generated.municipality !== "All" ? `-${generated.municipality}` : ""
      }_${generated.from}_to_${generated.to}`
    : "trend";
  const handleDownloadPng = () => downloadPng(`aipheed_trend_${exportLabel}.png`);
  const handleDownloadPdf = () => {
    if (!generated) return;
    const allProvinces = generated.province === "All";
    const muniId =
      !allProvinces && generated.municipality !== "All"
        ? muniList?.data.find((m) => m.name === generated.municipality)?.id
        : undefined;
    return downloadPdf(
      {
        type: "trend",
        scope: allProvinces ? "region" : "province",
        id: allProvinces ? undefined : PROVINCE_IDS[generated.province],
        from: generated.from,
        to: generated.to,
        municipality: muniId,
      },
      `aipheed_trend_${toAscii(exportLabel)}.pdf`
    );
  };

  return (
    <div>
      <div className="rounded-t-xl bg-card/80 border edge-faint px-5 sm:px-6 py-4">
        <h1 className="text-base sm:text-lg font-bold tracking-tight">Province / Municipality Risk Level Trend</h1>
        <p className="text-[11px] text-muted-foreground mt-0.5 compact:text-[14px]">
          Risk Level time series across selected province, municipality, and quarters
        </p>
      </div>

      <div className="rounded-b-xl bg-secondary/20 border border-t-0 edge-faint px-5 sm:px-6 py-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" data-tour="viz-filters">
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
          <FloatingSelect label="From" value={from} onChange={setFrom} options={quarterOptions} />
          <FloatingSelect label="To" value={to} onChange={setTo} options={quarterOptions} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-tour="viz-generate">
          <button
            onClick={handleGenerate}
            className="h-12 rounded-lg bg-primary text-primary-foreground text-[12px] font-bold hover:opacity-90 transition-opacity"
          >
            Generate Chart
          </button>
          <button
            onClick={handleClear}
            className="h-12 rounded-lg border border-primary/40 text-primary text-[12px] font-bold hover:bg-primary/10 transition-colors flex items-center justify-center gap-2"
          >
            <X className="h-3.5 w-3.5" /> Clear Filters
          </button>
        </div>

        <div className="flex items-center justify-between pt-2" data-tour="viz-download">
          <button
            onClick={handleDownloadPng}
            disabled={!hasChart}
            className="flex items-center gap-2 compact:min-h-11 text-[12px] font-bold text-risk-low hover:opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:opacity-40"
          >
            <ImageIcon className="h-4 w-4" /> Download PNG
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={!hasChart || pdfBusy}
            className="flex items-center gap-2 compact:min-h-11 text-[12px] font-bold text-risk-high hover:opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:opacity-40"
          >
            <FileText className="h-4 w-4" /> {pdfBusy ? "Preparing PDF..." : "Download PDF"}
          </button>
        </div>
      </div>

      <div className="mt-4 bg-card border edge-faint rounded-xl shadow-lg p-4 sm:p-6" data-tour="viz-chart">
        {loadFailed ? (
          <div className="h-[360px] flex items-center justify-center text-[12px] text-muted-foreground italic">
            {LOAD_ERROR_MESSAGE}
          </div>
        ) : !generated || data.length === 0 ? (
          <div className="h-[360px] flex items-center justify-center text-[12px] text-muted-foreground italic">
            Select a province and quarter range to view the trend.
          </div>
        ) : (
          <div ref={figureRef}>
          <ResponsiveContainer width="100%" height={400}>
            {/* The right margin holds the threshold labels, drawn beside the
                plot at the end of each reference line. Phones have no room for
                it: the labels sit inside the plot, above their lines. */}
            <LineChart data={data} margin={{ top: 20, right: compact ? 12 : THRESHOLD_LABEL_W, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border)/.4)" />
              <XAxis dataKey="quarter" tick={{ fontSize: fs(10), fill: "hsl(var(--muted-foreground))" }} />
              <YAxis
                domain={[0, 1]}
                tick={{ fontSize: fs(10), fill: "hsl(var(--muted-foreground))" }}
                label={{ value: "Risk Level Score", angle: -90, position: "insideLeft", fontSize: fs(10), fill: "hsl(var(--muted-foreground))" }}
              />
              <Tooltip
                contentStyle={{
                  fontSize: fs(11),
                  borderRadius: 0,
                  background: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                }}
                payloadUniqBy={(entry) => String(entry.name)}
                labelFormatter={(label: string) => (data.find((r) => r.quarter === label)?.forecast === true ? `${label} (forecast)` : label)}
              />
              <Legend wrapperStyle={{ fontSize: fs(11) }} />
              <ReferenceLine
                y={alertThreshold}
                stroke="hsl(var(--risk-high))"
                strokeDasharray="5 4"
                label={{ value: `Alert Threshold (${alertThreshold.toFixed(2)})`, position: compact ? "insideTopRight" : "right", fontSize: fs(9), fill: "hsl(var(--risk-high))" }}
              />
              <ReferenceLine
                y={displayCutoff}
                stroke="hsl(var(--risk-moderate))"
                strokeDasharray="5 4"
                label={{ value: `High Risk (${displayCutoff.toFixed(2)})`, position: compact ? "insideBottomRight" : "right", fontSize: fs(9), fill: "hsl(var(--risk-moderate))" }}
              />
              {/* Observed quarters: a solid line. Phones: value labels only for a
                  single line; with five they overlap. Every value is in the
                  tooltip (tap a point). */}
              {seriesKeys.map((p) => (
                <Line
                  key={p}
                  name={p}
                  type="monotone"
                  dataKey={p}
                  stroke={PROVINCE_COLORS[p] ?? "hsl(var(--primary))"}
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  connectNulls={false}
                >
                  {(!compact || seriesKeys.length === 1) && (
                    <LabelList dataKey={p} position="top" fontSize={fs(9)} fill="hsl(var(--foreground))" />
                  )}
                </Line>
              ))}
              {/* Forecast quarters: the same colour, dashed, as on the map timeline. */}
              {seriesKeys.map((p) => (
                <Line
                  key={forecastKey(p)}
                  name={p}
                  legendType="none"
                  type="monotone"
                  dataKey={forecastKey(p)}
                  stroke={PROVINCE_COLORS[p] ?? "hsl(var(--primary))"}
                  strokeWidth={2.5}
                  strokeDasharray="6 5"
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  connectNulls={false}
                >
                  {(!compact || seriesKeys.length === 1) && (
                    <LabelList dataKey={forecastLabelKey(p)} position="top" fontSize={fs(9)} fill="hsl(var(--foreground))" />
                  )}
                </Line>
              ))}
            </LineChart>
          </ResponsiveContainer>
          <ObservedForecastKey />
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Sub-tab B — Feature Contribution Breakdown ─── */
function ShapView() {
  const { fs } = useChartFont();
  const { data: config } = useConfig();
  const { data: quartersRes, error: quartersError } = useQuarters("nowcast");
  // The same quarters as the map, forecast ones included (see reportQuarterOptions).
  const quarterOptions = useMemo(() => reportQuarterOptions(quartersRes), [quartersRes]);
  const redCutoff = config?.thresholds.triggerRedCutoff ?? 20;

  const [province, setProvince] = useState<string>("Quezon");
  const [quarter, setQuarter] = useState<string>("");
  const [generated, setGenerated] = useState<{ province: string; quarter: string } | null>(null);

  // Default: the quarter the map opens on (quartersRes.current).
  useMemo(() => {
    if (!quarter && quartersRes?.current) setQuarter(quartersRes.current);
  }, [quarter, quartersRes]);

  const { data: explain, error: explainError } = useExplainability(
    "province",
    generated ? PROVINCE_IDS[generated.province] : "",
    generated?.quarter
  );
  const triggers = explain?.triggers ?? [];
  const loadFailed = isLoadFailure(quartersError) || isLoadFailure(explainError);

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

  const pngRef = useRef<HTMLDivElement>(null);
  const hasChart = !loadFailed && !!generated && data.length > 0;
  const { downloadPng, downloadPdf, pdfBusy } = useChartExport(pngRef, hasChart);

  const exportLabel = generated ? `${generated.province}_${generated.quarter}` : "shap";

  const handleDownloadPng = () => downloadPng(`aipheed_shap_${exportLabel}.png`);
  const handleDownloadPdf = () => {
    if (!generated) return;
    return downloadPdf(
      { type: "shap", scope: "province", id: PROVINCE_IDS[generated.province], to: generated.quarter },
      `aipheed_shap_${exportLabel}.pdf`
    );
  };

  return (
    <div>
      <div className="rounded-t-xl bg-card/80 border edge-faint px-5 sm:px-6 py-4">
        <h1 className="text-base sm:text-lg font-bold tracking-tight">SHAP Explainability — Driver Groups</h1>
        <p className="text-[11px] text-muted-foreground mt-0.5 compact:text-[14px]">
          Per-group contribution to the risk forecast, by province and quarter
        </p>
      </div>

      <div className="rounded-b-xl bg-secondary/20 border border-t-0 edge-faint px-5 sm:px-6 py-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FloatingSelect label="Province" value={province} onChange={setProvince} options={PROVINCES} />
          <FloatingSelect label="Quarter" value={quarter} onChange={setQuarter} options={quarterOptions} />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={handleGenerate}
            className="h-12 rounded-lg bg-primary text-primary-foreground text-[12px] font-bold hover:opacity-90 transition-opacity"
          >
            Generate Chart
          </button>
          <button
            onClick={handleClear}
            className="h-12 rounded-lg border border-primary/40 text-primary text-[12px] font-bold hover:bg-primary/10 transition-colors flex items-center justify-center gap-2"
          >
            <X className="h-3.5 w-3.5" /> Clear Filters
          </button>
        </div>

        <div className="flex items-center justify-between pt-2">
          <button
            onClick={handleDownloadPng}
            disabled={!hasChart}
            className="flex items-center gap-2 compact:min-h-11 text-[12px] font-bold text-risk-low hover:opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:opacity-40"
          >
            <ImageIcon className="h-4 w-4" /> Download PNG
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={!hasChart || pdfBusy}
            className="flex items-center gap-2 compact:min-h-11 text-[12px] font-bold text-risk-high hover:opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:opacity-40"
          >
            <FileText className="h-4 w-4" /> {pdfBusy ? "Preparing PDF..." : "Download PDF"}
          </button>
        </div>
      </div>

      <div className="mt-4 bg-card border edge-faint rounded-xl shadow-lg p-4 sm:p-6">
        {loadFailed ? (
          <div className="h-[360px] flex items-center justify-center text-[12px] text-muted-foreground italic">
            {LOAD_ERROR_MESSAGE}
          </div>
        ) : !generated || data.length === 0 ? (
          <div className="h-[360px] flex items-center justify-center text-[12px] text-muted-foreground italic">
            Select a province and quarter to view the trigger contributions.
          </div>
        ) : (
          <>
            <div className="mb-3 flex items-baseline justify-between gap-3 flex-wrap">
              <h2 className="text-[13px] font-bold tracking-tight">
                {generated.province} · {quarterOptions.find((q) => q.value === generated.quarter)?.label.includes("(forecast)")
                  ? forecastQuarterLabel(generated.quarter)
                  : generated.quarter.replace("-", " ")} — trigger contributions
              </h2>
              <span className="text-[10px] text-muted-foreground">SHAP explainability</span>
            </div>
            <div ref={pngRef}>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={data} layout="vertical" margin={{ top: 10, right: 48, left: 20, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border)/.4)" />
                <XAxis
                  type="number"
                  tick={{ fontSize: fs(10), fill: "hsl(var(--muted-foreground))" }}
                  domain={[0, 50]}
                  tickFormatter={(v: number) => `${v}%`}
                />
                <YAxis
                  type="category"
                  dataKey="feature"
                  tick={{ fontSize: fs(11), fill: "hsl(var(--foreground))" }}
                  width={120}
                />
                <Tooltip
                  contentStyle={{
                    fontSize: fs(11),
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
                  label={{ value: `${redCutoff}% even share`, position: "top", fontSize: fs(8.5), fill: "hsl(var(--risk-high))" }}
                />
                <Bar dataKey="pct" radius={[0, 0, 0, 0]}>
                  {data.map((d, i) => (
                    <Cell key={i} fill={d.color} />
                  ))}
                  <LabelList dataKey="pct" position="right" fontSize={fs(10)} fill="hsl(var(--foreground))" formatter={(v: number) => `${v}%`} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>

            {/* Colour key only. The written SHAP interpretation is in the PDF report. */}
            <div className="mt-3 flex flex-wrap justify-center gap-4 text-[9px] text-muted-foreground">
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
  /** Plain values, or { value, label } when the shown text differs (e.g. "Q1 2027 (forecast)"). */
  options: (string | QuarterOption)[];
}) {
  return (
    <label className="block">
      <span className="block mb-1.5 text-[11px] font-medium text-muted-foreground">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-12 rounded-lg bg-card border border-border/50 px-3 text-[12px] font-medium focus:outline-none focus:border-primary/60 transition-colors"
      >
        {options.map((o) => {
          const { value: v, label: l } = typeof o === "string" ? { value: o, label: o } : o;
          return (
            <option key={v} value={v}>
              {l}
            </option>
          );
        })}
      </select>
    </label>
  );
}
