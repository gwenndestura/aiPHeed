import { useEffect, useState } from "react";

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

/** In the header from 1024px up; below that, PSTClockMenuRow shows it in the menu. */
export function PSTClock() {
  const now = useNow();
  return (
    <div
      className="hidden lg:flex flex-col items-end leading-tight px-2.5 py-1 rounded-md bg-secondary/30 border border-border/30"
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

/** The clock as a menu section, below 1024px where the header has no room for it. */
export function PSTClockMenuRow() {
  const now = useNow();
  return (
    <div className="lg:hidden pb-3 mb-3 border-b border-border/40 px-2" title="Philippine Standard Time (UTC+8)">
      <p className="text-[9px] uppercase tracking-widest text-muted-foreground/60 font-semibold mb-1">
        Philippine Standard Time
      </p>
      <p className="font-mono-num text-[12px] tabular-nums text-foreground/90">
        {fmtDate(now)} · {fmtTime(now)}
      </p>
    </div>
  );
}
