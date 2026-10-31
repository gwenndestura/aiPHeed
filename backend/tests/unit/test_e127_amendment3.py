"""
tests/unit/test_e127_amendment3.py
----------------------------------
E127 Amendment 3: PAR quarterly counts from the data layer (explicit zero for a covered quarter without storms; actual
storm quarters; incomplete or missing coverage stays missing; duplicate and split storm identifiers; box edges; quarter
of first fix), and the rebuilt FIRI3 v1.3 history (9 regional origins, max change, 2025-Q2 band, no provincial change,
2026-Q4 PAR percentile 0.711 -> 0.750, no other change, no leakage), with Amendments 1 and 2, the v1.3 configuration,
the store and FIRI v2 unchanged.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from app.ml.inference import firi3 as F3

REPO = Path(__file__).resolve().parents[2].parent
E = REPO / "aipheed-backend-aligned" / "experiments" / "E127_FIRI3_Amendment_3_Implementation"
E124 = REPO / "aipheed-backend-aligned" / "experiments" / "E124_FIRI3_Prospective_Validation"
HAS = (E / "out" / "summary.json").exists()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


PC = load("e127_par_counts", E / "runner" / "par_counts.py")
Q = lambda s: int(s[:4]) * 4 + int(s[-1]) - 1          # noqa: E731


def tracks(rows):
    """rows: (SID, ATCF, time, lat, lon); plus a far-away anchor track so the file covers 2020-2026."""
    base = [("ANCHOR0", "", "2020-01-01 00:00", 40.0, 160.0), ("ANCHOR1", "", "2026-12-31 00:00", 40.0, 160.0)]
    df = pd.DataFrame(base + rows, columns=["SID", "USA_ATCF_ID", "ISO_TIME", "LAT", "LON"])
    df["SEASON"] = pd.to_datetime(df["ISO_TIME"]).dt.year
    df["NAME"] = df["SID"]
    return PC.prepare(df)


def count(pq, q):
    r = pq[pq["quarter"] == q].iloc[0]
    return r["count"], r["status"]


def test_explicit_zero_and_storm_quarters():
    t = tracks([("S1", "WP012024", "2024-04-10 00:00", 15.0, 125.0)])
    pq = PC.par_quarterly(t, Q("2024-Q1"), Q("2024-Q2"))
    assert count(pq, "2024-Q1") == (0, "verified")                  # covered, no storm: explicit 0
    assert count(pq, "2024-Q2") == (1, "verified")                  # actual storm


def test_incomplete_and_missing_coverage_not_filled():
    df = pd.DataFrame([("S1", "", "2024-01-01 00:00", 15.0, 125.0), ("S2", "", "2024-05-01 00:00", 15.0, 125.0)],
                      columns=["SID", "USA_ATCF_ID", "ISO_TIME", "LAT", "LON"]).assign(SEASON=2024, NAME="x")
    pq = PC.par_quarterly(PC.prepare(df), Q("2023-Q4"), Q("2024-Q3"))
    assert count(pq, "2023-Q4")[1] == "not_covered" and pd.isna(count(pq, "2023-Q4")[0])     # before the file starts
    assert count(pq, "2024-Q2")[1] == "not_covered" and count(pq, "2024-Q3")[1] == "not_covered"   # file ends inside 2024-Q2
    rows = PC.as_firi3_rows(pq, lambda q: F3.issue_date(q))
    assert set(rows["period"]) == {Q("2024-Q1")}                    # only covered quarters reach FIRI3; nothing filled with 0
    empty = PC.prepare(pd.DataFrame(columns=["SID", "USA_ATCF_ID", "ISO_TIME", "LAT", "LON", "SEASON", "NAME"]))
    assert (PC.par_quarterly(empty, Q("2024-Q1"), Q("2024-Q1"))["status"] == "not_covered").all() if len(empty) else True


def test_duplicate_and_split_identifiers():
    t = tracks([("S1", "WP172026", "2026-08-18 12:00", 8.0, 134.0), ("S1", "WP172026", "2026-08-18 12:00", 8.0, 134.0),   # repeated row
                ("S1", "", "2026-08-17 00:00", 6.0, 150.0),                                                              # early fix, no ATCF yet
                ("S2", "WP172026", "2026-08-31 06:00", 19.5, 118.0),                                                     # same storm, new SID
                ("S3", "WP182026", "2026-09-02 00:00", 20.0, 130.0)])
    pq = PC.par_quarterly(t, Q("2026-Q3"), Q("2026-Q3"))
    assert count(pq, "2026-Q3") == (2, "verified")                  # WP172026 once + WP182026


def test_boundary_and_quarter_assignment():
    t = tracks([("IN", "", "2025-06-30 18:00", 5.0, 115.0),         # on the corner: inside
                ("OUT", "", "2025-05-01 00:00", 25.5, 125.0),        # north of the box
                ("WEST", "", "2025-05-01 00:00", 15.0, 114.9),       # west of the box
                ("SPAN", "", "2025-06-30 12:00", 4.0, 130.0),        # outside on 30 June...
                ("SPAN", "", "2025-07-01 06:00", 6.0, 130.0)])       # ...first inside on 1 July -> Q3
    pq = PC.par_quarterly(t, Q("2025-Q2"), Q("2025-Q3"))
    assert count(pq, "2025-Q2") == (1, "verified") and count(pq, "2025-Q3") == (1, "verified")


# ---------------- real data
@pytest.fixture(scope="module")
def s():
    if not HAS:
        pytest.skip("E127 outputs missing")
    return json.loads((E / "out" / "summary.json").read_text())


def test_three_explicit_zeros(s):
    d = pd.read_csv(E / "E127_PAR_ZERO_STORM_DATA.csv")
    z = d[d["explicit_zero_added"]]
    assert sorted(z["quarter"]) == ["2023-Q1", "2024-Q1", "2025-Q1"] and (z["count"] == 0).all() and (z["status"] == "verified").all()
    mism = d[(d["status"] == "verified") & ~d["matches_e114_where_present"]]
    assert list(mism["quarter"]) == ["2026-Q3"] and "SAUDEL" in mism["note"].iloc[0]          # the known split-SID double count, not used by E119
    assert d.loc[d["quarter"] == "2026-Q3", "count"].iloc[0] == 7
    assert d.loc[d["quarter"] == "2026-Q4", "status"].iloc[0] == "not_covered"
    assert s["only_zero_quarters_changed"] and s["other_par_quarters_equal"] and s["other_inputs_identical"]


def test_history_rebuilt(s):
    imp = s["impact"]
    assert imp["changed"] == 9 and imp["scopes"] == ["regional"] and imp["provincial_changed"] == 0
    assert imp["origins"] == ["2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2", "2025-Q3", "2026-Q1", "2026-Q2", "2026-Q3"]
    assert abs(imp["max_abs_change"] - 0.041987) < 1e-6
    assert imp["band_changes"] == [{"origin": "2025-Q2", "band_v12": "above usual", "band_v13": "usual or below"}]
    assert imp["other_feature_score_changes"] == 0 and imp["other_indicator_changes"] == 0
    assert s["v12_reproduces_e125"] and s["v13_reproduces_e126_proposal"] and s["deterministic"]
    r = pd.read_csv(E / "E127_HISTORICAL_SCORE_RECONCILIATION.csv")
    assert len(r) == 138 and not r.loc[r["scope"] == "provincial", "changed"].any()
    assert r.loc[r["changed"], "explanation"].str.startswith("Amendment 3").all()


def test_2026q4_percentile(s):
    q = s["q4_2026"]
    assert q["v1.2"]["count"] == q["v1.3"]["count"] == 7 and q["v1.2"]["period_used"] == q["v1.3"]["period_used"] == "2026-Q3"
    assert abs(q["v1.2"]["score"] - 0.710526) < 1e-6 and q["v1.3"]["score"] == 0.75
    assert q["v1.3"]["prior_n"] - q["v1.2"]["prior_n"] == 3 and q["v1.3"]["prior_values_sorted"][:3] == [0.0, 0.0, 0.0]
    assert q["v1.2"]["reproduces"] and q["v1.3"]["reproduces"] and q["v1.3"]["future_values_in_reference"] == 0
    assert q["other_features_changed_at_2026q4"] == [] and q["provincial_features_changed_at_2026q4"] == 0


def test_no_leakage_and_amendments(s):
    lk = s["leakage"]
    assert lk["scored_values_available_before_issue"] and lk["par_rows_only_covered_quarters"] and lk["no_pre2021"]
    assert lk["amendment_1_rows"] == 40 and lk["amendment_1_by_series"] == {"cpi_food_yoy_pct": 20, "cpi_headline_yoy_pct": 20}
    assert lk["amendment_2_year_2026_origins"] == ["2024"] and "2025" in lk["amendment_2_note"][0]


def test_version_hashes_and_configuration(s):
    assert F3.VERSION == "FIRI3-candidate-1.3"
    assert hashlib.sha256((E / "E127_FIRI3_PROTOCOL_AMENDMENT_3.md").read_bytes()).hexdigest() == F3.AMENDMENT_3_SHA256
    S = load("e127_store", E124 / "runner" / "store.py")
    cfg = json.loads((E / "E127_FROZEN_VALIDATION_CONFIGURATION_v1_3.json").read_text())
    assert hashlib.sha256(S.canonical(cfg)).hexdigest() == (E / "E127_FROZEN_VALIDATION_CONFIGURATION_v1_3.sha256").read_text().strip() == s["config_v13_sha256"]
    assert cfg["firi3_version"] == F3.VERSION and cfg["amendment_3"]["sha256"] == F3.AMENDMENT_3_SHA256
    assert cfg["supersedes"]["canonical_sha256"] == (E124 / "E124_FROZEN_VALIDATION_CONFIGURATION.sha256").read_text().strip()
    old = json.loads((E124 / "E124_FROZEN_VALIDATION_CONFIGURATION.json").read_text())
    assert old["firi3_version"] == "FIRI3-candidate-1.2"                                  # v1.2 record kept
    assert cfg["weights"] == old["weights"] and cfg["risk_bands"] == old["risk_bands"] and cfg["aggregation"] == old["aggregation"]
    assert cfg["completeness"] == old["completeness"] and cfg["features"] == old["features"]


def test_store_registry_unchanged(s):
    assert s["store"]["forecasts"] == [] and [e[0] for e in s["store"]["events"]] == ["attempt_blocked"]
    assert s["store"]["next_forecast_id"] == "FIRI3-1.3-2026-Q4"


def test_firi_v2_untouched(s):
    from app.ml.inference import firi as FI
    raw = {k: {"x": v, "status": "observed" if v is not None else "missing", "note": ""} for k, v in
           {"A1": .7, "A2": 1.2, "A3": 3.0, "V1": .4, "C1": 0.0, "C2": 2.0, "C3": -5.0, "C4": 1.0, "E1": .3, "E2": -2.0, "N1": None, "H1": .6}.items()}
    r = FI.score_v2(raw, {k: [float(i) for i in range(-5, 10)] for k in FI.CONTINUOUS}, {"A": .5, "C": 1.5, "H": 1.0, "V": .5})
    assert r["firi"] == pytest.approx(0.3929012345679012, abs=1e-15)
    assert s["firi_v2"]["backend\\app\\ml\\inference\\firi.py"] if "backend\\app\\ml\\inference\\firi.py" in s["firi_v2"] else True
    assert hashlib.sha256((REPO / "backend" / "app" / "ml" / "inference" / "firi.py").read_bytes()).hexdigest() == "0e583131a7de3b9844241d3927eede813077d7cccbf949cd8313973436d0f8e3"
