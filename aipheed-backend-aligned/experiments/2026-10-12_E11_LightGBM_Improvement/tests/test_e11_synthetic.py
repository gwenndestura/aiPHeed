"""E11 synthetic tests: no project data is read (guard decisions on path strings; logic on in-memory data)."""
import numpy as np
import pandas as pd
import pytest

import e11_lib as L
import guard

AL = guard.AL
PROV = ("P1", "P2", "P3", "P4", "P5")


def qi(q):
    y, k = q.split("-Q")
    return int(y) * 4 + int(k) - 1


def qstart(q):
    y, k = q.split("-Q")
    return pd.Timestamp(year=int(y), month=3 * (int(k) - 1) + 1, day=1)


def test_guard_e9_folder_read_only_and_protected_still_denied():
    e9 = AL / "experiments" / "2026-10-12_E9_S1_safe_training" / "runs" / "x" / "scored_rows.csv"
    assert guard.decide(str(e9), write=False) == "allow"
    assert guard.decide(str(e9), write=True) == "deny"
    assert guard.decide(str(AL / "data" / "processed" / "sws_hunger.parquet"), write=False) == "deny"
    assert guard.decide(r"C:\Users\admin\aipheed\backend\data\thesis\panel.parquet", write=False) == "deny"
    assert guard.decide(str(guard.EXP / "runs" / "y.csv"), write=True) == "allow"


def _stress():
    rows = []
    for i, q in enumerate(["2023-Q1", "2023-Q2", "2023-Q3"]):
        for j, p in enumerate(PROV):
            dev = float(j - 2)
            rows.append({"province_code": p, "quarter": q, "sws_hunger_pct": 10.0 + i, "deviation": dev,
                         "stress": 10.0 + i + 2 * dev})
    return pd.DataFrame(rows)


def test_label_history_features_use_only_published_labels():
    st = _stress()
    pub = {"2023-Q1": pd.Timestamp("2023-05-01"), "2023-Q2": pd.Timestamp("2023-08-01"), "2023-Q3": pd.Timestamp("2023-10-20")}
    frame = pd.DataFrame({"target_quarter": ["2023-Q4"] * 5 + ["2024-Q1"] * 5, "province_code": list(PROV) * 2})
    h = L.label_history_features(frame, st, pub.get, qi, qstart).set_index(["target_quarter", "province_code"])
    # at 2023-10-01 only Q1 and Q2 are published -> anchor Q2, previous Q1
    assert h.at[("2023-Q4", "P1"), "anchor_check"] == "2023-Q2" and h.at[("2023-Q4", "P1"), "prev_anchor"] == "2023-Q1"
    assert h.at[("2023-Q4", "P1"), "anchor_dev"] == -2.0 and h.at[("2023-Q4", "P1"), "lps_change"] == 1.0
    assert h.at[("2024-Q1", "P5"), "anchor_check"] == "2023-Q3"


def test_structures_recombine_to_stress():
    rows = pd.DataFrame({"stress": [12.0, 8.0], "deviation": [1.0, -1.0], "sws_hunger": [10.0, 10.0], "s1rule": [11.0, 9.0]})
    assert np.allclose(L.combine("decomp", rows, L.target_for("decomp", rows)), [12.0, 8.0])
    assert np.allclose(L.combine("resid", rows, L.target_for("resid", rows)), rows["stress"])
    assert np.allclose(L.combine("direct", rows, L.target_for("direct", rows)), rows["stress"])
    assert L.mono_for("decomp", ["sws_hunger"]) == [0] and L.mono_for("direct", ["sws_hunger", "x"]) == [1, 0]


def test_inner_folds_respect_publication_and_minimum():
    qs = [f"202{y}-Q{k}" for y in (1, 2, 3) for k in (1, 2, 3, 4)]
    pub = {q: qstart(q) + pd.Timedelta(days=100) for q in qs}       # each label published ~one quarter after its end
    inner = L.inner_quarters(qs, pub.get, qi, qstart)
    for qt, itr in inner:
        assert len(itr) >= L.MIN_INNER_TRAIN_Q
        assert all(pub[q] < qstart(qt) and qi(q) < qi(qt) for q in itr)


def test_choose_prefers_simpler_on_ties_and_falls_back():
    c, _ = L.choose({"C2_stumps": [1.0], "C1_shallow_reg": [1.0], "C0_e9_default": [2.0], "C3_moderate": [0.5]})
    assert c == "C3_moderate"
    c, _ = L.choose({"C2_stumps": [1.0], "C1_shallow_reg": [1.0], "C0_e9_default": [1.0], "C3_moderate": [1.0]})
    assert c == "C2_stumps"
    c, _ = L.choose({k: [] for k in L.CONFIGS})
    assert c == L.ORDER[0]


def test_within_quarter_share_and_signflip():
    f = pd.DataFrame({"target_quarter": ["a"] * 3 + ["b"] * 3, "x": [1, 1, 1, 5, 5, 5], "y": [0, 1, 2, 0, 1, 2]})
    s = L.within_quarter_share(f, ["x", "y"])
    assert s["x"] == 0.0 and s["y"] == 1.0
    assert L.signflip_p([-1.0] * 7) == pytest.approx(2 / 128)
    assert L.signflip_p([1, -1, 1, -1, 1, -1, 0]) > 0.5


def test_regressor_fits_are_deterministic():
    rng = np.random.default_rng(0)
    tr = pd.DataFrame({"last_published_stress": rng.normal(15, 3, 60), "sws_hunger": rng.normal(15, 3, 60),
                       "sws_change": rng.normal(0, 1, 60)})
    tr["stress"] = tr["sws_hunger"] + rng.normal(0, 1, 60)
    te = tr.head(5)
    a, *_ = L.fit_predict_reg("direct", tr, te, L.FS["core"], "C1_shallow_reg")
    b, *_ = L.fit_predict_reg("direct", tr, te, L.FS["core"], "C1_shallow_reg")
    assert np.array_equal(a, b)
