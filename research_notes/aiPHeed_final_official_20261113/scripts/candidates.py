r"""Candidate comparison under the thesis rules (Algorithm 3 mean fold accuracy, Algorithm 4 F1 >= 0.75 / AUC >= 0.80) from the stored
predictions of the candidates already evaluated on 11-13 (no new candidate is fitted or scored here):
  FINAL       : selected model (this study)
  FINAL-ETMIX : p = (p_g + p_s)/2 (protocol a365da1f), Leads 1-8
  FINAL-ET    : test gap := quarters since the latest released round (protocol c5e76bd5), Leads 1-3 stored
  FINAL-SA    : RATE multiplier capped at the longest training gap (PROTOCOL_SA 15202d27), Leads 1-3 stored
Run: python -I candidates.py"""
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, f1_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
rows = []
def score(name, d):           # d: survey, lead, y_high, p
    for L, g in d.groupby("lead"):
        fa = {s: float(((x.p >= .5) == (x.y_high == 1)).mean()) for s, x in g.groupby("survey")}
        yh = (g.p >= .5).astype(int)
        rows.append({"model": name, "lead": int(L), "n": len(g), **{f"acc_{s[-4:]}": round(v, 4) for s, v in fa.items()}, "mean_fold_accuracy": round(np.mean(list(fa.values())), 4),
                     "f1_high": round(f1_score(g.y_high, yh), 4), "auc": round(roc_auc_score(g.y_high, g.p), 4),
                     "recall_high": round(float(yh[g.y_high == 1].mean()), 4), "precision_high": round(float(g.y_high[yh == 1].mean()), 4) if yh.sum() else None,
                     "recall_2021": f"{int(((g.survey == 'ENNS2021') & (g.y_high == 1) & (yh == 1)).sum())}/{int(((g.survey == 'ENNS2021') & (g.y_high == 1)).sum())}",
                     "brier": round(float(((g.p - g.y_high) ** 2).mean()), 4)})
A = pd.read_csv(RN / "aiPHeed_final_etmix_20261113" / "evidence" / "ETMIX_rows_all_leads.csv")
score("FINAL", A.rename(columns={"FINAL": "p"})[["survey", "lead", "y_high", "p"]])
score("FINAL-ETMIX", A.rename(columns={"ETMIX": "p"})[["survey", "lead", "y_high", "p"]])
for name, f in (("FINAL-ET", RN / "aiPHeed_final_stability_lead_20261113" / "evidence" / "E_FINALET_province_rows.csv"),
                ("FINAL-SA", RN / "aiPHeed_final_standalone_20261113" / "evidence" / "E_FINALSA_province_rows.csv")):
    d = pd.read_csv(f); lc = [c for c in d.columns if c.isdigit()]
    score(name, d.melt(id_vars=["province", "survey", "y_high"], value_vars=lc, var_name="lead", value_name="p").assign(lead=lambda x: x.lead.astype(int)))
T = pd.DataFrame(rows)
out = []
for m, g in T.groupby("model", sort=False):
    mr, stop = 0, False
    for _, r in g.sort_values("lead").iterrows():
        if not stop and r.mean_fold_accuracy >= .75: mr = r.lead
        elif not stop: stop = True
    out.append({"model": m, "leads_available": f"1-{g.lead.max()}", "MRLT_algorithm3": mr if stop else f">={mr} (stored leads all pass)"})
T.to_csv(EV / "CAND_algorithm3_by_lead.csv", index=False, lineterminator="\n"); pd.DataFrame(out).to_csv(EV / "CAND_mrlt.csv", index=False, lineterminator="\n")
pd.set_option("display.width", 250); print(T.to_string(index=False)); print(pd.DataFrame(out).to_string(index=False))
