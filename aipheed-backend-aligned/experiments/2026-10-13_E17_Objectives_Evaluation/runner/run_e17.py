"""E17 runner: Objectives 2 and 4 under EVALUATION_PROTOCOL.md (frozen; hashes checked first).
Usage: python -B runner/run_e17.py [--deliverables]"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "21")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e17_lib as L  # noqa: E402
import loaders as Ld  # noqa: E402

EXP = guard.EXP
THR_PRIMARY, THR_SECONDARY = 14.6, 10.84335
KS = range(1, 9)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jd(o):
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    raise TypeError(type(o))


def check_frozen():
    lines = (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").splitlines()
    for ln in lines:
        parts = ln.split()
        if len(parts) == 2 and len(parts[0]) == 64 and sha(EXP / parts[1]) != parts[0]:
            raise SystemExit(f"E17: {parts[1]} differs from its frozen hash; stop.")


def run_setting(f, comp, rounds, features, thr, rule, include_poverty, ks, perturb=True):
    X = L.build_frame(f, rounds, features, include_poverty)
    cols = L.NLP + L.gov_columns(features, include_poverty) + ["sws_hunger"]
    lab = L.label_table(comp, thr)
    rows, folds, skipped, pert = [], [], {}, {}
    for k in ks:
        for t in range(L.qk(L.FIRST_Q), L.qk(L.LAST_Q) - k + 1):
            train, test = L.fold_data(X, lab, rounds, k, t, rule)
            if test.empty:
                continue
            tq = test["target_quarter"].iloc[0]
            ntq = int(train["target_quarter"].nunique())
            if ntq < L.MIN_TRAIN_QUARTERS:
                skipped.setdefault(k, []).append(f"{tq} ({ntq} training quarters)")
                continue
            te, res, meta = L.predict_fold(train, test, cols, lab, rounds, t)
            if perturb:
                pert[f"k{k}_{tq}"] = perturbation_ok(f, comp, rounds, features, thr, rule, include_poverty, k, t, res)
            folds.append({"k": k, "feature_quarter": L.qs(t), "target_quarter": tq, **meta})
            for i, r in enumerate(te.itertuples()):
                for arm in L.ARMS:
                    v = res[arm][i]
                    rows.append({"k": k, "feature_quarter": L.qs(t), "target_quarter": tq, "province_code": r.province_code,
                                 "arm": arm, "score": float(v), "pred": int(v >= 0.5)})
    return pd.DataFrame(rows), pd.DataFrame(folds), skipped, pert


def perturbation_ok(f, comp, rounds, features, thr, rule, include_poverty, k, t, res) -> bool:
    """Overwrite everything not known at origin start(t+1) and confirm identical fold predictions (strict rule)."""
    if rule != "strict":
        return True
    origin = L.qstart(L.qs(t + 1))
    f2 = f.copy()
    feat = [c for c in f2.columns if c not in ("province_code", "quarter")]
    later = f2["quarter"].map(L.qk) > t
    f2.loc[later, feat] = 999.0
    gov = L.gov_columns(features, include_poverty)
    f2.loc[f2["quarter"].map(L.qk) == t, [c for c in gov if c in f2.columns]] = 999.0
    r2 = rounds.copy()
    r2.loc[r2["published"] >= origin, "H"] = 999.0
    c2 = comp.copy()
    unpub = [q for q in c2["quarter"].unique() if not L.label_published(rounds, q, t)]
    c2.loc[c2["quarter"].isin(unpub), "S1"] = 999.0 * np.where(np.arange(c2["quarter"].isin(unpub).sum()) % 2, 1, -1)
    X2 = L.build_frame(f2, r2, features, include_poverty)
    cols = L.NLP + L.gov_columns(features, include_poverty) + ["sws_hunger"]
    lab2 = L.label_table(c2, thr)
    train, test = L.fold_data(X2, lab2, r2, k, t, rule)
    _, res2, _ = L.predict_fold(train, test, cols, lab2, r2, t)
    return all(np.array_equal(res[a], res2[a], equal_nan=True) for a in L.ARMS)


def evaluate(pred: pd.DataFrame, lab: pd.DataFrame):
    d = pred.merge(lab[["province_code", "quarter", "y"]].rename(columns={"quarter": "target_quarter"}),
                   on=["province_code", "target_quarter"], how="left")
    assert d["y"].notna().all()
    d["correct"] = (d["pred"] == d["y"]).astype(int)
    hz, pq, cm, cmp = [], [], [], []
    for k, dk in d.groupby("k"):
        nq = dk["target_quarter"].nunique()
        for arm, da in dk.groupby("arm"):
            hard = arm in ("B1_persistence", "REF_majority")
            m = L.cls_metrics(da["y"], da["pred"], None if hard else da["score"])
            fold_acc = da.groupby("target_quarter")["correct"].mean()
            hz.append({"k": k, "arm": arm, "test_quarters": int(nq), "test_rows": m["n"], "HIGH": m["HIGH"], "LOW": m["LOW"],
                       "mean_fold_accuracy": float(fold_acc.mean()), **{x: m[x] for x in
                       ("accuracy", "precision_HIGH", "recall_HIGH", "F1_HIGH", "F1_weighted", "recall_LOW",
                        "balanced_accuracy", "ROC_AUC", "PR_AUC")},
                       "auc_note": "degenerate (hard 0/1 score)" if hard else ("not computable (one class)" if m["ROC_AUC"] is None else ""),
                       "reaches_0.75_mean_fold_accuracy": bool(fold_acc.mean() >= 0.75)})
            cm.append({"k": k, "arm": arm, "TP": m["TP"], "FP": m["FP"], "FN": m["FN"], "TN": m["TN"]})
            for q, g in da.groupby("target_quarter"):
                pq.append({"k": k, "arm": arm, "target_quarter": q, "rows": len(g), "HIGH": int(g["y"].sum()),
                           "pred_HIGH": int(g["pred"].sum()), "correct": int(g["correct"].sum()),
                           "accuracy": float(g["correct"].mean())})
        mm = dk[dk["arm"] == "M_lgbm"].sort_values(["target_quarter", "province_code"])
        for arm in [a for a in L.ARMS if a != "M_lgbm"]:
            bb = dk[dk["arm"] == arm].sort_values(["target_quarter", "province_code"])
            bt = L.boot_acc_diff(mm["correct"].to_numpy(), bb["correct"].to_numpy(), mm["target_quarter"].to_numpy())
            qa = mm.groupby("target_quarter")["correct"].mean() - bb.groupby("target_quarter")["correct"].mean()
            cmp.append({"k": k, "baseline": arm, "acc_diff_M_minus_baseline": bt["diff"], "ci_low": bt["ci_low"],
                        "ci_high": bt["ci_high"], "quarters": bt["quarters"], "quarters_M_better": int((qa > 0).sum()),
                        "quarters_tied": int((qa == 0).sum())})
    return d, pd.DataFrame(hz), pd.DataFrame(pq), pd.DataFrame(cm), pd.DataFrame(cmp)


def findings(hz: pd.DataFrame, cmp: pd.DataFrame) -> pd.DataFrame:
    out = []
    for k, h in hz.groupby("k"):
        h = h.set_index("arm")
        m = h.loc["M_lgbm"]
        nq = int(m["test_quarters"])
        bases = [a for a in h.index if a != "M_lgbm"]
        strongest = max(bases, key=lambda a: h.loc[a, "accuracy"])
        c = cmp[(cmp["k"] == k) & (cmp["baseline"] == strongest)].iloc[0]
        ba_ok = all((m["balanced_accuracy"] is not None and h.loc[a, "balanced_accuracy"] is not None
                     and m["balanced_accuracy"] >= h.loc[a, "balanced_accuracy"]) or h.loc[a, "balanced_accuracy"] is None
                    for a in bases) and m["balanced_accuracy"] is not None
        acc_ok = all(m["accuracy"] >= h.loc[a, "accuracy"] for a in bases)
        f2 = bool(nq >= 5 and acc_ok and ba_ok and c["ci_low"] > 0)
        out.append({"k": k, "test_quarters": nq, "test_rows": int(m["test_rows"]), "HIGH": int(m["HIGH"]), "LOW": int(m["LOW"]),
                    "M_mean_fold_accuracy": float(m["mean_fold_accuracy"]), "M_accuracy": float(m["accuracy"]),
                    "M_balanced_accuracy": m["balanced_accuracy"], "M_F1_HIGH": m["F1_HIGH"], "M_ROC_AUC": m["ROC_AUC"],
                    "strongest_baseline": strongest, "strongest_baseline_accuracy": float(h.loc[strongest, "accuracy"]),
                    "acc_diff_vs_strongest": float(c["acc_diff_M_minus_baseline"]),
                    "ci": f"[{c['ci_low']:.3f}, {c['ci_high']:.3f}]",
                    "F1_reaches_0.75_info_only": bool(m["mean_fold_accuracy"] >= 0.75),
                    "F2_outperforms_baselines": f2,
                    "status": ("insufficient evidence (<5 test quarters)" if nq < 5 else
                               ("outperforms baselines (F2)" if f2 else "does not outperform baselines")),
                    "F3_reliability": "not determinable: Chapter I defines no reliability criterion"})
    return pd.DataFrame(out)


def write_csv(df, p):
    df.to_csv(p, index=False, lineterminator="\n", float_format="%.6g")


def main(deliverables: bool):
    check_frozen()
    started = datetime.now(timezone.utc)
    out = EXP / "runs" / started.strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True)
    allow_start = guard.verify_allowlist()
    gov = Ld.load_governing()
    f = Ld.load_features(gov)
    comp = Ld.load_components()
    rounds = Ld.load_rounds()
    features = gov["feature_set"]["candidates_section_3_3_2_6"] + ["cpi_dev"]
    assert len(features) == 46 and gov["target"].startswith("label_stress (Eq. 3; HIGH if stress_score > global median 14.6)")

    settings = {"primary": (THR_PRIMARY, "strict", False, KS), "S-T0": (THR_SECONDARY, "strict", False, KS),
                "R0": (THR_PRIMARY, "r0", True, [1])}
    preds, foldtabs, skipped, perts = {}, {}, {}, {}
    for name, (thr, rule, pov, ks) in settings.items():
        p, fo, sk, pe = run_setting(f, comp, rounds, features, thr, rule, pov, ks)
        preds[name], foldtabs[name], skipped[name], perts[name] = p.assign(setting=name), fo.assign(setting=name), sk, pe
        if pe and not all(pe.values()):
            raise SystemExit(f"E17: future-perturbation check failed in {name}: {pe}")
    P = pd.concat(preds.values(), ignore_index=True)
    write_csv(P, out / "predictions.csv")
    seal = {"predictions_sha256": sha(out / "predictions.csv"), "sealed_utc": datetime.now(timezone.utc).isoformat(),
            "note": "Sealed before labels were joined; all 2021-2025 labels were seen in earlier experiments."}
    (out / "SEAL.json").write_text(json.dumps(seal, indent=1), encoding="utf-8", newline="\n")

    allres = {}
    tables = {"horizon": [], "per_quarter": [], "confusion": [], "comparison": [], "findings": []}
    for name, (thr, rule, pov, ks) in settings.items():
        lab = L.label_table(comp, thr)
        d, hz, pq, cm, cmp = evaluate(preds[name], lab)
        fd = findings(hz, cmp)
        write_csv(d, out / f"scored_rows_{name}.csv")
        for key, df in zip(["horizon", "per_quarter", "confusion", "comparison", "findings"], [hz, pq, cm, cmp, fd]):
            tables[key].append(df.assign(setting=name, threshold=thr, train_rule=rule, poverty_included=pov))
        allres[name] = {"threshold": thr, "train_rule": rule, "poverty_included": pov, "skipped": skipped[name],
                        "folds": foldtabs[name].to_dict("records"), "perturbation_checks": perts[name],
                        "findings": fd.to_dict("records")}
    T = {k: pd.concat(v, ignore_index=True) for k, v in tables.items()}
    for k, df in T.items():
        write_csv(df, out / f"{k}_results.csv")
    (out / "metrics.json").write_text(json.dumps(allres, indent=1, default=jd), encoding="utf-8", newline="\n")
    if deliverables:
        write_csv(T["findings"], EXP / "HORIZON_RESULTS.csv")
        write_csv(T["horizon"], EXP / "HORIZON_ARM_METRICS.csv")
        write_csv(T["comparison"], EXP / "BASELINE_COMPARISON.csv")
        write_csv(T["confusion"], EXP / "CONFUSION_MATRICES.csv")
        write_csv(T["per_quarter"], EXP / "PER_QUARTER_RESULTS.csv")
    manifest = {"started_utc": started.isoformat(), "finished_utc": datetime.now(timezone.utc).isoformat(),
                "protocol_hashes": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8"),
                "allowlist_sha256_start": allow_start, "allowlist_sha256_end": guard.verify_allowlist(),
                "code_sha256": {p.name: sha(p) for p in sorted((EXP / "runner").glob("*.py"))},
                "outputs_sha256": {p.name: sha(p) for p in sorted(out.glob("*")) if p.name != "manifest.json"},
                "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                                "lightgbm": __import__("lightgbm").__version__, "sklearn": __import__("sklearn").__version__},
                "access_log": guard.ACCESS_LOG}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=jd), encoding="utf-8", newline="\n")
    print(out)


if __name__ == "__main__":
    main("--deliverables" in sys.argv)
