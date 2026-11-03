"""FOOD_INSECURITY_SYSTEM Step 4 (PLAN.md section 2-3): fetch the PSA poverty tables once, read only.

    python fetch_psa.py      # -> backend/data/foodinsecurity_engine/psa/*.json (raw) + psa_poverty.csv

- Table 1  (0011F3DF010): poverty incidence among FAMILIES by province, 2018/2021/2023 -> the province weight (2023).
- Table 2  (0031F3DF020): poverty incidence among POPULATION by province -> the Lucena fallback (Quezon, 2021).
- Table 2a (0041F3DF02A): the same by province and highly urbanized city -> Lucena's own 2021 value.
Every raw response is stored with its SHA-256; nothing is fetched again by export_fi.py.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

EXP = Path(__file__).resolve().parents[2]
ROOT = EXP.parents[1]
OUT = ROOT / "backend" / "data" / "foodinsecurity_engine" / "psa"
API = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/1F/FY/"
TABLES = {"T1": "0011F3DF010.px", "T2": "0031F3DF020.px", "T2a": "0041F3DF02A.px"}
PLACES = {"Region IV-A": "PH040000000", "Batangas": "PH040500000", "Cavite": "PH040100000",
          "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000", "City of Lucena": "045624000"}


def _get(url: str, body: dict | None = None) -> bytes:
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "aiPHeed-research/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def _place(text: str) -> str | None:
    t = text.strip(". ")
    if t.startswith("Quezon City"):
        return None
    for name, code in PLACES.items():
        if t.startswith(name if name != "Region IV-A" else "Region IV-A (CALABARZON)"):
            return code
    return None


def fetch(tid: str, px: str) -> list[dict]:
    meta = json.loads(_get(API + px))
    geo = next(v for v in meta["variables"] if v["code"] == "Geolocation")
    sel = {c: _place(t) for c, t in zip(geo["values"], geo["valueTexts"])}
    sel = {c: p for c, p in sel.items() if p}
    others = [v for v in meta["variables"] if v["code"] != "Geolocation"]
    body = {"query": [{"code": "Geolocation", "selection": {"filter": "item", "values": list(sel)}}]
            + [{"code": v["code"], "selection": {"filter": "item", "values": v["values"]}} for v in others],
            "response": {"format": "json"}}
    raw = _get(API + px, body)
    (OUT / f"{tid}.json").write_bytes(raw)
    (OUT / f"{tid}_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    data = json.loads(raw)
    keys = [c["code"] for c in data["columns"] if c["type"] != "c"]
    texts = {v["code"]: dict(zip(v["values"], v["valueTexts"])) for v in meta["variables"]}
    rows = []
    for d in data["data"]:
        k = dict(zip(keys, d["key"]))
        geo_text = texts["Geolocation"][k["Geolocation"]]
        item_var = next(c for c in keys if c not in ("Geolocation", "Year"))
        val = d["values"][0]
        rows.append({"table": tid, "px": px, "place_code": sel[k["Geolocation"]], "place_text": geo_text.strip(". "),
                     "year": int(texts["Year"][k["Year"]]), "item": texts[item_var][k[item_var]],
                     "value": None if val in ("..", "...", "-", "") else float(val),
                     "raw_sha256": hashlib.sha256(raw).hexdigest(), "url": API + px})
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [r for tid, px in TABLES.items() for r in fetch(tid, px)]
    df = pd.DataFrame(rows)
    df["fetched_on"] = date.today().isoformat()
    df.to_csv(OUT / "psa_poverty.csv", index=False)
    show = df[df["item"].str.contains("Incidence|Coefficient", regex=True)]
    print(show.pivot_table(index=["table", "place_text", "item"], columns="year", values="value").to_string())


if __name__ == "__main__":
    main()
