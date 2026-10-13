"""
Development-protocol Rule L (scripts/supplementary/devprotocol_rule_l.py):
date eligibility, label timing, missing values, revised inputs, exclusion of
retail rice, supplementary SWS rounds as inputs only, and no production writes.
"""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.supplementary.devprotocol_rule_l as D
import scripts.supplementary.timing_audit as T

PRODUCTION_FILES = ["data/processed/labels.parquet", "data/processed/sws_hunger.parquet",
                    "data/processed/psa_indicators.parquet", "data/processed/features_fused.parquet",
                    "app/ml/corpus/sws_hunger_fetcher.py"]


def _hashes():
    return {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in PRODUCTION_FILES}


@pytest.fixture(scope="module")
def built():
    before = _hashes()
    frame, usable = D.development_frame()
    table = D.eligibility_table()
    return {"before": before, "after": _hashes(), "frame": frame, "usable": usable, "table": table,
            "rounds": D.sws_rounds()}


# ---- SWS rounds and date eligibility
def test_every_round_has_a_publication_record(built):
    r = built["rounds"]
    assert sum(x.source == "production" for x in r) == 20 and sum(x.source == "supplementary" for x in r) == 3
    assert [x.date_type for x in r if x.quarter == "2026-Q2"] == ["unknown"]


def test_no_protected_outcome_anywhere(built):
    assert not {x.quarter for x in built["rounds"]} & D.PROTECTED
    labels = D.W.window_labels(D.W.THR_PRIMARY)
    assert labels["quarter"].max() <= "2025-Q4"


def test_sws_inputs_published_before_origin(built):
    f = built["frame"].dropna(subset=["sws_published"])
    assert (pd.to_datetime(f["sws_published"]) < pd.to_datetime(f["origin"])).all()


def test_unknown_date_round_is_never_an_input(built):
    s = D.sws_known(T.qstart("2026-Q4"), built["rounds"])
    assert s["sws_round_quarter"] == "2026-Q1"          # June 2026 (date unknown) excluded


def test_supplementary_rounds_are_inputs_not_labels(built):
    assert all(not x.in_label_definition_A for x in built["rounds"] if x.source == "supplementary")
    assert D.label_published("2025-Q2")[0] is None and D.label_published("2025-Q3")[0] is None
    t = built["table"].set_index("target")
    assert t.loc["2025-Q3", "sws_input_published"] == pd.Timestamp("2025-06-27")
    assert t.loc["2025-Q4", "sws_input_published"] == pd.Timestamp("2025-08-15")
    assert t.loc["2026-Q1", "sws_input_published"] == pd.Timestamp("2025-11-05")
    assert t.loc["2025-Q3", "sws_input_source"] == "supplementary"


# ---- label timing (Rule L1)
def test_every_training_label_published_before_origin():
    for tq in ["2022-Q3", "2023-Q3", "2024-Q2", "2025-Q1", "2025-Q4", "2026-Q3"]:
        for q in D.eligible_training_quarters(tq):
            assert D.label_published(q)[0] < T.qstart(tq) and q < tq


def test_two_round_label_waits_for_second_round():
    assert "2022-Q2" not in D.eligible_training_quarters("2022-Q3")      # 2nd round published 2022-09-10
    assert "2022-Q2" in D.eligible_training_quarters("2022-Q4")


def test_2021_labels_not_before_rebasing():
    for q in ("2021-Q2", "2021-Q3", "2021-Q4"):
        assert D.label_published(q)[0] >= D.REBASE_DATE
    assert D.eligible_training_quarters("2022-Q1") == []


def test_label_waits_for_cpi_when_cpi_is_later():
    assert "2024-Q4" not in D.eligible_training_quarters("2025-Q1")
    assert D.label_published("2025-Q1")[0] == pd.Timestamp("2025-04-04") + pd.Timedelta(days=14)


# ---- verified vs proxy dates (WD1)
def test_proxy_and_verified_dates_are_distinguishable():
    assert D.cpi_published("2024-Q4", provincial=True)[1] == "verified"
    d, t = D.cpi_published("2023-Q1", provincial=True)
    assert t == "proxy" and d == pd.Timestamp("2023-04-05") + pd.Timedelta(days=14)
    assert D.cpi_published("2023-Q1", provincial=False) == (pd.Timestamp("2023-04-05"), "verified")
    assert D.label_published("2023-Q1", "strict")[0] is None


def test_strict_protocol_uses_only_verified_label():
    assert set(D.eligible_training_quarters("2026-Q3", "strict")) == {"2024-Q4"}


# ---- missing values stay missing
def test_unavailable_values_are_nan_not_zero(built):
    f = built["frame"].set_index(["target_quarter", "province_code"])
    early = f.loc[["2021-Q4", "2022-Q1"]]
    assert early["food_cpi_yoy"].isna().all() and early["headline_cpi"].isna().all()   # WD5
    assert built["frame"].loc[built["frame"]["target_quarter"] == "2021-Q3", "sws_hunger"].isna().all()
    assert not (built["frame"]["sws_hunger"] == 0).any()


# ---- revised inputs and excluded inputs
def test_revised_inputs_development_only():
    dev, strict = set(D.feature_mask("development")), set(D.feature_mask("strict"))
    for c in ("enso_numeric", "drought_alert", "tc_count", "rainfall_anomaly_pct"):
        assert c in dev and c not in strict
    for c in ("food_cpi_yoy", "cpi_rel", "rice_price_regular", "unemployment_rate", "ofw_remit_yoy_pct"):
        assert c in dev and c not in strict


def test_retail_rice_with_unresolved_provenance_is_excluded(built):
    for c in ("rice_retail_regular", "rice_retail_well"):
        assert c not in D.feature_mask("development") and c not in D.feature_mask("strict")
        assert c not in built["frame"].columns


def test_masks_cover_expected_counts():
    assert len(D.feature_mask("development")) == 49 and len(D.feature_mask("strict")) == 22


# ---- no production change
def test_building_the_frame_writes_nothing(built):
    assert built["before"] == built["after"]
