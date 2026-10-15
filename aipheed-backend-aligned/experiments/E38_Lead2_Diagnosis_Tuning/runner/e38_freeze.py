"""E38 freeze: the adopted next-quarter procedure's 2027-Q1 forecast (origin 2026-10-01, lead 2), its model artifact,
exact TreeSHAP and the decision threshold. The six baselines' 2027-Q1 forecasts are E37's frozen ones (identical
definitions and inputs). Refuses to overwrite.

    python -B runner/e38_freeze.py runs/<primary run>
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
import e38_lib as L  # noqa: E402
import e38_evaluate as E  # noqa: E402

C, np, pd = L.C, L.np, L.pd
MODEL_ID, VERSION = "aiPHeed-E38-LGBM-NQ", "E38.1"
E37FROZEN = L.E38.parent / "E37_Next_Quarter_Forecast" / "frozen" / "E37_PROSPECTIVE_2027Q1.json"


def write_frozen(path: Path, obj) -> str:
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path}")
    b = json.dumps(C.clean(obj), indent=1, sort_keys=True, allow_nan=False).encode()
    path.write_bytes(b)
    h = hashlib.sha256(b).hexdigest()
    path.with_suffix(".sha256").write_bytes(f"{h}  {path.name}\n".encode())
    return h


def main(run_dir):
    E.verify_protocol()
    res = json.loads((Path(run_dir) / "results.json").read_text(encoding="utf-8"))
    op = res["operational"]
    assert res["adoption"]["adopt_E38"], "the adoption rule did not select E38"
    adj, rest = ("prior_shift", op["chosen"][:-3]) if op["chosen"].endswith("+PS") else ("none", op["chosen"])
    fs, g = rest.split("x")
    feats = L.FEATURE_SETS[fs]
    d = L.Data()
    t = L.L7.OPERATIONAL_T
    tr, te = d.train(t), d.test(t)
    base, m = L.fit_predict(tr, te, feats, g)
    shift = (L._logit(L.recent_rate(d, t)) - L._logit((tr["y"].sum() + 1) / (len(tr) + 2))) if adj == "prior_shift" else 0.0
    sh = L.L6.shap_contributions(m, te[feats].reset_index(drop=True))
    import lightgbm

    mpath = L.E38 / "models" / "E38-LGBM-NQ_O2026-10-01_lead2.txt"
    if mpath.exists():
        raise SystemExit("model exists")
    m.booster_.save_model(str(mpath))
    raw = mpath.read_bytes()
    msha = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()       # LF-normalized identity (see E36 lesson)
    prov = {}
    for i, r in te.reset_index(drop=True).iterrows():
        p = 1 / (1 + math.exp(-(L._logit(base[r.province_code]) + shift)))
        z = float(sh.loc[i, "expected_value"]) + shift + sum(float(sh.loc[i, f]) for f in feats)
        assert abs(1 / (1 + math.exp(-z)) - p) < 1e-6
        drivers = sorted(({"key": f, "factor": L.L6.DISPLAY[f], "source": L.L6.SOURCE[f],
                           "value": None if r[f] != r[f] else float(r[f]), "contribution": float(sh.loc[i, f])}
                          for f in feats), key=lambda x: -abs(x["contribution"]))
        prov[r.province_code] = {"province": C.NAMES[r.province_code], "p_high": p, "decision_threshold": op["threshold"],
                                 "model_estimate": "HIGH" if p >= op["threshold"] else "LOW",
                                 "persistence_p": float(r.y_last) if r.y_last == r.y_last else None,
                                 "expected_value_logodds": float(sh.loc[i, "expected_value"]),
                                 "prior_shift_logodds": shift, "drivers": drivers}
    cfg = {"model_id": MODEL_ID, "version": VERSION, "artifact": mpath.name, "artifact_sha256_lf": msha, "lead": L.K,
           "feature_set": fs, "features": feats, "grid_id": g, "params": {**L.BASE, **L.GRID[g]}, "adjustment": adj,
           "prior_shift_logodds": shift, "decision_threshold": op["threshold"], "selection": op,
           "lightgbm_version": lightgbm.__version__, "training_rows": int(len(tr)),
           "training_target_quarters": sorted({C.qs(int(x)) for x in tr["target_q"]}),
           "protocol_sha256": res["protocol_sha256"], "evaluation_run": Path(run_dir).name,
           "status": "EXPERIMENTAL / NOT VALIDATED (development accuracy 39/55 = 0.709; 75% not met)"}
    mpath.with_suffix(".json").write_bytes(json.dumps(C.clean(cfg), indent=1).encode())
    e37 = json.loads(E37FROZEN.read_text(encoding="utf-8"))
    X = d.test(t)
    fc = {"quarter": "2027-Q1", "mode": "FORECAST", "lead": L.K, "model_id": MODEL_ID, "version": VERSION,
          "config": op["chosen"], "decision_threshold": op["threshold"], "artifact_sha256_lf": msha,
          "origin": "2026-10-01", "information_cutoff": "2026-10-01T00:00:00+08:00 (exclusive)",
          "feature_availability": e37["feature_availability"], "tau": d.tau(t),
          "latest_label_quarter": X["last_label_quarter"].iloc[0], "latest_H_quarter": X["H_last_quarter"].iloc[0],
          "provinces": prov, "six_baselines_2027Q1": {k: v for k, v in e37["baselines"].items()},
          "baselines_source": f"E37 frozen record {E37FROZEN.name} (identical definitions and inputs)",
          "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "scoring": "after the SWS 2027-Q1 round is posted and 2027-Q1 PSA CPI is released; never re-fitted before then"}
    h = write_frozen(L.E38 / "frozen" / "E38_PROSPECTIVE_2027Q1.json", fc)
    ev = {a: {k: res["metrics"][a][k] for k in ("n", "correct", "accuracy", "accuracy_ci95", "balanced_accuracy",
                                                 "precision", "recall", "specificity", "f1", "roc_auc", "pr_auc",
                                                 "brier", "HIGH", "LOW", "dates", "TN", "FP", "FN", "TP")}
          for a in ["E38-LGBM", "E36-LGBM"] + E.BASELINES + E.DIAG}
    h2 = write_frozen(L.E38 / "frozen" / "E38_SERVING_BUNDLE.json",
                      {"schema": "e38-bundle/1", "model": cfg, "forecast": fc, "prospective_sha256": h,
                       "evaluation": {"run": Path(run_dir).name, "lead": L.K, "dates": res["dates"], "metrics": ev,
                                      "paired": res["paired"], "adoption": res["adoption"], "path": res["path"]}})
    print("model(lf)", msha[:16], "prospective", h[:16], "bundle", h2[:16])
    for c, v in prov.items():
        print(v["province"], round(v["p_high"], 4), v["model_estimate"], "persistence", v["persistence_p"])


if __name__ == "__main__":
    main(sys.argv[1])
