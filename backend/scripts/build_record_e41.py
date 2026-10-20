"""Build the E41 Lead-2 two-layer record served by /api/v1/lead2 (only when AIPHEED_LEAD2_MODEL=e41).

    backend/venv/Scripts/python.exe -B scripts/build_record_e41.py [--run 20261015T101016Z]
      -> data/e41/e41_lead2_record.json

Inputs (read-only): the E41 frozen prospective forecast (sha-checked), the E41 evaluation run, and the E41 library
for the base-effect/momentum split of the frozen point forecast (same origin data; no new forecast is made).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
E41 = BACKEND.parent / "aipheed-backend-aligned" / "experiments" / "E41_Lead2_Audit"
OUT = BACKEND / "data" / "e41" / "e41_lead2_record.json"
sys.path.insert(0, str(E41 / "runner"))

FPP_DEF = ("Probability that the province's food inflation (PSA food CPI, year on year, quarter mean of the three "
           "monthly rates) in the target quarter is above 4.0%, the ceiling of the BSP 3 +/- 1% headline target. "
           "This is FOOD PRICE PRESSURE. It is not the probability that households are hungry or food insecure.")
E40_DEF = ("Probability that the researcher's exploratory E40 label is HIGH in the target quarter: regional SWS hunger "
           "above 11.3% AND provincial food inflation (or food minus headline) above its 2021-2022 60th percentile, in "
           "both the target quarter and the one before. Component simulation; exploratory and not validated.")
BAND_RULE = "Low if P < 0.33; Watch if 0.33 <= P < 0.67; High if P >= 0.67 (PROTOCOL section 8; not tuned)."
ALERT_RULE = ("Early-warning alert candidate when the price-pressure band is High AND the latest approved SWS hunger "
              "(regional) is above 11.3%. Two independent official signals; staged for administrator confirmation.")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def r(x, n=3):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="20261015T101016Z")
    a = ap.parse_args()
    import e41_lib as L

    fz = E41 / "frozen" / "E41_PROSPECTIVE_2027Q1.json"
    want = (E41 / "frozen" / "E41_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    if sha(fz) != want:
        raise SystemExit("E41 frozen forecast failed its hash check")
    F = json.loads(fz.read_text())
    res = json.loads((E41 / "runs" / a.run / "results.json").read_text())
    t = L.qi(F["origin_quarter_t"])
    d = L.load().cut(t)
    sp, ml, l1 = res["lead2"]["S_P"], res["lead2"]["S_ML"], res["lead1_context"]
    acc2 = sp["metrics"]["M1"]["accuracy"]

    provinces = {}
    for name, v in F["provinces"].items():
        code, ev, p = v["province_code"], v["evidence"], v["lead2_fpp_probability"]
        base = L.m1_point(d, t, 2, code, zero_drift=True)["F_hat"]
        mom = v["lead2_F_hat"] - base
        lo, hi = v["lead2_F_80pct"]
        h_last, h_age = ev["H_last"], ev["H_age"]
        news_n = ev["news_n"] or 0
        warnings = ["SWS hunger is a regional (Balance Luzon) measurement shared by all five provinces; it is not a "
                    "provincial observation.",
                    f"Wide uncertainty: the 80% range for food inflation is {lo:.1f}% to {hi:.1f}%.",
                    f"Lead-2 accuracy on development quarters is {acc2:.2f} (below 75%); use as decision support, "
                    "not as a determination.",
                    "OFW remittance: no official in-window series was obtained; this trigger has no data (not zero)."]
        if h_age is not None and h_age > 2:
            warnings.append(f"The latest approved SWS round is {int(h_age)} quarters old.")
        if news_n < 5:
            warnings.append(f"Only {int(news_n)} province-attributed articles in the evidence quarter (insufficient news).")
        for k, lab in (("palay_yoy", "palay"), ("fish_yoy", "fisheries")):
            if ev.get(k) is None:
                warnings.append(f"PSA {lab} production change is not available for the evidence quarter.")
        band = v["lead2_band"]
        direction = "adds" if mom >= 0 else "subtracts"
        provinces[code] = {
            "provinceCode": code, "name": name,
            "observed": {
                "foodInflationLatestMonths": {"value": r(ev["F_now"], 2), "unit": "% YoY",
                                              "months": [L.ym_s(L.m0_of(t) - 1), L.ym_s(L.m0_of(t))],
                                              "source": "PSA CPI (OpenStat 0012M4ACP23)", "level": "province",
                                              "kind": "observed price condition (not hunger)"},
                "foodInflationLastQuarter": {"value": r(ev["F_last"], 2), "quarter": L.qs(t - 1)},
                "headlineInflationLatestMonths": {"value": r(ev["HL_now"], 2)},
                "foodMinusHeadline": {"value": r(ev["gap_now"], 2)},
                "hungerRegional": {"value": h_last, "quarter": F["sws_latest_quarter"], "ageQuarters": h_age,
                                   "aboveE40Threshold11_3": None if h_last is None else h_last > 11.3,
                                   "source": "SWS self-rated involuntary hunger, Balance Luzon (approved rounds)",
                                   "level": "region", "kind": "observed hunger outcome, regional only"},
                "climateSupply_palayProductionYoY": {"value": r(ev["palay_yoy"], 1), "quarter": L.qs(t - 1),
                                                     "source": "PSA palay production (OpenStat 0012E4EVCP0)",
                                                     "level": "province", "kind": "supply proxy"},
                "climateSupply_cornProductionYoY": {"value": r(ev["corn_yoy"], 1), "quarter": L.qs(t - 1)},
                "fishSupply_fisheriesProductionYoY": {"value": r(ev["fish_yoy"], 1), "quarter": L.qs(t - 1),
                                                      "source": "PSA fisheries production (OpenStat 0132E4GVFP1)",
                                                      "level": "province", "kind": "supply proxy (no fish-kill event series)"},
                "fishSupply_aquacultureProductionYoY": {"value": r(ev["aqua_yoy"], 1), "quarter": L.qs(t - 1)},
                "employment_unemploymentRate": {"value": r(ev["ur_last"], 2), "quarter": L.qs(t - 1),
                                                "source": "PSA LFS (OpenStat 0021B3FKEI2)", "level": "national",
                                                "kind": "contributing condition, no provincial differentiation"},
                "ofwRemittance": {"value": None, "status": "no official in-window series obtained"},
                "news": {"articles": int(news_n), "quarter": L.qs(t), "sufficient": news_n >= 5,
                         "triggerShares": {k: r(ev[f"news_{k}"]) for k in L.TRIGGERS}},
            },
            "forecast": {
                "targetQuarter": F["lead2_target"], "lead": 2, "scoreType": "price_pressure_probability",
                "probabilityAbove4pct": r(p), "band": band,
                "foodInflationPoint": r(v["lead2_F_hat"], 2), "interval80": [r(lo, 2), r(hi, 2)],
                "components": {"baseEffect": r(base, 2), "recentMomentum": r(mom, 2)},
                "explanation": (f"Food inflation in {name} is projected at {v['lead2_F_hat']:.1f}% for "
                                f"{F['lead2_target']} (80% range {lo:.1f}% to {hi:.1f}%). Prices a year earlier alone "
                                f"imply {base:.1f}%; the recent monthly price trend {direction} {abs(mom):.1f} points. "
                                f"Probability of exceeding 4%: {p:.0%} ({band})."),
            },
            "lead1": {"targetQuarter": F["lead1_target"], "foodInflationPoint": r(v["lead1_F_hat"], 2),
                      "probabilityAbove4pct": r(v["lead1_fpp_probability"])},
            "exploratory": {"e40Probability": r(v["lead2_e40_probability"]),
                            "scoreType": "exploratory_food_stress_probability", "status": "exploratory, not validated"},
            "operational": {"category": band, "alertCandidate": band == "High" and h_last is not None and h_last > 11.3},
            "warnings": warnings,
        }

    def pick(m):
        return {k: r(m.get(k)) if not isinstance(m.get(k), list) else [r(x) for x in m[k]]
                for k in ("accuracy", "accuracy_ci95", "balanced_accuracy", "recall_HIGH", "recall_LOW", "brier",
                          "roc_auc", "MAE_F", "n", "positives", "dates")}

    body = {
        "schema": "e41/1", "name": "aiPHeed Lead-2 two-layer forecast (E41 candidate)",
        "status": "EXPERIMENTAL CANDIDATE: not the served dashboard model; enabled only with AIPHEED_LEAD2_MODEL=e41",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "origin": F["origin"], "targetQuarter": F["lead2_target"], "lead": 2,
        "information": {"cpiMonthsThrough": F["cpi_months_used_through"], "swsLatestQuarter": F["sws_latest_quarter"],
                        "rule": "only data published before the origin (E41 PROTOCOL section 3)"},
        "scoreTypes": {"price_pressure_probability": FPP_DEF, "exploratory_food_stress_probability": E40_DEF,
                       "observed": "values reported by PSA/SWS for past periods, with their level and age"},
        "operationalRules": {"band": BAND_RULE, "alert": ALERT_RULE,
                             "municipal": "No municipal probability is produced; LGU rankings are relative "
                                          "prioritization from PSA poverty and population density."},
        "provinces": provinces,
        "evaluation": {
            "lead2": {"dates": sp["dates"], "rows": sp["rows"], "period": [sp["first"], sp["last"]],
                      "arms": {k: pick(v) for k, v in sp["metrics"].items()},
                      "gates": sp["gates"], "calibration": sp["calibration_M1"],
                      "paired_brier_holm_p": {k: r(v["brier_gain"]["p_one_sided_holm"], 4)
                                              for k, v in sp["paired_vs_baselines"].items()}},
            "lead1": {"dates": l1["dates"], "arms": {k: pick(v) for k, v in l1["metrics"].items()}},
            "lead2_ml_subset": {"dates": ml["dates"], "arms": {k: pick(v) for k, v in ml["metrics"].items()}},
            "e40_label_dev": {k: res["e40_label_dev_only"][k] for k in ("SIM", "PERSIST", "LOW", "dates")},
            "hunger_layer": res["hunger_layer_lead2"],
            "status": "development evidence; the first blind outcomes are 2026-Q4 (lead 1) and 2027-Q1 (lead 2)",
        },
        "sources": {"frozen_forecast": fz.name, "frozen_sha256": want, "evaluation_run": a.run,
                    "protocol_sha256": F["protocol_sha256"]},
        "limitations": [
            "Food price pressure is not food insecurity; high prices do not prove hunger and low inflation does not prove access.",
            "SWS hunger is regional; no provincial or municipal hunger series exists in-window.",
            f"Lead-2 accuracy {acc2:.3f} on {sp['rows']} development estimates ({sp['dates']} quarters); the 75% "
            "target is not met at lead 2.",
            "OFW remittance has no official in-window data; climate and fish triggers use PSA production as proxies.",
            "All development quarters were seen by earlier experiments; prospective outcomes are pending.",
        ],
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, indent=1, default=str), encoding="utf-8")
    print(OUT, body["content_sha256"][:16])


if __name__ == "__main__":
    main()
