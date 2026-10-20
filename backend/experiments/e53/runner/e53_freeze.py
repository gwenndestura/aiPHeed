"""E53-A1 freeze, the same process as e48_freeze.py (E36's): the operational model at 2026-10-01, its 2026-Q4 forecast
with exact TreeSHAP, the baselines' forecasts, and the serving bundle (backtests refitted at each origin under the
nested rule, checked against the walk-forward, with TreeSHAP), for scripts/build_record_e36.build().

E53-A1 = E48-A1 inputs (E36's 13 + five trigger proportions) + the five measured condition ranks cond_* (e53_run.py,
strict-history ranks of data quarter F-2), pool "E53-A1", current trailing-median labels, lead 1.

    python -B backend/experiments/e53/runner/e53_freeze.py
Writes backend/experiments/e53/models/E53-A1-LGBM_O2026-10-01.{txt,json} + ARTIFACT_HASHES.json,
backend/experiments/e53/frozen/E53_PROSPECTIVE_2026Q4.json, E53_SERVING_BUNDLE.json (+ .sha256) and
E53_COND_2026Q2.json (the cond_* values used for serving). Refuses to overwrite.
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
import e53_run as X53  # noqa: E402  (Data, build_cond, register; brings in e48_lib / e36_lib)

sys.path.insert(0, str(X53.BACKEND / "experiments" / "e48" / "runner"))
import e48_freeze as F48  # noqa: E402  (target_75, paired, TRIG_DISPLAY; F = e36_freeze)

L, L6, C, np, pd, E = X53.L, X53.L6, X53.C, X53.np, X53.pd, X53.EV
F = F48.F
E53 = X53.E53
L6.guard32.EXP = E53
ARM = "E53-A1"
MODEL_ID, VERSION = "aiPHeed-E53-A1-LGBM", "E53.A1"
COND_DISPLAY = {
    "cond_market": "Measured market pressure: rank of provincial food and rice inflation (PSA CPI) against earlier quarters",
    "cond_climate": "Measured climate stress: rank of rainfall anomaly or storm signal (NASA POWER, NOAA) against earlier quarters",
    "cond_fish": "Measured fisheries decline (proxy): rank of the fall in fish production (PSA) against earlier quarters",
    "cond_employment": "Measured unemployment pressure (national, PSA LFS): rank against earlier quarters",
    "cond_ofw": "Measured fall in real OFW remittances (national, BSP; 2026 provisional): rank against earlier quarters"}


def main():
    X53.register()
    L6.DISPLAY.update({**F48.TRIG_DISPLAY, **COND_DISPLAY})
    L6.SOURCE.update({f: "news" for f in F48.TRIG_DISPLAY} | {f: "government" for f in COND_DISPLAY})
    d = X53.Data(X53.build_cond())
    Pr, info = L6.walk_forward(d)
    import lightgbm

    def avail(ic, t):
        ic["feature_availability"]["trig_*"] = f"news titles published in {C.qs(t)} (trigger classifier shares)"
        ic["feature_availability"]["cond_*"] = (f"measured conditions of {C.qs(t - 1)} ranked against 2021-Q1..{C.qs(t - 2)} "
                                                "(PSA CPI, NASA POWER/NOAA, PSA fisheries, PSA LFS national, BSP)")
        return ic

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
        ic = avail(F.info_cutoff(d, t), t)
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
    mdir, fdir = E53 / "models", E53 / "frozen"
    mdir.mkdir(exist_ok=True)
    fdir.mkdir(exist_ok=True)
    mpath = mdir / "E53-A1-LGBM_O2026-10-01.txt"
    if mpath.exists():
        raise SystemExit("model artifact exists; refusing to overwrite")
    m.booster_.save_model(str(mpath))
    raw = mpath.read_bytes()
    model_sha = F.sha_bytes(raw)
    (mdir / "ARTIFACT_HASHES.json").write_text(json.dumps({mpath.name: {
        "sha256_at_freeze": model_sha, "sha256_lf_normalized": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()}},
        indent=1), encoding="utf-8")
    ic = avail(F.info_cutoff(d, t), t)
    cfg = {"model_id": MODEL_ID, "version": VERSION, "artifact": mpath.name, "artifact_sha256": model_sha,
           "feature_set": fs, "features": feats, "grid_id": g, "params": {**L6._BASE, **L6.GRID[g]}, "selection": oc,
           "lightgbm_version": lightgbm.__version__, "training_rows": int(len(tr)), "training_HIGH": int(tr["y"].sum()),
           "training_target_quarters": sorted({C.qs(int(x)) for x in tr["target_q"]}),
           "gain_importance": dict(zip(feats, m.booster_.feature_importance("gain").astype(float))),
           "split_importance": dict(zip(feats, m.booster_.feature_importance("split").astype(int).tolist())),
           "protocol_sha256": "E53 (experiment): E36 frozen procedure + trigger and measured-condition inputs; see backend/experiments/e53",
           "evaluation_run": "e53_freeze walk-forward", "inputs": C.inputs_manifest(), **ic,
           "status": "EXPERIMENTAL / NOT VALIDATED (preview)"}
    (mdir / "E53-A1-LGBM_O2026-10-01.json").write_bytes(json.dumps(C.clean(cfg), indent=1).encode())
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
    h1 = F.write_frozen(fdir / "E53_PROSPECTIVE_2026Q4.json", fc)
    met = {a: E.arm_metrics(Pr[Pr["arm"] == a]) for a in E.BASELINES + [ARM, "ALWAYS_HIGH"]}
    keys = ("n", "correct", "accuracy", "balanced_accuracy", "precision", "recall", "specificity", "f1", "roc_auc",
            "brier", "accuracy_ci95", "HIGH", "LOW")
    metrics_all = {("E36-LGBM" if a == ARM else a): {k: v[k] for k in keys} for a, v in met.items()}
    bundle = {"schema": "e36-bundle/1", "model": cfg, "backtests": back, "forecast": fc,
              "evaluation": {"run": "e53_freeze walk-forward", "dates": info["dates"],
                             "target_75": F48.target_75(met[ARM], met), "metrics_all": metrics_all,
                             "paired_vs_baselines": F48.paired(Pr, ARM),
                             "note": "the proposed model (E53-A1) is stored under the key 'E36-LGBM' that the API reads"},
              "prospective_sha256": h1}
    h2 = F.write_frozen(fdir / "E53_SERVING_BUNDLE.json", bundle)
    cond = {"data_quarter": C.qs(t - 1), "history": f"2021-Q1..{C.qs(t - 2)} (strictly before the data quarter)",
            "rule": "rank = 100 * #{earlier values < x} / n; market = mean(rank D, rank rice CPI YoY); climate = "
                    "max(rank |rain anomaly|, rank storm signal); fish = rank of production decline YoY (proxy); "
                    "employment = mean(rank u, rank YoY change) national; ofw = rank of fall in real peso remittances "
                    "(national; 2026 provisional)",
            "values": {C.NAMES[c]: {k: (None if v != v else float(v)) for k, v in r.items()}
                       for c, r in te.set_index("province_code")[X53.COND].iterrows()}}
    (fdir / "E53_COND_2026Q2.json").write_text(json.dumps(cond, indent=1), encoding="utf-8")
    print("model", oc["chosen"], model_sha[:16], "| prospective", h1[:16], "| bundle", h2[:16],
          "| acc", round(met[ARM]["accuracy"], 4), "brier", round(met[ARM]["brier"], 4))
    for code in C.PROVS:
        v = fc["provinces"][code]
        print(C.NAMES[code], round(v["p_high"], 4), [(x["key"], round(x["contribution"], 3)) for x in v["drivers"][:4]])


if __name__ == "__main__":
    main()
