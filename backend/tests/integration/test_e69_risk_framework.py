"""
tests/integration/test_e69_risk_framework.py
--------------------------------------------
E69 (aipheed-backend-aligned/experiments/E69_Food_Insecurity_Risk_Framework): the two-scale food-insecurity risk
framework and the opt-in e69 serving mode.

Evidence: protocol frozen; the regional hunger outcome is never filled; Lead-2 information sets use only rounds posted
before the issue date; no Scale-1 model beats the latest reading; the forward outlook is sealed. Tier rule: reproduced
from its components; a climate hazard alone is never ELEVATED. Serving: e69 numbers equal e58, the tier is served beside
(never instead of) the score, back-tests get no outlook, region and province views agree, 142 LGUs, E38 default.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2
from app.ml.inference import e69_disclosure as D69
from app.quarterly.target import forecast_target

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
E69 = ROOT / "aipheed-backend-aligned" / "experiments" / "E69_Food_Insecurity_Risk_Framework"
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}
COUNTS = {"batangas": 34, "cavite": 23, "laguna": 30, "quezon": 41, "rizal": 14}
needs = pytest.mark.skipif(not (E69 / "out" / "r2_province_fusion.json").exists(), reason="E69 outputs not present")


def _out(n):
    return json.loads((E69 / "out" / n).read_text(encoding="utf-8"))


def _t(n, d="tables"):
    return pd.read_csv(E69 / d / n, dtype={"province_code": str})


@pytest.fixture
def mode(monkeypatch):
    def set_mode(m):
        if m is None:
            monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
        else:
            monkeypatch.setenv("AIPHEED_LEAD2_MODEL", m)
        monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    return set_mode


def _summary(q, slug, scope="province"):
    r = client.get("/api/v1/explainability", params={"scope": scope, "id": slug, "quarter": q})
    assert r.status_code == 200, r.text[:300]
    return r.json()["summary"]


def _lib():
    sys.path.insert(0, str(E69 / "runner"))
    import e69_lib as K
    return K


# ------------------------------------------------------------------------------------------------ evidence
@needs
def test_protocol_frozen_and_outputs_carry_its_hash():
    K = _lib()
    sha = K.verify_protocol()
    for f in ("r1_regional_hunger.json", "r2_province_fusion.json"):
        assert _out(f)["protocol_sha256"] == sha
    assert D69.disclosure()["protocolSha256"] == sha


def test_outcome_never_filled_and_rounds_respect_publication():
    K = _lib()
    Y = K.outcome()
    assert K.L.qi("2022-Q1") not in Y.index                      # no 2022-Q1 round: absent, not 0
    r = pd.read_csv(K.L.SWS_FILE)
    # the information set of origin 2026-Q2 (issue 2026-07-01) cannot contain the 2026-Q2 round (posted 2026-08-24)
    d = K.L.load()
    hs = K.posted(d, K.L.qi("2026-Q2"))
    assert K.L.qi("2026-Q2") not in hs.index and K.L.qi("2026-Q1") in hs.index
    assert (pd.to_datetime(r["published"]) > pd.Timestamp("2021-01-01")).all()


@needs
def test_scale1_no_model_beats_latest_reading_and_rw_selected():
    o = _out("r1_regional_hunger.json")
    assert o["selected_for_scale2"] == "R0_RW" and o["eligible_quarters"] == 18
    P = _t("r1_paired_vs_RW.csv")
    assert not P["better_than_RW"].any()
    S = _t("r1_scores_all_available.csv").set_index("model")
    assert S.loc["R0_RW", "MAE"] > S.loc["R0_RW", "noise_floor_MAE"]
    assert int(S.loc["R0_RW", "E2_hits"]) == 0


@needs
def test_province_skill_measured_against_quarter_mean():
    S = _t("r2_province_skill.csv").set_index("reading")
    assert S.loc["A0", "correct"] == 36 and S.loc["A0-QMEAN", "correct"] == 32
    sk = _out("r2_province_fusion.json")["province_skill"]
    assert 15 < sk["n_eff"] < 50 and sk["A0_province_skill_demonstrable"]


@needs
def test_tier_rule_reproduces_from_components_and_climate_alone_is_not_elevated():
    T = _t("r2_tier_history.csv")
    T = pd.concat([T, _t("outlook_forward.csv", "sealed")])
    for r in T.itertuples():
        Hc, A, C = r.H_component, r.A_component, r.C_component
        X = (str(r.X_component) == "True")
        want = ("ELEVATED" if Hc and (A or (C and X)) else "WATCH" if Hc and C else "NO ELEVATED SIGNAL")
        assert r.tier == want
    w = T[T["tier"] == "WATCH"]
    assert (~w["A_component"].astype(bool)).all()               # WATCH never carries an affordability hazard


@needs
def test_forward_outlook_sealed():
    s = E69 / "sealed" / "outlook_forward.csv"
    want = (E69 / "sealed" / "outlook_forward.csv.sha256").read_text().split()[0]
    assert hashlib.sha256(s.read_bytes()).hexdigest() == want == _out("r2_province_fusion.json")["sealed_sha256"]
    S = pd.read_csv(s)
    assert set(S["target"]) == {"2026-Q4", "2027-Q1"} and len(S) == 10


# ------------------------------------------------------------------------------------------------ serving
def test_e69_numbers_equal_e58_and_outlook_beside_score(mode):
    mode("e58")
    base = {(q, c): _summary(q, s) for q in ("2027-Q1", "2026-Q4") for c, s in SLUG.items()}
    mode("e69")
    assert LEAD2.layered() and LEAD2.serves("2027-Q1") and not LEAD2.serves("2027-Q2")
    assert forecast_target("2026-10-20T09:00:00")["target_quarter"] == "2027-Q1"
    d = D69.disclosure()
    for (q, c), b in base.items():
        s = _summary(q, SLUG[c])
        name = LEAD2.record()["provinces"][c]["name"]
        assert s["probability"] == b["probability"] and s["result"] == b["result"] and s["components"] == b["components"]
        assert s["modelIdentity"]["servingMode"] == "e69"
        assert s["riskOutlook"]["tier"] == d["riskOutlook"][q][name]["tier"]
        assert "not a probability and not a validated provincial forecast" in s["sentence"]
        if s["result"] == "LOW" and s["riskOutlook"]["tier"] in ("ELEVATED", "WATCH"):
            assert "A LOW food-price score above does not mean low food-insecurity risk" in s["sentence"]
        rh = s["regionalHungerOutlook"]
        assert rh["geography"].startswith("Balance Luzon") and rh["interval80"][0] < rh["expectedHunger"] < rh["interval80"][1]
        assert s["vulnerabilityProfile"]["province"] == name


def test_region_view_matches_provinces_and_backtests_get_no_outlook(mode):
    mode("e69")
    reg = _summary("2027-Q1", "calabarzon", "region")
    tiers = reg["riskOutlook"]["tiers"]
    for c, slug in SLUG.items():
        assert tiers[LEAD2.record()["provinces"][c]["name"]] == _summary("2027-Q1", slug)["riskOutlook"]["tier"]
    assert _summary("2026-Q3", "quezon").get("riskOutlook") is None


def test_disclosure_missing_falls_back_to_e68(mode, monkeypatch, tmp_path):
    mode("e69")
    monkeypatch.setattr(D69, "DISCLOSURE", tmp_path / "none.json")
    s = _summary("2027-Q1", "rizal")
    assert s.get("riskOutlook") is None and s.get("inputStatus")


def test_e69_lgus_and_default(mode):
    mode("e69")
    rows = []
    for s in SLUG.values():
        data = client.get(f"/api/v1/provinces/{s}/municipalities", params={"quarter": "2027-Q1"}).json()["data"]
        assert len(data) == COUNTS[s] and all(r["provinceId"] == s for r in data)
        rows += data
    assert len({r["lguCode"] for r in rows}) == 142
    assert all(math.isfinite(r["riskIndex"]) and r["riskLevel"] in ("low", "moderate", "high") for r in rows)
    mode(None)
    assert LEAD2.mode() == "e38"
