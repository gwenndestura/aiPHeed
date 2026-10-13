"""Regression test for the E23 disaggregator fix (synthetic frames injected; no file read)."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend_dev"))
from app.ml.inference.disaggregator import Disaggregator  # noqa: E402


def make():
    d = Disaggregator()
    d._lgu = pd.DataFrame({"province_code": ["A", "A", "B", "B"], "lgu_code": ["a1", "a2", "b1", "b2"],
                           "lgu_name": ["a1", "a2", "b1", "b2"], "population_2020": [100, 400, 100, 300],
                           "land_area_km2": [10, 10, 10, 10]})
    d._pov = pd.DataFrame({"lgu_code": ["a1", "a2", "b1", "b2"], "poverty_incidence_pct": [10, 10, 5, 9],
                           "source_note": ["x (province-mean fallback)", "x (province-mean fallback)", "x (LGU-specific SAE)", "y"]})
    return d


def test_missing_province_is_unavailable_not_zero():
    out = make().disaggregate([{"province_code": "A", "risk_probability": 0.8}], "Q")
    b = out[out["province_code"] == "B"]
    assert b["risk_index"].isna().all() and (b["data_sufficiency_flag"] == "NO_PROVINCE_FORECAST").all()
    assert out.tail(2)["province_code"].eq("B").all()           # unavailable rows sort last, never as "safest"


def test_values_and_fallback_flag():
    out = make().disaggregate([{"province_code": "A", "risk_probability": 0.5},
                               {"province_code": "B", "risk_probability": 1.0}], "Q").set_index("lgu_code")
    assert out.loc["a2", "risk_index"] == 0.2 and out.loc["a1", "risk_index"] == 0.0   # poverty tie -> density only
    assert out.loc["b2", "risk_index"] == 1.0
    assert out.loc["a1", "poverty_is_province_fallback"] and not out.loc["b1", "poverty_is_province_fallback"]
