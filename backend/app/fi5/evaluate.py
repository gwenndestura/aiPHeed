"""Objectives 2 and 4: walk-forward expanding-window evaluation of LightGBM and the four baselines, per lead.

Protocol (fixed in METHOD_LOCK.json before the run):
  * issue date = last day of issue quarter t; target = quarter t + lead, lead 1..4;
  * at every origin the models are refitted on all rows whose target label had been *published* by the issue date
    (expanding window), using only features available at each row's own issue date;
  * evaluated targets: 2010-Q1 .. 2026-Q3 (every quarter with an SWS reading); era blocks 2010-2015, 2016-2020,
    2021-2026;
  * the same rows, leads and origins are used for every model.

Reliability at a lead (all must hold): accuracy >= 0.75; HIGH recall >= 0.50 and precision >= 0.50; AUC >= 0.70;
Brier skill vs climatology > 0; accuracy >= 0.60 in every era block. The furthest reliable lead is the largest L such
that every lead 1..L is reliable.
"""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, roc_auc_score

from app.fi5.features import FEATURE_SETS, OUTCOME, FeatureBuilder, domain_of
from app.fi5.models import Model, lgbm_regressor
from app.fi5.paths import OUT
from app.fi5.sources import DOMAIN_ORDER
from app.fi5.target import labels, qindex

LEADS = [1, 2, 3, 4]
FIRST_ISSUE = "1999-Q1"
EVAL_FIRST_TARGET = "2010-Q1"
ERAS = [("2010-2015", 2010, 2015), ("2016-2020", 2016, 2020), ("2021-2026", 2021, 2026)]
RELIABILITY = {"accuracy": 0.75, "recall": 0.50, "precision": 0.50, "auc": 0.70, "brier_skill": 0.0, "era_accuracy": 0.60}

PROPOSED = "LightGBM (proposed)"
BASELINES = {
    "Naive persistence": ("persistence", None),
    "PSA-only (government indicators)": ("lgbm", "psa_only"),
    "NLP-only (news features)": ("lgbm", "nlp_only"),
    "Logistic regression": ("logit", "full"),
}
REFERENCE = {"Climatology (base rate)": ("climatology", None),
             "LightGBM without news (ablation)": ("lgbm", "full_no_news")}


def _domain_drop(dom: str) -> list[str]:
    """The full feature set without one explanatory domain (its government and its news features)."""
    return [f for f in FEATURE_SETS["full"] if f in OUTCOME or domain_of(f) != dom]


SPECS = {PROPOSED: ("lgbm", "full"), **BASELINES, **REFERENCE,
         **{f"LightGBM without {d} domain": ("lgbm", f"drop_{d}") for d in DOMAIN_ORDER}}


def feature_list(name: str | None) -> list[str]:
    if name is None:
        return []
    if name.startswith("drop_"):
        return _domain_drop(name[5:])
    return FEATURE_SETS[name]


def design(lead: int, fb: FeatureBuilder | None = None, lab: pd.DataFrame | None = None, area: str | None = None) -> pd.DataFrame:
    fb = fb or (FeatureBuilder(area=area) if area else FeatureBuilder())
    lab = (labels(area) if area else labels()) if lab is None else lab
    last_target = int(lab["qi"].max())
    X = fb.matrix(lead, qindex(FIRST_ISSUE), last_target - lead, lab)
    pub = lab.set_index("quarter")["published"]
    X["target_published"] = X["target_quarter"].map(pub)
    X["tqi"] = X["target_quarter"].map(qindex)
    X["issue_ts"] = pd.to_datetime(X["issue_date"])
    return X


def metrics(y: np.ndarray, p: np.ndarray, base: np.ndarray | None = None) -> dict:
    y, p = np.asarray(y, int), np.asarray(p, float)
    yhat = (p >= 0.5).astype(int)
    n = len(y)
    if n == 0:
        return {"n": 0}
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[0, 1]).ravel()
    out = {"n": int(n), "n_high": int(y.sum()), "n_low": int(n - y.sum()),
           "accuracy": float((yhat == y).mean()),
           "precision": float(tp / (tp + fp)) if tp + fp else None,
           "recall": float(tp / (tp + fn)) if tp + fn else None,
           "f1": float(2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else None,
           "fpr": float(fp / (fp + tn)) if fp + tn else None,
           "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(np.round(p, 9))) > 1 else None,
           "brier": float(np.mean((p - y) ** 2)),
           "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn), "predicted_high_share": float(yhat.mean())}
    if base is not None:
        bc = float(np.mean((np.asarray(base, float) - y) ** 2))
        out["brier_climatology"] = bc
        out["brier_skill"] = float(1 - out["brier"] / bc) if bc > 0 else None
    return out


def _fit_predict(spec, tr, te):
    kind, fs = spec
    m = Model(kind, feature_list(fs)).fit(tr, tr["y"].to_numpy(int))
    return m, m.predict_proba(te)


def walk_forward(lead: int, limit: int | None = None, X: pd.DataFrame | None = None,
                 chunk: tuple[int, int] | None = None) -> dict:
    """chunk=(k, n): evaluate only every n-th origin starting at k, so origins can be spread over processes."""
    X = design(lead) if X is None else X
    L = X[X["y"].notna()].reset_index(drop=True)
    ev = L[L["tqi"] >= qindex(EVAL_FIRST_TARGET)]
    if limit:
        ev = ev.iloc[:limit]
    if chunk:
        ev = ev.iloc[chunk[0]::chunk[1]]
    rows, gaps, choices = [], [], []
    for i, r in ev.iterrows():
        tr = L[L["target_published"] <= r["issue_ts"]]
        te = L.loc[[i]]
        rec = {"lead": lead, "issue_quarter": r["issue_quarter"], "target_quarter": r["target_quarter"],
               "y": int(r["y"]), "hunger_target": r["hunger_target"], "hunger_last": r["hunger_last"],
               "n_train": int(len(tr)), "train_high_share": float(tr["y"].mean())}
        for name, spec in SPECS.items():
            m, p = _fit_predict(spec, tr, te)
            rec[name] = float(p[0])
            if name == PROPOSED:
                ptr = m.predict_proba(tr)
                gaps.append({"target_quarter": r["target_quarter"], "train_accuracy": float(((ptr >= .5) == tr["y"]).mean()),
                             "oos_correct": int((p[0] >= .5) == r["y"])})
                choices.append(m.choice)
        reg = lgbm_regressor()
        cols = [c for c in FEATURE_SETS["full"] if tr[c].notna().sum() >= 5]
        reg.fit(tr[cols], tr["hunger_target"])
        rec["level_lgbm"] = float(reg.predict(te[cols])[0])
        rows.append(rec)
    return {"lead": lead, "oos": pd.DataFrame(rows), "gaps": pd.DataFrame(gaps), "choices": choices}


def permutation_control(lead: int, n_perm: int = 20, seed: int = 7, X: pd.DataFrame | None = None,
                        perm_ids: list[int] | None = None) -> dict:
    """Shuffle training labels at every origin: a model that learns real signal should lose it (AUC -> 0.5)."""
    X = design(lead) if X is None else X
    L = X[X["y"].notna()].reset_index(drop=True)
    ev = L[L["tqi"] >= qindex(EVAL_FIRST_TARGET)]
    aucs = []
    for k in (perm_ids if perm_ids is not None else range(n_perm)):
        rng = np.random.default_rng([seed, k])
        ps = []
        for i, r in ev.iterrows():
            tr = L[L["target_published"] <= r["issue_ts"]].copy()
            tr["y"] = rng.permutation(tr["y"].to_numpy())
            m = Model("lgbm", FEATURE_SETS["full"], select=False).fit(tr, tr["y"].to_numpy(int))
            ps.append(m.predict_proba(L.loc[[i]])[0])
        aucs.append(roc_auc_score(ev["y"].astype(int), ps))
    return {"lead": lead, "n_perm": n_perm, "auc_mean": float(np.mean(aucs)), "auc_sd": float(np.std(aucs)),
            "aucs": [float(a) for a in aucs]}


def block_bootstrap_diff(a: np.ndarray, b: np.ndarray, block: int = 4, reps: int = 2000, seed: int = 11):
    """Mean of (a - b) with a moving-block bootstrap 95% interval (serial dependence across quarters)."""
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    rng = np.random.default_rng(seed)
    starts = np.arange(0, max(n - block + 1, 1))
    k = int(np.ceil(n / block))
    bs = [d[np.concatenate([np.arange(s, min(s + block, n)) for s in rng.choice(starts, k)])[:n]].mean() for _ in range(reps)]
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def mcnemar_p(correct_a: np.ndarray, correct_b: np.ndarray) -> float:
    from scipy.stats import binomtest
    b = int(((correct_a == 1) & (correct_b == 0)).sum())
    c = int(((correct_a == 0) & (correct_b == 1)).sum())
    return float(binomtest(b, b + c, 0.5).pvalue) if b + c else 1.0


def summarise(oos: pd.DataFrame) -> dict:
    res = {}
    for lead, g in oos.groupby("lead"):
        y = g["y"].to_numpy(int)
        clim = g["Climatology (base rate)"].to_numpy(float)
        per = {}
        for name in SPECS:
            p = g[name].to_numpy(float)
            mm = metrics(y, p, clim)
            mm["eras"] = {}
            for era, a, b in ERAS:
                sel = g["target_quarter"].str[:4].astype(int).between(a, b).to_numpy()
                mm["eras"][era] = metrics(y[sel], p[sel], clim[sel])
            per[name] = mm
        # comparisons vs persistence and vs the proposed model
        comp = {}
        pp = g[PROPOSED].to_numpy(float)
        for name in SPECS:
            if name == PROPOSED:
                continue
            q = g[name].to_numpy(float)
            bd = block_bootstrap_diff((pp - y) ** 2, (q - y) ** 2)
            comp[name] = {"brier_diff_proposed_minus_other": bd[0], "ci95": [bd[1], bd[2]],
                          "accuracy_diff": float(((pp >= .5) == y).mean() - ((q >= .5) == y).mean()),
                          "mcnemar_p": mcnemar_p(((pp >= .5) == y).astype(int), ((q >= .5) == y).astype(int))}
        lvl = {"mae_lgbm": float(np.mean(np.abs(g["level_lgbm"] - g["hunger_target"]))),
               "mae_persistence": float(np.mean(np.abs(g["hunger_last"] - g["hunger_target"]))), "n": int(len(g))}
        lvl["mae_skill_vs_persistence"] = float(1 - lvl["mae_lgbm"] / lvl["mae_persistence"])
        res[int(lead)] = {"models": per, "vs_proposed": comp, "level": lvl, "reliability": reliability(per[PROPOSED])}
    return res


def reliability(m: dict) -> dict:
    chk = {
        "accuracy": m["accuracy"] >= RELIABILITY["accuracy"],
        "recall": (m["recall"] or 0) >= RELIABILITY["recall"],
        "precision": (m["precision"] or 0) >= RELIABILITY["precision"],
        "auc": (m["auc"] or 0) >= RELIABILITY["auc"],
        "brier_skill": (m.get("brier_skill") or -1) > RELIABILITY["brier_skill"],
        "era_accuracy": all(e.get("accuracy", 0) >= RELIABILITY["era_accuracy"] for e in m["eras"].values() if e.get("n")),
    }
    return {"checks": chk, "reliable": all(chk.values())}


def max_reliable_lead(summary: dict) -> int | None:
    best = None
    for L in sorted(summary):
        if summary[L]["reliability"]["reliable"]:
            best = L
        else:
            break
    return best


TRANSFER_FEATURES = ["hunger_last", "hunger_last_anom", "hunger_age_q", "oni", "unemp_rate", "unemp_yoy", "remit_yoy",
                     "gdelt_shortage", "gdelt_agri_supply", "gdelt_jobs_income", "gdelt_assistance"]
TRANSFER_AREAS = ["metro_manila", "visayas", "mindanao"]


def area_transfer(lead: int) -> dict:
    """Geographic generalisation: LightGBM trained on Balance Luzon rows only (area-agnostic features: the area's own
    hunger history and national indicators), applied to the other SWS areas at the same origins."""
    src = design(lead)
    S_ = src[src["y"].notna()].reset_index(drop=True)
    out = {}
    for area in TRANSFER_AREAS:
        T = design(lead, area=area)
        T = T[T["y"].notna() & (T["tqi"] >= qindex(EVAL_FIRST_TARGET))]
        ys, pl, pp = [], [], []
        for _, r in T.iterrows():
            tr = S_[S_["target_published"] <= r["issue_ts"]]
            m = Model("lgbm", TRANSFER_FEATURES).fit(tr, tr["y"].to_numpy(int))
            te = pd.DataFrame([r])
            ys.append(int(r["y"]))
            pl.append(float(m.predict_proba(te)[0]))
            pp.append(float(r["hunger_last_anom"] > 0))
        out[area] = {"lgbm_trained_on_balance_luzon": metrics(np.array(ys), np.array(pl)),
                     "area_persistence": metrics(np.array(ys), np.array(pp))}
    return {"lead": lead, "areas": out}


def _wf_task(args):
    lead, X, chunk = args
    return walk_forward(lead, X=X, chunk=chunk)


def _perm_task(args):
    lead, X, k = args
    return permutation_control(lead, X=X, perm_ids=[k])


def run(parallel: bool = True, perm: bool = True, n_perm: int = 20, workers: int | None = None) -> dict:
    import os
    workers = workers or max(1, (os.cpu_count() or 4) - 2)
    if parallel:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            designs = dict(zip(LEADS, ex.map(design, LEADS)))
            n_chunks = max(1, workers // len(LEADS))
            parts = list(ex.map(_wf_task, [(L, designs[L], (k, n_chunks)) for L in LEADS for k in range(n_chunks)]))
            pp = list(ex.map(_perm_task, [(L, designs[L], k) for L in [1, 2] for k in range(n_perm)])) if perm else []
            transfer = list(ex.map(area_transfer, LEADS))
    else:
        designs = {L: design(L) for L in LEADS}
        parts = [walk_forward(L, X=designs[L]) for L in LEADS]
        pp = [permutation_control(L, X=designs[L], perm_ids=[k]) for L in [1, 2] for k in range(n_perm)] if perm else []
        transfer = [area_transfer(L) for L in LEADS]
    outs = []
    for L in LEADS:
        mine = [o for o in parts if o["lead"] == L]
        oos = pd.concat([o["oos"] for o in mine]).sort_values("target_quarter").reset_index(drop=True)
        gaps = pd.concat([o["gaps"] for o in mine]).sort_values("target_quarter").reset_index(drop=True)
        outs.append({"lead": L, "oos": oos, "gaps": gaps, "choices": sum((o["choices"] for o in mine), [])})
    perms = []
    for L in ([1, 2] if perm else []):
        aucs = [a for o in pp if o["lead"] == L for a in o["aucs"]]
        perms.append({"lead": L, "n_perm": len(aucs), "auc_mean": float(np.mean(aucs)), "auc_sd": float(np.std(aucs)),
                      "aucs": aucs})
    oos = pd.concat([o["oos"] for o in outs], ignore_index=True)
    oos.to_csv(OUT / "walkforward_predictions.csv", index=False, lineterminator="\n")
    gaps = pd.concat([o["gaps"].assign(lead=o["lead"]) for o in outs], ignore_index=True)
    gaps.to_csv(OUT / "overfit_train_vs_oos.csv", index=False, lineterminator="\n")
    summary = summarise(oos)
    audit = {"train_vs_oos": {int(o["lead"]): {"mean_train_accuracy": float(o["gaps"]["train_accuracy"].mean()),
                                              "oos_accuracy": float(o["gaps"]["oos_correct"].mean()),
                                              "config_choices": pd.Series(o["choices"]).value_counts().to_dict()}
                              for o in outs},
             "label_permutation": perms,
             "geographic_transfer": {t["lead"]: t["areas"] for t in transfer}}
    result = {"summary": summary, "max_reliable_lead": max_reliable_lead(summary), "audit": audit,
              "protocol": {"leads": LEADS, "eval_first_target": EVAL_FIRST_TARGET, "eras": ERAS,
                           "reliability": RELIABILITY, "specs": {k: list(v) if v else None for k, v in SPECS.items()}}}
    (OUT / "evaluation.json").write_text(json.dumps(result, indent=1, default=str))
    return result


def label_noise_diagnostic() -> dict:
    """Post-hoc (written after the locked run; changes no model): share of evaluated labels whose anomaly is inside the
    SWS margin of error, and every model's accuracy on the quarters where the anomaly exceeds it."""
    from app.fi5.sources import sws_rounds
    lab = labels().set_index("quarter")
    moe = sws_rounds().groupby("quarter")["area_moe_bl"].max()
    pr = pd.read_csv(OUT / "walkforward_predictions.csv")
    pr["anomaly"] = pr["target_quarter"].map(lab["anomaly"])
    pr["moe"] = pr["target_quarter"].map(moe).fillna(6.0)
    pr["clear"] = pr["anomaly"].abs() >= pr["moe"]
    out = {"note": "post-hoc diagnostic after the locked evaluation; not used to choose or change any model",
           "share_labels_within_moe": float((~pr.drop_duplicates("target_quarter")["clear"]).mean()),
           "n_target_quarters": int(pr["target_quarter"].nunique()), "by_lead": {}}
    for lead, g in pr.groupby("lead"):
        c = g[g["clear"]]
        out["by_lead"][int(lead)] = {"n_clear": int(len(c)), "n_clear_high": int(c["y"].sum()),
                                     **{name: float(((c[name] >= .5) == c["y"]).mean()) if len(c) else None
                                        for name in [PROPOSED, *BASELINES]}}
    (OUT / "label_noise_diagnostic.json").write_text(json.dumps(out, indent=1))
    return out
