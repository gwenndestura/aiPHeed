// src/components/AccountsSection.tsx
// ------------------------------------
// /admin/accounts: requests for admin access (verified, waiting for a
// decision) and the admins who have it. Same table and button styles as the
// Review section. The server enforces every rule (only pending requests can
// be approved, no deactivating yourself); the buttons only mirror them.

import { StatusBadge } from "@/components/ui/status-badge";
import { Note } from "@/components/ui/note";
import { toast } from "@/hooks/use-toast";
import { ApiError } from "@/lib/api";
import type { AccountRow } from "@/lib/apiTypes";
import { useAccountAction, useAccounts, type AccountAction } from "@/lib/queries";

const th = "text-left font-semibold px-4 py-2.5";
const td = "px-4 py-2.5";
const actionBtn = "text-[11px] font-semibold hover:underline disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:no-underline";

const fmtDate = (d?: string | null) => (d ? new Date(d).toLocaleString() : "—");

export function AccountsSection({ readOnlyNote }: { readOnlyNote?: string | null }) {
  const { data, isLoading, error } = useAccounts();
  const action = useAccountAction();
  const busy = action.isPending;
  const locked = busy || !!readOnlyNote;

  const run = (row: AccountRow, kind: AccountAction) => {
    if (kind === "deactivate" && !window.confirm(`Deactivate ${row.email}? They will be signed out everywhere at once.`)) return;
    action.mutate(
      { id: row.id, action: kind },
      {
        onSuccess: () => {
          const done = { approve: "approved", reject: "rejected", deactivate: "deactivated" }[kind];
          toast({ title: `Account ${done}`, description: row.email });
        },
        onError: (err) =>
          toast({ variant: "destructive", title: "Could not update the account", description: err instanceof ApiError ? err.message : "Please try again." }),
      }
    );
  };

  return (
    <div className="px-6 py-5 space-y-6">
      {readOnlyNote && <Note label={null}>{readOnlyNote}</Note>}
      {error && <Note label={null}>{error instanceof ApiError ? error.message : "Data could not be loaded. Try again later."}</Note>}

      <section>
        <h2 className="text-[13px] font-bold tracking-tight mb-2">
          Waiting for approval{data ? ` (${data.pendingCount})` : ""}
        </h2>
        <div className="bg-card border border-border/50 rounded-xl overflow-hidden">
          <table className="w-full text-[11px]">
            <thead className="bg-secondary/40 text-muted-foreground">
              <tr>
                <th className={th}>Name</th>
                <th className={th}>Email</th>
                <th className={th}>Office / unit</th>
                <th className={th}>Email verified</th>
                <th className={th}>Action</th>
              </tr>
            </thead>
            <tbody>
              {(data?.pending ?? []).map((r) => (
                <tr key={r.id} className="border-t border-border/40 hover:bg-secondary/30">
                  <td className={`${td} font-medium`}>{r.name}</td>
                  <td className={td}>{r.email}</td>
                  <td className={td}>{r.office ?? "—"}</td>
                  <td className={`${td} tabular-nums text-muted-foreground`}>{fmtDate(r.emailVerifiedAt)}</td>
                  <td className={`${td} space-x-3 whitespace-nowrap`}>
                    <button onClick={() => run(r, "approve")} disabled={locked} title={readOnlyNote ?? undefined} className={`${actionBtn} text-primary`}>
                      Approve
                    </button>
                    <button onClick={() => run(r, "reject")} disabled={locked} title={readOnlyNote ?? undefined} className={`${actionBtn} text-destructive`}>
                      Reject
                    </button>
                  </td>
                </tr>
              ))}
              {!isLoading && !error && (data?.pending.length ?? 0) === 0 && (
                <tr><td colSpan={5} className="px-4 py-6 text-center text-muted-foreground text-[11px]">No requests are waiting.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-[13px] font-bold tracking-tight mb-2">Active admins</h2>
        <div className="bg-card border border-border/50 rounded-xl overflow-hidden">
          <table className="w-full text-[11px]">
            <thead className="bg-secondary/40 text-muted-foreground">
              <tr>
                <th className={th}>Name</th>
                <th className={th}>Email</th>
                <th className={th}>Office / unit</th>
                <th className={th}>Last sign-in</th>
                <th className={th}>Action</th>
              </tr>
            </thead>
            <tbody>
              {(data?.active ?? []).map((r) => (
                <tr key={r.id} className="border-t border-border/40 hover:bg-secondary/30">
                  <td className={`${td} font-medium`}>
                    {r.name}
                    {r.isSelf && <StatusBadge tone="neutral" className="ml-2">You</StatusBadge>}
                    {r.isDemo && <StatusBadge tone="neutral" className="ml-2">Demo account</StatusBadge>}
                  </td>
                  <td className={td}>{r.email}</td>
                  <td className={td}>{r.office ?? "—"}</td>
                  <td className={`${td} tabular-nums text-muted-foreground`}>{fmtDate(r.lastLoginAt)}</td>
                  <td className={td}>
                    <button
                      onClick={() => run(r, "deactivate")}
                      disabled={locked || r.isSelf}
                      title={r.isSelf ? "You cannot deactivate your own account." : readOnlyNote ?? undefined}
                      className={`${actionBtn} text-destructive`}
                    >
                      Deactivate
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
