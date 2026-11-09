"""E178 Part B results (docs/e178/PROTOCOL.md): the recorded decision follows from the stored numbers and the thresholds
fixed in advance, the hashes match, the no-augmentation run reproduced E168's selected outputs, and nothing in production
changed."""
from __future__ import annotations

import json

import pytest

from app.e178 import augment as A
from app.e178 import common as K

RES = K.OUT / "results.json"
needs = pytest.mark.skipif(not RES.exists(), reason="python -m app.e178.retrain eval not run")
PRODUCTION_ARTIFACT_SHA = "a01aa189795e97fc057cd345d5e5a52bd306bae648ed7144edb45c7e7358382b"


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fid():
    return json.loads((K.OUT / "fidelity.json").read_text(encoding="utf-8"))


@needs
def test_fidelity_thresholds_are_the_protocols(fid):
    assert fid["thresholds"] == A.FIDELITY
    assert A.FIDELITY == {"median_ks_max": 0.15, "max_w1_sd_max": 0.50, "corr_mad_max": 0.10, "tstr_ratio_max": 1.25,
                          "copy_share_max": 0.10, "copy_distance_frac": 0.05}
    assert fid["seed"] == 17801 and fid["ratio"] == 1.0 and len(fid["jobs"]) == 6


@needs
def test_fidelity_verdicts_follow_from_the_numbers(fid):
    t = fid["thresholds"]
    accepted = []
    for g in A.GENERATORS:
        ok_all = True
        for j, r in fid["jobs"].items():
            m = r[g]
            checks = {"ks": m["median_ks"] <= t["median_ks_max"], "wasserstein": m["max_w1_sd"] <= t["max_w1_sd_max"],
                      "correlation": m["corr_mad"] <= t["corr_mad_max"], "tstr": m["tstr_ratio"] <= t["tstr_ratio_max"],
                      "not_copies": m["copy_share"] <= t["copy_share_max"] and m["exact_copies"] == 0}
            assert checks == m["checks"], (j, g)
            ok_all &= all(checks.values())
        if ok_all:
            accepted.append(g)
    assert accepted == fid["accepted_generators"]


@needs
def test_decision_follows_the_protocol(res, fid):
    if not fid["accepted_generators"]:
        assert res["stage2_run"] is False and res["decision"].startswith("NOT RUN: no synthetic generator met the fidelity criteria")
        assert "E168 stays in production" in res["decision"]
        assert sorted(res["rejected_generators"]) == sorted(A.GENERATORS)
        return
    acc = res["decision_rule"]
    l1, l2 = res["leads"]["1"], res["leads"]["2"]
    assert acc["brier_ci_upper_below_0_lead1"] == (l1["brier_E178_minus_E168"]["ci95"][1] < 0)
    assert acc["brier_ci_upper_below_0_lead2"] == (l2["brier_E178_minus_E168"]["ci95"][1] < 0)
    assert acc["leakage_below_1e-9"] == (res["leakage_max_abs_change"] < 1e-9)
    assert acc["beats_shuffled"] == (res["shuffle"]["ci95"][1] < 0)
    assert res["decision"].startswith("E178 BETTER") == all(acc.values())


@needs
def test_e168_selected_outputs_were_reproduced():
    eq = json.loads((K.OUT / "equivalence.json").read_text())
    assert eq["rows_compared"] == eq["rows_expected"] == 432 and eq["same_configuration"]
    assert all(eq["max_abs_diff"][k] == 0.0 for k in ("mu", "p", "half", "mu_raw", "p_raw", "half_raw"))
    assert max(eq["max_abs_diff"].values()) <= 1e-15
    dev = json.loads((K.OUT / "deviations.json").read_text())["deviations"]
    assert dev[0]["id"] == "D1" and "proceed" in dev[0]["decision"]


@needs
def test_recorded_hashes_match():
    h = json.loads((K.OUT / "hashes.json").read_text())
    assert h["outputs"]
    for rel, sha in h["outputs"].items():
        assert K.sha256(K.BACKEND_DIR.parent / rel) == sha, rel


def test_production_is_untouched():
    reg = json.loads((K.D / "registry" / "registry.json").read_text())
    assert reg["production"]["model_id"] == "e168-lgbm-1.0"
    assert reg["production"]["artifact_file_sha256"] == PRODUCTION_ARTIFACT_SHA
    assert K.sha256(K.BACKEND_DIR / reg["production"]["artifact_path"]) == PRODUCTION_ARTIFACT_SHA
    assert not any("e178" in m for m in reg["models"])                 # never registered
    assert not (K.ROOT / "candidate").exists()                          # no candidate staged (E178 not run or not better)
