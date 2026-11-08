"""
PFI model: three layers with separate evidence (see app.pfi docstring).

Level  logit(FIES_r) = a + b'x_r, x = official structural covariates of region r in the survey year; candidates are a
       short fixed list (one per information group plus two pairs) scored leave-one-region-out on the 17 FIES regions.
       Selection rule (fixed before scoring): lowest LOO mean absolute error in percentage points; a candidate with
       fewer covariates wins when it is within 0.25 pp of the best.
       Provinces: the selected regression applied to provincial covariates, then shifted by one constant (logit) so the
       population-weighted provincial mean equals the direct CALABARZON estimate (benchmarking, standard in small-area
       estimation).
Bridge logit FIES_t - logit FIES_s = lambda * (logit SWS12_t - logit SWS12_s), SWS12 = mean of the quarterly SWS hunger
       readings of the survey year (FIES recalls 12 months). Fitted on national 2021 -> 2023 (both verified, both in the
       study window); the CALABARZON 2023 -> 2025 wave is held out.
Projection  SWS for unobserved quarters = normal + phi**age * (latest - normal) (FI9 damped persistence, frozen phi and
       conformal half-width), normal = mean of the last 20 published quarterly readings.

Uncertainty is propagated by Monte Carlo with a fixed seed (identical inputs give identical outputs): survey sampling
error of the anchor, coefficient and between-area error of the level model, the sampling distribution of lambda, and the
SWS sampling/projection error.
"""
from __future__ import annotations


import numpy as np
import pandas as pd
from scipy import stats

from app.pfi import PROVINCES
from app.pfi import sources as S
from app.pfi.sources import expit, logit

RATE_COVS = {"poverty", "subsistence", "unemployment"}          # rates enter on the logit scale
CANDIDATES = {
    "M0 no covariate (mean of regions)": [],
    "M1 poverty": ["poverty"],
    "M2 subsistence (food poverty)": ["subsistence"],
    "M3 unemployment": ["unemployment"],
    "M4 rice inflation": ["rice_inflation"],
    "M5 poverty + unemployment": ["poverty", "unemployment"],
    "M6 poverty + rice inflation": ["poverty", "rice_inflation"],
}
TIE_PP = 0.25
SEED = 20261103
N_DRAWS = 20000
FIES_NATIONAL_SE_PP = 0.5      # assumption: the national FIES CI is not on file; ENNS/NNS national samples are large
SWS_NATIONAL_MOE = 2.5         # SWS national 95% margin (n ~1,200-1,500)


def _design(df: pd.DataFrame, covs: list[str]) -> np.ndarray:
    cols = [np.ones(len(df))]
    for c in covs:
        v = df[c].to_numpy(float)
        cols.append(logit(v / 100) if c in RATE_COVS else v)
    return np.column_stack(cols)


def _ols(X: np.ndarray, y: np.ndarray):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = max(len(y) - X.shape[1], 1)
    s2 = float(resid @ resid / dof)
    cov = s2 * np.linalg.pinv(X.T @ X)
    return beta, cov, s2, dof


def _class_metrics(y_true: np.ndarray, y_pred: np.ndarray, p: np.ndarray | None = None) -> dict:
    y_true, y_pred = np.asarray(y_true, bool), np.asarray(y_pred, bool)
    tp, tn = int((y_true & y_pred).sum()), int((~y_true & ~y_pred).sum())
    fp, fn = int((~y_true & y_pred).sum()), int((y_true & ~y_pred).sum())
    n = len(y_true)
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    prec = tp / (tp + fp) if tp + fp else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else 0.0
    acc = (tp + tn) / n
    lo, hi = _wilson(tp + tn, n)
    out = {"n": n, "tp": tp, "tn": tn, "fp": fp, "fn": fn, "accuracy": acc, "accuracy_ci95": [lo, hi],
           "balanced_accuracy": (rec + spec) / 2 if rec is not None and spec is not None else None,
           "precision": prec, "recall": rec, "specificity": spec, "f1": f1}
    if p is not None:
        p = np.asarray(p, float)
        out["brier"] = float(np.mean((p - y_true) ** 2))
        pos, neg = p[y_true], p[~y_true]
        out["roc_auc"] = float(np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg])) if len(pos) and len(neg) else None
        order = np.argsort(-p)
        hits, ap = 0, 0.0
        for k, i in enumerate(order, 1):
            if y_true[i]:
                hits += 1
                ap += hits / k
        out["pr_auc"] = ap / max(int(y_true.sum()), 1)
        out["calibration"] = _calibration(p, y_true)
    return out


def _calibration(p: np.ndarray, y: np.ndarray) -> list[dict]:
    bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0001]
    rows = []
    for a, b in zip(bins[:-1], bins[1:]):
        m = (p >= a) & (p < b)
        rows.append({"bin": f"{a:.1f}-{min(b, 1):.1f}", "n": int(m.sum()),
                     "mean_p": float(p[m].mean()) if m.any() else None, "observed": float(y[m].mean()) if m.any() else None})
    return rows


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (float(c - h), float(c + h))


# ------------------------------------------------------------------------------------------------------------- level
def loo_level(regions: pd.DataFrame, covs: list[str], national_pct: float) -> dict:
    """Leave-one-region-out predictions of FIES (pp), with predictive t-intervals and P(above national)."""
    y = logit(regions["fies"].to_numpy(float) / 100)
    X = _design(regions, covs)
    pred, sd, p_above = [], [], []
    for i in range(len(y)):
        m = np.arange(len(y)) != i
        beta, cov, s2, dof = _ols(X[m], y[m])
        mu = float(X[i] @ beta)
        s = float(np.sqrt(s2 + X[i] @ cov @ X[i]))
        pred.append(mu)
        sd.append(s)
        p_above.append(float(1 - stats.t.cdf((logit(national_pct / 100) - mu) / s, dof)))
    pred, sd = np.array(pred), np.array(sd)
    obs = regions["fies"].to_numpy(float)
    pp = 100 * expit(pred)
    lo, hi = 100 * expit(pred - 1.96 * sd), 100 * expit(pred + 1.96 * sd)
    err = pp - obs
    true_high = obs >= national_pct
    pred_high = pp >= national_pct
    return {"covariates": covs, "n": len(obs), "mae_pp": float(np.mean(np.abs(err))), "rmse_pp": float(np.sqrt(np.mean(err ** 2))),
            "bias_pp": float(np.mean(err)), "max_abs_error_pp": float(np.max(np.abs(err))),
            "spearman": float(stats.spearmanr(pp, obs).correlation), "interval95_coverage": float(np.mean((obs >= lo) & (obs <= hi))),
            "residual_sd_logit": float(np.sqrt(np.mean((pred - logit(obs / 100)) ** 2))),
            "classification_above_national": _class_metrics(true_high, pred_high, np.array(p_above)),
            "rows": [{"region": k, "observed_pct": float(o), "predicted_pct": float(q), "interval95_pct": [float(a), float(b)],
                      "p_above_national": float(pa), "observed_above_national": bool(th), "predicted_above_national": bool(ph)}
                     for k, o, q, a, b, pa, th, ph in zip(regions["key"], obs, pp, lo, hi, p_above, true_high, pred_high)]}


def select_level(scores: dict[str, dict]) -> str:
    best = min(scores.values(), key=lambda s: s["mae_pp"])["mae_pp"]
    ok = [k for k, s in scores.items() if s["mae_pp"] <= best + TIE_PP]
    return min(ok, key=lambda k: (len(scores[k]["covariates"]), scores[k]["mae_pp"]))


def fit_level(regions: pd.DataFrame, covs: list[str]) -> dict:
    y = logit(regions["fies"].to_numpy(float) / 100)
    X = _design(regions, covs)
    beta, cov, s2, dof = _ols(X, y)
    return {"covariates": covs, "beta": beta.tolist(), "cov": cov.tolist(), "s2": s2, "dof": dof,
            "terms": ["intercept"] + [f"logit({c})" if c in RATE_COVS else c for c in covs]}


def benchmark_shift(eta: np.ndarray, weights: np.ndarray, target: float) -> float:
    """Constant c with sum(w * expit(eta + c)) = target (bisection; monotone in c)."""
    w = weights / weights.sum()
    lo, hi = -5.0, 5.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if float(np.sum(w * expit(eta + mid))) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ------------------------------------------------------------------------------------------------------------ bridge
def sws_annual(area: str, year: int, as_of=None) -> tuple[float, float, int]:
    """Mean of the quarterly SWS readings in `year` (pp), its sampling SE (pp) and the number of quarters."""
    q = S.sws_quarterly(area, as_of)
    q = q[q["quarter"].str.startswith(str(year))]
    moe = q["moe"].to_numpy(float) if area == "balance_luzon" else np.full(len(q), SWS_NATIONAL_MOE)
    se = float(np.sqrt(np.sum((moe / 1.96) ** 2)) / len(q)) if len(q) else np.nan
    return float(q["value"].mean()), se, int(len(q))


def bridge_lambda(rng: np.random.Generator, n: int = N_DRAWS) -> dict:
    """lambda from national FIES 2021 -> 2023 and national SWS annual means, with a parametric bootstrap."""
    f = S.fies()
    nat = f[f["key"] == "PH"].set_index("year")["pct"]
    s21, se21, k21 = sws_annual("national", 2021)
    s23, se23, k23 = sws_annual("national", 2023)
    dF = float(logit(nat[2023] / 100) - logit(nat[2021] / 100))
    dS = float(logit(s23 / 100) - logit(s21 / 100))
    lam = dF / dS
    F21 = rng.normal(nat[2021], FIES_NATIONAL_SE_PP, n)
    F23 = rng.normal(nat[2023], FIES_NATIONAL_SE_PP, n)
    S21 = np.clip(rng.normal(s21, se21, n), 0.5, 99)
    S23 = np.clip(rng.normal(s23, se23, n), 0.5, 99)
    dS_d = logit(S23 / 100) - logit(S21 / 100)
    lam_d = (logit(F23 / 100) - logit(F21 / 100)) / np.where(np.abs(dS_d) < 1e-3, np.nan, dS_d)
    lam_d = np.clip(np.nan_to_num(lam_d, nan=lam), 0.0, 2.0)          # hunger and food insecurity move together (>= 0)
    pre = f[(f["key"] == "PH") & (f["year"] == 2019)]
    s19 = sws_annual("national", 2019)[0]
    sens = None
    if len(pre):
        sens = {"interval": "national 2019 -> 2021 (pre-2021; sensitivity only, not used)",
                "fies_change_logit": float(logit(nat[2021] / 100) - logit(nat[2019] / 100)),
                "sws_change_logit": float(logit(s21 / 100) - logit(s19 / 100)),
                "implied_lambda": float((logit(nat[2021] / 100) - logit(nat[2019] / 100)) / (logit(s21 / 100) - logit(s19 / 100))),
                "note": "Opposite signs: SWS 3-month hunger rose during the 2020-21 lockdown quarters while 12-month FIES fell "
                        "between the 2019 and 2021 waves. The bridge is not supported across that shock."}
    return {"lambda": lam, "draws": lam_d, "lambda_median": float(np.median(lam_d)),
            "lambda_ci90": [float(np.quantile(lam_d, 0.05)), float(np.quantile(lam_d, 0.95))],
            "fit_interval": "national FIES 2021 -> 2023 (verified) with national SWS annual means",
            "fies_pct": {"2021": float(nat[2021]), "2023": float(nat[2023])},
            "sws_annual_pct": {"2021": s21, "2023": s23}, "sws_quarters": {"2021": k21, "2023": k23},
            "fies_change_logit": dF, "sws_change_logit": dS, "sensitivity_pre_window": sens}


def bridge_holdout(lam: float, lam_draws: np.ndarray) -> dict:
    """Predict CALABARZON FIES 2025 from 2023 using Balance Luzon SWS (held out from the lambda fit)."""
    f = S.fies()
    r = f[f["key"] == "IV-A"].set_index("year")
    b23, b25 = sws_annual("balance_luzon", 2023)[0], sws_annual("balance_luzon", 2025)[0]
    dS = float(logit(b25 / 100) - logit(b23 / 100))
    base = float(logit(r.loc[2023, "pct"] / 100))
    pred = 100 * float(expit(base + lam * dS))
    dist = 100 * expit(base + lam_draws * dS)
    obs = float(r.loc[2025, "pct"])
    line = float(r.loc[2023, "ci_high"])
    return {"target": "CALABARZON FIES 2025 (FNRI 2025 Updating Survey via PIA; provisional secondary, no CI)",
            "anchor_2023_pct": float(r.loc[2023, "pct"]), "sws_bl_annual_pct": {"2023": b23, "2025": b25},
            "predicted_pct": pred, "predicted_ci90_pct": [float(np.quantile(dist, 0.05)), float(np.quantile(dist, 0.95))],
            "observed_pct": obs, "error_pp": pred - obs, "no_change_baseline_error_pp": float(r.loc[2023, "pct"]) - obs,
            "lambda_1_error_pp": 100 * float(expit(base + dS)) - obs,
            "class_line_pct": line, "observed_class": "HIGH" if obs > line else "LOW",
            "predicted_class": "HIGH" if pred > line else "LOW",
            "class_rule": "HIGH = above the upper 95% limit of the 2023 survey estimate (significantly above the last measured level)"}


# -------------------------------------------------------------------------------------------------------- projection
def project_sws(as_of, target_qi: int, phi: float, hw95: float) -> dict:
    """Balance Luzon SWS for the four quarters ending at `target_qi` (FIES-style 12-month window), release-aware."""
    q = S.sws_quarterly("balance_luzon", as_of)
    last = q.iloc[-1]
    L = int(last["qi"])
    normal = float(q[q["qi"] > L - 20]["value"].mean())
    window = []
    for qi in range(target_qi - 3, target_qi + 1):
        row = q[q["qi"] == qi]
        if len(row):
            window.append({"quarter": row["quarter"].iloc[0], "kind": "observed", "value": float(row["value"].iloc[0]),
                           "se": float(row["moe"].iloc[0]) / 1.96, "published": str(row["published"].iloc[0].date())})
        elif qi > L:
            lvl = normal + phi ** (qi - L) * (float(last["value"]) - normal)
            window.append({"quarter": f"{qi // 4}-Q{qi % 4 + 1}", "kind": "projected", "value": lvl, "se": hw95 / 1.96,
                           "age_quarters": qi - L})
        else:
            window.append({"quarter": f"{qi // 4}-Q{qi % 4 + 1}", "kind": "no survey", "value": None, "se": None})
    return {"latest_quarter": last["quarter"], "latest_value": float(last["value"]),
            "latest_published": str(last["published"].date()), "normal_5y": normal, "window": window}


def window_draws(win: list[dict], rng: np.random.Generator, n: int) -> np.ndarray:
    """Draws of the 12-month mean: independent sampling error for observed quarters, one common shock for projections."""
    shock = rng.standard_normal(n)
    vals = []
    for w in win:
        if w["value"] is None:
            continue
        if w["kind"] == "observed":
            vals.append(rng.normal(w["value"], w["se"], n))
        else:
            vals.append(w["value"] + w["se"] * shock)
    return np.clip(np.mean(vals, axis=0), 0.5, 99)


def shapley_two(f, base: dict, new: dict) -> dict:
    """Exact Shapley split of f(new) - f(base) between two factors (average over both orders)."""
    keys = list(base)
    out = {}
    for k in keys:
        other = [o for o in keys if o != k][0]
        a = f({k: new[k], other: base[other]}) - f(base)
        b = f(new) - f({k: base[k], other: new[other]})
        out[k] = (a + b) / 2
    return out


