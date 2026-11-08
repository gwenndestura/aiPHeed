"""FI9-N: does news add forecasting value, and at which horizon? Reproduces FI6-N, then compares news on matched
issue dates for each horizon.

    python -m app.fi9n.study lock        # writes data/fi9n/out/PROTOCOL_LOCK.json (refuses to overwrite)
    python -m app.fi9n.study run         # refuses unless the lock matches

Horizons (targets 2010-Q1 .. latest; identical issue dates and cutoffs for every configuration within a horizon):
    QE1   issue on the last day of quarter t, target t+1 (FI6-N "Lead 1"); news = quarter t (complete)
    OP1   issue on the last day of t's 2nd month, target t+1 (FI9 Lead 1); news = last complete quarter t-1
    OP1w  as OP1, news = the 90 days before the issue date (FI7 windows)
    OP0   issue as OP1, target t (current-quarter nowcast); news = last complete quarter t-1
    QE2   issue on the last day of quarter t, target t+2 (FI6-N "Lead 2")
Every horizon uses the FI6-N model family (LightGBM change model, class at p >= 0.5) and the same feature sets.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from app.fi5.evaluate import block_bootstrap_diff, mcnemar_p
from app.fi5.target import qindex
from app.fi6 import models as M6
from app.fi6.features import GOV, OUTCOME
from app.fi6.news_model import NEWS_DOMAIN, NEWSA
from app.fi7 import models as M7
from app.fi7.design import WINDOW_COLS
from app.fi7.experiments import alternating_quarters
from app.fi9n import OUT, VERSION

EVAL_FIRST = "2010-Q1"
HORIZONS = ["QE1", "OP1", "OP1w", "OP0", "QE2"]
WMAP = {"w_market": "na_market", "w_climate": "na_climate", "w_employment": "na_employment", "w_remittance": "na_remittance",
        "w_poverty": "na_poverty", "w_climate_damage": "na_climate_damage", "w_displaced": "na_displaced"}
SETS = {"Government only": OUTCOME + GOV, "Government + news": OUTCOME + GOV + NEWSA, "News + latest reading": OUTCOME[:1] + NEWSA,
        **{f"Government + news without {d} news": OUTCOME + GOV + [f for f in NEWSA if NEWS_DOMAIN[f] != d]
           for d in ["market", "climate", "employment", "remittance", "poverty"]}}
PROTOCOL = {
    "version": VERSION,
    "horizons": {"QE1": "quarter-end issue, target next quarter, news of the issue quarter (FI6-N Lead 1)",
                 "OP1": "operational issue (end of 2nd month), target next quarter, news of the last complete quarter (FI9 Lead 1)",
                 "OP1w": "operational issue, target next quarter, news of the 90 days before issue",
                 "OP0": "operational issue, target current quarter (nowcast), news of the last complete quarter",
                 "QE2": "quarter-end issue, target two quarters ahead (FI6-N Lead 2)"},
    "configurations": {k: v for k, v in SETS.items()} | {"Naive persistence": "latest reading", "Damped persistence": "FI7 damped",
                                                       "Climatology": "training base rate"},
    "model": "FI6 LightGBM change model ('reg', monotone constraints); class = p >= 0.5; no tuning",
    "decisions": {
        "news_improves_probability_quality": "Brier(Government + news) - Brier(Government only): 95% block-bootstrap CI below 0; "
                                             "Bonferroni over the 5 horizons (99% CI) reported and required for a 'robust' claim",
        "news_improves_accuracy_or_recall": "McNemar p < 0.05 on correct classifications, or recall difference with a "
                                            "bootstrap CI excluding 0",
        "news_beyond_latest_reading": "Brier(News + latest reading) and Brier(Government + news) vs naive persistence: 95% CI below 0",
        "stable": "Brier difference (news vs no news) negative in each era with news (2016-2020, 2021-2026) and 95% CI below 0 "
                  "without the FI7 sawtooth quarters",
        "operationally_meaningful": "a news configuration that passes the FI7 reliability rule AND beats naive persistence "
                                    "(95% CI below 0) at that horizon",
    },
    "bootstrap": "FI6-N moving-block bootstrap (block 4, 2000 reps, seed 11)",
    "known_before_lock": "FI6-N results (QE1 news gain on Brier/AUC; QE2 borderline) and FI7/FI9 OP1 ablations (no gain)",
}


def _digest() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True).encode()).hexdigest()


def design(h: str) -> pd.DataFrame:
    if h in ("QE1", "QE2"):
        from app.fi6.news_model import design_n
        return design_n(1 if h == "QE1" else 2)
    from app.fi7.design import Designer
    X = Designer("operational").frame(0 if h == "OP0" else 1)
    if h == "OP1w":
        X = X.drop(columns=NEWSA).rename(columns=WMAP)
    return X


def _task(args):
    h, X, chunk = args
    L = X[X["y"].notna()].reset_index(drop=True)
    ev = L[L["tqi"] >= qindex(EVAL_FIRST)].iloc[chunk[0]::chunk[1]]
    rows = []
    for i, r in ev.iterrows():
        tr = L[L["target_published"] <= r["issue_ts"]]
        te = L.loc[[i]]
        rec = {"horizon": h, "issue_date": str(pd.Timestamp(r["issue_ts"]).date()), "target_quarter": r["target_quarter"],
               "y": int(r["y"]), "p_flip": float(r["p_flip"]), "news_available": bool(te[NEWSA].notna().any(axis=1).iloc[0]),
               "hunger_age_q": float(r.get("hunger_age_q", np.nan)),
               "train_max_target_published": str(pd.Timestamp(tr["target_published"].max()).date())}
        for name, fs in SETS.items():
            m = M6.fit(M6.make("reg", fs), "reg", tr)
            rec[name] = float(m.predict_proba(te)[0])
        rec["Naive persistence"] = float(M6.fit(M6.make("persist", None), "persist", tr).predict_proba(te)[0])
        rec["Damped persistence"] = float(M7.make("damped", []).fit(tr, tr["delta_target"].to_numpy(float)).predict_proba(te)[0])
        rec["Climatology"] = float(M6.fit(M6.make("clim", None), "clim", tr).predict_proba(te)[0])
        rows.append(rec)
    return rows


CONFIGS = list(SETS) + ["Naive persistence", "Damped persistence", "Climatology"]


def _metrics(y, p):
    c = (p >= 0.5).astype(int)
    tp, fp, fn, tn = ((c == 1) & (y == 1)).sum(), ((c == 1) & (y == 0)).sum(), ((c == 0) & (y == 1)).sum(), ((c == 0) & (y == 0)).sum()
    idx = np.minimum((p * 5).astype(int), 4)
    ece = sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).mean() for b in range(5) if (idx == b).any())
    rec, spec = (tp / (tp + fn) if tp + fn else None), (tn / (tn + fp) if tn + fp else None)
    return {"n": int(len(y)), "n_high": int(y.sum()), "accuracy": float((c == y).mean()), "recall": rec,
            "precision": float(tp / (tp + fp)) if tp + fp else None,
            "balanced_accuracy": (rec + spec) / 2 if rec is not None and spec is not None else None,
            "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(np.round(p, 9))) > 1 else None,
            "brier": float(np.mean((p - y) ** 2)), "ece_5bin": float(ece), "share_predicted_high": float(c.mean())}


def _diff(a, b, y, block=4, reps=2000, seed=11):
    d = (a - y) ** 2 - (b - y) ** 2
    m, lo, hi = block_bootstrap_diff((a - y) ** 2, (b - y) ** 2, block, reps, seed)
    n = len(d)
    rng = np.random.default_rng(seed)
    starts = np.arange(max(n - block + 1, 1))
    bs = np.array([d[np.concatenate([np.arange(s, min(s + block, n)) for s in rng.choice(starts, int(np.ceil(n / block)))])[:n]].mean()
                   for _ in range(reps)])
    return {"mean": m, "ci95": [lo, hi], "ci99_bonferroni5": [float(np.percentile(bs, 0.5)), float(np.percentile(bs, 99.5))],
            "p_better": float((bs < 0).mean())}


def _recall_diff(a, b, y, reps=2000, block=4, seed=11):
    pos = np.where(y == 1)[0]
    ca, cb = (a >= 0.5).astype(int), (b >= 0.5).astype(int)
    rng = np.random.default_rng(seed)
    out = []
    n = len(y)
    starts = np.arange(n - block + 1)
    for _ in range(reps):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.choice(starts, int(np.ceil(n / block)))])[:n]
        yy = y[idx]
        if yy.sum():
            out.append(ca[idx][yy == 1].mean() - cb[idx][yy == 1].mean())
    return {"mean": float(ca[pos].mean() - cb[pos].mean()), "ci95": [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]}


def analyse(pr: pd.DataFrame) -> dict:
    from app.fi9.evaluate import reliability
    saw = set(alternating_quarters())
    res = {}
    for h, g in pr.groupby("horizon", sort=False):
        g = g.sort_values("target_quarter").reset_index(drop=True)
        y = g["y"].to_numpy(int)
        H = {"issue_dates_example": g["issue_date"].iloc[-3:].tolist(), "mean_age_of_latest_reading_q": float(g["hunger_age_q"].mean())}
        cb = float(np.mean((g["Climatology"] - y) ** 2))
        H["metrics"] = {}
        for c in CONFIGS:
            s = _metrics(y, g[c].to_numpy(float))
            eras = {}
            for era, a_, b_ in [("2010-2015", 2010, 2015), ("2016-2020", 2016, 2020), ("2021-2026", 2021, 2026)]:
                m = g["target_quarter"].str[:4].astype(int).between(a_, b_).to_numpy()
                cc = (g[c].to_numpy(float)[m] >= 0.5).astype(int)
                eras[era] = {"n": int(m.sum()), "accuracy": float((cc == y[m]).mean()),
                             "recall": float(cc[y[m] == 1].mean()) if y[m].sum() else None}
            s["eras"] = eras
            s["roc_auc"] = s["auc"]
            s["reliability_fi7"] = reliability(s, cb)
            H["metrics"][c] = s
        gn, go, nl, pe = (g[c].to_numpy(float) for c in ["Government + news", "Government only", "News + latest reading", "Naive persistence"])
        H["news_vs_no_news"] = _diff(gn, go, y)
        H["news_vs_no_news"]["auc_diff"] = (H["metrics"]["Government + news"]["auc"] or np.nan) - (H["metrics"]["Government only"]["auc"] or np.nan)
        H["news_vs_no_news"]["mcnemar_p"] = mcnemar_p(((gn >= .5) == y).astype(int), ((go >= .5) == y).astype(int))
        H["news_vs_no_news"]["recall_diff"] = _recall_diff(gn, go, y)
        H["news_latest_vs_no_news"] = _diff(nl, go, y)
        H["news_latest_vs_no_news"]["mcnemar_p"] = mcnemar_p(((nl >= .5) == y).astype(int), ((go >= .5) == y).astype(int))
        H["news_latest_vs_no_news"]["recall_diff"] = _recall_diff(nl, go, y)
        H["gov_news_vs_persistence"] = _diff(gn, pe, y)
        H["news_latest_vs_persistence"] = _diff(nl, pe, y)
        H["no_news_vs_persistence"] = _diff(go, pe, y)
        H["news_domain_removal"] = {d: _diff(g[f"Government + news without {d} news"].to_numpy(float), gn, y)
                                    for d in ["market", "climate", "employment", "remittance", "poverty"]}
        H["by_era_news_minus_no_news"] = {}
        for era, a_, b_ in [("2010-2015", 2010, 2015), ("2016-2020", 2016, 2020), ("2021-2026", 2021, 2026)]:
            m = g["target_quarter"].str[:4].astype(int).between(a_, b_).to_numpy()
            H["by_era_news_minus_no_news"][era] = {"n": int(m.sum()), "news_available": int(g["news_available"].to_numpy()[m].sum()),
                                                   "mean_brier_diff": float(np.mean((gn[m] - y[m]) ** 2 - (go[m] - y[m]) ** 2))}
        ns = ~g["target_quarter"].isin(saw).to_numpy()
        H["without_sawtooth"] = {"n": int(ns.sum()), "news_vs_no_news": _diff(gn[ns], go[ns], y[ns]),
                                 "gov_news_vs_persistence": _diff(gn[ns], pe[ns], y[ns])}
        wn = g["news_available"].to_numpy()
        H["origins_with_news"] = {"n": int(wn.sum()), "news_vs_no_news": _diff(gn[wn], go[wn], y[wn])}
        D = PROTOCOL["decisions"]
        H["decisions"] = {
            "probability_quality_improved_95": H["news_vs_no_news"]["ci95"][1] < 0,
            "probability_quality_improved_bonferroni": H["news_vs_no_news"]["ci99_bonferroni5"][1] < 0,
            "auc_improved": H["news_vs_no_news"]["auc_diff"] > 0,
            "accuracy_or_recall_improved": (H["news_vs_no_news"]["mcnemar_p"] < 0.05 or H["news_vs_no_news"]["recall_diff"]["ci95"][0] > 0
                                            or H["news_latest_vs_no_news"]["mcnemar_p"] < 0.05
                                            or H["news_latest_vs_no_news"]["recall_diff"]["ci95"][0] > 0),
            "beyond_latest_reading": H["gov_news_vs_persistence"]["ci95"][1] < 0 or H["news_latest_vs_persistence"]["ci95"][1] < 0,
            "stable_across_eras": all(H["by_era_news_minus_no_news"][e]["mean_brier_diff"] < 0 for e in ["2016-2020", "2021-2026"]),
            "survives_sawtooth_exclusion": H["without_sawtooth"]["news_vs_no_news"]["ci95"][1] < 0,
            "operationally_meaningful": any(H["metrics"][c]["reliability_fi7"]["passes"] and _diff(g[c].to_numpy(float), pe, y)["ci95"][1] < 0
                                            for c in ["Government + news", "News + latest reading"]),
        }
        H["decision_text"] = D
        res[h] = H
    return res


def reproduce_fi6n() -> dict:
    """(a) recompute FI6-N's lead-1 numbers from its saved predictions with this module's code; (b) compare the re-run."""
    from app.paths import BACKEND_DIR
    saved = pd.read_csv(BACKEND_DIR / "data" / "fi6" / "out_news" / "news_walkforward_predictions.csv")
    rep = json.loads((BACKEND_DIR / "data" / "fi6" / "out_news" / "news_evaluation.json").read_text())
    out = {}
    for lead in (1, 2):
        g = saved[saved["lead"] == lead].sort_values("target_quarter")
        y = g["y"].to_numpy(int)
        mine = {c: _metrics(y, g[c].to_numpy(float)) for c in ["Government only", "News only", "Government + news", "Naive persistence"]}
        d = block_bootstrap_diff((g["Government + news"] - y) ** 2, (g["Government only"] - y) ** 2)
        r = rep["by_lead"][str(lead)]["all_origins"]
        out[f"lead{lead}"] = {"recomputed": {c: {k: mine[c][k] for k in ["accuracy", "recall", "auc", "brier"]} for c in mine},
                              "reported_brier": {c: r["models"][c]["brier"] for c in mine},
                              "reported_auc": {c: r["models"][c]["auc"] for c in mine},
                              "recomputed_gov_news_minus_gov": d, "reported_gov_news_minus_gov": [r["vs_gov_only"]["Government + news"]["brier_diff_vs_gov_only"]] + r["vs_gov_only"]["Government + news"]["ci95"]}
    return out


def run() -> dict:
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    if lock["sha256"] != _digest():
        raise RuntimeError("FI9-N protocol changed after lock")
    workers = max(1, (os.cpu_count() or 4) - 2)
    designs = {h: design(h) for h in HORIZONS}
    k = 3
    with ProcessPoolExecutor(max_workers=workers) as ex:
        parts = list(ex.map(_task, [(h, designs[h], (c, k)) for h in HORIZONS for c in range(k)]))
    pr = pd.DataFrame([r for p in parts for r in p]).sort_values(["horizon", "target_quarter"]).reset_index(drop=True)
    pr.to_csv(OUT / "news_predictions.csv", index=False, lineterminator="\n")
    from app.paths import BACKEND_DIR
    saved = pd.read_csv(BACKEND_DIR / "data" / "fi6" / "out_news" / "news_walkforward_predictions.csv")
    rerun = {}
    for h, lead in [("QE1", 1), ("QE2", 2)]:
        a = pr[pr["horizon"] == h].set_index("target_quarter")
        b = saved[saved["lead"] == lead].set_index("target_quarter")
        common = a.index.intersection(b.index)
        rerun[h] = {c: float((a.loc[common, c] - b.loc[common, s]).abs().max()) for c, s in
                    [("Government only", "Government only"), ("Government + news", "Government + news"), ("News + latest reading", "News only"),
                     ("Naive persistence", "Naive persistence")]}
    res = {"protocol_sha256": lock["sha256"], "fi6n_reproduction": reproduce_fi6n(), "rerun_vs_fi6n_saved_max_abs_p_diff": rerun,
           "horizons": analyse(pr)}
    (OUT / "news_study.json").write_text(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    return res


if __name__ == "__main__":
    if sys.argv[1:] == ["lock"]:
        from datetime import datetime, timezone
        p = OUT / "PROTOCOL_LOCK.json"
        if p.exists():
            sys.exit(f"already locked: {json.loads(p.read_text())['sha256']}")
        p.write_text(json.dumps({"sha256": _digest(), "locked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                 "protocol": PROTOCOL}, indent=1))
        print(_digest())
    elif sys.argv[1:] == ["run"]:
        r = run()
        print(json.dumps({"rerun": r["rerun_vs_fi6n_saved_max_abs_p_diff"],
                          "decisions": {h: v["decisions"] for h, v in r["horizons"].items()}}, indent=1))
