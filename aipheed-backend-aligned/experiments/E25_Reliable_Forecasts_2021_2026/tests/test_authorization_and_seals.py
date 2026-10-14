"""Cutoff, authorization and seal refusal paths; guard denials. Synthetic outcome files only (never evaluation)."""
import hashlib
import json

import pandas as pd
import pytest

import _paths  # noqa: F401
from _paths import EXP
import guard
import score_sealed as SS


def test_guard_denies_unlisted_project_data_and_other_experiments():
    for p in (guard.AL / "data" / "processed" / "psa_indicators.parquet",
              guard.AL / "experiments" / "2026-10-14_E24_Resolve_Forecasting" / "README.md",
              guard.ROOT / "backend" / "aipheed.db"):
        with pytest.raises(guard.AccessDenied):
            open(p, "rb")


def test_guard_rejects_hash_mismatch(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("a\n1\n")
    guard.ALLOW[f.resolve()] = ("0" * 64, None, "test")
    with pytest.raises(guard.AccessDenied):
        guard.read_allowed_text(f)
    del guard.ALLOW[f.resolve()]


def test_production_sws_is_read_only_with_its_2026H1_filter():
    df = guard.read_allowed_parquet(guard.PROD_SWS, ["quarter", "pct_total_hunger"])
    assert set(df["quarter"]) == {"2026-Q1", "2026-Q2"}


def test_seal_refuses_to_seal_twice():
    import subprocess  # noqa: F401  (the guard blocks subprocess; call main directly)
    import seal_e25
    import sys
    argv = sys.argv
    sys.argv = ["seal_e25.py"]
    try:
        with pytest.raises(SystemExit) as e:
            seal_e25.main()
        assert "refused" in str(e.value)
    finally:
        sys.argv = argv


def test_score_sealed_refuses_without_authorization(tmp_path):
    with pytest.raises(SystemExit) as e:
        SS.load_authorized(tmp_path / "AUTHORIZED_OUTCOMES.json")
    assert e.value.code == 2


def test_score_sealed_refuses_wrong_hash_and_unlisted_quarters(tmp_path):
    f = tmp_path / "sws.csv"
    f.write_text("quarter,pct_total_hunger\n2026-Q4,10.0\n2027-Q1,9.0\n")
    a = tmp_path / "auth.json"
    a.write_text(json.dumps({"files": [{"path": str(f), "sha256": "1" * 64, "kind": "sws_round", "quarter": "2026-Q4"}]}))
    with pytest.raises(SystemExit):
        SS.load_authorized(a)
    h = hashlib.sha256(f.read_bytes()).hexdigest()
    a.write_text(json.dumps({"files": [{"path": str(f), "sha256": h, "kind": "sws_round", "quarter": "2026-Q4"}]}))
    with pytest.raises(SystemExit):                         # file holds 2027-Q1 too: refused, not filtered
        SS.load_authorized(a)


def test_score_sealed_scores_complete_synthetic_outcomes(tmp_path):
    f = tmp_path / "sws.csv"
    f.write_text("quarter,pct_total_hunger\n2026-Q4,10.0\n")
    rows = ["province_code,reference_month,food_cpi_yoy_pct_raw"]
    for p, base in zip(["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"], [1, 2, 3, 4, 5]):
        for m in ("2026-10", "2026-11", "2026-12"):
            rows.append(f"{p},{m},{base}")
    c = tmp_path / "cpi.csv"
    c.write_text("\n".join(rows) + "\n")
    a = tmp_path / "auth.json"
    a.write_text(json.dumps({"files": [
        {"path": str(f), "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "kind": "sws_round", "quarter": "2026-Q4"},
        {"path": str(c), "sha256": hashlib.sha256(c.read_bytes()).hexdigest(), "kind": "provincial_food_cpi_yoy",
         "months": ["2026-10", "2026-11", "2026-12"]}]}))
    H, F = SS.load_authorized(a)
    o = SS.outcomes_for("2026-Q4", H, F, ["PH040100000", "PH040500000"])
    assert o is not None and abs(o["PH040500000"]["D"] - 2.0) < 1e-9
    assert SS.outcomes_for("2027-Q1", H, F, ["PH040100000"]) is None     # incomplete: never partially scored
