// src/lib/linkToken.ts
// ----------------------
// For pages opened from an emailed link (/verify-email, /reset-password):
// read ?token= once, then take it out of the address bar right away so it is
// not left in history, bookmarks or screenshots, and send no Referer from the
// page so the token can never reach another site.

import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export function useLinkToken(): string | null {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  // Read from the real URL on first render, before anything rewrites it.
  const [token] = useState<string | null>(() => new URLSearchParams(window.location.search).get("token"));

  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "referrer";
    meta.content = "no-referrer";
    document.head.appendChild(meta);
    if (window.location.search) {
      // history.replaceState under the hood: the token-bearing entry is gone.
      navigate(pathname, { replace: true });
    }
    return () => meta.remove();
    // Once per page visit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return token;
}
