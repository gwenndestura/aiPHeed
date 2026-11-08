"""E13 synthetic tests: guard decisions, availability rules, leakage (future-perturbation) invariance
and metric correctness. No project data is read by these tests."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RUNNER = Path(__file__).resolve().parents[1] / "runner"
sys.path.insert(0, str(RUNNER))
import guard  # noqa: E402
import e13_lib as L  # noqa: E402

ROOT = guard.ROOT


# ------------------------------------------------------------------ guard decisions (no file opened)
@pytest.mark.parametrize("path,write,want", [
    (ROOT / "backend" / "data" / "processed" / "psa_indicators.parquet", False, "deny"),
    (ROOT / "backend" / "data" / "processed" / "sws_hunger.parquet", False, "deny"),
    (ROOT / "aipheed-backend-aligned" / "data" / "processed" / "cpi_full.parquet", False, "deny"),
    (ROOT / "aipheed-backend-aligned" / "data" / "processed" / "labels.parquet", False, "deny"),
    (ROOT / "aipheed-backend-aligned" / "data" / "supplementary" / "collection_2026-10-09" /
     "provincial_food_cpi_yoy_2026H1_raw.csv", False, "deny"),
    (ROOT / "aipheed-backend-aligned" / "experiments" / "2026-10-12_E10_selection_alignment_q4" / "q4" /
     "predictions.csv", False, "deny"),
    (Path.home() / ".claude" / "projects" / "x.jsonl", False, "deny"),
    (ROOT / "backend" / "app" / "main.py", True, "deny"),
    (ROOT / "aipheed-backend-aligned" / "experiments" / "2026-10-12_E12_SWS_Scoring_Comparison" / "new.csv", True, "deny"),
    (ROOT / "backend" / "data" / "processed" / "psa_subsistence.parquet", False, "allow"),
    (guard.E12_RUN / "realized_components_2021_2025.csv", False, "allow"),
    (guard.E12_RUN / "manifest.json", False, "deny"),
    (guard.EXP / "runs" / "x.csv", True, "allow"),
])
def test_guard_decide(path, write, want):
    assert guard.decide(path, write) == want


def test_allowlist_has_no_mixed_or_protected_names():
    for p in guard.ALLOW:
        assert not any(s in p.name.lower() for s in guard.DENY_NAME_PARTS), p


# ------------------------------------------------------------------ synthetic data
def synth_rounds():
    rows = []
    for i in range(L.qi("2021-Q2"), L.qi("2025-Q4") + 1):
        q = L.qs(i)
        end = L.origin(L.qs(i + 1))
        rows.append({"quarter": q, "H": 10 + (i % 5), "published": end + pd.Timedelta(days=40),
                     "date_type": "verified", "definition_A": True, "source": "synthetic", "round": q})
    return pd.DataFrame(rows)


def synth_comp():
    rng = np.random.default_rng(0)
    rows = []
    for i in range(L.qi("2021-Q1"), L.qi("2025-Q4") + 1):
        F = rng.normal(5, 2, 5)
        m = F.mean()
        for pc, f in zip(L.PROVINCES, F):
            rows.append({"province_code": pc, "quarter": L.qs(i), "F": f, "mean5": m, "D": f - m,
                         "H": np.nan, "S1": np.nan, "province": L.PROVINCES[pc]})
    return pd.DataFrame(rows)


def test_h_last_respects_publication():
    r = synth_rounds()
    T = "2024-Q1"
    v, q = L.h_last(r, L.origin(T))
    # round of 2023-Q4 is published 40 days after 2024-01-01, so the latest visible is 2023-Q3
    assert q == "2023-Q3"


def test_a_training_only_published_targets():
    r, c = synth_rounds(), synth_comp()
    T = "2024-Q2"
    tr = L.a_training(r, c, T)
    pub = r.groupby("quarter")["published"].max()
    assert (tr["quarter"].map(pub) < L.origin(T)).all()
    assert tr["quarter"].map(L.qi).max() <= L.qi(T) - 2


def test_b_features_use_T_minus_2_only():
    c = synth_comp()
    f = L.b_features(c, "2024-Q1")
    lag = c[c["quarter"] == "2023-Q3"].set_index("province_code")
    assert np.allclose(f.set_index("province_code")["F_lag2"], lag["F"].reindex(f["province_code"]))


def test_future_perturbation_invariance_B():
    c = synth_comp()
    T = "2024-Q3"
    tr0, fe0 = L.b_training(c, T), L.b_features(c, T)
    c2 = c.copy()
    fut = c2["quarter"].map(L.qi) >= L.qi(T) - 1
    c2.loc[fut, ["F", "D", "mean5"]] = 999.0
    tr1, fe1 = L.b_training(c2, T), L.b_features(c2, T)
    pd.testing.assert_frame_equal(tr0, tr1)
    pd.testing.assert_frame_equal(fe0, fe1)


def test_future_perturbation_invariance_A():
    r, c = synth_rounds(), synth_comp()
    T = "2024-Q3"
    tr0, fe0 = L.a_training(r, c, T), L.a_features(r, c, T)
    r2 = r.copy()
    r2.loc[r2["published"] >= L.origin(T), "H"] = 999.0
    c2 = c.copy()
    c2.loc[c2["quarter"].map(L.qi) >= L.qi(T) - 1, ["F", "D", "mean5"]] = 999.0
    tr1, fe1 = L.a_training(r2, c2, T), L.a_features(r2, c2, T)
    pd.testing.assert_frame_equal(tr0, tr1)
    assert fe0 == fe1


def test_ridge_recovers_slope_with_small_alpha():
    x = np.arange(20, dtype=float)[:, None]
    y = 3 + 2 * x[:, 0]
    pred, coef = L.ridge_fit_predict(x, y, np.array([[30.0]]), alpha=1e-9)
    assert abs(pred[0] - 63) < 1e-6


def test_classification_and_auc():
    y = [1, 1, 0, 0, 1, 0]
    s = [0.9, 0.8, 0.7, 0.1, 0.2, 0.3]
    m = L.classification(y, [v > 0.5 for v in s])
    assert (m["TP"], m["FP"], m["FN"], m["TN"]) == (2, 1, 1, 2)
    a = L.auc_scores(y, s)
    assert abs(a["ROC_AUC"] - 7 / 9) < 1e-12
    assert L.auc_scores([1, 1], [0.1, 0.2]) == {"ROC_AUC": None, "PR_AUC": None}


def test_sign_flip_and_holm():
    assert L.sign_flip_p(np.array([-1.0, -1.0, -1.0])) == 1 / 8
    h = L.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert h == pytest.approx({"a": 0.03, "c": 0.06, "b": 0.06})


def test_cluster_bootstrap_identity():
    df = pd.DataFrame({"quarter": ["q1", "q1", "q2"], "y": [0, 0, 0], "a": [1, 1, 1], "b": [1, 1, 1]})
    r = L.cluster_bootstrap_mae_diff(df, "a", "b", n_boot=50)
    assert r["diff"] == 0 and r["ci_low"] == 0 and r["ci_high"] == 0
