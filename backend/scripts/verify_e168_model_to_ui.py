"""
End-to-end check: E168 model artifact -> model registry -> production API -> rendered dashboard values.

Stages compared, for all five CALABARZON provinces and each served forecast quarter (2027-Q1, Q2, Q3):
  1. artifact   data/e168/out/live_2027.json (p_high, risk_class): the frozen E168 procedure's output
  2. registry   data/registry/registry.json production model and its artifact SHA-256
  3. API        GET /api/v1/provinces?quarter=... (riskScore, riskLevel), run in-process with the production
                environment of backend/Dockerfile (AIPHEED_LEAD2_MODEL=thesis, AIPHEED_STRICT_MODEL=1)
  4. rendered   optional JSON captured from the browser (see RENDERED_JS below): {"2027-Q1": {"Quezon": "0.08", ...}}

Tolerance: API = artifact exactly; rendered = API rounded to 2 decimals (the dashboard's display format).

    python scripts/verify_e168_model_to_ui.py [rendered.json]   -> exit 0 when every stage matches
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
QUARTERS = {"2027-Q1": 1, "2027-Q2": 2, "2027-Q3": 3}
EXPECTED_MODEL = "e168-lgbm-1.0"
# Paste into the browser console on /dashboard after selecting a quarter: returns {province: displayed score}.
RENDERED_JS = ("Object.fromEntries([...document.querySelectorAll('button')].map(b=>b.textContent||'')"
               ".map(t=>t.match(/^(Quezon|Rizal|Laguna|Cavite|Batangas).*?(\\d\\.\\d\\d|—)$/)).filter(Boolean).map(m=>[m[1],m[2]]))")


def main() -> int:
    problems: list[str] = []
    live = json.loads((BACKEND / "data/e168/out/live_2027.json").read_text(encoding="utf-8"))
    art = {(r["province"], r["target_quarter"]): r for r in live["provinces"]}
    reg = json.loads((BACKEND / "data/registry/registry.json").read_text(encoding="utf-8"))
    prod = reg.get("production") or {}
    if prod.get("model_id") != EXPECTED_MODEL:
        problems.append(f"registry production is {prod.get('model_id')!r}, expected {EXPECTED_MODEL}")
    sha = hashlib.sha256((BACKEND / "data/e168/out/live_2027.json").read_bytes()).hexdigest()
    if prod.get("artifact_path") != "data/e168/out/live_2027.json":
        problems.append(f"registry artifact path is {prod.get('artifact_path')!r}")
    if prod.get("artifact_file_sha256") != sha:
        problems.append(f"registry artifact hash {str(prod.get('artifact_file_sha256'))[:12]} != live_2027.json {sha[:12]}")

    for k in ("AIPHEED_LEAD2_MODEL", "AIPHEED_STRICT_MODEL", "AIPHEED_THESIS_MODEL", "AIPHEED_MAP_MODEL"):
        os.environ.pop(k, None)
    db = Path(tempfile.mkdtemp()) / "verify.db"
    os.environ.update({"AIPHEED_LEAD2_MODEL": "thesis", "AIPHEED_STRICT_MODEL": "1", "SECRET_KEY": "verify-only",
                       "DATABASE_URL": f"sqlite+aiosqlite:///{db.as_posix()}"})
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True, capture_output=True, env=os.environ.copy())
    from fastapi.testclient import TestClient
    from app.main import app

    rendered = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")) if len(sys.argv) > 1 else {}
    table = []
    with TestClient(app) as c:
        reg_api = c.get("/api/v1/final/model-registry").json()
        if (reg_api.get("production") or {}).get("model_id") != EXPECTED_MODEL:
            problems.append(f"API registry production is {(reg_api.get('production') or {}).get('model_id')!r}")
        for q, lead in QUARTERS.items():
            d = c.get("/api/v1/provinces", params={"quarter": q}).json()
            if "e168" not in d["indicator"]["id"]:
                problems.append(f"{q}: API indicator {d['indicator']['id']!r} is not E168")
            api = {r["name"]: r for r in d["data"]}
            for p in CAL:
                a = art[(p, q)]
                r = api.get(p)
                row = {"quarter": q, "province": p, "artifact_p": a["p_high"], "artifact_class": a["risk_class"],
                       "api_p": r and r["riskScore"], "api_class": r and r["riskLevel"],
                       "rendered": (rendered.get(q) or {}).get(p)}
                if r is None:
                    problems.append(f"{q} {p}: missing from API")
                else:
                    if r["riskScore"] != a["p_high"]:
                        problems.append(f"{q} {p}: API {r['riskScore']} != artifact {a['p_high']}")
                    if r["riskLevel"].upper() != a["risk_class"]:
                        problems.append(f"{q} {p}: API class {r['riskLevel']} != artifact {a['risk_class']}")
                    if row["rendered"] is not None and row["rendered"] != f"{r['riskScore']:.2f}":
                        problems.append(f"{q} {p}: rendered {row['rendered']} != API {r['riskScore']:.2f}")
                table.append(row)
    print(json.dumps({"registry_production": prod.get("model_id"), "artifact_sha256": sha, "rows": table,
                      "problems": problems}, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
