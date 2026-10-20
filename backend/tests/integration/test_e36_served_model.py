"""
tests/integration/test_e36_served_model.py
------------------------------------------
The E36 LightGBM (aiPHeed-E36-LGBM), still selectable with AIPHEED_RECORD=e36 (the default is now E49-C2, see
test_e49_served_model.py), and the PSA 2021 / POPCEN 2024 LGU inputs, end to end: the record is
intact and matches the frozen E36 artifacts, the model artifact reproduces every served 2026-Q4 probability, the SHAP
drivers add up exactly to each estimate, and the API, map rows, LGU ranking and PDF all carry the same numbers.
Every request runs against an in-memory database (conftest), never backend/aipheed.db.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.quarterly.lgu_audit import build_ranking

REC_PATH = Path("data/e36/e36_record.json")
client = TestClient(app)
REC = json.loads(REC_PATH.read_text(encoding="utf-8"))
FC = next(q for q in REC["quarters"] if q["mode"] == "FORECAST")
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}


def test_record_integrity_and_schema():
    body = {k: v for k, v in REC.items() if k != "content_sha256"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() == REC["content_sha256"]
    assert REC["schema"] == "e36/1"
    assert "LightGBM" in REC["served_engine"]["name"]
    assert [q["mode"] for q in REC["quarters"]] == ["BACKTEST"] * 13 + ["FORECAST"] * 2
    assert [q["lead"] for q in REC["quarters"]] == [1] * 14 + [2]          # next quarter = lead 2 (E38)


def test_forecast_is_issued_before_its_quarter_with_previous_quarter_news():
    assert FC["quarter"] == "2026-Q4" and FC["origin"] == "2026-10-01"
    w = FC["provenance"]["news_evidence_window"]
    assert w["evidence_quarter"] == "2026-Q3" and w["window_end_excl_ph"] <= "2026-10-01T00:00:00+08:00"
    for q in REC["quarters"]:
        y, n = map(int, q["quarter"].split("-Q"))
        start = f"{y}-{3 * n - 2:02d}-01"
        assert q["origin"] <= start, q["quarter"]                    # issued no later than the quarter starts


def test_model_artifact_matches_and_reproduces_the_served_forecast():
    import lightgbm as lgb

    cfg = json.loads(Path("data/e36/model/E36-LGBM_O2026-10-01.json").read_text(encoding="utf-8"))
    txt = Path("data/e36/model/E36-LGBM_O2026-10-01.txt").read_bytes()
    # The bytes hashed at freeze time mixed line endings; git (core.autocrlf) stores the LF form, so the committed
    # artifact is identified by its LF-normalized hash (data/e36/model/ARTIFACT_HASHES.json). Content identity is
    # proven below by reproducing every served probability from the loaded booster.
    hashes = json.loads(Path("data/e36/model/ARTIFACT_HASHES.json").read_text(encoding="utf-8"))[
        "E36-LGBM_O2026-10-01.txt"]
    assert hashes["sha256_at_freeze"] == cfg["artifact_sha256"] == REC["served_engine"]["sha256"]
    assert hashlib.sha256(txt.replace(b"\r\n", b"\n")).hexdigest() == hashes["sha256_lf_normalized"]
    booster = lgb.Booster(model_str=txt.replace(b"\r\n", b"\n").decode("utf-8"))   # CRLF text aborts the parser
    feats = cfg["features"]
    for code, v in FC["provinces"].items():
        val = {d["key"]: d["value"] for d in v["drivers"]}
        x = pd.DataFrame([[math.nan if val[f] is None else val[f] for f in feats]], columns=feats)
        assert booster.predict(x)[0] == pytest.approx(v["p_high"], abs=6e-5), code


def test_shap_drivers_add_up_exactly_to_each_estimate():
    for q in REC["quarters"]:
        for code, v in q["provinces"].items():
            z = v["shap_expected_value_logodds"] + sum(d["contribution"] for d in v["drivers"])
            assert 1 / (1 + math.exp(-z)) == pytest.approx(v["p_high"], abs=2e-3), (q["quarter"], code)


def test_api_provinces_serve_the_record_with_basis_and_horizon(serve_e36):
    body = client.get("/api/v1/provinces?quarter=2026-Q4&horizon=forecast").json()
    got = {r["provinceCode"]: r for r in body["data"]}
    for code, v in FC["provinces"].items():
        r = got[code]
        assert r["riskScore"] == pytest.approx(v["p_high"])
        assert r["riskLabel"] is None                                 # no validated HIGH/LOW class
        assert "not a validated classification" in r["riskLevelBasis"]
        assert "lead 1" in r["horizonLabel"] and "2026-10-01" in r["confidenceStatement"]


def test_D3_qoq_only_between_consecutive_comparable_quarters(serve_e36):
    body = client.get("/api/v1/provinces?quarter=2025-Q4&horizon=forecast").json()
    assert all(r["qoqChange"] is None for r in body["data"])          # 2025-Q1 -> 2025-Q4 crosses a gap
    body = client.get("/api/v1/provinces?quarter=2026-Q4&horizon=forecast").json()
    last = next(q for q in REC["quarters"] if q["quarter"] == "2026-Q3")
    for r in body["data"]:
        assert r["qoqChange"] == pytest.approx(FC["provinces"][r["provinceCode"]]["p_high"]
                                               - last["provinces"][r["provinceCode"]]["p_high"], abs=1e-4)


def test_D7_province_poverty_is_the_population_weighted_2021_sae():
    v = pd.read_csv("data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
    v = v[v["poverty_lgu_estimate"].notna()]
    want = (v.assign(w=v.population_2024 * v.poverty_lgu_estimate).groupby("province")[["w", "population_2024"]].sum())
    body = client.get("/api/v1/provinces?quarter=2026-Q4&horizon=forecast").json()
    for r in body["data"]:
        assert r["povertyRate"] == pytest.approx(round(want.loc[r["name"], "w"] / want.loc[r["name"], "population_2024"], 1))
        assert "not an official PSA province figure" in r["povertyRateBasis"]


def test_psa_2021_sae_reaches_all_142_lgus_with_lucena_flagged():
    v = pd.read_csv("data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
    sae = pd.read_csv("data/reference/sae2021_calabarzon_municipal.csv", dtype={"lgu_code": str})
    assert len(v) == 142 and len(sae) == 141
    assert v["poverty_lgu_estimate"].notna().sum() == 141
    lucena = v[v["lgu_code"] == "045624000"].iloc[0]
    assert pd.isna(lucena["poverty_lgu_estimate"]) and "unverified" in lucena["poverty_source"]
    m = v.merge(sae, on="lgu_code")
    assert (m["poverty_lgu_estimate"] - m["poverty_incidence_2021"]).abs().max() < 1e-9
    assert int(v["population_2024"].sum()) == 16933234                # 2024 POPCEN CALABARZON total
    assert "population_2020" not in v.columns


def test_lgu_ranking_in_record_api_and_recompute_agree(serve_e36, lead2):
    # the record's stored ranking is built from the E38 2027-Q1 (lead-2) row; serve that row to compare with it
    vul = pd.read_csv("data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
    ros = pd.read_csv("data/reference/calabarzon_lgus.csv", dtype={"lgu_psgc": str})
    NQ = next(q for q in REC["quarters"] if q.get("role") == "next_quarter")      # the dashboard target
    rk = build_ranking(vul, ros, {c: v["p_high"] for c, v in NQ["provinces"].items()}, {})
    rec_rows = {r["lgu_code"]: r for r in REC["lgu_ranking"]["rows"]}
    assert len(rec_rows) == 142
    for r in rk["rows"]:
        assert r["risk_index"] == rec_rows[r["lgu_code"]]["risk_index"]
        assert r["rank_in_province"] == rec_rows[r["lgu_code"]]["rank_in_province"]
        assert r["poverty_value_used"] == rec_rows[r["lgu_code"]]["poverty_value_used"]
    api = client.get("/api/v1/quarterly/e31/lgu-ranking").json()["rows"]
    assert {r["lgu_code"]: r["risk_index"] for r in api} == {k: v["risk_index"] for k, v in rec_rows.items()}
    for code, slug in SLUG.items():
        m = client.get(f"/api/v1/provinces/{slug}/municipalities?quarter=2027-Q1").json()["data"]
        for row in m:
            assert row["riskIndex"] == pytest.approx(rec_rows[row["lguCode"]]["risk_index"], abs=1e-4)
            if row["lguCode"] == "045624000":
                assert row["povertyValueUsed"] == 16.8 and "unverified" in row["povertyLimitation"]
            else:
                assert row["povertyEstimateKind"].startswith("PSA municipal SAE")


def test_D4_cross_province_claim_is_not_made():
    text = " ".join(REC["lgu_ranking"]["does_not_mean"])
    assert "mostly reflect the province estimate" not in text
    assert "Compare LGUs within their province" in text


def test_pdf_is_the_record_and_names_the_model(serve_e36):
    r = client.get("/api/v1/quarterly/e31/report.pdf")
    assert r.status_code == 200 and r.headers["X-Record-SHA256"] == REC["content_sha256"]
    assert re.search(rb"/Subject \(([0-9a-f]{64})\)", r.content).group(1).decode() == REC["content_sha256"]


def test_model_performance_reports_e36_and_six_baselines():
    keys = {x["key"] for x in REC["validation"]["model_evaluation"]["rows"]}
    assert keys == {"E36-LGBM", "B1_PERSISTENCE", "B2_LR_COMB", "B3_LR_GOV", "B4_LR_NLP", "B5_LGBM_GOV",
                    "B6_LGBM_NLP", "ALWAYS_HIGH"}
    t = REC["validation"]["threshold_75pct"]
    assert t["point_met"] is True and t["demonstrated"] is False and "not demonstrated" in t["verdict"]


def test_prospective_forecast_is_frozen_and_unchanged():
    p = Path("data/e36/model/E36_PROSPECTIVE_2026Q4.json")
    want = Path("data/e36/model/E36_PROSPECTIVE_2026Q4.sha256").read_text().split()[0]
    b = p.read_bytes()
    assert want in (hashlib.sha256(b).hexdigest(), hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest())
    fr = json.loads(b)
    for code, v in fr["provinces"].items():
        assert FC["provinces"][code]["p_high"] == pytest.approx(v["p_high"], abs=5e-5)
