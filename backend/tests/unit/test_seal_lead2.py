"""Guards of the Lead-2 sealing step (backend/scripts/seal_lead2.py, score_seal.py; seals/PREREG_LEAD2.md):
inputs must be published before the issue date, a seal is never overwritten, and a seal edited after sealing (or a
changed pre-registration) is refused. Pure helpers only: no model is run."""
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import score_seal as SC  # noqa: E402
import seal_lead2 as SL  # noqa: E402

ISSUE = dt.date(2026, 10, 15)


# ------------------------------------------------------------------------------------------- publication-date guard
def test_inputs_published_before_the_issue_date_are_accepted():
    SL.assert_published_before([{"published": "2026-10-14"}, {"published": "2021-01-02"}], ISSUE, "SWS")


@pytest.mark.parametrize("pub", ["2026-10-15", "2026-10-16", None, ""])
def test_input_published_on_or_after_the_issue_date_or_undated_is_refused(pub):
    with pytest.raises(SL.SealError, match="not published before 2026-10-15"):
        SL.assert_published_before([{"published": "2026-10-01"}, {"published": pub}], ISSUE, "SWS")


def test_cpi_month_is_available_from_the_first_day_of_month_plus_two():
    aug_2026 = 2026 * 12 + 7
    assert SL.cpi_month_available(aug_2026, dt.date(2026, 10, 1))
    assert SL.cpi_month_available(aug_2026, ISSUE)
    assert not SL.cpi_month_available(aug_2026 + 1, ISSUE)          # September 2026 only from 2026-11-01


def test_scoring_waits_for_the_target_quarters_sws_round_and_cpi():
    q1_2027 = 2027 * 4
    rounds = pd.DataFrame({"area": ["BL", "BL", "NCR"], "q": [q1_2027 - 1, q1_2027, q1_2027],
                           "published": pd.to_datetime(["2026-10-14", "2027-04-20", "2027-04-01"])})
    assert not SC.outcome_published(q1_2027, rounds, dt.date(2027, 4, 19))   # BL round not yet out
    assert not SC.outcome_published(q1_2027, rounds, dt.date(2027, 4, 25))   # March CPI only from 2027-05-01
    assert SC.outcome_published(q1_2027, rounds, dt.date(2027, 5, 1))
    assert not SC.outcome_published(q1_2027 + 1, rounds, dt.date(2027, 12, 31))  # no round of that quarter


# ------------------------------------------------------------------------------------------- no overwrite
def test_a_seal_is_never_overwritten(tmp_path):
    p = tmp_path / "2026-10-15_2027-Q1.json"
    sha = SL.write_seal(p, {"a": 1})
    assert sha == hashlib.sha256(p.read_bytes()).hexdigest()
    before = p.read_bytes()
    with pytest.raises(SL.SealError, match="refusing to overwrite"):
        SL.write_seal(p, {"a": 2})
    assert p.read_bytes() == before


def test_the_ledger_is_append_only_and_lists_a_seal_once(tmp_path):
    led = tmp_path / "LEDGER.md"
    row = {"file": "x.json", "sha256": "ab" * 32, "issue": "2026-10-15", "target": "2027-Q1",
           "sealedAt": "2026-11-01T00:00:00+00:00", "timing": "late", "prereg": "cd" * 32, "commit": "abc"}
    SL.ledger_append(row, led)
    first = led.read_text(encoding="utf-8")
    with pytest.raises(SL.SealError, match="already in the ledger"):
        SL.ledger_append(row, led)
    SL.ledger_append({**row, "file": "y.json"}, led)
    text = led.read_text(encoding="utf-8")
    assert text.startswith(first)
    assert set(SL.ledger_entries(led)) == {"x.json", "y.json"}


# ------------------------------------------------------------------------------------------- hash check
def _sealed(tmp_path):
    p, led = tmp_path / "s.json", tmp_path / "LEDGER.md"
    sha = SL.write_seal(p, {"target": "2027-Q1", "candidates": {"C1_M0": {"PH040100000": {"probability": 0.4}}}})
    SL.ledger_append({"file": p.name, "sha256": sha, "issue": "2026-10-15", "target": "2027-Q1", "sealedAt": "t",
                      "timing": "late", "prereg": "x", "commit": "y"}, led)
    return p, led


def test_an_untouched_seal_verifies(tmp_path):
    p, led = _sealed(tmp_path)
    assert SL.verify_seal(p, led)["target"] == "2027-Q1"


def test_a_seal_edited_after_sealing_is_refused(tmp_path):
    p, led = _sealed(tmp_path)
    d = json.loads(p.read_text(encoding="utf-8"))
    d["candidates"]["C1_M0"]["PH040100000"]["probability"] = 0.6
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(SL.SealError, match="does not match its ledger hash"):
        SL.verify_seal(p, led)


def test_a_seal_missing_from_the_ledger_is_refused(tmp_path):
    p, led = _sealed(tmp_path)
    q = tmp_path / "other.json"
    q.write_bytes(p.read_bytes())
    with pytest.raises(SL.SealError, match="not in the ledger"):
        SL.verify_seal(q, led)


def test_the_committed_preregistration_matches_its_hash():
    assert SL.prereg_sha() == "91fe94e0de1ec697b1fcc8e9b385512bf344d2920c386b5bb6f494e22cb2e47b"
    text = SL.PREREG.read_text(encoding="utf-8")
    assert "## 8. Not changed by this file" in text and text.count("\n") > 100   # the whole file, not a fragment


def test_the_hash_line_is_found_at_the_end_not_where_the_text_mentions_it(tmp_path):
    body = b"# x\n\nThe hash is on the line beginning `PREREG-SHA256:`.\n\n## 1. Rules\n\nD0 >= 0.50\n\n"
    p = tmp_path / "PREREG_LEAD2.md"
    p.write_bytes(body + b"PREREG-SHA256: " + hashlib.sha256(body).hexdigest().encode() + b"\n")
    assert SL.prereg_sha(p) == hashlib.sha256(body).hexdigest()
    p.write_bytes(body + b"PREREG-SHA256: " + hashlib.sha256(body).hexdigest().encode() + b"\nextra\n")
    with pytest.raises(SL.SealError, match="last line"):
        SL.prereg_sha(p)


def test_the_committed_addendum_matches_its_hash():
    assert SL.prereg_sha(SC.ADDENDUM) == "662fc2d77a6c2be2834e3a8703302a3d553bfe5669fa9ed433fafd4df92787f9"


def test_addendum_rules_follow_the_registered_definitions():
    c1, c2 = {"hunger": 0.98, "price": 0.40}, {"hunger": 0.98, "price": 0.46}
    r = SC.addendum_rules(c1, c2)
    assert r["A1"] == (pytest.approx(0.98 * 0.46), "HIGH")              # h >= 0.50 and p2 >= 0.45
    assert r["A2"] == (pytest.approx(0.98 * 0.43), "LOW")               # h x mean(0.40, 0.46) = 0.42 < 0.50
    assert SC.addendum_rules(c1, {"hunger": 0.49, "price": 0.9})["A1"][1] == "LOW"
    assert SC.addendum_rules({"price": 0.6}, {"hunger": 0.9, "price": 0.6})["A2"][1] == "HIGH"


def test_a_changed_preregistration_is_refused(tmp_path):
    p = tmp_path / "PREREG_LEAD2.md"
    b = SL.PREREG.read_bytes()
    p.write_bytes(b.replace(b"0.50", b"0.45", 1))
    with pytest.raises(SL.SealError, match="changed after it was hashed"):
        SL.prereg_sha(p)
