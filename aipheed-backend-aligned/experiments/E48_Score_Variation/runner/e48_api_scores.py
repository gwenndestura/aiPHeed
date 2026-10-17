"""E48 step 1: every province score for every quarter, exactly as the API serves it, per serving mode.
    (run from backend/)  venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E48_Score_Variation/runner/e48_api_scores.py
"""
import json, os, sys
from pathlib import Path
OUT = Path(__file__).resolve().parents[1] / "runs"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, ".")
os.environ["AIPHEED_NOW"] = "2026-10-17T09:00:00"
res = {}
for mode in ("e38", "e46"):
    os.environ["AIPHEED_LEAD2_MODEL"] = mode
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import dashboard as svc
    for f in (svc._province_forecasts_cached, svc._municipal_frame_cached, svc._drivers_cached):
        f.cache_clear()
    c = TestClient(app)
    qs = [q for q in c.get("/api/v1/quarters?horizon=nowcast").json()["quarters"] if q["state"] != "unavailable"]
    rows = {}
    for q in qs:
        r = c.get(f"/api/v1/provinces?quarter={q['id']}&horizon=nowcast")
        if r.status_code != 200:
            continue
        b = r.json()
        rows[q["id"]] = {"state": q["state"], "indicator": b["indicator"]["id"],
                         "scores": {x["name"]: x["riskScore"] for x in b["data"]},
                         "labels": {x["name"]: x.get("horizonLabel") for x in b["data"]}}
    res[mode] = rows
(OUT / "api_scores_by_quarter.json").write_text(json.dumps(res, indent=1))
for mode, rows in res.items():
    print("MODE", mode)
    provs = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
    print("  quarter   " + "  ".join(f"{p[:8]:>8s}" for p in provs) + "  state")
    for q, v in rows.items():
        print(f"  {q}  " + "  ".join(f"{v['scores'].get(p, float('nan')):8.4f}" for p in provs) + f"  {v['state']}  {(v['labels'].get('Quezon') or '')[:70]}")
