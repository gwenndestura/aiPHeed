"""
tests/unit/test_e126_maintenance.py
-----------------------------------
E126: PAR zero-storm verification (true zeros vs missing; storm-id de-duplication; quarter coverage), the Amendment 3
proposal kept separate, the September LFS refresh (blocked without September; complete-quarter rule; both quarterly
methods), source status and 2026-Q4 readiness, historical reconciliation, firi3 latest-row selection with repeated
index labels, Amendment 1 / 2, snapshot store immutability on controlled records, protocol hashes, FIRI v2 regression.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.inference import firi3 as F3

REPO = Path(__file__).resolve().parents[2].parent
E = REPO / "aipheed-backend-aligned" / "experiments" / "E126_FIRI3_Pre_Issuance_Maintenance"
E124 = REPO / "aipheed-backend-aligned" / "experiments" / "E124_FIRI3_Prospective_Validation"
HAS = (E / "out" / "summary.json").exists()
T0 = F3.START_Q


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def s():
    if not HAS:
        pytest.skip("E126 outputs missing")
    return json.loads((E / "out" / "summary.json").read_text())


# ---------------- PAR verification
def test_par_zero_quarters_verified(s):
    pv = pd.read_csv(E / "E126_PAR_ZERO_STORM_VERIFICATION.csv")
    assert set(pv["quarter"]) == {"2023-Q1", "2024-Q1", "2025-Q1"}
    cov = pv[pv["file_covers_quarter"]]
    for q in ("2023-Q1", "2024-Q1", "2025-Q1"):
        c = cov[cov["quarter"] == q]
        assert len(c) >= 1 and (c["verdict"] == "true zero").all()
        assert (c["storms_first_entering_box"] == 0).all() and (c["storms_first_entering_official_polygon"] == 0).all()
        assert (c["storms_active_in_box_entered_earlier"] == 0).all()
    assert (pv.loc[~pv["file_covers_quarter"], "verdict"] == "source does not cover the full quarter").all()   # partial coverage is not a zero
    assert s["par_verification"]["all_confirmed"] and s["par_verification"]["e114_other_quarters_match_recount"]


def test_zero_versus_missing_and_dedup():
    R = load("e126_run", E / "runner" / "run_e126.py")
    t = pd.DataFrame({"SID": ["A1", "A2", "B1"], "SEASON": [2025] * 3, "NAME": ["X", "X", "Y"], "ISO_TIME": ["2025-08-01", "2025-09-01", "2025-08-15"],
                      "LAT": [15.0, 16.0, 14.0], "LON": [125.0, 124.0, 128.0], "USA_ATCF_ID": ["WP172025", "WP172025", "WP182025"]})
    t["ISO_TIME"] = pd.to_datetime(t["ISO_TIME"])
    t["q"] = t["ISO_TIME"].dt.year * 4 + (t["ISO_TIME"].dt.month - 1) // 3
    atcf = t["USA_ATCF_ID"]
    key = atcf.groupby(t["SID"]).agg(lambda x: x.dropna().mode().iloc[0])
    t["STORM"] = t["SID"].map(key)
    assert t["STORM"].nunique() == 2                                                # one storm under two SIDs counts once
    z = R.with_par_zeros(pd.DataFrame(columns=["feature", "unit", "period", "value", "avail", "status", "resolution", "source"]), ["2024-Q1"])
    assert (z["value"] == 0.0).all() and z["status"].eq("verified").all() and z.index.is_unique
    assert bool(R.in_poly([125.0], [15.0])[0]) and not bool(R.in_poly([116.0], [24.0])[0])   # official outline: 24N 116E is outside


def test_amendment_3_not_applied(s):
    assert F3.VERSION == "FIRI3-candidate-1.2" and not hasattr(F3, "AMENDMENT_3_SHA256")
    imp = s["impact"]["E125 refreshed inputs"]
    assert imp["provincial_changed"] == 0 and imp["scopes"] == ["regional"] and set(imp["features_changed"]) == {"CEC_cyclones_R"}
    h = pd.read_csv(E / "E126_HISTORICAL_SCORE_RECONCILIATION.csv")
    assert h["status_e126_proposed"].eq("PROPOSED (not applied; awaits owner approval)").all()
    ch = h[h["change_e125_to_e126_proposed"].fillna("") != ""]
    assert len(ch) == imp["scores_changed"] and (ch["scope"] == "regional").all()


# ---------------- LFS
def test_lfs_refresh_blocked_without_september():
    L = load("e126_lfs", E / "runner" / "lfs_refresh.py")
    rates = pd.DataFrame({"Year": [2026] * 3, "Month": ["July", "August", "September"], "Unemployment Rate Both sexes": ["5.0", "5.2", "."]})
    levels = pd.DataFrame({"Year": [2026] * 3, "Month": ["July", "August", "September"], "Persons in the Labor Force Both sexes": ["100", "100", "."],
                           "Unemployed Persons Both sexes": ["5", "5.2", "."]})
    r = L.evaluate(rates, levels)
    assert r["status"] == "BLOCKED" and r["mean_of_rates"] is None and r["months_present"] == ["July", "August"]


def test_full_quarter_both_methods():
    L = load("e126_lfs2", E / "runner" / "lfs_refresh.py")
    rates = pd.DataFrame({"Year": [2026] * 3, "Month": ["July", "August", "September"], "Unemployment Rate Both sexes": [4.0, 5.0, 6.0]})
    levels = pd.DataFrame({"Year": [2026] * 3, "Month": ["July", "August", "September"], "Persons in the Labor Force Both sexes": [100.0, 100.0, 200.0],
                           "Unemployed Persons Both sexes": [4.0, 5.0, 12.0]})
    r = L.evaluate(rates, levels)
    assert r["complete"] and r["mean_of_rates"] == pytest.approx(5.0) and r["level_based_rate"] == pytest.approx(100 * 21 / 400)
    assert r["status"] == "READY WITH WARNING"                                      # publication date stays a rule until archived


def test_real_lfs_status(s):
    q3 = s["lfs"]["q3_2026"]
    assert q3["status"] == "BLOCKED" and q3["months_present"] == ["July", "August"] and "August 2026" in q3["titles"]["rates"]
    assert s["lfs"]["frozen_input_equals_mean_of_rates"] and s["lfs"]["max_abs_rate_difference_pp"] < 0.05


# ---------------- status, readiness, reconciliation
def test_source_status_and_readiness(s):
    st = pd.read_csv(E / "E126_SOURCE_RELEASE_STATUS.csv")
    rd = pd.read_csv(E / "E126_2026Q4_DATA_READINESS.csv")
    assert len(st) == len(rd) == 34 and set(st["feature"]) == {f.code for f in F3.FEATURES}
    assert set(st["eligibility"]) <= {"READY", "READY WITH WARNING", "BLOCKED", "NOT APPLICABLE"}
    assert set(st.loc[st["eligibility"] == "READY", "publication_class"]) == {"verified"}
    assert rd.loc[rd["feature"] == "EHS_unemployment_change_R", "decision"].iloc[0] == "BLOCKED"
    assert s["result"] == "BLOCKED" and len(s["blockers"]) == 2
    assert s["cpi_region_recheck"].get("revised") == 0


def test_historical_reconciliation_versions(s):
    h = pd.read_csv(E / "E126_HISTORICAL_SCORE_RECONCILIATION.csv")
    assert len(h) == 138
    nz = lambda c: int((h[c].fillna("") != "").sum())                                  # noqa: E731
    assert nz("change_e121_to_e122") == 73 and nz("change_e122_to_e123") == 10 and nz("change_e123_to_e125") == 12


# ---------------- firi3 robustness (C-E126-1)
def test_latest_row_with_repeated_index_labels():
    rows = [{"feature": "typhoons_PAR", "unit": "PHILIPPINES", "period": T0 + i, "value": float(i % 4), "avail": F3.issue_date(T0 + i), "status": "verified", "source": "t"}
            for i in range(12)]
    o = pd.DataFrame(rows)
    dup = pd.concat([o.iloc[:6], o.iloc[6:].set_axis(range(6))])                      # labels 0..5 appear twice
    a = pd.DataFrame(columns=["feature", "unit", "ref", "value", "avail", "status", "source"])
    r1 = F3.feature_scores(o, a, [T0 + 11])
    r2 = F3.feature_scores(dup, a, [T0 + 11])
    assert r1.to_csv(index=False) == r2.to_csv(index=False)


# ---------------- store, hashes, regression
def test_store_controlled_records(tmp_path):
    S = load("e126_store", E124 / "runner" / "store.py")
    st = S.Store(tmp_path)
    o = pd.DataFrame([{"feature": "typhoons_local_100km", "unit": u, "period": T0 + i, "value": float((i + j) % 3), "avail": F3.issue_date(T0 + i), "status": "verified",
                       "source": "t"} for i in range(16) for j, u in enumerate(F3.PROVINCES)])
    a = pd.DataFrame(columns=["feature", "unit", "ref", "value", "avail", "status", "source"])
    origin = F3.qlabel(T0 + 15)
    with pytest.raises(RuntimeError):
        st.issue(origin, o, a, "cfg", {}, date(2024, 12, 31), {"failed": {}})
    d = st.issue(origin, o, a, "cfg", {}, date(2025, 1, 1), {"failed": {}})
    fid = S.forecast_id(origin)
    assert st.reproduce(fid, o, a, "cfg", {})
    with pytest.raises(FileExistsError):
        st.issue(origin, o, a, "cfg", {}, date(2025, 1, 2), {"failed": {}})
    st.correct(fid, "controlled", o.assign(value=o["value"] + 1), a, "cfg", {}, date(2025, 2, 1))
    assert st.verify(fid)["content_ok"] and (d / "corrections" / "C001.json").exists()
    rec = st.observe(fid, o.assign(value=np.where(o["period"] == T0 + 14, 9.0, o["value"])), a, "cfg", {}, date(2025, 3, 1))
    assert rec["forecast_stability"]["original_unchanged"]
    snap = json.loads((d / "snapshot.json").read_text())
    snap["units"][0]["band"] = "high"
    (d / "snapshot.json").write_text(json.dumps(snap))
    v = st.verify(fid)
    assert not (v["files_ok"] and v["content_ok"])


def test_real_store_and_hashes(s):
    b = s["baseline"]
    assert b["store_forecasts"] == [] and [e[0] for e in b["registry_events"]] == ["attempt_blocked"]
    assert b["config_frozen"] and b["protocol_ok"] and b["amendment_1_ok"] and b["amendment_2_ok"] and b["production_clean"]


def test_amendments_active():
    o = pd.DataFrame([{"feature": "cpi_food_yoy_pct", "unit": u, "period": T0 + i, "value": 1.0, "avail": F3.issue_date(T0 + i), "status": "r", "source": "t"}
                      for i in range(6) for u in F3.PROVINCES])
    a = pd.DataFrame([{"feature": "provincial_unemployment_rate_pct_annual", "unit": u, "ref": y, "value": float(i), "avail": f"{int(y) + 1}-06-30", "status": "r", "source": "t"}
                      for y in ("2024",) for i, u in enumerate(F3.PROVINCES)] +
                     [{"feature": "provincial_unemployment_rate_pct_annual", "unit": "Cavite", "ref": "2025", "value": 1.0, "avail": "2026-06-30", "status": "r", "source": "t"}])
    clean, ann, log = F3.validate_inputs(o, a)
    assert log["pre2021_base_rows_rejected"] == 20                                     # Amendment 1
    r = F3._rank5(ann, next(f for f in F3.FEATURES if f.code == "EHS_unemployment_prov"), F3.qindex("2026-Q3"))
    assert {x["period"] for x in r} == {"2024"}                                        # Amendment 2


def test_firi_v2_untouched():
    from app.ml.inference import firi as FI
    raw = {k: {"x": v, "status": "observed" if v is not None else "missing", "note": ""} for k, v in
           {"A1": .7, "A2": 1.2, "A3": 3.0, "V1": .4, "C1": 0.0, "C2": 2.0, "C3": -5.0, "C4": 1.0, "E1": .3, "E2": -2.0, "N1": None, "H1": .6}.items()}
    r = FI.score_v2(raw, {k: [float(i) for i in range(-5, 10)] for k in FI.CONTINUOUS}, {"A": .5, "C": 1.5, "H": 1.0, "V": .5})
    assert r["firi"] == pytest.approx(0.3929012345679012, abs=1e-15)
    p = REPO / "backend" / "app" / "ml" / "inference" / "firi.py"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == "0e583131a7de3b9844241d3927eede813077d7cccbf949cd8313973436d0f8e3"
