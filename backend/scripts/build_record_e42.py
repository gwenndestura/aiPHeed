"""Build the E42 Lead-2 record served by /api/v1/lead2 when AIPHEED_LEAD2_MODEL=e42.

    backend/venv/Scripts/python.exe -B scripts/build_record_e42.py [--run 20261015T131128Z]
      -> data/e42/e42_lead2_record.json

The forecast itself is unchanged: E41's frozen M1 forecast (E42's pre-registered procedure PS did not improve on it).
E42 adds, per province: the 2027-Q1 range across the frozen E42 variants, the exploratory signal count, the status
of each of the five triggers, and the development backtest of M1 (past target quarters with observed outcomes).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
EXP = BACKEND.parent / "aipheed-backend-aligned" / "experiments"
E41, E42 = EXP / "E41_Lead2_Audit", EXP / "E42_Lead2_Improvement"
SRC = BACKEND / "data" / "e41" / "e41_lead2_record.json"
OUT = BACKEND / "data" / "e42" / "e42_lead2_record.json"
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
SIGNAL_DEF = ("Exploratory food-stress signal count (0-2): 1 if the province's price-pressure band is High, plus 1 if "
              "the latest approved SWS hunger (regional, Balance Luzon) is above 11.3%. Unweighted; each component is "
              "shown with its status. Not a validated measure of food insecurity.")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def checked(p: Path) -> dict:
    rec = json.loads(p.read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() != rec["content_sha256"]:
        raise SystemExit(f"{p} failed its integrity check")
    return rec


def band(p: float) -> str:
    return "High" if p >= 2 / 3 else ("Watch" if p >= 1 / 3 else "Low")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="20261015T131128Z")
    ap.add_argument("--e41-run", default="20261015T101016Z")
    a = ap.parse_args()
    base = checked(SRC)
    fz = E42 / "frozen" / "E42_PROSPECTIVE_2027Q1.json"
    if sha(fz) != (E42 / "frozen" / "E42_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]:
        raise SystemExit("E42 frozen forecast failed its hash check")
    v42 = json.loads(fz.read_text())
    res = json.loads((E42 / "runs" / a.run / "results.json").read_text())
    hist = pd.read_csv(E41 / "runs" / a.e41_run / "predictions_lead2.csv", dtype={"province_code": str})
    hist = hist.dropna(subset=["M1_p", "y"])

    rec = copy.deepcopy(base)
    rec.pop("content_sha256", None)
    rec.update({"schema": "e42/1", "name": "aiPHeed Lead-2 two-layer forecast (E41 forecast, E42 evidence)",
                "status": "EXPERIMENTAL CANDIDATE: not the served dashboard model; enabled only with "
                          "AIPHEED_LEAD2_MODEL=e42",
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    rec["scoreTypes"]["exploratory_signal_count"] = SIGNAL_DEF
    for code, p in rec["provinces"].items():
        name = NAMES[code]
        v = v42["provinces"][name]
        variants = {"M1 (served, E41)": p["forecast"]["probabilityAbove4pct"], "M1h (half drift)": round(v["M1h_p"], 3),
                    "M1z (flat prices)": round(v["M1z_p"], 3), "PS (E42 primary)": round(v["PS_p"], 3),
                    "LR-GOV (Chapter I logistic baseline)": round(v["LR-GOV_p"], 3)}
        h = p["observed"]["hungerRegional"]
        price_high = p["forecast"]["band"] == "High"
        hunger_high = bool(h["aboveE40Threshold11_3"])
        hp = hist[hist["province_code"] == code].sort_values("target_q")
        p["forecast"]["variants"] = variants
        p["forecast"]["variantRange"] = [min(variants.values()), max(variants.values())]
        p["forecast"]["variantNote"] = ("Range of the frozen E42 alternatives for the same quarter. They agree on the "
                                        "province ordering; the level depends on the price-trend assumption.")
        p["signalCount"] = {"value": int(price_high) + int(hunger_high),
                            "components": {"pricePressureHigh": price_high, "regionalHungerAbove11_3": hunger_high},
                            "scoreType": "exploratory_signal_count"}
        p["triggerStatus"] = {
            "market": {"status": "contributes", "evidence": "PSA food and headline CPI (province)"},
            "climate": {"status": "no_model_input", "evidence": "PSA palay/corn production change (province), "
                        "shown as evidence; no PAGASA series obtainable in-window"},
            "fish_kill": {"status": "no_model_input", "evidence": "PSA fisheries/aquaculture production change "
                          "(province); no BFAR fish-kill event series"},
            "employment": {"status": "no_model_input", "evidence": "PSA LFS unemployment (national only)"},
            "ofw_remittance": {"status": "no_data", "evidence": "no official in-window regional or provincial series"},
        }
        p["pastForecasts"] = [{"targetQuarter": f"{int(q) // 4}-Q{int(q) % 4 + 1}",
                               "probabilityAbove4pct": round(float(pp), 3), "band": band(float(pp)),
                               "observedFoodInflation": round(float(f), 2), "observedAbove4pct": bool(int(y))}
                              for q, pp, f, y in zip(hp["target_q"], hp["M1_p"], hp["F_true"], hp["y"])]
        p["pastForecastsNote"] = ("Development backtest of the same M1 rule at each past origin (information "
                                  "available then); not forecasts issued live at the time.")
    sp, sc = res["S_P"], res["S_C"]
    rec["assessment"] = {
        "e42_classification_of_PS": sp["gates"]["classification"],
        "e41_m1_classification": "Requires further model development (usable for a controlled system demonstration "
                                 "as experimental): beats all baselines on Brier, fails the 75% and balanced-accuracy "
                                 "gates",
        "lead2_accuracy": {k: round(sp["metrics"][k]["accuracy"], 3) for k in ("M1", "M1h", "M1z", "PS",
                                                                               "B1_persistence", "B0_majority")},
        "nlp_value_brier_gain": {k: round(v["brier_gain"]["mean_gain"], 4) for k, v in sc["paired"]["NLP_value"].items()},
        "evidence": "development evidence (all quarters seen; E40 holdout exposed); prospective 2026-Q4/2027-Q1 pending",
    }
    rec["sources"].update({"e42_frozen": fz.name, "e42_frozen_sha256": sha(fz), "e42_run": a.run,
                           "e41_history_run": a.e41_run})
    rec["content_sha256"] = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(OUT, rec["content_sha256"][:16])


if __name__ == "__main__":
    main()
