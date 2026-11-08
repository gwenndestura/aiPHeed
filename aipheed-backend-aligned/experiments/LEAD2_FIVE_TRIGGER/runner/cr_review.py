"""CR_REVIEW: adoption review of candidate CR (LEAD2_CPI_REFRESH) against B0 = P0H4-U on the identical scored rows.

Diagnostic only. It reads the committed scored rows (out/cpi_refresh_rows.csv) and refreshed CPI inputs
(data/cpi_refresh.csv). It refits nothing and selects nothing. The frozen 0.50 cut, R1-R7 and final.adoption_rule
are applied unchanged; the threshold sweep and the release-day sensitivity are reported, never used.

    python cr_review.py         # ../out/cr_review.json, ../out/cr_review_changes.csv
"""
from __future__ import annotations

import itertools
import json
from datetime import date

import numpy as np
import pandas as pd

import final as FN
import lt_lib as T

F, M, KEY = T.F, T.M, T.KEY
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
# candidates already scored against P0H4-U on these Lead-2 rows (thesis package sections 13-19)
EARLIER = {"LEAD2_IMPROVE": ["B1", "B2", "B3", "B4"], "LEAD2_FINAL": ["K1"], "LEAD2_SUBGROUP": ["K2"],
           "LEAD2_TUNING": ["N0", "N1", "N2", "G0"], "LEAD2_CPI_REFRESH": ["CR"]}


def calls(g, c):
    return (g[f"{c}_p"] >= .5).astype(int)


def changes(g) -> pd.DataFrame:
    b, k = calls(g, "B0"), calls(g, "CR")
    x = g[b != k].copy()
    x["change"] = np.select([(x["y"] == 1) & (k[b != k] == 1), (x["y"] == 1), (k[b != k] == 1)],
                            ["new hit", "lost hit", "new false alarm"], "removed false alarm")
    x["province"] = x["province_code"].map(NAMES)
    x["target_quarter"] = x["q"].map(lambda q: F.qs(int(q)))
    x["price_moved"] = np.where(x["CR_price"] > x["B0_price"], "up", "down")
    return x


def quarter_table(g) -> pd.DataFrame:
    g = g.assign(bs_B0=(g["B0_p"] - g["y"]) ** 2, bs_CR=(g["CR_p"] - g["y"]) ** 2,
                 ok_B0=(calls(g, "B0") == g["y"]).astype(int), ok_CR=(calls(g, "CR") == g["y"]).astype(int))
    q = g.groupby("q").agg(high=("y", "sum"), bs_B0=("bs_B0", "mean"), bs_CR=("bs_CR", "mean"),
                           ok_B0=("ok_B0", "sum"), ok_CR=("ok_CR", "sum")).reset_index()
    q["d_brier"] = q["bs_CR"] - q["bs_B0"]
    q["quarter"] = q["q"].map(lambda v: F.qs(int(v)))
    q["block"] = np.where(q["q"] <= F.DEV_LAST, "DEV", "later")
    return q


def sign_flip(d: np.ndarray) -> float:
    """Exact one-sided paired permutation p (quarter means, H0: symmetric about 0) for mean(d) < 0."""
    obs = d.mean()
    tot = [np.mean(d * np.array(s)) for s in itertools.product((1, -1), repeat=len(d))]
    return float(np.mean(np.array(tot) <= obs + 1e-15))


def icc(g, col) -> float:
    """One-way ANOVA intraclass correlation of a row quantity within target quarters."""
    grp = [v.to_numpy(float) for _, v in g.groupby("q")[col]]
    n = np.mean([len(v) for v in grp])
    grand = g[col].mean()
    msb = sum(len(v) * (v.mean() - grand) ** 2 for v in grp) / (len(grp) - 1)
    msw = sum(((v - v.mean()) ** 2).sum() for v in grp) / (len(g) - len(grp))
    return float((msb - msw) / (msb + (n - 1) * msw)) if msb + (n - 1) * msw > 0 else float("nan")


def r6_margin(tp, fp, fn) -> dict:
    """Fewest single-row changes that break R6 (precision and recall >= 0.60)."""
    lose_tp = next(i for i in range(tp + 1) if (tp - i) / max(tp - i + fp, 1) < .6 or (tp - i) / (tp + fn) < .6)
    add_fp = next(i for i in range(100) if tp / (tp + fp + i) < .6)
    return {"lost_hits_to_fail": int(lose_tp), "extra_false_alarms_to_fail": int(add_fp)}


def release_rows(R: pd.DataFrame, ev: pd.DataFrame) -> dict:
    """CPI availability: for each scored Lead-2+ row, the claimed release date of its newest refreshed month (day 10
    of the next month) and the margin to the issue date; and how many rows lose a month under later release days."""
    R = R.merge(ev[KEY], on=KEY, how="inner")
    rel = [date((m + 1) // 12, (m + 1) % 12 + 1, 10) for m in R["m0r"].astype(int)]
    R["claimed_release"] = rel
    R["margin_days"] = [(date.fromisoformat(i) - r).days for i, r in zip(R["issue_B"], rel)]
    sens = {}
    for day in (5, 10, 12, 15, 20, 25, 28):
        def newest(iss, m0):
            d, m = date.fromisoformat(iss), m0
            while date((m + 2) // 12, (m + 2) % 12 + 1, day) < d and m < m0 + 2:
                m += 1
            return m
        nm = np.array([newest(i, int(m)) for i, m in zip(R["issue_B"], R["m0"])])
        sens[day] = {"rows_with_fewer_months_than_day10": int((nm < R["m0r"].to_numpy()).sum()),
                     "rows_with_more": int((nm > R["m0r"].to_numpy()).sum())}
    lead2 = R[R["lead"] == 2]
    return {"rows": int(len(R)), "extra_months": R["m0r"].sub(R["m0"]).value_counts().sort_index().to_dict(),
            "min_margin_days": int(R["margin_days"].min()), "margin_days_quantiles": R["margin_days"].quantile([0, .1, .5]).to_dict(),
            "lead2_issue_dates": sorted(lead2["issue_B"].unique().tolist()),
            "lead2_rows_margin_le_10_days": int((lead2["margin_days"] <= 10).sum()),
            "release_day_sensitivity": sens}


def main():
    E = pd.read_csv(T.OUT / "cpi_refresh_rows.csv", dtype={"province_code": str})
    res = json.loads((T.OUT / "cpi_refresh.json").read_text())
    g = E[E["lead"] == 2].copy()
    out = {"source": "out/cpi_refresh_rows.csv (committed 80bbe98)", "rows_lead2": int(len(g)),
           "quarters_lead2": int(g["q"].nunique())}

    # 1. the changed calls
    ch = changes(g)
    keep = ["province", "target_quarter", "change", "y", "B0_p", "CR_p", "pi_H_AB", "B0_price", "CR_price", "price", "price_moved"]
    ch[keep].to_csv(T.OUT / "cr_review_changes.csv", index=False, lineterminator="\n", float_format="%.4f")
    out["changed_calls"] = ch[keep].round(3).to_dict("records")
    out["change_counts"] = ch["change"].value_counts().to_dict()
    out["changed_quarters"] = int(ch["q"].nunique())
    lead = lambda c: {int(k): v for k, v in res["cands"][c]["leads"].items()}  # noqa: E731
    out["adoption_rule_recomputed"] = FN.adoption_rule(lead("B0"), lead("CR"))

    # 2. chronological consistency and 3. Brier robustness vs P0H4-U
    qt = quarter_table(g)
    out["by_quarter"] = qt[["quarter", "block", "high", "ok_B0", "ok_CR", "bs_B0", "bs_CR", "d_brier"]].round(4).to_dict("records")
    d = qt["d_brier"].to_numpy()
    tot = d.sum()
    out["brier_vs_B0"] = {
        "row_mean_diff": float(((g["CR_p"] - g["y"]) ** 2 - (g["B0_p"] - g["y"]) ** 2).mean()),
        "block_bootstrap_committed": res["cands"]["CR"]["leads"]["2"]["vs_B0"],
        "quarters_better_worse_tied": [int((d < -1e-9).sum()), int((d > 1e-9).sum()), int((abs(d) <= 1e-9).sum())],
        "sign_test_p_one_sided": float(sum(__import__("math").comb(int((abs(d) > 1e-9).sum()), i)
                                           for i in range(int((d < -1e-9).sum()), int((abs(d) > 1e-9).sum()) + 1))
                                       / 2 ** int((abs(d) > 1e-9).sum())),
        "exact_sign_flip_p_one_sided": sign_flip(d),
        "share_of_gain_from_top_quarter": float(d.min() / tot) if tot < 0 else float("nan"),
        "top_quarter": qt.loc[qt["d_brier"].idxmin(), "quarter"],
        "leave_one_quarter_out_diff": {r.quarter: float((tot - r.d_brier) / (len(d) - 1)) for r in qt.itertuples()},
        "by_block": {b: float(v["d_brier"].mean()) for b, v in qt.groupby("block")},
        "by_third": [float(np.mean(x)) for x in np.array_split(d, 3)],
    }
    lo = out["brier_vs_B0"]["leave_one_quarter_out_diff"]
    out["brier_vs_B0"]["loqo_range"] = [min(lo.values()), max(lo.values())]
    out["brier_vs_B0"]["multiplicity"] = {"candidates_scored_on_these_rows": EARLIER,
                                          "n_candidate_comparisons": sum(map(len, EARLIER.values())),
                                          "bonferroni_p_committed": min(1.0, res["cands"]["CR"]["leads"]["2"]["vs_B0"]["p_less"]
                                                                       * sum(map(len, EARLIER.values())))}

    # 5. dependence on the cut, a single quarter, a single row
    sweep = {}
    for cut in np.round(np.arange(.40, .601, .025), 3):
        row = {}
        for c in ("B0", "CR"):
            m = M.cls(g["y"], g[f"{c}_p"] - (cut - .5))       # M.cls cuts at 0.50; shift p to cut at `cut`
            row[c] = {k: round(float(m[k]), 3) for k in ("accuracy", "balanced_accuracy", "precision", "recall")}
            row[c]["R6"] = bool(m["precision"] >= .6 and m["recall"] >= .6)
        sweep[float(cut)] = row
    out["threshold_sweep_diagnostic"] = sweep
    loqo = {}
    for q in sorted(g["q"].unique()):
        h = g[g["q"] != q]
        loqo[F.qs(int(q))] = {c: F.evaluate(h, f"{c}_p", "PERS_AB")["failed"] for c in ("B0", "CR")}
    out["leave_one_quarter_out_R1_R7_failed"] = loqo
    out["cr_lead2_all_R_pass_in_loqo"] = int(sum(not v["CR"] for v in loqo.values()))
    m = res["cands"]["CR"]["leads"]["2"]["metrics"]
    out["r6_fragility_CR"] = r6_margin(int(m["tp"]), int(m["fp"]), int(m["fn"]))
    mb = res["cands"]["B0"]["leads"]["2"]["metrics"]
    out["r6_fragility_B0"] = {"extra_hits_needed": next(i for i in range(20) if (mb["tp"] + i) / (mb["tp"] + mb["fn"]) >= .6)}
    out["training_config_choice"] = {"CR_cfg_by_origin": E[E["lead"] == 2].groupby("t")["CR_cfg"].first().astype(int).to_dict()}

    # 6. effective observations
    g["d_row"] = (g["CR_p"] - g["y"]) ** 2 - (g["B0_p"] - g["y"]) ** 2
    rho = icc(g, "d_row")
    n_eff = len(g) / (1 + (5 - 1) * rho) if rho == rho else float("nan")
    sd = float(np.std(d, ddof=1))
    need = ((1.645 + 0.842) * sd / abs(d.mean())) ** 2 if d.mean() else float("inf")
    out["effective_n"] = {"rows": int(len(g)), "target_quarters": int(len(d)),
                          "quarters_with_high": int((qt["high"] > 0).sum()), "high_rows": int(g["y"].sum()),
                          "icc_brier_diff_within_quarter": rho, "design_effect_n_eff": n_eff,
                          "quarter_sd_of_brier_diff": sd,
                          "quarters_needed_80pct_power_one_sided_05": float(need),
                          "hunger_part_identical_within_quarter": bool(g.groupby("q")["pi_H_AB"].nunique().max() == 1)}

    # 4. CPI availability at the claimed issue dates
    R = pd.read_csv(T.DATA / "cpi_refresh.csv", dtype={"province_code": str})
    out["cpi_availability"] = release_rows(R, E[E["lead"] >= 2])

    # Leads 3-4 (the refresh also changes them)
    out["other_leads"] = {k: {c: {x: res["cands"][c]["leads"][k]["metrics"][x] for x in ("accuracy", "brier")}
                              | {"vs_B0": res["cands"][c]["leads"][k]["vs_B0"]["diff"]} for c in ("B0", "CR")}
                          for k in ("1", "3", "4")}
    (T.OUT / "cr_review.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: out[k] for k in ("change_counts", "changed_quarters", "brier_vs_B0", "cr_lead2_all_R_pass_in_loqo",
                                          "r6_fragility_CR", "effective_n", "cpi_availability", "other_leads")}, indent=1, default=str))
    print(ch[keep].round(3).to_string(index=False))
    print(qt.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
