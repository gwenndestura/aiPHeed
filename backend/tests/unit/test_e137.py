"""E137 survey-anchored risk model: outcome rules (uncertainty classes, pooled reference, HFIAS only), release-date
cutoffs of the features, fold isolation, the protocol lock and the registry status."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app import registry as R
from app.e137 import RAW, outcomes as O
from app.e137 import evaluate as E
from app.e137 import features as F

D = O.load()


def test_status_never_forces_uncertain_rows():
    s = O.status([0.5, -0.5, 0.05, 0.5, 0.5], [0.1, 0.1, 0.1, 0.1, np.nan], [3, 3, 3, 12, 3], [True, True, True, True, True])
    assert list(s) == ["ELEVATED", "LOWER", "NOT_DISTINGUISHABLE", "INSUFFICIENT", "INSUFFICIENT"]


def test_outcome_counts_and_reference():
    v = D[D["has_value"]]
    assert len(v) == 125 and set(D["survey"]) == {"FNRI2015", "ENNS2018", "ENNS2019"}
    assert v["q"].notna().all()                                   # wide-interval rows keep their soft label
    assert D.loc[D["survey"] != "FNRI2015", "ref"].round(1).eq(42.8).all()     # pooled 2018-2019 ENNS national
    assert D.loc[D["survey"] == "FNRI2015", "ref"].eq(53.8).all()
    assert (D["status"] == "INSUFFICIENT").sum() == 30 and D["status"].isin(["ELEVATED", "LOWER"]).sum() == 62


def test_mod_sev_is_hfias_moderate_plus_severe_not_fies():
    q = D[(D["province"] == "Quezon") & (D["survey"] == "ENNS2019")].iloc[0]
    assert q["p"] == pytest.approx(44.0)                          # 30.3 + 13.7 (FIES in the same deck is 32.2)
    lag = D[(D["province"] == "Laguna") & (D["survey"] == "ENNS2018")].iloc[0]
    assert lag["p"] == pytest.approx(26.2)                        # 18.3 + 7.9: the workbook's 18.3 is "moderate" only


def test_issue_dates_and_poverty_round_rule():
    assert F.issue_date(2015, 0) == pd.Timestamp("2015-07-01") and F.issue_date(2018, 4) == pd.Timestamp("2017-07-01")
    assert F._latest([2006, 2009, 2012, 2015], pd.Timestamp("2015-07-01")) == 2012
    assert F._latest([2006, 2009, 2012, 2015], pd.Timestamp("2016-12-31")) == 2012
    assert F._latest([2006, 2009, 2012, 2015], pd.Timestamp("2017-01-01")) == 2015


def test_quarterly_production_uses_published_quarters_only():
    cols = ["2015 Quarter 1", "2015 Quarter 2", "2015 Quarter 3"]
    assert F._published_quarters(cols, pd.Timestamp("2015-07-01")) == ["2015 Quarter 1"]   # Q2 public 14 Aug
    assert F._published_quarters(cols, pd.Timestamp("2015-08-15")) == ["2015 Quarter 1", "2015 Quarter 2"]


def test_cpi_feature_ignores_unpublished_year(monkeypatch):
    k, issue = "batangas", pd.Timestamp("2015-02-14")            # 2014 annual CPI is public on 15 Feb 2015
    a = F.row_features(k, issue, None)["m_food_cpi_yoy"]
    mod = F._cpi().copy()
    mod.loc[mod["k"] == k, "Annual 2014"] = 999.0
    monkeypatch.setattr(F, "_cpi", lambda: mod)
    assert F.row_features(k, issue, None)["m_food_cpi_yoy"] == pytest.approx(a)
    assert F.row_features(k, pd.Timestamp("2015-02-15"), None)["m_food_cpi_yoy"] != pytest.approx(a)


@pytest.mark.skipif(not (RAW / "ibtracs" / "ibtracs.WP.list.v04r01.csv").exists(), reason="IBTrACS not downloaded")
def test_storm_count_is_before_issue_date():
    hits = F._storm_hits("leyte")
    issue = pd.Timestamp("2013-11-01")                            # Haiyan (8 Nov 2013) must not count
    n = F.row_features("leyte", issue, None)["c_tc_4q"]
    assert n == ((hits["t"] < issue) & (hits["t"] >= issue - pd.Timedelta(days=365))).sum()
    assert F.row_features("leyte", pd.Timestamp("2013-12-01"), None)["c_tc_4q"] >= n + 1


def test_v1_folds_keep_a_province_in_one_region():
    v = D[D["has_value"]]
    assert v.groupby("key")["region"].nunique().max() == 1


def test_protocol_lock_matches_code():
    E.verify_lock()


def test_e137_is_rejected_and_not_in_production():
    reg = R.load()
    m = reg["models"]["e137-sarf-1.0"]
    assert m["status"] == "rejected" and m["gate"]["passed"] is False
    assert (reg.get("production") or {}).get("model_id") != "e137-sarf-1.0"
