"""
Regional GRDP per person, constant 2018 prices, for 2024 and 2025 (ESTIMATED), so the live Setup H + class weights forecast has
the regional-economy input its release rule requires (year Y usable from Q3 of Y+1: the 2026-Q4 issue needs 2025 and 2024).

Sources (copied to data/hcw/raw/psa/):
  * psa_grdp_by_region_2000_2023.csv  PSA OpenSTAT 2B5BPGD1, total GRDP by region (older release, 17 regions)
  * psa_grdp_by_region_2018_2025.csv  PSA OpenSTAT 2B5BPGD1, total GRDP by region (current release, 18 regions with NIR)
  * data/e154/raw/regional_income_long.csv  PSA GRDP per person by region, 2000-2023 (unchanged; the model's series)

Method (per region, old 17-region definitions the model was trained on):
  per_person(Y) = per_person(Y-1) x total(Y) / total(Y-1) / exp(population growth(Y))
  * total growth 2024 and 2025 from the current release (same release for both years of each ratio)
  * population growth: the population implied by PSA's own series, total / per person, 2018-2023; its yearly log growth
    falls almost linearly, so 2024 and 2025 continue that linear trend (fitted on 2019-2023)
  * Western and Central Visayas: the current release moves Negros Occidental / Negros Oriental and Siquijor into the new
    Negros Island Region, so both old regions take the growth of the combined total (Western Visayas + Central Visayas + NIR)
Only 2024 and 2025 are added; 2000-2023 stay exactly as PSA published them per person.

    python -m app.hcw.grdp_extend   -> data/hcw/raw/grdp_pc_2024_2025_estimated.csv (+ provenance json)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.paths import BACKEND_DIR

RAW = BACKEND_DIR / "data" / "hcw" / "raw"
OLD = RAW / "psa" / "psa_grdp_by_region_2000_2023.csv"
NEW = RAW / "psa" / "psa_grdp_by_region_2018_2025.csv"
OUT = RAW / "grdp_pc_2024_2025_estimated.csv"
PC = BACKEND_DIR / "data" / "e154" / "raw" / "regional_income_long.csv"


def _tot(path: str) -> pd.DataFrame:
    t = pd.read_csv(path, sep=";", skiprows=2, encoding="utf-8-sig").dropna(subset=["Region"])
    t["Region"] = t["Region"].str.strip(". ")
    cols = {c: int(c[-4:]) for c in t.columns if c.startswith("At Constant 2018 Prices")}
    return t.set_index("Region")[list(cols)].rename(columns=cols).astype(float)


def build() -> pd.DataFrame:
    old, new = _tot(OLD), _tot(NEW)
    G = pd.read_csv(PC)
    pcr = G[(G["table"] == "grdp_pc") & G["type of valuation"].str.contains("Constant")]
    pc = pcr.pivot_table(index="year", columns="region", values="value")
    rows, prov = [], {}
    for col in pc.columns:
        name = col.strip(". ")
        if name not in old.index:
            raise SystemExit(f"no total GRDP for {name}")
        yrs = list(range(2018, 2024))
        pop = np.log(old.loc[name, yrs].values / pc.loc[yrs, col].values)          # implied population (log, arbitrary scale)
        g = np.diff(pop)                                                       # growth 2019..2023
        a, b = np.polyfit(np.arange(len(g)), g, 1)
        g24, g25 = a * len(g) + b, a * (len(g) + 1) + b
        if name in ("Region VI (Western Visayas)", "Region VII (Central Visayas)"):
            comb = new.loc[["Region VI (Western Visayas)", "Region VII (Central Visayas)", "Negros Island Region (NIR)"]].sum()
            r24, r25 = comb[2024] / comb[2023], comb[2025] / comb[2024]
            basis = "combined Western Visayas + Central Visayas + NIR total (NIR split in the current release)"
        else:
            r24, r25 = new.loc[name, 2024] / new.loc[name, 2023], new.loc[name, 2025] / new.loc[name, 2024]
            basis = "own total, current release"
        p23 = float(pc.loc[2023, col])
        p24 = p23 * r24 / np.exp(g24)
        p25 = p24 * r25 / np.exp(g25)
        for y, v in ((2024, p24), (2025, p25)):
            rows.append({"table": "grdp_pc", "region": col, "type of valuation": "At Constant 2018 Prices", "year": y, "value": round(float(v), 1),
                         "status": "estimated", "method": "total growth (PSA 2B5BPGD1 current release) / extrapolated population growth"})
        prov[name] = {"pc_2023_published": p23, "total_growth_2024": round(r24 - 1, 5), "total_growth_2025": round(r25 - 1, 5),
                      "pop_growth_2019_2023": [round(x, 5) for x in g], "pop_growth_2024_2025_extrapolated": [round(g24, 5), round(g25, 5)],
                      "pc_2024_est": round(p24, 1), "pc_2025_est": round(p25, 1), "growth_basis": basis}
    D = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    D.to_csv(OUT, index=False, lineterminator="\n")
    (RAW / "grdp_pc_2024_2025_provenance.json").write_text(json.dumps(prov, indent=1), newline="\n")
    print(D[D["region"].str.contains("CALABARZON|Philippines")].to_string(index=False))
    return D


if __name__ == "__main__":
    build()
