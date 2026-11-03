"""NEW_MODEL Phase 2, item 6 (read only): why news is 2.8% of SHAP and why REF+news is worse than REF.

    python news_diagnostic.py   # -> ../out/news_diagnostic.json

Uses only stored outputs: IMPROVE_V2 pooled table (news columns), OPTION_1 REF+news forecasts and SHAP,
IMPROVE_V2_LEADS REF forecasts, BL labels. No model is fitted.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
sys.path.insert(0, str(EXP / "IMPROVE_V2" / "runner"))
import iv2_lib as V  # noqa: E402

H = V.H
ERA, LO, HI = H.qi("2021-Q1"), H.qi("2010-Q1"), H.qi("2026-Q3")


def main():
    T = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "table_pooled.csv", dtype={"area": str})
    T = T[(T["area"] == "BL") & (T["lead"] == 1)]
    lab = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "labels_areas.csv")
    lab = lab[lab["area"] == "BL"][["q", "y", "H"]]
    S = pd.read_csv(EXP / "OPTION_1" / "out" / "shap_refnews.csv")
    F = pd.read_csv(EXP / "OPTION_1" / "out" / "forecasts_refnews.csv")
    L = pd.read_csv(EXP / "IMPROVE_V2_LEADS" / "out" / "forecasts_leads.csv")
    out = {"news_columns": V.NEWS}
    t = T[T["t"] >= ERA]
    out["coverage"] = {"news_era_origins": int(len(t)),
                       "non_missing": {c: int(t[c].notna().sum()) for c in V.NEWS},
                       "N1R_missing_origins": [H.qs(int(x)) for x in t[t["N1R"].isna()]["t"]]}
    out["by_lead"] = {}
    for k in (1, 2):
        s = S[(S["lead"] == k) & (S["q"] >= LO) & (S["q"] <= HI) & S["q"].isin(lab["q"])]
        cols = [c for c in s.columns if c.startswith("shap_")]
        nc = [f"shap_{c}" for c in V.NEWS]
        ne = s[s["t"] >= ERA]
        share = lambda x: float(100 * x[nc].abs().sum().sum() / x[cols].abs().sum().sum())  # noqa: E731
        a = F[(F["name"] == "REF+news") & (F["lead"] == k)][["t", "q", "p"]].merge(
            L[(L["name"] == "REF") & (L["lead"] == k)][["t", "p"]], on="t", suffixes=("_news", "_ref")).merge(lab, on="q")
        a = a[(a["q"] >= LO) & (a["q"] <= HI)]
        per = {}
        for nm, g in (("pre_2021_origins", a[a["t"] < ERA]), ("news_era_origins", a[a["t"] >= ERA])):
            per[nm] = {"quarters": int(len(g)),
                       "brier_refnews": float(((g["p_news"] - g["y"]) ** 2).mean()),
                       "brier_ref": float(((g["p_ref"] - g["y"]) ** 2).mean()),
                       "acc_refnews": float(((g["p_news"] >= .5) == g["y"]).mean()),
                       "acc_ref": float(((g["p_ref"] >= .5) == g["y"]).mean()),
                       "identical_probabilities": int(((g["p_news"] - g["p_ref"]).abs() < 1e-12).sum()),
                       "high_share": float(g["y"].mean())}
        out["by_lead"][str(k)] = {"news_shap_share_all_columns_pct": share(s),
                                  "news_shap_share_news_era_pct": share(ne), **per}
    W = T[T["t"] >= ERA].merge(lab, on="q")
    out["univariate_auc_news_era_lead1"] = {c: {"n": int(len(g)), "auc": float(roc_auc_score(g["y"], g[c]))}
                                            for c in V.NEWS
                                            for g in [W.dropna(subset=[c, "y"])] if g["y"].nunique() == 2}
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "news_diagnostic.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
