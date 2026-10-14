import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Home, Database, BarChart3, Map as MapIcon, ClipboardCheck, MessageSquareText, Users, Menu, LogIn, LogOut, Sun, Moon, X, Mail, Lock, ArrowRight, Eye, EyeOff } from "lucide-react";
import { Note } from "@/components/ui/note";
import { Sheet, SheetClose, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { DisplayPreferencesModal } from "./DisplayPreferencesModal";
import { toast } from "@/hooks/use-toast";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { authLinkClass, authLinksRowClass } from "@/components/AuthCard";
import { PENDING_CODES, SignInNotice } from "@/components/SignInNotice";
import { ADMIN_NAV, adminPath, isActivePath } from "@/lib/adminNav";
import { useAccounts } from "@/lib/queries";
import { StatusBadge } from "@/components/ui/status-badge";
import { PSTClock } from "./PSTClock";
import logoDark from "@/assets/logo-dark.png";
import logoLight from "@/assets/logo-light.png";
import logoIcon from "@/assets/logo-icon.png";

interface Props {
  active?: "home" | "data" | "viz" | "none";
}

const THEME_KEY = "aipheed_theme";

export function TopNavbar({ active = "none" }: Props) {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    return (localStorage.getItem(THEME_KEY) as "dark" | "light") ?? "dark";
  });
  const [loginOpen, setLoginOpen] = useState(false);
  // Signed-in admins get the admin navigation on public pages too. Decided by
  // the server-confirmed session only -- never a URL parameter or a stored flag.
  const { status, user, logout } = useAuth();
  const isAdmin = status === "authenticated";
  const isDemo = isAdmin && !!user?.isDemo;
  // Fetched with the header, so the menu's pending count is ready when it opens.
  // Never for the demo account, which may not see account requests at all.
  useAccounts(isAdmin && !isDemo);

  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    localStorage.setItem(THEME_KEY, theme);
    window.dispatchEvent(new CustomEvent("aipheed:theme", { detail: { theme } }));
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  return (
    <header className="relative h-16 shrink-0 bg-card/95 backdrop-blur-sm border-b border-border/50 z-[1002] flex items-center px-4 gap-3">
      {/* Brand → landing */}
      <Link to="/" className="flex items-center mr-2 hover:opacity-90 transition-opacity shrink-0" aria-label="aiPHeed home">
        <img src={logoIcon} alt="aiPHeed" className="sm:hidden h-9 w-9 object-contain" />
        <img src={logoDark} alt="aiPHeed — Food Insecurity Forecasting" className="hidden sm:block dark-only h-10 w-auto object-contain" />
        <img src={logoLight} alt="aiPHeed — Food Insecurity Forecasting" className="hidden sm:block light-only h-10 w-auto object-contain" />
      </Link>
      {isDemo && <DemoBadge />}

      {/* Nav links — centered */}
      {/* A signed-in admin has five links; below 1024px they move into the menu. */}
      {/* The demo account also shows a "Demo account" badge, so its links move
          into the menu below 1280px instead of 1024px (see AdminMenuLinks). */}
      <nav className={`absolute left-1/2 -translate-x-1/2 items-center gap-1 ${isDemo ? "hidden xl:flex" : isAdmin ? "hidden lg:flex" : "flex"}`}>
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

      {/* PST clock */}
      <PSTClock />

      {/* Hamburger */}
      <Sheet>
        <SheetTrigger className="p-1.5 rounded-md hover:bg-secondary/60 transition-colors" aria-label="Menu">
          <Menu className="h-4 w-4" />
        </SheetTrigger>
        <SheetContent side="right" className="w-[280px] bg-card border-l border-border/50 z-[1100]">
          <SheetHeader>
            <SheetTitle className="text-sm">Menu</SheetTitle>
          </SheetHeader>
          <div className="mt-6 space-y-1">
            {isAdmin && <AdminMenuLinks demo={isDemo} />}
            <p className="text-[9px] uppercase tracking-widest text-muted-foreground/60 font-semibold px-2 mb-1">
              Account
            </p>
            {isAdmin && !isDemo && <AdminAccountsMenuItem />}
            {isAdmin ? (
              <button onClick={() => void logout()} className="w-full">
                <MenuRow icon={LogOut} label="Sign out" hint={user?.email} />
              </button>
            ) : (
              <button onClick={() => setLoginOpen(true)} className="w-full">
                <MenuRow icon={LogIn} label="DA Admin Login" hint="Restricted administrator access" />
              </button>
            )}

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
                  className={`relative inline-flex h-5 w-10 items-center rounded-full transition-colors border ${
                    theme === "light"
                      ? "bg-primary/30 border-primary/50"
                      : "bg-secondary border-border/50"
                  }`}
                >
                  <span className="absolute left-1 text-[8px]">🌙</span>
                  <span className="absolute right-1 text-[8px]">☀️</span>
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
          </div>
        </SheetContent>
      </Sheet>

      <AdminLoginModal open={loginOpen} onOpenChange={setLoginOpen} />
    </header>
  );
}

function AdminLoginModal({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [notice, setNotice] = useState<{ code: string; message: string; email: string } | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setNotice(null);
    const address = email.trim().toLowerCase();
    try {
      await login(address, password);
      toast({ title: "Welcome, DA Administrator", description: "Routing to admin dashboard…" });
      onOpenChange(false);
      navigate("/admin");
    } catch (err) {
      if (err instanceof ApiError && PENDING_CODES.has(err.code)) {
        setNotice({ code: err.code, message: err.message, email: address });
      } else {
        toast({
          title: "Sign-in failed",
          description: err instanceof Error ? err.message : "Could not reach the server.",
          variant: "destructive",
        });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="z-[1300] max-w-sm p-7 bg-card/95 backdrop-blur-md border border-border/50 rounded-2xl shadow-2xl shadow-primary/10">
        <DialogHeader>
          <div className="flex flex-col items-center text-center">
            <img src={logoIcon} alt="aiPHeed" className="h-20 w-20 object-contain mb-3 drop-shadow-[0_0_24px_rgba(232,69,60,0.35)]" />
            <DialogTitle className="text-lg font-bold tracking-tight">DA Admin Sign In</DialogTitle>
            <DialogDescription className="text-[11px] text-muted-foreground mt-1">
              Authorized access for feedback and review workflows
            </DialogDescription>
          </div>
        </DialogHeader>

        <form onSubmit={submit} className="space-y-3 mt-2">
          <div>
            <label htmlFor="admin-dialog-email" className="text-[10px] uppercase tracking-wider text-muted-foreground/70 font-semibold">Email</label>
            <div className="relative mt-1">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60" />
              <input
                id="admin-dialog-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                maxLength={200}
                autoComplete="username"
                className="w-full h-10 pl-9 pr-3 text-[12px] bg-secondary/50 border border-border/40 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus:border-primary/50 focus:bg-secondary/80 placeholder:text-muted-foreground/50"
              />
            </div>
          </div>

          <div>
            <label htmlFor="admin-dialog-password" className="text-[10px] uppercase tracking-wider text-muted-foreground/70 font-semibold">Password</label>
            <div className="relative mt-1">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60" />
              <input
                id="admin-dialog-password"
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                maxLength={1024}
                autoComplete="current-password"
                className="w-full h-10 pl-9 pr-10 text-[12px] bg-secondary/50 border border-border/40 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus:border-primary/50 focus:bg-secondary/80 placeholder:text-muted-foreground/50"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                title={showPassword ? "Hide password" : "Show password"}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-muted-foreground hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-10 mt-2 flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground text-[12px] font-bold hover:bg-primary/90 transition-colors shadow-md shadow-primary/20 disabled:opacity-60"
          >
            {loading ? "Checking access…" : "Sign in to Admin"}
            {!loading && <ArrowRight className="h-3.5 w-3.5" />}
          </button>
        </form>

        {notice && <SignInNotice {...notice} />}

        <Note className="mt-5">Administrator access is restricted to @calabarzon.da.gov.ph email addresses.</Note>

        <p className={authLinksRowClass}>
          <Link to="/forgot-password" onClick={() => onOpenChange(false)} className={authLinkClass}>
            Forgot password?
          </Link>
          <Link to="/signup" onClick={() => onOpenChange(false)} className={authLinkClass}>
            Create an account
          </Link>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className={authLinkClass}
          >
            Back to public map
          </button>
        </p>
      </DialogContent>
    </Dialog>
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
      className={`group relative px-4 py-2 text-[12px] font-semibold uppercase tracking-[0.14em] transition-colors ${
        active ? "text-primary" : "text-foreground/80 hover:text-primary"
      }`}
    >
      <span>{label}</span>
      <span
        className={`pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-1 h-[2px] rounded-full bg-primary transition-all duration-300 ${
          active ? "w-6 opacity-100" : "w-0 opacity-0 group-hover:w-6 group-hover:opacity-100"
        }`}
      />
    </Link>
  );
}

function MenuRow({ icon: Icon, label, hint, badge }: { icon: typeof Home; label: string; hint?: string; badge?: React.ReactNode }) {
  return (
    <span className="w-full flex items-center gap-3 px-2 py-2 rounded-md hover:bg-secondary/60 transition-colors text-left">
      <Icon className="h-3.5 w-3.5 text-muted-foreground" />
      <span className="flex-1 min-w-0">
        <span className="block text-[11px] font-medium">{label}</span>
        {hint && <span className="block text-[9px] text-muted-foreground/70 truncate">{hint}</span>}
      </span>
      {badge}
    </span>
  );
}
