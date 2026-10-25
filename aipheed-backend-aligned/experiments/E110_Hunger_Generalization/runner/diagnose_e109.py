"""E110 step 1: quantitative diagnosis of E109 from its data and stored predictions (no new model is scored).
Writes ../out/diagnosis.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E110 = HERE.parent
E109R = E110.parent / "E109_Hunger_Forecasting" / "runner"
sys.path.insert(0, str(E109R))
import e109_lib as H  # noqa: E402

E, np, pd = H.E, H.np, H.pd
E109_OUT = E109R.parent / "out"


def main() -> None:
    out = {}
    qs_ = H.outcome_quarters()
    vals = {q: H.outcome(q) for q in qs_}
    # 1. publication lag: how old is the latest reading at each issue date?
    ages = {}
    for k in H.LEADS:
        p = pd.read_csv(E109_OUT / f"predictions_lead{k}.csv")
        ages[str(k)] = {"gap_target_minus_latest_reading": p.apply(lambda r: int(r["q"]) - E.qi(r["h_last_quarter"]), axis=1)
                        .value_counts().sort_index().to_dict()}
    out["data_age_at_issue"] = ages
    pub = H.rounds()[H.rounds()["in_primary_series"]].copy()
    pub["lag_days_after_quarter_end"] = [
        (pd.Timestamp(p[:10]) - (pd.Timestamp(year=q // 4, month=(q % 4) * 3 + 3, day=1) + pd.offsets.MonthEnd(0))).days
        for p, q in zip(pub["published"], pub["q"])]
    out["publication_lag_days"] = {"median": float(pub["lag_days_after_quarter_end"].median()),
                                   "min": int(pub["lag_days_after_quarter_end"].min()),
                                   "max": int(pub["lag_days_after_quarter_end"].max())}
    # 2. signal vs survey noise in consecutive known quarters
    seq = [(q, vals[q]) for q in qs_]
    d = [(b[1] - a[1]) / np.sqrt(b[0] - a[0]) for a, b in zip(seq, seq[1:])]
    dd = np.array([b[1] - a[1] for a, b in zip(seq, seq[1:]) if b[0] - a[0] == 1])
    r4, r6 = (4 / 1.96) ** 2, (6 / 1.96) ** 2
    out["changes"] = {"n_consecutive": int(len(dd)), "sd_change": float(dd.std(ddof=1)),
                      "mean_abs_change": float(np.abs(dd).mean()),
                      "lag1_autocorr_of_changes": float(np.corrcoef(dd[:-1], dd[1:])[0, 1]),
                      "noise_sd_of_a_change_if_moe4": float(np.sqrt(2 * r4)), "noise_sd_of_a_change_if_moe6": float(np.sqrt(2 * r6)),
                      "share_of_change_variance_that_is_noise_moe4": float(2 * r4 / dd.var(ddof=1)),
                      "share_of_change_variance_that_is_noise_moe6": float(2 * r6 / dd.var(ddof=1)),
                      "per_quarter_sd_scaled": float(np.std(d, ddof=1))}
    # 3. regime before / after the 2025 respondent-base change
    pre = [v for q, v in seq if q <= E.qi("2024-Q4")]
    post = [v for q, v in seq if q >= E.qi("2025-Q2")]
    p23 = [v for q, v in seq if q <= E.qi("2023-Q3")]
    out["regimes"] = {"2021Q2_2023Q3": {"n": len(p23), "mean": float(np.mean(p23)), "sd": float(np.std(p23, ddof=1))},
                      "2021Q2_2024Q4_household_heads": {"n": len(pre), "mean": float(np.mean(pre)), "sd": float(np.std(pre, ddof=1))},
                      "2025Q2_2026Q3_adults": {"n": len(post), "mean": float(np.mean(post)), "sd": float(np.std(post, ddof=1)),
                                               "values": post}}
    # 4. E109 errors by quarter: where does the RW advantage come from?
    p1 = pd.read_csv(E109_OUT / "predictions_lead1.csv")
    out["e109_lead1_abs_errors"] = [{"quarter": r.quarter, "y": r.y, "RW": abs(r.RW - r.y), "LGBM": abs(r.LGBM - r.y),
                                     "MA2": abs(r.MA2 - r.y)} for r in p1.itertuples()]
    # 5. training size per origin
    out["e109_training_pairs"] = {str(k): pd.read_csv(E109_OUT / f"predictions_lead{k}.csv")["n_pairs"].tolist()
                                  for k in H.LEADS}
    # 6. descriptive association of each family's regional value with the next change (full sample; NOT a test)
    assoc = {}
    for k in (1, 2):
        rows = []
        X = H.regional_features(k)
        for t in X.index:
            hl = H.h_last(int(t))
            y = vals.get(int(t) + k)
            if hl is None or y is None:
                continue
            rows.append({**X.loc[t].to_dict(), "dy": y - hl[1]})
        df = pd.DataFrame(rows)
        assoc[str(k)] = {"n": len(df), **{c: (float(df[[c, "dy"]].dropna().corr().iloc[0, 1])
                                              if df[c].notna().sum() >= 6 and df[c].nunique() > 1 else None)
                                          for c in E.COLUMNS}}
    out["descriptive_corr_with_next_change"] = assoc
    H.write_json(E110 / "out" / "diagnosis.json", out)
    print(json.dumps({k: out[k] for k in ("data_age_at_issue", "publication_lag_days", "changes", "regimes")}, indent=1))
    print(json.dumps(out["descriptive_corr_with_next_change"], indent=0)[:1500])


if __name__ == "__main__":
    main()
