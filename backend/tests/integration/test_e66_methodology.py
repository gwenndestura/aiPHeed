"""
tests/integration/test_e66_methodology.py
-----------------------------------------
E66 (aipheed-backend-aligned/experiments/E66_Best_Methodology_Review): best defensible methodology for Objectives 1-4.

Evidence (from the E66 outputs, recomputed from the sealed E55-E65 files)
  * the protocol is frozen and every sealed prediction file is unchanged;
  * the unified scoreboard reproduces the reported E56 / E58-EW / E60-A figures and the E63 lead figures;
  * on all 50 evaluation rows T43 equals PS (provincial food-price pressure); no arm beats E56 by the frozen rule;
  * lead-1 and lead-2 rows are aligned (target = origin quarter + lead; issue = start of the quarter after the origin).
Climate Food-Stress Watch (app.ml.inference.climate_watch)
  * the hazard rule uses only PAGASA items dated before the issue date and agrees with E65's independent coding;
  * missing hunger -> INSUFFICIENT DATA; missing production -> "exposure unknown", never "no exposure";
  * e66 mode serves the E58 numbers unchanged plus the watch; e58 and the E38 default get no watch.
LGU (Objective 3)
  * 142 unique LGUs, five provinces with the expected counts, finite indices;
  * within-province order = vulnerability order; exact ranks remove the 4-dp ties; the default ranking is unchanged.
Dynamic target
  * the dashboard target is computed from the clock; the frozen 2027-Q1 record never serves a later quarter.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import climate_watch as CW
from app.ml.inference import e41_lead2 as LEAD2
from app.quarterly import lgu_poverty as LP
from app.quarterly.target import forecast_target

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "aipheed-backend-aligned" / "experiments"
E66 = EXP / "E66_Best_Methodology_Review"
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}
needs_e66 = pytest.mark.skipif(not (E66 / "out" / "r1_scoreboard.json").exists(), reason="E66 outputs not present")


def _out(name):
    return json.loads((E66 / "out" / name).read_text(encoding="utf-8"))


@pytest.fixture
def mode(monkeypatch):
    def set_mode(m):
        if m is None:
            monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
        else:
            monkeypatch.setenv("AIPHEED_LEAD2_MODEL", m)
        monkeypatch.setenv("AIPHEED_NOW", "2026-10-19T09:00:00")
    return set_mode


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


# ------------------------------------------------------------------------------------------------ evidence
@needs_e66
def test_protocol_frozen_and_sealed_files_unchanged():
    sys.path.insert(0, str(E66 / "runner"))
    import e66_lib as H
    assert H.verify_protocol() == _out("r1_scoreboard.json")["protocol_sha256"]
    assert H.verify_sealed() == _out("r1_scoreboard.json")["sealed"]


@needs_e66
def test_scoreboard_reproduces_reported_figures_and_no_arm_beats_e56():
    o = _out("r1_scoreboard.json")
    rep = o["reproduction"]
    assert rep["E56_acc"] == pytest.approx(0.72) and rep["E56_brier"] == pytest.approx(0.2140, abs=5e-4)
    assert rep["EW_acc"] == pytest.approx(0.78) and rep["E60A_acc"] == pytest.approx(0.74)
    assert not any(r["better_by_rule_holm"] for r in o["paired_vs_E56"])
    m = {r["arm"]: r for r in o["metrics50"]}
    assert m["Majority (as-of, always LOW)"]["recall_HIGH"] == 0.0


@needs_e66
def test_t43_equals_price_pressure_on_every_evaluation_row():
    R = pd.read_csv(E66 / "tables" / "r1_rows50_all_arms.csv")
    assert len(R) == 50 and (R["T43"] == R["PS"]).all()
    facts = _out("r4_r7.json")["target_facts"]
    assert facts["T43_equals_PS_when_hunger_above_line"] == "70/70"


@needs_e66
def test_lead_metrics_reproduce_e63_and_are_not_pooled():
    rows = {(r["lead"], r["arm"]): r for r in _out("r4_r7.json")["lead_metrics"]}
    assert rows[(1, "E56 procedure")]["brier"] == pytest.approx(0.130, abs=1e-3)
    assert rows[(2, "E56 procedure")]["brier"] == pytest.approx(0.214, abs=1e-3)
    assert rows[(3, "E56 procedure")]["brier"] == pytest.approx(0.251, abs=1e-3)
    assert {k[0] for k in rows} == {1, 2, 3}
    assert not any(r["better_by_rule"] for r in _out("r4_r7.json")["lead_paired"])


def test_lead_alignment_in_sealed_lead_predictions():
    S = pd.read_csv(EXP / "E63_Lead_Time_Study" / "sealed" / "predictions.csv")

    def qi(s):
        return int(s[:4]) * 4 + int(s[-1]) - 1
    assert ((S["target"].map(qi) - S["origin_quarter"].map(qi)) == S["lead"]).all()
    nxt = S["origin_quarter"].map(lambda s: qi(s) + 1)
    start = nxt.map(lambda i: f"{i // 4}-{3 * (i % 4) + 1:02d}-01")
    assert (start == S["issue_date"]).all()


# ------------------------------------------------------------------------------------------------ climate watch
def test_hazard_uses_only_items_before_the_issue_date():
    assert CW.hazard("2026-06-09")[0] is True          # El Nino Alert of 2026-04-22 in force; Advisory No. 1 not yet
    assert "2026-04-22" in CW.hazard("2026-06-09")[1]
    assert "2026-06-09" in CW.hazard("2026-06-10")[1]
    assert CW.hazard("2026-04-01")[0] is False          # only a Watch (2026-03-25)
    assert CW.hazard("2024-07-01")[0] is False          # El Nino Final Advisory 2024-06-07
    assert CW.hazard("2024-04-01")[0] is True
    assert CW.hazard("2021-10-01")[0] is False          # no El Nino item before 2023-03-24
    assert "2026-10-07" not in CW.hazard("2026-10-01")[1]


def test_missing_inputs_are_never_read_as_no_risk():
    w = CW.watch("2026-10-01", None, -50.0, None)
    assert w["level"] == "INSUFFICIENT DATA" and w["householdStress"] is None
    w = CW.watch("2026-10-01", 17.3, None, None)
    assert w["level"] == "CLIMATE WATCH" and w["localExposure"] is None and "unknown" in w["exposureNote"]
    assert CW.watch("2026-10-01", 11.3, -50.0, None)["level"] == "NO CLIMATE WATCH"     # strictly above 11.3%
    assert CW.watch("2026-10-01", 17.3, -10.0, 5.0)["level"] == "CLIMATE WATCH + LOCAL EXPOSURE"
    assert CW.watch("2026-04-01", 25.0, -50.0, -50.0)["level"] == "NO CLIMATE WATCH"
    assert CW.sentence(CW.watch("2026-04-01", 25.0, None, None), "2026-04-01") is None


@needs_e66
def test_hazard_rule_agrees_with_e65_coding_at_every_issue_date():
    o = _out("r5_el_nino.json")
    assert o["hazard_rule_mismatches_vs_e65"] == []
    W = pd.read_csv(E66 / "tables" / "r5_cfsw_history.csv")
    assert W["issue_date"].nunique() == 20 and len(W) == 100
    exported = pd.read_csv(ROOT / "backend" / "data" / "e66" / "cfsw_inputs.csv")
    assert (exported["level"].values == W["level"].values).all()


def test_e66_mode_serves_e58_numbers_unchanged_plus_watch(mode):
    mode("e58")
    base = {(q, c): _get("/api/v1/explainability", scope="province", id=s, quarter=q)["summary"]
            for q in ("2027-Q1", "2026-Q4") for c, s in SLUG.items()}
    assert all(v.get("climateWatch") is None for v in base.values())
    mode("e66")
    for (q, c), b in base.items():
        s = _get("/api/v1/explainability", scope="province", id=SLUG[c], quarter=q)["summary"]
        assert s["probability"] == b["probability"] and s["result"] == b["result"]
        assert s["components"] == b["components"]
        cw = s["climateWatch"]
        assert cw["level"].startswith("CLIMATE WATCH") and cw["issueDate"] == ("2026-10-01" if q == "2027-Q1" else "2026-07-01")
        assert "not a model input" in s["sentence"] and "not a food-insecurity probability" in s["sentence"]
    back = _get("/api/v1/explainability", scope="province", id="quezon", quarter="2026-Q3")["summary"]
    assert back.get("climateWatch") is None                          # back-tests: no claim
    reg = _get("/api/v1/explainability", scope="region", id="calabarzon", quarter="2027-Q1")["summary"]
    assert set(reg["climateWatch"]["provinces"]) == set(SLUG)


def test_e66_watch_levels_for_2027q1(mode):
    mode("e66")
    rec = LEAD2.record()
    got = {c: CW.for_quarter(rec, "2027-Q1", c)["level"] for c in SLUG}
    assert got == {"PH040100000": "CLIMATE WATCH + LOCAL EXPOSURE", "PH040200000": "CLIMATE WATCH + LOCAL EXPOSURE",
                   "PH040300000": "CLIMATE WATCH", "PH040400000": "CLIMATE WATCH",
                   "PH040500000": "CLIMATE WATCH + LOCAL EXPOSURE"}


def test_production_default_unchanged(mode):
    mode(None)
    assert LEAD2.mode() == "e38"
    ex = _get("/api/v1/explainability", scope="province", id="quezon", quarter="2027-Q1")
    assert ex.get("summary") is None


# ------------------------------------------------------------------------------------------------ LGU
def _vul():
    return pd.read_csv(ROOT / "backend" / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})


def _rank(prob, exact):
    from app.quarterly.forecaster_v2 import lgu_table
    return lgu_table(_vul(), prob, exact_ranks=exact)


PROB = {"PH040100000": 0.109, "PH040200000": 0.0703, "PH040300000": 0.146, "PH040400000": 0.0499, "PH040500000": 0.0427}


def test_lgu_coverage_and_finite_values():
    m = _rank(PROB, False)
    assert len(m) == 142 and m["lgu_code"].nunique() == 142
    assert m.groupby("province").size().to_dict() == {"Batangas": 34, "Cavite": 23, "Laguna": 30, "Quezon": 41, "Rizal": 14}
    assert m["risk_index"].notna().all() and (m["risk_index"].between(0, 1)).all()


def test_exact_ranks_remove_rounding_ties_and_default_is_unchanged():
    d, e = _rank(PROB, False), _rank(PROB, True)
    assert d["risk_index"].duplicated(keep=False).sum() > 0                    # 4-dp ties exist by design
    assert e["risk_index_exact"].duplicated(keep=False).sum() == 0
    # default ranks are computed from the 4-dp value, as approved
    assert (d["rank_region"] == d["risk_index"].rank(ascending=False, method="min")).all()
    for _, g in e.groupby("province_code"):                                   # within province = vulnerability order
        assert (g["rank_in_province"] == g["vulnerability_rank_in_province"]).all()


def test_e66_municipalities_endpoint_uses_exact_ranks(mode):
    def rows():
        out = []
        for s in SLUG.values():
            out += _get(f"/api/v1/provinces/{s}/municipalities", quarter="2027-Q1")["data"]
        return out
    mode("e58")
    r58 = rows()
    mode("e66")
    r66 = rows()
    assert len(r66) == 142 and len({r["lguCode"] for r in r66}) == 142
    assert sum(r["tied"] for r in r58) > 0 and sum(r["tied"] for r in r66) == 0
    assert len({r["rankRegion"] for r in r66}) == 142
    assert {r["lguCode"]: r["riskIndex"] for r in r58} == {r["lguCode"]: r["riskIndex"] for r in r66}   # values unchanged


# ------------------------------------------------------------------------------------------------ dynamic target
def test_dynamic_target_and_no_stale_forecast(monkeypatch):
    assert forecast_target("2026-10-19T09:00:00")["target_quarter"] == "2027-Q1"
    assert forecast_target("2027-01-15T09:00:00")["target_quarter"] == "2027-Q2"
    assert forecast_target("2027-03-31T23:59:00")["target_quarter"] == "2027-Q2"
    assert forecast_target("2027-04-01T00:00:00")["target_quarter"] == "2027-Q3"
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e66")
    assert LEAD2.serves("2027-Q1") and not LEAD2.serves("2027-Q2")
