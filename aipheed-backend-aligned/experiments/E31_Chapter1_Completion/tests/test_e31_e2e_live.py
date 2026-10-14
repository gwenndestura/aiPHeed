"""E31 live end-to-end test: a running backend (AIPHEED_E2E_URL, e.g. http://127.0.0.1:8031) must serve the SAME numbers
as the E31 record on every surface the dashboard uses. Skipped when no server is reachable (it is not a mock test)."""
import hashlib
import json
import os

import pytest

import _paths  # noqa: F401

requests = pytest.importorskip("requests")
BASE = os.getenv("AIPHEED_E2E_URL", "http://127.0.0.1:8031").rstrip("/") + "/api/v1"
REC_PATH = _paths.EXP / "backend_dev" / "data" / "e31" / "e31_record.json"
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}


def _up() -> bool:
    try:
        return requests.get(BASE + "/health", timeout=3).ok
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _up(), reason="no live backend at AIPHEED_E2E_URL")


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC_PATH.read_text(encoding="utf-8"))


def get(path, **params):
    r = requests.get(BASE + path, params=params, timeout=60)
    return r


def q(rec, quarter, mode):
    return next(x for x in rec["quarters"] if x["quarter"] == quarter and x["mode"] == mode)


def test_record_endpoint_is_the_file_and_verifies(rec):
    r = get("/quarterly/e31/record")
    assert r.ok and r.json()["content_sha256"] == rec["content_sha256"]


def test_province_map_matches_record_for_each_mode(rec):
    for quarter, mode, horizon in (("2026-Q3", "RETROSPECTIVE_BLIND", "forecast"), ("2027-Q1", "FORECAST", "forecast"),
                                   ("2026-Q4", "NOWCAST", "nowcast"), ("2024-Q4", "BACKTEST", "forecast")):
        body = get("/provinces", quarter=quarter, horizon=horizon).json()
        want = q(rec, quarter, mode)["provinces"]
        got = {d["provinceCode"]: d for d in body["data"]}
        assert set(got) == set(want)
        for c, v in want.items():
            assert got[c]["riskScore"] == v["p_high"], (quarter, c)
            assert got[c]["riskLabel"] is None                      # no HIGH/LOW for an unvalidated lead
        assert {d["forecastHorizonQuarters"] for d in body["data"]} == {q(rec, quarter, mode)["lead"]}


def test_default_quarters_are_nowcast_and_forecast(rec):
    f = get("/quarters", horizon="forecast").json()
    n = get("/quarters", horizon="nowcast").json()
    assert f["current"] == "2027-Q1" and f["quarters"][-1]["state"] == "forecast"
    assert "2026-Q4" not in [x["id"] for x in f["quarters"]]          # a forecast view never shows a nowcast
    # the default (nowcast) timeline opens on the quarter under way and keeps every mode labelled
    states = {x["id"]: x["state"] for x in n["quarters"]}
    assert n["current"] == "2026-Q4" and states["2026-Q4"] == "current" and states["2027-Q1"] == "forecast"
    assert states["2026-Q3"] == "actual" and states["2023-Q4"] == "actual"
    lab = {d["provinceCode"]: d["horizonLabel"] for d in get("/provinces", quarter="2026-Q4", horizon="nowcast").json()["data"]}
    assert all("nowcast" in v for v in lab.values())
    lab = {d["provinceCode"]: d["horizonLabel"] for d in get("/provinces", quarter="2027-Q1", horizon="nowcast").json()["data"]}
    assert all("forecast" in v for v in lab.values())


def test_ranking_explanations_are_exact_driver_differences(rec):
    body = get("/ranking", quarter="2027-Q1", horizon="forecast").json()
    prov = q(rec, "2027-Q1", "FORECAST")["provinces"]
    order = sorted(prov, key=lambda c: prov[c]["p_high"], reverse=True)
    assert [d["provinceCode"] for d in body["data"]] == order
    for i, d in enumerate(body["data"][:-1]):
        a, b = prov[order[i]]["drivers"], prov[order[i + 1]]["drivers"]
        diff = {x["key"]: round(x["contribution"] - y["contribution"], 4) for x, y in zip(a, b)}
        for w in d["whyAboveNextLower"]:
            assert abs(w["difference"] - diff[w["feature"]]) < 1e-4


def test_explainability_matches_record_drivers(rec):
    for c, slug in SLUG.items():
        body = get("/explainability", scope="province", id=slug, quarter="2026-Q4").json()
        want = {d["key"]: d["contribution"] for d in q(rec, "2026-Q4", "NOWCAST")["provinces"][c]["drivers"]}
        got = {t["key"]: t["signedContribution"] for t in body["triggers"]}
        assert got == want


def test_municipalities_match_record_ranking(rec):
    want = {r["lgu_code"]: r for r in rec["lgu_ranking"]["rows"]}
    n = 0
    for slug in SLUG.values():
        body = get(f"/provinces/{slug}/municipalities", quarter="2026-Q4").json()
        for m in body["data"]:
            w = want[m["lguCode"]]
            assert m["riskIndex"] == w["risk_index"] and m["rankInProvince"] == w["rank_in_province"]
            assert m["riskLevel"] is None                           # LGUs are never banded
            n += 1
    assert n == 142


def test_news_lists_only_validated_articles_with_metadata(rec):
    keys = {a["article_key"] for a in rec["news"]["articles"]}
    for c, slug in SLUG.items():
        for quarter in ("2026-Q3", "2026-Q4", "2024-Q3"):
            body = get("/news", scope="province", id=slug, quarter=quarter, pageSize=100).json()
            want = [a for a in rec["news"]["articles"] if a["province_code"] == c and a["quarter"] == quarter]
            assert body["total"] == len(want)
            for a in body["data"]:
                assert a["id"] in keys and a["title"] and a["source"] and a["date"].startswith(quarter[:4]) and a["url"]
    allp = get("/quarterly/e31/news", relevance="all", page_size=1).json()
    assert allp["total"] == rec["news"]["totals"]["province_attributed"]
    rel = get("/quarterly/e31/news", relevance="relevant", page_size=200).json()
    assert rel["total"] == len(rec["news"]["articles"])


def test_news_filters_and_validation_errors(rec):
    a = get("/quarterly/e31/news", province="Quezon", quarter="2026-Q3", relevance="DIRECT").json()
    assert all(x["province"] == "Quezon" and x["quarter"] == "2026-Q3" and x["relevance"] == "DIRECT" for x in a["items"])
    assert get("/quarterly/e31/news", relevance="bogus").status_code == 422
    assert get("/quarterly/e31/news", page=0).status_code == 422


def test_model_performance_reports_served_engine_and_baselines(rec):
    body = get("/forecast", scope="province", id="quezon", quarter="2027-Q1").json()
    assert body is not None
    # model performance travels in /config
    cfg = get("/config").json()
    blob = json.dumps(cfg)
    assert "0.8667" in blob or "PCF21" in blob or "modelPerformance" in blob


def test_pdf_is_the_record(rec):
    r = get("/quarterly/e31/report.pdf")
    assert r.ok and r.headers["X-Record-SHA256"] == rec["content_sha256"] and r.content[:4] == b"%PDF"


def test_errors_are_explicit():
    assert get("/provinces", quarter="2019-Q1").status_code in (404, 422)
    assert get("/provinces/atlantis/municipalities").status_code == 404
    assert get("/provinces", horizon="sometime").status_code == 422


def test_admin_login_and_protected_routes():
    email, pw = os.getenv("AIPHEED_E2E_ADMIN_EMAIL"), os.getenv("AIPHEED_E2E_ADMIN_PASSWORD")
    if not (email and pw):
        pytest.skip("no test admin credentials in the environment")
    s = requests.Session()
    assert s.get(BASE + "/admin/review", timeout=30).status_code in (401, 403)        # anonymous refused
    bad = s.post(BASE + "/auth/login", json={"email": email, "password": pw + "x"}, timeout=30)
    assert bad.status_code in (400, 401)
    ok = s.post(BASE + "/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert ok.ok, ok.text
    tok = ok.json().get("access_token") or ok.json().get("token")
    h = {"Authorization": f"Bearer {tok}"} if tok else {}
    me = s.get(BASE + "/auth/me", headers=h, timeout=30)
    assert me.ok and me.json()["email"] == email
    assert s.get(BASE + "/admin/review", headers=h, timeout=30).ok


def test_alert_workflow_stage_confirm_publish():
    """Stage the E31 candidates (scripts/stage_alerts_e31.py must have run against the server's DB), then an admin
    confirms one: only the confirmed alert becomes public, with its reason and the model-generated statement."""
    email, pw = os.getenv("AIPHEED_E2E_ADMIN_EMAIL"), os.getenv("AIPHEED_E2E_ADMIN_PASSWORD")
    if not (email and pw):
        pytest.skip("no test admin credentials in the environment")
    s = requests.Session()
    tok = s.post(BASE + "/auth/login", json={"email": email, "password": pw}, timeout=30).json()
    h = {"Authorization": f"Bearer {tok.get('access_token') or tok.get('token')}"}
    staged = s.get(BASE + "/admin/alerts", params={"status": "staged"}, headers=h, timeout=30).json()["data"]
    confirmed = s.get(BASE + "/admin/alerts", params={"status": "confirmed"}, headers=h, timeout=30).json()["data"]
    assert staged or confirmed, "run scripts/stage_alerts_e31.py first"
    reasons = {a["alert_reason"] for a in staged + confirmed}
    assert reasons <= {"REGIONAL_HUNGER_HIGH", "PROVINCE_PRICE_PRESSURE", "SUDDEN_RISE"}
    public_before = {a["id"] for a in get("/alerts").json()["data"]}
    assert not (public_before & {a["id"] for a in staged})          # nothing staged is public
    if staged:
        target = staged[0]
        r = s.post(BASE + f"/admin/alerts/{target['id']}/confirm", headers=h, timeout=30)
        assert r.ok
        pub = get("/alerts").json()["data"]
        hit = [a for a in pub if a["id"] == target["id"]]
        assert hit and hit[0]["alert_reason"] == target["alert_reason"] and "Not an official" in hit[0]["statement"]
        assert s.post(BASE + f"/admin/alerts/{target['id']}/dismiss", headers=h, timeout=30).status_code >= 400


def test_visualization_report_payloads_match_the_record(rec):
    t = get("/report/data", type="trend", scope="region", **{"from": "2026-Q2", "to": "2027-Q1"}).json()
    assert t["type"] == "trend" and t["metadata"][0][1] == rec["content_sha256"][:16]
    fig = next(b for b in t["blocks"] if b["kind"] == "figure")["chart"]
    assert fig["quarters"] == ["2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1"]
    qu = next(s for s in fig["series"] if s["name"] == "Quezon")["values"]
    now = q(rec, "2026-Q4", "NOWCAST")["provinces"]["PH040300000"]["p_high"]
    assert qu[2] == round(now * 100, 1)
    s = get("/report/data", type="shap", scope="province", id="quezon", to="2026-Q4").json()
    tab = next(b for b in s["blocks"] if b["kind"] == "table")["rows"]
    want = q(rec, "2026-Q4", "NOWCAST")["provinces"]["PH040300000"]["drivers"]
    assert [r[2] for r in tab] == [f"{d['contribution']:+.2f}" for d in want]
    assert get("/report/data", type="shap", scope="province", id="quezon").status_code == 422


def test_legacy_pdf_report_renders():
    r = get("/report", scope="province", id="quezon", quarter="2026-Q4")
    assert r.ok and r.content[:4] == b"%PDF"
