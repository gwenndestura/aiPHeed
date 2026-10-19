"""
app/services/search.py
-----------------------
Place search for the map: the five provinces and 142 cities and
municipalities, matched forgivingly.

Names and queries are normalised the same way (lower case, accents removed,
punctuation and extra spaces dropped, "city", "city of", "municipality of"
and "province" ignored, "sta"/"sto" read as "santa"/"santo"), then ranked:

  0  exact name
  1  name starts with the query
  2  a word in the name starts with the query
  3  name contains the query
  4  close spelling (difflib), for typos

Provinces come before cities and municipalities at the same rank. When
nothing matches, the closest few names come back as suggestions.

Standard library only; the names come from app.services.reference.
"""

from __future__ import annotations

import difflib
import functools
import re
import unicodedata
from dataclasses import dataclass

from app.services import reference as ref

# Typos: "tagaytai" -> Tagaytay is 0.875. Unrelated words stay far below.
TYPO_MIN_RATIO = 0.78
# A typo in the first part of a longer name being typed ("dasmarinyas",
# "general tria"): stricter, and only for queries of 5+ letters, or short
# queries would match the start of many names ("binan" -> "indan…").
TYPO_START_MIN_RATIO = 0.86
# "Did you mean": looser, only used when nothing matched at all.
SUGGEST_MIN_RATIO = 0.6
SUGGEST_MAX = 3
DEFAULT_LIMIT = 8

_FILLER = re.compile(r"\b(?:city of|municipality of|province of|city|municipality|province)\b")
_ABBREV = {"sta": "santa", "sto": "santo"}


def normalise(text: str) -> str:
    """'Sto. Tomas' -> 'santo tomas'; 'City of Biñan' -> 'binan'."""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = _FILLER.sub(" ", t)
    words = [_ABBREV.get(w, w) for w in t.split()]
    return " ".join(words)


@dataclass(frozen=True)
class Place:
    type: str              # "province" | "municipality"
    id: str
    name: str
    classification: str    # "Province" | "City" | "Municipality"
    province_id: str | None
    province_name: str | None
    keys: tuple[str, ...]  # normalised name and aliases


@functools.lru_cache(maxsize=1)
def places() -> tuple[Place, ...]:
    """Every searchable place, provinces first."""
    out: list[Place] = [
        Place("province", slug, meta["name"], "Province", None, None, (normalise(meta["name"]),))
        for slug, meta in ref.PROVINCES.items()
    ]
    roster = ref.lgu_roster()
    for _, r in roster.iterrows():
        names = [r["lgu_name"]]
        aliases = r.get("lgu_aliases")
        if isinstance(aliases, str):
            names += [a for a in aliases.split("|") if a.strip()]
        keys = tuple(dict.fromkeys(k for k in (normalise(n) for n in names) if k))
        out.append(Place(
            "municipality", r["id"], r["lgu_name"],
            "City" if str(r["lgu_type"]).lower() == "city" else "Municipality",
            r["provinceId"], r["province_name"], keys,
        ))
    return tuple(out)


def _rank(query: str, key: str) -> tuple[int, float] | None:
    """(rank, closeness) of one name against the query, or None."""
    if key == query:
        return 0, 1.0
    if key.startswith(query):
        return 1, len(query) / len(key)
    if any(w.startswith(query) for w in key.split()) or f" {query}" in f" {key}":
        return 2, len(query) / len(key)
    if query in key:
        return 3, len(query) / len(key)
    # Typos: against the whole name, and against its start (a typo in a
    # longer name being typed, e.g. "dasmarinyas" or "general tria").
    ratio = difflib.SequenceMatcher(None, query, key).ratio()
    if ratio >= TYPO_MIN_RATIO:
        return 4, ratio
    if len(query) >= 5 and len(key) > len(query):
        start = difflib.SequenceMatcher(None, query, key[: len(query)]).ratio()
        if start >= TYPO_START_MIN_RATIO:
            return 4, start
    return None


def _closeness(query: str, place: Place) -> float:
    return max(difflib.SequenceMatcher(None, query, k).ratio() for k in place.keys)


def _hit(place: Place, suggestion: bool = False) -> dict:
    return {
        "type": place.type,
        "id": place.id,
        "name": place.name,
        "classification": place.classification,
        "provinceId": place.province_id,
        "provinceName": place.province_name,
        "suggestion": suggestion,
    }


def search(q: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Ranked places for `q`; suggestions (flagged) when nothing matches."""
    query = normalise(q)
    if not query:
        return []
    # Typed "city" ("batangas city", "city of lipa"): a city is meant, so at
    # the same rank it comes before the province of the same name.
    wants_city = bool(re.search(r"\bcity\b", q.lower()))

    scored = []
    for order, place in enumerate(places()):
        best = None
        for key in place.keys:
            r = _rank(query, key)
            if r and (best is None or (r[0], -r[1]) < (best[0], -best[1])):
                best = r
        if best is None:
            continue
        type_order = 0 if place.type == "province" else 1
        if wants_city:
            type_order = 0 if place.classification == "City" else 1 if place.type == "province" else 2
        scored.append((best[0], type_order, -best[1], place.name.lower(), order, place))

    if scored:
        scored.sort(key=lambda s: s[:5])
        return [_hit(s[-1]) for s in scored[:limit]]

    # Nothing close enough: the nearest few, offered as "Did you mean".
    near = sorted(((_closeness(query, p), i, p) for i, p in enumerate(places())), key=lambda t: (-t[0], t[1]))
    return [_hit(p, suggestion=True) for ratio, _, p in near[:SUGGEST_MAX] if ratio >= SUGGEST_MIN_RATIO]
