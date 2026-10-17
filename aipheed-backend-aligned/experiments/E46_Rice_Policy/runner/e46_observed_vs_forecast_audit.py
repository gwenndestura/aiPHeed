"""E46 observed-vs-forecast audit: for every CALABARZON province, trace the "Observed" timeline value and the forecast
value from source to API, before and after the E46 governs fix. Reads the repository data and the running code only.

    backend/venv/Scripts/python.exe -B runner/e46_observed_vs_forecast_audit.py   (run from backend/)
      -> aipheed-backend-aligned/experiments/E46_Rice_Policy/runs/observed_vs_forecast_audit.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[4] / "backend"
E46 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
os.environ["AIPHEED_NOW"] = "2026-10-17T09:00:00"
sys.path.insert(0, str(E46.parent / "E43_Five_Trigger_Risk" / "runner"))
import e43_lib as K  # noqa: E402

L = K.L
QUARTERS = ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1"]


def api(mode: str) -> dict:
    os.environ["AIPHEED_LEAD2_MODEL"] = mode
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import dashboard as svc
    for f in (svc._province_forecasts_cached, svc._municipal_frame_cached, svc._drivers_cached):
        f.cache_clear()
    c = TestClient(app)
    out = {}
    for q in QUARTERS:
        r = c.get(f"/api/v1/provinces?quarter={q}&horizon=nowcast")
        out[q] = ({"status": r.status_code, "indicator": r.json()["indicator"]["id"],
                   "rows": {x["name"]: {k: x.get(k) for k in ("riskScore", "riskLevel", "scoreType", "estimateKind",
                                                            "observedOutcome", "horizonLabel")}
                            for x in r.json()["data"]}}
                  if r.status_code == 200 else {"status": r.status_code, "detail": r.json().get("detail")})
    return out


def main():
    th = L.e40_spec()
    d = L.load()
    lab = K.label_frame(d).assign(Q=lambda f: f["q"].map(L.qs))
    rec = json.loads((BACKEND / "data" / "e44" / "e44_record.json").read_text(encoding="utf-8"))
    from app.services import dashboard as svc
    v1 = {q: {r["province_code"]: r for r in svc._engine(svc.NOWCAST).forecast_quarter(q)} for q in QUARTERS[:3]}
    after = api("e44")
    default = api("e38")
    table = {}
    for code in L.PROVS:
        name = L.NAMES[code]
        o = lab[(lab["province_code"] == code) & (lab["Q"] == "2026-Q3")].iloc[0]
        p = rec["provinces"][code]
        past = {x["targetQuarter"]: x for x in p["pastForecasts"]}
        comp = p["forecast"]["components"]
        v = v1["2026-Q3"].get(code, {})
        table[name] = {
            "latest_observed_quarter": "2026-Q3",
            "observed_raw": {"sws_hunger_balance_luzon_pct": float(o["H"]), "food_yoy_pct": round(float(o["F"]), 3),
                             "headline_yoy_pct": round(float(o["HL"]), 3),
                             "food_minus_headline": round(float(o["F"] - o["HL"]), 3),
                             "thresholds": {"H": th["H"], "food_P60": round(th["food"][code], 3),
                                            "gap_P60": round(th["gap"][code], 3)}},
            "observed_T43_label": "HIGH" if int(o["y"]) else "LOW",
            "v1_label_for_comparison": {"observed_S1": v.get("observed_S1"), "observed_label": v.get("observed_label"),
                                        "E36_backtest_probability_shown_before_fix": v.get("risk_probability")},
            "candidate_backtest_2026Q3": {"probability": past["2026-Q3"]["probability"],
                                         "decision": past["2026-Q3"]["decision"],
                                         "observedHigh": past["2026-Q3"]["observedHigh"]},
            "forecast_target_quarter": rec["targetQuarter"],
            "forecast_uncalibrated_p_hunger_x_p_price": round(comp["regionalHungerAbove11_3"] * comp["provincialPriceSignal"], 4),
            "forecast_calibrated_probability": p["forecast"]["probability"],
            "displayed_before_fix": {"2026-Q3": v.get("risk_probability"), "2027-Q1": p["forecast"]["probability"]},
            "displayed_after_fix": {q: after[q]["rows"][name]["riskScore"] for q in QUARTERS if after[q]["status"] == 200},
            "difference_backtest_vs_forecast_same_score": round(p["forecast"]["probability"] - past["2026-Q3"]["probability"], 4),
        }
    out = {"before_fix_explanation": (
               "In AIPHEED_LEAD2_MODEL=e44 the timeline's past and current quarters showed the E31/E36 LightGBM "
               "probability of the v1 label (S1 = SWS hunger + 2 x food-CPI deviation, HIGH when above the trailing "
               "median), while the target quarter showed the E44 probability of T43. Two models, two target events."),
           "provinces": table, "api_after_fix_e44": after, "api_default_e38": default}
    (E46 / "runs" / "observed_vs_forecast_audit.json").write_text(json.dumps(out, indent=1, default=str))
    for n, r in table.items():
        print(n, json.dumps({k: r[k] for k in ("observed_raw", "observed_T43_label", "v1_label_for_comparison",
                                               "candidate_backtest_2026Q3", "forecast_uncalibrated_p_hunger_x_p_price",
                                               "forecast_calibrated_probability", "displayed_after_fix")}, default=str))


if __name__ == "__main__":
    main()
