"""
E155 deeper news: GDELT DOC 2.0 article counts per province and theme, from Philippine sources, daily from 2017. Public API, polite pacing, no outcome read.

For each province: articles mentioning it (the denominator, as in Balashankar et al. 2023) and articles mentioning it with each food-related theme.
Resumes where it stopped: one file per province and series.

    python -m app.e155.gdelt -> data/e155/raw/gdelt/<key>__<series>.csv
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from urllib.parse import quote

from app.e147 import features as Fe
from app.paths import BACKEND_DIR

RAW = BACKEND_DIR / "data" / "e155" / "raw" / "gdelt"
UA = "Mozilla/5.0 (aiPHeed thesis research; polite)"
THEMES = {"price": ("ECON_INFLATION", "TAX_ECON_PRICE", "FUELPRICES"), "shortage": ("FOOD_SECURITY", "TAX_DISEASE_STARVATION", "NATURAL_DISASTER_FAMINE"), "agri": ("WB_174_CROP_PRODUCTION", "AGRICULTURE", "TAX_FNCACT_FARMERS", "TAX_FNCACT_FISHERMEN"),
          "jobs": ("UNEMPLOYMENT", "WB_2747_UNEMPLOYMENT"), "disaster": ("NATURAL_DISASTER",), "aid": ("WB_1609_FOOD_AND_IN_KIND_TRANSFERS", "TAX_AIDGROUPS")}
PLACE = {"quezon": '"Quezon province"', "rizal": '"Rizal province"', "mountain province": '"Mountain Province"', "isabela province": '"Isabela province"', "cagayan province": '"Cagayan province"', "iloilo province": 'Iloilo', "north cotabato": '"North Cotabato"', "compostela valley": '"Compostela Valley"', "western samar": '"Western Samar"', "aurora": '"Aurora province"', "antique": '"Antique province"', "bay": None}
START, END = "20170101000000", "20261001000000"


def place(key: str) -> str | None:
    if key in PLACE:
        return PLACE[key]
    name = re.sub(r"\s+province$", "", key).title()
    return f'"{name}"' if " " in name else name


def fetch(q: str, path) -> str:
    url = ("https://api.gdeltproject.org/api/v2/doc/doc?query=" + quote(q) + "&mode=timelinevolraw&format=csv&timelinesmooth=0&startdatetime=" + START + "&enddatetime=" + END)
    for attempt in range(6):
        time.sleep(5.2 + 20 * attempt)
        try:
            raw = subprocess.run(["curl", "-s", "-m", "240", "-A", UA, url], check=True, capture_output=True).stdout
        except subprocess.CalledProcessError:
            continue
        if raw[:6] != b"Please" and b"Date" in raw[:40]:
            path.write_bytes(raw)
            return "ok"
        if raw and raw[:6] != b"Please":
            return "empty"
    return "throttled"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    keys = sorted(Fe.base_rows()["key"].unique())
    first = ["batangas", "cavite", "laguna", "quezon", "rizal"]
    keys = first + [k for k in keys if k not in first]
    log = []
    core = ["all", "price", "shortage", "disaster"]
    # first pass: every series for the five provinces, the core four for the rest; second pass: the remaining themes
    plan = [(k, s) for k in keys for s in (["all"] + list(THEMES) if k in first else core)] + [(k, s) for k in keys if k not in first for s in THEMES if s not in core]
    for k, s in plan:
        p = place(k)
        if not p:
            continue
        for s in [s]:
            f = RAW / f"{k.replace(' ', '_')}__{s}.csv"
            if f.exists():
                continue
            q = f"sourcecountry:philippines {p}" + ("" if s == "all" else " (" + " OR ".join(f"theme:{t}" for t in THEMES[s]) + ")")
            st = fetch(q, f)
            log.append(f"{k}\t{s}\t{st}")
            print(k, s, st, flush=True)
    (RAW / "fetch_log.tsv").write_text("\n".join(log) + "\n", newline="\n")
    print("done", flush=True)


if __name__ == "__main__":
    main()
