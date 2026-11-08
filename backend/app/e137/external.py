"""
E137 check S11 (PROTOCOL.md section 8): external agreement with PSA FIES 2023 regional moderate-or-severe prevalence.
Run once, after the development run.

    python -m app.e137.external acquire     2021-2023 inputs (PSA OpenSTAT, NASA POWER to 2023)
    python -m app.e137.external run         -> data/e137/out/external_s11.json

The final Lead-0 model (formulation chosen by the frozen rule, trained on all 125 HFIAS rows) is applied to every
province with features as of 2023-07-01 (Lead 0 for reference quarter 2023-Q3). Province probabilities are averaged to
regions with 2020 census weights. FIES is a different instrument from HFIAS, so this measures agreement, not accuracy.

Definitional differences from the training features (disclosed, not corrected):
    * CPI is the 2018=100 series with COICOP 2018 food groups (training: 2012=100 groups); the feature is a YoY ratio.
    * Poverty statistics use the 2018+ methodology; subsistence incidence is among population (training: families).
    * Census 2020 replaces 2015 for density and per-capita production.
"""
from __future__ import annotations

import json
import re
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from app.e137 import OUT, RAW
from app.e137 import evaluate as E
from app.e137 import features as F
from app.e137 import model as M
from app.e137 import outcomes as O
from app.e137.acquire import NASA, PX, _get, _manifest, _sha, centroids
from app.paths import BACKEND_DIR

RAW23 = RAW / "y2023"
ISSUE = pd.Timestamp("2023-07-01")
CPI_GROUPS = ["01.1.1.12 - Rice", "01.1.1.16 - Corn", "01.1.2 -", "01.1.3 -", "01.1.4 -", "01.1.6 -", "01.1.7 -"]
TABLES = {
    "cpi2018_ave": ("DB/2M/PI/CPI/2018NEW/0012M4ACP22.px",
                    {"Year": lambda t: t in ("2021", "2022"), "Period": lambda t: t == "Ave",
                     "Commodity Description": lambda t: any(t.startswith(g) for g in CPI_GROUPS)}),
    "poverty_pop_2018_2023": ("DB/1F/FY/0031F3DF020.px", {}),
    "subsistence_pop_2018_2023": ("DB/1F/FY/0071F3DF040.px", {}),
    "poverty_gap_2018_2023": ("DB/1F/FY/0201F3DF011.px", {}),
    "palay_corn_q_2020_2023": ("DB/2E/CS/0012E4EVCP0.px", {"Ecosystem/Croptype": lambda t: t in ("Palay", "Corn"),
                                                          "Year": lambda t: t in ("2020", "2021", "2022", "2023"),
                                                          "Period": lambda t: t.startswith("Quarter")}),
    "fisheries_q_2020_2023": ("DB/2E/FS/0132E4GVFP1.px", {"Subsector": lambda t: t == "FISHERIES",
                                                        "Year": lambda t: t in ("2020", "2021", "2022", "2023"),
                                                        "Quarter": lambda t: t.startswith("Quarter")}),
}
FIES_REGION = {"CAR": "Cordillera Administrative Region (CAR)", "Ilocos": "Region I", "Cagayan Valley": "Region II",
               "Central Luzon": "Region III", "CALABARZON": "Region IV-A", "MIMAROPA": "MIMAROPA Region", "Bicol": "Region V",
               "Western Visayas": "Region VI", "Central Visayas": "Region VII", "Eastern Visayas": "Region VIII",
               "Zamboanga Peninsula": "Region IX", "Northern Mindanao": "Region X", "Davao": "Region XI",
               "SOCCSKSARGEN": "Region XII", "Caraga": "Region XIII",
               "ARMM": "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)"}


def acquire() -> None:
    (RAW23 / "psa").mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (path, pick) in TABLES.items():
        meta = json.loads(_get(PX + path, timeout=120))
        q = []
        for v in meta["variables"]:
            if "values" not in v:
                q.append({"code": v["code"], "selection": {"filter": "all", "values": ["*"]}})
            elif v["code"] in pick:
                q.append({"code": v["code"], "selection": {"filter": "item", "values": [c for c, t in zip(v["values"], v["valueTexts"]) if pick[v["code"]](t.strip())]}})
            else:
                q.append({"code": v["code"], "selection": {"filter": "item", "values": v["values"]}})
        body = _get(PX + path, json.dumps({"query": q, "response": {"format": "csv"}}).encode())
        f = RAW23 / "psa" / f"{name}.csv"
        f.write_bytes(body)
        rows.append({"file": f"y2023/psa/{f.name}", "source_url": PX + path, "retrieved": pd.Timestamp.today().date().isoformat(),
                     "sha256": _sha(f), "description": name})
        print(name, len(body))
    (RAW23 / "nasa").mkdir(parents=True, exist_ok=True)
    for name, (lon, lat) in sorted(centroids().items()):
        f = RAW23 / "nasa" / f"power_{name}.json"
        url = NASA.format(lon=lon, lat=lat).replace("end=2019", "end=2023")
        if not f.exists():
            for attempt in range(4):
                try:
                    f.write_bytes(_get(url, timeout=120))
                    break
                except Exception as e:                       # noqa: BLE001
                    print("retry", name, e)
                    time.sleep(5 * (attempt + 1))
            time.sleep(1)
        rows.append({"file": f"y2023/nasa/{f.name}", "source_url": url, "retrieved": pd.Timestamp.today().date().isoformat(),
                     "sha256": _sha(f), "description": f"NASA POWER monthly PRECTOTCORR {name} 2000-2023"})
    _manifest(rows)


def _read(name):
    return pd.read_csv(RAW23 / "psa" / f"{name}.csv", dtype=str, encoding="latin-1")


def _clean_geo(s: pd.Series) -> pd.Series:
    return s.str.replace(r"\s+(r\d|\d/|[a-z]/|\*+)(,\s*(r\d|\d/|[a-z]/|\*+))*\s*$", "", regex=True).map(F.nospace)


def _fy(name, col_pat, year="2021") -> pd.Series:
    d = _read(name)
    d["k"] = _clean_geo(d.iloc[:, 0])
    col = next(c for c in d.columns if re.search(col_pat, c) and c.strip().endswith(year))
    s = pd.Series(pd.to_numeric(d[col], errors="coerce").values, index=d["k"])
    return s[~s.index.duplicated()]


def features_2023(keys: list[str], anchor: dict) -> pd.DataFrame:
    cpi = _read("cpi2018_ave")
    cpi["k"] = cpi["Geolocation"].map(F.nospace)
    yc = {y: next(c for c in cpi.columns if y in c) for y in ("2021", "2022")}
    pov, sub = _fy("poverty_pop_2018_2023", r"Poverty Incidence"), _fy("subsistence_pop_2018_2023", r"Subsistence Incidence")
    thr, gap = _fy("subsistence_pop_2018_2023", r"Food\s+Threshold"), _fy("poverty_gap_2018_2023", r"Estimate")
    cen = pd.read_csv(RAW / "psa" / "population_2010_2024.csv", dtype=str, encoding="latin-1")
    cen = cen[cen.iloc[:, 0].str.match(r"^\.\.\.\.[^.]")]
    cen["k"] = cen.iloc[:, 0].str.replace("*", "", regex=False).map(F.nospace)
    pop20 = pd.to_numeric(cen.set_index("k").filter(like="2020)").iloc[:, 0], errors="coerce")
    pop20 = pop20[~pop20.index.duplicated()]
    area = F._census()["area"]
    qd = {}
    for name, col, labs in (("agri", "palay_corn_q_2020_2023", ("Palay", "Corn")), ("fish", "fisheries_q_2020_2023", ("FISHERIES",))):
        d = _read(col)
        lab_col = "Ecosystem/Croptype" if name == "agri" else "Subsector"
        d = d[d[lab_col].isin(labs)].copy()
        d["k"] = d["Geolocation"].map(F.nospace)
        qcols = [c for c in d.columns if re.match(r"^\d{4} Quarter \d$", c)]
        d[qcols] = d[qcols].apply(pd.to_numeric, errors="coerce")
        qd[name] = (d.groupby("k")[qcols].sum(min_count=1), F._published_quarters(qcols, ISSUE))
    rain = {}
    for f in (RAW23 / "nasa").glob("power_*.json"):
        k = F.nospace(f.stem.replace("power_", ""))
        k = (F.GEO_ALIAS.get(k, k) or "").replace(" ", "")
        v = json.loads(f.read_text())["properties"]["parameter"]["PRECTOTCORR"]
        rain[k] = pd.Series({pd.Period(f"{x[:4]}-{x[4:]}", "M"): val for x, val in v.items() if x[4:] != "13"}, dtype=float)
    rows = []
    for k in keys:
        r = {f: np.nan for f in F.FEATURES}
        g = cpi[cpi["k"] == k]
        for name, sel in (("m_food_cpi_yoy", None), ("m_rice_cpi_yoy", "01.1.1.12 - Rice")):
            gi = g if sel is None else g[g["Commodity Description"] == sel]
            if len(gi):
                a, b = (pd.to_numeric(gi[yc[y]], errors="coerce").mean() for y in ("2022", "2021"))
                r[name] = float(np.log(a / b)) if a > 0 and b > 0 else np.nan
        if k in thr.index:
            r["m_food_threshold_rel"] = float(np.log(thr[k] / thr["philippines"]))
        if k in pov.index:
            r["p_poverty"] = float(F._logit(pov[k]))
        if k in sub.index:
            r["p_subsistence"] = float(F._logit(sub[k]))
        if k in gap.index:
            r["p_poverty_gap"] = float(gap[k])
        p = pop20.get(k, np.nan)
        if pd.notna(p) and k in area.index and area[k] > 0:
            r["p_density"] = float(np.log(p / area[k]))
        for name, (q, pub) in qd.items():
            if k in q.index and len(pub) >= 8:
                l4, p4 = q.loc[k, pub[-4:]].sum(min_count=4), q.loc[k, pub[-8:-4]].sum(min_count=4)
                if l4 > 0 and p4 > 0:
                    r[f"c_{name}_yoy"] = float(np.log(l4 / p4))
                if name == "agri" and pd.notna(p) and l4 > 0:
                    r["c_agri_pc"] = float(np.log(l4 / p))
        s = rain.get(k)
        if s is not None:
            last = (ISSUE - pd.Timedelta(days=30)).to_period("M") - 1
            months = pd.period_range(last - 5, last, freq="M")
            if all(m in s.index for m in months):
                clim = [s[[pd.Period(year=y, month=m.month, freq="M") for m in months]].mean() for y in range(2000, 2010)]
                r["c_rain_anom_6m"] = float((s[months].mean() - np.mean(clim)) / np.std(clim, ddof=1))
        hits = F._storm_hits(k)
        if F._geo().get(k) is not None:
            r["c_tc_4q"] = float(((hits["t"] < ISSUE) & (hits["t"] >= ISSUE - pd.Timedelta(days=365))).sum())
            r["c_tc_clim"] = float(((hits["t"] >= "1990-01-01") & (hits["t"] < "2010-01-01")).sum() / 20.0)
        r["a_prev_y"] = anchor.get(k, np.nan)
        rows.append({"k": k, "pop2020": p, **r})
    return pd.DataFrame(rows)


def run() -> dict:
    E.verify_lock()
    res = json.loads((OUT / "results.json").read_text())
    kind = res["formulation_choice"]["chosen"]
    X = E._data(*E.PRIMARY, 0)
    mdl = M.LGBRisk(kind).fit(X)
    psa = M.SoftLogit(M.PSA_ONLY).fit(X)
    d = O.load(*E.PRIMARY)
    d = d[d["has_value"]]
    latest = d.sort_values("year").groupby("key").last()
    anchor = {k.replace(" ", ""): v for k, v in latest["y"].items()}
    prov = d[d["survey"] == "FNRI2015"][["key", "province", "region"]].drop_duplicates("key")
    prov["k"] = prov["key"].str.replace(" ", "")
    Z = prov.merge(features_2023(prov["k"].tolist(), anchor), on="k")
    Z["p_lgbm"], Z["p_psa_only"] = mdl.predict_proba(Z), psa.predict_proba(Z)
    Z["latest_hfias_rel"] = Z["a_prev_y"]
    fies = pd.read_csv(BACKEND_DIR / "data" / "fi_labels" / "clean" / "published_fies_psa_sdg212.csv")
    fies = fies[(fies["year"] == 2023) & (fies["level"] == "region")].set_index("geography")["percent"]
    w = Z.dropna(subset=["pop2020"])
    reg = w.groupby("region").apply(lambda g: pd.Series({c: np.average(g[c], weights=g["pop2020"]) for c in
                                                        ["p_lgbm", "p_psa_only", "latest_hfias_rel"]} | {"n_prov": len(g)}))
    reg["fies_2023_mod_sev"] = reg.index.map(lambda r: fies.get(FIES_REGION.get(r)))
    reg = reg.dropna(subset=["fies_2023_mod_sev"])
    out = {"model": f"LGBM-{kind}, Lead 0, trained on {len(X)} HFIAS rows", "issue_date": ISSUE.date().isoformat(),
           "n_regions": int(len(reg)), "feature_coverage": Z[F.FEATURES].notna().mean().round(3).to_dict()}
    for c in ["p_lgbm", "p_psa_only", "latest_hfias_rel"]:
        s = spearmanr(reg[c], reg["fies_2023_mod_sev"])
        out[c] = {"spearman": float(s.statistic), "p": float(s.pvalue)}
    out["spearman"], out["p"] = out["p_lgbm"]["spearman"], out["p_lgbm"]["p"]
    out["passed"] = bool(out["spearman"] >= E.THRESHOLDS["S11_external_spearman"] and out["p"] < E.THRESHOLDS["S11_external_p"])
    out["regions"] = reg.round(4).reset_index().to_dict(orient="records")
    out["calabarzon_provinces_2023Q3"] = Z[Z["region"] == "CALABARZON"][["province", "p_lgbm", "p_psa_only", "latest_hfias_rel"]].round(4).to_dict(orient="records")
    (OUT / "external_s11.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({k: out[k] for k in ["n_regions", "p_lgbm", "p_psa_only", "latest_hfias_rel", "passed"]}, indent=1))
    return out


if __name__ == "__main__":
    {"acquire": acquire, "run": run}[sys.argv[1]]()
