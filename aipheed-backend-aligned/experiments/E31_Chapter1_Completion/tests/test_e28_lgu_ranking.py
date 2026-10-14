"""E28 Objective 3: the 142-LGU ranking and its audit (one implementation for record, API, dashboard and PDF)."""
import os

import numpy as np
import pandas as pd
import pytest

from _paths import EXP

BD = EXP / "backend_dev"
ROSTER = EXP.parents[1] / "data" / "reference" / "calabarzon_lgus.csv"
PROB = {"PH040100000": 0.52, "PH040200000": 0.61, "PH040300000": 0.73, "PH040400000": 0.44, "PH040500000": 0.58}


@pytest.fixture()
def tables():
    v = pd.read_csv(BD / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    r = pd.read_csv(ROSTER, dtype={"lgu_psgc": str})
    return v, r


def test_inputs_cover_exactly_the_142_lgus_and_agree_with_the_roster(tables):
    from app.quarterly.lgu_audit import audit_inputs

    _, c = audit_inputs(*tables)
    assert c["passes"], c
    assert c["rows_vulnerability"] == 142 and c["unique_codes_vulnerability"] == 142
    assert c["per_province"] == {"Batangas": 34, "Cavite": 23, "Laguna": 30, "Quezon": 41, "Rizal": 14}
    assert c["lgu_specific_poverty_estimates"] + c["province_mean_substitutes"] == 142
    assert "rosario" in c["namesakes_across_provinces_resolved_by_psgc"]


def test_every_lgu_gets_a_reproducible_ranking_and_substitutes_are_labelled(tables):
    from app.quarterly.lgu_audit import build_ranking

    a = build_ranking(*tables, PROB, {"t": "x"})
    b = build_ranking(*tables, PROB, {"t": "x"})
    assert a["rows_sha256"] == b["rows_sha256"]
    rows = a["rows"]
    assert len(rows) == 142 and len({r["lgu_code"] for r in rows}) == 142
    assert all(r["risk_index"] is not None and 0 <= r["risk_index"] <= 1 for r in rows)
    assert sorted(r["rank_region"] for r in rows)[0] == 1
    subs = [r for r in rows if r["poverty_lgu_estimate"] is None]
    assert len(subs) == 126
    assert all(r["poverty_value_kind"].startswith("province-mean substitute") for r in subs)
    assert all("density only" in r["limitation"] for r in subs)
    # never a zero poverty value presented for a missing estimate
    assert all(r["poverty_value_used"] > 0 for r in rows)
    # ranks follow risk_index; ties share a rank and are listed by PSGC
    srt = sorted(rows, key=lambda r: (-r["risk_index"], r["lgu_code"]))
    assert [r["lgu_code"] for r in srt] == [r["lgu_code"] for r in rows]
    for x, y in zip(rows, rows[1:]):
        assert (x["rank_region"] == y["rank_region"]) == (x["risk_index"] == y["risk_index"])


def test_missing_province_estimate_gives_null_not_zero(tables):
    from app.quarterly.lgu_audit import build_ranking

    p = dict(PROB)
    p.pop("PH040300000")                     # Quezon has no estimate
    rows = build_ranking(*tables, p, {})["rows"]
    q = [r for r in rows if r["province"] == "Quezon"]
    assert len(q) == 41 and all(r["risk_index"] is None and r["rank_region"] is None for r in q)
    assert rows[-41:] == q                   # listed last, never as the safest LGUs
    assert all(r["risk_index"] is not None for r in rows[:-41])


def test_ties_are_deterministic(tables):
    from app.quarterly.lgu_audit import build_ranking

    v, r = tables
    v = v.copy()
    v.loc[v["province"] == "Rizal", ["population_2020", "land_area_km2"]] = [1000, 10.0]   # identical density
    v.loc[v["province"] == "Rizal", "poverty_lgu_estimate"] = np.nan
    v.loc[v["province"] == "Rizal", "poverty_value_used"] = 5.0          # one substitute value for the whole province
    r = r.copy()
    r.loc[r["province_code"] == "PH040400000", ["population_2020", "land_area_km2"]] = [1000, 10.0]
    rows = build_ranking(v, r, PROB, {})["rows"]
    riz = [x for x in rows if x["province"] == "Rizal"]
    assert len({x["risk_index"] for x in riz}) == 1 and all(x["tied"] for x in riz)
    assert len({x["rank_region"] for x in riz}) == 1
    assert [x["lgu_code"] for x in riz] == sorted(x["lgu_code"] for x in riz)


def test_dashboard_disaggregator_uses_the_same_implementation(tables, monkeypatch):
    from app.ml.inference.disaggregator import Disaggregator
    from app.quarterly.lgu_audit import build_ranking

    monkeypatch.chdir(BD)
    fc = [{"province_code": k, "risk_probability": v, "data_sufficiency_flag": "OK"} for k, v in PROB.items()]
    df = Disaggregator().disaggregate(fc, quarter="2026-Q4")
    ref = {r["lgu_code"]: r for r in build_ranking(*tables, PROB, {})["rows"]}
    assert len(df) == 142
    for r in df.itertuples():
        assert r.risk_index == ref[r.lgu_code]["risk_index"]
        assert r.rank_region == ref[r.lgu_code]["rank_region"]
    # a province without a forecast: null, flagged, not zero
    df2 = Disaggregator().disaggregate([f for f in fc if f["province_code"] != "PH040500000"], quarter="2026-Q4")
    bat = df2[df2["province_code"] == "PH040500000"]
    assert len(bat) == 34 and bat["risk_index"].isna().all() and (bat["data_sufficiency_flag"] == "NO_PROVINCE_FORECAST").all()


def test_municipality_summary_survives_missing_estimates_and_shows_no_band(monkeypatch):
    import app.services.dashboard as svc

    monkeypatch.chdir(BD)
    fc = [{"province_code": k, "risk_probability": v, "data_sufficiency_flag": "OK"} for k, v in PROB.items()
          if k != "PH040100000"]
    monkeypatch.setattr(svc, "_province_forecasts", lambda q: fc)
    svc._municipal_frame.cache_clear()
    monkeypatch.setattr(svc, "_lgu_poverty_map", lambda: {})
    rows = svc.municipality_summary("2026-Q4")
    assert len(rows) == 142
    assert all(r["riskLevel"] is None for r in rows)
    cav = [r for r in rows if r["provinceId"] == "cavite"]
    assert cav and all(r["riskIndex"] is None and r["noProvinceEstimate"] for r in cav)
    assert rows[-len(cav):] == cav
    svc._municipal_frame.cache_clear()
