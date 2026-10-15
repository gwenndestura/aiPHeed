"""E37 freeze: the 2027-Q1 next-quarter forecast (lead 2 from origin 2026-10-01), its model artifact, exact TreeSHAP,
the six thesis baselines' forecasts and the lead-2 backtests for the dashboard. Refuses to overwrite.

    python -B runner/e37_freeze.py runs/<primary run>
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
import e37_lib as L  # noqa: E402
import e37_evaluate as E  # noqa: E402
import e36_freeze as F6  # noqa: E402

C, np, pd = L.C, L.np, L.pd
K = 2
MODEL_ID, VERSION = "aiPHeed-E37-LGBM-NQ", "E37.1"


def info_cutoff(d, t):
    X = d.test(t, K)
    return {"origin": str(L.origin(t).date()), "information_cutoff": f"{L.origin(t).date()}T00:00:00+08:00 (exclusive)",
            "lead": K, "feature_availability": {
                "H_last/H_trend/H_margin": f"SWS rounds posted before the origin; latest quarter {X['H_last_quarter'].iloc[0]}",
                "y_last": f"label of {X['last_label_quarter'].iloc[0]}",
                "D_last": f"PSA food CPI of {C.qs(t - 1)}", "Dnow/rice_rel": f"PSA food and rice CPI, months 1-2 of {C.qs(t)}",
                "news": f"validated articles published in {C.qs(t)}"}, "tau": d.tau(t)}


def main(run_dir):
    E.verify_protocol()
    run = Path(run_dir).resolve()
    res = json.loads((run / "results.json").read_text(encoding="utf-8"))
    Pr = pd.read_csv(run / "predictions.csv", dtype={"province_code": str})
    d = L.Data()
    import lightgbm

    back = []
    for target, s in res["selections"]["E36-LGBM"].items():
        t = C.qk(target) - K
        fs, g = s["chosen"].split("x")
        feats = L.FEATURE_SETS[fs]
        tr, te = d.train(t, K), d.test(t, K)
        m = L.L6.fit_lgbm(tr, feats, g)
        p = m.predict_proba(te[feats].astype(float))[:, 1]
        stored = Pr[(Pr["arm"] == "E36-LGBM") & (Pr["target_quarter"] == target)].set_index("province_code")["p"]
        assert all(abs(v - stored[c]) < 1e-8 for c, v in zip(te["province_code"], p)), target
        ex = F6.explain_rows(m, te.reset_index(drop=True), feats)
        pers = Pr[(Pr["arm"] == "B1_PERSISTENCE") & (Pr["target_quarter"] == target)].set_index("province_code")["p"]
        back.append({"quarter": target, "mode": "BACKTEST", "config": s["chosen"], **info_cutoff(d, t),
                     "provinces": {c: {"province": C.NAMES[c], "p_high": float(v),
                                       "observed_label": "HIGH" if d.label(c, t + K, t) else "LOW",
                                       "observed_S1": float(d.Sv[(c, t + K)]), "persistence_p": float(pers[c]), **ex[c]}
                                   for c, v in zip(te["province_code"], p)}})
    oc = res["operational_choice"]
    fs, g = oc["chosen"].split("x")
    feats = L.FEATURE_SETS[fs]
    t = L.OPERATIONAL_T
    tr, te = d.train(t, K), d.test(t, K)
    m = L.L6.fit_lgbm(tr, feats, g)
    p = m.predict_proba(te[feats].astype(float))[:, 1]
    mpath = L.E37 / "models" / "E37-LGBM-NQ_O2026-10-01_lead2.txt"
    if mpath.exists():
        raise SystemExit("model artifact exists; refusing to overwrite")
    mpath.parent.mkdir(exist_ok=True)
    m.booster_.save_model(str(mpath))
    msha = hashlib.sha256(mpath.read_bytes()).hexdigest()
    cfg = {"model_id": MODEL_ID, "version": VERSION, "artifact": mpath.name, "artifact_sha256": msha, "lead": K,
           "feature_set": fs, "features": feats, "grid_id": g, "params": {**L.L6._BASE, **L.GRID[g]},
           "selection": oc, "lightgbm_version": lightgbm.__version__, "training_rows": int(len(tr)),
           "training_target_quarters": sorted({C.qs(int(x)) for x in tr["target_q"]}),
           "protocol_sha256": res["protocol_sha256"], "evaluation_run": run.name, **info_cutoff(d, t),
           "status": "EXPERIMENTAL / NOT VALIDATED"}
    (mpath.with_suffix(".json")).write_bytes(json.dumps(C.clean(cfg), indent=1).encode())
    ex = F6.explain_rows(m, te.reset_index(drop=True), feats)
    arms = L.fixed_arms(d, t, K)
    base = {}
    for b in E.BASELINES + E.DIAGNOSTICS:
        if b in L.POOLS:
            (bfs, bg), _ = L.operational_choice(d, Pr, K, b)
            base[b] = {"config": L.cfg_name(bfs, bg), "p_high": arms[L.cfg_name(bfs, bg)],
                       "formal_thesis_baseline": True}
        else:
            base[b] = {"p_high": arms[b], "formal_thesis_baseline": b in E.BASELINES}
    fc = {"quarter": "2027-Q1", "mode": "FORECAST", "model_id": MODEL_ID, "version": VERSION, "config": oc["chosen"],
          "artifact_sha256": msha, **info_cutoff(d, t),
          "provinces": {c: {"province": C.NAMES[c], "p_high": float(v), "persistence_p": arms["B1_PERSISTENCE"][c], **ex[c]}
                        for c, v in zip(te["province_code"], p)},
          "baselines": base, "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "scoring": "after the SWS 2027-Q1 round is posted and 2027-Q1 CPI is released; never re-fitted before then"}
    h1 = F6.write_frozen(L.E37 / "frozen" / "E37_PROSPECTIVE_2027Q1.json", fc)
    mt = res["metrics"]
    keys = ("n", "correct", "accuracy", "balanced_accuracy", "precision", "recall", "specificity", "f1", "roc_auc",
            "pr_auc", "brier", "accuracy_ci95", "HIGH", "LOW", "dates")
    bundle = {"schema": "e37-bundle/1", "model": cfg, "backtests": back, "forecast": fc, "prospective_sha256": h1,
              "evaluation": {"run": run.name, "lead": K, "dates": res["dates"], "target_75": res["target_75"],
                             "metrics": {a: {k: mt[a][k] for k in keys} for a in ["E36-LGBM"] + E.BASELINES + E.DIAGNOSTICS},
                             "paired": res["paired"]}}
    h2 = F6.write_frozen(L.E37 / "frozen" / "E37_SERVING_BUNDLE.json", bundle)
    print("model", msha[:16], "prospective", h1[:16], "bundle", h2[:16])
    for c in C.PROVS:
        print(C.NAMES[c], round(fc["provinces"][c]["p_high"], 4), "persistence", arms["B1_PERSISTENCE"][c])


if __name__ == "__main__":
    main(sys.argv[1])
