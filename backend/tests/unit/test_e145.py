"""E145: phrases are uniform, news features never see the future, and the correction removes the volume effect."""
import numpy as np
import pandas as pd

from app.e137 import features as F
from app.e145 import collect as C
from app.e145 import features as X
from app.e145 import news as N


def _articles():
    rows = []
    for k, n, r in (("a", 100, 20), ("b", 10, 2), ("c", 50, 25)):
        for i in range(n):
            rows.append({"key": k, "id": f"{k}{i}", "published": pd.Timestamp("2014-06-01"), "stress": i < r,
                         "stress_score": 0.9 if i < r else 0.1, "gated": True, "hash": f"{k}{i}"})
    return pd.DataFrame(rows)


def test_every_ordinary_province_uses_the_same_two_phrases():
    assert C.queries_for("aklan") == ['"in Aklan"', '"Aklan province"']
    assert C.queries_for("agusan del sur") == ['"in Agusan del Sur"', '"Agusan del Sur province"']
    assert C.queries_for("quezon") == ['"Quezon province"']   # "Quezon" alone is mostly Quezon City


def test_window_excludes_articles_on_or_after_the_issue_date():
    a = _articles()
    late = a.copy()
    late["id"] = "late" + late["id"]
    late["published"] = pd.Timestamp("2015-04-01")           # exactly the issue date
    issue = pd.Timestamp("2015-04-01")
    t0 = X.window_stats(a, ["a", "b", "c"], issue).set_index("key")
    t1 = X.window_stats(pd.concat([a, late]), ["a", "b", "c"], issue).set_index("key")
    assert t0.equals(t1)


def test_window_excludes_articles_older_than_twelve_months():
    a = _articles()
    t = X.window_stats(a, ["a", "b", "c"], pd.Timestamp("2015-07-01")).set_index("key")
    assert t["n"].sum() == 0


def test_correction_is_neutral_for_the_national_rate_at_any_volume():
    """Province a (n=100) and b (n=10) have the same 20 % stress share; shrinkage may move b toward rho, never past it."""
    t = X.window_stats(_articles(), ["a", "b", "c"], pd.Timestamp("2015-04-01")).set_index("key")
    rho = t["r"].sum() / t["n"].sum()
    assert rho > 0.2
    assert t.loc["a", "nb_fssi"] < t.loc["b", "nb_fssi"] < 0
    assert t.loc["c", "nb_fssi"] > 0
    assert abs(t["nb_attention"].mean()) < 1e-9


def test_survey_reports_are_removed_and_gate_handles_filipino():
    assert N.SURVEY_RX.search("SWS: hunger rises in Q2")
    assert N.SURVEY_RX.search("Social Weather Stations poll")
    assert N.GATE_RX.search("Walang makain, gutom ang pamilya")
    assert N.GATE_RX.search("Typhoon damages rice farms")
    assert not N.GATE_RX.search("Basketball team wins in Aklan")


def test_lead_one_is_one_quarter_before_the_target_quarter():
    assert F.issue_date(2015, 1) == pd.Timestamp("2015-04-01")   # issue start of Q2, target Q3
    assert F.issue_date(2015, 4) == pd.Timestamp("2014-07-01")
    assert np.all([F.issue_date(2019, h) < pd.Timestamp("2019-07-01") for h in X.LEADS])
