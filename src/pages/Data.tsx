import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TopNavbar } from "@/components/TopNavbar";
import { PROVINCE_QUARTER_DATA, QUARTER_IDS, getRiskLevelFromScore } from "@/data/quarterData";
import { RISK_COLORS, RISK_LABELS, RiskLevel } from "@/data/types";
import { ArrowDown, ArrowUp, Download, Search } from "lucide-react";

interface Row {
  province: string;
  quarter: string;
  rfii: number;
  riskLevel: RiskLevel;
  articles: number;
  trigger: "Market" | "Climate" | "Employment";
  status: "Staged" | "Approved" | "Forecast";
}

const TRIGGERS = ["Market", "Climate", "Employment"] as const;

const ALL_ROWS: Row[] = PROVINCE_QUARTER_DATA.flatMap((p) =>
  QUARTER_IDS.slice(0, 6).map((q, i) => {
    const score = p.scoresByQuarter[q] ?? 0;
    return {
      province: p.name,
      quarter: q,
      rfii: score,
      riskLevel: getRiskLevelFromScore(score),
      articles: Math.round(p.articles * (0.7 + 0.05 * i)),
      trigger: TRIGGERS[(p.name.length + i) % 3],
      status: i < 5 ? "Approved" : "Staged",
    };
  })
);

type SortKey = keyof Row;

export default function DataPage() {
  const navigate = useNavigate();
  const [sortKey, setSortKey] = useState<SortKey>("rfii");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filterProv, setFilterProv] = useState<string>("all");
  const [filterRisk, setFilterRisk] = useState<string>("all");
  const [filterQ, setFilterQ] = useState<string>("all");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    let rows = ALL_ROWS.filter((r) => {
      if (filterProv !== "all" && r.province !== filterProv) return false;
      if (filterRisk !== "all" && r.riskLevel !== filterRisk) return false;
      if (filterQ !== "all" && r.quarter !== filterQ) return false;
      if (search && !r.province.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
    rows = [...rows].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === "number" && typeof bv === "number") return sortDir === "asc" ? av - bv : bv - av;
      return sortDir === "asc" ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
    });
    return rows;
  }, [sortKey, sortDir, filterProv, filterRisk, filterQ, search]);

  const setSort = (k: SortKey) => {
    if (sortKey === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir("desc"); }
  };

  const exportCsv = () => {
    const header = ["Province", "Quarter", "RFII", "Risk Level", "Articles", "Trigger", "Status"];
    const csv = [
      header.join(","),
      ...filtered.map((r) => [r.province, r.quarter, r.rfii.toFixed(2), r.riskLevel, r.articles, r.trigger, r.status].join(",")),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aipheed_data_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden">
      <TopNavbar active="data" />

      <main className="flex-1 overflow-auto">
        <div className="p-6 max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-lg font-bold tracking-tight">Risk Data — CALABARZON</h1>
              <p className="text-[11px] text-muted-foreground">All forecasts at province × quarter level. Click a row for details.</p>
            </div>
            <button
              onClick={exportCsv}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-[11px] font-bold hover:bg-primary/90"
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
              {PROVINCE_QUARTER_DATA.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
            </select>
            <select value={filterRisk} onChange={(e) => setFilterRisk(e.target.value)} className="h-8 text-[11px] bg-secondary/50 border border-border/40 rounded-md px-2 focus:outline-none">
              <option value="all">All risk levels</option>
              <option value="low">Low</option>
              <option value="moderate">Moderate</option>
              <option value="high">High</option>
              <option value="severe">Severe</option>
            </select>
            <select value={filterQ} onChange={(e) => setFilterQ(e.target.value)} className="h-8 text-[11px] bg-secondary/50 border border-border/40 rounded-md px-2 focus:outline-none">
              <option value="all">All quarters</option>
              {QUARTER_IDS.slice(0, 6).map((q) => <option key={q} value={q}>{q}</option>)}
            </select>
          </div>

          <div className="bg-card border border-border/50 rounded-xl overflow-hidden">
            <table className="w-full text-[11px]">
              <thead className="bg-secondary/40 text-muted-foreground">
                <tr>
                  {(["province", "quarter", "rfii", "riskLevel", "articles", "trigger", "status"] as SortKey[]).map((k) => (
                    <th key={k} className="text-left font-semibold px-4 py-2.5 cursor-pointer hover:text-foreground" onClick={() => setSort(k)}>
                      <span className="inline-flex items-center gap-1 capitalize">
                        {k === "rfii" ? "RFII" : k === "riskLevel" ? "Risk Level" : k}
                        {sortKey === k && (sortDir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((r, i) => (
                  <tr
                    key={i}
                    onClick={() => {
                      const prov = PROVINCE_QUARTER_DATA.find((p) => p.name === r.province);
                      if (prov) {
                        sessionStorage.setItem("aipheed_focus", JSON.stringify({ provinceId: prov.id }));
                        navigate("/");
                      }
                    }}
                    className="border-t border-border/40 hover:bg-secondary/30 cursor-pointer"
                  >
                    <td className="px-4 py-2 font-medium">{r.province}</td>
                    <td className="px-4 py-2">{r.quarter}</td>
                    <td className="px-4 py-2 tabular-nums font-bold" style={{ color: RISK_COLORS[r.riskLevel] }}>{r.rfii.toFixed(2)}</td>
                    <td className="px-4 py-2">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                        style={{ color: RISK_COLORS[r.riskLevel], background: `${RISK_COLORS[r.riskLevel]}15`, border: `1px solid ${RISK_COLORS[r.riskLevel]}55` }}>
                        {RISK_LABELS[r.riskLevel]}
                      </span>
                    </td>
                    <td className="px-4 py-2 tabular-nums">{r.articles}</td>
                    <td className="px-4 py-2">{r.trigger}</td>
                    <td className="px-4 py-2">{r.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-muted-foreground mt-2">{filtered.length} rows</p>
        </div>
      </main>
    </div>
  );
}
