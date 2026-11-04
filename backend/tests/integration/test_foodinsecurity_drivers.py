"""
tests/integration/test_foodinsecurity_drivers.py
------------------------------------------------
AIPHEED_MAP_MODEL=foodinsecurity: the explanation bars are mathematically consistent with the served C-b record.
The five shown driver groups plus otherPct make 100% (integer rounding only); each bar's direction is the sign of its
SHAP contribution; the groups that are not model inputs have no bar value and say so; the classification and score
shown are the forecast record's.
"""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import foodinsecurity_system as FI

client = TestClient(app)
SLUGS = ("cavite", "laguna", "quezon", "rizal", "batangas")
QUARTERS = ("2026-Q3", "2026-Q4")   # the latest past quarter and the issued Lead-1 forecast


@pytest.fixture
def fi(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-26T09:00:00")
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "foodinsecurity")
    monkeypatch.setattr(FI, "DATA", FI.CB_DATA)                 # these tests check C-b's own export (previous main model)
    monkeypatch.setattr(FI, "LGU_VULNERABILITY", FI.CB_DATA / "lgu_vulnerability.csv")
    return monkeypatch


def _explain(slug: str, q: str):
    r = client.get("/api/v1/explainability", params={"scope": "province", "id": slug, "quarter": q})
    return r


@pytest.mark.parametrize("q", QUARTERS)
def test_bars_and_other_sum_to_100_and_directions_follow_the_sign(fi, q):
    for s in SLUGS:
        r = _explain(s, q)
        if r.status_code != 200:            # an issued forecast is withheld until approved (Rule 1)
            assert q != "2026-Q3"
            continue
        x = r.json()
        total = sum(t["pct"] for t in x["triggers"]) + x["otherPct"]
        assert abs(total - 100) <= len(x["triggers"]), (s, q, total)
        for t in x["triggers"]:
            c = t["signedContribution"]
            exp = "increases_risk" if c > 0 else "protective" if c < 0 else "no_effect"
            assert t["direction"] == exp, (s, q, t["key"])
            if t["key"] in FI.NOT_INPUT:
                assert t["pct"] == 0 and t["status"] != "contributes" and c == 0


def test_score_and_class_shown_are_the_forecast_record(fi):
    rows = pd.read_csv(FI.DATA / "rows.csv", dtype={"province_code": str})
    d = client.get("/api/v1/provinces", params={"quarter": "2026-Q3"}).json()["data"]
    rec = rows[rows["quarter"] == "2026-Q3"].set_index("province")
    for p in d:
        r = rec.loc[p["name"]]
        assert p["riskScore"] == pytest.approx(float(FI.score(r.to_dict())), abs=0.01)
        assert (p["riskLevel"] == "high") == (str(r["class"]).upper() == "HIGH")
