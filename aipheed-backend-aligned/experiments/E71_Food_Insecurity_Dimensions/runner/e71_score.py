"""E71 step 2: labels, validation V1-V3, sensitivity, and the pre-registered forecast evaluation of the sealed rows.

    set AIPHEED_EXP=<clean export>\\aipheed-backend-aligned\\experiments
    python -B runner/e71_score.py      -> out/labels.csv, out/score.json, tables/E71_TABLES.md
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "E70_Objectives_Completion" / "runner"))
import e71_lib as Z  # noqa: E402
import e70_metrics as MT  # noqa: E402

H, L, np, pd = Z.H, Z.L, Z.np, Z.pd
from scipy.stats import spearmanr  # noqa: E402

E71 = Z.E71
RNG = np.random.default_rng(71)
ARMS = ["LGBM", "LGBM_NONEWS", "LR", "PSA_LR", "NLP_LR", "DIMFUSE", "PERSIST", "PROVCLIM", "MAJ"]
NAMES = {"LGBM": "LightGBM (Objective 2 model)", "LGBM_NONEWS": "LightGBM without news (ablation)",
         "LR": "IV. Logistic regression", "PSA_LR": "II. PSA-only LR", "NLP_LR": "III. NLP-only LR",
         "DIMFUSE": "DIMFUSE (dimension projection + logistic)", "PERSIST": "I. Naive persistence",
         "PROVCLIM": "Province climatology", "MAJ": "Majority"}
OBJ4 = {"PERSIST": "I", "PSA_LR": "II", "NLP_LR": "III", "LR": "IV"}


def fmt(v, d=3):
    return "—" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v:.{d}f}"


def holm(ps):
    items, out, run = sorted(ps.items(), key=lambda kv: kv[1]), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - i) * p))
        out[k] = run
    return out


def boot_spearman(a, b, B=4000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n, out = len(a), []
    for _ in range(B):
        i = RNG.integers(0, n, n)
        if len(set(a[i])) > 1 and len(set(b[i])) > 1:
            out.append(spearmanr(a[i], b[i])[0])
    return float(spearmanr(a, b)[0]), [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def mrow(name, m):
    w = m["acc_wilson95"]
    c = (m.get("calibration") or {}).get("logistic_recal") or {}
    return (f"| {name} | {m['correct']}/{m['n']} | {fmt(m['accuracy'])} [{fmt(w[0])}, {fmt(w[1])}] | {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} | "
            f"{fmt(m['precision_HIGH'])} | {fmt(m['recall_HIGH'])} | {fmt(m['f1_HIGH'])} | {fmt(m['recall_LOW'])} | "
            f"{fmt(m['balanced_accuracy'])} | {fmt(m['auc_roc'])} | {fmt(m['brier'])} | {fmt(c.get('slope'), 2)} |")


HDR = ("| Arm | Correct/n | Accuracy [Wilson 95%] | TP/FP/FN/TN | Prec H | Rec H | F1 H | Rec L | Bal acc | AUC | Brier | Cal. slope |\n"
       "|---|---|---|---|---|---|---|---|---|---|---|---|")
PHDR = "| a − b | Δ Brier [95% CI] | Quarter wins/losses (sign p; Holm) | McNemar a/b only (p) |\n|---|---|---|---|"


def prow(k, p):
    return (f"| {k} | {p['brier_diff']:+.3f} [{p['ci95'][0]:+.3f}, {p['ci95'][1]:+.3f}] | {p['quarter_brier_wins_a']}/"
            f"{p['quarter_brier_losses_a']} (p {p['sign_p']:.3f}{'; Holm ' + format(p['holm_p'], '.3f') if 'holm_p' in p else ''}) | "
            f"{p['mcnemar_a_right_only']}/{p['mcnemar_b_right_only']} (p {p['mcnemar_p']:.3f}) |")


def main():
    out, T = {}, []
    for n in ("predictions.csv", "prospective.csv"):
        want = (E71 / "sealed" / f"{n}.sha256").read_text().split()[0]
        assert hashlib.sha256((E71 / "sealed" / n).read_bytes()).hexdigest() == want, n
    d, x, _ = H.load_raw()
    ind = Z.indicators(d, x)
    ref = Z.reference(ind)
    S = Z.score(ind, ref)
    thr = Z.threshold(S)
    LAB = Z.labels(S, thr).merge(ind, on=["province_code", "q", "quarter"])
    # T43 price condition PS (E40 thresholds) for the collapse test
    spec = json.loads((Z.EXP / "E40_SWS_CPI_Tiers" / "label_spec.json").read_text())["thresholds"]
    LAB["PS"] = ((LAB["a1"] > LAB["province_code"].map(spec["food"])) | (LAB["gap"] > LAB["province_code"].map(spec["gap"]))).astype(float)
    LAB.loc[LAB["a1"].isna(), "PS"] = np.nan
    LAB["province"] = LAB["province_code"].map(L.NAMES)
    lab = LAB[LAB["HIGH"].notna()].copy()
    (E71 / "out").mkdir(exist_ok=True)
    LAB.to_csv(E71 / "out" / "labels.csv", index=False, float_format="%.6g", lineterminator="\n")

    # ---------------------------------------------------------------- label description
    prev = lab.groupby("quarter").agg(HIGH=("HIGH", "sum"), FIR71=("FIR71", "mean"), ACCESS=("ACCESS", "mean"),
                                      AVAILABILITY=("AVAILABILITY", "mean"), STABILITY=("STABILITY", "mean")).reset_index()
    out["threshold"] = thr
    out["labelled_rows"] = int(len(lab))
    out["labelled_quarters"] = [lab["quarter"].min(), lab["quarter"].max(), int(lab["quarter"].nunique())]
    T.append(f"## FIR71 labels\n\nThreshold (P60 of the 2022 reference composite): {thr:.4f}. Labelled rows {len(lab)} "
             f"({out['labelled_quarters'][0]} … {out['labelled_quarters'][1]}); HIGH share {lab['HIGH'].mean():.2f}.\n\n"
             "| Quarter | HIGH of 5 | mean FIR71 | ACCESS | AVAILABILITY | STABILITY |\n|---|---|---|---|---|---|\n" +
             "\n".join(f"| {r.quarter} | {int(r.HIGH)} | {r.FIR71:.3f} | {r.ACCESS:.3f} | {r.AVAILABILITY:.3f} | {r.STABILITY:.3f} |"
                       for r in prev.itertuples()))

    # ---------------------------------------------------------------- V1 regional outcome
    r = pd.read_csv(Z.EXP.parents[1] / "backend" / "data" / "inputs" / "sws_rounds.csv")
    hq = r.assign(q=r["quarter"].map(L.qi)).groupby("q")["H"].mean()
    reg = lab.groupby("q").agg(FIR71=("FIR71", "mean"), share=("HIGH", "mean"), n=("HIGH", "size"),
                               ACCESS=("ACCESS", "mean"), AVAILABILITY=("AVAILABILITY", "mean"),
                               STABILITY=("STABILITY", "mean")).reset_index()
    reg = reg[reg["n"] == 5]
    reg["H"] = reg["q"].map(hq)
    reg = reg.dropna(subset=["H"])
    v1 = {"quarters": int(len(reg))}
    v1["rho_FIR71_H"], v1["ci95"] = boot_spearman(reg["FIR71"], reg["H"])
    v1["supported"] = v1["ci95"][0] > 0
    for dn in Z.DIMS:
        v1[f"rho_{dn}_H"] = float(spearmanr(reg[dn], reg["H"])[0])
    v1["rho_shareHIGH_H"] = float(spearmanr(reg["share"], reg["H"])[0])
    dF, dH = np.diff(reg["FIR71"].to_numpy()), np.diff(reg["H"].to_numpy())
    cons = reg["q"].diff().iloc[1:].to_numpy() == 1
    v1["change_sign_agreement"] = [int(((np.sign(dF) == np.sign(dH)) & cons).sum()), int(cons.sum())]
    # exploratory: in-sample OLS weights of H on the regional dimension means
    Xw = np.column_stack([np.ones(len(reg))] + [reg[dn] for dn in Z.DIMS])
    beta = np.linalg.lstsq(Xw, reg["H"].to_numpy(), rcond=None)[0]
    v1["exploratory_ols_H_on_dims"] = dict(zip(["const"] + list(Z.DIMS), map(float, beta)))
    out["V1"] = v1
    T.append(f"## V1: regional outcome (SWS hunger; validation only, never an input)\n\nQuarters with all five provinces labelled "
             f"and an SWS round: {v1['quarters']}. Spearman ρ(mean FIR71, hunger) = {v1['rho_FIR71_H']:+.2f} "
             f"[{v1['ci95'][0]:+.2f}, {v1['ci95'][1]:+.2f}] → **{'SUPPORTED' if v1['supported'] else 'NOT SUPPORTED'}**. "
             f"By dimension: ACCESS {v1['rho_ACCESS_H']:+.2f}, AVAILABILITY {v1['rho_AVAILABILITY_H']:+.2f}, "
             f"STABILITY {v1['rho_STABILITY_H']:+.2f}; share HIGH {v1['rho_shareHIGH_H']:+.2f}. Consecutive-quarter change "
             f"direction agreement {v1['change_sign_agreement'][0]}/{v1['change_sign_agreement'][1]}. Exploratory in-sample OLS "
             f"of hunger on the dimensions: " + ", ".join(f"{k} {v:+.1f}" for k, v in v1["exploratory_ols_H_on_dims"].items()) + ".\n\n"
             "| Quarter | mean FIR71 | HIGH share | SWS hunger |\n|---|---|---|---|\n" +
             "\n".join(f"| {L.qs(int(r_.q))} | {r_.FIR71:.3f} | {r_.share:.1f} | {r_.H:.1f} |" for r_ in reg.itertuples()))

    # ---------------------------------------------------------------- V2 provincial cross-section
    sub = pd.read_csv(Z.EXP.parents[1] / "backend" / "data" / "inputs" / "psa_subsistence_population_2021_2023.csv",
                      dtype={"province_code": str})
    v2 = {}
    for yr_idx, yr_sub in ((2023, 2023), (2022, 2021)):
        m = lab[lab["q"] // 4 == yr_idx].groupby("province_code")["FIR71"].mean()
        s = sub[(sub["reference_year"] == yr_sub) & sub["province_code"].isin(Z.PROVS)].set_index("province_code")["subsistence_incidence_pct"]
        j = pd.concat([m, s], axis=1, keys=["FIR71", "subsistence"]).dropna()
        v2[f"FIR71_{yr_idx}_vs_subsistence_{yr_sub}"] = {"n": int(len(j)), "spearman": float(spearmanr(j["FIR71"], j["subsistence"])[0]),
                                                        "rows": {L.NAMES[k]: [round(v.FIR71, 3), v.subsistence] for k, v in j.iterrows()}}
    out["V2"] = v2
    T.append("## V2: provincial cross-section vs PSA subsistence incidence (face validity only, 5 units)\n\n" +
             "\n".join(f"- {k}: Spearman {v['spearman']:+.2f} (n {v['n']}); " + "; ".join(f"{p} {a[0]} vs {a[1]}%" for p, a in v["rows"].items())
                       for k, v in v2.items()))

    # ---------------------------------------------------------------- V3 collapse and sensitivity
    ps = lab[lab["PS"].notna()]
    v3 = {"class_equals_PS": [int((ps["HIGH"] == ps["PS"]).sum()), int(len(ps))]}
    v3["price_collapsed"] = v3["class_equals_PS"][0] / v3["class_equals_PS"][1] >= 0.90
    hi = lab[lab["HIGH"] == 1]
    v3["HIGH_largest_dimension"] = hi[list(Z.DIMS)].idxmax(axis=1).value_counts().to_dict()
    v3["HIGH_with_ACCESS_not_stressed"] = int((hi["ACCESS"] <= Z.STRESS).sum())
    v3["HIGH_n_stressed"] = hi["n_stressed"].value_counts().sort_index().to_dict()
    loo = {}
    for dn in Z.DIMS:
        S2 = Z.score(ind, ref, drop_dim=dn)
        l2 = Z.labels(S2, Z.threshold(S2))
        j = lab[["province_code", "q", "HIGH"]].merge(l2[["province_code", "q", "HIGH"]], on=["province_code", "q"], suffixes=("", "_loo")).dropna()
        loo[f"without_{dn}"] = [int((j["HIGH"] == j["HIGH_loo"]).sum()), int(len(j))]
    v3["leave_one_dimension_out_agreement"] = loo
    sens = {}
    for pc in (50, 75):
        l2 = Z.labels(S, Z.threshold(S, pc))
        j = lab[["province_code", "q", "HIGH"]].merge(l2[["province_code", "q", "HIGH"]], on=["province_code", "q"], suffixes=("", "_s")).dropna()
        sens[f"P{pc}"] = {"agreement": [int((j["HIGH"] == j["HIGH_s"]).sum()), int(len(j))], "prevalence": float(j["HIGH_s"].mean())}
    Sg = Z.score(ind, ref, access_key="gap")
    lg = Z.labels(Sg, Z.threshold(Sg))
    j = lab[["province_code", "q", "HIGH"]].merge(lg[["province_code", "q", "HIGH"]], on=["province_code", "q"], suffixes=("", "_s")).dropna()
    sens["gap_instead_of_food_yoy"] = {"agreement": [int((j["HIGH"] == j["HIGH_s"]).sum()), int(len(j))], "prevalence": float(j["HIGH_s"].mean())}
    rref = LAB[(LAB["q"] >= Z.REF[0]) & (LAB["q"] <= Z.REF[1])]
    sens["corr_food_yoy_vs_gap_reference"] = float(rref[["a1", "gap"]].corr().iloc[0, 1])
    sens["corr_food_yoy_vs_gap_all"] = float(LAB[["a1", "gap"]].corr().iloc[0, 1])
    v3["sensitivity"] = sens
    out["V3"] = v3
    T.append(f"## V3: collapse and sensitivity\n\nFIR71 class = T43 price condition on {v3['class_equals_PS'][0]}/{v3['class_equals_PS'][1]} "
             f"labelled rows → price-collapsed: **{v3['price_collapsed']}**. Largest dimension of HIGH rows: {v3['HIGH_largest_dimension']}; "
             f"HIGH rows with ACCESS not stressed (≤ 0.75): {v3['HIGH_with_ACCESS_not_stressed']} of {len(hi)}; stressed-dimension "
             f"count of HIGH rows: {v3['HIGH_n_stressed']}. Leave-one-dimension-out agreement: {loo}. Thresholds: {sens['P50']}, "
             f"{sens['P75']}. Gap variant: {sens['gap_instead_of_food_yoy']}. Correlation food YoY vs gap: reference "
             f"{sens['corr_food_yoy_vs_gap_reference']:+.2f}, all {sens['corr_food_yoy_vs_gap_all']:+.2f}.")

    # ---------------------------------------------------------------- forecasts
    P = pd.read_csv(E71 / "sealed" / "predictions.csv", dtype={"province_code": str})
    P["q_target"] = P["target"].map(L.qi)
    P = P.merge(lab[["province_code", "q", "HIGH"]].rename(columns={"q": "q_target"}), on=["province_code", "q_target"], how="left")
    assert P["HIGH"].notna().all()
    P["y"] = P["HIGH"].astype(int)
    out["nan_predictions"] = {a: int(P[f"{a}_p"].isna().sum()) for a in ARMS}
    for a in ARMS:
        P[f"{a}_p"] = P[f"{a}_p"].fillna(P["PROVCLIM_p"])          # never triggered if nan_predictions are all 0
    out["leads"] = {}
    for lead, R in P.groupby("lead"):
        R = R.reset_index(drop=True)
        res = {"rows": int(len(R)), "quarters": int(R["target"].nunique()), "targets": [R["target"].min(), R["target"].max()],
               "HIGH": int(R["y"].sum()), "icc": MT.icc(R), "metrics": {}}
        for a in ARMS:
            m = MT.metrics(R["y"], R[f"{a}_p"])
            m["calibration"] = MT.calibration(R["y"].to_numpy(), R[f"{a}_p"].to_numpy())
            res["metrics"][a] = m
        res["metrics"]["LGBM"]["acc_cluster_boot95"] = MT.cluster_boot_acc(R, "LGBM_p")
        pv = {f"LGBM vs {b}": MT.paired(R, "LGBM_p", f"{b}_p") for b in ["PERSIST", "PSA_LR", "NLP_LR", "LR", "PROVCLIM", "MAJ"]}
        hp = holm({f"LGBM vs {b}": pv[f"LGBM vs {b}"]["sign_p"] for b in OBJ4})
        for k, v in hp.items():
            pv[k]["holm_p"] = v
        pv["DIMFUSE vs LGBM"] = MT.paired(R, "DIMFUSE_p", "LGBM_p")
        pv["LGBM_NONEWS vs LGBM"] = MT.paired(R, "LGBM_NONEWS_p", "LGBM_p")
        pv["DIMFUSE vs PERSIST"] = MT.paired(R, "DIMFUSE_p", "PERSIST_p")
        res["paired"] = pv
        res["horizon_criterion"] = {a: all(MT.paired(R, f"{a}_p", f"{b}_p")["ci95"][1] < 0 and MT.paired(R, f"{a}_p", f"{b}_p")["sign_p"] < 0.05
                                           for b in ("PERSIST", "PROVCLIM")) for a in ("LGBM", "DIMFUSE")}
        dsel = "LGBM"
        res["by_quarter"] = R.assign(c=((R["LGBM_p"] >= .5).astype(int) == R["y"])).groupby("target").agg(
            n=("y", "size"), HIGH=("y", "sum"), correct=("c", "sum")).reset_index().to_dict("records")
        res["by_province"] = R.assign(c=((R["LGBM_p"] >= .5).astype(int) == R["y"]), fn=((R["LGBM_p"] < .5) & (R["y"] == 1))).groupby("province").agg(
            n=("y", "size"), HIGH=("y", "sum"), correct=("c", "sum"), FN=("fn", "sum")).reset_index().to_dict("records")
        out["leads"][int(lead)] = res
        t = [f"## Lead {lead}: {res['rows']} rows, {res['quarters']} quarters ({res['targets'][0]} … {res['targets'][1]}), {res['HIGH']} HIGH; "
             f"ICC {res['icc']['icc']:.2f}, effective n ≈ {res['icc']['effective_n']:.0f}\n", HDR]
        t += [mrow(NAMES[a], res["metrics"][a]) for a in ARMS]
        t += ["", PHDR] + [prow(k, v) for k, v in pv.items()]
        t.append("\nPer quarter (LGBM correct/n, HIGH): " + "; ".join(f"{q['target']} {q['correct']}/{q['n']} ({q['HIGH']})" for q in res["by_quarter"]))
        t.append("\nPer province (LGBM correct/n, HIGH, missed HIGH): " + "; ".join(f"{q['province']} {q['correct']}/{q['n']} ({q['HIGH']}, FN {q['FN']})" for q in res["by_province"]))
        t.append(f"\nE63-style reliable-horizon criterion (vs persistence and province climatology): {res['horizon_criterion']}")
        T.append("\n".join(t))

    # ---------------------------------------------------------------- selection and the 80% statement (PROTOCOL section 7)
    L2 = out["leads"][2]
    sel = "DIMFUSE" if L2["paired"]["DIMFUSE vs LGBM"]["ci95"][1] < 0 else "LGBM"
    m = L2["metrics"][sel]
    vsp = L2["paired"]["LGBM vs PERSIST"] if sel == "LGBM" else L2["paired"]["DIMFUSE vs PERSIST"]
    crit = {"accuracy_ge_0.80": m["accuracy"] >= 0.80, "recall_HIGH_ge_0.50": (m["recall_HIGH"] or 0) >= 0.50,
            "balanced_ge_0.70": (m["balanced_accuracy"] or 0) >= 0.70, "beats_persistence_brier_ci": vsp["ci95"][1] < 0}
    out["decision"] = {"selected": sel, "criteria": crit, "goal_80_met_as_proxy_prediction": all(crit.values()),
                       "food_insecurity_accuracy_claimable": bool(all(crit.values()) and out["V1"]["supported"]),
                       "unseen": False, "accuracy": m["accuracy"], "correct": m["correct"], "n": m["n"]}
    T.append(f"## Selection and the 80% statement (PROTOCOL §7)\n\nSelected: **{sel}**. Lead-2 {m['correct']}/{m['n']} = {m['accuracy']:.3f}, "
             f"HIGH recall {fmt(m['recall_HIGH'])}, balanced {fmt(m['balanced_accuracy'])}; vs persistence Δ Brier {vsp['brier_diff']:+.3f} "
             f"[{vsp['ci95'][0]:+.3f}, {vsp['ci95'][1]:+.3f}]. Criteria {crit}. **80% as proxy-prediction accuracy: "
             f"{all(crit.values())}. Claimable as food-insecurity accuracy: {out['decision']['food_insecurity_accuracy_claimable']}.** "
             "Evaluation quarters are not unseen.")
    Q = pd.read_csv(E71 / "sealed" / "prospective.csv", dtype={"province_code": str})
    out["prospective"] = Q[["lead", "origin_quarter", "target", "province", "LGBM_p", "DIMFUSE_p", "PERSIST_p", "LR_p"]].round(3).to_dict("records")
    T.append("## Sealed prospective forecasts (no outcome yet)\n\n| Lead | Origin | Target | Province | LGBM | DIMFUSE | PERSIST | LR |\n|---|---|---|---|---|---|---|---|\n" +
             "\n".join(f"| {r['lead']} | {r['origin_quarter']} | {r['target']} | {r['province']} | {r['LGBM_p']} | {r['DIMFUSE_p']} | {r['PERSIST_p']} | {r['LR_p']} |"
                       for r in out["prospective"]))
    (E71 / "out" / "score.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    (E71 / "tables").mkdir(exist_ok=True)
    (E71 / "tables" / "E71_TABLES.md").write_text("# E71 tables (runner/e71_score.py)\n\n" + "\n\n".join(T) + "\n", encoding="utf-8")
    print("done", out["decision"], out["V1"]["rho_FIR71_H"], out["V1"]["ci95"], out["V3"]["class_equals_PS"])


if __name__ == "__main__":
    main()
