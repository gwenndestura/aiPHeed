import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Mail } from "lucide-react";
import { Note } from "@/components/ui/note";
import { AuthCard, AuthField, AuthSubmit, authLinkClass, authLinksRowClass } from "@/components/AuthCard";
import { api, ApiError } from "@/lib/api";
import type { MessageResponse, VerifyEmailResponse } from "@/lib/apiTypes";
import { useLinkToken } from "@/lib/linkToken";

type State = { kind: "checking" } | { kind: "verified"; message: string } | { kind: "failed"; message: string };

export default function VerifyEmail() {
  // Read once, then removed from the address bar (see lib/linkToken.ts).
  const token = useLinkToken();
  const [state, setState] = useState<State>({ kind: "checking" });
  const sent = useRef(false);

  useEffect(() => {
    if (sent.current) return;
    sent.current = true;
    if (!token) {
      setState({ kind: "failed", message: "This link is not valid. Request a new one." });
      return;
    }
    api
      .post<VerifyEmailResponse>("/api/v1/auth/verify-email", { token }, { auth: false })
      .then((res) => setState({ kind: "verified", message: res.message }))
      .catch((err) =>
        setState({ kind: "failed", message: err instanceof ApiError ? err.message : "Could not reach the server." })
      );
  }, [token]);

  if (state.kind === "checking") {
    return (
      <AuthCard title="Verifying your email" subtitle="One moment…">
        <Note label={null}>Checking your link…</Note>
      </AuthCard>
    );
  }

  if (state.kind === "verified") {
    return (
      <AuthCard title="Email verified" subtitle="Your account request is with the administrators">
        <Note label={null}>{state.message}</Note>
        <p className={authLinksRowClass}>
          <Link to="/login" className={authLinkClass}>Back to sign in</Link>
          <Link to="/" className={authLinkClass}>Back to public map</Link>
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Link not accepted" subtitle="Request a new verification email below">
      <Note label={null}>{state.message}</Note>
      <ResendForm />
      <p className={authLinksRowClass}>
        <Link to="/login" className={authLinkClass}>Back to sign in</Link>
      </p>
    </AuthCard>
  );
}

function ResendForm() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [reply, setReply] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.post<MessageResponse>(
        "/api/v1/auth/resend-verification", { email: email.trim().toLowerCase() }, { auth: false }
      );
      setReply(res.message);
    } catch (err) {
      setReply(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setLoading(false);
    }
  };

  if (reply) return <Note label={null} className="mt-4">{reply}</Note>;
  return (
    <form onSubmit={submit} className="space-y-3 mt-4">
      <AuthField id="resend-email" label="Your official email" icon={Mail} type="email" value={email} onChange={setEmail} autoComplete="email" />
      <AuthSubmit loading={loading} label="Resend verification email" loadingLabel="Sending…" />
    </form>
  );
}
