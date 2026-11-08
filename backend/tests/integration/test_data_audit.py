"""
tests/integration/test_data_audit.py
------------------------------------
Non-destructive data validation (DATA_AUDIT_20261030). Reads source files only:
- schema and duplicates of the indicator source tables; province codes and the 142 LGUs;
- point-in-time rules on every Lead 1-2 row of the served training stack (CPI month, SWS round, news before issue;
  target = origin + lead);
- indicator-to-domain mapping against firi.py; geography substitutions recorded (national remittances copied, regional
  hunger copied); missing values never zero-filled; the development / confirmation split is disjoint;
- the audit outputs exist, classify all 12 indicators A-D, and the sources were not modified by the audit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
X = ROOT / "aipheed-backend-aligned" / "experiments"
A = X / "DATA_AUDIT_20261030"
PROV = {"PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"}
pytestmark = pytest.mark.skipif(not (A / "out" / "audit.json").exists(), reason="data audit outputs missing")


@pytest.fixture(scope="module")
def stack():
    S = pd.read_csv(X / "LEAD2_FIVE_TRIGGER" / "data" / "stack_l2.csv", dtype={"province_code": str})
    return S[S["lead"] <= 2]


def test_source_schemas_and_duplicates():
    c = pd.read_csv(X / "E41_Lead2_Audit/data_acquired/cpi_index_ACP22.csv")
    assert list(c.columns) == ["Geolocation", "Commodity Description", "Year", "Period", "value"]
    assert not c.duplicated(["Geolocation", "Commodity Description", "Year", "Period"]).any()
    y = pd.read_csv(X / "E40_SWS_CPI_Tiers/data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv", dtype=str)
    assert set(y["province_code"]) == PROV and not y.duplicated(["province_code", "commodity", "reference_month"]).any()
    f = pd.read_csv(X / "E41_Lead2_Audit/data_acquired/fisheries_production.csv")
    assert not f.duplicated(["Geolocation", "Subsector", "Year", "Quarter"]).any()


def test_geography_provinces_and_lgus():
    v = pd.read_csv(ROOT / "backend/data/inputs/lgu_vulnerability.csv")
    assert v["lgu_code"].nunique() == 142 and v.groupby("province").size().to_dict() == {"Batangas": 34, "Cavite": 23, "Laguna": 30, "Quezon": 41, "Rizal": 14}
    g = pd.read_csv(A / "GEOGRAPHICAL_COVERAGE_REPORT.csv")
    prov = g[g["resolution"] == "province"]
    assert (prov["calabarzon_provinces_present"] == 5).all()


def test_point_in_time_every_stack_row(stack):
    iss = pd.to_datetime(stack["issue_date"])
    assert ((pd.to_datetime(stack["psa_newest_month"] + "-01") + pd.offsets.MonthEnd(0)) < iss).all()
    for c in ("sws_newest_published", "news_latest_published"):
        m = stack[c].notna()
        assert (pd.to_datetime(stack.loc[m, c]) < iss[m]).all(), c
    assert (stack["target_q"] == stack["t"] + stack["lead"]).all()


def test_indicator_domain_mapping_and_classification():
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from app.ml.inference import firi as FI
    I = pd.read_csv(A / "INDICATOR_COMPLETENESS.csv")
    assert sorted(I["indicator"]) == sorted(FI.LABELS)
    for r in I.itertuples():
        assert r.firi_domain.startswith(FI.DOMAIN_OF[r.indicator])
        assert r.label == FI.LABELS[r.indicator]
    assert set(I["classification"]) <= {"A", "B", "C", "D"}


def test_substitutions_recorded_and_no_zero_fill(stack):
    q = pd.read_csv(A / "DATA_QUALITY_REPORT.csv").set_index("dataset")
    assert q.loc["BSP OFW cash remittances (macro panel)", "share_periods_identical_across_units"] == 1.0
    per_q = stack.groupby(["t", "lead"])["H1"].nunique()
    assert (per_q <= 1).all()                                    # one regional hunger value per quarter
    for c, first_year in (("N1", 2021), ("E2", 2021), ("C4", 2021), ("A3", 2021)):
        early = stack[stack["t"] // 4 == first_year][c]
        assert early.isna().all() and not (early == 0).any(), c   # no pre-2021 base: left missing, never zero
    clim = pd.read_parquet(X / "E107_Twelve_Indicator_LightGBM/data_inputs/pagasa_climate.parquet")
    assert clim["rainfall_anomaly_pct"].isna().all()             # recorded as absent, not zero


def test_split_integrity():
    E = pd.read_csv(X / "LEAD2_FIVE_TRIGGER/out/asof_reeval_rows.csv", dtype={"province_code": str})
    dev, conf = set(E.loc[E["q"] <= 2024 * 4 + 3, "q"]), set(E.loc[E["q"] > 2024 * 4 + 3, "q"])
    assert dev and conf and not (dev & conf)
    tr = json.loads((A / "out" / "audit.json").read_text())["training_readiness"]
    assert tr["provincial_T43c_lead2"]["independent_hunger_observations"] == 13 and tr["t43c_labels"]["hunger_values_per_quarter"] == 1


def test_audit_did_not_modify_sources():
    res = json.loads((A / "out" / "audit.json").read_text())
    for path, h in res["source_sha256"].items():
        if h:
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == h, path
    for f in ("DATA_AUDIT_REPORT.md", "INDICATOR_COMPLETENESS.csv", "DATASET_COVERAGE.csv", "TEMPORAL_ALIGNMENT_REPORT.csv",
              "GEOGRAPHICAL_COVERAGE_REPORT.csv", "DATA_QUALITY_REPORT.csv", "TRAINING_READINESS_REPORT.md", "DATA_ISSUES_AND_RECOMMENDATIONS.md"):
        assert (A / f).exists(), f
