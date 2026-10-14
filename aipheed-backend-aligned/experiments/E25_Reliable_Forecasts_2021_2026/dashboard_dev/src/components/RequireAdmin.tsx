// src/components/RequireAdmin.tsx
// ---------------------------------
// Route guard, replacing the old sessionStorage-flag check that used to live
// inside pages/Admin.tsx. Real authorization is still 401/403 on every
// /api/v1/admin/** call, enforced server-side -- this only avoids flashing
// the admin UI at an anonymous visitor before the redirect happens.

import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();

  if (status === "loading") {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
          <p className="text-[11px] text-muted-foreground">Checking session…</p>
        </div>
      </div>
    );
  }

  if (status !== "authenticated") {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
