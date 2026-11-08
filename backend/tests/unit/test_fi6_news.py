"""FI6-N news pipeline tests: geography (namesake masks), restated statistics, severity, exclusions, as-of features."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.fi5.paths import LGU_REFERENCE
from app.fi6 import news_events as E
from app.fi6 import news_model as NM


@pytest.fixture(scope="module")
def lgus():
    lg = pd.read_csv(LGU_REFERENCE)
    lg["n"] = lg["lgu_name"].str.lower().str.replace("ñ", "n").str.replace(" city", "", regex=False)
    return lg[lg["n"].str.len() >= 4]


def test_namesakes_are_masked(lgus):
    assert E.geo("Flooding in Quezon City displaces 300 families", lgus)["geo_level"] == "national"
    assert E.geo("Jose Rizal's birthday marked in Manila", lgus)["geo_level"] == "national"
    g = E.geo("Typhoon damages rice farms in Quezon province, Lucena", lgus)
    assert "Quezon" in g["provinces"] and g["geo_level"] == "lgu"


def test_ambiguous_lgu_needs_its_province(lgus):
    assert E.geo("Santa Rosa farmers protest low palay prices", lgus)["geo_level"] == "national"
    assert "Laguna" in E.geo("Santa Rosa, Laguna factory closes", lgus)["provinces"]
    assert E.geo("Antipolo landslide", lgus)["provinces"] == "Rizal"          # distinctive name stands alone


def test_restated_statistics_flagged():
    for t in ["Inflation eases to 3.1% in May - PSA", "Remittance growth steady at 7.4% in August",
              "Unemployment rate falls to 4.5%", "SWS: Hunger rises to 22.6%", "Typhoons push July inflation to 3.2%"]:
        assert E.flags(t)["restated_statistic"], t
    assert not E.flags("Typhoon destroys rice fields in Quezon")["restated_statistic"]


def test_severity_extraction():
    f = E.flags("'Ofel' causes P145.85-M damage to agri; 1,200 families evacuated")
    assert f["damage_pmillion"] == pytest.approx(145.85)
    assert E.flags("Typhoon losses hit P1.2 billion")["damage_pmillion"] == pytest.approx(1200)
    assert f["families_affected"] == 1200
    assert E.flags("Rice prices up P2")["damage_pmillion"] == 0


def test_exclusions():
    assert E.EXCLUDE_TITLE.search("Rappler Newscast | September 18, 2012")
    assert E.EXCLUDE_PATH.search("https://www.rappler.com/sports/12-foo/")
    assert not E.EXCLUDE_PATH.search("https://www.rappler.com/philippines/12-flood-batangas/")
    assert not E.EXCLUDE_TITLE.search("China introduces security review rules for foreign investors")


def test_asof_news_z_uses_only_earlier_quarters(monkeypatch, tmp_path):
    q = [f"{y}-Q{k}" for y in range(2012, 2016) for k in range(1, 5)]
    base = pd.DataFrame({"quarter": q, **{c: np.arange(len(q), dtype=float) for c in NM.NEWS_MAP.values()}})
    f1, f2 = tmp_path / "a.csv", tmp_path / "b.csv"
    base.to_csv(f1, index=False)
    changed = base.copy()
    changed.loc[changed.index[-3:], list(NM.NEWS_MAP.values())] = 999.0     # future quarters altered
    changed.to_csv(f2, index=False)
    monkeypatch.setattr(NM, "FEATURES", f1)
    a = NM.asof_news()
    monkeypatch.setattr(NM, "FEATURES", f2)
    b = NM.asof_news()
    pd.testing.assert_frame_equal(a.iloc[:-3], b.iloc[:-3])                  # earlier quarters unaffected
    assert a.iloc[:NM.MIN_HISTORY][list(NM.NEWS_MAP)].isna().all().all()


def test_news_feature_sets():
    assert set(NM.SETS["gov_plus_news"]) - set(NM.SETS["gov_only"]) == set(NM.NEWSA)
    for d in ["market", "climate", "employment", "remittance", "poverty"]:
        dropped = set(NM.SETS["gov_plus_news"]) - set(NM.SETS[f"minus_{d}_news"])
        assert dropped and all(NM.NEWS_DOMAIN[f] == d for f in dropped)


@pytest.mark.skipif(not (NM.OUT / "forecast_news.json").exists(), reason="run python -m app.fi6.news_model evaluate issue")
def test_news_api_routes():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    for p in ["news/evaluation", "news/forecast", "news/audit", "news/provinces?province=Laguna"]:
        assert c.get(f"/api/v1/fi6/{p}").status_code == 200, p
    ev = c.get("/api/v1/fi6/news/evaluation").json()
    assert set(ev["by_lead"]) == {"1", "2", "3", "4"}
