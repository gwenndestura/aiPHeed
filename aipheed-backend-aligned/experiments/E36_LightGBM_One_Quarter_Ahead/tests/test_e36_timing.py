"""E36 leakage tests (PROTOCOL.md section 8): future data must never reach a feature, a training row, a selection
or a prediction of a one-quarter-ahead forecast."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e36_lib as L  # noqa: E402

C, np, pd = L.C, L.np, L.pd
ORIGINS = ["2022-Q4", "2024-Q4", "2026-Q2", "2026-Q3"]          # targets 2023-Q1, 2025-Q1, 2026-Q3, 2026-Q4


@pytest.fixture(scope="module")
def d():
    return L.Data()


def scrambled(t: int) -> L.Data:
    """A copy in which everything published on or after O(t), or belonging to a later quarter, is falsified."""
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
            d2.nw[key] = row._replace(n_rel=row.n_rel * 10 + 3, n_direct=row.n_direct + 1, fssi_v2=0.99)
    return d2


@pytest.mark.parametrize("tq", ORIGINS)
def test_future_data_cannot_change_features_rows_or_predictions(d, tq):
    t = C.qk(tq)
    d2 = scrambled(t)
    drop = ["H_last_quarter", "last_label_quarter"]
    assert d2.test(t).drop(columns=drop).equals(d.test(t).drop(columns=drop))
    assert d2.train(t).drop(columns=drop).equals(d.train(t).drop(columns=drop))
    a, b = L.fixed_arms(d, t), L.fixed_arms(d2, t)
    assert a.keys() == b.keys()
    for arm in a:
        for p in C.PROVS:
            assert abs(a[arm][p] - b[arm][p]) < 1e-12, (arm, p)


@pytest.mark.parametrize("tq", ORIGINS)
def test_training_targets_are_before_and_published_before_origin(d, tq):
    t = C.qk(tq)
    tr = d.train(t)
    posted = set(d.posted_quarters(L.origin(t)))
    assert len(tr) >= 10
    assert tr["target_q"].max() <= t - 1
    assert set(tr["target_q"]) <= posted
    assert not tr[L.COMB].isna().any().any()            # identical complete rows for every arm


def test_news_feature_is_the_origin_quarter_only(d):
    t = C.qk("2025-Q1")
    X = d.test(t).set_index("province_code")
    for p in C.PROVS:
        n = d.nw[(p, t)]
        assert X.loc[p, "news_n"] == pytest.approx(np.log1p(n.n_rel))   # FORECAST rule: evidence quarter = T-1


@pytest.fixture(scope="module")
def wf(d):
    return L.walk_forward(d)


def test_development_dates_match_the_protocol(wf):
    """PROTOCOL.md section 2 as corrected by DEVIATIONS.md D-1 (13 dates)."""
    _, info = wf
    assert info["dates"] == ["2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3",
                             "2024-Q4", "2025-Q1", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]


def test_nested_selection_uses_only_labels_posted_before_each_origin(d, wf):
    _, info = wf
    for arm, by_date in info["selections"].items():
        for target, s in by_date.items():
            t = C.qk(target) - 1
            posted = set(d.posted_quarters(L.origin(t)))
            for pq in s["prior_dates"]:
                assert C.qk(pq) in posted and C.qk(pq) <= t - 1, (arm, target, pq)


def test_a_later_outcome_cannot_change_an_earlier_selection(d, wf):
    """Flip the observed S1 of the last development target: every earlier selection and prediction must stay."""
    Pr, info = wf
    d2 = L.Data()
    last = C.qk(info["dates"][-1])
    for p in C.PROVS:
        d2.Sv[(p, last)] = -100.0
    d2.S1.loc[d2.S1["tq"] == last, "S1"] = -100.0
    Pr2, info2 = L.walk_forward(d2)
    for arm in info["selections"]:
        for target, s in info["selections"][arm].items():
            if C.qk(target) < last:
                assert info2["selections"][arm][target]["chosen"] == s["chosen"], (arm, target)
    a = Pr[Pr["target_quarter"] != C.qs(last)].reset_index(drop=True)
    b = Pr2[Pr2["target_quarter"] != C.qs(last)].reset_index(drop=True)
    assert np.allclose(a["p"].to_numpy(), b["p"].to_numpy(), atol=1e-12)


def test_no_row_outside_the_study_window(d):
    assert d.S1["tq"].min() >= C.qk("2021-Q1") and d.S1["tq"].max() <= C.qk("2026-Q3")
    assert min(t for _, t in d.rice) >= C.qk("2021-Q1") and max(t for _, t in d.rice) <= C.qk("2026-Q3")
    assert min(t for _, t in d.Dm) >= C.qk("2021-Q1")
    dates = pd.to_datetime(C.P._usable_from(d.rounds).dropna())
    assert dates.max() <= pd.Timestamp("2026-10-14 23:59:59")


def test_operational_forecast_uses_only_information_before_2026_10_01(d):
    t = L.OPERATIONAL_T
    assert str(L.origin(t).date()) == "2026-10-01"
    X = d.test(t)
    H_q = C.qk(X["H_last_quarter"].iloc[0])
    used = d.defA[d.defA["tq"] == H_q]
    assert (used["usable"] < L.origin(t)).all()
    assert X["last_label_quarter"].iloc[0] == "2026-Q2"           # the Sept 2026 round was posted 2026-10-14
    tr = d.train(t)
    assert C.qs(int(tr["target_q"].max())) == "2026-Q2"
