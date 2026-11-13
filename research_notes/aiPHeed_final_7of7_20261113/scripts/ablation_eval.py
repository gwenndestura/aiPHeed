r"""Scores the group ablations (ablation.py) and builds the 77-input inventory. Outcome-free measures first (probability change, class
flips, gain share, geography), then performance changes on the reused rows (descriptive; nothing is selected for the model).
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python ablation_eval.py"""
import glob, json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; ST = RN / "aiPHeed_final_stability_lead_20261113"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ablation import GROUPS, group            # noqa: E402
from app.hcw import engine as H               # noqa: E402
EV = HERE / "evidence"
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[["key", "survey", "lead", "y_high"]]
CACHE = RN / "aiPHeed_objective_completion_20261111" / "cache"


def m(g):
    y, p = g.y_high.values, g.p.values
    h = p >= .5
    rec = (h & (y == 1)).sum() / max(1, (y == 1).sum()); spec = (~h & (y == 0)).sum() / max(1, (y == 0).sum())
    return {"BA": 0.5 * (rec + spec), "recall": rec, "precision": (h & (y == 1)).sum() / max(1, h.sum()),
            "auroc": roc_auc_score(y, p) if 0 < y.sum() < len(y) else np.nan, "brier": float(np.mean((p - y) ** 2))}


# (a) withholding at every fold-lead
W = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "ablation" / "WITHHOLD__*.csv"))]).merge(LAB, on=["key", "survey", "lead"])
base = W[W.variant == "none"].set_index(["key", "survey", "lead"])
rows = []
for v, g in W[W.variant != "none"].groupby("variant"):
    gi = g.set_index(["key", "survey", "lead"])
    d = (gi.p - base.p.reindex(gi.index))
    fl = (gi.p >= .5) != (base.p.reindex(gi.index) >= .5)
    per_lead = {int(L): round(float(x.abs().mean()), 4) for L, x in d.groupby(level="lead")}
    per_round = {s: int(x.sum()) for s, x in fl.groupby(level="survey")}
    dBA = {int(L): round(m(gg.reset_index())["BA"] - m(base.loc[gg.index].reset_index())["BA"], 3) for L, gg in gi.groupby(level="lead")}
    rows.append({"group": v[3:], "mean_abs_dp_all": round(float(d.abs().mean()), 4), "max_abs_dp": round(float(d.abs().max()), 3),
                 "flips_all_leads(of 576)": int(fl.sum()), "flips_by_round": per_round, "mean_abs_dp_by_lead": per_lead, "delta_BA_by_lead": dBA,
                 "leads_with_any_flip": int(sum(1 for L, x in fl.groupby(level="lead") if x.sum() > 0))})
WA = pd.DataFrame(rows).sort_values("mean_abs_dp_all", ascending=False)
WA.to_csv(EV / "G1_withhold_ablation.csv", index=False)
# (b) retraining at Lead 1
B = pd.concat([pd.read_csv(f) for f in glob.glob(str(ST / "parts_lead" / "FINALL__*__1__168.csv"))])[["key", "survey", "lead", "p"]].merge(LAB, on=["key", "survey", "lead"])
R = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "ablation" / "RETRAIN__*.csv"))]).merge(LAB, on=["key", "survey", "lead"])
b0 = m(B)
rr = []
for v, g in R.groupby("variant"):
    x = g.merge(B[["key", "survey", "p"]], on=["key", "survey"], suffixes=("", "_base"))
    mm = m(g)
    rr.append({"retrained_without": v.replace("retrain_without_", ""), **{f"d_{k}": round(mm[k] - b0[k], 3) for k in mm},
               "flips_vs_full": int(((x.p >= .5) != (x.p_base >= .5)).sum()), "mean_abs_dp": round(float((x.p - x.p_base).abs().mean()), 3),
               "by_round_dBA": {s: round(m(gg)["BA"] - m(B[B.survey == s])["BA"], 3) for s, gg in g.groupby("survey")}})
RA = pd.DataFrame(rr).sort_values("d_BA")
RA.to_csv(EV / "G2_retrain_ablation_L1.csv", index=False)
# (c) gain share and selection by meaning-based group, from the 110 FINAL fits
J = [json.load(open(f)) for f in glob.glob(str(ST / "features_lead" / "FINALL__*.json"))]
base_name = lambda c: c[3:] if c.startswith("mi_") else c
gs = []
for d in J:
    tot = sum(d["gain"].values()) or 1
    o = {g: 0.0 for g in GROUPS + ("timing",)}
    for c, v in d["gain"].items():
        o[group(base_name(c))] += v / tot
    gs.append({"survey": d["survey"], "lead": d["lead"], "seed": d["seed"], **o})
GS = pd.DataFrame(gs)
gain_tab = GS.groupby("lead")[list(GROUPS)].mean().round(3)
gain_round = GS[GS.lead == 1].groupby("survey")[list(GROUPS)].mean().round(3)
# (d) 77-input inventory with empirical geography (distinct values within an origin quarter, training rows of the 2021 L1 fold)
o = pickle.load(open(CACHE / "ENNS2021_1.pkl", "rb"))
tr = o["tr"]
import run_qs  # noqa: E402  (path set by ablation import? ensure)
FS = H.feature_sets()
allc = sorted({c for v in FS.values() for c in v})
sel = {}
for d in J:
    for c in d["selected"]:
        sel[base_name(c)] = sel.get(base_name(c), 0) + (0 if c.startswith("mi_") else 1)
gain_c = {}
for d in J:
    tot = sum(d["gain"].values()) or 1
    for c, v in d["gain"].items():
        gain_c[base_name(c)] = gain_c.get(base_name(c), 0) + v / tot / len(J)
inv = []
for c in allc:
    geo = "n/a"
    if c in tr and tr[c].notna().any():
        per_q = tr.groupby("i").apply(lambda x: (x[c].nunique(), x.groupby("region")[c].nunique().max(), x["region"].nunique()), include_groups=False)
        nu = max(v[0] for v in per_q)
        within_reg = max(v[1] for v in per_q)
        geo = "national (one value per quarter)" if nu <= 1 else ("regional (constant within region)" if within_reg <= 1 else "provincial / area-varying")
    inv.append({"input": c, "group": group(c), "feature_sets": ";".join(k for k, v in FS.items() if c in v), "empirical_geography": geo,
                "missing_share_train_2021L1": round(float(tr[c].isna().mean()), 3) if c in tr else None,
                "times_selected_of_110": sel.get(c, 0), "mean_gain_share": round(gain_c.get(c, 0.0), 4)})
INV = pd.DataFrame(inv)
INV.to_csv(EV / "G3_input_inventory.csv", index=False)
json.dump({"withhold": WA.to_dict("records"), "retrain_L1": RA.to_dict("records"), "gain_by_lead": gain_tab.to_dict("index"),
           "gain_L1_by_round": gain_round.to_dict("index"), "baseline_L1_seed168": {k: round(v, 3) for k, v in b0.items()}},
          open(EV / "G_group_evidence.json", "w"), indent=1, default=str)
pd.set_option("display.width", 250)
print(WA.drop(columns=["mean_abs_dp_by_lead"]).to_string(index=False)); print(RA.to_string(index=False)); print(gain_tab.to_string()); print(gain_round.to_string())
print(INV.groupby(["group", "empirical_geography"]).size().to_string())
