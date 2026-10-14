// src/components/SignInNotice.tsx
// ---------------------------------
// What the sign-in form says when the password was right but the account is
// not active yet (the server only reveals this after a correct password):
//   email_not_verified       -> "Verify your email to continue." + resend
//   account_pending_approval -> "Your account is waiting for approval."
// Used by /login and the header sign-in dialog.

import { useState } from "react";
import { Note } from "@/components/ui/note";
import { api, ApiError } from "@/lib/api";
import type { MessageResponse } from "@/lib/apiTypes";

export function SignInNotice({ code, message, email }: { code: string; message: string; email: string }) {
  const [sent, setSent] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const resend = async () => {
    setSending(true);
    try {
      const res = await api.post<MessageResponse>("/api/v1/auth/resend-verification", { email }, { auth: false });
      setSent(res.message);
    } catch (err) {
      setSent(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setSending(false);
    }
  };

  return (
    <Note label={null} className="mt-4">
      {message}
      {code === "email_not_verified" && (
        <>
          {" "}
          {sent ? (
            <span className="block mt-1">{sent}</span>
          ) : (
            <button
              type="button"
              onClick={resend}
              disabled={sending}
              className="underline underline-offset-2 hover:text-foreground disabled:opacity-60"
            >
              {sending ? "Sending…" : "Resend verification email"}
            </button>
          )}
        </>
      )}
    </Note>
  );
}
