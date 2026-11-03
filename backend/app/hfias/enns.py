"""Parse "Percentage of households by food security status in the Philippines and <area>: ENNS, <year>" (HFIAS, 90% CI)
from the FNRI ENNS provincial monographs. `python -m app.hfias.enns` writes clean/enns_hfias.csv."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pandas as pd

from app.hfias import CLEAN, RAW

TITLE = re.compile(r"Percentage of households by food security status in the Philippines and\s+(?P<area>.+?):\s*ENNS,\s*(?P<year>\d{4})",
                   re.S)
NUM = r"(\d+\.\d)\*?"
ROWS = {"food_secure": "Food Secure", "mild": "Mildly Food Insecure", "moderate": "Moderately Food Insecure",
        "severe": "Severely Food Insecure"}
Z90 = 1.6449


def parse_text(t: str) -> dict | None:
    """The first title occurrence followed by all four HFIAS rows (the table of contents repeats the title)."""
    for m in TITLE.finditer(t):
        r = _rows(t[m.end(): m.end() + 2500])
        if r:
            return {"area": " ".join(m["area"].split()), "year": int(m["year"]), **r}
    return None


def _rows(seg: str) -> dict | None:
    out = {}
    for k, label in ROWS.items():
        r = re.search(rf"{label}\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}", seg)
        if not r:
            return None
        ph, ph_l, ph_u, p, l, u = (float(x) for x in r.groups())
        out.update({f"{k}_pct": p, f"{k}_ci90": [l, u], f"{k}_se": (u - l) / (2 * Z90), f"ph_{k}_pct": ph,
                    f"{k}_sig_vs_ph": "*" in r.group(0).split()[-3]})
    return out


DECK = re.compile(r"Distribution of households by food security status:\s*Philippines and\s+(?P<area>.+?),\s*(?P<year>\d{4})"
                  r"\s+90%\s+CI\s+LL\s+(?P<ll>(?:\d+\.\d\s+){8})UL\s+(?P<ul>(?:\d+\.\d\s+){8})(?:\*[^\n]*\n)?"
                  r"(?P<v>(?:\d+\.\d\s+){8})", re.S)
HEADLINE = re.compile(r"Percentage of food insecure households\s*=\s*(\d+\.\d)%")
HEAD_TITLE = re.compile(r"(?:Philippines and|food insecurity items:)\s+(?P<area>[^\n,]+?),\s*(?P<year>201\d)")


def parse_deck(t: str) -> dict | None:
    """2019 slide decks: the HFIAS distribution chart prints 90% CI limits (Philippines, province pairs per category)
    and then the eight bar values (Philippines secure, mild, moderate, severe; then the province's)."""
    m = DECK.search(t)
    if not m:
        return None
    ll, ul, v = (list(map(float, m[g].split())) for g in ("ll", "ul", "v"))
    out = {"area": " ".join(m["area"].replace("Province", "").split()), "year": int(m["year"])}
    for i, k in enumerate(ROWS):
        lo, hi = ll[2 * i + 1], ul[2 * i + 1]
        out.update({f"{k}_pct": v[4 + i], f"{k}_ci90": [lo, hi], f"{k}_se": (hi - lo) / (2 * Z90),
                    f"ph_{k}_pct": v[i], f"{k}_sig_vs_ph": None})
    f = re.search(r"(\d+\.\d)\s+(\d+\.\d)\s+(\d+\.\d)\s+(\d+\.\d)\s+0\s+5\s+10[\s\d]*?Moderately Food Insecure Severely Food Insecure"
                  r"\s+Prevalence \(%\)", t)
    if f:                                                       # FIES (12-month recall): a different instrument, kept apart
        ph_m, ph_s, pm, ps = map(float, f.groups())
        out.update({"fies_mod_sev_pct": pm + ps, "ph_fies_mod_sev_pct": ph_m + ph_s})
    return out


def parse_headline(t: str) -> dict | None:
    """Image-only decks: only FNRI's headline 'Percentage of food insecure households = X%' (HFIAS, any level) is text."""
    h, m = HEADLINE.search(t), HEAD_TITLE.search(t)
    if not (h and m):
        return None
    return {"area": " ".join(m["area"].replace("Province", "").split()), "year": int(m["year"]),
            "insecure_headline_pct": float(h.group(1)), "headline_only": True}


def parse_pdf(p: Path) -> dict | None:
    t = subprocess.run(["pdftotext", "-raw", str(p), "-"], capture_output=True, text=True).stdout
    r = parse_text(t) or parse_deck(t) or parse_headline(t)
    if r:
        r["file"] = p.name
    return r


def build(src: Path = RAW / "fnri") -> pd.DataFrame:
    rows = [r for p in sorted(src.glob("*.pdf")) if (r := parse_pdf(p))]
    d = pd.DataFrame(rows)
    for c in ("food_secure_pct", "moderate_pct", "severe_pct", "mild_pct", "food_secure_se", "moderate_se", "severe_se",
              "ph_moderate_pct", "ph_severe_pct", "insecure_headline_pct"):
        if c not in d:
            d[c] = float("nan")
    d["mod_sev_pct"] = d["moderate_pct"] + d["severe_pct"]
    d["mod_sev_se"] = (d["moderate_se"] ** 2 + d["severe_se"] ** 2) ** 0.5
    d["ph_mod_sev_pct"] = d["ph_moderate_pct"] + d["ph_severe_pct"]
    d["insecure_pct"] = (100 - d["food_secure_pct"]).fillna(d["insecure_headline_pct"])
    d["insecure_se"] = d["food_secure_se"]                     # NaN for headline-only decks (no interval printed)
    d["instrument"] = "HFIAS"
    d["sum_check"] = d["food_secure_pct"] + d["mild_pct"] + d["moderate_pct"] + d["severe_pct"]
    for c in [c for c in d.columns if c.endswith("_ci90")]:
        d[c] = d[c].map(lambda v: f"{v[0]}-{v[1]}" if isinstance(v, list) else None)
    CLEAN.mkdir(parents=True, exist_ok=True)
    d.to_csv(CLEAN / "enns_hfias.csv", index=False, lineterminator="\n")
    return d


if __name__ == "__main__":
    d = build()
    print(len(d), d["year"].value_counts().to_dict())
