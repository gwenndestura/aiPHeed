"""E25 scoring (FROZEN_EVALUATION_PROTOCOL.md sections 3, 6, 7, 8). Called by run_e25.py after the predictions are
sealed; reads the sealed CSVs back so every number comes from the sealed bytes."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr

import e23_lib as L
import e25lib as E

qk, qs = E.qk, E.qs
REQ_B = ["B1_naive_persistence", "B2_lr_combined", "B3_lr_gov_only", "B4_lr_nlp_only", "B5_lgbm_gov_only",
         "B6_lgbm_nlp_only"]
PROPOSED = "PROPOSED_lgbm_combined"
REFS = ["B1p_calibrated_persistence", "CLIM_training_rate", "MAJ_training_majority", "REF_always_HIGH"]
T1_CANDS = ["PCF21", "PCF21_NOW", "PCF21_SUPP", "PCF21_HIER", "PCF21_MR", "PCF21_LI", "ENS_PCF21_B1p",
            "GATE_PCF21_B1p", "CAL_PCF21", "E24_LR_P"]
T2_CANDS = ["M4_21", "M3_21", "D_HIER", "D_HIER_NOW", "E24_LR_P_T2", "ENS_M4_B1p"]
ABL = ["ABL_no_FSSI", "ABL_no_FSSI_group", "ABL_no_cpi_dev"]
DIAG = ["DIAG_ORACLE_H", "DIAG_ORACLE_D"]
FINAL = {"T1": "PCF21", "T2": "M4_21"}
B1, B1P = "B1_naive_persistence", "B1p_calibrated_persistence"


# ================================================================================================ row sets
def rowset(P: pd.DataFrame, models: list[str], tmax: str) -> tuple[pd.DataFrame, list]:
    d = P[P["model"].isin(models) & (P["t"].map(qk) <= qk(tmax))]
    cnt = d.groupby(["lead", "t", "model"]).size().unstack("model")
    full = cnt.reindex(columns=models).fillna(0).eq(5).all(axis=1)
    keep = set(full[full].index)
    dropped = sorted(set(cnt.index) - keep)
    d = d[[(a, b) in keep for a, b in zip(d["lead"], d["t"])]]
    return d.sort_values(["lead", "t", "model", "province_code"]).reset_index(drop=True), dropped


# ================================================================================================ metrics / tests
def metrics(y, s) -> dict:
    m = L.cls_metrics(y, s)
    m["balanced_accuracy"] = (None if m["recall"] is None or m["specificity"] is None
                              else (m["recall"] + m["specificity"]) / 2)
    m["log_score"] = L.logloss(y, s) if len(y) else None
    return m


def _pair(d, a, b):
    da = d[d["model"] == a].sort_values(["lead", "t", "province_code"])
    db = d[d["model"] == b].sort_values(["lead", "t", "province_code"])
    assert len(da) == len(db) and (da["province_code"].to_numpy() == db["province_code"].to_numpy()).all()
    assert (da["t"].to_numpy() == db["t"].to_numpy()).all() and (da["y"].to_numpy() == db["y"].to_numpy()).all()
    return da, db


def compare(d, a, b) -> dict:
    """a vs b on identical rows. Per-date (origin) differences, averaged over leads when d holds several leads
    (each date counts once). Negative differences = a better. One-sided exact sign-flip (MC above 16 dates)."""
    da, db = _pair(d, a, b)
    y = da["y"].to_numpy()
    sa, sb = da["score"].to_numpy(), db["score"].to_numpy()
    ca, cb = ((sa >= .5).astype(int) == y).astype(float), ((sb >= .5).astype(int) == y).astype(float)
    f = pd.DataFrame({"t": da["t"].to_numpy(), "lead": da["lead"].to_numpy(), "acc": cb - ca,
                      "bri": (sa - y) ** 2 - (sb - y) ** 2})
    per = f.groupby(["t", "lead"])[["acc", "bri"]].mean().groupby(level=0).mean()
    ta, tb = L.signflip_brier(per["acc"].to_numpy()), L.signflip_brier(per["bri"].to_numpy())
    loo_a = [float(per.drop(o)["acc"].mean()) for o in per.index] if len(per) > 1 else [float(per["acc"].mean())]
    loo_b = [float(per.drop(o)["bri"].mean()) for o in per.index] if len(per) > 1 else [float(per["bri"].mean())]
    out = {"a": a, "b": b, "n_dates": int(len(per)), "acc_diff": float(ca.mean() - cb.mean()),
           "acc_p_one_sided": ta["p_one_sided"], "dates_better_acc": int((per["acc"] < 0).sum()),
           "dates_worse_acc": int((per["acc"] > 0).sum()), "brier_a": float(np.mean((sa - y) ** 2)),
           "brier_b": float(np.mean((sb - y) ** 2)), "brier_diff_per_date_mean": float(per["bri"].mean()),
           "brier_p_one_sided": tb["p_one_sided"], "dates_better_brier": int((per["bri"] < 0).sum()),
           "dates_worse_brier": int((per["bri"] > 0).sum()), "exact": ta["exact"],
           "loo_acc_diff_min": -max(loo_a), "loo_acc_diff_max": -min(loo_a),
           "loo_brier_diff_max": max(loo_b), "loo_brier_diff_min": min(loo_b)}
    if d["lead"].nunique() == 1 and y.min() != y.max():
        au = L.paired_auc_perm(da["t"].to_numpy(), y, sa, sb)
        out.update({"auc_a": au.get("auc_a"), "auc_b": au.get("auc_b"), "auc_diff": au.get("auc_diff"),
                    "auc_p_one_sided": au.get("p_one_sided")})
    return out


def strongest_acc(mm, pool):
    return max(pool, key=lambda m: (mm[m]["accuracy"], -mm[m]["Brier"]))


def strongest_brier(mm, pool):
    return min(pool, key=lambda m: (mm[m]["Brier"], -mm[m]["accuracy"]))


def boot_auc(d, model):
    dm = d[d["model"] == model]
    return L.cluster_boot_auc(dm["t"].to_numpy(), dm["y"].to_numpy(), dm["score"].to_numpy())


def evaluable(d, model):
    dm = d[d["model"] == model]
    nH, nL, no = int(dm["y"].sum()), int((1 - dm["y"]).sum()), int(dm["t"].nunique())
    return no >= L.MIN_ORIGINS and nH >= L.MIN_PER_CLASS and nL >= L.MIN_PER_CLASS, no, nH, nL


# ================================================================================================ one row set
def score_set(d: pd.DataFrame, models: list[str], final: str, cands: list[str], with_required: bool) -> dict:
    res = {"by_lead": {}, "pooled": {}}
    base = (REQ_B if with_required else [B1]) + [B1P]
    others = [m for m in REFS if m not in base]
    for k in sorted(d["lead"].unique()):
        dk = d[d["lead"] == k]
        ev, no, nH, nL = evaluable(dk, final)
        mm = {m: metrics(dk[dk["model"] == m]["y"], dk[dk["model"] == m]["score"]) for m in models}
        r = {"n_dates": no, "HIGH": nH, "LOW": nL, "evaluable": ev, "metrics": mm,
             "dates": sorted(dk["t"].unique(), key=qk), "target_quarters": sorted(dk["target_quarter"].unique(), key=qk),
             "tests": {}}
        for a in [final] + ([PROPOSED] if with_required else []) + [c for c in cands if c != final]:
            r["tests"][a] = {b: compare(dk, a, b) for b in base + others + ([PROPOSED] if with_required and a != PROPOSED else [])}
            hb = L.holm({b: r["tests"][a][b]["acc_p_one_sided"] for b in base if b != B1P})
            hbb = L.holm({b: r["tests"][a][b]["brier_p_one_sided"] for b in base})
            for b in base:
                if b != B1P:
                    r["tests"][a][b]["acc_p_holm_B1_B6"] = hb[b]
                r["tests"][a][b]["brier_p_holm_B1_B6_B1p"] = hbb[b]
        r["auc_ci"] = {m: boot_auc(dk, m) for m in ([final, PROPOSED] if with_required else [final])} if ev else {}
        r["strongest_acc"] = strongest_acc(mm, base if not with_required else REQ_B)
        r["strongest_brier"] = strongest_brier(mm, base)
        f = dk[dk["model"] == final].sort_values(["t", "province_code"])
        chg = f["y"].to_numpy() != f["y_last"].to_numpy()
        cor = (f["score"].to_numpy() >= .5).astype(int) == f["y"].to_numpy()
        r["label_change_rows"] = int(chg.sum())
        r["final_correct_on_changed"] = int((cor & chg).sum())
        r["final_wrong_on_unchanged"] = int((~cor & ~chg).sum())
        r["final_calibration_in_the_large"] = float(f["score"].mean() - f["y"].mean())
        # candidate multiplicity: Brier p of each candidate vs the strongest-by-Brier baseline, Holm over candidates
        sb = r["strongest_brier"]
        cp = {c: r["tests"][c][sb]["brier_p_one_sided"] for c in cands if c in r["tests"]}
        r["candidates_vs_strongest_brier"] = {c: {"p": cp[c], "p_holm_candidates": h} for c, h in L.holm(cp).items()}
        res["by_lead"][str(int(k))] = r
    # pooled leads (each date once)
    mm = {m: metrics(d[d["model"] == m]["y"], d[d["model"] == m]["score"]) for m in models}
    pr = {"n_dates": int(d["t"].nunique()), "rows_per_model": int(len(d[d["model"] == final])),
          "HIGH": int(d[d["model"] == final]["y"].sum()), "LOW": int((1 - d[d["model"] == final]["y"]).sum()),
          "metrics_rows_pooled": mm, "tests": {}}
    for a in [final] + ([PROPOSED] if with_required else []) + [c for c in cands if c != final]:
        pr["tests"][a] = {b: compare(d, a, b) for b in base + others}
        hbb = L.holm({b: pr["tests"][a][b]["brier_p_one_sided"] for b in base})
        for b in base:
            pr["tests"][a][b]["brier_p_holm_B1_B6_B1p"] = hbb[b]
    # pooled per-date Brier for strongest selection: mean over dates of lead-averaged per-date Brier
    pdb = {}
    for m in models:
        dm = d[d["model"] == m]
        pdb[m] = float(((dm["score"] - dm["y"]) ** 2).groupby([dm["t"], dm["lead"]]).mean().groupby(level=0).mean().mean())
    pr["per_date_brier"] = pdb
    pr["strongest_brier"] = min(base, key=lambda m: pdb[m])
    res["pooled"] = pr
    return res


# ================================================================================================ criteria
def criteria(res_RA, final, lead="1") -> dict:
    r = res_RA["by_lead"].get(lead)
    if r is None:
        return {"note": f"lead {lead} has no dates"}
    mm, s = r["metrics"], r["strongest_acc"]
    t_s, t_p = r["tests"][final][s], r["tests"][final][B1]
    ci = r["auc_ci"].get(final, {}) if r["evaluable"] else {}
    ba_f, ba_s = mm[final]["balanced_accuracy"] or 0, mm[s]["balanced_accuracy"] or 0
    C = {"strongest_baseline_by_accuracy": s,
         "C1_accuracy_gt_0.75": bool(mm[final]["accuracy"] > 0.75),
         "C2_beats_strongest": bool(t_s["acc_diff"] > 0 and t_s["acc_p_one_sided"] < 0.05 and t_s["brier_a"] <= t_s["brier_b"]),
         "C3_not_HIGH_dominance": bool(ba_f >= 0.60 and ba_f > ba_s),
         "C4_defensible_across_dates": bool(t_s["dates_better_acc"] > t_s["dates_worse_acc"] and t_s["loo_acc_diff_min"] >= 0),
         "C5_information_beyond_persistence": bool(r["final_correct_on_changed"] > r["final_wrong_on_unchanged"]),
         "C6_reliability_rule_E23": bool(r["evaluable"] and ci.get("ci_low") is not None and ci["ci_low"] > 0.5
                                         and t_p["brier_p_one_sided"] < 0.05),
         "C7_no_leakage": True,      # assertions in every fold (the run stops otherwise)
         "C8_reproducible": "checked by reproduce.py (second run, byte-identical seals)",
         "C9_generalizes_unseen": "NOT ASSESSABLE (no authorized unseen quarter scored)"}
    return C


def proposed_criteria(res_RA, final) -> dict:
    pr = res_RA["pooled"]
    sb = pr["strongest_brier"]
    t = pr["tests"][final][sb]
    r1 = res_RA["by_lead"].get("1", {})
    mm1 = r1.get("metrics", {})
    s1 = r1.get("strongest_acc")
    P = {"strongest_baseline_by_pooled_brier": sb,
         "P1_beats_no_skill_references": bool(pr["per_date_brier"][final] < pr["per_date_brier"]["REF_always_HIGH"] and
                                              pr["per_date_brier"][final] < pr["per_date_brier"]["CLIM_training_rate"]),
         "P2_beats_strongest_brier_pooled": bool(t["brier_diff_per_date_mean"] < 0 and t["brier_p_one_sided"] < 0.05),
         "P2_detail": {k: t[k] for k in ("n_dates", "brier_diff_per_date_mean", "brier_p_one_sided",
                                         "dates_better_brier", "dates_worse_brier")},
         "P2_holm_B1_B6_B1p": t.get("brier_p_holm_B1_B6_B1p"),
         "P3_not_HIGH_dominance": bool(s1 is not None and (mm1[final]["balanced_accuracy"] or 0) >= 0.6 and
                                       (mm1[final]["balanced_accuracy"] or 0) > (mm1[s1]["balanced_accuracy"] or 0)),
         "P4_defensible_across_dates": bool(t["dates_better_brier"] > t["dates_worse_brier"] and t["loo_brier_diff_max"] < 0),
         "P5_information_beyond_persistence": bool(r1 and r1["final_correct_on_changed"] > r1["final_wrong_on_unchanged"]),
         "P7_no_leakage": True, "P8_reproducible": "see reproduce.py",
         "P9_generalizes_unseen": "NOT ASSESSABLE"}
    # P6: per lead with >= 8 dates
    pv, cal = {}, {}
    for k, r in res_RA["by_lead"].items():
        if r["n_dates"] >= 8:
            pv[k] = max(r["tests"][final][B1]["brier_p_one_sided"], r["tests"][final][B1P]["brier_p_one_sided"])
            cal[k] = r["final_calibration_in_the_large"]
    ph = L.holm(pv)
    rel = {k: bool(ph[k] is not None and ph[k] < 0.05 and abs(cal[k]) <= 0.10 and
                   res_RA["by_lead"][k]["tests"][final][B1]["brier_diff_per_date_mean"] < 0 and
                   res_RA["by_lead"][k]["tests"][final][B1P]["brier_diff_per_date_mean"] < 0) for k in pv}
    P["P6_reliable_leads"] = {k: {"p_max_of_B1_B1p": pv[k], "p_holm_leads": ph[k], "calibration_in_the_large": cal[k],
                                  "reliable": rel[k]} for k in pv}
    P["P6_max_reliable_lead"] = max([int(k) for k, v in rel.items() if v], default=None)
    return P


def reliable_leads_E23(res_RA, model) -> dict:
    """E23 rule (H2, C6): evaluable, AUC CI lower bound > 0.5, Brier better than persistence with Holm p < 0.05
    across the evaluable leads."""
    pv = {k: r["tests"][model][B1]["brier_p_one_sided"] for k, r in res_RA["by_lead"].items()
          if r["evaluable"] and model in r["tests"]}
    ph = L.holm(pv)
    out = {}
    for k, r in res_RA["by_lead"].items():
        ev = r["evaluable"]
        ci = r["auc_ci"].get(model, {}) if ev else {}
        out[k] = {"evaluable": ev, "auc_ci_low": ci.get("ci_low"), "brier_p_holm": ph.get(k),
                  "reliable": bool(ev and ci.get("ci_low") is not None and ci["ci_low"] > 0.5 and ph.get(k) is not None
                                   and ph[k] < 0.05)}
    return out


# ================================================================================================ hypotheses
def hypotheses(res_RA, meta_A, keep, d_RA) -> dict:
    evl = [k for k, r in res_RA["by_lead"].items() if r["evaluable"]]
    prim = "1" if "1" in evl else (min(evl, key=int) if evl else None)
    out = {"evaluable_leads": evl, "primary_lead": prim}
    # SHAP description at lead 1 (and the primary lead if any)
    for lead in sorted({"1"} | ({prim} if prim else set())):
        dates = res_RA["by_lead"].get(lead, {}).get("dates", [])
        shp = [meta_A[f"T1_A|k{lead}|{t}"].get("shap_mean_abs") for t in dates]
        shp = [s for s in shp if s]
        if not shp:
            continue
        S = pd.DataFrame(shp).fillna(0.0)
        pooled = S.mean().sort_values(ascending=False)
        top5_share = {f: float(np.mean([f in s.sort_values(ascending=False).index[:5] for _, s in S.iterrows()]))
                      for f in ("FSSI", "cpi_dev")}
        out[f"shap_lead{lead}"] = {"pooled_rank": {f: int(list(pooled.index).index(f)) + 1 if f in pooled.index else None
                                                   for f in ("FSSI", "cpi_dev")},
                                   "top10": pooled.head(10).round(5).to_dict(), "top5_share_of_dates": top5_share,
                                   "n_dates": len(shp)}
        out[f"permutation_lead{lead}"] = permutation_importance(keep, d_RA, lead)
    if prim is None:
        out["H1"] = out["H2"] = out["H3"] = "NOT TESTABLE (no evaluable lead: every lead has < 5 LOW test rows)"
        return out
    sh = out[f"shap_lead{prim}"]
    pi = out[f"permutation_lead{prim}"]
    h1 = all(sh["pooled_rank"][f] is not None and sh["pooled_rank"][f] <= 5 and sh["top5_share_of_dates"][f] >= .5
             and (pi.get(f, {}).get("ci_low") or -1) > 0 for f in ("FSSI", "cpi_dev"))
    out["H1"] = "REJECTED (supported alternative)" if h1 else "NOT REJECTED"
    rel = reliable_leads_E23(res_RA, PROPOSED)
    out["H2"] = ("NOT TESTABLE (fewer than 2 evaluable leads)" if len(evl) < 2 else
                 ("REJECTED" if sum(v["reliable"] for v in rel.values()) >= 2 else "NOT REJECTED"))
    r = res_RA["by_lead"][prim]
    hp = L.holm({b: r["tests"][PROPOSED][b].get("auc_p_one_sided") for b in REQ_B})
    h3 = all(hp[b] is not None and hp[b] < 0.05 and r["tests"][PROPOSED][b]["brier_a"] < r["tests"][PROPOSED][b]["brier_b"]
             for b in REQ_B)
    out["H3"] = "REJECTED" if h3 else "NOT REJECTED"
    return out


def permutation_importance(keep, d_RA, lead, reps=200, seed=L.SEED):
    """Pooled test rows at this lead: permute one feature across rows, re-predict with each date's own model,
    dBrier per row averaged over permutations; date-cluster bootstrap of the mean."""
    ks = [kk for kk in keep if kk.startswith(f"T1_A|k{lead}|")]
    dates = set(d_RA[d_RA["lead"] == int(lead)]["t"].unique())
    ks = [kk for kk in ks if kk.split("|")[2] in dates]
    if not ks:
        return {}
    frames, base = [], []
    for kk in ks:
        f = keep[kk]["teX"].copy()
        f["_key"] = kk
        frames.append(f)
    A = pd.concat(frames, ignore_index=True)
    y = A["y"].to_numpy()

    def pred(df):
        out = np.empty(len(df))
        for kk in ks:
            mk = (df["_key"] == kk).to_numpy()
            mdl, use, k = keep[kk]["model"], keep[kk]["use"], keep[kk]["k"]
            out[mk] = mdl.predict_proba(df.loc[mk].assign(lead=k)[use])[:, 1]
        return out
    p0 = pred(A)
    rng = np.random.default_rng(seed)
    res = {}
    for f in ("FSSI", "cpi_dev"):
        dl = np.zeros(len(A))
        for _ in range(reps):
            B = A.copy()
            B[f] = rng.permutation(B[f].to_numpy())
            dl += (pred(B) - y) ** 2 - (p0 - y) ** 2
        dl /= reps
        g = A["_key"].to_numpy()
        ug = np.unique(g)
        idx = [np.where(g == u)[0] for u in ug]
        bs = []
        for _ in range(L.N_BOOT):
            pick = np.concatenate([idx[i] for i in rng.integers(0, len(ug), len(ug))])
            bs.append(dl[pick].mean())
        res[f] = {"mean_dBrier": float(dl.mean()), "ci_low": float(np.quantile(bs, .025)),
                  "ci_high": float(np.quantile(bs, .975)), "n_rows": int(len(A)), "n_dates": int(len(ug))}
    return res


# ================================================================================================ supporting
def continuous(P, Dt, d, cands):
    """T1-cont: CRPS and MAE of PCF arms vs the random walk, on the rows of d."""
    out = {}
    rows = d[d["model"] == "PCF21"][["lead", "t", "province_code", "value", "v_last", "rw_sd"]]
    for arm in [c for c in cands if c.startswith("PCF21")]:
        x = rows.merge(Dt[Dt["model"] == arm][["lead", "t", "province_code", "mu_S1", "sd_S1"]],
                       on=["lead", "t", "province_code"], how="inner")
        if x.empty:
            continue
        x["crps_m"] = E.crps_gauss(x["value"], x["mu_S1"], x["sd_S1"])
        x["crps_rw"] = E.crps_gauss(x["value"], x["v_last"], x["rw_sd"])
        x["d"] = x["crps_m"] - x["crps_rw"]
        per = x.groupby(["t", "lead"])["d"].mean().groupby(level=0).mean()
        tst = L.signflip_brier(per.to_numpy())
        r = {"rows": int(len(x)), "n_dates": int(len(per)), "crps_model": float(x["crps_m"].mean()),
             "crps_random_walk": float(x["crps_rw"].mean()), "mae_model": float((x["value"] - x["mu_S1"]).abs().mean()),
             "mae_random_walk": float((x["value"] - x["v_last"]).abs().mean()),
             "crps_p_one_sided": tst["p_one_sided"], "dates_better": tst["origins_better"],
             "dates_worse": tst["origins_worse"],
             "coverage_80": float((((x["value"] - x["mu_S1"]) / x["sd_S1"]).abs() <= E.Z80).mean())}
        lead1 = x[x["lead"] == 1]
        if len(lead1):
            per1 = lead1.groupby("t")["d"].mean()
            r["lead1"] = {"n_dates": int(len(per1)), "crps_model": float(lead1["crps_m"].mean()),
                          "crps_random_walk": float(lead1["crps_rw"].mean()),
                          "p_one_sided": L.signflip_brier(per1.to_numpy())["p_one_sided"]}
        out[arm] = r
    return out


def noise_ceiling(d1, data):
    T = data["targets"]["T1_A"]
    nr = T.ru.groupby("quarter").size()
    f = d1[d1["model"] == B1].copy()
    out = {}
    for n in (600, 300):
        se = f["target_quarter"].map(lambda q: np.sqrt(E.pcf.samp_var(T.H[q], n) / nr[q]))
        z = (f["value"] - f["threshold"]) / se
        pf = norm.cdf(-z.abs())
        err = (f["score"] >= .5).astype(int) != f["y"]
        out[f"n{n}"] = {"rows": int(len(f)), "expected_sampling_flips_all_rows": float(pf.sum()),
                        "expected_sampling_flips_on_persistence_errors": float(pf[err].sum()),
                        "persistence_errors": int(err.sum()),
                        "rows_within_1_SE": int((z.abs() < 1).sum()), "rows_within_2_SE": int((z.abs() < 2).sum()),
                        "brier_floor_if_true_level_known": float(np.mean(pf * (1 - pf))),
                        "change_rows": [{"target_quarter": a, "province_code": b, "S1": float(v), "tau": float(t),
                                         "z": float(zz), "p_flip": float(pp)} for a, b, v, t, zz, pp, c in
                                        zip(f["target_quarter"], f["province_code"], f["value"], f["threshold"], z, pf,
                                            f["y"] != f["y_last"]) if c]}
    return out


def threshold_stability(data):
    T, TF = data["targets"]["T1_A"], data["targets"]["T1_F"]
    taus = {qs(t): T.tau(t) for t in range(qk("2022-Q1"), qk("2026-Q2") + 1) if len(T.published(t))}
    lab = []
    for q in T.V["quarter"].unique():
        for k in E.LEADS:
            t = qk(q) - k
            if t < qk(E.FIRST_Q) or qs(t) not in taus:
                continue
            v = T.V[T.V["quarter"] == q]
            for r in v.itertuples():
                lab.append({"quarter": q, "lead": k, "province_code": r.province_code, "y": int(r.v > taus[qs(t)]),
                            "y_fixed": int(r.v > 14.6)})
    lab = pd.DataFrame(lab)
    g = lab.groupby(["quarter", "province_code"])["y"].nunique()
    return {"tau_by_origin": taus, "tau_min": min(taus.values()), "tau_max": max(taus.values()),
            "cells_quarter_province": int(len(g)), "cells_whose_label_depends_on_lead": int((g > 1).sum()),
            "share_cells_label_depends_on_lead": float((g > 1).mean()),
            "rows_label_differs_origin_vs_fixed14.6": int((lab["y"] != lab["y_fixed"]).sum()),
            "rows": int(len(lab))}


def province_ranking(d1_T2, Dt_T2):
    """Per date (lead 1, T2 rows): Spearman of forecast mu_D vs realized D, against persistence of D."""
    out = {}
    base = d1_T2[d1_T2["model"] == B1][["t", "province_code", "value", "v_last"]]
    for arm in ("M4_21", "M3_21", "D_HIER", "D_HIER_NOW"):
        x = base.merge(Dt_T2[(Dt_T2["model"] == arm) & (Dt_T2["lead"] == 1)][["t", "province_code", "mu_D"]],
                       on=["t", "province_code"])
        if x.empty:
            continue
        rows = []
        for t, g in x.groupby("t"):
            a = spearmanr(g["mu_D"], g["value"]).statistic
            b = spearmanr(g["v_last"], g["value"]).statistic
            rows.append((t, a, b))
        r = pd.DataFrame(rows, columns=["t", "model", "persistence"]).dropna()
        tst = L.signflip_brier((r["persistence"] - r["model"]).to_numpy())
        out[arm] = {"n_dates": int(len(r)), "mean_spearman_model": float(r["model"].mean()),
                    "mean_spearman_persistence": float(r["persistence"].mean()), "p_one_sided": tst["p_one_sided"],
                    "dates_better": tst["origins_better"], "dates_worse": tst["origins_worse"]}
    return out


def risk_coverage(d, final):
    f = d[d["model"] == final].sort_values(["lead", "t", "province_code"])
    b = d[d["model"] == B1].sort_values(["lead", "t", "province_code"])
    conf = (f["score"] - .5).abs().to_numpy()
    out = []
    for c in (0.0, 0.1, 0.2, 0.3, 0.4):
        m = conf >= c
        y = f["y"].to_numpy()[m]
        out.append({"min_confidence": c, "coverage": float(m.mean()), "rows": int(m.sum()),
                    "accuracy_final": float(((f["score"].to_numpy()[m] >= .5) == y).mean()) if m.any() else None,
                    "accuracy_B1_same_rows": float(((b["score"].to_numpy()[m] >= .5) == y).mean()) if m.any() else None,
                    "brier_final": float(np.mean((f["score"].to_numpy()[m] - y) ** 2)) if m.any() else None,
                    "brier_B1_same_rows": float(np.mean((b["score"].to_numpy()[m] - y) ** 2)) if m.any() else None,
                    "LOW_rows": int((1 - y).sum())})
    return out


def frozen_2026(P, models):
    d = P[(P["t"] == "2025-Q4") & P["target_quarter"].isin(["2026-Q1", "2026-Q2"]) & P["model"].isin(models)]
    out = {}
    for (q, k), g in d.groupby(["target_quarter", "lead"]):
        out[f"{q} (lead {k})"] = {m: {"accuracy": float(((gm["score"] >= .5) == gm["y"]).mean()),
                                      "brier": float(np.mean((gm["score"] - gm["y"]) ** 2)), "HIGH": int(gm["y"].sum()),
                                      "LOW": int((1 - gm["y"]).sum())} for m, gm in g.groupby("model")}
    return out


def training_sizes(meta):
    rows = pd.DataFrame(meta.values())
    if rows.empty:
        return {}
    g = rows.groupby("lead")["n_train_quarters"].agg(["min", "max"])
    return {str(int(k)): {"min_train_quarters": int(v["min"]), "max_train_quarters": int(v["max"])} for k, v in g.iterrows()}


# ================================================================================================ non-chronological LOQO
def loqo_noncrono(data, d1_T1, d1_T2, meta_T1, Dt_T1):
    """Lead 1, NON-CHRONOLOGICAL (uses future quarters; never forecasting evidence). Excludes the held-out target
    quarter and every pair with the same feature quarter."""
    import warnings
    out = {"label": "NON-CHRONOLOGICAL leave-one-quarter-out; uses future quarters; sensitivity only"}
    for tname, d1 in (("T1_A", d1_T1), ("T2", d1_T2)):
        T = data["targets"][tname]
        rows = []
        cache = {}
        for t in sorted(d1["t"].unique(), key=qk):
            tt = qk(t)
            tau = T.tau(tt) if tname != "T2" else 0.0
            te = E.test_rows(T, tt, 1, tau)
            q = te["target_quarter"].iloc[0]
            tr = E.training_pairs(T, qk("2027-Q1"), 1, tau, cache)
            tr = tr[(tr["target_quarter"] != q) & (tr["t"] != tt)]
            r = {"t": t, "target_quarter": q, "y": te["y"].tolist()}
            r["B1p"] = E.calibrated_persistence(tr, te["y_last"].to_numpy()).tolist()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                r["E24_LR_P"] = E.lr_p(tr, te).tolist()
            # D part (OLS): PCF21 / M4_21 refit on all other quarters
            Dm, Nm = data["Dm"], data["Nm"]
            now = tname == "T2"
            X, y = [], []
            for tp in range(qk("2022-Q1") if now else qk("2021-Q2"), qk(E.LAST_Q)):
                if tp == tt or qs(tp + 1) == q:
                    continue
                for p in E.PROVS:
                    dl, dt, dn = Dm.get((p, tp - 1)), Dm.get((p, tp + 1)), Nm.get((p, tp)) if now else 0.0
                    if dl is None or dt is None or dn is None:
                        continue
                    X.append([dn, dl] if now else [dl])
                    y.append(dt)
            beta, sig = E.pcf.d_fit(np.asarray(X, float), np.asarray(y, float))
            if now:
                mu = [float(np.dot(beta, [Nm[(p, tt)], Dm[(p, tt - 1)]])) for p in te["province_code"]]
                r["M4_21_LOQO"] = [E.pcf.p_pos(m_, sig) for m_ in mu]
            else:
                dd = Dt_T1[(Dt_T1["model"] == "PCF21") & (Dt_T1["lead"] == 1) & (Dt_T1["t"] == t)].set_index("province_code")
                mu = [float(beta[0] * Dm[(p, tt - 1)]) for p in te["province_code"]]
                r["PCF21_LOQO"] = [E.pcf.p_high(tau, dd.loc[p, "mu_H"], dd.loc[p, "sd_H"] ** 2, m_, sig)
                                   for p, m_ in zip(te["province_code"], mu)]
            rows.append(r)
        res = {}
        ys = np.concatenate([r["y"] for r in rows])
        for arm in [k for k in rows[0] if k not in ("t", "target_quarter", "y")]:
            s = np.concatenate([r[arm] for r in rows])
            res[arm] = {"accuracy": float(((s >= .5) == ys).mean()), "brier": float(np.mean((s - ys) ** 2))}
        chrono = {m: {"accuracy": float(((g["score"] >= .5) == g["y"]).mean()), "brier": float(np.mean((g["score"] - g["y"]) ** 2))}
                  for m, g in d1.groupby("model") if m in (B1, B1P, "E24_LR_P", "E24_LR_P_T2", "PCF21", "M4_21")}
        out[tname] = {"n_dates": len(rows), "noncronological": res, "chronological_same_rows": chrono}
    return out


# ================================================================================================ main entry
def score_all(rd, out, keep, data) -> dict:
    res = {}
    P = {nm: pd.read_csv(rd / f"predictions_{nm}.csv", dtype={"province_code": str}) for nm in out}
    for nm in P:   # sealed bytes are what is scored
        assert len(P[nm]) == len(out[nm][0])
    Dt = {nm: out[nm][1] for nm in out}
    meta = {nm: out[nm][2] for nm in out}
    # ---------------- T1_A
    allm = REQ_B + [PROPOSED] + REFS + T1_CANDS + ABL + DIAG
    dA, dropA = rowset(P["T1_A"], allm, E.LAST_FEATURE_Q)
    lab = [m for m in REQ_B[:1] + REFS + T1_CANDS + DIAG]
    dP, dropP = rowset(P["T1_A"], lab, "2026-Q1")
    rA = score_set(dA, allm, FINAL["T1"], T1_CANDS, True)
    rP = score_set(dP, lab, FINAL["T1"], T1_CANDS, False)
    res["T1_A"] = {"R_A": rA, "R_P": rP, "dropped_R_A": dropA, "dropped_R_P": dropP,
                   "criteria_C1_C9": criteria(rA, FINAL["T1"]),
                   "criteria_C1_C9_PROPOSED": criteria(rA, PROPOSED),
                   "proposed_P1_P9": proposed_criteria(rA, FINAL["T1"]),
                   "reliable_leads_E23_FINAL": reliable_leads_E23(rA, FINAL["T1"]),
                   "reliable_leads_E23_PROPOSED": reliable_leads_E23(rA, PROPOSED),
                   "hypotheses": hypotheses(rA, meta["T1_A"], keep, dA),
                   "continuous_R_A": continuous(P["T1_A"], Dt["T1_A"], dA, T1_CANDS),
                   "continuous_R_P": continuous(P["T1_A"], Dt["T1_A"], dP, T1_CANDS),
                   "noise_ceiling_lead1_R_A": noise_ceiling(dA[dA["lead"] == 1], data),
                   "risk_coverage_lead1_R_A": risk_coverage(dA[dA["lead"] == 1], FINAL["T1"]),
                   "risk_coverage_pooled_R_A": risk_coverage(dA, FINAL["T1"]),
                   "frozen_2026": frozen_2026(P["T1_A"], allm),
                   "training_sizes": training_sizes(meta["T1_A"]),
                   "gate_choices": pd.Series([m.get("gate") for m in meta["T1_A"].values() if m.get("gate")]).value_counts().to_dict(),
                   "cal_temperature": pd.Series([m.get("cal_temperature") for m in meta["T1_A"].values()
                                                 if m.get("cal_temperature") is not None]).describe().to_dict()}
    # ---------------- readings and fixed threshold (label-history arms)
    for nm in ("T1_B", "T1_C", "T1_F"):
        d, dr = rowset(P[nm], lab, "2026-Q1")
        d2, dr2 = rowset(P[nm], lab, E.LAST_FEATURE_Q)
        res[nm] = {"R_P": score_set(d, lab, FINAL["T1"], T1_CANDS, False),
                   "R_A_origins": score_set(d2, lab, FINAL["T1"], T1_CANDS, False), "dropped": dr}
    # ---------------- T2
    allm2 = REQ_B + [PROPOSED] + REFS + T2_CANDS
    lab2 = [B1] + REFS + T2_CANDS
    d2A, drop2A = rowset(P["T2"], allm2, E.LAST_FEATURE_Q)
    d2P, drop2P = rowset(P["T2"], lab2, "2026-Q1")
    r2A = score_set(d2A, allm2, FINAL["T2"], T2_CANDS, True)
    r2P = score_set(d2P, lab2, FINAL["T2"], T2_CANDS, False)
    res["T2"] = {"R_A": r2A, "R_P": r2P, "dropped_R_A": drop2A, "dropped_R_P": drop2P,
                 "criteria_C1_C9": criteria(r2A, FINAL["T2"]), "proposed_P1_P9": proposed_criteria(r2A, FINAL["T2"]),
                 "province_ranking_lead1_R_P": province_ranking(d2P[d2P["lead"] == 1], Dt["T2"]),
                 "frozen_2026": frozen_2026(P["T2"], allm2), "training_sizes": training_sizes(meta["T2"])}
    res["threshold_stability"] = threshold_stability(data)
    res["loqo_noncronological"] = loqo_noncrono(data, dA[dA["lead"] == 1], d2A[d2A["lead"] == 1], meta["T1_A"],
                                                Dt["T1_A"])
    # long tables for the deliverables
    rows = []
    for tg, rr in (("T1_A", res["T1_A"]["R_A"]), ("T1_A_RP", res["T1_A"]["R_P"]), ("T2", res["T2"]["R_A"]),
                   ("T2_RP", res["T2"]["R_P"]), ("T1_B_RP", res["T1_B"]["R_P"]), ("T1_C_RP", res["T1_C"]["R_P"]),
                   ("T1_F_RP", res["T1_F"]["R_P"])):
        for k, r in rr["by_lead"].items():
            for m, mm in r["metrics"].items():
                rows.append({"set": tg, "lead": k, "model": m, "n_dates": r["n_dates"], "HIGH": mm["HIGH"],
                             "LOW": mm["LOW"], "evaluable": r["evaluable"],
                             **{q: mm[q] for q in ("accuracy", "balanced_accuracy", "precision", "recall", "F1",
                                                   "specificity", "ROC_AUC", "Brier", "log_score", "TP", "FP", "FN", "TN")}})
        for m, mm in rr["pooled"]["metrics_rows_pooled"].items():
            rows.append({"set": tg, "lead": "pooled", "model": m, "n_dates": rr["pooled"]["n_dates"], "HIGH": mm["HIGH"],
                         "LOW": mm["LOW"], "evaluable": None,
                         **{q: mm[q] for q in ("accuracy", "balanced_accuracy", "precision", "recall", "F1",
                                               "specificity", "ROC_AUC", "Brier", "log_score", "TP", "FP", "FN", "TN")},
                         "per_date_brier": rr["pooled"]["per_date_brier"].get(m)})
    pd.DataFrame(rows).to_csv(rd / "metrics_all.csv", index=False, lineterminator="\n", float_format="%.6g")
    trs = []
    for tg, rr in (("T1_A", res["T1_A"]["R_A"]), ("T1_A_RP", res["T1_A"]["R_P"]), ("T2", res["T2"]["R_A"]),
                   ("T2_RP", res["T2"]["R_P"])):
        for k, r in list(rr["by_lead"].items()) + [("pooled", rr["pooled"])]:
            for a, tb in r["tests"].items():
                for b, t in tb.items():
                    trs.append({"set": tg, "lead": k, **t})
    pd.DataFrame(trs).to_csv(rd / "tests_all.csv", index=False, lineterminator="\n", float_format="%.6g")
    return res
