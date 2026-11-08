"""
tests/unit/test_e134_information.py
-----------------------------------
E134 (information bottleneck directive): frozen protocol and write-once seal, exact E133 reproduction and untouched
earlier seals, 2021+ raw data, point-in-time availability of the new area drivers, the region -> area crosswalk, area
drivers moving only the area level, the frozen selection rule and its reported outcome, the 15 deliverables, and the
primary-only scorer.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2].parent
EXP = REPO / "aipheed-backend-aligned" / "experiments"
E = EXP / "E134_Information_Bottleneck"
pytestmark = pytest.mark.skipif(not (E / "out" / "e134_metrics.csv").exists(), reason="E134 outputs not built")
DELIVERABLES = ["E134_FINAL_RESEARCH_PACKAGE.md", "E134_DATA_SOURCE_INVENTORY.csv", "E134_DATA_ACQUISITION_LOG.md",
                "E134_TARGET_MEASUREMENT_AUDIT.md", "E134_GEOGRAPHIC_ALIGNMENT_AUDIT.md", "E134_EVENT_ANALYSIS.md",
                "E134_FEATURE_CONTRIBUTION_REPORT.csv", "E134_MODEL_COMPARISON.csv", "E134_WALK_FORWARD_RESULTS.csv",
                "E134_LEAD_RELIABILITY_REPORT.md", "E134_GENERALIZATION_BIAS_OVERFITTING_REPORT.md",
                "E134_LEAKAGE_AND_CALIBRATION_AUDIT.md", "E134_PROVINCIAL_ESTIMATION_REPORT.md",
                "E134_PROSPECTIVE_VALIDATION_PROTOCOL.md", "E134_REPRODUCIBILITY_MANIFEST.md"]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load(name: str):
    sys.path.insert(0, str(E / "runner"))
    spec = importlib.util.spec_from_file_location(name, E / "runner" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_protocol_seal_deliverables_and_earlier_seals():
    assert (E / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0] == _sha(E / "E134_FROZEN_PROTOCOL.md")
    h, name = (E / "sealed" / "E134_SEAL_SHA256.txt").read_text().split()
    assert _sha(E / "sealed" / name) == h
    r = subprocess.run([sys.executable, "-I", "-B", str(E / "runner" / "e134_seal.py")], capture_output=True, text=True)
    assert r.returncode != 0 and "refusing to overwrite" in (r.stdout + r.stderr)
    for d in DELIVERABLES:
        assert (E / d).exists(), d
    rec = json.loads((E / "out" / "e134_baseline_record.json").read_text())
    assert rec["max_abs_forecast_diff"] == 0.0 and rec["rows_matched"] == rec["rows_old"]
    for f, sha in rec["seal_sha256"].items():
        folder = {"E131": "E131_Objectives_Resolution", "E132": "E132_Final_Methodology", "E133": "E133_Forecasting_Breakthrough"}[f[:4]]
        assert _sha(EXP / folder / "sealed" / f) == sha
    assert "**B. A viable path is not yet demonstrated.**" in (E / "E134_FINAL_RESEARCH_PACKAGE.md").read_text(encoding="utf-8")


def test_raw_data_window_and_crosswalk():
    R = _load("e134_run")
    log = json.loads((E / "data" / "acquisition_log.json").read_text())
    for k, v in log.items():
        if k.startswith("nasa_power"):
            assert "start=20210101" in v["url"]
            j = json.loads((E / "data" / "raw" / f"{k}.json").read_text())
            assert min(j["properties"]["parameter"]["PRECTOTCORR"]) >= "20210101"
        else:
            assert _sha(E / "data" / "raw" / f"{k}.csv") == v["sha256"]
    regions = sum(R.REGION_AREA.values(), [])
    assert len(regions) == len(set(regions)) == 18
    assert set(R.REGION_AREA) == set(R.X.AREAS)
    assert all(r in R.PALAY_KEYS for r in regions if r != "NCR")


def test_area_drivers_point_in_time():
    R = _load("e134_run")
    a = R.AreaDrivers()
    assert (a.palay["qi"] >= R.L.qi("2022-Q1")).all()
    for issue in (date(2023, 10, 1), date(2025, 1, 1), date(2026, 11, 1)):
        vals, last = a.at(issue)
        ok_r = set(a.rain.loc[a.rain["available"] <= issue, "qi"])
        ok_p = set(a.palay.loc[a.palay["available"] <= issue, "qi"])
        assert set(vals["aR"]) <= ok_r and set(vals["aP"]) <= ok_p
    _, last = a.at(date(2026, 11, 1))
    assert R.L.qs(last["aP"]) == "2026-Q2"          # 2026-Q3 palay is not available until 75 days after the quarter


def test_area_driver_moves_only_area_levels():
    R = _load("e134_run")
    M = R.M
    fit = M.Fit(q_c=1, q_d=1, rho=0.5, b=0, beta={"aR": 2.0})
    z = np.array([1.0, -1.0, 3.0, 1.0])
    u = R._exog134(fit, {"aR": z}, np.zeros(4))
    level = u[M.IC] + u[M.ID]
    assert np.allclose(level, 2.0 * z) and np.allclose(u[M.IA], 0) and u[M.IG] == 0


def test_selection_and_reported_outcome():
    s = json.loads((E / "out" / "e134_summary.json").read_text())
    Mt = pd.read_csv(E / "out" / "e134_metrics.csv")
    g = Mt[(Mt.set == "S-U") & (Mt.policy == "P-DASH") & (Mt.lead == 2)
           & Mt.model.isin(["E134-AREA-T", "E134-AREA-O", "E134-ENS", "HFM-X", "SEAS-LLM"])]
    best = g.sort_values(["within_tolerance", "mae"], ascending=[False, True]).iloc[0]
    assert s["selection"]["candidate"] == best["model"] == "HFM-X" and best["n"] == 40
    assert s["maximum_reliable_lead"] is None and s["any_rule_set_passed"] == [] and not s["any_model_any_lead_75"]
    assert s["gap_to_75_lead2_rows"] == {"within": 0.5, "rows": 40, "rows_within": 20, "rows_needed_for_75": 30,
                                         "additional_rows_needed": 10}
    F = pd.read_csv(E / "E134_FEATURE_CONTRIBUTION_REPORT.csv")
    assert not F.loc[F.lead == 2, "demonstrated_E133_criterion"].any()


def test_primary_only_scorer(tmp_path):
    sc = _load("score_e134")
    seal = pd.read_csv(E / "sealed" / "E134_PROSPECTIVE_SEAL.csv")
    rounds = tmp_path / "r.csv"
    pd.DataFrame([{"quarter": "2026-Q4", "fieldwork": "2026-12-01/2026-12-05", "published": "2027-01-20",
                   "respondent_base": "adults", "commissioned": False, "national": 22.0, "metro_manila": 25.0,
                   "balance_luzon": 22.0, "visayas": 20.0, "mindanao": 23.0, "bl_n": 600, "area_moe_bl": 4,
                   "area_moe_other": 6, "source_type": "test", "source": "test"}]).to_csv(rounds, index=False)
    S, summ = sc.score(seal, rounds)
    assert len(S) == 4 and "primary only" in summ["criterion"]
    r = S[S.area == "visayas"].iloc[0]
    f = seal[(seal.area == "visayas") & (seal.target == "2026-Q4")]["E134-ONI"].iloc[0]
    assert r["within_primary_E134-ONI"] == (abs(f - 20.0) <= r["tolerance_primary"])
