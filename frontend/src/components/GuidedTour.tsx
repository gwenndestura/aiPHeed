import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { useAuth } from "@/lib/auth";
import { useConfig } from "@/lib/queries";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { COMPACT_QUERY, MEDIUM_QUERY } from "@/lib/breakpoints";
import { isTourDone, markTourDone, tourElement, visible, TOUR_LAYOUT_EVENT, TOUR_START_EVENT, type TourId, type TourLayout } from "@/lib/tour";

/**
 * A guided tour of one page for first-time public visitors (MapTour,
 * DataTour, VizTour).
 *
 * Starts by itself once per browser (lib/tour.ts), once the page has loaded,
 * and never for a signed-in admin. "Take the tour" in the menu replays the
 * tour of the page being viewed. Each step dims the page, outlines one element
 * (marked data-tour="…") and explains it in a small card; on phones the card
 * sits at the top or bottom edge, clear of it.
 */

export type Layout = "phone" | "tablet" | "desktop";

/** What a step's text may depend on. */
export interface StepContext {
  layout: Layout;
  /** The High risk cutoff and the alert threshold, e.g. "0.50" and "0.60". */
  cutoff: string;
  alert: string;
  /** Below 768px the page links are folded into the menu (the header's nav is hidden). */
  linksInMenu: boolean;
}

/** An area on screen, in viewport pixels. */
export interface Area { top: number; left: number; right: number; bottom: number }

export interface Step {
  title: string;
  body: (ctx: StepContext) => ReactNode;
  /** The data-tour name of the element to outline and bring into view; none for a centred card. */
  target?: (layout: Layout) => string | undefined;
  /** Outlines this area instead (e.g. several elements together); null falls back to `target`. */
  area?: (layout: Layout) => Area | null;
  /** Panel, sheet, card or tab the step needs on screen (TOUR_LAYOUT_EVENT). */
  layout?: TourLayout;
  /** Where to scroll the element to: "nearest" (just into view) unless the text below it matters too. */
  scroll?: ScrollLogicalPosition;
}

export interface TourDef {
  id: TourId;
  steps: Step[];
  /** Calls `ready` once the page can be toured (or waiting is pointless); returns a cancel. */
  whenReady: (ready: () => void) => () => void;
  /** Sent when the tour closes, to put the page back in its usual layout. */
  resetLayout?: TourLayout;
  /**
   * The page scrolls under the tour (Data, Visualization): elements come into
   * view with room for the outline, and on phones an element the card would
   * cover is scrolled to the far edge of the screen, clear of the card.
   */
  pageScrolls?: boolean;
}

const PAD = 6; // space between the outline and the element
const GAP = 12; // between the card and the edge of the screen or the outline
const SCROLL_MARGIN = PAD + 6; // pageScrolls: room left around an element scrolled into view

/** scrollIntoView, keeping `margin` pixels clear around the element. */
function scrollToElement(el: Element, block: ScrollLogicalPosition, behavior: ScrollBehavior, margin: number) {
  const style = el instanceof HTMLElement ? el.style : null;
  const before = style?.scrollMargin ?? "";
  if (style && margin) style.scrollMargin = `${margin}px`;
  el.scrollIntoView({ block, behavior });
  if (style && margin) style.scrollMargin = before;
}

interface Box { top: number; left: number; width: number; height: number }

/** Where a step's outline goes, with padding, kept inside the window. */
function measure(step: Step, layout: Layout): Box | null {
  let r: Area | null = step.area?.(layout) ?? null;
  if (!r) {
    const name = step.target?.(layout);
    const el = name ? tourElement(name) : undefined;
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

/** The card, placed at `pos`, covers part of the outline. */
const covers = (pos: CardPos, cardH: number, b: Box) =>
  pos.top < b.top + b.height && b.top < pos.top + cardH && pos.left < b.left + b.width && b.left < pos.left + pos.width;

export function GuidedTour({ tour }: { tour: TourDef }) {
  const { id, steps, whenReady, resetLayout, pageScrolls = false } = tour;
  const margin = pageScrolls ? SCROLL_MARGIN : 0;
  const { status } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { data: config } = useConfig();
  const phone = useMediaQuery(COMPACT_QUERY);
  const tablet = useMediaQuery(MEDIUM_QUERY);
  const reduceMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
  const layout: Layout = phone ? "phone" : tablet ? "tablet" : "desktop";
  const cutoff = (config?.thresholds.riskDisplayCutoff ?? 0.5).toFixed(2);
  const alert = (config?.thresholds.alertThreshold ?? 0.6).toFixed(2);

  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [box, setBox] = useState<Box | null>(null);
  const [cardPos, setCardPos] = useState<CardPos | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const primaryRef = useRef<HTMLButtonElement>(null);
  const step = steps[index];
  const [linksInMenu, setLinksInMenu] = useState(false);
  const last = index === steps.length - 1;

  const start = useCallback(() => {
    setIndex(0);
    setOpen(true);
  }, []);

  // First visit: once the page has loaded, for visitors who are not signed in.
  useEffect(() => {
    if (status !== "anonymous" || isTourDone(id)) return;
    return whenReady(() => {
      if (!isTourDone(id)) start();
    });
  }, [status, id, whenReady, start]);

  // "Take the tour" from another page arrives here with state { tour: true }.
  // The request is cleared from the history entry at once (so a reload does not
  // replay it); the start it schedules is cancelled only if the page goes away.
  const replayRequested = !!(location.state as { tour?: boolean } | null)?.tour;
  const pendingReplay = useRef<(() => void) | null>(null);
  useEffect(() => {
    if (!replayRequested) return;
    navigate(location.pathname, { replace: true, state: null });
    pendingReplay.current?.();
    pendingReplay.current = whenReady(start);
  }, [replayRequested, navigate, location.pathname, whenReady, start]);
  useEffect(() => () => pendingReplay.current?.(), []);

  // "Take the tour" on this page.
  useEffect(() => {
    const onStart = (e: Event) => {
      if ((e as CustomEvent<TourId>).detail === id) start();
    };
    window.addEventListener(TOUR_START_EVENT, onStart);
    return () => window.removeEventListener(TOUR_START_EVENT, onStart);
  }, [id, start]);

  // Put the step's panel, card or tab on screen; bring its element into view.
  useEffect(() => {
    if (!open) return;
    if (step.layout) window.dispatchEvent(new CustomEvent<TourLayout>(TOUR_LAYOUT_EVENT, { detail: step.layout }));
    const nav = document.querySelector('header nav[data-tour="pages"]');
    setLinksInMenu(!nav || !visible(nav));
    const name = step.target?.(layout);
    if (!name) return;
    const t = window.setTimeout(() => {
      const el = tourElement(name);
      if (!el) return;
      let block = step.scroll ?? "nearest";
      // Phones: where the card would cover the element, scroll it to the screen edge away from the card.
      const b = measure(step, layout);
      const cardH = cardRef.current?.offsetHeight ?? 0;
      if (pageScrolls && layout === "phone" && b && cardH) {
        const pos = place(b, cardH, true);
        if (covers(pos, cardH, b)) block = pos.top < b.top ? "end" : "start";
      }
      scrollToElement(el, block, reduceMotion ? "auto" : "smooth", margin);
    }, 350);
    return () => window.clearTimeout(t);
  }, [open, step, layout, reduceMotion, pageScrolls, margin]);

  // Follow the element while panels slide, the sheet moves or the window resizes.
  useLayoutEffect(() => {
    if (!open) return;
    let raf = 0;
    let lastScroll = 0;
    const shown = performance.now();
    let cleared = false;
    const tick = () => {
      const name = step.target?.(layout);
      const b = measure(step, layout);
      if (!b && name && performance.now() - lastScroll > 400) {
        // Present but scrolled out of view: bring it in.
        const el = tourElement(name);
        if (el) {
          lastScroll = performance.now();
          scrollToElement(el, step.scroll ?? "nearest", "auto", margin);
        }
      }
      setBox((prev) => (prev && b && Math.abs(prev.top - b.top) < 0.5 && Math.abs(prev.left - b.left) < 0.5 && Math.abs(prev.width - b.width) < 0.5 && Math.abs(prev.height - b.height) < 0.5) || (!prev && !b) ? prev : b);
      const card = cardRef.current;
      if (card) {
        const pos = place(b, card.offsetHeight, layout === "phone");
        // Phones: the card still covers the outline once the step has settled (the
        // element grew, say). Once per step, scroll it to the edge away from the card.
        if (pageScrolls && layout === "phone" && b && name && !cleared && performance.now() - shown > 1200 && covers(pos, card.offsetHeight, b)) {
          cleared = true;
          const el = tourElement(name);
          if (el) scrollToElement(el, pos.top < b.top ? "end" : "start", "auto", margin);
        }
        setCardPos((prev) => (prev && Math.abs(prev.top - pos.top) < 0.5 && Math.abs(prev.left - pos.left) < 0.5 && prev.width === pos.width ? prev : pos));
      }
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, [open, step, layout, pageScrolls, margin]);

  // Each step: focus on the main button, so Enter moves on. Waits for the card
  // to be placed: until then it is transparent, and focus must land after.
  const placed = cardPos !== null;
  useEffect(() => {
    if (open && placed) primaryRef.current?.focus();
  }, [open, index, placed]);

  const close = useCallback(() => {
    markTourDone(id);
    setOpen(false);
    setBox(null);
    setCardPos(null);
    if (resetLayout) window.dispatchEvent(new CustomEvent<TourLayout>(TOUR_LAYOUT_EVENT, { detail: resetLayout }));
  }, [id, resetLayout]);

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
          className={`fixed z-[2500] bg-card text-card-foreground border edge-faint rounded-xl shadow-2xl p-5 [@media(max-height:500px)]:py-4 focus:outline-none ${motion} ${cardPos ? "" : "opacity-0"}`}
          style={cardPos ?? { top: 0, left: 0, width: layout === "phone" ? Math.min(window.innerWidth - 2 * GAP, PHONE_MAX_W) : DESKTOP_W }}
        >
          <p className="text-[12px] text-foreground/75 tabular-nums">
            Step {index + 1} of {steps.length}
          </p>
          <DialogPrimitive.Title className="mt-1 text-[16px] font-semibold tracking-tight">{step.title}</DialogPrimitive.Title>
          <DialogPrimitive.Description className="mt-2 text-[14px] leading-snug text-foreground/85">
            {step.body({ layout, cutoff, alert, linksInMenu })}
          </DialogPrimitive.Description>
          {/* Read out when the step changes; the dialog's label is read only once. */}
          <p className="sr-only" aria-live="polite">
            {`Step ${index + 1} of ${steps.length}: ${step.title}`}
          </p>

          {/* Phones held sideways (500px or less tall): a tighter card leaves more of the page in view. */}
          <div className="mt-4 [@media(max-height:500px)]:mt-3 flex items-center gap-2">
            <button type="button" onClick={close} className={`${btn} -ml-2 text-foreground/80 hover:text-foreground underline-offset-2 hover:underline`}>
              Skip
            </button>
            <span className="flex-1" />
            {index > 0 && (
              <button type="button" onClick={back} className={`${btn} border edge-control hover:bg-secondary/60`}>
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
