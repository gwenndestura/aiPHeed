"""
The news stories an E168 issue actually used, for the dashboard's "News reports used" panel.

The model's news features (app.e151.features) read stories published in the three months before the issue's cut-off,
one count per story, after the off-topic filter (app.e151.features.load_docs). This lists every story the CALABARZON
forecasts read: about a province or its towns, the region, Balance Luzon, and national news, each with its lead.

    python -m app.e168.news_used <issue folder>   -> data/e168/issues/<folder>/news_used.json (also written by stage)
"""
from __future__ import annotations

import json
import sys

import pandas as pd

from app.paths import BACKEND_DIR

ISSUES = BACKEND_DIR / "data" / "e168" / "issues"
GROUP_LABEL = {"market": "Food prices", "climate": "Weather and farm supply", "employment": "Jobs",
               "remittance": "OFWs and remittances", "poverty": "Hunger and poverty", "response": "Government response"}
CAL = {"batangas": "Batangas", "cavite": "Cavite", "laguna": "Laguna", "quezon": "Quezon", "rizal": "Rizal"}


def _lead(title: str, text: str, n: int = 220) -> str:
    """The article's opening lines (the publisher's lead), without the title, cut at a word near `n` characters."""
    t = (text or "")[len(title or ""):].lstrip(" .:-") if (text or "").startswith(title or "") else (text or "")
    t = " ".join(t.split())
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def build(cutoff: str) -> dict:
    """Stories in the streams the CALABARZON forecasts read (app.e151.features.stream_table): each province and its
    towns, the region as a whole, Balance Luzon (the provinces' area) and national news; three months before the cut-off."""
    from app.e151 import RAW
    from app.e151 import features as F
    cut = pd.Timestamp(cutoff)
    lo = cut - pd.DateOffset(months=3)
    d = F.load_docs()
    w = d[(d["published"] >= lo) & (d["published"] < cut)].copy()
    link = pd.read_parquet(RAW / "corpus.parquet", columns=["id", "link"]).drop_duplicates("id").set_index("id")["link"]
    groups = [f"v_{g}" for g in GROUP_LABEL]
    out = []
    for _, r in w.sort_values("published", ascending=False).iterrows():
        prov = [CAL[k] for k in str(r["provinces"] or "").split("|") if k in CAL]
        areas = str(r["areas"] or "").split("|")
        if r["geo_level"] in ("province", "lgu") and prov:
            level = "province"
        elif r["geo_level"] == "region_iva":
            level = "region"
        elif r["geo_level"] == "national":
            level = "national"
        elif "balance_luzon" in areas:
            level = "luzon"
        else:
            continue                                     # another region's or province's story: not read for CALABARZON
        top = max(groups, key=lambda c: float(r[c]))[2:]
        lead = _lead(r["title"], r["text"]) or _lead(r["title"], r.get("score_text", ""))   # lead, else its food-related sentences
        out.append({"id": r["id"], "title": r["title"], "lead": lead, "source": r["site"],
                    "date": r["published"].date().isoformat(), "url": link.get(r["id"]) or "",
                    "provinces": prov if level == "province" else [], "level": level, "region_wide": level == "region",
                    "group": top, "groupLabel": GROUP_LABEL[top]})
    lv = pd.Series([o["level"] for o in out]).value_counts().to_dict() if out else {}
    return {"cutoff": cut.date().isoformat(), "from": lo.date().isoformat(), "to": (cut - pd.Timedelta(days=1)).date().isoformat(),
            "counts": {k: int(v) for k, v in lv.items()}, "national_and_area_stories": int(lv.get("national", 0) + lv.get("luzon", 0)),
            "stories": out}


def write(folder) -> dict:
    folder = ISSUES / str(folder) if not hasattr(folder, "joinpath") else folder
    live = json.loads((folder / "live.json").read_text())
    doc = build(live.get("information_cutoff") or folder.name[8:18])
    (folder / "news_used.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    return {"stories": len(doc["stories"]), "window": [doc["from"], doc["to"]]}


if __name__ == "__main__":
    print(write(sys.argv[1]))
