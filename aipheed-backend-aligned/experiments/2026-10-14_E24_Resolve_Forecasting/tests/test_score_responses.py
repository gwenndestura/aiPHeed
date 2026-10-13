"""Scorer mechanics on SYNTHETIC responses generated inside the test. Never written to disk or reported."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "instruments"))
import score_responses as S  # noqa: E402

RANKS = pd.read_csv(Path(__file__).resolve().parents[2] / "2026-10-13_E23_Chapter1_Complete" / "rankings" / "lgu_rankings_backtest_2026Q1.csv",
                    dtype={"province_code": str})


def synth(n, level, agree=True, seed=0):
    rng = np.random.default_rng(seed)
    g = RANKS[RANKS["province_code"] == "PH040100000"].sort_values("risk_index", ascending=False)["lgu_name"].tolist()
    rows = []
    for _ in range(n):
        r = {"Timestamp": "2026/11/20 10:00:00 AM GMT+8", "CONSENT": "Yes", "P4 - Province": "Cavite"}
        for c in S.RATED:
            r[f"{c} - item"] = f"{int(np.clip(level + rng.integers(-1, 2), 1, 5))} - x"
        pick = (g[:3], g[-3:]) if agree else (list(rng.choice(g, 3, replace=False)), list(rng.choice(g, 3, replace=False)))
        for j in range(3):
            r[f"RK2_{j + 1}"], r[f"RK3_{j + 1}"] = pick[0][j], pick[1][j]
        rows.append(r)
    return pd.DataFrame(rows)


def test_favorable_and_consistent_rejects_both():
    out = S.score(synth(40, 4.6), RANKS)
    assert out["H5"]["decision"] == "rejected" and out["H4"]["decision"] == "rejected"


def test_neutral_and_random_do_not_reject():
    out = S.score(synth(40, 3, agree=False, seed=3), RANKS)
    assert out["H5"]["decision"] == "not rejected" and out["H4"]["decision"] == "not rejected"


def test_too_few_and_no_consent():
    d = synth(29, 5)
    assert S.score(d, RANKS)["H5"]["decision"] == "insufficient responses"
    d = synth(40, 5)
    d.loc[:20, "CONSENT"] = "No"
    out = S.score(d, RANKS)
    assert out["excluded_no_consent"] == 21 and out["H5"]["decision"] == "insufficient responses"


def test_missing_items_are_not_imputed():
    d = synth(40, 5)
    for c in [c for c in d.columns if c[:2] in ("FS", "AC", "US")][:6]:
        d.loc[:5, c] = None
    out = S.score(d, RANKS)
    assert out["excluded_incomplete"] == 6 and out["n_valid"] == 34


def test_refuses_non_forms_export():
    import pytest
    d = synth(40, 5).drop(columns="Timestamp")
    with pytest.raises(ValueError):
        S.score(d, RANKS)
