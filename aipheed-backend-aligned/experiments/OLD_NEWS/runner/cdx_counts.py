import sys, time, json, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding="utf-8")
out = sys.argv[1]
DOMAINS = ["newsinfo.inquirer.net", "mb.com.ph", "gmanetwork.com/news"]
GEO = r"(batangas|cavite|laguna|rizal|quezon|lucena|calabarzon)"
FOOD = r"(rice|bigas|food|hunger|gutom|price|presyo|palay|farmer|fish|harvest|drought|typhoon)"
res = {}
for dom in DOMAINS:
    for y in range(2015, 2026):
        q = {"url": dom + "/*", "from": f"{y}0101", "to": f"{y}1231", "output": "json", "fl": "original",
             "collapse": "urlkey", "filter": ["statuscode:200", f"original:(?i).*{GEO}.*", f"original:(?i).*{FOOD}.*"],
             "limit": "20000"}
        url = "https://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(q, doseq=True)
        req = urllib.request.Request(url, headers={"User-Agent": "aiPHeed-research/1.0 (metadata count only)"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read().decode("utf-8", "replace")
            rows = json.loads(body) if body.strip().startswith("[") else []
            # captures may predate the article: keep URLs whose path has the year of the window (article date slug) or no year
            n = max(len(rows) - 1, 0)
            res[f"{dom}|{y}"] = n
        except Exception as e:
            res[f"{dom}|{y}"] = f"error: {type(e).__name__} {e}"[:120]
        print(dom, y, res[f"{dom}|{y}"], flush=True)
        json.dump(res, open(out, "w"), indent=1)
        time.sleep(6)
