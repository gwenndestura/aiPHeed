"""E52 experiment checks: protocol frozen before scoring, run reproducible, criteria as reported, prospective freeze
copied from the already frozen I7 file without change.

    backend/venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

E52 = Path(__file__).resolve().parents[1]
EXP = E52.parent
RUNS = sorted((E52 / "runs").glob("2026*"))


def test_protocol_unchanged_since_freeze():
    want = (E52 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((E52 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want
    for r in RUNS:
        assert json.loads((r / "results.json").read_text())["protocol_sha256"] == want


def test_repeat_is_byte_identical_except_timestamp():
    assert len(RUNS) >= 2
    a, b = RUNS[0], RUNS[1]
    assert (a / "rows.csv").read_bytes() == (b / "rows.csv").read_bytes()
    ra, rb = (json.loads((x / "results.json").read_text()) for x in (a, b))
    ra.pop("run_utc"), rb.pop("run_utc")
    assert ra == rb


def test_reported_criteria_and_identical_rows():
    res = json.loads((RUNS[0] / "results.json").read_text())
    assert res["rows"] == 50 and res["independent_quarters"] == 10 and res["HIGH"] == 18
    c = res["criteria"]
    assert all(c.values()) and c["accepted_for_development"] is True
    m = res["metrics"]["E52PS"]
    assert round(m["accuracy"], 3) == 0.76 and round(m["balanced_accuracy"], 3) == 0.752
    assert m["accuracy_ci95"][0] < 0.75          # the 75% level is not established statistically on 50 rows
    assert min(res["leave_one_quarter_out"].values()) >= 0.70


def test_prospective_freeze_equals_the_frozen_i7_price_component():
    f = E52 / "frozen" / "E52_PS_PROSPECTIVE_2027Q1.json"
    assert hashlib.sha256(f.read_bytes()).hexdigest() == (f.parent / (f.stem + ".sha256")).read_text().split()[0]
    i7f = EXP / "E46_Rice_Policy" / "frozen" / "E46_I7_PROSPECTIVE_2027Q1.json"
    i7 = json.loads(i7f.read_text())
    fz = json.loads(f.read_text())
    assert hashlib.sha256(i7f.read_bytes()).hexdigest() in fz["probabilities_from"]
    for name, v in fz["provinces"].items():
        assert abs(v["p_price_pressure"] - i7["provinces"][name]["I7_p_price"]) < 1e-12
        assert v["decision"] == ("HIGH" if v["p_price_pressure"] >= 0.5 else "LOW")
