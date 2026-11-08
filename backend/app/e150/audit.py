"""
Data quality audit and experiment comparison. Fits nothing.

    python -m app.e150.audit -> data/e150/out/feature_availability.csv, data_manifest.csv, comparison.json
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

from app.e147 import OUT as O147
from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import OUT as O148
from app.e149 import OUT as O149
from app.e150 import OUT, RAW
from app.e150 import model as M
from app.fi5.target import qlabel
from app.paths import BACKEND_DIR

CAL = ["batangas", "cavite", "laguna", "quezon", "rizal"]
SOURCES = {
    "cpi_": ("Market and prices", "PSA OpenSTAT 0012M4ACPI1, 0012M4ACPI4 (2012=100), 0012M4ACP22 (2018=100)", "province", "monthly", "first day of second following month", "Good; food-only 01.1; bases never spliced; yoy inside one base"),
    "m_food_threshold_rel": ("Market and prices", "PSA OpenSTAT food threshold tables", "province", "triennial", "survey year + 2", "Coarse"),
    "c_soil": ("Climate stress", "NASA POWER GWETROOT", "province centroid", "monthly", "2-month delay", "Good; centroid, not area average"),
    "c_rain": ("Climate stress", "NASA POWER PRECTOTCORR", "province centroid", "monthly", "1-2 month delay", "Mixed; outliers in 2021"),
    "c_tc": ("Climate stress", "IBTrACS", "within 150 km of centroid", "event", "before issue", "Good"),
    "c_agri": ("Climate stress", "PSA palay and corn production", "province", "quarterly", "E137 publication rule", "Good; two files joined at 2020"),
    "c_fish": ("Climate stress", "PSA fisheries production", "province", "quarterly", "E137 publication rule", "Good; two files joined at 2020"),
    "oni": ("Climate stress", "NOAA ONI", "national", "monthly", "FI5 rule", "Good; no province variation"),
    "unemp_region": ("Employment", "PSA SDG table", "region", "annual, 2021 onward", "following year", "Limited history"),
    "unemp": ("Employment", "PSA LFS 0021B3FKEI2", "national", "quarterly rounds", "FI5 rule", "No province variation; cannot separate provinces"),
    "remit": ("OFW remittances", "BSP via World Bank; BSP quarterly from 2021", "national", "annual; quarterly from 2021", "FI5 rule", "No province variation; cannot separate provinces"),
    "p_": ("Poverty and vulnerability", "PSA poverty and subsistence rounds; PSA density", "province", "triennial or census", "survey year + 2", "Good but slow"),
    "fv2_": ("News/NLP", "Rappler, BusinessWorld, Interaksyon, VERA Files, NewsBytes, PCIJ archives; XLM-RoBERTa", "province sentence", "publication date", "before issue", "Attribution from sentences; sentiment unvalidated locally"),
}


def src(c):
    for k, v in SOURCES.items():
        if c.startswith(k):
            return v
    return ("Other", "", "", "", "", "")


def main():
    g = pd.read_parquet(O148 / "gov_panel.parquet")
    c = pd.read_parquet(OUT / "cpi_panel.parquet")
    n = pd.read_parquet(OUT / "news_v2_panel.parquet")
    P = g.merge(c, on=["key", "qi"], how="left").merge(n.drop(columns=["fv2_n"], errors="ignore"), on=["key", "qi"], how="left")
    rows = []
    cols = [x for x in P.columns if x not in ("key", "qi", "m_food_cpi_yoy", "m_rice_cpi_yoy", "cpi_age_m")]
    for cname in cols:
        s = src(cname)
        for k in CAL:
            x = P[P["key"] == k].sort_values("qi")
            v = x[cname]
            ok = x.loc[v.notna(), "qi"]
            ch = v.dropna()
            rows.append({"province": k, "feature": cname, "trigger_group": s[0], "source": s[1], "geography": s[2], "frequency": s[3], "release_rule": s[4], "quality_note": s[5], "first_issue": qlabel(int(ok.min())) if len(ok) else None, "last_issue": qlabel(int(ok.max())) if len(ok) else None,
                         "missing_share_2013_2026": round(float(v.isna().mean()), 3), "distinct_values": int(ch.round(6).nunique()), "share_quarters_changed": round(float((ch.diff().abs() > 1e-9).mean()), 3)})
    A = pd.DataFrame(rows)
    A.to_csv(OUT / "feature_availability.csv", index=False, lineterminator="\n")
    summ = A.groupby(["trigger_group", "feature"]).agg(missing=("missing_share_2013_2026", "mean"), changed=("share_quarters_changed", "mean"), geography=("geography", "first"), frequency=("frequency", "first")).round(2)
    print(summ.to_string())
    man = []
    for p in sorted(list((BACKEND_DIR / "data" / "e150" / "out").glob("*.parquet")) + list(RAW.glob("cpi_monthly.csv"))):
        man.append({"file": str(p.relative_to(BACKEND_DIR)), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    pd.DataFrame(man).to_csv(OUT / "data_manifest.csv", index=False, lineterminator="\n")
    # comparison on identical rows at 50 %
    Fe.LT = 0.0
    a = pd.read_csv(OUT / "oof_dev.csv")
    f = pd.read_csv(OUT / "oof_2021_retrospective.csv")
    pool = pd.concat([a, f], ignore_index=True)
    p9 = pd.concat([pd.read_csv(O149 / "oof_dev.csv"), pd.read_csv(O149 / "oof_2021.csv")], ignore_index=True)[["key", "survey", "lead", "Q-G", "mu_Q-G"]].rename(columns={"Q-G": "E149", "mu_Q-G": "mu_E149"})
    x = pool.merge(p9, on=["key", "survey", "lead"], how="left")
    p7 = pd.read_csv(O147 / "oof_2021.csv")[["key", "lead", "mu_G", "sigma_G"]]
    x = x.merge(p7.assign(survey="ENNS2021"), on=["key", "survey", "lead"], how="left")
    x["E147"], x["mu_E147"] = norm.cdf(x["mu_G"] / x["sigma_G"]), x["mu_G"]
    rng = np.random.default_rng(150)
    out = {}
    for lab, g_ in (("development_2018_2019", x[x["survey"] != "ENNS2021"]), ("retrospective_2021", x[x["survey"] == "ENNS2021"]), ("pool", x)):
        z = g_[g_["lead"] == 1].reset_index(drop=True)
        e = {"n": int(len(z)), "n_high": int(z["y_high"].sum()), "always_high": float(z["y_high"].mean())}
        for arm in ("A-H", "A-Hh", "A-G", "E149", "E147", "PERS", "DRIFT"):
            if z[arm].isna().all():
                continue
            d = z.dropna(subset=[arm])
            m = E7.metrics(d[arm], d["y_high"], d["q_true"])
            c_ = m["confusion"]
            low = c_["tn"] / (c_["tn"] + c_["fp"]) if c_["tn"] + c_["fp"] else None
            mu = d["mu_" + arm].values
            pct = 100 / (1 + np.exp(-mu))
            meas = 100 / (1 + np.exp(-d["y_true"].values))
            e[arm] = {"n": int(len(d)), "accuracy": m["accuracy"], "balanced_accuracy": (m["recall"] + low) / 2 if low is not None else None, "recall": m["recall"], "low_recall": low, "auc": m["auc"], "brier": m["brier"], "ece": m["ece"], "mae_points": float(np.mean(np.abs(pct - meas))), "calibration_slope": float(np.polyfit(mu, d["y_true"].values, 1)[0]), "spearman": float(spearmanr(mu, d["y_true"]).statistic)}
        d9 = z.dropna(subset=["E149"])
        e["A-H_minus_E149"] = E7.diff_ci(d9, "A-H", "E149", "q_true", rng)
        out[lab] = e
    out["province_rows_pool_L1"] = x[(x["lead"] == 1) & x["province"].isin(["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"])][["province", "survey", "p_true", "pct", "y_high", "mu_A-H", "A-H", "PERS", "E149"]].round(3).to_dict(orient="records")
    out["by_period_L1"] = {s: {"n": int(len(g2)), "accuracy": float(((g2["A-H"] >= 0.5).astype(int) == g2["y_high"]).mean()), "always_high": float(g2["y_high"].mean()), "persistence_accuracy": float(((g2["PERS"] >= 0.5).astype(int) == g2["y_high"]).mean()), "brier": E7.eb(g2["A-H"].values, g2["q_true"].values), "persistence_brier": E7.eb(g2["PERS"].values, g2["q_true"].values)} for s, g2 in x[x["lead"] == 1].groupby("survey")}
    out["by_island_L1"] = {s: {"n": int(len(g2)), "accuracy": float(((g2["A-H"] >= 0.5).astype(int) == g2["y_high"]).mean()), "always_high": float(g2["y_high"].mean())} for s, g2 in x[x["lead"] == 1].groupby("island")}
    (OUT / "comparison.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    f2 = lambda m: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items() if k != "n"}
    for lab in ("development_2018_2019", "retrospective_2021", "pool"):
        print(lab, out[lab]["n"], out[lab]["n_high"], round(out[lab]["always_high"], 3), "A-H-E149", round(out[lab]["A-H_minus_E149"]["diff"], 4), [round(v, 4) for v in out[lab]["A-H_minus_E149"]["ci95"]])
        for arm in ("A-H", "A-Hh", "A-G", "E149", "E147", "PERS", "DRIFT"):
            if arm in out[lab]:
                print("  ", arm, f2(out[lab][arm]))
    print(out["by_period_L1"], out["by_island_L1"])
    for r in out["province_rows_pool_L1"]:
        print(r)


if __name__ == "__main__":
    main()
