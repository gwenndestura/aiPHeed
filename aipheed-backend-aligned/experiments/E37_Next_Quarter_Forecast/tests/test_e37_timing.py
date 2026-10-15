"""E37 leakage and alignment tests for the next-quarter (lead 2) forecast."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e37_lib as L  # noqa: E402

C, np, pd = L.C, L.np, L.pd
K = 2


@pytest.fixture(scope="module")
def d():
    return L.Data()


def scrambled(t):
    o = L.origin(t)
    d2 = L.Data()
    usable = C.P._usable_from(d2.rounds).fillna(pd.Timestamp("2100-01-01"))
    late = d2.rounds.index[usable >= o]
    d2.rounds.loc[late, "H"] = d2.rounds.loc[late, "H"] * 3 + 7
    d2.defA = d2.rounds[d2.rounds["definition_A"].astype(str).str.lower() == "true"].assign(
        tq=lambda x: x["quarter"].map(C.qk), usable=lambda x: C.P._usable_from(x))
    for key in list(d2.Sv):
        if key[1] >= t:
            d2.Sv[key] += 50.0
    d2.S1.loc[d2.S1["tq"] >= t, "S1"] += 50.0
    for key in list(d2.Dm):
        if key[1] >= t:
            d2.Dm[key] -= 9.0
    for key in list(d2.Nm):
        if key[1] > t:
            d2.Nm[key] += 5.0
    for key in list(d2.rice):
        if key[1] > t:
            d2.rice[key] += 3.0
    for key, row in list(d2.nw.items()):
        if key[1] > t:
            d2.nw[key] = row._replace(n_rel=row.n_rel * 10 + 3, fssi_v2=0.99)
    return d2


@pytest.mark.parametrize("tq", ["2023-Q2", "2024-Q4", "2026-Q1", "2026-Q3"])
def test_future_data_cannot_change_a_lead2_forecast(d, tq):
    t = C.qk(tq)
    d2 = scrambled(t)
    drop = ["H_last_quarter", "last_label_quarter"]
    assert d2.test(t, K).drop(columns=drop).equals(d.test(t, K).drop(columns=drop))
    a, b = L.fixed_arms(d, t, K), L.fixed_arms(d2, t, K)
    for arm in a:
        for p in C.PROVS:
            assert abs(a[arm][p] - b[arm][p]) < 1e-12, (arm, p)


def test_training_targets_published_and_two_quarters_behind(d):
    for t in (C.qk("2024-Q4"), C.qk("2026-Q3")):
        tr = d.train(t, K)
        posted = set(d.posted_quarters(L.origin(t)))
        assert tr["target_q"].max() <= t - 1 and set(tr["target_q"]) <= posted
        assert ((tr["target_q"] - tr["t"]) == K).all()


def test_operational_forecast_targets_2027_q1_from_2026_10_01(d):
    t = L.OPERATIONAL_T
    assert str(L.origin(t).date()) == "2026-10-01" and C.qs(t + K) == "2027-Q1"
    X = d.test(t, K)
    assert (X["H_gap"] == C.qk("2027-Q1") - C.qk(X["H_last_quarter"].iloc[0])).all()
    assert X["last_label_quarter"].iloc[0] == "2026-Q2"          # the Sept 2026 round was posted after the origin


def test_missing_labels_are_never_evaluated(d):
    dates = L.eval_dates(d, K)
    targets = {C.qs(t + K) for t in dates}
    assert not targets & {"2022-Q1", "2025-Q2", "2025-Q3"}        # no definition-A label
    for t in dates:
        assert all(d.label(p, t + K, t) is not None for p in C.PROVS)


def test_nested_selection_uses_only_posted_prior_targets(d):
    Pr, info = L.walk_forward(d, K)
    for arm, by in info["selections"].items():
        for target, s in by.items():
            t = C.qk(target) - K
            posted = set(d.posted_quarters(L.origin(t)))
            assert all(C.qk(q) in posted and C.qk(q) <= t - 1 for q in s["prior_dates"]), (arm, target)
    assert set(Pr["arm"]) >= {"E36-LGBM", "B1_PERSISTENCE", "B2_LR_COMB", "B3_LR_GOV", "B4_LR_NLP",
                              "B5_LGBM_GOV", "B6_LGBM_NLP"}
