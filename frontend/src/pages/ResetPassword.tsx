import { useState } from "react";
import { Link } from "react-router-dom";
import { Lock } from "lucide-react";
import { Note } from "@/components/ui/note";
import { AuthCard, AuthField, AuthSubmit, PASSWORD_RULES, authLinkClass, authLinksRowClass } from "@/components/AuthCard";
import { api, ApiError } from "@/lib/api";
import type { MessageResponse } from "@/lib/apiTypes";
import { useLinkToken } from "@/lib/linkToken";

const LINK_CODES = new Set(["link_invalid", "link_expired", "link_used"]);

export default function ResetPassword() {
  // Read once, then removed from the address bar (see lib/linkToken.ts).
  const token = useLinkToken();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [linkProblem, setLinkProblem] = useState<string | null>(token ? null : "This link is not valid. Request a new one.");
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
      const res = await api.post<MessageResponse>("/api/v1/auth/reset-password", { token, password }, { auth: false });
      setDone(res.message);
    } catch (err) {
      if (err instanceof ApiError && LINK_CODES.has(err.code)) setLinkProblem(err.message);
      else setProblem(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <AuthCard title="Password changed" subtitle="Sign in with your new password">
        <Note label={null}>{done}</Note>
        <p className={authLinksRowClass}>
          <Link to="/login" className={authLinkClass}>Sign in</Link>
        </p>
      </AuthCard>
    );
  }

  if (linkProblem) {
    return (
      <AuthCard title="Link not accepted" subtitle="Password reset links work once, for 1 hour">
        <Note label={null}>{linkProblem}</Note>
        <p className={authLinksRowClass}>
          <Link to="/forgot-password" className={authLinkClass}>Request a new link</Link>
          <Link to="/login" className={authLinkClass}>Back to sign in</Link>
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Choose a new password" subtitle="This signs you out on every device">
      <form onSubmit={submit} className="space-y-3">
        <AuthField id="reset-password" label="New password" icon={Lock} type="password" value={password} onChange={setPassword}
          autoComplete="new-password" maxLength={1024} hint={PASSWORD_RULES} />
        <AuthField id="reset-confirm" label="Confirm new password" icon={Lock} type="password" value={confirm} onChange={setConfirm}
          autoComplete="new-password" maxLength={1024} />
        {problem && <Note label={null}>{problem}</Note>}
        <AuthSubmit loading={loading} label="Change password" loadingLabel="Changing password…" />
      </form>
      <p className={authLinksRowClass}>
        <Link to="/login" className={authLinkClass}>Back to sign in</Link>
      </p>
    </AuthCard>
  );
}
