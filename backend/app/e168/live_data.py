"""
Live public inputs for the served E168 issue: the newest government figures and news, refreshed automatically.

    python -m app.e168.live_data fetch      -> data/e168/live_raw/ (+ first_seen.json, fetch_log.jsonl)

What is fetched (public sources only, no login):
    PSA OpenSTAT   quarterly palay + corn and fisheries production by province; monthly CPI (food, rice) by province;
                   monthly Labour Force Survey unemployment rate (national)
    NASA POWER     monthly rainfall (PRECTOTCORR) and root-zone soil wetness (GWETROOT) at every province centroid
    NOAA CPC       Oceanic Nino Index (ONI)
    NOAA NCEI      IBTrACS tropical-cyclone tracks, last three years
    World Bank     personal remittances received (BSP figures, yearly)

Nothing here replaces the files the model was trained and validated on. The loaders in app.e147, app.e146, app.e137,
app.e150 and app.fi5 add a live figure only for a period those files do not already hold, so every training and
validation row is unchanged. A live figure counts for an issue date when it is usable under the training release rule
OR when it was already in the public download on or before that date (first_seen.json records the first day each
period was seen online). A period first seen after the issue date is never used for it.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from functools import lru_cache

import pandas as pd

from app.paths import BACKEND_DIR

LIVE = BACKEND_DIR / "data" / "e168" / "live_raw"
SEEN = LIVE / "first_seen.json"
LOG = LIVE / "fetch_log.jsonl"
PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/"
UA = "Mozilla/5.0 (aiPHeed thesis research; food security forecasting; DA Region IV-A)"
PROD = {"palay_corn_q": ("DB/2E/CS/0012E4EVCP0.px", "Ecosystem/Croptype", ("Palay", "Corn")),
        "fisheries_q": ("DB/2E/FS/0132E4GVFP1.px", "Subsector", ("FISHERIES",))}
LFS_PATH = "DB/1B/LFS/0021B3FKEI2.px"
CPI_PATH = "DB/2M/PI/CPI/2018NEW/0012M4ACP22.px"
NASA = ("https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=PRECTOTCORR,GWETROOT&community=AG"
        "&latitude={lat}&longitude={lon}&start={y0}&end={y1}&format=JSON")
ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
IBTRACS_URL = ("https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/"
               "v04r01/access/csv/ibtracs.last3years.list.v04r01.csv")
WDI_URL = "https://api.worldbank.org/v2/country/PHL/indicator/BX.TRF.PWKR.CD.DT?format=json&per_page=100"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


# ------------------------------------------------------------------------------------------------------------ http
def _get(url: str, data: bytes | None = None, timeout: int = 180) -> bytes:
    h = {"User-Agent": UA}
    if data is not None:
        h["Content-Type"] = "application/json"
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h, data=data), timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:   # retry transient failures
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def _px(path: str, pick: dict) -> bytes:
    meta = json.loads(_get(PX + path))
    q = []
    for v in meta["variables"]:
        if v["code"] in pick:
            vals = [c for c, t in zip(v["values"], v["valueTexts"]) if pick[v["code"]](t.strip())]
        else:
            vals = v["values"]
        q.append({"code": v["code"], "selection": {"filter": "item", "values": vals}})
    return _get(PX + path, json.dumps({"query": q, "response": {"format": "csv"}}).encode())


def _write(name: str, body: bytes) -> None:
    """Atomic write; an empty or failed download never replaces the previous file."""
    if not body or len(body) < 50:
        raise RuntimeError(f"{name}: empty download")
    f = LIVE / name
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(f.suffix + ".tmp")
    tmp.write_bytes(body)
    tmp.replace(f)


# ------------------------------------------------------------------------------------------------------- first seen
def _seen() -> dict:
    return json.loads(SEEN.read_text()) if SEEN.exists() else {}


def _mark(source: str, periods, day: str) -> list[str]:
    s = _seen()
    cur = s.setdefault(source, {})
    new = [p for p in sorted(set(periods)) if p not in cur]
    for p in new:
        cur[p] = day
    SEEN.write_text(json.dumps(s, indent=1, sort_keys=True), newline="\n")
    return new


def first_seen(source: str, period: str) -> pd.Timestamp | None:
    d = _seen_cached().get(source, {}).get(period)
    return pd.Timestamp(d) if d else None


@lru_cache(maxsize=None)
def _seen_cached() -> dict:
    return _seen()


def _live_dates() -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """(period cut-off, published-by) of the live issue: from the running refresh (AIPHEED_LIVE_ASOF, AIPHEED_LIVE_PUBLISHED)
    or, when serving, from the issue the refresh last promoted (state.json)."""
    a, p = os.getenv("AIPHEED_LIVE_ASOF"), os.getenv("AIPHEED_LIVE_PUBLISHED")
    if not a:
        st = _state_cached()
        a, p = st.get("served_cutoff"), st.get("served_published_by")
    if not a:
        return None, None
    a = pd.Timestamp(a).normalize()
    return a, (pd.Timestamp(p).normalize() if p else a)


@lru_cache(maxsize=None)
def _state_cached() -> dict:
    f = LIVE / "state.json"
    return json.loads(f.read_text()) if f.exists() else {}


def usable(source: str, period: str, period_end: pd.Timestamp, as_of: pd.Timestamp) -> bool:
    """A live figure for `period` counts at `as_of` when the period ended before `as_of` and the figure was online by the
    publication date that goes with `as_of` (the refresh day for the live issue; `as_of` itself for any other date)."""
    s = first_seen(source, period)
    if s is None or not pd.Timestamp(period_end) < pd.Timestamp(as_of):
        return False
    a, p = _live_dates()
    by = p if a is not None and pd.Timestamp(as_of).normalize() == a else pd.Timestamp(as_of)
    return s <= by


def effective_seen(source: str, period: str, period_end: pd.Timestamp) -> pd.Timestamp | None:
    """First-seen date as a release date: a figure first seen after the live cut-off but online by the refresh day, for a
    period that ended before the cut-off, is treated as available at the cut-off."""
    s = first_seen(source, period)
    if s is None:
        return None
    a, p = _live_dates()
    if a is not None and s > a and s <= p and pd.Timestamp(period_end) < a:
        return a
    return s


# ---------------------------------------------------------------------------------------------------------- fetchers
def fetch_production(today: str) -> dict:
    y1 = date.fromisoformat(today).year
    out = {}
    for name, (path, col, labs) in PROD.items():
        per = "Period" if name == "palay_corn_q" else "Quarter"
        body = _px(path, {col: lambda t, labs=labs: t in labs, "Year": lambda t: t.isdigit() and 2023 <= int(t) <= y1,
                          per: lambda t: t.startswith("Quarter")})
        _write(f"psa/{name}.csv", body)
        d = pd.read_csv(io.BytesIO(body), encoding="latin-1")
        qc = [c for c in d.columns if re.match(r"^\d{4} Quarter \d$", c)]
        has = [c for c in qc if pd.to_numeric(d[c], errors="coerce").notna().any()]
        out[name] = {"newest": has[-1] if has else None, "new_periods": _mark(name, has, today)}
    return out


def fetch_cpi(today: str) -> dict:
    meta = json.loads(_get(PX + CPI_PATH))
    var = {v["code"]: v for v in meta["variables"]}
    com = next(v for k, v in var.items() if "ommodity" in k)
    geo = next(v for k, v in var.items() if "eolocation" in k)
    yv = next(v for k, v in var.items() if k.lower().startswith("year"))
    pv = next(v for k, v in var.items() if k.lower().startswith("period") or k.lower().startswith("month"))
    from app.e150.acquire import _commodity_codes
    codes = _commodity_codes(com)
    frames = []
    for y, yt in zip(yv["values"], yv["valueTexts"]):
        if not yt.isdigit() or int(yt) < 2024:
            continue
        q = {"query": [{"code": geo["code"], "selection": {"filter": "all", "values": ["*"]}},
                       {"code": com["code"], "selection": {"filter": "item", "values": list(codes)}},
                       {"code": yv["code"], "selection": {"filter": "item", "values": [y]}},
                       {"code": pv["code"], "selection": {"filter": "all", "values": ["*"]}}], "response": {"format": "csv"}}
        w = pd.read_csv(io.BytesIO(_get(PX + CPI_PATH, json.dumps(q).encode())), encoding="utf-8-sig")
        long = w.melt(id_vars=[geo["code"], com["code"]], var_name="month", value_name="value")
        txt = dict(zip(com["valueTexts"], [codes.get(k, "") for k in com["values"]]))
        frames.append(pd.DataFrame({"geo": long[geo["code"]], "commodity": long[com["code"]].map(txt), "commodity_text": long[com["code"]],
                                    "year": long["month"].str[:4].astype(int), "period": long["month"].str[5:],
                                    "value": pd.to_numeric(long["value"], errors="coerce"), "base": 2018}))
        time.sleep(1.5)
    d = pd.concat(frames, ignore_index=True)
    _write("psa/cpi_monthly.csv", d.to_csv(index=False, lineterminator="\n").encode())
    have = d.dropna(subset=["value"])
    have = have[have["period"].isin([m[:3] for m in MONTHS])]
    per = sorted({f"{y}-{[m[:3] for m in MONTHS].index(p) + 1:02d}" for y, p in zip(have["year"], have["period"])})
    return {"newest": per[-1] if per else None, "new_periods": _mark("cpi", per, today)}


def fetch_lfs(today: str) -> dict:
    body = _px(LFS_PATH, {"Rates": lambda t: t == "Unemployment Rate"})
    d = pd.read_csv(io.BytesIO(body), encoding="latin-1", dtype=str)
    # PX gives one row per Year x Month x Rate with a column per sex; keep the fi5 file's layout
    want = ["Year", "Month"] + [f"Unemployment Rate {s}" for s in ("Both sexes", "Male", "Female")]
    if not all(c in d.columns for c in want):              # the archived file's layout is what the loader reads
        raise RuntimeError(f"LFS layout changed: {list(d.columns)[:8]}")
    out = d[want]
    _write("psa/lfs_unemployment_rate_national.csv", out.to_csv(index=False, lineterminator="\n").encode())
    v = out[out["Month"].isin(MONTHS) & pd.to_numeric(out["Unemployment Rate Both sexes"], errors="coerce").notna()]
    per = sorted(f"{y}-{MONTHS.index(m) + 1:02d}" for y, m in zip(v["Year"], v["Month"]))
    return {"newest": per[-1] if per else None, "new_periods": _mark("lfs", per, today)}


def fetch_nasa(today: str) -> dict:
    from app.e137 import features as F
    y1 = date.fromisoformat(today).year
    rows = []
    for k, xy in sorted(F._geo().items()):
        js = json.loads(_get(NASA.format(lat=round(xy[1], 3), lon=round(xy[0], 3), y0=y1 - 3, y1=y1), timeout=120))
        p = js["properties"]["parameter"]
        for ym in p["PRECTOTCORR"]:
            if ym.endswith("13"):
                continue
            r, g = p["PRECTOTCORR"].get(ym, -999), p.get("GWETROOT", {}).get(ym, -999)
            rows.append((k, f"{ym[:4]}-{ym[4:]}", r if r > -900 else None, g if g > -900 else None))
        time.sleep(0.5)
    d = pd.DataFrame(rows, columns=["k", "month", "rain", "gwetroot"])
    _write("nasa/monthly.csv", d.to_csv(index=False, lineterminator="\n").encode())
    have = sorted(d.dropna(subset=["rain"])["month"].unique())
    return {"newest_rain": have[-1] if have else None,
            "newest_soil": max(d.dropna(subset=["gwetroot"])["month"], default=None), "provinces": int(d["k"].nunique())}


def fetch_oni(today: str) -> dict:
    body = _get(ONI_URL)
    _write("noaa/oni.txt", body)
    seas = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    per = []
    for line in body.decode().splitlines()[1:]:
        p = line.split()
        if len(p) == 4 and p[0] in seas:
            m = seas.index(p[0]) + 2
            y = int(p[1]) + (1 if m > 12 else 0)
            per.append(f"{y}-{(m - 1) % 12 + 1:02d}")
    return {"newest": max(per), "new_periods": _mark("oni", per, today)}


def fetch_ibtracs(today: str) -> dict:
    body = _get(IBTRACS_URL, timeout=600)
    d = pd.read_csv(io.BytesIO(body), skiprows=[1], usecols=["SID", "BASIN", "ISO_TIME", "LAT", "LON"], low_memory=False)
    d = d[d["BASIN"] == "WP"].drop(columns=["BASIN"])
    _write("ibtracs/wp_last3years.csv", d.to_csv(index=False, lineterminator="\n").encode())
    return {"newest": str(d["ISO_TIME"].max()), "storms": int(d["SID"].nunique())}


def fetch_remittances(today: str) -> dict:
    body = _get(WDI_URL)
    _write("worldbank/remittances.json", body)
    rows = json.loads(body)[1]
    per = sorted(r["date"] for r in rows if r["value"] is not None)
    return {"newest": per[-1] if per else None, "new_periods": _mark("remittances", per, today)}


FETCHERS = {"psa_production": fetch_production, "psa_cpi": fetch_cpi, "psa_lfs": fetch_lfs, "nasa_power": fetch_nasa,
            "noaa_oni": fetch_oni, "ibtracs": fetch_ibtracs, "worldbank_remittances": fetch_remittances}


def fetch(today: str | None = None, only: list[str] | None = None) -> dict:
    """Fetch every source; one failure is recorded and leaves that source's previous file in place."""
    today = today or date.today().isoformat()
    LIVE.mkdir(parents=True, exist_ok=True)
    res = {}
    for name, fn in FETCHERS.items():
        if only and name not in only:
            continue
        t0 = time.time()
        try:
            res[name] = {"status": "ok", **fn(today)}
        except Exception as e:                       # noqa: BLE001 - keep the other sources going
            res[name] = {"status": "failed", "error": f"{type(e).__name__}: {e}"[:400]}
        res[name]["seconds"] = round(time.time() - t0, 1)
        print(name, json.dumps(res[name]), flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "as_of": today, "sources": res}) + "\n")
    clear_caches()
    return res


# ----------------------------------------------------------------------------------------------------------- loaders
def _f(name):
    p = LIVE / name
    return p if p.exists() else None


@lru_cache(maxsize=None)
def production(name: str) -> pd.DataFrame:
    """Province x 'YYYY Quarter N' production from the live download (empty when not fetched)."""
    key = {"agri": "palay_corn_q", "fish": "fisheries_q"}[name]
    p = _f(f"psa/{key}.csv")
    if p is None:
        return pd.DataFrame()
    from app.e137 import features as F
    _, col, labs = PROD[key]
    d = pd.read_csv(p, encoding="latin-1")
    d = d[d[col].isin(labs)].copy()
    d["k"] = d["Geolocation"].map(F.nospace)
    qc = [c for c in d.columns if re.match(r"^\d{4} Quarter \d$", c)]
    d[qc] = d[qc].apply(pd.to_numeric, errors="coerce")
    return d.groupby("k")[qc].sum(min_count=1)


@lru_cache(maxsize=None)
def nasa(param: str) -> dict:
    """{nospace province key: monthly Series (Period -> value)} for 'rain' or 'gwetroot'."""
    p = _f("nasa/monthly.csv")
    if p is None:
        return {}
    d = pd.read_csv(p).dropna(subset=[param])
    d["p"] = pd.PeriodIndex(d["month"], freq="M")
    return {k: g.set_index("p")[param].astype(float) for k, g in d.groupby("k")}


def clear_caches() -> None:
    for f in (production, nasa, _seen_cached, _state_cached):
        f.cache_clear()
    for mod, names in (("app.e147.features", ("_quarterly_late", "_rain_late")), ("app.e146.soil", ("_table",)),
                       ("app.e137.features", ("_tracks", "_storm_hits"))):
        m = sys.modules.get(mod)
        for n in names:
            fn = getattr(m, n, None) if m else None
            if fn is not None and hasattr(fn, "cache_clear"):
                fn.cache_clear()


def status() -> dict:
    """What the live folder holds now: newest period per source and when it was fetched."""
    last = None
    if LOG.exists():
        lines = [l for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
        last = json.loads(lines[-1]) if lines else None
    return {"last_fetch": last, "first_seen": {k: max(v) if v else None for k, v in _seen().items()}}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    if cmd == "fetch":
        print(json.dumps(fetch(sys.argv[2] if len(sys.argv) > 2 else None), indent=1))
    else:
        print(json.dumps(status(), indent=1))
