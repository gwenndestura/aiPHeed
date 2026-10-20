"""Build backend/data/e49/e49_record.json: E48-A1 with the E49-C2 calibrated probabilities, using the SAME builder as
e36/e48 (scripts/build_record_e36.build / write_pdf), as in build_record_e48.py.

    python -B backend/experiments/e49/runner/build_record_e49.py   (from the repo root)

How: the E48-A1 frozen bundle is read (hash-checked) and, before the builder sees it, every served probability
(backtests 2023-Q1..2026-Q3 and the 2026-Q4 forecast, per province) is replaced by the E49 C2 value
(runs/<stamp>/predictions.csv arm C2; E49_results.json index_history C2 for 2026-Q4). The builder then derives
signals, province summaries and the record hash from those values; the bundle's evaluation is recomputed from the
calibrated predictions (model metrics, the 75% statement, paired tests vs the six baselines on identical rows).
SHAP drivers are E48-A1's (the LightGBM before calibration). Writes only backend/data/e49/; never data/e36/, data/e48/
or frontend/.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
BACKEND = Path(__file__).resolve().parents[3]
E48, E49 = BACKEND / "experiments" / "e48", BACKEND / "experiments" / "e49"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))
sys.path.insert(0, str(E48 / "runner"))
import build_record_e36 as B  # noqa: E402
import e48_lib as L  # noqa: E402  (sets up e36_lib / e28_metrics paths)
import e36_evaluate as E  # noqa: E402

pd, np, M = L.pd, L.np, E.M
L.L6.guard32.EXP = E49
B.BUNDLE = E48 / "frozen" / "E48_SERVING_BUNDLE.json"
B.PROSPECTIVE = E48 / "frozen" / "E48_PROSPECTIVE_2026Q4.json"
B.MODEL_TXT = E48 / "models" / "E48-A1-LGBM_O2026-10-01.txt"
B.MODEL_CFG = E48 / "models" / "E48-A1-LGBM_O2026-10-01.json"
OUT = BACKEND / "data" / "e49"
NOTE = ("Probabilities are calibrated by shrinkage toward the training base rate (E49-C2); driver shares come from "
        "the LightGBM before calibration.")
CODE = {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000",
        "Batangas": "PH040500000"}


def calibrated() -> dict:
    res = json.loads((E49 / "E49_results.json").read_text(encoding="utf-8"))
    pr = pd.read_csv(E49 / "runs" / res["run"] / "predictions.csv", dtype={"province_code": str})
    c2 = pr[pr["arm"] == "C2"]
    out = {(r.target_quarter, r.province_code): float(r.p) for r in c2.itertuples()}
    for name, p in res["index_history"]["C2"]["2026-Q4"].items():
        if name != "CALABARZON":
            out[("2026-Q4", CODE[name])] = float(p)
    return out, res


def evaluation(bundle: dict) -> dict:
    """Recompute the bundle's evaluation block from the calibrated backtests (same keys as e36/e48)."""
    rows = []
    for q in bundle["backtests"]:
        for code, v in q["provinces"].items():
            y = 1 if v["observed_label"] == "HIGH" else 0
            rows.append({"t": q["quarter"], "target_quarter": q["quarter"], "province_code": code, "arm": "E36-LGBM",
                         "p": v["p_high"], "y": y})
            for b, ps in q["baselines_p_high"].items():
                rows.append({"t": q["quarter"], "target_quarter": q["quarter"], "province_code": code, "arm": b,
                             "p": float(ps[code]), "y": y})
    Pr = pd.DataFrame(rows)
    keys = ("n", "correct", "accuracy", "balanced_accuracy", "precision", "recall", "specificity", "f1", "roc_auc",
            "brier", "accuracy_ci95", "HIGH", "LOW")
    met = {a: E.arm_metrics(g) for a, g in Pr.groupby("arm")}
    ev = copy.deepcopy(bundle["evaluation"])
    ev["metrics_all"] = {a: {k: met[a][k] for k in keys} for a in met}
    m = met["E36-LGBM"]
    ev["target_75"] = {"correct": m["correct"], "n": m["n"], "accuracy": m["accuracy"],
                       "statement1_point_ge_0.75": m["accuracy"] >= 0.75, "date_bootstrap_ci95": m["accuracy_ci95"],
                       "statement2_demonstrated_lower_bound_ge_0.75": (m["accuracy_ci95"] or [0])[0] >= 0.75,
                       "wilson95_rows": m["accuracy_wilson95"], "always_high_accuracy": met["ALWAYS_HIGH"]["accuracy"],
                       "persistence_accuracy": met["B1_PERSISTENCE"]["accuracy"],
                       "balanced_accuracy": m["balanced_accuracy"]}
    pdl = {a: M.per_date_losses(g) for a, g in Pr.groupby("arm")}
    a_rows = Pr[Pr["arm"] == "E36-LGBM"].sort_values(["t", "province_code"])
    paired, raw = {}, {}
    for ref in E.BASELINES + ["ALWAYS_HIGH"]:
        diff = (pdl[ref]["bri"] - pdl["E36-LGBM"]["bri"]).to_numpy()
        j = a_rows.merge(Pr[Pr["arm"] == ref], on=["t", "province_code"], suffixes=("_a", "_r"))
        a_ok = (j["p_a"].to_numpy() >= .5).astype(int) == j["y_a"].to_numpy()
        r_ok = (j["p_r"].to_numpy() >= .5).astype(int) == j["y_r"].to_numpy()
        paired[ref] = {"dates": int(len(diff)), "rows": int(len(j)), "mean_brier_gain_vs_ref": float(diff.mean()),
                       "p_one_sided_arm_better": M.signflip_p(diff), "p_two_sided": E.signflip_two(diff),
                       "mcnemar": E.mcnemar_exact(a_ok, r_ok), "accuracy_diff": float(a_ok.mean() - r_ok.mean())}
        if ref in E.BASELINES:
            raw[ref] = paired[ref]["p_two_sided"]
    for ref, v in M.holm(raw).items():
        paired[ref]["holm_two_sided_over_six_baselines"] = v
    ev["paired_vs_baselines"] = paired
    ev["run"] = "E49-C2 calibrated E48-A1 backtests"
    ev["note"] = ("the proposed model (E48-A1 + E49-C2 calibration) is stored under the key 'E36-LGBM' that the API "
                  "reads; metrics recomputed from the calibrated probabilities")
    return ev


def main():
    import os

    os.chdir(BACKEND)
    cal, res = calibrated()
    original = B.frozen_ok
    replaced = []

    def frozen_ok(p):
        obj = original(p)                                  # the E48 hash check still runs
        if Path(p) == B.BUNDLE:
            obj = copy.deepcopy(obj)
            for q in obj["backtests"] + [obj["forecast"]]:
                for code, v in q["provinces"].items():
                    v["p_high_uncalibrated"] = v["p_high"]
                    v["p_high"] = cal[(q["quarter"], code)]
                    replaced.append((q["quarter"], code))
            obj["evaluation"] = evaluation(obj)
        return obj

    B.frozen_ok = frozen_ok
    B.DRIVER_METHOD = B.DRIVER_METHOD + ". " + NOTE
    rec = B.build()
    assert len(replaced) == 70, len(replaced)              # 13 backtest quarters + 2026-Q4, x 5 provinces
    se = rec["served_engine"]
    se.update({"name": "aiPHeed-E49-C2 (E48-A1 LightGBM + shrinkage calibration) - PREVIEW",
               "version": "E48.A1+E49.C2", "file": "data/e49/model/" + B.MODEL_TXT.name,
               "why_served": "Preview of E48-A1 (E36 inputs + the five trigger proportions) with E49-C2 shrinkage "
                             "calibration, in a separate local instance; the official system serves E36. " + NOTE,
               "evidence_status": "EXPERIMENTAL / PREVIEW (E49: lowest Brier among eligible calibration arms; gain "
                                  "over raw E48-A1 not significant)"})
    # The builder's limitation and verdict sentences hard-code E36's figures; restate them from this record's numbers.
    rows = {r["key"]: r for r in rec["validation"]["model_evaluation"]["rows"]}
    me, ah, pe = rows["E36-LGBM"], rows["ALWAYS_HIGH"], rows["B1_PERSISTENCE"]
    lim = [i for i, t in enumerate(rec["limitations"]) if t.startswith("One-quarter-ahead accuracy is")]
    assert len(lim) == 1
    rec["limitations"][lim[0]] = (
        f"One-quarter-ahead accuracy is {me['accuracy_lead1']:.3f} on {me['n']} development estimates, above always-HIGH "
        f"({ah['accuracy_lead1']:.3f}) and below persistence ({pe['accuracy_lead1']:.3f}). The 75% target is met as a "
        f"point estimate but not demonstrated (95% interval reaches {me['accuracy_ci95'][0]:.3f}). No baseline is "
        "beaten significantly.")
    v = rec["validation"]["threshold_75pct"]
    old = f"Always-HIGH reaches the same accuracy ({ah['accuracy_lead1']:.3f})"
    assert old in v["verdict"]
    v["verdict"] = v["verdict"].replace(old, f"Always-HIGH reaches {ah['accuracy_lead1']:.3f}")
    rec.pop("content_sha256", None)
    rec = B._clean(rec)
    rec["content_sha256"] = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    L.L6.guard32.EXP = OUT                                 # the research write guard: allow writes to data/e49 only
    (OUT / "model").mkdir(parents=True, exist_ok=True)
    for src in (B.MODEL_TXT, B.MODEL_CFG, B.MODEL_TXT.parent / "ARTIFACT_HASHES.json", B.BUNDLE, B.PROSPECTIVE,
                B.BUNDLE.with_suffix(".sha256"), B.PROSPECTIVE.with_suffix(".sha256")):
        shutil.copyfile(src, OUT / "model" / src.name)
    (OUT / "model" / "E49_C2_calibration.json").write_text(json.dumps(
        {"source": f"backend/experiments/e49/runs/{res['run']}", "params_by_target_quarter": res["calibration_params"]["C2"],
         "fallback_to_raw": res["fallback_to_raw"]["C2"], "note": NOTE}, indent=1), encoding="utf-8")
    blob = json.dumps(rec, indent=1, ensure_ascii=False, default=str, allow_nan=False).encode("utf-8")
    (OUT / "e49_record.json").write_bytes(blob)
    B.write_pdf(rec, OUT / "aiPHeed_E49_assessment_report.pdf")
    rows = rec["validation"]["model_evaluation"]["rows"]
    m = next(r for r in rows if r["key"] == "E36-LGBM")
    print(rec["content_sha256"][:16], len(blob), "bytes | model accuracy", m["accuracy_lead1"], "brier", m["brier"])
    for q in rec["quarters"]:
        if q["quarter"] >= "2025-Q4" and q["lead"] == 1:
            ps = {v["province"]: v["p_high"] for v in q["provinces"].values()}
            print(q["quarter"], round(sum(ps.values()) / 5, 4), ps)


if __name__ == "__main__":
    main()
