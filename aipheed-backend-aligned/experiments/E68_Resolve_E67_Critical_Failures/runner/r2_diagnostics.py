"""E68 r2 (PROTOCOL 4): target validity (R-T), independent face validity against PSA subsistence incidence (R-FV), and
the trigger-group variance structure (R-G). Descriptive only; nothing here selects a model.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E68_Resolve_E67_Critical_Failures/runner/r2_diagnostics.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e68_lib as R  # noqa: E402

H, L, E, F, P2, np, pd = R.H, R.L, R.E, R.F, R.P2, R.np, R.pd
from scipy.stats import spearmanr  # noqa: E402

SUBS = R.EXP / "E27_Resolve_Forecasting_Failures" / "acquisition" / "validated" / "psa_subsistence_population_2021_2023.csv"
LAST = "2026-Q3"


def main():
    R.verify_protocol()
    d, X, B = E.load()
    Y = R.labels(d)
    Y = Y[Y["q"].between(L.qi("2021-Q1"), L.qi(LAST)) & Y["T43"].notna()].copy()
    Y["year"] = Y["quarter"].str[:4].astype(int)
    Y["province"] = Y["province_code"].map(L.NAMES)
    Y["hunger_above"] = (Y["H_all"] > L.e40_spec()["H"]).astype(int)
    Y["eval"] = Y["q"].between(L.qi("2024-Q2"), L.qi("2026-Q3"))
    # R-T: rates and agreement
    by_year = Y.groupby("year")[["T43", "PS", "PS_AFF", "TAFF", "hunger_above"]].mean().reset_index()
    by_prov = Y.groupby("province")[["T43", "PS", "PS_AFF", "TAFF"]].mean().reset_index()
    ev = Y[Y["eval"]]
    xt = pd.crosstab(ev["T43"].astype(int), ev["TAFF"].astype(int)).rename_axis(index="T43", columns="TAFF")
    q_uni = Y.groupby("quarter").agg(T43_same=("T43", lambda s: s.nunique() == 1), TAFF_same=("TAFF", lambda s: s.nunique() == 1),
                                     T43_high=("T43", "sum"), TAFF_high=("TAFF", "sum"), H=("H_all", "first"))
    hungry_low = Y[(Y["hunger_above"] == 1) & (Y["T43"] == 0)]
    rt = {"rows": int(len(Y)), "quarters": int(Y["quarter"].nunique()), "eval_rows": int(len(ev)),
          "eval_quarters": int(ev["quarter"].nunique()),
          "eval_T43_eq_PS": int((ev["T43"] == ev["PS"]).sum()), "eval_TAFF_eq_PS_AFF": int((ev["TAFF"] == ev["PS_AFF"]).sum()),
          "eval_T43_HIGH": int(ev["T43"].sum()), "eval_TAFF_HIGH": int(ev["TAFF"].sum()),
          "quarters_hunger_above_line": int(Y.groupby("quarter")["hunger_above"].first().sum()),
          "quarters_one_label_T43": int(q_uni["T43_same"].sum()), "quarters_one_label_TAFF": int(q_uni["TAFF_same"].sum()),
          "rows_hunger_above_but_T43_LOW": int(len(hungry_low)),
          "rows_hunger_above_but_TAFF_LOW": int(((Y["hunger_above"] == 1) & (Y["TAFF"] == 0)).sum()),
          "crosstab_eval_T43_vs_TAFF": xt.to_dict()}
    H.write_csv(by_year, R.TABLES / "r2_target_by_year.csv")
    H.write_csv(by_prov, R.TABLES / "r2_target_by_province.csv")
    H.write_csv(q_uni.reset_index(), R.TABLES / "r2_target_by_quarter.csv")
    H.write_csv(Y[["quarter", "province", "H_all", "F", "HL", "PS", "T43", "PS_AFF", "TAFF"]], R.TABLES / "r2_labels_all.csv")
    # R-FV: annual HIGH rates vs PSA subsistence incidence (population), 2021 and 2023
    S = pd.read_csv(SUBS, dtype={"province_code": str})
    S = S[S["province_code"].isin(L.PROVS)]
    fv = []
    for yr in (2021, 2023):
        s = S[S["reference_year"] == yr].set_index("province_code")
        a = Y[Y["year"] == yr].groupby("province_code")[["T43", "PS", "TAFF", "F"]].mean()
        for lab in ("T43", "PS", "TAFF", "F"):
            x, yv = a.loc[L.PROVS, lab].to_numpy(float), s.loc[L.PROVS, "subsistence_incidence_pct"].to_numpy(float)
            rho = spearmanr(x, yv).correlation if np.ptp(x) > 0 else float("nan")
            fv.append({"year": yr, "measure": lab if lab != "F" else "mean food YoY", "spearman_vs_subsistence": rho,
                       "values": dict(zip([L.NAMES[p] for p in L.PROVS], np.round(x, 3))),
                       "subsistence": dict(zip([L.NAMES[p] for p in L.PROVS], yv)),
                       "max_cv_pct": float(s["cv_pct"].max())})
    H.write_csv(pd.DataFrame(fv), R.TABLES / "r2_face_validity_subsistence.csv")
    # R-G: within-quarter (cross-province) share of each feature's variance
    feats = [c for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g]] + list(F.M.POLICY)
    Z = X[X["t"].between(L.qi("2021-Q3"), L.qi(LAST))]
    rg = []
    for c in feats:
        v = Z[c].astype(float)
        tot = float(np.nanvar(v))
        within = float(np.nanmean(Z.groupby("t")[c].apply(lambda s: np.nanvar(s.astype(float)) if s.notna().sum() > 1 else np.nan)))
        rg.append({"feature": c, "group": "news" if c.startswith("news_") else R.K.group_of(c), "total_var": tot,
                   "within_quarter_share": (within / tot) if tot > 0 else float("nan"),
                   "national_or_regional": bool(tot > 0 and within / tot < 1e-9)})
    RG = pd.DataFrame(rg)
    H.write_csv(RG, R.TABLES / "r2_trigger_variance.csv")
    H.dump({"protocol_sha256": R.verify_protocol(), "target": rt,
            "face_validity": [{k: v for k, v in r.items() if k in ("year", "measure", "spearman_vs_subsistence")} for r in fv],
            "national_features": RG.loc[RG["national_or_regional"], "feature"].tolist()}, R.OUT / "r2_diagnostics.json")
    pd.set_option("display.width", 250)
    print(by_year.round(3).to_string()); print(by_prov.round(3).to_string()); print(xt); print(rt)
    print(pd.DataFrame(fv)[["year", "measure", "spearman_vs_subsistence"]].round(2).to_string())
    print(RG.round(3).to_string())


if __name__ == "__main__":
    main()
