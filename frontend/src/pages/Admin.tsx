import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  MessageSquareText,
  ClipboardCheck,
  LogOut,
  Eye,
  FileText,
  X,
  Map as MapIcon,
  Menu,
  Sun,
  Moon,
} from "lucide-react";
import { RISK_COLORS, RISK_LABELS } from "@/data/types";
import { EarlyWarningBanner } from "@/components/EarlyWarningBanner";
import { StatusBadge, type RiskLevelKey } from "@/components/ui/status-badge";
import { MetricLabel } from "@/components/ui/metric";
import { Note } from "@/components/ui/note";
import { MapDashboard } from "@/components/MapDashboard";
import { SidebarPeek } from "@/components/SidebarPeek";
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { PSTClock, PSTClockMenuRow } from "@/components/PSTClock";
import logoDark from "@/assets/logo-dark.png";
import logoLight from "@/assets/logo-light.png";
import logoIcon from "@/assets/logo-icon.png";

import { RegionMetadataPopup } from "@/components/RegionMetadataPopup";
import { toast } from "@/hooks/use-toast";
import { useAuth } from "@/lib/auth";
import { adminPath, sectionFromPath } from "@/lib/adminNav";
import { AdminAccountsMenuItem, AdminMenuLinks, AdminNavLinks, DemoBadge, MENU_TRIGGER_CLASS } from "@/components/TopNavbar";
import { AccountsSection } from "@/components/AccountsSection";
import { ApiError } from "@/lib/api";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { COMPACT_QUERY } from "@/lib/breakpoints";
import {
  useConfig,
  useQuarters,
  useReviewQueue,
  useAccounts,
  useApproveReview,
  useRejectReview,
  useUndoReview,
  useRestoreRejection,
  useAdminFeedback,
  useMunicipalities,
  useExplainability,
} from "@/lib/queries";
import { DEMO_READ_ONLY_NOTE, type ReviewItem, type FeedbackRow, type Trigger } from "@/lib/apiTypes";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { readStorage, writeStorage } from "@/lib/storage";

const THEME_KEY = "aipheed_theme";

export default function Admin() {
  // The URL is the only source of truth for the section: /admin, /admin/review,
  // /admin/feedback. Back/Forward and links therefore move between sections.
  const location = useLocation();
  const navigate = useNavigate();
  const section = sectionFromPath(location.pathname);
  const { user, logout } = useAuth();

  const { data: quartersRes } = useQuarters("nowcast");
  const { data: config } = useConfig();
  // Provinces still awaiting a decision for the newest quarter, above the
  // alert threshold -- what the banner is warning about.
  const { data: staged } = useReviewQueue(quartersRes?.current, "Staged");
  const alertThreshold = config?.thresholds.alertThreshold ?? 0.6;
  const warningItems = (staged?.data ?? []).filter((r) => r.riskScore >= alertThreshold);
  const topWarning = warningItems.slice().sort((a, b) => b.riskScore - a.riskScore)[0];

  if (!user) return null; // RequireAdmin (App.tsx) guarantees this never renders

  const doLogout = async () => {
    await logout();
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden">
      <AdminNavbar
        user={user}
        onLogout={doLogout}
      />

      {topWarning && (
        <EarlyWarningBanner
          message={`${topWarning.province} — ${topWarning.riskLevel === "high" ? "High" : topWarning.riskLevel} risk detected for ${topWarning.quarter}. ${warningItems.length} item${warningItems.length === 1 ? "" : "s"} awaiting review.`}
          onReview={() => navigate(adminPath("review"))}
        />
      )}

      <main className="flex-1 overflow-hidden relative">
        <div className={section === "map" ? "h-full w-full" : "hidden"}>
          <AdminMapView />
        </div>
        {section === "review" && <div className="h-full overflow-auto"><ReviewSection /></div>}
        {section === "feedback" && <div className="h-full overflow-auto"><FeedbackSection /></div>}
        {section === "accounts" && (
          <div className="h-full overflow-auto">
            <SectionHeader title="Accounts" subtitle="Approve requests for administrator access and manage who has it" />
            {user.isDemo ? (
              <div className="px-6 py-5"><Note label={null}>{DEMO_READ_ONLY_NOTE}</Note></div>
            ) : (
              <AccountsSection />
            )}
          </div>
        )}
      </main>
    </div>
  );
}

/* ---------- Admin Navbar — mirrors TopNavbar styling ---------- */
function AdminNavbar({
  user,
  onLogout,
}: {
  user: { email: string; role: string; isDemo?: boolean };
  onLogout: () => void;
}) {
  const [theme, setTheme] = useState<"dark" | "light">(
    () => (readStorage(THEME_KEY) as "dark" | "light" | null) ?? "dark"
  );
  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    writeStorage(THEME_KEY, theme);
    window.dispatchEvent(new CustomEvent("aipheed:theme", { detail: { theme } }));
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));
  // Fetched with the header, so the menu's pending count is ready when it opens.
  // Never for the demo account, which may not see account requests at all.
  useAccounts(!user.isDemo);

  return (
    <header className="relative h-16 shrink-0 bg-card/95 backdrop-blur-sm border-b edge-faint z-[1002] flex items-center px-4 gap-3">
      {/* Brand → landing page, as on public pages. In-app navigation, so the
          admin stays signed in (the public header then shows the admin nav). */}
      <Link
        to="/"
        className="flex items-center mr-2 hover:opacity-90 transition-opacity shrink-0 max-lg:min-h-11 max-lg:min-w-11"
        aria-label="aiPHeed home"
      >
        <img src={logoIcon} alt="aiPHeed" className="sm:hidden h-9 w-9 object-contain" />
        <img src={logoDark} alt="aiPHeed" className="hidden sm:block dark-only h-10 w-auto object-contain" />
        <img src={logoLight} alt="aiPHeed" className="hidden sm:block light-only h-10 w-auto object-contain" />
        <span className="hidden md:inline ml-2 text-[9px] uppercase tracking-widest text-primary font-bold">Admin</span>
      </Link>
      {user.isDemo && <DemoBadge />}

      {/* Nav links — centered */}
      {/* Five links; below 1024px they move into the menu (AdminMenuLinks). */}
      <nav className={`absolute left-1/2 -translate-x-1/2 ${user.isDemo ? "hidden xl:flex" : "hidden lg:flex"} items-center gap-1`}>
        <AdminNavLinks />
      </nav>

      <div className="flex-1" />

      {/* PST clock -- in the menu below 1280px, where the five links need the room */}
      <PSTClock from="xl" />

      {/* Hamburger */}
      <Sheet>
        <SheetTrigger className={MENU_TRIGGER_CLASS} aria-label="Menu">
          <Menu className="h-4 w-4" />
        </SheetTrigger>
        <SheetContent side="right" className="w-[280px] [--surface-base:var(--card)] border-l z-[1100]">
          <SheetHeader>
            <SheetTitle className="text-sm">Admin Menu</SheetTitle>
          </SheetHeader>
          <div className="mt-6 space-y-1">
            <AdminMenuLinks demo={!!user.isDemo} />
            <PSTClockMenuRow from="xl" />
            <p className="text-[9px] uppercase tracking-widest text-muted-foreground/60 font-semibold px-2 mb-1">
              Account
            </p>
            {!user.isDemo && <AdminAccountsMenuItem />}
            <div className="px-2 py-2 rounded-md bg-secondary/40 flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-[9px] font-bold text-primary">
                {user.email.slice(0, 2).toUpperCase()}
              </div>
              <span className="text-[10px] text-muted-foreground truncate">{user.email}</span>
            </div>
            <button
              onClick={onLogout}
              className="mt-1 w-full flex items-center gap-2 px-2 py-2 max-lg:min-h-11 rounded-md text-[11px] hover:bg-secondary/60 text-foreground"
            >
              <LogOut className="h-3.5 w-3.5" /> Sign out
            </button>

            <div className="pt-3 mt-3 border-t border-border/40">
              <p className="text-[9px] uppercase tracking-widest text-muted-foreground/60 font-semibold px-2 mb-2">
                Appearance
              </p>
              <div className="flex items-center justify-between gap-3 px-2 py-2 rounded-md">
                <span className="flex items-center gap-3">
                  {theme === "dark" ? <Moon className="h-3.5 w-3.5" /> : <Sun className="h-3.5 w-3.5" />}
                  <span className="text-[11px] font-medium">
                    {theme === "dark" ? "Dark mode" : "Light mode"}
                  </span>
                </span>
                <button
                  onClick={toggleTheme}
                  role="switch"
                  aria-checked={theme === "light"}
                  aria-label="Toggle dark / light mode"
                  className={`relative inline-flex h-5 w-10 items-center rounded-full transition-colors border after:absolute after:-inset-x-2 after:-inset-y-3 after:content-[''] ${
                    theme === "light"
                      ? "bg-primary border-primary"
                      : "bg-secondary border-border/50"
                  }`}
                >
                  <span aria-hidden className="absolute left-1 text-[8px]">🌙</span>
                  <span aria-hidden className="absolute right-1 text-[8px]">☀️</span>
                  <span
                    className={`relative z-10 inline-block h-4 w-4 transform rounded-full bg-card shadow-md transition-transform ${
                      theme === "light" ? "translate-x-5" : "translate-x-0.5"
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </header>
  );
}

/* ---------- Admin Map View — same floating-card layout as user page ---------- */
function AdminMapView() {
  return <MapDashboard showAboutFeedback={false} />;
}

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="px-6 compact:px-4 pt-6 pb-4 border-b border-border/40">
      <h1 className="text-lg font-bold tracking-tight">{title}</h1>
      <p className="text-[11px] compact:text-[14px] text-muted-foreground mt-0.5">{subtitle}</p>
    </div>
  );
}

/** Review state as a badge: the same element in the table and the review dialog. */
function statusBadgeFor(s: ReviewItem["status"]) {
  return <StatusBadge tone={s === "Approved" ? "positive" : s === "Rejected" ? "high" : "neutral"}>{s}</StatusBadge>;
}

/* ---------- Review ---------- */
type ReviewTab = "queue" | "log";

function apiErrorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

function ReviewSection() {
  const [open, setOpen] = useState<ReviewItem | null>(null);
  const [year, setYear] = useState<number | null>(null);
  const [quarter, setQuarter] = useState<"all" | "Q1" | "Q2" | "Q3" | "Q4">("all");
  const [tab, setTab] = useState<ReviewTab>("queue");

  const { data: quartersRes } = useQuarters("nowcast");
  const years = useMemo(() => {
    // The review queue covers nowcast quarters; the E20 forecast is not reviewed here.
    const set = new Set((quartersRes?.quarters ?? []).filter((q) => q.state !== "forecast").map((q) => q.year));
    return Array.from(set).sort((a, b) => b - a);
  }, [quartersRes]);
  useEffect(() => {
    if (year === null && years.length) setYear(years[0]);
  }, [year, years]);

  // Every quarter's rows in one call (a handful of provinces x ~20 quarters
  // is small) and filter client-side, so switching Year/Quarter doesn't
  // trigger a refetch.
  const { data: reviewRes, isLoading } = useReviewQueue();
  const rejectionReasons = reviewRes?.rejectionReasons ?? [];

  const approveMut = useApproveReview();
  const rejectMut = useRejectReview();
  const undoMut = useUndoReview();
  const restoreMut = useRestoreRejection();
  // One review action at a time: the buttons are disabled while any of these
  // is in flight, so a double click cannot send the same decision twice.
  // The demo account is view-only (the server refuses every change); its
  // buttons are disabled like during a request, with a note saying why.
  const readOnly = !!useAuth().user?.isDemo;
  const busy = readOnly || approveMut.isPending || rejectMut.isPending || undoMut.isPending || restoreMut.isPending;

  const statusBadge = statusBadgeFor;

  const approve = (it: ReviewItem) => {
    approveMut.mutate(it.id, {
      onSuccess: () => {
        setOpen(null);
        toast({ title: "Report approved", description: `${it.province} ${it.quarter} forecast is now public-ready.` });
      },
      onError: (err) => toast({ variant: "destructive", title: "Could not approve", description: apiErrorMessage(err, "Please try again.") }),
    });
  };

  const unpublish = (it: ReviewItem) => {
    undoMut.mutate(it.id, {
      onSuccess: () => {
        setOpen(null);
        toast({ title: "Publishing undone", description: `${it.province} ${it.quarter} forecast reverted to Staged.` });
      },
      onError: (err) => toast({ variant: "destructive", title: "Could not undo", description: apiErrorMessage(err, "Please try again.") }),
    });
  };

  const reject = (it: ReviewItem, reason: string, notes?: string) => {
    rejectMut.mutate(
      { itemId: it.id, reason, notes },
      {
        onSuccess: () => {
          setOpen(null);
          toast({
            variant: "destructive",
            title: "Forecast rejected",
            description: `Forecast for ${it.province} ${formatQuarterLabel(it.quarter)} has been rejected and will not be published.`,
          });
        },
        onError: (err) => toast({ variant: "destructive", title: "Could not reject", description: apiErrorMessage(err, "Please try again.") }),
      }
    );
  };

  const restore = (it: ReviewItem) => {
    restoreMut.mutate(
      { provinceId: it.provinceId, quarter: it.quarter },
      {
        onSuccess: () => {
          setOpen(null);
          toast({ title: "Rejection restored", description: `${it.province} ${it.quarter} can be reviewed again.` });
        },
        onError: (err) => toast({ variant: "destructive", title: "Could not restore", description: apiErrorMessage(err, "Please try again.") }),
      }
    );
  };

  const allItems = reviewRes?.data ?? [];
  const filtered = allItems.filter(
    (it) => (year === null || it.quarter.startsWith(`${year}-`)) && (quarter === "all" || it.quarter.endsWith(`-${quarter}`))
  );
  const sorted = [...filtered].sort((a, b) => {
    const qa = Number(a.quarter.split("-Q")[1]);
    const qb = Number(b.quarter.split("-Q")[1]);
    if (qa !== qb) return qb - qa;
    return a.province.localeCompare(b.province);
  });

  const rejectedItems = allItems.filter((it) => it.status === "Rejected");

  return (
    <div>
      <SectionHeader title="Review" subtitle="Approve, monitor, and audit risk reports per province" />
      {readOnly && <div className="px-6 pt-4"><Note label={null}>{DEMO_READ_ONLY_NOTE}</Note></div>}

      <div className="px-6 pt-4">
        <div className="inline-flex rounded-full border edge-faint bg-card shadow-sm p-0.5">
          {(["queue", "log"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 compact:min-h-11 text-[11px] font-bold seg-option transition-colors ${
                tab === t ? "seg-on" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "queue" ? "Review Queue" : "Rejection Log"}
            </button>
          ))}
        </div>
      </div>

      {tab === "queue" ? (
        <div className="p-6 pt-4">
          <div className="mb-4 flex items-center gap-3 flex-wrap">
            <label className="text-[11px] font-semibold text-muted-foreground">Year</label>
            <select
              value={year ?? ""}
              onChange={(e) => setYear(Number(e.target.value))}
              className="h-8 compact:h-11 compact:text-[16px] rounded-full border border-border/60 bg-card px-2 text-[11px] font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <label className="text-[11px] font-semibold text-muted-foreground ml-2">Quarter</label>
            <select
              value={quarter}
              onChange={(e) => setQuarter(e.target.value as typeof quarter)}
              className="h-8 compact:h-11 compact:text-[16px] rounded-full border border-border/60 bg-card px-2 text-[11px] font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All quarters</option>
              <option value="Q4">Q4</option>
              <option value="Q3">Q3</option>
              <option value="Q2">Q2</option>
              <option value="Q1">Q1</option>
            </select>
            <span className="ml-auto text-[10px] text-muted-foreground">
              {sorted.length} report{sorted.length === 1 ? "" : "s"}{year !== null ? ` · ${year}` : ""}
              {quarter !== "all" ? ` · ${quarter}` : ""}
            </span>
          </div>
          <div className="bg-card border edge-faint rounded-xl shadow-lg overflow-hidden">
            <table role="table" className="w-full text-[11px] stack-table">
              <thead role="rowgroup" className="bg-secondary/40 text-muted-foreground">
                <tr role="row">
                  <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Province</th>
                  <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Quarter</th>
                  <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Risk Level</th>
                  <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Risk Level Score</th>
                  <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Status</th>
                  <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Action</th>
                </tr>
              </thead>
              <tbody role="rowgroup">
                {sorted.map((r) => (
                  <tr role="row" key={r.id} className="border-t edge-control hover:bg-secondary/30">
                    <td role="cell" data-label="Province" className="px-4 py-2.5 font-medium">{r.province}</td>
                    <td role="cell" data-label="Quarter" className="px-4 py-2.5 tabular-nums text-muted-foreground">
                      <span className="font-semibold text-foreground">{r.quarter}</span>
                    </td>
                    <td role="cell" data-label="Risk Level" className="px-4 py-2.5">
                      {r.riskLevel in RISK_LABELS ? (
                        <StatusBadge level={r.riskLevel as RiskLevelKey} />
                      ) : (
                        r.riskLevel
                      )}
                    </td>
                    <td role="cell" data-label="Risk Level Score" className="px-4 py-2.5 tabular-nums font-bold" style={{ color: RISK_COLORS[r.riskLevel] ?? "#6b7280" }}>
                      {r.riskScore.toFixed(2)}
                    </td>
                    <td role="cell" data-label="Status" className="px-4 py-2.5">{statusBadge(r.status)}</td>
                    <td role="cell" data-label="Action" className="px-4 py-2.5">
                      <button
                        onClick={() => setOpen(r)}
                        className="text-primary hover:underline text-[11px] font-semibold flex items-center gap-1 compact:min-h-11"
                      >
                        <Eye className="h-3 w-3" /> View Details
                      </button>
                    </td>
                  </tr>
                ))}
                {!isLoading && sorted.length === 0 && (
                  <tr role="row"><td role="cell" colSpan={6} className="px-4 py-6 text-center text-muted-foreground text-[11px]">No reports for this filter.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <RejectionLog rejected={rejectedItems} onRestore={restore} busy={busy} />
      )}

      {open && (
        <ReviewDetailModal
          item={open}
          rejectionReasons={rejectionReasons}
          onClose={() => setOpen(null)}
          onApprove={() => approve(open)}
          onUnpublish={() => unpublish(open)}
          onReject={(reason, notes) => reject(open, reason, notes)}
          onRestore={() => restore(open)}
          busy={busy}
          readOnly={readOnly}
        />
      )}
    </div>
  );
}

function formatQuarterLabel(qid: string): string {
  const [y, q] = qid.split("-");
  return `${q} ${y}`;
}

function RejectionLog({ rejected, onRestore, busy = false }: { rejected: ReviewItem[]; onRestore: (it: ReviewItem) => void; busy?: boolean }) {
  return (
    <div className="p-6 pt-4">
      <div className="bg-card border edge-faint rounded-xl shadow-lg overflow-hidden">
        <table role="table" className="w-full text-[11px] stack-table">
          <thead role="rowgroup" className="bg-secondary/40 text-muted-foreground">
            <tr role="row">
              <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Province</th>
              <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Quarter</th>
              <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Reason</th>
              <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Notes</th>
              <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Timestamp</th>
              <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Action</th>
            </tr>
          </thead>
          <tbody role="rowgroup">
            {rejected.length === 0 && (
              <tr role="row"><td role="cell" colSpan={6} className="px-4 py-8 text-center text-muted-foreground italic">No rejections logged.</td></tr>
            )}
            {rejected.map((r) => (
              <tr role="row" key={r.id} className="border-t edge-control hover:bg-secondary/30">
                <td role="cell" data-label="Province" className="px-4 py-2.5 font-medium">{r.province}</td>
                <td role="cell" data-label="Quarter" className="px-4 py-2.5 tabular-nums">{r.quarter}</td>
                <td role="cell" data-label="Reason" className="px-4 py-2.5">{r.rejectionReason ?? "—"}</td>
                <td role="cell" data-label="Notes" className="px-4 py-2.5 text-muted-foreground">{r.rejectionNotes || "—"}</td>
                <td role="cell" data-label="Timestamp" className="px-4 py-2.5 tabular-nums text-muted-foreground">{r.updatedAt ? new Date(r.updatedAt).toLocaleString() : "—"}</td>
                <td role="cell" data-label="Action" className="px-4 py-2.5">
                  <button
                    onClick={() => onRestore(r)}
                    disabled={busy}
                    className="text-primary hover:underline text-[11px] font-semibold compact:min-h-11 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Restore
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note className="mt-2">This is the audit log of rejected forecasts. Restoring a forecast removes its rejection so it can be reviewed again.</Note>
    </div>
  );
}

function ReviewDetailModal({
  item,
  rejectionReasons,
  onClose,
  onApprove,
  onUnpublish,
  onReject,
  onRestore,
  busy = false,
  readOnly = false,
}: {
  item: ReviewItem;
  rejectionReasons: string[];
  onClose: () => void;
  onApprove: () => void;
  onUnpublish: () => void;
  onReject: (reason: string, notes?: string) => void;
  onRestore: () => void;
  /** A review request is in flight: the action buttons are disabled. */
  busy?: boolean;
  /** The demo account: actions disabled, with the note shown. */
  readOnly?: boolean;
}) {
  const [rejectOpen, setRejectOpen] = useState(false);
  // Chart text: 12px on phones (Recharts draws it; CSS cannot reach it).
  const compact = useMediaQuery(COMPACT_QUERY);
  const chartFs = compact ? 12 : 10;

  // Real municipality / city scores for this province-quarter.
  const { data: muniRes } = useMunicipalities(item.provinceId, item.quarter);
  const muniData = (muniRes?.data ?? []).slice().sort((a, b) => b.riskIndex - a.riskIndex);

  // Real SHAP driver groups for this province-quarter.
  const { data: explain } = useExplainability("province", item.provinceId, item.quarter);
  const triggers: Trigger[] = explain?.triggers ?? [];

  return (
    <div className="fixed inset-0 z-[2000] bg-background/70 backdrop-blur-sm flex items-center justify-center p-6 compact:p-0">
      <div className="surface-dialog border compact:rounded-none w-full max-w-3xl max-h-[88vh] compact:h-full compact:max-h-full overflow-hidden flex flex-col">
        <div className="px-5 py-3.5 border-b border-border/40 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold">{item.province} — Risk Review</h2>
            <p className="text-[10px] text-muted-foreground">
              <span className="font-semibold text-primary">{item.quarter}</span> · Risk Level {item.riskScore.toFixed(2)} · Status: {item.status}
            </p>
            {item.riskLevel in RISK_LABELS && (
              <div className="mt-1.5 flex items-center gap-1.5">
                <StatusBadge level={item.riskLevel as RiskLevelKey} />
                {statusBadgeFor(item.status)}
              </div>
            )}
          </div>
          <button onClick={onClose} aria-label="Close" className="p-1.5 compact:min-h-11 compact:min-w-11 flex items-center justify-center rounded-md hover:bg-secondary/60"><X className="h-4 w-4" /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 compact:p-4 grid grid-cols-2 gap-4">
          <div className="col-span-2 p-3 rounded-lg border edge-faint bg-secondary/30 flex items-center gap-3">
            <div className="bg-primary/15 rounded-lg p-2"><FileText className="h-4 w-4 text-primary" /></div>
            <div>
              <p className="text-[12px] font-semibold">{item.province} — {item.quarter} Risk Report</p>
              <p className="text-[10px] text-muted-foreground">Quarter forecast · reviewed by DA analyst</p>
            </div>
          </div>

          <div className="col-span-2 bg-card border edge-faint rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-[11px] font-bold">Municipality / City scores</h4>
              <span className="text-[10px] text-muted-foreground">{muniData.length} LGUs · sorted by Risk Level</span>
            </div>
            <div className="max-h-64 overflow-y-auto thin-scrollbar pr-1">
              <div className="grid grid-cols-2 compact:grid-cols-1 gap-x-4 gap-y-1">
                {muniData.map((m) => (
                  <div key={m.id} className="flex items-center gap-2 text-[11px] py-0.5">
                    <span className="flex-1 truncate" title={m.name}>{m.name}</span>
                    <div className="w-20 h-1.5 rounded-full bg-secondary/40 overflow-hidden">
                      <div
                        className="h-full"
                        style={{
                          width: `${Math.min(100, m.riskIndex * 100)}%`,
                          background: m.riskLevel === "high" ? "hsl(var(--risk-high))" : "hsl(var(--risk-low))",
                        }}
                      />
                    </div>
                    <span className="w-10 text-right tabular-nums font-bold">{m.riskIndex.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="col-span-2 bg-card border edge-faint rounded-lg p-3">
            <h4 className="text-[11px] font-bold mb-2">SHAP driver contributions</h4>
            {triggers.length > 0 ? (
              <ResponsiveContainer width="100%" height={Math.max(180, triggers.length * 28)}>
                <BarChart
                  data={triggers.map((t) => ({ label: t.label, value: t.signedContribution }))}
                  layout="vertical"
                  margin={{ left: 8, right: 16, top: 4, bottom: 4 }}
                >
                  <XAxis type="number" tick={{ fontSize: chartFs, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="label" width={130} tick={{ fontSize: chartFs, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ fontSize: compact ? 12 : 11, borderRadius: 0, background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }} formatter={(v: number) => v.toFixed(3)} />
                  <Bar dataKey="value" radius={[0, 0, 0, 0]}>
                    {triggers.map((t, i) => (
                      <Cell key={i} fill={t.signedContribution >= 0 ? "hsl(var(--risk-high))" : "hsl(var(--risk-low))"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-[11px] text-muted-foreground italic">Loading…</p>
            )}
          </div>

          {/* SHAP explanations — narrative */}
          <div className="col-span-2 bg-card border edge-faint rounded-lg p-3">
            <h4 className="text-[11px] font-bold mb-1">SHAP explanations</h4>
            <p className="text-[10px] compact:text-[14px] text-muted-foreground mb-3">
              {explain?.narrative ?? "Grouped driver reasons behind this quarter's Risk Level forecast."}
            </p>
            <ol className="space-y-2.5">
              {triggers
                .slice()
                .sort((a, b) => Math.abs(b.signedContribution) - Math.abs(a.signedContribution))
                .map((t) => (
                  <li key={t.key} className="text-[11px] compact:text-[14px] leading-snug">
                    <p className="font-bold text-foreground">{t.label} — {t.pct}%</p>
                    <p className="text-muted-foreground">
                      {t.direction === "increases_risk" ? "Pushed risk up" : "Pushed risk down"} (signed contribution {t.signedContribution.toFixed(3)}).
                    </p>
                  </li>
                ))}
            </ol>
          </div>
          <div className="col-span-2 bg-card border edge-faint rounded-lg p-3">
            <h4 className="text-[11px] font-bold mb-2">Provincial ranking (CALABARZON)</h4>
            <ProvincialRanking currentProvince={item.province} quarter={item.quarter} />
          </div>
        </div>

        <div className="px-5 py-3 border-t border-border/40 flex flex-wrap items-center justify-end gap-2">
          {readOnly && <Note label={null} className="mr-auto compact:basis-full">{DEMO_READ_ONLY_NOTE}</Note>}
          <button onClick={onClose} className="px-3 py-1.5 compact:min-h-11 rounded-md border edge-control text-[11px] hover:bg-secondary/60">Close</button>
          {item.status === "Rejected" ? (
            <button onClick={onRestore} disabled={busy} className="px-3 py-1.5 compact:min-h-11 rounded-md border border-primary/50 text-primary text-[11px] font-bold hover:bg-primary/10 disabled:opacity-40 disabled:cursor-not-allowed">Restore</button>
          ) : item.status === "Approved" ? (
            <>
              <button
                onClick={() => setRejectOpen(true)}
                disabled={busy}
                className="px-3 py-1.5 compact:min-h-11 rounded-md border border-destructive/60 text-destructive text-[11px] font-bold hover:bg-destructive/10 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Reject
              </button>
              <button onClick={onUnpublish} disabled={busy} className="px-3 py-1.5 compact:min-h-11 rounded-md border border-primary/50 text-primary text-[11px] font-bold hover:bg-primary/10 disabled:opacity-40 disabled:cursor-not-allowed">Undo Publishing</button>
            </>
          ) : (
            <>
              <button
                onClick={() => setRejectOpen(true)}
                disabled={busy}
                className="px-3 py-1.5 compact:min-h-11 rounded-md border border-destructive/60 text-destructive text-[11px] font-bold hover:bg-destructive/10 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Reject
              </button>
              <button onClick={onApprove} disabled={busy} className="px-3 py-1.5 compact:min-h-11 rounded-md bg-risk-low shadow-md text-white text-[11px] font-bold hover:bg-risk-low/90 disabled:opacity-40 disabled:cursor-not-allowed">Approve & Publish</button>
            </>
          )}
        </div>
      </div>

      {rejectOpen && (
        <RejectReasonModal
          item={item}
          reasons={rejectionReasons}
          onCancel={() => setRejectOpen(false)}
          onConfirm={(reason, notes) => {
            setRejectOpen(false);
            onReject(reason, notes);
          }}
        />
      )}
    </div>
  );
}

function ProvincialRanking({ currentProvince, quarter }: { currentProvince: string; quarter: string }) {
  const { data: reviewRes } = useReviewQueue(quarter);
  const ranked = (reviewRes?.data ?? []).slice().sort((a, b) => b.riskScore - a.riskScore);
  return (
    <div className="space-y-1.5">
      {ranked.map((r, i) => (
        <div key={r.id} className={`flex items-center gap-3 px-2 py-1.5 rounded ${r.province === currentProvince ? "bg-primary/10 ring-1 ring-primary/40" : ""}`}>
          <span className="text-[10px] w-5 text-muted-foreground tabular-nums">#{i + 1}</span>
          <span className="text-[11px] flex-1">{r.province}</span>
          <span className="text-[11px] tabular-nums font-bold" style={{ color: RISK_COLORS[r.riskLevel] ?? "#6b7280" }}>
            {r.riskScore.toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
}

function RejectReasonModal({
  item,
  reasons,
  onCancel,
  onConfirm,
}: {
  item: ReviewItem;
  reasons: string[];
  onCancel: () => void;
  onConfirm: (reason: string, notes?: string) => void;
}) {
  const [reason, setReason] = useState<string>("");
  const [other, setOther] = useState("");
  const [notes, setNotes] = useState("");

  const finalReason = reason === "Other" ? other.trim() : reason;
  const valid = finalReason.length > 0;

  return (
    <div className="fixed inset-0 z-[2100] bg-background/80 backdrop-blur-sm flex items-center justify-center p-6 compact:p-3">
      <div className="surface-dialog border border-destructive/40 w-full max-w-md overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border/40 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-destructive">Reject forecast</h2>
            <p className="text-[10px] text-muted-foreground">
              {item.province} · {item.quarter} · This action is permanent until restored from the Rejection Log.
            </p>
          </div>
          <button onClick={onCancel} aria-label="Close" className="p-1.5 compact:min-h-11 compact:min-w-11 flex items-center justify-center rounded-md hover:bg-secondary/60"><X className="h-4 w-4" /></button>
        </div>

        <div className="p-5 space-y-3">
          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
              Rejection reason <span className="text-destructive">*</span>
            </label>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full h-9 compact:h-11 compact:text-[16px] rounded-md border border-border/60 bg-background px-2 text-[12px] focus:outline-none focus:ring-2 focus:ring-destructive"
            >
              <option value="">Select a reason…</option>
              {reasons.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            {reason === "Other" && (
              <input
                value={other}
                onChange={(e) => setOther(e.target.value)}
                placeholder="Specify reason…"
                className="mt-2 w-full h-9 compact:h-11 compact:text-[16px] rounded-md border border-border/60 bg-background px-2 text-[12px] focus:outline-none focus:ring-2 focus:ring-destructive"
              />
            )}
          </div>

          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
              Notes <span className="text-muted-foreground/60 normal-case font-normal">(optional)</span>
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={2000}
              rows={3}
              placeholder="Additional context for audit log…"
              className="w-full rounded-md border border-border/60 bg-background px-2 py-1.5 text-[12px] compact:text-[16px] focus:outline-none focus:ring-2 focus:ring-destructive resize-none"
            />
          </div>
        </div>

        <div className="px-5 py-3 border-t border-border/40 flex items-center justify-end gap-2">
          <button onClick={onCancel} className="px-3 py-1.5 compact:min-h-11 rounded-md border edge-control text-[11px] hover:bg-secondary/60">Cancel</button>
          <button
            onClick={() => valid && onConfirm(finalReason, notes.trim() || undefined)}
            disabled={!valid}
            className="px-3 py-1.5 compact:min-h-11 rounded-md bg-destructive shadow-md text-destructive-foreground text-[11px] font-bold hover:bg-destructive/90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Confirm rejection
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------- Feedback (SUS submissions list) ---------- */
function FeedbackSection() {
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<FeedbackRow | null>(null);
  const { data: feedbackRes, isLoading } = useAdminFeedback(page, 50);

  const items = feedbackRes?.data ?? [];
  const summary = feedbackRes?.summary;

  return (
    <div>
      <SectionHeader title="Feedback" subtitle="System Usability Scale (SUS) submissions from public users" />
      <div className="p-6 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Stat label="Submissions" value={(summary?.count ?? 0).toString()} />
          <Stat label="Average SUS" value={summary?.meanScore != null ? `${summary.meanScore}/100` : "—"} accent />
          <Stat label="Latest" value={items[0] ? new Date(items[0].date).toLocaleDateString() : "—"} />
        </div>

        <div className="bg-card border edge-faint rounded-xl shadow-lg overflow-hidden">
          <table role="table" className="w-full text-[11px] stack-table">
            <thead role="rowgroup" className="bg-secondary/40 text-muted-foreground">
              <tr role="row">
                <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Date</th>
                <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Name</th>
                <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Agency</th>
                <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Score</th>
                <th role="columnheader" className="text-left font-semibold px-4 py-2.5">Action</th>
              </tr>
            </thead>
            <tbody role="rowgroup">
              {!isLoading && items.length === 0 && (
                <tr role="row">
                  <td role="cell" colSpan={5} className="px-4 py-8 text-center text-muted-foreground italic">
                    No feedback submissions yet.
                  </td>
                </tr>
              )}
              {items.map((f) => (
                <tr role="row" key={f.id} className="border-t edge-control hover:bg-secondary/30">
                  <td role="cell" data-label="Date" className="px-4 py-2.5 tabular-nums">{new Date(f.date).toLocaleDateString()}</td>
                  <td role="cell" data-label="Name" className="px-4 py-2.5 font-medium">{f.demographics.fullName || "Anonymous"}</td>
                  <td role="cell" data-label="Agency" className="px-4 py-2.5 text-muted-foreground">{f.demographics.agency || "—"}</td>
                  <td role="cell" data-label="Score" className="px-4 py-2.5">
                    <span
                      className={`font-bold tabular-nums ${f.score >= 68 ? "text-value-success" : "text-value-danger"}`}
                      title={f.score >= 68 ? "At or above the SUS benchmark of 68" : "Below the SUS benchmark of 68"}
                    >
                      {f.score}/100
                    </span>
                  </td>
                  <td role="cell" data-label="Action" className="px-4 py-2.5">
                    <button
                      onClick={() => setOpen(f)}
                      className="text-primary hover:underline text-[11px] font-semibold flex items-center gap-1 compact:min-h-11"
                    >
                      <Eye className="h-3 w-3" /> View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {feedbackRes && feedbackRes.total > feedbackRes.pageSize && (
          <div className="flex items-center justify-between text-[11px]">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 compact:min-h-11 rounded-md border edge-control hover:bg-secondary/60 disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-muted-foreground">Page {feedbackRes.page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page * feedbackRes.pageSize >= feedbackRes.total}
              className="px-3 py-1.5 compact:min-h-11 rounded-md border edge-control hover:bg-secondary/60 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {open && <FeedbackDetailModal item={open} questions={feedbackRes?.questions ?? []} onClose={() => setOpen(null)} />}
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="bg-card border edge-faint rounded-xl shadow-md px-4 py-3">
      <MetricLabel>{label}</MetricLabel>
      <p className={`font-mono-num text-2xl font-bold mt-1 tabular-nums ${accent ? "text-primary" : ""}`}>{value}</p>
    </div>
  );
}

function FeedbackDetailModal({ item, questions, onClose }: { item: FeedbackRow; questions: string[]; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-[2000] bg-background/70 backdrop-blur-sm flex items-center justify-center p-6 compact:p-0">
      <div className="surface-dialog border compact:rounded-none w-full max-w-2xl max-h-[88vh] compact:h-full compact:max-h-full overflow-hidden flex flex-col">
        <div className="px-5 py-3.5 border-b border-border/40 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold">SUS Feedback · {new Date(item.date).toLocaleDateString()}</h2>
            <p className="text-[10px] text-muted-foreground">
              {item.demographics.fullName || "Anonymous"} · {item.demographics.agency || "—"} · Score{" "}
              <span className="font-bold text-foreground">{item.score}/100</span>
            </p>
          </div>
          <button onClick={onClose} aria-label="Close" className="p-1.5 compact:min-h-11 compact:min-w-11 flex items-center justify-center rounded-md hover:bg-secondary/60"><X className="h-4 w-4" /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          <div className="grid grid-cols-2 compact:grid-cols-1 gap-2 text-[11px]">
            <KV k="Email" v={item.demographics.email || "—"} />
            <KV k="Designation" v={item.demographics.designation || "—"} />
            <KV k="Age" v={item.demographics.age || "—"} />
            <KV k="Sex" v={item.demographics.sex || "—"} />
            <KV k="Client type" v={item.demographics.clientType || "—"} />
            <KV k="Province" v={item.demographics.province || "—"} />
            <KV k="Municipality" v={item.demographics.municipality || "—"} />
          </div>

          <div>
            <h4 className="text-[11px] font-bold uppercase tracking-wider mb-2">Likert responses</h4>
            <ol className="space-y-1.5">
              {questions.map((q, i) => (
                <li key={i} className="text-[11px] compact:text-[14px] flex items-start gap-2">
                  <span className="text-muted-foreground tabular-nums w-5">{i + 1}.</span>
                  <span className="flex-1">{q}</span>
                  <span className="font-bold tabular-nums w-6 text-right">{item.answers[String(i)] ?? "—"}</span>
                </li>
              ))}
            </ol>
          </div>

          {(item.liked || item.improvements) && (
            <div className="grid grid-cols-1 gap-2">
              {item.liked && (
                <div className="bg-secondary/30 border edge-faint rounded-md p-3">
                  <MetricLabel className="mb-1">Liked most</MetricLabel>
                  <p className="text-[11px] compact:text-[14px] leading-snug">{item.liked}</p>
                </div>
              )}
              {item.improvements && (
                <div className="bg-secondary/30 border edge-faint rounded-md p-3">
                  <MetricLabel className="mb-1">Suggestions</MetricLabel>
                  <p className="text-[11px] compact:text-[14px] leading-snug">{item.improvements}</p>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="px-5 py-3 border-t border-border/40 flex items-center justify-end">
          <button onClick={onClose} className="px-3 py-1.5 compact:min-h-11 rounded-md border edge-control text-[11px] hover:bg-secondary/60">Close</button>
        </div>
      </div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="bg-secondary/30 border edge-faint rounded-md px-2.5 py-1.5">
      <MetricLabel>{k}</MetricLabel>
      <p className="text-[11px] font-medium truncate">{v}</p>
    </div>
  );
}
