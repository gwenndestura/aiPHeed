"""E38 leakage, selection and reproducibility tests (lead 2)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e38_lib as L  # noqa: E402

C, np, pd = L.C, L.np, L.pd
E37RUN = L.E38.parent / "E37_Next_Quarter_Forecast" / "runs" / "20261015T031545Z"


@pytest.fixture(scope="module")
def d():
    return L.Data()


def scrambled(t):
    o = L.L7.origin(t)
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
    for key, row in list(d2.nw.items()):
        if key[1] > t:
            d2.nw[key] = row._replace(n_rel=row.n_rel * 10 + 3, fssi_v2=0.99)
    for key in list(d2.trig):
        if key[1] > t:
            d2.trig[key] = {c: 1.0 for c in L.TRIG_COLS}
    return d2


@pytest.mark.parametrize("tq", ["2023-Q3", "2025-Q1", "2026-Q3"])
def test_future_data_cannot_change_any_pool_prediction_or_the_prior_shift(d, tq):
    t = C.qk(tq)
    a, b = L.pool_predictions(d, t), L.pool_predictions(scrambled(t), t)
    assert abs(a["_shift"] - b["_shift"]) < 1e-12
    for k in a:
        if k != "_shift":
            assert all(abs(a[k][p] - b[k][p]) < 1e-12 for p in C.PROVS), k


def test_recent_rate_uses_only_labels_posted_before_origin(d):
    t = C.qk("2026-Q3")                                # origin 2026-10-01; Sept round posted 2026-10-14
    posted = [q for q in d.posted_quarters(L.L7.origin(t)) if q <= t - 1][-4:]
    assert C.qs(max(posted)) == "2026-Q2"


def test_shared_configuration_reproduces_e37(d):
    """COMB x G1 without adjustment is the E36/E37 setting: identical predictions on every E37 outer date."""
    e37 = pd.read_csv(E37RUN / "predictions.csv", dtype={"province_code": str})
    e37 = e37[e37["arm"] == "COMBxG1"]
    for t in sorted({C.qk(x) for x in e37["t"]})[:4]:
        mine = L.pool_predictions(d, t)["COMBxG1"]
        ref = e37[e37["t"] == C.qs(t)].set_index("province_code")["p"]
        assert all(abs(mine[p] - ref[p]) < 1e-9 for p in C.PROVS), C.qs(t)


def test_threshold_and_selection_use_only_prior_dates(d):
    Pr, info = L.walk_forward(d)
    for target, s in info["path"].items():
        t = C.qk(target) - L.K
        posted = set(d.posted_quarters(L.L7.origin(t)))
        assert all(C.qk(q) in posted and C.qk(q) <= t - 1 for q in s["prior_dates"]), target
        assert s["threshold"] in L.THRESHOLDS
    # changing the outcome of the last date leaves every earlier choice and threshold unchanged
    d2 = L.Data()
    last = C.qk(info["dates"][-1])
    for p in C.PROVS:
        d2.Sv[(p, last)] = -100.0
    d2.S1.loc[d2.S1["tq"] == last, "S1"] = -100.0
    _, info2 = L.walk_forward(d2)
    for q, s in info["path"].items():
        if C.qk(q) < last:
            assert info2["path"][q]["chosen"] == s["chosen"] and info2["path"][q]["threshold"] == s["threshold"], q


def test_trigger_features_are_publication_quarter_proportions(d):
    t = C.qk("2024-Q3")
    X = d.test(t)
    for r in X.itertuples():
        for c in L.TRIG_COLS:
            v = getattr(r, c)
            assert 0.0 <= v <= 1.0
            assert v == d.trig.get((r.province_code, t), {}).get(c, 0.0)
