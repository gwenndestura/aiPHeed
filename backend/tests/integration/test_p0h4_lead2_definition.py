"""
P0H4 Lead 2 is the Chapter I combined label (hunger AND price), not a price-only forecast, and it says so:
  * every served row is P(hunger condition) x P(price condition) and its target is the issue quarter + lead;
  * Lead 2 forecasts the quarter after the issue quarter (not the Lead-1 quarter) and carries no observed outcome;
  * the served definition names both conditions; the Lead-2 label says experimental, Lead 1 says it passed;
  * the driver panel discloses that its bars explain the price part and that the hunger condition multiplies it;
  * the classification uses the 0.50 threshold.
"""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1

client = TestClient(app)


@pytest.fixture
def ch1(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-29T09:00:00")
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "ch1")           # the Chapter I map mode (opt-in)
    return monkeypatch


def _qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def test_rows_are_hunger_times_price_with_correct_horizons():
    r = pd.read_csv(CH1.DATA / "rows.csv", dtype={"province_code": str})
    issue_q = r["issue_date"].map(lambda d: int(d[:4]) * 4 + (int(d[5:7]) - 1) // 3)
    assert ((r["quarter"].map(_qi) - issue_q + 1) == r["lead"]).all()
    assert ((r["pi_hunger"] * r["pi_price"] - r["probability"]).abs() < 1e-5).all()
    assert ((r["probability"] >= 0.5) == (r["class"].str.upper() == "HIGH")).all()
    lead2 = r[r["lead"] == 2]
    assert len(lead2) == 5 and set(lead2["quarter"]) == {"2027-Q1"} and set(lead2["issue_date"]) == {"2026-10-01"}
    assert lead2["observed"].isna().all()                            # no future outcome attached to a forecast


def test_definition_names_both_conditions_and_lead2_is_experimental(ch1):
    d = CH1.INDICATOR["definition"]
    assert "hunger" in d and "food prices" in d and "P(hunger condition) x P(price condition)" in d
    f2 = client.get("/api/v1/forecast", params=dict(scope="province", id="cavite", quarter="2027-Q1", horizon="forecast")).json()
    f1 = client.get("/api/v1/forecast", params=dict(scope="province", id="cavite", quarter="2026-Q4", horizon="forecast")).json()
    assert "Lead-2" in f2["horizonLabel"] and "experimental" in f2["horizonLabel"]
    assert "Lead-1" in f1["horizonLabel"] and "passed the reliability test" in f1["horizonLabel"]
    row = CH1.row("PH040100000", "2027-Q1")
    assert f2["riskScore"] == pytest.approx(float(row["probability"]), abs=1e-6)


def test_panel_discloses_the_hunger_multiplier(ch1):
    e = client.get("/api/v1/explainability", params=dict(scope="province", id="cavite", quarter="2027-Q1")).json()
    note = e["triggers"][0]["evidenceNote"]
    h = float(CH1.row("PH040100000", "2027-Q1")["pi_hunger"])
    assert "food prices rise unusually fast" in note and "regional hunger condition" in note
    assert f"(here {h:.0%})" in note and "multiplies" in note
