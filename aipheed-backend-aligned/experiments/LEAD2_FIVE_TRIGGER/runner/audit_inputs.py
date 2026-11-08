"""Input audit (no model scoring): the 12 indicators and 5 trigger groups in the served model's own stack - presence in
the LightGBM column list, missingness, variation, duplicates, cross-sectional information, time alignment of the dated
inputs, class balance of the target, and the served dashboard rows vs a re-fit of the evaluated model.

    python audit_inputs.py      # ../out/input_audit.json, ../out/input_audit.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T

F = T.F


def main():
    S = T.stack()
    meta = json.loads((T.DATA / "meta_l2.json").read_text())
    assert meta["cols_U2"] == T.U2, "column list differs from the served U2 list"
    E = F.eval_rows()
    origins = sorted(E["t"].unique())
    ev = S[S["t"].isin(origins) & S["lead"].isin([1, 2, 3, 4])]
    rows = []
    for c in T.U2:
        if c == "lead":
            continue
        grp = next((g for g, cs in {**T.GROUPS, **T.OTHER_INPUTS}.items() if c in cs), "?")
        o = S[S["lead"] == 1].drop_duplicates(["t", "province_code"])
        o = o[o["t"] >= 8085]
        within = o.groupby("t")[c].var(ddof=0).mean()
        total = o[c].var(ddof=0)
        miss_by_year = ev.assign(y=ev["t"] // 4).groupby("y")[c].apply(lambda s: round(float(s.isna().mean()), 2)).to_dict()
        rows.append({"column": c, "group": grp, "in_lightgbm": True, "missing_eval": float(ev[c].isna().mean()),
                     "missing_all_rows": float(S[c].isna().mean()), "missing_by_origin_year": json.dumps(miss_by_year),
                     "distinct_values_eval": int(ev[c].nunique()), "constant_within_origin_share": float(
                         (ev.groupby("t")[c].nunique(dropna=True) <= 1).mean()),
                     "between_province_share": float(within / total) if total and total > 0 else 0.0,
                     "rho_with_time": float(o[[c, "t"]].corr(method="spearman").iloc[0, 1]) if o[c].std() > 0 else float("nan")})
    A = pd.DataFrame(rows)
    A.to_csv(T.OUT / "input_audit.csv", index=False, lineterminator="\n", float_format="%.4g")
    res = {"columns_in_model": T.U2, "groups": T.GROUPS, "other_inputs": T.OTHER_INPUTS, "indicator_group": T.INDICATOR_GROUP,
           "duplicate_rows": int(S.duplicated(["t", "lead", "province_code"]).sum()),
           "provinces": sorted(S["province_code"].unique()), "origins": [F.qs(int(t)) for t in sorted(S["t"].unique())]}
    # time alignment of the dated inputs (every value must be published before the issue date)
    iss = pd.to_datetime(S["issue_date"])
    chk = {}
    m0 = S["psa_newest_month"].astype(str)
    chk["psa_month_before_issue_quarter"] = bool((pd.to_datetime(m0 + "-01") + pd.offsets.MonthBegin(1) <= iss).all())
    sp = pd.to_datetime(S["sws_newest_published"], errors="coerce")
    chk["sws_published_before_issue"] = bool((sp.dropna() < iss[sp.notna()]).all())
    nw = pd.to_datetime(S["news_latest_published"], errors="coerce")
    chk["news_published_before_issue"] = bool((nw.dropna() < iss[nw.notna()]).all())
    chk["news_rows_dated"] = int(nw.notna().sum())
    chk["target_after_origin"] = bool((S["target_q"] > S["t"]).all())
    res["time_alignment"] = chk
    # class balance of the target (binary T43c; no MODERATE class exists in the Chapter I definition)
    res["class_balance"] = {int(k): {"LOW": int((g["y"] == 0).sum()), "HIGH": int((g["y"] == 1).sum()),
                                     "quarters": int(g["q"].nunique()), "HIGH_quarters": int(g.loc[g["y"] == 1, "q"].nunique())}
                            for k, g in E.groupby("lead")}
    # dashboard rows vs the evaluated model: re-fit P0 at every origin and compare with the served rows.csv pi_price
    R = pd.read_csv(T.EXP.parents[1] / "backend" / "data" / "ch1_engine" / "rows.csv", dtype=str, keep_default_na=False)
    R["tq"] = R["quarter"].str[:4].astype(int) * 4 + R["quarter"].str[-1].astype(int) - 1
    R["t"] = R["tq"] - R["lead"].astype(int)
    P = T.run(T.U2, sorted(R["t"].unique()))
    J = R.merge(P.astype({"lead": str}), on=["t", "lead", "province_code"], how="left")
    d = (J["pi_price"].astype(float) - J["pi_P"]).abs()
    res["dashboard_vs_refit"] = {"rows": int(len(J)), "refit_missing": int(J["pi_P"].isna().sum()),
                                 "max_abs_diff_pi_price": float(d.max()),
                                 "probability_equals_hunger_x_price": float((J["probability"].astype(float) - J["pi_hunger"].astype(float) * J["pi_price"].astype(float)).abs().max())}
    T.OUT.joinpath("input_audit.json").write_text(json.dumps(res, indent=1, default=float))
    print(A.drop(columns=["missing_by_origin_year"]).to_string(index=False))
    print(json.dumps({k: v for k, v in res.items() if k not in ("columns_in_model", "groups", "indicator_group", "origins")}, indent=1, default=float))
    print(A[["column", "missing_by_origin_year"]].to_string(index=False))


if __name__ == "__main__":
    main()
