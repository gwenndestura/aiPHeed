"""FINAL_OBJECTIVE_ACHIEVEMENT library (FINAL_FORECASTING_PROTOCOL.md). A thin layer over the FINAL library
(`../../FINAL_FOOD_INSECURITY_LIGHTGBM/runner/fi_lib.py`), which is imported unchanged. The changes are:

  F1  LightGBM learns d = H_q - h_last (deviation from persistence); the class and level come from h_last + d-hat
  F2  Lead 0 (the quarter that just ended, survey not yet published) is added; rows whose target is already published
      at the issue date are dropped
  F3  news columns come from GDELT GKG (real-time timestamps): NG_gap_<cat> x6 + NG_ant, plus FSSI-v3 (N1)
  F4  post_break = 1 when the newest known SWS reading is an adult-base round (published on or after 2025-06-27)
  F5  ASYM variant: quantile objective, alpha 0.7
"""
from __future__ import annotations

import functools
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OA = HERE.parent
EXP = OA.parent
sys.path.insert(0, str(EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM" / "runner"))
import fi_lib as M  # noqa: E402
import news_features as NF  # noqa: E402

np, pd, norm = M.np, M.pd, M.norm
OUT = OA / "out"
DATA = OA / "data"
LEADS = (0, 1, 2, 3, 4)
BREAK_PUBLISHED = "2025-06-27"                               # first adult-base round (April 2025) publication
NG_COLS = NF.news_cols("NG")
OA_NEWS = ["N1"] + NG_COLS
OA_COLS = M.H_COLS + M.E107_COLS + ["A_since"] + NG_COLS + ["post_break"]
FAMILY_COLS = {**M.FAMILY_COLS, "N1": OA_NEWS}
CORPUS_COLS = [c for c in OA_COLS if c not in NG_COLS] + NF.news_cols("NC")

M.LEADS = LEADS
M.NEWS_COLS = OA_NEWS
_ASYM = {"on": False}

# ------------------------------------------------------------------------------------------------ F2 F3 F4 rows
_orig_row = M.row_features


def row_features(area, t, k, dataset="primary", variant="primary"):
    r = _orig_row(area, t, k, dataset, variant)
    if r is None or r["true_horizon"] < 1:                    # target already published: not a forecast
        return None
    fw, iss = r["sws_newest_fieldwork_end"], r["issue_date"]
    g = NF.gap_features(fw, iss, "G")
    r.update(dict(zip(NG_COLS, g[:7])))
    r["gkg_n_window"], r["gkg_latest_published"] = g[7], (str(g[8]) if g[8] is not None else None)
    r["post_break"] = float(r["sws_newest_published"] >= BREAK_PUBLISHED)
    return r


M.row_features = row_features

# ------------------------------------------------------------------------------------------------ F1 target
_orig_training = M.training


def training(P, t, dataset):
    tr = _orig_training(P, t, dataset)
    if len(tr):
        tr = tr.copy()
        tr["z_tr"] = tr["z_tr"] - tr["h_anom"]                # z - (h_last - REF-hat) = H - h_last = d
    return tr


M.training = training
_orig_fil = M.fil_forecasts


def fil_forecasts(P, cols, dataset, **kw):
    F = _orig_fil(P, cols, dataset, **kw)
    if not len(F):
        return F
    F = F.merge(P[["area_name", "t", "lead", "h_anom"]], on=["area_name", "t", "lead"], how="left")
    F["dhat"] = F["zhat"]
    F["zhat"] = F["dhat"] + F["h_anom"]                       # back to z: level = REF-hat + z = h_last + d
    return F.drop(columns="h_anom")


M.fil_forecasts = fil_forecasts

# ------------------------------------------------------------------------------------------------ F5 ASYM
_orig_lgbm = M._lgbm


def _lgbm(leaves, trees):
    m = _orig_lgbm(leaves, trees)
    if _ASYM["on"]:
        m.set_params(objective="quantile", alpha=0.7)
    return m


M._lgbm = _lgbm


def set_asym(on: bool):
    _ASYM["on"] = on


def clear_caches():
    for f in (M.known, M.final_values, M.panel, NF.gap_features):
        f.cache_clear()


def max_reliable_lead(dec: dict) -> int | None:
    """Largest K such that every lead from the shortest evaluated lead up to K passes; None if the first fails."""
    best = None
    for k in LEADS:
        if dec[k]["pass"]:
            best = k
        else:
            break
    return best


# ------------------------------------------------------------------------------------------------ V1-V3
def rounds_by_quarter() -> pd.DataFrame:
    return M.rounds("primary")


def test_retest() -> dict:
    """V1: ELEVATED from each of two same-quarter rounds against the same REF."""
    r = rounds_by_quarter()
    pairs = []
    for (a, q), g in r.groupby(["area", "q"]):
        if len(g) != 2:
            continue
        ref = M.ref_final(a, q)
        h1, h2 = g.sort_values("published")["H"].to_numpy()
        pairs.append({"area": a, "quarter": M.qs(int(q)), "round1": h1, "round2": h2, "diff": h2 - h1,
                      "ref": ref, "agree": None if ref is None else int((h1 > ref) == (h2 > ref))})
    d = pd.DataFrame(pairs)
    v = d.dropna(subset=["ref"])
    a = float(v["agree"].mean()) if len(v) else float("nan")
    p = (1 + math.sqrt(2 * a - 1)) / 2 if a > 0.5 else 0.5
    return {"pairs": d.to_dict("records"), "n_pairs_with_label": len(v), "agreement": a,
            "implied_max_accuracy": p, "mean_abs_diff": float(d["diff"].abs().mean()),
            "max_abs_diff": float(d["diff"].abs().max())}


def area_params() -> dict:
    """V2: per-area Q from consecutive 2021+ quarter means (each with its own sampling variance), R = mean round
    variance; quarter pattern of observations."""
    r = rounds_by_quarter()
    out = {}
    for a in M.AREAS:
        g = r[r["area"] == a]
        qm = g.groupby("q").agg(H=("H", "mean"), R=("moe", lambda m: float(np.mean((np.asarray(m) / 1.959964) ** 2)
                                                                         / len(m))))
        vals = [((qm.loc[q, "H"] - qm.loc[q - 1, "H"]) ** 2 - qm.loc[q, "R"] - qm.loc[q - 1, "R"])
                for q in qm.index if q - 1 in qm.index]
        out[a] = {"Q": max(float(np.mean(vals)), 0.25), "R": float(np.mean((g["moe"] / 1.959964) ** 2)),
                  "n_pairs": len(vals), "obs_q": [int(q) for q in qm.index]}
    return out


def simulate(Q: float, R: float, obs_q: list[int], rng, n_series: int = 2000) -> dict:
    """V2: random-walk level + noise on the observed 2021+ quarter pattern. For every newest observation n and
    horizon h (target n+h observed, >= 2 observed in its REF window) score Bayes, PERSIST and MA2 calls."""
    q0, q1 = min(obs_q), max(obs_q)
    T = q1 - q0 + 1
    obs = np.zeros(T, bool)
    obs[[q - q0 for q in obs_q]] = True
    res = {h: {"bayes": [], "persist": [], "ma2": []} for h in range(1, 6)}
    for _ in range(n_series):
        lv = np.cumsum(rng.normal(0, math.sqrt(Q), T)) + 15.0
        y = np.where(obs, lv + rng.normal(0, math.sqrt(R), T), np.nan)
        acc = {h: {"bayes": [], "persist": [], "ma2": []} for h in range(1, 6)}
        a, P, last = None, None, None
        for n in range(T):                                    # Kalman filter over observed quarters
            if not obs[n]:
                continue
            if a is None:
                a, P = y[n], R
            else:
                P = P + Q * (n - last)
                K = P / (P + R)
                a, P = a + K * (y[n] - a), (1 - K) * P
            last = n
            known = [i for i in range(n + 1) if obs[i]]
            for h in range(1, 6):
                tq = n + h
                if tq >= T or not obs[tq]:
                    continue
                win = [i for i in range(tq - 4, tq) if obs[i]]
                if len(win) < 2:
                    continue
                truth = y[tq] > np.mean(y[win])
                fill = lambda val: np.mean([y[i] if i <= n else val for i in range(tq - 4, tq)    # noqa: E731
                                            if i > n or obs[i]])
                refh_b = fill(a)
                acc[h]["bayes"].append((a - refh_b > 0) == truth)
                hp = y[n]
                acc[h]["persist"].append((hp - fill(hp) > 0) == truth)
                ma = np.mean([y[i] for i in known[-2:]])
                acc[h]["ma2"].append((ma - fill(hp) > 0) == truth)
        for h in acc:
            for m in acc[h]:
                if acc[h][m]:
                    res[h][m].append(np.mean(acc[h][m]))
    return {h: {m: {"mean": float(np.mean(v)), "p05": float(np.quantile(v, 0.05)), "p95": float(np.quantile(v, .95))}
                for m, v in res[h].items() if v} for h in res}


def observed_baselines(P: pd.DataFrame) -> dict:
    """Observed 2021+ accuracy of PERSIST and MA2 by true horizon, over all panel rows with a label."""
    D = P[P["label"].notna()].copy()
    D["persist"] = ((D["h_last"] - D["ref_hat"]) > 0).astype(int) == D["label"]
    D["ma2"] = ((D["ma2"] - D["ref_hat"]) > 0).astype(int) == D["label"]
    out = {}
    for h, g in D.groupby("true_horizon"):
        if 1 <= h <= 5:
            out[int(h)] = {"n": len(g), "persist": float(g["persist"].mean()), "ma2": float(g["ma2"].mean())}
    return out


def null_bootstrap_check(rng, n_sets: int = 1000) -> dict:
    """V3: rejection rate of boot_diff at alpha 0.10 under a true null (equal expected Brier, correlated quarters)."""
    rej = 0
    for i in range(n_sets):
        nq = 15
        qeff = rng.normal(0, 0.05, nq)
        q = np.repeat(np.arange(nq), 4)
        base = 0.25 + qeff[q]
        a = base + rng.normal(0, 0.08, len(q))
        b = base + rng.normal(0, 0.08, len(q))
        R = pd.DataFrame({"q": q})
        if M.boot_diff(R, a, b, draws=500, seed=i)["p_less"] < 0.10:
            rej += 1
    return {"n_sets": n_sets, "rejection_rate_at_0.10": rej / n_sets}
