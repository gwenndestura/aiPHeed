"""Tests for food-insecurity label reconstruction, published-estimate extraction, weights and reproducibility."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import pytest

from app.fi_labels import hfias as H
from app.fi_labels.published import CLEAN, RAW


def _hh(**q):
    return pd.DataFrame([{f"q{i}": q.get(f"q{i}", 0) for i in range(1, 10)}])


@pytest.mark.parametrize("answers,expected", [
    ({}, "food_secure"),
    ({"q1": 1}, "food_secure"),                         # rarely worries only: still food secure (Guide v3)
    ({"q1": 2}, "mildly_food_insecure"),
    ({"q2": 1}, "mildly_food_insecure"),
    ({"q3": 1, "q4": 1}, "mildly_food_insecure"),
    ({"q3": 2}, "moderately_food_insecure"),
    ({"q5": 1}, "moderately_food_insecure"),
    ({"q6": 2, "q1": 3}, "moderately_food_insecure"),
    ({"q5": 3}, "severely_food_insecure"),
    ({"q7": 1}, "severely_food_insecure"),                # any of the three severe conditions
    ({"q9": 1, "q1": 0}, "severely_food_insecure"),
])
def test_hfias_category_follows_guide_v3(answers, expected):
    assert H.category(_hh(**answers)).iloc[0] == expected


def test_score_range_and_missing():
    df = pd.concat([_hh(), _hh(**{f"q{i}": 3 for i in range(1, 10)}), _hh(q1=np.nan)], ignore_index=True)
    s, c = H.score(df), H.category(df)
    assert s.iloc[0] == 0 and s.iloc[1] == 27 and pd.isna(s.iloc[2]) and pd.isna(c.iloc[2])
    with pytest.raises(ValueError):
        H.category(_hh(q1=4))


def test_weighted_prevalence_and_design_se():
    rng = np.random.default_rng(1)
    n = 4000
    y = pd.Series(rng.random(n) < 0.3).astype(int)
    w = pd.Series(rng.uniform(0.5, 2.0, n))
    r = H.weighted_prevalence(y, w)
    assert r["prevalence"] == pytest.approx(np.average(y, weights=w))
    assert r["se"] == pytest.approx(np.sqrt(0.21 / r["n_effective"]), rel=0.15)
    psu = pd.Series(np.repeat(np.arange(n // 20), 20))           # clustered design: SE should not shrink
    clustered = H.weighted_prevalence(y, w, pd.Series(0, index=y.index), psu)
    assert clustered["se"] > 0 and clustered["n"] == n


def test_published_tables_cover_all_provinces_and_sum_to_100():
    h = pd.read_csv(CLEAN / "published_hfias_2015_calabarzon.csv")
    assert set(h["geography"]) == {"CALABARZON", "Batangas", "Cavite", "Laguna", "Quezon", "Rizal"}
    sums = h.pivot_table(index="geography", columns="category", values="percent").sum(axis=1)
    assert ((sums - 100).abs() <= 0.2).all()
    assert (h["ci95_low"] <= h["percent"]).all() and (h["percent"] <= h["ci95_high"]).all()
    assert set(h["instrument"]) == {"HFIAS"}


def test_fies_benchmark_recorded_and_not_mixed_with_hfias():
    f = pd.read_csv(CLEAN / "published_fies_psa_sdg212.csv")
    r = f[(f["geography"] == "Region IV-A") & (f["year"] == 2023)].iloc[0]
    assert r["percent"] == 19.1 and r["ci95_low"] == 17.0 and r["ci95_high"] == 21.1
    assert set(f["instrument"]) == {"FIES"}
    assert not (f["level"] == "province").any()            # no provincial FIES values exist in the source


def test_raw_files_unchanged():
    m = pd.read_csv(RAW / "MANIFEST.csv")
    for _, r in m[m["status"] == "acquired"].iterrows():
        assert hashlib.sha256((RAW / r["file"]).read_bytes()).hexdigest() == r["sha256"], r["file"]


def test_owner_workbook_verified_records_match_primary():
    from app.fi_labels.workbook import OWNER
    v = pd.read_csv(CLEAN / "owner_workbook_records_verified.csv")
    assert len(v) == 50 and not (v["verification_status_aipheed"] == "MISMATCH_with_primary").any()
    prim = v[v["verification_status_aipheed"] == "verified_primary"]
    assert len(prim) == 40 and ((prim["label_value"] - prim["primary_value"]).abs() < 0.051).all()
    assert set(v.loc[v["record_id"].str.startswith("ENNS"), "verification_status_aipheed"]) == {"unverified_secondary"}
    assert (OWNER / "aiPHeed_CALABARZON_Labeled_Provincial_Data.xlsx").exists()
