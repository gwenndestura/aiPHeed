"""E111 Addendum 1 audit: E109/E110 p-values recomputed with Bartlett-weighted Newey-West variance."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e111_lib as G  # noqa: E402

E, F, H9, np, pd = G.E, G.F, G.H9, G.np, G.pd
out = {"E110": {}, "E109": {}}
e110 = HERE.parents[1] / "E110_Hunger_Generalization" / "out"
for k in (1, 2, 3, 4):
    df = pd.read_csv(e110 / f"panel_lead{k}.csv")
    out["E110"][str(k)] = {m: {"truncated": G._E110_DM(F.quarter_diff(df, m).to_numpy(), k).get("p"),
                               "newey_west": G.dm_nw(F.quarter_diff(df, m).to_numpy(), k).get("p")} for m in ("LLR", "COMB")}
e109 = HERE.parents[1] / "E109_Hunger_Forecasting" / "out"
for k in (1, 2, 3, 4):
    df = pd.read_csv(e109 / f"predictions_lead{k}.csv")
    d = (df["LGBM"] - df["y"]).abs() - (df["RW"] - df["y"]).abs()
    out["E109"][str(k)] = {"LGBM_vs_RW": {"truncated": H9.dm_test((df["LGBM"] - df["y"]).to_numpy(), (df["RW"] - df["y"]).to_numpy(), k).get("p"),
                                          "newey_west": G.dm_nw(d.to_numpy(), k).get("p")}}
G.write_json(HERE.parent / "out" / "audit_dm_kernel.json", out)
print(json.dumps(out, indent=1))
