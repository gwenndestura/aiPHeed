"""Round-3 diagnostics (no model is fitted): (1) the dates behind every Lead-2 target - SWS fieldwork, recall window,
publication, price months and their release, issue dates - and a recall-aligned price-label sensitivity; (2) the
borderline errors against rounding and sampling resolution; (3) the uncertainty of Lead-2 precision and recall;
(4) the V1 (poverty) construction.

    python diag_v3.py           # ../out/diag_v3.json, ../out/target_timing.csv
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import beta, norm

import lt_lib as T

sys.path.insert(0, str(T.EXP / "FORECAST_RESEARCH_II" / "runner"))
import ii_lib as II  # noqa: E402

F = T.F


def cp(k, n, a=0.05):
    lo = beta.ppf(a / 2, k, n - k + 1) if k > 0 else 0.0
    hi = beta.ppf(1 - a / 2, k + 1, n - k) if k < n else 1.0
    return [float(lo), float(hi)]


def main():
    E = pd.read_csv(T.OUT / "improve_rows.csv", dtype={"province_code": str})
    g2 = E[E["lead"] == 2].copy()
    r = F.rounds()
    bl = r[r["area"] == "BL"].copy()
    bl["fw_end"] = pd.to_datetime(bl["fw_end"])
    y = II.yoy_published()
    yt = y.set_index(["province_code", "commodity", "ym"])["yoy_pct"]
    food = [c for c in y["commodity"].unique() if str(c).lower().startswith("food")][0]
    allc = [c for c in y["commodity"].unique() if c != food][0]
    rows = []
    for q in sorted(g2["q"].unique()):
        qs_ = pd.Timestamp(year=q // 4, month=(q % 4) * 3 + 1, day=1)
        qe = qs_ + pd.offsets.QuarterEnd(0)
        rr = bl[bl["q"] == q]
        months, ov = set(), []
        for fe in rr["fw_end"]:
            w0 = fe - pd.Timedelta(days=91)
            ov.append(max(0, (min(fe, qe) - max(w0, qs_)).days) / 91)
            days = {}
            for d in pd.date_range(w0, fe, freq="D"):
                days[(d.year, d.month)] = days.get((d.year, d.month), 0) + 1
            months |= {ym for ym, _ in sorted(days.items(), key=lambda kv: -kv[1])[:3]}
        ym_list = sorted(y_ * 12 + m - 1 for y_, m in months)
        rows.append({"target": F.qs(int(q)), "sws_fieldwork_end": ", ".join(str(d.date()) for d in rr["fw_end"]),
                     "sws_recall_months": ", ".join(f"{m // 12}-{m % 12 + 1:02d}" for m in ym_list),
                     "recall_overlap_with_price_quarter": float(np.mean(ov)),
                     "sws_published": ", ".join(rr["published"]), "price_months": f"{qs_.strftime('%Y-%m')}..{qe.strftime('%Y-%m')}",
                     "price_last_month_released_approx": (qe + pd.offsets.MonthBegin(1) + pd.Timedelta(days=6)).date().isoformat(),
                     "lead1_issue": F.issue(int(q) - 1, "A"), "lead2_issue_B": F.issue(int(q) - 2, "B"),
                     "label_complete": max(max(rr["published"]), (qe + pd.offsets.MonthBegin(1) + pd.Timedelta(days=6)).date().isoformat()),
                     "_ym": ym_list})
    TT = pd.DataFrame(rows)
    # recall-aligned price label (sensitivity only: never used for training, selection or the criteria)
    flips, err_fixed = [], 0
    g2["err"] = (g2["B0_p"] >= .5).astype(int) != g2["y"]
    for _, t in TT.iterrows():
        q = int(t["target"][:4]) * 4 + int(t["target"][-1]) - 1
        for p in T.PROVS if hasattr(T, "PROVS") else II.PROVS:
            fm = [yt.get((p, food, m), np.nan) for m in t["_ym"]]
            am = [yt.get((p, allc, m), np.nan) for m in t["_ym"]]
            if any(np.isnan(fm + am)):
                continue
            Fr, Ar = float(np.mean(fm)), float(np.mean(am))
            pr = int((Fr - F.TH_F[p] > 0) or (Fr - Ar - F.TH_G[p] > 0))
            row = g2[(g2["q"] == q) & (g2["province_code"] == p)]
            if not len(row):
                continue
            row = row.iloc[0]
            y_ra = int(pr and row["hunger"])
            if y_ra != row["y"]:
                flips.append({"target": t["target"], "province": p, "T43c": int(row["y"]), "recall_aligned": y_ra,
                              "B0_class": int(row["B0_p"] >= .5)})
            if row["err"] and int(row["B0_p"] >= .5) == y_ra:
                err_fixed += 1
    out = {"timing": TT.drop(columns="_ym").to_dict("records"),
           "recall_overlap_mean": float(TT["recall_overlap_with_price_quarter"].mean()),
           "recall_overlap_min": float(TT["recall_overlap_with_price_quarter"].min()),
           "recall_aligned_sensitivity": {"lead2_rows": int(len(g2)), "labels_that_flip": flips, "n_flips": len(flips),
                                          "lead2_errors_that_would_be_correct": err_fixed,
                                          "note": "sensitivity only; T43c is unchanged"}}
    TT.drop(columns="_ym").to_csv(T.OUT / "target_timing.csv", index=False, lineterminator="\n", float_format="%.3g")
    # borderline errors vs resolution
    bt = pd.read_csv(T.OUT / "error_patterns.csv")
    bt = bt[bt["model"] == "B0"].copy()
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "label_noise_by_quarter.csv")
    se = dict(zip(lab["quarter"], lab["se_q"]))
    Hq = dict(zip(lab["quarter"], lab["H"]))
    bt["H"] = bt["target"].map(Hq)
    bt["hunger_se"] = bt["target"].map(se)
    bt["p_true_hunger_side_differs"] = [float(norm.cdf(-abs(h - 11.3) / s)) for h, s in zip(bt["H"], bt["hunger_se"])]
    bt["within_cpi_rounding(0.1)"] = bt["realised"].abs() <= 0.1
    out["borderline"] = bt[["province", "target", "type", "pattern", "realised", "within_cpi_rounding(0.1)", "H",
                            "p_true_hunger_side_differs"]].to_dict("records")
    out["borderline_summary"] = {"errors": int(len(bt)), "price_margin_lt_0.5": int((bt["realised"].abs() < .5).sum()),
                                 "price_margin_le_0.1": int((bt["realised"].abs() <= .1).sum()),
                                 "hunger_side_uncertain_ge_0.2": int((bt["p_true_hunger_side_differs"] >= .2).sum())}
    # precision / recall uncertainty (Lead 2, B0)
    tp = int(((g2["B0_p"] >= .5) & (g2["y"] == 1)).sum())
    fn = int(((g2["B0_p"] < .5) & (g2["y"] == 1)).sum())
    fp = int(((g2["B0_p"] >= .5) & (g2["y"] == 0)).sum())
    uq = np.array(sorted(g2["q"].unique()))
    rng = np.random.default_rng(2031)
    rb, pb = [], []
    for _ in range(4000):
        s = pd.concat([g2[g2["q"] == u] for u in rng.choice(uq, len(uq))])
        c = s["B0_p"] >= .5
        if s["y"].sum():
            rb.append(((c) & (s["y"] == 1)).sum() / s["y"].sum())
        if c.sum():
            pb.append(((c) & (s["y"] == 1)).sum() / c.sum())
    out["uncertainty"] = {"recall": tp / (tp + fn), "recall_cp95": cp(tp, tp + fn), "recall_block90": [float(np.quantile(rb, .05)), float(np.quantile(rb, .95))],
                          "P(block recall >= 0.60)": float(np.mean(np.array(rb) >= .6)),
                          "precision": tp / (tp + fp), "precision_cp95": cp(tp, tp + fp), "precision_block90": [float(np.quantile(pb, .05)), float(np.quantile(pb, .95))],
                          "high_cases": tp + fn, "high_quarters": int(g2.loc[g2["y"] == 1, "q"].nunique()), "quarters": int(len(uq)),
                          "earliest_eligible_origin": F.qs(int(E["t"].min())),
                          "why_not_longer": ("Origins before 2022-Q4 are not eligible under the frozen training rule (>= 6 known quarters, "
                                             ">= 5 HIGH and >= 5 LOW price labels) because the study window starts in 2021-Q1; pre-2021 data "
                                             "are outside the study window. SWS has no regular round in 2021-Q1, 2022-Q1, 2025-Q1.")}
    T.OUT.joinpath("diag_v3.json").write_text(json.dumps(out, indent=1, default=float))
    pd.set_option("display.width", 250)
    print(TT.drop(columns="_ym")[["target", "sws_fieldwork_end", "sws_recall_months", "recall_overlap_with_price_quarter", "sws_published",
                                  "lead2_issue_B", "label_complete"]].to_string(index=False))
    print("overlap mean/min", out["recall_overlap_mean"], out["recall_overlap_min"])
    print("recall-aligned flips", out["recall_aligned_sensitivity"]["n_flips"], out["recall_aligned_sensitivity"]["labels_that_flip"],
          "errors fixed", err_fixed)
    print(pd.DataFrame(out["borderline"]).to_string(index=False))
    print(out["borderline_summary"])
    print(out["uncertainty"])


if __name__ == "__main__":
    main()
