"""
tests/integration/test_e68_resolve_e67.py
-----------------------------------------
E68 (aipheed-backend-aligned/experiments/E68_Resolve_E67_Critical_Failures): corrections for E67's failures and the
opt-in e68 serving mode.

Evidence: protocol frozen; A0 reproduces E57; target construction and thresholds; T-AFF definition; no correction beats
A0 by the rule; prospective seal intact. Missing/stale handling and the input-status classification. Climate timing
(K1 acts only with a PAGASA El Nino status in force before the issue date). Serving: e68 numbers equal e58, identity,
LOW-under-watch text, affordability, input status, 142 LGUs, production default unchanged.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import climate_watch as CW
from app.ml.inference import e41_lead2 as LEAD2
from app.ml.inference import e68_disclosure as D68
from app.quarterly.target import forecast_target

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
E68 = ROOT / "aipheed-backend-aligned" / "experiments" / "E68_Resolve_E67_Critical_Failures"
E40_SPEC = ROOT / "aipheed-backend-aligned" / "experiments" / "E40_SWS_CPI_Tiers" / "label_spec.json"
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}
COUNTS = {"batangas": 34, "cavite": 23, "laguna": 30, "quezon": 41, "rizal": 14}
STATUSES = {"observed", "observed_zero", "missing", "stale", "substituted", "too_few_articles", "not_collected"}
needs_e68 = pytest.mark.skipif(not (E68 / "out" / "r3_score.json").exists(), reason="E68 outputs not present")


def _out(n):
    return json.loads((E68 / "out" / n).read_text(encoding="utf-8"))


def _t(n):
    return pd.read_csv(E68 / "tables" / n, dtype={"province_code": str})


@pytest.fixture
def mode(monkeypatch):
    def set_mode(m):
        if m is None:
            monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
        else:
            monkeypatch.setenv("AIPHEED_LEAD2_MODEL", m)
        monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    return set_mode


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _summary(q, slug, scope="province"):
    return _get("/api/v1/explainability", scope=scope, id=slug, quarter=q)["summary"]


def _lib():
    sys.path.insert(0, str(E68 / "runner"))
    import e68_lib as R
    return R


# ------------------------------------------------------------------------------------------------ evidence
@needs_e68
def test_protocol_frozen_and_a0_reproduces_e57():
    R = _lib()
    sha = R.verify_protocol()
    for f in ("r1_arms.json", "r2_diagnostics.json", "r3_score.json"):
        assert _out(f)["protocol_sha256"] == sha
    assert _out("r1_arms.json")["A0_vs_E57_max_abs_diff"] < 1e-9


@needs_e68
def test_target_construction_and_thresholds():
    spec = json.loads(E40_SPEC.read_text())["thresholds"]
    L = _t("r2_labels_all.csv")
    names = {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000",
             "Batangas": "PH040500000"}
    thF = L["province"].map(names).map(spec["food"])
    thG = L["province"].map(names).map(spec["gap"])
    ps = ((L["F"] > thF) | ((L["F"] - L["HL"]) > thG)).astype(int)
    assert (ps == L["PS"]).all()
    assert (L["T43"] == ((L["H_all"] > spec["H"]) & (L["PS"] == 1)).astype(int)).all()
    R = _lib()
    thH = L["province"].map(names).map(R.HEADLINE_P60)
    assert (L["PS_AFF"] == ((L["F"] > thF) | (L["HL"] > thH)).astype(int)).all()
    assert (L["TAFF"] == ((L["H_all"] > spec["H"]) & (L["PS_AFF"] == 1)).astype(int)).all()
    hp = _out("r1_arms.json")["headline_p60"]
    assert all(abs(hp[p] - v) < 1e-5 for p, v in R.HEADLINE_P60.items())     # frozen 2021-22 P60, recomputed
    d = _out("r2_diagnostics.json")["target"]
    assert d["eval_T43_eq_PS"] == 50 and d["eval_rows"] == 50 and d["eval_quarters"] == 10


@needs_e68
def test_no_correction_beats_a0_and_goal_not_met():
    P = _t("r3_t43_paired_vs_A0.csv")
    assert not P["better_than_A0_by_rule"].any()
    T = _t("r3_t43_arms.csv").set_index("reading")
    assert int(T.loc["A0", "correct"]) == 36
    assert not T["goal_met"].any()                          # G4 is never met on examined rows
    TA = _t("r3_taff_arms.csv").set_index("reading")
    assert TA.loc["TAFF-LGBM", "recall_HIGH"] == 0          # degenerate on its own target: reported, not adopted


@needs_e68
def test_prospective_seal_intact():
    s = E68 / "sealed" / "prospective.csv"
    want = (E68 / "sealed" / "prospective.csv.sha256").read_text().split()[0]
    assert hashlib.sha256(s.read_bytes()).hexdigest() == want == _out("r3_score.json")["sealed_sha256"]
    S = pd.read_csv(s)
    assert set(S["target"]) == {"2026-Q4", "2027-Q1"}
    assert set(S["arm"]) == {"A0", "M1", "N1", "K1", "C1", "TAFF", "TAFF-RULE"}
    assert S["p"].between(0, 1).all()


# ------------------------------------------------------------------------------------------------ missing / stale
def test_missing_and_thin_inputs_become_nan_not_zero():
    R = _lib()
    X = pd.DataFrame({"t": [8100, 8104, 8105], "news_n": [5, 30, 12], "tc_count": [0.0, 1.0, 0.0],
                      **{c: [0.0, 0.2, 0.0] for c in R.NEWS_SHARES}})
    X.loc[2, "t"] = R.L.qi("2026-Q3")
    M = R.missing_X(X)
    assert M.loc[0, R.NEWS_SHARES].isna().all()            # 5 titles: too few, unknown
    assert (M.loc[1, R.NEWS_SHARES] == 0.2).all()
    assert (M.loc[2, R.NEWS_SHARES] == 0.0).all()          # 12 titles, none on the trigger: observed zero
    assert math.isnan(M.loc[2, "tc_count"]) and M.loc[1, "tc_count"] == 1.0   # incomplete quarter -> unknown


def test_input_status_classifies_stale_missing_and_placeholder():
    sys.path.insert(0, str(E68 / "runner"))
    import r4_build_disclosure as B
    R = _lib()
    row = pd.Series({"F_now": 3.0, "gap_now": -2.0, "rice_whsl_yoy": np.nan, "H_last": 15.0, "H_age": 2.0,
                     "tc_count": 0.0, "enso": 1.0, "palay_yoy": 1.0, "corn_yoy": 2.0, "fish_yoy": 1.0, "aqua_yoy": 1.0,
                     "ur_yoy": 0.1, "under_yoy": 0.1, "remit_usd_yoy": np.nan, "remit_php_yoy": np.nan, "fx_yoy": 1.0,
                     "news_n": 8, **{c: 0.0 for c in R.NEWS_SHARES}})
    st = {i["key"]: i["status"] for i in B.statuses(row, R.L.qi("2026-Q3"))}
    assert st["sws_hunger"] == "stale" and st["rice_wholesale"] == "missing" and st["remit_usd_yoy"] == "missing"
    assert st["typhoons"] == "substituted" and st["fish_kill_events"] == "not_collected"
    assert all(st[c] == "too_few_articles" for c in R.NEWS_SHARES)
    row2 = row.copy()
    row2["news_n"], row2["H_age"] = 30, 1.0
    st2 = {i["key"]: i["status"] for i in B.statuses(row2, R.L.qi("2026-Q2"))}
    assert st2["sws_hunger"] == "observed" and st2["typhoons"] == "observed_zero" and st2["news_market"] == "observed_zero"
    assert set(st.values()) | set(st2.values()) <= STATUSES


@needs_e68
def test_stale_hunger_widening_only_widens():
    A = _t("r1_arm_predictions.csv")
    assert (A.loc[A["arm"] == "M1", "hunger_widen"] > 0).all()
    assert (A.loc[A["arm"] == "A0", "hunger_widen"] == 1.0).all()


# ------------------------------------------------------------------------------------------------ climate timing
def test_climate_status_uses_only_items_before_the_date():
    assert CW.hazard("2026-04-22")[0] is False                 # Alert issued that day: only the Watch is before it
    assert CW.hazard("2026-04-23")[0] is True
    assert CW.hazard("2026-04-01")[0] is False                 # only an El Nino Watch before 2026-04-01
    assert CW.hazard("2024-06-08")[0] is False                 # the 2024-06-07 Final Advisory ended the episode


@needs_e68
def test_k1_shift_only_with_el_nino_in_force_and_negative_in_2023_24():
    K = _t("r1_elnino_shift.csv")
    k = K[K["arm"] == "K1"]
    assert set(k.loc[k["in_force"] & (k["n_past_rows"] > 0), "origin_quarter"]) == {"2023-Q4", "2024-Q1", "2026-Q2", "2026-Q3"}
    assert (k.loc[~k["in_force"], "n_past_rows"] == 0).all()
    s = json.loads(k[k["origin_quarter"] == "2023-Q4"]["shift_food_m1"].iloc[0])
    assert all(v < 0 for v in s.values())                     # 2023-24: food inflation came in below projection


@needs_e68
def test_national_inputs_have_no_cross_province_variance():
    V = _t("r2_trigger_variance.csv").set_index("feature")
    for f in ("ur_yoy", "under_yoy", "remit_usd_yoy", "remit_php_yoy", "fx_yoy", "enso", "enso_l2"):
        assert V.loc[f, "national_or_regional"]


# ------------------------------------------------------------------------------------------------ serving
def test_e68_numbers_equal_e58_identity_and_default(mode):
    mode("e58")
    base = {(q, c): _summary(q, s) for q in ("2027-Q1", "2026-Q4") for c, s in SLUG.items()}
    mode("e68")
    assert LEAD2.layered() and LEAD2.serves("2027-Q1") and not LEAD2.serves("2027-Q2")
    assert forecast_target("2026-10-20T09:00:00")["target_quarter"] == "2027-Q1"
    for (q, c), b in base.items():
        s = _summary(q, SLUG[c])
        assert s["probability"] == b["probability"] and s["result"] == b["result"] and s["components"] == b["components"]
        assert s["modelIdentity"]["servingMode"] == "e68"
        assert "not a measure of household food insecurity" in s["event"]
    mode(None)
    assert LEAD2.mode() == "e38"
    assert _get("/api/v1/explainability", scope="province", id="quezon", quarter="2027-Q1").get("summary") is None


def test_low_under_watch_el_nino_and_affordability_text(mode):
    mode("e68")
    d = D68.disclosure()
    for c, slug in SLUG.items():
        s = _summary("2027-Q1", slug)
        name = LEAD2.record()["provinces"][c]["name"]
        assert s["result"] == "LOW" and s["climateWatch"]["level"].startswith("CLIMATE WATCH")
        assert "Why the score is LOW although a climate watch is in force" in s["sentence"]
        assert d["elNinoFinding"] in s["sentence"]
        a = d["affordability"]["2027-Q1"][name]
        assert s["affordability"] == a
        assert ("Affordability: headline inflation" in s["sentence"]) == a["headlineAbove"]
        assert all(i["status"] in STATUSES for i in s["inputStatus"])
        miss = {i["key"] for i in s["inputStatus"] if i["status"] == "missing"}
        assert {"remit_usd_yoy", "remit_php_yoy"} <= miss
        assert "treated as unknown, not as no risk" in s["sentence"]
    back = _summary("2026-Q3", "quezon")
    assert back.get("inputStatus") is None and back.get("modelIdentity") is None


def test_e68_lgus_142_finite_and_coloured(mode):
    mode("e68")
    rows = []
    for s in SLUG.values():
        data = _get(f"/api/v1/provinces/{s}/municipalities", quarter="2027-Q1")["data"]
        assert len(data) == COUNTS[s] and all(r["provinceId"] == s for r in data)
        rows += data
    assert len({r["lguCode"] for r in rows}) == 142
    assert all(math.isfinite(r["riskIndex"]) and 0 <= r["riskIndex"] <= 1 and r["riskLevel"] in ("low", "moderate", "high")
               for r in rows)
    assert sum(r["tied"] for r in rows) == 0
