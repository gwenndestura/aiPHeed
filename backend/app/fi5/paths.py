"""File locations for FI5. Everything FI5 reads or writes lives under backend/data/fi5 (raw copies of public
sources, NLP caches, outputs) or backend/data (the news corpus and the LGU reference tables)."""
from __future__ import annotations

from app.paths import BACKEND_DIR

DATA = BACKEND_DIR / "data"
FI5 = DATA / "fi5"
RAW = FI5 / "raw"
NLP = FI5 / "nlp"
OUT = FI5 / "out"
MODELS = FI5 / "models"

NEWS_ARTICLES = [DATA / "news_e31" / "articles.jsonl", DATA / "news_e60" / "articles.jsonl"]
LGU_REFERENCE = DATA / "reference" / "calabarzon_lgus.csv"
LGU_POVERTY_SAE2021 = DATA / "reference" / "sae2021_calabarzon_municipal.csv"

for _d in (RAW, NLP, OUT, MODELS):
    _d.mkdir(parents=True, exist_ok=True)
