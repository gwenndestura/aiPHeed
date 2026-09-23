import { useState } from "react";
import { Search } from "lucide-react";
import { useSearch } from "@/lib/queries";
import type { SearchHit } from "@/lib/apiTypes";

export function MapSearch() {
  const [searchQ, setSearchQ] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const { data } = useSearch(searchQ);
  const results = data?.data ?? [];

  const onPick = (r: SearchHit) => {
    setSearchQ("");
    setSearchOpen(false);
    window.dispatchEvent(
      new CustomEvent("aipheed:focus-region", {
        detail: r.type === "province" ? { provinceId: r.id } : { municipalityId: r.id },
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
              key={`${r.type}-${r.id}`}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => onPick(r)}
              className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-secondary/60 transition-colors"
            >
              <span className="text-[11px] font-medium">{r.name}</span>
              <span className="text-[9px] uppercase tracking-wider text-muted-foreground/70">
                {r.type === "province" ? "Province" : "Municipality"} · {r.type === "province" ? "CALABARZON" : r.provinceName}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
