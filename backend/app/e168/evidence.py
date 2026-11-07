"""
E168 supporting evidence for the final system (no model is refitted; everything reads frozen outputs).

    python -m app.e168.evidence face      -> data/e168/out/face_validity.json   (FNRI 2019 and 2023 face-validity comparisons)
    python -m app.e168.evidence lead      -> data/e168/out/lead_sensitivity.json (maximum-reliable-lead sensitivity)
    python -m app.e168.evidence seal      -> data/e168/out/seal_check.json       (ENNS 2022 seal integrity and status)
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np
import pandas as pd

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
OUT = D / "e168" / "out"
CAL = ["batangas", "cavite", "laguna", "quezon", "rizal"]
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))
lg = lambda p: np.log(np.asarray(p, float) / (100 - np.asarray(p, float)))


def _rows(lead: int) -> pd.DataFrame:
    A = pd.concat([pd.read_csv(OUT / "all_rows.csv"), pd.read_csv(OUT / "all_rows_l3_8.csv")])
    A = A[(A["mode"] == "main") & (A["lead"] == lead)][["key", "survey", "lead", "mu", "p", "half"]]
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    return G[G["lead"] == lead].merge(A, on=["key", "survey", "lead"])


def face():
    """FNRI 2019 (and the other CALABARZON survey rows): E168's as-of forecast against the published provincial HFIAS.
    FNRI 2023: CALABARZON-wide comparison against the published regional FIES 19.1 %, through the E169 FIES->HFIAS bridge."""
    x = _rows(1)
    cal = x[x["key"].isin(CAL)].copy()
    cal["forecast_pct"] = pct(cal["mu"]).round(1)
    cal["observed_pct"] = pct(cal["y_true"]).round(1)
    cal["difference_pts"] = (cal["forecast_pct"] - cal["observed_pct"]).round(1)
    cal["forecast_class"] = np.where(cal["p"] >= 0.5, "HIGH", "LOW")
    cal["observed_class"] = np.where(cal["y_high"] == 1, "HIGH", "LOW")
    rows = cal[["province", "survey", "lead", "forecast_pct", "observed_pct", "difference_pts", "forecast_class", "observed_class"]].to_dict("records")

    S = json.loads((OUT / "sealed_enns2022.json").read_text())
    sealed = [r for r in S["forecasts"] if r["key"] in CAL and r["lead"] == 1]
    br = json.loads((D / "e169" / "out" / "fies_bridge_feasibility.json").read_text())
    b = br["bridge_logit"]
    fies = pd.read_csv(D / "fi_labels" / "clean" / "published_fies_psa_sdg212.csv")
    r23 = fies[(fies.level == "region") & (fies.geography == "Region IV-A") & (fies.year == 2023)].iloc[0]
    pop = {"batangas": 2_993_000, "cavite": 4_573_000, "laguna": 3_383_000, "quezon": 1_951_000, "rizal": 3_330_000}
    from app.services import reference as ref
    try:
        from app.services import dashboard as Dsh
        pp = Dsh._province_population()
        pop = {k: pp.get(ref.province_code(k), v) for k, v in pop.items()}
        pop_src = "PSA POPCEN 2024 (dashboard province population)"
    except Exception:
        pop_src = "PSA POPCEN 2024, rounded (fallback constants)"
    w = np.array([pop[r["key"]] for r in sealed], float)
    reg_2022 = float(np.sum(w * np.array([r["E168_score"] for r in sealed])) / w.sum())
    fies23 = float(r23["percent"])
    bridged = float(pct(b["intercept"] + b["slope"] * lg(fies23)))
    lo_b, hi_b = (float(pct(b["intercept"] + b["slope"] * lg(float(r23[c])))) for c in ("ci95_low", "ci95_high"))
    out = {
        "fnri_2019_and_other_calabarzon_survey_rows": {
            "rows": rows,
            "basis": ("Lead-1 E168 forecast made as of one quarter before the survey quarter, with only survey rounds published "
                      "by then, against the FNRI-published provincial HFIAS moderate+severe share. difference = forecast - observed."),
            "fnri_2019": [r for r in rows if r["survey"] == "ENNS2019"],
            "class_agreement": f"{sum(r['forecast_class'] == r['observed_class'] for r in rows)} of {len(rows)}",
            "limits": "Five CALABARZON rows in total (2 in ENNS 2019), all observed LOW; no CALABARZON HIGH case exists to check.",
        },
        "fnri_2023": {
            "published": {"measure": "FIES moderate or severe food insecurity (FAO SDG 2.1.2), past 12 months", "geography": "Region IV-A (CALABARZON)",
                          "year": 2023, "percent": fies23, "ci95": [float(r23["ci95_low"]), float(r23["ci95_high"])], "source": r23["source"]},
            "bridge": {"what": "E169 FIES->HFIAS logit bridge fitted on 20 ENNS 2019 provincial factsheets reporting both scales",
                       "intercept": b["intercept"], "slope": b["slope"], "residual_sd_logit": b["residual_sd_logit"]},
            "bridged_hfias_2023_pct": round(bridged, 1), "bridged_range_from_fies_ci_pct": [round(lo_b, 1), round(hi_b, 1)],
            "e168_sealed_2022_regional_pct": round(reg_2022, 1),
            "e168_sealed_2022_provinces": {r["province"]: r["E168_score"] for r in sealed},
            "weights": pop_src,
            "difference_pts": round(reg_2022 - bridged, 1),
            "what_it_shows": ("Whether E168's provincial forecasts, combined to CALABARZON, are on the same scale as the region's "
                              "published 2023 food-insecurity level once the FIES figure is put on the HFIAS scale."),
            "what_it_cannot_show": ("It is not a validation: FIES is not HFIAS (bridged with error), regional is not provincial, the "
                                    "E168 forecasts are for the 2022 survey (sealed; the nearest E168 forecast to 2023), and the 19.1% "
                                    "is never used as a training label or provincial target."),
        },
    }
    (OUT / "face_validity.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(out, indent=1, default=float))


def lead():
    """How firm is 'reliable to 3 quarters'? Wilson intervals, the probability under bootstrap that accuracy >= 75 %, the
    horizon under nearby thresholds, and leave-one-round-out accuracy. The project rule itself is not changed."""
    H = json.loads((OUT / "lead_horizon.json").read_text())
    rng = np.random.default_rng(168)
    res = {"rule": "accuracy >= 0.75 and Brier significantly better than reusing the latest survey (fixed 2026-11-07, after results)",
           "leads": {}}
    for L in range(1, 9):
        if str(L) not in H["leads"]:
            continue
        x = _rows(L)
        ok = ((x["p"] >= 0.5) == (x["y_high"] == 1)).values.astype(float)
        n, a = len(ok), ok.mean()
        z = 1.96
        c, h = (a + z * z / (2 * n)) / (1 + z * z / n), z * np.sqrt(a * (1 - a) / n + z * z / (4 * n * n)) / (1 + z * z / n)
        bs = rng.choice(ok, (4000, n)).mean(axis=1)
        loro = {s: round(float(ok[(x["survey"] != s).values].mean()), 3) for s in x["survey"].unique()}
        res["leads"][L] = {"n": n, "correct": int(ok.sum()), "accuracy": round(float(a), 3), "wilson95": [round(c - h, 3), round(c + h, 3)],
                           "p_bootstrap_accuracy_ge_75": round(float((bs >= 0.75).mean()), 3),
                           "correct_needed_for_75": int(np.ceil(0.75 * n)), "margin_rows": int(ok.sum() - np.ceil(0.75 * n)),
                           "leave_one_round_out_accuracy": loro, "beats_persistence": H["leads"][str(L)]["beats_persistence_C2"]}
    def horizon(th):
        k = 0
        for L in range(1, 9):
            r = res["leads"].get(L)
            if r and r["accuracy"] >= th and r["beats_persistence"] and L == k + 1:
                k = L
            else:
                break
        return k
    res["horizon_by_threshold"] = {f"{th:.3f}": horizon(th) for th in (0.70, 0.725, 0.75, 0.775, 0.80)}
    res["horizon_lower_wilson_bound_ge_75"] = next(
        (L - 1 for L in range(1, 9) if not (res["leads"].get(L) and res["leads"][L]["wilson95"][0] >= 0.75)), 8)
    hb, ls = res["horizon_by_threshold"], res["leads"]
    res["reading"] = (f"Margins over 75%: " + ", ".join(f"Lead {L} {ls[L]['margin_rows']:+d} rows" for L in (1, 2, 3)) + ". "
                      f"Horizon by threshold: 0.70 -> {hb['0.700']}, 0.725 -> {hb['0.725']}, 0.75 -> {hb['0.750']}, "
                      f"0.775 -> {hb['0.775']}, 0.80 -> {hb['0.800']}. Horizon whose 95% lower bound is at least 75%: "
                      f"{res['horizon_lower_wilson_bound_ge_75']}. Bootstrap probability that accuracy is at least 75%: "
                      + ", ".join(f"Lead {L} {ls[L]['p_bootstrap_accuracy_ge_75']:.2f}" for L in (1, 2, 3)) + ". "
                      "'Reliable to 3 quarters' holds under the project rule but is not statistically robust.")
    (OUT / "lead_sensitivity.json").write_text(json.dumps(res, indent=1), newline="\n")
    print(json.dumps(res, indent=1))


def seal():
    p = OUT / "sealed_enns2022.json"
    b = p.read_bytes()
    d = json.loads(b)
    s = OUT / "seal_check.json"
    out = {"file": "data/e168/out/sealed_enns2022.json", "sha256": hashlib.sha256(b).hexdigest(), "expected_prefix": "f8228fae",
           "intact": hashlib.sha256(b).hexdigest().startswith("f8228fae"), "sealed_utc": d["sealed_utc"], "model": d["model"],
           "target": d["target"], "rule": d["rule"], "forecasts": len(d["forecasts"]),
           "calabarzon": [{k: r[k] for k in ("province", "lead", "E168_score", "E168_p_high", "E168_class")} for r in d["forecasts"] if r["key"] in CAL],
           "outcomes_status": ("Not published: no FNRI ENNS 2022 provincial HFIAS table was found in public sources "
                               "(docs/final/ENNS2022_OUTCOME_SEARCH.md). The forecasts stay sealed; no performance is reported."),
           "scoring": "python -m app.e171.score_enns2022 <outcomes.csv> once FNRI publishes provincial ENNS 2022 HFIAS"}
    s.write_text(json.dumps(out, indent=1), newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"face": face, "lead": lead, "seal": seal}[sys.argv[1]]()
