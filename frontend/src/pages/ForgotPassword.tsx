import { useState } from "react";
import { Link } from "react-router-dom";
import { Mail } from "lucide-react";
import { Note } from "@/components/ui/note";
import { AuthCard, AuthField, AuthSubmit, authLinkClass, authLinksRowClass } from "@/components/AuthCard";
import { api, ApiError } from "@/lib/api";
import type { MessageResponse } from "@/lib/apiTypes";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [reply, setReply] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setProblem(null);
    try {
      const res = await api.post<MessageResponse>(
        "/api/v1/auth/forgot-password", { email: email.trim().toLowerCase() }, { auth: false }
      );
      setReply(res.message);
    } catch (err) {
      setProblem(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthCard title="Forgot password" subtitle="We will email you a link to choose a new one">
      {reply ? (
        <Note label={null}>{reply}</Note>
      ) : (
        <form onSubmit={submit} className="space-y-3">
          <AuthField id="forgot-email" label="Official email" icon={Mail} type="email" value={email} onChange={setEmail} autoComplete="username" />
          {problem && <Note label={null}>{problem}</Note>}
          <AuthSubmit loading={loading} label="Send reset link" loadingLabel="Sending…" />
        </form>
      )}
      <p className={authLinksRowClass}>
        <Link to="/login" className={authLinkClass}>Back to sign in</Link>
      </p>
    </AuthCard>
  );
}
