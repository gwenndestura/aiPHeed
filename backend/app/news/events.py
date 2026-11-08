"""
app/news/events.py
------------------
E83 event-level news features (N2) and lead-text features (N1), built on the E64 pipeline (classifier v2, syndication
de-duplication). Every feature at origin t uses only articles published before O(t).

Design (from the literature review, E83 LITERATURE_REVIEW.md):
  * an article is evidence of a food-stress mechanism only when it describes one (classifier v2 trigger phrases), and
    its direction is classified separately: ADVERSE (the mechanism is worsening), IMPROVING (it is easing), RESPONSE
    (government or aid action), NEUTRAL. A story that only mentions food, poverty or a disaster is not adverse.
  * repeated coverage of one event is one event: articles of the same trigger within EVENT_DAYS whose title (+ lead)
    embeddings have cosine >= EVENT_COS form one cluster; the cluster's outlet count is its salience.
  * counts are divided by the corpus volume of the same quarter (all collected articles, relevant or not), so growth
    in collection or media attention is not read as growth in shocks (E73 found the market-news signal was a corpus-
    growth artifact).
  * province values are shrunk toward the regional value with weight KAPPA (sparse provinces borrow strength);
    national events enter every province through the regional value only.
"""
from __future__ import annotations

import functools
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from app.news import pipeline_v3 as P
from app.news.classifier_v2 import classify

DATA = Path(__file__).resolve().parents[2] / "data"
LEADS = DATA / "news_e83" / "leads.jsonl"
EMB_CACHE = DATA / "news_e83" / "embeddings.npz"
EMB_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EVENT_DAYS, EVENT_COS, KAPPA = 7, 0.72, 5.0
DRIVER_OF = {"market": "prices", "climate": "climate", "fish_kill": "supply", "employment": "household",
             "ofw_remittance": "household"}
DRIVERS = ("prices", "climate", "supply", "household")

ADVERSE = [r"\b(hike|hikes|increase[sd]?|surge[sd]?|soar\w*|spike[sd]?|jump\w*|climb\w*|rise[sn]?|rising|up by)\b",
           r"shortage", r"kakulangan", r"damage", r"pinsala", r"loss(es)?\b", r"lost\b", r"destroy", r"wipe", r"ruin", r"lay-?off",
           r"retrench", r"jobless", r"unemploy", r"nawalan", r"fish ?kill", r"red tide", r"oil spill", r"\bban\b",
           r"drought", r"tag-?tuyot", r"el ni[nñ]o", r"flood", r"baha", r"landslide", r"state of calamity", r"displac",
           r"evacuat", r"hunger", r"gutom", r"malnutrition", r"stunt", r"accelerat", r"quicken", r"mahal", r"taas",
           r"affected", r"victims?", r"stranded", r"halt", r"suspend", r"closure", r"shut", r"emergency", r"crisis",
           r"threat", r"warning", r"alert", r"higher", r"expensive", r"prices? up\b", r"\bup\b", r"\b(dead|killed|missing)\b"]
IMPROVING = [r"\b(ease[sd]?|easing|slow(s|ed|ing)?|drop(s|ped)?|decline[sd]?|fall(s|ing)?|fell|dip(s|ped)?|lower(ed)?|"
             r"cheaper|rollback|bumaba|baba)\b", r"stable", r"sufficient", r"enough", r"surplus", r"bumper",
             r"recover", r"lifted", r"lift(s|ed)? ban", r"resum", r"back to normal", r"remittances? (rise|grow|up|climb)",
             r"jobs? (created|generated)", r"employment (rate )?(rises|up|improves)", r"harvest (up|rise|increase)",
             r"(production|output) (up|rise|grows|increase)", r"cut(s)? (price|msrp)", r"price(s)? cut", r"safe to eat",
             r"lift\w* (the )?(food security )?emergency", r"no (fish ?kill|shortage)", r"contained", r"affordable",
             r"(buffer )?stocks? (rise|rises|up)", r"good harvest"]
RESPONSE = [r"\baid\b", r"relief", r"food packs?", r"subsid", r"kadiwa", r"distribut", r"assistance", r"ayuda", r"\bcash\b",
            r"\btupad\b", r"program", r"release of nfa", r"\bmsrp\b", r"price (cap|ceiling|freeze)", r"import", r"buffer",
            r"(gives|extends|allots|releases|provides|turns over)", r"livelihood", r"support", r"seeds?", r"fertilizer",
            r"loan", r"insurance"]
_A, _I, _R = ([re.compile(p, re.I) for p in ps] for ps in (ADVERSE, IMPROVING, RESPONSE))
# Off-topic families that classifier v2 admits through generic words ("shortage", "unemployment"): E83 spot-check.
OFF_TOPIC = re.compile(r"classroom|medicine|mental health|power (shortage|supply)|kills? (family|self)|teacher|vaccine|"
                       r"water shortage|electricity|blood", re.I)
SEVERE = re.compile(r"state of calamity|worst|severe|massive|emergency|million|billion|record|crisis|thousands", re.I)


def polarity(text: str) -> str:
    """ADVERSE / IMPROVING / RESPONSE / NEUTRAL for a relevant article. Improving cues win over generic movement words
    ('prices drop' contains no adverse cue; 'prices rise' does); a response story with adverse context (relief for
    flood victims) is RESPONSE, and it is counted with the adverse mechanism it responds to."""
    t = text or ""
    a = sum(bool(p.search(t)) for p in _A)
    i = sum(bool(p.search(t)) for p in _I)
    r = sum(bool(p.search(t)) for p in _R)
    if i and i >= a:
        return "IMPROVING"
    if r and r >= a:
        return "RESPONSE"
    if a:
        return "ADVERSE"
    return "NEUTRAL"


# ------------------------------------------------------------------------------------------------ inputs
@functools.lru_cache(maxsize=1)
def leads() -> dict[str, dict]:
    if not LEADS.exists():
        return {}
    out = {}
    for line in LEADS.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out[r["article_key"]] = r
    return out


def lead_text(key: str) -> str:
    r = leads().get(key)
    if not r or r["extraction_status"] not in ("lead_ok", "meta_only"):
        return ""
    return (r.get("lead") or r.get("meta_description") or "").strip()


@functools.lru_cache(maxsize=1)
def volume() -> dict[str, int]:
    """Collected articles per quarter (relevant or not): the media-attention / collection denominator."""
    v: dict[str, int] = {}
    for a in P.corpus():
        v[a["quarter"]] = v.get(a["quarter"], 0) + 1
    return v


@functools.lru_cache(maxsize=1)
def articles(use_leads: bool = True) -> tuple[dict, ...]:
    """Admitted (relevant, de-syndicated) articles with polarity. With leads, relevance and trigger are re-decided on
    title + lead, and articles whose lead shows no food-stress mechanism are dropped (lead-confirmed relevance)."""
    out = []
    for a in P.admitted():
        if OFF_TOPIC.search(a["title"]):
            continue
        lt = lead_text(a["article_key"]) if use_leads else ""
        b = dict(a)
        b["has_lead"] = bool(lt)
        if lt:
            c = classify(a["title"] + ". " + lt[:600])
            if not c["relevant"]:
                continue
            b["trigger"] = c["trigger"] if c["trigger"] != "none" else a["trigger"]
        b["polarity"] = polarity(a["title"] + (". " + lt[:400] if lt else ""))
        b["severe"] = bool(SEVERE.search(a["title"] + " " + lt[:400]))
        out.append(b)
    return tuple(out)


def _embed(texts: list[str]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(EMB_MODEL, device="cpu")
    return m.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)


@functools.lru_cache(maxsize=2)
def embeddings(use_leads: bool = True) -> dict[str, np.ndarray]:
    arts = articles(use_leads)
    keys = [a["article_key"] + ("|L" if use_leads and a["has_lead"] else "") for a in arts]
    cache = {}
    if EMB_CACHE.exists():
        z = np.load(EMB_CACHE, allow_pickle=False)
        cache = dict(zip(z["keys"].tolist(), z["vecs"]))
    miss = [(k, a) for k, a in zip(keys, arts) if k not in cache]
    if miss:
        texts = [a["title"] + (". " + lead_text(a["article_key"])[:300] if k.endswith("|L") else "") for k, a in miss]
        for (k, _), v in zip(miss, _embed(texts)):
            cache[k] = v
        EMB_CACHE.parent.mkdir(parents=True, exist_ok=True)
        ks = list(cache)
        np.savez(EMB_CACHE, keys=np.array(ks), vecs=np.stack([cache[k] for k in ks]))
    return {a["article_key"]: cache[k] for k, a in zip(keys, arts)}


@functools.lru_cache(maxsize=2)
def events(use_leads: bool = True) -> tuple[dict, ...]:
    """Greedy chronological clustering: an article joins the most similar open event of the same trigger whose first
    article is at most EVENT_DAYS older and similarity >= EVENT_COS. The event takes its first article's date (the date
    it became known), province (first attributed article) and the majority polarity of its articles."""
    E = embeddings(use_leads)
    evs: list[dict] = []
    for a in sorted(articles(use_leads), key=lambda a: (a["published_ph"], a["article_key"])):
        t = datetime.fromisoformat(a["published_ph"]).replace(tzinfo=None)
        v = E[a["article_key"]]
        best, bs = None, EVENT_COS
        for e in reversed(evs):
            if (t - e["start"]) > timedelta(days=EVENT_DAYS):
                break
            if e["trigger"] != a["trigger"]:
                continue
            s = float(v @ e["centroid"])
            if s >= bs:
                best, bs = e, s
        if best is None:
            evs.append({"start": t, "trigger": a["trigger"], "centroid": v, "members": [a],
                        "province_code": a["province_code"]})
        else:
            best["members"].append(a)
            c = best["centroid"] * (len(best["members"]) - 1) + v
            best["centroid"] = c / np.linalg.norm(c)
            if best["province_code"] is None and a["province_code"] is not None:
                best["province_code"] = a["province_code"]
    out = []
    for e in evs:
        pols = [m["polarity"] for m in e["members"]]
        pol = max(("ADVERSE", "IMPROVING", "RESPONSE", "NEUTRAL"), key=lambda p: (pols.count(p), p == "ADVERSE"))
        out.append({"start": e["start"], "quarter": e["members"][0]["quarter"], "trigger": e["trigger"],
                    "driver": DRIVER_OF[e["trigger"]], "province_code": e["province_code"], "polarity": pol,
                    "n_articles": len(e["members"]), "n_outlets": len({m["outlet"] for m in e["members"]}),
                    "severe": any(m["severe"] for m in e["members"]),
                    "keys": [m["article_key"] for m in e["members"]]})
    return tuple(out)


# ------------------------------------------------------------------------------------------------ features
def _shrink(xp: float, np_: float, xr: float) -> float:
    return (np_ * xp + KAPPA * xr) / (np_ + KAPPA)


def n2_features(t: int, use_leads: bool = True) -> list[dict]:
    """Event-level features per province at O(t), from events that became known in quarter t (before O(t)) and,
    for the change features, in quarter t-1. Rates are per 100 collected articles of the quarter."""
    O = P.origin(t)
    q, q1 = P.qs(t), P.qs(t - 1)
    ev = [e for e in events(use_leads) if e["start"] < O and e["quarter"] in (q, q1)]
    vol = volume()

    def rates(es, quarter, prov):
        mine = [e for e in es if e["quarter"] == quarter and (prov is None or e["province_code"] == prov)]
        V = max(vol.get(quarter, 0), 1) / 100.0
        r = {"n": len(mine)}
        for g in DRIVERS:
            adv = [e for e in mine if e["driver"] == g and e["polarity"] in ("ADVERSE",)]
            imp = [e for e in mine if e["driver"] == g and e["polarity"] == "IMPROVING"]
            r[f"adv_{g}"] = sum(1 + 0.5 * e["severe"] + 0.25 * math.log(e["n_outlets"]) for e in adv) / V
            r[f"imp_{g}"] = len(imp) / V
        r["resp"] = sum(1 for e in mine if e["polarity"] == "RESPONSE") / V
        r["src"] = len({o for e in mine for o in [e["n_outlets"]]})
        return r

    reg, reg1 = rates(ev, q, None), rates(ev, q1, None)
    rows = []
    for p in P.PROVINCE_CODES:
        mine, mine1 = rates(ev, q, p), rates(ev, q1, p)
        r = {"t": t, "province_code": p, "ev_n": float(mine["n"]), "ev_cov": math.log1p(mine["n"])}
        net, net1 = 0.0, 0.0
        for g in DRIVERS:
            a = _shrink(mine[f"adv_{g}"], mine["n"], reg[f"adv_{g}"])
            i = _shrink(mine[f"imp_{g}"], mine["n"], reg[f"imp_{g}"])
            a1 = _shrink(mine1[f"adv_{g}"], mine1["n"], reg1[f"adv_{g}"])
            i1 = _shrink(mine1[f"imp_{g}"], mine1["n"], reg1[f"imp_{g}"])
            r[f"ev_adv_{g}"], r[f"ev_net_{g}"] = a, a - i
            net, net1 = net + a - i, net1 + a1 - i1
        r["ev_net_all"], r["ev_net_all_d"] = net, net - net1
        r["ev_resp"] = _shrink(mine["resp"], mine["n"], reg["resp"])
        rows.append(r)
    return rows


N2_COLS = ["ev_cov"] + [f"ev_adv_{g}" for g in DRIVERS] + [f"ev_net_{g}" for g in DRIVERS] + \
          ["ev_net_all", "ev_net_all_d", "ev_resp"]


def n1_features(t: int) -> list[dict]:
    """Article-level lead-text features (no event clustering): per province, the share of lead-available admitted
    articles of quarter t (before O(t)) that are ADVERSE per driver, shrunk to the region; plus lead coverage."""
    O = P.origin(t)
    q = P.qs(t)
    arts = [a for a in articles(True) if a["quarter"] == q and datetime.fromisoformat(a["published_ph"]).replace(tzinfo=None) < O]
    withl = [a for a in arts if a["has_lead"]]

    def share(sub, g):
        return (sum(1 for a in sub if DRIVER_OF[a["trigger"]] == g and a["polarity"] == "ADVERSE") / len(sub)) if sub else 0.0
    rows = []
    for p in P.PROVINCE_CODES:
        mine = [a for a in withl if a["province_code"] == p]
        r = {"t": t, "province_code": p, "ld_cov": (len(withl) / len(arts)) if arts else 0.0}
        for g in DRIVERS:
            r[f"ld_adv_{g}"] = _shrink(share(mine, g), len(mine), share(withl, g))
        rows.append(r)
    return rows


N1_COLS = ["ld_cov"] + [f"ld_adv_{g}" for g in DRIVERS]


def n3_frame(origins: list[int]):
    import pandas as pd
    rows = [{k: v for k, v in r.items() if k not in ("article_keys", "national_keys", "fssi_status")}
            for t in origins for r in P.n3_features(t)]
    return pd.DataFrame(rows)


N3_COLS = ["n3_cov", "n3_market_rw", "n3_climate_rw", "n3_fish_kill_rw", "n3_employment_rw", "n3_nat_market_rw",
           "n3_nat_employment_rw", "n3_nat_ofw_remittance_rw", "n3_src", "n3_fssi"]
