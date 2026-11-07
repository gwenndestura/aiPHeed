"""E171 (exploratory) unit tests: the SWS trend inputs use only quarters published before the issue date; candidate learners behave."""
import numpy as np
import pandas as pd

from app.e148 import panel as Pn
from app.e171 import candidates as C


def _sw():
    rows = []
    for a in C.AREAS:
        for k, qi in enumerate(range(8040, 8090)):
            rows.append({"area": a, "qi": qi, "hunger": 10.0 + k * 0.1, "published": Pn.q_start(qi) + pd.Timedelta(days=45)})
    return pd.DataFrame(rows)


def _rows(i=8072, an=8062):
    return pd.DataFrame({"i": [i, i], "rq_anchor": [an, an], "sws_area": ["visayas", "mindanao"]})


def test_sws_inputs_ignore_quarters_published_after_the_issue_date():
    sw = _sw()
    base = C.add_sws(_rows(), sw)
    late = sw.copy()
    late.loc[late["published"] >= Pn.q_start(8072), "hunger"] = 999.0     # any value published at or after the cut
    assert np.allclose(C.add_sws(_rows(), late)[C.S_COLS].values, base[C.S_COLS].values)


def test_sws_since_is_change_from_the_anchor_year_and_national_is_shared():
    d = C.add_sws(_rows(), _sw())
    assert (d["sws_since"] > 0).all()                                      # the synthetic series rises
    assert d["sws_nat_since"].nunique() == 1                               # national input: one value for every province


def test_lead_band_falls_back_to_all_rows_when_too_few():
    rng = np.random.default_rng(0)
    n = 80
    d = pd.DataFrame({"x": rng.normal(size=n), "e": rng.normal(size=n), "se_true": 0.3, "region": rng.integers(0, 5, n).astype(str),
                      "gap_q": 4, "lead": np.r_[np.ones(10), np.full(n - 10, 7)]})
    C.LEAD_NOW["v"] = 1
    m = C.LeadBand(["x"]).fit(d)                                           # only 10 rows near lead 1 -> uses all 80
    assert len(m.gap_) == n


def test_trend_learner_recovers_a_linear_trend():
    rng = np.random.default_rng(1)
    n = 200
    d = pd.DataFrame({"sws_since": rng.normal(size=n), "sws_nat_since": rng.normal(size=n), "x": rng.normal(size=n), "se_true": 0.3,
                      "region": rng.integers(0, 5, n).astype(str), "gap_q": 4})
    d["e"] = 0.5 * d["sws_since"] + rng.normal(scale=0.05, size=n)
    m = C.TrendRes(["x"]).fit(d)
    assert abs(m.b_[1] - 0.5) < 0.05


def test_families_and_menu_are_the_protocol_ones():
    assert len(C.FAMILIES["E171"]) == 32 and C.FAMILIES["E168TA"] == [(a, "LGBM", f) for a in C.U.ANCH for f in ("GOV", "FULL")]
    assert all(C.Pv.SIGN[c] == 1 for c in C.S_COLS)
