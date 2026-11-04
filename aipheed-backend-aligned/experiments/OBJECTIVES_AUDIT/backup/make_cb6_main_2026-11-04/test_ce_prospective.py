"""Tests of the C-E prospective protocol (CE_PROSPECTIVE_PLAN.md). Run: python -m pytest -q test_ce_prospective.py

They check refusals and safeguards (no real seal is ever written), leakage rules, registry reproducibility, ledger
integrity checks and that the prospective scorer reproduces the historical C-E6 family. The slow seal replay is marked
`slow` (python -m pytest -q -m slow test_ce_prospective.py).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ce_prospective as C  # noqa: E402
import ce6_model as CE6  # noqa: E402
import ce_model as CE  # noqa: E402
import score_ce_prospective as S  # noqa: E402

PY = sys.executable


def run(*args, timeout=900):
    return subprocess.run([PY, *args], cwd=HERE, capture_output=True, text=True, timeout=timeout)


def test_preregistrations_and_plan_intact():
    assert C.check_plan()
    assert C.hash_line(C.HERE / "CE2_PREREGISTRATION.md").startswith("a1b469da")
    assert C.hash_line(C.HERE / "CE6_PREREGISTRATION.md").startswith("6e07ee14")
    assert C.hash_line(C.HERE / "CB6_PREREGISTRATION.md").startswith("2efd9677")
    assert C.check_addenda()["CE_PROSPECTIVE_ADDENDUM_1.md"].startswith("3cf7930e")


def test_real_seal_refused_without_authorization():
    assert not (C.PROS_CE / "AUTHORIZATION_2027-01-01.txt").exists()
    r = run("seal_ce.py", "--issue", "2027-01-01", "--seal")
    assert r.returncode != 0 and "not authorized" in r.stderr
    assert not C.LEDGER_CE.exists() and not (C.PROS_CE / "sealed_ce_2027-01-01.csv").exists()


def test_dry_run_never_writes_into_protected_folders():
    for bad in (C.PROS_CE, C.P.PROS):
        r = run("seal_ce.py", "--issue", "2026-10-01", "--dry-run", "--out", str(bad / "x"))
        assert r.returncode != 0 and "never writes into" in r.stderr


def test_exactly_one_mode():
    r = run("seal_ce.py", "--issue", "2027-01-01", "--dry-run", "--seal")
    assert r.returncode != 0 and "exactly one" in r.stderr


def test_rice_stock_features_use_only_months_before_issue_minus_4():
    S_ = CE6._stocks()
    for t in (CE.H.qi("2010-Q1"), CE.H.qi("2018-Q2"), CE.H.qi("2026-Q4")):
        iss = CE.H.issue(t)
        m = int(iss[:4]) * 12 + int(iss[5:7]) - 1 - CE6.LAG_MONTHS
        base = CE6.st_values(S_, t)
        X = S_.copy()
        X.loc[X.index > m, ["total", "nfa"]] = 1e9
        assert CE6.st_values(X, t) == base or all(np.isnan(base))
        X2 = S_.copy()
        X2.loc[m, "total"] *= 2                                   # the allowed month itself does change the value
        assert CE6.st_values(X2, t) != base


def test_remittance_feature_reads_only_t_minus_2_or_earlier():
    pt = CE._pt()
    t = CE.H.qi("2026-Q4")
    a = CE.e2_series(pt, [t]).iloc[0]
    p = pt.copy()
    p[p.index >= t - 1] = 1e9
    assert CE.e2_series(p, [t]).iloc[0] == a or np.isnan(a)


def test_registry_reproducible_and_three_identities():
    r = run("ce_registry.py", "verify")
    assert r.returncode == 0, r.stdout + r.stderr
    reg = json.loads(C.REGISTRY_CE.read_text(encoding="utf-8"))
    assert set(reg["models"]) == {"C-b", "C-E2", "C-E6", "C-B6"}
    assert reg["models"]["C-b"]["seal"]["matches_recorded"] is True
    assert reg["models"]["C-b"]["adoption"] == "adopted"
    assert all(reg["models"][m]["adoption"].startswith("not adopted") for m in ("C-E2", "C-E6", "C-B6"))
    assert "E1" not in reg["models"]["C-B6"]["features"] and "ST1" in reg["models"]["C-B6"]["features"]
    assert reg["prospective_seals"] == []


def test_scorer_rejects_a_tampered_sealed_file(tmp_path):
    f = tmp_path / "sealed_ce_2027-01-01.csv"
    pd.DataFrame([{"issue_date": "2027-01-01", "model": "C-E6", "lead": 1, "target_quarter": "2027-Q1", "p_high": .7,
                   "persist_si": 1.0, "clim": .7, "dry_run": False}]).to_csv(f, index=False)
    led = tmp_path / "SEAL_LEDGER_CE.md"
    C.P.append_ledger(led, {"file": f.name, "sha256": C.sha(f), "issue": "2027-01-01", "targets": "2027-Q1",
                            "sealed_at": "x", "commit": "0" * 12})
    assert len(S.collect_ce(led)) == 1
    f.write_text(f.read_text().replace("0.7", "0.9"))
    with pytest.raises(AssertionError, match="SHA-256 differs"):
        S.collect_ce(led)


def test_no_unpublished_label_is_scored():
    lab = C.P.labels_at("2027-03-01")
    assert lab[lab["q"] >= C.P.FIRST_TARGET].empty                 # no 2027 quarter has ended and been published


def test_scorer_reproduces_historical_c_e6_family():
    r = run("score_ce_prospective.py", "--replay-validate")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert '"P1_P4_match_results": true' in r.stdout


@pytest.mark.slow
def test_seal_dry_run_replays_stored_fits(tmp_path):
    r = run("seal_ce.py", "--issue", "2026-10-01", "--dry-run", "--out", str(tmp_path), timeout=1800)
    assert r.returncode == 0, r.stderr[-2000:]
    rep = json.loads(r.stdout[r.stdout.find("{"):])
    assert rep["replay"]["replay_matches"] is True
    assert not C.LEDGER_CE.exists()
