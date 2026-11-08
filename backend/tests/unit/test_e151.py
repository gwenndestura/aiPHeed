"""E151 leakage and attribution tests on small synthetic frames and on the built outputs when present."""
import numpy as np
import pandas as pd
import pytest

from app.e148 import panel as Pn
from app.e151 import OUT, RAW


def test_issue_date_is_first_day_of_quarter():
    assert Pn.q_start(2021 * 4 + 1) == pd.Timestamp("2021-04-01")


def test_attribution_levels():
    from app.e151.corpus import attribute

    d = pd.DataFrame([
        {"id": "a", "title": "Food packs reach Batangas families", "text": "Food packs reach Batangas families. Relief was sent.", "body": "", "link": ""},
        {"id": "b", "title": "Rice prices rise nationwide", "text": "Rice prices rise nationwide. The Department of Agriculture said.", "body": "", "link": ""},
        {"id": "c", "title": "Hunger in Somalia worsens", "text": "Hunger in Somalia worsens. Drought continues.", "body": "", "link": ""},
        {"id": "d", "title": "Floods in Calabarzon", "text": "Floods in Calabarzon hit farms.", "body": "", "link": ""},
        {"id": "e", "title": "Quezon City market prices", "text": "Quezon City market prices rise.", "body": "", "link": ""},
        {"id": "f", "title": "Cainta floods", "text": "Cainta floods again.", "body": "", "link": ""},
    ])
    r = attribute(d).set_index("id")
    assert r.at["a", "geo_level"] == "province" and r.at["a", "provinces"] == "batangas"
    assert r.at["b", "geo_level"] == "national"
    assert r.at["c", "geo_level"] == "international"
    assert r.at["d", "geo_level"] == "region_iva"
    assert "quezon" not in r.at["e", "provinces"].split("|")
    assert r.at["f", "provinces"] == "rizal"


def test_no_article_after_issue_date_enters_a_window():
    from app.e151 import features as F

    n = 400
    d = pd.DataFrame({"published": pd.date_range("2016-01-01", periods=n, freq="7D"), "site": "x", "id": [str(i) for i in range(n)]})
    for c in [f"v_{g}" for g in F.GROUPS] + ["v_hunger", "v_net"]:
        d[c] = 0.0
    cut = pd.Timestamp("2020-01-01")
    d.loc[d["published"] >= cut, "v_net"] = 100.0             # a future spike must not appear
    st = pd.DataFrame({"j": d.index, "stream": "all"})
    r = F._window(d, st, 2020 * 4, 0, {})
    assert r and abs(r[0]["e_net"]) < 1e-9


def test_outlet_centring_removes_outlet_level():
    from app.e151 import features as F

    n = 400
    d = pd.DataFrame({"published": pd.date_range("2016-01-01", periods=n, freq="5D"), "id": [str(i) for i in range(n)]})
    d["site"] = np.where(np.arange(n) % 2 == 0, "a", "b")
    for c in [f"v_{g}" for g in F.GROUPS] + ["v_hunger", "v_net"]:
        d[c] = 0.0
    d.loc[d["site"] == "a", "v_net"] = 1.0                    # a permanently gloomier outlet carries no change signal
    st = pd.DataFrame({"j": d.index, "stream": "all"})
    r = F._window(d, st, 2020 * 4, 0, {})
    assert abs(r[0]["e_net"]) < 1e-9


def test_screen_uses_only_given_rows():
    from app.e151.sws import _screen

    r = np.random.default_rng(1)
    t = pd.DataFrame({"lead": 1, "area": np.tile(["a", "b"], 40), "sws_last": r.normal(size=80), "good": r.normal(size=80), "bad": r.normal(size=80)})
    t["dy"] = 2 * t["good"] + r.normal(scale=0.1, size=80)
    assert "good" in _screen(t, ["good", "bad"])


@pytest.mark.skipif(not (OUT / "sws_predictions.csv").exists(), reason="outputs not built")
def test_sws_forecasts_never_train_on_unpublished_outcomes():
    p = pd.read_csv(OUT / "sws_predictions.csv")
    assert (p["T"] > p["qi"]).all()
    assert set(p["set"]) <= {"development", "confirmation"}


@pytest.mark.skipif(not (RAW / "stories.parquet").exists(), reason="stories not built")
def test_stories_exclude_international_and_survey_reports():
    from app.e145.news import SURVEY_RX

    d = pd.read_parquet(RAW / "stories.parquet", columns=["geo_level", "title"])
    assert (d["geo_level"] != "international").all()
    assert not d["title"].str.contains(SURVEY_RX).any()


def test_score_is_not_rescaled():
    """D4: the target is the published moderate plus severe figure, passed through the logit and nothing else."""
    from app.e151.prov import target_rows

    r = target_rows()
    assert ((100 / (1 + np.exp(-r["y"]))) - r["p"]).abs().max() < 1e-6


@pytest.mark.skipif(not (OUT / "gates.json").exists(), reason="outputs not built")
def test_gates_file_is_consistent_with_predictions():
    import json

    g = json.loads((OUT / "gates.json").read_text())
    p = pd.read_csv(OUT / "prov_oof.csv")
    x = p[p["lead"] == 1]
    acc = ((x["GNT"] >= 0.5) == (x["y_high"] == 1)).mean()
    assert abs(g["pool"]["R1_accuracy_ge_75"]["value"] - acc) < 1e-9
    assert g["all_pass"] is False
