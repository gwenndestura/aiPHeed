"""E60 step N2: trigger-targeted news collection into a NEW store (the E28/E31 stores are never written).

Root cause found in N1: the E28/E31 corpus was collected with six food/shock/relief query templates only; no query asked
about OFW remittances, employment or fisheries, so those trigger shares are structurally ~0. This script runs the
existing, tested Collector (app.news.collector: monthly windows, window splitting at the 100-item cap, credible-domain
policy v1, the project geocoder, authorized_through limit) with an additional trigger query plan written from the
trigger definitions only (no forecasting outcome was consulted).

    backend/venv/Scripts/python.exe -B runner/n2_collect_triggers.py [--max-requests N]
      -> data/news_e60/{articles,rejected,requests,windows,runs}.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

E60 = Path(__file__).resolve().parents[1]
BACKEND = E60.parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

import app.news.collector as C  # noqa: E402

TRIGGER_QUERIES = (
    C.QuerySpec("trg_market_en", "en", "market and food-price pressure",
                '{A} ("price hike" OR "rice price" OR "onion price" OR "price increase" OR shortage OR "price freeze" OR '
                '"price ceiling" OR "suggested retail price")'),
    C.QuerySpec("trg_climate_en", "en", "climate and agricultural disruption",
                '{A} ("crop damage" OR "agricultural damage" OR "damage to agriculture" OR "state of calamity" OR '
                '"El Nino" OR "La Nina" OR drought OR "rice farmers")'),
    C.QuerySpec("trg_fish_en", "en", "fish kills and fisheries disruption",
                '{A} ("fish kill" OR "red tide" OR "fishing ban" OR fisherfolk OR fishermen OR aquaculture OR '
                '"oil spill" OR "closed fishing season")'),
    C.QuerySpec("trg_employ_en", "en", "employment and livelihood pressure",
                '{A} (layoff OR layoffs OR retrenchment OR "job loss" OR jobless OR unemployment OR "factory closure" OR '
                '"displaced workers")'),
    C.QuerySpec("trg_ofw_en", "en", "OFW remittances and household support",
                '{A} (OFW OR OFWs OR remittance OR remittances OR "overseas Filipino" OR repatriated OR "migrant workers")'),
    C.QuerySpec("trg_fil", "fil", "Filipino: prices, fisheries, jobs, OFW, farm damage",
                '{A} (taas-presyo OR "mahal na bigas" OR mangingisda OR "nawalan ng trabaho" OR tanggal OR OFW OR '
                'padala OR "pinsala sa agrikultura")'),
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-requests", type=int, default=None)
    ap.add_argument("--from", dest="q_from", default="2021-Q1")
    ap.add_argument("--to", dest="q_to", default="2026-Q3")
    a = ap.parse_args()
    from app.news.policy import credible_fn
    from app.news.sources import GoogleNewsRSS
    from app.news.store import NewsStore
    from app.news.timeutil import quarters_between

    C.plan_for = lambda province: () if province == C.REGION else TRIGGER_QUERIES   # trigger plan only
    auth = json.loads((BACKEND / "config" / "authorization.json").read_text(encoding="utf-8"))
    store = NewsStore(E60 / "data" / "news_e60")
    col = C.Collector(store, [GoogleNewsRSS()], authorized_until=auth["authorized_until"], now=datetime.now(timezone.utc),
                      credible=credible_fn(None), authorized_through=auth["authorized_through"])
    res = col.run("backfill_e60_triggers", quarters_between(a.q_from, a.q_to), provinces=list(C.PROVINCES),
                  max_requests=a.max_requests)
    (E60 / "data" / "news_e60" / "query_plan.json").write_text(json.dumps(
        [{"query_id": s.query_id, "lang": s.lang, "theme": s.theme, "template": s.template} for s in TRIGGER_QUERIES], indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
