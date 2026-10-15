"""Live end-to-end check of the integrated app (final-aipheed-integration) against a RUNNING server that uses the
scratch preview database (E36 runner/serve_local.py: TEMP/aipheed_e36_preview.db). Never touches backend/aipheed.db.

    <backend venv python> -B runner/e2e_live.py [base_url]     -> runs/e2e_live_<stamp>.json

A random test admin password is generated here and never printed or stored.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "runs"
BACKEND = HERE.parents[3] / "backend"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
DB = Path(tempfile.gettempdir()) / "aipheed_e36_preview.db"
results: list[dict] = []


def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if r.headers.get("content-type", "").startswith("application/json") else raw)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check(name, ok, detail=""):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def main():
    env = dict(os.environ, DATABASE_URL=f"sqlite+aiosqlite:///{DB.as_posix()}", SECRET_KEY=secrets.token_hex(32))
    # ---- public surfaces on the dynamic target
    s, q = call("GET", "/api/v1/quarters?horizon=nowcast")
    target = q["forecastTarget"]["target_quarter"]
    check("quarters: current is the dynamic target", s == 200 and q["current"] == target and q["forecastTarget"]["available"],
          f"target {target}, calendar {q['calendarQuarter']}")
    s, p = call("GET", "/api/v1/provinces")
    check("provinces default to the target", s == 200 and all(r["currentQuarter"] == target for r in p["data"]),
          ", ".join(f"{r['name']} {r['riskScore']}" for r in p["data"]))
    s, m = call("GET", "/api/v1/provinces/quezon/municipalities")
    check("municipal ranking on the target", s == 200 and m["quarter"] == target and len(m["data"]) == 41)
    s, ex = call("GET", "/api/v1/explainability?scope=province&id=laguna")
    check("five triggers on the target", s == 200 and ex["quarter"] == target and len(ex["triggers"]) == 5,
          ", ".join(f"{t['key']} {t['pct']}%" for t in ex["triggers"]))
    s, rec = call("GET", "/api/v1/quarterly/e31/summary")
    s2, pdf = call("GET", "/api/v1/quarterly/e31/report.pdf")
    check("PDF is the served record", s2 == 200 and isinstance(pdf, bytes) and rec["content_sha256"].encode() in pdf)
    s, pub = call("GET", "/api/v1/alerts")
    check("no public alert before confirmation", s == 200 and pub.get("data", []) == [])
    # ---- admin: create a test account in the scratch DB, sign in
    email = f"e2e.{secrets.token_hex(3)}@calabarzon.da.gov.ph"
    pw = "E2e-" + secrets.token_urlsafe(18)
    r = subprocess.run([sys.executable, "-B", "scripts/create_admin.py", "--email", email, "--name", "E2E Tester"],
                       cwd=BACKEND, env={**env, "AIPHEED_ADMIN_PASSWORD": pw}, capture_output=True, text=True)
    check("create admin in scratch DB", r.returncode == 0, r.stderr.strip()[-200:])
    s, login = call("POST", "/api/v1/auth/login", body={"email": email, "password": pw})
    tok = login.get("token")
    check("admin sign-in", s == 200 and tok)
    s, rv = call("GET", f"/api/v1/admin/review?quarter={target}", tok)
    statuses = {i["status"] for i in rv.get("data", [])}
    check("review queue uses the approved vocabulary", s == 200 and statuses <= {"Staged", "Approved", "Rejected", "Pending"},
          str(statuses))
    item = next((i for i in rv.get("data", []) if i["status"] == "Staged"), None)
    if item:
        s, a1 = call("POST", f"/api/v1/admin/review/{item['id']}/approve", tok)
        s2, a2 = call("POST", f"/api/v1/admin/review/{item['id']}/approve", tok)
        check("approve is idempotent and shows Approved", s == s2 == 200 and a1["status"] == a2["status"] == "Approved"
              and a1["updatedAt"] == a2["updatedAt"])
    # ---- alerts: stage for the target only, confirm one, public shows it
    r = subprocess.run([sys.executable, "-B", "scripts/stage_alerts_e31.py"], cwd=BACKEND, env=env,
                       capture_output=True, text=True)
    staged = json.loads(r.stdout) if r.returncode == 0 else {}
    check("alert staging limited to the target quarter", r.returncode == 0 and
          all(x["quarter"] == target for x in staged.get("items", [])), f"{staged.get('staged')} staged")
    s, adm = call("GET", "/api/v1/admin/alerts?status=staged", tok)
    first = (adm.get("data") or [None])[0]
    s, pub = call("GET", "/api/v1/alerts")
    check("staged alerts are not public", pub.get("data", []) == [])
    if first:
        s, c = call("POST", f"/api/v1/admin/alerts/{first['id']}/confirm", tok)
        s2, pub = call("GET", "/api/v1/alerts")
        ids = [a["id"] for a in pub.get("data", [])]
        check("confirmed alert becomes public", s == 200 and first["id"] in ids, f"{first.get('provinceCode') or first.get('province_code')}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"e2e_live_{stamp}.json").write_text(json.dumps({"base": BASE, "target": target, "results": results}, indent=1))
    print(f"{sum(r['pass'] for r in results)}/{len(results)} passed")
    sys.exit(0 if all(r["pass"] for r in results) else 1)


if __name__ == "__main__":
    main()
