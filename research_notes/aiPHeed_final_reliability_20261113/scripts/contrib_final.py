r"""Deliverable 6: five dashboard contributor groups, validated for FINAL alone (elapsed-time hypothesis g = FINAL exactly).
Re-scores the EXISTING fits of ../aiPHeed_final_etmix_20261113/parts (110 fold fits with exact TreeSHAP, withholding and
permutation; 105 Lead-1 group retrains; 18 single-input retrains), keeping only hyp == 'g'. No refit; outcomes used only to score.
Rule (PROTOCOL_REL): a group genuinely improves out-of-sample forecasting only if retraining without it raises pooled Lead-1 Brier
with a 95 % bootstrap CI above 0 (5-seed mean probabilities). Run: python -I contrib_final.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
PT, EV = RN / "aiPHeed_final_etmix_20261113" / "parts", HERE / "evidence"
K = ["key", "survey", "lead"]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["province", "region", "y_high"]]
rng = np.random.default_rng(7)
DASH = {"market_prices": "1 Market and prices", "climate": "2 Climate stress", "employment": "3 Employment", "remittance": "4 OFW remittances",
        "poverty_vulnerability": "5 Poverty and social vulnerability", "regional_accounts": "(not on dashboard) Regional economy - GRDP/income, REGIONAL",
        "agri_fish_production": "(not on dashboard) Agriculture and fish production", "news_nlp": "(not on dashboard) News / NLP signals"}


def group(c):
    c = c[3:] if c.startswith("mi_") else c
    if c in ("gap_q", "lead"): return "timing"
    if c in ("hh_grdp_g", "hh_grdp_rel", "income_growth", "income_rel"): return "regional_accounts"
    if c in ("p_poverty", "p_poverty_gap", "p_subsistence", "p_density"): return "poverty_vulnerability"
    if c.startswith(("cpi_", "l_fg", "l_rice", "l_terms")): return "market_prices"
    if c.startswith(("c_rain", "c_soil", "c_tc", "rain_", "soil_", "tc_", "vu_")) or c == "oni": return "climate"
    if c.startswith("unemp"): return "employment"
    if c.startswith(("remit", "ofw")): return "remittance"
    if c.startswith(("ag_", "agri_", "c_agri", "l_fish")): return "agri_fish_production"
    return "news_nlp"


def met(y, p):
    y, p = np.asarray(y, int), np.asarray(p, float); h = p >= .5
    rec = (h & (y == 1)).sum() / max(1, (y == 1).sum()); spec = (~h & (y == 0)).sum() / max(1, (y == 0).sum())
    return {"BA": .5 * (rec + spec), "recall": rec, "acc": float((h == (y == 1)).mean()), "auc": roc_auc_score(y, p), "brier": float(np.mean((p - y) ** 2))}


def ci(d):
    b = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)]
    return [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]


F = pd.concat([pd.read_parquet(f) for f in glob.glob(str(PT / "FOLD__*.parquet"))])
F = F[F.hyp == "g"]
E = F.groupby(K + ["kind", "what", "rep"], as_index=False)["p"].mean().merge(LAB, on=K)      # 5-seed mean of FINAL
base = E[E.kind == "base"][K + ["p"]].rename(columns={"p": "p0"})
# reproduction: the fold fits' base FINAL vs the stored 5-seed FINAL rows used by rel_eval.py
REL = pd.read_csv(EV / "REL_rows_L1to5.csv")[K + ["FINAL"]]
chk = base.merge(REL, on=K)
repro = {"rows": int(len(chk)), "max_abs_diff_vs_stored_FINAL": float((chk.p0 - chk.FINAL).abs().max())}
E = E.merge(base, on=K); E["flip"] = (E.p >= .5) != (E.p0 >= .5)
B0 = base[base.lead == 1].merge(LAB, on=K)

# ---- retraining without a group (Lead 1, 3 rounds x 5 seeds)
RT = pd.concat([pd.read_csv(f) for f in glob.glob(str(PT / "RETRAIN__*.csv"))]); RT = RT[RT.hyp == "g"]
rows = []
for gname, x in RT.groupby("dropped"):
    z = x.groupby(["key", "survey"], as_index=False)["p"].mean().merge(B0, on=["key", "survey"])
    a, b = met(z.y_high, z.p), met(z.y_high, z.p0)
    dd = ((z.p - z.y_high) ** 2 - (z.p0 - z.y_high) ** 2).values
    c = ci(dd)
    w = E[(E.kind == "withhold_group") & (E.what == gname)]
    pm = E[(E.kind == "permute_group") & (E.what == gname) & (E.lead == 1)]
    pmz = pm.groupby(K, as_index=False).agg(p=("p", "mean"), p0=("p0", "first"), y=("y_high", "first"))
    rows.append({"group": gname, "dashboard": DASH.get(gname, gname), "retrain_dBrier_L1": round(float(dd.mean()), 4), "retrain_dBrier_ci95": c,
                 "retrain_dBA_L1": round(a["BA"] - b["BA"], 3), "retrain_dAcc_L1": round(a["acc"] - b["acc"], 3), "retrain_dRecall_L1": round(a["recall"] - b["recall"], 3),
                 "retrain_flips_L1": int(((z.p >= .5) != (z.p0 >= .5)).sum()),
                 "withhold_flips_L1to8": int(w.flip.sum()), "withhold_forecasts": int(len(w)),
                 "permute_dBrier_L1": round(float(((pmz.p - pmz.y) ** 2 - (pmz.p0 - pmz.y) ** 2).mean()), 4),
                 "genuine_out_of_sample_improvement": bool(c[0] > 0)})
RG = pd.DataFrame(rows)
RG = pd.concat([RG, pd.DataFrame([{"group": "remittance", "dashboard": DASH["remittance"], "genuine_out_of_sample_improvement": False,
                                    "note": "no remittance input among FINAL's candidates (dropped by design in app/hcw/engine.py DROP; no provincial series exists)"}])],
               ignore_index=True)
RG.to_csv(EV / "CONTRIB_group_retrain_L1.csv", index=False, lineterminator="\n")

# ---- exact TreeSHAP shares (FINAL only), and directional plausibility per input
SH = pd.concat([pd.read_parquet(f) for f in glob.glob(str(PT / "SHAP__*.parquet"))]); SH = SH[(SH.hyp == "g") & (SH.input != "bias")]
SH = SH.groupby(K + ["input"], as_index=False)["contrib"].sum().assign(contrib=lambda d: d.contrib / 5)
SH["group"] = SH.input.map(group)
tot = SH.assign(a=SH.contrib.abs()).groupby(K)["a"].sum()
gs = SH.assign(a=SH.contrib.abs()).groupby(K + ["group"])["a"].sum().div(tot).rename("share").reset_index()
sg = gs.groupby("group").agg(share_all_leads=("share", "mean")).join(gs[gs.lead == 1].groupby("group").agg(share_L1=("share", "mean"))).join(
    gs[gs.lead == 1].pivot_table(index="group", columns="survey", values="share", aggfunc="mean").add_prefix("share_L1_")).round(3).reset_index()
sg["dashboard"] = sg.group.map(DASH)
sg.to_csv(EV / "CONTRIB_shap_group_shares.csv", index=False, lineterminator="\n")

# direction: correlation between an input's value and its SHAP contribution in the test rows (needs the inputs)
import sys
sys.path.insert(0, "C:/Users/admin/aipheed_hcw/backend")
try:
    from app.e151 import prov as Pv
    from app.hcw import engine as H
    SIGN = {**Pv.SIGN, **H.NEW_SIGN}
except Exception as ex:          # noqa: BLE001
    SIGN = {}
    print("sign table unavailable:", ex)
imp = SH.assign(a=SH.contrib.abs()).groupby("input").agg(mean_abs_contrib=("a", "mean"), group=("group", "first"))
imp["fits_selected_of_110"] = [int(sum(1 for f in glob.glob(str(PT / "META__*.json")) if i in json.load(open(f))["selected"])) for i in imp.index]
imp["monotone_sign_imposed"] = [SIGN.get(i[3:] if i.startswith("mi_") else i, 0) if not i.startswith("mi_") else 0 for i in imp.index]
imp["dashboard"] = imp.group.map(DASH)
imp.sort_values("mean_abs_contrib", ascending=False).round(5).to_csv(EV / "CONTRIB_input_importance.csv", lineterminator="\n")

# single-input retrains (seed 168, Lead 1)
RF = pd.concat([pd.read_csv(f) for f in glob.glob(str(PT / "RETRAIN_FEAT__*.csv"))]); RF = RF[RF.hyp == "g"]
F168 = F[(F.kind == "base") & (F.seed == 168) & (F.lead == 1)][["key", "survey", "p"]].rename(columns={"p": "p0"}).merge(LAB[LAB.lead == 1], on=["key", "survey"])
fr = []
for c, x in RF.groupby("dropped"):
    z = x[["key", "survey", "p"]].merge(F168, on=["key", "survey"])
    dd = ((z.p - z.y_high) ** 2 - (z.p0 - z.y_high) ** 2).values
    fr.append({"input": c, "group": group(c), "dBrier_L1_seed168": round(float(dd.mean()), 4), "ci95": ci(dd), "flips": int(((z.p >= .5) != (z.p0 >= .5)).sum()),
               "genuine_improvement": bool(ci(dd)[0] > 0)})
pd.DataFrame(fr).to_csv(EV / "CONTRIB_single_input_retrain_L1.csv", index=False, lineterminator="\n")
json.dump(repro, open(EV / "CONTRIB_reproduction.json", "w"), indent=1)
pd.set_option("display.width", 300); pd.set_option("display.max_columns", 30)
print(repro); print(RG.to_string(index=False)); print(sg.to_string(index=False)); print(pd.DataFrame(fr).to_string(index=False))
print(imp.sort_values("mean_abs_contrib", ascending=False).head(15).to_string())
