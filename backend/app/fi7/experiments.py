"""FI7 controlled experiments against the frozen FI6-N reference, and the final evaluation.

    python -m app.fi7.experiments run          # every registered experiment (all cores), registry.csv + details
    python -m app.fi7.experiments final        # the frozen final configuration + all baselines, every lead

Protocol (unchanged from FI6): FI6 target; walk-forward expanding window; at each origin train on rows whose target
was published by the issue date; evaluated targets 2010-Q1 .. 2026-Q3; same origins for every configuration.

Adoption rule (written before any experiment ran): a candidate component is adopted when, against its parent
configuration at the next-quarter lead (operational h = 1), the mean per-origin Brier change is negative with
moving-block bootstrap support P(change < 0) >= 0.90, and it does not worsen Brier at h = 0 or h = 2 by more than
0.005. The decision-threshold experiment is judged on balanced accuracy and F1 at h = 1 (Brier is unaffected).
"""
from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from app.fi5.target import qindex
from app.fi6.features import GOV, NEWS as NEWS6, OUTCOME
from app.fi6.news_model import NEWSA
from app.fi7 import models as M
from app.fi7.design import EW_COLS, WINDOW_COLS, Designer
from app.fi7.paths import OUT

EVAL_FIRST = "2010-Q1"
ERAS = [("2010-2015", 2010, 2015), ("2016-2020", 2016, 2020), ("2021-2026", 2021, 2026)]
WORLD = ["world_rice_yoy", "world_rice_3m", "world_urea_yoy"]
TYPHOON = ["tc_max_wind_q", "typhoon_passages_4q"]
UNDER = ["underemp_rate", "underemp_yoy"]
FISH = ["fish_yoy"]
NEWSW = list(WINDOW_COLS)
EW = list(EW_COLS)
REF = OUTCOME + GOV + NEWSA                                   # the FI6-N "government + news" configuration

EXPERIMENTS = {   # id: (hypothesis, timing, model, features, leads, parent)
    "E00": ("FI6-N reference reproduced (quarter-end issue)", "quarter_end", "delta_lgbm", REF, [1, 2, 3, 4], None),
    "E01": ("Release-aware operational issue (end of 2nd month): fresher SWS, CPI, news", "operational", "delta_lgbm", REF, [0, 1, 2, 3], "E00"),
    "E02": ("+ world rice and urea prices lead domestic food prices", "operational", "delta_lgbm", REF + WORLD, [0, 1, 2, 3], "E01"),
    "E03": ("+ typhoon intensity (max wind, typhoon-strength passages)", "operational", "delta_lgbm", REF + TYPHOON, [0, 1, 2, 3], "E01"),
    "E04": ("+ underemployment (job quality, income loss)", "operational", "delta_lgbm", REF + UNDER, [0, 1, 2, 3], "E01"),
    "E05": ("+ fisheries production (food availability, livelihoods)", "operational", "delta_lgbm", REF + FISH, [0, 1, 2, 3], "E01"),
    "E06": ("News from the 90 days before issue instead of the last complete quarter", "operational", "delta_lgbm",
            OUTCOME + GOV + NEWSW, [0, 1, 2, 3], "E01"),
    "E07": ("+ early-warning news (escalation, persistence of risk events)", "operational", "delta_lgbm",
            OUTCOME + GOV + NEWSW + EW, [0, 1, 2, 3], "E06"),
    "E08": ("Ridge change model instead of LightGBM", "operational", "delta_ridge", REF, [0, 1, 2, 3], "E01"),
    "E09": ("Damped persistence (latest reading decays to normal; no other inputs)", "operational", "damped", [], [0, 1, 2, 3], "E01"),
    "E10": ("Decision threshold chosen on training out-of-fold predictions", "operational", "delta_lgbm_tau", REF, [0, 1, 2, 3], "E01"),
    "E11": ("Diagnostic: government + news without the latest-reading block", "operational", "delta_lgbm", GOV + NEWSA, [0, 1, 2, 3], "E01"),
}
# Registered after the first round (E00-E11) was read, so labelled post-hoc; judged by the same rule.
POSTHOC = {
    "F1": ("Combination of adopted components: operational timing + world prices + training threshold",
           "operational", "delta_lgbm_tau", REF + WORLD, [0, 1, 2, 3], "E02"),
    "E12": ("POST-HOC: damped-persistence anchor + LightGBM on its residual (government + news + world prices)",
            "operational", "anchored_lgbm", REF + WORLD, [0, 1, 2, 3], "E02"),
    "F2": ("POST-HOC: E12 + training threshold", "operational", "anchored_lgbm_tau", REF + WORLD, [0, 1, 2, 3], "F1"),
    "E13": ("POST-HOC reference: damped persistence + training threshold", "operational", "damped_tau", [], [0, 1, 2, 3], "E09"),
}


def _task(args):
    tag, kind, feats, lead, X, chunk = args
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
        rows.append({"tag": tag, "lead": lead, "issue_date": r["issue_date"], "target_quarter": r["target_quarter"],
                     "y": int(r["y"]), "p": p, "cls": cls, "p_flip": r["p_flip"], "n_train": int(len(tr)),
                     "train_acc": float(((ptr >= 0.5) == tr["y"]).mean()), "config": str(getattr(m, "choice", ""))})
    return rows


def run_configs(configs: dict, workers: int | None = None) -> pd.DataFrame:
    """configs: tag -> (timing, kind, features, leads). Returns all walk-forward predictions."""
    workers = workers or max(1, (os.cpu_count() or 4) - 2)
    timings = sorted({c[0] for c in configs.values()})
    designs = {}
    for t in timings:
        D = Designer(t)
        leads = sorted({l for c in configs.values() if c[0] == t for l in c[3]})
        designs.update({(t, l): D.frame(l) for l in leads})
    k = 3
    tasks = [(tag, kind, feats, l, designs[(t, l)], (c, k)) for tag, (t, kind, feats, leads) in configs.items()
             for l in leads for c in range(k)]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = [r for part in ex.map(_task, tasks) for r in part]
    return pd.DataFrame(out).sort_values(["tag", "lead", "target_quarter"]).reset_index(drop=True)


def scores(g: pd.DataFrame) -> dict:
    y, p, c = g["y"].to_numpy(int), g["p"].to_numpy(float), g["cls"].to_numpy(int)
    tp, fp = int(((c == 1) & (y == 1)).sum()), int(((c == 1) & (y == 0)).sum())
    fn, tn = int(((c == 0) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum())
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    prec = tp / (tp + fp) if tp + fp else None
    out = {"n": int(len(y)), "n_high": int(y.sum()), "n_low": int(len(y) - y.sum()), "accuracy": float((c == y).mean()),
           "balanced_accuracy": (rec + spec) / 2 if rec is not None and spec is not None else None,
           "precision": prec, "recall": rec, "f1": 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else None,
           "fpr": fp / (fp + tn) if fp + tn else None, "tp": tp, "fp": fp, "tn": tn, "fn": fn,
           "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(np.round(p, 9))) > 1 else None,
           "brier": float(np.mean((p - y) ** 2)), "mean_train_accuracy": float(g["train_acc"].mean())}
    out["eras"] = {}
    for era, a, b in ERAS:
        s = g["target_quarter"].str[:4].astype(int).between(a, b)
        yy, cc = y[s.to_numpy()], c[s.to_numpy()]
        out["eras"][era] = {"n": int(len(yy)), "n_high": int(yy.sum()), "accuracy": float((cc == yy).mean()) if len(yy) else None,
                            "recall": float((cc[yy == 1] == 1).mean()) if yy.sum() else None}
    bins = [(0, .2), (.2, .5), (.5, .8), (.8, 1.01)]
    out["calibration"] = [{"bin": f"{a:.1f}-{min(b, 1):.1f}", "n": int(((p >= a) & (p < b)).sum()),
                           "mean_p": float(p[(p >= a) & (p < b)].mean()) if ((p >= a) & (p < b)).any() else None,
                           "observed": float(y[(p >= a) & (p < b)].mean()) if ((p >= a) & (p < b)).any() else None} for a, b in bins]
    return out


def boot_delta(a: np.ndarray, b: np.ndarray, reps: int = 5000, block: int = 4, seed: int = 7) -> dict:
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    rng = np.random.default_rng(seed)
    starts = np.arange(max(n - block + 1, 1))
    k = int(np.ceil(n / block))
    bs = np.array([d[np.concatenate([np.arange(s, min(s + block, n)) for s in rng.choice(starts, k)])[:n]].mean() for _ in range(reps)])
    return {"mean": float(d.mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "p_negative": float((bs < 0).mean())}


def compare(pr: pd.DataFrame, tag: str, parent: str, lead_map: dict | None = None) -> dict:
    """Per-lead Brier comparison on identical target quarters (lead_map maps child lead -> parent lead)."""
    out = {}
    for lead in sorted(pr[pr["tag"] == tag]["lead"].unique()):
        pl = (lead_map or {}).get(lead, lead)
        a = pr[(pr["tag"] == tag) & (pr["lead"] == lead)].set_index("target_quarter")
        b = pr[(pr["tag"] == parent) & (pr["lead"] == pl)].set_index("target_quarter")
        common = a.index.intersection(b.index)
        if not len(common):
            continue
        y = a.loc[common, "y"].to_numpy()
        res = boot_delta((a.loc[common, "p"] - y) ** 2, (b.loc[common, "p"] - y) ** 2)
        res["n"] = int(len(common))
        out[int(lead)] = res
    return out


def run(round_: str = "1") -> pd.DataFrame:
    registry = EXPERIMENTS if round_ == "1" else POSTHOC
    cfg = {k: (v[1], v[2], v[3], v[4]) for k, v in registry.items()}
    pr = run_configs(cfg)
    if round_ != "1":
        prev = pd.read_csv(OUT / "experiment_predictions.csv")
        pr = pd.concat([prev[~prev["tag"].isin(registry)], pr], ignore_index=True)
        reg_prev = pd.read_csv(OUT / "experiment_registry.csv")
        detail_prev = json.loads((OUT / "experiment_details.json").read_text())
    pr.to_csv(OUT / "experiment_predictions.csv", index=False, lineterminator="\n")
    reg, detail = [], {}
    for k, (hyp, timing, kind, feats, leads, parent) in registry.items():
        sc = {int(l): scores(g) for l, g in pr[pr["tag"] == k].groupby("lead")}
        # E01 vs E00: the same target quarters, next-quarter = operational h1 vs quarter-end lead 2, etc.
        cmp = compare(pr, k, parent, {0: 1, 1: 2, 2: 3, 3: 4} if k == "E01" else None) if parent else {}
        h1 = cmp.get(1, {})
        if k in ("E00", "E09", "E11"):
            decision, why = "reference" if k == "E00" else "diagnostic/competitor", "not an adoptable component"
        elif k == "E01":
            decision = "adopt"
            why = "operationally correct timing (DA reads the outlook inside the current quarter); adopted on realism, comparison reported"
        elif k in ("E10", "F1", "E13"):          # threshold-only changes: judged on balanced accuracy and F1 at h1
            base, new = scores(pr[(pr["tag"] == parent) & (pr["lead"] == 1)]), sc[1]
            good = (new["balanced_accuracy"] or 0) > (base["balanced_accuracy"] or 0) and (new["f1"] or 0) > (base["f1"] or 0)
            decision, why = ("adopt" if good else "reject"), f"h1 balanced accuracy {base['balanced_accuracy']:.3f}->{new['balanced_accuracy']:.3f}, F1 {base['f1'] or 0:.3f}->{new['f1'] or 0:.3f}"
        else:
            ok = h1 and h1["mean"] < 0 and h1["p_negative"] >= 0.90 and all(cmp.get(l, {"mean": 0})["mean"] <= 0.005 for l in (0, 2))
            decision = "adopt" if ok else "reject"
            why = f"h1 dBrier {h1.get('mean', float('nan')):+.4f} P(<0)={h1.get('p_negative', float('nan')):.2f}; h0 {cmp.get(0, {}).get('mean', float('nan')):+.4f}; h2 {cmp.get(2, {}).get('mean', float('nan')):+.4f}"
        reg.append({"id": k, "hypothesis": hyp, "timing": timing, "model": kind, "n_features": len(feats), "parent": parent,
                    **{f"brier_h{l}": sc[l]["brier"] for l in sc}, **{f"auc_h{l}": sc[l]["auc"] for l in sc},
                    **{f"bacc_h{l}": sc[l]["balanced_accuracy"] for l in sc}, "decision": decision, "reason": why})
        detail[k] = {"scores": sc, "vs_parent": cmp, "features": feats, "timing": timing, "model": kind}
    rg = pd.DataFrame(reg)
    if round_ != "1":
        rg = pd.concat([reg_prev[~reg_prev["id"].isin(registry)], rg.assign(round="post-hoc")], ignore_index=True)
        detail = {**detail_prev, **detail}
    rg.to_csv(OUT / "experiment_registry.csv", index=False, lineterminator="\n")
    (OUT / "experiment_details.json").write_text(json.dumps(detail, indent=1, default=str))
    return rg



# ------------------------------------------------------------------------------------------------ final evaluation
FINAL_PROPOSED = "LightGBM (proposed, FI7)"
FINAL_SPECS = {   # tag -> (timing, kind, features, leads) ; all operational, identical origins
    FINAL_PROPOSED: ("operational", "delta_lgbm_tau", REF + WORLD, [0, 1, 2, 3]),
    "Damped persistence (statistical)": ("operational", "damped_tau", [], [0, 1, 2, 3]),
    "Naive persistence (latest reading)": ("operational", "persist", [], [0, 1, 2, 3]),
    "Government + latest reading (no news)": ("operational", "delta_lgbm_tau", OUTCOME + GOV + WORLD, [0, 1, 2, 3]),
    "PSA/government-only (no SWS, no news)": ("operational", "clf_lgbm", GOV + WORLD, [0, 1, 2, 3]),
    "NLP/news-only (no SWS)": ("operational", "clf_lgbm", NEWSA, [0, 1, 2, 3]),
    "Logistic regression": ("operational", "logit", REF + WORLD, [0, 1, 2, 3]),
    "Always LOW (reference)": ("operational", "clim", [], [0, 1, 2, 3]),
}
RELIABILITY = {"accuracy": 0.75, "recall": 0.50, "precision": 0.50, "auc": 0.70, "brier_skill": 0.0, "era_accuracy": 0.60}


def reliability(s: dict, clim_brier: float) -> dict:
    chk = {"accuracy": s["accuracy"] >= RELIABILITY["accuracy"], "recall": (s["recall"] or 0) >= RELIABILITY["recall"],
           "precision": (s["precision"] or 0) >= RELIABILITY["precision"], "auc": (s["auc"] or 0) >= RELIABILITY["auc"],
           "brier_skill": s["brier"] < clim_brier,
           "era_accuracy": all((e["accuracy"] or 0) >= RELIABILITY["era_accuracy"] for e in s["eras"].values() if e["n"])}
    return {"checks": chk, "reliable": all(chk.values())}


def final() -> dict:
    pr = run_configs(FINAL_SPECS)
    pr.to_csv(OUT / "final_predictions.csv", index=False, lineterminator="\n")
    res = {"by_lead": {}, "furthest_reliable_lead": {}}
    for lead in sorted(pr["lead"].unique()):
        g = pr[pr["lead"] == lead]
        clim = g[g["tag"] == "Always LOW (reference)"]
        cb = float(np.mean((clim["p"] - clim["y"]) ** 2))
        models = {}
        for tag in FINAL_SPECS:
            s = scores(g[g["tag"] == tag])
            s["brier_skill_vs_climatology"] = 1 - s["brier"] / cb if cb else None
            gw = g[g["tag"] == tag]
            w = 1 - gw["p_flip"].to_numpy(float)
            s["confidence_weighted_accuracy"] = float(np.sum(w * (gw["cls"].to_numpy() == gw["y"].to_numpy())) / np.sum(w))
            s["reliability"] = reliability(s, cb)
            models[tag] = s
        comp = {}
        for ref in [FINAL_PROPOSED, "Damped persistence (statistical)"]:
            comp[ref] = {}
            for tag in FINAL_SPECS:
                if tag == ref:
                    continue
                c = compare(pr.assign(tag=pr["tag"].replace({tag: "__o"})), ref, "__o")
                comp[ref][tag] = c.get(int(lead))
        res["by_lead"][int(lead)] = {"models": models, "brier_diff_ref_minus_other": comp}
    for tag in FINAL_SPECS:
        best = None
        for lead in [1, 2, 3]:                       # contiguous from the next quarter (h=0 is the current quarter)
            if res["by_lead"][lead]["models"][tag]["reliability"]["reliable"]:
                best = lead
            else:
                break
        res["furthest_reliable_lead"][tag] = best
        res.setdefault("nowcast_h0_reliable", {})[tag] = res["by_lead"][0]["models"][tag]["reliability"]["reliable"]
    (OUT / "final_evaluation.json").write_text(json.dumps(res, indent=1, default=str))
    return res



def alternating_quarters(min_run: int = 4) -> list[str]:
    """Target quarters inside a sawtooth: >= min_run consecutive quarter-to-quarter changes that alternate in sign and
    each exceed the larger of the two rounds' margins of error (survey-vehicle artefact candidate, see docs/fi7)."""
    from app.fi6.target import quarterly
    q = quarterly().reset_index(drop=True)
    ch = q["hunger"].diff()
    big = ch.abs() > np.maximum(q["moe"], q["moe"].shift())
    alt = (np.sign(ch) != np.sign(ch.shift())) & big & big.shift(fill_value=False)
    flagged, run = set(), []
    for i in range(1, len(q)):
        if alt.iloc[i]:
            run.append(i)
        else:
            if len(run) + 1 >= min_run:
                flagged.update(q["quarter"].iloc[run[0] - 1:run[-1] + 1])
            run = []
    if len(run) + 1 >= min_run:
        flagged.update(q["quarter"].iloc[run[0] - 1:run[-1] + 1])
    return sorted(flagged)


def sensitivity() -> dict:
    """Reliability recomputed without sawtooth quarters (no refitting; same stored walk-forward predictions)."""
    pr = pd.read_csv(OUT / "final_predictions.csv")
    alt = alternating_quarters()
    out = {"alternating_target_quarters": alt, "by_lead": {}}
    for lead in sorted(pr["lead"].unique()):
        g = pr[(pr["lead"] == lead) & ~pr["target_quarter"].isin(alt)]
        clim = g[g["tag"] == "Always LOW (reference)"]
        cb = float(np.mean((clim["p"] - clim["y"]) ** 2))
        out["by_lead"][int(lead)] = {}
        for tag in FINAL_SPECS:
            s = scores(g[g["tag"] == tag])
            s["reliability"] = reliability(s, cb)
            out["by_lead"][int(lead)][tag] = {k: s[k] for k in ["n", "n_high", "accuracy", "balanced_accuracy", "precision", "recall", "auc", "brier", "reliability"]}
    ev = json.loads((OUT / "final_evaluation.json").read_text())
    out["robust_reliable"] = {tag: {int(L): bool(ev["by_lead"][str(L)]["models"][tag]["reliability"]["reliable"] and
                                            out["by_lead"][int(L)][tag]["reliability"]["reliable"]) for L in [0, 1, 2, 3]} for tag in FINAL_SPECS}
    (OUT / "sensitivity_alternation.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "final", "sensitivity"])
    ap.add_argument("--round", default="1", choices=["1", "posthoc"])
    a = ap.parse_args()
    if a.cmd == "run":
        print(run(a.round).to_string())
    elif a.cmd == "sensitivity":
        print(json.dumps(sensitivity()["robust_reliable"], indent=1))
    else:
        r = final()
        print(json.dumps(r["furthest_reliable_lead"], indent=1), json.dumps(r["nowcast_h0_reliable"], indent=1))
