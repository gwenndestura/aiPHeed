"""
tests/unit/test_e122_cutoff.py
------------------------------
E122 cutoff and point-in-time rules of FIRI3 (Amendment 1): pre-2021 rows, lags, windows, YoY bases and percentile
references never enter; the >= 8 history rule; availability before the issue; no future rows; annual latest year;
provincial / regional separation; national values never copied into provinces; determinism; FIRI v2 untouched.
Plus the real-data audit outputs (traceability, re-derivation) when present.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.inference import firi3 as F3

T0 = F3.START_Q
PROVS = F3.PROVINCES
REPO = Path(__file__).resolve().parents[2].parent
AUD = REPO / "aipheed-backend-aligned" / "experiments" / "E122_Data_Cutoff_Audit"


def rows(series, values, units=PROVS, lag=1, status="rule_unverified"):
    out = []
    for p, v in values.items():
        for u in units:
            out.append({"feature": series, "unit": u, "period": p, "value": v[u] if isinstance(v, dict) else v,
                        "avail": F3.issue_date(p + lag - 1), "status": status, "source": "t"})
    return pd.DataFrame(out)


def empty_ann():
    return pd.DataFrame(columns=["feature", "unit", "ref", "value", "avail", "status", "source"])


def feat(code):
    return next(f for f in F3.FEATURES if f.code == code)


def test_amendment_hash():
    p = AUD / "E122_FIRI3_PROTOCOL_AMENDMENT_1.md"
    if not p.exists():
        pytest.skip("amendment file not present")
    assert hashlib.sha256(p.read_bytes()).hexdigest() == F3.AMENDMENT_1_SHA256


# 1 pre-2021 raw observation exclusion
def test_pre2021_raw_rows_excluded():
    o = pd.concat([rows("typhoons_local_100km", {T0 - 4: 9.0, T0 - 1: 9.0}), rows("typhoons_local_100km", {T0 + i: float(i % 3) for i in range(12)})])
    clean, _, log = F3.validate_inputs(o, empty_ann())
    assert log["pre2021_rows_rejected"] == 10 and clean["period"].min() == T0


# 2-4 lags, windows and YoY bases: a change-type value needs a 2021+ base, so 2021 change rows never enter
@pytest.mark.parametrize("series", sorted(F3.BASE_REQUIRED))
def test_2021_change_rows_rejected(series):
    o = rows(series, {T0 + i: float(i) for i in range(10)})
    clean, _, log = F3.validate_inputs(o, empty_ann())
    assert log["pre2021_base_rows_rejected"] == 4 * 5 and clean["period"].min() == F3.FIRST_CHANGE_Q


def test_level_series_keep_2021():
    for s in F3.LEVEL_SERIES:
        clean, _, log = F3.validate_inputs(rows(s, {T0: 1.0}), empty_ann())
        assert log["pre2021_base_rows_rejected"] == 0 and len(clean) == 5


# 5 normalization references: a 2021 change row cannot be a percentile reference
def test_2021_yoy_rejected_before_normalization():
    vals = {T0 + i: (100.0 if i < 4 else float(i)) for i in range(14)}          # 2021 values extreme
    o = rows("cpi_food_yoy_pct", vals)
    res = F3.compute(o, empty_ann(), [T0 + 13])["features"]
    r = res[(res["feature"] == "FMA_food_cpi") & (res["unit"] == "Cavite")].iloc[0]
    assert r["period"] == F3.qlabel(T0 + 12) and r["prior_n"] == 5 * 8             # references: 2022-Q1..T0+11 only (2021 rows rejected)
    assert r["score"] == 1.0                                                        # with 100s admitted it would not be the maximum


# 6 minimum eight earlier observations
def test_min_eight_history():
    o = rows("typhoons_PAR", {T0 + i: float(i) for i in range(8)}, units=("PHILIPPINES",))
    f = feat("CEC_cyclones_R")
    assert F3._dynamic(o, f, T0 + 8)[0]["status"] == "insufficient_history"         # current T0+7, 7 earlier values
    o = rows("typhoons_PAR", {T0 + i: float(i) for i in range(9)}, units=("PHILIPPINES",))
    r = F3._dynamic(o, f, T0 + 9)[0]                                                 # current T0+8 (published at T0+9's start, before the issue)
    assert r["prior_n"] == 8 and r["score"] == 1.0


# 7-9 availability before the issue; publication dates; no future rows
def test_issue_date_availability_and_future_rows():
    o = rows("typhoons_PAR", {T0 + i: float(i) for i in range(12)}, units=("PHILIPPINES",), lag=1)
    late = rows("typhoons_PAR", {T0 + 11: 99.0}, units=("PHILIPPINES",), lag=5)       # same period, published much later
    f = feat("CEC_cyclones_R")
    r = F3._dynamic(pd.concat([o[o["period"] < T0 + 11], late]), f, T0 + 11)[0]
    assert r["period"] == F3.qlabel(T0 + 10)                                       # the late row is not yet published at the issue
    fut = rows("typhoons_PAR", {T0 + 20: 50.0}, units=("PHILIPPINES",))
    r2 = F3._dynamic(pd.concat([o, fut]), f, T0 + 11)[0]
    assert r2["period"] == F3.qlabel(T0 + 10) and r2["aligned_value"] != 50.0
    assert r2["avail_date"] < F3.issue_date(T0 + 11)


def test_percentile_reference_excludes_current_and_unpublished():
    o = rows("typhoons_PAR", {T0 + i: float(i) for i in range(12)}, units=("PHILIPPINES",))
    r = F3._dynamic(o, feat("CEC_cyclones_R"), T0 + 11)[0]
    assert r["prior_n"] == 10                                                       # periods T0..T0+9; current T0+10 excluded


# 10 annual: latest published year; an incomplete latest year is not used (frozen rule; fallback is DI-3, not applied)
def test_annual_latest_year_and_incomplete():
    def ann(year, units, avail):
        return pd.DataFrame([{"feature": "provincial_unemployment_rate_pct_annual", "unit": u, "ref": str(year), "value": float(i), "avail": avail, "status": "r", "source": "t"}
                             for i, u in enumerate(units)])
    a = pd.concat([ann(2023, PROVS, "2024-06-30"), ann(2024, PROVS, "2025-06-30")])
    f = feat("EHS_unemployment_prov")
    assert {r["period"] for r in F3._rank5(a, f, F3.qindex("2025-Q1"))} == {"2023"}  # 2024 not yet published (issue 2025-04-01)
    assert {r["period"] for r in F3._rank5(a, f, F3.qindex("2025-Q3"))} == {"2024"}
    a2 = pd.concat([a, ann(2025, PROVS[:4], "2026-06-30")])
    r = F3._rank5(a2, f, F3.qindex("2026-Q3"))
    assert all(x["status"] == "incomplete_year" and x["score"] is None for x in r)
    fs = F3.feature_scores(pd.DataFrame(columns=["feature", "unit", "period", "value", "avail", "status", "source"]), a, [F3.qindex("2025-Q3")])
    assert fs.loc[fs["feature"] == "EHS_unemployment_prov", "period"].str.fullmatch(r"\d{4}").all()   # a year, never a quarter


# 11-13 geography
def test_provincial_and_regional_separation():
    o = pd.concat([rows("palay_production_yoy_pct", {T0 + 4 + i: float(i) for i in range(10)}),
                   rows("palay_production_yoy_pct", {T0 + 4 + i: 100.0 + i for i in range(10)}, units=("Region IV-A",))])
    fs = F3.compute(o, empty_ann(), [T0 + 14])["features"]
    p = fs[fs["feature"] == "AFP_palay"]
    rg = fs[fs["feature"] == "AFP_palay_R"]
    assert set(p["unit"]) == set(PROVS) and (p["aligned_value"].abs() < 100).all()  # provincial rows never read the regional series
    assert set(rg["unit"]) == {F3.REGION_LABEL} and (rg["aligned_value"].abs() >= 100).all()


def test_national_not_replicated_into_provinces():
    o = rows("E1_unemployment_change_pp", {T0 + 4 + i: float(i) for i in range(10)}, units=("PHILIPPINES",))
    fs = F3.compute(o, empty_ann(), [T0 + 14])["features"]
    assert fs[(fs["scope"] == "provincial") & fs["feature"].str.startswith("EHS")]["score"].isna().all()
    assert not any(f.scope == "P" and f.series == "E1_unemployment_change_pp" for f in F3.FEATURES)
    with pytest.raises(ValueError):
        F3.validate_inputs(rows("cpi_food_yoy_pct", {T0 + 4: 1.0}, units=("Metro Manila",)), empty_ann())


# 15 determinism
def test_deterministic_under_row_order():
    o = rows("rice_wholesale_yoy_pct", {T0 + 4 + i: float((i * 5) % 7) for i in range(12)})
    a = F3.compute(o, empty_ann(), range(T0, T0 + 16))
    b = F3.compute(o.iloc[::-1], empty_ann(), range(T0, T0 + 16))
    assert a["features"].to_csv(index=False) == b["features"].to_csv(index=False)


# 16 FIRI v2 regression
def test_firi_v2_untouched():
    from app.ml.inference import firi as FI
    raw = {k: {"x": v, "status": "observed" if v is not None else "missing", "note": ""} for k, v in
           {"A1": .7, "A2": 1.2, "A3": 3.0, "V1": .4, "C1": 0.0, "C2": 2.0, "C3": -5.0, "C4": 1.0, "E1": .3, "E2": -2.0, "N1": None, "H1": .6}.items()}
    r = FI.score_v2(raw, {k: [float(i) for i in range(-5, 10)] for k in FI.CONTINUOUS}, {"A": .5, "C": 1.5, "H": 1.0, "V": .5})
    assert r["firi"] == pytest.approx(0.3929012345679012, abs=1e-15)


# 14 and real-data audit (when the E122 outputs exist)
@pytest.mark.skipif(not (AUD / "out" / "summary.json").exists(), reason="E122 outputs missing")
def test_real_data_audit_outputs():
    s = json.loads((AUD / "out" / "summary.json").read_text())
    assert all(s["checks"].values()), s["checks"]
    assert s["log"]["pre2021_base_rows_rejected"] == 40
    tr = pd.read_csv(AUD / "E122_FINAL_SCORE_TRACEABILITY.csv")
    ok = tr[tr["status"] == "computed"]
    assert ok["reproduces"].all() and ok["all_inputs_2021_plus"].all() and ok["all_inputs_available_before_issue"].all()
    assert (ok["earliest_observation_used"].astype(str) >= "2021").all()
    fa = pd.read_csv(AUD / "E122_FEATURE_CUTOFF_AUDIT.csv")
    assert len(fa) == len(F3.FEATURES) and (fa["audit_status"] == "PASS").all()
    assert not fa["pre2021_influence"].any() and not fa["future_influence"].any()
    rd = pd.read_csv(AUD / "out" / "independent_rederivation.csv")
    assert rd["agrees"].all()
    for d in (AUD / "snapshots").iterdir():
        man = json.loads((d / "manifest.json").read_text())
        assert man["amendment_1_sha256"] == F3.AMENDMENT_1_SHA256
        for name, h in man["files"].items():
            assert hashlib.sha256((d / name).read_bytes()).hexdigest() == h
