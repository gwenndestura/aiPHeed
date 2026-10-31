"""Metadata scan of candidate OpenSTAT tables: provinces present, periodicity, year span, last update (no values)."""
import json, re, time
import px_list as P
KEY = re.compile(r"retail|wholesale|farmgate|price|production|palay|corn|fisher|aquacult|livestock|poultry|hog|swine|chicken|cattle|vegetable|fruit|crop|area harvested|yield|food|unemploy|employ|underemploy|wage|income|expenditure|poverty|subsistence|hunger|stock|inventory|damage|nutrition|water|sanitation|stunt|malnutri|undernourish|insecurity|domestic trade|egg|fish", re.I)
PROVS = ["CAVITE", "LAGUNA", "BATANGAS", "RIZAL", "QUEZON"]
tables = json.load(open("../out/openstat_tables.json"))
cand = [t for t in tables if KEY.search(t["text"] or "") and not (t["path"].startswith("DB/2L") and "omestic" not in t["text"])]
out = []
for t in cand:
    try:
        m = P.get(t["path"])
    except Exception as e:
        out.append({**t, "error": str(e)}); continue
    if not isinstance(m, dict) or "variables" not in m or any("valueTexts" not in v for v in m["variables"]):
        out.append({**t, "error": "no table metadata"}); continue
    geo, per, yrs, other = None, [], [], {}
    for v in m["variables"]:
        txt = [x.strip(". ").upper() for x in v["valueTexts"]]
        code = v["code"].lower()
        if "geoloc" in code or "region" in code or "province" in code or any(p in " ".join(txt) for p in ("CALABARZON", "PHILIPPINES")):
            geo = txt if geo is None else geo
        elif "year" in code:
            yrs = [int(x) for x in re.findall(r"\b(19\d\d|20\d\d)\b", " ".join(v["valueTexts"]))]
        elif any(k in code for k in ("period", "month", "quarter", "semester")):
            per = v["valueTexts"]
        else:
            other[v["code"]] = len(v["valueTexts"])
        if not yrs:
            yy = [int(x) for x in re.findall(r"\b(19\d\d|20\d\d)\b", " ".join(v["valueTexts"]))] if "year" in code or "period" in code else []
            yrs = yy or yrs
    pj = " ".join(per).lower()
    freq = "monthly" if ("jan" in pj or "january" in pj) else "quarterly" if "quarter" in pj or "q1" in pj else "semestral" if "semester" in pj else "annual/other" if per or yrs else "unknown"
    prov = [p for p in PROVS if geo and any(g == p or g.startswith(p + " ") or g == p + " PROVINCE" for g in geo)]
    out.append({**t, "title": m.get("title"), "n_geo": len(geo) if geo else 0, "has_calabarzon": bool(geo and any("CALABARZON" in g or "IV-A" in g for g in geo)),
                "provinces_present": prov, "n_provinces_present": len(prov), "frequency": freq, "year_min": min(yrs) if yrs else None,
                "year_max": max(yrs) if yrs else None, "other_dims": other})
    time.sleep(0.25)
json.dump(out, open("../out/openstat_candidates.json", "w"), indent=1)
print(len(cand), sum(1 for o in out if o.get("n_provinces_present") == 5))
