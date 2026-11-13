r"""PROTOCOL_OPT2 check R1 on the tables the engine actually receives (after run_qs.load merges), plus FINAL seed-168 probability
reproduction (rebuilt NOPAIR fit vs stored FINAL). Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=."""
import json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
sys.path.insert(0, str(HERE / "scripts"))
import build_lg as B
a = B.load(pickle.load(open(B.CACHE0 / "ENNS2021_1.pkl", "rb"))); b = B.load(pickle.load(open(B.CACHE / "NOPAIR_ENNS2021_1.pkl", "rb")))
out = {}
for j, part in enumerate(("tr", "te")):
    x, y = a[j], b[j]
    kk = ["key", "survey", "lead", "T"]
    x, y = x.sort_values(kk).reset_index(drop=True), y.sort_values(kk).reset_index(drop=True)
    num = [c for c in x.columns if c in y.columns and pd.api.types.is_numeric_dtype(x[c])]
    d = (x[num].astype(float) - y[num].astype(float)).abs()
    out[part] = {"max_abs_diff": float(np.nanmax(d.values)), "nan_mismatch": int((x[num].isna().values != y[num].isna().values).sum()),
                 "worst": d.max().sort_values(ascending=False).head(4).round(12).to_dict()}
s = pd.read_csv(RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd" / "FINAL__ENNS2021__1__168.csv")[["key", "p"]]
r = pd.read_csv(HERE / "parts" / "NOPAIR__ENNS2021__1__168.csv")[["key", "p"]]
m = s.merge(r, on="key", suffixes=("_stored", "_rebuilt"))
out["final_seed168_p_max_abs_diff"] = float((m.p_stored - m.p_rebuilt).abs().max()); out["n"] = len(m)
out["R1_PASS"] = bool(out["tr"]["max_abs_diff"] <= 1e-9 and out["te"]["max_abs_diff"] <= 1e-9 and out["final_seed168_p_max_abs_diff"] <= 1e-6)
json.dump(out, open(HERE / "evidence" / "LG_R1_after_load.json", "w"), indent=1); print(json.dumps(out, indent=1))
