"""
app/cb6_auto/fetchers.py
------------------------
One fetcher per input source. Each one rewrites its file in the persistent sources folder only after the response parses and
passes its checks; on any failure the file stays as it was and the failure is reported, so a bad reply can never replace
good data. A missing official value stays missing.

Sources: PSA OpenSTAT PXWeb (CPI, palay and corn, fisheries, rice stocks), NOAA CPC (ONI), World Bank (Pink Sheet), NOAA
NCEI IBTrACS (typhoon tracks), SWS (hunger releases, WordPress posts API).
"""
from __future__ import annotations

import hashlib
import html
import io
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from app.cb6_auto.config import SEED
from app.cb6_auto.features import PROVS, REGION, load_centroids, qs

PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/"
UA = "Mozilla/5.0 (aiPHeed thesis research)"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LONG_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]
HTTP = Callable[..., bytes]


class SourceRefused(Exception):
    """The source answered, but its content failed a check. The stored file is left unchanged."""


def http_get(url: str, data: bytes | None = None, timeout: int = 180) -> bytes:
    headers = {"User-Agent": UA}
    if data is not None:
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=timeout) as r:
        return r.read()


def _write(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False, lineterminator="\n")
    os.replace(tmp, path)


def _keep_history(old: pd.DataFrame, new: pd.DataFrame, keys: list[str], name: str) -> pd.DataFrame:
    """New values win on a shared period; a period only the old file holds is kept. A blank cell in the reply never erases
    a stored value. A reply covering under 75% of the stored values in its own time span is refused as broken."""
    filled = new.dropna(subset=["value"])
    period = keys[-1]
    span = old[(old[period] >= new[period].min()) & (old[period] <= new[period].max())].dropna(subset=["value"])
    if len(span) and len(span.merge(filled[keys], on=keys, how="inner")) < 0.75 * len(span):
        raise SourceRefused(f"{name}: the reply covers too little of the stored history")
    merged = pd.concat([old, filled], ignore_index=True).drop_duplicates(keys, keep="last")
    return merged.sort_values(keys).reset_index(drop=True)


# ================================================================================================ PSA OpenSTAT
def _px_table(get: HTTP, path: str, item_var: str, items: tuple[str, ...], kind: str) -> str:
    """The Region IV-A cells of one PXWeb table as CSV text (query logic of HISTORY_RETRAIN/runner/acquire.py)."""
    meta = json.loads(get(PX + path).decode("utf-8-sig"))
    query = []
    for v in meta["variables"]:
        pairs = list(zip(v["values"], v["valueTexts"]))
        if v["code"] in ("Geolocation", "Region Province"):
            sel = [c for c, t in pairs if "IV-A" in t.upper()]
        elif v["code"] == item_var:
            sel = [c for c, t in pairs if t.strip(". ").strip() in items]
        elif v["code"] == "Year":
            sel = [c for c, _ in pairs]
        else:
            keep = MONTHS + LONG_MONTHS if kind == "month" else ["Quarter 1", "Quarter 2", "Quarter 3", "Quarter 4"]
            sel = [c for c, t in pairs if t.strip() in keep]
        if not sel:
            raise SourceRefused(f"{path}: nothing selected for {v['code']}")
        query.append({"code": v["code"], "selection": {"filter": "item", "values": sel}})
    body = json.dumps({"query": query, "response": {"format": "csv"}}).encode()
    return get(PX + path, body).decode("utf-8-sig")


def tidy_px(text: str, kind: str) -> pd.DataFrame:
    d = pd.read_csv(io.StringIO(text), dtype=str)
    id_cols = [c for c in d.columns if not re.match(r"^\d{4} ", c)]
    if not any(c in ("Geolocation", "Region Province") for c in id_cols) or len(id_cols) != 2:
        raise SourceRefused(f"unexpected PXWeb columns {id_cols[:5]}")
    long = d.melt(id_vars=id_cols, var_name="period", value_name="raw")
    geo_col = next(c for c in id_cols if c in ("Geolocation", "Region Province"))
    item_col = next(c for c in id_cols if c != geo_col)
    long["geo_code"] = REGION
    long["item"] = long[item_col].str.strip(". ").str.strip()
    long["year"] = long["period"].str[:4].astype(int)
    per = long["period"].str[5:].str.strip()
    if kind == "month":
        long["month"] = per.map(lambda s: (MONTHS.index(s[:3]) + 1) if s[:3] in MONTHS else None)
        long["ym"] = long["year"] * 12 + long["month"] - 1
    else:
        long["quarter"] = per.str[-1].astype(int)
        long["q"] = long["year"] * 4 + long["quarter"] - 1
    long["value"] = pd.to_numeric(long["raw"].str.strip(), errors="coerce")     # "..", "", "-" -> NaN, never filled
    keep = ["geo_code", "item", "year"] + (["month", "ym"] if kind == "month" else ["quarter", "q"]) + ["value"]
    return long[keep].sort_values(keep[:-1]).reset_index(drop=True)


def fetch_cpi(src: Path, get: HTTP = http_get) -> dict:
    path = "2M/PI/CPI/2018NEW/0012M4ACP22.px"
    t = tidy_px(_px_table(get, path, "Commodity Description", ("0 - ALL ITEMS", "01.1 - FOOD", "01.1.1.12 - Rice"), "month"),
                "month")
    main = t[t["item"].isin(["0 - ALL ITEMS", "01.1 - FOOD"])]
    rice = t[t["item"] == "01.1.1.12 - Rice"][["year", "month", "ym", "value"]]
    if main.dropna(subset=["value"]).empty or rice.dropna(subset=["value"]).empty:
        raise SourceRefused("CPI table: no food, headline or rice values for Region IV-A")
    old = pd.read_csv(src / "cpi_ACP22.csv", dtype={"geo_code": str})
    _write(_keep_history(old, main, ["item", "ym"], "cpi_ACP22"), src / "cpi_ACP22.csv")
    old_r = pd.read_csv(src / "cpi_rice_region.csv")
    _write(_keep_history(old_r, rice, ["ym"], "cpi_rice"), src / "cpi_rice_region.csv")
    nn = main.dropna(subset=["value"])
    return {"newest": f"{int(nn['year'].iloc[-1])}", "newest_ym": int(nn["ym"].max()), "url": PX + path}


def _fetch_prod(src: Path, get: HTTP, path: str, var: str, items: tuple[str, ...], fname: str) -> dict:
    t = tidy_px(_px_table(get, path, var, items, "quarter"), "quarter")
    if t.dropna(subset=["value"]).empty:
        raise SourceRefused(f"{fname}: no Region IV-A values")
    old = pd.read_csv(src / fname, dtype={"geo_code": str})
    _write(_keep_history(old, t, ["item", "q"], fname), src / fname)
    return {"newest_quarter": qs(int(t.dropna(subset=["value"])["q"].max())), "url": PX + path}


def fetch_palay_corn(src: Path, get: HTTP = http_get) -> dict:
    return _fetch_prod(src, get, "2E/CS/0012E4EVCP0.px", "Ecosystem/Croptype", ("Palay", "Corn"), "palay_corn_EVCP0.csv")


def fetch_fisheries(src: Path, get: HTTP = http_get) -> dict:
    return _fetch_prod(src, get, "2E/FS/0132E4GVFP1.px", "Subsector", ("FISHERIES",), "fisheries_GVFP1.csv")


def tidy_stocks(text: str) -> pd.DataFrame:
    s = pd.read_csv(io.StringIO(text), dtype=str)
    if not {"Sector", "Year"} <= set(s.columns):
        raise SourceRefused(f"rice stocks: unexpected columns {list(s.columns)[:6]}")
    st = s.melt(id_vars=["Sector", "Year"], var_name="month", value_name="value")
    st["ym"] = st["Year"].astype(int) * 12 + st["month"].map(lambda m: MONTHS.index(str(m).strip()[:3]))
    st["value"] = pd.to_numeric(st["value"], errors="coerce")
    st["sector"] = st["Sector"].str.replace("Rice: ", "", regex=False).str.replace(" Stock", "", regex=False).str.lower()
    return st.pivot_table(index="ym", columns="sector", values="value").sort_index()


def fetch_stocks(src: Path, get: HTTP = http_get) -> dict:
    path = "2E/CS/0032E4ECNV0.px"
    q = {"query": [{"code": "Sector", "selection": {"filter": "item", "values": ["0", "1", "2", "3"]}}],
         "response": {"format": "csv"}}
    new = tidy_stocks(get(PX + path, json.dumps(q).encode()).decode("utf-8-sig"))
    need = {"total", "nfa", "household", "commercial"}
    if not need <= set(new.columns):
        raise SourceRefused(f"rice stocks: sectors {sorted(new.columns)}")
    old = pd.read_csv(src / "tidy_stocks_national.csv").set_index("ym")
    out = new.combine_first(old).sort_index()[list(old.columns)]
    tmp = src / "tidy_stocks_national.csv.tmp"
    out.to_csv(tmp, lineterminator="\n")
    os.replace(tmp, src / "tidy_stocks_national.csv")
    return {"newest_ym": int(new["total"].dropna().index.max()), "url": PX + path}


# ================================================================================================ NOAA ONI
SEASONS = {"DJF": 2, "JFM": 3, "FMA": 4, "MAM": 5, "AMJ": 6, "MJJ": 7, "JJA": 8, "JAS": 9, "ASO": 10, "SON": 11, "OND": 12,
           "NDJ": 1}


def parse_oni(text: str) -> pd.DataFrame:
    rows = []
    for line in text.splitlines():
        p = line.split()
        if len(p) == 4 and p[0] in SEASONS and p[1].isdigit():
            yr, end = int(p[1]), SEASONS[p[0]]
            rows.append({"end_year": yr + 1 if p[0] == "NDJ" else yr, "end_month": end, "SEAS": p[0], "YR": yr,
                         "oni": float(p[3])})
    if len(rows) < 800:
        raise SourceRefused(f"ONI: only {len(rows)} seasons parsed")
    return pd.DataFrame(rows)


def fetch_oni(src: Path, get: HTTP = http_get) -> dict:
    url = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
    new = parse_oni(get(url).decode("utf-8", "replace"))
    old = pd.read_csv(src / "cov_oni.csv")
    out = pd.concat([old, new], ignore_index=True).drop_duplicates(["end_year", "end_month"], keep="last")
    _write(out.sort_values(["end_year", "end_month"]), src / "cov_oni.csv")
    last = new.iloc[-1]
    return {"newest": f"{int(last['end_year'])}-{int(last['end_month']):02d}", "url": url}


# ================================================================================================ World Bank Pink Sheet
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
PINK_KEEP = {"Rice, Thai 5% ": "rice_thai5", "Rice, Thai 5%": "rice_thai5", "Rice, Viet Namese 5%": "rice_viet5",
             "Wheat, US HRW": "wheat_hrw", "Maize": "maize", "Palm oil": "palm_oil", "Sugar, world": "sugar_world",
             "Urea ": "urea", "Urea": "urea", "Crude oil, average": "crude_avg", "Soybean oil": "soybean_oil"}


def _col(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def _read_sheet(raw: bytes, name: str) -> list[list]:
    z = zipfile.ZipFile(io.BytesIO(raw))
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", _NS):
            ss.append("".join(t.text or "" for t in si.iter("{%s}t" % _NS["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid = next(s.get("{%s}id" % _NS["r"]) for s in wb.find("m:sheets", _NS) if s.get("name") == name)
    target = next(r.get("Target") for r in rels if r.get("Id") == rid)
    sh = ET.fromstring(z.read("xl/" + target.lstrip("/").replace("xl/", "")))
    rows = []
    for row in sh.iter("{%s}row" % _NS["m"]):
        cells = {}
        for c in row.findall("m:c", _NS):
            v = c.find("m:v", _NS)
            if v is None:
                isv = c.find("m:is", _NS)
                val = "".join(t.text or "" for t in isv.iter("{%s}t" % _NS["m"])) if isv is not None else None
            else:
                val = ss[int(v.text)] if c.get("t") == "s" else v.text
            cells[_col(c.get("r"))] = val
        rows.append([cells.get(i) for i in range(max(cells) + 1)] if cells else [])
    return rows


def parse_pink(raw: bytes) -> pd.DataFrame:
    rows = _read_sheet(raw, "Monthly Prices")
    hdr_i = next(i for i, r in enumerate(rows) if r and any(isinstance(x, str) and x.startswith("Crude oil") for x in r))
    cols = {i: PINK_KEEP[h] for i, h in enumerate(rows[hdr_i]) if isinstance(h, str) and h in PINK_KEEP}
    out = []
    for r in rows[hdr_i + 1:]:
        if not r or not isinstance(r[0], str) or not re.match(r"^\d{4}M\d{2}$", r[0]):
            continue
        y, m = int(r[0][:4]), int(r[0][5:])
        rec = {"month": f"{y}-{m:02d}", "ym": y * 12 + m - 1}
        for i, k in cols.items():
            try:
                rec[k] = float(r[i]) if i < len(r) else None
            except (TypeError, ValueError):
                rec[k] = None
        out.append(rec)
    return pd.DataFrame(out)


def fetch_pinksheet(src: Path, get: HTTP = http_get) -> dict:
    """The workbook's URL changes with each release, so it is read from the World Bank's commodity page."""
    page = get("https://www.worldbank.org/en/research/commodity-markets").decode("utf-8", "replace")
    m = re.search(r'https://[^"\']*CMO-Historical-Data-Monthly\.xlsx', page)
    if not m:
        raise SourceRefused("Pink Sheet: no workbook link on the World Bank commodity page")
    new = parse_pink(get(m.group(0)))
    old = pd.read_csv(src / "pinksheet_monthly_1960.csv")
    need = set(old.columns) - {"month", "ym"}
    if not need <= set(new.columns) or len(new) < 0.9 * len(old):
        raise SourceRefused(f"Pink Sheet: columns or rows missing ({len(new)} rows)")
    out = pd.concat([old, new[list(old.columns)]], ignore_index=True).drop_duplicates("ym", keep="last").sort_values("ym")
    _write(out, src / "pinksheet_monthly_1960.csv")
    return {"newest": str(new["month"].iloc[-1]), "url": m.group(0)}


# ================================================================================================ IBTrACS
IBTRACS = ("https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/"
           "access/csv/ibtracs.last3years.list.v04r01.csv")
RADIUS_KM = 300.0


def _haversine(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def typhoon_counts(csv_bytes: bytes, centroids: dict, now_utc: pd.Timestamp) -> pd.DataFrame:
    """Distinct storms with a fix within 300 km of each province centroid, per COMPLETED quarter of the file. A completed
    quarter with no storm is an observed 0; a quarter still running gets no row."""
    d = pd.read_csv(io.BytesIO(csv_bytes), skiprows=[1], usecols=["SID", "ISO_TIME", "LAT", "LON"], low_memory=False)
    d["ISO_TIME"] = pd.to_datetime(d["ISO_TIME"], errors="coerce")
    d = d.dropna(subset=["ISO_TIME"])
    if d.empty:
        raise SourceRefused("IBTrACS: no dated fixes")
    d["LAT"], d["LON"] = pd.to_numeric(d["LAT"], errors="coerce"), pd.to_numeric(d["LON"], errors="coerce")
    d["q"] = d["ISO_TIME"].dt.year * 4 + (d["ISO_TIME"].dt.month - 1) // 3
    q_first = int(d["q"].min()) + 1                                   # the file's first quarter may be partial
    q_done = now_utc.year * 4 + (now_utc.month - 1) // 3 - 1          # the last quarter that has ended
    rows = []
    for code, (lat, lon) in centroids.items():
        cnt = d[_haversine(lat, lon, d["LAT"].to_numpy(), d["LON"].to_numpy()) <= RADIUS_KM].groupby("q")["SID"].nunique()
        rows += [{"province_code": code, "q": q, "quarter": qs(q), "tc_count": int(cnt.get(q, 0))}
                 for q in range(q_first, q_done + 1)]
    return pd.DataFrame(rows)


def fetch_typhoons(src: Path, get: HTTP = http_get, now_utc: pd.Timestamp | None = None) -> dict:
    now_utc = now_utc if now_utc is not None else pd.Timestamp.now(tz="UTC")
    new = typhoon_counts(get(IBTRACS, timeout=600), load_centroids(SEED / "province_centroids.json"), now_utc)
    if set(new["province_code"]) != set(PROVS):
        raise SourceRefused("IBTrACS: provinces missing")
    old = pd.read_csv(src / "typhoons_province_quarter.csv", dtype={"province_code": str})
    # stored counts are never revised here: only quarters the file did not have are added
    add = new.merge(old[["province_code", "q"]], on=["province_code", "q"], how="left", indicator=True)
    add = add[add["_merge"] == "left_only"].drop(columns="_merge")
    out = pd.concat([old, add], ignore_index=True).sort_values(["province_code", "q"])
    _write(out, src / "typhoons_province_quarter.csv")
    return {"added_quarters": sorted(add["quarter"].unique().tolist()), "newest_quarter": qs(int(out["q"].max())),
            "url": IBTRACS}


# ================================================================================================ SWS
SWS_POSTS = "https://sws.org.ph/wp-json/wp/v2/posts?search=hunger&per_page=30&orderby=date"
AREA_WORDS = {"metro_manila": "Metro Manila", "balance_luzon": "Balance Luzon", "visayas": "Visayas", "mindanao": "Mindanao"}


class SwsParseError(ValueError):
    pass


def _plain(html_text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html_text))).strip()


def is_hunger_release(title: str) -> bool:
    """A regular hunger release; commissioned (Stratbase) rounds are not in the target definition."""
    t = html.unescape(title)
    return ("SOCIAL WEATHER REPORT" in t.upper() and re.search(r"\bhunger\b", t, re.I) is not None
            and "stratbase" not in t.lower())


def parse_sws_release(title: str, content_html: str, date_iso: str, link: str) -> dict:
    """One row of sws_area_rounds_full.csv, or SwsParseError. Each area's total must appear exactly once and agree with its
    Moderate + Severe breakdown wherever the release gives one, so a changed layout stops here and is never guessed at."""
    x = _plain(content_html)
    fw = re.search(r"Social Weather Survey (?:of|conducted from) ([A-Z][a-z]+) (\d{1,2})\s*[-\u2013]\s*(?:([A-Z][a-z]+) )?(\d{1,2}),? "
                   r"(\d{4})", x)
    if not fw:
        raise SwsParseError("fieldwork dates not found")
    m1, d1, m2, d2, y2 = fw.group(1), int(fw.group(2)), fw.group(3) or fw.group(1), int(fw.group(4)), int(fw.group(5))
    if m1 not in LONG_MONTHS or m2 not in LONG_MONTHS:
        raise SwsParseError("fieldwork month not recognised")
    mi, mj = LONG_MONTHS.index(m1) + 1, LONG_MONTHS.index(m2) + 1
    y1 = y2 - 1 if mi > mj else y2
    nat = re.search(r"found that (\d{1,2}\.\d)% of Filipino families", x)
    if not nat:
        raise SwsParseError("national figure not found")
    end = re.search(r"\[\s*Chart 3", x)
    if not end:
        raise SwsParseError("area sentence (Chart 3) not found")
    sent = x[max(0, end.start() - 400):end.start()].replace(" (or Luzon outside Metro Manila)", "")
    other = r"(?: and (?:the )?(?:Metro Manila|Balance Luzon|Visayas|Mindanao))?"
    vals = {}
    for key, word in AREA_WORDS.items():
        hits = re.findall(rf"{word}{other},? (?:both )?at (\d{{1,2}}\.\d)%", sent)
        if len(hits) != 1:
            raise SwsParseError(f"{word}: {len(hits)} totals in the area sentence")
        vals[key] = float(hits[0])
    for key, word in AREA_WORDS.items():
        b = re.search(rf"[Ii]n (?:the )?{word}, Moderate Hunger (.*?)Severe Hunger (.*?)\[", x)
        if b:
            pm, ps = re.findall(r"(\d{1,2}\.\d)%", b.group(1)), re.findall(r"(\d{1,2}\.\d)%", b.group(2))
            if pm and ps and abs(float(pm[-1]) + float(ps[-1]) - vals[key]) > 0.25:
                raise SwsParseError(f"{word}: {pm[-1]} + {ps[-1]} does not make {vals[key]}")
    n = re.search(r"([\d,]+) in Balance Luzon", x) or re.search(r"([\d,]+) each in [^.:]*?Balance Luzon", x)
    bl_n = float(n.group(1).replace(",", "")) if n else float("nan")
    mode = "face-to-face" if re.search(r"face-to-face", x, re.I) else ""
    base = "adults" if re.search(r"\badults\b", x) else ""
    return {"quarter": f"{y1}-Q{(mi - 1) // 3 + 1}", "fieldwork": f"{y1}-{mi:02d}-{d1:02d}/{y2}-{mj:02d}-{d2:02d}",
            "published": date_iso[:10], "respondent_base": base, "commissioned": False, "national": float(nat.group(1)),
            **vals, "bl_n": bl_n, "area_moe_bl": float("nan"), "area_moe_other": float("nan"),
            "source_type": "SWS release (automatic parse)", "source": link, "mode": mode, "moe_assumed": False, "era": "2021+"}


def fetch_sws(src: Path, get: HTTP = http_get) -> dict:
    """New rounds only (posted after the newest stored round); stored rounds are never edited. A release that cannot be
    parsed is reported in `needs_human`, and the forecast keeps using the newest round it has."""
    posts = json.loads(get(SWS_POSTS).decode("utf-8"))
    path = src / "sws_area_rounds_full.csv"
    old = pd.read_csv(path)
    newest = str(old["published"].astype(str).str[:10].max())
    have_fw = set(old["fieldwork"].astype(str))
    add, needs = [], []
    for p in posts:
        title = p["title"]["rendered"]
        link = p.get("link", "")
        if not is_hunger_release(title) or p["date"][:10] <= newest:
            continue
        try:
            r = parse_sws_release(title, p["content"]["rendered"], p["date"], link)
        except SwsParseError as e:
            needs.append({"title": _plain(title), "link": link, "published": p["date"][:10], "reason": str(e)})
            continue
        if r["fieldwork"] not in have_fw:
            add.append(r)
    if add:
        out = pd.concat([old, pd.DataFrame(add)[list(old.columns)]], ignore_index=True)
        _write(out, path)
    return {"added": [{"quarter": r["quarter"], "published": r["published"], "balance_luzon": r["balance_luzon"],
                       "source": r["source"]} for r in add], "needs_human": needs, "url": SWS_POSTS}


# ================================================================================================ all sources
FETCHERS = {"psa_cpi": fetch_cpi, "psa_palay_corn": fetch_palay_corn, "psa_fisheries": fetch_fisheries,
            "psa_rice_stocks": fetch_stocks, "noaa_oni": fetch_oni, "worldbank_pinksheet": fetch_pinksheet,
            "ibtracs_typhoons": fetch_typhoons, "sws_hunger": fetch_sws}


def collect_all(src: Path, fetchers: dict | None = None) -> dict:
    """Run every fetcher; one failure never stops the others or touches stored data."""
    report = {}
    for name, fn in (fetchers or FETCHERS).items():
        at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            report[name] = {"ok": True, "at": at, **fn(src)}
        except Exception as e:  # noqa: BLE001  (any source failure is recorded; the stored file is untouched)
            report[name] = {"ok": False, "at": at, "error": f"{type(e).__name__}: {e}"[:300]}
    return report


def file_hashes(src: Path) -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(src.glob("*.csv"))}
