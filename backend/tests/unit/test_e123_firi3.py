"""
tests/unit/test_e123_firi3.py
-----------------------------
E123 (FIRI3 Amendment 2): Current Conditions and Structural Vulnerability scores, common-core scores, missing indicators,
the latest-complete-year annual rule, publication-date and news/GDELT date restrictions, Batangas source consistency,
contribution / weighting / missingness / classification outputs, immutable prospective snapshots, protocol hashes,
FIRI v2 regression and the Amendment 1 CPI base rule.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.inference import firi3 as F3

T0 = F3.START_Q
PROVS = F3.PROVINCES
REPO = Path(__file__).resolve().parents[2].parent
E = REPO / "aipheed-backend-aligned" / "experiments" / "E123_FIRI3_Design_Resolution"
HAS_OUT = (E / "out" / "summary.json").exists()


def ind_frame(rows):
    """rows: {(unit, indicator): score or None}; provincial, one origin."""
    out = []
    for (u, i), s in rows.items():
        out.append({"scope": "provincial", "unit": u, "t": T0 + 12, "indicator": i, "score": s, "available": s is not None,
                    "components_available": 1, "components_defined": 1})
    return pd.DataFrame(out)


def full(u, **over):
    base = {"FMA": .6, "AFP": .4, "CEC": .5, "EHS": .9, "PSV": .1, "FIS": None}
    base.update(over)
    return {(u, k): v for k, v in base.items()}


def test_amendment_2_hash():
    p = E / "E123_FIRI3_PROTOCOL_AMENDMENT_2.md"
    if not p.exists():
        pytest.skip("amendment file not present")
    assert hashlib.sha256(p.read_bytes()).hexdigest() == F3.AMENDMENT_2_SHA256
    assert F3.VERSION.endswith("1.2")


def test_current_conditions_score():
    ind = ind_frame(full("Cavite"))
    c = F3.subscore(ind, F3.CONDITIONS, "CCS").iloc[0]
    assert c["status"] == "computed" and c["score"] == pytest.approx((.6 + .4 + .5) / 3) and c["members_missing"] == "FIS"
    assert c["band"] == F3.band(c["score"], 3)
    c2 = F3.subscore(ind_frame(full("Cavite", AFP=None)), F3.CONDITIONS, "CCS").iloc[0]
    assert c2["status"] == "not_computable" and c2["score"] is None                         # 2 of 4 < 3


def test_structural_vulnerability_score():
    s = F3.subscore(ind_frame(full("Cavite")), F3.STRUCTURAL, "SVS").iloc[0]
    assert s["score"] == pytest.approx(.5) and s["band"] == "at or below provincial middle"
    s2 = F3.subscore(ind_frame(full("Cavite", PSV=None)), F3.STRUCTURAL, "SVS").iloc[0]
    assert s2["status"] == "not_computable"                                                 # both needed
    reg = pd.DataFrame([{"scope": "regional", "unit": F3.REGION_LABEL, "t": T0 + 12, "indicator": "EHS", "score": .7, "available": True,
                         "components_available": 2, "components_defined": 2}])
    assert F3.subscore(reg, F3.STRUCTURAL, "SVS").iloc[0]["status"] == "not_defined"


def test_common_core_and_missing_indicators():
    rows = {}
    for u in PROVS:
        rows.update(full(u))
    rows[("Quezon", "AFP")] = None                                                          # one province lacks AFP
    ind = ind_frame(rows)
    ov = F3.overall(ind)
    cc = F3.common_core(ind, ov).set_index("unit")
    assert pd.isna(cc.loc["Quezon", "fixed_core"]) and cc.loc["Quezon", "fixed_core_status"] == "core_incomplete"
    assert cc.loc["Cavite", "fixed_core"] == pytest.approx((.6 + .4 + .5 + .9) / 4)
    assert cc.loc["Cavite", "cross_core_indicators"] == "CEC EHS FMA PSV"                   # AFP not common to all five
    assert cc.loc["Cavite", "cross_core"] == pytest.approx((.5 + .9 + .6 + .1) / 4)
    rows2 = {k: (v if k[1] in ("FMA", "AFP") else None) for k, v in rows.items()}
    cc2 = F3.common_core(ind_frame(rows2), F3.overall(ind_frame(rows2)))
    assert (cc2["cross_core_status"] == "comparison_not_possible").all()                   # < 3 common
    assert cc2["fixed_core"].isna().all() and cc2["firi3"].isna().all()


def test_annual_latest_complete_year():
    def ann(year, units, avail):
        return pd.DataFrame([{"feature": "provincial_underemployment_rate_pct_annual", "unit": u, "ref": str(year), "value": float(i),
                              "avail": avail, "status": "r", "source": "t"} for i, u in enumerate(units)])
    a = pd.concat([ann(2023, PROVS, "2024-06-30"), ann(2024, PROVS, "2025-06-30"), ann(2025, PROVS[:3], "2026-06-30")])
    f = next(x for x in F3.FEATURES if x.code == "EHS_underemployment_prov")
    r = F3._rank5(a, f, F3.qindex("2026-Q3"))
    assert {x["period"] for x in r} == {"2024"} and all("2025" in x["note"] for x in r)
    r0 = F3._rank5(a, f, F3.qindex("2024-Q1"))                                               # 2023 not yet published (issue 2024-04-01)
    assert all(x["status"] == "unavailable_at_issue" for x in r0)


def test_publication_date_restriction():
    rows = []
    for i in range(12):
        for u in PROVS:
            rows.append({"feature": "typhoons_local_100km", "unit": u, "period": T0 + i, "value": float(i % 4),
                         "avail": F3.issue_date(T0 + i + 1), "status": "verified", "source": "t"})          # published 2 quarters later
    o = pd.DataFrame(rows)
    fs = F3.feature_scores(o, pd.DataFrame(columns=["feature", "unit", "ref", "value", "avail", "status", "source"]), [T0 + 11])
    s = fs[fs["feature"] == "CEC_cyclones_100km"]
    assert set(s["period"]) == {F3.qlabel(T0 + 9)} and (s["avail_date"].astype(str) < s["issue_date"].astype(str)).all()


def test_amendment1_cpi_base():
    o = pd.DataFrame([{"feature": "cpi_food_yoy_pct", "unit": u, "period": T0 + i, "value": 1.0, "avail": F3.issue_date(T0 + i), "status": "r", "source": "t"}
                      for i in range(8) for u in PROVS])
    clean, _, log = F3.validate_inputs(o, pd.DataFrame(columns=["feature", "unit", "ref", "value", "avail", "status", "source"]))
    assert log["pre2021_base_rows_by_series"] == {"cpi_food_yoy_pct": 20} and clean["period"].min() == T0 + 4


def test_fssi_article_dates():
    try:
        from app.news import pipeline_v3 as P3
        arts = P3.admitted()
    except Exception as e:                                                                   # news stores not present
        pytest.skip(f"news stores unavailable: {e}")
    assert all("2021-01-01" <= a["ph_date"][:10] <= P3.LAST_DATE for a in arts)
    for t in range(T0, 2026 * 4 + 3):
        assert all(P3._ph(a) < P3.origin(t) and a["quarter"] == P3.qs(t) for a in P3.asof(t))
    keys = [a["article_key"] for a in arts]
    assert len(keys) == len(set(keys))


@pytest.mark.skipif(not HAS_OUT, reason="E123 outputs missing")
def test_real_outputs():
    s = json.loads((E / "out" / "summary.json").read_text())
    assert s["deterministic"] and s["firi_v2_unchanged"] and s["state"]["amendment_1_rows_rejected"] == 40
    assert s["news"]["fssi_max_abs_diff"] == 0.0 and s["news"]["fssi_article_count_mismatch"] == 0
    assert s["news"]["gdelt_max_abs_diff"] < 1e-9 and s["news"]["gdelt_avail_after_quarter_end"] and s["news"]["gdelt_first_quarter"] == "2021-Q1"
    assert s["di3"]["complete_years_only"] and s["di3"]["published_before_issue"] and s["di3"]["year_shown"]
    # Batangas: every value entering EHS equals the owner file, except 2024 unemployment, derived as 100 - employment rate
    ch = pd.DataFrame(s["batangas"]["chain"])
    bad = ch[~ch["matches"]]
    assert set(zip(bad["feature"], bad["reference_year"])) <= {("EHS_unemployment_prov", "2024")}
    own = pd.read_csv(REPO / "aipheed-backend-aligned" / "experiments" / "E116_FIRI_Domains" / "data" / "owner" /
                      "calabarzon_provincial_employment_food_insecurity_relevant_2021_2026.csv")
    assert 100 - float(own[(own["province"] == "Batangas") & (own["year"] == 2024)]["employment_rate_pct"].iloc[0]) == pytest.approx(
        float(ch[(ch["feature"] == "EHS_unemployment_prov") & (ch["reference_year"] == "2024")]["firi3_raw_value"].iloc[0]))
    # contribution reporting: indicator shares of each computed FIRI3 sum to 1
    sc = pd.read_csv(E / "out" / "scores_all.csv")
    ind = pd.read_csv(E / "out" / "overall.csv")
    assert len(sc) == len(ind)
    dom = pd.read_csv(E / "out" / "indicator_dominance.csv")
    assert set(dom["indicator"]) == set(F3.INDICATORS) and dom["share_of_firi3_mean"].between(0, 1).all()
    ws = pd.read_csv(E / "out" / "weighting_sensitivity.csv")
    assert {"redundancy-adjusted (E120 rule)", "conditions 1/2 : structure 1/2"} <= set(ws["variant"])
    mk = pd.read_csv(E / "out" / "missingness_by_k.csv").set_index("k")
    assert mk.loc[4, "mean_abs_firi3_minus_core"] == 0.0                                 # with exactly the core, FIRI3 = core
    cl = pd.read_csv(E / "out" / "classification_stability.csv")
    assert cl["band_change_pct"].between(0, 100).all()
    for name in ("E123_CURRENT_CONDITIONS_RESULTS.csv", "E123_STRUCTURAL_VULNERABILITY_RESULTS.csv"):
        d = pd.read_csv(E / name)
        assert d.loc[d["status"] == "computed", "score"].notna().all() and d.loc[d["status"] != "computed", "score"].isna().all()
    for m in (E / "snapshots").glob("*/manifest.json"):
        man = json.loads(m.read_text())
        assert man["amendment_2_sha256"] == F3.AMENDMENT_2_SHA256
        assert all(hashlib.sha256((m.parent / k).read_bytes()).hexdigest() == h for k, h in man["files"].items())


def test_prospective_snapshot_immutable(tmp_path):
    spec = importlib.util.spec_from_file_location("e123_prospective", E / "runner" / "prospective.py")
    pr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pr)
    rows = [{"feature": "typhoons_local_100km", "unit": u, "period": T0 + i, "value": float((i + j) % 3), "avail": F3.issue_date(T0 + i),
             "status": "verified", "source": "t"} for i in range(16) for j, u in enumerate(PROVS)]
    o = pd.DataFrame(rows)
    a = pd.DataFrame(columns=["feature", "unit", "ref", "value", "avail", "status", "source"])
    origin = F3.qlabel(T0 + 15)
    with pytest.raises(RuntimeError):
        pr.issue_snapshot(origin, o, a, tmp_path, today=date(2024, 12, 31))                 # before the issue date 2025-01-01
    d = pr.issue_snapshot(origin, o, a, tmp_path, today=date(2025, 1, 1))
    assert pr.verify(tmp_path) == {origin: True}
    with pytest.raises(FileExistsError):
        pr.issue_snapshot(origin, o, a, tmp_path, today=date(2025, 1, 2))
    before = (d / "scores.csv").read_bytes()
    o2 = o.copy()
    o2.loc[o2["period"] == T0 + 14, "value"] = 9.0                                          # a later revision
    pr.record_observation(origin, o2, a, tmp_path, today=date(2025, 3, 1))
    assert (d / "scores.csv").read_bytes() == before and (d / "observation_2025-03-01.csv").exists() and pr.verify(tmp_path)[origin]
    (d / "scores.csv").write_bytes(before + b"x")                                           # tampering is detected
    assert pr.verify(tmp_path) == {origin: False}
    with pytest.raises(RuntimeError):
        pr.record_observation(origin, o2, a, tmp_path, today=date(2025, 4, 1))


def test_firi_v2_regression():
    from app.ml.inference import firi as FI
    raw = {k: {"x": v, "status": "observed" if v is not None else "missing", "note": ""} for k, v in
           {"A1": .7, "A2": 1.2, "A3": 3.0, "V1": .4, "C1": 0.0, "C2": 2.0, "C3": -5.0, "C4": 1.0, "E1": .3, "E2": -2.0, "N1": None, "H1": .6}.items()}
    r = FI.score_v2(raw, {k: [float(i) for i in range(-5, 10)] for k in FI.CONTINUOUS}, {"A": .5, "C": 1.5, "H": 1.0, "V": .5})
    assert r["firi"] == pytest.approx(0.3929012345679012, abs=1e-15)
    src = (Path(F3.__file__)).read_text(encoding="utf-8")
    assert "from app.ml.inference import firi" not in src
