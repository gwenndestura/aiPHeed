import { useEffect, useLayoutEffect, useRef, useState, useMemo, useCallback } from "react";
import { ChevronUp, PanelLeft, PanelRight, PanelsTopLeft, PanelsRightBottom } from "lucide-react";
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
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { COMPACT_QUERY, MEDIUM_QUERY } from "@/lib/breakpoints";
import { isLoadFailure } from "@/lib/loadError";
import { isHighRisk } from "@/lib/risk";
import { TOUR_LAYOUT_EVENT, type TourLayout } from "@/lib/tour";
import { readStorage, removeStorage } from "@/lib/storage";

function FloatingCard({ children, className = "", style, tour }: { children: React.ReactNode; className?: string; style?: React.CSSProperties; tour?: string }) {
  return (
    <div
      data-tour={tour}
      className={`px-4 py-3.5 shadow-xl bg-card/85 text-card-foreground border border-border/60 ${className}`}
      style={{
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        borderRadius: 0,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/**
 * Tablets: the closed side panel as a labelled tab at the screen edge.
 * Opening it closes the other panel.
 */
function EdgeTab({ side, label, onClick }: { side: "left" | "right"; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Show the ${label} panel`}
      className={`absolute z-[1001] top-1/2 -translate-y-1/2 ${side === "left" ? "left-0 border-l-0" : "right-0 border-r-0"} w-11 py-5 flex items-center justify-center bg-card/95 border border-border/60 shadow-xl text-[13px] font-semibold text-foreground hover:bg-secondary/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring`}
      style={{ writingMode: "vertical-rl" }}
    >
      {label}
    </button>
  );
}

/** A card inside the phone sheet, which already has the blur and shadow. */
function SheetCard({ children, className = "", tour }: { children: React.ReactNode; className?: string; tour?: string }) {
  return <div data-tour={tour} className={`px-4 py-3.5 border border-border/50 bg-card/60 ${className}`}>{children}</div>;
}

function NoDataCardBody({ reason }: { reason?: string }) {
  return (
    <div className="py-8 text-center space-y-2">
      <p className="text-[11px] font-semibold text-muted-foreground">No data</p>
      {reason && <p className="text-[10px] text-muted-foreground/60 leading-snug px-2">{reason}</p>}
    </div>
  );
}

const COL_W = 320;
const PEEK_W = 24;
const COL_TOP = 0;
const COL_BOTTOM = 64;

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
// Tablets: width of the closed panel's edge tab.
const EDGE_TAB_W = 44;

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
  const rootRef = useRef<HTMLDivElement>(null);
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
    // Default to the newest forecast quarter once the timeline loads, falling
    // back to the newest scorable quarter when no forecast is served.
    if (quarterId || !quartersRes?.current) return;
    const forecast = [...quarters].reverse().find((q) => q.forecast && !q.noData);
    setQuarterId(forecast?.id ?? quartersRes.current);
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

  const handleRegionClick = useCallback((r: RegionData) => {
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

  useEffect(() => {
    if (!noData) return;
    setSelectedRegion(null);
    setPreviewRegion(null);
    setSelectedMunicipality(null);
  }, [noData]);

  useEffect(() => {
    const onFocus = (e: Event) => {
      const detail = (e as CustomEvent).detail as { provinceId?: string; municipalityId?: string };
      if (detail.provinceId) {
        const r = regionsData.find((rr) => rr.id === detail.provinceId);
        if (r) setSelectedRegion(r);
      }
      // A municipality focus needs its province selected first (the roster
      // loads per-province); resolved once that province's data is in.
      if (detail.municipalityId) {
        window.dispatchEvent(
          new CustomEvent("aipheed:pending-municipality", { detail: { municipalityId: detail.municipalityId } })
        );
      }
    };
    window.addEventListener("aipheed:focus-region", onFocus as EventListener);
    return () => window.removeEventListener("aipheed:focus-region", onFocus as EventListener);
  }, [regionsData]);

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
    const onPending = (e: Event) => {
      const detail = (e as CustomEvent).detail as { municipalityId?: string };
      const m = municipalitiesData.find((mm) => mm.id === detail.municipalityId);
      if (m) setSelectedMunicipality(m);
    };
    window.addEventListener("aipheed:pending-municipality", onPending as EventListener);
    return () => window.removeEventListener("aipheed:pending-municipality", onPending as EventListener);
  }, [municipalitiesData]);

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

  // The guided tour (MapTour) asks for a panel or a sheet height per step.
  useEffect(() => {
    const onTourLayout = (e: Event) => {
      const { panel, sheet } = (e as CustomEvent<TourLayout>).detail;
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
  const Card = compact ? SheetCard : FloatingCard;

  const aboutFeedback = showAboutFeedback && (
    <Card className={compact ? "" : "!py-2 shrink-0"} tour="about">
      <div className="flex items-center justify-between gap-2">
        <AboutModal />
        <span className="text-[10px] text-muted-foreground/30">·</span>
        <FeedbackModal />
      </div>
    </Card>
  );

  const leftCards = noData ? (
    <Card>
      <NoDataCardBody reason={currentQuarter?.reason} />
    </Card>
  ) : (
    <>
      <Card>
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
        <NewsArticlesCardBody selectedRegion={effectiveRegion} quarterId={quarterId} />
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
        // Phones: fit CALABARZON into the part of the map left uncovered.
        fitInsets={compact ? { top: wideCompact ? EDGE + SEARCH_H : SHEET_TOP_RESERVE + LEGEND_STACK_H, right: 0, bottom: SHEET_PEEK_H + 8 + ROW_H, left: 0 } : undefined}
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
          style={wideCompact ? { left: EDGE, top: EDGE, width: Math.min(SEARCH_MAX_W, rootW - 2 * EDGE - 200) } : { left: EDGE, right: EDGE, top: EDGE }}
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
            <span className="qt-float text-[12px]">© OpenStreetMap · Protomaps</span>
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
                {hasSelection && !noData ? <SheetCard className="p-0">{selectionPanel}</SheetCard> : <>{leftCards}{aboutFeedback}</>}
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
  // Closed panel: a 24px strip of it (desktop) or an edge tab (tablets).
  const closedW = medium ? EDGE_TAB_W : PEEK_W;
  return (
    <div ref={rootRef} className="h-full w-full relative overflow-hidden">
      {map}

      {/* LEFT floating column */}
      <div
        className={`absolute z-[1001] flex flex-col gap-2 transition-[left] duration-300 ${leftCollapsed ? "cursor-pointer" : "animate-slide-in-left"} ${medium && leftCollapsed ? "invisible" : ""}`}
        style={{ top: COL_TOP, bottom: COL_BOTTOM, left: leftCollapsed ? -(COL_W - PEEK_W) : 0, width: COL_W }}
        onClick={() => leftCollapsed && showLeft()}
        aria-label={leftCollapsed ? "Show left sidebar" : undefined}
        data-tour="summary"
      >
          {hasSelection && !noData ? (
            <div className="left-sidebar-scrollbar-left flex-1 min-h-0 overflow-y-auto thin-scrollbar">
              <FloatingCard className="p-0 overflow-hidden">{selectionPanel}</FloatingCard>
            </div>
          ) : (
            <>
              <div className="left-sidebar-scrollbar-left flex-1 min-h-0 overflow-y-auto thin-scrollbar flex flex-col gap-2">
                {leftCards}
              </div>
              {aboutFeedback}
            </>
          )}
      </div>

      {/* RIGHT floating column */}
      <div
        className={`absolute z-[1001] flex flex-col gap-2 overflow-y-auto thin-scrollbar transition-[right] duration-300 ${rightCollapsed ? "cursor-pointer" : "animate-slide-in-right"} ${medium && rightCollapsed ? "invisible" : ""}`}
        style={{ top: COL_TOP, bottom: COL_BOTTOM, right: rightCollapsed ? -(COL_W - PEEK_W) : 0, width: COL_W }}
        onClick={() => rightCollapsed && showRight()}
        aria-label={rightCollapsed ? "Show right sidebar" : undefined}
        data-tour="why"
      >
          {rightCards}
      </div>

      {medium && leftCollapsed && <EdgeTab side="left" label="Summary" onClick={showLeft} />}
      {medium && rightCollapsed && <EdgeTab side="right" label="Why" onClick={showRight} />}

      {/* Map search — top, beside left sidebar */}
      <div
        className="absolute z-[1001] animate-fade-in transition-[left] duration-300"
        style={{ left: (leftCollapsed ? closedW : COL_W) + 12, top: 12 }}
        data-tour="search"
      >
        <MapSearch />
      </div>

      <MapControls
        rightOffset={rightCollapsed ? closedW : COL_W}
        toggleLabel={toggle.label}
        toggleIcon={toggle.icon}
        onToggle={toggle.run}
      />

      {/* Bottom of the visible map: the quarter bar spanning the gap between the
          sidebars (same 12px inset as the search box), with the risk
          legend above its left edge (layout in index.css, .qt-row). */}
      <div
        className="qt-row absolute z-[1001] pointer-events-none transition-[left,right] duration-300"
        style={{
          left: (leftCollapsed ? closedW : COL_W) + 12,
          right: (rightCollapsed ? closedW : COL_W) + 12,
          bottom: 12,
        }}
      >
        <div className="qt-row-stack">
          <div className="qt-row-legend pointer-events-auto animate-fade-in" data-tour="legend">
            <MapLegend />
          </div>
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

      <div className="absolute bottom-2 right-3 z-[1000] text-[9px] text-muted-foreground/70 px-2 py-1">
        © OpenStreetMap · Protomaps
      </div>

      <RegionMetadataPopup region={metadataRegion} open={metadataOpen} onOpenChange={setMetadataOpen} />
      {historyModal}
    </div>
  );
}
