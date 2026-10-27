"""PROTOCOL section 3: T43c rebuilt from raw data, label anatomy, SWS sampling noise and the accuracy ceiling it
implies, and the construct-validity checks (price -> hunger link, FNRI FIES, OCTA, PSA FIES 2023).

    python target_audit.py      # out/target_audit.json, out/label_noise_by_quarter.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

import ii_lib as L

F = L.F
FIES_DIR = L.Path(r"C:\Users\admin\Downloads\PHL-PSA-FIES-2023-V1-PUF")
FIES_PROV = {10: "PH040500000", 21: "PH040100000", 34: "PH040200000", 56: "PH040300000", 58: "PH040400000"}


def quarter_yoy() -> pd.DataFrame:
    y = L.yoy_published().copy()
    y["q"] = (y["ym"] // 12) * 4 + (y["ym"] % 12) // 3
    g = y.groupby(["province_code", "commodity", "q"])["yoy_pct"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] == 3].pivot_table(index=["province_code", "q"], columns="commodity", values="mean").reset_index()
    food = [c for c in g.columns if str(c).lower().startswith("food")][0]
    allc = [c for c in g.columns if c not in ("province_code", "q", food)][0]
    return g.rename(columns={food: "F", allc: "HL"})[["province_code", "q", "F", "HL"]]


def rebuild() -> tuple[pd.DataFrame, dict]:
    Q = quarter_yoy()
    bl = L.bl_quarters()[["q", "H"]]
    R = Q.merge(bl, on="q", how="inner")
    R["m_food"] = R["F"] - R["province_code"].map(F.TH_F)
    R["m_gap"] = R["F"] - R["HL"] - R["province_code"].map(F.TH_G)
    R["price"] = ((R["m_food"] > 0) | (R["m_gap"] > 0)).astype(int)
    R["hunger"] = (R["H"] > F.H_LINE).astype(int)
    R["y"] = R["price"] * R["hunger"]
    lab = pd.read_csv(F.DATA / "labels_t43c.csv", dtype={"province_code": str})
    J = lab.merge(R, on=["province_code", "q"], suffixes=("_lab", ""), how="outer", indicator=True)
    both = J[J["_merge"] == "both"]
    rep = {"rows_labels_file": int(len(lab)), "rows_rebuilt": int(len(R)), "matched_rows": int(len(both)),
           "y_mismatch": int((both["y_lab"] != both["y"]).sum()),
           "price_mismatch": int((both["price_lab"] != both["price"]).sum()),
           "hunger_mismatch": int((both["hunger_lab"] != both["hunger"]).sum()),
           "max_abs_F_diff": float((both["F_lab"] - both["F"]).abs().max()),
           "only_in_labels": int((J["_merge"] == "left_only").sum()), "only_rebuilt": int((J["_merge"] == "right_only").sum())}
    R["year"] = R["q"] // 4
    R["reason"] = np.select([(R["m_food"] > 0) & (R["m_gap"] > 0), R["m_food"] > 0, R["m_gap"] > 0], ["both", "food", "gap"], "none")
    an = {}
    for yr, g in R.groupby("year"):
        an[int(yr)] = {"rows": int(len(g)), "quarters": int(g["q"].nunique()), "HIGH": int(g["y"].sum()),
                       "HIGH_by_reason": {k: int(((g["y"] == 1) & (g["reason"] == k)).sum()) for k in ("food", "gap", "both")},
                       "price_met_but_hunger_blocked": int(((g["price"] == 1) & (g["hunger"] == 0)).sum()),
                       "hunger_met_but_price_blocked": int(((g["price"] == 0) & (g["hunger"] == 1)).sum()),
                       "hunger_quarters_above": int(g.drop_duplicates("q")["hunger"].sum())}
    since = R[R["q"] >= 2023 * 4 + 3]
    rep["anatomy_by_year"] = an
    rep["since_2023Q4"] = {"rows": int(len(since)), "hunger_always_above": bool(since["hunger"].all()),
                           "label_equals_price_share": float((since["y"] == since["price"]).mean())}
    rep["overall"] = {"rows": int(len(R)), "HIGH": int(R["y"].sum()), "label_equals_price_share": float((R["y"] == R["price"]).mean()),
                      "label_equals_hunger_share": float((R["y"] == R["hunger"]).mean())}
    rep["thresholds"] = {"H": F.H_LINE, "food": F.TH_F, "gap": F.TH_G,
                         "definition": "P60 of 2021-Q1..2022-Q4 (relative to each province's own 2021-22 level)"}
    return R, rep


def noise(R: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    bl = L.bl_quarters().copy()
    bl["z"] = (bl["H"] - F.H_LINE) / bl["se_q"]
    bl["p_true_above"] = norm.cdf(bl["z"])
    bl["p_wrong_side"] = np.minimum(bl["p_true_above"], 1 - bl["p_true_above"])
    rng = np.random.default_rng(L.SEED)
    ceil = []
    for h, s in zip(bl["H"], bl["se_q"]):
        tr = rng.normal(h, s, 20000)
        ceil.append(float(np.mean(norm.cdf(np.abs(tr - F.H_LINE) / s))))
    bl["agree_ceiling"] = ceil
    bl["quarter"] = bl["q"].map(F.qs)
    E = F.eval_rows()
    E = E.merge(bl[["q", "agree_ceiling", "p_wrong_side"]], on="q", how="left")
    E["ceiling_row"] = np.where(E["price"] == 1, E["agree_ceiling"], 1.0)
    M_ = R.set_index(["province_code", "q"])[["m_food", "m_gap"]]
    mg = [max(M_.loc[(p, q)]) if (p, q) in M_.index else np.nan for p, q in zip(E["province_code"], E["q"])]
    E["price_margin"] = mg
    by = {}
    for k, g in E.groupby("lead"):
        by[int(k)] = {"rows": int(len(g)), "accuracy_ceiling": float(g["ceiling_row"].mean()),
                      "rows_price_met_hunger_wrong_side_ge_0.20": int(((g["price"] == 1) & (g["p_wrong_side"] >= .2)).sum()),
                      "price_borderline_share(|margin|<0.5)": float((g["price_margin"].abs() < .5).mean())}
    evq = sorted(E["q"].unique())
    sub = bl[bl["q"].isin(evq)]
    rep = {"by_lead": by, "eval_quarters_wrong_side_ge_0.20": sub.loc[sub["p_wrong_side"] >= .2, "quarter"].tolist(),
           "T2_supported": bool((sub["p_wrong_side"] >= .2).any()),
           "se_range_pp": [float(bl["se_q"].min()), float(bl["se_q"].max())]}
    return bl, rep


def circ_perm(x: pd.Series, h: pd.Series, lag: int) -> dict:
    """Spearman of x_q with h_{q+lag}; p from every non-identity cyclic shift of h over the full quarter range."""
    qs = list(range(min(x.index.min(), h.index.min()), max(x.index.max(), h.index.max()) + 1))
    xv = x.reindex(qs).to_numpy(float)
    hv = h.reindex(qs).to_numpy(float)

    def rho(hh):
        hs = np.roll(hh, -lag)
        m = ~np.isnan(xv) & ~np.isnan(hs)
        if lag > 0:
            m[-lag:] = False
        return spearmanr(xv[m], hs[m]).statistic if m.sum() >= 6 else np.nan, int(m.sum())

    r0, n = rho(hv)
    null = [rho(np.roll(hv, s))[0] for s in range(1, len(qs))]
    null = np.array([v for v in null if np.isfinite(v)])
    return {"rho": float(r0), "n": n, "p_one_sided": float((np.sum(null >= r0) + 1) / (len(null) + 1)), "n_shifts": int(len(null))}


def validity(R: pd.DataFrame) -> dict:
    ps = F.ps_full().copy()
    ps["mx"] = np.maximum(ps["F"] - ps["province_code"].map(F.TH_F), ps["F"] - ps["HL"] - ps["province_code"].map(F.TH_G))
    X = ps.groupby("q")["mx"].mean()
    X = X[X.index >= 2021 * 4]
    H = L.bl_quarters().set_index("q")["H"]
    out = {"price_hunger_level": {L_: circ_perm(X, H, L_) for L_ in (0, 1, 2)}}
    dH = H.reindex(range(H.index.min(), H.index.max() + 1)).diff()
    out["price_hunger_change"] = {L_: circ_perm(X, dH.dropna(), L_) for L_ in (0, 1, 2)}
    out["T3_supported"] = bool(any(out["price_hunger_level"][l]["rho"] > 0 and out["price_hunger_level"][l]["p_one_sided"] < .10
                                   for l in (0, 1)))
    # FNRI FIES (descriptive)
    fn = pd.read_csv(L.EXP / "E87_Outcome_Gap" / "data_acquired" / "fnri_fies_observations.csv")
    fn = fn[fn["indicator"] == "moderate_or_severe_FI"]
    R2 = R.copy()
    ann = {}
    for yr in (2021, 2023, 2025):
        h = L.bl_quarters()
        hy = h[h["q"] // 4 == yr]
        r = R2[R2["year"] == yr]
        p = ps[ps["q"] // 4 == yr]
        ann[yr] = {"BL_SWS_mean": float(hy["H"].mean()), "SWS_quarters": int(len(hy)),
                   "T43c_HIGH_share": float(r["y"].mean()) if len(r) else None,
                   "price_condition_share": float(((p["mx"]) > 0).mean()),
                   "FNRI": fn[fn["year"] == yr][["geography", "basis", "value_pct", "ci_low", "ci_high"]].to_dict("records")}
    out["fnri_annual"] = ann
    out["sha_fnri"] = L.sha256(L.EXP / "E87_Outcome_Gap" / "data_acquired" / "fnri_fies_observations.csv")
    # OCTA vs SWS (descriptive)
    o = pd.read_csv(L.DATA / "octa_bl.csv")
    o = o[~o["fieldwork"].str.contains("previous")].drop_duplicates(["fieldwork", "value"])
    o["fw_end"] = pd.to_datetime(o["fieldwork"].str.split("/").str[1])
    r = F.rounds()
    r = r[r["area"] == "BL"].copy()
    r["fw_end"] = pd.to_datetime(r["fw_end"])
    rows = []
    for _, x in o.iterrows():
        d = (r["fw_end"] - x["fw_end"]).abs().dt.days
        if d.min() <= 45:
            s = r.loc[d.idxmin()]
            rows.append({"octa_fw_end": x["fw_end"].date().isoformat(), "octa": float(x["value"]), "octa_published": x["published"],
                         "sws_q": F.qs(int(s["q"])), "sws_round": float(s["H"]), "sws_published": s["published"],
                         "same_side_11.3": bool((x["value"] > F.H_LINE) == (s["H"] > F.H_LINE)),
                         "octa_minus_sws_publication_days": int((pd.Timestamp(x["published"]) - pd.Timestamp(s["published"])).days)})
    out["octa"] = {"pairs": rows, "agree": int(sum(p["same_side_11.3"] for p in rows)), "n": len(rows),
                   "octa_earlier": int(sum(p["octa_minus_sws_publication_days"] < 0 for p in rows)),
                   "sha_octa": L.sha256(L.DATA / "octa_bl.csv")}
    # PSA FIES 2023 (Family Income and Expenditure Survey), descriptive n = 5
    csv = FIES_DIR / "FIES PUF 2023 Volume1.CSV"
    if csv.exists():
        d = pd.read_csv(csv, encoding="utf-8-sig", usecols=["W_REGN", "W_PROV", "FOOD", "TOTEX", "RFACT", "MEM_RFACT", "NPCINC"])
        d = d[(d["W_REGN"] == 4) & d["W_PROV"].isin(FIES_PROV)]
        fs = {}
        for wp, g in d.groupby("W_PROV"):
            fs[FIES_PROV[wp]] = {"food_share": float((g["RFACT"] * g["FOOD"]).sum() / (g["RFACT"] * g["TOTEX"]).sum()),
                                 "bottom30_people": float(g.loc[g["NPCINC"] <= 3, "MEM_RFACT"].sum() / g["MEM_RFACT"].sum()),
                                 "records": int(len(g))}
        hi = R.groupby("province_code")["y"].mean()
        mx = ps[ps["q"] >= 2021 * 4].groupby("province_code")["mx"].mean()
        pv = list(fs)
        out["fies2023"] = {"by_province": {L.NAMES[p]: {**fs[p], "T43c_HIGH_share": float(hi[p]), "mean_price_excess": float(mx[p])} for p in pv},
                           "spearman_foodshare_vs_HIGH": float(spearmanr([fs[p]["food_share"] for p in pv], [hi[p] for p in pv]).statistic),
                           "spearman_bottom30_vs_HIGH": float(spearmanr([fs[p]["bottom30_people"] for p in pv], [hi[p] for p in pv]).statistic),
                           "spearman_foodshare_vs_price_excess": float(spearmanr([fs[p]["food_share"] for p in pv], [mx[p] for p in pv]).statistic),
                           "sha_csv": L.sha256(csv), "note": "FIES = Family Income and Expenditure Survey; no food-insecurity items"}
    return out


def main():
    L.check_protocol()
    R, rep = rebuild()
    bl, nz = noise(R)
    val = validity(R)
    bl.to_csv(L.OUT / "label_noise_by_quarter.csv", index=False, lineterminator="\n", float_format="%.5g")
    R.to_csv(L.OUT / "labels_rebuilt.csv", index=False, lineterminator="\n", float_format="%.6g")
    res = {"T1_rebuild": rep, "T2_noise": nz, "T3_validity": val}
    L.dump("target_audit.json", res)
    print({k: v for k, v in rep.items() if k not in ("anatomy_by_year", "thresholds")})
    print("anatomy", rep["anatomy_by_year"])
    print("noise", nz)
    print(bl[["quarter", "H", "n_rounds", "se_q", "p_wrong_side", "agree_ceiling"]].to_string())
    for k in ("price_hunger_level", "price_hunger_change"):
        print(k, val[k])
    print("T3", val["T3_supported"])
    for yr, a in val["fnri_annual"].items():
        print(yr, {k: v for k, v in a.items() if k != "FNRI"}, [(x["geography"], x["value_pct"]) for x in a["FNRI"]])
    print("octa", val["octa"]["agree"], "/", val["octa"]["n"], "octa earlier", val["octa"]["octa_earlier"])
    for p in val["octa"]["pairs"]:
        print("  ", p)
    if "fies2023" in val:
        print(val["fies2023"])


if __name__ == "__main__":
    main()
