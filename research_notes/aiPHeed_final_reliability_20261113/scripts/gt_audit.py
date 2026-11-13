r"""Deliverable 1: ground-truth audit of the provincial HFIAS labels FINAL is trained and evaluated on.
Reads only the published provincial estimates already on disk (no household microdata exist locally or publicly for this network).
Run from C:\Users\admin\aipheed_e145\backend with PYTHONPATH=. :  python -I <this file>   (writes ../evidence/GT_*.csv/json)"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm

sys.path.insert(0, ".")
from app.e151 import prov as Pv            # noqa: E402
from app.e141 import panel as P141         # noqa: E402
from app.e137 import outcomes as O         # noqa: E402
from app.e147 import RAW as R147           # noqa: E402

EV = Path(__file__).resolve().parents[1] / "evidence"
LAB = pd.read_csv("data/e158/out/oof.csv")
L1 = LAB[LAB.lead == 1]

# all published provincial HFIAS rows (2013-2019 via E141 panel; 2021 via the FNRI Heat Map export)
allr = P141.outcomes("mod_sev")
hm = pd.DataFrame([json.loads(x) for x in open(R147 / "heatmap_provincial.jsonl", encoding="utf-8")])
hm["pct"] = pd.to_numeric(hm["fs_percentage"], errors="coerce")
rows = []
for yr in ("2013", "2015", "2018", "2019", "2021"):
    h = hm[hm.actual_year == yr]
    rows.append({"round": yr, "heatmap_areas_any_level": int(h[h.fs_survey_category == "Food Insecure Households"].province_name.nunique()),
                 "heatmap_areas_mod_or_sev": int(h[h.fs_survey_category.isin(["Moderately Food Insecure Households", "Severely Food Insecure Households"])].province_name.nunique())})
HM = pd.DataFrame(rows)

sv = {"2013": "NNS2013", "2015": "FNRI2015", "2018": "ENNS2018", "2019": "ENNS2019", "2021": "ENNS2021"}
t21 = Pv.target_rows(with_2021=True)
out = []
for yr, s in sv.items():
    d = t21[t21.survey == s] if s != "NNS2013" else allr[allr.survey == s]
    ev = L1[L1.survey == s]
    p = d["p"].astype(float); se = d["se_p"].astype(float)
    amb = (np.abs(p - 50) < 1.96 * se)
    pm = norm.cdf(-np.abs(p - 50) / se)            # probability the published HIGH/LOW side is wrong because of sampling error
    out.append({"round": s, "instrument": "HFIAS 9 items, 30-day recall (FNRI scoring)",
                "provinces_with_mod_sev_label": int(d.key.nunique()),
                "HIGH_(>=50%)": int((p >= 50).sum()), "median_pct": round(float(p.median()), 1),
                "se_source": {"NNS2013": "not printed; approximated sqrt(deff 3.17 p(1-p)/n) (flagged)",
                              "FNRI2015": "derived from printed category SEs via design effect",
                              "ENNS2018": "sum of printed category 90% CI half-widths / 1.645 (conservative)",
                              "ENNS2019": "sum of printed category 90% CI half-widths / 1.645 (conservative)",
                              "ENNS2021": "NOT PUBLISHED: assumed 3.0 pp for every province"}[s],
                "median_se_pp": round(float(se.median()), 2), "max_se_pp": round(float(se.max()), 2),
                "labels_within_1.96SE_of_50": int(amb.sum()), "expected_misclassified_labels": round(float(pm.sum()), 2),
                "used_in_training": s != "NNS2013", "evaluation_rows_L1": int(len(ev)), "evaluation_HIGH_L1": int(ev.y_high.sum()),
                "role": {"NNS2013": "anchor history only (not a training/test target in FINAL folds)", "FNRI2015": "training only",
                         "ENNS2018": "test fold 1 (train 2015)", "ENNS2019": "test fold 2 (train 2015 only: 2018 not released by the 2019 origin)", "ENNS2021": "test fold 3 (train 2015+2018+2019)"}[s]})
G = pd.DataFrame(out).merge(HM.assign(round=HM["round"].map(sv)), on="round", how="left")
G.to_csv(EV / "GT_rounds.csv", index=False, lineterminator="\n")

# province-level evaluation label table with exclusions
E = t21[t21.survey.isin(["ENNS2018", "ENNS2019", "ENNS2021"])][["key", "province", "region", "survey", "p", "se_p"]].copy()
E["in_evaluation"] = [(k, s) in set(zip(L1.key, L1.survey)) for k, s in zip(E.key, E.survey)]
E["p_label_side_wrong"] = norm.cdf(-np.abs(E.p - 50) / E.se_p).round(3)
E["HIGH"] = (E.p >= 50).astype(int)
E.sort_values(["survey", "key"]).to_csv(EV / "GT_evaluation_labels.csv", index=False, lineterminator="\n")

# exclusions: Heat Map areas with a value but not an evaluation row
ENNS = pd.read_csv("data/hfias/clean/enns_hfias.csv")
ex = []
for yr in ("2018", "2019", "2021"):
    s = sv[yr]
    h = hm[(hm.actual_year == yr) & (hm.fs_survey_category == "Food Insecure Households")]
    keep = set(L1[L1.survey == s].key)
    for nm in sorted(h.province_name.unique()):
        k = nm.lower()
        k2 = {"compostella valley": "compostela valley", "davao de oro": "compostela valley", "cotabato": "north cotabato",
              "mountain province": "mountain", "tawi-tawi": "tawi tawi", "samar": "western samar"}.get(k, k)
        if k2 in keep:
            continue
        has_ms = not hm[(hm.actual_year == yr) & (hm.province_name == nm) & hm.fs_survey_category.str.startswith(("Moderately", "Severely"))].empty
        in_lab = k2 in set(t21[t21.survey == s].key)
        in15 = k2 in set(t21[t21.survey == "FNRI2015"].key)
        ms_panel = ENNS[(ENNS.year == int(yr)) & (ENNS.area.str.lower() == k)]
        reason = ("city / HUC / NCR domain: no provincial predictors" if ("city" in k or k in ("ncr", "pateros", "metro manila", "national capital region"))
                  else "no moderate-or-severe breakdown published (any-level headline only)" if not has_ms
                  else "FNRI deck used for the panel prints the any-level headline only (no moderate/severe split); Heat Map split not reconciled, row left out"
                  if (len(ms_panel) and ms_panel.mod_sev_pct.isna().all())
                  else "province absent from FNRI 2015 appendix (no region/anchor/inputs)" if not in15
                  else "label present but no forecast row (model inputs unavailable at origin)" if in_lab
                  else "not in label panel")
        ex.append({"round": s, "area": nm, "reason": reason})
X = pd.DataFrame(ex)
X.to_csv(EV / "GT_excluded_areas.csv", index=False, lineterminator="\n")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(G.to_string(index=False)); print(X.groupby(["round", "reason"]).size())
