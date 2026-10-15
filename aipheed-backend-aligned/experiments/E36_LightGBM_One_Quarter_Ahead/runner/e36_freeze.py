"""E36 freeze: the operational model, its 2026-Q4 one-quarter-ahead forecast, the six baselines' forecasts, and the
serving bundle (backtests with exact TreeSHAP) for the dashboard.

    python -B runner/e36_freeze.py runs/<primary run>

Writes models/E36-LGBM_O2026-10-01.{txt,json}, frozen/E36_PROSPECTIVE_2026Q4.json (+ .sha256) and
frozen/E36_SERVING_BUNDLE.json (+ .sha256). Refuses to overwrite an existing frozen file.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e36_lib as L  # noqa: E402
import e36_evaluate as E  # noqa: E402

C, np, pd = L.C, L.np, L.pd
MODEL_ID = "aiPHeed-E36-LGBM"
VERSION = "E36.1"


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_frozen(path: Path, obj: dict) -> str:
    if path.exists():
        raise SystemExit(f"refusing to overwrite frozen file {path}")
    b = json.dumps(C.clean(obj), indent=1, sort_keys=True, allow_nan=False).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b)
    h = sha_bytes(b)
    path.with_suffix(".sha256").write_bytes(f"{h}  {path.name}\n".encode())
    return h


def explain_rows(model, X: pd.DataFrame, feats: list[str]) -> dict:
    sh = L.shap_contributions(model, X[feats])
    out = {}
    for i, r in X.iterrows():
        drivers = sorted(({"key": f, "factor": L.DISPLAY[f], "source": L.SOURCE[f],
                           "value": None if r[f] != r[f] else float(r[f]),
                           "contribution": float(sh.loc[i, f])} for f in feats),
                         key=lambda x: -abs(x["contribution"]))
        out[r["province_code"]] = {"expected_value_logodds": float(sh.loc[i, "expected_value"]), "drivers": drivers}
    return out


def info_cutoff(d: L.Data, t: int) -> dict:
    X = d.test(t)
    return {"origin": str(L.origin(t).date()), "information_cutoff": f"{L.origin(t).date()}T00:00:00+08:00 (exclusive)",
            "feature_availability": {
                "H_last/H_trend/H_margin": f"SWS rounds posted before the origin; latest quarter {X['H_last_quarter'].iloc[0]}",
                "y_last": f"label of {X['last_label_quarter'].iloc[0]} (latest quarter whose SWS rounds were posted before the origin)",
                "D_last": f"PSA food CPI of {C.qs(t - 1)}",
                "Dnow/rice_rel": f"PSA food and rice CPI, months 1-2 of {C.qs(t)}",
                "news": f"validated (R1.1) articles published in {C.qs(t)} (FORECAST rule: evidence quarter = target - 1)"},
            "tau": d.tau(t)}


def main(run_dir: str):
    E.verify_protocol()
    run = Path(run_dir).resolve()
    res = json.loads((run / "results.json").read_text(encoding="utf-8"))
    Pr = pd.read_csv(run / "predictions.csv", dtype={"province_code": str})
    d = L.Data()
    import lightgbm

    # ---------------- backtests: refit the nested choice at each origin, check p, explain
    back = []
    for target, s in res["selections"]["E36-LGBM"].items():
        t = C.qk(target) - 1
        fs, g = s["chosen"].split("x")
        feats = L.FEATURE_SETS[fs]
        tr, te = d.train(t), d.test(t)
        m = L.fit_lgbm(tr, feats, g)
        p = m.predict_proba(te[feats].astype(float))[:, 1]
        stored = Pr[(Pr["arm"] == "E36-LGBM") & (Pr["target_quarter"] == target)].set_index("province_code")["p"]
        for code, v in zip(te["province_code"], p):
            assert abs(v - stored[code]) < 1e-8, (target, code)
        ex = explain_rows(m, te.reset_index(drop=True), feats)
        ref = {a: Pr[(Pr["arm"] == a) & (Pr["target_quarter"] == target)].set_index("province_code")["p"].to_dict()
               for a in E.BASELINES + ["ALWAYS_HIGH"]}
        back.append({"quarter": target, "mode": "BACKTEST", "lead": 1, "config": s["chosen"],
                     "selection_rule": s["rule"], **info_cutoff(d, t), "training_rows": int(len(tr)),
                     "provinces": {code: {"province": C.NAMES[code], "p_high": float(v),
                                          "observed_label": "HIGH" if d.label(code, t + 1, t) else "LOW",
                                          "observed_S1": float(d.Sv[(code, t + 1)]),
                                          "persistence_p": ref["B1_PERSISTENCE"][code], **ex[code]}
                                   for code, v in zip(te["province_code"], p)},
                     "baselines_p_high": ref})
    # ---------------- operational model at 2026-10-01
    oc = res["operational_choice"]
    fs, g = oc["chosen"].split("x")
    feats = L.FEATURE_SETS[fs]
    t = L.OPERATIONAL_T
    tr, te = d.train(t), d.test(t)
    m = L.fit_lgbm(tr, feats, g)
    p = m.predict_proba(te[feats].astype(float))[:, 1]
    mdir = L.E36 / "models"
    mdir.mkdir(exist_ok=True)
    mpath = mdir / "E36-LGBM_O2026-10-01.txt"
    if mpath.exists():
        raise SystemExit("model artifact exists; refusing to overwrite")
    m.booster_.save_model(str(mpath))
    model_sha = sha_bytes(mpath.read_bytes())
    gain = dict(zip(feats, m.booster_.feature_importance("gain").astype(float)))
    cfg = {"model_id": MODEL_ID, "version": VERSION, "artifact": mpath.name, "artifact_sha256": model_sha,
           "feature_set": fs, "features": feats, "grid_id": g, "params": {**L._BASE, **L.GRID[g]},
           "selection": oc, "lightgbm_version": lightgbm.__version__, "training_rows": int(len(tr)),
           "training_HIGH": int(tr["y"].sum()),
           "training_target_quarters": sorted({C.qs(int(x)) for x in tr["target_q"]}),
           "gain_importance": gain, "protocol_sha256": res["protocol_sha256"], "evaluation_run": run.name,
           "inputs": res["inputs"], **info_cutoff(d, t), "status": "EXPERIMENTAL / NOT VALIDATED"}
    (mdir / "E36-LGBM_O2026-10-01.json").write_bytes(json.dumps(C.clean(cfg), indent=1).encode())
    ex = explain_rows(m, te.reset_index(drop=True), feats)
    arms = L.fixed_arms(d, t)
    full = Pr[~Pr["arm"].isin(["P45", "F12"])]
    base_fc = {}
    for b in E.BASELINES + ["ALWAYS_HIGH", "B1p_CAL_PERSISTENCE", "CLIMATOLOGY", "PCF21"]:
        if b in L.POOLS:
            (bfs, bg), _ = L.operational_choice(d, full, b)
            base_fc[b] = {"config": L.cfg_name(bfs, bg), "p_high": arms[L.cfg_name(bfs, bg)]}
        else:
            base_fc[b] = {"p_high": arms[b]}
    fc = {"quarter": "2026-Q4", "mode": "FORECAST", "lead": 1, "model_id": MODEL_ID, "version": VERSION,
          "config": oc["chosen"], "artifact_sha256": model_sha, **info_cutoff(d, t),
          "provinces": {code: {"province": C.NAMES[code], "p_high": float(v),
                               "persistence_p": arms["B1_PERSISTENCE"][code], **ex[code]}
                        for code, v in zip(te["province_code"], p)},
          "baselines": base_fc,
          "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "scoring": "after the SWS December 2026 round (2026-Q4) is released; never re-fitted before then"}
    h1 = write_frozen(L.E36 / "frozen" / "E36_PROSPECTIVE_2026Q4.json", fc)
    m_all = res["metrics"]["all"]
    keys = ("n", "correct", "accuracy", "balanced_accuracy", "precision", "recall", "specificity", "f1", "roc_auc",
            "brier", "accuracy_ci95", "HIGH", "LOW")
    bundle = {"schema": "e36-bundle/1", "model": cfg, "backtests": back, "forecast": fc,
              "evaluation": {"run": run.name, "dates": res["dates"], "target_75": res["target_75"],
                             "metrics_all": {a: {k: m_all[a][k] for k in keys}
                                             for a in E.BASELINES + ["E36-LGBM", "ALWAYS_HIGH"]},
                             "paired_vs_baselines": res["paired"]["E36-LGBM"]},
              "prospective_sha256": h1}
    h2 = write_frozen(L.E36 / "frozen" / "E36_SERVING_BUNDLE.json", bundle)
    print("model", mpath.name, model_sha[:16], "| prospective", h1[:16], "| bundle", h2[:16])
    for code in C.PROVS:
        v = fc["provinces"][code]
        print(C.NAMES[code], round(v["p_high"], 4), [(x["key"], round(x["contribution"], 3)) for x in v["drivers"][:3]])
    print("baselines 2026-Q4:", {b: {k: round(x, 3) for k, x in v["p_high"].items()} for b, v in base_fc.items()})


if __name__ == "__main__":
    main(sys.argv[1])
