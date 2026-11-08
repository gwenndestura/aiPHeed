"""
tests/unit/test_firi3.py
------------------------
FIRI3 (app/ml/inference/firi3.py) on small synthetic inputs: feature direction, transform and percentile; history and
staleness rules; annual cross-province ranks without quarterly expansion; components counted once; indicator and
overall completeness; equal weights; bands; geographic separation; point-in-time availability; pre-2021 rejection;
target refusal; determinism; FIRI v2 isolation and an unchanged FIRI v2 regression value.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.inference import firi3 as F3

PROVS = F3.PROVINCES
T0 = F3.START_Q


def obs_rows(series, values_by_period, units=PROVS, avail_lag=1, status="rule_unverified"):
    """values_by_period: {period: value or {unit: value}}; available at the start of period + avail_lag quarters."""
    rows = []
    for p, v in values_by_period.items():
        for u in units:
            val = v[u] if isinstance(v, dict) else v
            rows.append({"feature": series, "unit": u, "period": p, "value": val, "avail": F3.issue_date(p + avail_lag - 1), "status": status, "source": "test"})
    return pd.DataFrame(rows)


def empty_ann():
    return pd.DataFrame(columns=["feature", "unit", "ref", "value", "avail", "status", "source"])


def feat(code):
    return next(f for f in F3.FEATURES if f.code == code)


# ------------------------------------------------------------------------------------------------ Level 1
def test_percentile_direction_and_history():
    # palay production YoY: lower = more risk (direction -1); 10 earlier quarters, values 0..9 for every province
    vals = {T0 + i: float(i) for i in range(10)}
    vals[T0 + 10] = {u: v for u, v in zip(PROVS, (-50.0, 100.0, 4.5, 0.0, 9.0))}
    o = obs_rows("palay_production_yoy_pct", vals)
    r = F3._dynamic(o, feat("AFP_palay"), T0 + 11)
    s = {x["unit"]: x["score"] for x in r}
    assert s["Cavite"] == 1.0                     # a big production fall is the highest risk so far
    assert s["Laguna"] == 0.0                     # a big rise is the lowest risk
    prior = -np.repeat(np.arange(10.0), 5)
    assert s["Batangas"] == pytest.approx(F3.midrank(-4.5, prior))
    assert all(x["prior_n"] == 50 for x in r)     # earlier periods of all five provinces, not the current period


def test_insufficient_history_and_stale_are_not_scored():
    o = obs_rows("cpi_food_yoy_pct", {T0: 1.0}, units=("Cavite",))
    r = {x["unit"]: x for x in F3._dynamic(o, feat("FMA_food_cpi"), T0 + 1)}
    assert r["Cavite"]["status"] == "insufficient_history" and r["Cavite"]["score"] is None
    assert r["Laguna"]["status"] == "missing" and r["Laguna"]["score"] is None
    o = obs_rows("cpi_food_yoy_pct", {T0 + i: float(i) for i in range(10)})
    r = {x["unit"]: x for x in F3._dynamic(o, feat("FMA_food_cpi"), T0 + 9 + 4)}       # latest observation 4 quarters old
    assert r["Cavite"]["status"] == "stale" and r["Cavite"]["score"] is None


def test_abs_transform_for_rainfall_departure():
    vals = {T0 + i: float(i - 5) for i in range(10)}
    vals[T0 + 10] = {u: v for u, v in zip(PROVS, (-100.0, 100.0, 0.0, 0.0, 0.0))}
    r = {x["unit"]: x["score"] for x in F3._dynamic(obs_rows("rainfall_anomaly_mm", vals), feat("CEC_rain_departure"), T0 + 11)}
    assert r["Cavite"] == r["Laguna"] == 1.0      # drought and flood are both the largest departure


def test_point_in_time_availability():
    vals = {T0 + i: float(i) for i in range(12)}
    o = obs_rows("cpi_food_yoy_pct", vals, avail_lag=2)                                   # published two quarters later
    r = {x["unit"]: x for x in F3._dynamic(o, feat("FMA_food_cpi"), T0 + 11)}
    assert r["Cavite"]["period"] == F3.qlabel(T0 + 9)                                     # T0+10 is published on the issue day itself: not before it
    assert r["Cavite"]["avail_date"] < F3.issue_date(T0 + 11)


def test_annual_rank_latest_published_year_no_expansion():
    ann = pd.DataFrame([{"feature": "poverty_incidence_popweighted_pct", "unit": u, "ref": "2021", "value": v, "avail": "2025-07-01", "status": "verified", "source": "t"}
                        for u, v in zip(PROVS, (11.0, 8.0, 9.0, 7.0, 20.0))])
    f = feat("PSV_poverty")
    before = {x["unit"]: x for x in F3._rank5(ann, f, F3.qindex("2025-Q1"))}             # issue 2025-04-01: not yet published
    assert all(x["status"] == "unavailable_at_issue" and x["score"] is None for x in before.values())
    after = {x["unit"]: x for x in F3._rank5(ann, f, F3.qindex("2025-Q3"))}
    assert after["Quezon"]["score"] == 0.9 and after["Rizal"]["score"] == 0.1 and after["Laguna"]["score"] == 0.3
    assert after["Quezon"]["period"] == "2021"                                              # the year is kept, not a quarter
    fs = F3.feature_scores(pd.DataFrame(columns=["feature", "unit", "period", "value", "avail", "status", "source"]), ann, [F3.qindex("2025-Q3")])
    assert set(fs.loc[fs["feature"] == "PSV_poverty", "period"]) == {"2021"}


def test_annual_incomplete_year_not_scored():
    ann = pd.DataFrame([{"feature": "provincial_unemployment_rate_pct_annual", "unit": u, "ref": "2025", "value": 5.0, "avail": "2026-06-30", "status": "r", "source": "t"}
                        for u in PROVS[:4]])
    r = F3._rank5(ann, feat("EHS_unemployment_prov"), F3.qindex("2026-Q3"))
    assert all(x["status"] == "incomplete_year" and x["score"] is None for x in r)


# ------------------------------------------------------------------------------------------------ Level 2 and 3
def fs_frame(scores: dict, scope="provincial", unit="Cavite", t=T0 + 12):
    rows = []
    for f in F3.FEATURES:
        if (f.scope == "P") != (scope == "provincial"):
            continue
        rows.append({"scope": scope, "unit": unit, "t": t, "feature": f.code, "indicator": f.indicator, "component": f.component,
                     "score": scores.get(f.code, np.nan), "status": "verified" if f.code in scores else "missing"})
    return pd.DataFrame(rows)


def test_component_counts_once_and_indicator_mean():
    # protein prices (3 features) is one component; FMA = mean(food, cost, rice, protein-mean)
    s = {"FMA_food_cpi": 0.8, "FMA_headline_cpi": 0.6, "FMA_rice_wholesale": 0.4, "FMA_chicken": 0.0, "FMA_pork": 0.3, "FMA_tilapia": 0.6}
    ind = F3.indicator_scores(fs_frame(s))
    fma = ind[ind["indicator"] == "FMA"].iloc[0]
    assert fma["score"] == pytest.approx((0.8 + 0.6 + 0.4 + 0.3) / 4)
    assert fma["components_available"] == 4 and fma["components_defined"] == 4


def test_indicator_needs_half_of_components():
    ind = F3.indicator_scores(fs_frame({"AFP_palay": 0.9, "AFP_vegetables": 0.1}))       # 2 of 5 components < ceil(5/2) = 3
    afp = ind[ind["indicator"] == "AFP"].iloc[0]
    assert not afp["available"] and afp["score"] is None
    ind = F3.indicator_scores(fs_frame({"AFP_palay": 0.9, "AFP_vegetables": 0.1, "AFP_fisheries": 0.5}))
    assert ind[ind["indicator"] == "AFP"].iloc[0]["score"] == pytest.approx(0.5)


def full_scores():
    return {"FMA_food_cpi": .7, "FMA_headline_cpi": .7, "FMA_rice_wholesale": .7, "FMA_chicken": .7, "AFP_palay": .3, "AFP_vegetables": .3, "AFP_rootcrops": .3,
            "CEC_heat": .6, "CEC_cyclones_100km": .6, "EHS_unemployment_prov": .9, "PSV_poverty": .1, "FIS_fssi": .5}


def test_overall_equal_weights_completeness_and_band():
    ov = F3.overall(F3.indicator_scores(fs_frame(full_scores()))).iloc[0]
    assert ov["indicators_available"] == 6 and ov["firi3"] == pytest.approx((.7 + .3 + .6 + .9 + .1 + .5) / 6)
    assert ov["band"] == F3.band(ov["firi3"], 6)
    assert ov["loo_min"] <= ov["firi3"] <= ov["loo_max"]
    assert ov["verification_share"] is None                                             # no feature table passed
    three = {k: v for k, v in full_scores().items() if k.split("_")[0] in ("FMA", "AFP", "CEC")}
    ov3 = F3.overall(F3.indicator_scores(fs_frame(three))).iloc[0]
    assert ov3["firi3"] is None and ov3["status"] == "not_computable" and ov3["band"] == "not_computable"
    assert "EHS" in ov3["indicators_missing"]


def test_regional_needs_four_of_five_and_has_no_psv():
    assert F3.indicators("R") == ("FMA", "AFP", "CEC", "EHS", "FIS")
    s = {"FMA_food_cpi_R": .5, "FMA_headline_cpi_R": .5, "AFP_palay_R": .5, "CEC_heat_R": .5, "CEC_cyclones_R": .5, "FIS_shortage_news_R": .5}
    ov = F3.overall(F3.indicator_scores(fs_frame(s, scope="regional", unit=F3.REGION_LABEL))).iloc[0]
    assert ov["indicators_available"] == 3 and ov["firi3"] is None                       # AFP 1 of 4 components, EHS missing: 3 of 5
    s.update({"AFP_rootcrops_R": .5, "EHS_unemployment_change_R": .5})
    ov = F3.overall(F3.indicator_scores(fs_frame(s, scope="regional", unit=F3.REGION_LABEL))).iloc[0]
    assert ov["indicators_available"] == 5 and ov["firi3"] == pytest.approx(.5)


def test_bands():
    for k in (4, 5, 6):
        sd = math.sqrt(1 / 12) / math.sqrt(k)
        assert F3.band(0.4999, k) == "usual or below"
        assert F3.band(0.5, k) == "above usual"
        assert F3.band(0.5 + sd, k) == "elevated"
        assert F3.band(0.5 + 1.645 * sd, k) == "high"
    assert F3.band(None, 4) == "not_computable"


# ------------------------------------------------------------------------------------------------ input rules
def test_geographic_separation_of_specs():
    for f in F3.FEATURES:
        if f.scope == "P":
            assert f.unit is None and not f.code.endswith("_R")
        else:
            assert f.unit in F3.REGIONAL_UNITS and f.code.endswith("_R")
    o = obs_rows("cpi_food_yoy_pct", {T0: 1.0}, units=("Manila",))
    with pytest.raises(ValueError):
        F3.validate_inputs(o, empty_ann())


def test_pre2021_rows_rejected():
    o = pd.concat([obs_rows("cpi_food_yoy_pct", {T0 - 1: 99.0}), obs_rows("cpi_food_yoy_pct", {T0 + i: float(i) for i in range(10)})])
    clean, _, log = F3.validate_inputs(o, empty_ann())
    assert log["pre2021_rows_rejected"] == 5 and (clean["period"] >= T0).all()
    ann = pd.DataFrame([{"feature": "provincial_unemployment_rate_pct_annual", "unit": u, "ref": "2020", "value": 1, "avail": "2021-06-30", "status": "r", "source": "t"} for u in PROVS])
    _, a2, log2 = F3.validate_inputs(clean, ann)
    assert log2["pre2021_annual_rows_rejected"] == 5 and a2.empty


@pytest.mark.parametrize("name", ["sws_balance_luzon_total", "H1_bl_latest", "hunger_share", "firi_v2_score"])
def test_target_and_index_series_refused(name):
    o = obs_rows(name, {T0: 1.0}, units=("Cavite",))
    with pytest.raises(ValueError):
        F3.validate_inputs(o, empty_ann())


def test_no_feature_uses_target_or_index():
    assert not any(any(k in f.series.lower() for k in F3.FORBIDDEN) for f in F3.FEATURES)
    assert len(F3.FEATURES) == 34 and set(F3.INDICATORS) == {"FMA", "AFP", "CEC", "EHS", "PSV", "FIS"}


def test_missing_never_zero():
    o = obs_rows("cpi_food_yoy_pct", {T0 + i: float(i) for i in range(10)}, units=PROVS[:2])
    fs = F3.feature_scores(o, empty_ann(), [T0 + 10])
    m = fs[fs["feature"] == "FMA_food_cpi"].set_index("unit")
    assert m.loc["Batangas", "status"] == "missing" and pd.isna(m.loc["Batangas", "score"])
    assert (fs.loc[fs["status"] != "rule_unverified", "score"].isna()).all()


def test_deterministic():
    o = obs_rows("cpi_food_yoy_pct", {T0 + i: float((i * 7) % 5) for i in range(12)})
    a = F3.compute(o, empty_ann(), range(T0, T0 + 12))
    b = F3.compute(o.sample(frac=1, random_state=3), empty_ann(), range(T0, T0 + 12))
    for k in ("features", "overall"):
        assert a[k].to_csv(index=False) == b[k].to_csv(index=False)


# ------------------------------------------------------------------------------------------------ FIRI v2 isolation
def test_firi3_independent_of_firi_v2():
    src = Path(F3.__file__).read_text(encoding="utf-8")
    assert "import firi " not in src and "from app.ml.inference import firi" not in src and "firi as FI" not in src


def test_firi_v2_regression_unchanged():
    from app.ml.inference import firi as FI
    raw = {k: {"x": v, "status": "observed" if v is not None else "missing", "note": ""} for k, v in
           {"A1": .7, "A2": 1.2, "A3": 3.0, "V1": .4, "C1": 0.0, "C2": 2.0, "C3": -5.0, "C4": 1.0, "E1": .3, "E2": -2.0, "N1": None, "H1": .6}.items()}
    prior = {k: [float(i) for i in range(-5, 10)] for k in FI.CONTINUOUS}
    r = FI.score_v2(raw, prior, {"A": .5, "C": 1.5, "H": 1.0, "V": .5})
    assert r["firi"] == pytest.approx(0.3929012345679012, abs=1e-15) and r["class"] == "LOW"
    assert (FI.THRESHOLD, FI.MIN_DOMAINS, len(FI.LABELS)) == (0.5, 4, 12)


def test_firi_v2_files_unchanged():
    root = Path(__file__).resolve().parents[2]
    expect = {"app/ml/inference/firi.py": "0e583131a7de3b9844241d3927eede813077d7cccbf949cd8313973436d0f8e3",
              "data/thesis/firi2_history.csv": "b84558def7a00d4f077c0206d9c9cb6e9df3ef1fa02125fe0141f263ebb753ad",
              "data/thesis/firi2_reference.json": "25af6411488563d0b5782aa9ac05792be79d4880399d18558a63203a44860189"}
    for p, h in expect.items():
        f = root / p
        if not f.exists():
            pytest.skip(f"{p} not present")
        data = f.read_bytes().replace(b"\r\n", b"\n") if p.endswith(".py") else f.read_bytes()
        assert hashlib.sha256(data).hexdigest() == h or hashlib.sha256(f.read_bytes()).hexdigest() == h, p
