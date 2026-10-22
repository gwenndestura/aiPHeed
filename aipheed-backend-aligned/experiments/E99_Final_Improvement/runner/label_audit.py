"""E99-F Q6 (PROTOCOL.md): audit every thesis-mode API payload for probability wording attached to outputs that are
not validated probabilities (the LightGBM price-pressure score, FIRI, LGU indices). Run from backend/ with the backend
venv:  AIPHEED_LEAD2_MODEL=thesis <venv python> .../label_audit.py [out.json]"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter


PATTERNS = {
    "pct_chance": re.compile(r"\d{1,3}\s?%\s+(chance|probability|likelihood)", re.I),
    "chance_of_that": re.compile(r"\bchance (of|that)\b", re.I),
    "pct_probability_paren": re.compile(r"\(\s?\d{1,3}\s?% probability", re.I),
    "probability_of_high": re.compile(r"probability of HIGH", re.I),
    "province_probability": re.compile(r"province probability|probability x vulnerability", re.I),
    "price_pressure_pct": re.compile(r"price[- ]pressure (forecast|score)? ?(is|of)? ?\d{1,3}\s?%", re.I),
}
PROVS = ("batangas", "cavite", "laguna", "quezon", "rizal")
QUARTERS = ("2027-Q1", "2026-Q3", "2024-Q2")


def strings(o, path="$"):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from strings(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from strings(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def main(out: str | None = None) -> dict:
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    urls = ["/api/v1/config", "/api/v1/quarters"]
    for q in QUARTERS:
        urls += [f"/api/v1/provinces?quarter={q}", f"/api/v1/ranking?quarter={q}"]
        urls += [f"/api/v1/provinces/{p}/municipalities?quarter={q}" for p in PROVS]
        urls += [f"/api/v1/forecast?scope=province&id={p}&quarter={q}" for p in PROVS]
        urls += [f"/api/v1/explainability?scope=province&id={p}&quarter={q}" for p in PROVS]
        urls += [f"/api/v1/forecast?scope=region&id=calabarzon&quarter={q}",
                 f"/api/v1/explainability?scope=region&id=calabarzon&quarter={q}",
                 f"/api/v1/explainability?scope=municipality&id=quezon-lucena&quarter={q}"]
    urls += [f"/api/v1/forecast/timeseries?scope=province&id={p}" for p in PROVS]
    urls += ["/api/v1/report/data?type=trend&scope=region", "/api/v1/report/data?type=shap&scope=region&to=2027-Q1",
             "/api/v1/report/data?type=shap&scope=province&id=quezon&to=2027-Q1",
             "/api/v1/news?scope=region&id=calabarzon", "/api/v1/news?scope=province&id=quezon&quarter=2026-Q3"]
    hits, status = [], {}
    for u in urls:
        r = c.get(u)
        status[u] = r.status_code
        if r.status_code != 200:
            continue
        seen = set()
        for path, s in strings(r.json()):
            for name, rx in PATTERNS.items():
                if rx.search(s) and (name, s) not in seen:
                    seen.add((name, s))
                    hits.append({"url": u, "path": re.sub(r"\[\d+\]", "[]", path), "pattern": name, "text": s[:240]})
    res = {"urls": status, "hits": len(hits),
           "by_pattern": dict(Counter(h["pattern"] for h in hits)),
           "by_path": dict(Counter(h["path"] for h in hits)), "examples": hits[:40]}
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)
    return res


if __name__ == "__main__":
    os.environ.setdefault("AIPHEED_LEAD2_MODEL", "thesis")         # only when run as a script (not on import by tests)
    os.environ.setdefault("AIPHEED_NOW", "2026-10-22T10:00:00")
    sys.path.insert(0, ".")
    r = main(sys.argv[1] if len(sys.argv) > 1 else None)
    print(json.dumps({k: r[k] for k in ("hits", "by_pattern", "by_path")}, indent=1))
    for h in r["examples"][:25]:
        print(h["pattern"], "|", h["path"], "|", h["text"][:170])
    print({u: s for u, s in r["urls"].items() if s != 200})
