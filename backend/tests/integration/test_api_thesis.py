"""Public thesis-model routes (E168, LightGBM): reachable without login, consistent with the locked E168 outputs."""
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app

needs_e166 = pytest.mark.skipif(os.environ.get("AIPHEED_E166_SERVE", "1") == "0", reason="thesis-model serving switched off")

client = TestClient(app)


def test_overview_is_public_and_reports_both_reliability_rules():
    r = client.get("/api/v1/thesis/overview")
    assert r.status_code == 200
    d = r.json()
    assert d["maxReliableLeadStrict"] == 1 and d["maxReliableLeadPaperRule"] == 3
    l1 = next(x for x in d["leads"] if x["lead"] == 1)
    assert l1["correct"] == 56 and l1["rows"] == 72 and l1["reliable"] is True
    assert all(l1["criteria"].values())
    assert "pending adviser" in d["status"]["adoption"]


def test_forecast_has_five_calabarzon_provinces_with_drivers():
    d = client.get("/api/v1/thesis/forecast").json()
    assert d["targetQuarter"] == "2027-Q1" and d["highLine"] == 50
    assert sorted(p["province"] for p in d["provinces"]) == ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
    for p in d["provinces"]:
        assert p["class"] == ("HIGH" if p["score"] >= 50 else "LOW")
        assert 0 <= p["p_high"] <= 1 and p["topDrivers"]


def test_lgus_142_ranked_by_paper_formula_and_filterable():
    d = client.get("/api/v1/thesis/lgus").json()
    rows = d["rows"]
    assert d["count"] == 142 and len(rows) == 142
    assert [r["rank_in_region"] for r in rows] == list(range(1, 143))
    for r in rows:
        assert abs(r["vulnerability"] - (0.6 * r["poverty_norm"] + 0.4 * r["density_norm"])) < 1e-3
        assert abs(r["risk_index"] - r["province_risk_prob"] * r["vulnerability"]) < 1e-3
        assert r["data_sufficiency_flag"] in ("OK", "LIMITED_SIGNAL")
    q = client.get("/api/v1/thesis/lgus", params={"province": "Quezon"}).json()
    assert q["count"] == 41 and all(r["province_name"] == "Quezon" for r in q["rows"])


def test_baselines_e168_beats_all_rq3_on_accuracy_f1_auc():
    d = client.get("/api/v1/thesis/baselines", params={"lead": 1}).json()
    assert set(d["beatsRq3"]) == {"PERS", "LR", "LR_GOV", "LR_NEWS", "GOV", "NEWS"}
    for v in d["beatsRq3"].values():
        assert v["accuracy"] and v["f1"] and v["auc"]
    assert client.get("/api/v1/thesis/baselines", params={"lead": 9}).status_code == 422


@needs_e166
def test_existing_dashboard_serves_e168_on_every_quarter():
    q = client.get("/api/v1/quarters").json()
    assert q["current"] == "2027-Q1"
    assert all(x["state"] != "unavailable" for x in q["quarters"])          # the thesis model fills 2025-Q2 and 2025-Q3
    for quarter in ("2023-Q1", "2025-Q2", "2025-Q3", "2026-Q4", "2027-Q1"):
        d = client.get("/api/v1/provinces", params={"quarter": quarter}).json()
        assert d["indicator"]["id"] == "e168_high_food_insecurity_probability"
        assert len(d["data"]) == 5 and all(0 <= p["riskScore"] <= 1 for p in d["data"])
        n = sum(len(client.get(f"/api/v1/provinces/{p}/municipalities", params={"quarter": quarter}).json()["data"])
                for p in ("batangas", "cavite", "laguna", "quezon", "rizal"))
        assert n == 142


@needs_e166
def test_live_quarter_equals_the_sealed_e168_forecast():
    import json
    from app.paths import BACKEND_DIR
    sealed = {r["province"]: r["p_high"] for r in json.loads((BACKEND_DIR / "data/e168/out/sealed_2027-Q1.json").read_text())["forecasts"]}
    site = {p["name"]: p["riskScore"] for p in client.get("/api/v1/provinces", params={"quarter": "2027-Q1"}).json()["data"]}
    assert all(abs(site[k] - sealed[k]) < 1e-3 for k in sealed)


def test_drivers_and_face_validity():
    d = client.get("/api/v1/thesis/drivers").json()
    assert abs(sum(d["groupShare"].values()) - 1) < 1e-3 and set(d["h1"]["best_rank"]) == {"FSSI", "food_CPI_deviation"}
    f = client.get("/api/v1/thesis/face-validity").json()
    assert f["calabarzon_class_agreement"] == "5 of 5"


@needs_e166
def test_driver_shares_use_abs_shap_over_all_inputs_and_add_to_100():
    """Each driver's share = sum |SHAP| of its inputs / sum |SHAP| of all served inputs; otherPct is the rest (sums to 100)."""
    from app.services import e166_serving as S
    c = S._contrib("2027-Q1")
    for slug, name in (("batangas", "Batangas"), ("quezon", "Quezon"), ("cavite", "Cavite")):
        d = client.get("/api/v1/explainability", params={"scope": "province", "id": slug, "quarter": "2027-Q1"}).json()
        five = {t["key"]: t["pct"] for t in d["triggers"]}
        assert d["otherPct"] is not None and sum(five.values()) + d["otherPct"] == 100
        x = c[c["province"] == name]
        tot = x["contribution"].abs().sum()
        for k, v in five.items():
            assert abs(v - 100 * x[x["ui_group"] == k]["contribution"].abs().sum() / tot) <= 1.0
    r = client.get("/api/v1/explainability", params={"scope": "region", "id": "calabarzon", "quarter": "2027-Q1"}).json()
    assert sum(t["pct"] for t in r["triggers"]) + r["otherPct"] == 100


@needs_e166
def test_thesis_model_quarters_are_marked_as_forecasts_and_fish_is_production():
    s = client.get("/api/v1/forecast/timeseries", params={"scope": "province", "id": "quezon"}).json()["series"]
    assert s and all(p["isForecast"] for p in s)
    d = client.get("/api/v1/explainability", params={"scope": "province", "id": "quezon", "quarter": "2027-Q1"}).json()
    assert "Fish Production" in {t["label"] for t in d["triggers"]} and "Fish Kill" not in {t["label"] for t in d["triggers"]}


def test_render_deployment_serves_e168_in_strict_mode(monkeypatch):
    """render.yaml must deploy the thesis model: no Lead-2 research mode (it switches E168 off), AIPHEED_THESIS_MODEL=e168,
    and the strict start-up check passes on the committed E168 files."""
    import re
    from app.main import strict_model_check
    from app.paths import BACKEND_DIR
    from app.services import e166_serving as S
    text = (BACKEND_DIR.parent / "render.yaml").read_text()
    env = dict(re.findall(r"- key: (\w+)\s+value: \"?([^\"\n]+)\"?", text))
    assert "AIPHEED_LEAD2_MODEL" not in env and env.get("AIPHEED_THESIS_MODEL") == "e168" and env.get("AIPHEED_STRICT_MODEL") == "1"
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    monkeypatch.setenv("AIPHEED_THESIS_MODEL", "e168")
    monkeypatch.setenv("AIPHEED_STRICT_MODEL", "1")
    assert S.validate() == []
    strict_model_check()                                   # raises if E168 cannot be served
    assert client.get("/api/v1/provinces", params={"quarter": "2027-Q1"}).json()["indicator"]["id"] == "e168_high_food_insecurity_probability"


def test_e168_alerts_and_refresh_are_wired():
    from datetime import date
    from app.e168 import alerts as A, refresh as R
    from app.tasks import scheduler as SCH
    assert R.next_target(date(2026, 11, 7)) == "2027-Q1" and R.next_target(date(2027, 1, 2)) == "2027-Q2"
    assert A.candidates("2027-Q1") == []                   # every 2027-Q1 P(HIGH) is below the 0.60 alert threshold
    assert callable(SCH.run_e168_refresh)
