"""
E130 shared library: the five provinces, quarter arithmetic, the dashboard clock (app/quarterly/target.py), the
provincial food-deprivation reference score (PFDR v1 = PSA provincial subsistence incidence), the numerical-agreement
tolerance, the frozen numerical reliability rules (N1-N7), walk-forward splits and the planning simulation.

Nothing here fits a model to a provincial target. The E130 gate found no quarterly provincial reference, so the
reliability and split functions are exercised on synthetic data in the tests and kept ready for a valid target.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT.parent
REPO = EXP.parent.parent
OUT = ROOT / "out"
SEALED = ROOT / "sealed"

PROVINCES = ("Batangas", "Cavite", "Laguna", "Quezon", "Rizal")
LEADS = (1, 2, 3, 4)
WINDOW_START = date(2021, 1, 1)
DATA_LIMIT = date(2026, 10, 14)            # owner-authorized data limit (E31)
Z90 = float(stats.norm.ppf(0.95))           # two-sided 90 % sampling half-width multiplier
SEED = 130

SUBSISTENCE = REPO / "backend" / "data" / "inputs" / "psa_subsistence_population_2021_2023.csv"
PANEL = EXP / "E119_Preprocessing" / "E119_PROVINCIAL_VULNERABILITY_DATASET.csv"
ANNUAL = EXP / "E119_Preprocessing" / "E119_PROVINCIAL_ANNUAL_INDICATORS.csv"
INDICATORS = EXP / "E119_Preprocessing" / "E119_12_INDICATOR_DATA_MAPPING.csv"
GEOGRAPHY = EXP / "E119_Preprocessing" / "E119_GEOGRAPHIC_ALIGNMENT_REPORT.csv"
SWS = EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM" / "data" / "sws_area_rounds_2021.csv"
REMITTANCES = EXP / "CORRECTED_PIPELINE" / "out" / "remittances_quarterly_corrected.csv"
E128 = EXP / "E128_Food_Insecurity_ML_Development"
E129 = EXP / "E129_Provincial_Food_Insecurity_Feasibility"

# FNRI ENNS 2021 household moderate-or-severe food insecurity (FIES), 90 % CI; E129 Addendum 1 / P1 (the only
# provincial experienced-food-insecurity values held; the other three provinces were not ENNS 2021 domains).
FNRI_FIES_2021 = {"Batangas": (29.7, 27.3, 32.2), "Cavite": (31.7, 27.0, 36.4)}
# FNRI regional (CALABARZON) moderate-or-severe FIES: 2023 NNS households (n 1,752) and the 2025 updating survey.
FNRI_REGIONAL = {2023: 19.1, 2025: 22.6}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=_jsonable) + "\n", encoding="utf-8")


def _jsonable(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return None if np.isnan(x) else float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (date, pd.Timestamp)):
        return x.isoformat()
    raise TypeError(type(x))


# ------------------------------------------------------------------ quarters and the dashboard clock
def qi(q: str) -> int:
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def qstart(q: str) -> date:
    y, n = q.split("-Q")
    return date(int(y), 3 * int(n) - 2, 1)


def qend(q: str) -> date:
    return qstart(qs(qi(q) + 1)) - timedelta(days=1)


def quarter_of(d: date) -> str:
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def dashboard_clock(view: date) -> dict:
    """The served clock (backend app/quarterly/target.py): the dashboard quarter is the calendar quarter of the view
    date, the forecast is issued at its first day, and the dashboard's forecast target is the next quarter."""
    cal = quarter_of(view)
    return {"dashboard_quarter": cal, "issue_date": qstart(cal), "latest_complete_quarter": qs(qi(cal) - 1),
            "dashboard_target": qs(qi(cal) + 1)}


def operational_target(dashboard_quarter: str, lead: int) -> str:
    """Operational Lead k counts from the latest complete calendar quarter: Lead 1 is the dashboard quarter itself
    (under way, incomplete), Lead 2 the next quarter (the dashboard's forecast target, the minimum operational lead)."""
    return qs(qi(dashboard_quarter) - 1 + lead)


# ------------------------------------------------------------------ the provincial reference score (PFDR v1)
def province_codes() -> dict[str, str]:
    p = pd.read_csv(PANEL, usecols=["province", "province_code"]).drop_duplicates()
    return dict(zip(p["province_code"], p["province"]))


def load_reference() -> pd.DataFrame:
    """PFDR v1: PSA provincial subsistence incidence among the population (% below the provincial food threshold),
    one value per province and FIES survey year, with its published CV. Values are kept on their own scale."""
    raw = pd.read_csv(SUBSISTENCE, dtype={"province_code": str})
    assert (raw["reference_year"] >= WINDOW_START.year).all(), "pre-2021 reference row"
    raw["province"] = raw["province_code"].map(province_codes())
    assert raw["province"].notna().all() and set(raw["province"]) == set(PROVINCES)
    assert not raw.duplicated(["province", "reference_year"]).any(), "duplicated reference observation"
    r = raw.rename(columns={"reference_year": "survey_year", "subsistence_incidence_pct": "pfdr_pct"})
    r["se_pp"] = r["pfdr_pct"] * r["cv_pct"] / 100.0
    r["ci90_lo"] = (r["pfdr_pct"] - Z90 * r["se_pp"]).clip(lower=0.0)
    r["ci90_hi"] = r["pfdr_pct"] + Z90 * r["se_pp"]
    r["tolerance_pp"] = tolerance(r["se_pp"])
    return r[["province", "province_code", "survey_year", "pfdr_pct", "cv_pct", "se_pp", "ci90_lo", "ci90_hi",
              "tolerance_pp", "publication_date"]].sort_values(["province", "survey_year"]).reset_index(drop=True)


def change_tests(ref: pd.DataFrame, y0: int = 2021, y1: int = 2023) -> pd.DataFrame:
    """Two-sided z test of each province's change between survey rounds, from the published CVs."""
    a = ref[ref.survey_year == y0].set_index("province")
    b = ref[ref.survey_year == y1].set_index("province")
    d = pd.DataFrame({"value_y0": a["pfdr_pct"], "value_y1": b["pfdr_pct"], "se_y0": a["se_pp"], "se_y1": b["se_pp"]})
    d["change_pp"] = d["value_y1"] - d["value_y0"]
    d["se_change"] = np.sqrt(d["se_y0"] ** 2 + d["se_y1"] ** 2)
    d["z"] = d["change_pp"] / d["se_change"]
    d["p_two_sided"] = 2 * stats.norm.sf(d["z"].abs())
    d["exceeds_sampling_error_90"] = d["z"].abs() > Z90
    d["exceeds_sampling_error_95"] = d["z"].abs() > stats.norm.ppf(0.975)
    d["minimum_detectable_change_pp"] = (Z90 + stats.norm.ppf(0.80)) * d["se_change"]
    return d.reset_index()


def rank_stability_p(v0, se0, v1, se1, n_draws: int = 20000, seed: int = SEED) -> float:
    """P(Spearman <= observed) if each province's true value were the same in both rounds (precision-weighted common
    value) and only sampling error differed: a small p means the reordering is more than sampling noise."""
    v0, se0, v1, se1 = (np.asarray(a, float) for a in (v0, se0, v1, se1))
    mu = (v0 / se0 ** 2 + v1 / se1 ** 2) / (1 / se0 ** 2 + 1 / se1 ** 2)
    rng = np.random.default_rng(seed)
    a = np.clip(mu + rng.standard_normal((n_draws, len(mu))) * se0, 0, None)
    b = np.clip(mu + rng.standard_normal((n_draws, len(mu))) * se1, 0, None)
    ra, rb = a.argsort(axis=1).argsort(axis=1), b.argsort(axis=1).argsort(axis=1)
    n = len(mu)
    rho = 1 - 6 * ((ra - rb) ** 2).sum(axis=1) / (n * (n ** 2 - 1))
    obs = stats.spearmanr(v0, v1)[0]
    return float((rho <= obs + 1e-12).mean())


def heterogeneity(values: np.ndarray, ses: np.ndarray) -> dict:
    """Cochran's Q across provinces in one survey year, and the between-province true variance (DerSimonian-Laird)."""
    w = 1.0 / ses ** 2
    mw = float((w * values).sum() / w.sum())
    q = float((w * (values - mw) ** 2).sum())
    df = len(values) - 1
    tau2 = max(0.0, (q - df) / (w.sum() - (w ** 2).sum() / w.sum()))
    return {"Q": q, "df": df, "p": float(stats.chi2.sf(q, df)), "weighted_mean": mw, "tau2_dl": tau2,
            "between_sd": float(np.std(values, ddof=1)), "mean_sampling_se": float(np.sqrt(np.mean(ses ** 2)))}


# ------------------------------------------------------------------ numerical agreement
def tolerance(se_ref) -> np.ndarray:
    """Pre-registered tolerance: the reference's own two-sided 90 % sampling half-width (1.645 x SE). A prediction
    inside it cannot be told apart from the reference by the reference's own precision."""
    return Z90 * np.asarray(se_ref, dtype=float)


def within_tolerance(pred, ref, se_ref) -> np.ndarray:
    return np.abs(np.asarray(pred, float) - np.asarray(ref, float)) <= tolerance(se_ref)


def expected_within_share(forecast_sd_over_se) -> np.ndarray:
    """Expected share within tolerance when the forecast error against the true value has SD s_f and the reference's
    sampling error has SD s_e (independent, normal): 2 Phi(1.645 / sqrt(1 + (s_f/s_e)^2)) - 1."""
    r = np.asarray(forecast_sd_over_se, dtype=float)
    return 2 * stats.norm.cdf(Z90 / np.sqrt(1 + r ** 2)) - 1


def required_forecast_sd_over_se(share: float = 0.75) -> float:
    """Largest forecast error SD (against the truth, in units of the reference SE) that still gives `share` within
    tolerance. 0.75 gives 1.022: the forecast must be about as precise as the reference measurement itself."""
    q = stats.norm.ppf(0.5 + share / 2)
    return float(np.sqrt((Z90 / q) ** 2 - 1))


def numeric_metrics(y, f, se=None, prev=None, clim=None) -> dict:
    """MAE, RMSE, bias, R2 (around the evaluation mean), skill against climatology, share within tolerance and
    direction accuracy (only rows whose reference actually moved)."""
    y, f = np.asarray(y, float), np.asarray(f, float)
    e = f - y
    out = {"n": int(len(y)), "mae": float(np.mean(np.abs(e))), "rmse": float(np.sqrt(np.mean(e ** 2))),
           "bias": float(np.mean(e))}
    sst = float(np.sum((y - y.mean()) ** 2))
    out["r2"] = float(1 - np.sum(e ** 2) / sst) if sst > 0 else float("nan")
    if clim is not None:
        sc = float(np.sum((np.asarray(clim, float) - y) ** 2))
        out["r2_vs_climatology"] = float(1 - np.sum(e ** 2) / sc) if sc > 0 else float("nan")
    if se is not None:
        out["within_tolerance"] = float(np.mean(within_tolerance(f, y, se)))
    if prev is not None:
        prev = np.asarray(prev, float)
        moved = y != prev
        out["direction_rows"] = int(moved.sum())
        out["direction_accuracy"] = (float(np.mean(np.sign(f[moved] - prev[moved]) == np.sign(y[moved] - prev[moved])))
                                     if moved.any() else float("nan"))
    return out


def cluster_boot_p(loss_model, loss_base, clusters, n_boot: int = 2000, seed: int = SEED) -> float:
    """One-sided p for 'the model's mean loss is lower than the baseline's', resampling whole clusters (target
    quarters) with replacement: the share of bootstrap means of (base - model) that are <= 0."""
    d = pd.Series(np.asarray(loss_base, float) - np.asarray(loss_model, float))
    g = d.groupby(np.asarray(clusters)).agg(["sum", "count"])
    s, c = g["sum"].to_numpy(), g["count"].to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(g), size=(n_boot, len(g)))
    boot = s[idx].sum(axis=1) / c[idx].sum(axis=1)
    return float((boot <= 0).mean())


def numeric_reliability(rows: pd.DataFrame, model: str, baselines: list[str]) -> dict:
    """Frozen numerical reliability rules N1-N7 for one model at one lead (E130 protocol section 8).

    rows: one row per province x target quarter with y (reference), se (its sampling SE), target_q, province,
    f_<model>, f_<baseline> for each baseline (including 'persistence' and 'climatology'), lo80_<model>, hi80_<model>.
    """
    y, se, tq = rows["y"].to_numpy(float), rows["se"].to_numpy(float), rows["target_q"].to_numpy()
    f = rows[f"f_{model}"].to_numpy(float)
    m = numeric_metrics(y, f, se)
    base = {b: numeric_metrics(y, rows[f"f_{b}"].to_numpy(float), se) for b in baselines}
    nq, nrows = len(set(tq)), len(y)
    within = within_tolerance(f, y, se)
    order = np.argsort(tq, kind="stable")
    thirds = [float(within[ix].mean()) for ix in np.array_split(order, 3)] if nrows >= 3 else []
    loqo = [float(within[tq != q].mean()) for q in sorted(set(tq))] if nq > 1 else []
    p_persist = cluster_boot_p((f - y) ** 2, (rows["f_persistence"].to_numpy(float) - y) ** 2, tq)
    p_clim = cluster_boot_p((f - y) ** 2, (rows["f_climatology"].to_numpy(float) - y) ** 2, tq)
    per_prov = {}
    for p, g in rows.groupby("province"):
        mae_m = float(np.mean(np.abs(g[f"f_{model}"] - g["y"])))
        mae_p = float(np.mean(np.abs(g["f_persistence"] - g["y"])))
        per_prov[p] = {"rows": int(len(g)), "mae": mae_m, "mae_persistence": mae_p,
                       "skill_vs_persistence": float(1 - mae_m / mae_p) if mae_p > 0 else float("nan")}
    cover = float(np.mean((y >= rows[f"lo80_{model}"]) & (y <= rows[f"hi80_{model}"]))) \
        if f"lo80_{model}" in rows else float("nan")
    R = {
        "N1_data": nq >= 10 and nrows >= 40,
        "N2_within_tolerance_75": m["within_tolerance"] >= 0.75,
        "N3_beats_every_baseline_mae_rmse": all(m["mae"] < base[b]["mae"] and m["rmse"] < base[b]["rmse"] for b in baselines),
        "N4_squared_error_vs_persistence_and_climatology": p_persist < 0.10 and p_clim < 0.10,
        "N5_stability": (bool(thirds) and min(thirds) >= 0.60) and (bool(loqo) and min(loqo) >= 0.70),
        "N6_no_province_below_persistence": all(v["skill_vs_persistence"] >= 0 for v in per_prov.values()
                                                if v["skill_vs_persistence"] == v["skill_vs_persistence"]),
        "N7_interval_coverage_80": 0.70 <= cover <= 0.90 if cover == cover else False,
    }
    return {"metrics": m, "baselines": base, "rules": R, "passed": all(R.values()), "n_target_quarters": nq,
            "n_rows": nrows, "within_thirds": thirds, "loqo_min_within": min(loqo) if loqo else float("nan"),
            "p_sq_error_vs_persistence": p_persist, "p_sq_error_vs_climatology": p_clim, "per_province": per_prov,
            "coverage_80": cover}


def maximum_reliable_lead(passed_by_lead: dict[int, bool]) -> int | None:
    """The furthest consecutive lead from Lead 1 that passes; an unreliable intermediate lead ends the run."""
    k = 0
    for lead in sorted(passed_by_lead):
        if lead != k + 1 or not passed_by_lead[lead]:
            break
        k = lead
    return k or None


# ------------------------------------------------------------------ walk-forward splits
def walk_forward_splits(published: dict[str, date | None], lead: int, origins: list[str],
                        min_train_targets: int = 8) -> pd.DataFrame:
    """Expanding-window splits on issue dates (dashboard rule: the first day of the quarter after the origin). For
    origin t the test target is t+lead; training targets are quarters s+lead (s < t) whose reference was published
    strictly before the issue date. All provinces share the same cut. `published` maps a target quarter to the date
    its provincial reference became public (None when no reference exists)."""
    rows = []
    for t in origins:
        issue = qstart(qs(qi(t) + 1))
        target = qs(qi(t) + lead)
        train = [q for q, d in published.items() if d is not None and d < issue and qi(q) - lead < qi(t)]
        has_label = published.get(target) is not None
        rows.append({"origin": t, "issue_date": issue.isoformat(), "lead": lead, "target_quarter": target,
                     "n_train_targets": len(train), "train_last_target": max(train, key=qi) if train else "",
                     "target_has_reference": has_label,
                     "executable": has_label and len(train) >= min_train_targets})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ planning simulation (no real data)
def simulate_panel(n_quarters: int, r: float, rho: float, r2: float, h: int, share: float = 0.74, n_prov: int = 5,
                   n_sims: int = 300, n_boot: int = 400, seed: int = SEED) -> dict:
    """Synthetic provincial panel for planning only. True risk x = common AR(1) (variance `share`) + province AR(1)
    (variance 1 - share), both with quarterly persistence rho; the reference observes y = x + e, e ~ N(0, r^2).
    Persistence forecasts the latest observation, h quarters before the target. The 'informed' model knows rho and
    the noise level, shrinks the latest observation and predicts a fraction r2 of the true h-quarter innovation (an
    upper bound for a model learned from few quarters). Returns pass probabilities under N2-N4."""
    rng = np.random.default_rng(seed)
    burn, T = 40, n_quarters + h + 40
    e_c = rng.standard_normal((n_sims, T, 1)) * np.sqrt(share * (1 - rho ** 2))
    e_u = rng.standard_normal((n_sims, T, n_prov)) * np.sqrt((1 - share) * (1 - rho ** 2))
    x = np.zeros((n_sims, T, n_prov))
    c = np.zeros((n_sims, 1))
    u = np.zeros((n_sims, n_prov))
    c[:] = rng.standard_normal((n_sims, 1)) * np.sqrt(share)
    u[:] = rng.standard_normal((n_sims, n_prov)) * np.sqrt(1 - share)
    for t in range(T):
        c = rho * c + e_c[:, t]
        u = rho * u + e_u[:, t]
        x[:, t] = c + u
    y = x + rng.standard_normal(x.shape) * r
    tgt = np.arange(burn + h, burn + h + n_quarters)
    org = tgt - h
    yt, xt, yo, xo = y[:, tgt], x[:, tgt], y[:, org], x[:, org]
    lam = 1.0 / (1.0 + r ** 2)
    eta = xt - rho ** h * xo
    var_eta = 1 - rho ** (2 * h)
    if r2 > 0:
        nu = rng.standard_normal(eta.shape) * np.sqrt(var_eta * (1 - r2) / r2)
        eta_hat = r2 * (eta + nu)
    else:
        eta_hat = np.zeros_like(eta)
    f_inf = rho ** h * lam * yo + eta_hat
    f_per = yo
    tol = Z90 * r
    w_inf = (np.abs(f_inf - yt) <= tol).mean(axis=(1, 2))
    w_per = (np.abs(f_per - yt) <= tol).mean(axis=(1, 2))
    mae_i, mae_p = np.abs(f_inf - yt).mean(axis=(1, 2)), np.abs(f_per - yt).mean(axis=(1, 2))
    rmse_i, rmse_p = np.sqrt(((f_inf - yt) ** 2).mean(axis=(1, 2))), np.sqrt(((f_per - yt) ** 2).mean(axis=(1, 2)))
    d_q = (((f_per - yt) ** 2) - ((f_inf - yt) ** 2)).mean(axis=2)                       # (sims, quarters)
    idx = rng.integers(0, n_quarters, size=(n_boot, n_quarters))
    boot = d_q[:, idx].mean(axis=2)                                                     # (sims, n_boot)
    p = (boot <= 0).mean(axis=1)
    beats = (mae_i < mae_p) & (rmse_i < rmse_p) & (p < 0.10)
    return {"n_quarters": n_quarters, "rows": n_quarters * n_prov, "noise_ratio_r": r, "rho": rho, "r2": r2,
            "info_horizon_h": h, "common_share": share,
            "p_within75_informed": float((w_inf >= 0.75).mean()), "p_within75_persistence": float((w_per >= 0.75).mean()),
            "mean_within_informed": float(w_inf.mean()), "mean_within_persistence": float(w_per.mean()),
            "p_beats_persistence_sig": float(beats.mean()),
            "p_pass_N2_and_N4": float(((w_inf >= 0.75) & beats).mean()),
            "mean_skill_mae_vs_persistence": float(np.mean(1 - mae_i / mae_p))}
