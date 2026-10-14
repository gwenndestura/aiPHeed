"""E32 data-timing and feature tests: nothing released after the origin can reach a feature, a label or a prediction."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e32_common as C  # noqa: E402
import e32_lib as L  # noqa: E402


@pytest.fixture(scope="module")
def d():
    return L.Data()


@pytest.mark.parametrize("t", ["2023-Q3", "2024-Q4", "2025-Q4", "2026-Q2"])
def test_h_features_use_only_rounds_posted_before_origin(d, t):
    t = C.qk(t)
    X = d.features(t, 1)
    o = L.origin(t)
    q = C.qk(X["H_last_quarter"].iloc[0])
    used = d.defA[d.defA["tq"] == q]
    assert (used["usable"] < o).all()
    later = d.defA[(d.defA["tq"] > q) & (d.defA["usable"] < o)]
    assert later.empty                                       # H_last is the LATEST posted quarter


def test_price_rice_news_features_are_of_the_right_quarter(d):
    t = C.qk("2025-Q1")
    X = d.features(t, 1).set_index("province_code")
    for p in C.PROVS:
        assert X.loc[p, "D_last"] == d.Dm[(p, t - 1)]
        assert X.loc[p, "Dnow"] == d.Nm[(p, t)]
        assert X.loc[p, "rice_rel"] == pytest.approx(d.rice[(p, t)])
        n = d.nw[(p, t)]
        assert X.loc[p, "news_n"] == pytest.approx(np.log1p(n.n_rel))   # FORECAST rule: news of quarter t = T - k


def test_training_pairs_are_published_before_origin(d):
    for t in (C.qk("2024-Q2"), C.qk("2026-Q2")):
        tr = d.training_pairs(t, 1)
        posted = set(d.posted_quarters(L.origin(t)))
        assert len(tr) > 0 and tr["target_q"].max() <= t - 1 and set(tr["target_q"]) <= posted


def test_threshold_and_persistence_are_publication_aware(d):
    t = C.qk("2026-Q2")                        # origin 2026-07-01: the June 2026 round was posted 2026-08-24
    X = d.features(t, 1)
    assert X["last_label_quarter"].iloc[0] == "2026-Q1"     # March round posted 2026-05-12 -> usable
    assert d.tau(t) == pytest.approx(C.P.threshold_at(d.S1, d.rounds, t, L.origin(t))[0])
    ref = L.references(d, t, 1)
    for p in C.PROVS:
        assert ref["B1"][p] == float(d.Sv[(p, C.qk("2026-Q1"))] > d.tau(t))


def test_future_data_cannot_change_a_prediction(d):
    """Scramble every SWS value posted after the origin and every S1/D after t-1: features and every candidate's
    prediction at that origin must be identical."""
    t, k = C.qk("2025-Q1"), 1
    o = L.origin(t)
    base = {a: f(d, t, k) for a, f in L.CANDIDATES.items()}
    Xb = d.features(t, k).drop(columns=["H_last_quarter", "last_label_quarter"])
    d2 = L.Data()
    late = d2.rounds.index[P_usable(d2) >= o]
    d2.rounds.loc[late, "H"] = d2.rounds.loc[late, "H"] * 3 + 7
    d2.defA = d2.rounds[d2.rounds["definition_A"].astype(str).str.lower() == "true"].assign(
        tq=lambda x: x["quarter"].map(C.qk), usable=lambda x: C.P._usable_from(x))
    for key in list(d2.Sv):
        if key[1] >= t:
            d2.Sv[key] = d2.Sv[key] + 50.0
    d2.S1.loc[d2.S1["tq"] >= t, "S1"] += 50.0
    for key in list(d2.Dm):
        if key[1] >= t:
            d2.Dm[key] = d2.Dm[key] - 9.0
    assert d2.features(t, k).drop(columns=["H_last_quarter", "last_label_quarter"]).equals(Xb)
    for a, f in L.CANDIDATES.items():
        got = f(d2, t, k)
        assert all(abs(got[p] - base[a][p]) < 1e-12 for p in C.PROVS), a


def P_usable(d):
    return C.P._usable_from(d.rounds).fillna(pd.Timestamp("2100-01-01"))


def test_no_row_outside_the_study_window(d):
    assert d.S1["tq"].min() >= C.qk("2021-Q1") and d.S1["tq"].max() <= C.qk("2026-Q3")
    assert min(t for _, t in d.rice) >= C.qk("2021-Q1")
    assert max(t for _, t in d.rice) <= C.qk("2026-Q3")
