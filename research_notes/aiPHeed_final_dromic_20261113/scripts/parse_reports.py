r"""PROTOCOL_DRM step 2: choose, per event and window, the latest DROMIC report published before the window cut-off; download it (raw dir,
untrusted); extract PROVINCE rows of the affected / displaced / damaged-houses / cost-of-assistance tables. No outcome is read.
Usage: python -I parse_reports.py <raw_dir>        (PDFs: text extraction with PyMuPDF when importable, else logged as unparsed)"""
import csv, hashlib, html, json, re, sys, time, urllib.parse, urllib.request, zipfile
from datetime import date, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]; EV = HERE / "evidence"; RAW = Path(sys.argv[1]); DL = RAW / "reports"; DL.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (academic research; low-rate)"}
# Lead-1 issue quarters of the folds (quarter index = 4*year + q - 1): ENNS2018 T=8076 -> i 8075 (2018-Q4); ENNS2019 T=8078 -> 8077 (2019-Q2);
# ENNS2021 T=8086 -> 8085 (2021-Q2). Values are read from the fold tables in drm_features.py and checked against these.
WINDOWS = {"T2": (date(2015, 7, 1), None), "T3": (date(2015, 7, 1), None), "T4": (date(2015, 7, 1), None)}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
norm = lambda s: re.sub(r"[^a-z]", "", str(s).lower().replace("province", "").replace("city of ", ""))


def file_date(url):
    name = url.rsplit("/", 1)[-1].lower()
    c = re.findall(r"(\d{1,2})[-_ ]?(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*[-_ ]?(\d{4})", name)
    if c:
        d, m, y = c[-1]
        try:
            return datetime(int(y), MONTHS[m[:3]], int(d)).date(), "filename"
        except ValueError:
            pass
    m = re.search(r"/uploads/(\d{4})/(\d{2})/", url)
    if m:  # upload month; conservative = last day of that month
        y, mo = int(m.group(1)), int(m.group(2))
        nxt = date(y + (mo == 12), 1 if mo == 12 else mo + 1, 1)
        return date.fromordinal(nxt.toordinal() - 1), "upload_month_end"
    return None, "none"


def text_date(s):
    c = re.findall(r"(\d{1,2})\s*(january|february|march|april|may|june|july|august|september|october|november|december)[,\s]+(\d{4})", s.lower())
    if c:
        d, m, y = c[-1]
        try:
            return datetime(int(y), MONTHS[m[:3]], int(d)).date()
        except ValueError:
            return None
    return None


def links_for(slug):
    """All report links on the cached incident page: site uploads (.docx/.pdf) and Google Docs (2016-2017), each with its date
    (link text first, then file name, then upload month)."""
    p = RAW / f"inc_{slug}.html"
    if not p.exists():
        return []
    t = p.read_text(encoding="utf8", errors="ignore"); out = {}
    for u, a in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', t, flags=re.S):
        a = html.unescape(re.sub(r"<[^>]+>", "", a)).strip()
        if re.search(r"/wp-content/uploads/.+\.(docx?|pdf)$", u, flags=re.I):
            d = text_date(a); src = "link_text"
            if d is None:
                d, src = file_date(u)
            out[u] = (u, d, src)
        else:
            m = re.search(r"docs\.google\.com/(?:a/[^/]+/)?document/d/([\w-]+)", u)
            if m:
                d = text_date(a)
                out[f"gdoc:{m.group(1)}"] = (f"gdoc:{m.group(1)}", d, "link_text" if d else "none")
    return list(out.values())


def fetch(url):
    if url.startswith("gdoc:"):
        gid = url[5:]; f = DL / f"gdoc_{gid}.docx"; src = f"https://docs.google.com/document/d/{gid}/export?format=docx"
    else:
        pass
        name = re.sub(r"[^A-Za-z0-9._-]", "_", url.split("/uploads/")[-1])
        if len(name) > 120:                      # Windows path-length limit: keep a short, unique name
            name = name[:80] + "_" + hashlib.sha1(url.encode("utf8")).hexdigest()[:12] + Path(name).suffix
        f = DL / name
        src = urllib.parse.quote(url, safe=":/?=&%")       # non-ASCII characters (curly quotes) in file names
    if not f.exists():
        time.sleep(0.7)
        try:
            f.write_bytes(urllib.request.urlopen(urllib.request.Request(src, headers=UA), timeout=90).read())
        except Exception as ex:
            return None, f"download error {ex}"
    return f, "ok"


def cells_docx(f):
    x = zipfile.ZipFile(f).read("word/document.xml").decode("utf8", "ignore")
    out = []
    for t in re.findall(r"<w:tbl>.*?</w:tbl>", x, flags=re.S):
        rows = []
        for r in re.findall(r"<w:tr[ >].*?</w:tr>", t, flags=re.S):
            rows.append([html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<w:tc>.*?</w:tc>", r, flags=re.S)])
        out.append(rows)
    return out


def num(s):
    s = s.replace(",", "").replace("₱", "").replace("PHP", "").strip()
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else (0.0 if s in ("-", "", "0") else None)


def kind(header):
    h = header.upper()
    if "COST OF ASSISTANCE" in h:
        return "cost"
    if "DAMAGED HOUSES" in h or "DAMAGED HOUSE" in h:
        return "damaged"
    if "OUTSIDE" in h and "DISPLACED" in h:
        return "disp_out"
    if "INSIDE" in h or "EVACUATION CENTER" in h:
        return "disp_in"
    if "AFFECTED" in h:
        return "affected"
    return None


def extract(tables, provs):
    """Province rows: first cell = a known province name, with numeric cells after it. Value chosen per table kind."""
    res, seen = {}, set()
    for rows in tables:
        if not rows:
            continue
        head = " ".join(" ".join(r) for r in rows[:4])
        k = kind(head)
        if not k:
            continue
        for r in rows:
            if not r or not r[0]:
                continue
            key = provs.get(norm(r[0]))
            if not key:
                continue
            vals = [num(c) for c in r[1:]]
            vals = [v for v in vals if v is not None]
            if not vals:
                continue
            if k == "affected":
                v = vals[2] if len(vals) >= 3 else vals[-1]          # barangays, families, persons -> persons
            elif k == "disp_in":
                v = vals[4] if len(vals) >= 6 else (vals[-2] if len(vals) >= 2 else vals[-1])   # ECs cum/now, fam cum/now, persons cum/now
            elif k == "disp_out":
                v = vals[2] if len(vals) >= 4 else vals[-1]          # fam cum/now, persons cum/now
            elif k == "damaged":
                v = vals[1] if len(vals) >= 3 else vals[0]           # total, totally, partially -> totally
            else:
                v = vals[-1]                                         # grand total cost
            if (key, k) not in seen:                                 # first province row per table kind (grand-total tables precede breakdowns)
                res[(key, k)] = v; seen.add((key, k))
    return res


def main():
    prov_keys = json.load(open(EV / "province_keys.json"))
    provs = {norm(k): k for k in prov_keys}
    for a, b in {"cotabato": "north cotabato", "northcotabato": "north cotabato", "davaodeoro": "compostela valley", "westernsamar": "samar",
                 "mtprovince": "mountain province", "samarwesternsamar": "samar"}.items():
        if norm(b) in provs:
            provs[a] = provs[norm(b)]
    if "westernsamar" in provs:
        provs["samar"] = provs["westernsamar"]          # DROMIC "Samar" = project key "western samar"
    cut = json.load(open(EV / (sys.argv[2] if len(sys.argv) > 2 else "window_cutoffs.json")))
    PFX = sys.argv[3] if len(sys.argv) > 3 else "DROMIC"
    idx = list(csv.DictReader(open(EV / "DROMIC_index.csv", encoding="utf8")))
    out, log = [], []
    for r in idx:
        if r["family"] not in ("hydromet", "conflict"):
            continue
        ev = date.fromisoformat(r["event_date"])
        files = links_for(r["slug"])
        if not files:
            for w, c in cut.items():
                if date(2015, 7, 1) < ev < date.fromisoformat(c):
                    log.append({"slug": r["slug"], "window": w, "status": "no report link on incident page"})
            continue
        for w, c in cut.items():
            c = date.fromisoformat(c)
            if not (date(2015, 7, 1) < ev < c):
                continue
            cand = [x for x in files if x[1] and x[1] < c]
            if not cand:
                log.append({"slug": r["slug"], "window": w, "status": "no report before cut-off"}); continue
            u, d, src = max(cand, key=lambda x: (x[1], "terminal" in x[0].lower()))
            f, st = fetch(u)
            if f is None:
                log.append({"slug": r["slug"], "window": w, "status": st}); continue
            try:
                if f.suffix.lower() == ".docx":
                    vals = extract(cells_docx(f), provs)
                elif f.suffix.lower() == ".pdf":
                    log.append({"slug": r["slug"], "window": w, "status": "pdf (not parsed by docx path)", "file": f.name}); continue
                else:
                    log.append({"slug": r["slug"], "window": w, "status": "doc (legacy Word, not parsed)", "file": f.name}); continue
            except Exception as ex:
                log.append({"slug": r["slug"], "window": w, "status": f"parse error {ex}", "file": f.name}); continue
            if not vals:
                log.append({"slug": r["slug"], "window": w, "status": "parsed, no province rows", "file": f.name})
            for (key, k), v in vals.items():
                out.append({"slug": r["slug"], "family": r["family"], "event_date": r["event_date"], "window": w, "report": u.rsplit("/", 1)[-1],
                            "report_date": d.isoformat(), "date_source": src, "province": key, "measure": k, "value": v})
            log.append({"slug": r["slug"], "window": w, "status": "ok", "file": f.name, "n_values": len(vals)})
    with open(EV / f"{PFX}_province_values.csv", "w", newline="", encoding="utf8") as fo:
        wr = csv.DictWriter(fo, fieldnames=list(out[0].keys())); wr.writeheader(); wr.writerows(out)
    with open(EV / f"{PFX}_parse_log.csv", "w", newline="", encoding="utf8") as fo:
        wr = csv.DictWriter(fo, fieldnames=["slug", "window", "status", "file", "n_values"]); wr.writeheader()
        for l in log:
            wr.writerow({k: l.get(k, "") for k in wr.fieldnames})
    from collections import Counter
    print(len(out), "values"); print(Counter((l["window"], l["status"].split(" (")[0][:30]) for l in log))


if __name__ == "__main__":
    main()
