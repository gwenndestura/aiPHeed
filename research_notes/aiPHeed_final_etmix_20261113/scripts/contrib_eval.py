r"""Scores the FINAL-ETMIX contributor evidence produced by contrib_jobs.py and writes the contributor registry.
Every measure is computed on the ETMIX probability p = (p_g + p_s)/2, averaged over the five seeds, on held-out test rows of each
walk-forward fold. Outcomes are used only to score; nothing here changes the model. Retrospective (72 reused province-rounds).

Classification rules (fixed in this script before it was first run; group level):
  core        : retraining without the group lowers Lead-1 balanced accuracy by >= 0.03 OR raises Brier by >= 0.005, AND the
                within-fold permutation raises Brier in >= 2 of 3 survey rounds at Lead 1, AND withholding flips >= 2 % of forecasts
  supporting  : some measurable predictive effect (permutation dBrier > 0 pooled over leads, or >= 1 flip when withheld, or a
                retraining loss) but not all core conditions
  redundant   : withholding / permuting matters but retraining without it changes nothing (|dBA| < 0.01 and |dBrier| < 0.003):
                its information is carried by other inputs
  contextual  : no measurable predictive effect (0 flips, |permutation dBrier| < 0.001) but kept for situational context
  excluded    : not a candidate input of the model (dropped by design or unavailable)
Run: python -I contrib_eval.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
PT, EV = HERE / "parts", HERE / "evidence"
MX = RN / "aiPHeed_final_7of7_20261113"
K = ["key", "survey", "lead"]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["province", "region", "y_high"]]
GROUPS = ("market_prices", "climate", "employment", "regional_accounts", "poverty_vulnerability", "agri_fish_production", "news_nlp")
NAMES = {"regional_accounts": "Regional economy (GRDP and household income)", "market_prices": "Food prices and inflation",
         "poverty_vulnerability": "Poverty and social vulnerability", "agri_fish_production": "Agriculture and fish production",
         "climate": "Climate and typhoon exposure", "employment": "Employment", "news_nlp": "News signals (NLP / FSSI)"}
rng = np.random.default_rng(11)


def group(c):
    c = c[3:] if c.startswith("mi_") else c
    if c in ("gap_q", "lead"): return "timing"
    if c in ("hh_grdp_g", "hh_grdp_rel", "income_growth", "income_rel"): return "regional_accounts"
    if c in ("p_poverty", "p_poverty_gap", "p_subsistence", "p_density"): return "poverty_vulnerability"
    if c.startswith(("cpi_", "l_fg", "l_rice", "l_terms")): return "market_prices"
    if c.startswith(("c_rain", "c_soil", "c_tc", "rain_", "soil_", "tc_", "vu_")) or c == "oni": return "climate"
    if c.startswith("unemp"): return "employment"
    if c.startswith(("ag_", "agri_", "c_agri", "l_fish")): return "agri_fish_production"
    return "news_nlp"


def met(y, p):
    y, p = np.asarray(y, int), np.asarray(p, float); h = p >= .5
    rec = (h & (y == 1)).sum() / max(1, (y == 1).sum()); spec = (~h & (y == 0)).sum() / max(1, (y == 0).sum())
    return {"BA": .5 * (rec + spec), "recall": rec, "precision": (h & (y == 1)).sum() / max(1, h.sum()), "acc": float((h == (y == 1)).mean()),
            "auc": roc_auc_score(y, p) if 0 < y.sum() < len(y) else np.nan, "brier": float(np.mean((p - y) ** 2))}


# ------------------------------------------------------------------ fold results -> ETMIX probability per variant
F = pd.concat([pd.read_parquet(f) for f in glob.glob(str(PT / "FOLD__*.parquet"))])
V = ["kind", "what", "rep"]
E = F.groupby(K + V + ["seed"], as_index=False)["p"].mean()          # mean over hypotheses = ETMIX (g only where s == g)
E = E.groupby(K + V, as_index=False)["p"].mean().merge(LAB, on=K)    # 5-seed mean
base = E[E.kind == "base"][K + ["p"]].rename(columns={"p": "p0"})
# reproduction check against the stored ETMIX parts (protocol a365da1f)
X = pd.concat([pd.read_csv(f) for f in glob.glob(str(MX / "parts_mix" / "FINALMIX__*.csv"))]).groupby(K, as_index=False)["p"].mean()
chk = base.merge(X, on=K)
repro = {"rows": int(len(chk)), "max_abs_diff_vs_stored_ETMIX": float((chk.p0 - chk.p).abs().max())}
E = E.merge(base, on=K)
E["dp"], E["flip"] = E.p - E.p0, (E.p >= .5) != (E.p0 >= .5)


def effect(g, by_lead=True):
    """Performance change of a perturbed variant vs the unperturbed ETMIX on the same rows (rep-averaged for permutations)."""
    rows = []
    for (L, rep), x in g.groupby(["lead", "rep"]):
        a, b = met(x.y_high, x.p), met(x.y_high, x.p0)
        rows.append({"lead": L, "rep": rep, **{f"d_{k}": a[k] - b[k] for k in a}})
    d = pd.DataFrame(rows).groupby("lead").mean(numeric_only=True).drop(columns="rep")
    return d


out_groups, out_inputs = [], []
for kind, level in (("withhold_group", "group"), ("permute_group", "group"), ("withhold_input", "input"), ("permute_input", "input")):
    for what, g in E[E.kind == kind].groupby("what"):
        d = effect(g)
        x1 = g[g.lead == 1]
        rnd = {}
        for sv, xx in x1.groupby("survey"):
            rnd[sv[-4:]] = round(float(np.mean([met(z.y_high, z.p)["brier"] - met(z.y_high, z.p0)["brier"] for _, z in xx.groupby("rep")])), 4)
        # pooled L1 bootstrap interval for dBrier (rows resampled; reps averaged first)
        z = x1.groupby(K, as_index=False).agg(p=("p", "mean"), p0=("p0", "first"), y=("y_high", "first"))
        dd = (z.p - z.y) ** 2 - (z.p0 - z.y) ** 2
        bs = [dd.values[rng.integers(0, len(dd), len(dd))].mean() for _ in range(3000)] if len(dd) else [np.nan]
        if 1 not in d.index:                                  # input selected only in folds without a Lead-1 fit
            d.loc[1] = np.nan
        flips = g[g.rep == 0] if kind.startswith("withhold") else g
        rec = {"kind": kind, level: what, "group": group(what) if level == "input" else what,
               "mean_abs_dp_all_leads": round(float(g.dp.abs().mean()), 4), "max_abs_dp": round(float(g.dp.abs().max()), 3),
               "flips_all_leads": int(flips.flip.sum()) / (1 if kind.startswith("withhold") else 10), "forecasts": int(len(flips) / (1 if kind.startswith("withhold") else 10)),
               "dBrier_L1": round(float(d.at[1, "d_brier"]), 4), "dBrier_L1_ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
               "dBA_L1": round(float(d.at[1, "d_BA"]), 3), "dAUC_L1": round(float(d.at[1, "d_auc"]), 3), "dRecall_L1": round(float(d.at[1, "d_recall"]), 3),
               "dBrier_L1_by_round": rnd, "rounds_dBrier_up_L1": int(sum(v > 0 for v in rnd.values())),
               "dBrier_mean_L1to8": round(float(d.d_brier.mean()), 4), "leads_dBrier_up": int((d.d_brier > 0).sum()), "dBA_by_lead": {int(k): round(float(v), 3) for k, v in d.d_BA.items()}}
        (out_groups if level == "group" else out_inputs).append(rec)
G = pd.DataFrame(out_groups); I = pd.DataFrame(out_inputs)
G.to_csv(EV / "C1_group_withhold_permute.csv", index=False); I.to_csv(EV / "C2_input_withhold_permute.csv", index=False)

# ------------------------------------------------------------------ exact TreeSHAP (mixed over hypotheses, 5 seeds)
SH = pd.concat([pd.read_parquet(f) for f in glob.glob(str(PT / "SHAP__*.parquet"))])
SH = SH[SH.input != "bias"]
SH = SH.groupby(K + ["seed", "input"], as_index=False)["contrib"].mean()       # mean over hypotheses
SH = SH.groupby(K + ["input"], as_index=False)["contrib"].sum().assign(contrib=lambda d: d.contrib / 5)   # 5-seed mean (0 where not selected)
SH["group"] = SH.input.map(group)
SH = SH.merge(LAB, on=K)
tot = SH.assign(a=SH.contrib.abs()).groupby(K)["a"].sum()
gs = SH.assign(a=SH.contrib.abs()).groupby(K + ["group"])["a"].sum().div(tot).rename("share").reset_index().merge(LAB, on=K)
shap_group = gs.groupby("group").agg(mean_abs_share_all=("share", "mean")).join(
    gs[gs.lead == 1].groupby("group").agg(share_L1=("share", "mean"))).join(
    gs[gs.lead == 1].pivot_table(index="group", columns="survey", values="share", aggfunc="mean").add_prefix("share_L1_")).round(3)
sg = SH.groupby(K + ["group"], as_index=False)["contrib"].sum().merge(LAB, on=K)
dirn = sg[sg.lead == 1].groupby(["group", "y_high"])["contrib"].mean().unstack().rename(columns={0: "mean_contrib_LOW_rows", 1: "mean_contrib_HIGH_rows"}).round(4)
shap_group = shap_group.join(dirn)
shap_group.to_csv(EV / "C3_shap_group_shares.csv")
si = SH.assign(a=SH.contrib.abs()).groupby("input").agg(mean_abs_contrib=("a", "mean"), group=("group", "first")).join(
    SH[SH.lead == 1].assign(a=lambda d: d.contrib.abs()).groupby("input")["a"].mean().rename("mean_abs_contrib_L1")).sort_values("mean_abs_contrib", ascending=False).round(5)
# province consistency: share of each group per province at Lead 1
prov = gs[gs.lead == 1].pivot_table(index=["province", "survey"], columns="group", values="share").round(3)
prov.to_csv(EV / "C4_shap_group_share_by_province_L1.csv")

# ------------------------------------------------------------------ gain / split / selection from the 110 fits
M = [json.load(open(f)) for f in glob.glob(str(PT / "META__*.json"))]
sel = pd.Series([c for m in M for c in m["selected"]]).map(lambda c: c[3:] if c.startswith("mi_") else c).value_counts()
gain = pd.DataFrame([{"input": c, "gain_share": v / max(1e-12, sum(m["gain"].values())), "fit": i} for i, m in enumerate(M) for c, v in m["gain"].items()])
gain["base"] = gain.input.map(lambda c: c[3:] if c.startswith("mi_") else c)
gsh = gain.groupby("base")["gain_share"].sum() / len(M)
ggrp = gain.assign(g=gain.input.map(group)).groupby("g")["gain_share"].sum() / len(M)
si = si.join(gsh.rename("mean_gain_share"), how="outer").join(sel.rename("fits_selected_of_110"), how="outer")
si["group"] = si.index.map(group)
si.round(5).to_csv(EV / "C5_input_importance.csv")
integrity = {"fits": len(M), "selected_matches_stored_FINAL_fit": int(sum(m["selected_matches_stored_FINAL_fit"] for m in M)),
             "train_gap_equals_staleness_all_fits": all(m["train_gap_equals_staleness"] for m in M), **repro}

# ------------------------------------------------------------------ retraining without each group (Lead 1, 5 seeds)
RT = pd.concat([pd.read_csv(f) for f in glob.glob(str(PT / "RETRAIN__*.csv"))])
rt = RT.groupby(K + ["dropped", "seed"], as_index=False)["p"].mean().groupby(K + ["dropped"], as_index=False)["p"].mean().merge(LAB, on=K)
b1 = base[base.lead == 1].merge(LAB, on=K)
mb = met(b1.y_high, b1.p0)
rr = []
for gname, x in rt.groupby("dropped"):
    x = x.merge(b1[K + ["p0"]], on=K)
    mm = met(x.y_high, x.p)
    dd = (x.p - x.y_high) ** 2 - (x.p0 - x.y_high) ** 2
    bs = [dd.values[rng.integers(0, len(dd), len(dd))].mean() for _ in range(3000)]
    selected = RT[(RT.dropped == gname)].drop_duplicates(["survey", "seed"]).selected.str.split(";").explode()
    repl = selected.map(group).value_counts(normalize=True).round(3).to_dict()
    rr.append({"group": gname, **{f"d_{k}": round(mm[k] - mb[k], 3) for k in mm}, "dBrier_ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
               "flips_vs_full": int(((x.p >= .5) != (x.p0 >= .5)).sum()), "mean_abs_dp": round(float((x.p - x.p0).abs().mean()), 3),
               "by_round_dBA": {s[-4:]: round(met(z.y_high, z.p)["BA"] - met(z.y_high, z.p0)["BA"], 3) for s, z in x.groupby("survey")},
               "selected_group_mix_after_removal": repl})
RA = pd.DataFrame(rr).set_index("group")
RA.to_csv(EV / "C6_retrain_without_group_L1.csv")
RF = None
ff = glob.glob(str(PT / "RETRAIN_FEAT__*.csv"))
if ff:
    R2 = pd.concat([pd.read_csv(f) for f in ff]).groupby(K + ["dropped"], as_index=False)["p"].mean().merge(LAB, on=K)
    b168 = E[(E.kind == "base") & (E.lead == 1)]
    s168 = F[(F.kind == "base") & (F.lead == 1) & (F.seed == 168)].groupby(K, as_index=False)["p"].mean().rename(columns={"p": "p0"})
    rf = []
    for c, x in R2.groupby("dropped"):
        x = x.merge(s168, on=K); a, b = met(x.y_high, x.p), met(x.y_high, x.p0)
        rf.append({"input": c, **{f"d_{k}": round(a[k] - b[k], 3) for k in a}, "flips": int(((x.p >= .5) != (x.p0 >= .5)).sum()),
                   "by_round_dBA": {s[-4:]: round(met(z.y_high, z.p)["BA"] - met(z.y_high, z.p0)["BA"], 3) for s, z in x.groupby("survey")}})
    RF = pd.DataFrame(rf)
    RF.to_csv(EV / "C7_retrain_without_input_L1_seed168.csv", index=False)

# ------------------------------------------------------------------ correlation among the leading inputs (training rows, Lead 1 folds)
import pickle
C = RN / "aiPHeed_objective_completion_20261111" / "cache"
top = [c for c in si.sort_values("mean_abs_contrib", ascending=False).index[:12]]
cors = {}
for sv in ("ENNS2018", "ENNS2019", "ENNS2021"):
    o = pickle.load(open(C / f"{sv}_1.pkl", "rb"))
    tr = o["tr"]
    cc = [c for c in top if c in tr]
    cors[sv] = tr[cc].rank().corr().round(2)
cors["ENNS2021"].to_csv(EV / "C8_rank_correlation_top_inputs_train_2021L1.csv")

# ------------------------------------------------------------------ classification (rules in the module docstring)
geo = pd.read_csv(MX / "evidence" / "G3_input_inventory.csv").set_index("input")
# empirical geography for EVERY candidate input (the 7-of-7 inventory left the added groups blank): built like run_qs.load
o = pickle.load(open(C / "ENNS2021_1.pkl", "rb")); tr = o["tr"]
L_ = pd.read_parquet(C / "local_panel_asof.parquet"); lc = [c for c in L_.columns if c not in ("key", "qi") and c in tr.columns]
tr = tr.drop(columns=lc).merge(L_[["key", "qi"] + lc].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
cp = pd.read_parquet(C / "cand_panel.parquet"); new = [c for c in cp.columns if c not in ("key", "qi") and c not in tr]
tr = tr.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")


def geography(c):
    if c not in tr or tr[c].notna().sum() == 0:
        return "not available in training rows"
    x = tr[["region", "i", c]].dropna()
    if (x.groupby(["region", "i"])[c].nunique() > 1).any():
        return "provincial (varies within region)"
    if (x.groupby("i")[c].nunique() > 1).any():
        return "REGIONAL (same value for every province of a region)"
    return "NATIONAL (one value per quarter)"


geo["empirical_geography"] = [geography(c) for c in geo.index]
geo["missing_share_train_2021L1"] = [round(float(tr[c].isna().mean()), 3) if c in tr else np.nan for c in geo.index]
geo.drop(columns=["mean_gain_share", "times_selected_of_110"], errors="ignore").join(si[["mean_abs_contrib", "mean_abs_contrib_L1", "mean_gain_share", "fits_selected_of_110"]], how="left").to_csv(EV / "C9_input_inventory_etmix.csv")
reg_rows = []
for g in GROUPS:
    w = G[(G.kind == "withhold_group") & (G.group == g)].iloc[0]; p = G[(G.kind == "permute_group") & (G.group == g)].iloc[0]
    r = RA.loc[g]
    loss = r.d_BA <= -0.03 or r.d_brier >= 0.005
    core = loss and p.rounds_dBrier_up_L1 >= 2 and w.flips_all_leads / w.forecasts >= 0.02
    some = p.dBrier_mean_L1to8 > 0 or w.flips_all_leads >= 1 or loss
    redundant = (w.flips_all_leads >= 1 or p.dBrier_L1 > 0.001) and abs(r.d_BA) < 0.01 and abs(r.d_brier) < 0.003
    none = w.flips_all_leads == 0 and abs(p.dBrier_L1) < 0.001 and abs(p.dBrier_mean_L1to8) < 0.001
    cls = "core" if core else "contextual" if none else "redundant" if redundant else "supporting" if some else "contextual"
    ins = geo[geo.group == g]
    reg_rows.append({"group": g, "name": NAMES[g], "classification": cls,
                     # dashboard display rule (a presentation decision, set AFTER the classification above was first computed and disclosed as
                     # such): a group is shown as a forecast factor only if it is core, or supporting with >= 5 % of the Lead-1 attribution;
                     # redundant and contextual groups are shown as context, never as triggers
                     "tier": "core" if cls == "core" else ("supporting" if cls == "supporting" and g in shap_group.index
                                                             and float(shap_group.at[g, "share_L1"] or 0) >= 0.05 else "contextual"),
                     "evidence": {"withhold_flips": f"{w.flips_all_leads:g}/{w.forecasts}", "withhold_dBA_L1": w.dBA_L1, "permute_dBrier_L1": p.dBrier_L1,
                                  "permute_dBrier_L1_ci95": p.dBrier_L1_ci95, "permute_rounds_up_L1": int(p.rounds_dBrier_up_L1), "permute_dBrier_mean_L1to8": p.dBrier_mean_L1to8,
                                  "retrain_dBA_L1": float(r.d_BA), "retrain_dBrier_L1": float(r.d_brier), "retrain_dBrier_ci95": r.dBrier_ci95,
                                  "retrain_flips": int(r.flips_vs_full), "retrain_by_round_dBA": r.by_round_dBA,
                                  "shap_share_L1": float(shap_group.at[g, "share_L1"]) if g in shap_group.index else 0.0,
                                  "gain_share": round(float(ggrp.get(g, 0.0)), 3)},
                     "inputs": ins.index.tolist(), "geography": ins.empirical_geography.value_counts().to_dict()})
for r in reg_rows:
    e = r["evidence"]
    r["evidence_summary"] = (f"withholding changes {e['withhold_flips']} forecast classes; permutation raises Lead-1 Brier by {e['permute_dBrier_L1']:+.4f} "
                             f"(up in {e['permute_rounds_up_L1']}/3 rounds); retraining without it: balanced accuracy {e['retrain_dBA_L1']:+.3f}, Brier {e['retrain_dBrier_L1']:+.3f}; "
                             f"{e['shap_share_L1'] * 100:.0f}% of Lead-1 attribution")
doc = {"model": "final-etmix-1.0-experimental (protocol a365da1f)", "basis": "retrospective walk-forward, 72 reused province-rounds (50 at Leads 7-8); 110 fits x 2 hypotheses; Lead-1 retraining 105 fits",
       "integrity": integrity, "rules": __doc__.split("Classification rules")[1].split("Run:")[0].strip(), "groups": reg_rows,
       "excluded": [{"input": "c_fish_yoy (fish production growth)", "reason": "dropped by design in the candidate set (app.hcw.engine DROP)"},
                    {"input": "OFW remittances", "reason": "dropped by design; no provincial remittance series exists"},
                    {"input": "SWS hunger", "reason": "not a FINAL candidate input (different measure; tested 11-11, no gain)"}],
       "structural": {"anchor": "latest provincial HFIAS survey level: the starting point of every forecast", "timing": "elapsed time since the survey (gap_q; the two hypotheses g and s)"}}
(EV / "contributor_registry.json").write_text(json.dumps(doc, indent=1, default=float), newline="\n")
pd.set_option("display.width", 300); pd.set_option("display.max_columns", 30)
print(json.dumps(integrity, indent=1))
print(G.drop(columns=["dBA_by_lead"]).to_string(index=False))
print(shap_group.to_string()); print(RA.to_string())
print(si.head(25).to_string())
if RF is not None: print(RF.to_string(index=False))
print(pd.DataFrame([{k: r[k] for k in ("group", "classification", "tier")} for r in reg_rows]).to_string(index=False))
print(cors["ENNS2021"].to_string())
