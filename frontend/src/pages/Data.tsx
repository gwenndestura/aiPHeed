import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TopNavbar } from "@/components/TopNavbar";
import { DataTour } from "@/components/PageTours";
import { useQuarters, useProvinces } from "@/lib/queries";
import { selectableQuarters } from "@/lib/quarters";
import { RISK_COLORS, RISK_LABELS } from "@/data/types";
import type { ProvinceSummary } from "@/lib/apiTypes";
import { ArrowDown, ArrowUp, Download, Search } from "lucide-react";
import { StatusBadge, type RiskLevelKey } from "@/components/ui/status-badge";
import { formatSigned } from "@/components/ui/metric";
import { isLoadFailure, LOAD_ERROR_MESSAGE } from "@/lib/loadError";
import { writeStorage } from "@/lib/storage";

type SortKey = "name" | "riskScore" | "riskLevel" | "qoqChangePct" | "articleCount";

/** Phones: the table's sortable headings as one menu. */
const SORT_OPTIONS: { value: `${SortKey}:${"asc" | "desc"}`; label: string }[] = [
  { value: "riskScore:desc", label: "Sort: risk score, high to low" },
  { value: "riskScore:asc", label: "Sort: risk score, low to high" },
  { value: "name:asc", label: "Sort: province, A to Z" },
  { value: "name:desc", label: "Sort: province, Z to A" },
  { value: "qoqChangePct:desc", label: "Sort: quarter-on-quarter change, largest first" },
  { value: "qoqChangePct:asc", label: "Sort: quarter-on-quarter change, smallest first" },
  { value: "articleCount:desc", label: "Sort: articles, most first" },
  { value: "articleCount:asc", label: "Sort: articles, fewest first" },
  { value: "riskLevel:desc", label: "Sort: risk level, high first" },
  { value: "riskLevel:asc", label: "Sort: risk level, low first" },
];

export default function DataPage() {
  const navigate = useNavigate();
  const [sortKey, setSortKey] = useState<SortKey>("riskScore");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filterProv, setFilterProv] = useState<string>("all");
  const [filterRisk, setFilterRisk] = useState<string>("all");
  const [quarter, setQuarter] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState("");

  const { data: quartersRes, error: quartersError } = useQuarters("nowcast");
  const activeQuarter = quarter ?? quartersRes?.current;
  const { data: provincesRes, isLoading, error: provincesError } = useProvinces(activeQuarter, "nowcast");
  // A failed fetch is not an empty result: say so rather than "No rows".
  const loadFailed = isLoadFailure(quartersError) || isLoadFailure(provincesError);
  const rows = useMemo(() => (loadFailed ? [] : provincesRes?.data ?? []), [loadFailed, provincesRes]);

  const filtered = useMemo(() => {
    let r = rows.filter((row) => {
      if (filterProv !== "all" && row.name !== filterProv) return false;
      if (filterRisk !== "all" && row.riskLevel !== filterRisk) return false;
      if (search && !row.name.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
    r = [...r].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      if (typeof av === "number" && typeof bv === "number") return sortDir === "asc" ? av - bv : bv - av;
      return sortDir === "asc" ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
    });
    return r;
  }, [rows, sortKey, sortDir, filterProv, filterRisk, search]);

  const setSort = (k: SortKey) => {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir("desc"); }
  };

  const exportCsv = () => {
    const header = ["Province", "Quarter", "Risk Level Score", "Risk Level", "QoQ Change %", "Articles", "Status"];
    const csv = [
      header.join(","),
      ...filtered.map((r) =>
        [
          r.name,
          r.currentQuarter,
          r.riskScore?.toFixed(2) ?? "",
          r.riskLevel ?? "",
          r.qoqChangePct?.toFixed(1) ?? "",
          r.articleCount,
          r.withheld ? "Withheld" : "Published",
        ].join(",")
      ),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aipheed_data_${activeQuarter ?? "latest"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const goToRow = (r: ProvinceSummary) => {
    writeStorage("aipheed_focus", JSON.stringify({ provinceId: r.id }), "session");
    navigate("/dashboard");
  };

  const columns: { key: SortKey; label: string }[] = [
    { key: "name", label: "Province" },
    { key: "riskScore", label: "Risk score" },
    { key: "riskLevel", label: "Risk Level" },
    { key: "qoqChangePct", label: "Quarter-on-quarter change" },
    { key: "articleCount", label: "Articles" },
  ];

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden">
      <TopNavbar active="data" />

      <main className="flex-1 overflow-auto">
        <div className="p-6 compact:px-4 compact:py-5 max-w-7xl mx-auto">
          {/* Phones: title, then a full-width Export button. */}
          <div className="flex items-center justify-between mb-4 compact:flex-col compact:items-stretch compact:gap-3">
            <div>
              <h1 className="text-lg font-bold tracking-tight">Risk Data</h1>
              <p className="text-[11px] compact:text-[14px] text-muted-foreground">
                Province-level forecasts for {activeQuarter ?? "the latest quarter"}.{" "}
                <span className="compact:hidden">Click a row for details.</span>
                <span className="hidden compact:inline">Tap a province for details.</span>
              </p>
            </div>
            <button
              onClick={exportCsv}
              disabled={filtered.length === 0}
              data-tour="data-export"
              className="flex items-center justify-center gap-1.5 px-3 py-1.5 compact:h-11 compact:text-[14px] rounded-full bg-primary text-primary-foreground shadow-md text-[11px] font-bold hover:bg-primary/90 disabled:opacity-50"
            >
              <Download className="h-3.5 w-3.5" /> Export CSV
            </button>
          </div>

          {/* Filters: four in a row, two per row on phones (with a sort menu
              there, in place of the table's sortable headings). */}
          <div className="grid grid-cols-4 compact:grid-cols-2 gap-2 mb-4" data-tour="data-filters">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search province"
                aria-label="Search province"
                className="w-full h-8 compact:h-11 compact:text-[16px] pl-8 pr-2 text-[11px] bg-secondary/50 border border-border/40 rounded-full focus:outline-none focus:border-primary/50"
              />
            </div>
            <select value={filterProv} onChange={(e) => setFilterProv(e.target.value)} aria-label="Province" className="h-8 compact:h-11 compact:text-[16px] min-w-0 text-[11px] bg-secondary/50 border border-border/40 rounded-full px-2 focus:outline-none">
              <option value="all">All provinces</option>
              {rows.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
            </select>
            <select value={filterRisk} onChange={(e) => setFilterRisk(e.target.value)} aria-label="Risk level" className="h-8 compact:h-11 compact:text-[16px] min-w-0 text-[11px] bg-secondary/50 border border-border/40 rounded-full px-2 focus:outline-none">
              <option value="all">All risk levels</option>
              <option value="low">Low</option>
              <option value="high">High</option>
            </select>
            <select
              value={activeQuarter ?? ""}
              onChange={(e) => setQuarter(e.target.value)}
              aria-label="Quarter"
              className="h-8 compact:h-11 compact:text-[16px] min-w-0 text-[11px] bg-secondary/50 border border-border/40 rounded-full px-2 focus:outline-none"
            >
              {selectableQuarters(quartersRes?.quarters ?? [], quartersRes?.calendarQuarter).map((q) => (
                <option key={q.id} value={q.id} disabled={q.state === "unavailable"} title={q.reason ?? undefined}>
                  {q.label} {q.year}{q.state === "unavailable" ? " (no data)" : ""}
                </option>
              ))}
            </select>
            <select
              value={`${sortKey}:${sortDir}`}
              onChange={(e) => {
                const [k, d] = e.target.value.split(":");
                setSortKey(k as SortKey);
                setSortDir(d as "asc" | "desc");
              }}
              aria-label="Sort by"
              data-tour="data-sort"
              className="hidden compact:block col-span-2 h-11 text-[16px] min-w-0 bg-secondary/50 border border-border/40 rounded-full px-2 focus:outline-none"
            >
              {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>

          {/* Phones: one card per province instead of the table. */}
          <ul className="hidden compact:flex flex-col gap-2" aria-label="Provinces" data-tour="data-table">
            {loadFailed ? (
              <li className="px-4 py-6 text-center text-muted-foreground text-[14px] bg-card border edge-faint rounded-xl shadow-md">{LOAD_ERROR_MESSAGE}</li>
            ) : !isLoading && filtered.length === 0 && (
              <li className="px-4 py-6 text-center text-muted-foreground text-[14px] bg-card border edge-faint rounded-xl shadow-md">No rows for this filter.</li>
            )}
            {filtered.map((r, i) => {
              const color = r.riskLevel ? RISK_COLORS[r.riskLevel] : "#6b7280";
              return (
                <li key={r.id} data-tour={i === 0 ? "data-row" : undefined}>
                  <button
                    type="button"
                    onClick={() => goToRow(r)}
                    className="w-full text-left bg-card border edge-faint rounded-xl shadow-md px-4 py-3 hover:bg-secondary/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className="flex items-center justify-between gap-3">
                      <span className="text-[15px] font-semibold">{r.name}</span>
                      {r.riskLevel && r.riskLevel in RISK_LABELS ? <StatusBadge level={r.riskLevel as RiskLevelKey} /> : <span className="text-[14px]">{r.riskLevel ?? "—"}</span>}
                    </span>
                    <span className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1.5 text-[14px]">
                      <span className="flex flex-col">
                        <span className="text-[12px] text-muted-foreground">Risk score</span>
                        <span className="tabular-nums font-bold" style={{ color }}>{r.riskScore !== null ? r.riskScore.toFixed(2) : "—"}</span>
                      </span>
                      <span className="flex flex-col">
                        <span className="text-[12px] text-muted-foreground">Quarter-on-quarter change</span>
                        <span className="tabular-nums">{r.qoqChangePct !== null ? formatSigned(r.qoqChangePct, 1, "%") : "—"}</span>
                      </span>
                      <span className="flex flex-col">
                        <span className="text-[12px] text-muted-foreground">Articles</span>
                        <span className="tabular-nums">{r.articleCount}</span>
                      </span>
                      <span className="flex flex-col">
                        <span className="text-[12px] text-muted-foreground">Status</span>
                        <span>{r.withheld ? "Withheld" : "Published"}</span>
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="bg-card border edge-faint rounded-xl shadow-lg overflow-hidden compact:hidden" data-tour="data-table">
            <table className="w-full text-[11px]">
              <thead className="bg-secondary/40 text-muted-foreground" data-tour="data-sort">
                <tr>
                  {columns.map((c) => (
                    <th key={c.key} className="text-left font-semibold px-4 py-2.5 cursor-pointer hover:text-foreground" onClick={() => setSort(c.key)}>
                      <span className="inline-flex items-center gap-1">
                        {c.label}
                        {sortKey === c.key && (sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                      </span>
                    </th>
                  ))}
                  <th className="text-left font-semibold px-4 py-2.5">Status</th>
                </tr>
              </thead>
              <tbody>
                {loadFailed ? (
                  <tr><td colSpan={6} className="px-4 py-6 text-center text-muted-foreground text-[11px]">{LOAD_ERROR_MESSAGE}</td></tr>
                ) : !isLoading && filtered.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-6 text-center text-muted-foreground text-[11px]">No rows for this filter.</td></tr>
                )}
                {filtered.map((r) => {
                  const color = r.riskLevel ? RISK_COLORS[r.riskLevel] : "#6b7280";
                  return (
                    <tr
                      key={r.id}
                      onClick={() => goToRow(r)}
                      className="border-t edge-control hover:bg-secondary/30 cursor-pointer"
                    >
                      <td className="px-4 py-2 font-medium">{r.name}</td>
                      <td className="px-4 py-2 tabular-nums font-bold" style={{ color }}>
                        {r.riskScore !== null ? r.riskScore.toFixed(2) : "—"}
                      </td>
                      <td className="px-4 py-2">
                        {r.riskLevel && r.riskLevel in RISK_LABELS ? (
                          <StatusBadge level={r.riskLevel as RiskLevelKey} />
                        ) : (
                          r.riskLevel ?? "—"
                        )}
                      </td>
                      <td className="px-4 py-2 tabular-nums">
                        {r.qoqChangePct !== null ? formatSigned(r.qoqChangePct, 1, "%") : "—"}
                      </td>
                      <td className="px-4 py-2 tabular-nums">{r.articleCount}</td>
                      <td className="px-4 py-2">{r.withheld ? "Withheld" : "Published"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-muted-foreground mt-2" aria-live="polite">{loadFailed ? "—" : `${filtered.length} rows`}</p>
        </div>
      </main>
      {/* First-visit guide for public visitors (also "Take the tour" in the menu). */}
      <DataTour />
    </div>
  );
}
