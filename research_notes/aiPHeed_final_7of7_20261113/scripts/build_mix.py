r"""FINAL-MIX seed-level forecasts (protocol sha a365da1f) from existing fits only: p = (p_FINAL + p_FINAL-ET) / 2 where FINAL-ET
differs (ENNS2021 Leads 1-6), else FINAL. Writes parts_mix/FINALMIX__<survey>__<lead>__<seed>.csv for Leads 1-8. Run: python -I build_mix.py"""
import glob
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parents[1]; ST = HERE.parent / "aiPHeed_final_stability_lead_20261113"
OUT = HERE / "parts_mix"; OUT.mkdir(exist_ok=True)
K = ["key", "survey", "lead", "seed"]
F = pd.concat([pd.read_csv(f) for f in glob.glob(str(ST / "parts_lead" / "FINALL__*.csv"))])
E = pd.concat([pd.read_csv(f) for f in glob.glob(str(ST / "parts_et" / "ET__*.csv"))])
E = E[E.variant == "ET"][K + ["p"]].rename(columns={"p": "p_et"})
M = F.merge(E, on=K, how="left")
M["p_final"] = M["p"]
M["p"] = M[["p_final", "p_et"]].mean(axis=1)          # p_et missing -> FINAL itself (s = g there)
for (sv, L, sd), g in M.groupby(["survey", "lead", "seed"]):
    g[K + ["p", "p_final", "p_et", "mu", "thr", "origin", "gap_q"]].to_csv(OUT / f"FINALMIX__{sv}__{L}__{sd}.csv", index=False, lineterminator="\n")
print(len(list(OUT.glob("*.csv"))), "files;", int(M.p_et.notna().sum()), "rows differ from FINAL")
