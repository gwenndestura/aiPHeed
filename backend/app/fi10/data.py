"""Province-quarter forecast-time dataset for FI10 (one row per province x issue quarter x lead).

Target (measured, per province): quarter mean of the monthly year-on-year change in the provincial FOOD CPI (PSA).
    HIGH(p, t) = level(p, t) > mean + 1 SD of level(p, t-20 .. t-1)   (needs >= 12 earlier quarters)
This is food-price pressure in that province. It is a measured driver of food access, NOT a measure of food insecurity.
Issue date: FI9 operational timing (last day of the quarter's 2nd month). Lead h targets quarter c + h (h = 1..4).
Availability rules (never earlier than the real calendar):
    CPI month m: 10th of month m+1 | NASA POWER month m: 30 days after month end | palay quarter q: 45 days after
    quarter end | storms: track time | ONI: +10 days | LFS / remittances / poverty: FI5 release rules
    news: published on or before the issue date
Five trigger groups: market, climate (+ agricultural supply), employment and remittances, poverty, news.

    python -m app.fi10.data        # writes data/fi10/out/dataset.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.fi5 import sources as S5
from app.fi5.features import FeatureBuilder
from app.fi10 import OUT, PROVINCES, RAW
from app.fi9 import quarters as Q
from app.paths import BACKEND_DIR

E118 = BACKEND_DIR.parent / "aipheed-backend-aligned" / "experiments" / "E118_FAO_Data_Discovery" / "data" / "clean"
TC_KM, BASE_Q, MIN_BASE = 150.0, 20, 12
GROUPS = {
    "market": ["f_m", "f_q1", "f_q2", "f_q4", "mom", "z_food", "gap_known", "vol6", "head_m", "gap_fh", "rice_m", "rice_mom",
               "region_food_m", "nat_food_m", "others_food_m", "world_rice_yoy"],
    "climate": ["rain_anom_3m", "tc_90d", "tc_365d", "oni", "palay_yoy"],
    "employment": ["unemp_rate", "unemp_yoy", "remit_yoy"],
    "poverty": ["poverty_inc"],
    "news": ["news_prov_z", "news_nat_z"],
}
SEASON = ["tq2", "tq3", "tq4"]
PROV_FE = [f"is_{p}" for p in PROVINCES]


def cpi_monthly() -> pd.DataFrame:
    d = pd.read_csv(RAW / "cpi_monthly_long.csv")
    d["item"] = d["commodity_description"].map({"0 - ALL ITEMS": "all", "01.1 - FOOD": "food", "01.1.1.12 - Rice": "rice"})
    d["ym"] = d["year"] * 12 + d["month"] - 1
    d = d.sort_values(["geolocation", "item", "ym"])
    g = d.groupby(["geolocation", "item"])
    d["yoy"] = (d["value"] / g["value"].shift(12) - 1) * 100
    d.loc[(d["ym"] - g["ym"].shift(12)) != 12, "yoy"] = np.nan
    d["available_from"] = [pd.Timestamp(year=(m + 1) // 12, month=(m + 1) % 12 + 1, day=10) for m in d["ym"]]
    return d.pivot_table(index=["geolocation", "ym", "available_from"], columns="item", values="yoy").reset_index()


def quarterly_target(cm: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for p in PROVINCES:
        m = cm[cm["geolocation"] == p].copy()
        m["qi"] = m["ym"] // 3
        g = m.groupby("qi").agg(level=("food", "mean"), n=("food", "count"), published=("available_from", "max")).reset_index()
        g = g[g["n"] == 3].sort_values("qi").reset_index(drop=True)
        for i, r in g.iterrows():
            w = g[(g["qi"] >= r["qi"] - BASE_Q) & (g["qi"] < r["qi"])]["level"].dropna()
            ok = len(w) >= MIN_BASE and pd.notna(r["level"])
            thr = float(w.mean() + w.std(ddof=1)) if ok else np.nan
            rows.append({"province": p, "qi": int(r["qi"]), "quarter": Q.label(int(r["qi"])), "level": r["level"], "published": r["published"],
                         "threshold": thr, "y": float(r["level"] > thr) if ok else np.nan})
    return pd.DataFrame(rows)


def _prov_climate():
    n = pd.read_csv(BACKEND_DIR / "data" / "fi5" / "raw" / "nasa" / "nasa_power_monthly_1981_2025.csv")
    n = n[n["item"] == "PRECTOTCORR"].rename(columns={"unit": "province"})
    n["ym"] = n["period"].astype(int)
    import json
    extra = []
    for p in PROVINCES:
        f = BACKEND_DIR / "data" / "fi5" / "raw" / "nasa" / f"nasa_power_monthly_2021_2026_{p}.json"
        if f.exists():
            par = json.loads(f.read_text())["properties"]["parameter"].get("PRECTOTCORR", {})
            for k, v in par.items():
                y, mo = int(k[:4]), int(k[4:])
                if mo <= 12 and v is not None and v > -900:
                    extra.append({"province": p, "ym": y * 12 + mo - 1, "value": float(v)})
    n = pd.concat([n[["province", "ym", "value"]], pd.DataFrame(extra)]).drop_duplicates(["province", "ym"], keep="last")
    n["available_from"] = [pd.Timestamp(year=(m + 1) // 12, month=(m + 1) % 12 + 1, day=1) + pd.Timedelta(days=29) for m in n["ym"]]
    t = pd.read_csv(BACKEND_DIR / "data" / "fi5" / "raw" / "ibtracs" / "ibtracs_calabarzon_600km.csv")
    t["t"] = pd.to_datetime(t["ISO_TIME"], errors="coerce")
    storms = {}
    for p in PROVINCES:
        lat, lon = S5.CENTROIDS[p]
        near = S5._haversine(t["LAT"].to_numpy(), t["LON"].to_numpy(), lat, lon) <= TC_KM
        storms[p] = t[near].sort_values("t").groupby("SID")["t"].first().sort_values()
    pc = pd.read_csv(E118 / "prod_palay_corn.csv")
    pc = pc[(pc["item"] == "Palay") & pc["unit"].isin(PROVINCES)].rename(columns={"unit": "province"})
    pc["qi"] = pc["period"].astype(int)
    pc = pc.sort_values(["province", "qi"])
    pc["yoy"] = (pc["value"] / pc.groupby("province")["value"].shift(4) - 1) * 100
    pc.loc[(pc["qi"] - pc.groupby("province")["qi"].shift(4)) != 4, "yoy"] = np.nan
    pc["available_from"] = [Q.end(q) + pd.Timedelta(days=45) for q in pc["qi"]]
    return n, storms, pc


def _poverty():
    a = pd.read_csv(BACKEND_DIR / "data" / "fi5" / "raw" / "psa" / "psa_poverty_2006_2015.csv", encoding="latin-1")
    b = pd.read_csv(BACKEND_DIR / "data" / "fi5" / "raw" / "psa" / "psa_poverty_2018_2023.csv", encoding="latin-1")
    rows = []
    for df, years, col in [(a, [2006, 2009, 2012, 2015], "Poverty Incidence among Population Estimate (%) {}"),
                           (b, [2018, 2021, 2023], "Poverty Incidence among Population (%) {}")]:
        for _, r in df.iterrows():
            p = next((x for x in PROVINCES if x in str(r.iloc[0])), None)
            if p:
                for y in years:
                    v = pd.to_numeric(r.get(col.format(y)), errors="coerce")
                    if pd.notna(v):
                        rows.append({"province": p, "year": y, "poverty_inc": float(v),
                                     "available_from": pd.Timestamp(S5.POVERTY_RELEASE.get(y, f"{y + 2}-01-02"))})
    return pd.DataFrame(rows)


def _news(dates):
    a = pd.read_parquet(BACKEND_DIR / "data" / "fi6" / "news_archive" / "articles.parquet", columns=["published", "provinces", "excluded"])
    a = a[~a["excluded"].fillna(False)]
    e = pd.read_parquet(BACKEND_DIR / "data" / "fi6" / "news_archive" / "events.parquet")
    e = e[~e["restated_statistic"] & e["relevant"].fillna(False) & (e["p_harder"].fillna(0) > e["p_easier"].fillna(0))].drop_duplicates("event_id")
    out = {}
    for d in dates:
        lo = d - pd.Timedelta(days=90)
        aw, ew = a[(a["published"] > lo) & (a["published"] <= d)], e[(e["published"] > lo) & (e["published"] <= d)]
        out[(d, "_national")] = len(ew) / len(aw) if len(aw) >= 30 else np.nan
        for p in PROVINCES:
            na = aw["provinces"].fillna("").str.contains(p).sum()
            ne = ew["provinces"].fillna("").str.contains(p).sum()
            out[(d, p)] = ne / na if na >= 10 else np.nan
    return out


def build(live: pd.Timestamp | None = None) -> pd.DataFrame:
    """live: also build the rows of the current issue (issue date = min(scheduled, live)); the file is then not written.
    (Amendment after the locked FI10 run: the historical rows are unchanged; see docs/fi10.)"""
    cm = cpi_monthly()
    T = quarterly_target(cm)
    nasa, storms, palay = _prov_climate()
    pov = _poverty()
    fb = FeatureBuilder()
    from app.fi7 import extra_sources as X7
    extra = X7.load_cache()
    lo_q, hi_q = Q.index("1997-Q1"), int(T["qi"].max())
    issues = [(c, Q.scheduled_issue(c)) for c in range(lo_q, hi_q + 1)]
    if live is not None:
        lc = Q.qi_of(live)
        issues = [(c, d) for c, d in issues if d <= pd.Timestamp(live)] + [(lc, min(Q.scheduled_issue(lc), pd.Timestamp(live).normalize()))]
    news = _news([d for _, d in issues])
    rows = []
    for c, d in issues:
        known = cm[cm["available_from"] <= d]
        lfs = fb.lfs[fb.lfs["available_from"] <= d]
        rem = fb.remit[fb.remit["available_from"] <= d]
        oni = fb.oni[fb.oni["available_from"] <= d]
        wr = X7.asof_extra(d, Q.start(c), extra).get("world_rice_yoy", np.nan)
        latest = {g: k.sort_values("ym") for g, k in known.groupby("geolocation")}
        if any(p not in latest or latest[p].empty for p in PROVINCES):
            continue
        last_food = {p: latest[p]["food"].iloc[-1] for p in PROVINCES}
        for p in PROVINCES:
            k = latest[p]
            k = k[k["food"].notna()]
            if len(k) < 24:
                continue
            kq = k.assign(qi=k["ym"] // 3).groupby("qi")["food"].agg(["mean", "count"])
            kq = kq[kq["count"] == 3]["mean"]
            tk = T[(T["province"] == p) & (T["published"] <= d)]
            base = tk.tail(BASE_Q)["level"]
            bm, bs = (float(base.mean()), float(base.std(ddof=1))) if len(base) >= MIN_BASE else (np.nan, np.nan)
            n_p = nasa[(nasa["province"] == p) & (nasa["available_from"] <= d)].sort_values("ym")
            rain = np.nan
            if len(n_p) >= 36:                      # last 3 months vs the same 3 calendar months in earlier years
                e = int(n_p["ym"].iloc[-1])
                vals = n_p.set_index("ym")["value"]
                cur = vals.loc[e - 2:e].mean()
                hist = [vals.loc[e - 12 * k - 2:e - 12 * k].mean() for k in range(1, 60) if e - 12 * k - 2 >= vals.index.min()]
                if len(hist) >= 10:
                    rain = float((cur - np.mean(hist)) / np.std(hist, ddof=1))
            st = storms[p]
            pa = palay[(palay["province"] == p) & (palay["available_from"] <= d)].dropna(subset=["yoy"])
            pv = pov[(pov["province"] == p) & (pov["available_from"] <= d)].sort_values("year")
            f_m = float(k["food"].iloc[-1])
            rec = {"province": p, "issue_quarter": Q.label(c), "issue_date": d, "cpi_month": int(k["ym"].iloc[-1]),
                   "f_m": f_m, "f_q1": kq.iloc[-1] if len(kq) else np.nan, "f_q2": kq.iloc[-2] if len(kq) > 1 else np.nan,
                   "f_q4": kq.iloc[-4] if len(kq) > 3 else np.nan, "base_mean": bm, "base_sd": bs, "thr_known": bm + bs,
                   "vol6": float(k["food"].tail(6).std(ddof=1)), "head_m": float(latest[p]["all"].dropna().iloc[-1]),
                   "rice_m": float(latest[p]["rice"].dropna().iloc[-1]),
                   "rice_mom": float(latest[p]["rice"].dropna().iloc[-1] - latest[p]["rice"].dropna().iloc[-4:-1].mean()),
                   "region_food_m": float(latest["Region IV-A (CALABARZON)"]["food"].dropna().iloc[-1]),
                   "nat_food_m": float(latest["PHILIPPINES"]["food"].dropna().iloc[-1]),
                   "others_food_m": float(np.mean([last_food[q] for q in PROVINCES if q != p])), "world_rice_yoy": wr,
                   "rain_anom_3m": rain, "tc_90d": int(((st > d - pd.Timedelta(days=90)) & (st <= d)).sum()),
                   "tc_365d": int(((st > d - pd.Timedelta(days=365)) & (st <= d)).sum()),
                   "oni": float(oni["oni"].iloc[-1]) if len(oni) else np.nan, "palay_yoy": float(pa["yoy"].iloc[-1]) if len(pa) else np.nan,
                   "unemp_rate": float(lfs["unemp_rate"].iloc[-1]) if len(lfs) else np.nan,
                   "unemp_yoy": float(lfs["unemp_yoy"].iloc[-1]) if len(lfs) else np.nan,
                   "remit_yoy": float(rem["remit_yoy"].iloc[-1]) if len(rem) else np.nan,
                   "poverty_inc": float(pv["poverty_inc"].iloc[-1]) if len(pv) else np.nan,
                   "news_prov": news[(d, p)], "news_nat": news[(d, "_national")]}
            rec["mom"] = rec["f_m"] - rec["f_q1"]
            rec["z_food"] = (f_m - bm) / bs if bs and bs == bs and bs > 0 else np.nan
            rec["gap_known"] = f_m - rec["thr_known"]
            rec["gap_fh"] = f_m - rec["head_m"]
            for h in (1, 2, 3, 4):
                t = T[(T["province"] == p) & (T["qi"] == c + h)]
                r = {**rec, "lead": h, "target_quarter": Q.label(c + h),
                     **{f"tq{k}": int((c + h) % 4 == k - 1) for k in (2, 3, 4)}, **{f"is_{q}": int(q == p) for q in PROVINCES}}
                if len(t):
                    r.update(y=t["y"].iloc[0], level=t["level"].iloc[0], threshold=t["threshold"].iloc[0], target_published=t["published"].iloc[0])
                rows.append(r)
    D = pd.DataFrame(rows).sort_values(["lead", "issue_date", "province"]).reset_index(drop=True)
    for col, src in [("news_prov_z", "news_prov"), ("news_nat_z", "news_nat")]:       # z against earlier issue dates only
        D[col] = np.nan
        for (h, p), g in D.groupby(["lead", "province"]):
            x = g[src].to_numpy(float)
            z = [((x[i] - np.nanmean(x[:i])) / np.nanstd(x[:i], ddof=1)) if np.sum(~np.isnan(x[:i])) >= 8 and not np.isnan(x[i]) else np.nan for i in range(len(x))]
            D.loc[g.index, col] = z
    D["delta"] = D["level"] - D["f_m"]
    if live is None:                                   # serving builds the live rows in memory only
        D.to_csv(OUT / "dataset.csv", index=False, lineterminator="\n")
    return D


if __name__ == "__main__":
    D = build()
    L = D[D["y"].notna()]
    print(D.shape, "labelled", len(L))
    print(L.groupby("lead").agg(n=("y", "size"), high=("y", "mean"), first=("target_quarter", "min"), last=("target_quarter", "max")).to_string())
    print(L[L["lead"] == 1].groupby("province")["y"].agg(["size", "mean"]).to_string())
    print(D[list(sum([v for v in __import__("app.fi10.data", fromlist=["GROUPS"]).GROUPS.values()], []))].notna().mean().round(2).to_string())
