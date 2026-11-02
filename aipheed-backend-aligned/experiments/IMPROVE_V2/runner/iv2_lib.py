"""IMPROVE_V2 library (PLAN.md sha 2973784a...). Reuses HISTORY_RETRAIN's data, label, feature, model and scoring code
(hr_lib, imported read-only); adds only what the plan defines: pooled SWS areas (I1), rate regression (I2), Platt
calibration (I3), the news columns (Objective 1), the PSA-only and NLP-only baselines and SHAP group shares."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import functools
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

IV = Path(__file__).resolve().parents[1]
EXP = IV.parent
ROOT = EXP.parents[1]
BACKEND = ROOT / "backend"
OUT = IV / "out"
sys.path.insert(0, str(EXP / "HISTORY_RETRAIN" / "runner"))
import hr_lib as H  # noqa: E402

H_LINE = H.H_LINE
LAST_ORIGIN = H.qi("2026-Q3")
ORIGINS = list(range(H.FIRST_ORIGIN, LAST_ORIGIN + 1))          # 1998-Q3..2026-Q3 (PLAN 3: walk-forward from 1998-Q3)
NEWS_ERA = H.qi("2021-Q1")
OTHER_AREAS = ["NCR", "VIS", "MIN"]
AREA_COLS = [f"area_{a}" for a in OTHER_AREAS]
HUNGER = ["h_last", "h_change", "h_mean4", "true_h", "pi_H4L"]
SHARES = [f"{c}_share" for c in ("price", "shortage", "disaster", "agri_supply", "jobs_income", "assistance")]
NEWS = ["N1R", "G_pri_yoy"] + SHARES
PSA = ["R_food_yoy", "R_head_yoy", "R_rice_yoy", "R_food_mom", "R_C3", "R_C4", "E1", "R_A3"]
REG_GRID = [c for c in H.GRID if c["cw"] is None]                # depth {1,2} x trees {50,150}
GROUPS = {"H1 Hunger (SWS)": HUNGER, "A1-A2 Food and headline prices": ["R_food_yoy", "R_head_yoy", "R_food_mom"],
          "A3 Rice": ["R_rice_yoy"], "C1 Climate (ONI)": ["ONI_last", "ONI_max12"], "C2 Typhoons": ["tc_mean"],
          "C3 Crops": ["R_C3"], "C4 Fisheries": ["R_C4"], "World prices": H.WORLD, "N1 News": NEWS,
          "Area indicator": AREA_COLS}
PLATT_MIN, PLATT_MIN_CLASS, SIGMA_MIN_ERR = 20, 5, 8

# arm -> (pooled, regression, platt); the base fit of I3 is REF and of ALL is I1+I2 (PLAN 3)
ARMS = {"REF": (False, False, False), "I1": (True, False, False), "I2": (False, True, False),
        "I3": (False, False, True), "ALL": (True, True, True)}
BASES = {"REF": (False, False), "I1": (True, False), "I2": (False, True), "I12": (True, True)}
BASE_OF = {"REF": "REF", "I1": "I1", "I2": "I2", "I3": "REF", "ALL": "I12"}


def arm_name(arm: str, news: bool) -> str:
    return arm + ("+news" if news else "")


def cols(pooled: bool, news: bool) -> list[str]:
    """REF = HISTORY_RETRAIN cols('T2', 'b', 'LGBM') = T2_B + lead, unchanged."""
    return H.T2_B + (AREA_COLS if pooled else []) + (NEWS if news else []) + ["lead"]


# ================================================================================================ news (Objective 1)
@functools.lru_cache(maxsize=1)
def _pipeline():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from app.news import pipeline_v3 as P
    return P


@functools.lru_cache(maxsize=1)
def intensities() -> dict:
    return dict(_pipeline().intensities())


def n1r(t: int, sc: dict | None = None) -> float:
    """FIRI_V2_DATA_AUDIT news_coverage.n1r: regional FSSI-v3 of quarter t, items published before O(t), NaN < 5."""
    P = _pipeline()
    sc = intensities() if sc is None else sc
    q = H.qs(t)
    vals = [sc[a["article_key"]] for a in P.asof(t) if a.get("quarter") == q and a["article_key"] in sc]
    return float(np.mean(vals)) if len(vals) >= 5 else float("nan")


@functools.lru_cache(maxsize=1)
def e112_shares() -> pd.DataFrame:
    t = pd.read_csv(EXP / "E112_Food_Insecurity_Forecasting" / "out" / "news_quarterly_corpus.csv")
    t["last_published"] = pd.to_datetime(t["last_published"])
    return t.set_index("q")


def shares_at(t: int, tab: pd.DataFrame | None = None) -> dict:
    """Quarter t's six category shares, usable at O(t) only if last_published < O(t) (E112 rule)."""
    tab = e112_shares() if tab is None else tab
    if t not in tab.index or tab.loc[t, "last_published"] >= pd.Timestamp(H.issue(t)):
        return {c: np.nan for c in SHARES}
    return {c: float(tab.loc[t, c]) for c in SHARES}


# ================================================================================================ pooled areas (I1)
def area_labels(d: H.Data) -> pd.DataFrame:
    """y = area hunger(q) > 11.3 for each area; BL equals hr_lib.t2_labels."""
    g = d.sws.groupby(["area", "q"])["H"].mean().reset_index()
    g["q"] = g["q"].astype(int)
    g["y"] = (g["H"] > H_LINE).astype(int)
    return g


def complete_area(d: H.Data, t: int) -> pd.DataFrame:
    """(area, q) with q <= t-1 whose every round was published before O(t); hr_lib.complete_bl for all areas."""
    O = H.issue(t)
    s = d.sws[d.sws["q"] <= t - 1]
    ok = s.groupby(["area", "q"])["published"].apply(lambda p: bool((p < O).all()))
    ok = ok[ok].reset_index()[["area", "q"]]
    ok["q"] = ok["q"].astype(int)
    return ok


def known_labels(d: H.Data, t: int, lab: pd.DataFrame) -> pd.DataFrame:
    return lab.merge(complete_area(d, t), on=["area", "q"], how="inner")


def pi_area(d: H.Data, t: int, k: int, area: str) -> dict:
    """hr_lib.pi_h4l for any area: sigma = four-area pooled RMSE at the true horizon; < 8 errors -> the area's own
    errors (>= 4) else 4.0. For BL this is pi_h4l exactly (checked). Also returns sigma (I2's fallback)."""
    kn = H.known(d, t, area)
    if not kn:
        return {"pi": np.nan, "h_last": np.nan, "true_h": np.nan, "sigma": np.nan, "kn": []}
    q_last, h_last = kn[-1][0], kn[-1][1]
    h = (t + k) - q_last
    errs = []
    for a in H.AREAS:
        dd = {x[0]: x[1] for x in H.known(d, t, a)}
        errs += [dd[q + h] - dd[q] for q in dd if q + h in dd]
    if len(errs) < H.POOL_MIN:
        dd = {x[0]: x[1] for x in kn}
        e0 = [dd[q + h] - dd[q] for q in dd if q + h in dd]
        sig = math.sqrt(np.mean(np.square(e0))) if len(e0) >= 4 else H.SIGMA_H_FALLBACK
    else:
        sig = math.sqrt(float(np.mean(np.square(errs))))
    return {"pi": float(norm.cdf((h_last - H_LINE) / max(sig, 0.5))), "h_last": h_last, "true_h": h, "sigma": sig,
            "kn": kn}


def rows_origin(d: H.Data, t: int, sc: dict | None = None, tab: pd.DataFrame | None = None) -> list[dict]:
    """All four areas' rows at origin t, leads 1..15. BL rows = hr_lib.rows_t2 plus news, area columns and sigma;
    other areas carry the same non-hunger values with their own hunger columns (PLAN 3, I1)."""
    bl = H.rows_t2(d, t)
    nw = {"N1R": n1r(t, sc), **shares_at(t, tab)}
    out = []
    for area in ["BL"] + OTHER_AREAS:
        hz = {k: pi_area(d, t, k, area) for k in range(1, H.KMAX + 1)}
        hs = [x[1] for x in hz[1]["kn"]]
        for r in bl:
            k = r["lead"]
            x = {**r, **nw, "area": area, **{c: float(area == c[5:]) for c in AREA_COLS}, "sigma_h": hz[k]["sigma"]}
            if area != "BL":
                x.update({"pi_H4L": hz[k]["pi"], "h_last": hz[k]["h_last"], "true_h": hz[k]["true_h"],
                          "h_change": hs[-1] - hs[-2] if len(hs) >= 2 else np.nan,
                          "h_mean4": float(np.mean(hs[-4:])) if hs else np.nan,
                          "sws_newest_published": hz[k]["kn"][-1][2] if hz[k]["kn"] else None, "H_fallback": None})
            out.append(x)
    return out


def table(d: H.Data, origins) -> pd.DataFrame:
    return pd.DataFrame([r for t in origins for r in rows_origin(d, t)])


# ================================================================================================ models
def _reg(cfg: dict, cc: list[str]):
    import lightgbm as lgb
    return lgb.LGBMRegressor(objective="regression", learning_rate=0.05, reg_lambda=5.0, deterministic=True,
                             force_row_wise=True, feature_pre_filter=False, random_state=H.SEED_LGBM, n_jobs=1,
                             verbose=-1, max_depth=cfg["depth"], num_leaves=cfg["leaves"], n_estimators=cfg["trees"],
                             min_child_samples=15)


def _folds_bl(tr: pd.DataFrame, ycol: str):
    """hr_lib.inner_folds on pooled rows: each of the last 4 training origins held out; fitted on all areas' rows whose
    target precedes it; scored on BL rows only (PLAN 3, I1). On BL-only rows this is inner_folds exactly."""
    origins = sorted(tr["t"].unique())[-4:]
    f = [(tr[tr["q"] <= o - 1], tr[(tr["t"] == o) & (tr["area"] == "BL")]) for o in origins]
    if ycol == "y":
        return [(a, h) for a, h in f if a["q"].nunique() >= 3 and a["y"].nunique() == 2 and len(h)]
    return [(a, h) for a, h in f if a["q"].nunique() >= 3 and len(h)]


def select_cls(tr: pd.DataFrame, cc: list[str]) -> dict:
    folds = _folds_bl(tr, "y")
    if not folds:
        return H.GRID[0]
    ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
    sc = {}
    for c in H.GRID:
        ps = np.concatenate([H.LGBM(c, cc, False).fit(f).predict(h) for f, h in folds])
        p = np.clip(ps, 1e-6, 1 - 1e-6)
        sc[c["id"]] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
    return min(H.GRID, key=lambda c: (round(sc[c["id"]], 9), c["id"]))


def select_reg(tr: pd.DataFrame, cc: list[str]) -> dict:
    folds = _folds_bl(tr, "H")
    if not folds:
        return REG_GRID[0]
    sc = {}
    for c in REG_GRID:
        e = np.concatenate([_reg(c, cc).fit(f[cc].astype(float), f["H"].to_numpy(float)).predict(h[cc].astype(float))
                            - h["H"].to_numpy(float) for f, h in folds])
        sc[c["id"]] = float(np.mean(e ** 2))
    return min(REG_GRID, key=lambda c: (round(sc[c["id"]], 9), c["id"]))


def shap_frame(model, X: pd.DataFrame) -> pd.DataFrame:
    c = model.predict(X.astype(float), pred_contrib=True)
    return pd.DataFrame(np.asarray(c)[:, :-1], columns=X.columns, index=X.index)


def fit_base(S: pd.DataFrame, t: int, lab: pd.DataFrame, pooled: bool, regression: bool, news: bool,
             clim: float, d: H.Data) -> pd.DataFrame:
    """Forecast rows of origin t (BL, leads 1-2). Classification: p_raw. Regression: H_hat (P is set later from past
    errors). Training rows: q' <= t-1, t' < t, label known before O(t) (hr_lib.train_rows), all areas if pooled."""
    cc = cols(pooled, news)
    te = S[(S["t"] == t) & S["lead"].isin([1, 2]) & (S["area"] == "BL")].copy()
    src = S if pooled else S[S["area"] == "BL"]
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    te["p_raw"], te["H_hat"], te["fallback"], te["cfg"] = np.nan, np.nan, False, None
    shap = None
    if not regression:
        if H.eligible(trb):
            cfg = H.lgbm_select(tr, cc, mono=False) if not pooled else select_cls(tr, cc)
            m = H.LGBM(cfg, cc, False).fit(tr)
            te["p_raw"], te["cfg"] = m.predict(te), cfg["id"]
            if m.m is not None:
                shap = shap_frame(m.m, te[cc])
        else:
            te["p_raw"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    else:
        if trb["q"].nunique() >= 6:
            cfg = select_reg(tr, cc)
            m = _reg(cfg, cc).fit(tr[cc].astype(float), tr["H"].to_numpy(float))
            te["H_hat"], te["cfg"] = m.predict(te[cc].astype(float)), cfg["id"]
            shap = shap_frame(m, te[cc])
        else:
            te["p_raw"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    te["n_train"] = len(tr)
    if shap is not None:
        te = pd.concat([te, shap.add_prefix("shap_")], axis=1)
    return te


def sigma_pass(F: pd.DataFrame, d: H.Data, lab_bl: pd.DataFrame) -> pd.DataFrame:
    """I2: P = Phi((H_hat - 11.3) / max(sigma_k, 0.5)); sigma_k = RMSE of this arm's own earlier errors at lead k whose
    targets were known before O(t); < 8 errors -> the pi_H4L sigma of the issue date."""
    F = F.sort_values(["t", "lead"]).copy()
    Hq = lab_bl.set_index("q")["H"]
    F["sigma_used"], F["sigma_fallback"], F["n_err"] = np.nan, False, 0
    for i, r in F.iterrows():
        if np.isnan(r["H_hat"]):
            continue
        known = H.complete_bl(d, int(r["t"]))
        prev = F[(F["t"] < r["t"]) & (F["lead"] == r["lead"]) & F["H_hat"].notna() & F["q"].isin(known)]
        e = prev["H_hat"].to_numpy(float) - prev["q"].map(Hq).to_numpy(float)
        if len(e) >= SIGMA_MIN_ERR:
            sig, fb = math.sqrt(float(np.mean(e ** 2))), False
        else:
            sig, fb = float(r["sigma_h"]), True
        F.at[i, "sigma_used"], F.at[i, "sigma_fallback"], F.at[i, "n_err"] = sig, fb, len(e)
        F.at[i, "p_raw"] = float(norm.cdf((r["H_hat"] - H_LINE) / max(sig, 0.5)))
    return F


def platt_pass(F: pd.DataFrame, d: H.Data, lab_bl: pd.DataFrame) -> pd.DataFrame:
    """I3: Platt on the arm's own earlier forecasts at lead k whose targets were known before O(t); >= 20 pairs with
    >= 5 of each class, else unchanged (counted)."""
    from sklearn.linear_model import LogisticRegression
    F = F.sort_values(["t", "lead"]).copy()
    yq = lab_bl.set_index("q")["y"]
    lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))  # noqa: E731
    F["p_cal"], F["platt_skipped"], F["n_pairs"] = F["p_raw"], True, 0
    for i, r in F.iterrows():
        known = H.complete_bl(d, int(r["t"]))
        prev = F[(F["t"] < r["t"]) & (F["lead"] == r["lead"]) & F["q"].isin(known)]
        y = prev["q"].map(yq).to_numpy(int)
        F.at[i, "n_pairs"] = len(y)
        if len(y) >= PLATT_MIN and y.sum() >= PLATT_MIN_CLASS and (1 - y).sum() >= PLATT_MIN_CLASS:
            m = LogisticRegression(C=1e6, solver="lbfgs", max_iter=5000).fit(lg(prev["p_raw"].to_numpy(float))[:, None], y)
            F.at[i, "p_cal"] = float(m.predict_proba(lg(np.array([r["p_raw"]]))[:, None])[0, 1])
            F.at[i, "platt_skipped"] = False
    return F


# ================================================================================================ baselines
def logit_lead(S: pd.DataFrame, t: int, lab: pd.DataFrame, cc: list[str], clim: float, min_origin: int) -> pd.DataFrame:
    """HISTORY_RETRAIN fit_one LOGIT path for T2 (one model per lead), with a column list and a first origin."""
    S = S[(S["area"] == "BL") & (S["t"] >= min_origin)]
    out = []
    for k in (1, 2):
        tk = S[(S["t"] == t) & (S["lead"] == k)].copy()
        tr = S[(S["t"] < t) & (S["q"] <= t - 1) & (S["lead"] == k)].merge(lab[["q", "y"]], on="q", how="inner")
        if H.eligible(tr):
            p, fb = H.logit(tr, tk, cc), False
        else:
            p, fb = np.full(len(tk), float(tr["y"].mean()) if len(tr) else clim), True
        tk["p"], tk["fallback"] = p, fb
        out.append(tk)
    return pd.concat(out)


def group_shares(G: pd.DataFrame, cc: list[str]) -> dict:
    sc = [c for c in cc if c != "lead"]
    A = G[[f"shap_{c}" for c in sc]].abs().to_numpy(float)
    tot = A.sum(axis=1, keepdims=True)
    A = np.divide(A, tot, out=np.zeros_like(A), where=tot > 0)
    s = pd.Series(A.mean(axis=0), index=sc)
    return {g: round(100 * float(s[[c for c in v if c in s.index]].sum()), 1) for g, v in GROUPS.items()
            if any(c in s.index for c in v)}
