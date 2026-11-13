r"""Root-cause analysis of FINAL (RATE + MIND) on Rules 3 and 4, using the LOCKED forward forecasts only.

Reads (never writes): aiPHeed_final_cw_20261112/evidence/cw_rows_all_leads.csv (seed-averaged locked forecasts of FINAL and
H_cw = FIX), the E158 label table (truth, anchors, survey SEs) and the public HFIAS tables. No model is fitted, no
configuration is scored, no threshold is changed. Writes evidence/RC_*.csv|json in this study folder.
Run: python -I rootcause.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
RN = HERE.parent
EV = HERE / "evidence"
EV.mkdir(exist_ok=True)
ROWS = pd.read_csv(RN / "aiPHeed_final_cw_20261112/evidence/cw_rows_all_leads.csv")
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
F15 = pd.read_csv("C:/Users/admin/aipheed_hcw/backend/data/hfias/clean/fnri2015_hfias.csv")
N13 = pd.read_csv("C:/Users/admin/aipheed_hcw/backend/data/e141/clean/nns2013_hfias.csv")
FOCUS = ["Lanao del Norte", "Misamis Oriental", "Masbate", "Occidental Mindoro", "Agusan Del Sur"]
inv = lambda z: 1 / (1 + np.exp(-z))
rng = np.random.default_rng(7)                    # same seed and resampling unit as eval_cw.py

lab = LAB[LAB.lead.isin([1, 2, 3])][["key", "province", "survey", "lead", "y_anchor", "y_true", "se_true", "gap_q", "PERS"]]
ROWS["key"] = ROWS.province.str.lower().replace({"cagayan province": "cagayan", "iloilo province": "iloilo", "isabela province": "isabela",
                                                "mountain province": "mountain", "samar": "western samar", "tawi-tawi": "tawi tawi"})
X = ROWS.merge(lab.drop(columns="province"), on=["key", "survey", "lead"], how="left")
assert X.y_true.notna().all() and len(X) == 216
X["d"] = (X.FINAL - X.q_true) ** 2 - (X.FIX - X.q_true) ** 2          # >0: FINAL worse than H_cw
X["ok_F"], X["ok_H"] = (X.FINAL >= .5) == (X.y_high == 1), (X.FIX >= .5) == (X.y_high == 1)
X["group"] = np.select([X.ok_F & X.ok_H, ~X.ok_F & X.ok_H, X.ok_F & ~X.ok_H], ["both right", "FINAL only wrong", "H_cw only wrong"], "both wrong")
X["conf_wrong_F"] = ~X.ok_F & ((X.FINAL - .5).abs() >= .2)


def boot(d, cl, n=6000):
    u = np.unique(cl)
    idx = {c: np.flatnonzero(cl == c) for c in u}
    bs = np.array([d[np.concatenate([idx[c] for c in rng.choice(u, len(u))])].mean() for _ in range(n)])
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), float(bs.std())


cl = (X.key + X.survey).values
m, lo, hi, sd = boot(X.d.values, cl)
out = {"rule3_reproduced": {"diff": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)], "boot_sd": round(sd, 4),
                            "report_value": "-0.0006 [-0.0154, +0.0154]"}}

# A. Rule 3 decomposition: where does the paired Brier difference come from?
G = X.groupby("group").agg(rows=("d", "size"), sum_d=("d", "sum"), mean_d=("d", "mean")).reset_index()
G["share_of_pooled_mean"] = (G.sum_d / len(X)).round(4)
G.to_csv(EV / "RC3_decomposition_by_group.csv", index=False)
X["brier_F"], X["brier_H"] = (X.FINAL - X.q_true) ** 2, (X.FIX - X.q_true) ** 2
PR = X.groupby(["province", "survey"]).agg(y_high=("y_high", "first"), FINAL_mean=("FINAL", "mean"), HCW_mean=("FIX", "mean"),
                                         sum_d=("d", "sum")).reset_index().sort_values("sum_d")
PR.round(4).to_csv(EV / "RC3_province_round_contributions.csv", index=False)
# Brier gain needed: upper bound < 0 requires mean < about -1.96 x bootstrap sd (sd scales ~ 1/sqrt(clusters))
out["rule3_needed"] = {"pooled_mean_now": round(m, 4), "approx_mean_needed_for_upper_below_0": round(-1.96 * sd, 4),
                       "clusters": int(len(np.unique(cl))), "rows": int(len(X))}
out["rule3_top_losses"] = PR.tail(6)[["province", "survey", "y_high", "FINAL_mean", "HCW_mean", "sum_d"]].round(3).to_dict("records")
out["rule3_top_gains"] = PR.head(6)[["province", "survey", "y_high", "FINAL_mean", "HCW_mean", "sum_d"]].round(3).to_dict("records")
out["rule3_confident_wrong_FINAL"] = X[X.conf_wrong_F][["province", "survey", "lead", "y_high", "FINAL", "FIX"]].round(3).to_dict("records")
# both-wrong rows: does H_cw's lower confidence (slope 1.78) protect it?
bw = X[X.group == "both wrong"]
out["rule3_both_wrong"] = {"rows": int(len(bw)), "sum_d": round(float(bw.d.sum()), 4),
                           "mean_abs_dist_from_0.5_FINAL": round(float((bw.FINAL - .5).abs().mean()), 3),
                           "mean_abs_dist_from_0.5_HCW": round(float((bw.FIX - .5).abs().mean()), 3)}

# B. Rule 4: HIGH recall per lead and what is missing
need = {1: .84, 2: .80, 3: .76}
r4 = []
for L, g in X.groupby("lead"):
    h = g[g.y_high == 1]
    found = int((h.FINAL >= .5).sum())
    r4.append({"lead": int(L), "HIGH_rows": len(h), "found_FINAL": found, "found_HCW": int((h.FIX >= .5).sum()),
               "required_recall": need[L], "required_found": int(np.ceil(need[L] * len(h))),
               "missed_FINAL": "; ".join(f"{a} {b[-4:]} ({p:.2f})" for a, b, p in h[h.FINAL < .5][["province", "survey", "FINAL"]].values)})
pd.DataFrame(r4).to_csv(EV / "RC4_high_recall_by_lead.csv", index=False)
out["rule4"] = r4

# C. The five provinces: survey facts, not model inputs
f15 = F15[F15.level == "province"].set_index(F15[F15.level == "province"].name.str.lower().str.replace("-", " ").str.replace(" province", ""))
n13 = N13.set_index(N13.province.str.lower().str.replace("-", " "))
nat = {"FNRI2015": 53.8}
case = []
for (prov, sv), g in X[X.lead == 1].groupby(["province", "survey"]):
    k = r_key = g.key.iloc[0]
    r = g.iloc[0]
    case.append({"province": prov, "survey": sv, "region": r.region, "y_high": int(r.y_high),
                 "modsev_2013": n13.mod_sev_pct.get(k), "modsev_2015": f15.mod_sev_pct.get(k), "se_2015": f15.mod_sev_se.get(k),
                 "outcome_pct": round(100 * inv(r.y_true), 1), "change_pp": round(100 * (inv(r.y_true) - inv(r.y_anchor)), 1),
                 "anchor_z_from_50": round((100 * inv(r.y_anchor) - 50) / f15.mod_sev_se.get(k, np.nan), 2),
                 "p_FINAL": round(r.FINAL, 3), "p_HCW": round(r.FIX, 3), "p_PERSIST": round(r.PERS, 3), "gap_q": int(r.gap_q)})
C = pd.DataFrame(case)
C.to_csv(EV / "RC_all_lead1_rows_survey_facts.csv", index=False)
C[C.province.isin(FOCUS)].to_csv(EV / "RC_five_provinces.csv", index=False)

# D. Comparison groups (descriptive; NOT used to select anything)
# 2019: provinces whose 2015 anchor sat within 5 points above the cut-off
peers19 = C[(C.survey == "ENNS2019") & C.modsev_2015.between(50, 58)].sort_values("change_pp")
peers19.to_csv(EV / "RC_2019_near_cutoff_anchor_peers.csv", index=False)
# 2021: provinces with a 2015 anchor at or above 60 % (the missed three plus those that did fall)
peers21 = C[(C.survey == "ENNS2021") & (C.modsev_2015 >= 60)].sort_values("change_pp")
peers21.to_csv(EV / "RC_2021_high_anchor_peers.csv", index=False)
out["round_mean_change_pp"] = C.groupby("survey").change_pp.agg(["mean", "std", "count"]).round(1).reset_index().to_dict("records")
out["peers_2019_near_cutoff"] = peers19[["province", "region", "modsev_2015", "se_2015", "outcome_pct", "change_pp", "y_high", "p_FINAL", "p_HCW"]].to_dict("records")
out["peers_2021_high_anchor"] = peers21[["province", "region", "modsev_2015", "outcome_pct", "change_pp", "y_high", "p_FINAL", "p_HCW", "p_PERSIST"]].to_dict("records")

# E. Measurement: how often is the anchor statistically indistinguishable from the cut-off?
C["anchor_near_cut"] = C.anchor_z_from_50.abs() < 1.96
out["anchor_near_cutoff"] = {"rows": int(C.anchor_near_cut.sum()), "of": int(C.anchor_z_from_50.notna().sum()),
                             "error_rate_FINAL_near": round(float(((C.p_FINAL >= .5) != (C.y_high == 1))[C.anchor_near_cut].mean()), 3),
                             "error_rate_FINAL_far": round(float(((C.p_FINAL >= .5) != (C.y_high == 1))[~C.anchor_near_cut].mean()), 3)}

# F. Power for an independent round (Rule 3 interval half-width vs number of provinces), resampling observed per-cluster d
dc = X.groupby(cl).d.mean().values
pw = []
for n in (15, 20, 25, 30, 40, 50, 72):
    hw = np.mean([np.diff(np.percentile([rng.choice(dc, n).mean() for _ in range(400)], [2.5, 97.5]))[0] / 2 for _ in range(5)])
    pw.append({"provinces": n, "rule3_half_width": round(float(hw), 4)})
out["rule3_half_width_by_round_size"] = pw
out["rule4_granularity"] = {f"{k}_HIGH": round(1 / k, 3) for k in (8, 10, 13, 15, 25)}

json.dump(out, open(EV / "RC_summary.json", "w"), indent=1, default=str)
print(json.dumps({k: out[k] for k in ("rule3_reproduced", "rule3_needed", "rule3_both_wrong", "rule4", "anchor_near_cutoff", "round_mean_change_pp")}, indent=1, default=str))
print(G.round(4).to_string())
print(C[C.province.isin(FOCUS)].to_string())
print(peers19.to_string())
print(peers21.to_string())
