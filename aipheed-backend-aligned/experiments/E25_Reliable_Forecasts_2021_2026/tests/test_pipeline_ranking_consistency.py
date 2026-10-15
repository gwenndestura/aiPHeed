"""Quarterly pipeline (missing/stale data, transition with SYNTHETIC fixtures), LGU ranking determinism, the PCF
engine fixes, and API / dashboard / PDF consistency on the single forecast record."""
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

import _paths  # noqa: F401
from _paths import EXP
from app.quarterly import pcf_engine as PE
from app.quarterly.config import ForecastPeriod
from app.quarterly.lgu_poverty import rank_lgus
from app.quarterly.periods import Quarter
from app.quarterly.registry import Registry
from app.quarterly.update import run_update

PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]


# ---------------------------------------------------------------------------------------------- PCF engine fixes
def test_engine_never_uses_pre2021_D_pairs():
    Dm = {(p, q): 1.0 for p in PROVS for q in range(PE.qk("2019-Q1"), PE.qk("2026-Q2") + 1)}
    beta, sig, n = PE.d_fit(Dm, {}, PE.qk("2026-Q3"), 1, False)
    # pairs t' from 2021-Q2 (uses D(2021-Q1)) to t'+1 <= 2026-Q2 -> 20 quarters x 5
    assert n == 5 * (PE.qk("2026-Q1") - PE.qk("2021-Q2") + 1)


def test_unverified_round_usable_only_after_its_upper_bound():
    r = pd.DataFrame([{"quarter": "2025-Q4", "H": 16.7, "published": "2026-01-14", "published_eff": "2026-01-14",
                       "date_type": "verified", "definition_A": True, "source": "production"},
                      {"quarter": "2026-Q1", "H": 22.4, "published": None, "published_eff": "2026-09-10T00:00:00",
                       "date_type": "unverified", "definition_A": True, "source": "production_2026_authorized"},
                      {"quarter": "2026-Q2", "H": 17.3, "published": None, "published_eff": None,
                       "date_type": "unverified", "definition_A": True, "source": "x"}])
    before = PE.rounds_at_origin(r, pd.Timestamp("2026-07-01", tz="Asia/Manila"))
    after = PE.rounds_at_origin(r, pd.Timestamp("2026-10-01", tz="Asia/Manila"))
    assert list(before["quarter"]) == ["2025-Q4"]
    assert list(after["quarter"]) == ["2025-Q4", "2026-Q1"]        # no date at all = never usable


# ---------------------------------------------------------------------------------------------- pipeline: missing / stale
def _reg(tmp_path, end="2026-Q2", authorized=True, avail="2026-10-01T00:00:00+08:00"):
    f = tmp_path / f"x_{end}_{authorized}.csv"
    f.write_text(f"a\n{end}\n")
    reg = Registry(tmp_path / "reg.json")
    reg.register("src", "indicator", str(f), observation_start="2021-Q1", observation_end=end, available_at=avail,
                 authorized=authorized)
    return reg


def _period(reqs):
    return ForecastPeriod(Quarter.parse("2026-Q4"), pd.Timestamp("2026-12-31T23:59:59", tz="Asia/Manila"),
                          requirements=reqs)


@pytest.mark.parametrize("end,authorized,avail,status", [
    ("2026-Q2", True, "2026-10-01T00:00:00+08:00", "STALE"),
    ("2026-Q3", False, "2026-10-01T00:00:00+08:00", "UNAUTHORIZED"),
    ("2026-Q3", True, "2027-02-01T00:00:00+08:00", "NOT_AVAILABLE_BY_CUTOFF"),
    ("2026-Q3", True, "2026-10-01T00:00:00+08:00", "OK")])
def test_requirement_status(tmp_path, end, authorized, avail, status):
    from app.quarterly.update import check_requirement
    reg = _reg(tmp_path, end, authorized, avail)
    c = check_requirement({"id": "r", "kind": "indicator", "quarter": "2026-Q3", "source_ids": ["src"]}, reg,
                          _period([]))
    assert c["status"] == status


def test_insufficient_record_never_carries_a_forecast(tmp_path):
    reg = _reg(tmp_path, "2026-Q2")
    p = _period([{"id": "r", "kind": "indicator", "quarter": "2026-Q3", "source_ids": ["src"]}])
    rec = run_update(p, reg, tmp_path / "out", forecaster=lambda *a: {"x": 1},
                     now=pd.Timestamp("2027-01-02", tz="Asia/Manila"))
    assert rec["status"] == "INSUFFICIENT_DATA" and rec["forecast"] is None and rec["missing"]


def test_live_2027Q1_record_lists_missing_inputs():
    rec = json.loads((EXP / "backend_dev" / "data" / "quarterly_runs" / "2027-Q1" / "forecast_record.json").read_text())
    assert rec["status"] == "INSUFFICIENT_DATA" and rec["forecast"] is None
    joined = " ".join(rec["missing"])
    for need in ("sws_rounds", "provincial_D_quarterly", "provincial_D_now", "cutoff"):
        assert need in joined


# ---------------------------------------------------------------------------------------------- transition (SYNTHETIC)
def test_quarterly_transition_with_synthetic_complete_inputs(tmp_path):
    """Synthetic fixtures only (never evaluation): a complete set of inputs through 2026-Q3/Q4 -> READY with an
    indicative forecast; then the period advances to 2027-Q2 and the history is kept."""
    from app.quarterly.forecaster_v2 import make_pcf_forecaster
    rng = np.random.default_rng(0)
    qs = [str(Quarter.parse("2021-Q1").shift(i)) for i in range(24)]          # 2021-Q1 .. 2026-Q4
    rounds = pd.DataFrame([{"quarter": q, "round": q, "H": 12 + rng.normal(), "published": str(Quarter.parse(q).next().start().date()),
                            "published_eff": str(Quarter.parse(q).next().start().date()), "date_type": "verified",
                            "definition_A": True, "source": "production"} for q in qs[1:-1]])
    D = pd.DataFrame([{"province_code": p, "quarter": q, "D": rng.normal(), "F": 3.0} for q in qs[:-1] for p in PROVS])
    D["D"] -= D.groupby("quarter")["D"].transform("mean")
    S1 = D.merge(rounds[["quarter", "H"]], on="quarter").assign(S1=lambda x: x["H"] + 2 * x["D"])[["province_code", "quarter", "S1"]]
    N = D[D["quarter"] >= "2022-Q1"].assign(Dnow=lambda x: x["D"])[["province_code", "quarter", "Dnow"]]
    N = pd.concat([N, pd.DataFrame([{"province_code": p, "quarter": "2026-Q4", "Dnow": 0.1} for p in PROVS])])
    lg = pd.read_csv(EXP / "backend_dev" / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    files = {"sws_rounds": rounds, "s1_labels": S1, "d_quarterly_panel": D, "dnow_panel": N, "lgu_vulnerability": lg}
    reg = Registry(tmp_path / "reg.json")
    for sid, df in files.items():
        f = tmp_path / f"{sid}.csv"
        df.to_csv(f, index=False)
        kind = {"sws_rounds": "label", "s1_labels": "label", "lgu_vulnerability": "static"}.get(sid, "indicator")
        end = {"sws_rounds": "2026-Q3", "s1_labels": "2026-Q3", "d_quarterly_panel": "2026-Q3", "dnow_panel": "2026-Q4"}.get(sid)
        reg.register(sid, kind, str(f), observation_start="2021-Q1", observation_end=end,
                     available_at="2026-12-01T00:00:00+08:00", authorized=True)
    card = tmp_path / "card.json"
    card.write_text('{"name": "synthetic"}')
    reg.register("pcf_model_card", "model", str(card), authorized=True)
    reqs = [{"id": "sws", "kind": "label", "quarter": "2026-Q3", "source_ids": ["sws_rounds"]},
            {"id": "lab", "kind": "label", "quarter": "2026-Q3", "source_ids": ["s1_labels"]},
            {"id": "d", "kind": "indicator", "quarter": "2026-Q3", "source_ids": ["d_quarterly_panel"]},
            {"id": "n", "kind": "indicator", "quarter": "2026-Q4", "source_ids": ["dnow_panel"]},
            {"id": "m", "kind": "model", "source_ids": ["pcf_model_card"]},
            {"id": "l", "kind": "static", "source_ids": ["lgu_vulnerability"]}]
    p = _period(reqs)
    early = run_update(p, reg, tmp_path / "out", forecaster=make_pcf_forecaster({}),
                       now=pd.Timestamp("2026-12-15", tz="Asia/Manila"))
    assert early["status"] == "INSUFFICIENT_DATA"                       # cutoff not reached
    rec = run_update(p, reg, tmp_path / "out", forecaster=make_pcf_forecaster({}),
                     now=pd.Timestamp("2027-01-02", tz="Asia/Manila"))
    assert rec["status"] == "READY"
    pr = rec["forecast"]["leads"]["1"]["provinces"]
    assert all(v["risk"]["indicative_only"] for v in pr.values())
    assert len(rec["forecast"]["lgu_ranking"]) == 142
    assert (tmp_path / "out" / "2027-Q1" / "history").exists()          # earlier record kept
    nxt = p.advanced()
    assert str(nxt.reference_quarter) == "2027-Q1" and str(nxt.target_quarter) == "2027-Q2"
    assert all(r["quarter"] == str(Quarter.parse(o["quarter"]).next()) for r, o in zip(nxt.requirements, reqs) if "quarter" in o)


# ---------------------------------------------------------------------------------------------- LGU ranking
def test_ranking_deterministic_and_labels_substitutes():
    lg = pd.read_csv(EXP / "LGU_RANKING_VALIDATION.csv", dtype={"lgu_code": str})
    assert len(lg) == 142 and lg["lgu_code"].is_unique
    sub = lg[lg["poverty_lgu_estimate"].isna()]
    assert (sub["poverty_value_kind"] == "province-mean substitute (no municipal estimate)").all() and len(sub) == 126
    v = json.loads((EXP / "runs" / "lgu_validation.json").read_text())
    assert v["deterministic_under_shuffled_input"] and v["density_vs_poverty_where_both_exist"]["spearman_rho"] < 0
    cen = lg.assign(province_code=lg["province"].map({"Cavite": "PH040100000", "Laguna": "PH040200000",
                                                       "Quezon": "PH040300000", "Rizal": "PH040400000",
                                                       "Batangas": "PH040500000"}))
    pov = lg[["lgu_code", "poverty_lgu_estimate", "poverty_source"]].assign(poverty_province_value=lg["poverty_value_used"].where(lg["poverty_lgu_estimate"].isna()))
    probs = {p: 0.5 for p in PROVS}
    a = rank_lgus(cen[["province_code", "lgu_code", "lgu_name", "lgu_type", "population_2020", "land_area_km2"]], pov, probs)
    b = rank_lgus(cen.sample(frac=1, random_state=3)[["province_code", "lgu_code", "lgu_name", "lgu_type",
                                                      "population_2020", "land_area_km2"]], pov.sample(frac=1, random_state=4), probs)
    assert a[["lgu_code", "rank_region"]].reset_index(drop=True).equals(b[["lgu_code", "rank_region"]].reset_index(drop=True))
    m = a.merge(lg[["lgu_code", "vulnerability_index"]], on="lgu_code", suffixes=("", "_csv"))
    assert np.allclose(m["vulnerability_index"], m["vulnerability_index_csv"])   # within-province order independent of probability


# ---------------------------------------------------------------------------------------------- API / dashboard / PDF
def test_api_dashboard_pdf_read_one_record():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1 import quarterly
    rec_path = EXP / "backend_dev" / "data" / "e25" / "e25_forecast_record.json"
    quarterly.E25_RECORD = rec_path
    app = FastAPI()
    app.include_router(quarterly.router, prefix="/api/v1")
    r = TestClient(app).get("/api/v1/quarterly/e25-timeline")
    assert r.status_code == 200
    api = r.json()
    dash = EXP / "dashboard_dev" / "public" / "e25_forecast_record.json"
    assert dash.read_bytes() == rec_path.read_bytes()                   # byte-identical copies
    assert api == json.loads(dash.read_text(encoding="utf-8"))
    from pdfminer.high_level import extract_text
    txt = extract_text(str(EXP / "dashboard_dev" / "public" / "aiPHeed_E25_forecast_report.pdf"))
    assert api["content_sha256"] in txt.replace("\n", "")
    op = [q for q in api["quarters"] if q["quarter"] == "2027-Q1"][0]
    assert op["status"] in txt and "Outcome pending" in txt
    for q in api["quarters"]:
        if q["kind"].startswith("BACKTEST"):
            for p in q["provinces"].values():
                if p.get("forecast"):
                    assert str(p["forecast"]["p_high"]) in txt


def test_api_refuses_a_tampered_record(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1 import quarterly
    rec = json.loads((EXP / "backend_dev" / "data" / "e25" / "e25_forecast_record.json").read_text())
    rec["quarters"][0]["display"] = "tampered"
    f = tmp_path / "rec.json"
    f.write_text(json.dumps(rec))
    quarterly.E25_RECORD = f
    app = FastAPI()
    app.include_router(quarterly.router, prefix="/api/v1")
    assert TestClient(app).get("/api/v1/quarterly/e25-timeline").status_code == 500
