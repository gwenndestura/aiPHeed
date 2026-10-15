"""E39 tests: hand-computed labels, no leakage, missing quarters, determinism, tie ranks, withheld history, same
cutoff, per-date scoring formulas, chronological calibration, baselines from training data only."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e39_lib as L  # noqa: E402

C, np, pd = L.C, L.np, L.pd


@pytest.fixture(scope="module")
def d():
    return L.Data()


def test_hand_computed_labels(d):
    q = C.qk
    assert d.target("A", "PH040300000", q("2024-Q3")) == 1          # Quezon 7.50% > 4
    assert d.target("A", "PH040100000", q("2025-Q1")) == 1          # Cavite (4.0+4.1+4.3)/3 = 4.133% > 4
    assert d.target("A", "PH040400000", q("2025-Q1")) == 0          # Rizal 2.767%
    assert d.target("B", "PH040200000", q("2026-Q3")) == pytest.approx(3.6333333333, abs=1e-9)
    assert d.target("C", "PH040100000", q("2021-Q2")) == pytest.approx(15.35)   # mean of 15.7 and 15.0
    d2 = L.Data()
    d2.F[("PH040100000", q("2024-Q1"))] = 4.0
    assert d2.target("A", "PH040100000", q("2024-Q1")) == 0          # strictly above 4 only


def test_missing_sws_quarters_have_cpi_labels_but_no_hunger(d):
    for qq in ("2021-Q1", "2022-Q1", "2025-Q2", "2025-Q3"):
        assert d.target("B", "PH040100000", C.qk(qq)) is not None
        assert d.target("C", "PH040100000", C.qk(qq)) is None


def scrambled(t):
    o = L.L7.origin(t)
    d2 = L.Data()
    usable = C.P._usable_from(d2.rounds).fillna(pd.Timestamp("2100-01-01"))
    late = d2.rounds.index[usable >= o]
    d2.rounds.loc[late, "H"] = d2.rounds.loc[late, "H"] * 3 + 7
    d2.defA = d2.rounds[d2.rounds["definition_A"].astype(str).str.lower() == "true"].assign(
        tq=lambda x: x["quarter"].map(C.qk), usable=lambda x: C.P._usable_from(x))
    for key in list(d2.F):
        if key[1] >= t:
            d2.F[key] += 11.0
    for key in list(d2.Hq):
        if key >= t:
            d2.Hq[key] += 13.0
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
    return d2


@pytest.mark.parametrize("kind", ["A", "B", "C"])
@pytest.mark.parametrize("k", [1, 2])
def test_future_data_cannot_change_features_model_or_baselines(d, kind, k):
    t = C.qk("2025-Q1")
    d2 = scrambled(t)
    feats = L.FEATS[k]
    a_tr, b_tr = d.train(kind, t, k, feats), d2.train(kind, t, k, feats)
    drop = ["H_last_quarter", "last_label_quarter"]
    assert a_tr.drop(columns=drop).equals(b_tr.drop(columns=drop))
    a_te, b_te = d.X(kind, t, k), d2.X(kind, t, k)
    assert a_te.drop(columns=drop).equals(b_te.drop(columns=drop))
    pa, pb = L._lgbm(kind, a_tr, a_te, feats, k), L._lgbm(kind, b_tr, b_te, feats, k)
    assert all(abs(pa[p] - pb[p]) < 1e-12 for p in C.PROVS)
    ba, bb = L.baselines(d, kind, t, k, a_tr, a_te), L.baselines(d2, kind, t, k, b_tr, b_te)
    for name in ba:
        assert all(abs(ba[name][p] - bb[name][p]) < 1e-12 for p in C.PROVS), name


def test_training_targets_are_published_before_origin(d):
    t = C.qk("2026-Q2")
    tr = d.train("C", t, 1, L.FEATS[1])
    assert tr["target_q"].max() <= t - 1 and set(tr["target_q"]) <= set(d.posted_quarters(L.L7.origin(t)))
    trb = d.train("B", t, 2, L.FEATS[2])
    assert trb["target_q"].max() <= t - 1


def test_determinism(d):
    t = C.qk("2025-Q4")
    feats = L.FEATS[1]
    a = L._lgbm("B", d.train("B", t, 1, feats), d.X("B", t, 1), feats, 1)
    d2 = L.Data()
    b = L._lgbm("B", d2.train("B", t, 1, feats), d2.X("B", t, 1), feats, 1)
    assert a == b


def test_tie_ranks_share_the_average_rank():
    r, tied = L.avg_rank({"a": 0.4, "b": 0.4, "c": 0.9, "d": 0.1})
    assert r == {"a": 2.5, "b": 2.5, "c": 1.0, "d": 4.0}
    assert tied == {"a": True, "b": True, "c": False, "d": False}


@pytest.fixture(scope="module")
def wf_a(d):
    return L.walk_forward(d, "A", 1)


def test_withheld_history_and_statuses(wf_a):
    P, meta = wf_a
    for q, m in meta.items():
        if m["training_quarters"] < L.MIN_PRIOR:
            assert m["status"] == "Withheld"
            assert P[(P.target_quarter == q)]["pred"].isna().all()
    assert meta["2026-Q4"]["status"] == "No outcome yet"


def test_missing_round_is_not_scored(d):
    P, meta = L.walk_forward(d, "C", 1)
    assert meta["2025-Q2"]["status"] in ("Missing round", "Withheld")
    assert meta["2025-Q3"]["status"] in ("Missing round", "Withheld")
    assert not (P[P.target_quarter.isin(["2025-Q2", "2025-Q3"])]["status"] == "Scored").any()


def test_same_cutoff_for_predicted_and_observed():
    assert L.THRESHOLD == 4.0
    import json
    spec = json.loads((L.E39 / "label_v2_spec.json").read_text())
    assert spec["label_A"]["threshold"] == L.THRESHOLD


def test_per_date_scoring_formulas():
    g = pd.DataFrame({"target_quarter": ["q1"] * 2 + ["q2"] * 3, "pred": [0.2, 0.8, 0.5, 0.5, 1.0],
                      "y": [0, 1, 1, 0, 1]})
    b = L.per_date_loss(g, "A")
    assert b["q1"] == pytest.approx((0.04 + 0.04) / 2) and b["q2"] == pytest.approx((0.25 + 0.25 + 0) / 3)
    assert b.mean() == pytest.approx((0.04 + 0.5 / 3) / 2)          # dates weigh equally
    m = L.per_date_loss(g.assign(pred=[1, 2, 3, 4, 5], y=[1, 1, 1, 1, 1]), "B")
    assert m["q1"] == pytest.approx(0.5) and m["q2"] == pytest.approx(3.0)
    pb = L.pooled_binary(g)
    assert pb["TP"] == 3 and pb["FP"] == 1 and pb["TN"] == 1 and pb["FN"] == 0


def test_calibration_is_chronological(d, wf_a):
    """Changing the LAST observed outcome must not change any earlier calibrated probability."""
    P, meta = wf_a
    d2 = L.Data()
    for p in C.PROVS:
        d2.F[(p, L.LAST_OBS)] = 99.0 if d.F[(p, L.LAST_OBS)] <= 4 else -99.0
    P2, _ = L.walk_forward(d2, "A", 1)
    a = P[(P.arm == "model") & (P.target_quarter.map(C.qk) < L.LAST_OBS)].reset_index(drop=True)
    b = P2[(P2.arm == "model") & (P2.target_quarter.map(C.qk) < L.LAST_OBS)].reset_index(drop=True)
    assert np.allclose(a["pred"].astype(float).fillna(-1), b["pred"].astype(float).fillna(-1), atol=1e-12)


def test_calibration_rule():
    raw = {"x": 0.9, "y": 0.1}
    cal, how = L.calibrate(raw, [(0.9, 1)] * 3, prior_dates=3, clim=0.4)
    assert how == "shrinkage_to_climatology" and cal["x"] == pytest.approx(0.65)
    cal, how = L.calibrate(raw, [(0.9, 1), (0.2, 0)] * 10, prior_dates=10, clim=0.4)
    assert how == "platt" and 0 < cal["y"] < cal["x"] < 1


def test_conformal_needs_eight_dates():
    assert L.conformal([1, 2, 3], 3) is None
    assert L.conformal(list(range(1, 11)), 8) == 9            # ceil(0.8 * 11) = 9th smallest
