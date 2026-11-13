r"""Five-trigger-group audit of FINAL: candidate inputs (77) vs inputs actually selected per fit vs LightGBM gain share, per group,
from features_lead/*.json (written by run_lead.py; selection and gain are training-only). MIND flags (mi_<input>) count with
their input's group. Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python trigger_audit.py"""
import glob, json, sys
from collections import defaultdict
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent / "aiPHeed_final_standalone_20261113" / "scripts"))
from rerun_final import group_of                 # noqa: E402
from app.hcw import engine as H                  # noqa: E402

BRIEF = {"market": "1 Market and prices", "climate": "2 Climate stress", "employment": "3 Employment", "ofw_remittance": "4 OFW remittances",
         "poverty": "5 Poverty and social vulnerability", "agri_fish": "not a dashboard group (agriculture/fish production)",
         "news_aggregate": "not a dashboard group (cross-topic news indices)", "timing": "not a dashboard group (forecast timing)"}
base = lambda c: c[3:] if c.startswith("mi_") else c
FS = H.feature_sets()
allc = sorted({c for v in FS.values() for c in v})
cand = defaultdict(list)
for c in allc:
    cand[group_of(c)].append(c)
rows, sel_count, gain = [], defaultdict(lambda: defaultdict(int)), []
J = [json.load(open(f)) for f in glob.glob(str(HERE / "features_lead" / "FINALL__*.json"))]
for d in J:
    tot = sum(d["gain"].values()) or 1.0
    g = defaultdict(float)
    for c, v in d["gain"].items():
        g[group_of(base(c))] += v / tot
    for c in d["selected"]:
        sel_count[group_of(base(c))][base(c)] += 1
    gain.append({"survey": d["survey"], "lead": d["lead"], "seed": d["seed"], "n_selected": len(d["selected"]),
                 **{f"gain_{k}": round(g.get(k, 0.0), 4) for k in BRIEF}, **{f"n_{k}": sum(1 for c in d["selected"] if group_of(base(c)) == k) for k in BRIEF}})
G = pd.DataFrame(gain)
G.to_csv(HERE / "evidence" / "TRIG_gain_share_per_fit.csv", index=False)
nf = len(J)
for k, lab in BRIEF.items():
    sel = sel_count.get(k, {})
    rows.append({"group": lab, "candidate_inputs": len(cand.get(k, [])), "candidate_list": ";".join(cand.get(k, [])),
                 "inputs_ever_selected": len(sel), "selected_list(times_selected/of_fits)": ";".join(f"{c}({n}/{nf})" for c, n in sorted(sel.items(), key=lambda x: -x[1])),
                 "mean_gain_share_all_fits": round(float(G[f"gain_{k}"].mean()), 4) if nf else None,
                 "mean_gain_share_lead1": round(float(G[G.lead == 1][f"gain_{k}"].mean()), 4) if nf else None,
                 "fits_where_group_selected": int((G[f"n_{k}"] > 0).sum())})
A = pd.DataFrame(rows)
A.to_csv(HERE / "evidence" / "TRIG_group_audit.csv", index=False)
print("fits:", nf)
print(A.drop(columns=["candidate_list", "selected_list(times_selected/of_fits)"]).to_string(index=False))
print(G.groupby("lead")[[f"gain_{k}" for k in BRIEF]].mean().round(3).to_string())
