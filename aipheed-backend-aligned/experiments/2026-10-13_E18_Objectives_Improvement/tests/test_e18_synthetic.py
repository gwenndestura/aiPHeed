"""E18 synthetic tests (no project data)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e18_lib as L  # noqa: E402
import guard  # noqa: E402

PROV = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]


def test_extend_components_quarterly_mean_and_zero_sum():
    rows = [{"province_code": p, "reference_month": f"2026-0{m}", "food_cpi_yoy_pct_raw": float(i + m)}
            for i, p in enumerate(PROV) for m in range(1, 7)]
    cpi = pd.DataFrame(rows)
    sws = pd.DataFrame({"quarter": ["2026-Q1", "2026-Q2"], "pct_total_hunger": [20.0, 15.0]})
    base = pd.DataFrame(columns=["province_code", "quarter", "F", "mean5", "D", "H", "S1"])
    x = L.extend_components(base, cpi, sws)
    q1 = x[x["quarter"] == "2026-Q1"].set_index("province_code")
    assert q1.loc[PROV[0], "F"] == pytest.approx(2.0)          # mean of 1, 2, 3
    assert abs(q1["D"].sum()) < 1e-12
    assert (q1["S1"] - (20 + 2 * q1["D"])).abs().max() < 1e-12


def test_incomplete_provinces_give_no_D():
    rows = [{"province_code": p, "reference_month": "2026-01", "food_cpi_yoy_pct_raw": 1.0} for p in PROV[:4]]
    x = L.extend_components(pd.DataFrame(columns=["province_code", "quarter", "F", "mean5", "D", "H", "S1"]),
                            pd.DataFrame(rows), pd.DataFrame({"quarter": ["2026-Q1"], "pct_total_hunger": [20.0]}))
    assert x["D"].isna().all() and x["S1"].isna().all()


def test_c8_c9():
    hs = pd.Series([10.0, 12.0, 14.0, 16.0, 18.0], index=[1, 2, 3, 4, 5])
    assert L.c8_recent_mean(hs, 7, 2) == pytest.approx(15.0)
    assert L.c9_ewma(hs, 6, 1) == pytest.approx(16.125)
    assert L.c9_ewma(hs, 3, 1) == pytest.approx(11.0)       # uses only quarters <= 2


def test_selection_rule_requires_all_conditions():
    perq = pd.DataFrame({"P_persistence": [0.8, 0.8, 0.8, 0.8, 0.8], "N1_structural_rule": [1.0, 1.0, 1.0, 1.0, 1.0]},
                        index=["q1", "q2", "q3", "q4", "q5"])
    ov = {"P_persistence": {"accuracy": 0.8, "balanced_accuracy": 0.6},
          "N1_structural_rule": {"accuracy": 1.0, "balanced_accuracy": 0.9}}
    assert L.select(perq, ov, "N1_structural_rule")["passes"]
    perq["N1_structural_rule"] = [1.0, 0.6, 0.6, 1.0, 0.6]
    ov["N1_structural_rule"]["accuracy"] = 0.76
    assert not L.select(perq, ov, "N1_structural_rule")["passes"]


@pytest.mark.parametrize("path,want", [
    (guard.COLL / "provincial_food_cpi_yoy_2026H1_raw.csv", "allow"),
    (guard.PROD_SWS, "allow"),
    (guard.PROC / "cpi_full.parquet", "deny"),
    (guard.ROOT / "backend" / "data" / "processed" / "psa_indicators.parquet", "deny"),
    (guard.AL / "data" / "processed" / "fssi_quarterly.parquet", "deny"),
    (guard.ROOT / "Downloads" / "DA_Quarterly_Report_2026_Q3.pdf", "deny"),
])
def test_guard(path, want):
    assert guard.decide(path, False) == want
