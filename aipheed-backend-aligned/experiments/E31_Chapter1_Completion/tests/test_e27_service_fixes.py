"""E27 regression tests for the main dashboard service and predictor (dev copy), on synthetic fixtures only."""
import pandas as pd
import pytest

import _paths  # noqa: F401
from _paths import EXP
from app.ml.inference import predictor as PR
from app.services import dashboard as svc


def _predictor(lead):
    p = PR.Predictor.__new__(PR.Predictor)
    p._lead_time = lead
    p.load = lambda: None
    return p


@pytest.mark.parametrize("lead", [0, 2])
def test_predictor_never_quotes_75_percent_accuracy_as_validation(lead):
    p = _predictor(lead)
    s = p.confidence_statement()
    assert "not validated" in s and "held mean accuracy" not in s and "met the 75%" not in s
    assert "always says HIGH" in s
    assert ("not a forecast" in p.horizon_label()) == (lead == 0)
    assert lead == 0 or "not validated" in p.horizon_label()


def test_horizon_info_makes_no_validated_horizon_claim():
    d = svc.HORIZON_INFO[svc.FORECAST]
    assert "at or above 75%" not in d["definition"] and "adopted as the operational horizon" not in d["definition"]
    assert d["evidenceStatus"] == "EXPERIMENTAL" and "experimental" in d["name"]
    assert "Algorithm 3" not in svc.INDICATOR["horizon"]


class _Eng:
    def __init__(self, lead):
        self.lead_time = lead


@pytest.mark.parametrize("lead,state", [(0, "current"), (1, "forecast")])
def test_timeline_labels_a_same_quarter_estimate_as_current_not_forecast(monkeypatch, lead, state):
    monkeypatch.setattr(svc, "available_quarters", lambda horizon=svc.DEFAULT_HORIZON: ["2025-Q3", "2025-Q4"])
    monkeypatch.setattr(svc, "_engine", lambda horizon=svc.DEFAULT_HORIZON: _Eng(lead))
    t = svc.timeline()
    assert [x["state"] for x in t] == ["actual", state]


def test_news_dates_are_philippine_calendar_dates(monkeypatch, tmp_path):
    f = tmp_path / "articles.parquet"
    pd.DataFrame([{"published": "2026-03-31T17:30:00Z", "quarter": "2026-Q2", "is_relevant": True,
                   "province_code": "PH040300000", "title": "t", "top_topic_name": None}]).to_parquet(f)
    monkeypatch.setattr(svc, "CORPUS_PATH", f)
    svc._corpus.cache_clear()
    try:
        df = svc._corpus()
        assert df["_date"].tolist() == ["2026-04-01"]          # 01:30 PHT on 1 April, counted in 2026-Q2
        assert svc.news("PH040300000", "2026-Q2", 1, 10)["data"][0]["date"] == "2026-04-01"
    finally:
        svc._corpus.cache_clear()


def test_municipal_poverty_provenance_is_disclosed(monkeypatch):
    monkeypatch.setattr(svc, "LGU_PROVENANCE_PATH", EXP / "backend_dev" / "data" / "inputs" / "lgu_vulnerability.csv")
    svc._lgu_provenance.cache_clear()
    try:
        sub = svc._poverty_provenance("042123000", None)           # Gen. Mariano Alvarez: no municipal SAE
        assert sub["povertyEstimateKind"].startswith("province-mean substitute")
        assert sub["povertyValueUsed"] == 4.3 and "density only" in sub["povertyLimitation"]
        own = svc._poverty_provenance("045645000", 18.7)           # Sariaya: PSA municipal SAE 18.7
        assert own == {"povertyEstimateKind": "PSA municipal SAE estimate (2021)", "povertyValueUsed": 18.7,
                       "povertyLimitation": None}
        lg = pd.read_csv(EXP / "backend_dev" / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
        kinds = [svc._poverty_provenance(c, None)["povertyEstimateKind"] for c in lg["lgu_code"]]
        assert sum(k.startswith("province-mean") for k in kinds) == 126 and len(kinds) == 142
    finally:
        svc._lgu_provenance.cache_clear()


def test_risk_payloads_carry_evidence_status_and_basis():
    src = (EXP / "backend_dev" / "app" / "services" / "dashboard.py").read_text(encoding="utf-8")
    # E28: the LGU payload no longer carries a band at all (riskLevel None, LGU_POSITION_BASIS); the province payload
    # keeps the E27 basis text. So RISK_LEVEL_BASIS appears once and LGU_POSITION_BASIS once.
    assert src.count('"evidenceStatus": "EXPERIMENTAL"') >= 3 and src.count('"riskLevelBasis": RISK_LEVEL_BASIS') == 1
    assert src.count('"riskLevelBasis": LGU_POSITION_BASIS') == 1 and '"riskLevel": None,' in src
    assert "not a validated classification" in svc.RISK_LEVEL_BASIS
    assert "No HIGH/LOW band" in svc.LGU_POSITION_BASIS
