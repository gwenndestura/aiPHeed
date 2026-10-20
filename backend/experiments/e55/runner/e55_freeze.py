"""E55 freeze: E53-A1 at lead 2 (target 2027-Q1, origin 2026-10-01), the same pattern as e53_freeze.py.

    python -B backend/experiments/e55/runner/e55_freeze.py

Writes (refuses to overwrite):
  backend/experiments/e55/models/E55-LGBM-NQ_O2026-10-01_lead2.{txt,json} + ARTIFACT_HASHES.json
  backend/experiments/e55/frozen/E55_PROSPECTIVE_2027Q1.json, E55_SERVING_BUNDLE.json (+ .sha256)
The bundle has the schema of E38_SERVING_BUNDLE.json (model / forecast / evaluation / prospective_sha256), so the record
builder can use it as its next-quarter (lead-2) bundle, plus the 11 lead-2 development backtests.

Served probabilities are E55's C2-calibrated values (shrinkage fitted on earlier dates only), not the raw LightGBM;
the raw value is kept as p_high_uncalibrated. Exact TreeSHAP is of the raw LightGBM. Every probability is asserted
against E55_results.json and runs/<run>/predictions.csv; every refit against the walk-forward.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e55_run as X55  # noqa: E402  (K = 2, E53 Data / pool; brings in e53_run, e37/e38/e48/e36 libs)

sys.path.insert(0, str(X55.BACKEND / "experiments" / "e53" / "runner"))
import e53_freeze as F53  # noqa: E402  (COND_DISPLAY; F48 = e48_freeze; F = e36_freeze)

X53, L, L6, L7, C, np, pd, E = X55.X53, X55.L, X55.L6, X55.L7, X55.C, X55.np, X55.pd, X55.EV
F48, F = F53.F48, F53.F
E55 = X55.E55
L6.guard32.EXP = E55
K, POOL, PROVS, NAMES = X55.K, X55.POOL, X55.PROVS, X55.NAMES
MODEL_ID, VERSION = "aiPHeed-E55", "E55.1"
E38_RESULTS = X55.E38_RUN.parent / "results.json"
OUT_M, OUT_F = E55 / "models", E55 / "frozen"
MODEL = OUT_M / "E55-LGBM-NQ_O2026-10-01_lead2.txt"


def availability(d, t: int) -> dict:
    X = d.test(t, K)
    return {"origin": str(L6.origin(t).date()), "information_cutoff": f"{L6.origin(t).date()}T00:00:00+08:00 (exclusive)",
            "feature_availability": {
                "H_last/H_trend/H_margin": f"SWS rounds posted before the origin; latest quarter {X['H_last_quarter'].iloc[0]}",
                "y_last": f"label of {X['last_label_quarter'].iloc[0]} (latest quarter whose SWS rounds were posted before the origin)",
                "D_last": f"PSA food CPI of {C.qs(t - 1)}",
                "Dnow/rice_rel": f"PSA food and rice CPI, months 1-2 of {C.qs(t)}",
                "news": f"validated (R1.1) articles published in {C.qs(t)} (lead 2: evidence quarter = target - 2)",
                "trig_*": f"news titles published in {C.qs(t)} (trigger classifier shares)",
                "cond_*": (f"measured conditions of {C.qs(t - 1)} ranked against 2021-Q1..{C.qs(t - 2)} (PSA CPI, "
                           "NASA POWER/NOAA, PSA fisheries, PSA LFS national, BSP)")},
            "tau": d.tau(t)}


def main():
    for p in (MODEL, OUT_F / "E55_SERVING_BUNDLE.json", OUT_F / "E55_PROSPECTIVE_2027Q1.json"):
        if p.exists():
            raise SystemExit(f"refusing to overwrite {p}")
    res = json.loads((E55 / "E55_results.json").read_text(encoding="utf-8"))
    pred = pd.read_csv(E55 / "runs" / res["run"] / "predictions.csv", dtype={"province_code": str})
    cal = {(r.target_quarter, r.province_code): (float(r.p), float(r.p_raw)) for r in pred.itertuples()}
    X53.register()
    L6.DISPLAY.update({**F48.TRIG_DISPLAY, **F53.COND_DISPLAY})
    L6.SOURCE.update({f: "news" for f in F48.TRIG_DISPLAY} | {f: "government" for f in F53.COND_DISPLAY})
    d = X53.Data(X53.build_cond())
    Pr, info = L7.walk_forward(d, K)
    assert info["dates"] == res["test_quarters"], (info["dates"], res["test_quarters"])
    import lightgbm

    back = []
    for target, s in info["selections"][POOL].items():
        t = C.qk(target) - K
        fs, g = s["chosen"].split("x")
        feats = L6.FEATURE_SETS[fs]
        tr, te = d.train(t, K), d.test(t, K)
        m = L6.fit_lgbm(tr, feats, g)
        p = m.predict_proba(te[feats].astype(float))[:, 1]
        wf = Pr[(Pr["arm"] == POOL) & (Pr["target_quarter"] == target)].set_index("province_code")["p"]
        ex = F.explain_rows(m, te.reset_index(drop=True), feats)
        ref = {a: Pr[(Pr["arm"] == a) & (Pr["target_quarter"] == target)].set_index("province_code")["p"].to_dict()
               for a in ("B1_PERSISTENCE", "ALWAYS_HIGH")}
        provs = {}
        for code, v in zip(te["province_code"], p):
            assert abs(v - wf[code]) < 1e-8, (target, code)
            pc, praw = cal[(target, code)]
            assert abs(v - praw) < 1e-8, (target, code, v, praw)
            provs[code] = {"province": C.NAMES[code], "p_high": pc, "p_high_uncalibrated": float(v),
                           "observed_label": "HIGH" if d.label(code, t + K, t) else "LOW",
                           "observed_S1": float(d.Sv[(code, t + K)]), "persistence_p": ref["B1_PERSISTENCE"][code],
                           **ex[code]}
        back.append({"quarter": target, "mode": "BACKTEST", "lead": K, "config": s["chosen"], "selection_rule": s["rule"],
                     **availability(d, t), "training_rows": int(len(tr)), "provinces": provs, "baselines_p_high": ref})

    T = L7.OPERATIONAL_T
    (fs, g), sel = L7.operational_choice(d, Pr, K, POOL)
    cfg_name = L6.cfg_name(fs, g)
    fq = res["forecast_2027Q1"]
    assert cfg_name == fq["config"], (cfg_name, fq["config"])
    feats = L6.FEATURE_SETS[fs]
    tr, te = d.train(T, K), d.test(T, K)
    m = L6.fit_lgbm(tr, feats, g)
    p = m.predict_proba(te[feats].astype(float))[:, 1]
    shrink = res["shrink_params"]["2027-Q1"]
    OUT_M.mkdir(exist_ok=True)
    m.booster_.save_model(str(MODEL))
    raw = MODEL.read_bytes()
    sha, sha_lf = F.sha_bytes(raw), hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    (OUT_M / "ARTIFACT_HASHES.json").write_text(json.dumps({MODEL.name: {"sha256_at_freeze": sha,
                                                                       "sha256_lf_normalized": sha_lf}}, indent=1),
                                                encoding="utf-8")
    ex = F.explain_rows(m, te.reset_index(drop=True), feats)
    refs = L7.references(d, T, K)
    av = availability(d, T)
    provs = {}
    for code, v in zip(te["province_code"], p):
        name = C.NAMES[code]
        assert abs(v - fq[name]["p_raw"]) < 1e-9, (name, v, fq[name]["p_raw"])
        pc = shrink["a"] * float(v) + (1 - shrink["a"]) * shrink["base_rate"]
        assert abs(pc - fq[name]["p_high"]) < 1e-9, (name, pc, fq[name]["p_high"])       # served = E55's C2 value
        provs[code] = {"province": name, "p_high": pc, "p_high_uncalibrated": float(v),
                       "persistence_p": refs["B1_PERSISTENCE"][code], "decision_threshold": 0.5,
                       "model_estimate": "HIGH" if pc >= 0.5 else "LOW", **ex[code]}
    m55 = res["metrics"]["E55_C2"]
    status = (f"EXPERIMENTAL PREVIEW (development accuracy {m55['accuracy']:.3f} = {round(m55['accuracy'] * m55['n'])}/"
              f"{m55['n']}, balanced accuracy {m55['balanced_accuracy']:.3f}; below 75% and below persistence; did not "
              "meet its adoption rule)")
    model = {"model_id": MODEL_ID, "version": VERSION, "lead": K, "artifact": MODEL.name, "artifact_sha256_lf": sha_lf,
             "feature_set": fs, "features": feats, "grid_id": g, "params": {**L6._BASE, **L6.GRID[g]},
             "adjustment": "C2 shrinkage toward the training base rate", "shrink": shrink, "decision_threshold": 0.5,
             "selection": {"chosen": cfg_name, **sel}, "lightgbm_version": lightgbm.__version__,
             "training_rows": int(len(tr)), "training_target_quarters": sorted({C.qs(int(x)) for x in tr["target_q"]}),
             "evaluation_run": res["run"], "status": status,
             "protocol_sha256": "E55 (experiment): E53-A1 inputs at lead 2; see backend/experiments/e55"}
    (OUT_M / "E55-LGBM-NQ_O2026-10-01_lead2.json").write_bytes(json.dumps(C.clean(model), indent=1).encode())
    fc = {"quarter": "2027-Q1", "mode": "FORECAST", "lead": K, "model_id": MODEL_ID, "version": VERSION,
          "config": cfg_name, "artifact_sha256_lf": sha_lf, "decision_threshold": 0.5, **av,
          "provinces": provs, "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "scoring": "after the SWS 2027-Q1 round is posted and 2027-Q1 PSA CPI is released; never re-fitted before then"}
    h1 = F.write_frozen(OUT_F / "E55_PROSPECTIVE_2027Q1.json", fc)
    # evaluation on the 55 lead-2 rows: E55 (C2) recomputed; E38 and persistence as stored by E38 on identical rows
    e38 = json.loads(E38_RESULTS.read_text(encoding="utf-8"))["metrics"]
    g55 = pred.assign(arm="E55")
    met = {"E55": E.arm_metrics(g55)}
    assert abs(met["E55"]["accuracy"] - m55["accuracy"]) < 1e-12 and met["E55"]["correct"] == 37
    keys = ("n", "correct", "accuracy", "accuracy_ci95", "balanced_accuracy", "precision", "recall", "f1", "roc_auc",
            "brier", "TN", "FP", "TP", "FN", "HIGH", "LOW")
    metrics = {"E55": {k: met["E55"][k] for k in keys}, **{a: {k: e38[a][k] for k in keys} for a in
                                                          ("B1_PERSISTENCE", "E38-LGBM", "ALWAYS_HIGH")}}
    bundle = {"schema": "e36-bundle/1", "model": model, "forecast": fc, "backtests": back,
              "evaluation": {"run": res["run"], "lead": K, "dates": info["dates"], "metrics": metrics,
                             "paired": res["tests_vs"], "adoption": {**res["adoption"],
                                                                     "validation_status": "NOT DEMONSTRATED"}},
              "prospective_sha256": h1}
    h2 = F.write_frozen(OUT_F / "E55_SERVING_BUNDLE.json", bundle)
    print("model", cfg_name, sha_lf[:16], "| prospective", h1[:16], "| bundle", h2[:16], "| backtests", len(back),
          "| acc", round(m55["accuracy"], 4))
    for code in PROVS:
        v = provs[code]
        print(v["province"], round(v["p_high"], 4), "raw", round(v["p_high_uncalibrated"], 4),
              [(x["key"], round(x["contribution"], 3)) for x in v["drivers"][:4]])


if __name__ == "__main__":
    main()
