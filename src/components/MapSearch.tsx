import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { regionsData, municipalitiesData } from "@/data/mockData";

export function MapSearch() {
  const [searchQ, setSearchQ] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  const results = useMemo(() => {
    const q = searchQ.trim().toLowerCase();
    if (!q) return [];
    const provs = regionsData
      .filter((r) => r.name.toLowerCase().includes(q))
      .map((r) => ({ kind: "Province" as const, id: r.id, name: r.name, hint: "CALABARZON" }));
    const munis = municipalitiesData
      .filter((m) => m.name.toLowerCase().includes(q))
      .slice(0, 12)
      .map((m) => ({ kind: "Municipality" as const, id: m.id, name: m.name, hint: m.provinceName }));
    return [...provs, ...munis].slice(0, 16);
  }, [searchQ]);

  const onPick = (r: typeof results[number]) => {
    setSearchQ("");
    setSearchOpen(false);
    window.dispatchEvent(
      new CustomEvent("aipheed:focus-region", {
        detail: r.kind === "Province" ? { provinceId: r.id } : { municipalityId: r.id },
      })
    );
  };

  return (
    <div className="relative w-[240px]">
      <div className="relative bg-card/85 border border-border/60 shadow-lg rounded-md" style={{ backdropFilter: "blur(14px)", WebkitBackdropFilter: "blur(14px)" }}>
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground/70 pointer-events-none" />
        <input
          type="search"
          value={searchQ}
          onFocus={() => setSearchOpen(true)}
          onChange={(e) => {
            setSearchQ(e.target.value);
            setSearchOpen(true);
          }}
          onBlur={() => setTimeout(() => setSearchOpen(false), 200)}
          placeholder="Search provinces, municipalities…"
          className="w-full h-7 pl-7 pr-2.5 text-[11px] bg-transparent rounded-md focus:outline-none placeholder:text-muted-foreground/60"
        />
      </div>
      {searchOpen && results.length > 0 && (
        <div className="absolute top-9 left-0 right-0 max-h-72 overflow-y-auto bg-card border border-border/60 rounded-lg shadow-xl z-[1100]">
          {results.map((r) => (
            <button
              key={`${r.kind}-${r.id}`}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => onPick(r)}
              className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-secondary/60 transition-colors"
            >
              <span className="text-[11px] font-medium">{r.name}</span>
              <span className="text-[9px] uppercase tracking-wider text-muted-foreground/70">
                {r.kind} · {r.hint}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
