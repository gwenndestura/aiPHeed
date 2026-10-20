"""E71 tests. V4 scenario tests use SYNTHETIC indicator values (marked as such) and need no model library; the
remaining tests check the protocol freeze, the seals, the as-of timing and the scored decision.

    python -m pytest -q aipheed-backend-aligned/experiments/E71_Food_Insecurity_Dimensions/tests
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E71 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E71 / "runner"))
import e71_index as Z  # noqa: E402

KEYS = ["a1", "a2", "a3", "v1", "v2", "s1", "s2", "gap"]


# ------------------------------------------------------------------------------------------------ SYNTHETIC scenarios
def _synthetic_reference():
    """SYNTHETIC: 8 reference quarters x 5 provinces with ordinary variation (not real data)."""
    rng = np.random.default_rng(0)
    rows = []
    for q in range(Z.REF[0], Z.REF[1] + 1):
        for p in range(5):
            rows.append({"province_code": f"P{p}", "q": q, "quarter": str(q), "a1": rng.normal(4, 1.5),
                         "a2": rng.normal(15, 1), "a3": rng.normal(4, 2), "v1": rng.normal(0, 8), "v2": rng.normal(0, 6),
                         "s1": float(rng.integers(0, 3)), "s2": 0.0, "gap": rng.normal(0, 1)})
    return pd.DataFrame(rows)


NORMAL = {"a1": 4.0, "a2": 15.0, "a3": 4.0, "v1": 0.0, "v2": 0.0, "s1": 1.0, "s2": 0.0, "gap": 0.0}
SCEN = {  # SYNTHETIC situations from the brief
    "high_inflation_stable_access": {"a1": 10.0},
    "low_inflation_falling_income": {"a1": 1.0, "a2": 20.0, "a3": -8.0},
    "low_production_stable_prices": {"v1": -25.0, "v2": -20.0},
    "climate_shock": {"s1": 4.0, "s2": 1.0},
    "multiple_shocks": {"a1": 10.0, "a2": 20.0, "a3": -8.0, "v1": -25.0, "v2": -20.0, "s1": 4.0, "s2": 1.0},
    "baseline": {},
}


@pytest.fixture(scope="module")
def scen():
    ref_rows = _synthetic_reference()
    ref = Z.reference(ref_rows)
    rows = pd.DataFrame([{"province_code": k, "q": 9000, "quarter": "S", **(NORMAL | v)} for k, v in SCEN.items()])
    S = Z.score(rows, ref).set_index("province_code")
    thr = Z.threshold(Z.score(ref_rows, ref))
    return S, thr


def test_v4_scenarios_are_distinguished(scen):
    S, thr = scen
    top = S[list(Z.DIMS)].idxmax(axis=1)
    assert top["low_inflation_falling_income"] == "ACCESS" and S.loc["low_inflation_falling_income", "p_a1"] < 0.3
    assert top["low_production_stable_prices"] == "AVAILABILITY" and S.loc["low_production_stable_prices", "ACCESS"] < 0.75
    assert top["climate_shock"] == "STABILITY" and S.loc["climate_shock", "STABILITY"] > 0.75
    # high food inflation alone stresses one of the three ACCESS indicators only: no dimension above 0.75
    assert S.loc["high_inflation_stable_access", "n_stressed"] == 0
    assert S.loc["multiple_shocks", "n_stressed"] == 3
    assert S.loc["multiple_shocks", "FIR71"] == S["FIR71"].max() and S.loc["multiple_shocks", "FIR71"] > thr
    # the profiles of the single-shock situations differ from each other (no single score hides them)
    prof = S.loc[["low_inflation_falling_income", "low_production_stable_prices", "climate_shock"], list(Z.DIMS)]
    assert prof.round(2).drop_duplicates().shape[0] == 3


def test_v4_price_alone_cannot_dominate(scen):
    S, _ = scen
    # a maximal food-price shock moves FIR71 by at most one third of the indicator range share of ACCESS
    d = S.loc["high_inflation_stable_access", "FIR71"] - S.loc["baseline", "FIR71"]
    assert 0 < d <= 1 / 9 + 1e-9


def test_missing_is_never_zero():
    ref = Z.reference(_synthetic_reference())
    row = pd.DataFrame([{"province_code": "X", "q": 9000, "quarter": "S", **NORMAL, "v1": np.nan, "v2": np.nan}])
    S = Z.score(row, ref)
    assert np.isnan(S.loc[0, "AVAILABILITY"]) and np.isnan(S.loc[0, "FIR71"])     # INSUFFICIENT, not "no risk"
    row2 = row.assign(v1=-5.0)
    assert np.isfinite(Z.score(row2, ref).loc[0, "AVAILABILITY"])                  # one observed indicator suffices


def test_vulnerability_is_not_in_the_class_rule():
    assert "poverty" not in str(Z.DIMS) and set(Z.ADVERSE_HIGH) == set(KEYS)


# ------------------------------------------------------------------------------------------------ seals, timing, decision
def test_protocol_frozen_and_seals():
    b = (E71 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(b).hexdigest() == (E71 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    for n in ("predictions.csv", "prospective.csv"):
        assert hashlib.sha256((E71 / "sealed" / n).read_bytes()).hexdigest() == (E71 / "sealed" / f"{n}.sha256").read_text().split()[0]


def test_sealed_rows_timing():
    P = pd.read_csv(E71 / "sealed" / "predictions.csv")
    qi = lambda q: int(q[:4]) * 4 + int(q[-1]) - 1  # noqa: E731
    assert ((P["target"].map(qi) - P["origin_quarter"].map(qi)) == P["lead"]).all()
    assert (P["PERSIST_from"].map(qi) <= P["origin_quarter"].map(qi) - 1).all()          # last known label <= t-1
    assert not P.duplicated(["lead", "target", "province_code"]).any()
    assert "HIGH" not in P.columns and "FIR71" not in P.columns                         # no outcome in the seal


def test_scored_decision_matches_protocol():
    s = json.loads((E71 / "out" / "score.json").read_text(encoding="utf-8"))
    dec, m = s["decision"], s["leads"]["2"]["metrics"][s["decision"]["selected"]]
    assert dec["criteria"]["accuracy_ge_0.80"] == (m["accuracy"] >= 0.80)
    assert dec["goal_80_met_as_proxy_prediction"] == all(dec["criteria"].values())
    assert dec["food_insecurity_accuracy_claimable"] == (dec["goal_80_met_as_proxy_prediction"] and s["V1"]["supported"])
    assert dec["unseen"] is False
    assert all(v == 0 for v in s["nan_predictions"].values())


def test_annotation_scorer_on_synthetic_labels(tmp_path):
    """SYNTHETIC labels in a temp copy only; the real sample files stay unlabelled."""
    import csv
    import e71_annotation as A
    rows = list(csv.DictReader(A.A1.open(encoding="utf-8")))
    assert all(r["human_relevant"] == "" for r in rows)
    keys = {k["sample_id"]: k for k in csv.DictReader(A.KEY.open(encoding="utf-8"))}
    for name, flip in (("a1.csv", set()), ("a2.csv", {rows[0]["sample_id"]})):
        with (tmp_path / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            for r in rows:
                m = keys[r["sample_id"]]["model_admitted"]
                h = str(1 - int(m)) if r["sample_id"] in flip else m           # agree with the model except one row
                w.writerow({**r, "human_relevant": h})
    s = A.score(tmp_path / "a1.csv", tmp_path / "a2.csv")
    assert s["status"] == "ANNOTATED" and s["weighted_precision"] == 1.0 and s["weighted_recall"] == 1.0
    assert 0.9 < s["kappa_relevance"] < 1.0 and s["consensus_rows"] == len(rows) - 1
    assert A.score()["status"] == "NOT_ANNOTATED"
