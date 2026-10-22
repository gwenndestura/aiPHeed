"""E99-F Q4-Q5 (PROTOCOL.md): provincial measured data from local PSA files (FIES PUF 2021/2023, subsistence incidence)
versus FIRI v2 provincial means; the Lucena poverty substitute against the PSA SAE workbook, and its ranking effect.
Report-only. Run from backend/."""
from __future__ import annotations

import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
E99 = HERE.parent
EXP = E99.parent
DL = Path.home() / "Downloads"
PUF = {2021: (DL / "PHL-PSA-FIES-2021-V1-PUF.zip", "FIES PUF 2021 Volume 1 - HHLD_SUMMARY.CSV"),
       2023: (DL / "PHL-PSA-FIES-2023-V1-PUF" / "FIES PUF 2023 Volume1.CSV", None)}
SAE = DL / "2018 - 2021 SAE_with PSGC_noHUC.xlsx"
PROV = {10: "PH040500000", 21: "PH040100000", 34: "PH040200000", 56: "PH040300000", 58: "PH040400000"}
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal", "PH040500000": "Batangas"}
EXPERIENCE = re.compile(r"WORRI|HUNGR|SKIP|RAN_?OUT|FIES_|INSECUR|ATE_?LESS|WHOLE_?DAY", re.I)


def read_puf(year: int) -> pd.DataFrame:
    path, member = PUF[year]
    cols = ["W_REGN", "W_PROV", "FOOD", "TOTEX", "RFACT"]
    if member:
        with zipfile.ZipFile(path) as z, z.open(member) as f:
            hdr = pd.read_csv(f, nrows=0).columns
        with zipfile.ZipFile(path) as z, z.open(member) as f:
            df = pd.read_csv(f, usecols=cols, dtype=str)
    else:
        hdr = pd.read_csv(path, nrows=0).columns
        df = pd.read_csv(path, usecols=cols, dtype=str)
    df = df[df["W_REGN"].astype(int) == 4].copy()
    for c in ("FOOD", "TOTEX", "RFACT"):
        df[c] = df[c].astype(float)
    df["prov"] = df["W_PROV"].astype(int).map(PROV)
    df.attrs["experience_columns"] = [c for c in hdr if EXPERIENCE.search(c)]
    df.attrs["n_columns"] = len(hdr)
    return df


def food_share(df: pd.DataFrame) -> dict:
    d = df[df["TOTEX"] > 0].assign(s=lambda x: x["FOOD"] / x["TOTEX"])
    out = {}
    for p, g in d.groupby("prov"):
        w = g["RFACT"]
        out[p] = {"households": len(g), "weighted_mean_food_share": float(np.average(g["s"], weights=w)),
                  "weighted_share_hh_food_share_ge_0.65": float(np.average(g["s"] >= 0.65, weights=w))}
    return out


def sae_rows() -> dict:
    z = zipfile.ZipFile(SAE)
    ss = [''.join(re.findall(r'<t[^>]*>(.*?)</t>', s, flags=re.S))
          for s in re.findall(r'<si>(.*?)</si>', z.read('xl/sharedStrings.xml').decode('utf8'), flags=re.S)]
    names = re.findall(r'<sheet [^>]*name="([^"]+)"', z.read('xl/workbook.xml').decode('utf8'))
    out = {}
    for i, nm in enumerate(names, start=1):
        x = z.read(f'xl/worksheets/sheet{i}.xml').decode('utf8')
        rows = []
        for r in re.findall(r'<row[^>]*>(.*?)</row>', x, flags=re.S):
            cells = re.findall(r'<c r="([A-Z]+)\d+"([^>]*)>(?:<f>.*?</f>)?(?:<v>(.*?)</v>)?', r, flags=re.S)
            rows.append({col: (ss[int(v)] if 't="s"' in a and v else v) for col, a, v in cells})
        out[nm] = rows
    return out


def lucena_check() -> dict:
    wb = sae_rows()
    hits = {}
    for nm, rows in wb.items():
        for r in rows:
            if str(r.get("A", "")).strip() == "45624" or "LUCENA CITY" in str(r.get("C", "")).upper():
                hits[nm] = {k: r.get(k) for k in "ABCDEFG"}
    in_2021 = any("LUCENA" in str(r.get("C", "")).upper() and "NEW" not in str(r.get("C", "")).upper()
                  for r in wb["2018-2021_NoHUC"])
    own2018 = float(hits["2018"]["D"])
    v = pd.read_csv("data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
    served = float(v.loc[v["lgu_code"] == "045624000", "poverty_value_used"].iloc[0])
    quezon_mean = float(v.loc[(v["province"] == "Quezon") & v["poverty_lgu_estimate"].notna(), "poverty_lgu_estimate"].mean())
    sys.path.insert(0, str(EXP / "E97_Validation_Completion" / "runner"))
    import lgu_sensitivity as LS  # noqa: E402
    v["density"] = v["population_2024"] / v["land_area_km2"]
    r_served = LS.index(v, 0.6).groupby(v["province"]).rank(ascending=False, method="min")
    v2 = v.copy()
    v2.loc[v2["lgu_code"] == "045624000", "poverty_value_used"] = own2018
    r_own = LS.index(v2, 0.6).groupby(v2["province"]).rank(ascending=False, method="min")
    q = v["province"] == "Quezon"
    luc = v["lgu_code"] == "045624000"
    from app.ml.inference import firi as FI
    return {"workbook_hits": hits, "lucena_in_2021_table": in_2021, "served_substitute": served,
            "lucena_own_sae": {s: (float(h["D"]) if h.get("D") not in (None, "") else None) for s, h in hits.items()},
            "quezon_mean_of_municipal_2021_estimates": quezon_mean,
            "substitute_vs_own_2018_ratio": served / own2018,
            "rank_in_quezon": {"served": int(r_served[luc].iloc[0]), "with_own_2018_sae": int(r_own[luc].iloc[0])},
            "quezon_rank_spearman_served_vs_own": float(spearmanr(r_served[q], r_own[q]).statistic),
            "quezon_max_rank_shift": int((r_served[q] - r_own[q]).abs().max()),
            "firi_v1_uses_substitute": False,
            "firi_v1_note": "firi.vulnerability() averages poverty_lgu_estimate (Lucena NaN is skipped), so V1 and FIRI are unaffected",
            "firi_v1_quezon": FI.vulnerability()["PH040300000"]}


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = E99 / "runs" / f"{stamp}_provincial"
    o.mkdir(parents=True, exist_ok=True)
    puf = {}
    for y in (2021, 2023):
        df = read_puf(y)
        puf[y] = {"columns": df.attrs["n_columns"], "food_insecurity_experience_columns": df.attrs["experience_columns"],
                  "calabarzon_households": len(df), "by_province": food_share(df)}
    sub = pd.read_csv("data/inputs/psa_subsistence_population_2021_2023.csv", dtype={"province_code": str})
    h = pd.read_csv("data/thesis/firi2_history.csv", dtype={"province_code": str})
    f23 = h[(h["kind"] == "backtest") & h["target"].str.startswith("2023")].groupby("province_code")["FIRI"].mean()
    rows = []
    for p in NAMES:
        s = sub[(sub["province_code"] == p) & (sub["reference_year"] == 2023)].iloc[0]
        rows.append({"province": NAMES[p], "firi_2023_mean": float(f23[p]),
                     "food_share_2023": puf[2023]["by_province"][p]["weighted_mean_food_share"],
                     "food_share_2021": puf[2021]["by_province"][p]["weighted_mean_food_share"],
                     "subsistence_2023": float(s["subsistence_incidence_pct"]), "subsistence_2023_cv": float(s["cv_pct"])})
    T = pd.DataFrame(rows)
    res = {"stamp": stamp, "protocol_sha256": (E99 / "PROTOCOL.sha256").read_text().split()[0],
           "puf": puf, "provincial_table": T.round(4).to_dict(orient="records"),
           "spearman_n5": {"firi_vs_food_share_2023": float(spearmanr(T["firi_2023_mean"], T["food_share_2023"]).statistic),
                           "firi_vs_subsistence_2023": float(spearmanr(T["firi_2023_mean"], T["subsistence_2023"]).statistic)},
           "reading": ("No food-insecurity-experience module in either PUF: no provincial food-insecurity outcome can be "
                       "derived. Food share is an economic-access indicator (annual, 2 points); subsistence incidence has "
                       "CV 25-62%. With n = 5 these correlations are descriptive only; V1 is built from PSA SAE poverty, "
                       "itself modelled from FIES, so agreement is partly circular."),
           "lucena": lucena_check()}
    (o / "provincial_lucena.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("puf",)}, indent=1, default=float)[:4000])
    print({y: (v["columns"], v["food_insecurity_experience_columns"], v["calabarzon_households"]) for y, v in puf.items()})
    print(o)


if __name__ == "__main__":
    main()
