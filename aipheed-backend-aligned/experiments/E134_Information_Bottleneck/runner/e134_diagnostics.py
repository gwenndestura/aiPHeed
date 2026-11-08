"""
E134 diagnostics (protocol section 5; never candidates):
  T1 target uncertainty share of forecast error; N1 news evidence taxonomy and FSSI vs Balance Luzon residual;
  EV event timeline (driver publication relative to issue dates, 2023-07 .. 2026-10); PV provincial household-stress
  indicators from FIES 2023 Tables 7-8 against PFDR 2023 and the E131 relative food deprivation.

    python -I runner/e134_diagnostics.py      (after e134_run.py)
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e134_run as E  # noqa: E402

R, X, L = E.R, E.X, E.L
OUT, RAW = E.OUT, E.RAW
REPO = E.EXP.parent.parent
PROV = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
SEED = 134


def t1_target_uncertainty(P) -> pd.DataFrame:
    rows = []
    g0 = P[(P.policy == "P-DASH") & (P.n_obs >= 8)]
    for k, g in g0.groupby("lead"):
        for per, gp in [("all", g)] + list(g.groupby("period")):
            for m in ("PERSIST", "SEAS-LLM", "HFM-X", "E134-AREA-T", "E134-ONI", "ORACLE-LEVEL", "ORACLE-NOW"):
                e = gp[f"f_{m}"] - gp["y_true"]
                mse, s2 = float((e ** 2).mean()), float((gp["se"] ** 2).mean())
                rows.append({"lead": int(k), "period": per, "model": m, "rows": len(gp), "mse": mse,
                             "mean_sampling_variance": s2, "sampling_share_of_mse": s2 / mse if mse else np.nan,
                             "rmse_excess_over_sampling": float(np.sqrt(max(mse - s2, 0.0)))})
    return pd.DataFrame(rows)


def n1_news(P) -> tuple[pd.DataFrame, dict]:
    f = pd.read_csv(REPO / "backend" / "data" / "news_e31" / "fssi_v2_panel.csv")
    f = f[f["quarter"].map(L.qi) <= L.qi("2026-Q3")]
    def cls(r):
        if r["n_province_attributed"] == 0:
            return "no relevant article found"
        if r["n_admitted"] == 0:
            return "articles found, none admitted (insufficient evidence)"
        if r["evidence_status"] == "LIMITED_SIGNAL":
            return "admitted evidence, limited (1-3 articles)"
        return "admitted evidence, sufficient"
    f["taxonomy"] = f.apply(cls, axis=1)
    full = pd.MultiIndex.from_product([PROV, [L.qs(i) for i in range(L.qi("2021-Q1"), L.qi("2026-Q3") + 1)]])
    missing = len(full.difference(pd.MultiIndex.from_frame(f[["province", "quarter"]])))
    tax = f["taxonomy"].value_counts().rename_axis("taxonomy").reset_index(name="province_quarters")
    tax = pd.concat([tax, pd.DataFrame([{"taxonomy": "missing source (no panel row)", "province_quarters": missing}])])
    pop = pd.read_csv(REPO / "backend" / "data" / "reference" / "popcen2024_calabarzon_municipal.csv",
                      dtype={"lgu_code": str}).groupby("province")["population_2024"].sum()
    q = f.dropna(subset=["FSSI_v2"]).copy()
    q["w"] = q["province"].map(pop)
    agg = q.groupby("quarter").apply(lambda g: pd.Series({"fssi_pw": np.average(g["FSSI_v2"], weights=g["w"]),
                                                          "provinces": len(g)})).reset_index()
    agg["qi"] = agg["quarter"].map(L.qi)
    g = P[(P.policy == "P-DASH") & (P.lead == 2) & (P.area == "balance_luzon") & (P.n_obs >= 8)].copy()
    g["resid"] = g["y_true"] - g["f_HFM-X"]
    g["news_q"] = g["issue"].map(lambda d: L.qi(L.quarter_of(d)) - 1)     # news of the quarter ended before the issue
    m = g.merge(agg, left_on="news_q", right_on="qi", how="left")
    d = m.dropna(subset=["fssi_pw"])
    res = {"rows_with_fssi": int(len(d)), "rows_total": int(len(m))}
    if len(d) >= 5:
        rho = stats.spearmanr(d["fssi_pw"], d["resid"]).statistic
        rng = np.random.default_rng(SEED)
        perm = [stats.spearmanr(d["fssi_pw"], rng.permutation(d["resid"].to_numpy())).statistic for _ in range(10000)]
        res.update(spearman_fssi_vs_hfmx_residual=float(rho), p_perm=float(np.mean(np.abs(perm) >= abs(rho))))
    agg.to_csv(OUT / "e134_fssi_calabarzon_popweighted.csv", index=False)
    return tax, res


def ev_timeline(rr) -> pd.DataFrame:
    drv = {"rice": R.Drivers("rice"), "oni": R.Drivers("rice", "oni_quarter_mean")}
    adrv = E.AreaDrivers()
    qt = X.quarter_table(rr)
    nat = qt.groupby("quarter")["y"].mean()
    rows = []
    for D, issue in X.schedule(rr, "P-DASH"):
        if issue < date(2023, 7, 1):
            continue
        qa = X.asof(rr, issue)
        vals, last, _ = drv["rice"].at(issue)
        vo, lo, _ = drv["oni"].at(issue)
        av, al = adrv.at(issue)
        t2 = L.qs(L.qi(D) + 1)
        rec = {"issue": issue, "lead2_target": t2, "latest_sws_quarter": L.qs(int(qa["qi"].max())),
               "sws_4area_mean_latest": float(qa[qa.qi == qa.qi.max()]["y"].mean()),
               "sws_4area_mean_target": float(nat.get(t2, np.nan))}
        for nm, (v, l_) in {"rice_qq": (vals["A"], last["A"]), "typhoons": (vals["C"], last["C"]), "oni": (vo["C"], lo["C"]),
                            "unemp_chg": (vals["E"], last["E"]), "news_shortage": (vals["N"], last["N"])}.items():
            rec[f"{nm}_quarter"] = L.qs(l_) if l_ is not None else None
            rec[f"{nm}_z"] = float(v[l_]) if l_ is not None else np.nan
        for nm in ("aR", "aP"):
            rec[f"{nm}_quarter"] = L.qs(al[nm]) if al.get(nm) is not None else None
            rec[f"{nm}_z_mean_areas"] = float(np.mean(av[nm][al[nm]])) if al.get(nm) is not None else np.nan
        rows.append(rec)
    d = pd.DataFrame(rows)
    d["realized_change"] = d["sws_4area_mean_target"] - d["sws_4area_mean_latest"]
    return d


def pv_provincial() -> pd.DataFrame:
    t8 = pd.read_csv(RAW / "psa_fies2023_t8_income_expenditure_savings.csv", encoding="latin-1")
    t7 = pd.read_csv(RAW / "psa_fies2023_t7_expenditure_by_group.csv", encoding="latin-1")
    # PSA lists Quezon province excluding the independent component city of Lucena (Lucena kept out, as in E131)
    fix = {"Quezon (Excluding City Of Lucena)": "Quezon"}
    t8["geo"] = t8.iloc[:, 0].str.strip().str.title().replace(fix)
    t7["geo"] = t7.iloc[:, 0].str.strip().str.title().replace(fix)
    rr_tab = pd.read_csv(E.EXP / "E131_Objectives_Resolution" / "out" / "x3c_relative_risk.csv").set_index("province")
    rows = []
    for p in PROV:
        a = t8[t8.geo == p].set_index("Per Capita Income Decile")
        b = t7[(t7.geo == p) & t7["Major Expenditure Group"].str.startswith("Food and Non-Alcoholic")]
        if a.empty or b.empty:
            continue
        b = b.iloc[0]
        rows.append({"province": p,
                     "avg_income_all_k": float(a.loc["All Income Groups"].iloc[1]),
                     "avg_savings_decile1_k": float(a.loc["First Decile"].iloc[3]),
                     "savings_rate_decile1": float(a.loc["First Decile"].iloc[3] / a.loc["First Decile"].iloc[1]),
                     "food_share_all_pct": float(b["All Income Groups"]), "food_share_decile1_pct": float(b["1st Decile"]),
                     "pfdr_2023": float(rr_tab.loc[p, "pfdr_2023"]), "rr_food_deprivation_e131": float(rr_tab.loc[p, "rr_food_deprivation"])})
    d = pd.DataFrame(rows)
    # rank 1 = most stressed: highest food share, lowest savings rate
    d["rank_food_share_decile1_pct"] = d["food_share_decile1_pct"].rank(ascending=False)
    d["rank_savings_rate_decile1"] = d["savings_rate_decile1"].rank(ascending=True)
    d["rank_pfdr_2023"] = d["pfdr_2023"].rank(ascending=False)
    return d


def main():
    P = pd.read_csv(OUT / "e134_predictions.csv")
    P["issue"] = pd.to_datetime(P["issue"]).dt.date
    rr = X.rounds()
    t1_target_uncertainty(P).to_csv(OUT / "t1_target_uncertainty.csv", index=False)
    tax, res = n1_news(P)
    tax.to_csv(OUT / "n1_news_evidence_taxonomy.csv", index=False)
    L.dump(res, OUT / "n1_fssi_vs_residual.json")
    ev_timeline(rr).to_csv(OUT / "ev_driver_timeline.csv", index=False)
    pv = pv_provincial()
    pv.to_csv(OUT / "pv_provincial_household_stress.csv", index=False)
    if len(pv) >= 4:
        L.dump({"spearman_food_share_d1_vs_pfdr": float(stats.spearmanr(pv["food_share_decile1_pct"], pv["pfdr_2023"]).statistic),
                "spearman_savings_rate_d1_vs_pfdr": float(stats.spearmanr(pv["savings_rate_decile1"], pv["pfdr_2023"]).statistic),
                "n_provinces": int(len(pv))}, OUT / "pv_rank_agreement.json")
    for f in ("t1_target_uncertainty", "n1_news_evidence_taxonomy", "ev_driver_timeline", "pv_provincial_household_stress"):
        print(f)
        d = pd.read_csv(OUT / f"{f}.csv")
        print((d[(d.lead == 2) & (d.period == "all")] if f.startswith("t1") else d).round(3).to_string())
    print(res)


if __name__ == "__main__":
    main()
