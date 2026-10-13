"""
E9 post-run analysis (DEVIATION, disclosed): the runner omitted the protocol's quarter-cluster bootstrap
(03_FROZEN_PROTOCOL.md section 6). This script computes exactly that method, plus per-quarter and
per-province tables, from the run's own scored_rows.csv. It reads nothing outside the run folder.
Usage (from the aligned backend root): python -B <this file> <run folder name>
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard  # noqa: E402

guard.install()

import json  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import metrics as M  # noqa: E402

run = guard.EXP / "runs" / sys.argv[1]
S = pd.read_csv(run / "scored_rows.csv")
S = S[S["common_evaluable"]]
tests = sorted(S["target_quarter"].unique())
sel = [q for q in tests if q <= "2024-Q4"]
fin = [q for q in tests if q > "2024-Q4"]

st = S[S["kind"] == "stress"].copy()
st["abs_err"] = (st["stress_pred"] - st["stress_true"]).abs()
perq = st.groupby(["arm", "target_quarter"])["abs_err"].mean().unstack()
perq.to_csv(run / "post_per_quarter_mae.csv")

S["correct"] = (S["classification"] == "HIGH") == S["event_true"]
acc_q = S.groupby(["arm", "kind", "target_quarter"])["correct"].mean().unstack()
acc_q.to_csv(run / "post_per_quarter_accuracy.csv")
true_q = S[S["arm"] == "B1_carry_forward"].groupby("target_quarter")["event_true"].agg(["sum", "size"])
true_q.columns = ["true_HIGH", "rows"]
true_q.to_csv(run / "post_true_class_by_quarter.csv")

prov = st.groupby(["arm", "province_code"])["abs_err"].mean().unstack()
prov.to_csv(run / "post_per_province_mae.csv")
spread = st.groupby(["arm", "target_quarter"]).apply(
    lambda g: pd.Series({"pred_spread": g["stress_pred"].max() - g["stress_pred"].min(),
                         "true_spread": g["stress_true"].max() - g["stress_true"].min()})).reset_index()
spread.to_csv(run / "post_province_spread.csv", index=False)

boot = {}
for arm in perq.index:
    if arm == "B1_carry_forward":
        continue
    for name, qs_ in (("all", tests), ("selection", sel), ("final", fin)):
        boot[f"{arm}|mae_minus_B1|{name}"] = M.cluster_bootstrap_diff(
            perq.loc[arm].to_dict(), perq.loc["B1_carry_forward"].to_dict(), qs_)
    for ref in ("B2_regional", "B3_eq3_rule"):
        if arm != ref:
            boot[f"{arm}|mae_minus_{ref}|all"] = M.cluster_bootstrap_diff(
                perq.loc[arm].to_dict(), perq.loc[ref].to_dict(), tests)
out = {"deviation": "bootstrap omitted by the runner; computed post hoc with the pre-specified method",
       "tests": tests, "selection": sel, "final": fin, "bootstrap": boot}
(run / "post_analysis.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(perq.round(2).to_string())
print(true_q.to_string())
for k, v in boot.items():
    if k.endswith("|all") or "|final" in k:
        print(k, round(v["mean_diff"], 3), [round(x, 3) for x in v["ci95"]], f"{v['quarters_a_lower']}/{v['quarters']} quarters lower")
