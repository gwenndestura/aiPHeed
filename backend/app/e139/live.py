"""
E139 live features: the latest public values for every province at an issue date (default 2026-10-01, the start of
2026-Q4), built with the training release rules.

    python -m app.e139.live acquire     PSA CPI 2024-2025 (2018=100), palay/corn and fisheries 2023-2026, NASA POWER
                                        monthly 2000-2026 at each province centroid -> data/e139/raw/
    python -m app.e139.live build       -> data/e139/out/live_features.csv

Release rules: annual CPI A from 15 Feb A+1; poverty round R from 1 Jan R+2 (2023 round); census C from 1 Jan C+2
(2024); quarterly production 45 days after the quarter; NASA month 30 days after it ends; cyclones in real time.
Measured history: a_prev_y = the province's latest measured relative position (ENNS if surveyed, else 2015);
a_region_prev = mean of the latest measured positions of the region's provinces.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import date

import numpy as np
import pandas as pd

from app.e137 import RAW as RAW137
from app.e137 import external as X137
from app.e137 import features as F
from app.e137 import outcomes as O
from app.e137.acquire import NASA, PX, _get, _sha, centroids
from app.e138 import RAW as RAW138
from app.e139 import OUT
from app.paths import BACKEND_DIR

RAW = BACKEND_DIR / "data" / "e139" / "raw"
ISSUE = pd.Timestamp("2026-10-01")
TABLES = {
    "cpi2018_ave_2024_2025": ("DB/2M/PI/CPI/2018NEW/0012M4ACP22.px",
                              {"Year": lambda t: t in ("2024", "2025"), "Period": lambda t: t == "Ave",
                               "Commodity Description": lambda t: any(t.startswith(g) for g in X137.CPI_GROUPS)}),
    "palay_corn_q_2023_2026": ("DB/2E/CS/0012E4EVCP0.px", {"Ecosystem/Croptype": lambda t: t in ("Palay", "Corn"),
                                                          "Year": lambda t: t in ("2023", "2024", "2025", "2026"),
                                                          "Period": lambda t: t.startswith("Quarter")}),
    "fisheries_q_2023_2026": ("DB/2E/FS/0132E4GVFP1.px", {"Subsector": lambda t: t == "FISHERIES",
                                                        "Year": lambda t: t in ("2023", "2024", "2025", "2026"),
                                                        "Quarter": lambda t: t.startswith("Quarter")}),
}


def acquire() -> None:
    (RAW / "psa").mkdir(parents=True, exist_ok=True)
    (RAW / "nasa").mkdir(parents=True, exist_ok=True)
    man = []
    for name, (path, pick) in TABLES.items():
        meta = json.loads(_get(PX + path, timeout=120))
        q = []
        for v in meta["variables"]:
            if "values" not in v:
                q.append({"code": v["code"], "selection": {"filter": "all", "values": ["*"]}})
            else:
                vals = [c for c, t in zip(v["values"], v["valueTexts"]) if pick[v["code"]](t.strip())] if v["code"] in pick else v["values"]
                q.append({"code": v["code"], "selection": {"filter": "item", "values": vals}})
        f = RAW / "psa" / f"{name}.csv"
        f.write_bytes(_get(PX + path, json.dumps({"query": q, "response": {"format": "csv"}}).encode()))
        man.append(f"psa/{f.name},{PX + path},{date.today()},{_sha(f)}")
    for name, (lon, lat) in sorted(centroids().items()):
        f = RAW / "nasa" / f"power_{name}.json"
        url = NASA.format(lon=lon, lat=lat).replace("end=2019", "end=2026")
        if not f.exists():
            for attempt in range(4):
                try:
                    f.write_bytes(_get(url, timeout=120))
                    break
                except Exception as e:                       # noqa: BLE001
                    print("retry", name, e)
                    time.sleep(5 * (attempt + 1))
            time.sleep(1)
        man.append(f"nasa/{f.name},{url},{date.today()},{_sha(f)}")
    (RAW / "MANIFEST.csv").write_text("file,source_url,retrieved,sha256\n" + "\n".join(man) + "\n")


def _read(p):
    return pd.read_csv(p, dtype=str, encoding="latin-1")


def _fy(path, pat, year="2023"):
    d = _read(path)
    d["k"] = X137._clean_geo(d.iloc[:, 0])
    col = next(c for c in d.columns if re.search(pat, c) and c.strip().endswith(year))
    s = pd.Series(pd.to_numeric(d[col], errors="coerce").values, index=d["k"])
    return s[~s.index.duplicated()]


def history() -> tuple[dict, dict]:
    d = O.load()
    d = d[d["has_value"]].sort_values("year")
    latest = d.groupby("key").last()
    own = {k.replace(" ", ""): float(v) for k, v in latest["y"].items()}
    reg = latest.groupby("region")["y"].mean()
    region_of = {k.replace(" ", ""): r for k, r in latest["region"].items()}
    return own, {k: float(reg[r]) for k, r in region_of.items()}


def build(issue: pd.Timestamp = ISSUE) -> pd.DataFrame:
    y23 = RAW137 / "y2023" / "psa"
    pov, gap = _fy(y23 / "poverty_pop_2018_2023.csv", "Poverty Incidence"), _fy(y23 / "poverty_gap_2018_2023.csv", "Estimate")
    sub = _fy(RAW138 / "psa" / "subsistence_families_2018_2023.csv", "Subsistence Incidence")
    thr = _fy(RAW138 / "psa" / "subsistence_families_2018_2023.csv", r"Food\s+Threshold")
    cen = _read(RAW137 / "psa" / "population_2010_2024.csv")
    cen = cen[cen.iloc[:, 0].str.match(r"^\.\.\.\.[^.]")]
    cen["k"] = cen.iloc[:, 0].str.replace("*", "", regex=False).map(F.nospace)
    pop = pd.to_numeric(cen.set_index("k").filter(like="2024)").iloc[:, 0], errors="coerce")
    pop = pop[~pop.index.duplicated()]
    area = F._census()["area"]
    cpi = _read(RAW / "psa" / "cpi2018_ave_2024_2025.csv")
    cpi["k"] = cpi["Geolocation"].map(F.nospace)
    yc = {y: next(c for c in cpi.columns if y in c) for y in ("2024", "2025")}
    qd = {}
    for name, f, lab_col, labs in (("agri", "palay_corn_q_2023_2026.csv", "Ecosystem/Croptype", ("Palay", "Corn")),
                                   ("fish", "fisheries_q_2023_2026.csv", "Subsector", ("FISHERIES",))):
        d = _read(RAW / "psa" / f)
        d = d[d[lab_col].isin(labs)].copy()
        d["k"] = d["Geolocation"].map(F.nospace)
        qc = [c for c in d.columns if re.match(r"^\d{4} Quarter \d$", c)]
        d[qc] = d[qc].apply(pd.to_numeric, errors="coerce")
        qd[name] = (d.groupby("k")[qc].sum(min_count=1), F._published_quarters(qc, issue))
    rain = {}
    for f in (RAW / "nasa").glob("power_*.json"):
        k = F.nospace(f.stem.replace("power_", ""))
        k = (F.GEO_ALIAS.get(k, k) or "").replace(" ", "")
        v = json.loads(f.read_text())["properties"]["parameter"]["PRECTOTCORR"]
        s = pd.Series({pd.Period(f"{x[:4]}-{x[4:]}", "M"): val for x, val in v.items() if x[4:] != "13"}, dtype=float)
        rain[k] = s.where(s > -900)
    own, regprev = history()
    keys = sorted(own)
    rows = []
    for k in keys:
        r = {c: np.nan for c in F.FEATURES}
        r["p_poverty"] = float(F._logit(pov[k])) if k in pov.index else np.nan
        r["p_subsistence"] = float(F._logit(sub[k])) if k in sub.index else np.nan
        r["p_poverty_gap"] = float(gap[k]) if k in gap.index else np.nan
        r["m_food_threshold_rel"] = float(np.log(thr[k] / thr["philippines"])) if k in thr.index else np.nan
        p = pop.get(k, np.nan)
        if pd.notna(p) and k in area.index and area[k] > 0:
            r["p_density"] = float(np.log(p / area[k]))
        g = cpi[cpi["k"] == k]
        for name, sel in (("m_food_cpi_yoy", None), ("m_rice_cpi_yoy", "01.1.1.12 - Rice")):
            gi = g if sel is None else g[g["Commodity Description"] == sel]
            if len(gi):
                a, b = (pd.to_numeric(gi[yc[y]], errors="coerce").mean() for y in ("2025", "2024"))
                r[name] = float(np.log(a / b)) if a > 0 and b > 0 else np.nan
        for name, (q, pub) in qd.items():
            if k in q.index and len(pub) >= 8:
                l4, p4 = q.loc[k, pub[-4:]].sum(min_count=4), q.loc[k, pub[-8:-4]].sum(min_count=4)
                if l4 > 0 and p4 > 0:
                    r[f"c_{name}_yoy"] = float(np.log(l4 / p4))
                if name == "agri" and pd.notna(p) and l4 > 0:
                    r["c_agri_pc"] = float(np.log(l4 / p))
        s = rain.get(k)
        if s is not None:
            last = (issue - pd.Timedelta(days=30)).to_period("M") - 1
            months = pd.period_range(last - 5, last, freq="M")
            if all(m in s.index and pd.notna(s[m]) for m in months):
                clim = [s[[pd.Period(year=y, month=m.month, freq="M") for m in months]].mean() for y in range(2000, 2010)]
                r["c_rain_anom_6m"] = float((s[months].mean() - np.mean(clim)) / np.std(clim, ddof=1))
        hits = F._storm_hits(k)
        if F._geo().get(k) is not None:
            r["c_tc_4q"] = float(((hits["t"] < issue) & (hits["t"] >= issue - pd.Timedelta(days=365))).sum())
            r["c_tc_clim"] = float(((hits["t"] >= "1990-01-01") & (hits["t"] < "2010-01-01")).sum() / 20.0)
        r["a_prev_y"], r["a_region_prev"] = own.get(k, np.nan), regprev.get(k, np.nan)
        rows.append({"k": k, "issue_date": issue.date().isoformat(), **r})
    X = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    X.to_csv(OUT / "live_features.csv", index=False)
    return X


if __name__ == "__main__":
    {"acquire": acquire, "build": lambda: print(build()[F.FEATURES + ["a_region_prev"]].notna().mean().round(2).to_dict())}[sys.argv[1]]()
