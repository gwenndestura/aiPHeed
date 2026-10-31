"""E128 runner (E128_FROZEN_EXPERIMENT_PROTOCOL.md, hash checked): five models, direct leads 1-4, expanding-window
walk-forward on the regional SWS Balance Luzon target; frozen R1-R7; robustness (seeds, ablation, calibration, SHAP).
Offline only; reads the E119 / FINAL_FOOD_INSECURITY_LIGHTGBM inputs, writes under E128 only.

    python run_e128.py
"""
from __future__ import annotations

import hashlib
import json
import pickle
import sys
import warnings
from datetime import date
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from scipy.stats import binomtest
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
MODELS = ROOT / "models"
sys.path.insert(0, str(HERE))
import build_panel as BP  # noqa: E402

warnings.filterwarnings("ignore")
PROTOCOL = ROOT / "E128_FROZEN_EXPERIMENT_PROTOCOL.md"
SEED, BOOT_SEED, N_BOOT = 128, 2026, 2000
MIN_TRAIN, MIN_CLASS, INNER_LAST = 6, 2, 3
LGB_FIXED = dict(objective="binary", learning_rate=0.1, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
                 reg_lambda=1.0, min_data_in_bin=1, deterministic=True, force_col_wise=True, verbose=-1, n_jobs=1)
LGB_GRID = [dict(num_leaves=nl, n_estimators=ne, min_child_samples=mc, class_weight=cw)
            for nl in (2, 4) for ne in (25, 75) for mc in (2, 4) for cw in (None, "balanced")]
LR_GRID = [dict(C=c, class_weight=cw) for c in (0.1, 1.0) for cw in (None, "balanced")]
FEATS = {"M1_LightGBM": BP.ALL_FEATURES, "M3_PSA_only": BP.OFFICIAL, "M4_NLP_only": BP.NEWS, "M5_LogReg": BP.ALL_FEATURES}
MODEL_ORDER = ["M1_LightGBM", "M2_Persistence", "M3_PSA_only", "M4_NLP_only", "M5_LogReg"]
TARGETS = ("T1", "T4")


def check_protocol():
    h = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    assert h == (HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "protocol hash mismatch"
    return h


# ------------------------------------------------------------------ data and targets
def panel_with_targets():
    p, r = BP.build()
    med4, pers4 = [], []
    for _, row in p.iterrows():
        km = BP.known_quarter_means(r, date.fromisoformat(row["issue_date"]))
        med4.append(km.tail(4).mean() if len(km) else np.nan)
        prior = km.iloc[:-1].tail(4)                 # the 4 known quarters before the newest one
        pers4.append(float(km.iloc[-1] > prior.mean()) if len(prior) else np.nan)
    p["trail4_mean_at_issue"] = med4
    p["T1"] = p["y_high"]
    p["T4"] = np.where(p["y_bl_hunger"].notna() & p["trail4_mean_at_issue"].notna(),
                       (p["y_bl_hunger"] > p["trail4_mean_at_issue"]).astype(float), np.nan)
    p["persist_T1"] = np.where(p["H1_bl_latest"].notna(), (p["H1_bl_latest"] > BP.HUNGER_THRESHOLD).astype(float), np.nan)
    p["persist_T4"] = pers4
    p["y_pub_date"] = pd.to_datetime(p["y_published"].replace("", np.nan))
    return p, r


def training_rows(p, t, k, target):
    iss = pd.Timestamp(BP.qstart(t + 1))
    d = p[(p["lead"] == k) & p[target].notna() & (p["y_pub_date"] < iss)]
    return d.sort_values(["y_pub_date", "target_q"])


def eligible(tr, target):
    return len(tr) >= MIN_TRAIN and tr[target].sum() >= MIN_CLASS and (len(tr) - tr[target].sum()) >= MIN_CLASS


# ------------------------------------------------------------------ models
def fit_lgb(X, y, g, seed=SEED):
    m = lgb.LGBMClassifier(**LGB_FIXED, **g, random_state=seed)
    m.fit(X, y)
    return m


def fit_lr(X, y, g):
    m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                      LogisticRegression(C=g["C"], class_weight=g["class_weight"], max_iter=2000))
    m.fit(X, y)
    return m


def proba(m, X):
    return float(m.predict_proba(X)[:, 1][0]) if len(X) == 1 else m.predict_proba(X)[:, 1]


def logloss(y, q):
    q = np.clip(q, 1e-6, 1 - 1e-6)
    return float(-(y * np.log(q) + (1 - y) * np.log(1 - q)))


def inner_select(tr, feats, target, kind, seed=SEED):
    grid = LGB_GRID if kind == "lgb" else LR_GRID
    best, best_s, scores = grid[0], np.inf, []
    for g in grid:
        ls = []
        for j in range(len(tr) - INNER_LAST, len(tr)):
            vrow = tr.iloc[[j]]
            itr = tr[tr["y_pub_date"] < vrow["y_pub_date"].iloc[0]]
            if len(itr) < 4 or itr[target].nunique() < 2:
                continue
            m = fit_lgb(itr[feats], itr[target], g, seed) if kind == "lgb" else fit_lr(itr[feats], itr[target], g)
            ls.append(logloss(vrow[target].iloc[0], proba(m, vrow[feats])))
        s = float(np.mean(ls)) if ls else np.nan
        scores.append(s)
        if ls and s < best_s - 1e-12:
            best, best_s = g, s
    return best, (best_s if np.isfinite(best_s) else np.nan), int(sum(np.isfinite(scores)))


# ------------------------------------------------------------------ metrics
def metrics(y, q):
    y, q = np.asarray(y, float), np.asarray(q, float)
    c = (q >= 0.5).astype(float)
    tp, tn = int(((c == 1) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum())
    fp, fn = int(((c == 1) & (y == 0)).sum()), int(((c == 0) & (y == 1)).sum())
    npos, nneg = int((y == 1).sum()), int((y == 0).sum())
    rec = tp / npos if npos else np.nan
    spec = tn / nneg if nneg else np.nan
    prec = tp / (tp + fp) if (tp + fp) else np.nan
    both = npos > 0 and nneg > 0
    return dict(n=len(y), n_pos=npos, n_neg=nneg, tp=tp, fp=fp, tn=tn, fn=fn, accuracy=float((c == y).mean()) if len(y) else np.nan,
                balanced_accuracy=float((rec + spec) / 2) if both else np.nan, precision=prec, recall=rec, low_recall=spec,
                f1=(2 * prec * rec / (prec + rec)) if (prec == prec and rec == rec and (prec + rec) > 0) else np.nan,
                roc_auc=float(roc_auc_score(y, q)) if both else np.nan, pr_auc=float(average_precision_score(y, q)) if both else np.nan,
                brier=float(np.mean((q - y) ** 2)) if len(y) else np.nan, mean_prob=float(q.mean()) if len(y) else np.nan,
                high_share=float(y.mean()) if len(y) else np.nan)


def boot_p(loss_a, loss_b, seed=BOOT_SEED):
    """One-sided p for mean(loss_a - loss_b) < 0, paired bootstrap over target quarters."""
    d = np.asarray(loss_a) - np.asarray(loss_b)
    if len(d) == 0:
        return np.nan
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(N_BOOT, len(d)))
    return float((d[idx].mean(axis=1) >= 0).mean())


def mcnemar_p(ca, cb):
    b = int(((ca == 1) & (cb == 0)).sum())
    c = int(((ca == 0) & (cb == 1)).sum())
    return float(binomtest(b, b + c, 0.5, alternative="greater").pvalue) if (b + c) else 1.0, b, c


def holm(ps):
    order = np.argsort(ps)
    adj, run = np.empty(len(ps)), 0.0
    for i, j in enumerate(order):
        run = max(run, min(1.0, (len(ps) - i) * ps[j]))
        adj[j] = run
    return adj


def reliability(rows, mname):
    """Frozen R1-R7 on one model's outer rows (rows: one per target quarter, with q_<model>, persist, clim, maj)."""
    y = rows["y"].to_numpy(float)
    q = rows[f"q_{mname}"].to_numpy(float)
    m = metrics(y, q)
    c = (q >= 0.5).astype(float)
    acc_maj = float((rows["maj"].to_numpy() == y).mean())
    acc_per = float((rows["persist"].to_numpy() == y).mean())
    bl = (q - y) ** 2
    p_per = boot_p(bl, (rows["persist"].to_numpy(float) - y) ** 2)
    p_clim = boot_p(bl, (rows["clim"].to_numpy(float) - y) ** 2)
    br_per = float(np.mean((rows["persist"] - y) ** 2))
    br_clim = float(np.mean((rows["clim"] - y) ** 2))
    tq = rows["target_q"].to_numpy()
    order = np.argsort(tq)
    thirds = [order[i::1] for i in range(1)]
    parts = np.array_split(order, 3) if len(order) >= 3 else [order]
    acc_thirds = [float((c[ix] == y[ix]).mean()) for ix in parts if len(ix)]
    loqo = [float((np.delete(c, i) == np.delete(y, i)).mean()) for i in range(len(y))] if len(y) > 1 else [np.nan]
    nq = len(set(tq))
    R = {
        "R1": nq >= 10 and len(y) >= 40,
        "R1_quarters_only (sensitivity)": nq >= 10,
        "R2": m["accuracy"] >= 0.75,
        "R3": bool(m["balanced_accuracy"] >= 0.70) if m["balanced_accuracy"] == m["balanced_accuracy"] else False,
        "R4": m["accuracy"] > acc_maj and m["accuracy"] > acc_per,
        "R5": (m["brier"] < br_per and p_per < 0.10) and (m["brier"] < br_clim and p_clim < 0.10),
        "R6": bool(m["precision"] >= 0.60 and m["recall"] >= 0.60) if (m["precision"] == m["precision"] and m["recall"] == m["recall"]) else False,
        "R7": (min(acc_thirds) >= 0.60 if acc_thirds else False) and (np.nanmin(loqo) >= 0.70 if len(y) > 1 else False),
    }
    passed = all(R[k] for k in ("R1", "R2", "R3", "R4", "R5", "R6", "R7"))
    passed_sens = all(R[k] for k in ("R1_quarters_only (sensitivity)", "R2", "R3", "R4", "R5", "R6", "R7"))
    detail = dict(acc_majority=acc_maj, acc_persistence=acc_per, brier_persistence=br_per, brier_clim=br_clim,
                  p_brier_vs_persistence=p_per, p_brier_vs_clim=p_clim, acc_thirds=acc_thirds,
                  loqo_min_acc=float(np.nanmin(loqo)) if len(y) > 1 else np.nan, n_target_quarters=nq)
    return m, R, passed, passed_sens, detail


# ------------------------------------------------------------------ walk-forward
def walk_forward(p, target, feats_override=None, seed=SEED, keep=False, models=None):
    """Return predictions (one row per model x lead x origin) and fold records."""
    models = models or MODEL_ORDER
    preds, folds, artifacts, shap_rows = [], [], [], []
    for k in BP.LEADS:
        ev = p[(p["lead"] == k) & p[target].notna()].sort_values("t")
        for _, row in ev.iterrows():
            t = int(row["t"])
            tr = training_rows(p, t, k, target)
            if not eligible(tr, target):
                continue
            x1 = p[(p["lead"] == k) & (p["t"] == t)]
            base = dict(target=target, lead=k, origin=row["origin"], t=t, issue_date=row["issue_date"], target_quarter=row["target_quarter"],
                        target_q=int(row["target_q"]), y=float(row[target]), y_bl_hunger=float(row["y_bl_hunger"]),
                        y_published=row["y_published"], clim=float(tr[target].mean()), maj=float(tr[target].mean() >= 0.5),
                        persist=float(row[f"persist_{target}"]), n_train=len(tr), n_train_high=int(tr[target].sum()),
                        train_first_target=tr["target_quarter"].iloc[0], train_last_target=tr["target_quarter"].iloc[-1])
            for mname in models:
                rec = dict(base, model=mname)
                if mname == "M2_Persistence":
                    q, g, inner, nscored, tr_q = base["persist"], {}, np.nan, 0, None
                else:
                    feats = feats_override if (feats_override is not None and mname == "M1_LightGBM") else FEATS[mname]
                    kind = "lr" if mname == "M5_LogReg" else "lgb"
                    g, inner, nscored = inner_select(tr, feats, target, kind, seed)
                    m = fit_lgb(tr[feats], tr[target], g, seed) if kind == "lgb" else fit_lr(tr[feats], tr[target], g)
                    q = proba(m, x1[feats])
                    tr_q = m.predict_proba(tr[feats])[:, 1]
                    tm = metrics(tr[target].to_numpy(), tr_q)
                    rec.update(train_accuracy=tm["accuracy"], train_brier=tm["brier"], train_auc=tm["roc_auc"])
                    if kind == "lgb":
                        rec["n_trees_with_splits"] = int(sum(1 for tinfo in m.booster_.dump_model()["tree_info"] if tinfo["num_leaves"] > 1))
                    if keep:
                        tag = f"{target}_{mname}_L{k}_{row['origin']}"
                        path = MODELS / f"{tag}.{'txt' if kind == 'lgb' else 'pkl'}"
                        if kind == "lgb":
                            m.booster_.save_model(str(path))
                        else:
                            path.write_bytes(pickle.dumps(m))
                        artifacts.append(dict(model_id=f"E128-{tag}", target=target, model=mname, lead=k, origin=row["origin"],
                                              file=f"models/{path.name}", sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                              features=";".join(feats), params=json.dumps(g),
                                              preprocessing="native NaN" if kind == "lgb" else "median impute + standardize (train fold)",
                                              training_targets=f"{base['train_first_target']}..{base['train_last_target']}",
                                              n_train=len(tr), seed=seed if kind == "lgb" else "n/a (deterministic lbfgs)"))
                        if mname == "M1_LightGBM":
                            sv = shap.TreeExplainer(m.booster_).shap_values(x1[feats])
                            sv = sv[1] if isinstance(sv, list) else sv
                            shap_rows.append(dict(target=target, lead=k, origin=row["origin"], target_quarter=row["target_quarter"],
                                                  q=q, y=base["y"], **{f: float(v) for f, v in zip(feats, np.ravel(sv))}))
                rec.update(q=float(q), cls=float(q >= 0.5), params=json.dumps(g), inner_logloss=inner, inner_points_scored=nscored)
                preds.append(rec)
    return pd.DataFrame(preds), artifacts, pd.DataFrame(shap_rows)


def wide(pr):
    w = pr.pivot_table(index=["target", "lead", "origin", "t", "target_q", "target_quarter", "y", "persist", "clim", "maj"],
                       columns="model", values="q").reset_index()
    w.columns = [c if not isinstance(c, tuple) else c[0] for c in w.columns]
    return w.rename(columns={m: f"q_{m}" for m in MODEL_ORDER if m in w.columns})


def summarize(pr, label=""):
    out = []
    w = wide(pr)
    for (tg, k), rows in w.groupby(["target", "lead"]):
        for mname in [m for m in MODEL_ORDER if f"q_{m}" in rows]:
            for block, rr in (("ALL", rows), ("DEV", rows[rows["target_q"] <= 2024 * 4 + 3]), ("LATER", rows[rows["target_q"] > 2024 * 4 + 3])):
                if not len(rr):
                    continue
                m, R, ok, oks, det = reliability(rr, mname)
                out.append(dict(variant=label, target=tg, lead=k, model=mname, block=block, **m, **{f"pass_{a}": b for a, b in R.items()},
                                reliable=ok, reliable_if_R1_quarters_only=oks, **{a: (json.dumps(b) if isinstance(b, list) else b) for a, b in det.items()}))
    return pd.DataFrame(out)


def max_lead(summ, model, target, col="reliable"):
    s = summ[(summ["model"] == model) & (summ["target"] == target) & (summ["block"] == "ALL")].set_index("lead")
    K = 0
    for k in BP.LEADS:
        if k in s.index and bool(s.loc[k, col]):
            K = k
        else:
            break
    return K


def pairwise(pr):
    w = wide(pr)
    res = []
    for (tg, k), rows in w.groupby(["target", "lead"]):
        y = rows["y"].to_numpy(float)
        q1 = rows["q_M1_LightGBM"].to_numpy(float)
        ps, recs = [], []
        for b in ["M2_Persistence", "M3_PSA_only", "M4_NLP_only", "M5_LogReg"]:
            qb = rows[f"q_{b}"].to_numpy(float)
            pb = boot_p((q1 - y) ** 2, (qb - y) ** 2)
            pm, nb, nc = mcnemar_p(((q1 >= 0.5) == y).astype(int), ((qb >= 0.5) == y).astype(int))
            recs.append(dict(target=tg, lead=k, baseline=b, n=len(y), brier_lgbm=float(np.mean((q1 - y) ** 2)), brier_baseline=float(np.mean((qb - y) ** 2)),
                             acc_lgbm=float(((q1 >= 0.5) == y).mean()), acc_baseline=float(((qb >= 0.5) == y).mean()),
                             p_brier_one_sided=pb, mcnemar_p_one_sided=pm, lgbm_only_correct=nb, baseline_only_correct=nc))
            ps.append(pb)
        adj = holm(np.array(ps))
        for r_, a in zip(recs, adj):
            r_["p_brier_holm"] = float(a)
            r_["lgbm_better_significant"] = bool(a < 0.05)
            res.append(r_)
    return pd.DataFrame(res)


def calibration_table(pr):
    rows = []
    bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0001]
    for (tg, k, mname), g in pr.groupby(["target", "lead", "model"]):
        for lo, hi in zip(bins[:-1], bins[1:]):
            s = g[(g["q"] >= lo) & (g["q"] < hi)]
            rows.append(dict(target=tg, lead=k, model=mname, bin=f"[{lo:.1f},{min(hi, 1):.1f}]", n=len(s),
                             mean_prob=float(s["q"].mean()) if len(s) else np.nan, observed_high=float(s["y"].mean()) if len(s) else np.nan))
    return pd.DataFrame(rows)


def main():
    h = check_protocol()
    OUT.mkdir(exist_ok=True)
    MODELS.mkdir(exist_ok=True)
    p, r = panel_with_targets()
    assert p["t"].min() >= 2021 * 4
    # issue-date / lead mapping and class distribution
    p.drop(columns=["y_pub_date"]).to_csv(OUT / "panel.csv", index=False)
    preds, arts, sh = [], [], []
    for tg in TARGETS:
        pr, a, s = walk_forward(p, tg, keep=True)
        preds.append(pr), arts.extend(a), sh.append(s)
    pr = pd.concat(preds, ignore_index=True)
    summ = summarize(pr)
    pw = pairwise(pr)
    cal = calibration_table(pr)
    # seeds (M1 only)
    seed_rows = []
    for sd in (1, 2, 3, 4):
        for tg in TARGETS:
            ps_, _, _ = walk_forward(p, tg, seed=sd, models=["M1_LightGBM", "M2_Persistence"])
            ss = summarize(ps_)
            ss = ss[(ss["model"] == "M1_LightGBM") & (ss["block"] == "ALL")]
            for _, x in ss.iterrows():
                seed_rows.append(dict(seed=sd, target=tg, lead=x["lead"], accuracy=x["accuracy"], brier=x["brier"], recall=x["recall"],
                                      balanced_accuracy=x["balanced_accuracy"], reliable=x["reliable"]))
    base_s = summ[(summ["model"] == "M1_LightGBM") & (summ["block"] == "ALL")]
    for _, x in base_s.iterrows():
        seed_rows.append(dict(seed=SEED, target=x["target"], lead=x["lead"], accuracy=x["accuracy"], brier=x["brier"], recall=x["recall"],
                              balanced_accuracy=x["balanced_accuracy"], reliable=x["reliable"]))
    # ablation (M1 only, identical rows)
    abl = []
    variants = {"all_features": BP.ALL_FEATURES}
    for gname in ("market", "climate", "employment_ofw", "news_nlp", "poverty_vulnerability", "hunger_history"):
        variants[f"without_{gname}"] = [f for f in BP.ALL_FEATURES if f not in BP.GROUPS[gname]]
    variants["without_production"] = [f for f in BP.ALL_FEATURES if f not in BP.PRODUCTION]
    variants["without_all_five_triggers"] = list(BP.GROUPS["hunger_history"])
    for vname, fl in variants.items():
        for tg in TARGETS:
            ps_, _, _ = walk_forward(p, tg, feats_override=fl, models=["M1_LightGBM", "M2_Persistence"])
            ss = summarize(ps_, vname)
            ss = ss[(ss["model"] == "M1_LightGBM") & (ss["block"] == "ALL")]
            for _, x in ss.iterrows():
                abl.append(dict(variant=vname, target=tg, lead=x["lead"], n=x["n"], n_features=len(fl), accuracy=x["accuracy"], brier=x["brier"],
                                balanced_accuracy=x["balanced_accuracy"], recall=x["recall"], low_recall=x["low_recall"], roc_auc=x["roc_auc"],
                                identical_to_all=bool(set(fl) == set(BP.ALL_FEATURES))))
    abl = pd.DataFrame(abl)
    allr = abl[abl["variant"] == "all_features"].set_index(["target", "lead"])
    abl["delta_brier_vs_all (removal effect; + = group helped)"] = [x["brier"] - allr.loc[(x["target"], x["lead"]), "brier"] for _, x in abl.iterrows()]
    abl["delta_accuracy_vs_all"] = [x["accuracy"] - allr.loc[(x["target"], x["lead"]), "accuracy"] for _, x in abl.iterrows()]

    pr.to_csv(OUT / "predictions_raw.csv", index=False)
    summ.to_csv(OUT / "summary_metrics.csv", index=False)
    pw.to_csv(OUT / "pairwise_vs_baselines.csv", index=False)
    cal.to_csv(OUT / "calibration_bins.csv", index=False)
    pd.DataFrame(seed_rows).to_csv(OUT / "seed_sensitivity.csv", index=False)
    abl.to_csv(OUT / "ablation.csv", index=False)
    pd.DataFrame(arts).to_csv(OUT / "artifacts.csv", index=False)
    shp = pd.concat(sh, ignore_index=True)
    shp.to_csv(OUT / "shap_outer_rows.csv", index=False)
    horizon = {tg: {m: max_lead(summ, m, tg) for m in MODEL_ORDER} for tg in TARGETS}
    horizon_sens = {tg: {m: max_lead(summ, m, tg, "reliable_if_R1_quarters_only") for m in MODEL_ORDER} for tg in TARGETS}
    json.dump(dict(protocol_sha256=h, inputs=BP.input_hashes(), max_reliable_lead=horizon, max_lead_if_R1_quarters_only=horizon_sens,
                   n_predictions=len(pr), n_artifacts=len(arts)), open(OUT / "summary.json", "w"), indent=2)
    print(json.dumps(dict(max_reliable_lead=horizon, sens=horizon_sens), indent=1))


if __name__ == "__main__":
    main()
