"""Y16 tests (EXPERIMENT_PLAN.md section 6). Every write goes to pytest's tmp_path; prospective/ is never touched.

    python -m pytest -q tests -p no:cacheprovider
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

import kprospect as K  # noqa: E402

R = K.R
UTC = dt.timezone.utc
HDR = "area,quarter,H,published,moe,source_url,entered_utc\n"


@pytest.fixture()
def empty_overlay(tmp_path):
    p = tmp_path / "overlay.csv"
    p.write_text(HDR, encoding="utf-8")
    K.install_overlay(p)
    yield p
    K.install_overlay(p)


def overlay_with(tmp_path, rows: list[str]) -> Path:
    p = tmp_path / "overlay_rows.csv"
    p.write_text(HDR + "".join(r + "\n" for r in rows), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------------------------- timing
@pytest.mark.parametrize("issue,origin,target", [("2027-01-01", "2026-Q4", "2027-Q2"), ("2027-04-01", "2027-Q1", "2027-Q3"),
                                                 ("2027-10-01", "2027-Q3", "2028-Q1"), ("2026-10-01", "2026-Q3", "2027-Q1")])
def test_issue_to_target_mapping(issue, origin, target):
    t = K.origin_of(issue)
    assert R.qs(t) == origin and R.qs(t + 2) == target


def test_non_quarter_start_is_rejected():
    with pytest.raises(ValueError):
        K.origin_of("2027-01-02")


def test_window_rules():
    assert K.window_status("2027-01-01", dt.datetime(2027, 1, 1, 0, 30, tzinfo=UTC))["inWindow"]          # 08:30 Manila
    assert K.window_status("2027-01-01", dt.datetime(2026, 12, 31, 17, 0, tzinfo=UTC))["inWindow"]         # 01:00 Manila, Jan 1
    assert not K.window_status("2027-01-01", dt.datetime(2026, 12, 31, 15, 0, tzinfo=UTC))["inWindow"]     # Dec 31 Manila
    assert K.window_status("2027-01-01", dt.datetime(2027, 1, 8, 12, 0, tzinfo=UTC))["inWindow"]
    assert not K.window_status("2027-01-01", dt.datetime(2027, 1, 9, 12, 0, tzinfo=UTC))["inWindow"]


# ---------------------------------------------------------------------------------------------- no future data
def test_rounds_published_on_or_after_issue_do_not_change_the_forecast(tmp_path, empty_overlay):
    base = K.forecasts("2027-01-01")
    fut = overlay_with(tmp_path, [f"{a},2026-Q4,40.0,2027-01-01,4.0,https://example.org/test,2027-01-02T00:00:00Z" for a in K.AREAS] +
                       [f"{a},2026-Q4,41.0,2027-02-15,4.0,https://example.org/test,2027-02-16T00:00:00Z" for a in K.AREAS])
    K.install_overlay(fut)
    after = K.forecasts("2027-01-01")
    assert after["PERS"] == base["PERS"] and after["KAL"] == base["KAL"]
    assert after["newestSws"] == base["newestSws"]


def test_round_published_before_issue_is_used_positive_control(tmp_path, empty_overlay):
    base = K.forecasts("2027-01-01")
    p = overlay_with(tmp_path, ["BL,2026-Q4,5.0,2026-12-20,4.0,https://example.org/test,2026-12-21T00:00:00Z"])
    K.install_overlay(p)
    after = K.forecasts("2027-01-01")
    assert after["newestSws"]["quarter"] == "2026-Q4" and after["newestSws"]["value"] == 5.0
    assert after["PERS"] < base["PERS"] and after["KAL"] < base["KAL"]


def test_overlay_duplicate_of_project_round_is_ignored(tmp_path, empty_overlay):
    p = overlay_with(tmp_path, ["BL,2026-Q3,23.6,2026-10-14,4.0,https://example.org/dup,2026-10-29T00:00:00Z"])
    assert K.install_overlay(p) == 0


def test_overlay_requires_publication_date(tmp_path):
    p = overlay_with(tmp_path, ["BL,2026-Q4,15.0,,4.0,https://example.org/test,2026-10-29T00:00:00Z"])
    with pytest.raises(ValueError):
        K.read_overlay(p)


# ---------------------------------------------------------------------------------------------- missing data, reproducibility
def test_forecasts_are_finite_with_gaps(empty_overlay):
    # 2022-Q1 has no BL round and 2025-Q1 has no NCR/VIS/MIN round in the project series
    for iss in ("2022-07-01", "2025-07-01", "2027-01-01"):
        f = K.forecasts(iss)
        for m in ("PERS", "KAL"):
            assert f[m] is not None and 0 < f[m] < 1 and math.isfinite(f[m])


def test_reproducible(empty_overlay):
    a = K.forecasts("2027-01-01")
    for fn in (R.known, K.HM._series, K.HM._kfit):
        fn.cache_clear()
    b = K.forecasts("2027-01-01")
    assert a == b


def test_historical_parity_with_y15(empty_overlay):
    d = pd.read_csv(K.RES / "y15_food_insecurity_improvement" / "out" / "dev_rows.csv")
    d = d[d["KAL"].notna()].iloc[[0, 20, 40, 60, -1]]
    for t, h1, kal in zip(d["t"], d["H1"], d["KAL"]):
        f = K.forecasts(str(R.issue(int(t)).date()))
        assert abs(f["PERS"] - h1) < 1e-4 and abs(f["KAL"] - kal) < 1e-4


# ---------------------------------------------------------------------------------------------- sealing
def test_seal_fields_hash_and_no_overwrite(tmp_path, empty_overlay):
    now = dt.datetime(2027, 1, 1, 3, 0, tzinfo=UTC)
    f = K.issue_seal("2027-01-01", tmp_path / "pros", empty_overlay, now_utc=now)
    s = json.loads(f.read_text(encoding="utf-8"))
    for k in ("planSha256", "issueDate", "origin", "target", "writtenUtc", "writtenManila", "window", "validProspective",
              "newestSwsUsed", "forecasts", "classAt050", "modelVersion", "gitHead", "inputs", "auxiliaryBaselines"):
        assert k in s
    assert s["target"] == "2027-Q2" and s["validProspective"] is True
    assert s["planSha256"] == (K.Y16 / "PLAN_SHA256.txt").read_text().split()[0]
    assert all(v for v in s["inputs"].values())
    reg = (tmp_path / "pros" / "SEALS.txt").read_text().split()
    assert reg[0] == f.name and reg[1] == K.sha(f)
    with pytest.raises(K.ReissueError):                  # a second valid seal for the same issue date is refused
        K.issue_seal("2027-01-01", tmp_path / "pros", empty_overlay, now_utc=now)
    K.issue_seal("2027-01-01", tmp_path / "dry", empty_overlay, now_utc=now, dry_run=True)
    with pytest.raises(FileExistsError):                 # exclusive create: an existing seal file is never overwritten
        K.issue_seal("2027-01-01", tmp_path / "dry", empty_overlay, now_utc=now, dry_run=True)
    assert len(K.load_seals(tmp_path / "pros", allow_clock_override=True)) == 1


def test_refuses_outside_window_and_dry_run_is_not_valid(tmp_path, empty_overlay):
    with pytest.raises(RuntimeError):
        K.issue_seal("2027-01-01", tmp_path / "p", empty_overlay, now_utc=dt.datetime(2026, 10, 29, tzinfo=UTC))
    with pytest.raises(RuntimeError):
        K.issue_seal("2026-10-01", tmp_path / "p", empty_overlay, now_utc=dt.datetime(2026, 10, 29, tzinfo=UTC))
    f = K.issue_seal("2026-10-01", tmp_path / "dry", empty_overlay, now_utc=dt.datetime(2026, 10, 29, tzinfo=UTC), dry_run=True)
    assert json.loads(f.read_text())["validProspective"] is False
    assert K.load_seals(tmp_path / "dry").empty                     # dry runs never enter the evaluation
    assert not (tmp_path / "p").exists() or not list((tmp_path / "p").glob("seal_*.json"))


def test_tampered_seal_is_detected(tmp_path, empty_overlay):
    f = K.issue_seal("2027-01-01", tmp_path / "pros", empty_overlay, now_utc=dt.datetime(2027, 1, 1, 3, tzinfo=UTC))
    s = json.loads(f.read_text())
    s["forecasts"]["KAL"]["probability"] = 0.01
    f.write_text(json.dumps(s, indent=1))
    with pytest.raises(K.IntegrityError):
        K.load_seals(tmp_path / "pros")


# ---------------------------------------------------------------------------------------------- evaluation arithmetic
def test_paired_and_metrics_on_synthetic_data():
    d = pd.DataFrame({"y": [1, 1, 0, 1, 0, 1], "PERS": [.6, .7, .6, .8, .4, .3], "KAL": [.7, .8, .4, .9, .3, .4],
                      "target": ["2027-Q2", "2027-Q3", "2027-Q4", "2028-Q1", "2028-Q2", "2028-Q3"]})
    p = K.paired(d)
    di = (d["KAL"] - d["y"]) ** 2 - (d["PERS"] - d["y"]) ** 2
    assert abs(p["meanDiff_KAL_minus_PERS"] - di.mean()) < 1e-12
    assert p["signTest"]["KAL_better"] == int((di < 0).sum()) == 6
    assert abs(p["signTest"]["p_one_sided"] - 0.5 ** 6) < 1e-12
    m = K.metrics(d["y"], d["KAL"])
    assert (m["TP"], m["FP"], m["FN"], m["TN"]) == (3, 0, 1, 2)


def test_outcome_is_unresolved_before_120_days():
    assert K.outcome("2026-Q3", dt.date(2026, 10, 29)) is None                   # quarter ended 2026-09-30
    v = K.outcome("2026-Q2", dt.date(2026, 11, 1))
    assert v is not None and abs(v - 17.3) < 1e-9


def test_evaluation_stages_on_historical_pseudo_seals(tmp_path, empty_overlay):
    """Pipeline test only: pseudo-seals for 2021-2024 issue dates written 'on' their issue dates into tmp_path.
    Checks staging, pairing and the presence of every reported item; no metric is asserted or reported."""
    import evaluate as EV
    pdir = tmp_path / "pseudo"
    for y in range(2021, 2025):
        for m in (1, 4, 7, 10):
            iss = f"{y}-{m:02d}-01"
            K.issue_seal(iss, pdir, empty_overlay, now_utc=dt.datetime(y, m, 1, 3, tzinfo=UTC))
    res = EV.evaluate(pdir, empty_overlay, dt.date(2026, 10, 29), allow_clock_override=True)
    assert res["validSeals"] == 16
    assert res["stage"].startswith("descriptive") or res["stage"].startswith("integrity")
    for y in range(2025, 2027):
        for m in (1, 4, 7, 10):
            iss = f"{y}-{m:02d}-01"
            K.issue_seal(iss, pdir, empty_overlay, now_utc=dt.datetime(y, m, 1, 3, tzinfo=UTC))
    res = EV.evaluate(pdir, empty_overlay, dt.date(2026, 10, 29), allow_clock_override=True)
    assert res["stage"].startswith("PRIMARY") and len(res["targets"]) == 20
    assert set(res["sevenRules"]) == {"PERS", "KAL"} and "paired" in res and "superiority" in res
    assert "sensitivity_blockBootstrap" in res and "calibration_supplementary" in res
    assert res["sevenRules"]["PERS"]["rules"]["R5"]["pass"] is None
