"""
Label-availability rule L and the SWS nowcast of
scripts/supplementary/origin_info_study.py.
"""

import hashlib

import pandas as pd
import pytest

import scripts.supplementary.origin_info_study as O
import scripts.supplementary.reliability_diagnostics as R
import scripts.supplementary.window2021_study as W


@pytest.fixture(scope="module")
def data():
    f, inputs, _, _ = W.window_frame(extend=True)
    labels = W.window_labels(W.THR_PRIMARY)
    d = R.pairs(f[f["quarter"] <= "2025-Q4"], labels, 1)
    lab = labels.assign(cpi_rel_target=labels["food_cpi_yoy"] - labels["regional_food_cpi_yoy"])
    d = d.merge(lab[["province_code", "quarter", "cpi_rel_target"]].rename(columns={"quarter": "target_quarter"}),
                on=["target_quarter", "province_code"])
    return d, O.quarter_table(d, labels)


def test_preregistration_and_amendment_unchanged():
    assert hashlib.sha256((O.EXP / "PREREGISTRATION_v4.json").read_bytes()).hexdigest() == O.PREREG_SHA
    assert hashlib.sha256((O.EXP / "PREREGISTRATION_v4_AMENDMENT_L.json").read_bytes()).hexdigest() == O.AMEND_SHA


def test_rule_l_excludes_unreleased_training_labels(data):
    d, _ = data
    for Tq, tr, te in O.splits(d, 8, True):
        for s in tr["target_quarter"].unique():
            assert O.REL[s] < O.T.qstart(Tq), (Tq, s)
        assert tr["target_quarter"].map(R.qi).max() < R.qi(Tq)


def test_without_rule_l_the_previous_quarter_leaks(data):
    d, _ = data
    leaked = [Tq for Tq, tr, _ in O.splits(d, 8, False)
              if any(O.REL[s] >= O.T.qstart(Tq) for s in tr["target_quarter"].unique())]
    assert len(leaked) == 7          # documents the defect found in earlier studies


def test_nowcast_uses_training_quarters_only(data):
    d, qt = data
    Tq = "2024-Q4"
    trq = [s for s in qt.index if O.released_before(s, Tq) and R.qi(s) < R.qi(Tq)]
    tr = d[d["target_quarter"].isin(trq)]
    m1 = O.Nowcast("N2").fit(tr, qt.loc[sorted(trq, key=R.qi)])
    qt2 = qt.copy()
    qt2.loc[Tq, "sws_target"] = 999.0                  # perturb the test quarter's outcome
    m2 = O.Nowcast("N2").fit(tr, qt2.loc[sorted(trq, key=R.qi)])
    te = d[d["target_quarter"] == Tq]
    assert (m1.predict(te, qt.loc[[Tq]])[0] == m2.predict(te, qt2.loc[[Tq]])[0]).all()


def test_frozen_rule_l_forecasts_trained_on_released_labels_only():
    fc = pd.read_csv(O.EXP / "FROZEN_2026_RULE_L.csv")
    for _, r in fc.drop_duplicates("target_quarter").iterrows():
        assert O.REL[r["latest_train_label"]] < O.T.qstart(r["target_quarter"])
