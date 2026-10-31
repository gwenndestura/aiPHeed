"""
tests/unit/test_e124_prospective.py
-----------------------------------
E124 prospective FIRI3 store and configuration: frozen configuration equals the module; issue-date handling; 2021+
cutoff, Amendment 1 and 2 rules inside snapshots; publication eligibility; geography; missing data; snapshot
immutability, reproducible content hash, duplicate prevention, corrections kept beside the original, source revisions
separated from new information; FIRI v2 untouched; monitoring outputs. Controlled records only (temporary folders).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from app.ml.inference import firi3 as F3

REPO = Path(__file__).resolve().parents[2].parent
E = REPO / "aipheed-backend-aligned" / "experiments" / "E124_FIRI3_Prospective_Validation"
T0 = F3.START_Q
PROVS = F3.PROVINCES


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S = load("e124_store", E / "runner" / "store.py")
EMPTY_ANN = pd.DataFrame(columns=["feature", "unit", "ref", "value", "avail", "status", "source"])


def controlled(n=16, bump=None):
    """Synthetic test inputs: local cyclone counts and palay YoY for the five provinces (never written to the real store)."""
    rows = []
    for i in range(n):
        for j, u in enumerate(PROVS):
            rows.append({"feature": "typhoons_local_100km", "unit": u, "period": T0 + i, "value": float((i + j) % 3), "avail": F3.issue_date(T0 + i),
                         "status": "verified", "source": "test"})
            if i >= 4:
                v = float((i * 3 + j) % 7) - 3
                if bump and (T0 + i, u) in bump:
                    v = bump[(T0 + i, u)]
                rows.append({"feature": "palay_production_yoy_pct", "unit": u, "period": T0 + i, "value": v, "avail": F3.issue_date(T0 + i + 1),
                             "status": "rule_unverified", "source": "test"})
    return pd.DataFrame(rows)


ORIGIN = F3.qlabel(T0 + 15)            # 2024-Q4, issue 2025-01-01
ISSUE_DAY = date(2025, 1, 1)


def test_frozen_configuration_matches_module():
    cfg_p = E / "E124_FROZEN_VALIDATION_CONFIGURATION.json"
    if not cfg_p.exists():
        pytest.skip("configuration not generated")
    cfg = json.loads(cfg_p.read_text())
    assert hashlib.sha256(S.canonical(cfg)).hexdigest() == (E / "E124_FROZEN_VALIDATION_CONFIGURATION.sha256").read_text().strip()
    assert cfg["firi3_version"] == F3.VERSION and cfg["protocol"]["sha256"] == F3.PROTOCOL_SHA256
    assert cfg["amendment_1"]["sha256"] == F3.AMENDMENT_1_SHA256 and cfg["amendment_2"]["sha256"] == F3.AMENDMENT_2_SHA256
    assert [f["code"] for f in cfg["features"]] == [f.code for f in F3.FEATURES]
    assert cfg["weights"] == {i: 1.0 for i in F3.INDICATORS} and cfg["issue"]["first_issue_date"] == "2027-01-01"


def test_issue_before_issue_date_is_blocked_and_logged(tmp_path):
    st = S.Store(tmp_path)
    with pytest.raises(RuntimeError):
        st.issue(ORIGIN, controlled(), EMPTY_ANN, "cfg", {"x": "1"}, date(2024, 12, 31), {"failed": {}})
    ev = st.events()
    assert ev[-1]["event"] == "attempt_blocked" and "before the issue date" in ev[-1]["reasons"][0]
    assert not (tmp_path / "forecasts" / S.forecast_id(ORIGIN)).exists()


def test_eligibility_failure_blocks_even_on_issue_date(tmp_path):
    st = S.Store(tmp_path)
    with pytest.raises(RuntimeError):
        st.issue(ORIGIN, controlled(), EMPTY_ANN, "cfg", {}, ISSUE_DAY, {"failed": {"C3": "inputs to refresh: nasa"}, "missing_inputs": [{"feature": "CEC_heat"}]})
    assert st.events()[-1]["missing_inputs"] == [{"feature": "CEC_heat"}]


def test_issue_hash_reproducible_and_immutable(tmp_path):
    st = S.Store(tmp_path)
    obs = controlled()
    d = st.issue(ORIGIN, obs, EMPTY_ANN, "cfg", {"src": "abc"}, ISSUE_DAY, {"failed": {}})
    fid = S.forecast_id(ORIGIN)
    v = st.verify(fid)
    assert v["files_ok"] and v["content_ok"]
    assert st.reproduce(fid, obs.sample(frac=1, random_state=3), EMPTY_ANN, "cfg", {"src": "abc"})   # same inputs -> same content hash
    assert not st.reproduce(fid, obs, EMPTY_ANN, "cfg-other", {"src": "abc"})                         # configuration is part of the hash
    with pytest.raises(FileExistsError):                                                             # duplicate issuance refused
        st.issue(ORIGIN, obs, EMPTY_ANN, "cfg", {"src": "abc"}, date(2025, 1, 2), {"failed": {}})
    snap = json.loads((d / "snapshot.json").read_text())
    assert snap["forecast_id"] == fid and snap["issue_date"] == "2025-01-01" and snap["protocol_sha256"] == F3.PROTOCOL_SHA256
    assert snap["amendment_1_sha256"] == F3.AMENDMENT_1_SHA256 and snap["amendment_2_sha256"] == F3.AMENDMENT_2_SHA256
    assert {u["unit"] for u in snap["units"] if u["scope"] == "provincial"} == set(PROVS)
    for u in snap["units"]:
        assert set(u["indicator_scores"]) == set(F3.INDICATORS) and u["firi3"] is None and u["status"] == "not_computable"   # 2 indicators < 4
        assert u["completeness_pct"] <= 100
    edited = json.loads((d / "snapshot.json").read_text())
    edited["units"][0]["band"] = "high"                                                                # silent modification is detected
    (d / "snapshot.json").write_text(json.dumps(edited, sort_keys=True, indent=1))
    v2 = st.verify(fid)
    assert not (v2["files_ok"] and v2["content_ok"])


def test_trace_excludes_missing_and_never_zero(tmp_path):
    st = S.Store(tmp_path)
    d = st.issue(ORIGIN, controlled(), EMPTY_ANN, "cfg", {}, ISSUE_DAY, {"failed": {}})
    tr = pd.read_csv(d / "feature_trace.csv")
    assert (tr.loc[tr["eligibility"] == "not scored", "score"].isna()).all()
    assert (tr.loc[tr["eligibility"] == "not scored", "exclusion_reason"].str.len() > 0).all()
    assert (tr.loc[tr["eligibility"] == "scored", "avail_date"].astype(str) < tr.loc[tr["eligibility"] == "scored", "issue_date"].astype(str)).all()
    p = tr[tr["feature"] == "AFP_palay"]
    assert (p["period"].dropna().map(F3.qindex) >= F3.FIRST_CHANGE_Q).all()                          # Amendment 1 inside the snapshot
    assert set(tr.loc[tr["scope"] == "provincial", "unit"]) == set(PROVS) and not tr.loc[tr["scope"] == "provincial", "feature"].str.endswith("_R").any()


def test_correction_kept_beside_original(tmp_path):
    st = S.Store(tmp_path)
    obs = controlled()
    d = st.issue(ORIGIN, obs, EMPTY_ANN, "cfg", {}, ISSUE_DAY, {"failed": {}})
    fid = S.forecast_id(ORIGIN)
    before = (d / "snapshot.json").read_bytes()
    c = st.correct(fid, "test correction", controlled(bump={(T0 + 14, "Cavite"): 50.0}), EMPTY_ANN, "cfg", {}, date(2025, 2, 1))
    rec = json.loads(c.read_text())
    assert (d / "snapshot.json").read_bytes() == before and st.verify(fid)["content_ok"]
    assert rec["original_content_sha256"] == st.verify(fid)["content_sha256"] and rec["reason"] == "test correction"
    assert [e["event"] for e in st.events()][-2:] == ["issued", "correction"]


def test_revision_vs_new_information(tmp_path):
    st = S.Store(tmp_path)
    obs = controlled()
    st.issue(ORIGIN, obs, EMPTY_ANN, "cfg", {}, ISSUE_DAY, {"failed": {}})
    fid = S.forecast_id(ORIGIN)
    revised = controlled(bump={(T0 + 13, "Cavite"): 9.0})                     # the period used at the issue gets a new value -> data revision
    rec = st.observe(fid, revised, EMPTY_ANN, "cfg", {}, date(2025, 3, 1))
    assert rec["forecast_stability"]["original_unchanged"]
    ch = pd.DataFrame(rec["feature_changes"])
    assert set(ch.loc[(ch["unit"] == "Cavite") & (ch["feature"] == "AFP_palay"), "change_type"]) == {"data revision (same period, new value)"}
    assert rec["data_revision_sensitivity"]["features_revised"] == 1
    later = controlled(n=17)                                                   # a later period becomes available -> new information
    rec2 = st.observe(fid, later.assign(avail=later["avail"].where(later["period"] < T0 + 16, "2024-12-15")), EMPTY_ANN, "cfg", {}, date(2025, 4, 1))
    assert rec2["prospective_measurement"]["features_new_period"] >= 1 or rec2["data_revision_sensitivity"]["features_revised"] == 0


@pytest.mark.skipif(not (E / "out" / "summary.json").exists(), reason="E124 outputs missing")
def test_real_readiness_outputs():
    s = json.loads((E / "out" / "summary.json").read_text())
    assert s["reproduces_e123"] and s["production_tree_clean"] and s["hashes_ok"]
    assert s["attempt"].startswith("blocked") and "2027-01-01" in s["attempt"]
    assert not (E / "store" / "forecasts" / "FIRI3-1.2-2026-Q4").exists()                               # nothing issued early
    rs = pd.read_csv(E / "E124_SOURCE_RELEASE_STATUS.csv")
    allowed = {"not yet released", "released and verified", "released (publication date unverified)", "retrieved but incomplete",
               "released per rule but not retrieved (refresh needed)", "not applicable"}
    assert set(rs["availability_status"]) <= allowed and len(rs) == len(F3.FEATURES)
    el = pd.read_csv(E / "E124_FEATURE_ELIGIBILITY_AUDIT.csv")
    assert len(el) == len(F3.FEATURES) and el["amendment_1_base_ok"].all()
    cmpf = pd.read_csv(E / "E124_FIRI3_VS_FIRI2_COMPARISON.csv")
    assert (cmpf["effect_amendment_1"].abs() > 1e-8).sum() == 73 and (cmpf["effect_amendment_2"].abs() > 1e-8).sum() == 10
    assert cmpf.loc[cmpf["scope"] == "regional", "firi_v2"].isna().all()


def test_firi_v2_untouched():
    from app.ml.inference import firi as FI
    raw = {k: {"x": v, "status": "observed" if v is not None else "missing", "note": ""} for k, v in
           {"A1": .7, "A2": 1.2, "A3": 3.0, "V1": .4, "C1": 0.0, "C2": 2.0, "C3": -5.0, "C4": 1.0, "E1": .3, "E2": -2.0, "N1": None, "H1": .6}.items()}
    r = FI.score_v2(raw, {k: [float(i) for i in range(-5, 10)] for k in FI.CONTINUOUS}, {"A": .5, "C": 1.5, "H": 1.0, "V": .5})
    assert r["firi"] == pytest.approx(0.3929012345679012, abs=1e-15)
