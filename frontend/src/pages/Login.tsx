import { useState } from "react";
import { useNavigate, useLocation, Link, Navigate } from "react-router-dom";
import { Mail, Lock } from "lucide-react";
import { Note } from "@/components/ui/note";
import { toast } from "@/hooks/use-toast";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { safeRedirectPath } from "@/lib/redirect";
import { AuthCard, AuthField, AuthSubmit, authLinkClass, authLinksRowClass } from "@/components/AuthCard";
import { SignInNotice } from "@/components/SignInNotice";
import { PENDING_SIGN_IN_CODES } from "@/lib/apiTypes";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, status } = useAuth();
  // The admin page that sent us here (RequireAdmin), if it is a path on this site.
  const returnTo = safeRedirectPath((location.state as { from?: unknown } | null)?.from);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  // Right password, account not active yet: said on the page, not in a toast.
  const [notice, setNotice] = useState<{ code: string; message: string; email: string } | null>(null);

  // Already signed in: no form to show. Same destination as after a sign-in
  // (the requested page, else /admin), so the two cannot race each other.
  if (status === "authenticated") {
    return <Navigate to={returnTo} replace />;
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setNotice(null);
    const address = email.trim().toLowerCase();
    try {
      // The backend is now the sole authority on the email/password check
      // (domain restriction included) -- no client-side check is duplicated
      // here, so this can't drift out of sync with the server's own rule.
      await login(address, password);
      toast({
        title: "Welcome, DA Administrator",
        description: "Routing to admin dashboard…",
      });
      navigate(returnTo, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && PENDING_SIGN_IN_CODES.has(err.code)) {
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
    <AuthCard title="DA Admin Sign In" subtitle="Authorized access for feedback and review workflows">
      <form onSubmit={submit} className="space-y-3">
        <AuthField id="login-email" label="Email" icon={Mail} type="email" value={email} onChange={setEmail}
          autoComplete="username" />
        <AuthField id="login-password" label="Password" icon={Lock} type="password" value={password} onChange={setPassword}
          autoComplete="current-password" maxLength={1024} />
        <AuthSubmit loading={loading} label="Sign in to Admin" loadingLabel="Checking access…" />
      </form>

      {notice && <SignInNotice {...notice} />}

      <Note className="mt-5">Administrator access is restricted to @calabarzon.da.gov.ph email addresses.</Note>

      <p className={authLinksRowClass}>
        <Link to="/forgot-password" className={authLinkClass}>Forgot password?</Link>
        <Link to="/signup" className={authLinkClass}>Create an account</Link>
        <Link to="/" className={authLinkClass}>Back to public map</Link>
      </p>
    </AuthCard>
  );
}
