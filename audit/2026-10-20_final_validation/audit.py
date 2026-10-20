"""Independent audit recomputation (no project label/metric library is imported).

Rebuilds T43 labels from the raw PSA CPI YoY file, the SWS rounds file and the frozen E40 thresholds, then recomputes
every Lead-1/2/3 metric, the Objective 4 baseline comparison and the FIRI v2 regional/T43 results from the sealed,
prediction-level files. Writes audit_results.json and prints a summary.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

MAIN = Path(r"C:\Users\admin\aipheed")
FINAL = Path(r"C:\Users\admin\aipheed_final")
EXP = MAIN / "aipheed-backend-aligned" / "experiments"
HERE = Path(__file__).resolve().parent
FT = HERE / "ft"

YOY = EXP / "E40_SWS_CPI_Tiers" / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv"
SWS = MAIN / "backend" / "data" / "inputs" / "sws_rounds.csv"
SPEC = json.loads((EXP / "E40_SWS_CPI_Tiers" / "label_spec.json").read_text())["thresholds"]
E57 = FINAL / "aipheed-backend-aligned/experiments/E57_E56_Rolling_Origin_Test/sealed/predictions.csv"
E63 = FINAL / "aipheed-backend-aligned/experiments/E63_Lead_Time_Study/sealed/predictions.csv"
BASE = EXP / "E55_Food_Insecurity_LightGBM/runs/baselines_20261017T154832Z/rows_baselines.csv"
FIRI2_ROWS = FT / "out/firi2/rows.csv"
FIRI2_REG = FT / "out/firi2/regional.csv"
PROV = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
        "PH040500000": "Batangas"}
RNG = np.random.default_rng(2026)


def qi(q):
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i):
    return f"{i // 4}-Q{i % 4 + 1}"


# ------------------------------------------------------------------------------------------------ labels
def labels():
    y = pd.read_csv(YOY, dtype={"province_code": str})
    assert y["reference_month"].min() >= "2021-01", "pre-2021 data in CPI file"
    y["q"] = y["reference_month"].str[:4].astype(int) * 4 + (y["reference_month"].str[5:7].astype(int) - 1) // 3
    g = y.groupby(["province_code", "commodity", "q"])["yoy_pct"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] == 3]
    F = g[g["commodity"] == "food"][["province_code", "q", "mean"]].rename(columns={"mean": "F"})
    HL = g[g["commodity"] == "all_items"][["province_code", "q", "mean"]].rename(columns={"mean": "HL"})
    Y = F.merge(HL, on=["province_code", "q"])
    Y["PS"] = ((Y["F"] > Y["province_code"].map(SPEC["food"])) |
               ((Y["F"] - Y["HL"]) > Y["province_code"].map(SPEC["gap"]))).astype(int)
    r = pd.read_csv(SWS)
    assert r["quarter"].min() >= "2021-Q1"
    r["q"] = r["quarter"].map(qi)
    H_all = r.groupby("q")["H"].mean()
    H_app = r[r["definition_A"].astype(str) == "True"].groupby("q")["H"].mean()
    Y["H_all"], Y["H_app"] = Y["q"].map(H_all), Y["q"].map(H_app)
    Y["T43"] = np.where(Y["H_all"].notna(), ((Y["H_all"] > SPEC["H"]) & (Y["PS"] == 1)).astype(float), np.nan)
    Y["T43_app"] = np.where(Y["H_app"].notna(), ((Y["H_app"] > SPEC["H"]) & (Y["PS"] == 1)).astype(float), np.nan)
    Y["target"] = Y["q"].map(qs)
    return Y, r


# ------------------------------------------------------------------------------------------------ metrics
def wilson(k, n, z=1.959964):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def auc(y, p):
    y, p = np.asarray(y), np.asarray(p, float)
    pos, neg = p[y == 1], p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return None
    s = 0.0
    for a in pos:
        s += (neg < a).sum() + 0.5 * (neg == a).sum()
    return s / (len(pos) * len(neg))


def metrics(y, p, thr=0.5):
    y, p = np.asarray(y, int), np.asarray(p, float)
    d = (p >= thr).astype(int)
    tp, fp = int(((d == 1) & (y == 1)).sum()), int(((d == 1) & (y == 0)).sum())
    fn, tn = int(((d == 0) & (y == 1)).sum()), int(((d == 0) & (y == 0)).sum())
    n = len(y)
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    precL = tn / (tn + fn) if tn + fn else None
    recL = tn / (tn + fp) if tn + fp else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    f1L = 2 * tn / (2 * tn + fn + fp) if 2 * tn + fn + fp else None
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    return {"n": n, "pos": int(y.sum()), "neg": int(n - y.sum()), "correct": tp + tn, "accuracy": (tp + tn) / n,
            "acc_wilson95": wilson(tp + tn, n), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "precision_HIGH": prec, "recall_HIGH": rec, "f1_HIGH": f1, "precision_LOW": precL, "recall_LOW": recL,
            "f1_LOW": f1L, "balanced_accuracy": None if rec is None or recL is None else (rec + recL) / 2,
            "auc_roc": auc(y, p), "brier": float(np.mean((p - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc))), "share_pred_HIGH": float(d.mean())}


def cluster_boot_acc(R, col, ycol="y", B=4000):
    qs_ = R["target"].unique()
    g = {q: R[R["target"] == q] for q in qs_}
    out = []
    for _ in range(B):
        s = RNG.choice(qs_, len(qs_), replace=True)
        D = pd.concat([g[q] for q in s])
        out.append(((D[col] >= 0.5).astype(int) == D[ycol]).mean())
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def paired(R, a, b, ycol="y", B=4000):
    """Arm a minus arm b: Brier difference with quarter-cluster bootstrap CI, quarter sign test, McNemar exact."""
    R = R.copy()
    R["la"], R["lb"] = (R[a] - R[ycol]) ** 2, (R[b] - R[ycol]) ** 2
    per_q = R.groupby("target")[["la", "lb"]].mean()
    diff = per_q["la"] - per_q["lb"]
    w, l_ = int((diff < -1e-12).sum()), int((diff > 1e-12).sum())
    qs_ = per_q.index.to_numpy()
    cnt = R.groupby("target").size()
    bs = []
    for _ in range(B):
        s = RNG.choice(qs_, len(qs_), replace=True)
        bs.append(float((per_q.loc[s, "la"] * cnt.loc[s].values).sum() / cnt.loc[s].sum()
                        - (per_q.loc[s, "lb"] * cnt.loc[s].values).sum() / cnt.loc[s].sum()))
    ca = (R[a] >= .5).astype(int) == R[ycol]
    cb = (R[b] >= .5).astype(int) == R[ycol]
    n10, n01 = int((ca & ~cb).sum()), int((~ca & cb).sum())
    acc_q = R.assign(ca=ca, cb=cb).groupby("target")[["ca", "cb"]].mean()
    dq = acc_q["ca"] - acc_q["cb"]
    aw, al = int((dq > 0).sum()), int((dq < 0).sum())
    return {"brier_diff": float(R["la"].mean() - R["lb"].mean()), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "quarter_brier_wins_a": w, "quarter_brier_losses_a": l_,
            "sign_p": float(binomtest(w, w + l_, .5).pvalue) if w + l_ else 1.0,
            "mcnemar_a_right_only": n10, "mcnemar_b_right_only": n01,
            "mcnemar_p": float(binomtest(n10, n10 + n01, .5).pvalue) if n10 + n01 else 1.0,
            "acc_diff": float(ca.mean() - cb.mean()), "quarter_acc_wins_a": aw, "quarter_acc_losses_a": al,
            "acc_quarter_sign_p": float(binomtest(aw, aw + al, .5).pvalue) if aw + al else 1.0}


def calibration(y, p, bins=(0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0001)):
    y, p = np.asarray(y), np.asarray(p, float)
    rows, ece = [], 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum():
            rows.append({"bin": f"[{lo:.1f},{min(hi, 1):.1f})", "n": int(m.sum()), "mean_p": float(p[m].mean()),
                         "obs_rate": float(y[m].mean())})
            ece += m.sum() / len(y) * abs(p[m].mean() - y[m].mean())
    ci = None
    if len(set(y)) > 1:
        lp = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
        # calibration-in-the-large and slope by simple logistic fit (Newton)
        X = np.c_[np.ones_like(lp), lp]
        b = np.zeros(2)
        for _ in range(50):
            mu = 1 / (1 + np.exp(-X @ b))
            W = mu * (1 - mu) + 1e-9
            b = b + np.linalg.solve(X.T @ (X * W[:, None]), X.T @ (y - mu))
        ci = {"intercept": float(b[0]), "slope": float(b[1]), "mean_p": float(p.mean()), "obs_rate": float(y.mean())}
    return {"bins": rows, "ece": float(ece), "logistic_recal": ci}


def icc(R, ycol="y"):
    """One-way ANOVA ICC of the label within target quarters (how much provinces in a quarter move together)."""
    g = R.groupby("target")[ycol]
    k = g.size().mean()
    msb = (g.size() * (g.mean() - R[ycol].mean()) ** 2).sum() / (g.ngroups - 1)
    msw = ((R[ycol] - g.transform("mean")) ** 2).sum() / (len(R) - g.ngroups)
    v = (msb - msw) / (msb + (k - 1) * msw) if (msb + (k - 1) * msw) else float("nan")
    deff = 1 + (k - 1) * v
    return {"icc": float(v), "design_effect": float(deff), "effective_n": float(len(R) / deff) if deff > 0 else None}


# ------------------------------------------------------------------------------------------------ main
def main():
    out = {}
    Y, sws = labels()
    lab = Y[["province_code", "target", "T43", "T43_app", "PS", "H_all", "H_app", "F", "HL"]]

    # ---- Lead-2 (E57) and Leads 1-3 (E63)
    E = pd.read_csv(E57, dtype={"province_code": str}).merge(lab, on=["province_code", "target"], how="left")
    assert E["T43"].notna().all()
    E["y"] = E["T43"].astype(int)
    S = pd.read_csv(E63, dtype={"province_code": str}).merge(lab, on=["province_code", "target"], how="left")
    assert S["T43"].notna().all()
    S["y"] = S["T43"].astype(int)

    # timing checks
    tim = {}
    for name, D, k in (("E57", E.assign(lead=2), None), ("E63", S, None)):
        D = D.copy()
        D["oq"] = D["origin_quarter"].map(qi)
        nxt = D["oq"] + 1
        exp_issue = pd.to_datetime([f"{n // 4}-{(n % 4) * 3 + 1:02d}-01" for n in nxt])
        tim[name] = {"issue_is_first_day_after_origin_quarter": bool((pd.to_datetime(D["issue_date"]).values == exp_issue.values).all()),
                     "target_minus_origin_equals_lead": bool(((D["target"].map(qi) - D["oq"]) == D["lead"]).all()),
                     "duplicate_rows": int(D.duplicated(["lead", "target", "province_code"]).sum()),
                     "persist_from_before_issue_quarter": bool((D["PERSIST_from"].dropna().map(qi) < D.loc[D["PERSIST_from"].notna(), "oq"] + 1).all())}
        # persistence label source: were all SWS rounds of PERSIST_from published before the issue date?
        pub = sws.assign(published=pd.to_datetime(sws["published"])).groupby("quarter")["published"].max()
        ok = [(pd.Timestamp(i) > pub.get(pf, pd.Timestamp("2100-01-01"))) for pf, i in zip(D["PERSIST_from"], D["issue_date"]) if isinstance(pf, str)]
        tim[name]["persist_label_sws_published_before_issue"] = bool(all(ok))
        # was the target quarter's own SWS round published before the issue date? (must be False for every row)
        tpub = [pub.get(t) for t in D["target"]]
        tim[name]["any_target_sws_published_before_issue"] = bool(any((tp is not None and tp < pd.Timestamp(i)) for tp, i in zip(tpub, D["issue_date"])))
    out["timing"] = tim

    # T43 equals PS on evaluated rows?
    out["t43_equals_ps"] = {"E57_rows": int((E["T43"] == E["PS"]).sum()), "E57_n": len(E),
                            "E63_rows": int((S["T43"] == S["PS"]).sum()), "E63_n": len(S),
                            "min_H_all_on_E63_targets": float(S["H_all"].min()),
                            "T43_all_vs_approved_rounds_disagree_E57": int((E["T43"] != E["T43_app"]).sum()),
                            "T43_approved_missing_E57": int(E["T43_app"].isna().sum())}

    arms = {"LightGBM E56 P(T43)": "E56_p", "Persistence": "PERSIST_p", "Majority (always LOW)": "MAJORITY_p",
            "Climatology": "CLIM_p"}
    L2 = {name: metrics(E["y"], E[c]) for name, c in arms.items()}
    L2["LightGBM E56 P(T43)"]["acc_cluster_boot95"] = cluster_boot_acc(E, "E56_p")
    out["lead2_E57"] = {"quarters": int(E["target"].nunique()), "targets": [E["target"].min(), E["target"].max()],
                        "metrics": L2, "calibration_E56": calibration(E["y"], E["E56_p"]),
                        "paired_vs": {nm: paired(E, "E56_p", c) for nm, c in arms.items() if c != "E56_p"},
                        "icc": icc(E),
                        "by_quarter": E.assign(c=((E["E56_p"] >= .5).astype(int) == E["y"])).groupby("target").agg(
                            n=("y", "size"), pos=("y", "sum"), correct=("c", "sum"), mean_p=("E56_p", "mean")).reset_index().to_dict("records"),
                        "by_province": E.assign(c=((E["E56_p"] >= .5).astype(int) == E["y"])).groupby("province").agg(
                            n=("y", "size"), pos=("y", "sum"), correct=("c", "sum"),
                            TP=("c", lambda s: int(((E.loc[s.index, "E56_p"] >= .5) & (E.loc[s.index, "y"] == 1)).sum())),
                            FN=("c", lambda s: int(((E.loc[s.index, "E56_p"] < .5) & (E.loc[s.index, "y"] == 1)).sum()))).reset_index().to_dict("records")}
    leads = {}
    for lead, R in S.groupby("lead"):
        m = {name: metrics(R["y"], R[c]) for name, c in arms.items()}
        m["LightGBM E56 P(T43)"]["acc_cluster_boot95"] = cluster_boot_acc(R, "E56_p")
        leads[int(lead)] = {"quarters": int(R["target"].nunique()), "targets": [R["target"].min(), R["target"].max()],
                            "train_rows_range": [int(R["n_train_rows"].min()), int(R["n_train_rows"].max())],
                            "train_quarters_range": [int(R["n_train_q"].min()), int(R["n_train_q"].max())],
                            "metrics": m, "calibration_E56": calibration(R["y"], R["E56_p"]),
                            "paired_vs": {nm: paired(R, "E56_p", c) for nm, c in arms.items() if c != "E56_p"},
                            "icc": icc(R)}
    out["leads_E63"] = leads
    # E57 vs E63 lead-2 rows identical?
    s2 = S[S["lead"] == 2][["target", "province_code", "E56_p"]].merge(E[["target", "province_code", "E56_p"]], on=["target", "province_code"], suffixes=("_63", "_57"))
    out["E57_vs_E63_lead2"] = {"common_rows": len(s2), "max_abs_diff": float((s2["E56_p_63"] - s2["E56_p_57"]).abs().max())}

    # ---- Objective 4 baselines (45 rows)
    B = pd.read_csv(BASE, dtype={"province_code": str})
    B = B.merge(lab[["province_code", "target", "T43"]], on=["province_code", "target"], how="left")
    out["baseline_label_check"] = {"rows": len(B), "label_mismatch_vs_independent_T43": int((B["y"] != B["T43"]).sum())}
    R = B.merge(E[["target", "province_code", "E56_p", "issue_date"]], on=["target", "province_code"], how="inner")
    R["y"] = R["T43"].astype(int)
    R["MAJ_p"] = 0.0
    barms = {"LightGBM E56 (proposed)": "E56_p", "I. Naive persistence": "B1_PERSIST_p", "II. PSA-only LR": "B2_LR_GOV_p",
             "III. NLP-only LR": "B4_LR_NLP_p", "IV. Combined LR": "B6_LR_COMB_p", "Majority (always LOW)": "MAJ_p",
             "(extra) LightGBM gov-only": "B3_LGBM_GOV_p", "(extra) LightGBM NLP-only": "B5_LGBM_NLP_p"}
    out["objective4"] = {"rows": len(R), "quarters": int(R["target"].nunique()), "targets": [R["target"].min(), R["target"].max()],
                         "t_label_before_target": bool((R["t_label"].map(qi) < R["target"].map(qi)).all()),
                         "metrics": {nm: metrics(R["y"], R[c]) for nm, c in barms.items()},
                         "paired_lightgbm_vs": {nm: paired(R, "E56_p", c) for nm, c in barms.items() if c != "E56_p"},
                         "lightgbm_acc_cluster_boot95": cluster_boot_acc(R, "E56_p")}

    # ---- FIRI v2 (C3): regional outcome and T43 agreement
    F2 = pd.read_csv(FIRI2_ROWS, dtype={"province_code": str})
    G = pd.read_csv(FIRI2_REG)
    reg = {}
    for lead, D in G.groupby("lead"):
        D = D.dropna(subset=["C3"])
        D = D.rename(columns={"target": "target"})
        reg[int(lead)] = {"quarters": len(D), "C3": metrics(D["y"], D["C3"]), "H1_alone": metrics(D["y"], D["H1"]),
                          "always": metrics(D["y"], D["ALWAYS"]), "C0_v1": metrics(D["y"], D["C0"]),
                          "C3_vs_H1": paired(D.assign(target=D["target"]), "C3", "H1"),
                          "C3_vs_always": paired(D.assign(target=D["target"]), "C3", "ALWAYS")}
    out["firi2_regional"] = reg
    # independent check of the regional outcome y against SWS file
    h = sws.groupby("quarter")["H"].mean()
    G["y_indep"] = (G["target"].map(h) > SPEC["H"]).astype(float)
    G.loc[G["target"].map(h).isna(), "y_indep"] = np.nan
    out["firi2_regional_label_check"] = {"rows": len(G), "mismatch": int((G["y_indep"].notna() & (G["y_indep"] != G["y"])).sum()),
                                         "H_obs_mismatch": int((G["target"].map(h).round(4) != G["H_obs"].round(4)).sum())}
    t43 = {}
    for lead, D in F2.merge(lab[["province_code", "target", "T43"]], on=["province_code", "target"], how="inner").groupby("lead"):
        D = D.dropna(subset=["C3", "T43"])
        e = E if lead == 2 else S[S["lead"] == lead]
        D = D.merge(e[["target", "province_code"]], on=["target", "province_code"], how="inner")
        t43[int(lead)] = {"rows": len(D), "C3_vs_T43": metrics(D["T43"].astype(int), D["C3"]),
                          "share_HIGH": float((D["C3"] >= .5).mean())}
    out["firi2_vs_T43_on_lightgbm_rows"] = t43
    # province-row FIRI v2 vs regional outcome at lead 2 (each province gets the same regional y)
    P = F2[F2["lead"] == 2].merge(G[G["lead"] == 2][["target", "y"]], on="target").dropna(subset=["C3"])
    out["firi2_province_rows_vs_regional_lead2"] = metrics(P["y"], P["C3"])
    out["firi2_province_rows_icc"] = icc(P.assign(y=(P["C3"] >= .5).astype(int)))

    (HERE / "audit_results.json").write_text(json.dumps(out, indent=1, default=lambda o: None if o is None else (float(o) if isinstance(o, (np.floating, np.integer)) else str(o))))
    # concise print
    def p(m):
        return (f"n={m['n']} pos={m['pos']} acc={m['correct']}/{m['n']}={m['accuracy']:.4f} W95=[{m['acc_wilson95'][0]:.3f},{m['acc_wilson95'][1]:.3f}] "
                f"TP/FP/FN/TN={m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} precH={m['precision_HIGH']} recH={m['recall_HIGH']} "
                f"f1H={m['f1_HIGH']} recL={m['recall_LOW']} bal={m['balanced_accuracy']} auc={m['auc_roc']} brier={m['brier']:.4f} ll={m['log_loss']:.4f}")
    print("TIMING", json.dumps(tim, indent=0))
    print("T43==PS", out["t43_equals_ps"])
    print("--- LEAD 2 (E57)", out["lead2_E57"]["quarters"], out["lead2_E57"]["targets"])
    for k, m in L2.items():
        print(" ", k, p(m))
    print("  boot", L2["LightGBM E56 P(T43)"]["acc_cluster_boot95"], "ICC", out["lead2_E57"]["icc"])
    print("  calib", out["lead2_E57"]["calibration_E56"])
    for k, v in out["lead2_E57"]["paired_vs"].items():
        print("  vs", k, v)
    for lead, v in leads.items():
        print(f"--- LEAD {lead} (E63)", v["quarters"], v["targets"], "train rows", v["train_rows_range"], "train q", v["train_quarters_range"])
        for k, m in v["metrics"].items():
            print(" ", k, p(m))
        for k, w in v["paired_vs"].items():
            print("  vs", k, {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in w.items()})
        print("  calib ece", round(v["calibration_E56"]["ece"], 4), v["calibration_E56"]["logistic_recal"], "ICC", v["icc"])
    print("E57 vs E63", out["E57_vs_E63_lead2"])
    print("--- OBJ4", out["objective4"]["rows"], out["objective4"]["targets"], out["baseline_label_check"], "tlabel<target", out["objective4"]["t_label_before_target"])
    for k, m in out["objective4"]["metrics"].items():
        print(" ", k, p(m))
    for k, v in out["objective4"]["paired_lightgbm_vs"].items():
        print("  vs", k, {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()})
    print("  boot", out["objective4"]["lightgbm_acc_cluster_boot95"])
    print("--- FIRI v2 regional")
    for lead, v in reg.items():
        print(" lead", lead, "C3", p(v["C3"]))
        print("        H1", p(v["H1_alone"]))
        print("        ALWAYS", p(v["always"]))
        print("        vsH1", {k: (round(x, 4) if isinstance(x, float) else x) for k, x in v["C3_vs_H1"].items()})
    print("  label check", out["firi2_regional_label_check"])
    for lead, v in t43.items():
        print(" FIRI v2 vs T43 lead", lead, v["rows"], p(v["C3_vs_T43"]), "shareHIGH", round(v["share_HIGH"], 3))
    print(" FIRI v2 province rows vs regional y lead2", p(out["firi2_province_rows_vs_regional_lead2"]), out["firi2_province_rows_icc"])
    print(" by quarter", out["lead2_E57"]["by_quarter"])
    print(" by province", out["lead2_E57"]["by_province"])


if __name__ == "__main__":
    main()
