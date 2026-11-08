import { useState } from "react";
import { Link } from "react-router-dom";
import { Mail, Lock, User, Building2 } from "lucide-react";
import { Note } from "@/components/ui/note";
import { AuthAlert, AuthCard, AuthField, AuthSubmit, DOMAIN_HINT, PASSWORD_RULES, authLinkClass, authLinksRowClass } from "@/components/AuthCard";
import { api, ApiError } from "@/lib/api";
import type { MessageResponse } from "@/lib/apiTypes";

// The server is the authority on every rule (domain, password policy,
// lengths); the only client-side check is that the two passwords match.
export default function SignUp() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [office, setOffice] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setProblem(null);
    if (password !== confirm) {
      setProblem("The two passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      const res = await api.post<MessageResponse>(
        "/api/v1/auth/signup",
        { fullName: fullName.trim(), email: email.trim().toLowerCase(), office: office.trim(), password },
        { auth: false }
      );
      setDone(res.message);
    } catch (err) {
      setProblem(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <AuthCard title="Check your email" subtitle="One more step before an administrator can review your request.">
        <Note label={null}>{done}</Note>
        <p className={authLinksRowClass}>
          <Link to="/login" className={authLinkClass}>Back to sign in</Link>
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Request administrator access" subtitle="Requests need email verification and approval by an administrator.">
      <form onSubmit={submit} className="space-y-4">
        <AuthField id="signup-name" label="Full name" icon={User} value={fullName} onChange={setFullName} autoComplete="name" />
        <AuthField id="signup-email" label="Official email" icon={Mail} type="email" value={email} onChange={setEmail} autoComplete="email" hint={DOMAIN_HINT} />
        <AuthField id="signup-office" label="Office / unit" icon={Building2} value={office} onChange={setOffice} autoComplete="organization" />
        <AuthField id="signup-password" label="Password" icon={Lock} type="password" value={password} onChange={setPassword}
          autoComplete="new-password" maxLength={1024} hint={PASSWORD_RULES} />
        <AuthField id="signup-confirm" label="Confirm password" icon={Lock} type="password" value={confirm} onChange={setConfirm}
          autoComplete="new-password" maxLength={1024} />
        {problem && <AuthAlert>{problem}</AuthAlert>}
        <AuthSubmit loading={loading} label="Request access" loadingLabel="Sending request…" />
      </form>

      <p className={authLinksRowClass}>
        <span>
          Already have access?{" "}
          <Link to="/login" className={authLinkClass}>Sign in</Link>
        </span>
      </p>
    </AuthCard>
  );
}
