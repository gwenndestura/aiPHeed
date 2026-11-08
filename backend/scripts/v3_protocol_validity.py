"""
v3 protocol validity study (docs/aipheed/v3/PROTOCOL_VALIDITY.md). No model is fitted or changed and no frozen value is
altered: this computes, for pre-stated alternative scoring rules, the oracle bound, persistence and the v2 selected
model on the frozen S-U rows (DEVELOPMENT). Every rule's definition is fixed in RULES below, taken from the frozen
protocol's own information-only sensitivities (T1) or from earlier project documents (Chapter I, E110), never from
these results.

    python -I backend/scripts/v3_protocol_validity.py    -> docs/aipheed/v3/results/*
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import sws as T  # noqa: E402

V2 = REPO / "docs" / "aipheed" / "v2" / "results"
OUT = REPO / "docs" / "aipheed" / "v3" / "results"
Z90, Z95 = T.Z90, 1.959963984540054

def _q_pre_surge() -> float:
    """Sensitivity: the pooled local-level innovation variance estimated only from rounds published before 2024-01-01
    (the calm regime). The primary bound uses all data (includes the 2024 surge), as DIAGNOSIS Q1 did."""
    from datetime import date
    from app.forecasting.v2 import models as V
    return V.fit("LL", T.known_at(T.load_rounds(), date(2024, 1, 1))).q


Q_PRE = _q_pre_surge()
Q_TRUE = json.loads((V2 / "diagnosis_summary.json").read_text())["Q1_noise_and_oracle"]["local_level_fit_all_data"]["q"]

# Tolerance rules: (label, source, half-width as a function of the row)
TOL = {
    "a_frozen": ("1.645 x binomial SE at observed p (frozen T1)", lambda r: Z90 * r.se),
    "b_published_se": ("1.645 x SE implied by the published margin at p = 0.5 (frozen T1 information-only sensitivity)",
                       lambda r: Z90 * r.se_pub),
    "b_published_moe": ("published 95 % margin of the quarter, 1.96 x SE_pub (SWS's own reporting convention)",
                        lambda r: Z95 * r.se_pub),
    "a_x2_info": ("2 x frozen tolerance (frozen T1 information-only sensitivity)", lambda r: 2 * Z90 * r.se),
}
BANDS = {"c1_chapter1_11.3": (11.3, "HIGH if hunger > 11.3 % (Chapter I definition, served P0H4 hunger part)"),
         "c2_e110_b3_20": (20.0, "HIGH if hunger > 20 % (E110 B3, research-defined)")}


def rows() -> pd.DataFrame:
    P = pd.read_csv(V2 / "v2_outer_predictions.csv")
    O = pd.read_csv(V2 / "diag_su_rows_with_oracles.csv")[["area", "issue", "lead", "O_NOW", "se_latest"]]
    full = T.quarter_table(T.load_rounds())[["area", "qi", "se_pub"]].rename(columns={"qi": "tqi"})
    d = P.merge(O, on=["area", "issue", "lead"]).merge(full, on=["area", "tqi"])
    assert len(d) == len(P) == 152
    d["s_true"] = np.sqrt(d.h * Q_TRUE + d.se ** 2)
    d["s_pre"] = np.sqrt(d.h * Q_PRE + d.se ** 2)        # sd of target observation given the current true level
    return d


def tolerance_table(d: pd.DataFrame) -> pd.DataFrame:
    out = []
    for key, (src, f) in TOL.items():
        tol = d.apply(f, axis=1)
        for k, g in d.assign(tol_=tol).groupby("lead"):
            out.append({"option": key, "definition": src, "lead": int(k), "n": len(g), "median_tol_pp": g.tol_.median(),
                        "oracle_analytic": float(np.mean(2 * stats.norm.cdf(g.tol_ / g.s_true) - 1)),
                        "oracle_analytic_pre_surge_q": float(np.mean(2 * stats.norm.cdf(g.tol_ / g.s_pre) - 1)),
                        "oracle_empirical_O_NOW": float((np.abs(g.O_NOW - g.y) <= g.tol_).mean()),
                        "persistence": float((np.abs(g.f_PERSIST - g.y) <= g.tol_).mean()),
                        "v2_selected": float((np.abs(g.f_V2 - g.y) <= g.tol_).mean()),
                        "persistence_if_true_level_never_changed": float(np.mean(
                            2 * stats.norm.cdf(g.tol_ / np.sqrt(g.se ** 2 + g.se_latest ** 2)) - 1))})
    return pd.DataFrame(out)


def band_table(d: pd.DataFrame) -> pd.DataFrame:
    out = []
    for key, (c, src) in BANDS.items():
        for k, g in d.groupby("lead"):
            hi = g.y > c
            out.append({"option": key, "definition": src, "lead": int(k), "n": len(g), "share_high": float(hi.mean()),
                        "majority_class_hindsight": float(max(hi.mean(), 1 - hi.mean())),
                        "oracle_analytic": float(np.mean(stats.norm.cdf(np.abs(g.O_NOW - c) / g.s_true))),
                        "oracle_empirical_O_NOW": float(((g.O_NOW > c) == hi).mean()),
                        "persistence": float(((g.f_PERSIST > c) == hi).mean()),
                        "v2_selected": float(((g.f_V2 > c) == hi).mean())})
    return pd.DataFrame(out)


def direction_table(d: pd.DataFrame) -> pd.DataFrame:
    out = []
    for k, g in d.groupby("lead"):
        m = Z95 * g.se_pub                                   # E110 B4: rise above the latest reading by > the published margin
        rise = (g.y - g.y_latest) > m
        p_rise = 1 - stats.norm.cdf((g.y_latest + m - g.O_NOW) / g.s_true)
        out.append({"option": "d1_e110_b4_rise_gt_margin", "lead": int(k), "n": len(g), "share_rise": float(rise.mean()),
                    "oracle_analytic": float(np.mean(np.maximum(p_rise, 1 - p_rise))),
                    "oracle_empirical_O_NOW": float(((p_rise > 0.5) == rise).mean()),
                    "persistence": float((~rise).mean()), "v2_selected": float((~rise).mean()),
                    "balanced_accuracy_persistence": 0.5})
        up = g.y > g.y_latest
        out.append({"option": "d2_sign_up_down", "lead": int(k), "n": len(g), "share_rise": float(up.mean()),
                    "oracle_analytic": float(np.mean(stats.norm.cdf(np.abs(g.O_NOW - g.y_latest) / g.s_true))),
                    "oracle_empirical_O_NOW": float(((g.O_NOW > g.y_latest) == up).mean()),
                    "persistence": 0.5, "v2_selected": 0.5, "balanced_accuracy_persistence": 0.5,
                    "note": "persistence predicts no change: no direction (scored 0.5 by convention)"})
    return pd.DataFrame(out)


def nowcast_h1() -> dict:
    """Option (e): one quarter past the newest reading (P-REL-like, h = 1), all consecutive pairs 2021-2026."""
    full = T.quarter_table(T.load_rounds())
    r = []
    for a, s in full.groupby("area"):
        s = s.set_index("qi")
        for t in s.index:
            if t - 1 in s.index:
                r.append({"y": s.y[t], "y0": s.y[t - 1], "se": s.se[t], "se0": s.se[t - 1], "se_pub": s.se_pub[t]})
    r = pd.DataFrame(r)
    sd = np.sqrt(Q_TRUE + r.se ** 2)
    res = {"n_pairs": len(r)}
    for key, tol in (("a_frozen", Z90 * r.se), ("b_published_se", Z90 * r.se_pub), ("b_published_moe", Z95 * r.se_pub)):
        res[key] = {"oracle_analytic": float(np.mean(2 * stats.norm.cdf(tol / sd) - 1)),
                    "persistence": float((np.abs(r.y0 - r.y) <= tol).mean()),
                    "persistence_if_true_level_never_changed": float(np.mean(2 * stats.norm.cdf(tol / np.sqrt(r.se ** 2 + r.se0 ** 2)) - 1))}
    return res


def resolution(d: pd.DataFrame) -> pd.DataFrame:
    g = d[d.lead == 2]
    return pd.DataFrame([{
        "lead2_rows": len(g), "median_frozen_tol": float((Z90 * g.se).median()),
        "median_published_moe_quarter": float((Z95 * g.se_pub).median()),
        "median_ratio_frozen_tol_to_moe": float((Z90 * g.se / (Z95 * g.se_pub)).median()),
        "median_sd_difference_two_readings": float(np.sqrt(g.se ** 2 + g.se_latest ** 2).median()),
        "median_95pct_least_significant_difference": float((Z95 * np.sqrt(g.se ** 2 + g.se_latest ** 2)).median()),
        "share_rows_frozen_tol_below_lsd95": float((Z90 * g.se < Z95 * np.sqrt(g.se ** 2 + g.se_latest ** 2)).mean())}])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = rows()
    t, b, dr, res = tolerance_table(d), band_table(d), direction_table(d), resolution(d)
    for name, x in (("tolerance_options", t), ("band_options", b), ("direction_options", dr), ("resolution", res)):
        x.to_csv(OUT / f"v3_{name}.csv", index=False)
    now = nowcast_h1()
    (OUT / "v3_nowcast_h1.json").write_text(json.dumps(now, indent=1) + "\n", encoding="utf-8", newline="\n")
    pd.set_option("display.width", 250)
    for x in (t, b, dr, res):
        print(x.drop(columns=[c for c in ("definition", "note") if c in x]).round(3).to_string())
    print(json.dumps(now, indent=1))
    print("q_true", Q_TRUE, "q_pre_surge", Q_PRE)
    (OUT / "v3_q.json").write_text(json.dumps({"q_all_data": Q_TRUE, "q_pre_surge": Q_PRE}) + "\n",
                                   encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
