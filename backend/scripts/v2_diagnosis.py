"""
v2 Step 1 diagnosis (docs/aipheed/v2/DIAGNOSIS.md). No model is proposed or selected here; every number is a
property of the target, the tolerance, the rows or the candidate signals.

  Q1 noise floor and oracle bounds        Q2 why existing models fail (error decomposition, dynamics tests)
  Q3 leading signals of FUTURE CHANGE     Q4 effective sample size and confirmation schedule
  Q5 legitimacy of pooling SWS areas      Q6 target / lead / issue-date alignment re-verification

    python -I backend/scripts/v2_diagnosis.py        (backend venv; about a minute)

Outputs: docs/aipheed/v2/results/diag_*.csv, diagnosis_summary.json, diagnosis_run.txt (console).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import models as M  # noqa: E402
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.evidence import AREAS  # noqa: E402
from app.quarterly.target import forecast_target  # noqa: E402

EXP = REPO / "aipheed-backend-aligned" / "experiments"
OUT = REPO / "docs" / "aipheed" / "v2" / "results"
E136 = EXP / "E136_Methodology_Review" / "out" / "e136_predictions.csv"
E119 = EXP / "E119_Preprocessing" / "E119_REGIONAL_MODELING_DATASET.csv"
SEED, NBOOT = 2026, 5000
Z = T.Z90
SURGE, BREAK = T.qi("2024-Q1"), T.qi("2025-Q2")


def period(q: int) -> str:
    return "pre-surge (<=2023)" if q < SURGE else ("surge (2024)" if q < T.qi("2025-Q1") else "post (2025-26)")


# ------------------------------------------------------------------ Q6 rows (rebuilt with backend code)
def rows(rr: pd.DataFrame) -> pd.DataFrame:
    """P-DASH rows: issue = first day of dashboard quarter D (2021-Q3 .. 2026-Q4), target = D - 1 + k (protocol E1);
    information = rounds published strictly before the issue (as_of); truth = all rounds of the target quarter."""
    full = T.quarter_table(rr)
    out = []
    for D in range(T.qi("2021-Q3"), T.qi("2026-Q4") + 1):
        issue = date(D // 4, 3 * (D % 4) + 1, 1)
        known = T.known_at(rr, issue)
        if known.empty:
            continue
        for a in AREAS:
            s = known[known.area == a].sort_values("qi")
            if s.empty:
                continue
            for k in (1, 2, 3, 4):
                tgt = D - 1 + k
                t = full[(full.area == a) & (full.qi == tgt)]
                if t.empty:
                    continue
                out.append({"area": a, "D": T.qs(D), "issue": issue.isoformat(), "lead": k, "target": T.qs(tgt),
                            "tqi": tgt, "y_true": float(t.y.iloc[0]), "se": float(t.se.iloc[0]), "tol": float(t.tol.iloc[0]),
                            "y_latest": float(s.y.iloc[-1]), "q_latest": int(s.qi.iloc[-1]), "h": tgt - int(s.qi.iloc[-1]),
                            "se_latest": float(s.se.iloc[-1]), "n_obs": len(s), "published_target": str(t.published.iloc[0])})
    return pd.DataFrame(out)


def q6_alignment(rr, R) -> dict:
    P = pd.read_csv(E136)
    P = P[P.policy == "P-DASH"]
    m = R.merge(P[["area", "issue", "lead", "target", "y_true", "y_latest", "h", "n_obs", "tol"]],
                on=["area", "issue", "lead"], how="outer", suffixes=("", "_e136"), indicator=True)
    both = m[m._merge == "both"]
    res = {"rows_backend": int(len(R)), "rows_e136_pdash": int(len(P)), "rows_matched": int(len(both)),
           "rows_only_backend": int((m._merge == "left_only").sum()), "rows_only_e136": int((m._merge == "right_only").sum()),
           "target_mismatch": int((both.target != both.target_e136).sum())}
    for c in ("y_true", "y_latest", "tol"):
        res[f"max_abs_diff_{c}"] = float(np.abs(both[c] - both[f"{c}_e136"]).max())
    for c in ("h", "n_obs"):
        res[f"mismatch_{c}"] = int((both[c] != both[f"{c}_e136"]).sum())
    # the dashboard clock agrees with the lead definition: viewing on any day of D gives target D + 1 = Lead 2
    clock = []
    for d in ("2026-11-01T09:00", "2026-12-31T23:59", "2027-01-01T00:00", "2024-02-15T12:00"):
        ft = forecast_target(d)
        D = T.qi(ft["calendar_quarter"])
        clock.append(T.qi(ft["target_quarter"]) == D - 1 + 2 and ft["origin"] == date(D // 4, 3 * (D % 4) + 1, 1).isoformat())
    res["dashboard_clock_equals_lead2_definition"] = bool(all(clock))
    # every round used at an issue was published strictly before it; every truth round is in the target quarter
    viol = 0
    for issue in sorted(R.issue.unique()):
        k = T.as_of(rr, date.fromisoformat(issue))
        viol += int((pd.to_datetime(k.published) >= pd.Timestamp(issue)).sum())
    res["rounds_used_on_or_after_issue"] = viol
    # a planted off-by-one lead shift is detected by the same comparison (the check is not vacuous)
    shifted = R.copy()
    shifted["target"] = shifted["tqi"].map(lambda q: T.qs(q + 1))
    mm = shifted.merge(P[["area", "issue", "lead", "target"]], on=["area", "issue", "lead"], suffixes=("", "_e136"))
    res["planted_shift_detected_rows"] = int((mm.target != mm.target_e136).sum())
    res["partial_quarters_at_issue"] = int(sum(
        (T.known_at(rr, date.fromisoformat(i)).groupby(["area", "quarter"]).k.first()
         < T.quarter_table(rr).set_index(["area", "quarter"]).k.reindex(
            T.known_at(rr, date.fromisoformat(i)).set_index(["area", "quarter"]).index).values).sum()
        for i in sorted(R.issue.unique())))
    return res


# ------------------------------------------------------------------ local-level filter / smoother (known R_t)
def ll_filter_smooth(y, R, q, idx, bvar=0.0):
    n = len(y)
    af, Pf, ap, Pp = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    a, P, started = None, None, False
    for i, (t, yt, rt) in enumerate(zip(idx, y, R)):
        if not started:
            if yt == yt:
                a, P, started = yt, rt, True
                af[i], Pf[i] = a, P
            continue
        P = P + q + (bvar if t == BREAK else 0.0)
        ap[i], Pp[i] = a, P
        if yt == yt:
            K = P / (P + rt)
            a, P = a + K * (yt - a), (1 - K) * P
        af[i], Pf[i] = a, P
    as_ = af.copy()
    last = np.where(~np.isnan(af))[0]
    for i in range(last[-1] - 1, last[0] - 1, -1):
        if np.isnan(Pp[i + 1]):
            continue
        C = Pf[i] / Pp[i + 1]
        as_[i] = af[i] + C * (as_[i + 1] - ap[i + 1])
    return af, Pf, as_


def fit_ll(qt, with_break: bool):
    upto = int(qt.qi.max())
    data = {a: M.series(qt, a, upto) for a in AREAS}
    best = (-np.inf, None, None)
    for b in (M.B_GRID if with_break else (0.0,)):
        for s2 in M.S2_GRID:
            ll = sum(M._kf_break(data[a][1], data[a][2], s2, b, data[a][0])[2] for a in AREAS)
            if ll > best[0]:
                best = (ll, s2, b)
    return {"loglik": float(best[0]), "q": float(best[1]), "b": float(best[2]), "data": data}


def fit_ar_latent(qt):
    """Mean-reverting latent: x_t = m_a + phi (x_{t-1} - m_a) + eta, eta ~ N(0, q); m_a = area sample mean.
    Pooled profile ML over (phi, q). phi = 1 is the local level. In-sample diagnostic only."""
    upto = int(qt.qi.max())
    data = {a: M.series(qt, a, upto) for a in AREAS}
    best = (-np.inf, None, None)
    for phi in np.round(np.linspace(0.3, 1.0, 36), 3):
        for q in M.S2_GRID:
            ll = 0.0
            for a in AREAS:
                idx, y, R = data[a]
                m = np.nanmean(y)
                mu, P, started = None, None, False
                for yt, rt in zip(y, R):
                    if not started:
                        if yt == yt:
                            mu, P, started = yt - m, rt, True
                        continue
                    mu, P = phi * mu, phi * phi * P + q
                    if yt == yt:
                        S = P + rt
                        ll += -0.5 * (np.log(2 * np.pi * S) + (yt - m - mu) ** 2 / S)
                        K = P / S
                        mu, P = mu + K * (yt - m - mu), (1 - K) * P
            if ll > best[0]:
                best = (ll, phi, q)
    return {"loglik": float(best[0]), "phi": float(best[1]), "q": float(best[2])}


# ------------------------------------------------------------------ Q1 noise floor and oracle bounds
def q1_noise(rr, full, R) -> tuple[dict, pd.DataFrame]:
    res = {}
    res["round_se_pp"] = {k: float(v) for k, v in rr.se.describe()[["min", "50%", "max"]].items()}
    res["quarter_tol_pp"] = {k: float(v) for k, v in full.tol.describe()[["min", "50%", "max"]].items()}
    # within-quarter replication: quarters with 2 non-commissioned rounds (2021-Q2, 2022-Q2, 2025-Q2)
    pairs = []
    for (a, q), g in rr.groupby(["area", "quarter"]):
        if len(g) == 2:
            d = float(g.value.iloc[1] - g.value.iloc[0])
            pairs.append({"area": a, "quarter": q, "diff": d, "se_diff": float(np.sqrt((g.se ** 2).sum())),
                          "z": d / float(np.sqrt((g.se ** 2).sum()))})
    pr = pd.DataFrame(pairs)
    res["within_quarter_round_pairs"] = {"n": len(pr), "rms_z": float(np.sqrt((pr.z ** 2).mean())),
                                         "share_abs_z_gt_1.96": float((pr.z.abs() > 1.96).mean()),
                                         "chi2_p_binomial_se_adequate": float(stats.chi2.sf((pr.z ** 2).sum(), len(pr))),
                                         "note": "rounds ~1-3 months apart; part of the difference is true change"}
    res["revisions"] = "none recorded: each round has one published value in sws_area_rounds.csv (revisions NOT VERIFIED)"
    # change distribution over h quarters (all area pairs, full data) and the no-change (persistence) bound
    ch = []
    y = full.set_index(["area", "qi"])
    for a in AREAS:
        s = full[full.area == a].set_index("qi")
        for t0 in s.index:
            for h in (1, 2, 3, 4, 5):
                if t0 + h in s.index:
                    ch.append({"area": a, "h": h, "chg": s.y[t0 + h] - s.y[t0], "tol": s.tol[t0 + h]})
    ch = pd.DataFrame(ch)
    tab = ch.groupby("h").apply(lambda g: pd.Series({
        "n_pairs": len(g), "sd_change": g.chg.std(), "mean_change": g.chg.mean(),
        "p25_abs": g.chg.abs().quantile(0.25), "median_abs": g.chg.abs().median(), "p75_abs": g.chg.abs().quantile(0.75),
        "median_tol": g.tol.median(), "share_change_within_tol": (g.chg.abs() <= g.tol).mean()}), include_groups=False)
    res["change_by_h"] = tab.reset_index().round(4).to_dict("records")
    # oracle bounds on the S-U rows (n_obs >= 8)
    fl = fit_ll(full, with_break=True)
    sm = {}
    for a in AREAS:
        idx, yy, RR = fl["data"][a]
        af, Pf, as_ = ll_filter_smooth(yy, RR, fl["q"], idx, fl["b"])
        sm[a] = pd.Series(as_, index=idx)
    S = R[R.n_obs >= 8].copy()
    S["O_PERSIST"] = S.y_latest
    S["O_NOW"] = [sm[a][q] for a, q in zip(S.area, S.q_latest)]            # true level at the latest data quarter (hindsight)
    S["O_TARGET_LEVEL"] = [sm[a][q] for a, q in zip(S.area, S.tqi)]         # true level of the target itself (ceiling)
    nb = []
    for a, q in zip(S.area, S.tqi):
        v = [y.y.get((a, q - 1), np.nan), y.y.get((a, q + 1), np.nan)]
        nb.append(np.nanmean(v) if not all(np.isnan(v)) else np.nan)
    S["O_LOCAL_MEAN"] = nb                                                   # mean of the neighbouring quarters (hindsight)
    S["O_AREA_MEAN"] = S.area.map(full.groupby("area").y.mean())             # full-sample mean (hindsight)
    oracle = []
    for k, g in S.groupby("lead"):
        rec = {"lead": int(k), "n": len(g), "n_quarters": g.target.nunique(), "median_h": float(g.h.median()),
               "median_se": float(g.se.median()), "median_tol": float(g.tol.median())}
        for c in ("O_PERSIST", "O_NOW", "O_LOCAL_MEAN", "O_AREA_MEAN", "O_TARGET_LEVEL"):
            gg = g.dropna(subset=[c])
            rec[f"{c}_within"] = float((np.abs(gg[c] - gg.y_true) <= gg.tol).mean())
        # analytic: the forecaster knows today's true level exactly; the true level then moves as a random walk with
        # variance q per quarter (ML, all data); the target is observed with its own sampling SE
        rec["analytic_known_level_within"] = float(np.mean(
            2 * stats.norm.cdf(Z * g.se / np.sqrt(g.h * fl["q"] + g.se ** 2)) - 1))
        rec["analytic_perfect_true_target_within"] = float(2 * stats.norm.cdf(Z) - 1)
        # the forecast-error SD of the TRUE target level that gives 75 % within, and the share of the true-change
        # variance over the horizon a predictor must explain to get there
        z75 = stats.norm.ppf(0.875)
        need = g.se * np.sqrt((Z / z75) ** 2 - 1)
        rec["required_true_level_error_sd_median"] = float(need.median())
        rec["true_change_sd_over_horizon_median"] = float(np.sqrt(g.h * fl["q"]).median())
        rec["share_of_true_change_variance_to_explain"] = float(np.clip(1 - (need ** 2) / (g.h * fl["q"]), 0, 1).median())
        oracle.append(rec)
    res["local_level_fit_all_data"] = {"q": fl["q"], "break_var": fl["b"], "loglik": fl["loglik"]}
    res["oracle"] = oracle
    res["required_error_sd_over_se"] = float(np.sqrt((Z / stats.norm.ppf(0.875)) ** 2 - 1))
    return res, S


# ------------------------------------------------------------------ Q2 failure decomposition and dynamics
def acf_pairs(full, lag, diff=False):
    xs, ys = [], []
    for a in AREAS:
        s = full[full.area == a].set_index("qi").y
        if diff:
            s = pd.Series({t: s[t] - s[t - 1] for t in s.index if t - 1 in s.index})
        s = s - s.mean()
        for t in s.index:
            if t + lag in s.index:
                xs.append(s[t]); ys.append(s[t + lag])
    if len(xs) < 5:
        return np.nan, len(xs)
    return float(np.corrcoef(xs, ys)[0, 1]), len(xs)


def q2_failure(rr, full, S) -> dict:
    P = pd.read_csv(E136)
    P = P[(P.policy == "P-DASH") & (P.n_obs >= 8)]
    res = {}
    dec = []
    for model in ("PERSIST", "SEAS-LLM", "HFM-X"):
        for k in (1, 2):
            g = P[P.lead == k].copy()
            e = g[f"f_{model}"] - g.y_true
            g["e"] = e
            noise = float((g.se ** 2).mean() + (S[S.lead == k].se_latest ** 2).mean()) if model == "PERSIST" else np.nan
            rec = {"model": model, "lead": k, "n": len(g), "mse": float((e ** 2).mean()), "bias": float(e.mean()),
                   "bias_sq_share": float(e.mean() ** 2 / (e ** 2).mean()),
                   "measurement_noise_share_of_mse": noise / float((e ** 2).mean()) if noise == noise else np.nan,
                   "top10pct_rows_share_of_sse": float((e ** 2).sort_values(ascending=False).head(max(1, len(e) // 10)).sum() / (e ** 2).sum())}
            g["per"] = g.target.map(T.qi).map(period)
            for p_, gg in g.groupby("per"):
                rec[f"sse_share_{p_}"] = float((gg.e ** 2).sum() / (g.e ** 2).sum())
                rec[f"bias_{p_}"] = float(gg.e.mean())
                rec[f"n_{p_}"] = len(gg)
            dec.append(rec)
    res["error_decomposition"] = dec
    # regression to the mean: future change vs distance of the latest value from the expanding area mean at issue
    L2 = S[S.lead == 2].copy()
    em = []
    for x in L2.itertuples():
        k = T.known_at(rr, date.fromisoformat(x.issue))
        em.append(float(k[k.area == x.area].y.mean()))
    L2["dev"] = L2.y_latest - np.array(em)
    L2["chg"] = L2.y_true - L2.y_latest
    sl = stats.linregress(L2.dev, L2.chg)
    res["lead2_change_on_deviation_from_expanding_mean"] = {"slope": float(sl.slope), "p": float(sl.pvalue), "n": len(L2),
                                                           "interpretation": "slope < 0 means regression to the mean"}
    # high-tercile bias split: the ex-post true level of the target (O_TARGET_LEVEL) shows the selection part
    cut = L2.y_true.quantile(2 / 3)
    top = L2[L2.y_true >= cut]
    res["lead2_high_tercile"] = {"n": len(top), "persist_bias": float((top.y_latest - top.y_true).mean()),
                                 "selection_part_any_true_level_forecaster": float((top.O_TARGET_LEVEL - top.y_true).mean()),
                                 "lag_part": float((top.y_latest - top.O_TARGET_LEVEL).mean()),
                                 "mean_true_change_over_horizon": float((top.O_TARGET_LEVEL - top.O_NOW).mean())}
    res["lead2_overall_bias_persist"] = float((L2.y_latest - L2.y_true).mean())
    res["lead2_mean_true_change_over_horizon"] = float((L2.O_TARGET_LEVEL - L2.O_NOW).mean())
    # dynamics: ACF of levels and changes, unit-root, mean reversion, seasonality, breaks
    res["acf_levels"] = {f"lag{l}": acf_pairs(full, l)[0] for l in (1, 2, 3, 4)}
    res["acf_changes"] = {f"lag{l}": acf_pairs(full, l, diff=True)[0] for l in (1, 2, 3, 4)}
    adf = []
    pool_x, pool_y, pool_a = [], [], []
    for a in AREAS:
        s = full[full.area == a].set_index("qi").y
        xs = [s[t - 1] for t in s.index if t - 1 in s.index]
        ys = [s[t] - s[t - 1] for t in s.index if t - 1 in s.index]
        r = stats.linregress(xs, ys)
        adf.append({"area": a, "n": len(xs), "b": float(r.slope), "t": float(r.slope / r.stderr)})
        pool_x += list(np.array(xs) - np.mean(xs)); pool_y += list(np.array(ys) - np.mean(ys)); pool_a += [a] * len(xs)
    pr = stats.linregress(pool_x, pool_y)
    res["unit_root_df_regression"] = {"per_area": adf, "pooled_within_b": float(pr.slope), "pooled_within_t": float(pr.slope / pr.stderr),
                                      "df_5pct_critical_value_constant_n25": -3.00,
                                      "note": "Dickey-Fuller t (constant); |t| below 3.00 cannot reject a unit root; power is low at n~20"}
    ll = fit_ll(full, with_break=True)
    ar = fit_ar_latent(full)
    ll0 = fit_ll(full, with_break=False)
    res["latent_dynamics"] = {"local_level": {"q": ll0["q"], "loglik": ll0["loglik"]},
                              "mean_reverting_latent": ar,
                              "lr_stat_phi_lt_1": float(2 * (ar["loglik"] - ll0["loglik"])),
                              "local_level_with_break": {"q": ll["q"], "b": ll["b"], "loglik": ll["loglik"]}}
    # seasonality: area-demeaned quarter changes by quarter-of-year (consecutive quarters only)
    rows_ = []
    for a in AREAS:
        s = full[full.area == a].set_index("qi").y
        for t in s.index:
            if t - 1 in s.index:
                rows_.append({"area": a, "qoy": t % 4 + 1, "chg": s[t] - s[t - 1], "post": t >= BREAK})
    sd = pd.DataFrame(rows_)
    seas = {}
    for lab, g in (("all", sd), ("pre-break", sd[~sd.post]), ("post-break", sd[sd.post])):
        grp = [x.chg.values for _, x in g.groupby("qoy") if len(x) > 1]
        seas[lab] = {"mean_change_by_qoy": g.groupby("qoy").chg.mean().round(3).to_dict(),
                     "n_by_qoy": g.groupby("qoy").size().to_dict(),
                     "kruskal_p": float(stats.kruskal(*grp).pvalue) if len(grp) > 1 else None}
    res["seasonality_quarter_changes"] = seas
    # breaks: area-demeaned levels before vs after
    full2 = full.copy()
    full2["dm"] = full2.y - full2.groupby("area").y.transform("mean")
    br = {}
    for name, cut in (("2024-Q1 surge onset", SURGE), ("2025-Q2 respondent base", BREAK)):
        a_, b_ = full2[full2.qi < cut].y, full2[full2.qi >= cut].y
        br[name] = {"mean_before": float(a_.mean()), "mean_after": float(b_.mean()), "sd_before": float(a_.std()),
                    "sd_after": float(b_.std()), "welch_p": float(stats.ttest_ind(a_, b_, equal_var=False).pvalue)}
    br["mean_by_period"] = full2.assign(per=full2.qi.map(period)).groupby("per").y.agg(["mean", "std", "size"]).round(3).to_dict("index")
    res["structural_breaks"] = br
    return res


# ------------------------------------------------------------------ Q3 leading signals of future change
def load_e131():
    p = EXP / "E131_Objectives_Resolution" / "runner" / "e131_x1.py"
    sys.path.insert(0, str(EXP / "E130_Provincial_Risk_Score_Forecasting" / "runner"))
    spec = importlib.util.spec_from_file_location("e131_x1_diag", p)
    m = importlib.util.module_from_spec(spec)
    sys.modules["e131_x1_diag"] = m
    spec.loader.exec_module(m)
    return m


PRIMARY = {"A": "rice_yoy", "C": "typhoons_PAR", "E": "E1_unemployment_change_pp", "N": "news_gdelt_shortage_share",
           "V": "poverty"}
SECONDARY = {"A": ["food_yoy", "relfood_chg4"], "C": ["oni_quarter_mean", "rainfall_anomaly_mm"],
             "E": ["E2_remittance_decline_pct", "unemployment_rate_pct"], "N": ["news_gdelt_jobs_income_share"], "V": []}


def signal_table(rr, R) -> pd.DataFrame:
    X = load_e131()
    cpi = X.cpi_quarterly()
    pov = X.poverty_area()
    reg = pd.read_csv(E119)
    reg = reg[reg.lead == 1].copy()
    out = []
    for x in R[R.lead.isin([1, 2]) & (R.n_obs >= 2)].itertuples():
        issue = date.fromisoformat(x.issue)
        rec = {"area": x.area, "issue": x.issue, "lead": x.lead, "chg": x.y_true - x.y_latest, "h": x.h}
        c = cpi[(cpi.area == x.area) & (pd.to_datetime(cpi.available).dt.date < issue)].sort_values("qi").tail(1)
        for f in ("rice_yoy", "food_yoy", "relfood_chg4"):
            rec[f] = float(c[f].iloc[0]) if len(c) else np.nan
        g = reg[reg.issue_date == x.issue]
        for f in ("typhoons_PAR", "oni_quarter_mean", "rainfall_anomaly_mm", "E1_unemployment_change_pp",
                  "E2_remittance_decline_pct", "unemployment_rate_pct", "news_gdelt_shortage_share", "news_gdelt_jobs_income_share"):
            rec[f] = float(g[f].iloc[0]) if len(g) and g[f].iloc[0] == g[f].iloc[0] else np.nan
        yrs = [y for y, d in X.POV_PUBLISHED.items() if d < issue]
        rec["poverty"] = pov[x.area][max(yrs)] if yrs else np.nan
        out.append(rec)
    return pd.DataFrame(out)


def _spearman(a, b):
    ra, rb = stats.rankdata(a), stats.rankdata(b)
    if ra.std() == 0 or rb.std() == 0:
        return np.nan
    return float(np.corrcoef(ra, rb)[0, 1])


def q3_signals(sig: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    res = []
    for k in (1, 2):
        g = sig[sig.lead == k]
        issues = np.array(sorted(g.issue.unique()))
        for grp in PRIMARY:
            for f in [PRIMARY[grp], *SECONDARY[grp]]:
                d = g[["issue", "area", "chg", f]].dropna()
                if d.issue.nunique() < 6 or d[f].nunique() < 3:
                    res.append({"lead": k, "group": grp, "feature": f, "primary": f == PRIMARY[grp], "n_rows": len(d),
                                "n_issues": int(d.issue.nunique()), "spearman": np.nan, "note": "too few issues or values"})
                    continue
                rho = _spearman(d[f], d.chg)
                by = {i: x for i, x in d.groupby("issue")}
                iss = np.array(sorted(by))
                boot = []
                for _ in range(NBOOT):
                    pick = rng.choice(iss, len(iss))
                    bb = pd.concat([by[i] for i in pick])
                    boot.append(_spearman(bb[f], bb.chg))
                boot = np.array(boot)
                # block permutation: whole issue blocks of the feature are permuted across issues (the 4 areas of an
                # issue share national features), the change stays attached to its row
                perm = []
                fv = {i: by[i].set_index("area")[f] for i in iss}
                for _ in range(NBOOT):
                    mp = dict(zip(iss, rng.permutation(iss)))
                    pf = np.array([fv[mp[i]].get(a, np.nan) for i, a in zip(d.issue, d.area)])
                    ok = ~np.isnan(pf)
                    perm.append(_spearman(pf[ok], d.chg.to_numpy()[ok]))
                perm = np.array(perm)
                res.append({"lead": k, "group": grp, "feature": f, "primary": f == PRIMARY[grp], "n_rows": len(d),
                            "n_issues": int(d.issue.nunique()), "spearman": rho,
                            "boot_ci_lo": float(np.nanquantile(boot, 0.025)), "boot_ci_hi": float(np.nanquantile(boot, 0.975)),
                            "p_block_perm": float((np.abs(perm[~np.isnan(perm)]) >= abs(rho)).mean())})
    out = pd.DataFrame(res)
    for fam, mask in (("holm_primary", out.primary & out.spearman.notna()), ("holm_all", out.spearman.notna())):
        o = out[mask].sort_values("p_block_perm")
        m = len(o)
        adj = np.minimum(np.maximum.accumulate([(m - i) * p for i, p in enumerate(o.p_block_perm)]), 1.0)
        out[fam] = np.nan
        out.loc[o.index, fam] = adj
    return out


# ------------------------------------------------------------------ Q4 effective sample size
def q4_sample(S, rr) -> dict:
    res = {}
    P = pd.read_csv(E136)
    P = P[(P.policy == "P-DASH") & (P.n_obs >= 8)]
    for k, g in S.groupby("lead"):
        res[f"lead{k}"] = {"rows": len(g), "target_quarters": int(g.target.nunique()), "areas": int(g.area.nunique())}
    g = P[P.lead == 2].copy()
    w = (np.abs(g["f_PERSIST"] - g.y_true) <= g.tol).astype(float)
    g["w"] = w
    # one-way ANOVA ICC of the within indicator, clusters = target quarters (m = 4 areas)
    m_ = g.groupby("target").size().mean()
    msb = g.groupby("target").w.mean().var(ddof=1) * m_
    msw = g.groupby("target").w.var(ddof=1).mean()
    icc = float(max(0.0, (msb - msw) / (msb + (m_ - 1) * msw))) if (msb + (m_ - 1) * msw) > 0 else 0.0
    deff = 1 + (m_ - 1) * icc
    # quarter-to-quarter correlation of the 4-area mean within share (persistence of success across quarters)
    res["lead2_within_icc_areas_in_quarter"] = icc
    res["lead2_design_effect"] = float(deff)
    p = 0.75
    need = {}
    for hw in (0.10, 0.05):
        n_eff = (1.96 ** 2) * p * (1 - p) / hw ** 2
        need[f"quarters_for_ci_halfwidth_{hw}"] = int(np.ceil(n_eff * deff / 4))
    for ptrue in (0.80, 0.85, 0.90):
        n_eff = ((1.96 * np.sqrt(p * (1 - p)) + 0.8416 * np.sqrt(ptrue * (1 - ptrue))) / (ptrue - p)) ** 2
        need[f"quarters_to_show_gt75_with_80pct_power_if_true_{ptrue}"] = int(np.ceil(n_eff * deff / 4))
    res["requirements"] = need
    hw_now = 1.96 * np.sqrt(p * (1 - p) * deff / len(g))
    res["current_ci_halfwidth_at_75pct_lead2"] = float(hw_now)
    # publication lag and the confirmation schedule for unseen Lead-2 targets
    lag = (pd.to_datetime(rr.drop_duplicates("quarter", keep="last").published)
           - pd.PeriodIndex(rr.drop_duplicates("quarter", keep="last").quarter.str.replace("-", ""), freq="Q").end_time.normalize())
    res["publication_lag_days_median"] = float(lag.dt.days.median())
    res["quarters_without_a_round_2021_2026"] = [T.qs(q) for q in range(T.qi("2021-Q2"), T.qi("2026-Q3") + 1)
                                                 if T.qs(q) not in set(rr.quarter)]
    first = T.qi("2026-Q4")
    sched = []
    for n in (1, 6, 10, 20):
        tq = first + n - 1
        end = pd.Period(T.qs(tq).replace("-", ""), freq="Q").end_time.normalize() + pd.Timedelta(days=int(np.ceil(lag.dt.days.median())))
        sched.append({"unseen_lead2_target_quarters": n, "last_target": T.qs(tq), "expected_published_by": str(end.date())})
    res["schedule_if_every_quarter_has_a_round"] = sched
    return res


# ------------------------------------------------------------------ Q5 pooling
def q5_pooling(full) -> dict:
    res = {}
    W = full.pivot(index="qi", columns="area", values="y")
    dW = W.diff()
    dW = dW[dW.index.isin([q for q in W.index if q - 1 in W.index])]
    res["corr_quarter_changes"] = dW.corr().round(3).to_dict()
    res["mean_offdiag_corr_changes"] = float(dW.corr().values[np.triu_indices(4, 1)].mean())
    # heterogeneity of mean-reversion slopes: per-area slope vs pooled slope (F test on interaction)
    rows_ = []
    for a in AREAS:
        s = full[full.area == a].set_index("qi").y
        m = s.mean()
        for t in s.index:
            if t - 1 in s.index:
                rows_.append({"area": a, "x": s[t - 1] - m, "d": s[t] - s[t - 1]})
    d = pd.DataFrame(rows_)
    rss_sep = 0.0
    slopes = {}
    for a, g in d.groupby("area"):
        r = stats.linregress(g.x, g.d)
        slopes[a] = float(r.slope)
        rss_sep += float(((g.d - (r.intercept + r.slope * g.x)) ** 2).sum())
    Xp = np.column_stack([pd.get_dummies(d.area).to_numpy(float), d.x])
    beta, *_ = np.linalg.lstsq(Xp, d.d.to_numpy(), rcond=None)
    rss_pool = float(((d.d - Xp @ beta) ** 2).sum())
    df1, df2 = 3, len(d) - 8
    F = ((rss_pool - rss_sep) / df1) / (rss_sep / df2)
    res["mean_reversion_slopes"] = {"per_area": slopes, "pooled": float(beta[-1]), "F": float(F),
                                    "p_heterogeneity": float(stats.f.sf(F, df1, df2)), "n": len(d)}
    # local-level innovation variance per area vs pooled (likelihood ratio)
    pooled = fit_ll(full, with_break=False)
    sep_ll = 0.0
    qa = {}
    for a in AREAS:
        idx, y, R = pooled["data"][a]
        best = max(((M._kf_break(y, R, s2, 0.0, idx)[2], s2) for s2 in M.S2_GRID))
        sep_ll += best[0]
        qa[a] = float(best[1])
    lr = 2 * (sep_ll - pooled["loglik"])
    res["local_level_q"] = {"per_area": qa, "pooled": pooled["q"], "lr": float(lr), "p_chi2_3": float(stats.chi2.sf(lr, 3))}
    return res


# ------------------------------------------------------------------ robustness of the two in-sample signals
def robustness(rr, sig: pd.DataFrame, S: pd.DataFrame) -> dict:
    """(a) Is the ONI association more than the one 2023-24 El Nino episode followed by the 2024 surge?
    (b) Is the in-sample 'regression to the mean' forecastable out of sample (parameters from data known at issue)?"""
    res = {}
    reg = pd.read_csv(E119)
    reg = reg[reg.lead == 1][["issue_date", "oni_quarter_mean", "oni_quarter_mean__period"]].dropna()
    hot = reg[reg.oni_quarter_mean >= 0.5].oni_quarter_mean__period.tolist()
    res["oni_quarters_ge_0.5_seen_at_issues"] = sorted(set(hot))
    oni = {}
    for k in (1, 2):
        g = sig[(sig.lead == k)].dropna(subset=["oni_quarter_mean"]).copy()
        tq = g.apply(lambda x: T.qi(x.issue[:4] + "-Q" + str((int(x.issue[5:7]) - 1) // 3 + 1)) - 1 + k, axis=1)
        for lab, m in (("all", np.ones(len(g), bool)), ("targets_outside_2024", ~tq.between(SURGE, SURGE + 3)),
                       ("issues_before_2023-07", g.issue < "2023-07-01"), ("issues_from_2025", g.issue >= "2025-01-01")):
            d = g[m.values if hasattr(m, "values") else m]
            oni[f"lead{k}_{lab}"] = {"n_rows": len(d), "n_issues": int(d.issue.nunique()),
                                     "spearman": _spearman(d.oni_quarter_mean, d.chg) if d.issue.nunique() >= 4 else None}
    res["oni_association_by_subset"] = oni
    # (b) out-of-sample mean reversion on S-U Lead-2 rows
    rows_ = []
    for x in S[S.lead == 2].itertuples():
        known = T.known_at(rr, date.fromisoformat(x.issue))
        pairs = []
        for a in AREAS:
            s = known[known.area == a].set_index("qi").y
            for t0 in s.index:
                if t0 + x.h in s.index:
                    pairs.append((s[t0] - s[s.index <= t0].mean(), s[t0 + x.h] - s[t0]))
        s = known[known.area == x.area].y
        dev = x.y_latest - s.mean()
        b = stats.linregress(*zip(*pairs)) if len(pairs) >= 6 else None
        rows_.append({"expmean": float(s.mean()), "mr": x.y_latest + (b.intercept + b.slope * dev if b else 0.0),
                      "y": x.y_true, "tol": x.tol, "persist": x.y_latest, "slope": b.slope if b else np.nan})
    d = pd.DataFrame(rows_)
    res["lead2_out_of_sample"] = {
        c: {"within": float((np.abs(d[c] - d.y) <= d.tol).mean()), "mae": float(np.abs(d[c] - d.y).mean())}
        for c in ("persist", "expmean", "mr")}
    res["lead2_out_of_sample"]["mr_slope_range_at_issues"] = [float(d.slope.min()), float(d.slope.max())]
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rr = T.load_rounds()
    full = T.quarter_table(rr)
    R = rows(rr)
    summary = {"data_file_sha256": hashlib.sha256(T.SWS_ROUNDS.read_bytes()).hexdigest(), "seed": SEED, "nboot": NBOOT}
    summary["Q6_alignment"] = q6_alignment(rr, R)
    q1, S = q1_noise(rr, full, R)
    summary["Q1_noise_and_oracle"] = q1
    S.to_csv(OUT / "diag_su_rows_with_oracles.csv", index=False)
    summary["Q2_failure"] = q2_failure(rr, full, S)
    sig = signal_table(rr, R)
    sig.to_csv(OUT / "diag_signal_table.csv", index=False)
    q3 = q3_signals(sig)
    q3.to_csv(OUT / "diag_q3_leading_signals.csv", index=False)
    summary["Q3_signals_any_holm_lt_0.10"] = q3[q3.holm_all < 0.10][["lead", "feature", "spearman", "holm_all"]].to_dict("records")
    summary["Q3_primary_min_holm"] = float(q3.holm_primary.min())
    summary["Q2Q3_robustness"] = robustness(rr, sig, S)
    summary["Q4_sample"] = q4_sample(S, rr)
    summary["Q5_pooling"] = q5_pooling(full)
    (OUT / "diagnosis_summary.json").write_text(json.dumps(summary, indent=1, default=float) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, default=float))
    print(q3.round(4).to_string())


if __name__ == "__main__":
    main()
