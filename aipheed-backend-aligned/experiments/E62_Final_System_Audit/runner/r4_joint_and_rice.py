"""E62 r4: (a) is P_hunger x P_price a valid joint probability? (b) does rice wholesale price carry a leading signal?

(a) Dependence of provincial price pressure (PS) on regional hunger (H > 11.3), 2021-Q2..2026-Q3, from the r1 labels:
    row-level Fisher test (as E61 reported), then the same question at the level where hunger actually varies (one value
    per quarter): quarter-level Spearman of H with the share of provinces under price pressure, and a permutation test
    that shuffles hunger across quarters (rows inside a quarter are not independent). A time-trend check: the two series
    against the quarter index.
(b) Rice wholesale YoY (previous quarter, as the model sees it) vs the food YoY and the PS label two quarters later, with
    and without the latest food YoY already known (partial correlation), province-quarters 2022-Q1..2026-Q3; units and
    coverage of the input.

Diagnostics only: nothing here selects or changes a model.

    backend/venv/Scripts/python.exe -B runner/r4_joint_and_rice.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E62 = Path(__file__).resolve().parents[1]
EXP = E62.parent
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402
from scipy import stats  # noqa: E402

E, F, L, np, pd = G.E, G.F, G.L, G.np, G.pd
LAB = E62 / "tables" / "r1_labels_independent.csv"
RNG = np.random.default_rng(62)


def dependence(W: pd.DataFrame) -> dict:
    W = W[W["H_all"].notna()].copy()
    W["Hhi"] = (W["H_all"] > 11.3).astype(int)
    tab = pd.crosstab(W["Hhi"], W["PS"])
    odds, p_f = stats.fisher_exact(tab.to_numpy())
    rate = W.groupby("Hhi")["PS"].mean()
    Q = W.groupby("quarter").agg(H=("H_all", "first"), ps_share=("PS", "mean")).reset_index()
    Q["qi"] = Q["quarter"].map(L.qi)
    rho, p_rho = stats.spearmanr(Q["H"], Q["ps_share"])
    # permutation: shuffle hunger values across quarters, recompute the PS-rate difference (high - low hunger)
    obs = rate.get(1, np.nan) - rate.get(0, np.nan)
    hq = Q.set_index("quarter")["H"]
    diffs = []
    for _ in range(20000):
        perm = dict(zip(hq.index, RNG.permutation(hq.to_numpy())))
        hh = (W["quarter"].map(perm) > 11.3).astype(int)
        if hh.nunique() < 2:
            continue
        diffs.append(W["PS"][hh == 1].mean() - W["PS"][hh == 0].mean())
    diffs = np.array(diffs)
    p_perm = float(np.mean(np.abs(diffs) >= abs(obs) - 1e-12))
    t_h, p_th = stats.spearmanr(Q["qi"], Q["H"])
    t_ps, p_tps = stats.spearmanr(Q["qi"], Q["ps_share"])
    hi_q = Q[Q["H"] > 11.3]["quarter"].tolist()
    lo_q = Q[Q["H"] <= 11.3]["quarter"].tolist()
    return {"rows": int(len(W)), "quarters": int(len(Q)), "crosstab": tab.to_dict(),
            "PS_rate_hunger_high": round(float(rate.get(1, np.nan)), 3), "PS_rate_hunger_low": round(float(rate.get(0, np.nan)), 3),
            "fisher_row_level": {"odds_ratio": round(float(odds), 3), "p": float(p_f)},
            "quarter_level_spearman_H_vs_PS_share": {"rho": round(float(rho), 3), "p": round(float(p_rho), 4)},
            "quarter_permutation_p": round(p_perm, 4),
            "trend_H": {"rho": round(float(t_h), 3), "p": round(float(p_th), 4)},
            "trend_PS_share": {"rho": round(float(t_ps), 3), "p": round(float(p_tps), 4)},
            "low_hunger_quarters": lo_q, "high_hunger_quarters_n": len(hi_q),
            "reading": None}


def rice(d, X, B) -> dict:
    lab = pd.read_csv(LAB, dtype={"province_code": str})
    lab["q"] = lab["quarter"].map(L.qi)
    rows = []
    for t in range(L.qi("2022-Q1"), L.qi("2026-Q3") + 1):
        _, te = F.frame(d, X, B, t, None)
        for _, r in te.iterrows():
            rows.append({"t": t, "province_code": r["province_code"], "rice_whsl_yoy": r["rice_whsl_yoy"],
                         "F_now": r["F_now"], "gap_now": r["gap_now"], "base0": r["base_0.0"]})
    R = pd.DataFrame(rows)
    R = R.merge(lab[["q", "province_code", "F", "PS"]].rename(columns={"q": "tq"}).assign(t=lambda f: f["tq"] - 2),
                on=["t", "province_code"], how="left")
    cov = {"rows": int(len(R)), "rice_missing": int(R["rice_whsl_yoy"].isna().sum()),
           "rice_range": [round(float(R["rice_whsl_yoy"].min()), 1), round(float(R["rice_whsl_yoy"].max()), 1)]}
    S = R.dropna(subset=["rice_whsl_yoy", "F", "F_now"])
    r1 = stats.spearmanr(S["rice_whsl_yoy"], S["F"])
    r2 = stats.spearmanr(S["F_now"], S["F"])
    # partial: residualise F(t+2) and rice on F_now (OLS), correlate residuals
    def resid(y, x):
        A = np.c_[np.ones(len(x)), x]
        return y - A @ np.linalg.lstsq(A, y, rcond=None)[0]
    pr = stats.pearsonr(resid(S["rice_whsl_yoy"].to_numpy(), S["F_now"].to_numpy()),
                        resid(S["F"].to_numpy(), S["F_now"].to_numpy()))
    # quarter-level (rice moves together across provinces): mean over provinces
    Qm = S.groupby("t")[["rice_whsl_yoy", "F", "F_now"]].mean()
    rq = stats.spearmanr(Qm["rice_whsl_yoy"], Qm["F"])
    prq = stats.pearsonr(resid(Qm["rice_whsl_yoy"].to_numpy(), Qm["F_now"].to_numpy()),
                         resid(Qm["F"].to_numpy(), Qm["F_now"].to_numpy()))
    auc_rice = None
    S2 = S.dropna(subset=["PS"])
    if S2["PS"].nunique() == 2:
        from sklearn.metrics import roc_auc_score
        auc_rice = round(float(roc_auc_score(S2["PS"], S2["rice_whsl_yoy"])), 3)
        auc_fnow = round(float(roc_auc_score(S2["PS"], S2["F_now"])), 3)
    by_q = Qm.round(2).reset_index().assign(origin=lambda f: f["t"].map(L.qs), target=lambda f: (f["t"] + 2).map(L.qs))
    by_q.drop(columns="t").to_csv(E62 / "tables" / "r4_rice_vs_food_by_quarter.csv", index=False, lineterminator="\n")
    return {"coverage": cov, "n_pairs": int(len(S)),
            "spearman_rice_vs_food_yoy_t_plus_2": [round(float(r1.statistic), 3), round(float(r1.pvalue), 4)],
            "spearman_latest_food_vs_food_yoy_t_plus_2": [round(float(r2.statistic), 3), round(float(r2.pvalue), 4)],
            "partial_r_rice_given_latest_food": [round(float(pr.statistic), 3), round(float(pr.pvalue), 4)],
            "quarter_level_n": int(len(Qm)),
            "quarter_level_spearman_rice_vs_food_t_plus_2": [round(float(rq.statistic), 3), round(float(rq.pvalue), 4)],
            "quarter_level_partial_r_given_latest_food": [round(float(prq.statistic), 3), round(float(prq.pvalue), 4)],
            "auc_PS_rice": auc_rice, "auc_PS_latest_food": auc_fnow}


def main():
    W = pd.read_csv(LAB, dtype={"province_code": str})
    dep = dependence(W)
    d, X, B = E.load()
    rc = rice(d, X, B)
    res = {"dependence": dep, "rice": rc}
    (E62 / "out" / "r4_joint_and_rice.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
