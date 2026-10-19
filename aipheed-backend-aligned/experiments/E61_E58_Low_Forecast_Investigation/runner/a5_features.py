"""E61 A5: feature and data-timing audit of the E56/E58 inputs at the 10 rolling origins and the 2027-Q1 origin.

Per feature (price part, "all" set): share missing, share exactly zero, distinct values, latest value at 2027-Q1, and
the E59 count of origins whose selected trees split on its group. Also the 2027-Q1 hunger-component terms (which
inputs move the predicted hunger rate), and the release-lag table from E59 (`timing_by_origin.csv`).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E61_E58_Low_Forecast_Investigation/runner/a5_features.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e61_lib as X  # noqa: E402

np, pd, L, F, E = X.np, X.pd, X.L, X.F, X.E


def main():
    d, Xf, B = E.load()
    cols = F.feature_cols("all")
    frames = []
    for t in list(range(L.qi("2023-Q4"), L.qi("2026-Q1") + 1)) + [L.qi("2026-Q3")]:
        _, te = F.frame(d, Xf, B, t, None)
        frames.append(te.assign(origin=L.qs(t)))
    A = pd.concat(frames, ignore_index=True)
    hist, now = A[A["origin"] != "2026-Q3"], A[A["origin"] == "2026-Q3"]
    use = pd.read_csv(X.EXP / "E59_E58_Validation_Audit" / "out" / "trigger_use_by_origin.csv")
    used = use.groupby("group")["inputs_used_in_splits"].apply(lambda s: int((s > 0).sum())).to_dict()
    rows = []
    for c in cols:
        g = E.group_of(c)
        rows.append({"feature": c, "group": "news" if c.startswith("news_") else g,
                     "missing_share_backtest": float(hist[c].isna().mean()), "zero_share_backtest": float((hist[c] == 0).mean()),
                     "distinct_backtest": int(hist[c].nunique()),
                     "missing_2027Q1": int(now[c].isna().sum()), "zero_2027Q1": int((now[c] == 0).sum()),
                     "values_2027Q1": [None if pd.isna(v) else round(float(v), 3) for v in now[c]],
                     "origins_group_used_in_trees_E59": used.get("news_volume" if c == "news_n" else g)})
    T = pd.DataFrame(rows)
    X.write_csv(T.astype({"values_2027Q1": str}), X.TABLES / "a5_feature_audit.csv")
    hun = json.loads((X.ART / "hunger.json").read_text())
    terms = {k: hun["z_row"][k] * hun["coef"][k] for k in hun["coef"]}
    from scipy.stats import norm
    no_news = hun["H_hat"] - terms["news_n"]
    no_missing = hun["H_hat"] - sum(v for k, v in terms.items() if k.endswith("__missing"))
    timing = pd.read_csv(X.EXP / "E59_E58_Validation_Audit" / "out" / "timing_by_origin.csv")
    X.dump({"features": rows, "hunger_component_2027Q1": {
        "H_base_latest_posted": hun["H_base"], "intercept": hun["intercept"], "H_hat": hun["H_hat"], "rmse": hun["rmse"],
        "terms_points": {k: round(v, 3) for k, v in sorted(terms.items(), key=lambda kv: -abs(kv[1]))},
        "p_hunger": float(1 - norm.cdf((11.3 - hun["H_hat"]) / hun["rmse"])),
        "H_hat_without_news_volume_term": no_news,
        "p_hunger_without_news_volume_term": float(1 - norm.cdf((11.3 - no_news) / hun["rmse"])),
        "H_hat_without_missing_indicators": no_missing},
        "release_timing_E59": timing.to_dict("records")}, X.OUT / "a5_features.json")
    print(T.drop(columns=["values_2027Q1"]).round(2).to_string())
    print(now[["province_code", "F_now", "gap_now", "D_now", "rice_whsl_yoy", "remit_usd_yoy", "news_market", "news_climate", "news_n"]].to_string())
    print("hunger terms", {k: round(v, 2) for k, v in sorted(terms.items(), key=lambda kv: -abs(kv[1]))[:8]})
    print("H_hat", round(hun["H_hat"], 2), "without news_n", round(no_news, 2))


if __name__ == "__main__":
    main()
