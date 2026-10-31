"""
tests/unit/test_e130_provincial.py
----------------------------------
E130 provincial risk-score forecasting (outcome BLOCKED): deliverables, the PFDR reference construction, geographic
separation and no SWS copies, the operational lead mapping against the served dashboard clock, no future or target
leakage, walk-forward splits, numerical agreement and the N1-N7 rules on synthetic data, the sealed survey-year
forecasts, reproducibility, and that E128, E129, FIRI v2, FIRI3 and production are untouched.
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
E = REPO / "aipheed-backend-aligned" / "experiments" / "E130_Provincial_Risk_Score_Forecasting"
E128 = REPO / "aipheed-backend-aligned" / "experiments" / "E128_Food_Insecurity_ML_Development"
pytestmark = pytest.mark.skipif(not (E / "out" / "gate.json").exists(), reason="E130 outputs not built")

DELIVERABLES = [
    "E130_DATA_INVENTORY.csv", "E130_PROVINCIAL_TARGET_VALIDITY_AUDIT.md", "E130_REFERENCE_RISK_SCORE_METHODOLOGY.md",
    "E130_REFERENCE_SCORE_DATA.csv", "E130_TARGET_UNCERTAINTY_AUDIT.md", "E130_PROVINCIAL_FEATURE_AVAILABILITY.csv",
    "E130_ISSUE_DATE_AND_OPERATIONAL_LEAD_MAPPING.csv", "E130_FROZEN_EXPERIMENT_PROTOCOL.md", "E130_R1_R7_RELIABILITY_AUDIT.md",
    "E130_WALK_FORWARD_SPLITS.csv", "E130_MODEL_TRAINING_RESULTS.csv", "E130_NUMERICAL_RISK_SCORE_PREDICTIONS.csv",
    "E130_LEAD_1_TO_4_NUMERICAL_COMPARISON.csv", "E130_BASELINE_COMPARISON.csv", "E130_SCORE_AGREEMENT_ANALYSIS.md",
    "E130_OVERFITTING_ANALYSIS.md", "E130_PROVINCIAL_BIAS_AND_GENERALIZATION.md", "E130_FEATURE_GROUP_ABLATION.csv",
    "E130_CALIBRATION_AND_UNCERTAINTY.md", "E130_MAXIMUM_RELIABLE_LEAD_TIME_REPORT.md", "E130_RELIABLE_HORIZON_COMPARISON.csv",
    "E130_FIRST_UNRELIABLE_LEAD_ANALYSIS.md", "E130_SHAP_EXPLANATIONS.md", "E130_MODEL_COMPARISON.md",
    "E130_RELIABILITY_DECISION.md", "E130_FINAL_RECOMMENDATION.md"]
SEAL_SHA = "94a08cd1d4b4497effbf95340f091eca46d2cc087d562a37ed134eb1b38593ed"


@pytest.fixture(scope="module")
def L():
    sys.path.insert(0, str(E / "runner"))
    spec = importlib.util.spec_from_file_location("e130_lib", E / "runner" / "e130_lib.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------ deliverables, decision, integrity
def test_deliverables_and_blocked_decision():
    assert all((E / f).exists() for f in DELIVERABLES), [f for f in DELIVERABLES if not (E / f).exists()]
    assert "**BLOCKED**" in (E / "E130_RELIABILITY_DECISION.md").read_text(encoding="utf-8")
    g = json.load(open(E / "out" / "gate.json"))
    assert g["any_candidate_passes"] is False and g["pfdr_valid_survey_year_reference"] is True
    assert json.load(open(E / "out" / "gate_recheck.json"))["decision_unchanged"] is True


def test_protocol_and_seal_frozen():
    assert (E / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0] == _sha(E / "E130_FROZEN_EXPERIMENT_PROTOCOL.md")
    assert _sha(E / "sealed" / "E130_SURVEY_YEAR_SEAL.csv") == SEAL_SHA
    assert SEAL_SHA in (E / "E130_FROZEN_EXPERIMENT_PROTOCOL.md").read_text(encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", "-B", str(E / "runner" / "seal_e130.py")], capture_output=True, text=True)
    assert r.returncode != 0 and "refusing to overwrite" in (r.stderr + r.stdout)
    assert _sha(E / "sealed" / "E130_SURVEY_YEAR_SEAL.csv") == SEAL_SHA


def test_no_model_artifacts_and_nothing_trained():
    assert not [p for p in E.rglob("*") if p.suffix in (".pkl", ".joblib", ".lgb", ".onnx")]
    tr = pd.read_csv(E / "E130_MODEL_TRAINING_RESULTS.csv")
    assert (~tr["trained"]).all()
    assert (pd.read_csv(E / "E130_LEAD_1_TO_4_NUMERICAL_COMPARISON.csv")["valid_evaluation_origins"] == 0).all()


def test_e128_e129_firi_and_production_untouched():
    assert _sha(E128 / "E128_FROZEN_EXPERIMENT_PROTOCOL.md") == "c7a92670d65da9ddf04233739341f6765b719cf8338be2642bda2a9f3e8618f3"
    inf = REPO / "backend" / "app" / "ml" / "inference"
    assert _sha(inf / "firi.py") == "0e583131a7de3b9844241d3927eede813077d7cccbf949cd8313973436d0f8e3"
    assert _sha(inf / "firi3.py") == "d8298024541f48ae9a472179c836fc1428ebae7fd83e58a24e47ab616d8e2cd1"
    man = json.load(open(E / "out" / "e130_manifest.json"))
    assert man["starting_commit"].startswith("99358f0")
    for k in ("e128_protocol", "e129_decision", "firi_v2_code", "firi3_code", "dashboard_clock_code"):
        assert len(man["inputs_sha256"][k]) == 64


# ------------------------------------------------------------------ the reference score
def test_reference_construction_scale_and_window(L):
    r = L.load_reference()
    assert len(r) == 10 and set(r.province) == set(L.PROVINCES) and set(r.survey_year) == {2021, 2023}
    assert ((r.pfdr_pct >= 0) & (r.pfdr_pct <= 100)).all()
    assert np.allclose(r.se_pp, r.pfdr_pct * r.cv_pct / 100)
    assert np.allclose(r.tolerance_pp, 1.6448536269514722 * r.se_pp)
    assert (r.ci90_lo >= 0).all() and (r.ci90_lo <= r.pfdr_pct).all() and (r.pfdr_pct <= r.ci90_hi).all()
    q = r.set_index(["province", "survey_year"])["pfdr_pct"]
    assert q[("Quezon", 2021)] == 6.6 and q[("Rizal", 2023)] == 2.6


def test_no_duplicates_and_no_sws_copies(L):
    d = pd.read_csv(E / "E130_REFERENCE_SCORE_DATA.csv")
    prov = d[d.reference_id.str.startswith("PFDR-")]
    assert len(prov) == 10 and not prov.duplicated(["province", "period"]).any()
    assert prov.source.str.startswith("PSA").all() and prov.province.notna().all()
    sws = d[d.reference_id.str.startswith("SWS-")]
    assert sws.province.isna().all() and sws.geography.str.contains("regional").all()
    assert sws.used_as.str.contains("never copied").all()
    quarter_means = pd.read_csv(L.SWS).groupby("quarter")["balance_luzon"].mean().round(4)
    assert not set(prov.value.round(4)) & set(quarter_means)          # no provincial value is an SWS value
    assert (pd.read_csv(L.SWS)["quarter"].map(L.qi) >= L.qi("2021-Q1")).all()


def test_change_tests_and_rank_stability(L):
    ch = L.change_tests(L.load_reference()).set_index("province")
    assert ch.loc["Quezon", "z"] == pytest.approx(-4.741, abs=1e-3) and ch.loc["Rizal", "z"] == pytest.approx(2.398, abs=1e-3)
    assert int(ch.exceeds_sampling_error_90.sum()) == 3 and int(ch.exceeds_sampling_error_95.sum()) == 2
    ru = json.load(open(E / "out" / "reference_uncertainty.json"))
    r = L.load_reference()
    a = r[r.survey_year == 2021].set_index("province").loc[list(L.PROVINCES)]
    b = r[r.survey_year == 2023].set_index("province").loc[list(L.PROVINCES)]
    assert L.rank_stability_p(a.pfdr_pct, a.se_pp, b.pfdr_pct, b.se_pp) == pytest.approx(ru["rank_stability_p_if_no_true_change"])
    same = L.rank_stability_p([1, 2, 3, 4, 5], [.01] * 5, [1, 2, 3, 4, 5], [.01] * 5)
    assert same == 1.0                                               # identical precise orderings are never "unstable"


# ------------------------------------------------------------------ issue dates and operational leads
def test_mapping_matches_served_dashboard_clock(L):
    sys.path.insert(0, str(REPO / "backend"))
    from app.quarterly.target import forecast_target
    mp = pd.read_csv(E / "E130_ISSUE_DATE_AND_OPERATIONAL_LEAD_MAPPING.csv")
    assert len(mp) == 23 * 5 * 4 and set(mp.province) == set(L.PROVINCES)
    for dq, g in mp.groupby("dashboard_quarter"):
        mid = L.qstart(dq).replace(day=15).isoformat() + "T12:00:00"
        ft = forecast_target(mid)
        assert ft["calendar_quarter"] == dq and ft["origin"] == g.issue_date.iloc[0]
        assert set(g[g.operational_lead == 2].target_quarter) == {ft["target_quarter"]}    # Lead 2 = dashboard target
        assert set(g[g.operational_lead == 1].target_quarter) == {dq}                       # Lead 1 = current quarter
        assert set(g[g.operational_lead == 1].latest_complete_calendar_quarter) == {ft["latest_complete_data_quarter"]}
    assert mp[mp.operational_lead >= 2].meets_minimum_operational_horizon.all()
    assert not mp[mp.operational_lead == 1].meets_minimum_operational_horizon.any()


def test_mapping_reproduces_e128_and_resolves_horizon():
    s = json.load(open(E / "out" / "mapping_summary.json"))
    assert s["e128_cross_check"] == {"rows_compared": 92, "target_quarters_identical": True, "sws_horizons_identical": True}
    assert s["sws_horizon_quarter_start"]["2"] == {"2": 2, "3": 19}
    assert all(v == {k: 20} for k, v in ((k, s["sws_horizon_release_anchored"][k]) for k in "1234"))


def test_no_future_leakage_in_mapping(L):
    mp = pd.read_csv(E / "E130_ISSUE_DATE_AND_OPERATIONAL_LEAD_MAPPING.csv")
    for r in mp.drop_duplicates(["dashboard_quarter", "province"]).itertuples():
        issue = date.fromisoformat(r.issue_date)
        y, m = map(int, r.latest_cpi_month.split("-"))
        assert date(y + (m == 12), m % 12 + 1, 1) <= date(issue.year, issue.month, 1) or (y, m) < (issue.year, issue.month)
        if isinstance(r.sws_newest_published, str):
            assert date.fromisoformat(r.sws_newest_published) < issue
        if pd.notna(r.pfdr_newest_survey_year_at_issue_held_vintage):
            assert issue > date(2024, 8, 15)                                # both held rounds published 2024-08-15
        for col in ("latest_news_quarter", "latest_rainfall_quarter", "latest_typhoon_quarter", "latest_production_quarter"):
            v = getattr(r, col)
            if isinstance(v, str) and v:
                assert L.qend(v) < issue
    assert not mp.target_quarter_has_provincial_reference.any() and not mp.evaluable_provincial_target.any()


def test_no_target_leakage_in_seal(L):
    s = pd.read_csv(E / "sealed" / "E130_SURVEY_YEAR_SEAL.csv")
    assert s.information_set.str.contains("2021 and 2023").all() and not s.information_set.str.contains("2025").any()
    assert (pd.to_datetime(s.sealed_utc) < pd.Timestamp("2026-11-01", tz="UTC")).all()


# ------------------------------------------------------------------ features
def test_provincial_feature_alignment_and_missing(L):
    fa = pd.read_csv(E / "E130_PROVINCIAL_FEATURE_AVAILABILITY.csv").set_index("feature")
    panel = pd.read_csv(L.PANEL)
    assert len(panel) == 115 and panel.groupby("province").size().eq(23).all()
    for f in ("cpi_food_yoy_pct", "N1_fssi_v3", "typhoons_local_100km"):
        assert fa.loc[f, "missing_pct"] == pytest.approx(round(100 * panel[f].isna().mean(), 1))
    assert fa.loc["cpi_food_yoy_pct", "share_common_quarter_effect"] == pytest.approx(0.747, abs=1e-3)
    for f in ("E2_remittance_decline_pct", "oni_quarter_mean", "typhoons_PAR", "H1_bl_latest (SWS Balance Luzon hunger)"):
        assert fa.loc[f, "identical_across_provinces_share"] == 1.0
    groups = set(fa.trigger_group.str[:1])
    assert {"1", "2", "3", "4", "5"} <= groups


# ------------------------------------------------------------------ splits, agreement, rules
def test_walk_forward_splits(L):
    pub = {"2021-Q2": date(2021, 7, 28), "2021-Q3": date(2021, 12, 6), "2021-Q4": date(2022, 3, 25), "2022-Q1": None,
           "2022-Q2": date(2022, 9, 10)}
    s = L.walk_forward_splits(pub, 1, ["2021-Q3", "2021-Q4", "2022-Q1"], min_train_targets=1).set_index("origin")
    assert s.loc["2021-Q3", "issue_date"] == "2021-10-01" and s.loc["2021-Q3", "target_quarter"] == "2021-Q4"
    assert s.loc["2021-Q3", "n_train_targets"] == 1                      # only 2021-Q2 published before 2021-10-01
    assert s.loc["2021-Q4", "n_train_targets"] == 2 and s.loc["2021-Q4", "train_last_target"] == "2021-Q3"
    assert not s.loc["2021-Q4", "executable"]                           # target 2022-Q1 has no reference
    assert s.loc["2022-Q1", "executable"]
    wf = pd.read_csv(E / "E130_WALK_FORWARD_SPLITS.csv")
    q = wf[wf.design.str.startswith("quarterly")]
    assert len(q) == 23 * 4 and (q.n_train_targets == 0).all() and (~q.executable.astype(bool)).all()


def test_numerical_agreement_math(L):
    assert L.required_forecast_sd_over_se(0.75) == pytest.approx(1.0220, abs=1e-4)
    assert float(L.expected_within_share(0.0)) == pytest.approx(0.90, abs=1e-9)
    assert float(L.expected_within_share(L.required_forecast_sd_over_se(0.75))) == pytest.approx(0.75, abs=1e-9)
    assert list(L.within_tolerance([1.0, 1.5], [1.2, 1.2], [0.1, 0.1])) == [False, False]
    assert list(L.within_tolerance([1.1, 1.36], [1.2, 1.2], [0.1, 0.1])) == [True, True]
    m = L.numeric_metrics([1, 2, 3], [1, 2, 4], se=[1, 1, 1], prev=[1, 1, 1])
    assert m["mae"] == pytest.approx(1 / 3) and m["within_tolerance"] == 1.0 and m["direction_accuracy"] == 1.0


def _synthetic(n_q=12, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for t in range(n_q):
        for p in range(5):
            y = 5 + p + np.sin(t) * 2
            rows.append({"target_q": t, "province": f"P{p}", "y": y, "se": 0.5, "f_model": y + rng.normal(0, noise),
                         "f_persistence": 5 + p + np.sin(t - 2) * 2, "f_climatology": 5 + p, "f_other": y + 1.5,
                         "lo80_model": y - 0.4, "hi80_model": y + 0.4})
    return pd.DataFrame(rows)


def test_reliability_rules_on_synthetic_data(L):
    good = L.numeric_reliability(_synthetic(noise=0.05), "model", ["persistence", "climatology", "other"])
    assert good["rules"]["N1_data"] and good["rules"]["N2_within_tolerance_75"] and good["rules"]["N3_beats_every_baseline_mae_rmse"]
    assert good["rules"]["N4_squared_error_vs_persistence_and_climatology"] and good["n_rows"] == 60
    short = L.numeric_reliability(_synthetic(n_q=6, noise=0.05), "model", ["persistence", "climatology"])
    assert not short["rules"]["N1_data"] and not short["passed"]
    d = _synthetic(noise=0.05)
    d["f_model"] = d["f_persistence"]                                   # a copy of persistence cannot beat it
    same = L.numeric_reliability(d, "model", ["persistence", "climatology"])
    assert not same["rules"]["N3_beats_every_baseline_mae_rmse"] and not same["passed"]
    assert all(b in good["baselines"] for b in ("persistence", "climatology", "other"))     # identical rows for all
    assert good["baselines"]["other"]["n"] == good["metrics"]["n"]


def test_maximum_reliable_lead_is_consecutive(L):
    assert L.maximum_reliable_lead({1: True, 2: True, 3: False, 4: True}) == 2
    assert L.maximum_reliable_lead({1: False, 2: True}) is None
    assert L.maximum_reliable_lead({1: True}) == 1


# ------------------------------------------------------------------ uncertainty, reproducibility
def test_seal_intervals(L):
    s = pd.read_csv(E / "sealed" / "E130_SURVEY_YEAR_SEAL.csv")
    assert len(s) == 15 and not s.duplicated(["model", "province"]).any()
    assert (s.pi90_lo <= s.pred_pct).all() and (s.pred_pct <= s.pi90_hi).all() and (s.pi90_lo >= 0).all()
    half = 1.6448536269514722 * np.sqrt(s.s2_change + s.latest_se_2023 ** 2)
    assert np.allclose(s.pi90_hi - s.pred_pct, half, atol=1e-5)
    p = pd.read_csv(E / "E130_NUMERICAL_RISK_SCORE_PREDICTIONS.csv")
    assert (p.seal_sha256 == SEAL_SHA).all() and p.reference_value.isna().all()


def test_reproducibility(L):
    a = L.simulate_panel(10, 1.0, 0.9, 0.5, 2, n_sims=40, n_boot=50, seed=7)
    b = L.simulate_panel(10, 1.0, 0.9, 0.5, 2, n_sims=40, n_boot=50, seed=7)
    assert a == b
    ru = json.load(open(E / "out" / "reference_uncertainty.json"))
    ch = L.change_tests(L.load_reference())
    assert [round(x, 9) for x in ch.z] == [round(c["z"], 9) for c in ru["changes"]]
    sim = pd.read_csv(E / "out" / "planning_simulation.csv")
    assert len(sim) == 192 and sim.label.str.startswith("SYNTHETIC").all()
    assert sim[sim.n_quarters == 10].p_pass_N2_and_N4.max() < 0.8
