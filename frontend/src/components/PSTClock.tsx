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

export function PSTClock() {
  const [now, setNow] = useState<Date>(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      className="hidden md:flex flex-col items-end leading-tight px-2.5 py-1 rounded-md bg-secondary/30 border border-border/30"
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
