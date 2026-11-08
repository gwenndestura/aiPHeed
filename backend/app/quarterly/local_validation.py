"""
app/quarterly/local_validation.py  (E26)
----------------------------------------
Does aiPHeed distinguish meaningful LOCAL risk? Compares aiPHeed's provincial or LGU risk ordering with an
authorized local food-insecurity outcome (for example CBMS 2024 household FIES by municipality, validated by
app.quarterly.outcomes). Cross-sectional agreement only: it validates the ORDERING (Objective 3, SOP Q4), never a
probability, and never uses a constructed price indicator as the outcome.

Reported: Spearman and Kendall rank correlation with a unit-cluster bootstrap CI; top-third agreement (the share of
the outcome's top third that aiPHeed also puts in its top third, against the 1/3 expected by chance); and the same
statistics for the density-only and poverty-only orderings, so any agreement can be attributed to its source.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

SEED, N_BOOT = 20261014, 4000


def _top_third(score: pd.Series, outcome: pd.Series) -> float:
    n = len(score)
    k = max(1, n // 3)
    a = set(score.sort_values(ascending=False).index[:k])
    b = set(outcome.sort_values(ascending=False).index[:k])
    return len(a & b) / k


def agreement(score: pd.Series, outcome: pd.Series, groups: pd.Series | None = None) -> dict:
    """score, outcome: indexed by unit (province or LGU code). groups: optional province of each unit, so that the
    within-province agreement (the part the vulnerability weights claim) is reported separately."""
    idx = score.index.intersection(outcome.index)
    if len(idx) < 5:
        raise ValueError("fewer than 5 units with both a score and an authorized outcome")
    s, o = score.loc[idx].astype(float), outcome.loc[idx].astype(float)
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(N_BOOT):
        b = rng.choice(len(idx), len(idx), replace=True)
        if len(np.unique(b)) > 2:
            r = spearmanr(s.iloc[b], o.iloc[b]).statistic
            if r == r:
                boots.append(r)
    out = {"units": int(len(idx)), "spearman": float(spearmanr(s, o).statistic),
           "spearman_ci95": [float(np.quantile(boots, .025)), float(np.quantile(boots, .975))] if boots else None,
           "kendall": float(kendalltau(s, o).statistic), "top_third_agreement": _top_third(s, o),
           "top_third_chance": 1 / 3}
    if groups is not None:
        g = groups.loc[idx]
        within = {}
        for prov, ii in g.groupby(g).groups.items():
            if len(ii) >= 5:
                within[str(prov)] = float(spearmanr(s.loc[ii], o.loc[ii]).statistic)
        out["within_province_spearman"] = within
    return out


def attribution(table: pd.DataFrame, outcome_col: str, score_col: str = "risk_index",
                density_col: str = "density", poverty_col: str = "poverty_value_used",
                group_col: str = "province_code") -> dict:
    """Agreement of the aiPHeed score and of the two single-component orderings with the same outcome."""
    t = table.set_index(table.columns[0]) if table.index.name is None else table
    res = {}
    for name, col in (("aiPHeed_risk_index", score_col), ("density_only", density_col), ("poverty_only", poverty_col)):
        res[name] = agreement(t[col], t[outcome_col], t[group_col] if group_col in t.columns else None)
    return res
