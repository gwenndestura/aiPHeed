r"""PROTOCOL_ATTR (sha 79ebae22, locked before this script ran): fit ATTR (Bayesian structural-attractor regression) per fold, build HYB / HYB-F /
ATTR-ABS / oracle diagnostic, score everything per round + pooled, seeds, training-transition drops, bootstrap, decision rule.
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=."""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
from sklearn.linear_model import BayesianRidge
from sklearn.metrics import roc_auc_score, average_precision_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"; PARTS = HERE / "parts"
sys.path.insert(0, str(RN / "aiPHeed_objective_completion_20261111" / "scripts"))
import run_qs
lg = lambda p: np.log(p / (1 - p)); ex = lambda z: 100 / (1 + np.exp(-z))
K = ["key", "survey", "lead"]; RNDS = ["ENNS2018", "ENNS2019", "ENNS2021"]
NAT = {"NNS2013": 0.2432467540453589, "FNRI2015": lg(.538), "ENNS2018": lg(.416), "ENNS2019": lg(.469), "ENNS2021": lg(.410)}
ANCH = {"FNRI2015": "NNS2013", "ENNS2018": "FNRI2015", "ENNS2019": "FNRI2015", "ENNS2021": "FNRI2015"}
LATEST = {"ENNS2018": "FNRI2015", "ENNS2019": "FNRI2015", "ENNS2021": "ENNS2019"}
S = ["income_rel", "p_poverty", "p_poverty_gap", "hh_grdp_rel", "p_subsistence"]
TMAP = {"FNRI2015": "T1", "ENNS2018": "T2", "ENNS2019": "T3"}


def fit_attr(survey, drop=None):
    tr, te, _ = run_qs.load(survey, 1)
    tr = tr[tr.lead == 1].copy()
    if drop:
        tr = tr[tr.survey.map(TMAP) != drop]
    for d in (tr, te):
        d["z_a"] = d.y_anchor - d.survey.map(ANCH).map(NAT)
    zT = tr.y_true - tr.survey.map(NAT)
    med = tr[S].median()
    Xtr, Xte = tr[["z_a"] + S].fillna(med), te[["z_a"] + S].fillna(med)
    mu_, sd_ = Xtr.mean(), Xtr.std().replace(0, 1)
    br = BayesianRidge().fit(((Xtr - mu_) / sd_).values, zT.values, sample_weight=(1 / (tr.se_true ** 2 + 0.05)).values)
    m, s = br.predict(((Xte - mu_) / sd_).values, return_std=True)
    coef = dict(zip(["z_a"] + S, np.round(br.coef_, 4)))
    info = {"n_train": len(tr), "transitions": sorted(tr.survey.unique().tolist()), "coef_std": coef, "test_missing": int(te[S].isna().sum().sum()),
            "train_missing_share": float(tr[S].isna().mean().mean())}
    return te[["key", "survey", "lead"]].assign(z_hat=m, sd=s), info


def stored(folder, arm):
    d = pd.concat([pd.read_csv(f, usecols=K + ["seed", "p", "mu"]) for f in glob.glob(str(folder / f"{arm}__ENNS20*__1__*.csv"))])
    d["sd"] = np.where(np.abs(d.mu) > 1e-6, d.mu / norm.ppf(np.clip(d.p, 1e-9, 1 - 1e-9)), np.nan)
    d["sd"] = d.sd.fillna(d.sd.median())
    return d


def met(y, p):
    y = np.asarray(y, int); p = np.asarray(p, float); h = p >= .5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    r = tp / max(1, tp + fn); pr = tp / (tp + fp) if tp + fp else 0.0; sp = tn / max(1, tn + fp)
    return {"recall": r, "f1": 2 * pr * r / (pr + r) if tp else 0.0, "precision": pr, "ba": (r + sp) / 2, "brier": float(np.mean((p - y) ** 2)),
            "accuracy": (tp + tn) / len(y), "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p), "prev": float(y.mean()), "cm": f"{tp}/{fp}/{fn}/{tn}"}


ok = lambda m: all([m["recall"] >= .7, m["f1"] >= .7, m["precision"] >= .7, m["ba"] >= .7, m["brier"] <= .2, m["accuracy"] >= .75, m["roc_auc"] >= .7, m["pr_auc"] > m["prev"]])

if __name__ == "__main__":
    PARTS.mkdir(exist_ok=True)
    A, INFO = [], {}
    for sv in RNDS:
        a, i = fit_attr(sv); A.append(a.assign(variant="main")); INFO[sv] = i
    for dr in ("T1", "T2", "T3"):
        a, i = fit_attr("ENNS2021", drop=dr); A.append(a.assign(variant=f"drop_{dr}")); INFO[f"ENNS2021_drop_{dr}"] = i
    A = pd.concat(A); A.to_csv(PARTS / "ATTR_all.csv", index=False, lineterminator="\n")
    LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["province", "y_high", "PERS"]]; LAB = LAB[LAB.lead == 1]
    GT = pd.read_csv(RN / "aiPHeed_final_reliability_20261113" / "evidence" / "GT_evaluation_labels.csv")[["key", "survey", "p"]].rename(columns={"p": "pct"})
    D = LAB.merge(GT, on=["key", "survey"]); D["y_rel"] = (lg(D.pct / 100) > D.survey.map(NAT)).astype(int)
    LG = stored(RN / "aiPHeed_final_model_optimization_20261113" / "parts", "LG")
    FI = stored(RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd", "FINAL")

    def hyb(base, att):
        b = base.merge(att[K + ["z_hat"]], on=K)
        g = b.groupby(["survey", "seed"])
        b["mu_h"] = g.mu.transform("mean") + (b.z_hat - g.z_hat.transform("mean"))
        b["p"] = norm.cdf(b.mu_h / b.sd)
        return b

    main = A[A.variant == "main"]
    H_LG, H_FI = hyb(LG, main), hyb(FI, main)
    P = {"FINAL": FI.groupby(K, as_index=False).p.mean(), "FINAL_LG": LG.groupby(K, as_index=False).p.mean(),
         "PERS": D[K + ["PERS"]].rename(columns={"PERS": "p"}), "HYB": H_LG.groupby(K, as_index=False).p.mean(), "HYB_F": H_FI.groupby(K, as_index=False).p.mean(),
         "ATTR_ABS": main.assign(p=norm.cdf((main.z_hat + main.survey.map(LATEST).map(NAT)) / main.sd))[K + ["p"]],
         "DIAG_ORACLE_LEVEL": main.assign(p=norm.cdf((main.z_hat + main.survey.map(NAT)) / main.sd))[K + ["p"]]}
    for dr in ("T1", "T2", "T3"):
        a = A[A.variant == f"drop_{dr}"]
        h = hyb(LG[LG.survey == "ENNS2021"], a)
        P[f"HYB_drop_{dr}"] = h.groupby(K, as_index=False).p.mean()
    for s, g in H_LG.groupby("seed"):
        P[f"HYB_seed{s}"] = g[K + ["p"]]
    rows = []
    for nm, pr in P.items():
        d = D.merge(pr, on=K)
        for s, x in list(d.groupby("survey")) + ([("POOLED", d)] if d.survey.nunique() == 3 else []):
            m = met(x.y_high, x.p)
            rows.append({"label": "absolute", "model": nm, "round": s, "n": len(x), **{k: round(v, 4) for k, v in m.items() if k != "cm"},
                         "TP/FP/FN/TN": m["cm"], "all_8_pass": ok(m)})
    d = D.merge(main.assign(p=norm.cdf(main.z_hat / main.sd))[K + ["p"]], on=K)
    for s, x in list(d.groupby("survey")) + [("POOLED", d)]:
        m = met(x.y_rel, x.p); rows.append({"label": "relative", "model": "ATTR", "round": s, "n": len(x), **{k: round(v, 4) for k, v in m.items() if k != "cm"},
                                            "TP/FP/FN/TN": m["cm"], "all_8_pass": ok(m)})
    R = pd.DataFrame(rows); R.to_csv(EV / "ATTR_per_round_L1.csv", index=False, lineterminator="\n")
    # within the 2021 high-start group (2015 level >= 64 %), descriptive
    tr21, te21, _ = run_qs.load("ENNS2021", 1)
    hs = te21[ex(te21.y_anchor) >= 64].key.tolist()
    W = D[(D.survey == "ENNS2021") & D.key.isin(hs)]
    within = {}
    for nm in ("FINAL", "FINAL_LG", "PERS", "HYB"):
        w = W.merge(P[nm], on=K); within[nm] = round(float(roc_auc_score(w.y_high, w.p)), 3) if w.y_high.nunique() > 1 else None
    w = W.merge(main[K + ["z_hat"]], on=K); within["ATTR_z_hat"] = round(float(roc_auc_score(w.y_high, w.z_hat)), 3)
    # bootstrap HYB - FINAL_LG
    b = D.merge(P["HYB"].rename(columns={"p": "h"}), on=K).merge(P["FINAL_LG"].rename(columns={"p": "l"}), on=K)
    mh = H_LG.groupby(K, as_index=False).mu_h.mean(); ml = LG.groupby(K, as_index=False).mu.mean()
    b = b.merge(mh, on=K).merge(ml, on=K)
    diff = {"brier": ((b.h - b.y_high) ** 2 - (b.l - b.y_high) ** 2).values, "abs_err_pp": ((ex(b.mu_h) - b.pct).abs() - (ex(b.mu) - b.pct).abs()).values}
    rng = np.random.default_rng(20261113); idx = [np.where(b.survey.values == s)[0] for s in RNDS]; boot = {}
    for k, v in diff.items():
        bs = [v[np.concatenate([rng.choice(i, len(i)) for i in idx])].mean() for _ in range(2000)]
        boot[k] = {"HYB_minus_LG": round(float(v.mean()), 4), "ci95": [round(float(np.quantile(bs, .025)), 4), round(float(np.quantile(bs, .975)), 4)]}
        i21 = idx[2]; bs = [v[rng.choice(i21, len(i21))].mean() for _ in range(2000)]
        boot[k + "_2021"] = {"HYB_minus_LG": round(float(v[i21].mean()), 4), "ci95": [round(float(np.quantile(bs, .025)), 4), round(float(np.quantile(bs, .975)), 4)]}
    g = lambda m, r: R[(R.label == "absolute") & (R.model == m) & (R["round"] == r)].iloc[0]
    T13 = {"income_rel": -1, "p_poverty": 1, "p_poverty_gap": 1, "hh_grdp_rel": -1, "p_subsistence": 1}
    signs = {sv: {c: bool(np.sign(INFO[sv]["coef_std"][c]) == s_ or INFO[sv]["coef_std"][c] == 0) for c, s_ in T13.items()} for sv in RNDS}
    cm = lambda m, r: tuple(map(int, g(m, r)["TP/FP/FN/TN"].split("/")[:2]))
    dec = {"1_2018_2019_all8_and_within_0.05": all(bool(g("HYB", s).all_8_pass) and g("HYB", s).f1 >= g("FINAL_LG", s).f1 - .05 and g("HYB", s).ba >= g("FINAL_LG", s).ba - .05 for s in RNDS[:2]),
           "2_pooled_all8": bool(g("HYB", "POOLED").all_8_pass), "3_pooled_brier_le_LG_plus_0.005": float(g("HYB", "POOLED").brier) <= float(g("FINAL_LG", "POOLED").brier) + .005,
           "4_2021_auc_gt_LG_and_f1_ge": float(g("HYB", "ENNS2021").roc_auc) > float(g("FINAL_LG", "ENNS2021").roc_auc) and float(g("HYB", "ENNS2021").f1) >= float(g("FINAL_LG", "ENNS2021").f1),
           "5_every_seed_2021_tp_fp_as_mean_or_better": all(cm(f"HYB_seed{s}", "ENNS2021")[0] >= cm("HYB", "ENNS2021")[0] and cm(f"HYB_seed{s}", "ENNS2021")[1] <= cm("HYB", "ENNS2021")[1] for s in H_LG.seed.unique()),
           "6_signs_match_T1_T3": all(all(v.values()) for v in signs.values())}
    dec["RECOMMENDED"] = all(dec.values())
    out = {"attr_fit_info": INFO, "coef_sign_check": signs, "within_highstart_2021_auc": within, "highstart_provinces": hs, "bootstrap": boot, "decision": dec}
    json.dump(out, open(EV / "ATTR_verdict.json", "w"), indent=1, default=str)
    rows21 = D[D.survey == "ENNS2021"].merge(main[K + ["z_hat", "sd"]], on=K)
    for nm in ("FINAL", "FINAL_LG", "HYB", "ATTR_ABS"):
        rows21 = rows21.merge(P[nm].rename(columns={"p": nm}), on=K)
    rows21.sort_values("HYB", ascending=False).to_csv(EV / "ATTR_2021_rows.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 260); pd.set_option("display.max_rows", 200)
    print(R[["label", "model", "round", "recall", "f1", "precision", "ba", "brier", "accuracy", "roc_auc", "pr_auc", "TP/FP/FN/TN", "all_8_pass"]].to_string(index=False))
    print(json.dumps(out, indent=1, default=str))
    print(rows21.sort_values("HYB", ascending=False)[["province", "y_high", "pct", "FINAL", "FINAL_LG", "HYB", "ATTR_ABS", "z_hat"]].round(3).head(14).to_string(index=False))
