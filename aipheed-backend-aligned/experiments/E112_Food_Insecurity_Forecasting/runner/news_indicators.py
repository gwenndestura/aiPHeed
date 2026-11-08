"""E112 news indicators: dated, de-duplicated, coverage-normalised and de-seasonalised event signals.

Step 1  load every headline of the project corpus (E31 + E60 stores; app.news.pipeline_v3.corpus), with its PH publication time
Step 2  drop syndicated copies (pipeline_v3.dedupe: same normalised title within 3 days, any outlet)
Step 3  tag each headline with the six event categories below (title keyword lexicon, English and Filipino; transparent)
Step 4  per quarter: share of all headlines in each category (coverage-normalised; the corpus grows ~4x over 2021-26)
Step 5  de-season: year-over-year change of each share (quarter q minus quarter q-4), so the typhoon calendar cancels
Step 6  a quarter's indicator is available at issue date O(t) only if every headline of that quarter was published
        before O(t): the forecast at O(t) uses quarter t (complete on the last day before O(t)) and earlier quarters

GDELT GKG (backend/data/gdelt_e85, CALABARZON-located documents, 2021+) gives the same six categories from GKG themes as
an independent cross-check source. No hunger data are read here.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E112 = HERE.parent
BACKEND = E112.parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

CATEGORIES = {
    "price": r"\bpric(e|es|ing)\b|presyo|inflation|implasyon|price (hike|increase|cap|ceiling)|taas[- ]?presyo|mahal|"
             r"\bcostly\b|\bexpensive\b|rice price|bigas",
    "shortage": r"shortage|kakulangan|\bhunger\b|\bhungry\b|gutom|food insecurity|food security|malnutrition|"
                r"walang makain|supply (gap|problem|deficit)|scarcity",
    "disaster": r"typhoon|bagyo|\bstorm\b|\bflood|baha|landslide|drought|tagtuyot|el ni[nñ]o|la ni[nñ]a|"
                r"state of calamity|calamity|eruption|earthquake|lindol",
    "agri_supply": r"\bcrop|palay|harvest|\bani\b|farmer|magsasaka|fisher|mangingisda|fish ?kill|\basf\b|"
                   r"african swine|bird flu|avian|agricultur|production loss|damage to agri|livestock|poultry",
    "jobs_income": r"unemploy|jobless|layoff|laid off|walang trabaho|\bjobs?\b|\bwage|sahod|sweldo|income|\bofw|"
                   r"remittance|livelihood|kabuhayan",
    "assistance": r"ayuda|relief|food pack|\baid\b|subsid|assistance|tulong|kadiwa|4ps|walang gutom|"
                  r"cash (aid|grant|transfer)|distribution|feeding",
}
GDELT_THEMES = {
    "price": ("ECON_INFLATION", "WB_442_INFLATION", "TAX_ECON_PRICE", "FUELPRICES"),
    "shortage": ("FOOD_SECURITY", "TAX_DISEASE_STARVATION", "NATURAL_DISASTER_FAMINE", "UNGP_AFFORDABLE_NUTRITIOUS_FOOD"),
    "disaster": ("NATURAL_DISASTER",),
    "agri_supply": ("WB_174_CROP_PRODUCTION", "AGRICULTURE", "TAX_FNCACT_FARMERS", "TAX_FNCACT_FISHERMEN"),
    "jobs_income": ("UNEMPLOYMENT", "WB_2747_UNEMPLOYMENT", "TAX_FNCACT_UNEMPLOYED"),
    "assistance": ("WB_1609_FOOD_AND_IN_KIND_TRANSFERS", "TAX_AIDGROUPS"),
}
CATS = list(CATEGORIES)
_RX = {k: re.compile(v, re.I) for k, v in CATEGORIES.items()}


def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def corpus_frame() -> pd.DataFrame:
    from app.news import pipeline_v3 as P
    arts, _ = P.dedupe(list(P.corpus()))
    d = pd.DataFrame(arts)
    d["published"] = pd.to_datetime(d["published_ph"].astype(str).str[:19])
    d["q"] = d["quarter"].map(qi)
    for k, rx in _RX.items():
        d[k] = d["title"].astype(str).map(lambda s, rx=rx: bool(rx.search(s)))
    d["any_food_event"] = d[CATS].any(axis=1)
    return d


def gdelt_frame() -> pd.DataFrame:
    g = pd.read_parquet(BACKEND / "data/gdelt_e85/gkg_calabarzon_2021_2026.parquet")
    g["published"] = pd.to_datetime(g["DATE"].astype(str).str[:14], format="%Y%m%d%H%M%S", errors="coerce")
    g["q"] = g["published"].dt.year * 4 + (g["published"].dt.month - 1) // 3
    themes = g["V2Themes"].fillna("").map(lambda t: {x.split(",")[0] for x in t.split(";") if x})
    for k, pre in GDELT_THEMES.items():
        g[k] = themes.map(lambda s, pre=pre: any(any(x.startswith(p) for p in pre) for x in s))
    return g


def quarterly(d: pd.DataFrame, source: str) -> pd.DataFrame:
    """Per quarter: n, last publication time, category shares, and their year-over-year change."""
    g = d.groupby("q")
    out = pd.DataFrame({"n": g.size(), "last_published": g["published"].max()})
    for k in CATS:
        out[f"{k}_share"] = g[k].mean()
    out = out.sort_index()
    for k in CATS:
        prev = out[f"{k}_share"].reindex(out.index - 4).to_numpy()
        out[f"{k}_yoy"] = out[f"{k}_share"].to_numpy() - prev
    out.index.name = "q"
    out["quarter"] = [qs(int(q)) for q in out.index]
    out["source"] = source
    return out.reset_index()


def build() -> dict[str, pd.DataFrame]:
    return {"corpus": quarterly(corpus_frame(), "project RSS corpus (E31+E60), title lexicon"),
            "gdelt": quarterly(gdelt_frame(), "GDELT GKG themes, CALABARZON-located")}


def features_at(t: int, table: pd.DataFrame, prefix: str) -> dict:
    """News indicators usable at issue date O(t): quarter t's YoY changes (complete before O(t))."""
    row = table[table["q"] == t]
    if not len(row):
        return {f"{prefix}{k}": np.nan for k in CATS}
    r = row.iloc[0]
    return {f"{prefix}{k}": float(r[f"{k}_yoy"]) if pd.notna(r[f"{k}_yoy"]) else np.nan for k in CATS}


if __name__ == "__main__":
    t = build()
    for name, df in t.items():
        df.to_csv(E112 / "out" / f"news_quarterly_{name}.csv", index=False, lineterminator="\n", float_format="%.6g")
        print(name, len(df))
        print(df[["quarter", "n"] + [f"{k}_share" for k in CATS]].round(3).to_string(index=False))
