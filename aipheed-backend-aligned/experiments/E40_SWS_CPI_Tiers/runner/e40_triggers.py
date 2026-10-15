"""E40 task B: trigger composition and market regex audit. The NLP model and backend/app/ml/nlp/trigger_classifier.py
are NOT modified; the deployed keyword lists are imported read-only and a candidate market-v2 rule is defined here.

composition_c(p, q) = (hits_c + K * prior_c) / (total_hits + K), K = 5, prior = regional mix over quarters <= q
(as-of; the all-quarters regional mix is reported for display only). Reliable when n_articles >= 5; otherwise the
display pools the four trailing quarters at region level ("insufficient news").

    <backend venv python> -B runner/e40_triggers.py   -> runs/triggers/{market_audit.json, composition.csv, summary.json}
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

import pandas as pd

E40 = Path(__file__).resolve().parents[1]
ROOT = E40.parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.nlp.trigger_classifier import TRIGGER_KEYWORDS  # noqa: E402  (read-only)

STORE = E40.parent / "E31_Chapter1_Completion" / "backend_dev" / "data" / "news_e31" / "articles.jsonl"
OUT = E40 / "runs" / "triggers"
CATS = list(TRIGGER_KEYWORDS)
K = 5
MIN_ARTICLES = 5
GENERIC = ["price", "prices", "presyo", "bigas", "palengke", "market", "palay", "rice"]   # user list + bare staples
CONTEXT = ["tumaas", "tataas", "pagtaas", "sumipa", "sipa", "surge", "surges", "surged", "soar", "soars", "soaring",
           "hike", "hikes", "spike", "spikes", "jump", "jumps", "rise", "rises", "rising", "increase", "increases",
           "shortage", "shortages", "kakulangan", "kulang", "scarcity", "mahal", "mataas", "inflation", "record high",
           "skyrocket", "skyrocketing", "taas-presyo", "price ceiling", "price cap", "price control"]
_rx = {c: [(kw, re.compile(r"\b" + re.escape(kw) + r"\b", re.I)) for kw in kws] for c, kws in TRIGGER_KEYWORDS.items()}
_ctx = re.compile(r"\b(" + "|".join(re.escape(w) for w in CONTEXT) + r")\b", re.I)
_generic_only = {kw for kw in TRIGGER_KEYWORDS["market"] if kw.lower() in GENERIC}


def articles() -> pd.DataFrame:
    a = pd.DataFrame([json.loads(x) for x in STORE.open(encoding="utf-8")])
    assert a["ph_date"].min() >= "2021-01-01", "pre-2021 article found"
    return a[["article_key", "ph_date", "quarter", "geo_province_code", "title"]]


def matches(title: str) -> dict[str, list[str]]:
    return {c: [kw for kw, r in rx if r.search(title or "")] for c, rx in _rx.items()}


def market_v2(title: str, kws: list[str]) -> bool:
    """market-v2: a market keyword that is not a bare generic term AND a surge/shortage context word in the title."""
    return bool([k for k in kws if k not in _generic_only]) and bool(_ctx.search(title or ""))


def tag(a: pd.DataFrame) -> pd.DataFrame:
    m = a["title"].map(matches)
    for c in CATS:
        a[c] = m.map(lambda d, c=c: int(bool(d[c])))
    a["market_kws"] = m.map(lambda d: d["market"])
    a["market_v2"] = [int(market_v2(t, k)) for t, k in zip(a["title"], a["market_kws"])]
    return a


def composition(a: pd.DataFrame, cats_cols: dict[str, str]) -> pd.DataFrame:
    """Province-quarter shrunk composition; prior = regional mix over quarters <= q (as-of)."""
    att = a[a["geo_province_code"].notna()]
    qs = sorted(att["quarter"].unique())
    rows = []
    for q in qs:
        upto = att[att["quarter"] <= q]
        tot = sum(upto[col].sum() for col in cats_cols.values())
        prior = {c: (upto[col].sum() / tot if tot else 1 / len(cats_cols)) for c, col in cats_cols.items()}
        for p, g in att[att["quarter"] == q].groupby("geo_province_code"):
            hits = {c: int(g[col].sum()) for c, col in cats_cols.items()}
            th = sum(hits.values())
            r = {"province_code": p, "quarter": q, "n_articles": len(g), "total_hits": th,
                 "reliable": len(g) >= MIN_ARTICLES}
            r.update({f"hits_{c}": h for c, h in hits.items()})
            r.update({f"comp_{c}": (hits[c] + K * prior[c]) / (th + K) for c in cats_cols})
            rows.append(r)
    return pd.DataFrame(rows)


def region_pooled(a: pd.DataFrame, cats_cols: dict[str, str], q: str) -> dict:
    """Display fallback: region level, the 4 quarters ending at q, same shrinkage."""
    att = a[a["geo_province_code"].notna()]
    qs = sorted(att["quarter"].unique())
    win = [x for x in qs if x <= q][-4:]
    g = att[att["quarter"].isin(win)]
    upto = att[att["quarter"] <= q]
    tot = sum(upto[col].sum() for col in cats_cols.values())
    prior = {c: (upto[col].sum() / tot if tot else 1 / len(cats_cols)) for c, col in cats_cols.items()}
    hits = {c: int(g[col].sum()) for c, col in cats_cols.items()}
    th = sum(hits.values())
    return {"quarters": win, "n_articles": len(g), **{f"comp_{c}": (hits[c] + K * prior[c]) / (th + K) for c in cats_cols}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    a = tag(articles())
    att = a[a["geo_province_code"].notna()]
    tok = collections.Counter(k for ks in a["market_kws"] for k in ks)
    ncat = a[CATS].sum(axis=1)
    ncat2 = (a[[c for c in CATS if c != "market"]].sum(axis=1) + a["market_v2"])
    v1 = {c: c for c in CATS}
    v2 = {**{c: c for c in CATS if c != "market"}, "market": "market_v2"}
    hits_v1 = {c: int(att[c].sum()) for c in CATS}
    hits_v2 = {c: int(att[v2[c]].sum()) for c in CATS}
    audit = {
        "corpus": {"articles": len(a), "province_attributed": len(att), "text": "titles only (Google News RSS)"},
        "market_top30_matched_keywords_all_articles": tok.most_common(30),
        "generic_terms_requested_for_removal": GENERIC,
        "generic_terms_present_in_deployed_market_list": sorted(_generic_only),
        "context_words_required_v2": CONTEXT,
        "market_articles": {"v1_all": int(a["market"].sum()), "v2_all": int(a["market_v2"].sum()),
                            "v1_attributed": hits_v1["market"], "v2_attributed": hits_v2["market"]},
        "market_share_of_trigger_hits_attributed": {
            "before_v1": hits_v1["market"] / max(sum(hits_v1.values()), 1),
            "after_v2": hits_v2["market"] / max(sum(hits_v2.values()), 1)},
        "hits_by_category_attributed": {"v1": hits_v1, "v2": hits_v2},
        "market_v1_titles_dropped_by_v2": a[(a["market"] == 1) & (a["market_v2"] == 0)]["title"].tolist(),
        "market_v1_titles_kept_by_v2": a[(a["market"] == 1) & (a["market_v2"] == 1)]["title"].tolist(),
        "categories_per_article": {
            "all_v1": {"0": int((ncat == 0).sum()), "1": int((ncat == 1).sum()), "2+": int((ncat >= 2).sum())},
            "all_v2": {"0": int((ncat2 == 0).sum()), "1": int((ncat2 == 1).sum()), "2+": int((ncat2 >= 2).sum())},
            "attributed_v1": {"0": int((ncat[att.index] == 0).sum()), "1": int((ncat[att.index] == 1).sum()),
                              "2+": int((ncat[att.index] >= 2).sum())}},
        "dashboard_market_100pct_explained": (
            "The dashboard's 'market = 100%' driver split is not a news proportion. It comes from "
            "backend/app/ml/inference/e31_engine.py::five_trigger_drivers, which groups SHAP values of the E20 model: "
            "market = SHAP(D_last, Dnow, rice_rel) and the other four groups have no model features, so they are 0 "
            "and market is always 100% of the attribution. The news trigger composition here is a separate, "
            "descriptive measure."),
        "note": "trigger_classifier.py and the NLP model are unchanged; market-v2 is a candidate rule for review only"}
    comp = composition(a, v2)
    comp_v1 = composition(a, v1)
    comp.to_csv(OUT / "composition.csv", index=False, float_format="%.6g", lineterminator="\n")
    comp_v1.to_csv(OUT / "composition_v1_market.csv", index=False, float_format="%.6g", lineterminator="\n")
    allq_prior = {c: hits_v2[c] / max(sum(hits_v2.values()), 1) for c in CATS}
    summary = {"K": K, "min_articles": MIN_ARTICLES, "regional_all_quarters_prior_display": allq_prior,
               "province_quarters": len(comp), "reliable": int(comp["reliable"].sum()),
               "insufficient_news": int((~comp["reliable"]).sum()),
               "province_quarters_with_zero_trigger_hits": int((comp["total_hits"] == 0).sum()),
               "region_pooled_latest": region_pooled(a, v2, sorted(att["quarter"].unique())[-1])}
    (OUT / "market_audit.json").write_text(json.dumps(audit, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: audit[k] for k in ("market_top30_matched_keywords_all_articles", "generic_terms_present_in_deployed_market_list",
                                            "market_articles", "market_share_of_trigger_hits_attributed",
                                            "hits_by_category_attributed", "categories_per_article")}, indent=1))
    print("DROPPED:", audit["market_v1_titles_dropped_by_v2"])
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
