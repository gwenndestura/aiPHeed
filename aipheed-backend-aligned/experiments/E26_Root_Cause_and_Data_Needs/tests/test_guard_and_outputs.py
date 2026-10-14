"""Guard denials, frozen protocol hashes, recorded outputs (root cause, VOI rows, horizon) and E25 seal integrity."""
import hashlib
import json

import pytest

import _paths  # noqa: F401
from _paths import EXP
import guard


def test_guard_denies_unlisted_data_other_experiments_and_writes_outside():
    for p in (guard.AL / "data" / "processed" / "psa_indicators.parquet",
              guard.AL / "experiments" / "2026-10-14_E24_Resolve_Forecasting" / "README.md",
              guard.E25 / "FINAL_REPORT.md",
              guard.ROOT / "backend" / "aipheed.db"):
        with pytest.raises(guard.AccessDenied):
            open(p, "rb")
    with pytest.raises(guard.AccessDenied):
        open(guard.E25 / "runs" / "e26_should_not_write.json", "w")


def test_frozen_protocol_and_amendments_match_their_hashes():
    for ln in (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").splitlines():
        parts = ln.split()
        if len(parts) == 2 and len(parts[0]) == 64:
            assert hashlib.sha256((EXP / parts[1]).read_bytes()).hexdigest() == parts[0], parts[1]


def test_root_cause_outputs_are_consistent():
    r = json.loads((EXP / "runs" / "root_cause.json").read_text(encoding="utf-8"))
    a = r["A_budget"]
    assert a["independent_regional_outcome_series"] == 1
    assert a["independent_provincial_food_insecurity_outcomes_in_authorized_data"] == 0
    assert abs(a["label_variance_share_regional_H"] + a["label_variance_share_2D"] + a["label_variance_share_2cov"] - 1) < 1e-9
    v = r["C_voi"]
    assert hashlib.sha256((EXP / "runs" / "voi_predictions.csv").read_bytes()).hexdigest() == v["predictions_sha256"]
    for lead, res in v["by_lead"].items():
        n = {(x["n_dates"], x["HIGH"], x["LOW"]) for x in res.values()}
        assert len(n) == 1, f"lead {lead}: models are not scored on identical rows"
        assert {"I0|B1", "I0|B1p", "I0|PCF21", "I0|PCF21_NOW", "I1|PCF21", "I3|B1", "IO|ORACLE_H"} <= set(res)


def test_voi_rows_identical_across_sets_and_models():
    import pandas as pd
    P = pd.read_csv(EXP / "runs" / "voi_predictions.csv")
    keys = {sm: tuple(sorted(zip(g["lead"], g["t"], g["province_code"]))) for sm, g in P.groupby(["set", "model"])}
    assert len(set(keys.values())) == 1
    assert (P.groupby(["lead", "t", "province_code"])["y"].nunique() == 1).all()   # one outcome per row


def test_horizon_and_reproducibility_records():
    h = json.loads((EXP / "runs" / "horizon.json").read_text(encoding="utf-8"))
    assert h["params"]["seed"] == 20261014 and h["params"]["paths"] == 10000
    assert set(h["scenarios"]) >= {"S0", "S_timely"}
    rep = json.loads((EXP / "runs" / "reproducibility.json").read_text(encoding="utf-8"))
    assert rep["all_identical"]
    for f, v in rep["outputs"].items():
        assert hashlib.sha256((EXP / f).read_bytes()).hexdigest() == v["after"], f


def test_e25_and_its_seal_unchanged_record():
    r = json.loads((EXP / "runs" / "e25_unchanged.json").read_text(encoding="utf-8"))
    assert r["all_unchanged"] and r["seal_unchanged"] and r["files"] == 451


def test_dev_ledgers_hold_the_e25_seal_only():
    import sys
    sys.path.insert(0, str(EXP / "backend_dev"))
    from app.quarterly import ledger as LG
    meta = json.loads((guard.E25_RUNS / "SEAL_E25_20261014T002548Z" / "SEAL.json").read_text(encoding="utf-8"))
    for target, n in (("T1_A", 22), ("T2", 12)):
        L = LG.Ledger(EXP / "runs" / "ledger" / f"{target}.jsonl")
        assert L.verify() and len(L.seals()) == n and not L.outcomes() and not L.missing()
        assert {e["payload"]["inputs"][0]["forecasts_sha256"] for e in L.seals()} == {meta["sha256_forecasts"]}
        assert {e["payload"]["inputs"][0]["sealed_utc"] for e in L.seals()} == {meta["sealed_utc"]}
