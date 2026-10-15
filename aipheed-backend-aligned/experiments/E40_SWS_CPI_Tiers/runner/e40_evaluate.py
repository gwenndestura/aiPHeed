"""E40 single evaluation run on the DEVELOPMENT quarters only (2023-Q1..2025-Q1 targets). The 4 holdout quarters are not
scored; their forecasts (and 2026-Q4) are issued from a model trained on development labels only and sealed by hash.

Folds: one per development target quarter with >= 8 known training label-quarters at its origin. A fold whose training
set has fewer than 2 HIGH rows FAILS the gate: no trained model is fitted on it and the failure is reported (the gate
is never relaxed). Baselines that need no fitted classifier (persistence, always-majority) are scored on every fold.

    <backend venv python> -B runner/e40_evaluate.py      -> runs/eval_<UTC>/ (+ frozen/E40_HOLDOUT_FORECASTS.json)
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e40_model as M  # noqa: E402

qi, qn = M.qi, M.qn
TRAINED = {"E40_BLEND": ("BLEND", "BLEND"), "E40_BLEND_NO_CPI": ("BLEND", "NO_CPI"), "LR_GOV_ONLY": ("LR", "GOV"),
           "LR_NLP_ONLY": ("LR", "NLP")}
BASE = ["PERSISTENCE", "ALWAYS_MAJORITY"]


def main():
    d = M.Data()
    dev = [qi(q) for q in d.spec["development_quarters"]]
    hold = [qi(q) for q in d.spec["holdout_quarters_untouched"]]
    run = M.E40 / "runs" / ("eval_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    run.mkdir(parents=True)
    folds, preds = [], []
    oof = {m: [] for m in TRAINED}
    for tgt in dev:
        t = tgt - 1
        tr = d.training(t)
        nq = tr["t"].nunique() if len(tr) else 0
        te = d.features(t)
        te["y"] = [d.y.get((p, tgt)) for p in te["province_code"]]
        te = te[te["y"].notna()].copy()
        te["stress"] = [d.stress[(p, tgt)] for p in te["province_code"]]
        hi = int(tr["y"].sum()) if len(tr) else 0
        f = {"target": qn(tgt), "origin": str(M.origin(t).date()), "train_label_quarters": int(nq),
             "train_rows": int(len(tr)), "train_HIGH": hi, "test_rows": int(len(te)), "test_HIGH": int(te["y"].sum()),
             "has_min_8_quarters": nq >= M.MIN_TRAIN_QUARTERS, "gate_ge2_HIGH": hi >= M.MIN_TRAIN_HIGH}
        if nq < M.MIN_TRAIN_QUARTERS:
            f["status"] = "not a fold (fewer than 8 training quarters)"
            folds.append(f)
            continue
        f["status"] = "fold; trained models fitted" if f["gate_ge2_HIGH"] else "fold; GATE FAILED (fewer than 2 HIGH training rows): no trained model"
        clim = (hi + 1) / (len(tr) + 2)
        maj = int(hi * 2 > len(tr))
        for r in te.itertuples():
            base = {"target": qn(tgt), "target_t": tgt, "province_code": r.province_code, "y": int(r.y),
                    "stress": r.stress, "gap_now": r.gap_now}
            preds.append({**base, "method": "PERSISTENCE", "p": r.y_last if r.y_last == r.y_last else float(maj),
                          "calibration": "none (0/1)"})
            preds.append({**base, "method": "ALWAYS_MAJORITY", "p": clim, "pred_class": maj,
                          "calibration": "training base rate (Laplace)"})
        if f["gate_ge2_HIGH"]:
            for m, (kind, fs) in TRAINED.items():
                raw = M.fit_predict(kind, tr, te, M.FEATURE_SETS[fs])
                cal, how = M.platt(oof[m])
                pc = cal(raw)
                for r, rv, pv in zip(te.itertuples(), raw, pc):
                    preds.append({"target": qn(tgt), "target_t": tgt, "province_code": r.province_code, "y": int(r.y),
                                  "stress": r.stress, "gap_now": r.gap_now, "method": m, "p_raw": float(rv),
                                  "p": float(pv), "calibration": how})
                oof[m] += [(float(rv), int(yv)) for rv, yv in zip(raw, te["y"])]
        folds.append(f)
    P = pd.DataFrame(preds)
    fold_rows = [f for f in folds if f["status"].startswith("fold")]
    failed = [f["target"] for f in fold_rows if not f["gate_ge2_HIGH"]]
    table, fold_metrics = {}, []
    for m in BASE + list(TRAINED):
        g = P[P["method"] == m] if len(P) else pd.DataFrame()
        if g.empty:
            table[m] = {"status": "not evaluated: no fold passed the >= 2-HIGH training gate" if m in TRAINED else "no rows"}
            continue
        cut = 0.5
        if m == "ALWAYS_MAJORITY":
            g = g.assign(p_cls=g["pred_class"])
        mt = M.metrics(g, cut) if m != "ALWAYS_MAJORITY" else {
            **M.metrics(g, cut), "accuracy": float((g["pred_class"] == g["y"]).mean()),
            "balanced_accuracy": M.balanced_acc(g["y"], g["pred_class"])}
        mt["CI95_accuracy"] = M.bootstrap(g, lambda s: float(((s["p"] >= 0.5).astype(int) == s["y"]).mean())) \
            if m != "ALWAYS_MAJORITY" else M.bootstrap(g, lambda s: float((s["pred_class"] == s["y"]).mean()))
        mt["CI95_balanced_accuracy"] = M.bootstrap(g, lambda s: M.balanced_acc(s["y"], (s["p"] >= 0.5).astype(int))) \
            if m != "ALWAYS_MAJORITY" else M.bootstrap(g, lambda s: M.balanced_acc(s["y"], s["pred_class"]))
        mt["CI95_Brier"] = M.bootstrap(g, lambda s: float(((s["p"] - s["y"]) ** 2).mean()))
        mt["folds_scored"] = sorted(g["target"].unique())
        table[m] = mt
        for q, gq in g.groupby("target"):
            fold_metrics.append({"method": m, "target": q, "n": len(gq), "HIGH": int(gq["y"].sum()),
                                 "Brier": float(((gq["p"] - gq["y"]) ** 2).mean()),
                                 "accuracy": float(((gq["pred_class"] if m == "ALWAYS_MAJORITY" else (gq["p"] >= 0.5).astype(int)) == gq["y"]).mean())})
    trained_ok = [m for m in TRAINED if "status" not in table[m]]
    oof_all = P[P["method"] == "E40_BLEND"][["y", "p"]] if "E40_BLEND" in trained_ok else pd.DataFrame()
    cutoff, cut_how = M.choose_cutoff(oof_all)
    verdict = ("NOT DEMONSTRATED: no trained model could be evaluated, because every development fold failed the "
               ">= 2-HIGH training gate. The system cannot be presented as a classifier on this sample; at most it is "
               "a ranking/monitoring display of the observed inputs.") if not trained_ok else None
    if trained_ok:
        b, pe, mj = table["E40_BLEND"], table["PERSISTENCE"], table["ALWAYS_MAJORITY"]
        beats = all(b[k] > o[k] for o in (pe, mj) for k in ("balanced_accuracy",)) and all(b["Brier"] < o["Brier"] for o in (pe, mj))
        verdict = ("blend beats persistence and majority on balanced accuracy and Brier" if beats else
                   "NOT DEMONSTRATED: the blend does not beat persistence and the majority class on balanced accuracy "
                   "and Brier; position the system as a ranking/monitoring tool")
    # ---------------------------------------------------------------- sealed holdout / operational forecasts
    last_dev = max(dev)
    sealed = []
    for tgt in hold + [qi("2026-Q4")]:
        t = tgt - 1
        tr = d.training(t, max_label_t=last_dev)            # development labels only; holdout labels never read
        hi = int(tr["y"].sum())
        te = d.features(t)
        rec = {"target": qn(tgt), "origin": str(M.origin(t).date()), "train_rows": len(tr), "train_HIGH": hi,
               "gate_ge2_HIGH": hi >= M.MIN_TRAIN_HIGH, "calibration": "uncalibrated (no out-of-fold scores: all "
               "development folds failed the gate); raw blend clipped to [0.02, 0.98]", "cutoff": cutoff,
               "provinces": {}}
        if rec["gate_ge2_HIGH"]:
            raw = np.clip(M.fit_predict("BLEND", tr, te, M.FEATURE_SETS["BLEND"]), *M.CLIP)
            te = te.assign(p=raw)
            te["rank"] = M.rank_with_ties(te)
            for r in te.itertuples():
                rec["provinces"][r.province_code] = {"score": round(float(r.p), 6), "band": "HIGH" if r.p >= cutoff else "LOW",
                                                     "rank": int(r.rank), "gap_now": round(float(r.gap_now), 4)}
        sealed.append(rec)
    body = json.dumps({"issued_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "label_freeze": json.loads((M.E40 / "frozen" / "E40_LABEL_FREEZE.json").read_text())["sha256"],
                       "scored": False, "note": "sealed before any holdout outcome is read; not scored in E40; "
                       "indicative, not an official classification", "forecasts": sealed}, indent=1).encode()
    out_f = M.E40 / "frozen" / "E40_HOLDOUT_FORECASTS.json"
    assert not out_f.exists(), "holdout forecasts already sealed"
    out_f.write_bytes(body)
    res = {"run": run.name, "folds": folds, "gate_failed_folds": failed, "table": table, "fold_metrics": fold_metrics,
           "band_cutoff": cutoff, "band_cutoff_rule": cut_how, "verdict": verdict,
           "holdout_forecasts_sha256": hashlib.sha256(body).hexdigest(),
           "lgbm_params": M.LGBM, "feature_sets": M.FEATURE_SETS}
    (run / "evaluation.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    if len(P):
        P.to_csv(run / "predictions_dev.csv", index=False, float_format="%.6g", lineterminator="\n")
    print(json.dumps({k: res[k] for k in ("folds", "gate_failed_folds", "verdict", "band_cutoff", "band_cutoff_rule",
                                         "holdout_forecasts_sha256")}, indent=1, default=float))
    for m, v in table.items():
        print(m, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items()
                  if k in ("status", "n", "HIGH", "accuracy", "balanced_accuracy", "F1_HIGH", "AUC", "Brier",
                           "CI95_balanced_accuracy", "CI95_Brier")})


if __name__ == "__main__":
    main()
