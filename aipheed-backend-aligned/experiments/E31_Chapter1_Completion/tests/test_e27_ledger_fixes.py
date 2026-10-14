"""E27 regression tests for ledger fixes L1-L3 (BUG_FIXES.md)."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

import _paths  # noqa: F401
from _paths import EXP
from app.quarterly import ledger as LG

PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
INP = [{"source": "synthetic", "authorized": True}]
PHT = timezone(timedelta(hours=8))


def _auth(tmp_path, name, obj):
    f = tmp_path / f"{name}.json"
    f.write_text(json.dumps(obj, sort_keys=True))
    return {"path": str(f), "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "authorized_by": "test",
            "authorized_on": "2027-05-20"}


def _seal(L, arm, role, q, origin, p, now, tau=None, cutoff=None):
    return L.seal(arm=arm, role=role, target_quarter=q, origin=origin, info_cutoff=cutoff or origin,
                  probabilities=dict(zip(PROVS, p)), model_sha256="m" * 64, inputs=INP, now=now, threshold=tau)


def test_L1_seal_after_the_target_quarter_ended_is_refused(tmp_path):
    L = LG.Ledger(tmp_path / "l.jsonl")
    end = datetime(2027, 4, 1, tzinfo=PHT)                       # 2027-Q1 ends at 2027-04-01 00:00 PHT
    with pytest.raises(LG.LedgerRefused, match="had ended"):
        _seal(L, "PCF", "candidate", "2027-Q1", "2027-01-01T00:00:00+08:00", [.6] * 5, end)
    _seal(L, "PCF", "candidate", "2027-Q1", "2027-01-01T00:00:00+08:00", [.6] * 5, end - timedelta(seconds=1))


def test_L1_imported_seal_is_timed_by_its_verified_seal_time_not_the_import_time(tmp_path):
    L = LG.Ledger(tmp_path / "l.jsonl")
    e = L.seal(arm="X", role="candidate", target_quarter="2026-Q4", origin="2026-10-01T00:00:00",
               info_cutoff="2026-09-30T23:59:59+08:00", probabilities=dict(zip(PROVS, [.6] * 5)),
               model_sha256="m" * 64, inputs=INP, now=datetime(2032, 1, 1, tzinfo=timezone.utc),
               sealed_at=datetime(2026, 10, 14, 0, 25, 48, tzinfo=timezone.utc))
    assert e["payload"]["sealed_at_utc"] == "2026-10-14T00:25:48+00:00"


def test_L2_information_cutoff_after_origin_is_refused(tmp_path):
    L = LG.Ledger(tmp_path / "l.jsonl")
    now = datetime(2027, 1, 2, tzinfo=PHT)
    with pytest.raises(LG.LedgerRefused, match="after the origin"):
        _seal(L, "PCF", "candidate", "2027-Q1", "2027-01-01T00:00:00+08:00", [.6] * 5, now,
              cutoff="2027-01-01T08:00:00+08:00")
    with pytest.raises(LG.LedgerRefused, match="unparseable"):
        _seal(L, "PCF", "candidate", "2027-Q1", "2027-01-01T00:00:00+08:00", [.6] * 5, now, cutoff="x")


def test_L3_each_seal_is_labelled_with_its_own_threshold(tmp_path):
    """Lead-2 (origin 2026-10-01, tau 15) and lead-1 (origin 2027-01-01, tau 17) forecasts of 2027-Q1. The measured
    S1 = 16 is HIGH for the first and LOW for the second; one shared label set would be wrong for one of them."""
    L = LG.Ledger(tmp_path / "l.jsonl")
    q = "2027-Q1"
    o2, o1 = "2026-10-01T00:00:00+08:00", "2027-01-01T00:00:00+08:00"
    _seal(L, "PCF:lead2", "candidate", q, o2, [.9] * 5, datetime(2026, 10, 2, tzinfo=PHT), tau=15.0)
    _seal(L, "B1:lead2", "baseline_persistence", q, o2, [0.0] * 5, datetime(2026, 10, 2, tzinfo=PHT), tau=15.0)
    _seal(L, "PCF:lead1", "candidate", q, o1, [.9] * 5, datetime(2027, 1, 2, tzinfo=PHT), tau=17.0)
    _seal(L, "B1:lead1", "baseline_persistence", q, o1, [0.0] * 5, datetime(2027, 1, 2, tzinfo=PHT), tau=17.0)
    measured = {p: {"H": 14.0, "D": 1.0} for p in PROVS}                  # S1 = 16 everywhere
    L.record_outcome_measured(target_quarter=q, target="T1", measured=measured,
                              authorization=_auth(tmp_path, "out", measured))
    s2, s1 = L.score("PCF:lead2"), L.score("PCF:lead1")
    # lead 2: label HIGH -> candidate (0.9) right, persistence (0) wrong; lead 1: label LOW -> the reverse
    assert s2["baselines"]["baseline_persistence"]["d_accuracy"] == [1.0]
    assert s1["baselines"]["baseline_persistence"]["d_accuracy"] == [-1.0]


def test_L3_measured_outcome_requires_one_regional_H_and_a_matching_file(tmp_path):
    L = LG.Ledger(tmp_path / "l.jsonl")
    bad = {p: {"H": 14.0 + i, "D": 0.0} for i, p in enumerate(PROVS)}
    with pytest.raises(LG.LedgerRefused, match="regional"):
        L.record_outcome_measured(target_quarter="2027-Q1", target="T1", measured=bad,
                                  authorization=_auth(tmp_path, "bad", bad))
    good = {p: {"H": 14.0, "D": 0.0} for p in PROVS}
    a = _auth(tmp_path, "good", good)
    with pytest.raises(LG.LedgerRefused, match="does not match"):
        L.record_outcome_measured(target_quarter="2027-Q1", target="T1", measured=good,
                                  authorization={**a, "sha256": "0" * 64})


def test_L3_real_E25_seal_threshold_is_read_from_the_hash_verified_sealed_file():
    """The E25 seal was imported by E26 before thresholds were stored. Its tau must be recoverable, unchanged."""
    L = LG.Ledger(EXP / "backend_dev" / "data" / "ledger" / "T1_A.jsonl")
    pcf = [e["payload"] for e in L.seals() if e["payload"]["arm"].startswith("PCF21:lead")]
    assert {p["target_quarter"] for p in pcf} == {"2026-Q4", "2027-Q1"}
    for p in pcf:
        assert abs(L._threshold(p, "T1") - 14.993333333333336) < 1e-9     # E25 seal_info thresholds T1_A
