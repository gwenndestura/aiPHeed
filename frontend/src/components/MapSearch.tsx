import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { Search } from "lucide-react";
import { useSearch } from "@/lib/queries";
import type { SearchHit } from "@/lib/apiTypes";

/** Wait this long after the last keystroke before searching. */
const DEBOUNCE_MS = 150;

/** "City · Batangas", "Municipality · Cavite", "Province · CALABARZON". */
function placeLine(r: SearchHit): string {
  if (r.type === "province") return "Province · CALABARZON";
  return `${r.classification ?? "Municipality"} · ${r.provinceName ?? ""}`;
}

/**
 * Search for a province, city or municipality (a combobox: arrow keys move
 * the highlight, Enter picks it, or the best result when none is
 * highlighted, Escape closes the list). Picking one asks the map page to
 * select it (MapDashboard, "aipheed:focus-region"): a city or municipality
 * with its province, which loads the province's list first.
 *
 * `fill`: as wide as its container, 44px tall (the phone layout).
 */
export function MapSearch({ fill = false }: { fill?: boolean }) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  // Enter pressed before the results for the typed text arrived.
  const [enterPending, setEnterPending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const id = useId();
  const listId = `${id}-list`;
  const optionId = (i: number) => `${id}-opt-${i}`;

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(query), DEBOUNCE_MS);
    return () => window.clearTimeout(t);
  }, [query]);

  const { data, isFetching } = useSearch(debounced);
  const typed = query.trim();
  const loading = typed !== "" && (debounced.trim() !== typed || isFetching || !data);
  const results = typed && !loading ? data?.data ?? [] : [];
  const suggestions = results.length > 0 && results.every((r) => r.suggestion);
  const noMatch = typed !== "" && !loading && results.length === 0;
  const expanded = open && typed !== "" && (results.length > 0 || noMatch);

  // New results: nothing highlighted until the arrow keys are used.
  useEffect(() => setActive(-1), [debounced]);

  // Keep the highlighted option in view in a long list.
  useEffect(() => {
    if (active < 0) return;
    document.getElementById(optionId(active))?.scrollIntoView({ block: "nearest" });
    // optionId is derived from a stable id
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const pick = (r: SearchHit) => {
    setQuery("");
    setDebounced("");
    setOpen(false);
    setActive(-1);
    inputRef.current?.blur(); // phones: put the keyboard away to show the map
    window.dispatchEvent(
      new CustomEvent("aipheed:focus-region", {
        detail: r.type === "province" ? { provinceId: r.id } : { provinceId: r.provinceId, municipalityId: r.id },
      })
    );
  };

  // Enter: the highlighted result, else the best one; with none, the list says so.
  const choose = () => {
    if (!typed) return;
    if (loading) {
      setEnterPending(true);
      return;
    }
    setOpen(true);
    if (results.length) pick(results[active >= 0 ? active : 0]);
  };
  useEffect(() => {
    if (!enterPending || loading) return;
    setEnterPending(false);
    setOpen(true);
    if (results.length) pick(results[0]);
    // pick and results are read at the moment the results arrive
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enterPending, loading]);

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      if (results.length) setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      choose();
    } else if (e.key === "Escape") {
      if (open) {
        e.preventDefault();
        setOpen(false);
        setActive(-1);
      }
    }
  };

  return (
    <div className={`relative ${fill ? "w-full" : "w-[240px]"}`}>
      <div className="relative surface-float border rounded-full">
        <Search className={`absolute left-2.5 top-1/2 -translate-y-1/2 ${fill ? "h-4 w-4" : "h-3 w-3"} text-muted-foreground/70 pointer-events-none`} />
        <input
          ref={inputRef}
          type="search"
          role="combobox"
          aria-label="Search provinces, cities and municipalities"
          aria-autocomplete="list"
          aria-expanded={expanded}
          aria-controls={listId}
          aria-activedescendant={expanded && active >= 0 ? optionId(active) : undefined}
          autoComplete="off"
          value={query}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            setEnterPending(false);
          }}
          onKeyDown={onKeyDown}
          onBlur={() => setTimeout(() => setOpen(false), 200)}
          placeholder="Search provinces, municipalities…"
          className={`w-full ${fill ? "h-11 pl-9 text-[16px]" : "h-7 pl-7 text-[11px]"} pr-2.5 field-inset rounded-full focus:outline-none placeholder:text-muted-foreground/60`}
        />
      </div>

      {/* Results, read out as they change. */}
      <p className="sr-only" aria-live="polite">
        {!typed || loading ? "" : noMatch ? `No places match ${typed}` : `${results.length} ${suggestions ? "suggestions" : "results"}`}
      </p>

      {expanded && (
        <div className={`absolute ${fill ? "top-12" : "top-9"} left-0 right-0 max-h-72 overflow-y-auto surface-float border z-[1100]`}>
          {noMatch ? (
            <p className={`px-3 py-2 text-[11px] text-muted-foreground ${fill ? "min-h-11 flex items-center" : ""}`}>
              No places match "{typed}"
            </p>
          ) : (
            <>
              {suggestions && <p className="px-3 pt-2 pb-1 text-[10px] text-muted-foreground">Did you mean…</p>}
              <ul ref={listRef} id={listId} role="listbox" aria-label={suggestions ? "Did you mean" : "Places"}>
                {results.map((r, i) => (
                  <li
                    key={`${r.type}-${r.id}`}
                    id={optionId(i)}
                    role="option"
                    aria-selected={i === active}
                    onMouseDown={(e) => e.preventDefault()}
                    onMouseEnter={() => setActive(i)}
                    onClick={() => pick(r)}
                    className={`w-full flex items-center justify-between gap-x-3 px-3 py-2 text-left cursor-pointer border-l-2 transition-colors ${
                      i === active ? "bg-secondary border-primary" : "border-transparent hover:bg-secondary/60"
                    } ${fill ? "min-h-11 flex-wrap" : ""}`}
                  >
                    <span className="text-[11px] font-medium">{r.name}</span>
                    <span className="text-[9px] text-muted-foreground">{placeLine(r)}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
