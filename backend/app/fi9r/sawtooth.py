"""SWS Balance Luzon sawtooth investigation from the round-level release metadata.

    python -m app.fi9r.sawtooth          # writes data/fi9r/out/sawtooth.json

Uses only what the SWS releases state (fieldwork dates, Balance Luzon sample size, margin of error, respondent base,
mode). Where the release gave no sample size the round is left unclassified; nothing is imputed.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats

from app.fi5.sources import sws_rounds
from app.fi6.target import quarterly
from app.fi7.experiments import alternating_quarters
from app.fi9r import OUT


def _lag1(x: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    return float(np.corrcoef(x[:-1], x[1:])[0, 1]) if len(x) > 3 else np.nan


def change_structure(q: pd.DataFrame) -> dict:
    """Autocorrelation and variance of quarter-to-quarter changes vs what sampling error alone would give."""
    out = {}
    for era, m in {"all": q["qi"] > 0, "pre-2021": q["quarter"] < "2021", "2021+": q["quarter"] >= "2021",
                   "2023-Q2+": q["quarter"] >= "2023-Q2"}.items():
        g = q[m].reset_index(drop=True)
        consec = g["qi"].diff() == 1
        d = g["hunger"].diff().where(consec)
        se2 = g["se"] ** 2
        noise_var = (se2 + se2.shift()).where(consec)          # var of a change if hunger were constant
        # expected lag-1 autocorrelation of changes if the true level is a random walk + white sampling noise
        var_d, mean_noise = float(np.nanvar(d, ddof=1)), float(np.nanmean(noise_var))
        sig_eta = max(var_d - mean_noise, 0.0)
        exp_rho = -np.nanmean(se2) / (sig_eta + 2 * np.nanmean(se2)) if (sig_eta + 2 * np.nanmean(se2)) > 0 else np.nan
        out[era] = {"n_changes": int(d.notna().sum()), "lag1_autocorr_changes": _lag1(d.to_numpy(float)),
                    "expected_lag1_if_sampling_noise_only": float(exp_rho),
                    "var_changes": var_d, "mean_sampling_var_of_change": mean_noise,
                    "share_of_change_variance_from_sampling": float(min(1.0, mean_noise / var_d)) if var_d else None}
    return out


def design_effect() -> dict:
    """Rounds whose release states the Balance Luzon sample size (2021-Q3 and 2023-Q2 onward)."""
    r = sws_rounds().copy()
    r = r[r["bl_n"].notna()].copy()
    r["t"] = pd.to_datetime(r["fieldwork"].str[:10], errors="coerce")
    r["se"] = r["area_moe_bl"] / 1.96
    r["small"] = (r["bl_n"] <= 300).astype(int)
    r = r.sort_values("t").reset_index(drop=True)
    rows = r[["quarter", "fieldwork", "published", "bl_n", "area_moe_bl", "balance_luzon", "respondent_base", "mode"]]
    res = {"rounds": json.loads(rows.to_json(orient="records"))}

    def wls(d: pd.DataFrame, cols: list[str]) -> dict:
        X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in cols])
        w = 1 / d["se"].to_numpy(float) ** 2
        W = np.diag(w)
        XtWX = X.T @ W @ X
        beta = np.linalg.solve(XtWX, X.T @ W @ d["balance_luzon"].to_numpy(float))
        resid = d["balance_luzon"].to_numpy(float) - X @ beta
        dof = len(d) - X.shape[1]
        s2 = float(resid @ W @ resid / dof) if dof > 0 else np.nan        # >1 means more scatter than sampling error
        cov = np.linalg.inv(XtWX) * max(s2, 1.0)
        b, se = float(beta[cols.index("small") + 1]), float(np.sqrt(cov[cols.index("small") + 1, cols.index("small") + 1]))
        return {"n_rounds": int(len(d)), "effect_small_minus_large_pp": b, "se": se,
                "p_two_sided": float(2 * stats.t.sf(abs(b / se), dof)) if dof > 0 else None,
                "residual_scatter_vs_sampling": s2}

    r["time"] = (r["t"] - r["t"].min()).dt.days / 365.25
    res["wls_2023Q2_on_trend"] = wls(r[r["quarter"] >= "2023-Q2"], ["small", "time"])
    res["wls_adult_base_2025Q2_on_trend"] = wls(r[r["respondent_base"] == "adults"], ["small", "time"])
    # adjacent-round contrast: each n=300 round vs the mean of its neighbouring larger rounds
    c = []
    for i in range(1, len(r) - 1):
        if r.loc[i, "small"] == 1 and r.loc[i - 1, "small"] == 0 and r.loc[i + 1, "small"] == 0:
            c.append({"round": r.loc[i, "fieldwork"], "value": float(r.loc[i, "balance_luzon"]),
                      "neighbours_mean": float((r.loc[i - 1, "balance_luzon"] + r.loc[i + 1, "balance_luzon"]) / 2)})
    res["sandwiched_small_rounds"] = c
    if c:
        diffs = np.array([x["value"] - x["neighbours_mean"] for x in c])
        res["sandwiched_mean_diff_pp"] = float(diffs.mean())
    res["respondent_base_change"] = {"household_heads_last": str(r.loc[r["respondent_base"] == "household heads", "fieldwork"].iloc[-1]),
                                     "adults_first": str(r.loc[r["respondent_base"] == "adults", "fieldwork"].iloc[0])}
    return res


def metadata_inventory() -> dict:
    r = sws_rounds()
    return {"rounds": int(len(r)), "rounds_with_sample_size": int(r["bl_n"].notna().sum()),
            "rounds_with_assumed_moe": int(r["moe_assumed"].sum()),
            "rounds_with_rule_based_release_date": int(r["source_type"].str.contains("rule").sum()),
            "modes": r["mode"].value_counts().to_dict(), "mobile_phone_quarters": sorted(r.loc[r["mode"] != "face-to-face", "quarter"].unique()),
            "respondent_base": r["respondent_base"].value_counts().to_dict(),
            "quarters_with_two_rounds": sorted(r.groupby("quarter").size().loc[lambda s: s > 1].index)}


def run() -> dict:
    q = quarterly()
    res = {"metadata": metadata_inventory(), "change_structure": change_structure(q), "design": design_effect(),
           "alternating_quarters_fi7_rule": alternating_quarters()}
    (OUT / "sawtooth.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    r = run()
    print(json.dumps({k: r[k] for k in ["metadata", "change_structure"]}, indent=1, default=str))
    d = r["design"]
    print({k: d[k] for k in d if k != "rounds"})
