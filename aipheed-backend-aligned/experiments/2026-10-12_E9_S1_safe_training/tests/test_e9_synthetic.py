"""
E9 synthetic tests. No project data file is read: guard decisions are tested on path strings,
enforcement on temporary synthetic files, and frame/metric logic on in-memory synthetic data.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pytest

import guard
import metrics as M
import safe_frame as F
from vault import Stop, Vault

AL = guard.AL
PROV = ("P1", "P2", "P3", "P4", "P5")


# ------------------------------------------------------------------ guard: decisions (paths only)
@pytest.mark.parametrize("path", [
    r"C:\Users\admin\aipheed\backend\data\processed\psa_indicators.parquet",
    r"C:\Users\admin\aipheed\backend\data\thesis\panel.parquet",
    r"C:\Users\admin\aipheed\backend\models\thesis_food_insecurity_model.joblib",
    r"C:\Users\admin\aipheed\aipheed-backend-aligned\data\processed\sws_hunger.parquet",
    r"C:\Users\admin\aipheed\aipheed-backend-aligned\data\processed\cpi_full.parquet",
    r"C:\Users\admin\aipheed\aipheed-backend-aligned\data\processed\corpus_geocoded.parquet",
    r"C:\Users\admin\aipheed\aipheed-backend-aligned\data\processed\oil_prices.parquet",
    r"C:\Users\admin\aipheed\aipheed-backend-aligned\aipheed.db",
    r"C:\Users\admin\aipheed\aipheed-backend-aligned\models\lgbm_best.pkl",
    r"C:\Users\admin\aipheed\aipheed-backend-aligned\data\revised\datadriven_forecasts_retrospective.parquet",
    r"C:\Users\admin\aipheed\Claude outputs\x.docx",
    str(Path.home() / ".claude" / "projects" / "x" / "session.jsonl"),
])
def test_protected_and_unlisted_paths_are_denied_for_reading(path):
    assert guard.decide(path, write=False) == "deny"


@pytest.mark.parametrize("rel", list(guard.ALLOW))
def test_allowlisted_paths_are_allowed(rel):
    assert guard.decide(str(AL / rel), write=False) == "allow"


def test_project_code_is_allowed_and_writes_outside_experiment_denied():
    assert guard.decide(str(AL / "app" / "ml" / "features" / "risk_score_v2.py"), write=False) == "allow"
    assert guard.decide(str(AL / "data" / "processed" / "labels.parquet"), write=True) == "deny"
    assert guard.decide(r"C:\Users\admin\aipheed\backend\.env", write=True) == "deny"
    assert guard.decide(str(guard.EXP / "runs" / "x.csv"), write=True) == "allow"


# ------------------------------------------------------------------ guard: enforcement (synthetic files)
def test_opening_a_protected_name_raises_even_in_temp(tmp_path):
    f = tmp_path / "cpi_full_synthetic.csv"
    f.write_text("a\n1\n")              # writing a synthetic file in temp is allowed
    with pytest.raises(guard.AccessDenied):
        open(f).read()                  # reading anything with a protected name is not
    with pytest.raises(guard.AccessDenied):
        pd.read_csv(f)


def test_all_public_parquet_entry_points_are_blocked(tmp_path):
    import pyarrow.parquet as pq
    p = tmp_path / "synthetic.parquet"
    with pytest.raises(guard.AccessDenied):
        pd.read_parquet(p)
    for fn in (pq.read_table, pq.read_schema, pq.read_metadata, pq.ParquetFile):
        with pytest.raises(guard.AccessDenied):
            fn(p)


def test_read_time_row_filter_never_returns_later_quarters(tmp_path):
    import pyarrow.parquet as pq
    p = tmp_path / "synthetic_rows.parquet"
    pq.write_table(pa.table({"quarter": ["2025-Q3", "2025-Q4", "2026-Q1", "2026-Q3"], "v": [1.0, 2.0, 3.0, 4.0]}), p)
    df = guard.read_filtered(p, ["quarter", "v"], "2025-Q4")
    assert sorted(df["quarter"]) == ["2025-Q3", "2025-Q4"]


def test_unlisted_parquet_cannot_use_the_allowed_reader():
    with pytest.raises(guard.AccessDenied):
        guard.read_allowed_parquet("data/processed/sws_hunger.parquet", ["quarter"])


def test_sqlite_and_subprocess_are_blocked():
    import sqlite3
    import subprocess
    with pytest.raises(guard.AccessDenied):
        sqlite3.connect(":memory:")
    with pytest.raises(guard.AccessDenied):
        subprocess.run(["cmd", "/c", "echo"], capture_output=True)


# ------------------------------------------------------------------ frame logic (synthetic)
def _yoy(values: dict[str, list[float]], quarters: list[str]) -> pd.DataFrame:
    return pd.DataFrame(values, index=quarters)


def test_quarter_arithmetic_and_origin():
    assert F.qadd("2024-Q1", -2) == "2023-Q3" and F.qadd("2023-Q4", 1) == "2024-Q1"
    assert F.qstart("2024-Q3") == pd.Timestamp("2024-07-01")


def test_cpi_rel_sums_to_zero_and_needs_all_five():
    qs = ["2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4"]
    g = _yoy({p: [1.0 + i, 2.0 + i, 3.0 + i, 4.0 + i] for i, p in enumerate(PROV)}, qs)
    f = F.provincial_cpi_features(g, "2023-Q4", PROV)
    assert abs(sum(f[p]["cpi_rel"] for p in PROV)) < 1e-12
    g.loc["2023-Q4", "P3"] = np.nan
    f = F.provincial_cpi_features(g, "2023-Q4", PROV)
    assert all(np.isnan(f[p]["cpi_rel"]) for p in PROV)          # never zero-filled
    assert np.isnan(f["P3"]["food_cpi_yoy"])


def test_cpi_dev_requires_two_prior_quarters():
    g = _yoy({p: [np.nan, np.nan, 5.0, 7.0] for p in PROV}, ["2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4"])
    f = F.provincial_cpi_features(g, "2023-Q4", PROV)
    assert np.isnan(f["P1"]["cpi_dev"])                           # only one prior value
    g.loc["2023-Q2"] = 3.0
    f = F.provincial_cpi_features(g, "2023-Q4", PROV)
    assert f["P1"]["cpi_dev"] == pytest.approx(7.0 - 4.0)


def test_last_published_and_training_quarters_respect_publication():
    stress = pd.DataFrame([{"province_code": p, "quarter": q, "stress": float(i)}
                           for i, q in enumerate(["2023-Q1", "2023-Q2", "2023-Q3"]) for p in PROV])
    pub = {"2023-Q1": pd.Timestamp("2023-05-01"), "2023-Q2": pd.Timestamp("2023-08-01"),
           "2023-Q3": pd.Timestamp("2023-10-20")}
    published = pub.get
    assert F.eligible_training_quarters(stress, "2023-Q4", published) == ["2023-Q1", "2023-Q2"]
    a, v = F.last_published(stress, "2023-Q4", published)
    assert a == "2023-Q2" and v["P1"] == 1.0
    assert F.eligible_training_quarters(stress, "2024-Q1", published) == ["2023-Q1", "2023-Q2", "2023-Q3"]


def test_poverty_vintage_by_origin():
    assert F.poverty_survey_year(pd.Timestamp("2022-07-01")) == 2020
    assert F.poverty_survey_year(pd.Timestamp("2022-10-01")) == 2021
    assert F.poverty_survey_year(pd.Timestamp("2024-10-01")) == 2023


def test_vault_refuses_unpublished_labels_and_early_reveal(tmp_path):
    stress = pd.DataFrame([{"province_code": "P1", "quarter": q, "stress": 1.0} for q in ("2023-Q1", "2023-Q4")])
    pub = {"2023-Q1": pd.Timestamp("2023-05-01"), "2023-Q4": pd.Timestamp("2024-01-20")}
    v = Vault(stress, pub.get)
    assert len(v.train(["2023-Q1"], "2023-Q4")) == 1
    with pytest.raises(Stop):
        v.train(["2023-Q4"], "2023-Q4")
    pred = tmp_path / "pred.csv"
    pred.write_text("x\n1\n")
    with pytest.raises(Stop):
        v.reveal(["2023-Q4"], pred)
    v.seal(pred)
    assert len(v.reveal(["2023-Q4"], pred)) == 1
    pred.write_text("x\n2\n")
    with pytest.raises(Stop):
        v.reveal(["2023-Q4"], pred)


# ------------------------------------------------------------------ metrics (synthetic)
def test_classification_metrics_and_undefined_balanced_accuracy():
    m = M.classification(np.array([True, True, False, False]), np.array([True, False, False, True]))
    assert m["accuracy"] == 0.5 and m["balanced_accuracy"] == 0.5
    assert m["confusion"] == {"true_HIGH_pred_HIGH": 1, "true_HIGH_pred_LOW": 1,
                              "true_LOW_pred_HIGH": 1, "true_LOW_pred_LOW": 1}
    m = M.classification(np.array([True, True, True]), np.array([True, True, True]))
    assert m["accuracy"] == 1.0 and m["balanced_accuracy"] is None


def test_auc_withheld_when_a_class_is_rare():
    r = M.ranking_auc(np.array([True] * 30 + [False] * 2), np.linspace(0, 1, 32))
    assert r["roc_auc"] is None and "not meaningful" in r["note"]


def test_brier_rejects_non_probabilities():
    assert M.brier(np.array([1, 0]), np.array([1.0, 0.0])) == 0.0
    with pytest.raises(ValueError):
        M.brier(np.array([1, 0]), np.array([14.0, 9.0]))


def test_concordant_pairs():
    obs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert M.concordant_pairs(obs, obs) == (10.0, 10)
    assert M.concordant_pairs(-obs, obs) == (0.0, 10)
    assert M.concordant_pairs(np.ones(5), obs) == (5.0, 10)
