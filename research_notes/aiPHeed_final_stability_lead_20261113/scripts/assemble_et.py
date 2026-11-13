r"""Assembles FINAL-ET seed-level forecasts for Leads 1-3 in the layout of the standalone scorer: ENNS2021 rows from parts_et
(variant ET); ENNS2018/2019 rows = FINAL (identical by construction: s = gap there). Also checks that the FINAL-variant rows of
parts_et reproduce the FINAL fits of parts_lead (same fitted model). Run: python -I assemble_et.py"""
import glob, json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "parts_et_L13"
OUT.mkdir(exist_ok=True)
F = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts_lead" / "FINALL__*.csv"))])
E = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts_et" / "ET__*.csv"))])
K = ["key", "survey", "lead", "seed"]
chk = E[E.variant == "FINAL"][K + ["p"]].merge(F[K + ["p"]], on=K, suffixes=("_et_run", "_lead_run"))
rep = {"rows_compared": int(len(chk)), "max_abs_diff": float((chk.p_et_run - chk.p_lead_run).abs().max())}
et = E[E.variant == "ET"][K + ["p", "mu", "thr"]]
for (sv, L, sd), g in F[F.lead.isin([1, 2, 3])].groupby(["survey", "lead", "seed"]):
    x = g[K + ["p", "mu", "thr"]]
    if sv == "ENNS2021":
        x = et[(et.survey == sv) & (et.lead == L) & (et.seed == sd)]
        assert len(x) == 25
    x.to_csv(OUT / f"FINALET__{sv}__{L}__{sd}.csv", index=False, lineterminator="\n")
rep["files"] = len(list(OUT.glob("*.csv")))
json.dump(rep, open(HERE / "evidence" / "ET_same_model_check.json", "w"), indent=1)
print(rep)
