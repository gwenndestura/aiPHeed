"""
E10 audit of E9: recomputes E9's reported numbers from E9's own outputs (no project data, no retraining).
Reads only: E9 run folder outputs, E9 runner code (imported), and the hash-pinned timing CSVs.
Usage (from the aligned backend root): python -B <this file>
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard  # noqa: E402

guard.install()

import json  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

E9 = guard.AL / "experiments" / "2026-10-12_E9_S1_safe_training"
RUN = E9 / "runs" / "20261012T140816Z"
spec = importlib.util.spec_from_file_location("e9_metrics", E9 / "runner" / "metrics.py")
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
sys.path.insert(0, str(guard.AL))
import scripts.supplementary.devprotocol_rule_l as D  # noqa: E402

out = {}
S = pd.read_csv(RUN / "scored_rows.csv")
metrics = json.loads((RUN / "metrics.json").read_text(encoding="utf-8"))
post = json.loads((RUN / "post_analysis.json").read_text(encoding="utf-8"))
sel = json.loads((RUN / "selection.json").read_text(encoding="utf-8"))
man = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
frame = pd.read_csv(RUN / "input_frame.csv")

# 1. identical rows, quarters and targets for every arm
C = S[S["common_evaluable"]]
rows_per_arm = C.groupby(["arm", "kind"]).apply(lambda g: tuple(sorted(zip(g["target_quarter"], g["province_code"]))))
out["same_rows_all_arms"] = bool(rows_per_arm.nunique() == 1)
out["rows_per_arm"] = int(C.groupby(["arm", "kind"]).size().iloc[0])
truth = C.groupby(["target_quarter", "province_code"])["stress_true"].nunique()
out["single_truth_per_row"] = bool((truth == 1).all())
out["tests"] = sorted(C["target_quarter"].unique())
ev = C.drop_duplicates(["target_quarter", "province_code"])
out["true_HIGH"], out["true_LOW"] = int(ev["event_true"].sum()), int((~ev["event_true"]).sum())
out["LOW_rows"] = ev[~ev["event_true"]][["target_quarter", "province_code"]].values.tolist()

# 2. recompute stress MAE and classification for each arm/period vs metrics.json
rec = {}
for (arm, kind), g in C.groupby(["arm", "kind"]):
    for pname, qs in metrics["periods"].items():
        h = g[g["target_quarter"].isin(qs)]
        r = M.classification(h["event_true"].values, (h["classification"] == "HIGH").values)
        rep = metrics["arms"][f"{arm}|{kind}"][pname]
        ok = abs((r["accuracy"] or 0) - (rep["classification"]["accuracy"] or 0)) < 1e-12
        if kind == "stress":
            mae = float((h["stress_pred"] - h["stress_true"]).abs().mean())
            ok = ok and abs(mae - rep["stress"]["mae"]) < 1e-9
        if kind == "probability":
            ok = ok and abs(M.brier(h["event_true"].values, h["probability"].values) - rep["brier"]) < 1e-12
        rec[f"{arm}|{kind}|{pname}"] = ok
out["metrics_reproduced"] = all(rec.values())
out["metrics_mismatches"] = [k for k, v in rec.items() if not v]

# 3. bootstrap reproducibility (same function, seed and quarter order)
st = C[C["kind"] == "stress"].assign(err=lambda d: (d["stress_pred"] - d["stress_true"]).abs())
perq = st.groupby(["arm", "target_quarter"])["err"].mean().unstack()
tests, sel_q = post["tests"], post["selection"]
boot_ok = {}
for key, val in post["bootstrap"].items():
    arm, comp, period = key.split("|")
    ref = comp.replace("mae_minus_", "")
    ref = "B1_carry_forward" if ref == "B1" else ref
    qs = {"all": tests, "selection": sel_q, "final": post["final"]}[period]
    r = M.cluster_bootstrap_diff(perq.loc[arm].to_dict(), perq.loc[ref].to_dict(), qs)
    boot_ok[key] = (abs(r["mean_diff"] - val["mean_diff"]) < 1e-12 and
                    all(abs(a - b) < 1e-12 for a, b in zip(r["ci95"], val["ci95"])))
out["bootstrap_reproduced"] = all(boot_ok.values())
out["bootstrap_entries"] = len(boot_ok)
# sensitivity of the interval to the bootstrap seed (shows instability with 7 clusters)
alt = [M.cluster_bootstrap_diff(perq.loc["M1_core"].to_dict(), perq.loc["B1_carry_forward"].to_dict(), tests, seed=s)["ci95"]
       for s in (1, 7, 123, 2024)]
out["M1_minus_B1_ci95_other_seeds"] = alt
# exact (exhaustive) sign information: per-quarter differences
d = (perq.loc["M1_core"] - perq.loc["B1_carry_forward"]).reindex(tests)
out["M1_minus_B1_per_quarter"] = d.round(4).to_dict()
for ref in ("B2_regional", "B3_eq3_rule"):
    out[f"M1_minus_{ref}_per_quarter"] = (perq.loc["M1_core"] - perq.loc[ref]).reindex(tests).round(4).to_dict()
out["B3_minus_B1_per_quarter"] = (perq.loc["B3_eq3_rule"] - perq.loc["B1_carry_forward"]).reindex(tests).round(4).to_dict()
# exact sign-flip test of the mean per-quarter difference (7 quarters -> 128 sign patterns), descriptive only
def signflip_p(x):
    x = np.asarray(x, float); obs = abs(x.mean()); n = len(x)
    pats = np.array([[1 if (k >> i) & 1 else -1 for i in range(n)] for k in range(2 ** n)])
    return float((np.abs((pats * x).mean(axis=1)) >= obs - 1e-12).mean())
out["signflip_p_two_sided"] = {
    "M1_vs_B1": signflip_p(d.values),
    "M1_vs_B2": signflip_p((perq.loc["M1_core"] - perq.loc["B2_regional"]).reindex(tests).values),
    "M1_vs_B3": signflip_p((perq.loc["M1_core"] - perq.loc["B3_eq3_rule"]).reindex(tests).values),
    "B3_vs_B1": signflip_p((perq.loc["B3_eq3_rule"] - perq.loc["B1_carry_forward"]).reindex(tests).values),
    "B2_vs_B1": signflip_p((perq.loc["B2_regional"] - perq.loc["B1_carry_forward"]).reindex(tests).values),
    "note": "post hoc, not prespecified; 7 quarters; descriptive"}

# 4. feature availability: every non-null input dated strictly before its origin
date_cols = {"sws_published": ["sws_hunger", "sws_change"], "anchor_published": ["last_published_stress"],
             "prov_cpi_published": ["cpi_rel", "cpi_rel_lag1", "food_cpi_yoy", "food_cpi_yoy_lag1", "cpi_dev"],
             "reg_cpi_published": ["headline_cpi", "food_minus_headline_yoy", "food_minus_headline_yoy_lag1"],
             "unemp_available": ["unemployment_rate"]}
viol = []
for dc, feats in date_cols.items():
    for _, r in frame.iterrows():
        if any(pd.notna(r[f]) for f in feats) and (pd.isna(r[dc]) or pd.Timestamp(r[dc]) >= pd.Timestamp(r["origin"])):
            viol.append({"target": r["target_quarter"], "province": r["province_code"], "date_col": dc})
out["availability_violations"] = viol
out["availability_rows_checked"] = int(len(frame))
out["date_types_in_test_rows"] = {c: sorted(frame[frame["target_quarter"].isin(tests)][c].dropna().unique().tolist())
                                  for c in ("sws_date_type", "anchor_date_type", "prov_cpi_date_type", "reg_cpi_date_type", "unemp_date_type")}

# 5. tau0 quarters all published before the first test origin; training labels per fold before origin
pub = lambda q: D.label_published(q, "development")[0]
out["tau0_quarters_published_before_2023_10_01"] = all(pub(q) < pd.Timestamp("2023-10-01") for q in man["tau0_quarters"])
folds = json.loads((RUN / "folds.json").read_text(encoding="utf-8"))
out["fold_labels_published_before_origin"] = all(
    pub(q) < pd.Timestamp(f["target"][:4] + "-" + str(3 * (int(f["target"][-1]) - 1) + 1).zfill(2) + "-01")
    for f in folds for q in f["train_quarters"])
out["train_quarters_per_fold"] = {f["target"]: f["n_train_quarters"] for f in folds}

# 6. selection recomputed from selection quarters only
sq = sel["selection_quarters"]
mae_sel = st[st["target_quarter"].isin(sq)].groupby("arm")["err"].apply(
    lambda e: e.groupby(st.loc[e.index, "target_quarter"]).mean().mean()).to_dict()
out["selection_mae_reproduced"] = all(abs(mae_sel[a] - v) < 1e-9 for a, v in sel["selection_mae"].items())
out["selection_used_only"] = sq

(Path(guard.EXP) / "audit_e9_results.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
for k, v in out.items():
    print(k, ":", v)
