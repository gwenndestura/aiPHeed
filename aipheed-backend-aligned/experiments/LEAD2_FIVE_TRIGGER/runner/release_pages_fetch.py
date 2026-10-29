"""Archived copies of the PSA Region IV-A CPI release pages (Internet Archive Wayback Machine), saved as evidence and
parsed into a catalogue. The live site (rsso04a.psa.gov.ph) sits behind bot verification, which is not bypassed.

For every archived CPI page: the page title, the release's own **Release-Date** field (the release record's date, kept
distinct from the page's posting / capture timestamps), its reference number, the reference month named in the title,
the series (all income households vs bottom 30% / Lucena City, which are other series), and the provinces whose
inflation figures the text states. Pages whose reference month is 2026-10 or later are skipped (blind boundary).

    python release_pages_fetch.py [cdx.txt]   # ../data/psa_release_evidence/wayback/*.html, ../data/psa_release_evidence/wayback_catalog.csv
"""
from __future__ import annotations

import csv
import html
import re
import sys
import time
import urllib.request
from pathlib import Path

import lt_lib as T

OUT = T.DATA / "psa_release_evidence"
SAVE = OUT / "wayback"
MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september",
                                           "october", "november", "december"])}
PROV = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]


def text_of(s: str) -> list[str]:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", s, flags=re.S)
    return [x.strip() for x in html.unescape(re.sub(r"<[^>]+>", "\n", t)).split("\n") if x.strip()]


def parse(s: str) -> dict:
    L = text_of(s)
    title = L[0].split("|")[0].strip() if L else ""
    rel = ref = label = ""
    for i, x in enumerate(L):
        if x.lower().replace(" ", "").rstrip(":") in ("release-date", "releasedate", "dateofrelease") and i + 1 < len(L):
            rel, label = L[i + 1], x
            if i + 3 < len(L) and re.fullmatch(r"\d{4}-\d{2,4}", L[i + 3]):
                ref = L[i + 3]
            elif i + 2 < len(L) and re.fullmatch(r"\d{4}-\d{2,4}", L[i + 2]):
                ref = L[i + 2]
            break
    iso = ""
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})", rel)
    if m and m.group(1).lower() in MONTHS:
        iso = f"{m.group(3)}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    tm = re.search(r"(?i)(january|february|march|april|may|june|july|august|september|october|november|december)\s*,?\s*(20\d\d)", title)
    refm = f"{tm.group(2)}-{MONTHS[tm.group(1).lower()]:02d}" if tm else ""
    body = " ".join(L[:200])
    low = title.lower() + " " + body.lower()[:3000]
    series = ("bottom_30" if "bottom 30" in low or "bottom-30" in low else "lucena_city" if "lucena" in title.lower() else "all_income")
    stated = [p for p in PROV if re.search(rf"{p}[^.]{{0,120}}\d+(\.\d+)?\s*percent", body)]
    return {"title": title, "release_date_label": label, "release_date_field": rel, "release_date_iso": iso, "reference_no": ref, "reference_month": refm,
            "series": series, "provinces_with_figures": ";".join(stated), "subject": subject(L, title)}


def subject(L: list[str], title: str) -> str:
    """Whose release this is: the province named in the title, else the one named in the first substantive sentence
    after the release-date field (e.g. "The Batangas Province headline inflation..."), else "regional" when that
    sentence is about CALABARZON / Region IV-A; "unknown" otherwise. Generic titles hide many provincial releases."""
    named = [p for p in PROV if p.lower() in title.lower()]
    if len(named) == 1:
        return named[0]
    i = next((j for j, x in enumerate(L) if x.lower().replace(" ", "").rstrip(":") in ("release-date", "releasedate")), 0)
    for x in L[i + 1:i + 40]:
        if len(x) < 60:
            continue
        reg = min([x.find(k) for k in ("CALABARZON", "Region IV-A") if k in x], default=10 ** 6)
        prov = min([(x.find(p), p) for p in PROV if p in x], default=(10 ** 6, ""))
        if prov[0] < reg:
            return prov[1]
        if reg < 10 ** 6:
            return "regional"
    return "unknown"


def main():
    cdxs = [Path(a) for a in sys.argv[1:]] or sorted(OUT.glob("wayback_cdx_*.txt"))
    SAVE.mkdir(parents=True, exist_ok=True)
    rows = [l.split() for c in cdxs for l in c.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if len(r) >= 3 and r[2] == "200" and re.search(r"(?i)inflat|consumer-price|cpi", r[1])]
    cat = []
    for ts, url, *_ in rows:
        slug = url.rstrip("/").split("/")[-1]
        dst = SAVE / f"{slug}__{ts}.html"
        if not dst.exists():
            req = urllib.request.Request(f"https://web.archive.org/web/{ts}id_/{url}", headers={"User-Agent": "aiPHeed-research/1.0"})
            err = ""
            for attempt in range(3):
                try:
                    dst.write_bytes(urllib.request.urlopen(req, timeout=60).read())
                    err = ""
                    break
                except Exception as e:                                # noqa: BLE001
                    err = str(e)
                    if "404" in err:
                        break
                    time.sleep(15 * (attempt + 1))
            if err:
                cat.append({"capture": ts, "url": url, "file": "", "error": err})
                continue
            time.sleep(1.5)
        p = parse(dst.read_text(encoding="utf-8", errors="replace"))
        if p["reference_month"] and p["reference_month"] >= "2026-10":
            dst.unlink()                                               # blind boundary: never keep sealed-period releases
            continue
        if p["reference_month"] and p["reference_month"] < "2021-01":
            dst.unlink()                                               # study window 2021+: not needed
            continue
        cat.append({"capture": ts, "url": url, "file": f"wayback/{dst.name}", "sha256": T.sha256(dst), **p,
                    "wayback_url": f"https://web.archive.org/web/{ts}/{url}", "error": ""})
    cols = ["reference_month", "title", "release_date_label", "release_date_field", "release_date_iso", "reference_no", "series", "subject", "provinces_with_figures",
            "url", "capture", "wayback_url", "file", "sha256", "error"]
    with open(OUT / "wayback_catalog.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(cat, key=lambda r: (r.get("reference_month", ""), r.get("title", ""))))
    print(len(cat), "pages catalogued;", sum(1 for r in cat if r.get("error")), "errors")


if __name__ == "__main__":
    main()
