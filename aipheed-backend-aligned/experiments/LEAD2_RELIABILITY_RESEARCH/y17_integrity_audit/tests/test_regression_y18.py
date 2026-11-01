"""Y18 regression tests: each Y17 confirmed defect (F1-F12, F16-F18) and each Y18 fix (X1-X7, Amendment 1) as a
PASSING test. Synthetic data and pytest tmp_path only; the real overlay, prospective/ and dry_runs/ are never written.
test_adversarial.py (the Y17 evidence) is kept unchanged.

    python -m pytest -q tests/test_regression_y18.py -p no:cacheprovider
"""
from __future__ import annotations

import ast
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
Y16 = Path(__file__).resolve().parents[2] / "y16_kalman_prospective"
RUNNER = Y16 / "runner"
sys.path.insert(0, str(RUNNER))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

import kprospect as K  # noqa: E402
import evaluate as EV  # noqa: E402
import attest as AT  # noqa: E402
import issue as IS  # noqa: E402

R = K.R
UTC = dt.timezone.utc
HDR = "area,quarter,H,published,moe,source_url,entered_utc\n"
URL = "https://www.sws.org.ph/example-release"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
JAN1 = dt.datetime(2027, 1, 1, 3, tzinfo=UTC)
OK_ROW = f"BL,2026-Q4,15.0,2026-12-20,4.0,{URL},2026-12-21T00:00:00Z"


def ov(tmp_path, rows, name="ov.csv", header=HDR) -> Path:
    p = tmp_path / name
    p.write_text(header + "".join(r + "\n" for r in rows), encoding="utf-8")
    return p


@pytest.fixture()
def empty(tmp_path):
    p = ov(tmp_path, [], "empty.csv")
    K.install_overlay(p)
    yield p
    K.install_overlay(p)


def y16_copy(tmp_path, edit_plan=False, edit_amendment=False) -> Path:
    d = tmp_path / "y16copy"
    d.mkdir()
    for f in ("EXPERIMENT_PLAN.md", "PLAN_SHA256.txt", "BOOTSTRAP_AMENDMENT.md", "BOOTSTRAP_AMENDMENT_SHA256.txt"):
        shutil.copy(Y16 / f, d / f)
    if edit_plan:
        (d / "EXPERIMENT_PLAN.md").write_text("edited plan", encoding="utf-8")
    if edit_amendment:
        (d / "BOOTSTRAP_AMENDMENT.md").write_text("edited amendment", encoding="utf-8")
    return d


def run_O(code: str):
    return subprocess.run([sys.executable, "-O", "-c", f"import sys; sys.path.insert(0, r'{RUNNER}'); import kprospect as K; "
                           "from pathlib import Path; import datetime as dt; " + code], capture_output=True, text=True, env=ENV)


# =========================================================================================== X1 (F1)
def test_X1_no_assert_statements_in_runner():
    for f in ("kprospect.py", "issue.py", "evaluate.py", "attest.py"):
        tree = ast.parse((RUNNER / f).read_text(encoding="utf-8"))
        assert not [n for n in ast.walk(tree) if isinstance(n, ast.Assert)], f


@pytest.mark.parametrize("what", ["plan", "amendment"])
def test_X1_changed_plan_or_amendment_rejected_under_python_O(tmp_path, what):
    d = y16_copy(tmp_path, edit_plan=(what == "plan"), edit_amendment=(what == "amendment"))
    fn = "plan_sha" if what == "plan" else "amendment_sha"
    r = run_O(f"K.Y16 = Path(r'{d}'); K.{fn}()")
    assert r.returncode != 0 and "IntegrityError" in r.stderr


@pytest.mark.parametrize("bad", ["2027-01-02", "2027-02-01", "27-01-01", "2027/01/01", "not-a-date"])
def test_X1_invalid_issue_date_rejected_under_python_O(bad):
    r = run_O(f"K.origin_of('{bad}')")
    assert r.returncode != 0 and "ValueError" in r.stderr


def test_X1_invalid_overlay_rejected_under_python_O(tmp_path):
    p = ov(tmp_path, ["BL,2026-Q4,150,2026-12-20,4.0,https://x.org/a,2026-12-21T00:00:00Z"])
    r = run_O(f"K.read_overlay(Path(r'{p}'))")
    assert r.returncode != 0 and "OverlayError" in r.stderr


def test_X1_tampered_seal_and_window_rejected_under_python_O(tmp_path, empty):
    f = K.issue_seal("2027-01-01", tmp_path / "s", empty, now_utc=JAN1)
    s = json.loads(f.read_text())
    s["forecasts"]["KAL"]["probability"] = 0.01
    f.write_text(json.dumps(s))
    r = run_O(f"K.load_seals(Path(r'{tmp_path / 's'}'), allow_clock_override=True)")
    assert r.returncode != 0 and "IntegrityError" in r.stderr
    r = run_O(f"K.issue_seal('2027-01-01', Path(r'{tmp_path / 'w'}'), Path(r'{empty}'), now_utc=dt.datetime(2026, 10, 30, tzinfo=dt.timezone.utc))")
    assert r.returncode != 0 and "IssueWindowError" in r.stderr and not (tmp_path / "w").exists()


# =========================================================================================== X2 (F2, F3)
BAD = [("H", "BL,2026-Q4,150,2026-12-20,4.0,{u},2026-12-21T00:00:00Z"), ("H", "BL,2026-Q4,-3,2026-12-20,4.0,{u},2026-12-21T00:00:00Z"),
       ("H", "BL,2026-Q4,nan,2026-12-20,4.0,{u},2026-12-21T00:00:00Z"), ("H", "BL,2026-Q4,inf,2026-12-20,4.0,{u},2026-12-21T00:00:00Z"),
       ("H", "BL,2026-Q4,abc,2026-12-20,4.0,{u},2026-12-21T00:00:00Z"),
       ("moe", "BL,2026-Q4,15,2026-12-20,-4.0,{u},2026-12-21T00:00:00Z"), ("moe", "BL,2026-Q4,15,2026-12-20,0,{u},2026-12-21T00:00:00Z"),
       ("moe", "BL,2026-Q4,15,2026-12-20,20,{u},2026-12-21T00:00:00Z"),
       ("quarter", "BL,2026-Q9,15,2026-12-20,4.0,{u},2026-12-21T00:00:00Z"), ("quarter", "BL,26-Q4,15,2026-12-20,4.0,{u},2026-12-21T00:00:00Z"),
       ("area", "XX,2026-Q4,15,2026-12-20,4.0,{u},2026-12-21T00:00:00Z"),
       ("published", "BL,2026-Q4,15,01/12/2027,4.0,{u},2027-01-13T00:00:00Z"),
       ("published", "BL,2026-Q4,15,2026-12-20T00:00:00,4.0,{u},2026-12-21T00:00:00Z"),
       ("published", "BL,2026-Q4,15,2026-12-31T20:00:00-08:00,4.0,{u},2027-01-02T00:00:00Z"),
       ("published", "BL,2026-Q4,15,2026-02-30,4.0,{u},2026-12-21T00:00:00Z"),
       ("published", "BL,2026-Q4,15,,4.0,{u},2026-12-21T00:00:00Z"),
       ("published", "BL,2027-Q2,15,2026-12-20,4.0,{u},2026-12-21T00:00:00Z"),          # before its quarter began
       ("published", "BL,2026-Q4,15,2026-12-20,4.0,{u},2026-12-01T00:00:00Z"),          # after the entry time
       ("entered_utc", "BL,2026-Q4,15,2026-12-20,4.0,{u},2026-12-21"),
       ("entered_utc", "BL,2026-Q4,15,2026-12-20,4.0,{u},2026-12-21T00:00:00+08:00"),
       ("source_url", "BL,2026-Q4,15,2026-12-20,4.0,,2026-12-21T00:00:00Z"),
       ("source_url", "BL,2026-Q4,15,2026-12-20,4.0,http://x.org/a,2026-12-21T00:00:00Z"),
       ("source_url", "BL,2026-Q4,15,2026-12-20,4.0,u,2026-12-21T00:00:00Z"),
       ("area", " BL,2026-Q4,15,2026-12-20,4.0,{u},2026-12-21T00:00:00Z")]


@pytest.mark.parametrize("field,row", BAD)
def test_X2_each_invalid_field_is_rejected_by_name(tmp_path, field, row):
    """Only one field is invalid per case (the others are valid), so the rejection is attributable to that field."""
    p = ov(tmp_path, [row.format(u=URL)])
    with pytest.raises(K.OverlayError, match=f"row 1 .*field '{field}'"):
        K.read_overlay(p)


def test_X2_header_must_match_exactly(tmp_path):
    p = ov(tmp_path, [OK_ROW + ",extra"], header=HDR.strip() + ",note\n")
    with pytest.raises(K.OverlayError, match="header"):
        K.read_overlay(p)


def test_X2_valid_row_keeps_source_metadata(tmp_path):
    d = K.read_overlay(ov(tmp_path, [OK_ROW]))
    assert d.loc[0, "source_url"] == URL and d.loc[0, "published"] == "2026-12-20" and d.loc[0, "entered_utc"] == "2026-12-21T00:00:00Z"


def test_X2_cutoff_rows_excluded_and_listed_in_seal(tmp_path, empty):
    p = ov(tmp_path, [OK_ROW, f"BL,2026-Q4,19.0,2027-01-03,4.0,{URL}/2,2027-01-03T05:00:00Z"])
    base = K.forecasts("2027-01-01")
    f = K.issue_seal("2027-01-01", tmp_path / "s", p, now_utc=dt.datetime(2027, 1, 4, 3, tzinfo=UTC))
    s = json.loads(f.read_text())
    assert [r["published"] for r in s["overlayRowsUsed"]] == ["2026-12-20"]
    assert s["overlayRowsExcludedByCutoff"] == [{"area": "BL", "quarter": "2026-Q4", "published": "2027-01-03"}]
    K.install_overlay(ov(tmp_path, [OK_ROW], "only_ok.csv"))
    assert s["forecasts"]["KAL"]["probability"] == K.forecasts("2027-01-01")["KAL"] != base["KAL"]


# =========================================================================================== X3 (F4, F5)
def test_X3_exact_duplicate_rows_rejected(tmp_path):
    with pytest.raises(K.OverlayError, match="exact duplicate"):
        K.read_overlay(ov(tmp_path, [OK_ROW, OK_ROW]))


def test_X3_conflicting_rows_rejected(tmp_path):
    with pytest.raises(K.OverlayError, match="conflicting"):
        K.read_overlay(ov(tmp_path, [OK_ROW, OK_ROW.replace(",15.0,", ",16.0,")]))


def test_X3_same_value_different_date_rejected_as_probable_duplicate(tmp_path):
    with pytest.raises(K.OverlayError, match="probable duplicate"):
        K.read_overlay(ov(tmp_path, [OK_ROW, OK_ROW.replace("2026-12-20", "2026-12-19")]))


def test_X3_conflict_with_project_series_rejected(tmp_path, empty):
    with pytest.raises(K.OverlayError, match="conflicts with the project series"):
        K.install_overlay(ov(tmp_path, [f"BL,2026-Q3,99.0,2026-10-14,4.0,{URL},2026-10-15T00:00:00Z"]))


def test_X3_project_value_with_other_date_rejected(tmp_path, empty):
    with pytest.raises(K.OverlayError, match="probable duplicate"):
        K.install_overlay(ov(tmp_path, [f"BL,2026-Q3,23.6,2026-10-20,4.0,{URL},2026-10-21T00:00:00Z"]))


def test_X3_exact_project_duplicate_ignored_and_reported(tmp_path, empty):
    assert K.install_overlay(ov(tmp_path, [f"BL,2026-Q3,23.6,2026-10-14,4.0,{URL},2026-10-15T00:00:00Z"])) == 0
    assert K.OVERLAY_REPORT["rowsAlreadyInProjectSeries"] == [1]


def test_X3_legitimate_second_round_added_and_reported(tmp_path, empty):
    n = K.install_overlay(ov(tmp_path, [f"BL,2026-Q3,21.0,2026-11-20,4.0,{URL},2026-11-21T00:00:00Z"]))
    assert n == 1 and K.OVERLAY_REPORT["rowsAddingARoundToAnExistingQuarter"] == [1]


def test_X3_failed_validation_leaves_previous_series_untouched(tmp_path, empty):
    before = K.forecasts("2027-01-01")
    with pytest.raises(K.OverlayError):
        K.install_overlay(ov(tmp_path, [OK_ROW, OK_ROW]))
    assert K.forecasts("2027-01-01") == before


# =========================================================================================== X4 (F7, F12)
def test_X4_seal_records_rows_snapshot_versions_and_hashes(tmp_path, empty):
    p = ov(tmp_path, [OK_ROW])
    f = K.issue_seal("2027-01-01", tmp_path / "s", p, now_utc=JAN1)
    s = json.loads(f.read_text())
    assert s["overlayRowsUsed"] == [{"area": "BL", "quarter": "2026-Q4", "H": 15.0, "published": "2026-12-20", "moe": 4.0,
                                     "source_url": URL, "entered_utc": "2026-12-21T00:00:00Z"}]
    snap = json.dumps(s["overlayRowsUsed"], sort_keys=True, separators=(",", ":"))
    assert s["overlaySnapshotSha256"] == hashlib.sha256(snap.encode()).hexdigest()
    assert s["overlayReport"]["overlaySha256"] == K.sha(p) and s["planSha256"] and s["amendment1Sha256"]
    assert {"hmodels.py", "rlib.py", "kprospect.py", "issue.py", "evaluate.py", "attest.py"} <= set(s["modelVersion"])
    assert {"python", "numpy", "scipy", "pandas", "sklearn"} <= set(s["environment"])          # F16


def test_X4_later_overlay_additions_do_not_change_the_seal_and_still_verify(tmp_path, empty):
    p = ov(tmp_path, [OK_ROW])
    f = K.issue_seal("2027-01-01", tmp_path / "s", p, now_utc=JAN1)
    h0 = K.sha(f)
    p.write_text(HDR + OK_ROW + "\n" + f"BL,2027-Q1,17.0,2027-04-20,4.0,{URL}/q1,2027-04-21T00:00:00Z\n", encoding="utf-8")
    assert K.sha(f) == h0
    d = K.load_seals(tmp_path / "s", allow_clock_override=True)
    assert K.verify_overlay(d, p) == 1


def test_X4_F12_altered_or_removed_overlay_row_stops_evaluation(tmp_path, empty):
    p = ov(tmp_path, [OK_ROW])
    K.issue_seal("2027-01-01", tmp_path / "s", p, now_utc=JAN1)
    p.write_text(HDR + OK_ROW.replace(",15.0,", ",5.0,") + "\n", encoding="utf-8")
    with pytest.raises(K.IntegrityError, match="overlay history changed"):
        EV.evaluate(tmp_path / "s", p, dt.date(2027, 1, 3), allow_clock_override=True)
    p.write_text(HDR, encoding="utf-8")
    with pytest.raises(K.IntegrityError, match="overlay history changed"):
        EV.evaluate(tmp_path / "s", p, dt.date(2027, 1, 3), allow_clock_override=True)


# =========================================================================================== X5 (F8)
def test_X5_deleted_registered_seal_detected(tmp_path, empty):
    f = K.issue_seal("2027-01-01", tmp_path / "s", empty, now_utc=JAN1)
    f.unlink()
    assert K.reconcile(tmp_path / "s")["missingFiles"] == [f.name]
    with pytest.raises(K.IntegrityError, match="missingFiles"):
        K.load_seals(tmp_path / "s", allow_clock_override=True)


def test_X5_unregistered_and_malformed_detected(tmp_path, empty):
    f = K.issue_seal("2027-01-01", tmp_path / "s", empty, now_utc=JAN1)
    shutil.copy(f, tmp_path / "s" / "seal_issue_2027-04-01_written_20270401T030000Z.json")
    with open(tmp_path / "s" / "SEALS.txt", "a") as g:
        g.write("garbage line\n")
    rec = K.reconcile(tmp_path / "s")
    assert rec["unregisteredFiles"] == ["seal_issue_2027-04-01_written_20270401T030000Z.json"]
    assert rec["malformedRegistryLines"] == [2] and not rec["ok"]


def test_X5_reissue_refused_and_manual_reissue_reported(tmp_path, empty):
    pd_ = tmp_path / "s"
    f = K.issue_seal("2027-01-01", pd_, empty, now_utc=JAN1)
    with pytest.raises(K.ReissueError):
        K.issue_seal("2027-01-01", pd_, empty, now_utc=dt.datetime(2027, 1, 2, 3, tzinfo=UTC))
    s = json.loads(f.read_text())                                  # simulate a manually planted second valid seal
    s["writtenUtc"] = "2027-01-02T03:00:00Z"
    g = pd_ / "seal_issue_2027-01-01_written_20270102T030000Z.json"
    g.write_text(json.dumps(s, indent=1))
    with open(pd_ / "SEALS.txt", "a") as h:
        h.write(f"{g.name} {K.sha(g)} validProspective=True\n")
    res = EV.evaluate(pd_, empty, dt.date(2027, 1, 3), allow_clock_override=True)
    assert res["integrity"]["reissues"] == {"2027-01-01": [f.name, g.name]}
    assert res["validSeals"] == 1                                  # the first by write time counts (registered rule)


def test_X5_documented_limit_consistent_rewrite_is_local_only(tmp_path, empty):
    pd_ = tmp_path / "s"
    f = K.issue_seal("2027-01-01", pd_, empty, now_utc=JAN1)
    s = json.loads(f.read_text())
    s["forecasts"]["KAL"]["probability"] = 0.01
    f.write_text(json.dumps(s, indent=1))
    (pd_ / "SEALS.txt").write_text(f"{f.name} {K.sha(f)} validProspective=True\n")
    rec = K.reconcile(pd_)
    assert rec["ok"] and "external attestation" in rec["limits"]   # not detectable locally; stated, not claimed


# =========================================================================================== X6 (F9)
def test_X6_attestation_payload_and_pending_status(tmp_path, empty):
    f = K.issue_with_log("2027-01-01", tmp_path / "s", empty, now_utc=JAN1)
    payload = (tmp_path / "s" / "attestations" / f"{f.stem}.attestation.txt").read_text().strip()
    for part in ("issue=2027-01-01", "target=2027-Q2", f"sealSha256={K.sha(f)}", f"planSha256={K.plan_sha()}",
                 f"amendment1Sha256={K.amendment_sha()}", "writtenUtc=2027-01-01T03:00:00Z"):
        assert part in payload
    assert K.attestation_status(tmp_path / "s") == {f.name: "pending"}


def test_X6_operator_records_status_never_inferred(tmp_path, empty):
    f = K.issue_with_log("2027-01-01", tmp_path / "s", empty, now_utc=JAN1)
    with pytest.raises(ValueError):
        AT.record(tmp_path / "s", f.name, "pending", "x", "y")
    with pytest.raises(ValueError):
        AT.record(tmp_path / "s", f.name, "completed", "e-mail", " ")
    AT.record(tmp_path / "s", f.name, "completed", "e-mail to adviser", "receipt 123")
    assert K.attestation_status(tmp_path / "s") == {f.name: "completed"}
    res = EV.evaluate(tmp_path / "s", empty, dt.date(2027, 1, 3), allow_clock_override=True)
    assert res["supplementary"]["attestationStatus"] == {f.name: "completed"}


def test_X6_nothing_is_transmitted():
    for f in ("kprospect.py", "attest.py", "issue.py", "evaluate.py"):
        src = (RUNNER / f).read_text(encoding="utf-8")
        for mod in ("smtplib", "urllib", "requests", "http.client", "socket"):
            assert f"import {mod}" not in src and f"from {mod}" not in src, (f, mod)


def test_X6_F9_caller_supplied_clock_refused_by_real_evaluation(tmp_path, empty):
    f = K.issue_seal("2027-01-01", tmp_path / "s", empty, now_utc=JAN1)
    assert json.loads(f.read_text())["clockSource"] == "caller-supplied"
    with pytest.raises(K.IntegrityError, match="clockSource"):
        K.load_seals(tmp_path / "s")


# =========================================================================================== X7 (F11 failure log)
@pytest.mark.parametrize("case", ["bad_date", "bad_overlay", "existing_seal", "outside_window", "plan_mismatch"])
def test_X7_failed_attempts_logged_original_exception_kept_no_seal(tmp_path, empty, monkeypatch, case):
    out = tmp_path / "s"
    issue, overlay, now, exc = "2027-01-01", empty, JAN1, None
    if case == "bad_date":
        issue, exc = "2027-01-02", ValueError
    elif case == "bad_overlay":
        overlay, exc = ov(tmp_path, [OK_ROW, OK_ROW], "bad.csv"), K.OverlayError
    elif case == "existing_seal":
        K.issue_with_log("2027-01-01", out, empty, now_utc=JAN1)
        now, exc = dt.datetime(2027, 1, 2, 3, tzinfo=UTC), K.ReissueError
    elif case == "outside_window":
        now, exc = dt.datetime(2026, 10, 30, tzinfo=UTC), K.IssueWindowError
    else:
        monkeypatch.setattr(K, "Y16", y16_copy(tmp_path, edit_plan=True))
        exc = K.IntegrityError
    seals_before = sorted(p.name for p in out.glob("seal_*.json")) if out.exists() else []
    with pytest.raises(exc):
        K.issue_with_log(issue, out, overlay, now_utc=now)
    log = K.read_attempts(out)
    assert log[-1]["result"] == "failed" and log[-1]["errorType"] == exc.__name__ and log[-1]["issueRequested"] == issue
    assert {"python", "numpy"} <= set(log[-1]["environment"]) and "attemptUtc" in log[-1]
    assert sorted(p.name for p in out.glob("seal_*.json")) == seals_before            # no seal created by the failure
    monkeypatch.undo()
    assert len(K.load_seals(out, allow_clock_override=True)) == len(seals_before)


def test_X7_dry_runs_are_not_attempts_and_never_valid(tmp_path, empty):
    f = K.issue_seal("2026-10-01", tmp_path / "d", empty, now_utc=dt.datetime(2026, 10, 30, tzinfo=UTC), dry_run=True)
    assert json.loads(f.read_text())["validProspective"] is False
    assert K.read_attempts(tmp_path / "d") == [] and K.load_seals(tmp_path / "d").empty


def test_X7_F17_cli_refuses_and_logs_non_canonical_overlay_for_real_issue(tmp_path, monkeypatch):
    fake = tmp_path / "y16"
    (fake / "prospective").mkdir(parents=True)
    monkeypatch.setattr(K, "Y16", fake)
    with pytest.raises(SystemExit):
        IS.main(["--issue", "2027-01-01", "--overlay", str(ov(tmp_path, [], "other.csv"))])
    assert K.read_attempts(fake / "prospective")[-1]["errorType"] == "NonCanonicalOverlay"
    assert not list((fake / "prospective").glob("seal_*.json"))


# =========================================================================================== evaluation (F6, F10, F11, F14, F18)
def test_F6_primary_lock_written_once_and_enforced(tmp_path):
    out = tmp_path / "o"
    assert K.lock_primary(out, {"a": 1}) == "primary analysis written and locked"
    first = (out / "PRIMARY_ANALYSIS.json").read_text()
    assert K.lock_primary(out, {"a": 1}).startswith("primary locked (unchanged")
    with pytest.raises(K.IntegrityError, match="already locked"):
        K.lock_primary(out, {"a": 2})
    assert (out / "PRIMARY_ANALYSIS.json").read_text() == first


def test_F10_calibration_supplementary_and_unavailable_when_small():
    c = K.calibration([1, 0, 1, 1], [.9, .2, .7, .6])
    assert c["slope"] == "unavailable" and c["label"].startswith("supplementary") and sum(b["n"] for b in c["bins"]) == 4
    rng = np.random.default_rng(0)
    y = np.array([1, 0] * 10)
    c = K.calibration(y, np.clip(y * .6 + .2 + rng.normal(0, .1, 20), .01, .99))
    assert isinstance(c["slope"], float) and len(c["bins"]) == 5


def test_F11_missed_issues_counted_only_after_window_closes(tmp_path, empty):
    pd_ = tmp_path / "s"
    K.issue_seal("2027-04-01", pd_, empty, now_utc=dt.datetime(2027, 4, 1, 3, tzinfo=UTC))
    d = K.load_seals(pd_, allow_clock_override=True)
    assert K.missed_issues(d, dt.date(2027, 4, 2)) == ["2027-01-01"]
    assert K.missed_issues(d.iloc[0:0], dt.date(2027, 1, 8)) == []                  # window still open
    assert K.missed_issues(d.iloc[0:0], dt.date(2027, 1, 9)) == ["2027-01-01"]
    res = EV.evaluate(pd_, empty, dt.date(2027, 4, 2), allow_clock_override=True)
    assert res["supplementary"]["missedIssues"] == ["2027-01-01"]


def test_F14_block_bootstrap_per_amendment():
    t = [R.qs(R.qi("2027-Q2") + i) for i in range(20)]
    rng = np.random.default_rng(3)
    y = (rng.random(20) > .3).astype(int)
    d = pd.DataFrame({"target": t, "y": y, "PERS": rng.random(20), "KAL": rng.random(20)})
    b = K.block_paired(d)
    assert b["blockLength"] == 4 and b["n"] == 20 and b["gapsInSeries"] == 0 and "robust" in b
    assert b == K.block_paired(d)                                                  # fixed seed: deterministic
    assert K.block_paired(d.head(7))["result"].startswith("unavailable")
    assert abs(b["meanDiff_KAL_minus_PERS"] - K.paired(d)["meanDiff_KAL_minus_PERS"]) < 1e-12


def test_F14_sensitivity_cannot_rescue_a_failed_primary():
    src = (RUNNER / "evaluate.py").read_text(encoding="utf-8")
    assert 'if primary["superiority"]:' in src and 'verdict = "no superiority"' in src
    assert 'pr["p_one_sided_bootstrap"] < 0.05 and pr["CI95"][1] < 0' in src             # registered thresholds unchanged


def test_F18_evaluation_uses_manila_date():
    assert "dt.datetime.now(K.MANILA).date()" in (RUNNER / "evaluate.py").read_text(encoding="utf-8")


def test_amendment_hash_matches_and_is_enforced(tmp_path, monkeypatch):
    assert K.amendment_sha() == (Y16 / "BOOTSTRAP_AMENDMENT_SHA256.txt").read_text().split()[0]
    assert K.sha(Y16.parent / "y17_integrity_audit" / "BOOTSTRAP_AMENDMENT.md") == K.amendment_sha()
    monkeypatch.setattr(K, "Y16", y16_copy(tmp_path, edit_amendment=True))
    with pytest.raises(K.IntegrityError):
        K.amendment_sha()


def test_plan_hash_unchanged():
    assert K.plan_sha() == "208b575464d21e41dd78447c39e4586fb7101bdb0b263f298b210b7701bd9699"
