import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { useAuth } from "@/lib/auth";
import { useConfig } from "@/lib/queries";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { COMPACT_QUERY, MEDIUM_QUERY } from "@/lib/breakpoints";
import { isTourDone, markTourDone, TOUR_LAYOUT_EVENT, TOUR_START_EVENT, type TourLayout } from "@/lib/tour";

/**
 * Guided tour of the map page for first-time public visitors.
 *
 * Starts by itself once per browser (lib/tour.ts), after the map has loaded,
 * and never for a signed-in admin. "Take the tour" in the menu or in About &
 * Methodology replays it. Each step dims the page, outlines one element
 * (marked data-tour="…" in MapDashboard and the header) and explains it in a
 * small card; on phones the card sits at the top or bottom edge, clear of it.
 */

type Layout = "phone" | "tablet" | "desktop";

interface Step {
  title: string;
  body: (layout: Layout, cutoff: string, linksInMenu: boolean) => ReactNode;
  /** A data-tour name, "provinces" (the outline of the CALABARZON map), or none (centred card). */
  target?: (layout: Layout) => string;
  /** Panel or sheet the step needs on screen. */
  layout?: TourLayout;
}

const STEPS: Step[] = [
  {
    title: "Welcome to aiPHeed",
    body: () =>
      "aiPHeed shows quarterly forecasts of food insecurity risk for the five provinces of CALABARZON. The forecasts are model estimates, reviewed by Department of Agriculture staff before they are published.",
    layout: { panel: "summary", sheet: "collapsed" },
  },
  {
    title: "The map",
    body: (l) =>
      `Each province is coloured by its forecast risk level. ${l === "phone" ? "Tap" : "Click"} a province to see its details.`,
    target: () => "provinces",
    layout: { sheet: "collapsed" },
  },
  {
    title: "Reading the colours",
    body: (_l, cutoff) =>
      `Yellow means low risk. Red means high risk: a risk score of ${cutoff} or more, on a scale from 0 to 1.`,
    target: () => "legend",
    layout: { sheet: "collapsed" },
  },
  {
    title: "Province summary",
    body: (l) =>
      `${l === "phone" ? "The Summary tab" : "This panel"} shows the regional picture. Select a province to see its risk score, its change from the previous quarter and its population.`,
    target: (l) => (l === "phone" ? "sheet" : "summary"),
    layout: { panel: "summary", sheet: "half" },
  },
  {
    title: "Why this risk",
    body: (l) =>
      `${l === "phone" ? "The Why tab" : "This panel"} lists the factors pushing the risk up or down, such as food prices or the weather, and the news articles behind them.`,
    target: (l) => (l === "phone" ? "sheet" : "why"),
    layout: { panel: "why", sheet: "half" },
  },
  {
    title: "Choose a quarter",
    body: (l) =>
      l === "phone"
        ? "Pick a quarter here. Forecast quarters have a dashed outline, and Current marks the quarter we are in now. History lists every quarter."
        : "Pick a quarter on the timeline. The solid line marks observed quarters, the dashed line forecasts, and Today marks where we are now. View history lists every quarter.",
    target: () => "timeline",
    layout: { panel: "summary", sheet: "collapsed" },
  },
  {
    title: "Search",
    body: () => "Type the name of a province, city or municipality to find it on the map.",
    target: () => "search",
    layout: { sheet: "collapsed" },
  },
  {
    title: "Data and charts",
    body: (_l, _c, linksInMenu) =>
      `${linksInMenu ? "Open the menu for the Data and Visualization pages." : "Two more pages:"} Data lists every province in a table you can export as CSV. Visualization draws trend charts you can download as PNG or PDF.`,
    target: () => "pages",
    layout: { sheet: "collapsed" },
  },
  {
    title: "About and feedback",
    body: () =>
      "About & Methodology explains how the forecasts are made and their limits. Send Feedback tells us how the site worked for you. You can replay this tour from About & Methodology or the menu.",
    target: () => "about",
    layout: { panel: "summary", sheet: "full" },
  },
];

const PAD = 6; // space between the outline and the element
const GAP = 12; // between the card and the edge of the screen or the outline

interface Box { top: number; left: number; width: number; height: number }

const visible = (el: Element) => {
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  return r.width > 0 && r.height > 0 && cs.visibility !== "hidden";
};

/** Where a step's element is on screen, with padding, kept inside the window. */
function measure(name: string | undefined): Box | null {
  if (!name) return null;
  let r: { top: number; left: number; right: number; bottom: number } | null = null;
  if (name === "provinces") {
    // The CALABARZON outline: the union of the province shapes, within the map.
    const shapes = [...document.querySelectorAll(".leaflet-overlay-pane path.leaflet-interactive")].map((p) => p.getBoundingClientRect()).filter((b) => b.width > 0);
    const mapEl = document.querySelector('[data-tour="map"]');
    if (mapEl) {
      // The map area the panels leave uncovered.
      const m = mapEl.getBoundingClientRect();
      const clip = { top: m.top, left: m.left, right: m.right, bottom: m.bottom };
      const panel = (n: string) => [...document.querySelectorAll(`[data-tour="${n}"]`)].find(visible)?.getBoundingClientRect();
      const left = panel("summary"), right = panel("why"), sheet = panel("sheet");
      if (left && left.left <= clip.left + 1) clip.left = Math.max(clip.left, left.right);
      if (right && right.right >= clip.right - 1) clip.right = Math.min(clip.right, right.left);
      if (sheet) clip.bottom = Math.min(clip.bottom, sheet.top);
      r = shapes.length
        ? shapes.reduce((a, b) => ({ top: Math.min(a.top, b.top), left: Math.min(a.left, b.left), right: Math.max(a.right, b.right), bottom: Math.max(a.bottom, b.bottom) }), { top: Infinity, left: Infinity, right: -Infinity, bottom: -Infinity })
        : clip;
      r = { top: Math.max(r.top, clip.top), left: Math.max(r.left, clip.left), right: Math.min(r.right, clip.right), bottom: Math.min(r.bottom, clip.bottom) };
    }
  } else {
    const el = [...document.querySelectorAll(`[data-tour="${name}"]`)].find(visible);
    if (el) r = el.getBoundingClientRect();
  }
  if (!r) return null;
  const vw = window.innerWidth, vh = window.innerHeight;
  const top = Math.max(2, r.top - PAD), left = Math.max(2, r.left - PAD);
  const bottom = Math.min(vh - 2, r.bottom + PAD), right = Math.min(vw - 2, r.right + PAD);
  if (bottom <= top || right <= left) return null;
  return { top, left, width: right - left, height: bottom - top };
}

interface CardPos { top: number; left: number; width: number }

/** Card widths: desktop and tablet; phones across the screen; phones held sideways, at a side edge. */
const DESKTOP_W = 340;
const PHONE_MAX_W = 640;
const SIDE_W = 300;
const MIN_SIDE_W = 240;

/**
 * The card's position and width: beside, below or above the outline. On
 * phones, the top or bottom edge, whichever leaves the outline uncovered;
 * held sideways (too short for that), a narrower card at the left or right.
 */
function place(target: Box | null, cardH: number, phone: boolean): CardPos {
  const vw = window.innerWidth, vh = window.innerHeight;
  if (phone) {
    const full = Math.min(vw - 2 * GAP, PHONE_MAX_W);
    const atBottom = { top: vh - cardH - GAP, left: (vw - full) / 2, width: full };
    const atTop = { top: GAP, left: (vw - full) / 2, width: full };
    if (!target) return atBottom;
    const above = target.top - GAP;
    const below = vh - (target.top + target.height) - GAP;
    if (below >= cardH) return atBottom;
    if (above >= cardH) return atTop;
    const sideTop = Math.max(GAP, (vh - cardH) / 2);
    if (vw - (target.left + target.width) >= SIDE_W + 2 * GAP) return { top: sideTop, left: vw - SIDE_W - GAP, width: SIDE_W };
    if (target.left >= SIDE_W + 2 * GAP) return { top: sideTop, left: GAP, width: SIDE_W };
    return below >= above ? atBottom : atTop;
  }
  const card = { w: DESKTOP_W, h: cardH };
  const centreX = (vw - card.w) / 2;
  if (!target) return { top: Math.max(GAP, (vh - card.h) / 2), left: centreX, width: card.w };
  const above = target.top - GAP;
  const below = vh - (target.top + target.height) - GAP;
  const clampX = (x: number) => Math.min(Math.max(GAP, x), vw - card.w - GAP);
  const clampY = (y: number) => Math.min(Math.max(GAP, y), vh - card.h - GAP);
  const right = { fits: vw - (target.left + target.width) - GAP >= card.w + GAP, pos: { top: clampY(target.top), left: target.left + target.width + GAP } };
  const left = { fits: target.left - GAP >= card.w + GAP, pos: { top: clampY(target.top), left: target.left - card.w - GAP } };
  const midX = clampX(target.left + target.width / 2 - card.w / 2);
  const down = { fits: below >= card.h + GAP, pos: { top: target.top + target.height + GAP, left: midX } };
  const up = { fits: above >= card.h + GAP, pos: { top: target.top - card.h - GAP, left: midX } };
  const order = target.height > target.width ? [right, left, down, up] : [down, up, right, left];
  const fit = order.find((o) => o.fits);
  if (fit) return { ...fit.pos, width: card.w };
  // No room for the full card: a narrower one beside the outline, on the roomier side.
  const roomRight = vw - (target.left + target.width) - 2 * GAP;
  const roomLeft = target.left - 2 * GAP;
  const room = Math.max(roomRight, roomLeft);
  if (room >= MIN_SIDE_W) {
    const w = Math.min(card.w, room);
    return { top: clampY(target.top), left: roomRight >= roomLeft ? vw - w - GAP : GAP, width: w };
  }
  return { top: vh - card.h - GAP, left: vw - card.w - GAP, width: card.w };
}

/** Calls `ready` once the map page has drawn its timeline and provinces (or gave up waiting). */
function whenMapReady(ready: () => void): () => void {
  const started = Date.now();
  let timer = 0;
  const check = () => {
    const timeline = !!document.querySelector('[data-tour="timeline"]');
    const shapes = !!document.querySelector(".leaflet-overlay-pane path.leaflet-interactive");
    const waited = Date.now() - started;
    if ((timeline && shapes) || (timeline && waited > 6000) || waited > 12000) {
      timer = window.setTimeout(ready, 500); // let the panels finish sliding in
    } else {
      timer = window.setTimeout(check, 250);
    }
  };
  check();
  return () => window.clearTimeout(timer);
}

export function MapTour() {
  const { status } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { data: config } = useConfig();
  const phone = useMediaQuery(COMPACT_QUERY);
  const tablet = useMediaQuery(MEDIUM_QUERY);
  const reduceMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
  const layout: Layout = phone ? "phone" : tablet ? "tablet" : "desktop";
  const cutoff = (config?.thresholds.riskDisplayCutoff ?? 0.5).toFixed(2);

  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [box, setBox] = useState<Box | null>(null);
  const [cardPos, setCardPos] = useState<CardPos | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const primaryRef = useRef<HTMLButtonElement>(null);
  const step = STEPS[index];
  // Below 768px the page links are folded into the menu (the header's nav is hidden).
  const [linksInMenu, setLinksInMenu] = useState(false);
  const last = index === STEPS.length - 1;

  const start = useCallback(() => {
    setIndex(0);
    setOpen(true);
  }, []);

  // First visit: once the map has loaded, for visitors who are not signed in.
  useEffect(() => {
    if (status !== "anonymous" || isTourDone()) return;
    return whenMapReady(() => {
      if (!isTourDone()) start();
    });
  }, [status, start]);

  // "Take the tour" from another page arrives here with state { tour: true }.
  // The request is cleared from the history entry at once (so a reload does not
  // replay it); the start it schedules is cancelled only if the page goes away.
  const replayRequested = !!(location.state as { tour?: boolean } | null)?.tour;
  const pendingReplay = useRef<(() => void) | null>(null);
  useEffect(() => {
    if (!replayRequested) return;
    navigate(location.pathname, { replace: true, state: null });
    pendingReplay.current?.();
    pendingReplay.current = whenMapReady(start);
  }, [replayRequested, navigate, location.pathname, start]);
  useEffect(() => () => pendingReplay.current?.(), []);

  // "Take the tour" on this page.
  useEffect(() => {
    window.addEventListener(TOUR_START_EVENT, start);
    return () => window.removeEventListener(TOUR_START_EVENT, start);
  }, [start]);

  // Put the step's panel or sheet on screen; bring its element into view.
  useEffect(() => {
    if (!open) return;
    if (step.layout) window.dispatchEvent(new CustomEvent<TourLayout>(TOUR_LAYOUT_EVENT, { detail: step.layout }));
    const nav = document.querySelector('header nav[data-tour="pages"]');
    setLinksInMenu(!nav || !visible(nav));
    const name = step.target?.(layout);
    if (!name || name === "provinces") return;
    const t = window.setTimeout(() => {
      const el = [...document.querySelectorAll(`[data-tour="${name}"]`)].find(visible);
      el?.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
    }, 350);
    return () => window.clearTimeout(t);
  }, [open, step, layout, reduceMotion]);

  // Follow the element while panels slide, the sheet moves or the window resizes.
  useLayoutEffect(() => {
    if (!open) return;
    let raf = 0;
    let lastScroll = 0;
    const tick = () => {
      const name = step.target?.(layout);
      const b = measure(name);
      if (!b && name && name !== "provinces" && performance.now() - lastScroll > 400) {
        // Present but scrolled out of view: bring it in.
        const el = [...document.querySelectorAll(`[data-tour="${name}"]`)].find(visible);
        if (el) {
          lastScroll = performance.now();
          el.scrollIntoView({ block: "nearest" });
        }
      }
      setBox((prev) => (prev && b && Math.abs(prev.top - b.top) < 0.5 && Math.abs(prev.left - b.left) < 0.5 && Math.abs(prev.width - b.width) < 0.5 && Math.abs(prev.height - b.height) < 0.5) || (!prev && !b) ? prev : b);
      const card = cardRef.current;
      if (card) {
        const pos = place(b, card.offsetHeight, layout === "phone");
        setCardPos((prev) => (prev && Math.abs(prev.top - pos.top) < 0.5 && Math.abs(prev.left - pos.left) < 0.5 && prev.width === pos.width ? prev : pos));
      }
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, [open, step, layout]);

  // Each step: focus on the main button, so Enter moves on. Waits for the card
  // to be placed: until then it is transparent, and focus must land after.
  const placed = cardPos !== null;
  useEffect(() => {
    if (open && placed) primaryRef.current?.focus();
  }, [open, index, placed]);

  const close = useCallback(() => {
    markTourDone();
    setOpen(false);
    setBox(null);
    setCardPos(null);
    // Back to the page's usual layout: summary panel, phone sheet collapsed.
    window.dispatchEvent(new CustomEvent<TourLayout>(TOUR_LAYOUT_EVENT, { detail: { panel: "summary", sheet: "collapsed" } }));
  }, []);

  const next = () => (last ? close() : setIndex((i) => i + 1));
  const back = () => setIndex((i) => Math.max(0, i - 1));

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const onButton = (e.target as HTMLElement).tagName === "BUTTON";
    if (e.key === "ArrowRight" || (e.key === "Enter" && !onButton)) {
      e.preventDefault();
      next();
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      back();
    }
  };

  const motion = reduceMotion ? "" : "transition-[top,left,width,height] duration-300 ease-out";
  const btn = "h-9 compact:h-11 px-3 rounded-md text-[13px] compact:text-[14px] font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card";

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(o) => !o && close()}>
      <DialogPrimitive.Portal>
        {/* The dimmed page with a clear window over the step's element. */}
        <div aria-hidden className="fixed inset-0 z-[2400]" style={box ? undefined : { background: "rgba(0,0,0,0.62)" }}>
          {box && (
            <div
              className={`absolute rounded-md pointer-events-none ${motion}`}
              style={{
                ...box,
                boxShadow: "0 0 0 9999px rgba(0,0,0,0.62)",
                outline: "2px solid hsl(var(--primary))",
                outlineOffset: 0,
              }}
            />
          )}
        </div>
        <DialogPrimitive.Content
          ref={cardRef}
          onKeyDown={onKeyDown}
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            primaryRef.current?.focus();
          }}
          // Esc skips the tour; a click on the dimmed page does nothing.
          onEscapeKeyDown={(e) => {
            e.preventDefault();
            close();
          }}
          onInteractOutside={(e) => e.preventDefault()}
          className={`fixed z-[2500] bg-card text-card-foreground border border-border/60 rounded-xl shadow-2xl p-5 focus:outline-none ${motion} ${cardPos ? "" : "opacity-0"}`}
          style={cardPos ?? { top: 0, left: 0, width: layout === "phone" ? Math.min(window.innerWidth - 2 * GAP, PHONE_MAX_W) : DESKTOP_W }}
        >
          <p className="text-[12px] text-foreground/75 tabular-nums">
            Step {index + 1} of {STEPS.length}
          </p>
          <DialogPrimitive.Title className="mt-1 text-[16px] font-semibold tracking-tight">{step.title}</DialogPrimitive.Title>
          <DialogPrimitive.Description className="mt-2 text-[14px] leading-snug text-foreground/85">
            {step.body(layout, cutoff, linksInMenu)}
          </DialogPrimitive.Description>
          {/* Read out when the step changes; the dialog's label is read only once. */}
          <p className="sr-only" aria-live="polite">
            {`Step ${index + 1} of ${STEPS.length}: ${step.title}`}
          </p>

          <div className="mt-4 flex items-center gap-2">
            <button type="button" onClick={close} className={`${btn} -ml-2 text-foreground/80 hover:text-foreground underline-offset-2 hover:underline`}>
              Skip
            </button>
            <span className="flex-1" />
            {index > 0 && (
              <button type="button" onClick={back} className={`${btn} border border-border/60 hover:bg-secondary/60`}>
                Back
              </button>
            )}
            <button ref={primaryRef} type="button" onClick={next} className={`${btn} bg-primary text-[#0D0F14] hover:bg-primary/90`}>
              {last ? "Start exploring" : "Next"}
            </button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
