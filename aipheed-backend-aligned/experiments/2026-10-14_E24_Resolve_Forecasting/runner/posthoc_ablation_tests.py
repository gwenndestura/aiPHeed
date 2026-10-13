"""DESCRIPTIVE ONLY: paired tests for ablation arms noticed AFTER the frozen run (never used to select a model).
Usage: python -B runner/posthoc_ablation_tests.py <E24 run>"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard; guard.install()
import pandas as pd
import run_e24 as RE
run = sys.argv[1]
out = {}
for t, arms in (("T1", ["ABL_lgbm_P", "ABL_lgbm_GP", "ABL_lr_P"]), ("T2", ["ABL_lr_P", "ABL_lr_NP"])):
    P = pd.read_csv(guard.EXP / "runs" / run / f"predictions_{t}.csv", dtype={"province_code": str})
    d = P[P["lead"] == 1]
    out[t] = {a: RE.compare(d, a, "B1_naive_persistence") for a in arms}
(guard.EXP / "runs" / run / "posthoc_ablation_tests.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for t, v in out.items():
    for a, x in v.items():
        print(t, a, {k: (round(y, 3) if isinstance(y, float) else y) for k, y in x.items()})
