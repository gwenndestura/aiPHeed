"""
E168: LightGBM-only nested procedure (docs/e168/PROTOCOL.md). Survey baseline + LightGBM change model + calibration layer,
every choice made on training rows only.

    python -m app.e168.lgbm_only eval
"""
from __future__ import annotations

import json
import sys
import warnings
from itertools import product

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import binomtest, norm
from sklearn.model_selection import GroupKFold

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e152.panel import OUT as O152
from app.e154 import model as E154
from app.e155.test import panel as sun_panel
from app.e156 import leads as LD
from app.e157.sources import SOURCES
from app.e162 import rank as R2
from app.e163 import model as C
from app.e164 import auto as A4
from app.e165 import final as F5
from app.e166 import nested_source as N
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e168" / "out"
GNT = list(Pv.GNT_COLS)
NEWS = [c for c in GNT if c in Pv.NEWS_ALL]
CONS = SOURCES["regional_consumption"]
FS = {"GOV": [c for c in GNT if c not in NEWS], "FULL": GNT, "GOV+cons": [c for c in GNT if c not in NEWS] + CONS, "FULL+cons": GNT + CONS}
HPO = list(product((3, 7), (10, 40), (5.0, 20.0), (150, 400)))
ANCH = ("H", "OH", "RSS")
TRIG = [c for c in GNT if C.gmap(c) is not None] + CONS
G5 = ["market", "climate", "employment", "remittance", "poverty"]
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


class LGBRes:
    def __init__(self, cols, nl, mcs, lam, ne, prune):
        self.cols, self.nl, self.mcs, self.lam, self.ne, self.prune = list(cols), nl, mcs, lam, ne, prune

    def fit(self, d):
        use = [c for c in self.cols if c in d and d[c].notna().any() and d[c].nunique() > 1]
        if self.prune and len(use) > 1:
            R = d[use].rank().corr().abs()
            keep = []
            for c in use:
                if all(not (R.at[c, k] > 0.95) for k in keep):
                    keep.append(c)
            use = keep
        self.use_ = use
        par = dict(objective="regression", num_leaves=self.nl, max_depth=-1, min_child_samples=self.mcs, reg_lambda=self.lam, reg_alpha=0.0, min_split_gain=0.0, n_estimators=self.ne, learning_rate=0.02,
                   colsample_bytree=0.8, subsample=0.8, subsample_freq=1, monotone_constraints=[Pv.SIGN.get(c, 0) for c in use], monotone_constraints_method="basic", random_state=168, n_jobs=1, verbose=-1)
        w = (1.0 / (d["se_true"] ** 2 + 0.05)).values
        self.m_ = lgb.LGBMRegressor(**par).fit(d[use], d["e"].values, sample_weight=w)
        return self

    def predict(self, X):
        return self.m_.predict(X[self.use_])


def run_proc(tr, te, AN, ablate=False):
    tr = tr.reset_index(drop=True)
    y, q, w = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    best = None
    for a, f, pr, h in product(ANCH, FS, (False, True), HPO):
        atr = AN[a][0]
        oof = np.zeros(len(tr))
        for i_tr, i_te in folds:
            oof[i_te] = atr[i_te] + LGBRes(FS[f], *h, pr).fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])).predict(tr.iloc[i_te])
        sse = float(np.sum(w * (y - oof) ** 2))
        if best is None or sse < best["sse"]:
            best = {"sse": sse, "cfg": (a, f, pr, h), "oof": oof}
    a, f, pr, h = best["cfg"]
    atr, ate = AN[a]
    oof = best["oof"]
    mdl = LGBRes(FS[f], *h, pr).fit(tr.assign(e=y - atr))
    mu = ate + mdl.predict(te)
    # calibration layers, cross-fitted on inner OOF
    sd, _ = A4.scale(y - oof, gap, gap)
    lin, pl = np.zeros(len(tr)), np.zeros(len(tr))
    for i_tr, i_te in folds:
        Z = np.column_stack([np.ones(len(i_tr)), oof[i_tr]]) * np.sqrt(w[i_tr])[:, None]
        ab = np.linalg.lstsq(Z, y[i_tr] * np.sqrt(w[i_tr]), rcond=None)[0]
        lin[i_te] = ab[0] + ab[1] * oof[i_te]
        pl[i_te] = F5.soft_platt(oof[i_tr], q[i_tr]).predict_proba(oof[i_te].reshape(-1, 1))[:, 1]
    sdl, _ = A4.scale(y - lin, gap, gap)
    inner = {"raw": float(np.mean((norm.cdf(oof / sd) - q) ** 2)), "linear": float(np.mean((norm.cdf(lin / sdl) - q) ** 2)), "platt": float(np.mean((pl - q) ** 2))}
    chosen = min(inner, key=inner.get)
    sd_te, half = A4.scale(y - oof, gap, te["gap_q"].values)
    Z = np.column_stack([np.ones(len(tr)), oof]) * np.sqrt(w)[:, None]
    ab = np.linalg.lstsq(Z, y * np.sqrt(w), rcond=None)[0]
    mu_lin = ab[0] + ab[1] * mu
    sd_lin, half_lin = A4.scale(y - lin, gap, te["gap_q"].values)
    P = {"raw": (mu, norm.cdf(mu / sd_te), half), "linear": (mu_lin, norm.cdf(mu_lin / sd_lin), half_lin), "platt": (mu, F5.soft_platt(oof, q).predict_proba(mu.reshape(-1, 1))[:, 1], half)}
    abl = {}
    if ablate:
        for g in G5:
            cols = [c for c in FS[f] if C.gmap(c) != g and not (g == "employment" and c == "income_growth") and not (g == "poverty" and c == "income_rel")]
            m2 = LGBRes(cols, *h, pr).fit(tr.assign(e=y - atr))
            mu2 = ate + m2.predict(te)
            abl[g] = norm.cdf(mu2 / sd_te) if chosen != "linear" else norm.cdf((ab[0] + ab[1] * mu2) / sd_lin)
    tag = f"{a}|{f}|prune={pr}|leaves={h[0]},minchild={h[1]},lambda={h[2]},trees={h[3]}|cal={chosen}"
    return P, chosen, tag, abl, inner, len(mdl.use_)


def task(survey, lead, H, L, S_P, mode):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    rel = M.released(i, Pv.ROUNDS)
    if mode == "corrupt":
        b = S.s8.base
        z = ~b["survey"].isin(rel)
        b.loc[z, "y"] = np.random.default_rng(7).normal(0, 2, int(z.sum()))
    P_ = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = N.add_sources(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), L, H, S_P)
    tr = N.add_sources(Pv.add_inputs(S, P_.tr), L, H, S_P)
    AN = A4.anchors(S, P_, tr, te)
    if mode.startswith("shuf"):
        s_ = int(mode[4:])
        tr, te = C.shuffle_cols(tr, TRIG, s_), C.shuffle_cols(te, TRIG, s_)
    P, chosen, tag, abl, inner, nfeat = run_proc(tr, te, AN, ablate=(mode == "main" and lead == 1))
    o = te[["key", "survey", "lead"]].copy()
    o["mode"], o["cfg"], o["cal"], o["n_features"] = mode, tag, chosen, nfeat
    for k, (mu, p, half) in P.items():
        o[f"mu_{k}"], o[f"p_{k}"], o[f"half_{k}"] = mu, p, half
    o["mu"], o["p"], o["half"] = P[chosen]
    for g, v in abl.items():
        o[f"abl_{g}"] = v
    for k, v in inner.items():
        o[f"inner_brier_{k}"] = v
    return o


def evaluate():
    OUT.mkdir(parents=True, exist_ok=True)
    H, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    jobs = [(s, h, "main") for s in ("ENNS2018", "ENNS2019", "ENNS2021") for h in (1, 2)] + [(s, 1, m) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for m in ("shuf1", "shuf2", "shuf3", "corrupt")]
    if (OUT / "all_rows.csv").exists() and "--rerun" not in sys.argv:
        Al = pd.read_csv(OUT / "all_rows.csv")
    else:
        Al = pd.concat([x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H, L, S_P, m) for s, h, m in jobs) if x is not None], ignore_index=True)
        Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    k = ["key", "survey", "lead"]
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")
    E6 = pd.concat([pd.read_csv(D / "e166" / "out" / "all_rows.csv")])
    res = {"leads": {}, "mcnemar": {}}
    for Ld in (1, 2):
        m = Al[(Al["lead"] == Ld) & (Al["mode"] == "main")]
        x = G[G["lead"] == Ld].merge(m, on=k)
        x = x.rename(columns={"mu": "mu_E168", "p": "E168", "half": "half_E168"})
        for c in ("raw", "linear", "platt"):
            x[f"E168_{c}"], x[f"mu_E168_{c}"], x[f"half_E168_{c}"] = x[f"p_{c}"], x[f"mu_{c}"], x[f"half_{c}"]
        x = x.merge(E6[(E6["lead"] == Ld) & (E6["mode"] == "main")][k + ["mu", "p", "half"]].rename(columns={"mu": "mu_E166", "p": "E166", "half": "half_E166"}), on=k)
        assert len(x) == 72
        rng = np.random.default_rng(168)
        arms = ["PERS", "E158", "E166", "E168", "E168_raw", "E168_linear", "E168_platt"]
        cm = {}
        for a in arms:
            mm = C.cls_metrics(x, a, rng)
            f_low = 2 * mm["low_precision"] * mm["low_recall"] / max(1e-9, mm["low_precision"] + mm["low_recall"])
            mm["macro_f1"] = round((mm["f1"] + f_low) / 2, 3)
            mm["prob_calibration"] = F5.prob_cal(x, a, rng)
            b = pd.cut(x[a], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
            mm["reliability"] = x.groupby(b, observed=False).agg(n=("y_high", "size"), mean_p=(a, "mean"), observed=("y_high", "mean")).round(3).reset_index().astype(str).to_dict("records")
            mm["E156"] = LD.evaluate(x, a, a)["leads"][0]["criteria"]
            cm[a] = mm
        d = E7.diff_ci(x, "E168", "E158", "q_true", rng, n=2000)
        cF, cE = (x["E168"] >= .5) == (x["y_high"] == 1), (x["E158"] >= .5) == (x["y_high"] == 1)
        bb, cc = int((cF & ~cE).sum()), int((~cF & cE).sum())
        res["mcnemar"][Ld] = {"e168_only_right": bb, "e158_only_right": cc, "p": round(float(binomtest(bb, bb + cc, .5).pvalue), 4) if bb + cc else 1.0}
        per = {s: {a: {"accuracy": round(float(((g[a] >= .5) == (g["y_high"] == 1)).mean()), 3), "brier": round(float(np.mean((g[a] - g["q_true"]) ** 2)), 4), "bias_pts": round(float(np.mean(pct(g[f"mu_{a}"]) - pct(g["y_true"]))), 2)} for a in ("E158", "E166", "E168")} for s, g in x.groupby("survey")}
        _, rk = R2.rank_measures(x, ["E158", "E166", "E168"])
        res["leads"][Ld] = {"class": cm, "brier_minus_E158": {"diff": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]]}, "per_round": per, "ranking_concordance": rk["concordance"],
                            "selected": x.groupby("survey")[["cfg", "cal", "n_features"]].first().to_dict("index"), "inner_brier": x.groupby("survey")[["inner_brier_raw", "inner_brier_linear", "inner_brier_platt"]].first().round(4).to_dict("index")}
        if Ld == 1:
            x1 = x
    x = x1
    for m in ("shuf1", "shuf2", "shuf3", "corrupt"):
        x = x.merge(Al[(Al["lead"] == 1) & (Al["mode"] == m)][k + ["mu", "p"]].rename(columns={"mu": f"mu_{m}", "p": m}), on=k)
    x["SHUF"] = x[["shuf1", "shuf2", "shuf3"]].mean(axis=1)
    rng = np.random.default_rng(168)
    v = E7.diff_ci(x, "E168", "SHUF", "q_true", rng, n=2000)
    res["shuffle"] = {"brier_shuffled": round(float(np.mean((x["SHUF"] - x["q_true"]) ** 2)), 4), "E168_minus_shuffled": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]}
    res["leakage_max_abs_change"] = float(np.max(np.abs(x["mu_E168"] - x["mu_corrupt"])))
    abl = {}
    for g in G5:
        dd = E7.diff_ci(x, "E168", f"abl_{g}", "q_true", rng, n=2000)
        abl[g] = {"brier_without": round(float(np.mean((x[f"abl_{g}"] - x["q_true"]) ** 2)), 4), "E168_minus_without": round(dd["diff"], 4), "ci95": [round(z, 4) for z in dd["ci95"]], "accuracy_without": round(float(((x[f"abl_{g}"] >= .5) == (x["y_high"] == 1)).mean()), 3)}
    res["ablation"] = abl
    res["bias"] = {a: C.bias(x, a, np.random.default_rng(161)) for a in ("E158", "E166", "E168")}
    e1 = res["leads"][1]
    acc = {"E156_all_lead1": all(e1["class"]["E168"]["E156"].values()), "leakage": res["leakage_max_abs_change"] < 1e-9, "beats_shuffled": res["shuffle"]["ci95"][1] < 0, "non_inferior_E158": e1["brier_minus_E158"]["ci95"][1] < 0.02}
    better = e1["class"]["E168"]["brier"] < e1["class"]["E158"]["brier"] and e1["class"]["E168"]["accuracy"] >= e1["class"]["E158"]["accuracy"]
    res["acceptance"] = acc
    res["decision"] = "ACCEPT" if all(acc.values()) else ("IMPROVED BUT NOT ACCEPTED" if better else ("INSUFFICIENT EVIDENCE" if not (e1["class"]["E168"]["E156"]["C1"] and e1["class"]["E168"]["E156"]["C4"]) else "NOT ACCEPTED"))
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), newline="\n")
    print(json.dumps({kk: res[kk] for kk in ("acceptance", "decision", "leakage_max_abs_change", "shuffle", "mcnemar", "ablation")}, indent=1, default=str))
    for Ld in (1, 2):
        r = res["leads"][Ld]
        print(f"\nLead {Ld} brier-E158 {r['brier_minus_E158']} selected {r['selected']}")
        cols = ("accuracy", "balanced_accuracy", "high_precision", "high_recall", "low_precision", "low_recall", "f1", "macro_f1", "auc", "brier", "calibration_slope", "calibration_slope_ci95", "mae_pts", "mean_signed_pts")
        print(pd.DataFrame({a: {c: v_.get(c) for c in cols} | {"pcal": v_["prob_calibration"]["slope_ci95"], "E156": "".join(str(int(t)) for t in v_["E156"].values()), "conf": v_["confusion"]} for a, v_ in r["class"].items()}).T.to_string())
        print("per round", r["per_round"], "conc", {a: v_["est"] for a, v_ in r["ranking_concordance"].items()}, "inner", r["inner_brier"])
        print("reliab E168", r["class"]["E168"]["reliability"])
    print({a: {g_: (v_["mean"], v_["ci95"]) for g_, v_ in res["bias"][a].items() if g_ != "calabarzon_rows"} | {"CAL": res["bias"][a]["calabarzon_rows"]} for a in res["bias"]})


if __name__ == "__main__":
    {"eval": evaluate}[sys.argv[1]]()
