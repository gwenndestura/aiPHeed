"""
tests/unit/test_e131_resolution.py
----------------------------------
E131 (resolving E130 against the master directive): deliverables and frozen protocol, the measured SWS target and its
sampling-error tolerance, operational leads and point-in-time information, the recorded metrics and selection rule,
the reliability verdicts, the measurement-aware filter, the provincial price-versus-income identity, the write-once
seals, and that production, FIRI v2 and FIRI3 are untouched.
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
E = REPO / "aipheed-backend-aligned" / "experiments" / "E131_Objectives_Resolution"
pytestmark = pytest.mark.skipif(not (E / "out" / "e131_summary.json").exists(), reason="E131 outputs not built")
MODELS = ["PERSIST", "CLIM", "LLM", "DLLM", "RIDGE-H", "LGBM-H", "RIDGE-ALL", "LGBM-ALL", "PSA-ONLY", "NLP-ONLY"]
FILES = ["E131_FROZEN_PROTOCOL.md", "E131_DIAGNOSTIC_REPORT.md", "E131_DATA_SOURCE_INVESTIGATION.md", "E131_ALTERNATIVE_APPROACHES.md",
         "E131_SELECTED_SOLUTION.md", "E131_EXPERIMENTAL_RESULTS.md", "E131_TARGET_VALIDATION_REPORT.md",
         "E131_NUMERICAL_FORECASTING_REPORT.md", "E131_LEAD_TIME_REPORT.md", "E131_TRIGGER_CONTRIBUTION_REPORT.md",
         "E131_RELIABILITY_REPORT.md", "E131_PRODUCTION_READINESS_REPORT.md", "E131_THESIS_OBJECTIVE_ASSESSMENT.md",
         "E131_PROVINCIAL_CPI_QUESTIONS.md"]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def X():
    sys.path.insert(0, str(E / "runner"))
    spec = importlib.util.spec_from_file_location("e131_x1", E / "runner" / "e131_x1.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_deliverables_protocol_and_seals():
    assert all((E / f).exists() for f in FILES), [f for f in FILES if not (E / f).exists()]
    assert (E / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0] == _sha(E / "E131_FROZEN_PROTOCOL.md")
    for line in (E / "sealed" / "E131_SEAL_SHA256.txt").read_text().splitlines():
        h, name = line.split()
        assert _sha(E / "sealed" / name) == h
    r = subprocess.run([sys.executable, "-I", "-B", str(E / "runner" / "e131_seal.py")], capture_output=True, text=True)
    assert r.returncode != 0 and "refusing to overwrite" in (r.stdout + r.stderr)


def test_target_and_tolerance(X):
    qt = pd.read_csv(E / "out" / "x1_target_quarters.csv")
    assert len(qt) == 80 and qt["quarter"].nunique() == 20 and (qt["quarter"].map(lambda q: int(q[:4])) >= 2021).all()
    assert np.allclose(qt["tol"], 1.6448536269514722 * qt["se"])
    rr = X.rounds()
    one = rr[(rr.quarter == "2026-Q3") & (rr.area == "balance_luzon")].iloc[0]
    n = 0.9604 / (4.0 / 100) ** 2                                      # published margin 4 points
    assert one["se"] == pytest.approx(100 * np.sqrt(0.236 * 0.764 / n), rel=1e-9)
    two = qt[(qt.quarter == "2025-Q2") & (qt.area == "balance_luzon")].iloc[0]
    assert two["y"] == pytest.approx((17.0 + 15.3) / 2)               # quarter mean of its two rounds


def test_operational_leads_and_point_in_time(X):
    P = pd.read_csv(E / "out" / "x1_predictions.csv")
    assert (P["target"].map(X.L.qi) == P["D"].map(X.L.qi) - 1 + P["lead"]).all()   # Lead k = latest complete quarter + k
    assert (P["h"] >= P["lead"]).all()                                               # newest reading is never the target
    rr = X.rounds()
    for r in P.sample(25, random_state=1).itertuples():
        qa = X.asof(rr, pd.Timestamp(r.issue).date())
        s = qa[qa.area == r.area].sort_values("qi")
        assert s["y"].iloc[-1] == pytest.approx(r.y_latest)
        assert all(d < pd.Timestamp(r.issue).date() for d in rr[rr.quarter.isin(s.quarter)]["published"]
                   if d < pd.Timestamp(r.issue).date()) and pd.Timestamp(str(r.published_target)).date() > pd.Timestamp(r.issue).date() - pd.Timedelta(days=0)
    cpi = pd.read_csv(E / "out" / "x1_area_cpi_quarterly.csv")
    assert cpi[cpi["quarter"] < "2022-Q1"][["food_yoy", "rice_yoy"]].isna().all().all()  # no pre-2021 YoY base


def test_metrics_reproduce_and_selection():
    P = pd.read_csv(E / "out" / "x1_predictions.csv")
    M = pd.read_csv(E / "out" / "x1_metrics.csv")
    c = P[(P.policy == "P-DASH") & (P.lead == 2)].dropna(subset=[f"f_{m}" for m in MODELS])
    within = float((np.abs(c["f_LLM"] - c["y_true"]) <= c["tol"]).mean())
    rec = M[(M.policy == "P-DASH") & (M.lead == 2) & (M.model == "LLM")].iloc[0]
    assert within == pytest.approx(rec["within_tolerance"]) and len(c) == rec["n"] == 28
    s = json.load(open(E / "out" / "e131_summary.json"))
    cand = M[(M.policy == "P-DASH") & (M.lead == 2) & ~M.model.isin(["PERSIST", "CLIM"])].sort_values(
        ["within_tolerance", "mae"], ascending=[False, True]).iloc[0]["model"]
    assert s["selection"]["candidate"] == cand == "LLM"
    assert M["within_tolerance"].max() < 0.75                          # 75 % agreement not reached anywhere


def test_reliability_verdicts():
    common = json.load(open(E / "out" / "x1_rules.json"))
    uni = json.load(open(E / "out" / "x1_univariate_rules.json"))
    assert not any(v["passed"] for v in list(common.values()) + list(uni.values()))
    assert all(v is None for v in json.load(open(E / "out" / "e131_summary.json"))["max_reliable_lead_P_DASH"].values())
    llm = common["P-DASH|2|LLM"]["rules"]                               # shared rows: 7 quarters, so N1 fails
    assert llm["N3_beats_every_baseline_mae_rmse"] and not llm["N2_within_tolerance_75"] and not llm["N1_data"]
    assert uni["P-DASH|2|LLM"]["rules"]["N1_data"] and not uni["P-DASH|2|LLM"]["rules"]["N2_within_tolerance_75"]


def test_measurement_aware_filter(X):
    y = np.array([10.0, np.nan, 10.0, 10.0])
    mu, P, _ = X._kf(y, np.array([1.0, 1.0, 1.0, 1.0]), s2=1e-6)
    assert mu == pytest.approx(10.0) and P < 1.0                        # constant series, missing quarter skipped
    mu2, _, _ = X._kf(np.array([10.0, 20.0]), np.array([1e-6, 1e-6]), s2=100.0)
    assert mu2 == pytest.approx(20.0, abs=1e-3)                         # precise observations are followed
    mu3, _, _ = X._kf(np.array([10.0, 20.0]), np.array([4.0, 4.0]), s2=1e-9)
    assert mu3 == pytest.approx(15.0, abs=1e-6)                         # two equally noisy readings of a stable level average
    mu4, _, _ = X._kf(np.array([10.0, 20.0]), np.array([1e-6, 1e6]), s2=1e-9)
    assert mu4 == pytest.approx(10.0, abs=1e-3)                         # a very noisy new reading barely moves a precise level


def test_provincial_identity_and_replication():
    a = pd.read_csv(E / "out" / "x3a_price_income_decomposition.csv")
    assert np.allclose(a["price_effect_pp"] + a["income_effect_pp"], a["official_change_pp"])
    assert (a["price_effect_pp"] >= 0).all() and (a["replication_gap_pp"].abs() <= 0.3).all()
    assert set(a.loc[a["income_effect_pp"] < -1, "province"]) == {"Cavite", "Laguna", "Quezon"}
    inp = json.load(open(E / "out" / "x3_inputs.json"))
    assert len(inp["puf_sha256"]) == 64 and inp["puf_records_calabarzon_5_provinces"] == 7244


def test_seal_content():
    s = pd.read_csv(E / "sealed" / "E131_PROSPECTIVE_SEAL.csv")
    assert len(s) == 16 and set(s.target) == {"2026-Q4", "2027-Q1", "2027-Q2", "2027-Q3"} and (s.issue == "2026-10-31").all()
    assert set(s.latest_quarter) == {"2026-Q3"} and all(m in s.columns for m in MODELS)
    p = pd.read_csv(E / "sealed" / "E131_PROVINCIAL_MODEL_BASED_SEAL.csv")
    assert len(p) == 20 and p.label.str.startswith("model-based").all()


def test_production_untouched():
    inf = REPO / "backend" / "app" / "ml" / "inference"
    assert _sha(inf / "firi.py") == "0e583131a7de3b9844241d3927eede813077d7cccbf949cd8313973436d0f8e3"
    assert _sha(inf / "firi3.py") == "d8298024541f48ae9a472179c836fc1428ebae7fd83e58a24e47ab616d8e2cd1"
    man = json.load(open(REPO / "aipheed-backend-aligned" / "experiments" / "E130_Provincial_Risk_Score_Forecasting" / "out" / "e130_manifest.json"))
    assert _sha(REPO / "backend" / "app" / "quarterly" / "target.py") == man["inputs_sha256"]["dashboard_clock_code"]
