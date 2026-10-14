"""
Food-insecurity relevance rule for news titles (E31, version R1).

WHY. The E28 gate (food-nexus guard + XLM-R max entailment >= 0.30 over the ten FSSI hypotheses) was validated on a
blind, manually reviewed sample of 355 titles (E31 validation/): precision 0.62 and an estimated recall of about 0.13
for food-insecurity-related province-attributed articles. Direct reports (food aid, subsidised rice, relief goods)
scored LOWER than food-business features, because the hypotheses describe conditions and the titles describe
responses. The relevance decision is therefore made by this transparent rule; XLM-RoBERTa keeps its Objective 1 role
of scoring the food-stress content of the articles the rule admits (FSSI-v2).

WHAT. Three classes, from the annotation rubric (validation/ANNOTATION_RUBRIC.md):
  DIRECT    a food-insecurity condition or response affecting people (hunger, malnutrition, food aid / relief goods /
            food packs / feeding, subsidised-rice and Kadiwa access programmes);
  INDIRECT  a food-system stress that plausibly affects food availability or access (fish kills, animal disease,
            pests, crop / fishery damage or losses, oil spills and shellfish bans, staple price increases, supply
            shortages, threatened livelihoods of farmers and fishers);
  NONE      everything else (general agriculture programmes, food business and lifestyle, politics, crime, weather
            without a food consequence in the title).
The terms were written from the rubric and refined ONLY on the DEV half of the review sample; the TEST half was
scored once with the frozen rule (validation/RELEVANCE_VALIDATION.md).
"""
from __future__ import annotations

import re

VERSION = "R1"

_DIRECT = [
    r"hunger", r"hungry", r"gutom", r"kagutuman", r"starv\w*", r"famine", r"malnutrition", r"malnourish\w*",
    r"undernourish\w*", r"stunting", r"wasting", r"food insecur\w*",
    r"food (?:aid|assistance|packs?|relief|bank|pantry|subsid\w*)", r"relief (?:goods|packs?|operations?|efforts?)",
    r"relief", r"ayuda", r"feeding(?: program\w*)?", r"soup kitchen", r"community pantry", r"pantry",
    r"nutritious food", r"meals? (?:to|for)", r"serves meals",
    r"p ?20(?:-per-kilo| per kilo)? rice", r"bbm rice", r"benteng bigas", r"20 ?rice", r"kadiwa",
    r"rice (?:aid|assistance|subsidy|distribution)", r"sacks of rice", r"bigas (?:para|sa)",
]
_STRESS = [
    r"fish ?kills?", r"african swine fever", r"\basf\b", r"bird flu", r"avian (?:flu|influenza)", r"armyworms?",
    r"pests?\b", r"infestation", r"locust\w*", r"oil spill", r"algal bloom", r"red tide", r"shellfish ban",
    r"prohibits consumption of fish", r"(?:agri|agricultural|crop|farm|fisher(?:y|ies)|agri-fisher(?:y|ies))\w* "
    r"(?:damage|losses?|loss)", r"damage to (?:crops|agri\w*|farms?)", r"(?:crops?|agri\w*) (?:damaged|destroyed|lost)",
    r"destroys .{0,30}(?:agri|crops|farm)", r"(?:heat|drought|el ni[nñ]o) (?:costs|damage|hits?)",
    r"el ni[nñ]o damage", r"tilapia (?:lost|worth)", r"tons? of (?:tilapia|fish|bangus)",
    r"(?:shortage|scarcity) (?:in|of)", r"shortage", r"supply (?:shortage|disruption|woes)",
    r"(?:price|presyo)s? (?:hike|increase|surge|spike|soar|up|gap|at)", r"(?:mahal|taas)(?:-| )?(?:presyo|na)",
    r"inflation", r"(?:rice|pork|fish|onion|vegetable|egg|sugar|chicken|food) prices?",
    r"stabili[sz]e (?:rice|food|pork) prices", r"bring (?:down )?fish prices",
    r"(?:livelihoods?|kabuhayan) .{0,40}(?:fisher\w*|farmer\w*|mangingisda|magsasaka)",
    r"(?:fisher\w*|fisherfolk|farmers?|mangingisda|magsasaka) .{0,40}(?:affected|struggl\w*|at risk|threaten\w*|"
    r"lose|losses|hit|cope|complain\w*|apektado)",
    r"lose (?:land|livelihood\w*)", r"mill shutdown", r"(?:production|catch(?:es)?) (?:down|drops?|falls?|smaller)",
    r"smaller catches", r"guts fish sales", r"prices at .{0,10}low",
    r"damage to .{0,30}crops", r"production .{0,40}down", r"harvest early",   # R1 dev refinements (frozen after)
]
_DIRECT_RE = re.compile(r"(?<![a-z])(?:" + "|".join(_DIRECT) + r")", re.IGNORECASE)
_STRESS_RE = re.compile(r"(?<![a-z])(?:" + "|".join(_STRESS) + r")", re.IGNORECASE)
# a food-business / lifestyle / event headline is NONE even when it names food
_EXCLUDE_RE = re.compile(r"(?<![a-z])(?:restaurant|resto|caf[eé]|food trip|where to eat|must-try|fine dining|"
                         r"food fest|grand opening|opens first|staycation|airbnb|agritourism|selfies|unli|samgyup|"
                         r"recipe|culinary)", re.IGNORECASE)


def classify(title: str) -> str:
    """DIRECT, INDIRECT or NONE for one title (or title + lead)."""
    t = title or ""
    if _EXCLUDE_RE.search(t) and not _DIRECT_RE.search(t):
        return "NONE"
    if _DIRECT_RE.search(t):
        return "DIRECT"
    if _STRESS_RE.search(t):
        return "INDIRECT"
    return "NONE"


def is_relevant(title: str) -> bool:
    return classify(title) != "NONE"
