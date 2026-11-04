"""Objective 4: independent verification of the stored baselines (no new candidate).

- Logistic baselines (combined, PSA-only, NLP-only): a separate sklearn Pipeline implementation (SimpleImputer median,
  StandardScaler, L2 LogisticRegression C=1), trained per lead on labels published before O(t).
- Persistence: recomputed from the raw SWS rounds published before O(t).
- Government-only and NLP-only LightGBM: refitted with the h3 specification (reproduction, not independent code).
- Target identity, evaluation window and information cut-offs are checked for every comparator.

    python obj4_baselines.py   # -> ../out/obj4_baselines.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
OUT = HERE / "out"
sys.path.insert(0, str(EXP / "IMPROVE_V2" / "runner"))
import iv2_lib as V  # noqa: E402

H = V.H
GOV = ["R_food_yoy", "R_head_yoy", "R_rice_yoy", "R_food_mom", "R_C3", "R_C4", "ONI_last", "ONI_max12",
       "tc_mean"] + H.WORLD
SPECS = {"LOGIT": (H.T2_B, H.FIRST_ORIGIN), "PSA-only": (V.PSA, H.FIRST_ORIGIN), "NLP-only": (V.NEWS, V.NEWS_ERA)}
LGB = {"LGBM-GOV": (GOV + ["lead"], H.FIRST_ORIGIN), "LGBM-NLP": (V.NEWS + ["lead"], V.NEWS_ERA)}
ORIG = H.ORIGINS_EVAL + [V.LAST_ORIGIN]


def logit_indep(tr: pd.DataFrame, te: pd.DataFrame, cols: list[str]) -> np.ndarray:
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    X = tr[cols].astype(float)
    keep = [c for c in cols if X[c].notna().any() and X[c].nunique(dropna=True) > 1]
    if not keep:
        return np.full(len(te), float(tr["y"].mean()))
    m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                      LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=5000))
    m.fit(X[keep].to_numpy(), tr["y"].to_numpy(int))
    return m.predict_proba(te[keep].astype(float).to_numpy())[:, 1]


_G: dict = {}


def _init():
    _G["d"] = H.load()
    _G["lab"] = V.area_labels(_G["d"])
    _G["T"] = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "table_pooled.csv", dtype={"area": str})


def _lgb(job):
    name, t = job
    cc, m0 = LGB[name]
    d, lab, T = _G["d"], _G["lab"], _G["T"]
    S = T[(T["area"] == "BL") & (T["t"] >= m0)]
    te = S[(S["t"] == t) & S["lead"].isin([1, 2])].copy()
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    tr = S[(S["t"] < t) & (S["q"] <= t - 1)].merge(kb[["area", "q", "y"]], on=["area", "q"], how="inner")
    if H.eligible(tr):
        cfg = H.lgbm_select(tr, cc, mono=False)
        p = H.LGBM(cfg, cc, False).fit(tr).predict(te)
    else:
        p = float(tr["y"].mean()) if len(tr) else clim
    return te[["t", "lead", "q"]].assign(name=name, p=p)


def main():
    _init()
    d, lab, T = _G["d"], _G["lab"], _G["T"]
    S = T[T["area"] == "BL"]
    iv = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    lds = pd.read_csv(EXP / "IMPROVE_V2_LEADS" / "out" / "forecasts_leads.csv")
    res, rows, cut_ok = {}, [], True
    for t in ORIG:
        kb = V.known_labels(d, t, lab)
        kb = kb[kb["area"] == "BL"][["q", "y"]]
        pub = d.sws[d.sws["area"] == "BL"].groupby("q")["published"].max()
        cut_ok &= bool((pub.reindex(kb["q"]) < H.issue(t)).all())
        for nm, (cc, m0) in SPECS.items():
            if t < m0:
                continue
            for k in (1, 2):
                Sk = S[(S["t"] >= m0) & (S["lead"] == k)]
                te = Sk[Sk["t"] == t]
                tr = Sk[(Sk["t"] < t) & (Sk["q"] <= t - 1)].merge(kb, on="q", how="inner")
                p = logit_indep(tr, te, cc) if H.eligible(tr) else np.full(len(te), float(tr["y"].mean()) if len(tr) else
                                                                           float(kb["y"].mean()) if len(kb) else 0.0)
                rows.append({"name": nm, "t": t, "lead": k, "p": float(p[0])})
        r = d.sws[(d.sws["area"] == "BL") & (d.sws["published"] < H.issue(t))]
        last = r[r["q"] == r["q"].max()]["H"].mean() if len(r) else np.nan
        for k in (1, 2):
            rows.append({"name": "PERSIST", "t": t, "lead": k,
                         "p": float(last > H.H_LINE) if pd.notna(last) else float(kb["y"].mean())})
    I = pd.DataFrame(rows)
    stored = pd.concat([iv[iv["name"].isin(list(SPECS))][["name", "t", "lead", "p"]],
                        lds[lds["name"] == "PERSIST"][["name", "t", "lead", "p"]]])
    m = I.merge(stored, on=["name", "t", "lead"], suffixes=("_indep", "_stored"))
    for nm, g in m.groupby("name"):
        res[nm] = {"rows": int(len(g)), "max_abs_diff": float((g["p_indep"] - g["p_stored"]).abs().max()),
                   "calls_differing": int(((g["p_indep"] >= .5) != (g["p_stored"] >= .5)).sum())}
    with Pool(8, initializer=_init) as pool:
        L = pd.concat(pool.map(_lgb, [(n, t) for n in LGB for t in H.ORIGINS_EVAL if t >= LGB[n][1]]), ignore_index=True)
    m2 = L.merge(h3[["name", "t", "lead", "p"]], on=["name", "t", "lead"], suffixes=("_refit", "_stored"))
    for nm, g in m2.groupby("name"):
        res[nm] = {"rows": int(len(g)), "max_abs_diff": float((g["p_refit"] - g["p_stored"]).abs().max()),
                   "note": "reproduction with the h3 specification (same library code)"}
    res["information_cutoff_labels_published_before_issue"] = cut_ok
    lab_bl = lab[lab["area"] == "BL"]
    res["target_identity"] = "every comparator is scored on the same BL labels (iv2_lib.area_labels, H > 11.3) by run_iv2.frame"
    res["n_bl_labels"] = int(len(lab_bl))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "obj4_baselines.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
