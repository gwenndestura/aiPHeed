"""E69 r3 (PROTOCOL 5): build backend/data/e69/e69_disclosure.json for the e69 serving mode from the E69 outputs only:
the regional hunger outlook (Scale 1), the provincial risk-outlook tiers (Scale 2) for the two issued targets, the
vulnerability profile and the evaluation summaries. Nothing here changes a forecast, colour or rank.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E69_Food_Insecurity_Risk_Framework/runner/r3_build_disclosure.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e69_lib as K  # noqa: E402

H, L, np, pd = K.H, K.L, K.np, K.pd
from scipy.stats import norm  # noqa: E402

DEST = H.BACKEND / "data" / "e69" / "e69_disclosure.json"


def _r(v, n=2):
    return None if v is None or (isinstance(v, float) and not np.isfinite(v)) else round(float(v), n)


def main():
    K.verify_protocol()
    r1 = json.loads((K.OUT / "r1_regional_hunger.json").read_text())
    r2 = json.loads((K.OUT / "r2_province_fusion.json").read_text())
    S = pd.read_csv(K.TABLES / "r1_scores_all_available.csv").set_index("model")
    Fh = pd.read_csv(K.TABLES / "r1_regional_hunger_forecasts.csv")
    T = pd.read_csv(K.SEALED / "outlook_forward.csv", dtype={"province_code": str})
    sk = pd.read_csv(K.TABLES / "r2_province_skill.csv").set_index("reading")
    rw = S.loc["R0_RW"]
    always = float(rw["E1_events"]) / float(rw["quarters"])      # always 'above' on the same quarters as R0
    hunger_eval = (f"Two quarters ahead, no method forecast regional hunger better than its latest reading: average error "
                   f"{rw['MAE']:.1f} points over {int(rw['quarters'])} quarters (survey noise alone is about "
                   f"{rw['noise_floor_MAE']:.1f}); 'above 11.3%' was right in {int(rw['E1_correct'])} of {int(rw['quarters'])} "
                   f"quarters and none of the {int(rw['E2_events'])} sharp rises (5 points or more) was foreseen. SWS samples "
                   "300-600 adults in Balance Luzon (margin of error about 4-6 points) and gives no provincial figure.")
    regional = {}
    for _, f in Fh[Fh["t"].isin(K.FORWARD)].iterrows():
        h, s = float(f["R0_RW_hat"]), float(f["R0_RW_sigma"])
        regional[f["target"]] = {"issueDate": f["issue_date"], "model": "latest posted SWS reading (random walk; E69 R0)",
                                 "expectedHunger": _r(h, 1), "interval80": [_r(h - 1.2816 * s, 1), _r(h + 1.2816 * s, 1)],
                                 "probabilityAbove11_3": _r(f["R0_RW_p_elev"], 3), "probabilitySharpRise": _r(f["R0_RW_p_rise"], 3),
                                 "latestReading": _r(f["base"], 1), "geography": "Balance Luzon (region), not provincial",
                                 "evaluation": hunger_eval}
    outlook = {}
    for r in T.itertuples():
        comp = {"regionalHungerElevated": bool(r.H_component), "probabilityHungerElevated": _r(r.P_hunger_elevated, 3),
                "affordabilityHazard": bool(r.A_component), "pricePressureScore": _r(r.P_price, 3),
                "headlineAtIssue": _r(r.headline_at_issue), "headlineUsual": _r(r.headline_usual),
                "climateHazard": bool(r.C_component), "climateStatus": r.C_status,
                "localProductionExposure": None if pd.isna(r.X_component) else bool(r.X_component == True),  # noqa: E712
                "palayYoY": _r(r.palay_yoy, 1), "cornYoY": _r(r.corn_yoy, 1)}
        outlook.setdefault(r.target, {})[r.province] = {"tier": r.tier, "issueDate": r.issue_date, "components": comp}
    a0, qm = sk.loc["A0"], sk.loc["A0-QMEAN"]
    body = {
        "schema": "aipheed.e69.disclosure/1", "experiment": "E69_Food_Insecurity_Risk_Framework",
        "protocolSha256": K.verify_protocol(), "sealedSha256": r2["sealed_sha256"],
        "framework": ("Food-insecurity risk outlook (E69): regional hunger is the only food-insecurity outcome measured "
                      "every quarter; it is combined with province evidence on affordability (price-pressure score, headline "
                      "inflation) and climate (PAGASA status, local crop production). ELEVATED = hunger expected above 11.3% "
                      "AND (an affordability hazard OR a climate hazard with a local production drop); WATCH = hunger "
                      "expected high AND a climate hazard only. It is an evidence summary for planning, not a probability "
                      "and not a validated provincial forecast; it does not change the score, colour or rank."),
        "tierRule": "ELEVATED = H and (A or (C and X)); WATCH = H and C; otherwise NO ELEVATED SIGNAL; INSUFFICIENT DATA if H unknown",
        "regionalHungerOutlook": regional, "riskOutlook": outlook,
        "vulnerabilityProfile": {v["province"]: {k: v[k] for k in v if k != "province"} for v in r2["vulnerability"].values()},
        "vulnerabilityNote": ("PSA subsistence incidence (2021, 2023) and 2021 small-area poverty describe how many households "
                              "are poor; their sampling errors (CV 17-62% for subsistence) are too large to rank provinces, so "
                              "they are shown as context and are not part of the tier."),
        "provinceSkill": (f"The provincial price model separates provinces within a quarter (within-quarter AUC "
                          f"{a0['within_quarter_auc']:.2f}; {int(a0['correct'])} of 50 correct against {int(qm['correct'])} when "
                          "every province gets the quarter average), so its province ordering carries information beyond the "
                          "shared regional trend; the five provinces count as about "
                          f"{r2['province_skill']['n_eff']:.0f} independent observations, not 50."),
        "goalStatus": ("The >75% Lead-2 goal applies to province classifications and is not met on valid evidence (E68: 0.72; "
                       "no correction better). For regional hunger, 'above 11.3%' at Lead-2 was right in "
                       f"{int(rw['E1_correct'])}/{int(rw['quarters'])} quarters, below always predicting 'above' "
                       f"({always:.0%} on the same quarters)."),
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_bytes(json.dumps(body, indent=1, sort_keys=True).encode("utf-8"))
    print(json.dumps({k: v for k, v in body.items() if k not in ("riskOutlook",)}, indent=1)[:5000])


if __name__ == "__main__":
    main()
