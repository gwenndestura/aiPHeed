"""FORECAST_RESEARCH library (PROTOCOL_FORECAST_RESEARCH.md): issue schedules A/B, the hunger term pi_H, the
continuous price-error arms Z0-Z3, the evaluation rows and the reliability rule. Reads only the snapshot in ../data
(written by snapshot.py from the FINAL_ARCHITECTURE build) and the FINAL_ARCHITECTURE evaluation rows.
"""
from __future__ import annotations

import functools
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

import metrics as M

HERE = Path(__file__).resolve().parent
FR = HERE.parent
EXP = FR.parent
DATA, OUT = FR / "data", FR / "out"
OUT.mkdir(exist_ok=True)
SEED = 2031
H_LINE, POOL_MIN = 11.3, 8
AREAS = ("NCR", "BL", "VIS", "MIN")
LEADS = (1, 2, 3, 4)
DEV_LAST = 2024 * 4 + 3
SPEC = json.loads((EXP / "E40_SWS_CPI_Tiers" / "label_spec.json").read_text())["thresholds"]
TH_F, TH_G = SPEC["food"], SPEC["gap"]

FAMILY_COLS = {
    "A1": ["A1_food", "A1_gap", "A_mom", "F_ex", "G_ex", "mom1", "mom6", "accel", "vol6", "O_food_yoy",
           "W_cereal_yoy"],
    "A2": ["A2", "W_crude_yoy"],
    "A3": ["A3", "R_rice_yoy", "R_rice_mom3", "O_rice_yoy", "W_rice_yoy", "W_rice_mom"],
    "V1": ["V1"], "C1": ["C1", "ONI_last", "ONI_max12"], "C2": ["C2"], "C3": ["C3", "W_urea_yoy"], "C4": ["C4"],
    "E1": ["E1"], "E2": ["E2"], "N1": ["N1", "G_pri_yoy"], "H1": ["h_last"],
}
FAMILIES = list(FAMILY_COLS)
F12 = [c for f in FAMILIES for c in FAMILY_COLS[f]] + ["lead"]
FAMILY_OF = {c: f for f, cs in FAMILY_COLS.items() for c in cs}


def qs(q: int) -> str:
    return f"{q // 4}-Q{q % 4 + 1}"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_protocol():
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().strip()
    assert sha256(FR / "PROTOCOL_FORECAST_RESEARCH.md") == want, "protocol changed after freezing"


# ================================================================================================ data
@functools.lru_cache(maxsize=1)
def stack() -> pd.DataFrame:
    S = pd.read_csv(DATA / "stack.csv", dtype={"province_code": str})
    S = S[S["lead"].isin(LEADS)].copy()
    ps = ps_full()
    S = S.merge(ps[["province_code", "q", "F", "HL"]].rename(columns={"q": "target_q"}),
                on=["province_code", "target_q"], how="left")
    S["ef"] = (S["F"] - S["province_code"].map(TH_F)) - S["A1_food"]
    S["eg"] = (S["F"] - S["HL"] - S["province_code"].map(TH_G)) - S["A1_gap"]
    return S.reset_index(drop=True)


@functools.lru_cache(maxsize=1)
def ps_full() -> pd.DataFrame:
    return pd.read_csv(DATA / "ps_full.csv", dtype={"province_code": str})


@functools.lru_cache(maxsize=1)
def rounds() -> pd.DataFrame:
    r = pd.read_csv(DATA / "sws_rounds_primary.csv")
    r["published"] = r["published"].astype(str).str[:10]
    return r


@functools.lru_cache(maxsize=1)
def eval_rows() -> pd.DataFrame:
    D = pd.read_csv(EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    keep = ["t", "lead", "province_code", "q", "y", "price", "hunger", "H", "pi_H4", "P5_price", "P0_price",
            "P0H4_p3", "S3_p", "PERSIST-SI_p", "CLIM_p", "ALWAYS-LOW_p"]
    return D[D["lead"].isin(LEADS)][keep].reset_index(drop=True)


# ================================================================================================ issue dates
def origin(t: int) -> pd.Timestamp:
    n = t + 1
    return pd.Timestamp(year=n // 4, month=(n % 4) * 3 + 1, day=1)


def issue(t: int, schedule: str) -> str:
    o = origin(t)
    if schedule == "A":
        return o.date().isoformat()
    cap = o + pd.DateOffset(months=2)                       # day 1 of month 3 of quarter t+1
    r = rounds()
    r = r[(r["area"] == "BL") & (r["q"] == t)]
    if len(r):
        last = pd.Timestamp(r["published"].max()) + pd.Timedelta(days=1)
        if last <= cap:
            return max(last, o).date().isoformat()
    return cap.date().isoformat()


def quarter_start(q: int) -> pd.Timestamp:
    return pd.Timestamp(year=q // 4, month=(q % 4) * 3 + 1, day=1)


# ================================================================================================ hunger term
@functools.lru_cache(maxsize=4096)
def known(iss: str, area: str) -> tuple:
    r = rounds()
    r = r[(r["area"] == area) & (r["published"] < iss)]
    return tuple((int(q), float(g["H"].mean()), g["published"].max()) for q, g in sorted(r.groupby("q")))


def pi_h(iss: str, target_q: int) -> dict:
    kn = known(iss, "BL")
    if not kn:
        return {"pi_H": float("nan")}
    q_last, h_last = kn[-1][0], kn[-1][1]
    h = target_q - q_last
    errs = []
    for a in AREAS:
        d = {x[0]: x[1] for x in known(iss, a)}
        errs += [d[q + h] - d[q] for q in d if q + h in d]
    if len(errs) < POOL_MIN:                                # LEAD2 a3.h4: fall back to the served H1 (lead rule)
        return {"pi_H": float("nan"), "h_last_iss": h_last, "sws_q": qs(q_last), "true_h": int(h),
                "sigma_h": float("nan"), "fallback": True}
    sig = math.sqrt(np.mean(np.square(errs)))
    return {"pi_H": float(norm.cdf((h_last - H_LINE) / max(sig, 0.5))), "h_last_iss": h_last,
            "sws_q": qs(q_last), "true_h": int(h), "sigma_h": sig, "fallback": False}


def hunger_climatology(iss: str) -> float:
    """Share of complete BL quarters published before iss that are above 11.3 (H1-removal ablation)."""
    kn = known(iss, "BL")
    return float(np.mean([h > H_LINE for _, h, _ in kn])) if kn else 0.5


# ================================================================================================ price arms
def _impute(tr: pd.DataFrame, te: pd.DataFrame, cols):
    med = tr[cols].median()
    return tr[cols].fillna(med).fillna(0.0).astype(float), te[cols].fillna(med).fillna(0.0).astype(float)


def _ridge_fit_predict(tr, te, cols, target, alpha):
    from sklearn.linear_model import Ridge
    a, b = _impute(tr, te, cols)
    mu, sd = a.mean(), a.std(ddof=0).replace(0, 1.0)
    m = Ridge(alpha=alpha).fit((a - mu) / sd, tr[target].to_numpy(float))
    return m.predict((b - mu) / sd)


LGB_GRID = [dict(id=f"g{i}", depth=d, trees=n, min_child=mc) for i, (d, n, mc) in
            enumerate((d, n, mc) for d in (1, 2) for n in (50, 150) for mc in (10, 20))]
RIDGE_GRID = [1.0, 10.0, 100.0, 1000.0]


def _lgb(cfg):
    import lightgbm as lgb
    return lgb.LGBMRegressor(objective="regression", learning_rate=0.05, n_estimators=cfg["trees"],
                             max_depth=cfg["depth"], num_leaves=2 ** cfg["depth"], min_child_samples=cfg["min_child"],
                             reg_lambda=5.0, colsample_bytree=0.8, subsample=1.0, deterministic=True,
                             force_row_wise=True, feature_pre_filter=False, random_state=SEED, n_jobs=1, verbose=-1)


def _lgb_fit_predict(tr, te, cols, target, cfg, return_model=False):
    m = _lgb(cfg).fit(tr[cols].astype(float), tr[target].to_numpy(float))
    p = m.predict(te[cols].astype(float))
    return (p, m) if return_model else p


def _folds(tr: pd.DataFrame):
    out = []
    for o in sorted(tr["t"].unique())[-4:]:
        f = tr[(tr["t"] < o) & (tr["target_q"] <= o - 1)]
        h = tr[tr["t"] == o]
        if f["target_q"].nunique() >= 3 and len(h):
            out.append((f, h))
    return out


def price_train(S: pd.DataFrame, t: int, target_mode: str = "error") -> pd.DataFrame:
    tr = S[(S["t"] < t) & (S["target_q"] <= t - 1) & S["F"].notna()].copy()
    if target_mode == "excess":                              # A1-removal ablation: predict the realised excess
        tr["ef"] = tr["F"] - tr["province_code"].map(TH_F)
        tr["eg"] = tr["F"] - tr["HL"] - tr["province_code"].map(TH_G)
    return tr


def _sigma_by_lead(res: pd.DataFrame, fallback: dict) -> dict:
    out = {}
    for k in LEADS:
        r = res[res["lead"] == k]
        out[k] = max(float(np.sqrt(np.mean(r["r"] ** 2))), 0.25) if len(r) >= 8 else fallback[k]
    return out


def price_arm(arm: str, S: pd.DataFrame, t: int, cols=None, target_mode: str = "error", return_models=False):
    """pi_P and the continuous forecasts for the rows of origin t (all leads 1-4)."""
    cols = F12 if cols is None else cols
    tr = price_train(S, t, target_mode)
    te = S[S["t"] == t].copy()
    base_f = te["A1_food"].to_numpy(float) if target_mode == "error" else np.zeros(len(te))
    base_g = te["A1_gap"].to_numpy(float) if target_mode == "error" else np.zeros(len(te))
    if target_mode == "excess":
        te_cols = [c for c in cols if c not in ("A1_food", "A1_gap")]
        cols = te_cols
    sd1 = {}
    for e in ("ef", "eg"):
        sd1[e] = {}
        for k in LEADS:
            g = tr[tr["lead"] == k]
            v = g[e].dropna()
            if g["target_q"].nunique() < 4 or not len(v):
                sd1[e][k] = 2.0
            elif arm == "Z0":
                sd1[e][k] = float(np.sqrt(np.mean(v ** 2)))      # e108_lib.sigmas (no floor)
            else:
                sd1[e][k] = max(float(v.std(ddof=1)), 0.25)
    info, models = {}, {}
    preds, sig = {}, {}
    for e in ("ef", "eg"):
        trn = tr[tr[e].notna()]
        if arm == "Z0" and target_mode == "error":
            preds[e] = np.zeros(len(te))
            sig[e] = sd1[e]
            continue
        if arm in ("Z0", "Z1") or len(trn) < 30:
            mu = {k: float(trn.loc[trn["lead"] == k, e].mean()) if (trn["lead"] == k).sum() else 0.0 for k in LEADS}
            if arm == "Z0":                                 # excess mode: zero forecast of excess is meaningless
                mu = {k: float(trn[e].mean()) for k in LEADS}
            preds[e] = te["lead"].map(mu).to_numpy(float)
            sig[e] = sd1[e]
            continue
        folds = _folds(trn)
        grid = RIDGE_GRID if arm == "Z2" else LGB_GRID
        best, best_se, best_res = grid[0], None, None
        if folds:
            for g in grid:
                res = []
                for f, h in folds:
                    p = (_ridge_fit_predict(f, h, cols, e, g) if arm == "Z2" else _lgb_fit_predict(f, h, cols, e, g))
                    res.append(pd.DataFrame({"lead": h["lead"].to_numpy(), "r": h[e].to_numpy(float) - p}))
                res = pd.concat(res)
                se = float(np.mean(res["r"] ** 2))
                if best_se is None or round(se, 10) < round(best_se, 10):
                    best, best_se, best_res = g, se, res
        if arm == "Z2":
            preds[e] = _ridge_fit_predict(trn, te, cols, e, best)
        else:
            preds[e], models[e] = _lgb_fit_predict(trn, te, cols, e, best, return_model=True)
        sig[e] = _sigma_by_lead(best_res, sd1[e]) if best_res is not None else sd1[e]
        info[e] = best if arm == "Z2" else best["id"]
    fh = base_f + preds["ef"]
    gh = base_g + preds["eg"]
    sf = te["lead"].map(sig["ef"]).to_numpy(float)
    sg = te["lead"].map(sig["eg"]).to_numpy(float)
    pf, pg = norm.cdf(fh / sf), norm.cdf(gh / sg)
    pp = 1 - (1 - pf) * (1 - pg)
    out = te[["t", "lead", "province_code", "target_q"]].copy()
    out["pi_P"], out["ef_hat"], out["eg_hat"] = pp, preds["ef"], preds["eg"]
    out["F_ex_hat"], out["G_ex_hat"], out["sigma_f"], out["sigma_g"] = fh, gh, sf, sg
    out["cfg"] = json.dumps(info) if info else arm
    if return_models:
        out.attrs["models"], out.attrs["cols"] = models, cols
    return out


# ================================================================================================ run
def run_arm(arm: str, origins, cols=None, target_mode: str = "error", S=None) -> pd.DataFrame:
    S = stack() if S is None else S
    return pd.concat([price_arm(arm, S, int(t), cols, target_mode) for t in origins], ignore_index=True)


def attach_hunger(P: pd.DataFrame, schedule: str, climatology: bool = False) -> pd.DataFrame:
    P = P.copy()
    h1 = stack().set_index(["t", "lead", "province_code"])["H1"]
    rows = []
    for t, k, p in zip(P["t"], P["lead"], P["province_code"]):
        iss = issue(int(t), schedule)
        h = pi_h(iss, int(t) + int(k))
        if np.isnan(h["pi_H"]):                              # pooled sigma not estimable: served H1 at O(t)
            h["pi_H"] = float(h1[(int(t), int(k), p)])
        if climatology:
            h["pi_H"] = hunger_climatology(iss)
        rows.append({"issue_date": iss, "warning_days": (quarter_start(int(t) + int(k)) - pd.Timestamp(iss)).days,
                     **h})
    return pd.concat([P.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def persistence(E: pd.DataFrame, schedule: str) -> np.ndarray:
    """Same-information persistence: newest hunger reading at the schedule's issue date AND the price condition on
    the newest three published CPI months (F_ex / G_ex of the stack)."""
    S = stack().drop_duplicates(["t", "province_code"]).set_index(["t", "province_code"])
    out = []
    for t, p, clim in zip(E["t"], E["province_code"], E["CLIM_p"]):
        kn = known(issue(int(t), schedule), "BL")
        fx, gx = S.loc[(int(t), p), "F_ex"], S.loc[(int(t), p), "G_ex"]
        if not kn or pd.isna(fx) or pd.isna(gx):
            out.append(clim)
            continue
        out.append(float(kn[-1][1] > H_LINE and (fx > 0 or gx > 0)))
    return np.array(out)


def evaluate(E: pd.DataFrame, col: str, pers_col: str) -> dict:
    """R1-R7 at one lead (FINAL_THESIS_OBJECTIVES ch1_lib.decide, re-implemented on these columns)."""
    y = E["y"].to_numpy(int)
    m = M.cls(y, E[col])
    acc_base = {b: float(((E[c] >= .5).astype(int) == E["y"]).mean())
                for b, c in (("ALWAYS-LOW", "ALWAYS-LOW_p"), ("PERSIST", pers_col))}
    bs = (E[col] - y) ** 2
    tp = M.boot_diff(E["q"], bs, (E[pers_col] - y) ** 2)
    tc = M.boot_diff(E["q"], bs, (E["CLIM_p"] - y) ** 2)
    uq = np.array(sorted(E["q"].unique()))
    thirds = np.array_split(uq, 3)
    acc3 = [float(((E[E["q"].isin(th)][col] >= .5).astype(int) == E[E["q"].isin(th)]["y"]).mean()) for th in thirds]
    loqo = [float(((E[E["q"] != q][col] >= .5).astype(int) == E[E["q"] != q]["y"]).mean()) for q in uq]
    c = {"R1": len(uq) >= 10 and len(E) >= 40, "R2": m["accuracy"] >= .75, "R3": m["balanced_accuracy"] >= .70,
         "R4": m["accuracy"] > acc_base["ALWAYS-LOW"] and m["accuracy"] > acc_base["PERSIST"],
         "R5": tp["diff"] < 0 and tc["diff"] < 0 and tp["p_less"] < .10 and tc["p_less"] < .10,
         "R6": m["precision"] >= .60 and m["recall"] >= .60,
         "R7": min(acc3) >= .60 and min(loqo) >= .70}
    return {"metrics": m, "acc_ci90": M.acc_ci(E["q"], y, E[col]), "baseline_accuracy": acc_base,
            "brier_vs_persist": tp, "brier_vs_clim": tc, "acc_thirds": acc3, "loqo_min": min(loqo),
            "criteria": c, "failed": [k for k, v in c.items() if not v], "reliable": all(c.values())}


def max_reliable(dec: dict) -> int:
    best = 0
    for k in LEADS:
        if dec[k]["reliable"]:
            best = k
        else:
            break
    return best
