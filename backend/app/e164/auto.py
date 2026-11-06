"""
E164 nested automatic model selection (AUTO), per docs/e164/PROTOCOL.md (fixed before results).
Selection of anchor, learner, feature set and calibration uses training rows only (region GroupKFold).

    python -m app.e164.auto eval
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e158 import model as E8
from app.e160 import arms as A
from app.e162 import rank as R2
from app.e163 import model as C
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e164" / "out"
ANCH = ["H", "RP", "OH", "RSS"]
LEARN = ["NONE", "RIDGE", "ENET", "RF", "LGBM"]
TRIG = [c for c in E8.COLS if C.gmap(c) is not None]
NEWS = [c for c in E8.COLS if c in Pv.NEWS_ALL]
FS = {"GOV": [c for c in E8.COLS if c not in NEWS], "FULL": list(E8.COLS), "NEWSONLY": NEWS + ["gap_q", "lead"]}
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


class ENetRes(C.RidgeRes):
    ALPHAS = (0.001, 0.01, 0.1)

    def fit(self, d):
        d = d.reset_index(drop=True)
        self.use_ = [c for c in self.cols if c in d and d[c].notna().any() and d[c].nunique() > 1]
        self.med_, self.sd_ = d[self.use_].median(), d[self.use_].std().replace(0, 1).fillna(1)
        X, y, w = self._X(d), d["e"].values, (1.0 / (d["se_true"] ** 2 + 0.05)).values
        folds = list(GroupKFold(min(5, d["region"].nunique())).split(d, groups=d["region"]))
        best = (np.inf, None)
        for a in self.ALPHAS:
            pred = np.zeros(len(d))
            for tr, te in folds:
                pred[te] = ElasticNet(alpha=a, l1_ratio=0.5, max_iter=5000).fit(X[tr], y[tr], sample_weight=w[tr]).predict(X[te])
            sse = float(np.sum(w * (y - pred) ** 2))
            if sse < best[0]:
                best = (sse, a)
        self.alpha_ = best[1]
        self.m_ = ElasticNet(alpha=self.alpha_, l1_ratio=0.5, max_iter=5000).fit(X, y, sample_weight=w)
        return self


class RFRes:
    def __init__(self, cols):
        self.cols = list(cols)

    def fit(self, d):
        self.use_ = [c for c in self.cols if c in d and d[c].notna().any() and d[c].nunique() > 1]
        self.med_ = d[self.use_].median()
        w = (1.0 / (d["se_true"] ** 2 + 0.05)).values
        self.m_ = RandomForestRegressor(n_estimators=300, max_depth=3, min_samples_leaf=20, max_features=0.3, random_state=164, n_jobs=1).fit(d[self.use_].fillna(self.med_).values, d["e"].values, sample_weight=w)
        return self

    def predict(self, X):
        return self.m_.predict(X[self.use_].fillna(self.med_).values)


LEARNERS = {"RIDGE": C.RidgeRes, "ENET": ENetRes, "RF": RFRes, "LGBM": Pv.Res2}


def scale(oof_err, gap_tr, gap_te):
    Z = np.column_stack([np.ones(len(gap_tr)), gap_tr])
    b = np.linalg.lstsq(Z, oof_err ** 2, rcond=None)[0]
    b[1] = max(b[1], 0.0)
    s = np.sqrt(np.clip(b[0] + b[1] * gap_tr, 1e-3, None))
    q = float(np.quantile(np.abs(oof_err) / s, 0.90))
    sd = np.sqrt(np.clip(b[0] + b[1] * np.asarray(gap_te, float), 1e-3, None))
    return sd, q * sd


def anchors(S, P, tr, te):
    Ca, RC = A.Cache(S), C.RCache(S)
    a_tr, a_te = A.anchors(Ca, tr), A.anchors(Ca, te)
    h_te, _ = P.hier.predict(te, te["T"].values)
    r_tr, _, _ = C.rss_rows(RC, tr)
    r_te, _, _ = C.rss_rows(RC, te)
    return {"H": (tr["base"].values, h_te), "RP": (a_tr["a_RP"].values, a_te["a_RP"].values), "OH": (a_tr["a_OH"].values, a_te["a_OH"].values), "RSS": (r_tr, r_te)}


def menu(kind):
    fs = {"ALL": ["GOV", "FULL"], "NONEWS": ["GOV"], "NEWSONLY": ["NEWSONLY"]}[kind]
    return [(a, "NONE", None) for a in ANCH] + [(a, l, f) for a in ANCH for l in LEARNERS for f in fs]


def run_procedure(tr, te, AN, kind="ALL", fixed=False):
    """Inner selection on training rows; returns AUTO forecast for te and (optionally) every fixed configuration."""
    tr = tr.reset_index(drop=True)
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    res, fixed_out = [], {}
    for a, l, f in menu(kind):
        atr, ate = AN[a]
        if l == "NONE":
            oof = atr.copy()
        else:
            oof = np.zeros(len(tr))
            for i_tr, i_te in folds:
                d = tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])
                oof[i_te] = atr[i_te] + LEARNERS[l](FS[f]).fit(d).predict(tr.iloc[i_te])
        sse_id = float(np.sum(w * (y - oof) ** 2))
        cal = np.zeros(len(tr))
        for i_tr, i_te in folds:
            Z = np.column_stack([np.ones(len(i_tr)), oof[i_tr]]) * np.sqrt(w[i_tr])[:, None]
            ab = np.linalg.lstsq(Z, y[i_tr] * np.sqrt(w[i_tr]), rcond=None)[0]
            cal[i_te] = ab[0] + ab[1] * oof[i_te]
        sse_cal = float(np.sum(w * (y - cal) ** 2))
        res.append({"cfg": (a, l, f), "sse": min(sse_id, sse_cal), "calib": sse_cal < sse_id, "oof": cal if sse_cal < sse_id else oof, "oof_id": oof})
        if fixed:
            mu = ate if l == "NONE" else ate + LEARNERS[l](FS[f]).fit(tr.assign(e=y - atr)).predict(te)
            sd, _ = scale(y - oof, tr["gap_q"].values, te["gap_q"].values)
            fixed_out[f"{a}_{l}_{f or 'NA'}"] = (mu, norm.cdf(mu / sd))
    best = min(res, key=lambda r: r["sse"])
    a, l, f = best["cfg"]
    atr, ate = AN[a]
    mu = ate if l == "NONE" else ate + LEARNERS[l](FS[f]).fit(tr.assign(e=y - atr)).predict(te)
    if best["calib"]:
        Z = np.column_stack([np.ones(len(tr)), best["oof_id"]]) * np.sqrt(w)[:, None]
        ab = np.linalg.lstsq(Z, y * np.sqrt(w), rcond=None)[0]
        mu = ab[0] + ab[1] * mu
    sd, half = scale(y - best["oof"], tr["gap_q"].values, te["gap_q"].values)
    tag = f"{a}|{l}|{f or '-'}|{'cal' if best['calib'] else 'id'}"
    return mu, norm.cdf(mu / sd), half, sd, tag, fixed_out


def task(survey, lead, H, mode="main"):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    rel = M.released(i, Pv.ROUNDS)
    if not rel:
        return None
    if mode == "corrupt":
        b = S.s8.base
        z = ~b["survey"].isin(rel)
        b.loc[z, "y"] = np.random.default_rng(7).normal(0, 2, int(z.sum()))
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H).reset_index(drop=True)
    if te.empty:
        return None
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    AN = anchors(S, P, tr, te)
    out = te[["key", "survey", "lead"]].copy()
    out["mode"] = mode
    if mode.startswith("shuf"):
        sd_ = int(mode[4:])
        tr, te = C.shuffle_cols(tr, TRIG, sd_), C.shuffle_cols(te, TRIG, sd_)
    kind = {"nonews": "NONEWS", "newsonly": "NEWSONLY"}.get(mode, "ALL")
    mu, p, half, sd, tag, fx = run_procedure(tr, te, AN, kind, fixed=(mode == "main"))
    out["mu_AUTO"], out["AUTO"], out["half_AUTO"], out["cfg"] = mu, p, half, tag
    out["ALWAYS_LOW"] = float(np.mean(tr["y_true"] >= 0))
    for k, (m_, p_) in fx.items():
        out[f"mu_{k}"], out[k] = m_, p_
    return out


def evaluate():
    OUT.mkdir(parents=True, exist_ok=True)
    H = E154.income()
    jobs = [(s, h, "main") for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in (1, 2, 3, 4)]
    jobs += [(s, 1, m) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for m in ("shuf1", "shuf2", "shuf3", "nonews", "newsonly", "corrupt")]
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H, m) for s, h, m in jobs) if x is not None]
    Al = pd.concat(R, ignore_index=True)
    Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    k = ["key", "survey", "lead"]
    main = Al[Al["mode"] == "main"].dropna(axis=1, how="all")
    G = pd.read_csv(D / "e163" / "out" / "oof.csv")
    G2 = pd.read_csv(D / "e151" / "out" / "prov_oof.csv")[k + ["mu_ANCHOR", "ANCHOR"]]
    F = G[G["lead"] <= 4].merge(G2, on=k).merge(main.drop(columns="mode"), on=k)
    assert len(F) == len(G[G["lead"] <= 4])
    F["half_ANCHOR"] = 0.0
    F["mu_ALWAYS_LOW"] = -1.0
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    res = {}
    x1 = F[F["lead"] == 1].reset_index(drop=True)
    for m in ("shuf1", "shuf2", "shuf3", "nonews", "newsonly", "corrupt"):
        v = Al[(Al["mode"] == m)][k + ["mu_AUTO", "AUTO", "cfg"]].rename(columns={"mu_AUTO": f"mu_{m}", "AUTO": m, "cfg": f"cfg_{m}"})
        x1 = x1.merge(v, on=k)
    res["leakage_max_abs_change"] = float(np.max(np.abs(x1["mu_AUTO"] - x1["mu_corrupt"])))
    x1["SHUF"] = x1[["shuf1", "shuf2", "shuf3"]].mean(axis=1)
    rng = np.random.default_rng(164)
    brier = lambda a, g=x1: float(np.mean((g[a] - g["q_true"]) ** 2))
    res["controls"] = {}
    for c in ("SHUF", "nonews", "newsonly"):
        d = E7.diff_ci(x1, "AUTO", c, "q_true", rng, n=2000)
        res["controls"][c] = {"brier": round(brier(c), 4), "AUTO_minus_this": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]], "accuracy": round(float(((x1[c] >= .5) == (x1["y_high"] == 1)).mean()), 3)}
    res["selected_configs"] = {L: F[F["lead"] == L].groupby("survey")["cfg"].first().to_dict() for L in (1, 2, 3, 4)}
    res["selected_configs_controls"] = {m: x1.groupby("survey")[f"cfg_{m}"].first().to_dict() for m in ("shuf1", "nonews", "newsonly")}
    base_arms = ["ALWAYS_LOW", "PERS", "ANCHOR", "RP", "C1", "E158", "AUTO"]
    fixed = [c for c in main.columns if c.count("_") >= 2 and not c.startswith(("mu_", "half_")) and c not in ("ALWAYS_LOW",)]
    res["leads"] = {}
    for L in (1, 2, 3, 4):
        x = F[F["lead"] == L].reset_index(drop=True)
        cm = {}
        for a in base_arms:
            if f"half_{a}" not in x:
                x[f"half_{a}"] = 0.0
            m_ = C.cls_metrics(x, a, rng) if a != "ALWAYS_LOW" else None
            if m_ is None:
                yv = x["y_high"].values == 1
                m_ = {"accuracy": round(float((~yv).mean()), 3), "brier": round(brier(a, x), 4), "high_recall": 0.0, "low_recall": 1.0}
            m_["pr_auc"] = round(float(average_precision_score(x["y_high"], x[a])), 3) if a != "ALWAYS_LOW" else round(float(x["y_high"].mean()), 3)
            if a != "ALWAYS_LOW":
                m_["calibration_intercept"] = round(float(np.polyfit(x[f"mu_{a}"], x["y_true"], 1)[1]), 3)
            cm[a] = m_
        d = E7.diff_ci(x, "AUTO", "E158", "q_true", rng, n=2000)
        P_, rk = R2.rank_measures(x, ["E158", "AUTO", "C1", "RP", "PERS"])
        fx = {c: {"accuracy": round(float(((x[c] >= .5) == (x["y_high"] == 1)).mean()), 3), "brier": round(brier(c, x), 4)} for c in fixed if c in x}
        per = {s: {a: {"accuracy": round(float(((g[a] >= .5) == (g["y_high"] == 1)).mean()), 3), "brier": round(brier(a, g), 4)} for a in ("E158", "AUTO")} for s, g in x.groupby("survey")}
        res["leads"][L] = {"class": cm, "AUTO_minus_E158": {"diff": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]]}, "ranking": rk, "fixed_configs_descriptive": fx, "per_round": per}
        if L == 1:
            bins = pd.cut(x["AUTO"], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
            res["reliability_AUTO_lead1"] = x.groupby(bins, observed=False).agg(n=("y_high", "size"), mean_p=("AUTO", "mean"), observed=("y_high", "mean")).round(3).reset_index().astype(str).to_dict("records")
            res["bias"] = {a: C.bias(x, a, np.random.default_rng(161)) for a in ("E158", "AUTO")}
    l1 = res["leads"][1]
    au, e8 = l1["class"]["AUTO"], l1["class"]["E158"]
    isl = lambda a: max(abs(res["bias"][a][f"island:{k}"]["mean"]) for k in ("Luzon", "Visayas", "Mindanao"))
    g = {"A1": au["brier"] <= e8["brier"] and not (l1["AUTO_minus_E158"]["ci95"][0] > 0),
         "A2": not (res["controls"]["SHUF"]["ci95"][0] > 0),
         "A3": sum(v["AUTO"]["brier"] <= v["E158"]["brier"] for v in l1["per_round"].values()) >= 2 and all(v["AUTO"]["accuracy"] >= v["E158"]["accuracy"] - 0.10 for v in l1["per_round"].values()),
         "A4": au["high_recall"] >= .5 and au["low_recall"] >= .5 and au["confusion"]["fn"] <= e8["confusion"]["fn"] + 1,
         "A5": (au["calibration_slope_ci95"][0] <= 1 <= au["calibration_slope_ci95"][1]) or abs(au["calibration_slope"] - 1) <= abs(e8["calibration_slope"] - 1),
         "A6": isl("AUTO") <= isl("E158") + 1,
         "A7": res["leakage_max_abs_change"] < 1e-9,
         "A8": l1["ranking"]["concordance"]["AUTO"]["est"] >= 0.55}
    g["all"] = all(g.values())
    res["gates"] = g
    res["groups_contribute"] = bool(res["controls"]["SHUF"]["ci95"][1] < 0)
    res["max_reliable_lead"] = {a: None for a in ("AUTO",)}
    from app.e156 import leads as LD
    res["max_reliable_lead"]["AUTO"] = LD.evaluate(F, "AUTO", "AUTO")["maximum_reliable_lead"]
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), newline="\n")
    print(json.dumps({k_: res[k_] for k_ in ("leakage_max_abs_change", "gates", "groups_contribute", "controls", "selected_configs", "selected_configs_controls", "max_reliable_lead")}, indent=1, default=str))
    for L in (1, 2, 3, 4):
        r = res["leads"][L]
        print(f"\nLead {L}  AUTO-E158 {r['AUTO_minus_E158']}")
        cols = ("accuracy", "balanced_accuracy", "high_precision", "high_recall", "low_precision", "low_recall", "f1", "auc", "pr_auc", "brier", "calibration_slope", "calibration_intercept", "mae_pts", "false_alarm_rate", "missed_high_rate")
        print(pd.DataFrame({a: {c: v.get(c) for c in cols} for a, v in r["class"].items()}).T.to_string())
        print("conc", {a: v["est"] for a, v in r["ranking"]["concordance"].items()}, "per round", r["per_round"])
    print("fixed L1 top 8 by brier", sorted(res["leads"][1]["fixed_configs_descriptive"].items(), key=lambda t: t[1]["brier"])[:8])
    print(json.dumps(res["bias"], indent=1), res["reliability_AUTO_lead1"])



def live():
    """2027-Q1 Lead 1 AUTO forecast with the same procedure on all released rounds; group shares for linear learners; seal."""
    import hashlib
    from datetime import datetime, timezone
    from app.e160.trace import build
    S, P, tr, m, te = build()
    AN = anchors(S, P, tr, te)
    mu, p, half, sd, tag, _ = run_procedure(tr, te, AN, "ALL")
    a, l, f, cal = tag.split("|")
    shares = None
    if l in ("ENET", "RIDGE"):
        atr = AN[a][0]
        mdl = LEARNERS[l](FS[f]).fit(tr.assign(e=tr["y_true"].values - atr))
        X = mdl._X(tr)
        contrib = np.abs(X * mdl.m_.coef_[None, :]).mean(axis=0)
        g = {}
        for c, v in zip(mdl.use_, contrib):
            k = C.gmap(c) or "timing"
            g[k] = g.get(k, 0.0) + float(v)
        tot = sum(g.values()) or 1.0
        shares = {k: round(v / tot, 4) for k, v in sorted(g.items(), key=lambda t: -t[1])}
        nz = {c: round(float(b), 4) for c, b in zip(mdl.use_, mdl.m_.coef_) if abs(b) > 1e-9}
    rng = np.random.default_rng(164)
    s_rank = sd * np.sqrt(1 - 0.726)
    draw = mu[None, :] + rng.standard_normal((10000, len(te))) * s_rank[None, :]
    top = np.bincount(draw.argmax(axis=1), minlength=len(te)) / 10000
    rows = [{"province": te["province"].iloc[k], "score": round(float(pct(mu[k])), 1), "low90": round(float(pct(mu[k] - half[k])), 1), "high90": round(float(pct(mu[k] + half[k])), 1),
             "p_high": round(float(p[k]), 3), "class": "HIGH" if mu[k] >= 0 else "LOW", "p_highest": round(float(top[k]), 3), "anchor": round(float(pct(AN[a][1][k])), 1)} for k in range(len(te))]
    out = {"issue": "2026-10-01", "target_quarter": "2027-Q1", "lead": 1, "config": tag, "forecasts": rows, "group_shares": shares, "nonzero_coefficients": nz if shares else None, "train_rows": int(len(tr))}
    (OUT / "live.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    sp = OUT / "sealed_2027-Q1.json"
    if not sp.exists():
        sp.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), **out}, indent=1, default=float), newline="\n")
    print("seal", hashlib.sha256(sp.read_bytes()).hexdigest())
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"eval": evaluate, "live": live}[sys.argv[1]]()
