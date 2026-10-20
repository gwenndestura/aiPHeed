import { useEffect, useMemo, useRef, type CSSProperties, type KeyboardEvent } from "react";
import { QUARTER_IDS } from "@/data/quarterData";
import { quarterMonthRange } from "@/lib/quarters";

export interface Quarter {
  id: string;
  year: number;
  q: 1 | 2 | 3 | 4;
  label: string;
  monthsLabel: string;
  forecast?: boolean;
  locked?: boolean;
  current?: boolean;
  past?: boolean; // a quarter earlier than "now" — an actual, not a forecast
  noData?: boolean; // selectable, but no score: shown gray
  reason?: string; // why a noData quarter has no score
}

interface Props {
  value: string;
  onChange: (id: string) => void;
  quarters?: Quarter[];
  // Every selectable quarter, when `quarters` is only the visible window: a
  // quarter picked from History that is older than the window still gets
  // its label, with no dot highlighted.
  allQuarters?: Quarter[];
  onOpenHistory?: () => void;
  /**
   * "bar" (default): the track with labelled points. "strip": a row of 44px
   * quarter buttons that scrolls sideways, for the phone layout.
   */
  variant?: "bar" | "strip";
}

const MONTHS = ["Jan–Mar", "Apr–Jun", "Jul–Sep", "Oct–Dec"];

// Chronological rank of a "YYYY-Qn" id.
const ord = (id: string) => {
  const [y, q] = id.split("-Q");
  return Number(y) * 4 + (Number(q) - 1);
};

/** The quarter that contains `now` in real time — e.g. September ⇒ Q3. */
export function currentQuarterId(now: Date = new Date()): string {
  return `${now.getFullYear()}-Q${Math.floor(now.getMonth() / 3) + 1}`;
}

/**
 * Timeline quarters, spanning the full available data range. `current` tracks
 * real time: quarters before it are actuals (history), quarters after it are
 * forecasts. `current` is clamped to the data range so it always resolves.
 */
export function buildQuarters(now: Date = new Date()): Quarter[] {
  const ids = QUARTER_IDS as readonly string[];
  const first = ord(ids[0]);
  const last = ord(ids[ids.length - 1]);
  const cur = Math.min(Math.max(ord(currentQuarterId(now)), first), last);

  return ids.map((id) => {
    const [yStr, qStr] = id.split("-Q");
    const q = Number(qStr) as 1 | 2 | 3 | 4;
    const o = ord(id);
    return {
      id,
      year: Number(yStr),
      q,
      label: `Q${q}`,
      monthsLabel: MONTHS[q - 1],
      forecast: o > cur,
      current: o === cur,
      past: o < cur,
      locked: false,
    };
  });
}

type Status = "observed" | "current" | "forecast";

const statusOf = (q: Quarter): Status => (q.forecast ? "forecast" : q.current ? "current" : "observed");

const STATUS_TAG: Record<Status, string> = {
  observed: "Observed",
  current: "Current quarter",
  forecast: "Forecast",
};
const STRIP_TAG: Record<Status, string> = { observed: "Observed", current: "Current", forecast: "Forecast" };

// The track fills the map area between the sidebars; this is the tightest
// the points may squeeze before it scrolls instead.
const MIN_SPACING = 64;

const fullName = (q: Quarter) => `Q${q.q} ${q.year}`;

// Where today falls on the track, in dot-index units: on the current
// quarter's dot, else between the last actual and the first forecast.
// null when today lies outside the visible window.
function todayPosition(qs: Quarter[]): number | null {
  const cur = qs.findIndex((q) => q.current);
  if (cur >= 0) return cur;
  const firstForecast = qs.findIndex((q) => q.forecast);
  return firstForecast > 0 ? firstForecast - 0.5 : null;
}

export function QuarterTimeSlider({ value, onChange, quarters, allQuarters, onOpenHistory, variant = "bar" }: Props) {
  const qs = useMemo(() => quarters ?? buildQuarters(), [quarters]);
  const found = qs.findIndex((q) => q.id === value);
  const outsideWindow = found < 0 && !!allQuarters?.some((q) => q.id === value);
  const idx = outsideWindow ? -1 : Math.max(0, found);
  const shown = (outsideWindow ? allQuarters!.find((q) => q.id === value) : qs[idx]) ?? qs[0];

  const scrollRef = useRef<HTMLDivElement>(null);
  const pointRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const at = (i: number) => (qs.length > 1 ? (i / (qs.length - 1)) * 100 : 0);

  // Solid up to today, dashed after it. With today outside the window the
  // whole track is one style: dashed if it is all forecast, else solid.
  const today = todayPosition(qs);
  const todayOnPoint = today !== null && Number.isInteger(today) ? today : -1;
  const split = today !== null ? at(today) : qs.every((q) => q.forecast) ? 0 : 100;

  const description = [
    "Solid line: observed quarters. Dashed line: forecast quarters.",
    today === null
      ? ""
      : todayOnPoint >= 0
        ? `Today is at ${fullName(qs[todayOnPoint])}.`
        : `Today falls between ${fullName(qs[Math.floor(today)])} and ${fullName(qs[Math.ceil(today)])}.`,
  ].join(" ").trim();

  // Roving tab stop: the selected point, or the first usable one when the
  // selected quarter sits outside the window.
  const tabStop = idx >= 0 && !qs[idx]?.locked ? idx : qs.findIndex((q) => !q.locked);

  // When the track scrolls (narrow screens), keep the selected point in view,
  // including after the bar resizes (sidebars opening, window resizing).
  useEffect(() => {
    const sc = scrollRef.current;
    const el = idx >= 0 ? pointRefs.current[idx] : null;
    if (!sc || !el) return;
    const keepInView = () => {
      if (sc.scrollWidth <= sc.clientWidth) return;
      const s = sc.getBoundingClientRect();
      const p = el.getBoundingClientRect();
      sc.scrollLeft += p.left + p.width / 2 - (s.left + s.width / 2);
    };
    keepInView();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(keepInView);
    ro.observe(sc);
    return () => ro.disconnect();
  }, [idx, qs.length]);

  const onKeyDown = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    const usable = qs.flatMap((q, j) => (q.locked ? [] : [j]));
    let next: number | undefined;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = usable.find((j) => j > i);
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = usable.filter((j) => j < i).pop();
    else if (e.key === "Home") next = usable[0];
    else if (e.key === "End") next = usable[usable.length - 1];
    else return;
    e.preventDefault();
    if (next === undefined || next === i) return;
    pointRefs.current[next]?.focus();
    onChange(qs[next].id);
  };

  const gaps = Math.max(qs.length - 1, 1);
  const trackSize = { "--qt-track-min": `${gaps * MIN_SPACING}px` } as CSSProperties;

  const pointProps = (q: Quarter, i: number) => ({
    ref: (el: HTMLButtonElement | null) => (pointRefs.current[i] = el),
    type: "button" as const,
    role: "radio",
    "aria-checked": i === idx,
    "aria-label": `${fullName(q)}, ${STATUS_TAG[statusOf(q)].toLowerCase()}${i === todayOnPoint ? ", today" : ""}${q.noData ? ", no data" : ""}${q.locked ? ", not yet available" : ""}`,
    title: q.locked ? "Data not yet available." : `${quarterMonthRange(q)}${i === todayOnPoint ? " · Today" : ""}`,
    tabIndex: i === tabStop ? 0 : -1,
    disabled: q.locked,
    onClick: () => onChange(q.id),
    onKeyDown: (e: KeyboardEvent<HTMLButtonElement>) => onKeyDown(e, i),
  });

  if (variant === "strip") {
    return (
      <div ref={scrollRef} className="qt-strip min-w-0 overflow-x-auto no-scrollbar">
        <div className="flex items-stretch gap-1.5 w-max">
          {/* A quarter picked from History, older than the window. */}
          {outsideWindow && (
            <span className="qt-chip" aria-current="true">
              <span className="font-semibold">{fullName(shown)}</span>
              <span className="qt-muted">{STRIP_TAG[statusOf(shown)]}</span>
            </span>
          )}
          <div role="radiogroup" aria-label="Quarter" aria-description={description} className="flex items-stretch gap-1.5">
            {qs.map((q, i) => (
              <button
                key={q.id}
                {...pointProps(q, i)}
                className={`qt-chip${q.forecast ? " qt-chip-forecast" : ""}${q.noData ? " qt-point-nodata" : ""}`}
              >
                <span className="font-semibold">{fullName(q)}</span>
                <span className="qt-muted">{STRIP_TAG[statusOf(q)]}</span>
              </button>
            ))}
          </div>
          {onOpenHistory && (
            <button type="button" onClick={onOpenHistory} aria-label="View history" className="qt-chip justify-center font-semibold">
              History
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="qt-float qt-float-bar select-none">
      {/* Selected quarter, centred over the track, with View history at the
          right end. The two side boxes share the leftover width equally and
          never shrink below the history link (the left one holds an invisible
          copy of it), so the group stays centred; when space runs out the group
          shrinks and wraps, still centred, before it could reach the link. */}
      <div className="flex items-center gap-x-3">
        <div className="flex-1 basis-0 flex justify-start">
          {onOpenHistory && (
            <span aria-hidden className="qt-link invisible whitespace-nowrap">
              <span className="qt-history-full">View history</span>
              <span className="qt-history-short">History</span>
            </span>
          )}
        </div>
        <div className="min-w-0 flex items-center justify-center gap-x-3 gap-y-1 flex-wrap">
          <span className="text-[13px] leading-5 font-semibold">{fullName(shown)}</span>
          <span className="qt-muted qt-status text-[11px]">{quarterMonthRange(shown)}</span>
          <span className="qt-tag">{STATUS_TAG[statusOf(shown)]}</span>
        </div>
        <div className="flex-1 basis-0 flex justify-end">
          {onOpenHistory && (
            <button type="button" onClick={onOpenHistory} aria-label="View history" className="qt-link whitespace-nowrap">
              <span className="qt-history-full">View history</span>
              <span className="qt-history-short">History</span>
            </button>
          )}
        </div>
      </div>

      {/* Track. The scroll box clips at its padding edge, and the end points'
          labels hang half their width (~24px plus the halo) past their dots,
          so the inset must clear that or "Q1 2026" loses its first letter. */}
      <div ref={scrollRef} className="min-w-0 overflow-x-auto no-scrollbar px-8 mt-1">
        <div
          role="radiogroup"
          aria-label="Quarter"
          aria-description={description}
          className="qt-track relative h-[46px]"
          style={trackSize}
        >
          {split > 0 && (
            <div className="qt-segment absolute left-0 top-[16px]" style={{ width: `${split}%` }} title="Observed">
              <span className="qt-line-observed" />
            </div>
          )}
          {split < 100 && (
            <div className="qt-segment absolute right-0 top-[16px]" style={{ left: `${split}%` }} title="Forecast">
              <span className="qt-line-forecast" />
            </div>
          )}
          {today !== null && (
            <div
              aria-hidden
              title="Today"
              className="absolute top-0 -translate-x-1/2 flex flex-col items-center"
              style={{ left: `${split}%` }}
            >
              <span className="qt-muted text-[10px] leading-[14px]">Today</span>
              {todayOnPoint < 0 && <span className="qt-today-line mt-[2px] h-3" />}
            </div>
          )}

          {qs.map((q, i) => (
            <button
              key={q.id}
              {...pointProps(q, i)}
              className={`qt-point${q.noData ? " qt-point-nodata" : ""} absolute top-[16px] -translate-x-1/2 flex flex-col items-center px-1 whitespace-nowrap`}
              style={{ left: `${at(i)}%` }}
            >
              <span className="h-[14px] flex items-center justify-center">
                <span className="qt-dot" />
              </span>
              <span className="qt-label text-[10px] leading-[14px] mt-0.5">{fullName(q)}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Legend, centred under the track */}
      <div aria-hidden className="qt-muted flex items-center justify-center gap-4 text-[10px] leading-[14px]">
        <span className="flex items-center gap-1.5">
          <span className="qt-key qt-line-observed" />
          Observed
        </span>
        <span className="flex items-center gap-1.5">
          <span className="qt-key qt-line-forecast" />
          Forecast
        </span>
      </div>
    </div>
  );
}
