"""
E12 runner (see ../E12_PROTOCOL.md). Run from the aligned backend root:  python -B <this file>
Category A (descriptive) and Category B (internal-consistency forecasting of the constructed S1 indicator).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard  # noqa: E402

guard.install()

import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import warnings  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

E9 = guard.AL / "experiments" / "2026-10-12_E9_S1_safe_training"
E9RUN = E9 / "runs" / "20261012T140816Z"
sys.path.insert(0, str(E9 / "runner"))
sys.path.insert(0, str(guard.AL))
import scripts.supplementary.devprotocol_rule_l as D  # noqa: E402
from app.ml.features import risk_score_v2 as R  # noqa: E402
import metrics as M9  # noqa: E402
import safe_frame as F9  # noqa: E402
import e12_lib as L  # noqa: E402

warnings.filterwarnings("ignore")
EXP = guard.EXP
PROTOCOL = EXP / "E12_PROTOCOL.md"
TAU0_RECORDED = 10.84335
MIN_TRAIN_Q = 8


class Stop(RuntimeError):
    pass


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_new(path: Path, df: pd.DataFrame) -> None:
    if path.exists():
        raise Stop(f"refusing to overwrite {path.name}")
    df.to_csv(path, index=False)


def main():
    if not PROTOCOL.exists():
        raise Stop("protocol missing")
    started = datetime.now(timezone.utc)
    run = EXP / "runs" / started.strftime("%Y%m%dT%H%M%SZ")
    run.mkdir(parents=True, exist_ok=False)
    man = {"started_utc": started.isoformat(), "protocol_sha256": sha(PROTOCOL), "allowlist_sha256_start": guard.verify_allowlist(),
           "code_sha256": {"run_e12.py": sha(Path(__file__)), "e12_lib.py": sha(HERE / "e12_lib.py"), "guard.py": sha(HERE / "guard.py"),
                           "E9 safe_frame.py": sha(E9 / "runner" / "safe_frame.py"),
                           "risk_score_v2.py": guard.sha256("app/ml/features/risk_score_v2.py")},
           "environment": {"python": sys.version.split()[0], "platform": platform.platform(), "pandas": pd.__version__, "numpy": np.__version__}}

    # ---------------- data and S1 reproduction gate
    src = F9.load_sources(guard)
    psa = src["psa"]
    st, rounds = F9.s1_targets(D, R, psa)
    ref = pd.read_csv(E9RUN / "s1_targets_2021_2025.csv")
    g = st.merge(ref[["province_code", "quarter", "stress"]], on=["province_code", "quarter"], suffixes=("", "_ref"))
    gate = float((g["stress"] - g["stress_ref"]).abs().max())
    if len(g) != len(ref) or gate > 1e-9:
        raise Stop(f"S1 reproduction gate failed vs E9 reference: {gate}")
    lab = src["lab"].merge(st[["province_code", "quarter", "stress"]], on=["province_code", "quarter"])
    gate_labels = {"max_abs_diff": float((lab["stress"] - lab["stress_score"]).abs().max()),
                   "rows_equal_after_round4": int((np.abs(lab["stress"].round(4) - lab["stress_score"]) < 1e-12).sum()), "rows": int(len(lab))}
    names = guard.read_allowed_parquet("data/processed/labels.parquet", ["province_code", "province_name"]) \
        .drop_duplicates("province_code").set_index("province_code")["province_name"].to_dict()
    published = lambda q: D.label_published(q, "development")[0]
    tau_full, tau_q = R.reference_threshold(st[["province_code", "quarter", "stress"]], published, pd.Timestamp("2023-10-01"))
    between = int(((st["stress"] > min(tau_full, TAU0_RECORDED)) & (st["stress"] <= max(tau_full, TAU0_RECORDED))).sum())
    if between:
        raise Stop("an S1 value lies between the recorded and full-precision tau0")
    TAU0 = TAU0_RECORDED

    # realized table: F for all 2021-2025 quarters; H for definition-A quarters
    real = L.deviations(psa.rename(columns={"food_cpi_yoy": "F"})[["province_code", "quarter", "F"]])
    hq = st.groupby("quarter")["sws_hunger_pct"].first()
    real["H"] = real["quarter"].map(hq)
    real["S1"] = real["H"] + 2.0 * real["D"]
    chk = real.dropna(subset=["S1"]).merge(st[["province_code", "quarter", "stress"]], on=["province_code", "quarter"])
    if len(chk) != len(st) or (chk["S1"] - chk["stress"]).abs().max() > 1e-9:
        raise Stop("E12 S1 construction differs from compute_stress")
    real["province"] = real["province_code"].map(names)
    lq = sorted(st["quarter"].unique(), key=F9.qi)
    rl = real[real["quarter"].isin(lq)].copy()          # labelled quarters (H and D both available)

    # ---------------- Option A grid (Category A)
    groups = L.equivalence_groups()
    gid = {r: i + 1 for i, r in enumerate(groups)}
    d_rank = L.within_quarter_ranks(rl, "D")
    d_spread = L.within_quarter_spread(rl, "D")
    s1_high = int((rl["S1"] > TAU0).sum())
    rows = []
    for a in L.ALPHAS:
        for b in L.BETAS:
            r_ = L.ratio(a, b)
            s = L.option_a(rl["H"], rl["D"], a, b)
            t = rl.assign(s=s)
            rank_same = bool((L.within_quarter_ranks(t, "s") == d_rank).all())
            spread = L.within_quarter_spread(t, "s")
            equiv_s1 = r_ == L.ratio(1.0, 2.0)
            thr = (b / 2.0) * TAU0 if equiv_s1 else None
            high = int((s > thr).sum()) if equiv_s1 else None
            rows.append({"alpha": a, "beta": b, "ratio_alpha_over_beta": f"{r_.numerator}/{r_.denominator}", "ratio_value": float(r_),
                         "equivalence_group": gid[r_], "equivalent_to_S1": equiv_s1, "equivalent_to_option_C": a == 0.0,
                         "score_mean": float(s.mean()), "score_min": float(s.min()), "score_max": float(s.max()),
                         "mean_within_quarter_spread": float(spread.mean()),
                         "spread_equals_beta_times_D_spread": bool(np.allclose(spread.values, b * d_spread.values)),
                         "ranking_identical_to_D": rank_same,
                         "threshold_rule": "S1 tau0 transformed: (beta/2)*tau0" if equiv_s1 else "none defined (no approved threshold)",
                         "threshold": thr, "HIGH_rows_of_80": high,
                         "HIGH_identical_to_S1": (high == s1_high) if equiv_s1 else None})
    grid_a = pd.DataFrame(rows)
    eq = []
    for r_, members in groups.items():
        eq.append({"equivalence_group": gid[r_], "ratio_alpha_over_beta": f"{r_.numerator}/{r_.denominator}", "ratio_value": float(r_),
                   "n_combinations": len(members), "members_alpha_beta": "; ".join(f"({a},{b})" for a, b in members),
                   "equivalent_to": "Option C (provincial deviation only)" if r_ == 0 else ("S1 (H + 2D), after scaling" if r_ == L.ratio(1, 2) else "-"),
                   "canonical_form": f"beta * ({float(r_):.6g}*H + D)"})
    eq_a = pd.DataFrame(eq)

    # ---------------- Category B frame (E9 origin inputs) and folds
    fr = pd.read_csv(E9RUN / "input_frame.csv")
    fr = fr.rename(columns={"sws_hunger": "H_in", "cpi_rel": "D_in", "food_cpi_yoy": "F_in"})
    fr = fr.merge(rl[["province_code", "quarter", "S1", "H", "D", "F"]].rename(columns={"quarter": "target_quarter", "S1": "S1_true",
                                                                                         "H": "H_true", "D": "D_true", "F": "F_true"}),
                  on=["province_code", "target_quarter"], how="left")
    # own-score values at the anchor (latest published label quarter) for persistence
    anc = rl.set_index(["quarter", "province_code"])
    for c in ("H", "D", "F", "S1"):
        fr[f"{c}_anchor"] = [anc[c].get((a, p), np.nan) if isinstance(a, str) else np.nan
                             for a, p in zip(fr["anchor_quarter"], fr["province_code"])]
    tests, skipped = [], {}
    for q in lq:
        tq = F9.eligible_training_quarters(st, q, published)
        (tests.append(q) if len(tq) >= MIN_TRAIN_Q else skipped.__setitem__(q, f"{len(tq)} eligible training quarters (< {MIN_TRAIN_Q})"))
    distinct_ratios = [r for r in groups]

    cands = {"S1_rule": lambda d, s: d["H_in"] + 2 * d["D_in"], "S1_carry_forward": lambda d, s: d["last_published_stress"],
             "H_only": lambda d, s: d["H_in"], "F_only": lambda d, s: d["F_in"], "D_only (Option C)": lambda d, s: d["D_in"]}
    for r_ in distinct_ratios:
        cands[f"OptionA_ratio_{r_.numerator}/{r_.denominator}"] = (lambda rr: (lambda d, s: float(rr) * d["H_in"] + d["D_in"]))(r_)
    for wh in L.WH:
        cands[f"OptionB_wH_{wh}"] = (lambda w: (lambda d, s: L.option_b(d["H_in"], d["D_in"], w, s)))(wh)
    native = {"S1_rule", "S1_carry_forward"}

    pred_rows, bfolds = [], []
    for T in tests:
        tq = F9.eligible_training_quarters(st, T, published)
        tr = fr[fr["target_quarter"].isin(tq)].dropna(subset=["S1_true"])
        te = fr[fr["target_quarter"] == T]
        stt = L.z_stats(rl[rl["quarter"].isin(tq)].groupby("quarter")["H"].first(), rl[rl["quarter"].isin(tq)]["D"])
        bfolds.append({"target": T, "train_quarters": tq, "stats": stt})
        for name, fn in cands.items():
            xtr, xte = fn(tr, stt), fn(te, stt)
            a, b = L.ols_map(xtr.values, tr["S1_true"].values)
            for (_, r), x in zip(te.iterrows(), xte.values):
                pred_rows.append({"candidate": name, "target_quarter": T, "province_code": r["province_code"], "score_at_origin": x,
                                  "mapped_S1": a + b * x, "map_a": a, "map_b": b, "S1_true": r["S1_true"],
                                  "native_S1_scale": name in native})
    P = pd.DataFrame(pred_rows)

    def summarize(df):
        out = {}
        for name, g in df.groupby("candidate"):
            perq = []
            for q, h in g.groupby("target_quarter"):
                c, n = L.concordant(h["score_at_origin"], h["S1_true"])
                perq.append({"q": q, "mae_mapped": float((h["mapped_S1"] - h["S1_true"]).abs().mean()),
                             "mae_raw": float((h["score_at_origin"] - h["S1_true"]).abs().mean()) if h["native_S1_scale"].iloc[0] else None,
                             "regional_err": float(abs(h["mapped_S1"].mean() - h["S1_true"].mean())),
                             "conc_share": c / n if n else None, "b": float(h["map_b"].iloc[0])})
            pq = pd.DataFrame(perq)
            e = g["mapped_S1"] - g["S1_true"]
            loqo = [pq.drop(i)["mae_mapped"].mean() for i in pq.index]
            out[name] = {"quarters": len(pq), "rows": int(len(g)), "MAE_mapped": float(e.abs().mean()), "RMSE_mapped": float(np.sqrt((e ** 2).mean())),
                         "MAE_raw_native": float((g["score_at_origin"] - g["S1_true"]).abs().mean()) if g["native_S1_scale"].iloc[0] else None,
                         "mean_regional_error": float(pq["regional_err"].mean()),
                         "mean_concordant_share": float(pq["conc_share"].dropna().mean()) if pq["conc_share"].notna().any() else None,
                         "ranking_defined": bool(pq["conc_share"].notna().any() and g.groupby("target_quarter")["score_at_origin"].nunique().gt(1).any()),
                         "negative_map_slope_quarters": int((pq["b"] < 0).sum()),
                         "LOQO_MAE_mapped_range": [float(min(loqo)), float(max(loqo))], "per_quarter": perq}
        return out
    catB = summarize(P)
    # identical mapped predictions => equivalent candidates
    piv = P.pivot_table(index=["target_quarter", "province_code"], columns="candidate", values="mapped_S1")
    dup = {}
    for c1 in piv.columns:
        for c2 in piv.columns:
            if c1 < c2 and np.allclose(piv[c1], piv[c2], atol=1e-9):
                dup.setdefault(c1, []).append(c2)

    # own-score persistence (scale-free)
    own = {}
    tr_all = fr[fr["target_quarter"].isin(lq)]
    for c in ("S1", "H", "D", "F"):
        rowsq = []
        for T in tests:
            h = fr[fr["target_quarter"] == T]
            tq = F9.eligible_training_quarters(st, T, published)
            sd = float(rl[rl["quarter"].isin(tq)][c].std(ddof=1))
            cc, n = L.concordant(h[f"{c}_anchor"], h[f"{c}_true"])
            rowsq.append({"q": T, "nmae": float((h[f"{c}_anchor"] - h[f"{c}_true"]).abs().mean() / sd) if sd > 0 else None,
                          "conc": (cc / n) if (n and c != "H") else None})      # H is constant within a quarter: ranking undefined
        q_ = pd.DataFrame(rowsq)
        own[c] = {"normalized_MAE_mean": float(q_["nmae"].mean()), "concordance_mean": float(q_["conc"].dropna().mean()) if q_["conc"].notna().any() else None,
                  "ranking_defined": bool(q_["conc"].notna().any()), "per_quarter": rowsq}

    # S1 classification (S1 only)
    cls = {}
    for name in ("S1_rule", "S1_carry_forward"):
        h = P[P["candidate"] == name]
        yt, yp = (h["S1_true"] > TAU0).values, (h["score_at_origin"] > TAU0).values
        cls[name] = M9.classification(yt, yp)

    # ---------------- Option B grid (Category A per fold, realized components with frozen training stats)
    bg = []
    for f in bfolds:
        T, s_ = f["target"], f["stats"]
        t = rl[rl["quarter"] == T]
        for wh in L.WH:
            sc = L.option_b(t["H"], t["D"], wh, s_)
            tt = t.assign(s=sc)
            eff = (wh / s_["sd_h"]) / ((1 - wh) / s_["sd_d"]) if (wh < 1 and s_["sd_h"] > 0 and s_["sd_d"] > 0) else (np.inf if wh == 1 else None)
            bg.append({"wH": wh, "wF": 1 - wh, "fold_target_quarter": T, "n_train_quarters": s_["n_h_quarters"], "n_train_D_rows": s_["n_d_rows"],
                       "mu_H": s_["mu_h"], "sd_H": s_["sd_h"], "mu_D": s_["mu_d"], "sd_D": s_["sd_d"],
                       "zero_variance_H": s_["zero_var_h"], "zero_variance_D": s_["zero_var_d"],
                       "effective_alpha_over_beta": eff,
                       "equivalent_to": "Option C (rescaled D)" if wh == 0 else ("H only (no provincial ranking)" if wh == 1 else "Option A with the effective ratio, plus a constant shift"),
                       "score_min": float(sc.min()), "score_max": float(sc.max()),
                       "within_quarter_spread": float(sc.max() - sc.min()),
                       "ranking_identical_to_D": bool((L.within_quarter_ranks(tt, "s") == L.within_quarter_ranks(t, "D")).all()) if wh < 1 else False,
                       "classification": "not evaluable (no approved threshold)"})
    grid_b = pd.DataFrame(bg)
    skipped_b = [{"fold_target_quarter": q, "reason": why} for q, why in skipped.items()]

    # ---------------- Option C (all quarters with complete F)
    oc = real[["quarter", "province_code", "province", "F", "mean5", "D"]].copy()
    oc["complete_five"] = oc["D"].notna()
    oc["rank_by_D"] = L.within_quarter_ranks(oc, "D")
    oc["sign"] = np.where(oc["D"] > 0, "above mean", np.where(oc["D"] < 0, "below mean", np.where(oc["D"] == 0, "at mean", "missing")))
    oc["label"] = "relative provincial food-price pressure (not hunger; near zero does not mean low food insecurity)"

    # ---------------- quarterly results and two-layer descriptives
    qr = []
    prev_rank = None
    for q in sorted(real["quarter"].unique(), key=F9.qi):
        t = real[real["quarter"] == q]
        comp = bool(t["D"].notna().all())
        order = " > ".join(t.sort_values("D", ascending=False)["province"]) if comp else None
        rk = t.set_index("province_code")["D"] if comp else None
        kend = float(pd.Series(rk).corr(pd.Series(prev_rank), method="kendall")) if (comp and prev_rank is not None) else None
        hv = t["H"].iloc[0]
        row = {"quarter": q, "H_balance_luzon": hv, "H_definitionA_rounds": len([r for r in rounds if r.quarter == q and r.in_label_definition_A]),
               "label_published": None if pd.isna(hv) or published(q) is None else str(published(q).date()),
               "F_available_provinces": int(t["F"].notna().sum()), "complete_five": comp, "mean5_F": t["mean5"].iloc[0],
               "D_spread": float(t["D"].max() - t["D"].min()) if comp else None, "ranking_by_D": order,
               "kendall_vs_previous_complete_quarter": kend,
               "S1_min": float(t["S1"].min()) if t["S1"].notna().any() else None, "S1_max": float(t["S1"].max()) if t["S1"].notna().any() else None,
               "S1_HIGH_count_tau0": int((t["S1"] > TAU0).sum()) if t["S1"].notna().all() else None,
               "H_only_call": (None if pd.isna(hv) else ("HIGH" if hv > TAU0 else "LOW")),
               "S1_HIGH_equals_H_only_call_rows": int(((t["S1"] > TAU0) == (t["H"] > TAU0)).sum()) if t["S1"].notna().all() else None,
               "used_in_categoryB": q in tests}
        if comp:
            prev_rank = rk
        qr.append(row)
    QR = pd.DataFrame(qr)
    hseries = sorted([{"quarter": r.quarter, "round": r.label, "H": r.value, "published": None if r.published is None else str(r.published.date()),
                       "date_type": r.date_type, "definition_A": r.in_label_definition_A, "source": r.source} for r in rounds],
                     key=lambda x: (F9.qi(x["quarter"]), x["published"] or ""))
    two_layer = {"regional_layer_rounds": hseries,
                 "regional_scope": "SWS Balance Luzon (wider than CALABARZON); one value per quarter shared by all five provinces",
                 "provincial_layer_quarters_complete": int(QR["complete_five"].sum()), "quarters_total": int(len(QR)),
                 "S1_ranking_equals_D_ranking_all_labelled_quarters": bool((L.within_quarter_ranks(rl, "S1") == d_rank).all()),
                 "S1_HIGH_equals_H_only_call_share": float(((rl["S1"] > TAU0) == (rl["H"] > TAU0)).mean()),
                 "variance_share_between_quarters_S1": float(1 - ((rl["S1"] - rl.groupby("quarter")["S1"].transform("mean")) ** 2).sum()
                                                             / ((rl["S1"] - rl["S1"].mean()) ** 2).sum())}
    # tau0 leave-one-quarter-out (descriptive; bypasses the 8-quarter minimum)
    base = st[st["quarter"].isin(tau_q)]
    loqo_tau = {q: float(base[base["quarter"] != q]["stress"].median()) for q in tau_q}

    # ---------------- write deliverables (new files only)
    write_new(EXP / "OPTION_A_WEIGHT_GRID.csv", grid_a)
    write_new(EXP / "OPTION_A_EQUIVALENCE_GROUPS.csv", eq_a)
    write_new(EXP / "OPTION_B_STANDARDIZED_GRID.csv", pd.concat([grid_b, pd.DataFrame(skipped_b)], ignore_index=True))
    write_new(EXP / "OPTION_C_PROVINCIAL_ONLY.csv", oc.sort_values(["quarter", "rank_by_D"]))
    bc = [{"candidate": k, "category": "B (internal consistency: target = next-quarter S1, a constructed indicator)",
           **{kk: vv for kk, vv in v.items() if kk != "per_quarter"},
           "mapped_predictions_identical_to": "; ".join(dup.get(k, []))} for k, v in catB.items()]
    bc += [{"candidate": f"own-score carry-forward: {c}", "category": "B (own-score persistence; scale-free)",
            "normalized_MAE_mean": v["normalized_MAE_mean"], "mean_concordant_share": v["concordance_mean"], "ranking_defined": v["ranking_defined"]}
           for c, v in own.items()]
    write_new(EXP / "BASELINE_COMPARISON.csv", pd.DataFrame(bc))
    write_new(EXP / "QUARTERLY_RESULTS.csv", QR)
    P.to_csv(run / "categoryB_predictions.csv", index=False)
    real.to_csv(run / "realized_components_2021_2025.csv", index=False)
    details = {"gate_vs_E9": gate, "gate_vs_labels_parquet": gate_labels, "tau0_recorded": TAU0_RECORDED, "tau0_full_precision": tau_full,
               "tau0_quarters": tau_q, "values_between_tau0s": between, "tau0_LOQO_descriptive": loqo_tau,
               "labelled_quarters": lq, "categoryB_tests": tests, "categoryB_skipped": skipped, "categoryB": catB,
               "categoryB_equivalent_mapped_predictions": dup, "own_score_persistence": own, "S1_classification": cls,
               "two_layer": two_layer, "folds_stats": bfolds, "S1_HIGH_rows_of_80": s1_high}
    (run / "details.json").write_text(json.dumps(details, indent=1, default=str), encoding="utf-8")
    man.update({"tests": tests, "skipped": skipped, "access_log_parquet": [a for a in guard.ACCESS_LOG if a["op"] == "read_parquet"],
                "access_log_opens": sorted({a["path"] for a in guard.ACCESS_LOG if a["op"] == "open"}),
                "allowlist_sha256_end": guard.verify_allowlist(), "finished_utc": datetime.now(timezone.utc).isoformat()})
    man["outputs_sha256"] = {p.name: sha(p) for p in sorted(run.glob("*")) if p.name != "manifest.json"}
    man["deliverables_sha256"] = {n: sha(EXP / n) for n in ("OPTION_A_WEIGHT_GRID.csv", "OPTION_A_EQUIVALENCE_GROUPS.csv",
                                                             "OPTION_B_STANDARDIZED_GRID.csv", "OPTION_C_PROVINCIAL_ONLY.csv",
                                                             "BASELINE_COMPARISON.csv", "QUARTERLY_RESULTS.csv")}
    (run / "manifest.json").write_text(json.dumps(man, indent=1, default=str), encoding="utf-8")
    print(f"RUN {run.name} | gate {gate:.2e} | tests {len(tests)} skipped {len(skipped)} | groups {len(groups)}")


if __name__ == "__main__":
    main()
