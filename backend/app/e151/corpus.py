"""
E151 unified news corpus and geographic attribution. Reads no outcome.

Joins every collected archive (E147, E150, FI6 including its national queries, E31 and E60 multi-publisher titles), removes survey reports, removes
exact duplicates across archives, and gives each article one geographic level instead of forcing it into a province.

    python -m app.e151.corpus build -> data/e151/raw/corpus.parquet, data/e151/out/corpus_audit.json
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter

import numpy as np
import pandas as pd

from app.e145 import news as N
from app.e147 import RAW as R147
from app.e147 import features as Fe
from app.e150 import RAW as R150
from app.e150.news_v2 import name_rx
from app.e151 import OUT, RAW

DATA = R150.parents[1]
TAG = re.compile(r"<[^>]+>")
SENT = re.compile(r"(?<=[.!?])\s+")
SKIP_PATH = re.compile(r"/(sports?|entertainment|life-and-style|lifestyle|technology|tech|movies?|music|celebrities|showbiz|esports|travel|fashion|bulletin-board)(/|-)", re.I)
INTL_PATH = re.compile(r"/(world|globalnation/world|asia-pacific)(/|$)", re.I)
INTL_WORD = re.compile(r"\b(Somalia|Yemen|Gaza|Ukraine|Russia|Sudan|Afghanistan|North Korea|Syria|Ethiopia|Venezuela|Sri Lanka|Myanmar|Haiti|Nigeria|Kenya|United Nations report|US Congress)\b")
SURVEY = N.SURVEY_RX
GATE = re.compile(
    r"\b(rice|palay|bigas|food|foods|pagkain|hunger|hungry|gutom|malnutrition|malnourished|nutrition|prices?|presyo|inflation|"
    r"farmers?|magsasaka|fishers?|fisherfolk|mangingisda|crops?|harvest|agricultur\w*|typhoon|bagyo|floods?|flooding|baha|drought|tagtuyot|el ni.o|la ni.a|"
    r"livelihoods?|kabuhayan|poverty|kahirapan|mahirap|relief|ayuda|unemploy\w*|jobless|layoffs?|retrench\w*|shortages?|kakulangan|"
    r"OFWs?|remittances?|repatriat\w*|displaced|evacuees?|4Ps|pantawid|food packs?|calamity|vegetables?|gulay|isda|fish kill|red tide|African swine fever|ASF)\b", re.I)
# Manila datelines mark the national desk, not an event in Metro Manila
NATIONAL_DATELINE = re.compile(r"^\s*MANILA,? (Philippines)?", re.I)
NATIONAL_WORD = re.compile(r"\b(nationwide|Philippines|Filipinos|Malaca.ang|Palace|Department of Agriculture|DA Secretary|Agriculture Secretary|PSA|Philippine Statistics Authority|NEDA|DOLE|DSWD|BSP|Bangko Sentral|national government|Senate|House of Representatives|Kamara|Senado)\b")
AREA_WORD = {"balance_luzon": re.compile(r"\b(Luzon|Bicol|Ilocos|Cagayan Valley|Central Luzon|Cordillera|CALABARZON|MIMAROPA|Southern Tagalog)\b"), "visayas": re.compile(r"\b(Visayas|Western Visayas|Central Visayas|Eastern Visayas)\b"),
             "mindanao": re.compile(r"\b(Mindanao|BARMM|Bangsamoro|SOCCSKSARGEN|Caraga|Zamboanga Peninsula|Davao Region|Northern Mindanao)\b"), "metro_manila": re.compile(r"\b(Metro Manila|NCR|National Capital Region|Quezon City|Makati|Pasig|Taguig|Caloocan|Navotas|Malabon|Marikina|Para.aque|Las Pi.as|Muntinlupa|Pasay|Valenzuela|Mandaluyong|Tondo)\b")}
REGION_IVA = re.compile(r"\b(CALABARZON|Calabarzon|Southern Tagalog|Region IV-?A|Region 4-?A)\b")
CAL = {"batangas": "Batangas", "cavite": "Cavite", "laguna": "Laguna", "quezon": "Quezon", "rizal": "Rizal"}
STRICT = {"quezon": re.compile(r"(Quezon province|Quezon Province|\bin Quezon\b(?! City)|Quezon (Gov|Governor)\b|province of Quezon|, Quezon\b(?! City))"),
          "rizal": re.compile(r"(Rizal province|Rizal Province|\bin Rizal\b(?! Park| Avenue| Memorial| Medical| Commercial)|Rizal (Gov|Governor)\b|province of Rizal|, Rizal\b)"),
          "laguna": re.compile(r"\bLaguna\b(?! (de Bay|Lake|Bay))")}
# LGU names that also mean something else: they count only when the province is named in the same text
AMBIGUOUS = {"San Pablo", "Santa Rosa", "San Pedro", "Rosario", "San Juan", "Lemery", "Taal", "Tanauan", "Pila", "Bay", "Alaminos", "Magdalena", "Victoria", "Real", "Infanta", "General Luna", "Lopez", "Rodriguez", "Teresa", "San Mateo", "Cardona", "Mabini",
             "Alfonso", "Ternate", "Santa Cruz", "Santa Maria", "San Antonio", "San Jose", "San Luis", "San Nicolas", "Padre Garcia", "Laurel", "Balete", "Lian", "Luisiana", "Liliw", "Nagcarlan", "Rizal", "Quezon", "Paete", "Pakil", "Pangil", "Siniloan", "Famy", "Mabitac", "Kalayaan",
             "Dolores", "Candelaria", "Catanauan", "Burdeos", "Patnanungan", "Jomalig", "Panukulan", "Polillo", "General Nakar", "Agdangan", "Plaridel", "Sampaloc", "Sariaya", "Unisan", "Mulanay", "Macalelon", "Perez", "Alabat", "Tagkawayan", "Guinayangan", "Morong", "Baras", "Calauag", "Pitogo", "Buenavista", "San Andres", "San Francisco", "San Narciso", "Pagbilao", "Lucban", "Tiaong", "Gumaca", "Atimonan", "Mauban", "Tayabas", "Cuenca", "Ibaan", "Malvar", "Nasugbu", "Calaca", "Calatagan", "Balayan", "Tuy", "Bauan", "Tingloy"}
UNIQUE_ALWAYS = {"Tayabas", "Lucban", "Sariaya", "Pagbilao", "Tiaong", "Gumaca", "Atimonan", "Mauban", "Calauag", "Nasugbu", "Calatagan", "Balayan", "Bauan", "Tingloy", "Polillo", "Siniloan"}


def _clean(s) -> str:
    return " ".join(html.unescape(TAG.sub(" ", s or "")).split())


def _norm_title(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def load_all() -> pd.DataFrame:
    a = pd.read_parquet(R147 / "articles_clean.parquet")[["id", "title", "text", "published", "link", "site"]].drop_duplicates("id")
    a["origin"] = "province_query"
    rows = []
    with open(R150 / "articles_more.jsonl", encoding="utf-8", newline="\n") as f:
        for x in f:
            try:
                rows.append(json.loads(x))
            except json.JSONDecodeError:
                pass
    m = pd.DataFrame(rows).drop_duplicates("id")
    m["title"], m["lead"] = m["title"].map(_clean), m["excerpt"].map(_clean)
    m["text"] = (m["title"] + ". " + m["lead"]).str.slice(0, 700)
    m["published"] = pd.to_datetime(m["date"])
    m = m[["id", "title", "text", "published", "link", "site"]].assign(origin="province_query")
    f6 = pd.read_parquet(DATA / "fi6" / "news_archive" / "articles.parquet")
    live = DATA / "e168" / "live_raw" / "news" / "fi6_new_articles.parquet"
    if live.exists():                     # articles collected by the live refresh after the archive build (app.e168.live_refresh)
        n = pd.read_parquet(live)
        n = n[~(n["site"] + ":" + n["wp_id"].astype(str)).isin(set(f6["site"] + ":" + f6["wp_id"].astype(str)))]
        f6 = pd.concat([f6, n], ignore_index=True)
    f6["id"] = f6["site"] + ":" + f6["wp_id"].astype(str)
    f6["title"], f6["lead"] = f6["title"].map(_clean), f6["lead"].map(_clean)
    f6["text"] = (f6["title"] + ". " + f6["lead"]).str.slice(0, 700)
    f6["published"] = pd.to_datetime(f6["published"])
    f6["origin"] = np.where(f6["query_kind"] == "national", "national_query", "calabarzon_query")
    f6 = f6[["id", "title", "text", "published", "link", "site", "origin"]]
    gn = []
    for d in ("news_e31", "news_e60"):
        with open(DATA / d / "articles.jsonl", encoding="utf-8") as f:
            for x in f:
                r = json.loads(x)
                gn.append({"id": "gn:" + r["article_key"][:20], "title": _clean(r["title"]), "text": _clean(r["title"]), "published": pd.Timestamp(r["published_ph"]).tz_localize(None), "link": "", "site": r["source_domain"], "origin": "google_news_title"})
    g = pd.DataFrame(gn).drop_duplicates("id")
    # national and CALABARZON queries are kept in preference to a province query for the same article: the origin matters for the audit only
    d = pd.concat([f6, a, m, g], ignore_index=True)
    d["title"] = d["title"].fillna("")
    d = d[d["title"].str.len() > 0].drop_duplicates("id")
    return d


def attribute(d: pd.DataFrame) -> pd.DataFrame:
    base = Fe.base_rows().drop_duplicates("key")
    keys = sorted(base["key"])
    rx = {k: STRICT.get(k, name_rx(k)) for k in keys}
    area_of = base.set_index("key")["sws_area"].to_dict()
    lg = pd.read_csv(DATA / "reference" / "calabarzon_lgus.csv")
    lg["pkey"] = lg["province_name"].str.lower()
    lgu = {}
    for _, r in lg.iterrows():
        names = [r["lgu_name"]] + [x for x in str(r.get("lgu_aliases", "") or "").split("|") if x and x != "nan"]
        for nm in names:
            core = re.sub(r"\s*\(.*\)|\s+City$", "", nm).strip()
            if len(core) >= 4 and core not in CAL.values():
                lgu[core] = r["pkey"]
    rx_lgu = re.compile(r"\b(" + "|".join(sorted(map(re.escape, lgu), key=len, reverse=True)) + r")\b")
    prov_word = {k: re.compile(r"\b" + v + r"\b") for k, v in CAL.items()}
    out = []
    for r in d.itertuples(index=False):
        t = r.text or ""
        body = r.body or ""
        link = r.link or ""
        lead_hits = {k for k, x in rx.items() if x.search(t)}
        lgu_hits = set()
        for nm in set(rx_lgu.findall(t)):
            pk = lgu[nm]
            if nm in UNIQUE_ALWAYS or nm not in AMBIGUOUS or prov_word[pk].search(t):
                lgu_hits.add(pk)
        title_hit = {k for k, x in rx.items() if x.search(r.title)}
        body_ct = Counter()
        if body:
            for s in SENT.split(body)[:60]:
                for k, x in rx.items():
                    if x.search(s):
                        body_ct[k] += 1
        intl = bool(INTL_PATH.search(link)) or (bool(INTL_WORD.search(r.title)) and not lead_hits and not lgu_hits and "Philippine" not in t and "Filipino" not in t)
        areas = {a for a, x in AREA_WORD.items() if x.search(t)}
        nat_dateline = bool(NATIONAL_DATELINE.search(t[len(r.title):].lstrip(". ")))
        primary = lead_hits | lgu_hits
        weak = {k for k, c in body_ct.items() if c >= 2}
        if intl:
            level = "international"
            provs: set = set()
        elif 1 <= len(primary) <= 3:
            level = "lgu" if (lgu_hits - lead_hits) and not title_hit else "province"
            provs = primary
        elif len(primary) > 3:
            level = "multi_province"
            provs = set()
        elif REGION_IVA.search(t):
            level = "region_iva"
            provs = set()
        elif areas:
            level = "area"
            provs = set()
        elif 1 <= len(weak) <= 2 and not NATIONAL_WORD.search(t) and not nat_dateline:
            level = "province_body_only"
            provs = weak
        elif body_ct and not weak:
            level = "passing_mention"
            provs = set()
        else:
            level = "national"
            provs = set()
        pa = {area_of[k] for k in primary if k in area_of}
        if level == "multi_province" and len(pa) == 1:
            areas |= pa
        area_set = areas | {area_of[k] for k in provs if k in area_of}
        out.append((level, "|".join(sorted(provs)), "|".join(sorted(area_set)), "|".join(sorted(primary)), len(primary), len(body_ct)))
    d[["geo_level", "provinces", "areas", "named_in_lead", "n_named_lead", "n_named_body"]] = pd.DataFrame(out, index=d.index)
    return d


def build():
    d = load_all()
    n0 = len(d)
    ft = {}
    with open(R150 / "fulltext.jsonl", encoding="utf-8", newline="\n") as f:
        for x in f:
            r = json.loads(x)
            ft[r["id"]] = _clean(r["content"])
    d["body"] = d["id"].map(ft).fillna("")
    s0 = d["text"].str.contains(SURVEY) | d["title"].str.contains(SURVEY)
    d = d[~s0].copy()
    # exact duplicates across archives: same normalized title within 30 days counts once, and we remember how many outlets ran it
    d["tn"] = d["title"].map(_norm_title)
    d = d.sort_values("published").reset_index(drop=True)
    d["bucket"] = (d["published"].astype("int64") // (30 * 86400 * 10 ** 9)).astype(int)
    grp = d.groupby(["tn", "bucket"])
    d["n_copies"] = grp["id"].transform("size")
    d["n_outlets"] = grp["site"].transform("nunique")
    dup_removed = int(d.duplicated(["tn", "bucket"]).sum())
    long_title = d["tn"].str.len() >= 25
    d = d[~(d.duplicated(["tn", "bucket"]) & long_title)].copy()
    d["skip_section"] = d["link"].fillna("").str.contains(SKIP_PATH)
    d["gate"] = (d["text"].str.contains(GATE) | d["body"].str.slice(0, 1500).str.contains(GATE)) & ~d["skip_section"]
    d = attribute(d)
    d["score_text"] = [(t + " " + " ".join([s for s in SENT.split(b)[:40] if GATE.search(s)][:2]))[:650] if b else t for t, b in zip(d["text"], d["body"])]
    d["hash"] = d["score_text"].map(lambda s: hashlib.sha1(s.encode("utf-8")).hexdigest())
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    d.drop(columns=["bucket", "tn"]).to_parquet(RAW / "corpus.parquet", index=False)
    g = d[d["gate"] & (d["geo_level"] != "international")]
    g.drop_duplicates("hash")[["hash", "score_text"]].to_parquet(RAW / "to_score.parquet", index=False)
    a = {"articles_loaded": n0, "survey_reports_removed": int(s0.sum()), "exact_duplicates_seen": dup_removed, "articles_kept": int(len(d)), "by_origin": d["origin"].value_counts().to_dict(), "by_site_top": d["site"].value_counts().head(15).to_dict(), "n_sites": int(d["site"].nunique()),
         "geo_level_all": d["geo_level"].value_counts().to_dict(), "gate_pass": int(d["gate"].sum()), "geo_level_gated": g["geo_level"].value_counts().to_dict(), "to_score": int(g["hash"].nunique()), "with_full_text": int((d["body"] != "").sum()),
         "gated_by_year": g["published"].dt.year.value_counts().sort_index().to_dict(), "gated_site_share_by_year": {int(y): round(float(x["site"].value_counts(normalize=True).iloc[0]), 3) for y, x in g.groupby(g["published"].dt.year)},
         "calabarzon_gated": {k: int(g["provinces"].str.split("|").map(lambda s: k in s).sum()) for k in CAL}, "published_after_2026_09_30": int((d["published"] >= "2026-10-01").sum())}
    (OUT / "corpus_audit.json").write_text(json.dumps(a, indent=1, default=str), newline="\n")
    print(json.dumps(a, indent=1, default=str))


if __name__ == "__main__":
    build()
