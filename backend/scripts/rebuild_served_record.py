"""
scripts/rebuild_served_record.py
--------------------------------
Rule 1 (Quarter Self-Update, p.48): rebuild the served E49-family record for an origin. The steps are the ones that
produced data/e49/e49_record.json, run in one pass:

  1. walk-forward + freeze (backend/experiments/e48/runner/e48_freeze.py): E48-A1 inputs, pool E48-T5, nested rule,
     seed 36; backtests refitted at each origin with exact TreeSHAP; the operational model at the origin and its
     one-quarter-ahead forecast;
  2. E49-C2 calibration (backend/experiments/e49/runner/e49_run.py `calibrated`, "shrink"): p' = a*p + (1-a)*base
     rate, a fitted on eligible earlier dates only;
  3. the record builder (scripts/build_record_e36.build and write_pdf, as backend/experiments/e49/runner/
     build_record_e49.py uses it), with the calibrated probabilities and the recomputed evaluation.

Writes ONLY to data/rebuild/<YYYYMMDD>/ (or --out): e49_record.json, the PDF, model/ (artifact, config, frozen
bundle, prospective forecast, E49_C2_calibration.json). It never writes data/e49/ (or any other served record),
never calls build_record_e36.main (which also copies a record into frontend/public), and serves nothing: promoting a
rebuilt record is a separate, human decision.

    python -B scripts/rebuild_served_record.py                       (from backend/; origin = the served one)
    python -B scripts/rebuild_served_record.py --origin-quarter 2026-Q4 --dry-run

--origin-quarter Q: the last complete quarter (origin = first day of the next quarter; forecast target = Q+1). A new
quarter needs its inputs (SWS round, CPI months, news) in the experiment data sources first; otherwise its dates
drop out by the existing rules. Known limits: the lead-2 (next-quarter, E38) row and its model are carried from
their frozen files, not rebuilt; some builder sentences name the 2026-Q4 test.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
for p in (BACKEND, BACKEND / "scripts", BACKEND / "experiments" / "e48" / "runner",
          BACKEND / "experiments" / "e49" / "runner"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

REBUILD_ROOT = BACKEND / "data" / "rebuild"
ARM = "E48-T5"
SERVED_DIRS = ("data/e36", "data/e48", "data/e49", "data/e53")


def _libs():
    import build_record_e36 as B
    import build_record_e49 as BE      # evaluation(), NOTE (the E49 build's own helpers)
    import e48_freeze as FZ            # TRIG_DISPLAY, target_75, paired (the E48 freeze's own helpers)
    import e49_run as R                # calibrated (the E49-C2 procedure)

    return B, BE, FZ, R, FZ.L, FZ.L6, FZ.C, FZ.E, FZ.F


def rebuild(origin_quarter: str | None = None, out_dir: Path | str | None = None, dry_run: bool = False,
            stamp: str | None = None) -> dict:
    """Run the rebuild. Returns {"out_dir", "record" (dict), "probabilities" {(quarter, code): p}, "content_sha256",
    "dry_run", ...}. With dry_run, everything is written to a temporary directory that is deleted afterwards."""
    B, BE, FZ, R, L, L6, C, E, F = _libs()
    saved = {"OPERATIONAL_T": L6.OPERATIONAL_T, "LAST_TARGET": L6.LAST_TARGET, "EXP": L6.guard32.EXP,
             "B": {k: getattr(B, k) for k in ("BUNDLE", "PROSPECTIVE", "MODEL_TXT", "MODEL_CFG", "frozen_ok",
                                              "DRIVER_METHOD")}}
    tmp = tempfile.mkdtemp(prefix="aipheed_rebuild_dry_") if dry_run else None
    stamp = stamp or datetime.now(timezone.utc).strftime("%Y%m%d")
    out = Path(tmp) if dry_run else Path(out_dir) if out_dir else REBUILD_ROOT / stamp
    if not dry_run:
        rel = out.resolve()
        if any(rel == (BACKEND / s).resolve() or (BACKEND / s).resolve() in rel.parents for s in SERVED_DIRS):
            raise SystemExit(f"refusing to write into a served record directory: {out}")
        if out.exists() and any(out.iterdir()):
            raise SystemExit(f"{out} exists and is not empty; refusing to overwrite")
    try:
        L6.guard32.EXP = out
        t = C.qk(origin_quarter) if origin_quarter else saved["OPERATIONAL_T"]
        L6.OPERATIONAL_T, L6.LAST_TARGET = t, max(saved["LAST_TARGET"], t)
        bundle_path, prosp_path, model_txt, cal = _freeze_and_calibrate(B, BE, FZ, R, L, L6, C, E, F, t, out)
        rec = _build(B, BE, out, bundle_path, prosp_path, model_txt, cal)
        probs = {(q["quarter"], code): v["p_high"] for q in rec["quarters"] if q.get("lead", 1) == 1
                 for code, v in q["provinces"].items()}
        result = {"out_dir": str(out), "dry_run": dry_run, "origin": str(L.L6.origin(t).date()),
                  "forecast_quarter": C.qs(t + 1), "record": rec, "probabilities": probs,
                  "content_sha256": rec["content_sha256"], "files": sorted(str(p.relative_to(out))
                                                                         for p in out.rglob("*") if p.is_file())}
        return result
    finally:
        L6.OPERATIONAL_T, L6.LAST_TARGET, L6.guard32.EXP = saved["OPERATIONAL_T"], saved["LAST_TARGET"], saved["EXP"]
        for k, v in saved["B"].items():
            setattr(B, k, v)
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def _freeze_and_calibrate(B, BE, FZ, R, L, L6, C, E, F, t, out):
    """e48_freeze.main at origin O(t), writing under `out`, then the E49-C2 probabilities (e49_run.main's C2 arm)."""
    import lightgbm

    L.register_pools()
    L6.DISPLAY.update(FZ.TRIG_DISPLAY)
    L6.SOURCE.update({f: "news" for f in FZ.TRIG_DISPLAY})
    d = L.Data(paper=False)
    Pr, info = L6.walk_forward(d)
    origin = str(L6.origin(t).date())
    target = C.qs(t + 1)

    back = []
    for tq, s in info["selections"][ARM].items():
        tb = C.qk(tq) - 1
        fs, g = s["chosen"].split("x")
        feats = L6.FEATURE_SETS[fs]
        tr, te = d.train(tb), d.test(tb)
        m = L6.fit_lgbm(tr, feats, g)
        p = m.predict_proba(te[feats].astype(float))[:, 1]
        stored = Pr[(Pr["arm"] == ARM) & (Pr["target_quarter"] == tq)].set_index("province_code")["p"]
        for code, v in zip(te["province_code"], p):
            assert abs(v - stored[code]) < 1e-8, (tq, code)
        ex = F.explain_rows(m, te.reset_index(drop=True), feats)
        ref = {a: Pr[(Pr["arm"] == a) & (Pr["target_quarter"] == tq)].set_index("province_code")["p"].to_dict()
               for a in E.BASELINES + ["ALWAYS_HIGH"]}
        ic = F.info_cutoff(d, tb)
        ic["feature_availability"]["trig_*"] = f"news titles published in {C.qs(tb)} (trigger classifier shares)"
        back.append({"quarter": tq, "mode": "BACKTEST", "lead": 1, "config": s["chosen"], "selection_rule": s["rule"],
                     **ic, "training_rows": int(len(tr)),
                     "provinces": {code: {"province": C.NAMES[code], "p_high": float(v),
                                          "observed_label": "HIGH" if d.label(code, tb + 1, tb) else "LOW",
                                          "observed_S1": float(d.Sv[(code, tb + 1)]),
                                          "persistence_p": ref["B1_PERSISTENCE"][code], **ex[code]}
                                   for code, v in zip(te["province_code"], p)},
                     "baselines_p_high": ref})

    full = Pr[~Pr["arm"].isin(["P45", "F12"])]
    (fs, g), sel = L6.operational_choice(d, full, ARM)
    feats = L6.FEATURE_SETS[fs]
    oc = {"origin": origin, "chosen": L6.cfg_name(fs, g), "feature_set": fs, "features": feats,
          "params": {**L6._BASE, **L6.GRID[g]}, **sel}
    tr, te = d.train(t), d.test(t)
    m = L6.fit_lgbm(tr, feats, g)
    p = m.predict_proba(te[feats].astype(float))[:, 1]
    mdir = out / "model"
    mdir.mkdir(parents=True, exist_ok=True)
    mpath = mdir / f"E48-A1-LGBM_O{origin}.txt"
    m.booster_.save_model(str(mpath))
    raw = mpath.read_bytes()
    model_sha = F.sha_bytes(raw)
    (mdir / "ARTIFACT_HASHES.json").write_text(json.dumps({mpath.name: {
        "sha256_at_freeze": model_sha, "sha256_lf_normalized": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()}},
        indent=1), encoding="utf-8")
    ic = F.info_cutoff(d, t)
    ic["feature_availability"]["trig_*"] = f"news titles published in {C.qs(t)} (trigger classifier shares)"
    cfg = {"model_id": FZ.MODEL_ID, "version": FZ.VERSION, "artifact": mpath.name, "artifact_sha256": model_sha,
           "feature_set": fs, "features": feats, "grid_id": g, "params": {**L6._BASE, **L6.GRID[g]}, "selection": oc,
           "lightgbm_version": lightgbm.__version__, "training_rows": int(len(tr)), "training_HIGH": int(tr["y"].sum()),
           "training_target_quarters": sorted({C.qs(int(x)) for x in tr["target_q"]}),
           "gain_importance": dict(zip(feats, m.booster_.feature_importance("gain").astype(float))),
           "protocol_sha256": "rebuild (scripts/rebuild_served_record.py): E48 freeze procedure",
           "evaluation_run": "rebuild walk-forward", "inputs": C.inputs_manifest(), **ic,
           "status": "EXPERIMENTAL / NOT VALIDATED (rebuild; not served)"}
    mcfg = mdir / f"E48-A1-LGBM_O{origin}.json"
    mcfg.write_bytes(json.dumps(C.clean(cfg), indent=1).encode())
    ex = F.explain_rows(m, te.reset_index(drop=True), feats)
    arms = L6.fixed_arms(d, t)
    base_fc = {}
    for b in E.BASELINES + ["ALWAYS_HIGH", "B1p_CAL_PERSISTENCE", "CLIMATOLOGY", "PCF21"]:
        if b in L6.POOLS:
            (bfs, bg), _ = L6.operational_choice(d, full, b)
            base_fc[b] = {"config": L6.cfg_name(bfs, bg), "p_high": arms[L6.cfg_name(bfs, bg)]}
        elif b in arms:
            base_fc[b] = {"p_high": arms[b]}
    fc = {"quarter": target, "mode": "FORECAST", "lead": 1, "model_id": FZ.MODEL_ID, "version": FZ.VERSION,
          "config": oc["chosen"], "artifact_sha256": model_sha, **ic,
          "provinces": {code: {"province": C.NAMES[code], "p_high": float(v), "persistence_p": arms["B1_PERSISTENCE"][code],
                               **ex[code]} for code, v in zip(te["province_code"], p)},
          "baselines": base_fc, "frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "scoring": "rebuild; not a served forecast"}
    prosp = mdir / f"E48_PROSPECTIVE_{target.replace('-', '')}.json"
    h1 = F.write_frozen(prosp, fc)
    met = {a: E.arm_metrics(Pr[Pr["arm"] == a]) for a in E.BASELINES + [ARM, "ALWAYS_HIGH"]}
    keys = ("n", "correct", "accuracy", "balanced_accuracy", "precision", "recall", "specificity", "f1", "roc_auc",
            "brier", "accuracy_ci95", "HIGH", "LOW")
    bundle = {"schema": "e36-bundle/1", "model": cfg, "backtests": back, "forecast": fc,
              "evaluation": {"run": "rebuild walk-forward", "dates": info["dates"],
                             "target_75": FZ.target_75(met[ARM], met),
                             "metrics_all": {("E36-LGBM" if a == ARM else a): {k: v[k] for k in keys}
                                             for a, v in met.items()},
                             "paired_vs_baselines": FZ.paired(Pr, ARM),
                             "note": "the proposed model (E48-A1) is stored under the key 'E36-LGBM' that the API reads"},
              "prospective_sha256": h1}
    bpath = mdir / "E48_SERVING_BUNDLE.json"
    F.write_frozen(bpath, bundle)

    # ---- E49-C2 (e49_run.main, arm C2)
    dates = [C.qk(q) - 1 for q in info["dates"]]
    labels = {tj: {c: int(d.label(c, tj + 1, tj)) for c in L.PROVS} for tj in dates}
    base = {tj: float((d.train(tj)["y"].sum() + 1) / (len(d.train(tj)) + 2)) for tj in dates + [t]}
    prior_of = {tj: L6.eligible_prior_dates(d, tj, dates) for tj in dates + [t]}
    rawp = {tj: {c: float(Pr[(Pr["arm"] == ARM) & (Pr["t"] == C.qs(tj))].set_index("province_code")["p"][c])
                 for c in L.PROVS} for tj in dates}
    rawp[t] = {c: float(fc["provinces"][c]["p_high"]) for c in L.PROVS}
    calp, fb, pa = R.calibrated(rawp, {**labels, t: {c: 0 for c in L.PROVS}}, base, prior_of, "shrink")
    cal = {(C.qs(tj + 1), c): calp[tj][c] for tj in dates + [t] for c in L.PROVS}
    (mdir / "E49_C2_calibration.json").write_text(json.dumps(
        {"source": "scripts/rebuild_served_record.py", "params_by_target_quarter": {C.qs(k + 1): v for k, v in pa.items()},
         "fallback_to_raw": [C.qs(k + 1) for k in fb if k != t], "note": BE.NOTE}, indent=1), encoding="utf-8")
    return bpath, prosp, mpath, cal


def _build(B, BE, out, bundle_path, prosp_path, model_txt, cal) -> dict:
    """build_record_e49.main's record step on the rebuilt bundle (record into `out` only)."""
    from app.quarterly import self_description as SD

    B.BUNDLE, B.PROSPECTIVE, B.MODEL_TXT, B.MODEL_CFG = bundle_path, prosp_path, model_txt, model_txt.with_suffix(".json")
    original = B.frozen_ok
    replaced = []

    def frozen_ok(p):
        obj = original(p)                                  # the hash check still runs
        if Path(p) == B.BUNDLE:
            obj = copy.deepcopy(obj)
            for q in obj["backtests"] + [obj["forecast"]]:
                for code, v in q["provinces"].items():
                    v["p_high_uncalibrated"] = v["p_high"]
                    v["p_high"] = cal[(q["quarter"], code)]
                    replaced.append((q["quarter"], code))
            obj["evaluation"] = BE.evaluation(obj)
        return obj

    B.frozen_ok = frozen_ok
    B.DRIVER_METHOD = B.DRIVER_METHOD + ". " + BE.NOTE
    rec = B.build()
    se = rec["served_engine"]
    se.update({"name": "aiPHeed-E49-C2 (E48-A1 LightGBM + shrinkage calibration)", "version": "E48.A1+E49.C2",
               "file": "data/e49/model/" + model_txt.name})
    se.update({k: v for k, v in SD.compose(rec, "e49").items() if k in ("why_served", "evidence_status")})
    se["rebuild"] = {"script": "scripts/rebuild_served_record.py", "probabilities_replaced": len(replaced),
                     "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "served": False}
    rows = {r["key"]: r for r in rec["validation"]["model_evaluation"]["rows"]}
    me, ah, pe = rows["E36-LGBM"], rows["ALWAYS_HIGH"], rows["B1_PERSISTENCE"]
    lim = [i for i, x in enumerate(rec["limitations"]) if x.startswith("One-quarter-ahead accuracy is")]
    if len(lim) == 1:                                       # the builder's sentence names E36's figures; restate
        lo = me["accuracy_ci95"][0]
        rec["limitations"][lim[0]] = (
            f"One-quarter-ahead accuracy is {me['accuracy_lead1']:.3f} on {me['n']} development estimates, "
            f"{'above' if me['accuracy_lead1'] > ah['accuracy_lead1'] else 'not above'} always-HIGH "
            f"({ah['accuracy_lead1']:.3f}) and {'below' if me['accuracy_lead1'] < pe['accuracy_lead1'] else 'not below'} "
            f"persistence ({pe['accuracy_lead1']:.3f}). The 75% target is "
            f"{'demonstrated' if lo >= 0.75 else 'met as a point estimate but not demonstrated'} (95% interval lower "
            f"bound {lo:.3f}). No baseline is beaten significantly.")
    rec.pop("content_sha256", None)
    rec = B._clean(rec)
    rec["content_sha256"] = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    blob = json.dumps(rec, indent=1, ensure_ascii=False, default=str, allow_nan=False).encode("utf-8")
    (out / "e49_record.json").write_bytes(blob)
    B.write_pdf(rec, out / "aiPHeed_E49_assessment_report.pdf")
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--origin-quarter", default=None, help="last complete quarter (default: the served origin's)")
    ap.add_argument("--out", default=None, help="output directory (default data/rebuild/<YYYYMMDD>)")
    ap.add_argument("--dry-run", action="store_true", help="build in a temporary directory and delete it")
    a = ap.parse_args(argv)
    import os

    os.chdir(BACKEND)
    res = rebuild(a.origin_quarter, a.out, dry_run=a.dry_run)
    print(json.dumps({k: res[k] for k in ("out_dir", "dry_run", "origin", "forecast_quarter", "content_sha256", "files")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
