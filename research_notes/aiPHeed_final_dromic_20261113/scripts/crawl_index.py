r"""PROTOCOL_DRM step 1: index DROMIC incident pages 2016-2021 and their report files (no outcome involved).
Polite: one request at a time, 0.7 s apart. Raw HTML goes to the scratchpad (untrusted data); the index goes to evidence/.
Usage: python -I crawl_index.py <raw_dir>"""
import csv, re, sys, time, urllib.request
from datetime import datetime
from pathlib import Path
EV = Path(__file__).resolve().parents[1] / "evidence"; RAW = Path(sys.argv[1]); RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (academic research; low-rate)"}
HYD = re.compile(r"typhoon|tropical|storm|depression|lpa|low-pressure|monsoon|habagat|amihan|flood|flashflood|landslide|shear-line|trough|tail-end|rain")
CON = re.compile(r"armed-conflict")
MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def get(url, f):
    if f.exists():
        return f.read_text(encoding="utf8", errors="ignore")
    time.sleep(0.7)
    try:
        t = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf8", "ignore")
    except Exception as ex:
        return f"__ERR__ {ex}"
    f.write_text(t, encoding="utf8"); return t


def slug_date(s):
    m = re.search(r"(\d{1,2})-(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*-(\d{4})", s)
    return datetime(int(m.group(3)), MON[m.group(2)], int(m.group(1))).date() if m else None


inc = {}
for y in range(2016, 2022):
    p = 1
    while True:
        url = f"https://dromic.dswd.gov.ph/category/situation-reports/{y}/" + (f"page/{p}/" if p > 1 else "")
        t = get(url, RAW / f"cat_{y}_{p}.html")
        if t.startswith("__ERR__") or "Nothing Found" in t:
            break
        links = set(re.findall(r'href="https://dromic\.dswd\.gov\.ph/([a-z0-9-]+)/"', t))
        new = [l for l in links if slug_date(l) and l not in inc]
        for l in new:
            inc[l] = y
        mp = max([int(x) for x in re.findall(rf"situation-reports/{y}/page/(\d+)/", t)] + [1])
        if p >= mp:
            break
        p += 1
rows = []
for s, y in sorted(inc.items()):
    fam = "hydromet" if HYD.search(s) else ("conflict" if CON.search(s) else None)
    rows.append({"slug": s, "category_year": y, "event_date": slug_date(s), "family": fam or "other"})
sel = [r for r in rows if r["family"] != "other"]
for r in sel:
    t = get(f"https://dromic.dswd.gov.ph/{r['slug']}/", RAW / f"inc_{r['slug']}.html")
    files = sorted(set(re.findall(r'href="(https://dromic\.dswd\.gov\.ph/wp-content/uploads/[^"]+\.(?:docx?|pdf))"', t, flags=re.I)))
    r["n_files"] = len(files); r["files"] = " ".join(files)
with open(EV / "DROMIC_index.csv", "w", newline="", encoding="utf8") as f:
    w = csv.DictWriter(f, fieldnames=["slug", "category_year", "event_date", "family", "n_files", "files"]); w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in w.fieldnames})
from collections import Counter
print(len(rows), "incidents;", Counter((r["category_year"], r["family"]) for r in rows))
print("selected with files:", sum(1 for r in sel if r.get("n_files")), "of", len(sel))
