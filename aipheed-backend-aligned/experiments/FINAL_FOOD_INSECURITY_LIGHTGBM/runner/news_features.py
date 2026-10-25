"""FINAL news features (FINAL_PROTOCOL.md sections 3.3-3.4): dated, de-duplicated, gap-aligned news indicators.

Step 1  load the project headline corpus (E31 + E60 stores) with PH publication times; syndicated copies removed by
        app.news.pipeline_v3.dedupe (E112 news_indicators.corpus_frame, six-category title lexicon unchanged)
Step 2  flag each food-event headline as ANTICIPATORY (forward-looking wording) or reporting
Step 3  drop repeated coverage of one event: same category, word-set Jaccard >= 0.5 with a kept headline of the previous
        7 days
Step 4  for an issue date O and the newest SWS fieldwork end F: window W = [F + 1 day, O), W' = W - 365 days;
        feature = category share in W minus the same share in W' (removes seasonality and corpus growth)
Only headlines published before O can enter W, so every feature is known at the issue date.

GDELT GKG (CALABARZON-located documents; GDELT's own processing timestamps) gives the same categories from GKG themes
and the anticipatory lexicon applied to URL slugs; it is a replication source, not a model input. GDELT DOC national
volume (E114, 2017+) feeds the long-history arm.
"""
from __future__ import annotations

import functools
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FINAL = HERE.parent
EXP = FINAL.parent
BACKEND = EXP.parents[1] / "backend"
sys.path.insert(0, str(EXP / "E112_Food_Insecurity_Forecasting" / "runner"))
import news_indicators as NI  # noqa: E402

CATS = NI.CATS
DOC_CATS = ["shortage", "agri_supply", "jobs_income", "assistance"]     # the four E114 GDELT DOC series collected
MIN_WINDOW = 30                                                        # headlines needed in W and in W'
JACCARD, DUP_DAYS = 0.5, 7
ANTICIPATORY = re.compile(
    r"\b(expect(s|ed|ing)?|could|might|likely|loom(s|ing)?|threat(s|en|ens|ened)?|warn(s|ed|ing|ings)?|alerts?|"
    r"brac(e|es|ed|ing)|forecast(s|ed)?|project(ed|ion|ions)|outlook|fears?|feared|risks?|seen to|set to|"
    r"to (rise|increase|hit|soar|spike|climb|go up|worsen)|possible|possibly|potential|anticipat\w*|"
    r"inaasahan|asahan|posibleng?|nagbabala|babala|banta|maaaring|nakaamba)\b", re.I)
_STOP = {"the", "and", "for", "with", "from", "that", "this", "are", "was", "has", "have", "its", "into", "over",
         "amid", "after", "says", "said", "new", "more", "ang", "mga", "ng", "sa", "na", "at"}


def _words(s: str) -> frozenset:
    return frozenset(w for w in re.findall(r"[a-zñ]{3,}", str(s).lower()) if w not in _STOP)


def _event_dups(d: pd.DataFrame, text: str = "title") -> np.ndarray:
    """True where a food-event item repeats an event kept in the previous DUP_DAYS days (same category, Jaccard)."""
    d = d.sort_values("published")
    dup = np.zeros(len(d), dtype=bool)
    kept: list[tuple[pd.Timestamp, frozenset, frozenset]] = []
    cats = d[CATS].to_numpy()
    for i, (ts, txt) in enumerate(zip(d["published"], d[text])):
        c = frozenset(k for k, v in zip(CATS, cats[i]) if v)
        if not c:
            continue
        w = _words(txt)
        kept = [x for x in kept if (ts - x[0]).days <= DUP_DAYS]
        if w and any(c & kc and len(w & kw) / len(w | kw) >= JACCARD for _, kc, kw in kept):
            dup[i] = True
            continue
        kept.append((ts, c, w))
    out = pd.Series(dup, index=d.index)
    return out


@functools.lru_cache(maxsize=1)
def corpus() -> pd.DataFrame:
    d = NI.corpus_frame()
    d = d[["article_key", "title", "outlet", "published", "q", "province_code"] + CATS].copy()
    d["food_event"] = d[CATS].any(axis=1)
    d["anticipatory"] = d["food_event"] & d["title"].astype(str).map(lambda s: bool(ANTICIPATORY.search(s)))
    d["event_dup"] = _event_dups(d).reindex(d.index).to_numpy()
    return d.sort_values("published").reset_index(drop=True)


@functools.lru_cache(maxsize=1)
def gkg() -> pd.DataFrame:
    g = NI.gdelt_frame()
    g = g[g["published"].notna()].copy()
    slug = g["DocumentIdentifier"].astype(str).str.rstrip("/").str.split("/").str[-1]
    g["title"] = slug.str.replace(r"\.(html?|php|aspx?)$", "", regex=True).str.replace(r"[-_+]", " ", regex=True)
    g = g.drop_duplicates("DocumentIdentifier")
    g["food_event"] = g[CATS].any(axis=1)
    g["anticipatory"] = g["food_event"] & g["title"].map(lambda s: bool(ANTICIPATORY.search(s)))
    g = g[["published", "title", "food_event", "anticipatory"] + CATS].sort_values("published").reset_index(drop=True)
    g["event_dup"] = _event_dups(g).reindex(g.index).to_numpy()
    return g


def _shares(tab: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict | None:
    w = tab[(tab["published"] >= start) & (tab["published"] < end) & ~tab["event_dup"]]
    if len(w) < MIN_WINDOW:
        return None
    out = {c: float(w[c].mean()) for c in CATS}
    fe = w[w["food_event"]]
    out["ant"] = float(fe["anticipatory"].mean()) if len(fe) else np.nan
    out["_n"], out["_last"] = len(w), w["published"].max()
    return out


@functools.lru_cache(maxsize=20000)
def gap_features(fw_end: str, issue: str, source: str = "C") -> tuple:
    """(NC_gap_<cat> x6, NC_ant, n headlines in W, latest headline time) for W = [fw_end + 1 day, issue)."""
    tab = corpus() if source == "C" else gkg()
    s, e = pd.Timestamp(fw_end) + pd.Timedelta(days=1), pd.Timestamp(issue)
    now, ago = _shares(tab, s, e), _shares(tab, s - pd.Timedelta(days=365), e - pd.Timedelta(days=365))
    if now is None or ago is None:
        return tuple([np.nan] * (len(CATS) + 1)) + ((now or {}).get("_n", 0), (now or {}).get("_last"))
    vals = [now[c] - ago[c] for c in CATS] + [now["ant"] - ago["ant"]]
    return tuple(vals) + (now["_n"], now["_last"])


@functools.lru_cache(maxsize=20000)
def ant_rep_gap(fw_end: str, issue: str, source: str = "C") -> tuple:
    """(anticipatory, reporting) food-event shares of all de-duplicated items in W, each minus its W' value
    (section 8.4 analysis; not a model input)."""
    tab = corpus() if source == "C" else gkg()
    s, e = pd.Timestamp(fw_end) + pd.Timedelta(days=1), pd.Timestamp(issue)
    vals = []
    for a, b in ((s, e), (s - pd.Timedelta(days=365), e - pd.Timedelta(days=365))):
        w = tab[(tab["published"] >= a) & (tab["published"] < b) & ~tab["event_dup"]]
        if len(w) < MIN_WINDOW:
            return (np.nan, np.nan)
        vals.append((float(w["anticipatory"].mean()), float((w["food_event"] & ~w["anticipatory"]).mean())))
    return (vals[0][0] - vals[1][0], vals[0][1] - vals[1][1])


def news_cols(prefix: str = "NC") -> list[str]:
    return [f"{prefix}_gap_{c}" for c in CATS] + [f"{prefix}_ant"]


def features(fw_end: str, issue: str, source: str = "C") -> dict:
    v = gap_features(fw_end, issue, source)
    p = "NC" if source == "C" else "NG"
    return dict(zip(news_cols(p), v[:len(CATS) + 1]))


# ================================================================================================ GDELT DOC (long arm)
@functools.lru_cache(maxsize=1)
def doc_daily() -> pd.DataFrame:
    d = pd.read_csv(FINAL / "data" / "long" / "cov_gdelt_doc.csv")
    d["Date"] = pd.to_datetime(d["Date"])
    return d.pivot_table(index="Date", columns="category", values="Value").sort_index()


@functools.lru_cache(maxsize=20000)
def doc_gap(fw_end: str, issue: str) -> tuple:
    """Mean daily GDELT DOC volume share in W minus W' for the four collected categories (NaN before 2017 coverage)."""
    d = doc_daily()
    s, e = pd.Timestamp(fw_end) + pd.Timedelta(days=1), pd.Timestamp(issue)
    s0, e0 = s - pd.Timedelta(days=365), e - pd.Timedelta(days=365)
    if s0 < d.index.min() or e > d.index.max() + pd.Timedelta(days=1) or e - s < pd.Timedelta(days=14):
        return tuple([np.nan] * len(DOC_CATS))
    now = d[(d.index >= s) & (d.index < e)]
    ago = d[(d.index >= s0) & (d.index < e0)]
    return tuple(float(now[c].mean() - ago[c].mean()) * 100 for c in DOC_CATS)


def save_flags(path: Path) -> pd.DataFrame:
    """Per-headline flags (no titles) so the news features can be audited without republishing the text."""
    d = corpus()
    out = d[["article_key", "outlet", "published", "q", "province_code", "food_event", "anticipatory", "event_dup"]
            + CATS]
    out.to_csv(path, index=False, lineterminator="\n")
    return out
