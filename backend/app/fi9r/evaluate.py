"""FI9-R reassessment: independent SWS-only row builder (reproduces FI9), locked candidates, baselines, intervals,
uncertainty and robustness diagnostics, adoption decision.

    python -m app.fi9r.evaluate run      # refuses unless the FI9-R protocol lock matches

Outputs (data/fi9r/out): wf_predictions.csv (every model x target quarter), reassessment.json, adoption.json.
Production FI9 files are only read.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.fi5.sources import sws_rounds
from app.fi6.news_model import NEWSA
from app.fi6.target import labels, quarterly
from app.fi7 import models as M
from app.fi7.experiments import alternating_quarters, boot_delta
from app.fi9 import quarters as Q
from app.fi9.evaluate import DOMAIN_GOV, metrics, reliability
from app.fi9r import OUT
from app.fi9r.protocol import check
from app.paths import BACKEND_DIR

FI9_PRED = BACKEND_DIR / "data" / "fi9" / "baseline_20261103" / "lead1_predictions.csv"
BASELINE_Q, MIN_OBS, MIN_TRAIN, EVAL_FIRST = 20, 8, 20, "2010-Q1"
DOMAINS = {**DOMAIN_GOV, "news": list(NEWSA)}


# ------------------------------------------------------------------------------------------------ rows
def sws_series(shift_rule_dates: int = 0) -> pd.DataFrame:
    q = quarterly().copy()
    if shift_rule_dates:
        r = sws_rounds()
        rule_q = set(r.loc[r["source_type"].str.contains("rule"), "quarter"])
        m = q["quarter"].isin(rule_q)
        q.loc[m, "published"] = q.loc[m, "published"] + pd.Timedelta(days=shift_rule_dates)
    return q


def sws_rows(q: pd.DataFrame, live: pd.Timestamp | None = None) -> pd.DataFrame:
    """One row per operational issue date with the SWS inputs known then (FI9 definitions), built independently."""
    lab = labels().set_index("quarter")
    last_t = int(lab.index[lab["y"].notna()].map(Q.index).max())
    first = Q.index("1999-Q1")
    issues = [(i, Q.scheduled_issue(i)) for i in range(first, last_t)]
    if live is not None:
        issues.append((Q.qi_of(live), min(Q.scheduled_issue(Q.qi_of(live)), live)))
    rows = []
    for i, d in issues:
        t = i + 1
        k = q[q["published"] <= d]
        if not len(k):
            continue
        last = k.iloc[-1]
        win = k[(k["qi"] >= t - BASELINE_Q) & (k["qi"] < t)]["hunger"]
        base = float(win.mean()) if len(win) >= MIN_OBS else np.nan
        tq = Q.label(t)
        has = tq in lab.index and pd.notna(lab.loc[tq, "y"])
        rows.append({"issue_quarter": Q.label(i), "issue_date": d, "target_quarter": tq, "hunger_last": float(last["hunger"]),
                     "last_reading_quarter": last["quarter"], "hunger_age_q": t - int(last["qi"]), "baseline_known": base,
                     "moe_last": float(last["moe"]), "threshold_known": base + float(last["moe"]),
                     "y": float(lab.loc[tq, "y"]) if has else np.nan, "hunger_target": float(lab.loc[tq, "hunger"]) if has else np.nan,
                     "p_flip": float(lab.loc[tq, "p_flip"]) if has else np.nan,
                     "target_published": q.set_index("quarter")["published"].get(tq, pd.NaT)})
    X = pd.DataFrame(rows)
    X["delta_target"] = X["hunger_target"] - X["hunger_last"]
    return X


# ------------------------------------------------------------------------------------------------ local level
def _kalman(y, r, qv):
    """Local-level filter on a quarterly grid (NaN = no survey). Returns filtered mean/var at each step and loglik."""
    m, P, ll = np.nan, np.nan, 0.0
    ms, Ps = [], []
    for yt, rt in zip(y, r):
        if np.isnan(m):
            if not np.isnan(yt):
                m, P = yt, rt
        else:
            P = P + qv
            if not np.isnan(yt):
                S = P + rt
                ll += -0.5 * (np.log(2 * np.pi * S) + (yt - m) ** 2 / S)
                K = P / S
                m, P = m + K * (yt - m), (1 - K) * P
        ms.append(m)
        Ps.append(P)
    return np.array(ms), np.array(Ps), ll


QGRID = np.logspace(-1.5, 2, 36)


def local_level(q_known: pd.DataFrame, target_qi: int) -> dict:
    g = q_known.set_index("qi").reindex(range(int(q_known["qi"].min()), int(q_known["qi"].max()) + 1))
    y, r = g["hunger"].to_numpy(float), (g["se"] ** 2).to_numpy(float)
    best = max(QGRID, key=lambda qv: _kalman(y, r, qv)[2])
    ms, Ps, _ = _kalman(y, r, best)
    age = target_qi - int(q_known["qi"].max())
    r_next = float(np.nanmean(r[~np.isnan(y)][-4:]))
    return {"m": float(ms[-1]), "var_state": float(Ps[-1] + best * age), "r_next": r_next, "q": float(best)}


# ------------------------------------------------------------------------------------------------ walk-forward
def _tau(p, y):
    """FI7 rule: threshold maximising balanced accuracy on training predictions (0.1..0.9, 33 steps)."""
    best, tau = -1, 0.5
    if len(set(y)) == 2:
        for t in np.linspace(0.1, 0.9, 33):
            yh = p >= t
            ba = (np.mean(yh[y == 1]) + np.mean(~yh[y == 0])) / 2
            if ba > best + 1e-9:
                best, tau = ba, float(t)
    return tau


def _conf(res):
    res = np.sort(np.abs(res[~np.isnan(res)]))
    n = len(res)
    k = min(n - 1, int(np.ceil((n + 1) * 0.95)) - 1)
    return float(res[k]) if n >= 10 else np.nan


def walk_forward(X: pd.DataFrame, q: pd.DataFrame, feats: pd.DataFrame | None = None, with_domains: bool = True) -> pd.DataFrame:
    X = X.reset_index(drop=True)
    L = X[X["y"].notna()].reset_index(drop=True)
    # stage 1: every labelled row gets the base forecasts made with only its own issue-date information
    base = []
    for i, r in L.iterrows():
        tr = L[L["target_published"] <= r["issue_date"]]
        rec = {"i": i}
        if len(tr) >= MIN_TRAIN:
            dm = M.make("damped", []).fit(tr, tr["delta_target"].to_numpy(float))
            te = L.loc[[i]]
            rec.update(d_level=float(dm.predict_level(te)[0]), d_p=float(dm.predict_proba(te)[0]), d_sigma=dm.sigma)
        ll = local_level(q[q["published"] <= r["issue_date"]], Q.index(r["target_quarter"]))
        sd = np.sqrt(ll["var_state"] + ll["r_next"])
        rec.update(ll_m=ll["m"], ll_sd=sd, ll_p=float(1 - norm.cdf((r["threshold_known"] - ll["m"]) / sd)), ll_q=ll["q"])
        base.append(rec)
    B = pd.DataFrame(base).set_index("i")
    L = L.join(B)
    if feats is not None:
        L = L.merge(feats, on="issue_date", how="left")
    fi9 = pd.read_csv(FI9_PRED)
    out = []
    ev = L[L["target_quarter"] >= EVAL_FIRST]
    for i, r in ev.iterrows():
        tr = L[L["target_published"] <= r["issue_date"]]
        te = L.loc[[i]]
        y_tr = tr["y"].to_numpy(int)
        inner = tr.iloc[max(M.MIN_INNER_TRAIN, int(len(tr) * 0.6)):]          # FI7 inner-fold region
        inner = inner[inner["d_p"].notna()]
        common = {"issue_quarter": r["issue_quarter"], "issue_date": str(pd.Timestamp(r["issue_date"]).date()),
                  "target_quarter": r["target_quarter"], "y": int(r["y"]), "hunger_target": r["hunger_target"],
                  "hunger_last": r["hunger_last"], "p_flip": r["p_flip"], "n_train": len(tr),
                  "target_published": str(pd.Timestamp(r["target_published"]).date()),
                  "train_max_target_published": str(pd.Timestamp(tr["target_published"].max()).date())}

        def add(tag, p, cls, level=np.nan, lo=np.nan, hi=np.nan, clo=np.nan, chi=np.nan, tr_acc=np.nan, tr_brier=np.nan, **kw):
            out.append({**common, "tag": tag, "p": float(np.clip(p, 0, 1)), "cls": int(cls), "level_hat": level,
                        "pi95_lo": lo, "pi95_hi": hi, "cpi95_lo": clo, "cpi95_hi": chi, "train_acc": tr_acc, "train_brier": tr_brier, **kw})

        base_rate = float(y_tr.mean())
        add("Always LOW", base_rate, 0, tr_acc=1 - base_rate, tr_brier=float(np.mean((base_rate - y_tr) ** 2)))
        add("Always HIGH", base_rate, 1, tr_acc=base_rate, tr_brier=float(np.mean((base_rate - y_tr) ** 2)))
        nv = M.make("persist", []).fit(tr, tr["delta_target"].to_numpy(float))
        pn = float(nv.predict_proba(te)[0])
        ptr = nv.predict_proba(tr)
        add("Naive persistence", pn, pn >= 0.5, r["hunger_last"], r["hunger_last"] - 1.96 * nv.sigma, r["hunger_last"] + 1.96 * nv.sigma,
            tr_acc=float(((ptr >= 0.5) == y_tr).mean()), tr_brier=float(np.mean((ptr - y_tr) ** 2)))
        # C0: exactly the production FI9 configuration
        c0 = M.make("damped_tau", []).fit(tr, tr["delta_target"].to_numpy(float))
        p0, lv0, s0 = float(c0.predict_proba(te)[0]), float(c0.inner.predict_level(te)[0]), c0.sigma
        cw = _conf((inner["hunger_target"] - inner["d_level"]).to_numpy(float))
        ptr = c0.predict_proba(tr)
        add("C0 damped persistence (FI9)", p0, int(c0.predict_class(te)[0]), lv0, lv0 - 1.96 * s0, lv0 + 1.96 * s0, lv0 - cw, lv0 + cw,
            tr_acc=float((c0.predict_class(tr) == y_tr).mean()), tr_brier=float(np.mean((ptr - y_tr) ** 2)), tau=c0.tau)
        # C1 local level and C1b damped local level
        tau1 = _tau(inner["ll_p"].to_numpy(float), inner["y"].to_numpy(int))
        cw1 = _conf((inner["hunger_target"] - inner["ll_m"]).to_numpy(float))
        add("C1 local level", r["ll_p"], r["ll_p"] >= tau1, r["ll_m"], r["ll_m"] - 1.96 * r["ll_sd"], r["ll_m"] + 1.96 * r["ll_sd"],
            r["ll_m"] - cw1, r["ll_m"] + cw1, tr_acc=float(((tr["ll_p"] >= tau1) == y_tr).mean()),
            tr_brier=float(np.mean((tr["ll_p"] - y_tr) ** 2)), tau=tau1)
        d0 = (tr["ll_m"] - tr["baseline_known"]).to_numpy(float)
        d1 = (tr["hunger_target"] - tr["baseline_known"]).to_numpy(float)
        ag = tr["hunger_age_q"].to_numpy(float)
        ok = ~(np.isnan(d0) | np.isnan(d1))
        grid = np.linspace(0, 1, 101)
        phi = float(grid[int(np.argmin([np.sum((d1[ok] - g ** ag[ok] * d0[ok]) ** 2) for g in grid]))])
        sig = max(float(np.std(d1[ok] - phi ** ag[ok] * d0[ok], ddof=1)), 1.0)
        lvb = lambda d: d["baseline_known"] + phi ** d["hunger_age_q"] * (d["ll_m"] - d["baseline_known"])
        pb = lambda d: 1 - norm.cdf((d["threshold_known"] - lvb(d)) / sig)
        pin = np.asarray(pb(inner), float)
        tau1b = _tau(pin, inner["y"].to_numpy(int))
        l1b = float(lvb(r))
        add("C1b damped local level", float(pb(r)), float(pb(r)) >= tau1b, l1b, l1b - 1.96 * sig, l1b + 1.96 * sig,
            tr_acc=float((np.asarray(pb(tr)) >= tau1b).astype(int).__eq__(y_tr).mean()), tr_brier=float(np.mean((np.asarray(pb(tr)) - y_tr) ** 2)), tau=tau1b)
        # C2: Platt recalibration of C0's probability on inner out-of-fold (walk-forward) training predictions
        z = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
        if inner["y"].nunique() == 2:
            pl = LogisticRegression(C=1.0, max_iter=1000).fit(z(inner["d_p"].to_numpy(float)).reshape(-1, 1), inner["y"].to_numpy(int))
            p2 = float(pl.predict_proba(z(np.array([p0])).reshape(-1, 1))[0, 1])
        else:
            p2 = p0
        add("C2 recalibrated damped", p2, int(c0.predict_class(te)[0]), lv0)
        # C3: one domain's indicators correct C0's level residual (ridge, alpha by GCV on training only)
        if feats is not None and with_domains:
            trw = tr[tr["d_level"].notna()]
            for dom, cols in DOMAINS.items():
                Z = trw[cols].to_numpy(float)
                keep = ~np.all(np.isnan(Z), axis=0)
                if keep.sum() == 0:
                    continue
                rg = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                   RidgeCV(alphas=[1.0, 10.0, 100.0, 1000.0], store_cv_results=True))
                resid = (trw["hunger_target"] - trw["d_level"]).to_numpy(float)
                rg.fit(Z[:, keep], resid)
                cv = rg[-1].cv_results_[:, list(rg[-1].alphas).index(rg[-1].alpha_)]
                s3 = max(float(np.sqrt(np.mean(cv))), 1.0)
                lv3 = lv0 + float(rg.predict(te[cols].to_numpy(float)[:, keep])[0])
                p3 = float(1 - norm.cdf((r["threshold_known"] - lv3) / s3))
                add(f"C3 {dom}", p3, p3 >= c0.tau, lv3, lv3 - 1.96 * s3, lv3 + 1.96 * s3)
    W = pd.DataFrame(out)
    old = fi9[fi9["tag"].isin(["LightGBM (proposed, FI7)", "Logistic regression"])].copy()
    old["tag"] = old["tag"].map({"LightGBM (proposed, FI7)": "FI9 LightGBM (saved)", "Logistic regression": "FI9 logistic (saved)"})
    old = old[old["target_quarter"].isin(W["target_quarter"])]
    return pd.concat([W, old[[c for c in old.columns if c in W.columns]]], ignore_index=True)


# ------------------------------------------------------------------------------------------------ summaries
def _period_masks(W):
    yr = W["target_quarter"].str[:4].astype(int)
    saw = set(alternating_quarters())
    return {"full": W.index == W.index, "A_development": yr <= 2017, "B_previously_examined": yr >= 2018,
            "full_without_sawtooth": ~W["target_quarter"].isin(saw)}


def soft_brier(g):
    p, y, f = g["p"].to_numpy(float), g["y"].to_numpy(float), g["p_flip"].to_numpy(float)
    return float(np.mean((1 - f) * (p - y) ** 2 + f * (p - (1 - y)) ** 2))


def coverage(g, lo, hi):
    ok = g[lo].notna()
    if not ok.any():
        return None
    inside = (g.loc[ok, "hunger_target"] >= g.loc[ok, lo]) & (g.loc[ok, "hunger_target"] <= g.loc[ok, hi])
    return {"n": int(ok.sum()), "coverage": float(inside.mean()), "mean_width_pp": float((g.loc[ok, hi] - g.loc[ok, lo]).mean())}


def boot_ci(g, reps=2000, block=4, seed=11):
    """Block-bootstrap 95% CIs of the main classification metrics."""
    rng = np.random.default_rng(seed)
    n = len(g)
    y, c, p = g["y"].to_numpy(int), g["cls"].to_numpy(int), g["p"].to_numpy(float)
    starts = np.arange(n - block + 1)
    res = {k: [] for k in ["accuracy", "balanced_accuracy", "recall", "precision", "f1", "brier"]}
    for _ in range(reps):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.choice(starts, int(np.ceil(n / block)))])[:n]
        yy, cc, pp = y[idx], c[idx], p[idx]
        tp, fp, fn, tn = ((cc == 1) & (yy == 1)).sum(), ((cc == 1) & (yy == 0)).sum(), ((cc == 0) & (yy == 1)).sum(), ((cc == 0) & (yy == 0)).sum()
        res["accuracy"].append((tp + tn) / n)
        res["brier"].append(np.mean((pp - yy) ** 2))
        if tp + fn and tn + fp:
            res["balanced_accuracy"].append((tp / (tp + fn) + tn / (tn + fp)) / 2)
            res["recall"].append(tp / (tp + fn))
        if tp + fp:
            res["precision"].append(tp / (tp + fp))
        res["f1"].append(2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0)
    return {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in res.items() if v}


def leave_one_high_out(g):
    out = []
    for tq in g.loc[g["y"] == 1, "target_quarter"]:
        s = metrics(g[g["target_quarter"] != tq])
        out.append({"dropped": tq, "recall": s["recall"], "precision": s["precision"], "f1": s["f1"], "balanced_accuracy": s["balanced_accuracy"]})
    return out


def summarize(W) -> dict:
    res = {"periods": {}}
    masks = _period_masks(W)
    for name, m in masks.items():
        g = W[m]
        clim = g[g["tag"] == "Always LOW"]
        cb = float(np.mean((clim["p"] - clim["y"]) ** 2))
        P = {"climatology_brier": cb, "target_quarters": [g["target_quarter"].min(), g["target_quarter"].max()], "models": {}}
        c0 = g[g["tag"] == "C0 damped persistence (FI9)"].set_index("target_quarter")
        nv = g[g["tag"] == "Naive persistence"].set_index("target_quarter")
        for tag, gg in g.groupby("tag", sort=False):
            gg = gg.copy()
            for c in ["train_acc", "train_brier"]:
                gg[c] = gg[c].astype(float).fillna(np.nan)
            s = metrics(gg)
            s["reliability"] = reliability(s, cb)
            s["soft_label_brier"] = soft_brier(gg)
            s["share_predicted_high"] = float(gg["cls"].mean())
            a = gg.set_index("target_quarter")
            for ref, R in [("vs_C0", c0), ("vs_naive", nv)]:
                common = a.index.intersection(R.index)
                if tag not in (ref,) and len(common):
                    s[ref] = boot_delta((a.loc[common, "p"] - a.loc[common, "y"]) ** 2, (R.loc[common, "p"] - R.loc[common, "y"]) ** 2)
            s["interval_gaussian"] = coverage(gg, "pi95_lo", "pi95_hi")
            s["interval_conformal"] = coverage(gg, "cpi95_lo", "cpi95_hi")
            P["models"][tag] = s
        res["periods"][name] = P
    full = W
    for tag in ["C0 damped persistence (FI9)", "Naive persistence", "C1 local level"]:
        g = full[full["tag"] == tag].sort_values("target_quarter")
        res.setdefault("metric_ci95_full", {})[tag] = boot_ci(g)
        res.setdefault("leave_one_high_out", {})[tag] = leave_one_high_out(g)
    return res


def adoption(S: dict) -> dict:
    F, B, N = (S["periods"][k]["models"] for k in ("full", "B_previously_examined", "full_without_sawtooth"))
    out = {}
    for tag in [t for t in F if t.startswith(("C1", "C2", "C3"))]:
        f, b, n = F[tag], B[tag], N[tag]
        chk = {"reliability_full": f["reliability"]["passes"], "reliability_B": b["reliability"]["passes"],
               "reliability_without_sawtooth": n["reliability"]["passes"], "ece_full_le_0_10": f["ece_5bin"] <= 0.10,
               "overfit_gap_le_0_10": (np.isnan(f["train_accuracy_mean"]) or f["train_accuracy_mean"] - f["accuracy"] <= 0.10),
               "brier_better_than_C0_P90": f["vs_C0"]["mean"] < 0 and f["vs_C0"]["p_negative"] >= 0.90,
               "brier_better_than_naive_P90": f["vs_naive"]["mean"] < 0 and f["vs_naive"]["p_negative"] >= 0.90,
               "not_worse_than_C0_on_B": b["vs_C0"]["mean"] <= 0}
        out[tag] = {"checks": {k: bool(v) for k, v in chk.items()}, "adopt": bool(all(chk.values()))}
    g = F["C0 damped persistence (FI9)"]
    gi, ci = g["interval_gaussian"]["coverage"], g["interval_conformal"]["coverage"]
    out["interval"] = {"gaussian_coverage": gi, "conformal_coverage": ci,
                       "replace_with_conformal": bool(not (0.90 <= gi <= 0.99) and ci is not None and 0.90 <= ci <= 0.99)}
    adopted = [t for t, v in out.items() if t != "interval" and v["adopt"]]
    out["decision"] = (f"adopt {adopted}" if adopted else "retain C0 (FI9 damped persistence): no candidate passed every adoption check")
    return out


# ------------------------------------------------------------------------------------------------ diagnostics
def label_stability() -> dict:
    q = quarterly()
    base = labels().set_index("quarter")["y"]
    ev = base[(base.index >= EVAL_FIRST) & base.notna()]
    out = {}
    for w in [12, 16, 24, 28]:
        ys = {}
        for _, r in q.iterrows():
            win = q[(q["qi"] >= r["qi"] - w) & (q["qi"] < r["qi"])]
            if len(win) >= MIN_OBS:
                ys[r["quarter"]] = int(r["hunger"] - win["hunger"].mean() > r["moe"])
        s = pd.Series(ys).reindex(ev.index)
        out[f"{w}q"] = {"n_high": int(s.sum()), "flips_vs_20q": int((s != ev).sum()),
                        "flipped": sorted(ev.index[(s != ev).to_numpy()])}
    out["20q"] = {"n_high": int(ev.sum())}
    return out


def design_adjusted(X: pd.DataFrame, q: pd.DataFrame) -> dict:
    """Diagnostic only: put the latest reading on a common design (n=300 vs n>=600) using the effect estimated from
    rounds published by each issue date; compare naive persistence on targets 2024+ (sample sizes known)."""
    r = sws_rounds()
    r = r[r["bl_n"].notna()].copy()
    per_q = r.groupby("quarter").agg(n=("bl_n", "min"), k=("bl_n", "size"), pub=("published", "max"))
    rows = []
    for _, x in X[(X["target_quarter"] >= "2024-Q1") & X["y"].notna()].iterrows():
        d = x["issue_date"]
        kn = r[(r["published"] <= d) & (r["quarter"] >= "2023-Q2")]
        lq = x["last_reading_quarter"]
        adj = 0.0
        if len(kn) >= 6 and kn["bl_n"].le(300).any() and kn["bl_n"].gt(300).any() and lq in per_q.index and per_q.loc[lq, "k"] == 1:
            eff = kn.loc[kn["bl_n"] <= 300, "balance_luzon"].mean() - kn.loc[kn["bl_n"] > 300, "balance_luzon"].mean()
            adj = -eff / 2 if per_q.loc[lq, "n"] <= 300 else eff / 2
        sd = 4.5
        p_raw = 1 - norm.cdf((x["threshold_known"] - x["hunger_last"]) / sd)
        p_adj = 1 - norm.cdf((x["threshold_known"] - x["hunger_last"] - adj) / sd)
        rows.append({"target": x["target_quarter"], "y": int(x["y"]), "latest": x["hunger_last"], "adjustment_pp": round(adj, 2),
                     "p_raw": p_raw, "p_adj": p_adj})
    D = pd.DataFrame(rows)
    return {"rows": json.loads(D.to_json(orient="records")), "n": int(len(D)),
            "brier_raw": float(np.mean((D["p_raw"] - D["y"]) ** 2)), "brier_adjusted": float(np.mean((D["p_adj"] - D["y"]) ** 2)),
            "note": "sigma fixed at 4.5 pp for both; a comparison of inputs, not a fitted model"}


def release_shift(days: int = 30) -> dict:
    q = sws_series(days)
    W = walk_forward(sws_rows(q), q, None, with_domains=False)
    out = {}
    for tag in ["C0 damped persistence (FI9)", "Naive persistence", "C1 local level"]:
        s = metrics(W[W["tag"] == tag])
        out[tag] = {k: s[k] for k in ["n", "accuracy", "balanced_accuracy", "recall", "precision", "brier"]}
    return out


def live(today: pd.Timestamp) -> dict:
    q = sws_series()
    X = sws_rows(q, live=today)
    r = X.iloc[-1]
    L = X[X["y"].notna() & (X["target_published"] <= r["issue_date"])]
    c0 = M.make("damped_tau", []).fit(L, L["delta_target"].to_numpy(float))
    te = X.iloc[[-1]]
    ll = local_level(q[q["published"] <= r["issue_date"]], Q.index(r["target_quarter"]))
    sd = np.sqrt(ll["var_state"] + ll["r_next"])
    rr = sws_rounds()
    last_n = rr.loc[rr["quarter"] == r["last_reading_quarter"], "bl_n"].tolist()
    return {"issue_date": str(pd.Timestamp(r["issue_date"]).date()), "target_quarter": r["target_quarter"],
            "latest": r["hunger_last"], "latest_round_bl_n": last_n, "line": r["threshold_known"],
            "C0": {"p": float(c0.predict_proba(te)[0]), "class": int(c0.predict_class(te)[0]), "level": float(c0.inner.predict_level(te)[0])},
            "naive": {"level": r["hunger_last"]},
            "C1_local_level": {"level": ll["m"], "sd": float(sd), "p": float(1 - norm.cdf((r["threshold_known"] - ll["m"]) / sd))}}


def run() -> dict:
    lock = check()
    from app.fi7.design import Designer
    q = sws_series()
    X = sws_rows(q)
    # independent rows must reproduce the FI9 forecast-time dataset
    F = pd.read_csv(BACKEND_DIR / "data" / "fi9" / "baseline_20261103" / "forecast_time_dataset_h1.csv")
    chk = X.assign(issue_date=X["issue_date"].dt.date.astype(str)).merge(F, on="issue_date", suffixes=("", "_fi9"))
    repro = {c: float((chk[c] - chk[f"{c}_fi9"]).abs().max()) for c in ["hunger_last", "baseline_known", "hunger_age_q", "threshold_known"]}
    D = Designer("operational").frame(1)
    feats = D[["issue_date"] + sorted({c for v in DOMAINS.values() for c in v})].copy()
    feats["issue_date"] = pd.to_datetime(feats["issue_date"])
    W = walk_forward(X, q, feats)
    W.to_csv(OUT / "wf_predictions.csv", index=False, lineterminator="\n")
    S = summarize(W)
    fi9 = pd.read_csv(FI9_PRED)
    a = W[W["tag"] == "C0 damped persistence (FI9)"].set_index("target_quarter")
    b = fi9[fi9["tag"] == "Damped persistence (statistical)"].set_index("target_quarter")
    S["reproduces_fi9"] = {"rows_max_abs_diff": repro, "n_rows_compared": int(len(chk)),
                           "c0_vs_fi9_max_abs_p_diff": float((a["p"] - b.loc[a.index, "p"]).abs().max()),
                           "c0_vs_fi9_class_mismatches": int((a["cls"] != b.loc[a.index, "cls"]).sum())}
    S["label_stability"] = label_stability()
    S["design_adjusted_diagnostic"] = design_adjusted(X, q)
    S["release_date_shift_30d"] = release_shift(30)
    S["live_2026_11_03"] = live(pd.Timestamp("2026-11-03"))
    S["protocol_sha256"] = lock
    (OUT / "reassessment.json").write_text(json.dumps(S, indent=1, default=str))
    A = adoption(S)
    (OUT / "adoption.json").write_text(json.dumps(A, indent=1))
    return {"reproduces_fi9": S["reproduces_fi9"], "adoption": A}


if __name__ == "__main__" and sys.argv[1:] == ["run"]:
    print(json.dumps(run(), indent=1, default=str))
