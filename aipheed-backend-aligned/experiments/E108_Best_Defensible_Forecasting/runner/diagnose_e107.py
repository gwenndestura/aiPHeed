"""E108 step 1: independent diagnosis of E107 from data and E107's stored outputs (no new model is scored here).

Writes ../out/diagnosis.json. Every number in ROOT_CAUSE.md section 2 comes from this file.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E108 = HERE.parent
E107R = E108.parent / "E107_Twelve_Indicator_LightGBM" / "runner"
sys.path.insert(0, str(E107R))
import e107_lib as E  # noqa: E402
import e107_model as M  # noqa: E402

L, np, pd = E.L, E.np, E.pd
OUT = E108 / "out"
E107_OUT = E107R.parent / "out"


def ps_frame(d) -> pd.DataFrame:
    """Provincial food-price-pressure label PS for every complete CPI quarter in d (no SWS needed)."""
    th = L.e40_spec()
    F = L.quarter_F(d)
    HL = L.quarter_F(d, "all_items").rename(columns={"F": "HL"})
    q = F.merge(HL, on=["province_code", "q"])
    q["y"] = ((q["F"] > q["province_code"].map(th["food"])) |
              ((q["F"] - q["HL"]) > q["province_code"].map(th["gap"]))).astype(int)
    return q


def main() -> None:
    d, _ = E.data()
    out: dict = {}
    t43, ps, r = E.t43_frame(d), ps_frame(d), E.r_frame(d)
    j = ps.merge(t43[["province_code", "q", "y"]].rename(columns={"y": "t43"}), on=["province_code", "q"], how="left")
    j = j.merge(r[["q", "H"]], on="q", how="left")
    per_q = []
    for q, g in j.groupby("q"):
        per_q.append({"quarter": E.qs(int(q)), "hunger": None if pd.isna(g["H"].iloc[0]) else float(g["H"].iloc[0]),
                      "PS_high": int(g["y"].sum()), "T43_high": None if g["t43"].isna().all() else int(g["t43"].sum()),
                      "PS1_but_T43_0": int(((g["y"] == 1) & (g["t43"] == 0)).sum())})
    out["labels_by_quarter"] = per_q
    out["counts"] = {"T43_rows": len(t43), "T43_high": int(t43["y"].sum()), "PS_rows": len(ps), "PS_high": int(ps["y"].sum()),
                     "PS_quarters": int(ps["q"].nunique()), "R_quarters": len(r), "R_high": int(r["y"].sum()),
                     "PS1_T43_0_rows": int(((j["y"] == 1) & (j["t43"] == 0)).sum()),
                     "quarters_with_PS_but_no_T43": [E.qs(int(q)) for q in sorted(set(ps["q"]) - set(t43["q"]))]}

    # indicator variation and missingness
    X = E.feature_table(2)
    var = {}
    for c in E.COLUMNS:
        g = X.groupby("t")[c]
        var[c] = {"missing_share": float(X[c].isna().mean()),
                  "max_distinct_across_provinces_in_one_origin": int(g.nunique().max()),
                  "national_or_regional": bool(g.nunique().max() <= 1),
                  "n_distinct_values": int(X[c].nunique()),
                  "within_origin_sd_share": float(np.nanmean(g.std()) / X[c].std()) if X[c].std() else None}
    out["variation"] = var

    # E107 direct training sets: contradiction rows and period-marker separability, per lead and eval origin
    tr_stats = {}
    for k in E.LEADS:
        Xk = E.feature_table(k)
        rows = []
        for q in sorted(E.outcomes("T43")["q"].unique()):
            t = q - k
            if t < E.FIRST_ORIGIN:
                continue
            tr = M.train_rows(Xk, t, k, "T43")
            if not E.eligible(tr, "T43"):
                continue
            tps = tr.merge(ps[["province_code", "q", "y"]].rename(columns={"y": "ps"}), on=["province_code", "q"])
            hi_q = sorted(tr.loc[tr["y"] == 1, "q"].unique())
            nat = {}
            for c in ("E1", "E2", "C1", "H1"):
                v = tr[["q", c, "y"]].dropna()
                nat[c] = M.auc(v["y"], v[c]) if v["y"].nunique() == 2 else None
            rows.append({"target": E.qs(int(q)), "origin": E.qs(int(t)), "n_train": len(tr), "n_high": int(tr["y"].sum()),
                         "high_quarters": [E.qs(int(x)) for x in hi_q],
                         "PS1_labelled_LOW": int(((tps["ps"] == 1) & (tps["y"] == 0)).sum()),
                         "PS1_total": int(tps["ps"].sum()),
                         "A1_signal_auc_in_training": M.auc(tr.dropna(subset=["A1_food"])["y"],
                                                            tr.dropna(subset=["A1_food"])[["A1_food", "A1_gap"]].max(axis=1)),
                         "national_feature_auc_in_training": nat,
                         "N1_nonmissing_train_rows": int(tr["N1"].notna().sum())})
        tr_stats[str(k)] = rows
    out["e107_training_sets"] = tr_stats

    # E1 / E2 alignment spot check against the raw series
    lf = d.lfs[d.lfs["series"] == "ur"].set_index("ym")["value"]
    checks = []
    for oq in ("2023-Q3", "2024-Q4", "2025-Q2", "2026-Q2"):
        t = E.qi(oq)
        qm = lambda q: float(np.mean([lf[(q // 4) * 12 + (q % 4) * 3 + j] for j in range(3)]))  # noqa: E731
        checks.append({"origin": oq, "E1_feature": float(X.loc[X["t"] == t, "E1"].iloc[0]),
                       "ur_t-1_minus_ur_t-5_raw": qm(t - 1) - qm(t - 5)})
    out["e1_alignment_checks"] = checks

    # E107 evaluation behaviour: share HIGH predicted, false alarms, per lead (stored predictions)
    beh = {}
    for k in E.LEADS:
        f = E107_OUT / f"predictions_T43_lead{k}.csv"
        if f.exists() and f.stat().st_size > 5:
            p = pd.read_csv(f, dtype={"province_code": str})
            c = (p["p"] >= 0.5).astype(int)
            beh[str(k)] = {"rows": len(p), "high_rate_observed": float(p["y"].mean()), "high_rate_predicted": float(c.mean()),
                           "false_alarms": int(((c == 1) & (p["y"] == 0)).sum()), "missed_high": int(((c == 0) & (p["y"] == 1)).sum()),
                           "within_quarter_sd_of_p": float(p.groupby("q")["p"].std().mean())}
    out["e107_behaviour"] = beh
    E.write_json(OUT / "diagnosis.json", out)
    print(json.dumps({k: out[k] for k in ("counts", "e1_alignment_checks", "e107_behaviour")}, indent=1, default=str))
    for row in per_q:
        print(row)


if __name__ == "__main__":
    main()
