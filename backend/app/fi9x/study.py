"""FI9-X locked government + news fusion study (Lead 1 at two issue timings, Lead 2), with baselines and seasonal models.

    python -m app.fi9x.study lock
    python -m app.fi9x.study run          # refuses unless the lock matches; uses all cores

Origins: OP1 (FI9 issue: end of the quarter's 2nd month, target next quarter), QE1 (last day of the quarter, target
next quarter), OP2 (FI9 issue, two quarters ahead). Every configuration at an origin uses the same issue dates,
publication cutoffs and target quarters (2010-Q1 .. latest).

Stage 1: every base configuration is fitted at every labelled row with >= 20 earlier published targets (walk-forward).
Stage 2: residual, stacking, averaging and nested configurations are fitted only on the stage-1 walk-forward
         (chronological out-of-fold) predictions of earlier rows.
Stage 3: each probabilistic configuration's HIGH/LOW threshold is chosen per origin on earlier rows' out-of-fold
         predictions (FI7 inner region, balanced accuracy); naive persistence keeps 0.5, C0 keeps its own rule.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.fi5.target import qindex
from app.fi6 import models as M6
from app.fi6.features import GOV, OUTCOME
from app.fi6.news_model import NEWSA
from app.fi7 import models as M7
from app.fi7.experiments import WORLD, alternating_quarters, boot_delta
from app.fi9.evaluate import metrics, reliability
from app.fi9r.evaluate import _tau, local_level
from app.fi9x import OUT, VERSION
from app.fi9x import newsfeat as NF

DOMS = ["market", "climate", "employment", "remittance", "poverty"]
ORIGINS = {"OP1": ("operational", 1), "QE1": ("quarter_end", 1), "OP2": ("operational", 2)}
GOVF = OUTCOME + GOV + WORLD
EVAL_FIRST, MIN_TRAIN = "2010-Q1", 25          # FI7 inner folds need >= 25 training rows
REPS = {
    "R0": list(NEWSA),                                                                            # FI6-N features
    "R1": ["nidx_QTD"],                                                                           # food-stress index
    "R2": [f"z_dom_{d}_QTD" for d in DOMS] + ["z_dmg_QTD", "z_fam_QTD"],                           # domains, quarter to date
    "R3": ["z_hard_QTD", "z_warn_QTD", "z_resp_QTD", "z_disr_QTD", "z_netdir_QTD"],                # event types
    "R4": [f"z_dom_{d}_W30" for d in DOMS] + ["z_hard_W30"],                                      # last 30 days
    "R5": [f"z_dom_{d}_RW" for d in DOMS] + ["z_hard_RW"],                                        # recency weighted
    "R6": ["z_mom_hard", "z_mom_dom"],                                                            # momentum
    "R7": ["nidx_QTD", "z_hard_QTD", "z_resp_QTD", "z_mom_dom"],                                  # compact mix
    "R8": ["nidx_W90"],                                                                           # 90-day index
    "R9": ["nidx_LCQ"],                                                                           # last complete quarter
}
RAW = [f"{k}_{w}" for w in ["W30", "W60", "W90", "QTD", "LCQ", "RW"] for k in
       [f"dom_{d}" for d in DOMS] + ["hard", "warn", "resp", "disr", "netdir", "dmg", "fam", "vol"]] + ["mom_hard", "mom_dom"]

PROTOCOL = {
    "version": VERSION,
    "target": "FI9 target unchanged: SWS Balance Luzon hunger > preceding-20-quarter normal + round MOE",
    "origins": {k: f"{v[0]} issue, lead {v[1]}" for k, v in ORIGINS.items()},
    "representations": REPS,
    "configurations": "see CONFIGS / META in app/fi9x/study.py (frozen with this lock via code sha256)",
    "threshold": "per origin, balanced-accuracy-optimal on earlier rows' out-of-fold predictions (FI7 inner region)",
    "adoption_rule_lead1": [
        "FI7 reliability rule passes on full, on 2018+ (B) and without the sawtooth quarters",
        "accuracy >= 0.75, balanced accuracy >= 0.70 and recall >= 0.50 on full",
        "Brier better than C0 (production model, same origin) with block-bootstrap P >= 0.90",
        "Brier better than naive persistence with P >= 0.90",
        "mean Brier difference vs naive persistence negative in both 2010-2017 and 2018+",
        "the advantage over naive persistence stays negative when any single quarter is dropped",
        "ECE <= 0.10 and train-minus-out-of-sample accuracy <= 0.10",
        "news configurations: Brier better than their no-news counterpart with P >= 0.90",
    ],
    "max_reliable_lead": "the longest lead at the FI9 issue timing where some configuration passes the FI7 rule on full, "
                         "B and without sawtooth AND is not worse than naive persistence",
    "multiplicity": "about 40 configurations x 3 origins are compared; a pass must hold in both halves and survive "
                    "drop-one-quarter, and is reported with the number of configurations tried",
    "bootstrap": {"block": 4, "reps": 5000, "seed": 7},
}


# ------------------------------------------------------------------------------------------------ data
def frame(origin: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    from app.fi7.design import Designer
    timing, lead = ORIGINS[origin]
    D = Designer(timing)
    X = D.frame(lead).sort_values("issue_ts").reset_index(drop=True)
    cache = OUT / f"news_raw_{origin}.csv"
    if cache.exists():
        nf = pd.read_csv(cache, parse_dates=["issue_date"])
    else:
        nf = NF.features(X["issue_ts"])
        nf.to_csv(cache, index=False, lineterminator="\n")
    X = X.merge(nf.rename(columns={"issue_date": "issue_ts"}), on="issue_ts", how="left")
    X = pd.concat([X, NF.expanding_z(X, RAW)], axis=1)
    for w in ["QTD", "W90", "LCQ"]:
        X[f"nidx_{w}"] = X[[f"z_dom_{d}_{w}" for d in DOMS]].mean(axis=1, skipna=False)
    return X, D.q


# ------------------------------------------------------------------------------------------------ base models
class Seasonal:
    """Damped persistence on the deseasonalised series: quarter-of-year effects estimated from published readings."""

    def fit(self, tr, q_known):
        s = self._season(q_known)
        dev0 = tr["hunger_last"] - tr["last_reading_quarter"].map(lambda x: s.get(int(x[-1]), 0)) - tr["baseline_known"]
        dev1 = tr["hunger_target"] - tr["target_quarter"].map(lambda x: s.get(int(x[-1]), 0)) - tr["baseline_known"]
        a = tr["hunger_age_q"].to_numpy(float)
        ok = ~(dev0.isna() | dev1.isna()).to_numpy()
        grid = np.linspace(0, 1, 101)
        self.phi = float(grid[int(np.argmin([np.sum((dev1.to_numpy()[ok] - g ** a[ok] * dev0.to_numpy()[ok]) ** 2) for g in grid]))])
        self.sigma = max(float(np.std(dev1.to_numpy()[ok] - self.phi ** a[ok] * dev0.to_numpy()[ok], ddof=1)), 1.0)
        self.s = s
        return self

    @staticmethod
    def _season(q):
        q = q.sort_values("qi")
        trail = q["hunger"].rolling(20, min_periods=8).mean().shift(1)
        dev = (q["hunger"] - trail).dropna()
        k = q.loc[dev.index, "quarter"].str[-1].astype(int)
        m = dev.groupby(k).mean()
        return (m - m.mean()).to_dict() if len(m) == 4 else {}

    def level(self, te):
        sl = self.s.get(int(te["last_reading_quarter"][-1]), 0)
        st = self.s.get(int(te["target_quarter"][-1]), 0)
        return te["baseline_known"] + st + self.phi ** te["hunger_age_q"] * (te["hunger_last"] - sl - te["baseline_known"])


def _clf(features, l1=False):
    lr = LogisticRegression(penalty="elasticnet", solver="saga", l1_ratio=0.5, C=0.5, max_iter=5000) if l1 else \
        LogisticRegression(C=1.0, max_iter=2000)
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), lr)


def _usable(tr, cols):
    return [c for c in cols if c in tr and tr[c].notna().sum() >= 5 and tr[c].nunique() > 1]


CONFIGS = {   # name -> (kind, features)
    "Always LOW": ("const_low", None), "Always HIGH": ("const_high", None), "Climatology": ("clim", None),
    "Naive persistence": ("persist", None), "C0 damped persistence (production)": ("c0", None),
    "Damped persistence": ("damped", None), "Local level": ("ll", None), "Seasonal damped persistence": ("seasonal", None),
    "Logistic (government)": ("logit", GOVF), "Elastic-net logistic (government)": ("enet", GOVF),
    "Elastic-net logistic (government + news R2)": ("enet", GOVF + REPS["R2"]),
    "NLP-only logistic (news R2, no SWS)": ("logit", REPS["R2"]),
    "LightGBM (government)": ("lgbm", GOVF), "LightGBM (government + news R0)": ("lgbm", GOVF + REPS["R0"]),
    "LightGBM (government + news R1)": ("lgbm", GOVF + REPS["R1"]),
    "Ridge (latest reading only)": ("ridge", OUTCOME), "Ridge (government)": ("ridge", GOVF),
    **{f"Ridge (government + news {r})": ("ridge", GOVF + REPS[r]) for r in REPS},
    "News-only ridge (latest + news R1)": ("ridge", OUTCOME + REPS["R1"]),
    "News-only ridge (latest + news R2)": ("ridge", OUTCOME + REPS["R2"]),
    "Intermediate PCA (government only)": ("pca", (GOV + WORLD, [])),
    "Intermediate PCA (government + news)": ("pca", (GOV + WORLD, REPS["R2"] + REPS["R3"])),
}
META = {   # stage-2 configurations built from stage-1 out-of-fold predictions
    **{f"Residual: damped + news {r}": ("resid", "Damped persistence", r) for r in REPS},
    "Residual: LightGBM government + news R1": ("resid", "LightGBM (government)", "R1"),
    "Residual: seasonal + news R1": ("resid", "Seasonal damped persistence", "R1"),
    "Late fusion: stack (damped, LightGBM gov, news-only R1)": ("stack", ["Damped persistence", "LightGBM (government)", "News-only ridge (latest + news R1)"], None),
    "Late fusion: stack without news (damped, LightGBM gov)": ("stack", ["Damped persistence", "LightGBM (government)"], None),
    "Late fusion: average (damped, ridge gov + news R1)": ("avg", ["Damped persistence", "Ridge (government + news R1)"], None),
    "Timing-aware nested: residual, representation chosen in training": ("nested", "Residual: damped + news ", None),
    "Timing-aware nested: early ridge, representation chosen in training": ("nested", "Ridge (government + news ", None),
}
COUNTERPART = {
    **{f"Ridge (government + news {r})": "Ridge (government)" for r in REPS},
    "LightGBM (government + news R0)": "LightGBM (government)", "LightGBM (government + news R1)": "LightGBM (government)",
    "Elastic-net logistic (government + news R2)": "Elastic-net logistic (government)",
    "News-only ridge (latest + news R1)": "Ridge (latest reading only)", "News-only ridge (latest + news R2)": "Ridge (latest reading only)",
    "Intermediate PCA (government + news)": "Intermediate PCA (government only)",
    **{f"Residual: damped + news {r}": "Damped persistence" for r in REPS},
    "Residual: LightGBM government + news R1": "LightGBM (government)",
    "Residual: seasonal + news R1": "Seasonal damped persistence",
    "Late fusion: stack (damped, LightGBM gov, news-only R1)": "Late fusion: stack without news (damped, LightGBM gov)",
    "Late fusion: average (damped, ridge gov + news R1)": "Damped persistence",
    "Timing-aware nested: residual, representation chosen in training": "Damped persistence",
    "Timing-aware nested: early ridge, representation chosen in training": "Ridge (government)",
    "NLP-only logistic (news R2, no SWS)": "Climatology",
}
NEWS_CONFIGS = set(COUNTERPART)


def _fit_base(kind, feats, tr, te, q_known):
    y = tr["y"].to_numpy(int)
    r = te.iloc[0]
    if kind in ("const_low", "const_high", "clim"):
        p = float(y.mean())
        return {"p": p, "cls": {"const_low": 0, "const_high": 1}.get(kind), "tr_acc": float((y == (1 if kind == "const_high" else 0)).mean()),
                "tr_brier": float(np.mean((p - y) ** 2))}
    if kind == "c0" and len(tr) < 25:          # FI7 inner folds need >= 25 rows; only early rows (before 2010) hit this
        kind = "damped"
    if kind in ("persist", "c0", "damped", "lgbm", "ridge"):
        m = {"persist": lambda: M6.make("persist", None), "c0": lambda: M7.make("damped_tau", []), "damped": lambda: M7.make("damped", []),
             "lgbm": lambda: M6.make("reg", _usable(tr, feats)), "ridge": lambda: M7.RidgeDelta(_usable(tr, feats))}[kind]()
        m.fit(tr, tr["delta_target"].to_numpy(float))
        p, ptr = float(m.predict_proba(te)[0]), m.predict_proba(tr)
        if kind == "persist":
            lvl, cls, ctr = float(r["hunger_last"]), int(p >= 0.5), (ptr >= 0.5).astype(int)
        elif kind == "c0":
            lvl, cls, ctr = float(m.inner.predict_level(te)[0]), int(m.predict_class(te)[0]), m.predict_class(tr)
        elif kind == "damped":
            lvl, cls, ctr = float(m.predict_level(te)[0]), None, (ptr >= 0.5).astype(int)
        else:
            lvl, cls, ctr = float(r["hunger_last"] + m.predict_delta(te)[0]), None, (ptr >= 0.5).astype(int)
        return {"p": p, "level": lvl, "sd": float(m.sigma), "cls": cls, "tr_acc": float((ctr == y).mean()), "tr_brier": float(np.mean((ptr - y) ** 2))}
    if kind == "ll":
        ll = local_level(q_known, qindex(r["target_quarter"]))
        sd = float(np.sqrt(ll["var_state"] + ll["r_next"]))
        return {"p": float(1 - norm.cdf((r["threshold_known"] - ll["m"]) / sd)), "level": ll["m"], "sd": sd}
    if kind == "seasonal":
        m = Seasonal().fit(tr, q_known)
        lvl = float(m.level(r))
        ltr = tr.apply(m.level, axis=1).to_numpy(float)
        ptr = 1 - norm.cdf((tr["threshold_known"].to_numpy(float) - ltr) / m.sigma)
        return {"p": float(1 - norm.cdf((r["threshold_known"] - lvl) / m.sigma)), "level": lvl, "sd": m.sigma,
                "tr_acc": float(((ptr >= 0.5) == y).mean()), "tr_brier": float(np.mean((ptr - y) ** 2))}
    if kind in ("logit", "enet"):
        cols = _usable(tr, feats)
        if len(set(y)) < 2 or not cols:
            return {"p": float(y.mean())}
        m = _clf(cols, kind == "enet").fit(tr[cols], y)
        ptr = m.predict_proba(tr[cols])[:, 1]
        return {"p": float(m.predict_proba(te[cols])[0, 1]), "tr_acc": float(((ptr >= 0.5) == y).mean()), "tr_brier": float(np.mean((ptr - y) ** 2))}
    if kind == "pca":
        gcols, ncols = _usable(tr, feats[0]), _usable(tr, feats[1])
        Z_tr, Z_te = tr[OUTCOME].copy(), te[OUTCOME].copy()
        for tag, cols in (("g", gcols), ("n", ncols)):
            if len(cols) >= 2:
                pp = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), PCA(n_components=2)).fit(tr[cols])
                for j, (a, b) in enumerate(zip(pp.transform(tr[cols]).T, pp.transform(te[cols]).T)):
                    Z_tr[f"{tag}pc{j}"], Z_te[f"{tag}pc{j}"] = a, b
        for c in ("threshold_known", "y"):
            Z_tr[c], Z_te[c] = tr[c].to_numpy(), te[c].to_numpy()
        m = M7.RidgeDelta([c for c in Z_tr if c not in ("threshold_known", "y")]).fit(Z_tr, tr["delta_target"].to_numpy(float))
        ptr = m.predict_proba(Z_tr)
        return {"p": float(m.predict_proba(Z_te)[0]), "level": float(r["hunger_last"] + m.predict_delta(Z_te)[0]), "sd": m.sigma,
                "tr_acc": float(((ptr >= 0.5) == y).mean()), "tr_brier": float(np.mean((ptr - y) ** 2))}
    raise ValueError(kind)


def _stage1(args):
    origin, name, X, q = args
    kind, feats = CONFIGS[name]
    L = X[X["y"].notna()].reset_index(drop=True)
    out = []
    for i, r in L.iterrows():
        tr = L[L["target_published"] <= r["issue_ts"]]
        if len(tr) < MIN_TRAIN:
            continue
        res = _fit_base(kind, feats, tr, L.loc[[i]], q[q["published"] <= r["issue_ts"]])
        out.append({"origin": origin, "config": name, "row": i, **res})
    return out


# ------------------------------------------------------------------------------------------------ stage 2/3
def _inner(tr_idx: np.ndarray) -> np.ndarray:
    return tr_idx[max(M7.MIN_INNER_TRAIN, int(len(tr_idx) * 0.6)):]


def _stage2(origin: str, L: pd.DataFrame, P: pd.DataFrame) -> pd.DataFrame:
    piv = {c: g.set_index("row") for c, g in P.groupby("config")}
    rows = []
    pub, iss = L["target_published"].to_numpy(), L["issue_ts"].to_numpy()
    for i in range(len(L)):
        tr_idx = np.where(pub <= iss[i])[0]
        if len(tr_idx) < MIN_TRAIN:
            continue
        r = L.iloc[i]
        thr = float(r["threshold_known"])
        for name, (kind, base, rep) in META.items():
            if kind == "resid":
                b = piv[base]
                ok = [j for j in tr_idx if j in b.index and pd.notna(b.loc[j, "level"])]
                if i not in b.index or len(ok) < 15:
                    continue
                cols = [c for c in REPS[rep] if L.loc[ok, c].notna().sum() >= 5]
                lvl0 = float(b.loc[i, "level"])
                if not cols:
                    rows.append({"origin": origin, "config": name, "row": i, "p": float(b.loc[i, "p"]), "level": lvl0, "sd": float(b.loc[i, "sd"])})
                    continue
                res = L.loc[ok, "hunger_target"].to_numpy(float) - b.loc[ok, "level"].to_numpy(float)
                rg = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                   RidgeCV(alphas=[1.0, 10.0, 100.0, 1000.0], store_cv_results=True)).fit(L.loc[ok, cols], res)
                cv = rg[-1].cv_results_[:, list(rg[-1].alphas).index(rg[-1].alpha_)]
                sd = max(float(np.sqrt(np.mean(cv))), 1.0)
                lvl = lvl0 + float(rg.predict(L.loc[[i], cols])[0])
                rows.append({"origin": origin, "config": name, "row": i, "p": float(1 - norm.cdf((thr - lvl) / sd)), "level": lvl, "sd": sd})
            elif kind in ("stack", "avg"):
                if any(i not in piv[c].index for c in base):
                    continue
                if kind == "avg":
                    rows.append({"origin": origin, "config": name, "row": i, "p": float(np.mean([piv[c].loc[i, "p"] for c in base]))})
                    continue
                inn = [j for j in _inner(tr_idx) if all(j in piv[c].index for c in base)]
                ys = L.loc[inn, "y"].to_numpy(int)
                z = lambda p: np.log(np.clip(p, 1e-3, 1 - 1e-3) / (1 - np.clip(p, 1e-3, 1 - 1e-3)))
                if len(inn) < 15 or len(set(ys)) < 2:
                    continue
                Z = np.column_stack([z(piv[c].loc[inn, "p"].to_numpy(float)) for c in base])
                lr = LogisticRegression(C=1.0, max_iter=2000).fit(Z, ys)
                zi = np.array([[z(np.array([piv[c].loc[i, "p"]]))[0] for c in base]])
                rows.append({"origin": origin, "config": name, "row": i, "p": float(lr.predict_proba(zi)[0, 1])})
    return pd.DataFrame(rows)


def _nested(origin: str, L: pd.DataFrame, P: pd.DataFrame) -> pd.DataFrame:
    rows = []
    pub, iss = L["target_published"].to_numpy(), L["issue_ts"].to_numpy()
    for name, (kind, prefix, _) in META.items():
        if kind != "nested":
            continue
        cands = {c: g.set_index("row") for c, g in P.groupby("config") if c.startswith(prefix) and c.rstrip(")").split()[-1] in REPS and c.rstrip(")").split()[-1] != "R0"}
        for i in range(len(L)):
            tr_idx = np.where(pub <= iss[i])[0]
            inn = _inner(tr_idx)
            score = {}
            for c, g in cands.items():
                jj = [j for j in inn if j in g.index]
                if i in g.index and len(jj) >= 10:
                    score[c] = float(np.mean((g.loc[jj, "p"].to_numpy(float) - L.loc[jj, "y"].to_numpy(float)) ** 2))
            if not score:
                continue
            best = min(score, key=score.get)
            rec = cands[best].loc[i]
            rows.append({"origin": origin, "config": name, "row": i, "p": float(rec["p"]), "level": rec.get("level", np.nan),
                         "sd": rec.get("sd", np.nan), "chosen": best})
    return pd.DataFrame(rows)


def _thresholds(L: pd.DataFrame, P: pd.DataFrame) -> pd.DataFrame:
    out = []
    pub, iss = L["target_published"].to_numpy(), L["issue_ts"].to_numpy()
    for c, g in P.groupby("config"):
        g = g.set_index("row").sort_index()
        for i in g.index:
            rec = g.loc[i].to_dict()
            if pd.isna(rec.get("cls")):
                inn = [j for j in _inner(np.where(pub <= iss[i])[0]) if j in g.index]
                tau = _tau(g.loc[inn, "p"].to_numpy(float), L.loc[inn, "y"].to_numpy(int)) if len(inn) >= 10 else 0.5
                rec["cls"], rec["tau"] = int(rec["p"] >= tau), tau
                if pd.isna(rec.get("tr_acc")) and len(inn):
                    rec["tr_acc"] = float(((g.loc[inn, "p"] >= tau).astype(int) == L.loc[inn, "y"]).mean())
                    rec["tr_brier"] = float(np.mean((g.loc[inn, "p"] - L.loc[inn, "y"]) ** 2))
            out.append({"config": c, "row": i, **{k: v for k, v in rec.items() if k not in ("config",)}})
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------ evaluation
def _drop_one_max(a, b, y):
    d = (a - y) ** 2 - (b - y) ** 2
    return float(max((d.sum() - d[k]) / (len(d) - 1) for k in range(len(d))))


def evaluate(W: pd.DataFrame) -> dict:
    saw = set(alternating_quarters())
    res = {}
    for origin, G in W.groupby("origin"):
        yr = G["target_quarter"].str[:4].astype(int)
        periods = {"full": G, "A_2010_2017": G[yr <= 2017], "B_2018_plus": G[yr >= 2018], "without_sawtooth": G[~G["target_quarter"].isin(saw)],
                   "pre_2021": G[yr <= 2020], "post_2021": G[yr >= 2021], "news_rich_2014_plus": G[yr >= 2014]}
        R = {}
        for pname, g in periods.items():
            clim = g[g["config"] == "Climatology"]
            cb = float(np.mean((clim["p"] - clim["y"]) ** 2))
            base = {c: gg.set_index("target_quarter") for c, gg in g.groupby("config")}
            M = {}
            for c, gg in g.groupby("config"):
                s = metrics(gg.assign(level_hat=gg["level"], train_acc=gg["tr_acc"], train_brier=gg["tr_brier"]))
                s["reliability"] = reliability(s, cb)
                s["fnr"] = (s["confusion"]["fn"] / s["n_high"]) if s["n_high"] else None
                a = base[c]
                for ref, refname in (("vs_C0", "C0 damped persistence (production)"), ("vs_naive", "Naive persistence"),
                                     ("vs_counterpart", COUNTERPART.get(c))):
                    if refname and refname != c and refname in base:
                        b_ = base[refname].loc[a.index]
                        s[ref] = boot_delta((a["p"] - a["y"]) ** 2, (b_["p"] - b_["y"]) ** 2)
                        if pname == "full" and ref == "vs_naive":
                            s["vs_naive_drop_one_max"] = _drop_one_max(a["p"].to_numpy(), b_["p"].to_numpy(), a["y"].to_numpy())
                M[c] = s
            R[pname] = {"climatology_brier": cb, "n": int(g["target_quarter"].nunique()), "models": M}
        res[origin] = R
    return res


def adoption(E: dict) -> dict:
    out = {}
    for origin in ("OP1", "QE1"):
        F, B, A, N = (E[origin][k]["models"] for k in ("full", "B_2018_plus", "A_2010_2017", "without_sawtooth"))
        for c, s in F.items():
            if c in ("C0 damped persistence (production)", "Naive persistence", "Always LOW", "Always HIGH", "Climatology"):
                continue
            chk = {"reliability_full": s["reliability"]["passes"], "reliability_B": B[c]["reliability"]["passes"],
                   "reliability_without_sawtooth": N[c]["reliability"]["passes"],
                   "accuracy_ge_075_bacc_ge_070_recall_ge_050": s["accuracy"] >= 0.75 and (s["balanced_accuracy"] or 0) >= 0.70 and (s["recall"] or 0) >= 0.5,
                   "brier_vs_C0_P90": s["vs_C0"]["mean"] < 0 and s["vs_C0"]["p_negative"] >= 0.90,
                   "brier_vs_naive_P90": s["vs_naive"]["mean"] < 0 and s["vs_naive"]["p_negative"] >= 0.90,
                   "both_halves_better_than_naive": A[c]["vs_naive"]["mean"] < 0 and B[c]["vs_naive"]["mean"] < 0,
                   "drop_one_quarter_robust": s.get("vs_naive_drop_one_max", 1) < 0,
                   "ece_le_010": s["ece_5bin"] <= 0.10,
                   "overfit_gap_le_010": (s["train_accuracy_mean"] - s["accuracy"]) <= 0.10 if s["train_accuracy_mean"] == s["train_accuracy_mean"] else True}
            if c in NEWS_CONFIGS:
                chk["news_beats_counterpart_P90"] = "vs_counterpart" in s and s["vs_counterpart"]["mean"] < 0 and s["vs_counterpart"]["p_negative"] >= 0.90
            out[f"{origin} | {c}"] = {"checks": {k: bool(v) for k, v in chk.items()}, "adopt": bool(all(chk.values())),
                                      "n_failed": int(sum(not v for v in chk.values()))}
    adopted = [k for k, v in out.items() if v["adopt"]]
    lead = {}
    for origin in ("OP1", "OP2"):
        ok = [c for c, s in E[origin]["full"]["models"].items() if s["reliability"]["passes"] and E[origin]["B_2018_plus"]["models"][c]["reliability"]["passes"]
              and E[origin]["without_sawtooth"]["models"][c]["reliability"]["passes"] and (c == "Naive persistence" or s.get("vs_naive", {}).get("mean", 1) <= 0)]
        lead[origin] = ok
    return {"candidates": out, "adopted": adopted, "n_configurations_tested": len(out),
            "reliable_configurations_by_lead_FI9_timing": lead,
            "max_reliable_lead": max([int(o[-1]) for o, v in lead.items() if v], default=None),
            "decision": f"adopt {adopted}" if adopted else "retain production C0: no configuration passed every adoption check"}


# ------------------------------------------------------------------------------------------------ run
def _code_sha() -> str:
    from app.paths import BACKEND_DIR
    return hashlib.sha256(b"".join((BACKEND_DIR / "app" / "fi9x" / f).read_bytes().replace(b"\r\n", b"\n") for f in ("study.py", "newsfeat.py"))).hexdigest()


def _digest() -> str:
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True).encode()).hexdigest()


def run() -> dict:
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    if lock["sha256"] != _digest() or lock["code_sha256"] != _code_sha():
        raise RuntimeError("FI9-X protocol or code changed after the lock")
    frames = {o: frame(o) for o in ORIGINS}
    workers = max(1, (os.cpu_count() or 4) - 2)
    tasks = [(o, c, frames[o][0], frames[o][1]) for o in ORIGINS for c in CONFIGS]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        P1 = pd.DataFrame([r for part in ex.map(_stage1, tasks) for r in part])
    allrows = []
    for o in ORIGINS:
        L = frames[o][0][frames[o][0]["y"].notna()].reset_index(drop=True)
        P = P1[P1["origin"] == o]
        P2 = _stage2(o, L, P)
        P = pd.concat([P, P2], ignore_index=True)
        P = pd.concat([P, _nested(o, L, P)], ignore_index=True)
        T = _thresholds(L, P.drop(columns=["origin"]))
        T["origin"] = o
        T = T.merge(L[["issue_quarter", "issue_date", "target_quarter", "y", "hunger_target", "p_flip", "target_published"]].rename_axis("row").reset_index(), on="row")
        allrows.append(T[T["target_quarter"] >= EVAL_FIRST])
        frames[o][0].to_csv(OUT / f"design_{o}.csv", index=False, lineterminator="\n")
    W = pd.concat(allrows, ignore_index=True)
    W.to_csv(OUT / "predictions.csv", index=False, lineterminator="\n")
    E = evaluate(W)
    (OUT / "evaluation.json").write_text(json.dumps(E, indent=1, default=str))
    A = adoption(E)
    (OUT / "adoption.json").write_text(json.dumps(A, indent=1))
    return A


if __name__ == "__main__":
    if sys.argv[1:] == ["lock"]:
        from datetime import datetime, timezone
        p = OUT / "PROTOCOL_LOCK.json"
        if p.exists():
            sys.exit(f"already locked: {json.loads(p.read_text())['sha256']}")
        p.write_text(json.dumps({"sha256": _digest(), "code_sha256": _code_sha(), "configs": sorted(CONFIGS) + sorted(META),
                                 "locked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "protocol": PROTOCOL}, indent=1))
        print(_digest())
    elif sys.argv[1:] == ["run"]:
        a = run()
        print(a["decision"], "| tested", a["n_configurations_tested"], "| max reliable lead", a["max_reliable_lead"])
        print(json.dumps(a["reliable_configurations_by_lead_FI9_timing"], indent=1))
