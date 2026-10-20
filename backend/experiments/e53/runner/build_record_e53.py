"""Build backend/data/e53/e53_record.json: E53-A1 (E48-A1 inputs + measured driver conditions) with E49-C2 shrinkage
calibration, using the SAME builder as e36/e48/e49 (scripts/build_record_e36.build / write_pdf), as build_record_e49.py.

    python -B backend/experiments/e53/runner/build_record_e53.py   (from the repo root)

The E53-A1 frozen bundle (e53_freeze.py) is read (hash-checked); before the builder sees it every served probability
(backtests 2023-Q1..2026-Q3 and the 2026-Q4 forecast) is replaced by the C2-calibrated A1 value of the E53 run
(runs/<stamp>/predictions.csv arm A1; E53_results.json arms.A1.q4_2026.index), and the evaluation is recomputed from
those values (build_record_e49.evaluation). Text that the builder hard-codes for E36 (accuracy limitation, 75% verdict)
is restated from this record's own numbers. Writes only backend/data/e53/.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
BACKEND = Path(__file__).resolve().parents[3]
E53 = BACKEND / "experiments" / "e53"
sys.path.insert(0, str(BACKEND / "experiments" / "e49" / "runner"))
import build_record_e49 as R49  # noqa: E402  (evaluation(); brings in build_record_e36 as B, e48_lib, e36_evaluate)

B, L, pd = R49.B, R49.L, R49.pd
L.L6.guard32.EXP = E53
B.BUNDLE = E53 / "frozen" / "E53_SERVING_BUNDLE.json"
B.PROSPECTIVE = E53 / "frozen" / "E53_PROSPECTIVE_2026Q4.json"
B.MODEL_TXT = E53 / "models" / "E53-A1-LGBM_O2026-10-01.txt"
B.MODEL_CFG = E53 / "models" / "E53-A1-LGBM_O2026-10-01.json"
OUT = BACKEND / "data" / "e53"
COND = E53 / "frozen" / "E53_COND_2026Q2.json"
# The lead-2 ("next_quarter") row comes from E55 (E53-A1 at lead 2, e55_freeze.py), not from E38.
E55 = BACKEND / "experiments" / "e55"
B.NQ_BUNDLE = E55 / "frozen" / "E55_SERVING_BUNDLE.json"
B.NQ_PROSPECTIVE = E55 / "frozen" / "E55_PROSPECTIVE_2027Q1.json"
B.NQ_MODEL_TXT = E55 / "models" / "E55-LGBM-NQ_O2026-10-01_lead2.txt"
B.NQ_MODEL_CFG = E55 / "models" / "E55-LGBM-NQ_O2026-10-01_lead2.json"
NQ_NAME = "aiPHeed-E55 (E53-A1 at lead 2, shrinkage-calibrated) - EXPERIMENTAL PREVIEW"
NQ_LABEL = {"E55": "Proposed preview: E53-A1 at lead 2, shrinkage-calibrated (E55)",
            "E38-LGBM": "Previous lead-2 LightGBM (E38)", "B1_PERSISTENCE": "B1 Naive persistence",
            "ALWAYS_HIGH": "Diagnostic: always HIGH (majority class)"}


def nq_numbers(nb: dict) -> dict:
    m = nb["evaluation"]["metrics"]
    e, p = m["E55"], m["B1_PERSISTENCE"]
    return {"acc": e["accuracy"], "correct": e["correct"], "n": e["n"], "bal": e["balanced_accuracy"],
            "pers": p["accuracy"], "e38": m["E38-LGBM"]["accuracy"]}


def nq_texts(nb: dict) -> dict:
    x = nq_numbers(nb)
    assert (round(x["acc"], 3), x["correct"], x["n"], round(x["pers"], 3)) == (0.673, 37, 55, 0.8), x
    return {
        "verdict": (f"Next-quarter accuracy {x['acc']:.3f} ({x['correct']}/{x['n']}), balanced accuracy {x['bal']:.3f}: "
                    f"below the 75% target and below persistence ({x['pers']:.3f}). It did not meet its adoption rule "
                    "(E55). Shown as an experimental preview only."),
        "status": (f"next-quarter forecast (two quarters ahead), frozen before the outcome exists; development accuracy "
                   f"{x['acc']:.3f} ({x['correct']}/{x['n']}), balanced accuracy {x['bal']:.3f}, below the 75% target and "
                   f"below persistence ({x['pers']:.3f}); experimental preview (E55)"),
        "accuracy_note": (f"development accuracy {x['acc']:.3f}, below 75% and below persistence ({x['pers']:.3f}); "
                          "experimental preview"),
        "horizon_label": (f"Next quarter (two quarters ahead) — experimental preview; development accuracy "
                          f"{x['acc']:.3f}, below persistence."),
        "limitation": (f"The next-quarter forecast (two quarters after the latest complete data quarter; E55, E53-A1 at "
                       f"lead 2) scored {x['acc']:.3f} ({x['correct']}/{x['n']}) on development dates, balanced accuracy "
                       f"{x['bal']:.3f}, below the 75% target and below persistence ({x['pers']:.3f}); it did not meet "
                       "its adoption rule and is shown as an experimental preview only.")}


def e55_validation(nb: dict) -> dict:
    """validation.next_quarter_evaluation from E55 (replaces build_record_e36.next_quarter_validation, E38)."""
    ev = nb["evaluation"]
    rows = [{"arm": NQ_LABEL.get(a, a), "key": a, "correct": v["correct"], "n": v["n"], "accuracy": B.r4(v["accuracy"]),
             "accuracy_ci95": [round(c, 6) for c in v["accuracy_ci95"]], "balanced_accuracy": B.r4(v["balanced_accuracy"]),
             "low_recall": f"{v['TN']}/{v['TN'] + v['FP']}", "brier": B.r4(v["brier"]),
             "formal_thesis_baseline": a == "B1_PERSISTENCE"} for a, v in ev["metrics"].items()]
    return {"basis": f"Nested walk-forward, lead 2, {len(ev['dates'])} development quarters (the 55 rows of E38); "
                     f"run {ev['run']}", "dates": ev["dates"], "rows": rows, "adoption": ev["adoption"],
            "paired": ev["paired"], "verdict": nq_texts(nb)["verdict"]}
NOTE = ("Probabilities are calibrated by shrinkage toward the training base rate (E49-C2 procedure); driver shares come "
        "from the LightGBM before calibration. Employment and OFW Remittance inputs are national-level indicators.")


E52_SCORES = BACKEND / "experiments" / "e52" / "E52_scores.csv"
COND_LEVEL = {"market": "province", "climate": "province", "fish_kill": "province", "employment": "national",
              "ofw_remittance": "national"}
COND_SOURCE = {
    "market": "PSA provincial food and rice CPI (OpenStat)",
    "climate": "NASA POWER daily rainfall (reanalysis) and NOAA IBTrACS storms",
    "fish_kill": "PSA OpenStat fisheries production (proxy for fish kills, not incidents)",
    "employment": "PSA Labor Force Survey, national unemployment (quarter mean)",
    "ofw_remittance": "BSP cash remittances (national; 2026 values provisional, secondary reports), ECB FX, PSA food CPI"}


def condition_components() -> dict:
    """Per forecast quarter, province and driver: the data quarter and a one-line summary of the measured values
    behind the condition input (E52 inputs, data quarter F-2). The score itself is the record's cond_* value."""
    import math

    ok = lambda x: x == x and x is not None and not (isinstance(x, float) and math.isnan(x))
    rows = {}
    for r in pd.read_csv(E52_SCORES, dtype={"province_code": str}).itertuples():
        k = r.driver
        if k == "market":
            s = (f"food inflation {r.in_D_pp:+.2f} pp vs the five-province mean; rice CPI {r.in_rice_cpi_yoy:+.1f}% "
                 "year on year") if ok(r.in_D_pp) and ok(r.in_rice_cpi_yoy) else "not available"
        elif k == "climate":
            if ok(r.in_rain_anomaly_pct):
                a = r.in_rain_anomaly_pct
                storm = "no storm signal" if not ok(r.in_tc_max_signal) or r.in_tc_max_signal == 0 \
                    else f"storm signal {r.in_tc_max_signal:g}"
                s = f"rainfall {abs(a):.0f}% {'below' if a < 0 else 'above'} the 1991-2020 normal; {storm}"
            else:
                s = "not available"
        elif k == "fish_kill":
            s = (f"fisheries production {r.in_production_yoy * 100:+.1f}% year on year (proxy for fish kills)"
                 if ok(r.in_production_yoy) else "not available")
        elif k == "employment":
            s = (f"national unemployment {r.in_unemployment_pct:.2f}% ({r.in_yoy_change_pp:+.2f} pp year on year)"
                 if ok(r.in_unemployment_pct) and ok(r.in_yoy_change_pp) else "not available")
        else:
            s = (f"real peso value of OFW remittances {r.in_g_real_pct:+.1f}% year on year (national"
                 + ("; provisional)" if r.data_quarter >= "2026-Q1" else ")") if ok(r.in_g_real_pct) else "not available")
        rows.setdefault(r.forecast_quarter, {}).setdefault(r.province_code, {})[k] = {
            "dataQuarter": r.data_quarter, "summary": s, "level": COND_LEVEL[k], "source": COND_SOURCE[k]}
    # the lead-2 forecast (2027-Q1, origin 2026-10-01) uses the same data quarter (2026-Q2) as the 2026-Q4 forecast
    assert all(v["dataQuarter"] == "2026-Q2" for p in rows["2026-Q4"].values() for v in p.values())
    rows["2027-Q1"] = json.loads(json.dumps(rows["2026-Q4"]))
    return {"note": "Measured values behind each condition input (data quarter: the latest complete quarter before the "
                    "forecast origin). The 0-100 score served with them is the record's cond_* value (rank against "
                    "strictly earlier quarters).",
            "source_file": "backend/experiments/e52/E52_scores.csv", "rows": rows}


def calibrated():
    res = json.loads((E53 / "E53_results.json").read_text(encoding="utf-8"))
    pr = pd.read_csv(E53 / "runs" / res["run"] / "predictions.csv", dtype={"province_code": str})
    a1 = pr[pr["arm"] == "A1"]
    out = {(r.target_quarter, r.province_code): float(r.p) for r in a1.itertuples()}
    for name, p in res["arms"]["A1"]["q4_2026"]["index"].items():
        if name != "CALABARZON":
            out[("2026-Q4", R49.CODE[name])] = float(p)
    return out, res


def main():
    import copy
    import os

    os.chdir(BACKEND)
    cal, res = calibrated()
    original = B.frozen_ok
    replaced = []

    def frozen_ok(p):
        obj = original(p)                                  # the bundle hash check still runs
        if Path(p) == B.BUNDLE:
            obj = copy.deepcopy(obj)
            for q in obj["backtests"] + [obj["forecast"]]:
                for code, v in q["provinces"].items():
                    v["p_high_uncalibrated"] = v["p_high"]
                    v["p_high"] = cal[(q["quarter"], code)]
                    replaced.append((q["quarter"], code))
            obj["evaluation"] = R49.evaluation(obj)
            obj["evaluation"]["run"] = "E53-A1 + C2 calibrated backtests"
            obj["evaluation"]["note"] = ("the proposed model (E53-A1 + C2 calibration) is stored under the key "
                                         "'E36-LGBM' that the API reads; metrics recomputed from the calibrated probabilities")
        return obj

    B.frozen_ok = frozen_ok
    B.DRIVER_METHOD = B.DRIVER_METHOD + ". " + NOTE
    nb = original(B.NQ_BUNDLE)                             # hash-checked E55 bundle
    texts = nq_texts(nb)
    row_original = B.next_quarter_row

    def next_quarter_row(nb_, base):
        r = row_original(nb_, base)
        r.update({"status": texts["status"], "model_name": NQ_NAME, "horizon_label": texts["horizon_label"],
                  "accuracy_note": texts["accuracy_note"]})
        return r

    B.next_quarter_row = next_quarter_row
    B.next_quarter_validation = e55_validation
    rec = B.build()
    assert len(replaced) == 70, len(replaced)
    nq = next(q for q in rec["quarters"] if q.get("role") == "next_quarter")
    assert nq["model_id"] == "aiPHeed-E55" and nq["lead"] == 2 and nq["quarter"] == "2027-Q1", nq["model_id"]
    for code, v in nq["provinces"].items():                # served = E55's C2-calibrated value
        assert abs(v["p_high"] - round(nb["forecast"]["provinces"][code]["p_high"], 4)) < 1e-9, code
    rec["next_quarter_model"].update({
        "name": NQ_NAME, "file": "data/e53/model/" + B.NQ_MODEL_TXT.name,
        "why_served": ("E53-A1 at lead 2 (E55), shrinkage-calibrated, shown only with AIPHEED_MAX_LEAD=2 as an "
                       "experimental preview; it did not meet its adoption rule."),
        "evidence_status": nb["model"]["status"]})
    nl = [i for i, t in enumerate(rec["limitations"]) if t.startswith("The next-quarter forecast")]
    assert len(nl) == 1
    rec["limitations"][nl[0]] = texts["limitation"]
    src = rec["lgu_ranking"]["probability_source"]["source"]           # the LGU ranking is built from the E55 row
    assert src.startswith("next-quarter FORECAST 2027-Q1 (aiPHeed-E55"), src
    se = rec["served_engine"]
    se.update({"name": "aiPHeed-E53-A1 (LightGBM: E48-A1 inputs + measured driver conditions, shrinkage calibration) - PREVIEW",
               "version": "E53.A1+C2", "file": "data/e53/model/" + B.MODEL_TXT.name,
               "why_served": "Preview of E53-A1 (E36 inputs, the five trigger proportions and five measured driver "
                             "condition ranks) with shrinkage calibration, served only when AIPHEED_RECORD=e53; the "
                             "default system serves E49. " + NOTE,
               "evidence_status": "EXPERIMENTAL / PREVIEW (E53: eligible under its pre-declared rule; no paired "
                                  "difference with E49 is significant)"})
    rows = {r["key"]: r for r in rec["validation"]["model_evaluation"]["rows"]}
    me, ah, pe = rows["E36-LGBM"], rows["ALWAYS_HIGH"], rows["B1_PERSISTENCE"]
    rel = lambda a, b: "above" if a > b + 1e-9 else ("below" if a < b - 1e-9 else "equal to")
    lim = [i for i, t in enumerate(rec["limitations"]) if t.startswith("One-quarter-ahead accuracy is")]
    assert len(lim) == 1
    ci = me["accuracy_ci95"]
    rec["limitations"][lim[0]] = (
        f"One-quarter-ahead accuracy is {me['accuracy_lead1']:.3f} on {me['n']} development estimates, "
        f"{rel(me['accuracy_lead1'], ah['accuracy_lead1'])} always-HIGH ({ah['accuracy_lead1']:.3f}) and "
        f"{rel(me['accuracy_lead1'], pe['accuracy_lead1'])} persistence ({pe['accuracy_lead1']:.3f}). The 95% interval "
        f"reaches {ci[0]:.3f}, so the 75% target is not demonstrated. No baseline is beaten significantly.")
    rec["limitations"].insert(lim[0] + 1, (
        "The measured Employment and OFW Remittance inputs are national-level indicators (PSA LFS national "
        "unemployment; BSP national remittances, 2026 values provisional): they are the same for every province and "
        "cannot by themselves separate provinces."))
    from app.quarterly.verdicts import verdict_from_record   # composed from the numbers (E57 objectives audit)

    rec["validation"]["threshold_75pct"].update(verdict_from_record(rec["validation"]))
    rec.pop("content_sha256", None)
    rec = B._clean(rec)
    rec["content_sha256"] = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    L.L6.guard32.EXP = OUT                                 # the research write guard: allow writes to data/e53 only
    (OUT / "model").mkdir(parents=True, exist_ok=True)
    for src in (B.MODEL_TXT, B.MODEL_CFG, B.MODEL_TXT.parent / "ARTIFACT_HASHES.json", B.BUNDLE, B.PROSPECTIVE,
                B.BUNDLE.with_suffix(".sha256"), B.PROSPECTIVE.with_suffix(".sha256"), COND):
        shutil.copyfile(src, OUT / "model" / src.name)
    for src in (B.NQ_MODEL_TXT, B.NQ_MODEL_CFG, B.NQ_BUNDLE, B.NQ_PROSPECTIVE, B.NQ_BUNDLE.with_suffix(".sha256"),
                B.NQ_PROSPECTIVE.with_suffix(".sha256")):
        shutil.copyfile(src, OUT / "model" / src.name)
    shutil.copyfile(B.NQ_MODEL_TXT.parent / "ARTIFACT_HASHES.json", OUT / "model" / "E55_ARTIFACT_HASHES.json")
    (OUT / "model" / "condition_components.json").write_text(json.dumps(condition_components(), indent=1),
                                                             encoding="utf-8")
    (OUT / "model" / "E53_C2_calibration.json").write_text(json.dumps(
        {"source": f"backend/experiments/e53/runs/{res['run']}", "arm": "A1",
         "params_by_target_quarter": res["arms"]["A1"]["shrink_params"], "note": NOTE}, indent=1), encoding="utf-8")
    blob = json.dumps(rec, indent=1, ensure_ascii=False, default=str, allow_nan=False).encode("utf-8")
    (OUT / "e53_record.json").write_bytes(blob)
    B.write_pdf(rec, OUT / "aiPHeed_E53_assessment_report.pdf")
    m = next(r for r in rec["validation"]["model_evaluation"]["rows"] if r["key"] == "E36-LGBM")
    print(rec["content_sha256"][:16], len(blob), "bytes | model", {k: m[k] for k in m if k not in ("label", "arm")})
    for q in rec["quarters"]:
        if q["quarter"] >= "2025-Q4" and q["lead"] == 1:
            ps = {v["province"]: v["p_high"] for v in q["provinces"].values()}
            print(q["quarter"], round(sum(ps.values()) / 5, 4), ps)


if __name__ == "__main__":
    main()
