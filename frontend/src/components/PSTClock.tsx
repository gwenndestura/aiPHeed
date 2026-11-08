import { useEffect, useState } from "react";
import { MenuSection } from "./MenuSection";

function fmtDate(d: Date) {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "Asia/Manila",
  }).format(d);
}

function fmtTime(d: Date) {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "Asia/Manila",
    hour12: false,
  }).format(d);
}

function useNow() {
  const [now, setNow] = useState<Date>(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

/**
 * Where the clock moves from the menu to the header: 1024px, or 1280px in
 * the admin headers, whose five links need the room.
 */
type ShowFrom = "lg" | "xl";

/** In the header from `from` up; below that, PSTClockMenuRow shows it in the menu. */
export function PSTClock({ from = "lg" }: { from?: ShowFrom }) {
  const now = useNow();
  return (
    <div
      className={`hidden ${from === "xl" ? "xl:flex" : "lg:flex"} flex-col items-end leading-tight px-3.5 py-1 rounded-full bg-secondary/60`}
      title="Philippine Standard Time (UTC+8)"
    >
      <span className="text-[8px] uppercase tracking-[0.18em] text-muted-foreground/70 font-semibold">
        Philippine Standard Time
      </span>
      <span className="font-mono-num text-[10px] tabular-nums text-foreground/90">
        {fmtDate(now)} · {fmtTime(now)}
      </span>
    </div>
  );
}

/** The clock as a menu section, below `from` where the header has no room for it. */
export function PSTClockMenuRow({ from = "lg" }: { from?: ShowFrom }) {
  const now = useNow();
  return (
    <MenuSection heading="Philippine Standard Time" className={from === "xl" ? "xl:hidden" : "lg:hidden"} title="Philippine Standard Time (UTC+8)">
      <p className="px-2 pb-1.5 font-mono-num text-[12px] tabular-nums text-foreground/90">
        {fmtDate(now)} · {fmtTime(now)}
      </p>
    </MenuSection>
  );
}
