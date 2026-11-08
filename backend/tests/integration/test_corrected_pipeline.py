"""
tests/integration/test_corrected_pipeline.py
--------------------------------------------
Corrected experimental data pipeline (experiments/CORRECTED_PIPELINE): indicator and domain mappings; point-in-time
rules (as-of thresholds, annual employment, remittance evidence, CPI vintage flags); geography (national and regional
values never copied into the provincial profile); missing values preserved with a status; Lead alignment;
training/inference consistency of the threshold correction; regression against the original pipeline; raw inputs
unchanged.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
C = ROOT / "aipheed-backend-aligned" / "experiments" / "CORRECTED_PIPELINE"
X = ROOT / "aipheed-backend-aligned" / "experiments"
pytestmark = pytest.mark.skipif(not (C / "out" / "pipeline_manifest.json").exists(), reason="corrected pipeline outputs missing")
sys.path.insert(0, str(C / "runner"))


@pytest.fixture(scope="module")
def P():
    return pd.read_csv(C / "out" / "provincial_profile.csv", dtype={"province_code": str})


@pytest.fixture(scope="module")
def N():
    return pd.read_csv(C / "out" / "national_context.csv")


@pytest.fixture(scope="module")
def stack1():
    S = pd.read_csv(X / "LEAD2_FIVE_TRIGGER" / "data" / "stack_l2.csv", dtype={"province_code": str})
    return S[S["lead"] == 1].sort_values(["t", "province_code"]).reset_index(drop=True)


def test_indicator_and_domain_mappings():
    from app.ml.inference import firi as FI
    g = pd.read_csv(C / "out" / "indicator_registry.csv")
    assert sorted(g["indicator"]) == sorted(FI.LABELS) and len(g) == 12
    assert all(r.firi_domain == FI.DOMAIN_OF[r.indicator] and r.label == FI.LABELS[r.indicator] for r in g.itertuples())
    five = {"market_prices": {"A1", "A2", "A3"}, "fish_production": {"C4"}, "climate": {"C1", "C2", "C3"},
            "employment": {"E1"}, "ofw_remittances": {"E2"}}
    for d, codes in five.items():
        assert set(g.loc[g["trigger_domain"] == d, "indicator"]) == codes
    assert (g["provincial_forecast_scope"] == "not validated (no provincial outcome)").all()


def test_asof_thresholds_point_in_time_and_frozen_equivalence():
    import pipeline as PL
    L = PL.cpi_quarterly()
    F, G, H = PL.frozen_thresholds()
    th = PL.asof_thresholds(L, "2023-01-20")                         # window exactly 2021-Q1..2022-Q4
    for p in PL.PROV:
        assert th[p]["n"] == 8 and abs(th[p]["food"] - F[p]) < 1e-9 and abs(th[p]["gap"] - G[p]) < 1e-9 and abs(th[p]["head"] - H[p]) < 1e-5
    early = PL.asof_thresholds(L, "2021-06-01")
    assert all(np.isnan(v["food"]) for v in early.values())        # too few published quarters: unavailable, not zero
    for iss in ("2023-01-05", "2024-07-24", "2026-10-01"):
        used = L[[PL.quarter_usable(int(q), iss) for q in L["q"]]]
        nq = (used["q"] * 3 + 3)
        assert all(f"{m // 12}-{m % 12 + 1:02d}-10" < iss for m in nq)


def test_training_inference_consistency_latest_origin(P):
    import pipeline as PL
    L = PL.cpi_quarterly()
    F, _, _ = PL.frozen_thresholds()
    last = P[P["t"] == P["t"].max()]
    th = PL.asof_thresholds(L, last["issue_date"].iloc[0])
    for r in last.itertuples():
        assert abs(r.A1_food_asof - (r.A1_food_frozen + F[r.province_code] - th[r.province_code]["food"])) < 1e-6


def test_regression_against_original_pipeline(P, N, stack1):
    P = P.sort_values(["t", "province_code"]).reset_index(drop=True)
    for new, old in (("A1_food_frozen", "A1_food"), ("A1_gap_frozen", "A1_gap"), ("A2_frozen", "A2"), ("A3_rice_yoy", "A3"),
                     ("C2_tc_300km", "C2"), ("C3_palay_corn_drop", "C3"), ("C4_fish_drop", "C4"), ("N1_fssi", "N1"), ("V1_vulnerability_profile", "V1")):
        a, b = P[new].to_numpy(float), stack1[old].to_numpy(float)
        assert np.array_equal(np.isnan(a), np.isnan(b)) and np.nanmax(np.abs(a - b)) < 1e-5, new
    s = stack1.drop_duplicates("t").set_index("t")
    n = N.set_index("t")
    assert np.nanmax(np.abs(n["E2_remit_decline_pct"] - s["E2"])) < 1e-3
    R = pd.read_csv(C / "out" / "regional_forecast_panel.csv")
    E = pd.read_csv(X / "E116_FIRI_Domains" / "out" / "e116_rows.csv")
    m = R.merge(E[["area", "t", "lead", "AF_food", "F_yoy", "h_last"]], on=["area", "t", "lead"], suffixes=("", "_e116"))
    assert len(m) == len(R)                                            # e116_rows.csv is stored at 6 significant digits
    assert all(np.allclose(m[c], m[f"{c}_e116"], rtol=1e-5, atol=1e-6, equal_nan=True) for c in ("AF_food", "F_yoy", "h_last"))


def test_geography_no_copied_national_or_regional_values(P, N):
    for c in P.columns:
        assert not c.startswith(("E2", "C1", "H1")), c                # national / regional values live in national_context only
    assert N["t"].is_unique and set(N["E2_resolution"]) == {"national"} and set(N["H1_resolution"]) == {"region (Balance Luzon)"}
    assert P.groupby("t")["province_code"].nunique().eq(5).all()


def test_missing_values_preserved_with_status(P, N):
    assert (P.loc[P["A3_rice_yoy"].isna(), "A3_status"].str.startswith("not_collected")).all()
    assert (P.loc[P["N1_fssi"].isna(), "N1_status"].str.startswith("insufficient_data")).all()
    assert not (P.loc[P["N1_fssi"].isna(), "N1_admitted_articles"] >= 5).any()
    assert (P.loc[P["A1_food_asof"].isna(), "threshold_status"] == "insufficient_data").all()
    assert P["C2_tc_local_100km"].isna().sum() == (P["C2_status"] == "incomplete").sum()
    assert (N.loc[N["E2_remit_decline_pct"].isna(), "E2_status"].str.startswith("not_collected")).all()


def test_publication_flags(P, N):
    assert (P.loc[P["issue_date"] < "2022-06-07", "cpi_vintage_status"] != "2018=100 public").all()
    assert (P.loc[P["issue_date"] < "2025-07-01", "V1_status"].str.startswith("unavailable_at_issue")).all()
    yrs = P["E1_prov_reference_year"].dropna()
    assert (yrs < P.loc[yrs.index, "issue_date"].str[:4].astype(int)).all()
    assert set(N["E2_status"].astype(str).str.split(" ").str[0]) <= {"verified", "rule_unverified", "not_collected"}


def test_lead_alignment_regional_panel():
    R = pd.read_csv(C / "out" / "regional_forecast_panel.csv")
    assert (R["q"] == R["t"] + R["lead"]).all() and set(R["lead"]) == {1, 2}
    assert (R["q_last"] <= R["t"]).all()
    assert (R["issue"] == [f"{(t + 1) // 4}-{((t + 1) % 4) * 3 + 1:02d}-01" for t in R["t"]]).all()


def test_raw_inputs_unchanged():
    man = json.loads((C / "out" / "pipeline_manifest.json").read_text())
    for path, h in man["inputs_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == h, path
