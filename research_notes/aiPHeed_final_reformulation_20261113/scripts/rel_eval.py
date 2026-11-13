r"""PROTOCOL_REL (sha 4b740e48) scoring: relative label (province > national of the same round) and the original absolute label, per round + pooled,
seeds, sensitivities, bootstrap, Monte Carlo, decision rule. Run: python -I rel_eval.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm, beta
from sklearn.metrics import roc_auc_score, average_precision_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; P_ = HERE / "parts"; EV = HERE / "evidence"
K = ["key", "survey", "lead"]; RNDS = ["ENNS2018", "ENNS2019", "ENNS2021"]
NAT_PCT = {"FNRI2015": 53.8, "ENNS2018": 41.6, "ENNS2019": 46.9, "ENNS2021": 41.0}
lg = lambda p: np.log(p / (1 - p))
LATEST = {"ENNS2018": "FNRI2015", "ENNS2019": "FNRI2015", "ENNS2021": "ENNS2019"}   # latest round released at each Lead-1 origin
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["province", "y_high", "PERS"]]
LAB = LAB[LAB.lead == 1]
GT = pd.read_csv(RN / "aiPHeed_final_reliability_20261113" / "evidence" / "GT_evaluation_labels.csv")[["key", "survey", "p", "se_p", "HIGH"]].rename(columns={"p": "pct"})
D = LAB.merge(GT, on=["key", "survey"], how="left")
assert D.pct.notna().all() and (D.HIGH == D.y_high).all(), "label mismatch"
D["nat"] = D.survey.map(NAT_PCT); D["y_rel"] = (D.pct > D.nat).astype(int)
D["confident"] = (D.pct - D.nat).abs() > 1.96 * D.se_p
Lt = D.survey.map(LATEST).map(lambda r: lg(NAT_PCT[r] / 100)).values
sd_of = lambda mu, p: np.where(np.abs(mu) > 1e-6, mu / norm.ppf(np.clip(p, 1e-9, 1 - 1e-9)), np.nan)

# ---------------- predictions
FI = pd.concat([pd.read_csv(f, usecols=K + ["seed", "p", "mu"]) for f in glob.glob(str(RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd" / "FINAL__ENNS20*__1__*.csv"))])
FI = FI.merge(D[K], on=K)
FI["sd"] = sd_of(FI.mu.values, FI.p.values); FI["sd"] = FI.sd.fillna(FI.sd.median())
FI["Lt"] = FI.survey.map(LATEST).map(lambda r: lg(NAT_PCT[r] / 100))
FI["p_rel"] = norm.cdf((FI.mu - FI.Lt) / FI.sd)
RL = pd.concat([pd.read_csv(f) for f in glob.glob(str(P_ / "REL_LGBM__*.csv"))])
RL["sd"] = sd_of(RL.mu.values, RL.p.values); RL["sd"] = RL.sd.fillna(RL.sd.median())
RL["Lt"] = RL.survey.map(LATEST).map(lambda r: lg(NAT_PCT[r] / 100))
RL["p_abs"] = norm.cdf((RL.mu + RL.Lt) / RL.sd)
ST = pd.read_csv(P_ / "REL_STAT_all.csv")
mean_ = lambda d, col="p": d.groupby(K, as_index=False)[col].mean()
REL = {"REL_LGBM": mean_(RL), "REL_HB": ST[(ST.model == "REL_HB") & (ST.variant == "main")][K + ["p"]],
       "REL_P": ST[(ST.model == "REL_P") & (ST.variant == "main")][K + ["p"]], "FINAL_as_REL": mean_(FI, "p_rel").rename(columns={"p_rel": "p"}),
       "ALWAYS_LOW": D[K].assign(p=0.0)}
ABS = {"FINAL": mean_(FI), "REL_LGBM_as_ABS": mean_(RL, "p_abs").rename(columns={"p_abs": "p"}), "PERS": D[K + ["PERS"]].rename(columns={"PERS": "p"})}


def met(y, p):
    y = np.asarray(y, int); p = np.asarray(p, float); h = p >= .5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    r = tp / max(1, tp + fn); pr = tp / (tp + fp) if tp + fp else 0.0; sp = tn / max(1, tn + fp)
    one = len(set(y)) > 1
    return {"recall": r, "f1": 2 * pr * r / (pr + r) if tp else 0.0, "precision": pr, "ba": (r + sp) / 2, "brier": float(np.mean((p - y) ** 2)),
            "accuracy": (tp + tn) / len(y), "roc_auc": roc_auc_score(y, p) if one else np.nan, "pr_auc": average_precision_score(y, p) if one else np.nan,
            "prev": float(y.mean()), "n_high": int(y.sum()), "n_low": int(len(y) - y.sum()), "cm": f"{tp}/{fp}/{fn}/{tn}"}


ok = lambda m: all([m["recall"] >= .7, m["f1"] >= .7, m["precision"] >= .7, m["ba"] >= .7, m["brier"] <= .2, m["accuracy"] >= .75,
                    m["roc_auc"] >= .7, m["pr_auc"] > m["prev"]])
evaluable = lambda m: m["n_high"] >= 8 and m["n_low"] >= 8
cp = lambda k, n: [round(float(beta.ppf(.025, k, n - k + 1)) if k else 0.0, 3), round(float(beta.ppf(.975, k + 1, n - k)) if k < n else 1.0, 3)]


def table(preds, ycol, label, subset=None):
    rows = []
    for nm, pr in preds.items():
        d = D.merge(pr[K + ["p"]], on=K)
        if subset is not None:
            d = d[subset(d)]
        for s, x in list(d.groupby("survey")) + [("POOLED", d)]:
            m = met(x[ycol], x.p); tp = int(m["cm"].split("/")[0])
            rows.append({"label": label, "model": nm, "round": s, "n": len(x), **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k != "cm"},
                         "TP/FP/FN/TN": m["cm"], "recall_ci95": cp(tp, m["n_high"]) if m["n_high"] else None, "evaluable": evaluable(m), "all_8_pass": ok(m)})
    return pd.DataFrame(rows)


T_rel = table(REL, "y_rel", "relative"); T_abs = table(ABS, "y_high", "absolute")
T_conf = table(REL, "y_rel", "relative_confident_labels_only", subset=lambda d: d.confident)
seed_rows = []
for s, g in RL.groupby("seed"):
    t = table({f"REL_LGBM_seed{s}": g[K + ["p"]]}, "y_rel", "relative"); seed_rows.append(t)
for s, g in FI.groupby("seed"):
    seed_rows.append(table({f"FINAL_as_REL_seed{s}": g[K + ["p_rel"]].rename(columns={"p_rel": "p"})}, "y_rel", "relative"))
T_seed = pd.concat(seed_rows)
sens = {}
for tag, f in (("REL_LGBM_L13_seed168", "REL_LGBM_L13__*__168.csv"), ("REL_LGBM_DROP_FNRI2015", "REL_LGBM_DROP_FNRI2015__*"),
               ("REL_LGBM_DROP_ENNS2018", "REL_LGBM_DROP_ENNS2018__*"), ("REL_LGBM_DROP_ENNS2019", "REL_LGBM_DROP_ENNS2019__*")):
    sens[tag] = pd.concat([pd.read_csv(x) for x in glob.glob(str(P_ / f))])[K + ["p"]]
for v in ("l13_2015", "drop_FNRI2015", "drop_ENNS2018", "drop_ENNS2019"):
    sens[f"REL_HB_{v}"] = ST[(ST.model == "REL_HB") & (ST.variant == v)][K + ["p"]]
sens["REL_LGBM_seed168"] = RL[RL.seed == 168][K + ["p"]]
T_sens = table(sens, "y_rel", "relative")
ALL = pd.concat([T_rel, T_abs, T_conf, T_seed, T_sens]); ALL.to_csv(EV / "REL_per_round_L1.csv", index=False, lineterminator="\n")

# ---------------- paired bootstrap of pooled Brier (stratified by round; each province appears once)
rng = np.random.default_rng(20261113)
B = D[K + ["y_rel"]].copy()
for nm, pr in REL.items():
    B = B.merge(pr[K + ["p"]].rename(columns={"p": nm}), on=K)
idx = {s: np.where(B.survey.values == s)[0] for s in RNDS}
boot = {}
for a, b in (("REL_LGBM", "FINAL_as_REL"), ("REL_LGBM", "REL_P"), ("REL_LGBM", "REL_HB"), ("REL_HB", "REL_P"), ("FINAL_as_REL", "REL_P")):
    da = (B[a] - B.y_rel) ** 2 - (B[b] - B.y_rel) ** 2
    bs = [float(np.mean(da.values[np.concatenate([rng.choice(v, len(v)) for v in idx.values()])])) for _ in range(2000)]
    boot[f"{a} - {b}"] = {"dBrier": round(float(da.mean()), 4), "ci95": [round(float(np.quantile(bs, .025)), 4), round(float(np.quantile(bs, .975)), 4)]}

# ---------------- Monte Carlo pass probability at the relative class counts
cnt = {s: (int(D[D.survey == s].y_rel.sum()), int((D.survey == s).sum() - D[D.survey == s].y_rel.sum())) for s in RNDS}
cnt_abs = {s: (int(D[D.survey == s].y_high.sum()), int((D.survey == s).sum() - D[D.survey == s].y_high.sum())) for s in RNDS}


def mc(tpr, fpr, counts, N=200_000):
    r2 = np.random.default_rng(7); out, joint = {}, np.ones(N, bool)
    for s, (P, Nn) in counts.items():
        tp, fp = r2.binomial(P, tpr, N), r2.binomial(Nn, fpr, N); fn, tn = P - tp, Nn - fp
        rec = tp / P; prec = np.where(tp + fp > 0, tp / np.maximum(tp + fp, 1), 0); f1 = np.where(tp > 0, 2 * prec * rec / np.maximum(prec + rec, 1e-12), 0)
        okk = (rec >= .7) & (prec >= .7) & (f1 >= .7) & ((rec + tn / Nn) / 2 >= .7) & ((tp + tn) / (P + Nn) >= .75)
        out[s] = round(float(okk.mean()), 3); joint &= okk
    out["all_three"] = round(float(joint.mean()), 3); return out


def rates(t, nm):
    r = t[(t.model == nm) & (t["round"] == "POOLED")].iloc[0]; tp, fp, fn, tn = map(int, r["TP/FP/FN/TN"].split("/")); return tp / (tp + fn), fp / (fp + tn)


MC = {"relative_counts": cnt, "absolute_counts": cnt_abs}
for nm in ("REL_LGBM", "FINAL_as_REL"):
    t, f = rates(T_rel, nm); MC[f"{nm} skill (TPR {t:.2f}, FPR {f:.2f}) at relative counts"] = mc(t, f, cnt)
    MC[f"{nm} skill at ABSOLUTE counts"] = mc(t, f, cnt_abs)

# ---------------- decision rule (PROTOCOL_REL)
def g(t, m, r):
    return t[(t.model == m) & (t["round"] == r)].iloc[0]


ev_rounds = [s for s in RNDS if bool(g(T_rel, "REL_LGBM", s).evaluable)]
dec = {"evaluable_rounds": ev_rounds,
       "a_pooled_all8": bool(g(T_rel, "REL_LGBM", "POOLED").all_8_pass),
       "b_mean_all8_every_evaluable_round": all(bool(g(T_rel, "REL_LGBM", s).all_8_pass) for s in ev_rounds),
       "b_every_seed_all8_every_evaluable_round": all(bool(g(T_seed, f"REL_LGBM_seed{sd}", s).all_8_pass) for sd in RL.seed.unique() for s in ev_rounds),
       "c_brier_le_FINAL_as_REL": float(g(T_rel, "REL_LGBM", "POOLED").brier) <= float(g(T_rel, "FINAL_as_REL", "POOLED").brier),
       "c_brier_le_REL_P": float(g(T_rel, "REL_LGBM", "POOLED").brier) <= float(g(T_rel, "REL_P", "POOLED").brier),
       "d_2018_2019_F1_BA_within_0.05_of_FINAL_as_REL": all(float(g(T_rel, "REL_LGBM", s)[k]) >= float(g(T_rel, "FINAL_as_REL", s)[k]) - .05 for s in RNDS[:2] for k in ("f1", "ba"))}
dec["RECOMMENDED"] = all(v for k, v in dec.items() if isinstance(v, bool))
hb_close = abs(float(g(T_rel, "REL_HB", "POOLED").brier) - float(g(T_rel, "REL_LGBM", "POOLED").brier)) <= .005
hb_ok = bool(g(T_rel, "REL_HB", "POOLED").all_8_pass) and all(bool(g(T_rel, "REL_HB", s).all_8_pass) for s in ev_rounds)
dec["LightGBM_adds_no_measurable_value_over_REL_HB"] = bool(hb_close and hb_ok)

# ---------------- absolute-target error decomposition for FINAL (why 2021 fails under the absolute label)
fm = mean_(FI, "mu").merge(D[K + ["pct", "y_high"]], on=K)
fm["err"] = fm.mu - lg(fm.pct / 100)
fm["nat_ref_shift"] = fm.survey.map(LATEST).map(lambda r: lg(NAT_PCT[r] / 100)) - fm.survey.map(lambda r: lg(NAT_PCT[r] / 100))
decomp = fm.groupby("survey").agg(mean_error_logit=("err", "mean"), latest_national_minus_actual_national_logit=("nat_ref_shift", "first"),
                                  sd_error_logit=("err", "std")).round(3).to_dict(orient="index")
out = {"bootstrap_pooled_brier_relative": boot, "monte_carlo": MC, "decision": dec, "FINAL_absolute_error_decomposition": decomp,
       "label_counts": {"relative": cnt, "absolute": cnt_abs, "confident_relative_rows": int(D.confident.sum())},
       "label_agreement_abs_vs_rel": {f"abs{a}_rel{b}": {s: int(((D.survey == s) & (D.y_high == a) & (D.y_rel == b)).sum()) for s in RNDS} for a in (0, 1) for b in (0, 1)}}
json.dump(out, open(EV / "REL_verdict.json", "w"), indent=1, default=str)
D.merge(REL["REL_LGBM"].rename(columns={"p": "REL_LGBM"}), on=K).merge(REL["FINAL_as_REL"].rename(columns={"p": "FINAL_as_REL"}), on=K).merge(
    REL["REL_HB"].rename(columns={"p": "REL_HB"}), on=K).merge(REL["REL_P"].rename(columns={"p": "REL_P"}), on=K).merge(
    ABS["FINAL"].rename(columns={"p": "FINAL_abs"}), on=K).to_csv(EV / "REL_province_rows_L1.csv", index=False, lineterminator="\n")
pd.set_option("display.width", 260); pd.set_option("display.max_rows", 300)
c = ["label", "model", "round", "n_high", "n_low", "recall", "f1", "precision", "ba", "brier", "accuracy", "roc_auc", "pr_auc", "TP/FP/FN/TN", "evaluable", "all_8_pass"]
print(pd.concat([T_rel, T_abs])[c].to_string(index=False)); print(T_conf[c].to_string(index=False))
print(T_seed[c].to_string(index=False)); print(T_sens[c].to_string(index=False)); print(json.dumps(out, indent=1, default=str))
