"""
What each trigger group contributes to the fitted model (exact TreeSHAP), the quarterly estimates for the five provinces, and the news audit.
Descriptive, after scoring: changes no forecast.

    python -m app.e148.explain -> data/e148/out/explain.json, issue/calabarzon_quarterly_table.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.e147 import features as Fe
from app.e148 import OUT
from app.e148 import model as M
from app.e148 import panel as Pn
from app.fi5.target import qlabel

GROUPS = {"Market and prices": ["m_food_cpi_yoy", "m_rice_cpi_yoy", "m_food_threshold_rel"],
          "Climate stress": ["c_soil_anom_3m", "c_rain_anom_6m", "c_tc_4q", "c_agri_yoy", "c_fish_yoy", "oni", "soil_since", "rain_since", "tc_rate_since", "agri_since"],
          "Employment": ["unemp_rate", "unemp_yoy", "unemp_region", "unemp_chg_since"], "OFW remittances": ["remit_yoy", "remit_q_yoy", "remit_since"],
          "Poverty and vulnerability": ["p_poverty", "p_subsistence", "p_poverty_gap", "p_density"], "Survey history": ["y_anchor", "gap_q", "rtm", "rc2011", "lead"], "SWS area signal": ["sws_last", "d_sws", "sws_fc"]}


def main():
    S = M.Store()
    tr = M.rows_for(S, M.targets(S, ["FNRI2015", "ENNS2018", "ENNS2019"]), list(range(1, 9)), "F")
    m = M.QModel(M.SETS["Q-G"]).fit(tr)
    b = m.m_.chosen_ if hasattr(m.m_, "chosen_") else m.m_
    booster = b.m_.booster_
    cols = b.cols
    c = booster.predict(tr[cols], pred_contrib=True)[:, :-1]
    imp = pd.Series(np.abs(c).mean(axis=0), index=cols)
    out = {"n_trees": int(b.n_trees_), "inputs_used": cols, "inputs_with_any_split": [k for k, v in imp.items() if v > 0], "unused_inputs": [k for k, v in imp.items() if v == 0], "shap_share_by_group": {}, "shap_by_input": imp.round(5).sort_values(ascending=False).to_dict()}
    tot = imp.sum()
    for g, fs in GROUPS.items():
        out["shap_share_by_group"][g] = float(imp.reindex(fs).fillna(0).sum() / tot) if tot > 0 else 0.0
    oof = m.oof_
    out["spatial_leave_region_out"] = {"change_rho_lead1": float(oof[oof["lead"] == 1][["pred", "y"]].corr(method="spearman").iloc[0, 1]), "rmse_logit": float(np.sqrt(np.mean(oof["res"] ** 2))), "sigma_by_lead": {int(k): float(v) for k, v in m.sigma_.items()}}
    Sr = pd.read_csv(OUT / "quarterly_series_lead1.csv")
    c5 = Sr[Sr["province"].isin(["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"])].copy()
    c5["quarter"] = c5["T"].map(lambda t: qlabel(int(t)))
    c5["estimate_pct"] = 100 / (1 + np.exp(-c5["mu_Q-G"]))
    c5["low90"], c5["high90"] = 100 / (1 + np.exp(-(c5["mu_Q-G"] - 1.645 * c5["sigma_Q-G"]))), 100 / (1 + np.exp(-(c5["mu_Q-G"] + 1.645 * c5["sigma_Q-G"])))
    c5["row_type"] = "estimated (no survey this quarter; lead-1 backtest; not validated for this quarter)"
    c5[["province", "quarter", "estimate_pct", "low90", "high90", "gap_q", "n_train_surveys", "row_type"]].round(1).to_csv(OUT / "issue" / "calabarzon_quarterly_table.csv", index=False, lineterminator="\n")
    w = c5.pivot_table(index="quarter", columns="province", values="estimate_pct")
    out["quarterly_movement"] = {"sd_within_province_points": w.std().round(2).to_dict(), "mean_abs_quarter_change_points": w.diff().abs().mean().round(2).to_dict(), "mean_spread_across_provinces_points": float((w.max(axis=1) - w.min(axis=1)).mean()), "quarters": int(len(w)), "pair_corr_mean": float(w.corr().values[np.triu_indices(5, 1)].mean())}
    (OUT / "explain.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps({k: out[k] for k in ("n_trees", "shap_share_by_group", "unused_inputs", "spatial_leave_region_out", "quarterly_movement")}, indent=1, default=float))
    print(list(out["shap_by_input"].items())[:10])
    print(w.tail(10).round(1).to_string())


if __name__ == "__main__":
    main()
