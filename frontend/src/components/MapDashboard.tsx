import { useEffect, useLayoutEffect, useRef, useState, useMemo, useCallback } from "react";
import { ChevronLeft, ChevronRight, ChevronUp, PanelLeft, PanelRight, PanelsTopLeft, PanelsRightBottom } from "lucide-react";
import { FilterState, RegionData, MunicipalityData } from "@/data/types";
import { provinceToRegion, municipalityToData, apiQuarterToSlider } from "@/lib/adapters";
import { useQuarters, useProvinces, useMunicipalities, useRejections, useForecast } from "@/lib/queries";
import { quarterPeriodLabel, selectableQuarters, timelineWindow } from "@/lib/quarters";
import { PhilippineMap } from "@/components/PhilippineMap";
import { LeftPanel, RfiiScoreCardBody, RiskDriversCardBody, ProvinceRankingCardBody } from "@/components/LeftPanel";
import {
  ShapNarrativeCardBody,
  NewsArticlesCardBody,
} from "@/components/RightAnalyticsPanel";
import { QuarterTimeSlider } from "@/components/QuarterTimeSlider";
import { ForecastHistoryModal } from "@/components/ForecastHistoryModal";
import { RegionMetadataPopup } from "@/components/RegionMetadataPopup";
import { MapLegend } from "@/components/MapLegend";
import { MapControls } from "@/components/MapControls";
import { MapBottomSheet, SHEET_PEEK_H, type SheetSnap } from "@/components/MapBottomSheet";
import { AboutModal } from "@/components/AboutModal";
import { FeedbackModal } from "@/components/FeedbackModal";
import { MapSearch } from "@/components/MapSearch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/ui/status-badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { COMPACT_QUERY, MEDIUM_QUERY } from "@/lib/breakpoints";
import { isLoadFailure } from "@/lib/loadError";
import { isHighRisk } from "@/lib/risk";
import { TOUR_LAYOUT_EVENT, type TourLayout } from "@/lib/tour";
import { readStorage, removeStorage } from "@/lib/storage";

/** A card in a side column: its own floating card, with its own soft shadow. */
function PanelCard({ children, className = "", tour }: { children: React.ReactNode; className?: string; tour?: string }) {
  return (
    <div data-tour={tour} className={`px-4 py-3.5 surface-card text-card-foreground ${className}`}>
      {children}
    </div>
  );
}

/**
 * A closed side panel: a small floating tab, inset from the screen edge and
 * centred on the map, its arrow pointing the way the panel opens; its name
 * is in the label and, on hover, a tooltip. On tablets opening it closes the
 * other panel. 32px wide; its tap area reaches 44px on touch screens.
 */
function PanelTab({ side, label, onClick }: { side: "left" | "right"; label: string; onClick: () => void }) {
  const name = `Show the ${label} panel`;
  const Icon = side === "left" ? ChevronRight : ChevronLeft;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={onClick}
          aria-label={name}
          className="absolute z-[1001] top-1/2 -translate-y-1/2 flex items-center justify-center surface-float rounded-md border text-foreground hover:bg-secondary/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring touch-target-x"
          style={{ [side]: EDGE, width: TAB_W, height: TAB_H }}
        >
          <Icon aria-hidden className="h-5 w-5" />
        </button>
      </TooltipTrigger>
      <TooltipContent side={side === "left" ? "right" : "left"}>{name}</TooltipContent>
    </Tooltip>
  );
}

/** A card inside the phone sheet, which already has the blur and shadow. */
function SheetCard({ children, className = "", tour }: { children: React.ReactNode; className?: string; tour?: string }) {
  return <div data-tour={tour} className={`px-4 py-3.5 inner-card ${className}`}>{children}</div>;
}

function NoDataCardBody({ reason }: { reason?: string }) {
  return (
    <div className="py-8 text-center space-y-2">
      <p className="text-[11px] font-semibold text-muted-foreground">No data</p>
      {reason && <p className="text-[10px] text-muted-foreground/60 leading-snug px-2">{reason}</p>}
    </div>
  );
}

// Side panels: inset EDGE (below) from the screen edges and the header.
const COL_W = 320;
const COL_TOP = 12;
const COL_BOTTOM = 64;
// A closed panel's tab.
const TAB_W = 32;
const TAB_H = 64;

// Phone layout: the search box across the top, the legend under it, the
// sheet at the bottom with the quarter strip and zoom buttons just above it.
const EDGE = 12;
const SEARCH_H = 44;
const SHEET_TOP_RESERVE = EDGE + SEARCH_H + 8;
const ROW_H = 44;
const LEGEND_STACK_H = 52;
// Map left visible between the search box and the quarter strip when the
// sheet is open; with less, the strip steps aside (phones held sideways).
// With the sheet collapsed it always shows: it is the way to change quarter.
const MIN_MAP_H = 96;
// Phones held sideways: wide enough for the legend beside the search box.
const WIDE_COMPACT_W = 600;
const SEARCH_MAX_W = 420;
// Room kept for the compact legend beside the search box (about 285px with
// Low / High / No forecast, plus a gap).
const LEGEND_BESIDE_W = 300;
// Tablets and desktops: the search box's height and the map buttons' width.
const DESKTOP_SEARCH_H = 28;
const CONTROLS_W = 32;

interface Props {
  showAboutFeedback?: boolean;
}

export function MapDashboard({ showAboutFeedback = true }: Props) {
  const [filters] = useState<FilterState>({ year: 2024, riskLevel: "all", region: "all" });
  const [selectedRegion, setSelectedRegion] = useState<RegionData | null>(null);
  const [previewRegion, setPreviewRegion] = useState<RegionData | null>(null);
  const [selectedMunicipality, setSelectedMunicipality] = useState<MunicipalityData | null>(null);
  const [metadataRegion] = useState<RegionData | null>(null);
  const [metadataOpen, setMetadataOpen] = useState(false);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  // Phones, upright or sideways, and narrow windows: one bottom sheet.
  // Tablets and small laptops: one side panel open at a time.
  const compact = useMediaQuery(COMPACT_QUERY);
  const medium = useMediaQuery(MEDIUM_QUERY);
  const [sheetSnap, setSheetSnap] = useState<SheetSnap>("collapsed");
  const [sheetTab, setSheetTab] = useState("summary");
  const [sheetH, setSheetH] = useState(SHEET_PEEK_H);
  // The tour's news step holds the News articles analyzed card open.
  const [tourNews, setTourNews] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  // Height of the timeline (it wraps on narrow widths): the legend sits above it.
  const timelineRowRef = useRef<HTMLDivElement>(null);
  const [timelineRowH, setTimelineRowH] = useState(0);
  const [rootH, setRootH] = useState(0);
  const [rootW, setRootW] = useState(0);

  const { data: quartersRes, error: quartersError } = useQuarters("nowcast");
  const quarters = useMemo(
    () =>
      selectableQuarters(quartersRes?.quarters ?? [], quartersRes?.calendarQuarter).map((q) =>
        apiQuarterToSlider(q, quartersRes?.calendarQuarter)
      ),
    [quartersRes]
  );

  const [quarterId, setQuarterId] = useState<string>("");
  useEffect(() => {
    // Open on the backend's default quarter (the Lead-1 quarter, e.g. 2026-Q4)
    // once the timeline loads; fall back to the newest forecast quarter only
    // when that quarter is not on the timeline or has no score.
    if (quarterId || !quartersRes?.current) return;
    const preferred = quarters.find((q) => q.id === quartersRes.current && !q.noData);
    const forecast = [...quarters].reverse().find((q) => q.forecast && !q.noData);
    setQuarterId(preferred?.id ?? forecast?.id ?? quartersRes.current);
  }, [quartersRes, quarters, quarterId]);

  // The timeline shows only the newest quarters; History lists all of them.
  const timelineQuarters = useMemo(() => timelineWindow(quarters), [quarters]);

  const currentQuarter = quarters.find((q) => q.id === quarterId) ?? quarters[quarters.length - 1];
  const quarterLabel = currentQuarter ? quarterPeriodLabel(currentQuarter) : "";

  // A quarter with no score is selectable: the map stays gray (no province
  // has a score) and the panels say so.
  const noData = !!currentQuarter?.noData;

  const { data: provincesRes, error: provincesError } = useProvinces(quarterId || undefined, "nowcast", !noData);
  // Fetch failure (not a 404): the panels say so instead of showing zeros.
  const loadFailed = isLoadFailure(quartersError) || isLoadFailure(provincesError);
  const regionsData = useMemo(
    () => (noData ? [] : (provincesRes?.data ?? []).map(provinceToRegion)),
    [provincesRes, noData]
  );

  const { data: rejectionsRes } = useRejections(quarterId || undefined, !noData);
  const rejectedIds = useMemo(
    () => new Set((rejectionsRes?.data ?? []).map((r) => r.provinceId)),
    [rejectionsRes]
  );

  const { data: municipalitiesRes } = useMunicipalities(selectedRegion?.id ?? null, quarterId || undefined);
  const municipalitiesData = useMemo(() => {
    if (!municipalitiesRes || !selectedRegion) return [];
    return municipalitiesRes.data.map((m) => municipalityToData(m, selectedRegion.name));
  }, [municipalitiesRes, selectedRegion]);

  // The same request as the regional score card's (shared cache): the
  // phone sheet's one-line summary when no province is selected.
  const { data: regionForecast } = useForecast("region", "calabarzon", quarterId || undefined, "nowcast");

  const filteredRegions = useMemo(() => {
    return regionsData.filter((r) => {
      if (filters.riskLevel !== "all" && r.riskLevel !== filters.riskLevel) return false;
      if (filters.region !== "all" && r.id !== filters.region) return false;
      return true;
    });
  }, [regionsData, filters]);

  const handleRegionClick = useCallback((r: RegionData | null) => {
    if (!r) return; // never toggle on a missing region (double-click on "Back to CALABARZON")
    setSelectedRegion((prev) => (prev?.id === r.id ? null : r));
    setSelectedMunicipality(null);
  }, []);

  const handleMunicipalityClick = useCallback((m: MunicipalityData) => {
    setSelectedMunicipality((prev) => (prev?.id === m.id ? null : m));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedRegion(null);
    setSelectedMunicipality(null);
  }, []);

  const handleHover = useCallback((r: RegionData | null) => setPreviewRegion(r), []);

  // A selection follows the selected quarter: the panels show that quarter's
  // score, not the one the province or municipality had when it was clicked.
  useEffect(() => {
    setSelectedRegion((prev) => (prev ? regionsData.find((r) => r.id === prev.id) ?? prev : prev));
  }, [regionsData]);
  useEffect(() => {
    setSelectedMunicipality((prev) => (prev ? municipalitiesData.find((m) => m.id === prev.id) ?? prev : prev));
  }, [municipalitiesData]);

  useEffect(() => {
    if (!noData) return;
    setSelectedRegion(null);
    setPreviewRegion(null);
    setSelectedMunicipality(null);
  }, [noData]);

  // Search (and the Data page) focus a province, or a city / municipality
  // with its province. The request is kept as pending and resolved as the
  // data arrives: the province once the province list is in (it reloads on a
  // quarter change), then the municipality once that province's list is in.
  // The listener is added once and only records the request: re-adding it
  // whenever the data changed left a moment in which a pick fired from the
  // search box's own effect found no listener and was lost.
  const [pendingMunicipalityId, setPendingMunicipalityId] = useState<string | null>(null);
  const [pendingProvinceId, setPendingProvinceId] = useState<string | null>(null);
  useEffect(() => {
    const onFocus = (e: Event) => {
      const detail = (e as CustomEvent).detail as { provinceId?: string; municipalityId?: string };
      setPendingProvinceId(detail.provinceId ?? null);
      setPendingMunicipalityId(detail.municipalityId ?? null);
    };
    window.addEventListener("aipheed:focus-region", onFocus as EventListener);
    return () => window.removeEventListener("aipheed:focus-region", onFocus as EventListener);
  }, []);
  useEffect(() => {
    if (!pendingProvinceId) return;
    const r = regionsData.find((rr) => rr.id === pendingProvinceId);
    if (!r) return;
    // Another province: its municipality from before no longer applies.
    if (selectedRegion?.id !== r.id) setSelectedMunicipality(null);
    setSelectedRegion(r);
    setPendingProvinceId(null);
  }, [pendingProvinceId, regionsData, selectedRegion]);

  // The Data page hands off a row click via sessionStorage (setItem before
  // navigating here) rather than a live event, since this component isn't
  // mounted yet when that click happens. Province data loads asynchronously,
  // so this retries as regionsData fills in.
  useEffect(() => {
    const raw = readStorage("aipheed_focus", "session");
    if (!raw || regionsData.length === 0) return;
    try {
      const detail = JSON.parse(raw) as { provinceId?: string };
      if (detail.provinceId && regionsData.some((r) => r.id === detail.provinceId)) {
        removeStorage("aipheed_focus", "session");
        window.dispatchEvent(new CustomEvent("aipheed:focus-region", { detail }));
      }
    } catch {
      removeStorage("aipheed_focus", "session");
    }
  }, [regionsData]);

  useEffect(() => {
    if (!pendingMunicipalityId) return;
    const m = municipalitiesData.find((mm) => mm.id === pendingMunicipalityId);
    if (!m) return;
    setSelectedMunicipality(m);
    setPendingMunicipalityId(null);
    // Its details: the Summary panel (tablets: closing Why; phones: the
    // sheet's Summary tab, opened halfway below).
    if (compact) {
      setSheetTab("summary");
    } else {
      setLeftCollapsed(false);
      if (medium) setRightCollapsed(true);
    }
  }, [pendingMunicipalityId, municipalitiesData, compact, medium]);

  // Phones: a municipality picked on the map or from search opens the sheet halfway.
  useEffect(() => {
    if (!compact || !selectedMunicipality) return;
    setSheetSnap((s) => (s === "collapsed" ? "half" : s));
  }, [compact, selectedMunicipality]);

  // ─── Layout ───
  // Height of the map area, for the sheet's three heights. Re-attached when
  // the layout switches, since each layout renders its own root.
  useLayoutEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const read = () => {
      setRootH(el.clientHeight);
      setRootW(el.clientWidth);
    };
    read();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(read);
    ro.observe(el);
    return () => ro.disconnect();
  }, [compact]);

  useLayoutEffect(() => {
    const el = timelineRowRef.current;
    if (!el) return;
    const read = () => setTimelineRowH(el.offsetHeight);
    read();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(read);
    ro.observe(el);
    return () => ro.disconnect();
  }, [compact]);

  // Tablets: the left panel open, the right one an edge tab. From 1280px
  // both open again.
  useEffect(() => {
    setLeftCollapsed(false);
    setRightCollapsed(medium);
  }, [medium]);

  // Phones: picking a province opens the sheet halfway.
  useEffect(() => {
    if (!compact || !selectedRegion) return;
    setSheetSnap((s) => (s === "collapsed" ? "half" : s));
  }, [compact, selectedRegion]);

  // The panels or sheet changed size: let the map redraw for its box once
  // the transition has finished.
  useEffect(() => {
    const t = setTimeout(() => window.dispatchEvent(new Event("aipheed:map-resize")), 320);
    return () => clearTimeout(t);
  }, [compact, medium, leftCollapsed, rightCollapsed, sheetSnap]);

  // The guided tour (MapTour) asks for a panel, a sheet height or the open news card per step.
  useEffect(() => {
    const onTourLayout = (e: Event) => {
      const { panel, sheet, news } = (e as CustomEvent<TourLayout>).detail;
      setTourNews(!!news);
      if (compact) {
        if (panel) setSheetTab(panel);
        if (sheet) setSheetSnap(sheet);
      } else if (panel === "summary") {
        setLeftCollapsed(false);
        if (medium) setRightCollapsed(true);
      } else if (panel === "why") {
        setRightCollapsed(false);
        if (medium) setLeftCollapsed(true);
      }
    };
    window.addEventListener(TOUR_LAYOUT_EVENT, onTourLayout);
    return () => window.removeEventListener(TOUR_LAYOUT_EVENT, onTourLayout);
  }, [compact, medium]);

  // On tablets, opening one panel closes the other.
  const showLeft = () => {
    setLeftCollapsed(false);
    if (medium) setRightCollapsed(true);
  };
  const showRight = () => {
    setRightCollapsed(false);
    if (medium) setLeftCollapsed(true);
  };

  const effectiveRegion = selectedRegion ?? previewRegion;
  const hasSelection = !!effectiveRegion;
  const bothCollapsed = leftCollapsed && rightCollapsed;
  const regionRejected = !!effectiveRegion && rejectedIds.has(effectiveRegion.id);

  const toggle = medium
    ? leftCollapsed
      ? { label: "Show the Summary panel", icon: PanelLeft, run: showLeft }
      : { label: "Show the Why panel", icon: PanelRight, run: showRight }
    : {
        label: bothCollapsed ? "Open both panels" : "Collapse both panels",
        icon: bothCollapsed ? PanelsTopLeft : PanelsRightBottom,
        run: () => {
          const nextCollapsed = !bothCollapsed;
          setLeftCollapsed(nextCollapsed);
          setRightCollapsed(nextCollapsed);
        },
      };

  // ─── Panel contents, shared by the side columns and the phone sheet ───
  const Card = compact ? SheetCard : PanelCard;

  const aboutFeedbackRow = (
    <div className="flex items-center justify-between gap-2">
      <AboutModal />
      <span className="text-[10px] text-muted-foreground/30">·</span>
      <FeedbackModal />
    </div>
  );
  // Desktop: a floating card of its own at the foot of the left column.
  const aboutFeedback = showAboutFeedback && (compact ? (
    <SheetCard tour="about">{aboutFeedbackRow}</SheetCard>
  ) : (
    <div data-tour="about" className="relative surface-card mt-auto shrink-0 px-4 py-2 text-card-foreground">
      {aboutFeedbackRow}
    </div>
  ));

  const leftCards = noData ? (
    <Card>
      <NoDataCardBody reason={currentQuarter?.reason} />
    </Card>
  ) : (
    <>
      {/* Its glow stays inside this panel: not over the map, the other panels or the screen edge.
          shrink-0: with overflow hidden the column could otherwise squeeze it. */}
      <Card className="overflow-hidden shrink-0">
        <RfiiScoreCardBody quarterId={quarterId} quarterLabel={quarterLabel} regionsData={regionsData} loadFailed={loadFailed} />
      </Card>
      <Card>
        <RiskDriversCardBody quarterId={quarterId} />
      </Card>
      <Card>
        <ProvinceRankingCardBody onRegionClick={handleRegionClick} regionsData={regionsData} loadFailed={loadFailed} />
      </Card>
    </>
  );

  const selectionPanel = (
    <LeftPanel
      selectedRegion={effectiveRegion}
      previewRegion={previewRegion}
      selectedMunicipality={selectedMunicipality}
      quarterId={quarterId}
      regionsData={regionsData}
      municipalitiesData={municipalitiesData}
      onClose={clearSelection}
      onCloseMunicipality={() => setSelectedMunicipality(null)}
      onRegionClick={handleRegionClick}
      onMunicipalityClick={handleMunicipalityClick}
      rejectedProvinceIds={rejectedIds}
    />
  );

  const rightCards = noData ? (
    <Card>
      <NoDataCardBody reason={currentQuarter?.reason} />
    </Card>
  ) : effectiveRegion && regionRejected ? (
    <Card>
      <div className="py-8 text-center space-y-2">
        <p className="text-[11px] font-semibold text-muted-foreground">No forecast available</p>
        <p className="text-[10px] text-muted-foreground/60 leading-snug px-2">
          This quarter's forecast for <span className="font-semibold">{effectiveRegion.name}</span> has been rejected by the admin.
        </p>
      </div>
    </Card>
  ) : currentQuarter ? (
    <>
      <Card>
        <ShapNarrativeCardBody
          quarter={currentQuarter}
          selectedRegion={effectiveRegion}
          selectedMunicipality={selectedMunicipality}
        />
      </Card>
      <Card>
        <NewsArticlesCardBody selectedRegion={effectiveRegion} quarterId={quarterId} tourOpen={tourNews} />
      </Card>
    </>
  ) : null;

  const historyModal = (
    <ForecastHistoryModal
      open={historyOpen}
      onOpenChange={setHistoryOpen}
      quarters={quarters}
      value={quarterId}
      onSelect={(id) => {
        setQuarterId(id);
        setHistoryOpen(false);
      }}
    />
  );

  const wideCompact = compact && rootW >= WIDE_COMPACT_W;

  // Tablets and desktops: what a side panel covers from its screen edge,
  // open or closed (its tab).
  const sideW = (collapsed: boolean) => EDGE + (collapsed ? TAB_W : COL_W);

  const map = (
    <div className="absolute inset-0" data-tour="map">
      <PhilippineMap
        regions={filteredRegions}
        selectedRegion={selectedRegion}
        selectedMunicipality={selectedMunicipality}
        municipalities={municipalitiesData}
        onHover={handleHover}
        onClick={handleRegionClick}
        onMunicipalityClick={handleMunicipalityClick}
        onBackgroundClick={clearSelection}
        rejectedProvinceIds={rejectedIds}
        // Fit CALABARZON (or the chosen place) into the part of the map left
        // uncovered: phones, above the sheet at its current height; larger
        // screens, between the panels (or their tabs), below the search box,
        // left of the map buttons and above the timeline.
        fitInsets={
          compact
            ? { top: wideCompact ? EDGE + SEARCH_H : SHEET_TOP_RESERVE + LEGEND_STACK_H, right: 0, bottom: sheetH + 8 + ROW_H, left: 0 }
            : { top: EDGE + DESKTOP_SEARCH_H, right: sideW(rightCollapsed) + EDGE + CONTROLS_W, bottom: EDGE + timelineRowH, left: sideW(leftCollapsed) }
        }
        minZoom={compact ? 6.5 : 8}
        zoomSnap={compact ? 0.25 : 1}
      />
    </div>
  );

  // ─── Phones: one bottom sheet ───
  if (compact) {
    // The one-line summary on the sheet's handle.
    const subject = selectedMunicipality ?? effectiveRegion;
    const peekName = subject?.name ?? "CALABARZON";
    let peekScore: number | null = null;
    let peekLevel: RegionData["riskLevel"] | null = null;
    let peekNote: string | null = null;
    if (noData) peekNote = "No data for this quarter";
    else if (!selectedMunicipality && regionRejected) peekNote = "No forecast available";
    else if (subject) {
      peekScore = subject.riskScore;
      peekLevel = subject.riskLevel;
    } else if (typeof regionForecast?.riskScore === "number") {
      peekScore = regionForecast.riskScore;
      const high = regionForecast.riskLevel ? regionForecast.riskLevel === "high" : isHighRisk(regionForecast.riskScore);
      peekLevel = high ? "high" : "low";
    }

    // The quarter strip and zoom buttons ride on the sheet; at full height
    // there is no room for them under the search box, so they step aside.
    const rowBottom = sheetH + 8;
    const rowVisible = sheetSnap === "collapsed" || rootH - rowBottom - ROW_H - SHEET_TOP_RESERVE >= MIN_MAP_H;
    // Under the search box (upright), or beside it at the top right (sideways).
    const legendVisible = wideCompact || rootH - rowBottom - ROW_H >= SHEET_TOP_RESERVE + LEGEND_STACK_H + 8;

    return (
      <div ref={rootRef} className="h-full w-full relative overflow-hidden">
        {map}

        <div
          className="absolute z-[1002]"
          style={wideCompact ? { left: EDGE, top: EDGE, width: Math.min(SEARCH_MAX_W, rootW - 2 * EDGE - LEGEND_BESIDE_W) } : { left: EDGE, right: EDGE, top: EDGE }}
          data-tour="search"
        >
          <MapSearch fill />
        </div>

        {legendVisible && (
          <div
            className={`absolute z-[1001] flex flex-col ${wideCompact ? "items-end" : "items-start"} gap-1 pointer-events-none`}
            style={wideCompact ? { right: EDGE, top: EDGE } : { left: EDGE, top: SHEET_TOP_RESERVE }}
          >
            <div data-tour="legend"><MapLegend compact /></div>
            <span className="qt-float text-[12px] leading-4 font-normal text-[hsl(var(--text-muted))]">© OpenStreetMap · Protomaps</span>
          </div>
        )}

        {rowVisible && (
          <div className="absolute z-[1002] flex items-end gap-2" style={{ left: EDGE, right: EDGE, bottom: rowBottom }} data-tour="timeline">
            <div className="flex-1 min-w-0">
              {currentQuarter && (
                <QuarterTimeSlider
                  variant="strip"
                  value={quarterId}
                  onChange={setQuarterId}
                  quarters={timelineQuarters}
                  allQuarters={quarters}
                  onOpenHistory={() => setHistoryOpen(true)}
                />
              )}
            </div>
            <MapControls layout="row" />
          </div>
        )}

        <Tabs value={sheetTab} onValueChange={setSheetTab}>
          <MapBottomSheet
            snap={sheetSnap}
            onSnapChange={setSheetSnap}
            containerHeight={rootH}
            topReserve={SHEET_TOP_RESERVE}
            onHeightChange={setSheetH}
            peek={
              <>
                <span className="font-semibold truncate">{peekName}</span>
                {peekScore !== null && (
                  <>
                    <span aria-hidden className="text-muted-foreground">·</span>
                    <span className="font-semibold tabular-nums">{peekScore.toFixed(2)}</span>
                    {peekLevel && <StatusBadge level={peekLevel} className="shrink-0" />}
                  </>
                )}
                {peekNote && (
                  <>
                    <span aria-hidden className="text-muted-foreground">·</span>
                    <span className="text-muted-foreground truncate">{peekNote}</span>
                  </>
                )}
                <ChevronUp aria-hidden className={`ml-auto h-5 w-5 shrink-0 text-muted-foreground transition-transform ${sheetSnap === "full" ? "rotate-180" : ""}`} />
              </>
            }
            header={
              <div className="shrink-0 px-3 pb-2">
                <TabsList className="w-full grid grid-cols-2 h-auto p-1" aria-label="Details">
                  <TabsTrigger value="summary" className="h-11 text-[14px]">Summary</TabsTrigger>
                  <TabsTrigger value="why" className="h-11 text-[14px]">Why</TabsTrigger>
                </TabsList>
              </div>
            }
          >
            <div className="px-3 pb-3">
              <TabsContent value="summary" className="mt-0 flex flex-col gap-2">
                {/* The province panel has its own About / Feedback footer. */}
                {hasSelection && !noData ? <SheetCard className="p-0 overflow-hidden">{selectionPanel}</SheetCard> : <>{leftCards}{aboutFeedback}</>}
              </TabsContent>
              <TabsContent value="why" className="mt-0 flex flex-col gap-2">
                {rightCards}
              </TabsContent>
            </div>
          </MapBottomSheet>
        </Tabs>

        <RegionMetadataPopup region={metadataRegion} open={metadataOpen} onOpenChange={setMetadataOpen} />
        {historyModal}
      </div>
    );
  }

  // ─── Tablets and desktops: side columns ───
  return (
    <div ref={rootRef} className="h-full w-full relative overflow-hidden">
      {map}

      {/* LEFT floating column */}
      <div
        className={`absolute z-[1001] flex flex-col gap-2.5 transition-[left,visibility] duration-300 ${leftCollapsed ? "invisible" : "animate-slide-in-left"}`}
        style={{ top: COL_TOP, bottom: COL_BOTTOM, left: leftCollapsed ? -(COL_W + EDGE) : EDGE, width: COL_W }}
        aria-hidden={leftCollapsed || undefined}
        data-tour="summary"
      >
          {/* Separate floating cards, 10px apart; they scroll together. */}
          {hasSelection && !noData ? (
            <div className="left-sidebar-scrollbar-left shadow-room flex-1 min-h-0 overflow-y-auto thin-scrollbar">
              <div className="surface-card overflow-hidden text-card-foreground">{selectionPanel}</div>
            </div>
          ) : (
            <>
              <div className="left-sidebar-scrollbar-left shadow-room flex-1 min-h-0 overflow-y-auto thin-scrollbar flex flex-col gap-2.5">
                {leftCards}
              </div>
              {aboutFeedback}
            </>
          )}
      </div>

      {/* RIGHT floating column */}
      <div
        className={`absolute z-[1001] flex flex-col transition-[right,visibility] duration-300 ${rightCollapsed ? "invisible" : "animate-slide-in-right"}`}
        style={{ top: COL_TOP, bottom: COL_BOTTOM, right: rightCollapsed ? -(COL_W + EDGE) : EDGE, width: COL_W }}
        aria-hidden={rightCollapsed || undefined}
        data-tour="why"
      >
          {rightCards && (
            <div className="shadow-room min-h-0 overflow-y-auto thin-scrollbar flex flex-col gap-2.5">
              {rightCards}
            </div>
          )}
      </div>

      {leftCollapsed && <PanelTab side="left" label="Summary" onClick={showLeft} />}
      {rightCollapsed && <PanelTab side="right" label="Why" onClick={showRight} />}

      {/* Map search — top, beside left sidebar */}
      <div
        className="absolute z-[1001] animate-fade-in transition-[left] duration-300"
        style={{ left: sideW(leftCollapsed) + 12, top: 12 }}
        data-tour="search"
      >
        <MapSearch />
      </div>

      <MapControls
        rightOffset={sideW(rightCollapsed)}
        toggleLabel={toggle.label}
        toggleIcon={toggle.icon}
        onToggle={toggle.run}
      />

      {/* Bottom of the visible map: the quarter bar spanning the gap between the
          sidebars (same 12px inset as the search box; layout in index.css, .qt-row). */}
      <div
        ref={timelineRowRef}
        className="qt-row absolute z-[1001] pointer-events-none transition-[left,right] duration-300"
        style={{
          left: sideW(leftCollapsed) + 12,
          right: sideW(rightCollapsed) + 12,
          bottom: 12,
        }}
      >
        <div className="qt-row-stack">
          {currentQuarter && (
            <div className="qt-row-bar pointer-events-auto animate-slide-up" data-tour="timeline">
              <QuarterTimeSlider
                value={quarterId}
                onChange={setQuarterId}
                quarters={timelineQuarters}
                allQuarters={quarters}
                onOpenHistory={() => setHistoryOpen(true)}
              />
            </div>
          )}
        </div>
      </div>

      {/* Risk legend: in the map buttons' column (same width and right edge),
          just above the right end of the timeline; it moves with the right
          panel like the buttons. */}
      <div
        className="absolute z-[1001] transition-[right] duration-300 animate-fade-in"
        style={{ right: sideW(rightCollapsed) + 12, bottom: 12 + timelineRowH + 8 }}
        data-tour="legend"
      >
        <MapLegend />
      </div>

      {/* Map credit: in a bottom corner below an open panel, clear of the
          timeline (which has no box behind it). Both panels closed: the
          timeline is capped and centred, so the right corner is free. */}
      <div className={`absolute bottom-2 ${rightCollapsed && !leftCollapsed ? "left-3" : "right-3"} z-[1000] text-[9px] text-muted-foreground/70 px-2 py-1`}>
        © OpenStreetMap · Protomaps
      </div>

      <RegionMetadataPopup region={metadataRegion} open={metadataOpen} onOpenChange={setMetadataOpen} />
      {historyModal}
    </div>
  );
}
