"""
E150 public data acquisition. No food-insecurity outcome is read here.

    python -m app.e150.acquire cpi      # monthly provincial CPI, food (01.1) and rice only, 2012-based and 2018-based -> data/e150/raw/cpi_monthly.csv
    python -m app.e150.acquire news     # extra outlets, later Rappler years, then full text of gated articles -> data/e150/raw/ (text gitignored)
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote

import pandas as pd

from app.e145.collect import keys, queries_for
from app.e147 import RAW as R147
from app.e150 import RAW

PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/"
UA = "Mozilla/5.0 (aiPHeed thesis research; food security forecasting; DA Region IV-A)"
FIELDS = "id,date,link,title,excerpt"


def _get(url, data=None):
    h = {"User-Agent": UA}
    if data is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=h, data=data)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), b""
    except Exception:
        return 0, {}, b""


def _table(path):
    c, _, b = _get(PX + path)
    return json.loads(b)


def _commodity_codes(v):
    """Strict food-only: 01.1 FOOD, and rice. Never 01 (food and non-alcoholic beverages)."""
    out = {}
    for code, text in zip(v["values"], v["valueTexts"]):
        t = text.strip().lower()
        if re.match(r"^01\.1\s*-\s*food$", t) or re.match(r"^(01\.1\s*)?food$", t):
            out[code] = "food"
        elif re.search(r"\brice\b", t) and "cake" not in t and "flour" not in t and "and" not in t:
            out[code] = "rice"
    return out


def cpi():
    RAW.mkdir(parents=True, exist_ok=True)
    c, _, b = _get(PX + "DB/2M/PI/CPI/2012")
    tabs = json.loads(b)
    log = {"2012_tables": [(t["id"], t["text"][:110]) for t in tabs]}
    frames = []
    candidates = [("2018", "DB/2M/PI/CPI/2018NEW/0012M4ACP22.px")] + [("2012", f"DB/2M/PI/CPI/2012/{t['id']}") for t in tabs if t["id"].endswith(".px") and ("Commodity" in t["text"]) and ("Year-on-Year" not in t["text"]) and ("Weights" not in t["text"]) and ("Purchasing" not in t["text"])][:2]
    for base, path in candidates:
        m = _table(path)
        var = {v["code"]: v for v in m["variables"]}
        com = next((v for k, v in var.items() if "ommodity" in k), None)
        geo = next((v for k, v in var.items() if "eolocation" in k), None)
        codes = _commodity_codes(com) if com else {}
        log[path] = {"title": m.get("title"), "variables": {k: len(v["values"]) for k, v in var.items()}, "chosen": {com["valueTexts"][com["values"].index(k)]: t for k, t in codes.items()} if com else None}
        if not codes or geo is None:
            continue
        # one year at a time: the API caps the cells in a query
        yv = next(v for k, v in var.items() if k.lower().startswith("year"))
        pv = next(v for k, v in var.items() if k.lower().startswith("period") or k.lower().startswith("month"))
        for y, yt in zip(yv["values"], yv["valueTexts"]):
            q = {"query": [{"code": geo["code"], "selection": {"filter": "all", "values": ["*"]}}, {"code": com["code"], "selection": {"filter": "item", "values": list(codes)}},
                           {"code": yv["code"], "selection": {"filter": "item", "values": [y]}}, {"code": pv["code"], "selection": {"filter": "all", "values": ["*"]}}], "response": {"format": "csv"}}
            code, _, body = _get(PX + path, json.dumps(q).encode())
            if code != 200:
                log[f"{path}|{yt}"] = code
                time.sleep(2)
                continue
            import io
            w = pd.read_csv(io.BytesIO(body), encoding="utf-8-sig")
            long = w.melt(id_vars=[geo["code"], com["code"]], var_name="month", value_name="value")
            d = pd.DataFrame({"geo": long[geo["code"]], "commodity": long[com["code"]].map(lambda x: dict(zip(com["valueTexts"], [codes.get(k, "") for k in com["values"]]))[x]), "commodity_text": long[com["code"]], "year": long["month"].str[:4].astype(int), "period": long["month"].str[5:],
                              "value": pd.to_numeric(long["value"], errors="coerce"), "base": base})
            frames.append(d)
            print(base, yt, len(d), flush=True)
            time.sleep(1.5)
    all_ = pd.concat(frames, ignore_index=True)
    all_.to_csv(RAW / "cpi_monthly.csv", index=False, lineterminator="\n")
    (RAW / "cpi_acquire_log.json").write_text(json.dumps(log, indent=1, default=str), newline="\n")
    print(json.dumps(log, indent=0, default=str)[:1800])
    print(all_.groupby(["base", "commodity", "commodity_text"]).agg(n=("value", "count"), geos=("geo", "nunique"), y0=("year", "min"), y1=("year", "max")))


SITES = {"rappler": ("www.rappler.com", "2021-07-02T00:00:00"), "interaksyon": ("www.interaksyon.com", "2012-01-01T00:00:00"), "bworld": ("www.bworldonline.com", "2012-01-01T00:00:00"),
         "newsbytes": ("newsbytes.ph", "2021-07-02T00:00:00"), "verafiles": ("verafiles.org", "2021-07-02T00:00:00"), "pcij": ("pcij.org", "2021-07-02T00:00:00")}
HOST = {k: v[0] for k, v in SITES.items()}


def news():
    RAW.mkdir(parents=True, exist_ok=True)
    done_p = RAW / "news_done.txt"
    done = set(done_p.read_text().splitlines()) if done_p.exists() else set()
    with open(RAW / "articles_more.jsonl", "a", encoding="utf-8", newline="\n") as out, open(done_p, "a", newline="\n") as dn:
        for site, (host, after) in SITES.items():
            for key in keys():
                for q in queries_for(key):
                    tag = f"{site}|{key}|{q}"
                    if tag in done:
                        continue
                    page, status = 1, "ok"
                    while True:
                        code, h, body = _get(f"https://{host}/wp-json/wp/v2/posts?search={quote(q)}&after={after}&before=2026-10-01T00:00:00&per_page=100&page={page}&orderby=date&order=asc&_fields={FIELDS}")
                        if code == 400:
                            break
                        if code != 200:
                            status = f"HTTP{code}"
                            break
                        rows = json.loads(body)
                        for r in rows:
                            out.write(json.dumps({"site": site, "key": key, "query": q, "id": f"{site}:{r['id']}", "date": r["date"], "link": r["link"], "title": r["title"]["rendered"], "excerpt": r["excerpt"]["rendered"]}, ensure_ascii=False) + "\n")
                        time.sleep(1.5)
                        if page >= int(h.get("X-WP-TotalPages", h.get("x-wp-totalpages", 1))) or not rows:
                            break
                        page += 1
                    out.flush()
                    if status == "ok":
                        dn.write(tag + "\n")
                        dn.flush()
                    print(tag, status, page, flush=True)
                    time.sleep(0.1)
    fulltext()


def fulltext():
    """Full text of gated articles only, in batches of 100 ids, so province sentences can be found. Text stays local (gitignored)."""
    a = pd.read_parquet(R147 / "articles_clean.parquet")
    ids = list(a[a["gated"]]["id"].unique())
    more = RAW / "articles_more.jsonl"
    if more.exists():
        from app.e145 import news as N
        m = pd.read_json(more, lines=True)
        m["text"] = (m["title"].map(N.clean) + ". " + m["excerpt"].map(N.clean))
        ids += list(m[m["text"].str.contains(N.GATE_RX)]["id"].unique())
    ids = sorted(set(ids))
    path = RAW / "fulltext.jsonl"
    have = set()
    if path.exists():
        have = {json.loads(x)["id"] for x in open(path, encoding="utf-8", newline="\n")}
    todo = {}
    for i in ids:
        if i not in have:
            s, n = i.split(":", 1)
            todo.setdefault(s, []).append(n)
    host = {**HOST, "rappler": "www.rappler.com", "newsbytes": "newsbytes.ph", "verafiles": "verafiles.org", "pcij": "pcij.org"}
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        for s, lst in todo.items():
            for j in range(0, len(lst), 100):
                code, _, body = _get(f"https://{host[s]}/wp-json/wp/v2/posts?include={','.join(lst[j:j + 100])}&per_page=100&_fields=id,content")
                if code == 200:
                    for r in json.loads(body):
                        f.write(json.dumps({"id": f"{s}:{r['id']}", "content": r.get("content", {}).get("rendered", "")}, ensure_ascii=False) + "\n")
                    f.flush()
                print(s, j, code, flush=True)
                time.sleep(1.5)


if __name__ == "__main__":
    {"cpi": cpi, "news": news, "fulltext": fulltext}[sys.argv[1]]()
