import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Home, Database, BarChart3, Map as MapIcon, ClipboardCheck, MessageSquareText, Users, Menu, LogIn, LogOut, Sun, Moon, Compass } from "lucide-react";
import { Sheet, SheetClose, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { DisplayPreferencesModal } from "./DisplayPreferencesModal";
import { useAuth } from "@/lib/auth";
import { ADMIN_NAV, adminPath, isActivePath } from "@/lib/adminNav";
import { useAccounts } from "@/lib/queries";
import { StatusBadge } from "@/components/ui/status-badge";
import { PSTClock, PSTClockMenuRow } from "./PSTClock";
import { requestTour, tourForPath, TOUR_HINTS } from "@/lib/tour";
import logoDark from "@/assets/logo-dark.png";
import logoLight from "@/assets/logo-light.png";
import logoIcon from "@/assets/logo-icon.png";
import { readStorage, writeStorage } from "@/lib/storage";

interface Props {
  active?: "home" | "data" | "viz" | "none";
}

const THEME_KEY = "aipheed_theme";

export function TopNavbar({ active = "none" }: Props) {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    return (readStorage(THEME_KEY) as "dark" | "light" | null) ?? "dark";
  });
  // Signed-in admins get the admin navigation on public pages too. Decided by
  // the server-confirmed session only -- never a URL parameter or a stored flag.
  const { status, user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isAdmin = status === "authenticated";
  const signedOut = status === "anonymous";
  const isDemo = isAdmin && !!user?.isDemo;
  // Fetched with the header, so the menu's pending count is ready when it opens.
  // Never for the demo account, which may not see account requests at all.
  useAccounts(isAdmin && !isDemo);

  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    writeStorage(THEME_KEY, theme);
    window.dispatchEvent(new CustomEvent("aipheed:theme", { detail: { theme } }));
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  return (
    <header className="relative h-16 shrink-0 surface-header z-[1002] flex items-center px-4 gap-3">
      {/* Brand → landing */}
      <Link to="/" className="flex items-center mr-2 hover:opacity-90 transition-opacity shrink-0 max-lg:min-h-11 max-lg:min-w-11" aria-label="aiPHeed home">
        <img src={logoIcon} alt="aiPHeed" className="sm:hidden h-9 w-9 object-contain" />
        <img src={logoDark} alt="aiPHeed — Food Insecurity Forecasting" className="hidden sm:block dark-only h-10 w-auto object-contain" />
        <img src={logoLight} alt="aiPHeed — Food Insecurity Forecasting" className="hidden sm:block light-only h-10 w-auto object-contain" />
      </Link>
      {isDemo && <DemoBadge />}

      {/* Nav links — centered */}
      {/* Public: three links, in the menu below 768px (PublicMenuLinks). */}
      {/* A signed-in admin has five links; below 1024px they move into the menu. */}
      {/* The demo account also shows a "Demo account" badge, so its links move
          into the menu below 1280px instead of 1024px (see AdminMenuLinks). */}
      <nav data-tour="pages" className={`absolute left-1/2 -translate-x-1/2 items-center gap-1 ${isDemo ? "hidden xl:flex" : isAdmin ? "hidden lg:flex" : "hidden md:flex"}`}>
        {isAdmin ? (
          <AdminNavLinks />
        ) : (
          <>
            <NavBtn label="Mapping" active={active === "home"} to="/dashboard" />
            <NavBtn label="Data" active={active === "data"} to="/data" />
            <NavBtn label="Visualization" active={active === "viz"} to="/visualization" />
          </>
        )}
      </nav>

      <div className="flex-1" />

      {/* PST clock -- in the menu below 1024px (1280px for admins) */}
      <PSTClock from={isAdmin ? "xl" : "lg"} />

      {/* Hamburger */}
      <Sheet>
        <SheetTrigger className={MENU_TRIGGER_CLASS} aria-label="Menu" data-tour="pages">
          <Menu className="h-4 w-4" />
        </SheetTrigger>
        {/* A full-height column: the items scroll when the screen is short
            (a phone held sideways); the sign-in footer stays at the bottom. */}
        <SheetContent side="right" className="w-[280px] [--surface-base:var(--card)] border-l z-[1100] flex flex-col gap-0 p-0">
          <SheetHeader className="shrink-0 px-6 pt-6">
            <SheetTitle className="text-sm">Menu</SheetTitle>
          </SheetHeader>
          <div className={`flex-1 min-h-0 overflow-y-auto thin-scrollbar px-6 mt-6 space-y-1 ${signedOut ? "pb-4" : "pb-[calc(1.5rem+env(safe-area-inset-bottom))]"}`}>
            {isAdmin ? <AdminMenuLinks demo={isDemo} /> : <PublicMenuLinks active={active} />}
            <PSTClockMenuRow from={isAdmin ? "xl" : "lg"} />
            {/* Signed in: Accounts and Sign out. Visitors who are not signed in
                get "Admin sign in" in the footer at the bottom of the menu. */}
            {isAdmin && (
              <>
                <p className="text-[9px] uppercase tracking-widest text-muted-foreground/60 font-semibold px-2 mb-1">
                  Account
                </p>
                {!isDemo && <AdminAccountsMenuItem />}
                <button onClick={() => void logout()} className="w-full">
                  <MenuRow icon={LogOut} label="Sign out" hint={user?.email} />
                </button>
              </>
            )}

            <div className={`${isAdmin ? "pt-3 mt-3 border-t border-border/40" : ""}`}>
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

            <div className="pt-3 mt-3 border-t border-border/40">
              <p className="text-[9px] uppercase tracking-widest text-muted-foreground/60 font-semibold px-2 mb-2">
                Settings
              </p>
              <DisplayPreferencesModal />
            </div>

            <div className="pt-3 mt-3 border-t border-border/40">
              <p className="text-[9px] uppercase tracking-widest text-muted-foreground/60 font-semibold px-2 mb-1">
                Help
              </p>
              {/* Replays this page's guided tour; pages without one get the map's (opening the map page first). */}
              <SheetClose asChild>
                <button type="button" onClick={() => requestTour(navigate, pathname)} className="w-full">
                  <MenuRow icon={Compass} label="Take the tour" hint={TOUR_HINTS[tourForPath(pathname) ?? "map"]} />
                </button>
              </SheetClose>
            </div>
          </div>

          {/* Footer for visitors who are not signed in: the way to /login for DA
              staff (the only sign-in form). Kept apart from the items above. */}
          {signedOut && (
            <div className="shrink-0 border-t border-border/40 px-6 pt-3 pb-[calc(1.5rem+env(safe-area-inset-bottom))]">
              <p className="text-[9px] uppercase tracking-widest text-muted-foreground/60 font-semibold px-2 mb-1">
                DA staff
              </p>
              <SheetClose asChild>
                <Link to="/login" className="block w-full">
                  <MenuRow icon={LogIn} label="Admin sign in" hint="For DA CALABARZON staff only" wrapHint />
                </Link>
              </SheetClose>
            </div>
          )}
        </SheetContent>
      </Sheet>

    </header>
  );
}

/** The header's menu button: 44px square below 1024px, where it is tapped; as before above. */
export const MENU_TRIGGER_CLASS =
  "flex items-center justify-center rounded-md hover:bg-secondary/60 transition-colors h-11 w-11 -mr-2 lg:mr-0 lg:h-auto lg:w-auto lg:p-1.5";

/** The public links as menu rows, below 768px where the header has room only for the logo and the menu. */
function PublicMenuLinks({ active }: { active: Props["active"] }) {
  const links = [
    { to: "/dashboard", label: "Mapping", icon: MapIcon, on: active === "home" },
    { to: "/data", label: "Data", icon: Database, on: active === "data" },
    { to: "/visualization", label: "Visualization", icon: BarChart3, on: active === "viz" },
  ];
  return (
    <div className="md:hidden pb-3 mb-3 border-b border-border/40">
      <p className="text-[9px] uppercase tracking-widest text-muted-foreground/60 font-semibold px-2 mb-1">
        Navigate
      </p>
      {links.map((l) => (
        <SheetClose asChild key={l.to}>
          <Link to={l.to} className="block w-full" aria-current={l.on ? "page" : undefined}>
            <MenuRow icon={l.icon} label={l.label} />
          </Link>
        </SheetClose>
      ))}
    </div>
  );
}

/** The signed-in admin's links (lib/adminNav.ts), used by this header and the admin header alike. */
export function AdminNavLinks() {
  const { pathname } = useLocation();
  return (
    <>
      {ADMIN_NAV.map((l) => (
        <NavBtn key={l.path} label={l.label} to={l.path} active={isActivePath(pathname, l.path)} />
      ))}
    </>
  );
}

const ADMIN_NAV_ICONS: Record<string, typeof Home> = {
  "/admin": MapIcon,
  "/data": Database,
  "/visualization": BarChart3,
  "/admin/review": ClipboardCheck,
  "/admin/feedback": MessageSquareText,
};

/**
 * The same links as AdminNavLinks, as menu rows, for widths below 1024px where
 * the header has no room for them. Hidden from 1024px up. Each closes the menu.
 */
export function AdminMenuLinks({ demo = false }: { demo?: boolean }) {
  const { pathname } = useLocation();
  return (
    <div className={`${demo ? "xl:hidden" : "lg:hidden"} pb-3 mb-3 border-b border-border/40`}>
      <p className="text-[9px] uppercase tracking-widest text-muted-foreground/60 font-semibold px-2 mb-1">
        Navigate
      </p>
      {ADMIN_NAV.map((l) => (
        <SheetClose asChild key={l.path}>
          <Link to={l.path} className="block w-full" aria-current={isActivePath(pathname, l.path) ? "page" : undefined}>
            <MenuRow icon={ADMIN_NAV_ICONS[l.path] ?? Home} label={l.label} />
          </Link>
        </SheetClose>
      ))}
    </div>
  );
}

/**
 * "Accounts" in the menu (not the header, which is full), with the number of
 * requests waiting for approval. In both headers.
 */
/** "Demo account" next to the logo while the view-only presentation account is signed in. */
export function DemoBadge() {
  return (
    <StatusBadge tone="moderate" className="shrink-0" title="View-only: changes are not available in the demo account.">
      Demo account
    </StatusBadge>
  );
}

export function AdminAccountsMenuItem() {
  const { data } = useAccounts();
  const pending = data?.pendingCount ?? 0;
  return (
    <SheetClose asChild>
      <Link to={adminPath("accounts")} className="block w-full">
        <MenuRow
          icon={Users}
          label="Accounts"
          hint="Approve requests, manage admins"
          badge={pending > 0 ? <StatusBadge tone="moderate" title={`${pending} waiting for approval`}>{pending}</StatusBadge> : null}
        />
      </Link>
    </SheetClose>
  );
}

export function NavBtn({ label, active, to }: { label: string; active?: boolean; to: string }) {
  return (
    <Link
      to={to}
      aria-current={active ? "page" : undefined}
      className={`relative px-4 py-2 max-lg:min-h-11 max-lg:inline-flex max-lg:items-center rounded-full text-[13px] font-medium transition-colors ${
        active ? "nav-active" : "text-foreground/80 hover:text-foreground hover:bg-secondary/60"
      }`}
    >
      <span>{label}</span>
    </Link>
  );
}

/** `wrapHint`: the hint may take a second line instead of being cut off (phones show it larger). */
function MenuRow({ icon: Icon, label, hint, badge, wrapHint = false }: { icon: typeof Home; label: string; hint?: string; badge?: React.ReactNode; wrapHint?: boolean }) {
  return (
    <span className="w-full flex items-center gap-3 px-2 py-2 max-lg:min-h-11 rounded-md hover:bg-secondary/60 transition-colors text-left">
      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      <span className="flex-1 min-w-0">
        <span className="block text-[11px] font-medium">{label}</span>
        {hint && <span className={`block text-[9px] text-muted-foreground/70 ${wrapHint ? "leading-snug" : "truncate"}`}>{hint}</span>}
      </span>
      {badge}
    </span>
  );
}
