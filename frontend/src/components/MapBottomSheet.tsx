import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";

/**
 * The map's side panels on phones (upright or sideways) and narrow windows:
 * one sheet over the bottom of the map, at three heights. Tap the handle to
 * step through them, drag it to any height (it settles on the nearest), or
 * use the arrow keys on it.
 */
export type SheetSnap = "collapsed" | "half" | "full";
const ORDER: SheetSnap[] = ["collapsed", "half", "full"];

/** Handle (grab bar and one-line summary), without the home-bar inset. */
export const SHEET_PEEK_H = 60;
const MIN_MAP_H = 96;

interface Props {
  snap: SheetSnap;
  onSnapChange: (s: SheetSnap) => void;
  /** Height of the map area the sheet sits in. */
  containerHeight: number;
  /** Kept clear at the top at full height (the search box). */
  topReserve: number;
  /** The one-line summary on the handle, e.g. "CALABARZON · 0.50 High risk". */
  peek: ReactNode;
  /** Above the scrolling content while open (the tabs). */
  header?: ReactNode;
  children: ReactNode;
  /** The sheet's height as it changes, dragging included. */
  onHeightChange?: (px: number) => void;
}

/** The iPhone home-bar inset, env(safe-area-inset-bottom), in px (0 elsewhere). */
function useSafeAreaBottom() {
  const [px, setPx] = useState(0);
  useEffect(() => {
    const probe = document.createElement("div");
    probe.style.cssText = "position:fixed;bottom:0;height:0;padding-bottom:env(safe-area-inset-bottom);visibility:hidden;pointer-events:none";
    document.body.appendChild(probe);
    const read = () => setPx(parseFloat(getComputedStyle(probe).paddingBottom) || 0);
    read();
    window.addEventListener("resize", read);
    return () => {
      window.removeEventListener("resize", read);
      probe.remove();
    };
  }, []);
  return px;
}

export function MapBottomSheet({ snap, onSnapChange, containerHeight, topReserve, peek, header, children, onHeightChange }: Props) {
  const safeBottom = useSafeAreaBottom();
  const contentId = useId();
  const collapsedH = SHEET_PEEK_H + safeBottom;
  const fullH = Math.max(collapsedH, containerHeight - topReserve);
  // Half: half the map area, but leaving at least MIN_MAP_H of map visible
  // under the search box on short screens (phones held sideways).
  const halfH = Math.min(fullH, Math.max(collapsedH + 48, Math.min(Math.round(containerHeight * 0.5), containerHeight - topReserve - MIN_MAP_H)));
  const heightOf = (s: SheetSnap) => (s === "collapsed" ? collapsedH : s === "half" ? halfH : fullH);

  // While dragging, the height follows the finger; on release it settles.
  const [dragH, setDragH] = useState<number | null>(null);
  const drag = useRef<{ startY: number; startH: number; moved: boolean } | null>(null);
  const suppressClick = useRef(false);
  const height = Math.round(dragH ?? heightOf(snap));

  useLayoutEffect(() => {
    onHeightChange?.(height);
  }, [height, onHeightChange]);

  const step = (dir: 1 | -1) => {
    const i = ORDER.indexOf(snap) + dir;
    if (i >= 0 && i < ORDER.length) onSnapChange(ORDER[i]);
  };

  const onPointerDown = (e: PointerEvent<HTMLButtonElement>) => {
    if (e.button !== 0) return;
    drag.current = { startY: e.clientY, startH: height, moved: false };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: PointerEvent<HTMLButtonElement>) => {
    const d = drag.current;
    if (!d) return;
    const dy = d.startY - e.clientY;
    if (!d.moved && Math.abs(dy) < 6) return;
    d.moved = true;
    setDragH(Math.min(fullH, Math.max(collapsedH, d.startH + dy)));
  };
  const onPointerUp = (e: PointerEvent<HTMLButtonElement>) => {
    const d = drag.current;
    drag.current = null;
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
    if (!d?.moved) return;
    suppressClick.current = true;
    const h = dragH ?? d.startH;
    const nearest = ORDER.reduce((a, b) => (Math.abs(heightOf(b) - h) < Math.abs(heightOf(a) - h) ? b : a));
    setDragH(null);
    onSnapChange(nearest);
  };
  const onClick = () => {
    if (suppressClick.current) {
      suppressClick.current = false;
      return;
    }
    // Collapsed → half → full → collapsed.
    onSnapChange(snap === "full" ? "collapsed" : ORDER[ORDER.indexOf(snap) + 1]);
  };
  const onKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "ArrowUp") step(1);
    else if (e.key === "ArrowDown") step(-1);
    else if (e.key === "Escape" && snap !== "collapsed") onSnapChange("collapsed");
    else return;
    e.preventDefault();
  };

  const open = snap !== "collapsed" || dragH !== null;
  const hint = snap === "collapsed" ? "Show details" : snap === "half" ? "Show more" : "Collapse";

  return (
    <section
      aria-label="Map details"
      data-tour="sheet"
      className={`absolute inset-x-0 bottom-0 z-[1003] flex flex-col surface-dialog rounded-b-none text-card-foreground border-t shadow-[0_-8px_24px_rgba(0,0,0,0.35)] ${dragH === null ? "transition-[height] duration-300 ease-out" : ""}`}
      style={{ height, backdropFilter: "blur(14px)", WebkitBackdropFilter: "blur(14px)" }}
    >
      <button
        type="button"
        aria-expanded={snap !== "collapsed"}
        aria-controls={contentId}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onClick={onClick}
        onKeyDown={onKeyDown}
        className="shrink-0 w-full touch-none select-none flex flex-col items-center px-4 pt-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
        style={{ height: SHEET_PEEK_H }}
      >
        <span aria-hidden className="h-1 w-10 rounded-full bg-foreground/30" />
        <span className="flex-1 w-full min-w-0 flex items-center gap-2 text-[14px]">{peek}</span>
        <span className="sr-only">{hint}</span>
      </button>

      <div id={contentId} hidden={!open} className="flex-1 min-h-0 flex flex-col">
        {header}
        <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain thin-scrollbar" style={{ paddingBottom: safeBottom }}>
          {children}
        </div>
      </div>
    </section>
  );
}
