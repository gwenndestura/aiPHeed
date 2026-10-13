"""E15 synthetic tests (no project data is read). Run: python -B -m pytest -q -p no:cacheprovider tests"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "runner"))
import guard  # noqa: E402
import two_layer as TL  # noqa: E402

CODES = list(TL.PROVINCES)


def fixture_F(quarters, values=None, missing=()):
    rows = []
    rng = np.random.default_rng(1)
    for q in quarters:
        for i, pc in enumerate(CODES):
            v = values[q][i] if values and q in values else float(rng.normal(5, 2))
            if (q, pc) in missing:
                v = np.nan
            rows.append({"quarter": q, "province_code": pc, "F": v})
    return pd.DataFrame(rows)


def fixture_rounds(spec):
    """spec: list of (quarter, H, published, definition_A)."""
    return pd.DataFrame([{"quarter": q, "H": h, "published": pd.Timestamp(p), "date_type": "verified",
                          "definition_A": a, "source": "synthetic", "round": f"round {q} {p}"}
                         for q, h, p, a in spec])


QS = ["2030-Q1", "2030-Q2", "2030-Q3", "2030-Q4"]
ROUNDS = fixture_rounds([("2030-Q1", 10.0, "2030-05-01", True), ("2030-Q2", 12.0, "2030-08-01", True),
                         ("2030-Q2", 14.0, "2030-09-01", True), ("2030-Q4", 9.0, "2031-02-01", True)])


def build(F=None, rounds=ROUNDS, quarters=QS):
    return TL.build_two_layer(F if F is not None else fixture_F(quarters), rounds, quarters, data_through="2030-Q4")


# 1 -----------------------------------------------------------------------------------------------
def test_D_sums_to_zero_for_complete_data():
    out = build()
    for q in out["quarters"]:
        pl = q["provincial_layer"]
        assert pl["status"] == "COMPLETE"
        assert abs(sum(p["relative_pressure_D_pp"] for p in pl["provinces"])) < 1e-12
        assert sorted(p["relative_pressure_rank"] for p in pl["provinces"]) == [1, 2, 3, 4, 5]


# 2 -----------------------------------------------------------------------------------------------
def test_missing_inflation_gives_no_D_no_rank_and_no_zero_fill():
    F = fixture_F(QS, missing={("2030-Q2", "PH040300000")})
    out = build(F)
    q2 = next(q for q in out["quarters"] if q["quarter"] == "2030-Q2")
    pl = q2["provincial_layer"]
    assert pl["status"] == "INCOMPLETE_NO_D_OR_RANK" and pl["missing_provinces"] == ["Quezon"]
    assert pl["five_province_mean_F_pct_unweighted"] is None
    for p in pl["provinces"]:
        assert p["relative_pressure_D_pp"] is None and p["relative_pressure_rank"] is None
        if p["province"] == "Quezon":
            assert p["food_inflation_yoy_pct"] is None          # null, never 0
        else:
            assert p["food_inflation_yoy_pct"] is not None
    assert q2["legacy_layer"]["status"] == "UNAVAILABLE_INCOMPLETE_PROVINCES"
    assert all(p["S1"] is None and p["label"] is None for p in q2["legacy_layer"]["provinces"])
    # other quarters unaffected
    assert all(q["provincial_layer"]["status"] == "COMPLETE" for q in out["quarters"] if q["quarter"] != "2030-Q2")


# 3 -----------------------------------------------------------------------------------------------
def test_regional_value_appears_once_per_quarter():
    out = build()
    txt = json.dumps(out)
    assert txt.count('"level_pct"') == len(QS)
    for q in out["quarters"]:
        for p in q["provincial_layer"]["provinces"]:
            assert not any("hunger" in k or "level" in k for k in p)
    t = TL.to_tables(out)
    assert len(t["regional_layer"]) == len(QS) and t["regional_layer"]["quarter"].is_unique


def test_regional_trend_uses_prior_eligible_quarter_and_records_gap():
    out = build()
    r = {q["quarter"]: q["regional_layer"] for q in out["quarters"]}
    assert r["2030-Q1"]["trend"] is None
    assert r["2030-Q2"]["level_pct"] == 13.0                     # mean of two rounds
    assert r["2030-Q2"]["trend"]["change_pct_points"] == 3.0
    assert r["2030-Q3"]["status"] == "NO_ROUND" and r["2030-Q3"]["level_pct"] is None
    assert r["2030-Q4"]["trend"] == {"change_pct_points": -4.0, "compared_with_quarter": "2030-Q2", "quarters_apart": 2}


# 4 -----------------------------------------------------------------------------------------------
def test_ties_follow_documented_rule():
    vals = {q: [5.0, 7.0, 7.0, 3.0, 1.0] for q in QS}             # Cavite, Laguna, Quezon, Rizal, Batangas
    out = build(fixture_F(QS, values=vals))
    p = {x["province"]: x for x in out["quarters"][0]["provincial_layer"]["provinces"]}
    assert p["Laguna"]["relative_pressure_rank"] == 1 and p["Quezon"]["relative_pressure_rank"] == 1
    assert p["Cavite"]["relative_pressure_rank"] == 3                # rank 2 skipped
    assert p["Rizal"]["relative_pressure_rank"] == 4 and p["Batangas"]["relative_pressure_rank"] == 5
    assert p["Laguna"]["tied_with"] == ["Quezon"] and p["Quezon"]["tied_with"] == ["Laguna"]
    assert p["Cavite"]["tied_with"] == []
    # values equal only after rounding to 9 decimals are tied; a 1e-6 difference is not
    r, _ = TL.rank_desc({"a": 1.0, "b": 1.0 + 1e-12, "c": 1.0 + 1e-6})
    assert r == {"c": 1, "a": 2, "b": 2}
    # provinces are always listed alphabetically
    assert [x["province"] for x in out["quarters"][0]["provincial_layer"]["provinces"]] == sorted(p)


def test_uniform_conditions_still_rank_but_all_tied():
    vals = {q: [4.0] * 5 for q in QS}
    out = build(fixture_F(QS, values=vals))
    ranks = [x["relative_pressure_rank"] for x in out["quarters"][0]["provincial_layer"]["provinces"]]
    assert ranks == [1, 1, 1, 1, 1]


# 5 -----------------------------------------------------------------------------------------------
def test_legacy_reproduces_S1_exactly_and_uses_strict_threshold():
    out = build()
    for q in out["quarters"]:
        lg, pl = q["legacy_layer"], q["provincial_layer"]
        if lg["status"] != "AVAILABLE":
            continue
        D = {p["province"]: p["relative_pressure_D_pp"] for p in pl["provinces"]}
        for p in lg["provinces"]:
            assert abs(p["S1"] - (lg["H_A_production_rounds_pct"] + 2 * D[p["province"]])) <= 1e-9
            assert p["label"] == ("HIGH" if p["S1"] > TL.TAU0 else "LOW")
    # S1 exactly at the threshold is LOW (strict >)
    F = fixture_F(["2030-Q1"], values={"2030-Q1": [5.0] * 5})
    r = fixture_rounds([("2030-Q1", TL.TAU0, "2030-05-01", True)])
    o = TL.build_two_layer(F, r, ["2030-Q1"], "2030-Q1")
    assert {p["label"] for p in o["quarters"][0]["legacy_layer"]["provinces"]} == {"LOW"}


def test_legacy_needs_a_production_round():
    r = fixture_rounds([("2030-Q1", 20.0, "2030-05-01", False)])
    o = TL.build_two_layer(fixture_F(["2030-Q1"]), r, ["2030-Q1"], "2030-Q1")
    q = o["quarters"][0]
    assert q["regional_layer"]["level_pct"] == 20.0               # regional layer still shown
    assert q["legacy_layer"]["status"] == "UNAVAILABLE_NO_PRODUCTION_ROUND"
    assert all(p["S1"] is None for p in q["legacy_layer"]["provinces"])


# 6 -----------------------------------------------------------------------------------------------
def test_no_banned_wording_in_any_output_field():
    out = build(fixture_F(QS, missing={("2030-Q3", "PH040100000")}))
    assert TL.wording_violations(out) == []
    for t in TL.to_tables(out).values():
        assert TL.wording_violations(list(t.columns)) == []
        assert TL.wording_violations(t.astype(str).to_numpy().ravel().tolist()) == []
    # the checker itself catches banned wording
    assert TL.wording_violations({"x": "Province is food insecure"}) and TL.wording_violations({"risk_level": 1})
    assert TL.wording_violations({"x": "not validated as food insecurity"}) == []


# 7 -----------------------------------------------------------------------------------------------
def test_output_validates_against_schema():
    import jsonschema
    schema = json.loads((EXP / "TWO_LAYER_SCHEMA.json").read_text(encoding="utf-8"))
    for out in (build(), build(fixture_F(QS, missing={("2030-Q1", "PH040500000")}))):
        jsonschema.validate(json.loads(json.dumps(out)), schema)
    bad = build()
    bad["quarters"][0]["provincial_layer"]["provinces"][0]["risk"] = "x"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(json.loads(json.dumps(bad)), schema)


# 8 -----------------------------------------------------------------------------------------------
ROOT = guard.ROOT


@pytest.mark.parametrize("path,write,want", [
    (ROOT / "backend" / "data" / "processed" / "psa_indicators.parquet", False, "deny"),
    (ROOT / "backend" / "data" / "processed" / "psa_subsistence.parquet", False, "deny"),
    (ROOT / "aipheed-backend-aligned" / "data" / "processed" / "sws_hunger.parquet", False, "deny"),
    (ROOT / "aipheed-backend-aligned" / "data" / "supplementary" / "collection_2026-10-09" /
     "provincial_food_cpi_yoy_2026H1_raw.csv", False, "deny"),
    (ROOT / "aipheed-backend-aligned" / "experiments" / "2026-10-12_E10_selection_alignment_q4" / "q4" /
     "manifest.json", False, "deny"),
    (Path.home() / ".claude" / "projects" / "x.jsonl", False, "deny"),
    (guard.E13_RUN / "metrics.json", True, "deny"),
    (ROOT / "frontend" / "src" / "App.tsx", True, "deny"),
    (guard.E12_RUN / "details.json", False, "allow"),
    (guard.E13_RUN / "scored_rows.csv", False, "allow"),
    (guard.E13_RUN / "predictions.csv", False, "deny"),
    (guard.EXP / "runs" / "x.json", True, "allow"),
])
def test_guard_decide(path, write, want):
    assert guard.decide(path, write) == want
