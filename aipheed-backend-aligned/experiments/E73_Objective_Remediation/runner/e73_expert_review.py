"""E73: scoring of the structured expert / DA-evaluator review (validation layer E: judgement, not prediction).
No review has been conducted; tested on SYNTHETIC ratings only.

Form (expert_review/EXPERT_REVIEW_FORM.csv): one row per reviewer x item; item_type in
  indicator_relevance (does this indicator measure its stated food-security dimension? 1-4),
  explanation_clarity (is the explanation understandable and correct? 1-4),
  category_plausibility (is the province-quarter risk class plausible given local knowledge? agree / disagree / unsure).
Scores: item-level content validity index I-CVI = share of reviewers rating 3 or 4 (Polit and Beck 2006; acceptable
>= 0.78 with 6+ reviewers), scale-level S-CVI/Ave, and Fleiss' kappa for the categorical plausibility items.
"""
from __future__ import annotations

import pandas as pd

COLUMNS = ["reviewer_id", "role", "item_type", "item_id", "item_text", "rating", "comment"]


def i_cvi(df: pd.DataFrame) -> pd.DataFrame:
    r = df[df["item_type"].isin(["indicator_relevance", "explanation_clarity"])].copy()
    r["rating"] = pd.to_numeric(r["rating"], errors="coerce")
    g = r.dropna(subset=["rating"]).groupby(["item_type", "item_id"])["rating"]
    out = pd.DataFrame({"reviewers": g.size(), "i_cvi": g.apply(lambda s: float((s >= 3).mean()))}).reset_index()
    out["acceptable"] = (out["reviewers"] >= 6) & (out["i_cvi"] >= 0.78)
    return out


def fleiss_kappa(df: pd.DataFrame) -> float | None:
    r = df[df["item_type"] == "category_plausibility"]
    if r.empty:
        return None
    tab = pd.crosstab(r["item_id"], r["rating"])
    n = tab.sum(axis=1)
    if n.nunique() != 1 or n.iloc[0] < 2:
        return None                                    # Fleiss requires the same number of raters per item
    m = int(n.iloc[0])
    p_i = ((tab ** 2).sum(axis=1) - m) / (m * (m - 1))
    p_bar = float(p_i.mean())
    p_j = tab.sum(axis=0) / tab.values.sum()
    p_e = float((p_j ** 2).sum())
    return None if p_e == 1 else (p_bar - p_e) / (1 - p_e)


def summary(df: pd.DataFrame) -> dict:
    cv = i_cvi(df)
    return {"reviewers": int(df["reviewer_id"].nunique()), "items": cv.to_dict("records"),
            "s_cvi_ave": {t: float(g["i_cvi"].mean()) for t, g in cv.groupby("item_type")},
            "fleiss_kappa_plausibility": fleiss_kappa(df),
            "note": "expert judgement and operational usefulness; not statistical predictive validation"}
