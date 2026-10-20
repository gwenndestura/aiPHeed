"""E70 step 2 (PROTOCOL sections 2, 5, 6): read the sealed E70 forecasts, rebuild the labels independently from the
raw files of the library export, and apply every pre-registered metric and decision rule.

    set AIPHEED_EXP=<clean export>\\aipheed-backend-aligned\\experiments
    python -B runner/e70_score.py                -> out/score.json, tables/*.md
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e70_metrics as MT  # noqa: E402

np, pd = MT.np, MT.pd
binomtest = MT.binomtest
E70 = HERE.parent
EXP = Path(os.environ["AIPHEED_EXP"])
ROOT = EXP.parents[1]
YOY = EXP / "E40_SWS_CPI_Tiers" / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv"
SWS = ROOT / "backend" / "data" / "inputs" / "sws_rounds.csv"
SPEC = json.loads((EXP / "E40_SWS_CPI_Tiers" / "label_spec.json").read_text())["thresholds"]
E63 = EXP / "E63_Lead_Time_Study" / "sealed" / "predictions.csv"
BASE = EXP / "E55_Food_Insecurity_LightGBM" / "runs" / "baselines_20261017T154832Z" / "rows_baselines.csv"
NEWS = EXP / "E40_SWS_CPI_Tiers" / "runs" / "triggers" / "composition.csv"
SEALED = E70 / "sealed"
MAIN = ["R0", "A1", "A2", "S0"]
ARM_NAMES = {"R0": "R0 E56-TUNED (reference)", "A1": "A1 STABLE", "A2": "A2 SHRINK", "S0": "S0 STRUCT (price projection only)",
             "PERSIST": "Naive persistence", "MAJORITY": "Majority (as-of)", "CLIM": "Climatology (as-of)",
             "PROVCLIM": "Province climatology (as-of)"}
THR = 0.5


def qi(q):
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i):
    return f"{i // 4}-Q{i % 4 + 1}"


def check_seal(name):
    p = SEALED / name
    want = (SEALED / f"{name}.sha256").read_text().split()[0]
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    assert got == want, f"{name} does not match its seal"
    return got


# ================================================================================================ labels (independent)
def labels():
    y = pd.read_csv(YOY, dtype={"province_code": str})
    assert y["reference_month"].min() >= "2021-01"
    y["q"] = y["reference_month"].str[:4].astype(int) * 4 + (y["reference_month"].str[5:7].astype(int) - 1) // 3
    g = y.groupby(["province_code", "commodity", "q"])["yoy_pct"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] == 3]
    Fq = g[g["commodity"] == "food"][["province_code", "q", "mean"]].rename(columns={"mean": "F"})
    HL = g[g["commodity"] == "all_items"][["province_code", "q", "mean"]].rename(columns={"mean": "HL"})
    Y = Fq.merge(HL, on=["province_code", "q"])
    Y["food_hi"] = (Y["F"] > Y["province_code"].map(SPEC["food"])).astype(int)
    Y["gap_hi"] = ((Y["F"] - Y["HL"]) > Y["province_code"].map(SPEC["gap"])).astype(int)
    Y["PS"] = ((Y["food_hi"] == 1) | (Y["gap_hi"] == 1)).astype(int)
    r = pd.read_csv(SWS)
    assert r["quarter"].min() >= "2021-Q1"
    r["q"] = r["quarter"].map(qi)
    H_all = r.groupby("q")["H"].mean()
    H_app = r[r["definition_A"].astype(str) == "True"].groupby("q")["H"].mean()
    Y["H_all"], Y["H_app"] = Y["q"].map(H_all), Y["q"].map(H_app)
    Y["T43"] = np.where(Y["H_all"].notna(), ((Y["H_all"] > SPEC["H"]) & (Y["PS"] == 1)).astype(float), np.nan)
    Y["T43_app"] = np.where(Y["H_app"].notna(), ((Y["H_app"] > SPEC["H"]) & (Y["PS"] == 1)).astype(float), np.nan)
    Y["target"] = Y["q"].map(qs)
    return Y, r, H_all, H_app


# ================================================================================================ helpers
def within_quarter_auc(R, col):
    num = den = 0.0
    for _, g in R.groupby("target"):
        p, y = g[col].to_numpy(float), g["y"].to_numpy(int)
        for i in np.where(y == 1)[0]:
            for j in np.where(y == 0)[0]:
                den += 1
                num += 1.0 if p[i] > p[j] else (0.5 if p[i] == p[j] else 0.0)
    return {"auc": num / den if den else None, "pairs": int(den)}


def full(R, col):
    m = MT.metrics(R["y"], R[col], THR)
    m["acc_cluster_boot95"] = MT.cluster_boot_acc(R, col)
    m["within_quarter"] = within_quarter_auc(R, col)
    m["calibration"] = MT.calibration(R["y"].to_numpy(), R[col].to_numpy())
    return m


def by(R, col, key):
    d = (R[col] >= THR).astype(int)
    out = []
    for k, g in R.assign(d=d).groupby(key):
        out.append({key: k, "n": int(len(g)), "HIGH": int(g["y"].sum()), "correct": int((g["d"] == g["y"]).sum()),
                    "TP": int(((g["d"] == 1) & (g["y"] == 1)).sum()), "FN": int(((g["d"] == 0) & (g["y"] == 1)).sum()),
                    "FP": int(((g["d"] == 1) & (g["y"] == 0)).sum()), "mean_p": float(g[col].mean())})
    return out


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    k, out, run = len(items), {}, 0.0
    for i, (name, p) in enumerate(items):
        run = max(run, min(1.0, (k - i) * p))
        out[name] = run
    return out


def fmt(x, d=3):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def mrow(name, m):
    w = m["acc_wilson95"]
    return (f"| {name} | {m['correct']}/{m['n']} | {fmt(m['accuracy'])} [{fmt(w[0])}, {fmt(w[1])}] | "
            f"{m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} | {fmt(m['precision_HIGH'])} | {fmt(m['recall_HIGH'])} | "
            f"{fmt(m['f1_HIGH'])} | {fmt(m['recall_LOW'])} | {fmt(m['balanced_accuracy'])} | {fmt(m['auc_roc'])} | "
            f"{fmt(m['within_quarter']['auc'])} | {fmt(m['brier'])} | "
            f"{fmt((m['calibration']['logistic_recal'] or {}).get('slope'), 2)} |")


HDR = ("| Arm | Correct/n | Accuracy [Wilson 95%] | TP/FP/FN/TN | Prec H | Rec H | F1 H | Rec L | Bal acc | AUC | "
       "Within-q AUC | Brier | Cal. slope |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def prow(name, p):
    return (f"| {name} | {p['brier_diff']:+.3f} [{p['ci95'][0]:+.3f}, {p['ci95'][1]:+.3f}] | "
            f"{p['quarter_brier_wins_a']}/{p['quarter_brier_losses_a']} (p {p['sign_p']:.3f}"
            f"{', Holm ' + format(p['holm_p'], '.3f') if 'holm_p' in p else ''}) | "
            f"{p['mcnemar_a_right_only']}/{p['mcnemar_b_right_only']} (p {p['mcnemar_p']:.3f}) | {p['acc_diff']:+.3f} |")


PHDR = ("| Comparison (a − b) | Δ Brier [quarter-bootstrap 95% CI] | Quarter Brier wins/losses (two-sided sign p) | "
        "McNemar a-only/b-only (p) | Δ accuracy |\n|---|---|---|---|---|")


# ================================================================================================ main
def main():
    out = {"seals": {n: check_seal(n) for n in ("predictions.csv", "prospective.csv", "ablations.csv")}}
    Y, sws, H_all, H_app = labels()
    lab = Y[["province_code", "target", "T43", "T43_app", "PS", "food_hi", "gap_hi", "H_all", "H_app", "F", "HL"]]
    P = pd.read_csv(SEALED / "predictions.csv", dtype={"province_code": str})
    S = pd.read_csv(E63, dtype={"province_code": str})
    base_cols = ["PERSIST_p", "PERSIST_from", "MAJORITY_p", "CLIM_p", "PROVCLIM_p"]
    P = P.merge(S[["lead", "origin_quarter", "province_code", "E56_p"] + base_cols],
                on=["lead", "origin_quarter", "province_code"], how="left")
    assert P["E56_p"].notna().all() and float((P["R0_p"] - P["E56_p"]).abs().max()) < 1e-9
    P = P.merge(lab, on=["province_code", "target"], how="left")
    assert P["T43"].notna().all()
    P["y"] = P["T43"].astype(int)
    tables = []

    # ---------------------------------------------------------------- 2.1 target audit
    win = [q for q in H_app.index if qi("2021-Q1") <= q <= qi("2022-Q4")]
    hw = H_app.loc[win]
    ta = {"hunger_window_quarter_means": {qs(q): float(v) for q, v in hw.items()},
          "H_threshold_frozen": SPEC["H"], "by_lead": {}}
    for lead, R in P.groupby("lead"):
        d = {"rows": int(len(R)), "T43_equals_PS": int((R["T43"] == R["PS"]).sum()),
             "hunger_binding_rows": int((R["T43"] != R["PS"]).sum()),
             "min_H_all_target": float(R["H_all"].min()), "HIGH": int(R["y"].sum()),
             "HIGH_via_food_only": int(((R["y"] == 1) & (R["food_hi"] == 1) & (R["gap_hi"] == 0)).sum()),
             "HIGH_via_gap_only": int(((R["y"] == 1) & (R["food_hi"] == 0) & (R["gap_hi"] == 1)).sum()),
             "HIGH_via_both": int(((R["y"] == 1) & (R["food_hi"] == 1) & (R["gap_hi"] == 1)).sum()),
             "T43_approved_missing": int(R["T43_app"].isna().sum()),
             "T43_approved_disagree": int(((R["T43_app"] != R["T43"]) & R["T43_app"].notna()).sum()),
             "threshold_sensitivity": {}}
        for pc in (25, 50, 60, 75, 90):
            th = float(np.percentile(hw.to_numpy(), pc))
            t = ((R["H_all"] > th) & (R["PS"] == 1)).astype(int)
            d["threshold_sensitivity"][f"P{pc}={th:.2f}"] = {"T43_equals_PS": int((t == R["PS"]).sum()),
                                                            "prevalence": float(t.mean())}
        ta["by_lead"][int(lead)] = d
    out["target_audit"] = ta
    t = ["## Target audit (PROTOCOL §2.1)\n",
         f"2021–22 approved-round hunger quarter means: {', '.join(f'{k} {v:.2f}' for k, v in ta['hunger_window_quarter_means'].items())}; frozen threshold H = {SPEC['H']}.\n",
         "| Lead | Rows | T43 = PS | Hunger condition binding | Min hunger in target quarters | HIGH | HIGH via food only / gap only / both | T43 approved-rounds missing / disagree |",
         "|---|---|---|---|---|---|---|---|"]
    for lead, d in ta["by_lead"].items():
        t.append(f"| {lead} | {d['rows']} | {d['T43_equals_PS']} | {d['hunger_binding_rows']} | {d['min_H_all_target']:.1f} | "
                 f"{d['HIGH']} | {d['HIGH_via_food_only']} / {d['HIGH_via_gap_only']} / {d['HIGH_via_both']} | "
                 f"{d['T43_approved_missing']} / {d['T43_approved_disagree']} |")
    t.append("\nThreshold sensitivity (hunger threshold at 2021–22 percentiles; rows where T43 = PS, of all rows):\n")
    t.append("| Lead | " + " | ".join(ta["by_lead"][2]["threshold_sensitivity"]) + " |")
    t.append("|---" * 6 + "|")
    for lead, d in ta["by_lead"].items():
        t.append(f"| {lead} | " + " | ".join(f"{v['T43_equals_PS']}/{d['rows']}" for v in d["threshold_sensitivity"].values()) + " |")
    tables.append("\n".join(t))

    # ---------------------------------------------------------------- leads: metrics, paired, decision inputs
    arms = MAIN + ["PERSIST", "MAJORITY", "CLIM", "PROVCLIM"]
    out["leads"] = {}
    for lead, R in P.groupby("lead"):
        R = R.reset_index(drop=True)
        res = {"quarters": int(R["target"].nunique()), "targets": [R["target"].min(), R["target"].max()],
               "rows": int(len(R)), "HIGH": int(R["y"].sum()), "icc": MT.icc(R),
               "metrics": {a: full(R, f"{a}_p") for a in arms}}
        pv = {}
        for a in ["A1", "A2", "S0"]:
            pv[f"{a} vs R0"] = MT.paired(R, f"{a}_p", "R0_p")
        for a in MAIN:
            for b in ["PERSIST", "MAJORITY", "CLIM", "PROVCLIM"]:
                pv[f"{a} vs {b}"] = MT.paired(R, f"{a}_p", f"{b}_p")
        hp = holm({k: pv[k]["sign_p"] for k in ("A1 vs R0", "A2 vs R0")})
        for k, v in hp.items():
            pv[k]["holm_p"] = v
        res["paired"] = pv
        res["by_quarter"] = {a: by(R, f"{a}_p", "target") for a in MAIN}
        res["by_province"] = {a: by(R, f"{a}_p", "province") for a in MAIN}
        # E63 section 8 horizon criterion per arm
        res["reliable_horizon_criterion"] = {
            a: all(pv[f"{a} vs {b}"]["ci95"][1] < 0 and pv[f"{a} vs {b}"]["sign_p"] < 0.05 for b in ("PERSIST", "CLIM"))
            for a in MAIN}
        out["leads"][int(lead)] = res
        t = [f"## Lead {lead}: {res['rows']} rows, {res['quarters']} target quarters ({res['targets'][0]} … {res['targets'][1]}), "
             f"{res['HIGH']} HIGH; ICC {res['icc']['icc']:.2f}, effective n ≈ {res['icc']['effective_n']:.0f}\n", HDR]
        for a in arms:
            t.append(mrow(ARM_NAMES[a], res["metrics"][a]))
        t.append("\n" + PHDR)
        for k, v in pv.items():
            t.append(prow(k, v))
        t.append("\nE63 §8 reliable-horizon criterion met: " + ", ".join(f"{a} {'YES' if v else 'no'}" for a, v in res["reliable_horizon_criterion"].items()))
        tables.append("\n".join(t))

    # ---------------------------------------------------------------- decision rule 1 (PROTOCOL section 6)
    L2, L1, L3 = out["leads"][2], out["leads"][1], out["leads"][3]
    dec = {}
    for a in ("A1", "A2"):
        p2 = L2["paired"][f"{a} vs R0"]
        crit = {"brier_ci_upper_below_0": p2["ci95"][1] < 0, "holm_sign_p_below_0.05": p2["holm_p"] < 0.05,
                "recall_HIGH_ge_R0": (L2["metrics"][a]["recall_HIGH"] or 0) >= (L2["metrics"]["R0"]["recall_HIGH"] or 0),
                "lead1_not_credibly_worse": L1["paired"][f"{a} vs R0"]["ci95"][0] <= 0,
                "lead3_not_credibly_worse": L3["paired"][f"{a} vs R0"]["ci95"][0] <= 0}
        dec[a] = {"criteria": crit, "passes": all(crit.values())}
    sel = next((a for a in ("A1", "A2") if dec[a]["passes"]), "R0")
    m = L2["metrics"][sel]
    goal = {"selected_arm": sel, "accuracy": m["accuracy"], "correct": m["correct"], "n": m["n"],
            "recall_HIGH": m["recall_HIGH"], "balanced_accuracy": m["balanced_accuracy"],
            "met": bool(m["accuracy"] >= 0.80 and (m["recall_HIGH"] or 0) >= 0.50 and (m["balanced_accuracy"] or 0) >= 0.70),
            "any_arm_ge_0.80": {a: L2["metrics"][a]["accuracy"] >= 0.80 for a in MAIN}}
    out["decision"] = {"rule1": dec, "goal_80": goal}
    t = ["## Decision rules (PROTOCOL §6)\n", "| Candidate | Brier CI upper < 0 | Holm sign p < 0.05 | HIGH recall ≥ R0 | Lead-1 not worse | Lead-3 not worse | Passes |",
         "|---|---|---|---|---|---|---|"]
    for a, v in dec.items():
        c = v["criteria"]
        t.append(f"| {a} | {c['brier_ci_upper_below_0']} | {c['holm_sign_p_below_0.05']} | {c['recall_HIGH_ge_R0']} | "
                 f"{c['lead1_not_credibly_worse']} | {c['lead3_not_credibly_worse']} | **{v['passes']}** |")
    t.append(f"\nSelected arm: **{sel}**. Lead-2 accuracy {m['correct']}/{m['n']} = {m['accuracy']:.3f}, HIGH recall "
             f"{fmt(m['recall_HIGH'])}, balanced accuracy {fmt(m['balanced_accuracy'])}. **80% goal met: {goal['met']}.**")
    tables.append("\n".join(t))

    # ---------------------------------------------------------------- error decomposition (R0, lead 2)
    R = P[P["lead"] == 2].copy()
    errs = []
    for r in R.itertuples():
        d = int(r.R0_p >= THR)
        if d == r.y:
            continue
        if r.y == 1:
            comp = "price component (P_price < 0.5)" if r.R0_p_price < THR else "hunger component (P_price ≥ 0.5, P_hunger pulled the product below 0.5)"
        else:
            comp = "price component (P_price ≥ 0.5, PS = 0)"
        errs.append({"target": r.target, "province": r.province, "y": int(r.y), "p": float(r.R0_p),
                     "p_price": float(r.R0_p_price), "p_hunger": float(r.p_hunger), "H_target": float(r.H_all),
                     "component": comp})
    out["lead2_R0_errors"] = errs
    t = ["## Lead-2 R0 errors by component\n", "| Target | Province | Observed | P | P_price | P_hunger | Hunger in target quarter | Component |",
         "|---|---|---|---|---|---|---|---|"]
    for e in errs:
        t.append(f"| {e['target']} | {e['province']} | {'HIGH' if e['y'] else 'LOW'} | {e['p']:.3f} | {e['p_price']:.3f} | "
                 f"{e['p_hunger']:.3f} | {e['H_target']:.1f} | {e['component']} |")
    tables.append("\n".join(t))

    # ---------------------------------------------------------------- data sufficiency (news at origin)
    N = pd.read_csv(NEWS, dtype={"province_code": str})
    N = N.rename(columns={"quarter": "origin_quarter"})[["province_code", "origin_quarter", "n_articles"]]
    R = R.merge(N, on=["province_code", "origin_quarter"], how="left")
    R["news_band"] = pd.cut(R["n_articles"].fillna(0), [-1, 0, 4, 1e9], labels=["0 articles", "1–4", "≥5"]).astype(str)
    out["lead2_by_news_sufficiency"] = by(R, "R0_p", "news_band")
    t = ["## Lead-2 R0 by news volume in the origin quarter (E40 composition counts)\n",
         "| News band | n | HIGH | Correct | FN | FP |", "|---|---|---|---|---|---|"]
    for b in out["lead2_by_news_sufficiency"]:
        t.append(f"| {b['news_band']} | {b['n']} | {b['HIGH']} | {b['correct']} | {b['FN']} | {b['FP']} |")
    tables.append("\n".join(t))

    # ---------------------------------------------------------------- ablations and single-group models (lead 2)
    A = pd.read_csv(SEALED / "ablations.csv", dtype={"province_code": str})
    A = A.merge(P[P["lead"] == 2][["origin_quarter", "province_code", "y", "R0_p", "target"]],
                on=["origin_quarter", "province_code", "target"], how="inner")
    assert len(A) == 50
    acols = [c[:-2] for c in A.columns if c.endswith("_p") and (c.startswith("ABL_") or c.startswith("ONLY_"))]
    ab = {}
    for a in acols:
        ab[a] = {"metrics": full(A, f"{a}_p"), "vs_R0": MT.paired(A, f"{a}_p", "R0_p"),
                 "identical_to_R0_rows": int((A[f"{a}_p"] - A["R0_p"]).abs().lt(1e-12).sum())}
        if a.startswith("ABL_"):
            ab[a]["group_adds_value"] = ab[a]["vs_R0"]["ci95"][0] > 0
    out["ablations"] = ab
    t = ["## Lead-2 ablations and single-group models (50 rows)\n", HDR]
    for a in acols:
        t.append(mrow(a, ab[a]["metrics"]))
    t.append("\n" + PHDR)
    for a in acols:
        t.append(prow(f"{a} vs R0", ab[a]["vs_R0"]))
    t.append("\nGroup adds value (PROTOCOL §6.4, removing it worsens Brier with CI lower bound > 0): " +
             ", ".join(f"{a[4:]} {'YES' if ab[a]['group_adds_value'] else 'no'} ({ab[a]['identical_to_R0_rows']}/50 rows identical to R0)"
                       for a in acols if a.startswith("ABL_")))
    tables.append("\n".join(t))

    # ---------------------------------------------------------------- Objective 4 baselines (45 rows)
    Bf = pd.read_csv(BASE, dtype={"province_code": str})
    O = Bf.merge(P[P["lead"] == 2][["target", "province_code", "y", "R0_p", "A1_p", "A2_p", "S0_p"]],
                 on=["target", "province_code"], how="inner", suffixes=("_base", ""))
    assert len(O) == 45 and (O["y_base"] == O["y"]).all()
    O["MAJ_p"] = (O["CLIM_p"] >= 0.5).astype(float)
    bl = {"I. Naive persistence": "B1_PERSIST_p", "II. PSA-only LR": "B2_LR_GOV_p", "III. NLP-only LR": "B4_LR_NLP_p",
          "IV. Combined LR": "B6_LR_COMB_p", "(extra) LightGBM PSA/gov-only": "B3_LGBM_GOV_p",
          "(extra) LightGBM NLP-only": "B5_LGBM_NLP_p", "(extra) Majority (as-of)": "MAJ_p"}
    o4 = {"rows": int(len(O)), "HIGH": int(O["y"].sum()), "icc": MT.icc(O),
          "metrics": {a: full(O, f"{a}_p") for a in MAIN} | {k: full(O, v) for k, v in bl.items()}, "paired": {}}
    for a in MAIN:
        fam = {k: MT.paired(O, f"{a}_p", v) for k, v in bl.items()}
        hp = holm({k: fam[k]["sign_p"] for k in list(bl)[:4]})
        for k in hp:
            fam[k]["holm_p"] = hp[k]
            fam[k]["credible_advantage"] = fam[k]["ci95"][1] < 0 and hp[k] < 0.05
        o4["paired"][a] = fam
    out["objective4"] = o4
    t = [f"## Objective 4: same 45 rows (targets 2024-Q3 … 2026-Q3), {o4['HIGH']} HIGH\n", HDR]
    for k, m in o4["metrics"].items():
        t.append(mrow(ARM_NAMES.get(k, k), m))
    for a in MAIN:
        t.append(f"\n**{ARM_NAMES[a]} vs baselines** (Holm over the four required baselines)\n\n" + PHDR)
        for k, v in o4["paired"][a].items():
            t.append(prow(f"{a} − {k}", v) + (f" credible: **{v['credible_advantage']}**" if "credible_advantage" in v else ""))
    tables.append("\n".join(t))

    # ---------------------------------------------------------------- DIRECT-R regional outcome
    dr = {}
    for lead, R in P.groupby("lead"):
        Q = R.groupby("target").agg(p_hunger=("p_hunger", "first"), H_all=("H_all", "first"), H_app=("H_app", "first")).reset_index()
        Q["y"] = (Q["H_all"] > SPEC["H"]).astype(int)
        Q["ALWAYS_p"] = 1.0
        dr[int(lead)] = {"quarters": int(len(Q)), "above_threshold": int(Q["y"].sum()),
                         "I7_hunger_component": MT.metrics(Q["y"], Q["p_hunger"]),
                         "always_above": MT.metrics(Q["y"], Q["ALWAYS_p"]),
                         "approved_rounds_missing": int(Q["H_app"].isna().sum())}
    out["direct_regional"] = dr
    t = ["## DIRECT-R: regional SWS hunger > 11.3 at the target quarter (one value per quarter, never per province)\n",
         "| Lead | Quarters | Above 11.3 | I7 hunger component correct | Brier | Always-above correct |", "|---|---|---|---|---|---|"]
    for lead, d in dr.items():
        t.append(f"| {lead} | {d['quarters']} | {d['above_threshold']} | {d['I7_hunger_component']['correct']}/{d['quarters']} | "
                 f"{d['I7_hunger_component']['brier']:.3f} | {d['always_above']['correct']}/{d['quarters']} |")
    t.append("\nWith no quarter below the threshold, accuracy on this direct outcome cannot separate skill from always-above.")
    tables.append("\n".join(t))

    # ---------------------------------------------------------------- prospective (no outcomes)
    Pr = pd.read_csv(SEALED / "prospective.csv", dtype={"province_code": str})
    out["prospective"] = Pr[["lead", "origin_quarter", "issue_date", "target", "province"] + [f"{a}_p" for a in MAIN]].round(4).to_dict("records")
    t = ["## Sealed prospective forecasts (outcomes not yet published)\n",
         "| Lead | Origin | Issue | Target | Province | R0 | A1 | A2 | S0 |", "|---|---|---|---|---|---|---|---|---|"]
    for r in out["prospective"]:
        t.append(f"| {r['lead']} | {r['origin_quarter']} | {r['issue_date']} | {r['target']} | {r['province']} | "
                 + " | ".join(f"{r[f'{a}_p']:.3f}" for a in MAIN) + " |")
    tables.append("\n".join(t))

    (E70 / "out").mkdir(exist_ok=True)
    (E70 / "out" / "score.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    (E70 / "tables").mkdir(exist_ok=True)
    (E70 / "tables" / "E70_TABLES.md").write_text("# E70 tables (generated by runner/e70_score.py)\n\n" + "\n\n".join(tables) + "\n", encoding="utf-8")
    print("\n\n".join(tables))


if __name__ == "__main__":
    main()
