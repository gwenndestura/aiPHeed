"""E60 news relevance and trigger classifier v2 (rules developed on the DEV annotation half only; EVAL is never read here).

Design, from the trigger definitions and DEV error patterns:
  * a trigger fires on a phrase that describes a food-stress mechanism, not on a bare topic word
    (v1's "flood", "typhoon", "price" fired on flood-control politics, generic weather bulletins and promotions);
  * exclusions remove the DEV false-positive families (flood-control politics/scandal, crime, sports, business
    openings, recipes and promotions, cosmetics);
  * weather forecasts and bulletins count only when they name a CALABARZON place (geocoder) or "CALABARZON";
  * national price/rice measures are relevant but attributed NATIONAL (they enter regional features only).

    from n4_classifier import classify; classify(title) -> {"relevant": 0/1, "trigger": str, "rule": str}
"""
from __future__ import annotations

import re

T = {
    "market": [r"price (hike|increase|surge|spike|freeze|cap|ceiling)s?", r"taas[- ]presyo", r"pagtaas ng presyo",
               r"mahal na (bigas|gulay|isda|bilihin)", r"\bmsrp\b", r"suggested retail price", r"price control",
               r"(rice|bigas|onion|sibuyas|sugar|asukal|pork|baboy|vegetable|gulay|egg|itlog|fish) (price|prices|presyo)",
               r"(prices|presyo) of (rice|onion|sugar|pork|vegetables|fish|eggs)", r"shortage", r"kakulangan",
               r"\bnfa rice\b", r"nfa (stocks|buffer)", r"rice (import|imports|tariff|supply|stocks)", r"food security emergency",
               r"food inflation", r"inflation (rate|eases|accelerates|quickens|slows|rises|climbs)", r"kadiwa",
               r"rice tariffication", r"\bp\d+(\.\d+)?/kilo", r"₱\d+(\.\d+)?/kilo"],
    "climate": [r"crop damage", r"(agricultural|agri|farm) damage", r"damage to (crops|agriculture|farms)",
                r"pinsala sa (agrikultura|pananim|palay)", r"(palay|rice|crops?) (damaged|losses|lost)",
                r"state of calamity", r"(flood|flooding|baha)\b.*\b(famil|resident|evacuat|displac|trapped|affected|victim|relief|food pack)",
                r"(famil|resident|evacuat|displac|victim)\w*\b.*\b(flood|flooding|baha|typhoon|storm|bagyo)",
                r"landslide", r"drought", r"el ni[nñ]o", r"tag-?tuyot", r"(typhoon|storm|bagyo)\b.*\b(damage|victims|affected|relief|food packs?|aid)",
                r"(relief|food packs?|ayuda)\b.*\b(typhoon|storm|flood|bagyo|baha|calamity)",
                r"(rainfall|flood|storm surge) (warning|alert|threat)", r"under (flood|storm) (threat|signal)",
                r"\d+ ?mm of rain", r"(flood|flooding|baha) (persists|hits|submerges?|inundates?|swamps?)",
                r"(severe|heavy|massive|worst) flood", r"damage to [\w’']+ (crops|farms|agriculture)"],
    "fish_kill": [r"fish ?kill", r"red tide", r"shellfish ban", r"fishing ban", r"closed fishing season", r"oil spill",
                  r"(fisherfolk|fishermen|mangingisda)\b.*\b(affected|losses|ban|aid|prepare|displaced|income|catch)",
                  r"(tilapia|bangus|milkfish) (die|died|deaths|losses)", r"aquaculture (losses|damage)", r"\bbfar\b",
                  r"algal bloom", r"\balgae\b", r"fish deaths"],
    "employment": [r"lay-?offs?\b", r"laid off", r"retrench", r"job (loss|losses|cuts)", r"jobless", r"unemploy",
                   r"nawalan ng trabaho", r"factory (closure|closes|shut)", r"displaced workers", r"workers (lose|lost)",
                   r"\btupad\b", r"emergency employment", r"(cash|fuel) (aid|subsidy) (to|for) (drivers|jeepney|tricycle|operators|farmers|fisherfolk)",
                   r"livelihood (aid|assistance|loss)", r"\bdole\b.*\b(aid|assistance|displaced)"],
    # bare "OFW" fires on crime and human-interest stories (DEV); require a household-support or displacement context
    "ofw_remittance": [r"remittances?", r"repatriat", r"\bpadala\b", r"deployment ban", r"balik-?manggagawa",
                       r"\bowwa\b.*\b(aid|assistance)", r"\bofws?\b.*\b(stranded|jobless|displaced|laid off)",
                       r"(stranded|displaced|jobless) ofws?\b"],
}
EXCLUDE = [r"flood[- ]control", r"\bprobe\b", r"scandal", r"\bsenate\b", r"inquiry", r"ombudsman", r"\bsolon\b", r"lawmaker",
           r"drug", r"shabu", r"buy-?bust", r"murder", r"\bkilled\b.*\bshot\b", r"arrest", r"nabbed", r"scam",
           r"basketball", r"\bmpbl\b", r"\bpba\b", r"volleyball", r"taekwondo", r"tournament",
           r"opens (first|new)", r"grand opening", r"recipe", r"\bcake\b", r"restaurant", r"\bmall\b", r"cosmetics",
           r"anniversary", r"festival", r"concert", r"tourism", r"churches"]
PLACE_NEEDED = {"climate"}            # weather items must name a CALABARZON place
_T = {k: [re.compile(p, re.I) for p in v] for k, v in T.items()}
_X = [re.compile(p, re.I) for p in EXCLUDE]
_REGION = re.compile(r"calabarzon|southern tagalog|region iv-?a", re.I)
ORDER = ["fish_kill", "ofw_remittance", "employment", "market", "climate"]   # most specific first


def classify(title: str, geocode=None) -> dict:
    t = title or ""
    if any(x.search(t) for x in _X):
        return {"relevant": 0, "trigger": "none", "rule": "exclusion"}
    for k in ORDER:
        hit = next((p.pattern for p in _T[k] if p.search(t)), None)
        if hit is None:
            continue
        if k in PLACE_NEEDED:
            place = (geocode(t) if geocode else None) or (_REGION.search(t) and "REGION")
            if not place:
                continue
        return {"relevant": 1, "trigger": k, "rule": hit}
    return {"relevant": 0, "trigger": "none", "rule": "no trigger phrase"}
