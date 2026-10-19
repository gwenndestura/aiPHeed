"""
GET /api/v1/search: forgiving place search for the map (app/services/search.py).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.search import normalise

client = TestClient(app)


def hits(q: str, **params) -> list[dict]:
    r = client.get("/api/v1/search", params={"q": q, **params})
    assert r.status_code == 200
    return r.json()["data"]


def names(q: str, **params) -> list[str]:
    return [h["name"] for h in hits(q, **params)]


# --- normalising ------------------------------------------------------------

def test_normalise_drops_accents_punctuation_and_place_words():
    assert normalise("Biñan") == "binan"
    assert normalise("  Los   Baños, ") == "los banos"
    assert normalise("City of Lipa") == "lipa"
    assert normalise("Lipa City") == "lipa"
    assert normalise("Municipality of Infanta") == "infanta"
    assert normalise("Quezon Province") == "quezon"
    assert normalise("Sto. Tomas") == "santo tomas"
    assert normalise("sta rosa") == "santa rosa"
    assert normalise("Jala-Jala") == "jala jala"


# --- matching ---------------------------------------------------------------

def test_exact_name_comes_first():
    assert names("Calamba")[0] == "Calamba"
    assert names("tayabas")[0] == "Tayabas"


def test_prefix():
    assert names("calam")[0] == "Calamba"
    assert "Laguna" in names("lagu")


def test_accents_binan_and_dasmarinas():
    assert names("binan")[0] == "Biñan"
    assert names("dasmarinas")[0] == "Dasmariñas"
    assert names("los banos")[0] == "Los Baños"


def test_city_words_are_ignored():
    for q in ("lipa city", "city of lipa", "Lipa City", "municipality of lipa"):
        assert names(q)[0] == "Lipa", q


def test_one_letter_typo():
    assert names("tagaytai")[0] == "Tagaytay"
    assert names("tayabass")[0] == "Tayabas"
    assert names("dasmarinyas")[0] == "Dasmariñas"


def test_sta_and_sto():
    assert names("sta rosa")[0] == "Santa Rosa"
    assert names("sta. cruz")[0] == "Santa Cruz"
    assert names("santo tomas")[0] == "Sto. Tomas"
    assert names("sto tomas")[0] == "Sto. Tomas"


def test_ranking_order():
    # exact, then starts with, then a word starts with, then contains
    got = names("san", limit=50)
    assert got[0].startswith("San ")
    # province before the city of the same name...
    assert names("batangas")[:2] == ["Batangas", "Batangas City"]
    assert names("cavite")[:2] == ["Cavite", "Cavite City"]
    # ...unless "city" was typed
    assert names("batangas city")[:2] == ["Batangas City", "Batangas"]
    # starts with ("Rosario") before a word starts with ("Santa Rosa")
    got = names("rosa", limit=50)
    assert got.index("Rosario") < got.index("Santa Rosa")
    # a word starts with, before only containing it
    got = names("pablo", limit=50)
    assert got[0] == "San Pablo"


def test_limit_defaults_to_eight_and_is_respected():
    assert len(hits("a")) == 8
    assert len(hits("a", limit=3)) == 3
    assert len(hits("a", limit=50)) == 50


def test_nonsense_returns_no_unrelated_places():
    for q in ("qqqzzx", "hello", "xyz", "zzzzzzzz", "!!!"):
        assert hits(q) == [], q


def test_no_close_match_gives_flagged_suggestions():
    got = hits("imis")
    assert got and all(h["suggestion"] for h in got)
    assert got[0]["name"] == "Imus"
    assert not any(h["suggestion"] for h in hits("imus"))


def test_results_carry_type_classification_and_province():
    province = hits("laguna")[0]
    assert province == {
        "type": "province", "id": "laguna", "name": "Laguna", "classification": "Province",
        "provinceId": None, "provinceName": None, "suggestion": False,
    }
    city = hits("tagaytay")[0]
    assert (city["type"], city["classification"], city["provinceId"], city["provinceName"]) == ("municipality", "City", "cavite", "Cavite")
    town = hits("infanta")[0]
    assert (town["classification"], town["provinceName"], town["id"]) == ("Municipality", "Quezon", "quezon-infanta")
