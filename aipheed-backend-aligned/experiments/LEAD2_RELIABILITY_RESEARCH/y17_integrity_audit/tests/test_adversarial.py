"""Y17 adversarial tests of the Y16 workflow. All writes go to pytest's tmp_path; the real overlay, prospective/ and
dry_runs/ are never written. Defect tests assert the CORRECT behaviour and are xfail(strict=True): they fail today
as evidence; when a defect is fixed they XPASS and the strict marker forces a review.

    python -m pytest -q tests -p no:cacheprovider -rxX
"""
from __future__ import annotations

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

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

import kprospect as K  # noqa: E402
import evaluate as EV  # noqa: E402

R = K.R
UTC = dt.timezone.utc
HDR = "area,quarter,H,published,moe,source_url,entered_utc\n"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def ov(tmp_path, rows, name="ov.csv") -> Path:
    p = tmp_path / name
    p.write_text(HDR + "".join(r + "\n" for r in rows), encoding="utf-8")
    return p


@pytest.fixture()
def empty(tmp_path):
    p = ov(tmp_path, [], "empty.csv")
    K.install_overlay(p)
    yield p
    K.install_overlay(p)


def fake_y16(tmp_path) -> Path:
    """A temporary copy of the plan files, to test enforcement without touching the real plan."""
    d = tmp_path / "y16copy"
    d.mkdir()
    for f in ("EXPERIMENT_PLAN.md", "PLAN_SHA256.txt"):
        shutil.copy(Y16 / f, d / f)
    return d


# =========================================================================================== A preregistration
def test_A1_plan_hash_matches_independently():
    h = hashlib.sha256((Y16 / "EXPERIMENT_PLAN.md").read_bytes()).hexdigest()
    assert h == (Y16 / "PLAN_SHA256.txt").read_text().split()[0] == "208b575464d21e41dd78447c39e4586fb7101bdb0b263f298b210b7701bd9699"


def test_A2_plan_frozen_before_code_by_file_times():
    frozen = pd.Timestamp((Y16 / "PLAN_FROZEN_AT.txt").read_text().strip()).timestamp()
    assert os.path.getmtime(Y16 / "EXPERIMENT_PLAN.md") <= frozen + 1
    for f in ("runner/kprospect.py", "runner/issue.py", "runner/evaluate.py", "tests/test_y16.py"):
        assert os.path.getmtime(Y16 / f) > frozen


def test_A3_changed_plan_is_rejected(tmp_path, monkeypatch):
    d = fake_y16(tmp_path)
    (d / "EXPERIMENT_PLAN.md").write_text("edited", encoding="utf-8")
    monkeypatch.setattr(K, "Y16", d)
    with pytest.raises(AssertionError):
        K.plan_sha()


@pytest.mark.xfail(strict=True, reason="F1 confirmed defect: integrity checks are `assert` statements, removed by python -O")
def test_A4_plan_check_survives_python_O(tmp_path):
    d = fake_y16(tmp_path)
    (d / "EXPERIMENT_PLAN.md").write_text("edited", encoding="utf-8")
    code = f"import sys; sys.path.insert(0, r'{RUNNER}'); import kprospect as K; from pathlib import Path; K.Y16 = Path(r'{d}'); K.plan_sha()"
    r = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True, env=ENV)
    assert r.returncode != 0, "a changed plan was accepted under python -O"


def test_A5_superiority_rule_matches_plan_on_synthetic_primary(monkeypatch):
    # plan: bootstrap p < 0.05, CI95 entirely below 0, sign test p < 0.10 (all three)
    res = {"p_one_sided_bootstrap": 0.04, "CI95": [-0.05, -0.001], "signTest": {"p_one_sided": 0.09}}
    ok = res["p_one_sided_bootstrap"] < 0.05 and res["CI95"][1] < 0 and res["signTest"]["p_one_sided"] < 0.10
    src = (RUNNER / "evaluate.py").read_text(encoding="utf-8")
    assert 'pr["p_one_sided_bootstrap"] < 0.05 and pr["CI95"][1] < 0' in src and 'pr["signTest"]["p_one_sided"] < 0.10' in src
    assert ok


@pytest.mark.xfail(strict=True, reason="F6 confirmed defect: the primary analysis is recomputed and re-written on every run; nothing locks it")
def test_A6_primary_analysis_is_locked_after_first_run():
    src = (RUNNER / "evaluate.py").read_text(encoding="utf-8")
    assert "primary" in src.lower() and ("lock" in src.lower() or "already" in src.lower())


# =========================================================================================== B timing
@pytest.mark.parametrize("y", range(2027, 2033))
def test_B1_mapping_is_derived_not_hardcoded(y):
    for m, qo in ((1, 4), (4, 1), (7, 2), (10, 3)):
        t = K.origin_of(f"{y}-{m:02d}-01")
        assert R.issue(t) == pd.Timestamp(f"{y}-{m:02d}-01")
        oy = y - 1 if m == 1 else y
        assert R.qs(t) == f"{oy}-Q{qo}" and R.qs(t + 2) == R.qs(R.qi(f"{oy}-Q{qo}") + 2)
    assert R.qs(K.origin_of("2027-01-01") + 2) == "2027-Q2"


@pytest.mark.parametrize("now,inside", [("2026-12-31T15:59:59Z", False), ("2026-12-31T16:00:00Z", True),
                                        ("2027-01-08T15:59:59Z", True), ("2027-01-08T16:00:00Z", False)])
def test_B2_manila_window_boundaries(now, inside):
    n = pd.Timestamp(now).to_pydatetime()
    assert K.window_status("2027-01-01", n)["inWindow"] is inside


@pytest.mark.parametrize("bad", ["2027-01-02", "2027-02-01", "2027-13-01", "not-a-date"])
def test_B3_invalid_issue_dates_rejected_by_cli(bad):
    r = subprocess.run([sys.executable, "-B", str(RUNNER / "issue.py"), "--issue", bad, "--dry-run",
                        "--overlay", str(Y16 / "data" / "sws_rounds_overlay.csv")], capture_output=True, text=True, env=ENV, cwd=str(RUNNER))
    assert r.returncode != 0


@pytest.mark.xfail(strict=True, reason="F1 confirmed defect: origin_of validates with assert; python -O lets a non-quarter-start date through")
def test_B4_invalid_issue_date_rejected_under_python_O():
    code = f"import sys; sys.path.insert(0, r'{RUNNER}'); import kprospect as K; K.origin_of('2027-01-02')"
    r = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True, env=ENV)
    assert r.returncode != 0


def test_B5_risk_library_allows_a_backdated_timestamp(tmp_path, empty):
    """Potential risk F9: the window is checked against the system clock or a caller-supplied now_utc; nothing
    external attests the write time, so a backdated 'valid' seal can be fabricated through the library."""
    f = K.issue_seal("2026-10-01", tmp_path / "p", empty, now_utc=dt.datetime(2026, 10, 1, 3, tzinfo=UTC))
    assert json.loads(f.read_text())["validProspective"] is True


@pytest.mark.parametrize("pub", ["2027-01-01", "2027-01-01T00:00:00", "2027-01-05"])
def test_B6_rounds_on_or_after_issue_are_excluded(tmp_path, empty, pub):
    base = K.forecasts("2027-01-01")
    K.install_overlay(ov(tmp_path, [f"BL,2026-Q4,40.0,{pub},4.0,u,2026-10-29T00:00:00Z"]))
    assert K.forecasts("2027-01-01")["KAL"] == base["KAL"]


@pytest.mark.xfail(strict=True, reason="F3 confirmed defect: ambiguous non-ISO dates are parsed silently (12/01/2026 -> Dec 1)")
def test_B7_non_iso_publication_date_rejected(tmp_path):
    with pytest.raises(Exception):
        K.read_overlay(ov(tmp_path, ["BL,2026-Q4,15.0,01/12/2027,4.0,u,2026-10-29T00:00:00Z"]))  # 12 Jan or 1 Dec?
        K.install_overlay(ov(tmp_path, ["BL,2026-Q4,15.0,01/12/2027,4.0,u,2026-10-29T00:00:00Z"], "b.csv"))


def test_B8_timezone_aware_date_does_not_leak(tmp_path, empty):
    """2026-12-31T20:00-08:00 is 2027-01-01 04:00 UTC: it must not be admitted for the 2027-01-01 issue."""
    base = K.forecasts("2027-01-01")
    p = ov(tmp_path, ["BL,2026-Q4,40.0,2026-12-31T20:00:00-08:00,4.0,u,2026-10-29T00:00:00Z"])
    try:
        K.install_overlay(p)
        after = K.forecasts("2027-01-01")
    except Exception:
        return                                           # fails closed: acceptable
    assert after["KAL"] == base["KAL"], "a round published after the origin (in UTC) was admitted"


# =========================================================================================== C parity and leakage
def test_C1_same_functions_as_y14_y15():
    src = (RUNNER / "kprospect.py").read_text(encoding="utf-8")
    assert 'R.forecast("BL", t, 2, AREAS)' in src and 'HM.kalman("BL", t, 2, AREAS)' in src
    assert K.AREAS == ("NCR", "BL", "VIS", "MIN")
    y15 = (Y16.parent / "y15_food_insecurity_improvement" / "runner" / "run.py").read_text(encoding="utf-8")
    assert 'HM.kalman("BL", int(t), 2, tuple(R.AREAS))' in y15


def test_C2_both_models_share_origin_target_and_cutoff(empty):
    f = K.forecasts("2027-01-01")
    assert f["origin"] == "2026-Q4" and f["target"] == "2027-Q2" and f["newestSws"]["quarter"] == "2026-Q3"
    assert f["newestSws"]["lastPublished"] < "2027-01-01"


def test_C3_persistence_uses_only_latest_eligible_reading(tmp_path, empty):
    K.install_overlay(ov(tmp_path, ["BL,2026-Q4,11.3,2026-12-20,4.0,u,2026-10-29T00:00:00Z"]))
    f = K.forecasts("2027-01-01")
    assert f["newestSws"]["value"] == 11.3 and abs(f["PERS"] - 0.5) < 1e-12        # Phi(0) exactly
    assert f["aux"]["PERSIST_binary"] == 0.0                                       # > 11.3 is required


@pytest.mark.xfail(strict=True, reason="F4 confirmed defect: identical rows inside the overlay are each added (double-counted)")
def test_C4_duplicate_rows_within_overlay_are_not_double_counted(tmp_path, empty):
    row = "BL,2026-Q4,30.0,2026-12-20,4.0,u,2026-10-29T00:00:00Z"
    once = ov(tmp_path, [row], "once.csv")
    twice = ov(tmp_path, [row, row], "twice.csv")
    K.install_overlay(once)
    a = K.forecasts("2027-01-01")["KAL"]
    K.install_overlay(twice)
    b = K.forecasts("2027-01-01")["KAL"]
    assert a == b


def test_C5_deterministic_across_processes(empty):
    code = (f"import sys; sys.path.insert(0, r'{RUNNER}'); import kprospect as K; from pathlib import Path; "
            f"K.install_overlay(Path(r'{empty}')); f = K.forecasts('2027-01-01'); print(repr(f['PERS']), repr(f['KAL']))")
    outs = {subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, env=ENV).stdout.strip() for _ in range(2)}
    assert len(outs) == 1 and outs.pop()


# =========================================================================================== D overlay and provenance
@pytest.mark.xfail(strict=True, reason="F2 confirmed defect: overlay values are not range-checked")
@pytest.mark.parametrize("row", ["BL,2026-Q4,150,2026-12-20,4.0,u,2026-10-29T00:00:00Z",
                                 "BL,2026-Q4,-3,2026-12-20,4.0,u,2026-10-29T00:00:00Z",
                                 "BL,2026-Q4,15,2026-12-20,-4.0,u,2026-10-29T00:00:00Z",
                                 "BL,2026-Q9,15,2026-12-20,4.0,u,2026-10-29T00:00:00Z",
                                 "BL,2026-Q4,15,2026-12-20,4.0,,2026-10-29T00:00:00Z",
                                 "BL,2026-Q4,15,2026-12-20,4.0,u,",
                                 "BL,2027-Q2,15,2026-12-20,4.0,u,2026-10-29T00:00:00Z",
                                 "BL,2026-Q4,15,2026-12-20,4.0,u,2026-12-01T00:00:00Z"])
def test_D1_invalid_overlay_rows_rejected(tmp_path, row):
    """150 / -3 hunger; negative MoE; quarter Q9; empty source URL; empty entry time; a 2027-Q2 round 'published'
    before its quarter began; publication after the recorded entry time."""
    with pytest.raises(Exception):
        p = ov(tmp_path, [row])
        K.read_overlay(p)
        K.install_overlay(p)


def test_D2_valid_area_and_date_presence_enforced(tmp_path):
    with pytest.raises(AssertionError):
        K.read_overlay(ov(tmp_path, ["XX,2026-Q4,15,2026-12-20,4.0,u,2026-10-29T00:00:00Z"]))
    with pytest.raises(AssertionError):
        K.read_overlay(ov(tmp_path, ["BL,2026-Q4,15,,4.0,u,2026-10-29T00:00:00Z"]))


@pytest.mark.xfail(strict=True, reason="F5 confirmed defect: a conflicting value for an existing project round is silently ignored")
def test_D3_conflict_with_project_round_is_reported(tmp_path, empty):
    p = ov(tmp_path, ["BL,2026-Q3,99.0,2026-10-14,4.0,u,2026-10-29T00:00:00Z"])     # project has 23.6
    with pytest.raises(Exception):
        K.install_overlay(p)


def test_D4_exact_duplicate_of_project_round_is_ignored(tmp_path, empty):
    assert K.install_overlay(ov(tmp_path, ["BL,2026-Q3,23.6,2026-10-14,4.0,u,2026-10-29T00:00:00Z"])) == 0


@pytest.mark.xfail(strict=True, reason="F7 confirmed defect: the seal keeps only the overlay hash, not the rows/source URLs used")
def test_D5_seal_preserves_overlay_provenance(tmp_path, empty):
    p = ov(tmp_path, ["BL,2026-Q4,15.0,2026-12-20,4.0,https://www.sws.org.ph/example,2026-12-21T00:00:00Z"])
    f = K.issue_seal("2027-01-01", tmp_path / "s", p, now_utc=dt.datetime(2027, 1, 1, 3, tzinfo=UTC))
    assert "https://www.sws.org.ph/example" in f.read_text(encoding="utf-8")


def test_D6_input_hashes_cover_sws_files_overlay_and_code(tmp_path, empty):
    f = K.issue_seal("2027-01-01", tmp_path / "s", empty, now_utc=dt.datetime(2027, 1, 1, 3, tzinfo=UTC))
    s = json.loads(f.read_text())
    keys = " ".join(s["inputs"])
    assert "sws_area_rounds_full.csv" in keys and "sws_rounds.csv" in keys and "empty.csv" in keys
    assert {"hmodels.py", "rlib.py", "kprospect.py", "issue.py"} <= set(s["modelVersion"])


def test_D7_risk_seal_and_registry_edited_together_go_undetected(tmp_path, empty):
    """Potential risk F8: the registry is a plain file next to the seals; editing both consistently is undetected."""
    pd_ = tmp_path / "s"
    f = K.issue_seal("2027-01-01", pd_, empty, now_utc=dt.datetime(2027, 1, 1, 3, tzinfo=UTC))
    s = json.loads(f.read_text())
    s["forecasts"]["KAL"]["probability"] = 0.01
    f.write_text(json.dumps(s, indent=1))
    (pd_ / "SEALS.txt").write_text(f"{f.name} {K.sha(f)} validProspective=True\n", encoding="utf-8")
    assert float(K.load_seals(pd_)["KAL"].iloc[0]) == 0.01


@pytest.mark.xfail(strict=True, reason="F8 confirmed defect: a registered seal whose file was deleted is not detected")
def test_D8_deleted_seal_is_detected(tmp_path, empty):
    pd_ = tmp_path / "s"
    f = K.issue_seal("2027-01-01", pd_, empty, now_utc=dt.datetime(2027, 1, 1, 3, tzinfo=UTC))
    f.unlink()
    with pytest.raises(Exception):
        K.load_seals(pd_)


@pytest.mark.xfail(strict=True, reason="F8 confirmed defect: an unregistered seal file (not in SEALS.txt) fails only via assert; "
                                       "a second valid seal for the same issue is silently dropped, not reported")
def test_D9_reissue_for_same_date_is_reported(tmp_path, empty):
    pd_ = tmp_path / "s"
    K.issue_seal("2027-01-01", pd_, empty, now_utc=dt.datetime(2027, 1, 1, 3, tzinfo=UTC))
    K.issue_seal("2027-01-01", pd_, empty, now_utc=dt.datetime(2027, 1, 2, 3, tzinfo=UTC))
    res = EV.evaluate(pd_, empty, dt.date(2027, 1, 3))
    assert "reissued" in json.dumps(res).lower() or "duplicate" in json.dumps(res).lower()


# =========================================================================================== E evaluation
def test_E1_outcome_waits_120_days_and_missing_is_nan():
    assert K.outcome("2026-Q2", dt.date(2026, 10, 27)) is None          # 2026-06-30 + 120 = 2026-10-28
    assert K.outcome("2026-Q2", dt.date(2026, 10, 28)) == pytest.approx(17.3)
    v = K.outcome("2022-Q1", dt.date(2026, 10, 29))                     # BL has no 2022-Q1 round
    assert v != v                                                       # NaN -> reported as missingOutcome


def test_E2_paired_direction_ci_and_sign_test_by_hand():
    import numpy as np
    d = pd.DataFrame({"y": [1, 0, 1, 1, 0], "PERS": [.9, .2, .4, .6, .7], "KAL": [.8, .3, .6, .9, .5]})
    p = K.paired(d)
    di = np.array([(.8 - 1) ** 2 - (.9 - 1) ** 2, .3 ** 2 - .2 ** 2, (.6 - 1) ** 2 - (.4 - 1) ** 2,
                   (.9 - 1) ** 2 - (.6 - 1) ** 2, .5 ** 2 - .7 ** 2])
    assert p["meanDiff_KAL_minus_PERS"] == pytest.approx(di.mean())
    assert p["CI95"][0] <= di.mean() <= p["CI95"][1]
    assert p["signTest"]["KAL_better"] == int((di < 0).sum()) and p["signTest"]["nonZero"] == 5


def test_E3_metrics_small_sample_unavailable_not_misleading():
    m = K.metrics([1, 1, 1], [.9, .8, .4])
    assert m["auc"] is None and m["balanced"] is None and m["specificity"] is None


@pytest.mark.xfail(strict=True, reason="F10 confirmed defect: calibration (registered in plan section 5) is not computed by evaluate.py")
def test_E4_calibration_reported():
    src = (RUNNER / "evaluate.py").read_text(encoding="utf-8") + (RUNNER / "kprospect.py").read_text(encoding="utf-8")
    assert "calib" in src.lower()


@pytest.mark.xfail(strict=True, reason="F11 confirmed defect: missed issue windows are not enumerated or counted (plan section 5)")
def test_E5_missed_issue_dates_are_counted(tmp_path, empty):
    pd_ = tmp_path / "s"
    K.issue_seal("2027-04-01", pd_, empty, now_utc=dt.datetime(2027, 4, 1, 3, tzinfo=UTC))     # 2027-01-01 missed
    res = EV.evaluate(pd_, empty, dt.date(2027, 4, 2))
    assert "2027-01-01" in json.dumps(res)


@pytest.mark.xfail(strict=True, reason="F12 confirmed defect: evaluate.py does not verify the overlay is append-only against the seals (plan section 5)")
def test_E6_edited_overlay_row_after_sealing_is_detected(tmp_path, empty):
    p = ov(tmp_path, ["BL,2026-Q4,15.0,2026-12-20,4.0,u,2026-12-21T00:00:00Z"])
    K.issue_seal("2027-01-01", tmp_path / "s", p, now_utc=dt.datetime(2027, 1, 1, 3, tzinfo=UTC))
    p.write_text(HDR + "BL,2026-Q4,5.0,2026-12-20,4.0,u,2026-12-21T00:00:00Z\n", encoding="utf-8")   # history rewritten
    with pytest.raises(Exception):
        EV.evaluate(tmp_path / "s", p, dt.date(2027, 1, 3))


def test_E7_seven_rules_on_synthetic_20_rows():
    import numpy as np
    rng = np.random.default_rng(1)
    y = np.array([1] * 14 + [0] * 6)
    d = pd.DataFrame({"target": [R.qs(R.qi("2027-Q2") + i) for i in range(20)], "y": y,
                      "PERS": np.clip(y * .7 + .15 + rng.normal(0, .05, 20), 0, 1),
                      "KAL": np.clip(y * .8 + .1 + rng.normal(0, .05, 20), 0, 1),
                      "PERSIST": y.astype(float), "CLIM": np.full(20, .6)})
    r = K.seven_rules(d, "KAL")
    assert r["estimable"] and r["rules"]["R1"]["pass"] is False          # 20 rows < 40
    assert r["rules"]["R2"]["pass"] and r["rules"]["R3"]["pass"] and r["rules"]["R6"]["pass"]
    assert K.seven_rules(d, "PERS")["rules"]["R5"]["pass"] is None


def test_E8_primary_uses_first_20_resolved_in_issue_order_and_descriptive_below():
    src = (RUNNER / "evaluate.py").read_text(encoding="utf-8")
    assert "PRIMARY_N, DESCRIPTIVE_N = 20, 8" in src and 'sort_values("issue")' in src and "r.head(PRIMARY_N)" in src
    assert "descriptive (no hypothesis test" in src
