"""E48-A1 freeze, the same process as E36's (runner/e36_freeze.py): the operational model at 2026-10-01, its 2026-Q4
forecast with exact TreeSHAP, the six baselines' forecasts, and the serving bundle (backtests refitted at each origin
under the nested rule, checked against the walk-forward, with TreeSHAP), for scripts/build_record_e36.build().

E48-A1 = E36's 13 inputs + the five trigger proportions (e38_lib shares), current trailing-median labels, lead 1,
E36's grid and nested rule (pool "E48-T5": COMPACT/COMB + trig_*, settings G1/G4/G3/G2, default COMB_T5 x G1).

    python -B backend/experiments/e48/runner/e48_freeze.py
Writes backend/experiments/e48/models/E48-A1-LGBM_O2026-10-01.{txt,json} + ARTIFACT_HASHES.json and
backend/experiments/e48/frozen/E48_PROSPECTIVE_2026Q4.json, E48_SERVING_BUNDLE.json (+ .sha256). Refuses to overwrite.
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
import e48_lib as L  # noqa: E402
import e36_evaluate as E  # noqa: E402
import e36_freeze as F  # noqa: E402  (explain_rows, info_cutoff, write_frozen; same e36_lib module object)

L6, C, np, pd, M = L.L6, L.C, L.np, L.pd, E.M
L6.guard32.EXP = L.E48
ARM = "E48-T5"
MODEL_ID, VERSION = "aiPHeed-E48-A1-LGBM", "E48.A1"
TRIG_DISPLAY = {"trig_market": "Share of the province's news titles about market and food prices",
                "trig_climate": "Share of the province's news titles about climate and weather",
                "trig_employment": "Share of the province's news titles about employment",
                "trig_ofw_remittance": "Share of the province's news titles about OFW remittances",
                "trig_fish_kill": "Share of the province's news titles about fish kills"}


def target_75(m, ref):
    return {"correct": m["correct"], "n": m["n"], "accuracy": m["accuracy"],
            "statement1_point_ge_0.75": m["accuracy"] >= 0.75, "date_bootstrap_ci95": m["accuracy_ci95"],
            "statement2_demonstrated_lower_bound_ge_0.75": (m["accuracy_ci95"] or [0])[0] >= 0.75,
            "wilson95_rows": m["accuracy_wilson95"], "always_high_accuracy": ref["ALWAYS_HIGH"]["accuracy"],
            "persistence_accuracy": ref["B1_PERSISTENCE"]["accuracy"], "balanced_accuracy": m["balanced_accuracy"]}


def paired(Pr, arm):
    """e36_evaluate.main's paired block, for the E48 arm."""
    pdl = {a: M.per_date_losses(g) for a, g in Pr.groupby("arm")}
    out, praw = {}, {}
    a_rows = Pr[Pr["arm"] == arm].sort_values(["t", "province_code"])
    for ref in E.BASELINES + ["ALWAYS_HIGH", "PCF21", "B1p_CAL_PERSISTENCE", "CLIMATOLOGY"]:
        common = pdl[arm].index.intersection(pdl[ref].index)
        diff = (pdl[ref]["bri"][common] - pdl[arm]["bri"][common]).to_numpy()
        j = a_rows.merge(Pr[Pr["arm"] == ref], on=["t", "province_code"], suffixes=("_a", "_r"))
        a_ok = (j["p_a"].to_numpy() >= .5).astype(int) == j["y_a"].to_numpy()
        r_ok = (j["p_r"].to_numpy() >= .5).astype(int) == j["y_r"].to_numpy()
        out[ref] = {"dates": int(len(common)), "rows": int(len(j)), "mean_brier_gain_vs_ref": float(diff.mean()),
                    "p_one_sided_arm_better": M.signflip_p(diff), "p_two_sided": E.signflip_two(diff),
                    "mcnemar": E.mcnemar_exact(a_ok, r_ok), "accuracy_diff": float(a_ok.mean() - r_ok.mean())}
        if ref in E.BASELINES:
            praw[ref] = out[ref]["p_two_sided"]
    for ref, v in M.holm(praw).items():
        out[ref]["holm_two_sided_over_six_baselines"] = v
    return out


def main():
    L.register_pools()
    L6.DISPLAY.update(TRIG_DISPLAY)
    L6.SOURCE.update({f: "news" for f in TRIG_DISPLAY})
    d = L.Data(paper=False)
    Pr, info = L6.walk_forward(d)
    import lightgbm

    back = []
    for target, s in info["selections"][ARM].items():
        t = C.qk(target) - 1
        fs, g = s["chosen"].split("x")
        feats = L6.FEATURE_SETS[fs]
        tr, te = d.train(t), d.test(t)
        m = L6.fit_lgbm(tr, feats, g)
        p = m.predict_proba(te[feats].astype(float))[:, 1]
        stored = Pr[(Pr["arm"] == ARM) & (Pr["target_quarter"] == target)].set_index("province_code")["p"]
        for code, v in zip(te["province_code"], p):
            assert abs(v - stored[code]) < 1e-8, (target, code)
        ex = F.explain_rows(m, te.reset_index(drop=True), feats)
        ref = {a: Pr[(Pr["arm"] == a) & (Pr["target_quarter"] == target)].set_index("province_code")["p"].to_dict()
               for a in E.BASELINES + ["ALWAYS_HIGH"]}
        ic = F.info_cutoff(d, t)
        ic["feature_availability"]["trig_*"] = f"news titles published in {C.qs(t)} (trigger classifier shares)"
        back.append({"quarter": target, "mode": "BACKTEST", "lead": 1, "config": s["chosen"], "selection_rule": s["rule"],
                     **ic, "training_rows": int(len(tr)),
                     "provinces": {code: {"province": C.NAMES[code], "p_high": float(v),
                                          "observed_label": "HIGH" if d.label(code, t + 1, t) else "LOW",
                                          "observed_S1": float(d.Sv[(code, t + 1)]),
                                          "persistence_p": ref["B1_PERSISTENCE"][code], **ex[code]}
                                   for code, v in zip(te["province_code"], p)},
                     "baselines_p_high": ref})

    full = Pr[~Pr["arm"].isin(["P45", "F12"])]
    (fs, g), sel = L6.operational_choice(d, full, ARM)
    oc = {"origin": "2026-10-01", "chosen": L6.cfg_name(fs, g), "feature_set": fs, "features": L6.FEATURE_SETS[fs],
          "params": {**L6._BASE, **L6.GRID[g]}, **sel}
    feats = L6.FEATURE_SETS[fs]
    t = L6.OPERATIONAL_T
    tr, te = d.train(t), d.test(t)
    m = L6.fit_lgbm(tr, feats, g)
    p = m.predict_proba(te[feats].astype(float))[:, 1]
    mdir = L.E48 / "models"
    mdir.mkdir(exist_ok=True)
    mpath = mdir / "E48-A1-LGBM_O2026-10-01.txt"
    if mpath.exists():
        raise SystemExit("model artifact exists; refusing to overwrite")
    m.booster_.save_model(str(mpath))
    raw = mpath.read_bytes()
    model_sha = F.sha_bytes(raw)
    (mdir / "ARTIFACT_HASHES.json").write_text(json.dumps({mpath.name: {
        "sha256_at_freeze": model_sha, "sha256_lf_normalized": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()}},
        indent=1), encoding="utf-8")
    ic = F.info_cutoff(d, t)
    ic["feature_availability"]["trig_*"] = f"news titles published in {C.qs(t)} (trigger classifier shares)"
    cfg = {"model_id": MODEL_ID, "version": VERSION, "artifact": mpath.name, "artifact_sha256": model_sha,
           "feature_set": fs, "features": feats, "grid_id": g, "params": {**L6._BASE, **L6.GRID[g]}, "selection": oc,
           "lightgbm_version": lightgbm.__version__, "training_rows": int(len(tr)), "training_HIGH": int(tr["y"].sum()),
           "training_target_quarters": sorted({C.qs(int(x)) for x in tr["target_q"]}),
           "gain_importance": dict(zip(feats, m.booster_.feature_importance("gain").astype(float))),
           "protocol_sha256": "E48 (experiment): E36 frozen procedure + trigger pool; see backend/experiments/e48",
           "evaluation_run": "e48_freeze walk-forward", "inputs": C.inputs_manifest(), **ic,
           "status": "EXPERIMENTAL / NOT VALIDATED (preview)"}
    (mdir / "E48-A1-LGBM_O2026-10-01.json").write_bytes(json.dumps(C.clean(cfg), indent=1).encode())
    ex = F.explain_rows(m, te.reset_index(drop=True), feats)
    arms = L6.fixed_arms(d, t)
    base_fc = {}
    for b in E.BASELINES + ["ALWAYS_HIGH", "B1p_CAL_PERSISTENCE", "CLIMATOLOGY", "PCF21"]:
        if b in L6.POOLS:
            (bfs, bg), _ = L6.operational_choice(d, full, b)
            base_fc[b] = {"config": L6.cfg_name(bfs, bg), "p_high": arms[L6.cfg_name(bfs, bg)]}
        elif b in arms:
            base_fc[b] = {"p_high": arms[b]}
    fc = {"quarter": "2026-Q4", "mode": "FORECAST", "lead": 1, "model_id": MODEL_ID, "version": VERSION,
          "config": oc["chosen"], "artifact_sha256": model_sha, **ic,
          "provinces": {code: {"province": C.NAMES[code], "p_high": float(v), "persistence_p": arms["B1_PERSISTENCE"][code],
                               **ex[code]} for code, v in zip(te["province_code"], p)},
          "baselines": base_fc, "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "scoring": "preview only; not a served forecast"}
    h1 = F.write_frozen(L.E48 / "frozen" / "E48_PROSPECTIVE_2026Q4.json", fc)
    met = {a: E.arm_metrics(Pr[Pr["arm"] == a]) for a in E.BASELINES + [ARM, "ALWAYS_HIGH"]}
    keys = ("n", "correct", "accuracy", "balanced_accuracy", "precision", "recall", "specificity", "f1", "roc_auc",
            "brier", "accuracy_ci95", "HIGH", "LOW")
    metrics_all = {("E36-LGBM" if a == ARM else a): {k: v[k] for k in keys} for a, v in met.items()}
    bundle = {"schema": "e36-bundle/1", "model": cfg, "backtests": back, "forecast": fc,
              "evaluation": {"run": "e48_freeze walk-forward", "dates": info["dates"], "target_75": target_75(met[ARM], met),
                             "metrics_all": metrics_all, "paired_vs_baselines": paired(Pr, ARM),
                             "note": "the proposed model (E48-A1) is stored under the key 'E36-LGBM' that the API reads"},
              "prospective_sha256": h1}
    h2 = F.write_frozen(L.E48 / "frozen" / "E48_SERVING_BUNDLE.json", bundle)
    print("model", oc["chosen"], model_sha[:16], "| prospective", h1[:16], "| bundle", h2[:16],
          "| acc", round(met[ARM]["accuracy"], 4), "brier", round(met[ARM]["brier"], 4))
    for code in C.PROVS:
        v = fc["provinces"][code]
        print(C.NAMES[code], round(v["p_high"], 4), [(x["key"], round(x["contribution"], 3)) for x in v["drivers"][:4]])


if __name__ == "__main__":
    main()
