"""
Phase 8: enumerate every API route and smoke-test every GET route that takes no path parameter, under the deployed
configuration (AIPHEED_LEAD2_MODEL=thesis, AIPHEED_STRICT_MODEL unset for the test client, in-memory database).
Records method, path, tags, whether an admin/auth dependency guards it, the status code, whether an error body is
JSON with a message, and whether the body leaks secret-looking keys. Writes docs/aipheed/results/api_audit.csv.

    python -I backend/scripts/api_audit.py
"""
from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
os.chdir(REPO / "backend")
os.environ.setdefault("AIPHEED_LEAD2_MODEL", "thesis")
os.environ["PYTEST_CURRENT_TEST"] = "api_audit"           # skip .env loading, as under pytest

from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, str(REPO / "backend" / "tests"))
import conftest  # noqa: E402,F401  (installs the in-memory database override)
from app.main import app  # noqa: E402

SECRET = re.compile(r"(secret|password|api[_-]?key|token)\"?\s*:\s*\"[^\"]{6,}", re.I)


def guarded(route: APIRoute) -> bool:
    names = {getattr(d.call, "__name__", "") for d in route.dependant.dependencies}
    return any(n for n in names if any(k in n.lower() for k in ("admin", "auth", "current", "require")))


def main():
    c = TestClient(app, raise_server_exceptions=False)
    rows = []
    for r in app.routes:
        if not isinstance(r, APIRoute):
            continue
        for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
            rec = {"method": m, "path": r.path, "tags": ";".join(map(str, r.tags)), "guarded": guarded(r),
                   "status": "", "json_error_message": "", "secret_like_in_body": ""}
            if m == "GET" and "{" not in r.path:
                resp = c.get(r.path)
                rec["status"] = resp.status_code
                body = resp.text[:200000]
                if resp.status_code >= 400:
                    try:
                        rec["json_error_message"] = bool(resp.json().get("detail") or resp.json().get("message") or resp.json().get("error"))
                    except Exception:  # noqa: BLE001
                        rec["json_error_message"] = False
                rec["secret_like_in_body"] = bool(SECRET.search(body))
            rows.append(rec)
    out = REPO / "docs" / "aipheed" / "results" / "api_audit.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    tested = [x for x in rows if x["status"] != ""]
    print(f"routes {len(rows)}; GET smoke-tested {len(tested)}; status counts:",
          {s: sum(1 for x in tested if x["status"] == s) for s in sorted({x["status"] for x in tested})})
    print("5xx:", [(x["path"], x["status"]) for x in tested if int(x["status"]) >= 500])
    print("non-JSON errors:", [x["path"] for x in tested if x["json_error_message"] is False])
    print("secret-like:", [x["path"] for x in tested if x["secret_like_in_body"]])
    print("unguarded mutating:", [(x["method"], x["path"]) for x in rows if x["method"] != "GET" and not x["guarded"]])


if __name__ == "__main__":
    main()
