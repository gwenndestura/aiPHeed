"""Y12 step 3 (EXPERIMENT_PLAN.md sections 2-6): domestic rice-supply indicators vs persistence for the provincial
Lead-2 price condition (2012-base analogue), 5 CALABARZON provinces, targets 2002-Q1..2020-Q4, refitted at every origin.
Runs the main lags and the sensitivity lags, applies acceptance A1-A4, and writes:
out/dev_rows_main.csv, out/dev_rows_sens.csv, out/dev_results.json.

    python -B run_dev.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
import warnings
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import log_loss, roc_auc_score  # noqa: E402

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
Y12 = HERE.parent
RES = Y12.parent
EXP = RES.parent
ACQ, OUT = Y12 / "data_acquired", Y12 / "out"
sys.path.insert(0, str(EXP / "E41_Lead2_Audit" / "runner"))
SEED, B = 2036, 5000
C_GRID = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
T_FIRST, T_LAST = 2002 * 4 - 2, 2020 * 4 + 3 - 2          # origins whose Lead-2 target is 2002-Q1 .. 2020-Q4
S_FEATS = ["S1_stocks_yoy", "S2_stocks_d3", "S3_nfa_share", "S4_commercial_yoy", "S5_farmgate_yoy", "S6_farmgate_d3"]
P_FEATS = ["xF", "xG", "F_last", "dF3", "dF6", "rice_yoy", "rice_d3"]


def plan_ok():
    want = (HERE / "PLAN_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((Y12 / "EXPERIMENT_PLAN.md").read_bytes()).hexdigest() == want, "plan changed after freezing"
    man = {m["file"]: m["sha256"] for m in json.loads((ACQ / "manifest.json").read_text())}
    pins = {"stocks_national_monthly.csv": "aaa6073c", "farmgate_palay_old.csv": "d4bda7b2", "farmgate_palay_new.csv": "db8642d6",
            "cpi2012_yoy_1995_2011.csv": "f06a943a", "cpi2012_yoy_2012_2021.csv": "fca48969"}
    for f, p in pins.items():
        assert man[f].startswith(p) and hashlib.sha256((ACQ / f).read_bytes()).hexdigest().startswith(p), f


def m0(t: int) -> int:
    return (t // 4) * 12 + 3 * (t % 4) + 1


def qmonths(q: int) -> list[int]:
    return [(q // 4) * 12 + 3 * (q % 4) + i for i in range(3)]


# ================================================================================================ data
class D:
    def __init__(self):
        import e41_lib as E
        th = E.e40_spec()
        self.tf, self.tg = th["food"], th["gap"]
        cp = pd.read_csv(ACQ / "tidy_cpi2012_yoy.csv")
        self.cpi = {(g, c): s.set_index("ym")["value"] for (g, c), s in cp.groupby(["geo", "commodity"])}
        self.st = pd.read_csv(ACQ / "tidy_stocks_national.csv").set_index("ym")
        fg = pd.read_csv(ACQ / "tidy_farmgate_palay.csv")
        fg = fg[(fg["variety"] == "other") & fg["value"].notna()]
        fg = fg[((fg["series"] == "old") & (fg["ym"] < 2010 * 12)) | ((fg["series"] == "new") & (fg["ym"] >= 2010 * 12))]
        self.fg = {g: s.set_index("ym")["value"] for g, s in fg.groupby("geo")}

    def c(self, p, com, ym):
        s = self.cpi[(p, com)]
        return float(s[ym]) if ym in s.index else np.nan

    def newest(self, s: pd.Series, M: int):
        """Newest value at month <= M, at most 3 months older (plan section 3)."""
        for k in range(4):
            if M - k in s.index and pd.notna(s[M - k]):
                return M - k
        return None


def supply(d: D, p: str, M_st: int, M_fg: int) -> dict:
    out = dict.fromkeys(S_FEATS, np.nan)
    tot, com, nfa = d.st["total"], d.st["commercial"], d.st["nfa"]
    M = d.newest(tot, M_st)
    if M is not None:
        if M - 12 in tot.index:
            out["S1_stocks_yoy"] = math.log(tot[M] / tot[M - 12])
            out["S4_commercial_yoy"] = math.log(com[M] / com[M - 12]) if com[M] > 0 and com[M - 12] > 0 else np.nan
        if M - 3 in tot.index:
            out["S2_stocks_d3"] = math.log(tot[M] / tot[M - 3])
        out["S3_nfa_share"] = nfa[M] / tot[M]
    s = d.fg.get(p)
    if s is None or d.newest(s, M_fg) is None:
        s = d.fg["IV-A"]
    M = d.newest(s, M_fg)
    if M is not None:
        if M - 12 in s.index:
            out["S5_farmgate_yoy"] = math.log(s[M] / s[M - 12])
        if M - 3 in s.index:
            out["S6_farmgate_d3"] = math.log(s[M] / s[M - 3])
    return out


def row(d: D, p: str, t: int, lag_st: int, lag_fg: int, world=None) -> dict | None:
    m = m0(t)
    F = [d.c(p, "food", m - i) for i in range(7)]
    A = [d.c(p, "all_items", m - i) for i in range(3)]
    tm = qmonths(t + 2)
    base = [d.c(p, "food", x - 12) for x in tm]
    gbase = [d.c(p, "food", x - 12) - d.c(p, "all_items", x - 12) for x in tm]
    if any(math.isnan(x) for x in F + A + base + gbase):
        return None
    f3, g3 = float(np.mean(F[:3])), float(np.mean(F[:3]) - np.mean(A))
    r = {"province": p, "t": t, "q": t + 2, "target": f"{(t + 2) // 4}-Q{(t + 2) % 4 + 1}",
         "F3": f3, "G3": g3, "xF": f3 - d.tf[p], "xG": g3 - d.tg[p], "F_last": F[0], "dF3": F[0] - F[3], "dF6": F[0] - F[6],
         "F_base": float(np.mean(base)), "G_base": float(np.mean(gbase)),
         "rice_yoy": d.c(p, "rice", m), "rice_d3": d.c(p, "rice", m) - d.c(p, "rice", m - 3),
         "pers_bin": float(f3 > d.tf[p] or g3 > d.tg[p]), **supply(d, p, m - lag_st, m - lag_fg)}
    if world is not None:
        r.update(world(t))
    ft = [d.c(p, "food", x) for x in tm]
    at = [d.c(p, "all_items", x) for x in tm]
    if not any(math.isnan(x) for x in ft + at):
        r["F_tgt"], r["G_tgt"] = float(np.mean(ft)), float(np.mean(ft) - np.mean(at))
        r["y"] = int(r["F_tgt"] > d.tf[p] or r["G_tgt"] > d.tg[p])
        # concurrent supply (leading test only): measured at the target months
        r.update({f"conc_{k}": v for k, v in supply(d, p, tm[-1], tm[-1]).items()})
    return r


# ================================================================================================ models
def _std(tr, te, cols):
    X = tr[cols].to_numpy(float)
    mu = np.nanmean(X, 0)
    mu = np.where(np.isnan(mu), 0, mu)
    X = np.where(np.isnan(X), mu, X)
    sd = X.std(0)
    sd[sd == 0] = 1
    Z = te[cols].to_numpy(float)
    Z = np.where(np.isnan(Z), mu, Z)
    return (X - mu) / sd, (Z - mu) / sd


def logit(tr, te, cols, C=None):
    X, Z = _std(tr, te, cols)
    y = tr["y"].to_numpy(int)
    if C is None:
        cut = tr["t"].quantile(0.75)
        a, b = (tr["t"] <= cut).to_numpy(), (tr["t"] > cut).to_numpy()
        best, C = np.inf, C_GRID[0]
        if len(set(y[a])) == 2:
            for c in C_GRID:
                ll = log_loss(y[b], LogisticRegression(C=c, max_iter=3000).fit(X[a], y[a]).predict_proba(X[b])[:, 1], labels=[0, 1])
                if ll < best:
                    best, C = ll, c
    return LogisticRegression(C=C, max_iter=3000).fit(X, y).predict_proba(Z)[:, 1]


def cont(tr, te, fcols):
    out = []
    for tgt, cols, th in (("F_tgt", ["F3", "F_base"] + fcols, "tf"), ("G_tgt", ["G3", "G_base"], "tg")):
        X, Z = _std(tr, te, cols)
        X1, Z1 = np.column_stack([np.ones(len(X)), X]), np.column_stack([np.ones(len(Z)), Z])
        yy = tr[tgt].to_numpy(float)
        b = np.linalg.lstsq(X1, yy, rcond=None)[0]
        sig = max(math.sqrt(float(np.mean((yy - X1 @ b) ** 2))), 0.1)
        thr = te["_thF"].to_numpy() if th == "tf" else te["_thG"].to_numpy()
        out.append(norm.cdf((Z1 @ b - thr) / sig))
    return 1 - (1 - out[0]) * (1 - out[1])


def war(tr, te, wf):
    tr = tr.dropna(subset=wf)
    avail = [c for c in wf if te[c].notna().all()]
    cr = {c: abs(tr[c].corr(tr["F_tgt"] - tr["F3"])) for c in avail}
    top = sorted(cr, key=cr.get, reverse=True)[:3]
    return cont(tr, te, top)


def run(lag_st: int, lag_fg: int, d: D, world=None, wf=None) -> pd.DataFrame:
    allr = [r for t in range(T_FIRST - 30, T_LAST + 1) for p in PROVS if (r := row(d, p, t, lag_st, lag_fg, world)) is not None]
    A = pd.DataFrame(allr)
    A["_thF"] = A["province"].map(d.tf)
    A["_thG"] = A["province"].map(d.tg)
    preds = []
    for t in range(T_FIRST, T_LAST + 1):
        te = A[(A["t"] == t) & A["y"].notna()].copy()
        tr = A[(A["t"] <= t - 3) & A["y"].notna()].copy()
        if te.empty or len(tr) < 40 or tr["y"].sum() < 5 or (1 - tr["y"]).sum() < 5:
            continue
        tr["y"] = tr["y"].astype(int)
        te["PERS_PROB"] = logit(tr, te, ["xF", "xG"], C=100.0)
        te["CLIM"] = te["province"].map(tr.groupby("province")["y"].mean()).fillna(tr["y"].mean())
        te["M1"] = logit(tr, te, ["xF", "xG", "S1_stocks_yoy", "S5_farmgate_yoy"], C=1.0)
        te["M2"] = logit(tr, te, P_FEATS + S_FEATS)
        te["M2_0"] = logit(tr, te, P_FEATS)
        te["M3"] = cont(tr, te, ["S1_stocks_yoy", "S5_farmgate_yoy"])
        te["M3_0"] = cont(tr, te, [])
        if wf:
            te["WAR_P"] = war(tr, te, wf)
        te["trainRows"] = len(tr)
        te["supplyMissing"] = te[S_FEATS].isna().sum(1)
        preds.append(te)
    return pd.concat(preds, ignore_index=True)


# ================================================================================================ evaluation
def metrics(y, p) -> dict:
    y, p = np.asarray(y, int), np.asarray(p, float)
    yh = (p >= .5).astype(int)
    tp, fp, fn, tn = [int(((yh == a) & (y == b)).sum()) for a, b in ((1, 1), (1, 0), (0, 1), (0, 0))]
    r = lambda a, b: a / b if b else None  # noqa: E731
    rec, spec, prec = r(tp, tp + fn), r(tn, tn + fp), r(tp, tp + fp)
    return {"n": len(y), "pos": int(y.sum()), "TP": tp, "FP": fp, "FN": fn, "TN": tn, "accuracy": (tp + tn) / len(y),
            "balanced": (rec + spec) / 2 if rec is not None and spec is not None else None, "precision": prec, "recall": rec,
            "specificity": spec, "f1": 2 * prec * rec / (prec + rec) if prec and rec else 0.0,
            "auc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else None, "brier": float(np.mean((p - y) ** 2))}


def boot(d: pd.DataFrame, a: str, b: str, block: int = 1) -> dict:
    l = (d[a] - d["y"]) ** 2 - (d[b] - d["y"]) ** 2
    g = l.groupby(d["q"]).agg(["sum", "size"]).sort_index()
    s, n = g["sum"].to_numpy(), g["size"].to_numpy()
    k = len(g)
    rng = np.random.default_rng(SEED)
    if block == 1:
        idx = rng.integers(0, k, size=(B, k))
    else:
        nb = math.ceil(k / block)
        st = rng.integers(0, k - block + 1, size=(B, nb))
        idx = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :k]
    bs = s[idx].sum(1) / n[idx].sum(1)
    return {"diff": float(l.mean()), "p_one_sided": float(np.mean(bs >= 0)), "clusters": k}


def calib(y, p) -> dict:
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    lg = np.log(p / (1 - p)).reshape(-1, 1)
    m = LogisticRegression(C=1e6, max_iter=3000).fit(lg, np.asarray(y, int))
    bins = pd.qcut(p, 5, duplicates="drop")
    tab = pd.DataFrame({"p": p, "y": y}).groupby(bins, observed=True).agg(meanP=("p", "mean"), observed=("y", "mean"), n=("y", "size"))
    return {"slope": float(m.coef_[0, 0]), "intercept": float(m.intercept_[0]),
            "bins": [{k: round(float(v), 3) for k, v in r.items()} for _, r in tab.iterrows()]}


def leading(d: pd.DataFrame) -> dict:
    d = d.assign(dF=d["F_tgt"] - d["F3"])
    out = {}
    rng = np.random.default_rng(SEED)
    qs = d["q"].unique()
    by = {q: g for q, g in d.groupby("q")}
    draws = [pd.concat([by[q] for q in rng.choice(qs, len(qs))]) for _ in range(1000)]
    for f in S_FEATS:
        res = {}
        for lab, col in (("leading", f), ("concurrent", f"conc_{f}")):
            g = d.dropna(subset=[col])
            v = [x.dropna(subset=[col])[col].corr(x.dropna(subset=[col])["dF"]) for x in draws]
            res[lab] = {"r": round(float(g[col].corr(g["dF"])), 3),
                        "CI90": [round(float(np.nanquantile(v, .05)), 3), round(float(np.nanquantile(v, .95)), 3)], "n": len(g)}
        out[f] = res
    return out


def evaluate(p: pd.DataFrame, cols: list[str]) -> dict:
    p = p[p["target"] >= "2002-Q1"]
    res = {"rows": len(p), "quarters": int(p["q"].nunique()), "prevalence": float(p["y"].mean()),
           "period": f"{p['target'].min()}..{p['target'].max()}",
           "supplyMissingCells": int(p["supplyMissing"].sum())}
    for c in ["pers_bin", "CLIM", "PERS_PROB"] + cols:
        res[c] = metrics(p["y"], p[c])
    res["vs_PERS_PROB"] = {c: {"cluster": boot(p, c, "PERS_PROB"), "block4": boot(p, c, "PERS_PROB", 4)}
                           for c in cols + ["CLIM"]}
    res["vs_ablation"] = {"M1": boot(p, "M1", "PERS_PROB"), "M2": boot(p, "M2", "M2_0"), "M3": boot(p, "M3", "M3_0")}
    return res


def main():
    plan_ok()
    d = D()
    s = importlib.util.spec_from_file_location("y10", RES / "y10_world_prices" / "run_dev.py")
    Y10 = importlib.util.module_from_spec(s)
    s.loader.exec_module(Y10)
    Y10.W = Y10.world()
    wf = [f"{c}_d{k}" for c in ("rice", "crude", "urea", "maize", "wheat", "palm") for k in (6, 12)]
    main_p = run(2, 1, d, Y10.wfeats, wf)
    sens_p = run(5, 4, d)
    cols = ["M1", "M2", "M3", "M2_0", "M3_0", "WAR_P"]
    res = {"main": evaluate(main_p, cols), "sensitivity": evaluate(sens_p, ["M1", "M2", "M3", "M2_0", "M3_0"])}
    # Holm over M1, M2, M3 (A1)
    ps = {c: res["main"]["vs_PERS_PROB"][c]["cluster"]["p_one_sided"] for c in ("M1", "M2", "M3")}
    order = sorted(ps, key=ps.get)
    holm, run_max = {}, 0.0
    for i, c in enumerate(order):
        run_max = max(run_max, min(1.0, (3 - i) * ps[c]))
        holm[c] = run_max
    acc = {}
    for c in ("M1", "M2", "M3"):
        m, b = res["main"], res["main"]["PERS_PROB"]
        acc[c] = {"A1": m["vs_PERS_PROB"][c]["cluster"]["diff"] < 0 and holm[c] < 0.10,
                  "A2": (m[c]["balanced"] or 0) >= (b["balanced"] or 0),
                  "A3": m["vs_ablation"][c]["diff"] < 0 and m["vs_ablation"][c]["p_one_sided"] < 0.10,
                  "A4": res["sensitivity"][c]["brier"] < res["sensitivity"]["PERS_PROB"]["brier"]}
        acc[c]["credible"] = all(acc[c].values())
    res["holm_p"] = holm
    res["acceptance"] = acc
    cred = [c for c in acc if acc[c]["credible"]]
    res["credible"] = cred
    res["step4Candidate"] = min(cred, key=lambda c: res["main"][c]["brier"]) if cred else None
    mp = main_p[main_p["target"] >= "2002-Q1"]
    res["calibration"] = {c: calib(mp["y"], mp[c]) for c in ("PERS_PROB", "M1", "M2", "M3")}
    res["perProvinceBrier"] = {c: mp.groupby("province").apply(lambda g: float(np.mean((g[c] - g["y"]) ** 2))).round(4).to_dict()
                               for c in ("PERS_PROB", "M1", "M2", "M3")}
    res["leadingTest"] = leading(mp)
    res["designEffect_note"] = "rows within a target quarter share national supply features; inference clusters by quarter"
    OUT.mkdir(exist_ok=True)
    (OUT / "dev_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    main_p.to_csv(OUT / "dev_rows_main.csv", index=False, lineterminator="\n", float_format="%.5f")
    sens_p.to_csv(OUT / "dev_rows_sens.csv", index=False, lineterminator="\n", float_format="%.5f")
    for k in ("main", "sensitivity"):
        r = res[k]
        print(f"== {k}: rows {r['rows']} quarters {r['quarters']} prevalence {r['prevalence']:.3f} {r['period']} missing supply cells {r['supplyMissingCells']}")
        for c in [x for x in ("pers_bin", "CLIM", "PERS_PROB") + tuple(cols) if x in r]:
            m = r[c]
            print(f"  {c:9s} acc {m['accuracy']:.3f} bal {m['balanced'] or 0:.3f} P {m['precision'] or 0:.2f} R {m['recall'] or 0:.2f} "
                  f"spec {m['specificity'] or 0:.2f} F1 {m['f1']:.3f} AUC {m['auc'] or 0:.3f} Brier {m['brier']:.4f}"
                  + (f"  vsPP {r['vs_PERS_PROB'][c]['cluster']['diff']:+.4f} p {r['vs_PERS_PROB'][c]['cluster']['p_one_sided']:.3f} "
                     f"(block4 p {r['vs_PERS_PROB'][c]['block4']['p_one_sided']:.3f})" if c in r["vs_PERS_PROB"] else ""))
    print("vs ablation:", res["main"]["vs_ablation"])
    print("holm:", holm)
    print("acceptance:", acc)
    print("credible:", cred, "step-4 candidate:", res["step4Candidate"])
    for c, v in res["calibration"].items():
        print("calibration", c, round(v["slope"], 3), round(v["intercept"], 3))
    for f, v in res["leadingTest"].items():
        print(f"lead test {f:18s} leading r {v['leading']['r']:+.3f} {v['leading']['CI90']}  concurrent r {v['concurrent']['r']:+.3f} {v['concurrent']['CI90']}")
    print("per-province Brier:", res["perProvinceBrier"])


if __name__ == "__main__":
    main()
