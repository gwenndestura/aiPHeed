"""
tests/unit/test_e132_final.py
-----------------------------
E132 (final master directive): frozen protocol and write-once seals, reproduction of E131's persistence and LLM,
the frozen selection rule, 75 % not reached and no reliability rule set passed, the oracle and SWS-vs-OCTA
diagnostics as reported, the seasonal effect only after the documented 2025 break, 2021+ inputs, and the
primary-only scorer.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2].parent
E = REPO / "aipheed-backend-aligned" / "experiments" / "E132_Final_Methodology"
E131 = REPO / "aipheed-backend-aligned" / "experiments" / "E131_Objectives_Resolution"
pytestmark = pytest.mark.skipif(not (E / "out" / "e132_metrics.csv").exists(), reason="E132 outputs not built")
BASELINES = {"PERSIST", "CLIM"}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_protocol_seals_and_package():
    assert (E / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0] == _sha(E / "E132_FROZEN_PROTOCOL.md")
    for line in (E / "sealed" / "E132_SEAL_SHA256.txt").read_text().splitlines():
        h, name = line.split()
        assert _sha(E / "sealed" / name) == h
    r = subprocess.run([sys.executable, "-I", "-B", str(E / "runner" / "e132_seal.py")], capture_output=True, text=True)
    assert r.returncode != 0 and "refusing to overwrite" in (r.stdout + r.stderr)
    text = (E / "E132_FINAL_RESEARCH_PACKAGE.md").read_text(encoding="utf-8")
    assert all(f"## {i}." in text for i in range(1, 19))                    # all 18 required deliverables


def test_reproduces_e131_univariate_models():
    m132 = pd.read_csv(E / "out" / "e132_metrics.csv")
    m131 = pd.read_csv(E131 / "out" / "x1_metrics.csv")
    for model in ("PERSIST", "LLM", "DLLM", "CLIM"):
        a = m132[(m132.policy == "P-DASH") & (m132.lead == 2) & (m132.model == model)].iloc[0]
        b = m131[(m131.policy == "P-DASH") & (m131.lead == 2) & (m131.model == model)].iloc[0]
        assert a["within_tolerance"] == pytest.approx(b["within_tolerance"]) and a["mae"] == pytest.approx(b["mae"])


def test_selection_rule_and_verdicts():
    M = pd.read_csv(E / "out" / "e132_metrics.csv")
    lead2 = M[(M.policy == "P-DASH") & (M.lead == 2) & ~M.model.isin(BASELINES)].sort_values(
        ["within_tolerance", "mae"], ascending=[False, True])
    assert lead2.iloc[0]["model"] == "SEAS-LLM" and lead2.iloc[0]["within_tolerance"] == pytest.approx(17 / 28)
    assert M["within_tolerance"].max() < 0.75
    R = json.load(open(E / "out" / "e132_rules.json"))
    assert not any(v["passed"] for v in R.values())
    s = R["P-DASH|2|SEAS-LLM"]["rules"]
    assert s["N3_beats_every_baseline_mae_rmse"] and s["N7_interval_coverage_80"] and not s["N2_within_tolerance_75"]


def test_diagnostics_as_reported():
    U = pd.read_csv(E / "out" / "e132_univariate_and_oracle.csv").set_index(["policy", "lead", "model"])
    assert U.loc[("P-DASH", 2, "ORACLE-NOW"), "within"] == pytest.approx(0.35)
    assert U.loc[("P-DASH", 2, "ORACLE-LEVEL"), "within"] > 0.9 > U.loc[("P-DASH", 2, "ORACLE-NOW"), "within"]
    d = json.load(open(E / "out" / "d2_sws_vs_octa.json"))
    assert d["matched_quarters"] == 7 and d["share_within_sws_primary_tolerance"] == pytest.approx(2 / 7)


def test_seasonal_effect_only_after_documented_break():
    P = pd.read_csv(E / "out" / "e132_predictions.csv")
    pre = P[P["target"].map(lambda q: int(q[:4]) * 4 + int(q[-1]) - 1) < 2025 * 4 + 1]
    assert (pre["seas_effect"] == 0).all()


def test_inputs_are_2021_onward():
    for f in ("psa_sdg_daily_basic_pay_region.csv", "psa_sdg_unemployment_region.csv"):
        cols = pd.read_csv(E / "data" / "raw" / f, nrows=0, encoding="utf-8-sig").columns
        assert all(int(c[:4]) >= 2021 for c in cols if c[:4].isdigit())


def test_scorer_primary_only(tmp_path):
    sys.path.insert(0, str(E / "runner"))
    spec = importlib.util.spec_from_file_location("score_e132", E / "runner" / "score_e132.py")
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    assert _sha(S.SEAL) == S.SEAL_SHA
    hdr = pd.read_csv(S.X.SWS, nrows=0).columns
    row = {c: "" for c in hdr}
    row.update(quarter="2026-Q4", published="2027-01-15", commissioned=False, metro_manila=25.0, balance_luzon=21.0,
               visayas=18.0, mindanao=24.0, area_moe_bl=4.0, area_moe_other=6.0)
    pd.DataFrame([row]).to_csv(tmp_path / "rounds.csv", index=False)
    D, summ = S.score(pd.read_csv(S.SEAL), tmp_path / "rounds.csv")
    assert len(D) == 4 and np.allclose(D["tolerance_primary"], 1.6448536269514722 * D["se"])
    assert summ["criterion"].startswith("primary only") and not [c for c in D.columns if "secondary" in c]
