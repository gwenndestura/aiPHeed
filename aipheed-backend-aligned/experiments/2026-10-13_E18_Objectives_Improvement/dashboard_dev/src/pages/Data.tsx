import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TopNavbar } from "@/components/TopNavbar";
import { useQuarters, useProvinces } from "@/lib/queries";
import { RISK_COLORS, RISK_LABELS } from "@/data/types";
import type { ProvinceSummary } from "@/lib/apiTypes";
import { ArrowDown, ArrowUp, Download, Search } from "lucide-react";

type SortKey = "name" | "riskScore" | "riskLevel" | "qoqChangePct" | "articleCount";

export default function DataPage() {
  const navigate = useNavigate();
  const [sortKey, setSortKey] = useState<SortKey>("riskScore");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filterProv, setFilterProv] = useState<string>("all");
  const [filterRisk, setFilterRisk] = useState<string>("all");
  const [quarter, setQuarter] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState("");

  const { data: quartersRes } = useQuarters("nowcast");
  const activeQuarter = quarter ?? quartersRes?.current;
  const { data: provincesRes, isLoading } = useProvinces(activeQuarter, "nowcast");
  const rows = provincesRes?.data ?? [];

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
    sessionStorage.setItem("aipheed_focus", JSON.stringify({ provinceId: r.id }));
    navigate("/dashboard");
  };

  const columns: { key: SortKey; label: string }[] = [
    { key: "name", label: "Province" },
    { key: "riskScore", label: "Risk Level" },
    { key: "riskLevel", label: "Risk Level" },
    { key: "qoqChangePct", label: "QoQ Change" },
    { key: "articleCount", label: "Articles" },
  ];

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden">
      <TopNavbar active="data" />

      <main className="flex-1 overflow-auto">
        <div className="p-6 max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-lg font-bold tracking-tight">Risk Data — CALABARZON</h1>
              <p className="text-[11px] text-muted-foreground">
                Province-level forecasts for {activeQuarter ?? "the latest quarter"}. Click a row for details.
              </p>
            </div>
            <button
              onClick={exportCsv}
              disabled={filtered.length === 0}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-[11px] font-bold hover:bg-primary/90 disabled:opacity-50"
            >
              <Download className="h-3.5 w-3.5" /> Export CSV
            </button>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-4 gap-2 mb-4">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search province"
                className="w-full h-8 pl-8 pr-2 text-[11px] bg-secondary/50 border border-border/40 rounded-md focus:outline-none focus:border-primary/50"
              />
            </div>
            <select value={filterProv} onChange={(e) => setFilterProv(e.target.value)} className="h-8 text-[11px] bg-secondary/50 border border-border/40 rounded-md px-2 focus:outline-none">
              <option value="all">All provinces</option>
              {rows.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
            </select>
            <select value={filterRisk} onChange={(e) => setFilterRisk(e.target.value)} className="h-8 text-[11px] bg-secondary/50 border border-border/40 rounded-md px-2 focus:outline-none">
              <option value="all">All risk levels</option>
              <option value="low">Low</option>
              <option value="high">High</option>
            </select>
            <select
              value={activeQuarter ?? ""}
              onChange={(e) => setQuarter(e.target.value)}
              className="h-8 text-[11px] bg-secondary/50 border border-border/40 rounded-md px-2 focus:outline-none"
            >
              {(quartersRes?.quarters ?? []).map((q) => (
                <option key={q.id} value={q.id}>{q.label} {q.year}</option>
              ))}
            </select>
          </div>

          <div className="bg-card border border-border/50 rounded-xl overflow-hidden">
            <table className="w-full text-[11px]">
              <thead className="bg-secondary/40 text-muted-foreground">
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
                {!isLoading && filtered.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-6 text-center text-muted-foreground text-[11px]">No rows for this filter.</td></tr>
                )}
                {filtered.map((r) => {
                  const color = r.riskLevel ? RISK_COLORS[r.riskLevel] : "#6b7280";
                  return (
                    <tr
                      key={r.id}
                      onClick={() => goToRow(r)}
                      className="border-t border-border/40 hover:bg-secondary/30 cursor-pointer"
                    >
                      <td className="px-4 py-2 font-medium">{r.name}</td>
                      <td className="px-4 py-2 tabular-nums font-bold" style={{ color }}>
                        {r.riskScore !== null ? r.riskScore.toFixed(2) : "—"}
                      </td>
                      <td className="px-4 py-2">
                        {r.riskLevel ? (
                          <span
                            className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                            style={{ color, background: `${color}15`, border: `1px solid ${color}55` }}
                          >
                            {RISK_LABELS[r.riskLevel] ?? r.riskLevel}
                          </span>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-2 tabular-nums">
                        {r.qoqChangePct !== null ? `${r.qoqChangePct > 0 ? "+" : ""}${r.qoqChangePct.toFixed(1)}%` : "—"}
                      </td>
                      <td className="px-4 py-2 tabular-nums">{r.articleCount}</td>
                      <td className="px-4 py-2">{r.withheld ? "Withheld" : "Published"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-muted-foreground mt-2">{filtered.length} rows</p>
        </div>
      </main>
    </div>
  );
}
