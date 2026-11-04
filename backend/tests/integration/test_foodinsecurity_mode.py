"""
tests/integration/test_foodinsecurity_mode.py
---------------------------------------------
AIPHEED_MAP_MODEL=foodinsecurity (app.ml.inference.foodinsecurity_system; FOOD_INSECURITY_SYSTEM/PLAN.md revision 4):
the regional C-b forecast (IMPROVE_V2 reference inputs + the FSSI anomaly; NEW_MODEL/NEWS_V2) of SWS hunger above
11.3% sets every province's class and colour; the texts state that its NLP input changes no classification; the province score
weights it by PSA 2023 poverty among families and never changes the class; the P0H4 price band, PSA food poverty and the
news sentences and flag are context only; LGUs are ranked 0.6 poverty + 0.4 density within the province (Lucena: its own
PSA Table 2a value); only Leads 1-2 are served (Maximum Reliable Lead Time 2 under the paper's 75% rule; R1-R7 fail);
issued forecasts stay STAGED until approved (Rule 1); HIGH forecasts and province news flags are staged for human
confirmation, never notified automatically (Rule 7); the ch1 and FIRI modes and the default are unchanged.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1
from app.ml.inference import foodinsecurity_system as FI
from app.ml.inference import served_risk as SR

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "aipheed-backend-aligned" / "experiments"
SLUGS = ("cavite", "laguna", "quezon", "rizal", "batangas")
RUNNER = EXP / "FOOD_INSECURITY_SYSTEM" / "runner"
CB = EXP / "NEW_MODEL" / "NEWS_V2"


@pytest.fixture
def fi(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-26T09:00:00")
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "foodinsecurity")
    monkeypatch.setattr(FI, "DATA", FI.CB_DATA)                 # these tests check C-b's own export (previous main model)
    monkeypatch.setattr(FI, "LGU_VULNERABILITY", FI.CB_DATA / "lgu_vulnerability.csv")
    return monkeypatch


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _rows() -> pd.DataFrame:
    return pd.read_csv(FI.DATA / "rows.csv", dtype={"province_code": str})


def _export_module():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("export_fi_under_test", RUNNER / "export_fi.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------------------------- the export
def test_rows_are_the_cb_forecasts_and_the_official_p0h4_price_part(fi):
    F = pd.read_csv(CB / "out" / "forecasts.csv")
    F = F[F["name"] == "C-b"].set_index(["t", "lead"])["p"]
    lab = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "labels_areas.csv")
    lab = lab[lab["area"] == "BL"].set_index("q")["y"]
    c = pd.read_csv(CH1.DATA / "rows.csv", dtype={"province_code": str})
    price = c.set_index(["province_code", "quarter", "lead", "issue_date"])["pi_price"]
    for (code, q), r in FI.rows().items():
        qi = int(q[:4]) * 4 + int(q[-1]) - 1
        t, k = qi - int(r["lead"]), int(r["lead"])
        assert float(r["probability"]) == pytest.approx(F[(t, k)], abs=1e-6)
        assert float(r["pi_price"]) == pytest.approx(float(price[(code, q, k, r["issue_date"])]), abs=1e-6)
        if r["observed"]:
            assert (r["observed"] == "HIGH") == bool(lab[qi])
    assert {r["model"] for r in FI.rows().values()} == {"NEWS_V2-CB"}


def test_one_regional_probability_per_quarter_and_nothing_beyond_lead_2(fi):
    R = _rows()
    assert R.groupby("quarter")["probability"].nunique().max() == 1      # the classification is regional
    assert R["lead"].max() == 2 and set(R["lead"]) == {1, 2}
    assert set(R[R["lead"] == 2]["quarter"]) == {"2027-Q1"}
    assert (R["class"] == R["probability"].ge(0.5).map({True: "HIGH", False: "LOW"})).all()


def test_max_reliable_lead_is_two_under_the_75_rule_and_zero_under_r1_r7(fi):
    ev = FI.evaluation()
    res = json.loads((CB / "out" / "results_cb.json").read_text(encoding="utf-8"))
    assert ev["max_reliable_lead"] == res["max_reliable_lead_alg3"] == 2
    assert ev["max_reliable_lead_r1_r7"] == res["max_reliable_lead_R1_R7"] == 0
    assert ev["leads"]["1"]["alg3_pass"] and ev["leads"]["2"]["alg3_pass"] and not ev["leads"]["3"]["alg3_pass"]
    assert ev["leads"]["3"]["metrics"]["accuracy"] < 0.75 <= ev["leads"]["2"]["metrics"]["accuracy"]
    assert ev["sources"]["reproduced"] is True
    h = _get("/api/v1/final/risk/rows")
    assert h["maxReliableLead"] == 2 and max(int(r["lead"]) for r in h["rows"]) == 2


def test_sealed_lead2_forecast_is_the_served_one(fi):
    path = CB / "sealed_prospective_CB.csv"
    seal = pd.read_csv(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest.startswith("67baec66")
    l2 = seal[seal["lead"] == 2].iloc[0]
    assert l2["target_quarter"] == "2027-Q1"
    for code in CH1_CODES():
        r = FI.row(code, "2027-Q1")
        assert float(r["probability"]) == pytest.approx(float(l2["p_high"]), abs=1e-6)
        assert r["seal_sha256"] == digest


def CH1_CODES():
    return sorted({c for c, _ in FI.rows()})


def test_export_refuses_a_changed_plan(fi, tmp_path):
    m = _export_module()
    assert m.check_plan() == FI.evaluation()["plan_sha256"]
    bad = tmp_path / "PLAN.md"
    bad.write_bytes(m.PLAN.read_bytes().replace(b"Revision 2", b"Revision X", 1))
    m.PLAN = bad
    with pytest.raises(AssertionError, match="changed"):
        m.check_plan()


# ---------------------------------------------------------------------------------------------- province score
def test_scores_differ_by_province_and_the_poorest_equals_the_regional_probability(fi):
    R = _rows()
    pov = {p["province_code"]: p["pov_families_2023"] for p in FI.evaluation()["province_poverty"]}
    top = max(pov, key=pov.get)
    for q, g in R.groupby("quarter"):
        assert g["score"].nunique() == 5
        for r in g.itertuples():
            assert r.score == pytest.approx(r.probability * pov[r.province_code] / max(pov.values()), abs=1e-6)
        assert g.loc[g["province_code"] == top, "score"].iloc[0] == pytest.approx(g["probability"].iloc[0], abs=1e-6)


def test_class_and_colour_are_regional_even_when_the_score_is_below_half(fi):
    R = _rows()
    q = next(q for q, g in R.groupby("quarter")
             if g["probability"].iloc[0] >= 0.5 and (g["score"] < 0.5).any() and q < "2026-Q4")
    d = _get("/api/v1/provinces", quarter=q)
    assert any(x["riskScore"] < 0.5 for x in d["data"])
    assert {x["riskLevel"] for x in d["data"]} == {"high"}                # never lowered by the weighting
    assert [x["riskScore"] for x in d["data"]] == sorted((x["riskScore"] for x in d["data"]), reverse=True)
    lgus = [x for s in SLUGS for x in _get(f"/api/v1/provinces/{s}/municipalities", quarter=q)["data"]]
    assert len(lgus) == 142 and {x["riskLevel"] for x in lgus} == {"high"}
    assert all(x["riskLevelBasis"] == FI.LGU_LEVEL_BASIS for x in lgus)


def test_price_band_follows_the_cuts_and_changes_nothing(fi):
    R = _rows()
    for r in R.itertuples():
        assert r.price_band == ("Low" if r.pi_price < 0.33 else "Medium" if r.pi_price < 0.67 else "High")
    a = FI.row("PH040300000", "2026-Q3")
    b = {**a, "pi_price": "0.95", "price_band": "High"}
    assert FI.score(a) == FI.score(b) and FI.is_high(a) == FI.is_high(b) and FI._priority(a) == FI._priority(b)
    assert "food-price pressure: High (P0H4 price part 0.95; context, does not change the score)" in \
        FI.province_context(b)
    assert R.groupby(["province_code"])["price_band"].nunique().max() > 1   # province information changes over time


def test_food_poverty_low_precision_clause_only_above_30_cv(fi):
    for p in FI.evaluation()["province_poverty"]:
        r = FI.row(p["province_code"], "2026-Q3")
        t = FI.food_poverty_text(r)
        assert ("low precision (CV > 30%)" in t) == (p["food_pov_2023_cv"] > 30)
        assert "not used for ranking" in t
    assert "low precision" not in FI.food_poverty_text(FI.row("PH040400000", "2026-Q3"))   # Rizal, CV 24.5


# ---------------------------------------------------------------------------------------------- LGUs
def test_lucena_carries_its_own_table_2a_value_and_citation(fi):
    lu = FI.evaluation()["lucena"]
    assert lu["own"] and lu["value"] == 10.0 and "Table 2a" in lu["source"] and "0041F3DF02A" in lu["url"]
    v = pd.read_csv(FI.LGU_VULNERABILITY, dtype={"lgu_code": str})
    raw = pd.read_csv(ROOT / "backend" / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    assert v.loc[v["lgu_code"] == FI.LUCENA, "poverty_value_used"].iloc[0] == 10.0
    assert raw.loc[raw["lgu_code"] == FI.LUCENA, "poverty_value_used"].iloc[0] == 16.8   # the input is not edited
    assert v.drop(columns=["poverty_lgu_estimate", "poverty_cv", "poverty_source", "poverty_value_used"]).equals(
        raw.drop(columns=["poverty_lgu_estimate", "poverty_cv", "poverty_source", "poverty_value_used"]))
    lgus = _get("/api/v1/provinces/quezon/municipalities", quarter="2026-Q3")["data"]
    x = next(x for x in lgus if x["lguCode"] == FI.LUCENA)
    assert x["povertyValueUsed"] == 10.0 and "Table 2a" in x["povertyEstimateKind"]
    assert "City of Lucena" in x["povertyLimitation"]


def test_lgu_index_is_06_poverty_04_density_within_province_times_the_province_score(fi):
    q = "2026-Q3"
    v = pd.read_csv(FI.LGU_VULNERABILITY, dtype={"lgu_code": str})
    v["density"] = v["population_2024"] / v["land_area_km2"]
    n = lambda s: (s - s.min()) / (s.max() - s.min())  # noqa: E731
    v["idx"] = v.groupby("province")["poverty_value_used"].transform(n) * 0.6 + \
        v.groupby("province")["density"].transform(n) * 0.4
    score = {r["province"]: float(r["score"]) for (_, qq), r in FI.rows().items() if qq == q}
    got = {x["lguCode"]: x["riskIndex"] for s in SLUGS
           for x in _get(f"/api/v1/provinces/{s}/municipalities", quarter=q)["data"]}
    for r in v.itertuples():
        exact = round(score[r.province] * r.idx, 4)
        shown = math.floor(exact * 100) / 100 if 0.495 <= exact < 0.5 else exact   # dashboard._shown
        assert got[r.lgu_code] == pytest.approx(shown, abs=1.5e-4)


# ---------------------------------------------------------------------------------------------- news
def _flag_case(history: list[float], now: float, n: int, family: str = "DISASTER"):
    m = _export_module()
    t0 = 2024 * 4
    rows = []
    for i, x in enumerate(history + [now]):
        r = {"t": t0 + i, "province_code": "PH040100000", "gp_logn": math.log1p(n)}
        for f in m.ALL_FAMILIES:
            r[f"gp_share_{f}"] = x if f == family else 0.2
        rows.append(r)
    return m.province_news(pd.DataFrame(rows), "PH040100000", t0 + len(history))


def test_news_flag_rule_on_synthetic_inputs(fi):
    base = [0.30, 0.32, 0.31, 0.29, 0.30, 0.31, 0.30, 0.32]
    assert _flag_case(base, 0.45, 100)["news_flag"] is True
    assert _flag_case(base, 0.33, 100)["news_flag"] is False                     # under 5 points
    assert "too few province articles" in _flag_case(base, 0.45, 19)["province_news_text"]
    assert "not enough news history" in _flag_case(base[:5], 0.45, 100)["province_news_text"]
    assert _flag_case(base[:6], 0.45, 100)["news_flag"] is True                  # 6 quarters is enough
    assert _flag_case(base, 0.90, 100, family="RESPONSE")["news_flag"] is False  # RESPONSE never flags
    noisy = [0.10, 0.50, 0.12, 0.48, 0.11, 0.52, 0.10, 0.49]
    assert _flag_case(noisy, 0.45, 100)["news_flag"] is False                    # under 1.5 sd


def test_news_flags_are_never_named_in_public_text(fi):
    """PLAN section 8.1: the flag lives in rows.csv and the staged alert candidates only."""
    assert any(FI.is_flagged(r) for r in FI.rows().values())
    assert not any("flag" in r["province_news_text"] for r in FI.rows().values())
    for q in ("2026-Q3", "2025-Q4"):
        for s in ("quezon", "cavite"):
            e = _get("/api/v1/explainability", scope="province", id=s, quarter=q)
            f = _get("/api/v1/forecast", scope="province", id=s, quarter=q)
            text = json.dumps([e, f])
            assert "early-warning flag" not in text and "news flag" not in text
        assert "news flag" not in json.dumps(_get("/api/v1/provinces", quarter=q))


def test_strict_rule_is_report_only(fi):
    out = RUNNER.parent / "out" / "strict_flag.json"
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["rule"] == {"z_min": 2.0, "rise_min": 0.1, "min_articles": 30}
    assert res["plan_sha256"] == FI.evaluation()["plan_sha256"]
    assert res["strict_subset_of_served"] is True
    assert "strict" not in (FI.DATA / "rows.csv").read_text(encoding="utf-8").splitlines()[0]   # not served


def test_news_never_changes_score_class_or_rank(fi):
    a = FI.row("PH040100000", "2026-Q3")
    b = {**a, "news_flag": "False" if FI.is_flagged(a) else "True", "province_news_text": "x"}
    assert FI.score(a) == FI.score(b) and FI.is_high(a) == FI.is_high(b) and FI._priority(a) == FI._priority(b)


# ---------------------------------------------------------------------------------------------- text fields
def test_summary_and_note_carry_the_honest_context(fi):
    e = _get("/api/v1/explainability", scope="province", id="quezon", quarter="2026-Q3")
    s = e["summary"]["sentence"]
    assert "past forecast; actual: HIGH" in s
    assert "latest SWS Balance Luzon hunger reading 22.4% (2026-Q1" in s
    assert "classification is regional, the province score weights it by PSA poverty and never changes the class" in s
    assert "province score 0.80" in s and "food-price pressure: Medium" in s and "Province news (GDELT" in s
    assert "passes the paper's 75% accuracy rule" in s and "fails the stricter reliability rules R1-R7" in s
    assert "NLP input (FSSI anomaly) is included" in s and "changed 0 of 62 classifications" in s
    assert ". " not in s.rstrip(".").replace("0.", "0_")                          # one sentence: only the first is shown
    assert FI.REGIONAL in e["note"]
    assert "19.1% of CALABARZON households" in e["note"] and "95% CI 17.0-21.1" in e["note"]
    assert "19.1%" in e["summary"]["caveat"] and "changes no classification" in e["summary"]["caveat"]
    assert e["summary"]["components"]["combination"].startswith("not combined")
    assert e["summary"]["probability"] == pytest.approx(float(FI.row("PH040300000", "2026-Q3")["probability"]), abs=1e-4)
    t = {x["key"]: x for x in e["triggers"]}
    assert set(t) == set(FI.SHOWN_GROUPS) and sum(x["pct"] for x in e["triggers"]) + e["otherPct"] == 100
    assert t["employment"]["status"] == t["ofw_remittance"]["status"] == "no_model_input"
    assert "same for every province" in t["market"]["evidenceNote"]
    assert "Medium" in t["market"]["plainEvidence"]


def test_reliability_text_names_both_rules(fi):
    r = FI.row("PH040300000", "2026-Q3")
    t = FI.reliability_text(r)
    assert "75% accuracy rule" in t and "R1-R7" in t and "R7 (stability)" in t and "0.790" in t
    assert "changed 0 of 62 classifications" in t                     # the NLP input's effect, stated, not hidden
    assert "Maximum Reliable Lead Time 2" in FI.model_line() and "0 under the stricter rules R1-R7" in FI.model_line()
    assert FI.model_line().startswith("C-b:")


def test_driver_bars_are_the_same_for_every_province(fi):
    a = {x["key"]: x["pct"] for x in _get("/api/v1/explainability", scope="province", id="cavite",
                                          quarter="2026-Q3")["triggers"]}
    b = {x["key"]: x["pct"] for x in _get("/api/v1/explainability", scope="province", id="rizal",
                                          quarter="2026-Q3")["triggers"]}
    assert a == b


def test_reports_describe_the_food_insecurity_forecast(fi):
    import io

    pl = _get("/api/v1/report/data", type="trend", scope="province", id="quezon", **{"from": "2023-Q1", "to": "2026-Q3"})
    text = json.dumps(pl)
    assert "regional SWS hunger (Balance Luzon) is above 11.3%" in text and "19.1%" in text
    assert "FIRI" not in text and "P0H4: P(HIGH)" not in text
    assert dict(pl["metadata"])["Model"] == FI.model_line()
    r = client.get("/api/v1/report", params={"scope": "province", "id": "quezon", "quarter": "2026-Q3"})
    if r.status_code in (401, 403):
        pytest.skip("report PDF is guarded in this configuration")
    assert r.status_code == 200, r.text[:300]
    from pdfminer.high_level import extract_text

    pdf = " ".join(extract_text(io.BytesIO(r.content)).split())
    assert "FIRI" not in pdf and "Maximum Reliable Lead Time 2" in pdf


# ---------------------------------------------------------------------------------------------- Rule 1
def test_issued_forecasts_are_staged_until_approved(fi):
    for q in ("2026-Q4", "2027-Q1"):
        d = _get("/api/v1/provinces", quarter=q)
        assert all(x["withheld"] and x["riskScore"] is None for x in d["data"])
    r = client.get("/api/v1/explainability", params={"scope": "province", "id": "quezon", "quarter": "2027-Q1"})
    assert r.status_code == 404 and "STAGED" in r.json()["error"]["message"]
    r = client.get("/api/v1/forecast", params={"scope": "province", "id": "quezon", "quarter": "2027-Q1"})
    assert r.status_code == 404
    assert not any(x["withheld"] for x in _get("/api/v1/provinces", quarter="2026-Q3")["data"])   # past: not gated


def test_unapproved_pairs_exclude_approved_forecasts(fi):
    every = FI.unapproved_pairs(set())
    assert every == {(s, q) for s in SLUGS for q in ("2026-Q4", "2027-Q1")}
    assert FI.unapproved_pairs({("quezon", "2027-Q1")}, "2027-Q1") == {(s, "2027-Q1") for s in SLUGS if s != "quezon"}


async def test_an_approved_forecast_is_public_and_flags_high_for_confirmation(fi, client, test_db):
    from sqlalchemy import select

    from app.db.models import ReviewRecord
    from app.services import review as rv

    await rv.ensure_rows(test_db, "2027-Q1")
    rows = (await test_db.execute(select(ReviewRecord).where(ReviewRecord.quarter == "2027-Q1"))).scalars().all()
    assert len(rows) == 5 and {r.status for r in rows} == {rv.STAGED}
    assert len(await rv.rejected_pairs(test_db, "2027-Q1")) == 5
    for r in rows:
        r.status = rv.PUBLISHED
    await test_db.commit()
    assert await rv.rejected_pairs(test_db, "2027-Q1") == set()
    d = (await client.get("/api/v1/provinces", params={"quarter": "2027-Q1"})).json()
    assert all(not x["withheld"] and x["riskScore"] is not None for x in d["data"])
    assert {x["riskLevel"] for x in d["data"]} == {"high"}
    f = (await client.get("/api/v1/forecast", params={"scope": "province", "id": "quezon", "quarter": "2027-Q1"})).json()
    assert "flagged for human confirmation" in f["confidenceStatement"]
    assert "no notification is sent to DSWD" in f["confidenceStatement"]


# ---------------------------------------------------------------------------------------------- Rule 7
async def test_high_forecasts_and_news_flags_are_staged_alert_candidates_never_notified(fi, test_db):
    c = FI.alert_candidates()
    regional = [x for x in c if x["alert_reason"] == FI.ALERT_REASON]
    news = [x for x in c if x["alert_reason"] == FI.NEWS_ALERT_REASON]
    assert [x["quarter"] for x in regional] == ["2026-Q4", "2027-Q1"]           # both regional forecasts are HIGH
    assert {x["province_code"] for x in regional} == {FI.REGION_CODE}           # one regional alert, not five
    flagged = {(c_, q) for (c_, q), r in FI.rows().items() if FI.kind(r) == "forecast" and FI.is_flagged(r)}
    assert {(x["province_code"], x["quarter"]) for x in news} == flagged
    assert all("no notification is sent to DSWD" in x["statement"] for x in c)
    first = await FI.stage_alerts(test_db)
    again = await FI.stage_alerts(test_db)
    assert len(first["staged"]) == len(c) and len(again["existing"]) == len(c) and not again["staged"]
    from app.db.repository.alert_repo import AlertRepository

    repo = AlertRepository(test_db)
    assert len(await repo.get_staged()) == len(c) and await repo.get_confirmed() == []   # nothing public until confirmed


def test_nothing_sends_a_notification(fi):
    src = (Path(FI.__file__)).read_text(encoding="utf-8")
    assert "mailer" not in src and "send_email" not in src and "smtplib" not in src


# ---------------------------------------------------------------------------------------------- other modes unchanged
def test_dispatcher_serves_ch1_and_firi_unchanged(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.delenv("AIPHEED_MAP_MODEL", raising=False)                       # default: FIRI v2
    assert SR.engine() is CH1 and not SR.active() and SR.key() == ""
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "ch1")
    assert SR.engine() is CH1 and SR.active() and SR.key() == ""
    from app.services import dashboard as svc
    assert "+ch1" in svc._lead2_key() and "+fi" not in svc._lead2_key()
    assert svc._lgu_vulnerability_path() == svc.LGU_PROVENANCE_PATH             # ch1 keeps the input file
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "foodinsecurity")
    assert SR.engine() is FI and "+ch1+fi" in svc._lead2_key()
    assert svc._lgu_vulnerability_path() == FI.LGU_VULNERABILITY


def test_default_mode_is_still_firi_and_review_gate_is_off(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-26T09:00:00")
    monkeypatch.delenv("AIPHEED_MAP_MODEL", raising=False)
    assert not FI.active()
    d = _get("/api/v1/provinces", quarter="2027-Q1")
    assert d["indicator"]["id"] != "regional_food_insecurity_forecast"
    assert not any(x["withheld"] for x in d["data"])


def test_ch1_mode_still_serves_the_chapter1_probability(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-26T09:00:00")
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "ch1")
    d = _get("/api/v1/provinces", quarter="2027-Q1")
    assert d["indicator"]["id"] == "chapter1_food_insecurity_risk"
    for r in d["data"]:
        code = {v["province"]: k for (k, qq), v in CH1.rows().items() if qq == "2027-Q1"}[r["name"]]
        assert r["riskScore"] == pytest.approx(float(CH1.row(code, "2027-Q1")["probability"]), abs=0.01)
    lu = next(x for x in _get("/api/v1/provinces/quezon/municipalities", quarter="2027-Q1")["data"]
              if x["lguCode"] == FI.LUCENA)
    assert lu["povertyEstimateKind"] == "province substitute (no municipal estimate)"   # ch1 LGU inputs unchanged
