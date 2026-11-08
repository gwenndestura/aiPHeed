"""E152 leakage tests on synthetic series and on the built panel."""
import numpy as np
import pandas as pd
import pytest

from app.e152 import panel as Pa


def test_window_never_reads_recent_months():
    idx = pd.period_range("2015-01", "2021-12", freq="M")
    s = pd.Series(1.0, index=idx)
    issue = pd.Timestamp("2020-04-01")
    a = Pa.window(s, issue, 3)
    s2 = s.copy()
    s2[s2.index > issue.to_period("M") - Pa.LAG_M] = 999.0
    assert Pa.window(s2, issue, 3) == a


def test_rain_anomaly_never_reads_recent_months():
    idx = pd.period_range("2000-01", "2021-12", freq="M")
    r = np.random.default_rng(1)
    s = pd.Series(r.normal(size=len(idx)), index=idx)
    issue = pd.Timestamp("2020-04-01")
    a = Pa.rain_anom(s, issue, 3)
    s2 = s.copy()
    s2[s2.index > issue.to_period("M") - Pa.LAG_M] = 999.0
    assert Pa.rain_anom(s2, issue, 3) == a


def test_names_match_provinces():
    assert Pa.norm_name("....Tawi-tawi") == "tawi-tawi"
    assert Pa.norm_name("....Sulu a/") == "sulu"
    assert Pa.norm_name("mountain") == "mountain province"
    assert Pa.norm_name("tawi tawi") == "tawi-tawi"


def test_drift_uses_only_newer_rounds_in_same_region():
    from app.e148 import model as M8
    from app.e152.model import SHRINK, drift

    tr = pd.DataFrame({"lead": [1, 1, 1, 1, 2], "region": ["A", "A", "B", "A", "A"], "survey": ["ENNS2018", "ENNS2019", "ENNS2019", "FNRI2015", "ENNS2019"], "e": [1.0, 1.0, 9.0, 9.0, 9.0]})
    te = pd.DataFrame({"region": ["A", "A", "C"], "rq_anchor": [M8.RQ["FNRI2015"], M8.RQ["ENNS2019"], M8.RQ["FNRI2015"]]})
    d = drift(tr, te)
    assert d[0] == pytest.approx(2.0 / (2 + SHRINK))
    assert d[1] == 0.0 and d[2] == 0.0


def test_score_line_is_unchanged():
    from app.e150.issue import expit100

    assert expit100(0.0) == 50.0
