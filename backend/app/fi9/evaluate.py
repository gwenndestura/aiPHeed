"""FI9 locked Lead-1 walk-forward: every baseline (FI7 configurations, re-run for reproducibility), the five-domain
and news ablation, numeric level forecasts, calibration, label uncertainty, split and sawtooth checks, selection.

    python -m app.fi9.evaluate run        # refuses to run unless the protocol lock matches (app.fi9.protocol)

Writes data/fi9/out/lead1_predictions.csv (one row per configuration x target quarter, with the training cutoff of
each forecast) and lead1_evaluation.json. Nothing is tuned here.
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from app.fi5.target import qindex
from app.fi6.news_model import NEWSA
from app.fi7 import models as M
from app.fi7.design import Designer
from app.fi7.experiments import EVAL_FIRST, FINAL_SPECS, REF, WORLD, alternating_quarters, boot_delta
from app.fi9 import OUT
from app.fi9.protocol import PROTOCOL, check

LGBM = "LightGBM (proposed, FI7)"
PERSIST, DAMPED, CLIM = "Naive persistence (latest reading)", "Damped persistence (statistical)", "Always LOW (reference)"
DOMAIN_GOV = {"market": ["cpi_food_yoy", "cpi_rice_yoy", "palay_yoy", *WORLD], "climate": ["rain_anom_3m", "tc_exposure_q", "oni"],
              "employment": ["unemp_rate", "unemp_yoy"], "remittance": ["remit_yoy"], "poverty": ["poverty_inc"]}
FULL = REF + WORLD
ABLATION = {f"LightGBM without {d}": [c for c in FULL if c not in cols] for d, cols in DOMAIN_GOV.items()}
ABLATION["LightGBM without news/NLP"] = [c for c in FULL if c not in NEWSA]
CONFIGS = {**{k: (v[1], v[2]) for k, v in FINAL_SPECS.items()}, **{k: ("delta_lgbm_tau", f) for k, f in ABLATION.items()}}
ERAS = [("2010-2015", 2010, 2015), ("2016-2020", 2016, 2020), ("2021-2026", 2021, 2026)]


def _level(m, X):
    """Numeric hunger forecast (pp) where the model has one; persistence = the latest reading."""
    for obj in (m, getattr(m, "inner", None)):
        if obj is not None and hasattr(obj, "predict_level"):
            return float(obj.predict_level(X)[0])
        if obj is not None and hasattr(obj, "predict_delta"):
            return float(X["hunger_last"].iloc[0] + obj.predict_delta(X)[0])
    return float(X["hunger_last"].iloc[0]) if type(m).__name__ == "Persistence" else np.nan


def _task(args):
    tag, kind, feats, X, chunk = args
    L = X[X["y"].notna()].reset_index(drop=True)
    ev = L[L["tqi"] >= qindex(EVAL_FIRST)].iloc[chunk[0]::chunk[1]]
    rows = []
    for i, r in ev.iterrows():
        tr = L[L["target_published"] <= r["issue_ts"]]
        m = M.fit(M.make(kind, feats), kind, tr)
        te = L.loc[[i]]
        p = float(m.predict_proba(te)[0])
        cls = int(m.predict_class(te)[0]) if hasattr(m, "predict_class") else int(p >= 0.5)
        ptr = m.predict_proba(tr)
        rows.append({"tag": tag, "issue_quarter": r["issue_quarter"], "issue_date": r["issue_date"], "target_quarter": r["target_quarter"],
                     "y": int(r["y"]), "p": p, "cls": cls, "level_hat": _level(m, te), "hunger_target": float(r["hunger_target"]),
                     "hunger_last": float(r["hunger_last"]), "p_flip": float(r["p_flip"]), "n_train": int(len(tr)),
                     "train_max_target_published": str(pd.Timestamp(tr["target_published"].max()).date()),
                     "target_published": str(pd.Timestamp(r["target_published"]).date()),
                     "train_acc": float(((ptr >= 0.5) == tr["y"]).mean()), "train_brier": float(np.mean((ptr - tr["y"]) ** 2))})
    return rows


def run_walkforward(workers: int | None = None) -> pd.DataFrame:
    workers = workers or max(1, (os.cpu_count() or 4) - 2)
    X = Designer("operational").frame(1)
    k = 3
    tasks = [(tag, kind, feats, X, (c, k)) for tag, (kind, feats) in CONFIGS.items() for c in range(k)]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = [r for part in ex.map(_task, tasks) for r in part]
    return pd.DataFrame(out).sort_values(["tag", "target_quarter"]).reset_index(drop=True)


# ------------------------------------------------------------------------------------------------------- metrics
def ece(y, p, bins: int = 5) -> float:
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).mean() for b in range(bins) if (idx == b).any()))


def calib_line(y, p) -> dict:
    """Calibration intercept and slope: logistic regression of the outcome on logit(p) (ideal 0 and 1)."""
    if len(set(y)) < 2:
        return {"intercept": None, "slope": None}
    q = np.clip(p, 1e-4, 1 - 1e-4)
    lr = LogisticRegression(penalty=None, max_iter=1000).fit(np.log(q / (1 - q)).reshape(-1, 1), y)
    return {"intercept": float(lr.intercept_[0]), "slope": float(lr.coef_[0][0])}


def metrics(g: pd.DataFrame) -> dict:
    y, p, c = g["y"].to_numpy(int), g["p"].to_numpy(float), g["cls"].to_numpy(int)
    tp, fp = int(((c == 1) & (y == 1)).sum()), int(((c == 1) & (y == 0)).sum())
    fn, tn = int(((c == 0) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum())
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    prec = tp / (tp + fp) if tp + fp else None
    two = len(set(y)) == 2
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    err = g["level_hat"].to_numpy(float) - g["hunger_target"].to_numpy(float)
    ok = ~np.isnan(err)
    correct = (c == y).astype(float)
    flip = g["p_flip"].to_numpy(float)
    bins = [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)]
    out = {"n": int(len(y)), "n_high": int(y.sum()), "n_low": int(len(y) - y.sum()),
           "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
           "accuracy": float(correct.mean()), "balanced_accuracy": (rec + spec) / 2 if rec is not None and spec is not None else None,
           "precision": prec, "recall": rec, "specificity": spec,
           "f1": 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0,
           "roc_auc": float(roc_auc_score(y, p)) if two and len(set(np.round(p, 9))) > 1 else None,
           "pr_auc": float(average_precision_score(y, p)) if two else None,
           "brier": float(np.mean((p - y) ** 2)), "log_loss": float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))),
           "ece_5bin": ece(y, p), "calibration_line": calib_line(y, p),
           "reliability_table": [{"bin": f"{a:.1f}-{min(b, 1):.1f}", "n": int(((p >= a) & (p < b)).sum()),
                                  "mean_p": float(p[(p >= a) & (p < b)].mean()) if ((p >= a) & (p < b)).any() else None,
                                  "observed": float(y[(p >= a) & (p < b)].mean()) if ((p >= a) & (p < b)).any() else None}
                                 for a, b in bins],
           "mae_level_pp": float(np.mean(np.abs(err[ok]))) if ok.any() else None,
           "rmse_level_pp": float(np.sqrt(np.mean(err[ok] ** 2))) if ok.any() else None,
           "expected_accuracy_under_label_uncertainty": float(np.mean(correct * (1 - flip) + (1 - correct) * flip)),
           "n_uncertain_labels_pflip_gt_0_25": int((flip > 0.25).sum()),
           "train_accuracy_mean": float(g["train_acc"].mean()), "train_brier_mean": float(g["train_brier"].mean())}
    out["eras"] = {}
    for era, a, b in ERAS:
        s = g["target_quarter"].str[:4].astype(int).between(a, b).to_numpy()
        if s.sum():
            out["eras"][era] = {"n": int(s.sum()), "n_high": int(y[s].sum()), "accuracy": float(correct[s].mean()),
                                "recall": float((c[s][y[s] == 1] == 1).mean()) if y[s].sum() else None}
    return out


def reliability(s: dict, clim_brier: float) -> dict:
    R = PROTOCOL["reliability_rule_fi7"]
    chk = {"accuracy": s["accuracy"] >= R["accuracy"], "recall": (s["recall"] or 0) >= R["recall"],
           "precision": (s["precision"] or 0) >= R["precision"], "auc": (s["roc_auc"] or 0) >= R["auc"],
           "brier_below_climatology": s["brier"] < clim_brier,
           "every_era_accuracy": all(e["accuracy"] >= R["every_era_accuracy"] for e in s["eras"].values() if e["n"] >= 4)}
    return {"checks": chk, "passes": all(chk.values())}


def summarize(pr: pd.DataFrame) -> dict:
    yr = pr["target_quarter"].str[:4].astype(int)
    (d0, d1), (t0, t1) = PROTOCOL["split"]["development_target_years"], PROTOCOL["split"]["test_target_years"]
    saw = set(alternating_quarters())
    periods = {"full": pr, "development": pr[yr.between(d0, d1)], "test": pr[yr.between(t0, t1)],
               "full_without_sawtooth": pr[~pr["target_quarter"].isin(saw)]}
    res = {"periods": {}, "sawtooth_quarters": sorted(saw)}
    for name, g in periods.items():
        clim = g[g["tag"] == CLIM]
        cb = float(np.mean((clim["p"] - clim["y"]) ** 2))
        res["periods"][name] = {"climatology_brier": cb, "target_quarters": [g["target_quarter"].min(), g["target_quarter"].max()],
                                "models": {}}
        for tag in CONFIGS:
            s = metrics(g[g["tag"] == tag])
            s["brier_skill_vs_climatology"] = 1 - s["brier"] / cb if cb else None
            s["reliability"] = reliability(s, cb)
            a = g[g["tag"] == tag].set_index("target_quarter")
            b = g[g["tag"] == PERSIST].set_index("target_quarter").loc[a.index]
            s["vs_persistence_brier"] = boot_delta((a["p"] - a["y"]) ** 2, (b["p"] - b["y"]) ** 2) if tag != PERSIST else None
            if tag.startswith("LightGBM without"):
                f = g[g["tag"] == LGBM].set_index("target_quarter").loc[a.index]
                s["vs_full_lightgbm_brier"] = boot_delta((a["p"] - a["y"]) ** 2, (f["p"] - f["y"]) ** 2)
            res["periods"][name]["models"][tag] = s
    # selection on development targets only (protocol)
    dev = res["periods"]["development"]["models"]
    elig = []
    for tag in PROTOCOL["candidates"]:
        s = dev[tag]
        if not s["reliability"]["passes"]:
            continue
        if tag not in (PERSIST, DAMPED) and not (s["vs_persistence_brier"]["mean"] < 0 and s["vs_persistence_brier"]["p_negative"] >= 0.90):
            continue
        elig.append(tag)
    if elig:
        selected, why = min(elig, key=lambda t: dev[t]["brier"]), f"lowest development Brier among those passing: {elig}"
    else:
        selected = min([PERSIST, DAMPED], key=lambda t: dev[t]["brier"])
        why = "no candidate passed on development; persistence-family member with the lower development Brier"
    full, test, nosaw = (res["periods"][k]["models"][selected] for k in ("full", "test", "full_without_sawtooth"))
    checks = {"full_period_passes_with_ge_10_high": bool(full["reliability"]["passes"] and full["n_high"] >= 10),
              "test_period_passes": bool(test["reliability"]["passes"]),
              "without_sawtooth_passes": bool(nosaw["reliability"]["passes"]),
              "ece_full_le_0_10": bool(full["ece_5bin"] <= 0.10)}
    show_p = test["brier"] < res["periods"]["test"]["climatology_brier"] and full["ece_5bin"] <= 0.10
    res["selection"] = {"selected": selected, "reason": why, "eligible_on_development": elig,
                        "validated_lead1_checks": checks,
                        "lead1_status": "validated (regional)" if all(checks.values()) else "provisional",
                        "probability_display": "calibrated probability shown" if show_p else "class only; probability not calibrated"}
    return res


def run() -> dict:
    lock = check()
    pr = run_walkforward()
    pr.to_csv(OUT / "lead1_predictions.csv", index=False, lineterminator="\n")
    res = summarize(pr)
    res["protocol_sha256"] = lock
    fi7 = pd.read_csv(OUT.parent.parent / "fi7" / "out" / "final_predictions.csv")
    fi7 = fi7[fi7["lead"] == 1].set_index(["tag", "target_quarter"])["p"]
    mine = pr[pr["tag"].isin(FINAL_SPECS)].set_index(["tag", "target_quarter"])["p"]
    common = mine.index.intersection(fi7.index)
    res["reproduces_fi7_lead1"] = {"n_compared": int(len(common)),
                                   "max_abs_p_diff": float((mine.loc[common] - fi7.loc[common]).abs().max())}
    (OUT / "lead1_evaluation.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__" and sys.argv[1:] == ["run"]:
    r = run()
    print(json.dumps(r["selection"], indent=1), r["reproduces_fi7_lead1"])
