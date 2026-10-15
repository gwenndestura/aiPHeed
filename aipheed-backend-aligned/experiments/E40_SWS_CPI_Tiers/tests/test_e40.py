"""E40 tests: frozen-window immutability, no pre-2021 data, no look-ahead, the training-fold gate, market-v2, ties.

    <backend venv python> -B -m pytest tests -q        (cwd = the E40 folder)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E40 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E40 / "runner"))
import e40_label as L  # noqa: E402
import e40_model as M  # noqa: E402


@pytest.fixture(scope="module")
def d():
    return M.Data()


# ------------------------------------------------------------------ frozen window
def test_frozen_files_match_their_hashes():
    fr = json.loads((E40 / "frozen" / "E40_LABEL_FREEZE.json").read_text())
    for f, h in fr["sha256"].items():
        assert hashlib.sha256((E40 / f).read_bytes()).hexdigest() == h, f


def test_thresholds_ignore_everything_after_the_window():
    q = L.quarterly_inputs()
    base = L.frozen_thresholds(q, 60)
    later = q["quarter"].map(L.qi) > L.qi(L.WINDOW[1])
    q2 = q.copy()
    q2.loc[later, ["H", "food", "cpi_gap"]] *= 7.0                      # wild post-window values
    assert L.frozen_thresholds(q2, 60) == base
    assert L.frozen_thresholds(q[~later], 60) == base


def test_spec_thresholds_equal_a_fresh_window_computation():
    spec = json.loads((E40 / "label_spec.json").read_text())
    fresh = L.frozen_thresholds(L.quarterly_inputs(), spec["percentile"])
    assert json.loads(json.dumps(fresh)) == spec["thresholds"]


def test_label_is_binary_and_never_zero_fills_missing_sws():
    lab = pd.read_csv(E40 / "label_primary.csv")
    assert set(lab["label"].dropna()) <= {"HIGH", "LOW"}
    for q in ("2021-Q1", "2022-Q1", "2025-Q2", "2025-Q3"):
        assert lab[lab.quarter == q]["y_high"].isna().all(), q


# ------------------------------------------------------------------ no pre-2021 data
def test_no_input_predates_2021(d):
    assert d.m["reference_month"].min() >= "2021-01"
    assert d.rounds["t"].min() >= L.qi("2021-Q1")
    assert d.lab["t"].min() >= L.qi("2021-Q1")
    assert min(t for (_, t) in d.news) >= L.qi("2021-Q1")
    import e40_triggers as T
    assert T.articles()["ph_date"].min() >= "2021-01-01"


def test_monthly_cpi_rejects_a_pre_2021_row(tmp_path, monkeypatch):
    src = pd.read_csv(L.CPI, dtype={"province_code": str})
    bad = pd.concat([src, src.head(1).assign(reference_month="2020-12")])
    f = tmp_path / "cpi.csv"
    bad.to_csv(f, index=False)
    monkeypatch.setattr(L, "CPI", f)
    with pytest.raises(AssertionError):
        L.monthly_cpi()


# ------------------------------------------------------------------ no look-ahead
@pytest.mark.parametrize("target", ["2024-Q1", "2024-Q3", "2025-Q1"])
def test_features_only_use_information_before_the_origin(d, target):
    t = L.qi(target) - 1
    o = M.origin(t)
    full = d.features(t)
    c = M.Data()
    c.rounds = c.rounds[c.rounds["usable"] < o]                          # drop rounds posted at/after the origin
    m = c.m
    keep = (m["quarter"].map(L.qi) < t) | ((m["quarter"].map(L.qi) == t) & (m["month_in_q"] <= 2))
    c.m = m[keep]                                                        # drop CPI months not yet released
    c.news = {k: v for k, v in c.news.items() if k[1] <= t}
    c.comp = {k: v for k, v in c.comp.items() if k[1] <= t}
    c.y = {k: v for k, v in c.y.items() if k[1] <= t - 1}
    pd.testing.assert_frame_equal(full, c.features(t))


def test_training_labels_are_known_before_the_origin(d):
    for target in ("2024-Q2", "2025-Q1", "2026-Q1"):
        t = L.qi(target) - 1
        o = M.origin(t)
        for s in d.known_labels(t):
            assert s <= t - 1
            assert (d.rounds[d.rounds["t"] == s]["usable"] < o).all()
        tr = d.training(t)
        assert (tr["target_t"] <= t - 1).all()


def test_holdout_forecasts_use_development_labels_only(d):
    hold = json.loads((E40 / "label_spec.json").read_text())["holdout_quarters_untouched"]
    for q in hold:
        tr = d.training(L.qi(q) - 1, max_label_t=L.qi("2025-Q1"))
        assert (tr["target_t"] <= L.qi("2025-Q1")).all()


# ------------------------------------------------------------------ gate, cutoff, ties, market-v2
def test_every_development_fold_is_reported_against_the_gate():
    ev = sorted((E40 / "runs").glob("eval_*"))[-1]
    r = json.loads((ev / "evaluation.json").read_text(encoding="utf-8"))
    folds = [f for f in r["folds"] if f["status"].startswith("fold")]
    assert folds and all(("GATE FAILED" in f["status"]) == (f["train_HIGH"] < M.MIN_TRAIN_HIGH) for f in folds)
    assert set(r["gate_failed_folds"]) == {f["target"] for f in folds if f["train_HIGH"] < 2}
    assert all(f["train_label_quarters"] >= M.MIN_TRAIN_QUARTERS for f in folds)


def test_cutoff_defaults_to_half_without_out_of_fold_highs():
    assert M.choose_cutoff(pd.DataFrame({"y": [0, 0, 1], "p": [.1, .2, .3]}))[0] == 0.5


def test_platt_is_identity_clip_without_two_of_each_class():
    f, how = M.platt([(0.99, 1), (0.1, 0), (0.2, 0)])
    assert "uncalibrated" in how and f(np.array([0.999]))[0] == 0.98


def test_ties_broken_by_cpi_gap_then_shared():
    df = pd.DataFrame({"p": [.5, .5, .5, .2], "gap_now": [1.0, 2.0, 2.0, 9.0]})
    assert M.rank_with_ties(df).tolist() == [3, 1, 1, 4]


def test_market_v2_requires_context_and_a_non_generic_term():
    import e40_triggers as T
    assert T.market_v2("Rice price hike hits Batangas", ["rice price", "price hike"])
    assert not T.market_v2("DA observes lower rice price at markets", ["rice price"])
    assert not T.market_v2("Palay prices rise in May", ["palay"])


def test_no_cpi_variant_has_no_cpi_or_label_features():
    assert not set(M.FEATURE_SETS["NO_CPI"]) & M.CPI_DERIVED
