"""
tests/integration/test_lead2_final_signal.py
--------------------------------------------
PROTOCOL_LEAD2_FINAL_SIGNAL: protocol frozen and inputs hashed (reproducibility); every method forecast and every
error distribution behind a probability uses only outcomes known before the origin; gates decided on DEV only; no
candidate selected, so no 65-row audit; news missingness follows its definition; sensitivities and contributions
recorded; seals and served model unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
FS = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FINAL_SIGNAL"
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
pytestmark = pytest.mark.skipif(not (FS / "out" / "study.json").exists(), reason="final-signal outputs missing")
SEALS = {"cr_prospective.csv": "dd293e2e36c87be26657b98c51184c5b8b1887bb0252ee4aa65a3dc3a1103da6",
         "cranc_prospective.csv": "07c99e569746cb255dbd748c8c0eed095fd31944be551272d0187c45b49e3986",
         "rizal_2027q1_companion.csv": "b1edb799f6f08158161164e8fab96c8ec3954cba91d8af36fe6392866753094a"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def st():
    return json.loads((FS / "out" / "study.json").read_text())


def test_protocol_and_inputs_reproducible(st):
    assert sha(FS / "PROTOCOL_LEAD2_FINAL_SIGNAL.md") == (FS / "runner" / "PROTOCOL_SHA256.txt").read_text().strip() == st["protocol_sha256"]
    paths = {"stack_l2.csv": LT / "data" / "stack_l2.csv", "asof_reeval_rows.csv": LT / "out" / "asof_reeval_rows.csv",
             "labels_t43c.csv": ROOT / "aipheed-backend-aligned" / "experiments" / "FORECAST_RESEARCH" / "data" / "labels_t43c.csv",
             "known_price_l2.csv": LT / "data" / "known_price_l2.csv"}
    for k, p in paths.items():
        assert sha(p) == st["input_sha256"][k], k


def test_method_forecasts_point_in_time(st):
    assert st["ridge_train_max_target_lt_origin"] and st["sigma_log_max_error_target_lt_origin"]
    assert all(r["train_max_target"] <= r["origin"] - 1 for r in st["ridge_log"])
    V = pd.read_csv(FS / "out" / "method_rows.csv", dtype={"province_code": str})
    L = pd.read_csv(ROOT / "aipheed-backend-aligned" / "experiments" / "FORECAST_RESEARCH" / "data" / "labels_t43c.csv", dtype={"province_code": str})
    th = {"PH040100000": 4.713333333333334}
    g = L[L["province_code"] == "PH040100000"].set_index("q")
    for r in V[(V["province_code"] == "PH040100000") & V["M1_f"].notna()].head(10).itertuples():
        assert abs(r.M1_f - (g.loc[r.t - 1, "F"] - th["PH040100000"])) < 1e-4      # last observation = quarter t-1, known at O(t)
        assert r.t - 1 < r.q


def test_gates_dev_only_and_no_candidate(st):
    assert st["gates"] == {"K-A": False, "K-B": False, "K-E": False}
    c = json.loads((FS / "out" / "candidates.json").read_text())
    assert c["selected"] is None and not any(v["fitted"] for v in c["cands"].values())
    assert st["news"]["N1_nan_iff_articles_lt5"] and st["news"]["dev_coverage"] < .30


def test_sensitivities_and_contributions_recorded():
    s = json.loads((FS / "out" / "sensitivity.json").read_text())["B0"]
    assert s["S-EARLY"]["L2_DEV"]["rows"] == 0                  # DEV cannot be evaluated without the early training rows
    assert s["S-LAG"]["L2_DEV"]["brier"] > s["S-LAG"]["L2_DEV"]["reference_brier_same_rows"]
    g = pd.read_csv(FS / "LEAD2_TRIGGER_CONTRIBUTIONS.csv")
    assert set(g["group"]) == {"market_prices", "climate_stress", "employment_remittances", "poverty_vulnerability", "news_nlp"}
    assert len(g) == 20 and g["holm_p"].between(0, 1).all()
    a = pd.read_csv(FS / "LEAD2_INDICATOR_AVAILABILITY.csv")
    assert len(a) == 12 and a.loc[a["indicator"] == "V1", "availability_status"].str.contains("VIOLATION").all()


def test_seals_and_served_model_unchanged(monkeypatch):
    for f, h in SEALS.items():
        assert sha(LT / "sealed" / f) == h
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
