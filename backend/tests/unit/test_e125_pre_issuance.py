"""
tests/unit/test_e125_pre_issuance.py
------------------------------------
E125 pre-issuance refresh: NASA POWER 2026 coverage and E119-method reproduction; complete 2026-Q3 cyclone counts
(storms de-duplicated, local counts consistent with track distances, PAR national); September 2026 LFS handling;
CPI release evidence vs FIRI3 issues; Amendment 1 and 2; all 34 feature decisions; reproducibility; frozen
configuration; FIRI v2 regression; the real store untouched and immutable.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.inference import firi3 as F3

REPO = Path(__file__).resolve().parents[2].parent
E = REPO / "aipheed-backend-aligned" / "experiments" / "E125_FIRI3_Pre_Issuance"
E124 = REPO / "aipheed-backend-aligned" / "experiments" / "E124_FIRI3_Prospective_Validation"
HAS = (E / "out" / "summary.json").exists()
pytestmark = pytest.mark.skipif(not HAS, reason="E125 outputs missing")


@pytest.fixture(scope="module")
def s():
    return json.loads((E / "out" / "summary.json").read_text())


def test_nasa_power_coverage(s):
    a = pd.read_csv(E / "E125_NASA_POWER_REFRESH_AUDIT.csv")
    y26 = a[a["month"].str.startswith("2026")]
    present = y26[y26["value_refreshed"].notna()]
    assert set(present["month"]) == {f"2026-{m:02d}" for m in range(1, 10)}
    assert present.groupby("month")["unit"].nunique().eq(5).all() and set(present["item"]) == {"PRECTOTCORR", "T2M"}
    assert s["nasa"]["method_reproduces_e119"] and "2026-Q3" in s["nasa"]["complete_quarters_2026"]
    assert set(y26.loc[y26["value_refreshed"].isna(), "month"]) <= {"2026-10", "2026-11", "2026-12"}       # never interpolated


def test_cyclone_quarter_complete_and_deduplicated(s):
    assert s["cyclones"]["quarter_complete"] and s["cyclones"]["last_fix_in_file"] >= "2026-09-30"
    c = pd.read_csv(E / "E125_CYCLONE_REFRESH_AUDIT.csv")
    q3 = c[c["quarter"] == "2026-Q3"]
    par = q3[q3["scope"] == "PAR"].iloc[0]
    storms = [x.split("(")[0].strip() for x in par["storms"].split(";")]
    assert par["count_refreshed"] == 7 == len(set(storms))                                  # WP172026 SAUDEL once, not twice
    assert set(q3.loc[q3["scope"] == "local 100 km", "unit"]) == set(F3.PROVINCES)
    assert set(q3.loc[q3["scope"] == "PAR", "unit"]) == {"PHILIPPINES"}
    hist = c[(c["quarter"] < "2026-Q3")]
    bad = hist[~hist["match"]]
    assert set(zip(bad["scope"], bad["quarter"])) <= {("PAR", "2025-Q1")}                   # the documented zero quarter (D-E125-2)


@pytest.mark.skipif(not (E / "data" / "raw" / "ibtracs.last3years.list.v04r01.csv").exists(), reason="IBTrACS raw file not present (not tracked; hash in refresh_log.json)")
def test_local_counts_match_track_distances():
    spec = importlib.util.spec_from_file_location("e125_run", E / "runner" / "run_e125.py")
    R = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(R)
    t = pd.read_csv(E / "data" / "raw" / "ibtracs.last3years.list.v04r01.csv", skiprows=[1], usecols=["SID", "ISO_TIME", "LAT", "LON"], low_memory=False)
    t["LAT"], t["LON"] = pd.to_numeric(t["LAT"], errors="coerce"), pd.to_numeric(t["LON"], errors="coerce")
    t["ISO_TIME"] = pd.to_datetime(t["ISO_TIME"], errors="coerce")
    q = t[(t["ISO_TIME"] >= "2026-07-01") & (t["ISO_TIME"] < "2026-10-01")]
    c = pd.read_csv(E / "E125_CYCLONE_REFRESH_AUDIT.csv")
    for prov, (la, lo) in R.PF_CENTROIDS.items():
        n = q[R.hav(la, lo, q["LAT"].to_numpy(), q["LON"].to_numpy()) <= 100]["SID"].nunique()
        got = c[(c["scope"] == "local 100 km") & (c["unit"] == prov) & (c["quarter"] == "2026-Q3")]["count_refreshed"].iloc[0]
        assert n == got


def test_september_lfs_and_complete_quarter(s):
    assert s["lfs"]["q3_months_present"] == ["July", "August"]
    el = pd.read_csv(E / "E125_FEATURE_ELIGIBILITY_AUDIT.csv").set_index("feature")
    assert el.loc["EHS_unemployment_change_R", "decision"] == "BLOCKED"                     # 2 of 3 months is not a complete quarter
    assert "September" in el.loc["EHS_unemployment_change_R", "reason"]


def test_cpi_release_evidence(s):
    assert s["cpi"]["uses_where_evidence_is_on_or_after_issue"] == 0
    assert s["cpi"]["min_margin_days_rule_to_issue"] > s["cpi"]["archived_release_minus_day10_days"]["max"]
    cc = pd.read_csv(E / "out" / "cpi_release_evidence_checks.csv")
    assert (cc["rule_avail"].astype(str) < cc["issue_date"].astype(str)).all()


def test_all_34_feature_decisions():
    el = pd.read_csv(E / "E125_FEATURE_ELIGIBILITY_AUDIT.csv")
    assert len(el) == len(F3.FEATURES) == 34 and set(el["feature"]) == {f.code for f in F3.FEATURES}
    assert set(el["decision"]) <= {"READY", "READY WITH WARNING", "BLOCKED", "NOT APPLICABLE"}
    assert el["cutoff_2021_ok"].all() and el["amendment_1_ok"].all() and el["geography_ok"].all()
    assert set(el.loc[el["decision"] == "READY", "publication_class"]) == {"verified"}          # nothing promoted
    ehs = el[el["feature"].isin(["EHS_unemployment_prov", "EHS_underemployment_prov"])]
    assert (ehs["period_used"] == 2024).all() or (ehs["period_used"].astype(str) == "2024").all()   # Amendment 2 fallback
    pv = pd.read_csv(E / "E125_PUBLICATION_DATE_VERIFICATION.csv")
    assert (pv["classification"] == pv["e125_classification"]).all()


def test_reconciliation_explained_and_reproducible(s):
    assert s["reproducible"] and s["previous_reproduces_e123"] and s["reconciliation"]["explained"]
    r = pd.read_csv(E / "E125_SCORE_RECONCILIATION.csv")
    ch = r[r["changed"]]
    assert set(ch["origin"]) <= {"2026-Q2", "2026-Q3"} and not r["calculation_defect"].any()
    assert ch["causes"].str.contains("newly available observations").all()


def test_frozen_configuration_and_hashes(s):
    assert s["frozen_ok"] and s["hashes_ok"]
    spec = importlib.util.spec_from_file_location("e124_store_t", E124 / "runner" / "store.py")
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    cfg = json.loads((E124 / "E124_FROZEN_VALIDATION_CONFIGURATION.json").read_text())
    assert hashlib.sha256(S.canonical(cfg)).hexdigest() == (E124 / "E124_FROZEN_VALIDATION_CONFIGURATION.sha256").read_text().strip()


def test_real_store_untouched_and_duplicate_issue_refused(tmp_path, s):
    assert s["store"]["forecasts"] == [] and [e[0] for e in s["store"]["events"]] == ["attempt_blocked"]
    assert not any((E124 / "store" / "forecasts").iterdir())
    spec = importlib.util.spec_from_file_location("e124_store_d", E124 / "runner" / "store.py")
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    shutil.copytree(E124 / "store", tmp_path / "store")                                     # copy: the real registry is not touched
    st = S.Store(tmp_path / "store")
    T0 = F3.START_Q
    o = pd.DataFrame([{"feature": "typhoons_local_100km", "unit": u, "period": T0 + i, "value": float(i % 3), "avail": F3.issue_date(T0 + i), "status": "verified",
                       "source": "test"} for i in range(16) for u in F3.PROVINCES])
    a = pd.DataFrame(columns=["feature", "unit", "ref", "value", "avail", "status", "source"])
    with pytest.raises(RuntimeError):
        st.issue("2026-Q4", o, a, "cfg", {}, date(2026, 10, 31), {"failed": {}})         # before the issue date
    origin = F3.qlabel(T0 + 15)
    st.issue(origin, o, a, "cfg", {}, date(2025, 1, 1), {"failed": {}})
    with pytest.raises(FileExistsError):
        st.issue(origin, o, a, "cfg", {}, date(2025, 1, 2), {"failed": {}})


def test_firi_v2_untouched(s):
    from app.ml.inference import firi as FI
    raw = {k: {"x": v, "status": "observed" if v is not None else "missing", "note": ""} for k, v in
           {"A1": .7, "A2": 1.2, "A3": 3.0, "V1": .4, "C1": 0.0, "C2": 2.0, "C3": -5.0, "C4": 1.0, "E1": .3, "E2": -2.0, "N1": None, "H1": .6}.items()}
    r = FI.score_v2(raw, {k: [float(i) for i in range(-5, 10)] for k in FI.CONTINUOUS}, {"A": .5, "C": 1.5, "H": 1.0, "V": .5})
    assert r["firi"] == pytest.approx(0.3929012345679012, abs=1e-15) and s["production_clean"]
