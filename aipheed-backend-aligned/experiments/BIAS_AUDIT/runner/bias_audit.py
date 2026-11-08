"""BIAS_AUDIT: model bias, trigger-composition bias and overfitting checks of the served model P0H4
(price LightGBM P0, one model across leads, times the hunger term H4). Every refit uses the frozen UNI-FINAL training
rule (issue-date cut-offs, inner chronological validation) on the identical evaluation rows.

    python bias_audit.py ablation      # group ablations (dashboard groups as implemented + the user's grouping)
    python bias_audit.py permutation   # held-out permutation importance by group (shuffle across issue dates)
    python bias_audit.py composition   # SHAP group shares: stability, group size, redundancy, missingness, sharing
    python bias_audit.py sensitivity   # realistic input perturbations on the latest origins
    python bias_audit.py predictive    # calibration-in-the-large and errors by province, period, event type
    python bias_audit.py conditional   # does Market mask other groups? ablations inside a model without Market
    python bias_audit.py fairshare     # SHAP per column and on rows with the group's inputs present
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
OUT = HERE.parent / "out"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))
import l2_lib as X  # noqa: E402
import run_l2 as RL  # noqa: E402

U, C, FM, B, E, L, np, pd = X.U, X.C, X.FM, X.B, X.E, X.L, X.np, X.pd
L2OUT = EXP / "LEAD2_OPTIMIZATION" / "out"
SERVED = EXP.parents[1] / "backend" / "data" / "ch1_engine"
FULL = X.base_cols(True)
FAM = {c: X.FAMILY_OF[c] for c in FULL}
DASH = {"market": {"A1", "A2", "A3"}, "climate": {"C1", "C2", "C3"}, "fish_kill": {"C4"}, "employment": {"E1"},
        "ofw_remittance": {"E2"}, "news (other)": {"N1"}, "poverty (other)": {"V1"}, "hunger feature (other)": {"H1"}}
USER = {"climate C1-C4": {"C1", "C2", "C3", "C4"}, "employment+remittances E1-E2": {"E1", "E2"}}
SHARED = {"C1", "E1", "E2", "H1"}            # one national/regional value per issue date


def gcols(fams: set) -> list[str]:
    return [c for c in FULL if FAM[c] in fams]


def data():
    U.setup()
    S = U.stack(RL._K())
    D = pd.read_csv(L2OUT / "predictions_addendum3.csv", dtype={"province_code": str})
    return S, D[D["lead"] <= 3].copy()


def fit_origin(S, t, keep):
    tr, te = U.train_rows(S, t), S[S["t"] == t]
    if not B.eligible(tr) or not len(te):
        return None, None
    cfg, _ = U.select(tr, keep, True)
    return U.UniPrice(cfg, keep, True).fit(tr), te


def metrics(g, p) -> dict:
    from sklearn.metrics import average_precision_score, roc_auc_score
    y = g["y"].astype(int).to_numpy()
    p = np.asarray(p, float)
    yh = (p >= .5).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    fn, tn = int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    rec, spec = tp / max(tp + fn, 1), tn / max(tn + fp, 1)
    return {"rows": int(len(g)), "quarters": int(g["q"].nunique()), "high": int(y.sum()), "acc": (tp + tn) / len(y),
            "bal": (rec + spec) / 2, "precision": tp / (tp + fp) if tp + fp else None, "recall": rec,
            "false_alarm_rate": fp / max(fp + tn, 1), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else None,
            "pr_auc": float(average_precision_score(y, p)) if len(set(y)) == 2 else None,
            "brier": float(np.mean((p - y) ** 2)),
            "per_quarter_correct": {L.qs(int(q)): int(((h[c_] >= .5).astype(int) == h["y"]).sum())
                                    for q, h in g.assign(_p=p).groupby("q") for c_ in ["_p"]}}


# ================================================================================================ ablation
def phase_ablation():
    S, D = data()
    sets = {f"without {k}": gcols(v) for k, v in {**DASH, **USER}.items()}
    out = {"full": {}}
    for k, g in D.groupby("lead"):
        if k <= 2:
            out["full"][int(k)] = metrics(g, g["P0H4_p3"])
    for name, drop in sets.items():
        keep = [c for c in FULL if c not in drop]
        fr = []
        for t in RL._origins():
            m, te = fit_origin(S, t, keep)
            if m is not None:
                fr.append(te[["t", "lead", "province_code"]].assign(pp=m.predict(te)))
        A = D.merge(pd.concat(fr), on=["t", "lead", "province_code"], how="left")
        assert A["pp"].notna().all(), name
        A["p"] = A["pi_H4"] * A["pp"]
        out[name] = {"dropped_columns": drop}
        for k, g in A.groupby("lead"):
            if k > 2:
                continue
            y = g["y"].astype(int).to_numpy()
            out[name][int(k)] = {**metrics(g, g["p"]),
                                 "brier_full_minus_ablated": FM.boot_diff(g, (g["P0H4_p3"] - y) ** 2, (g["p"] - y) ** 2)}
        m1, m2 = out[name][1], out[name][2]
        print(f"{name:34s} L1 acc {m1['acc']:.3f} bal {m1['bal']:.3f} R {m1['recall']:.2f} Brier {m1['brier']:.3f} "
              f"(d {m1['brier_full_minus_ablated']['diff']:+.4f} p {m1['brier_full_minus_ablated']['p_two']:.3f}) | "
              f"L2 acc {m2['acc']:.3f} bal {m2['bal']:.3f} R {m2['recall']:.2f} Brier {m2['brier']:.3f} "
              f"(d {m2['brier_full_minus_ablated']['diff']:+.4f} p {m2['brier_full_minus_ablated']['p_two']:.3f})", flush=True)
    ps = {(n, k): v[k]["brier_full_minus_ablated"]["p_two"] for n, v in out.items() if n != "full" for k in (1, 2)}
    for (n, k), h in FM.holm(ps).items():
        out[n][k]["brier_full_minus_ablated"]["holm_p"] = h
    FM.write_json(OUT / "group_ablation.json", out)


# ================================================================================================ permutation
def phase_permutation(reps: int = 20):
    S, D = data()
    models = {}
    for t in RL._origins():
        m, te = fit_origin(S, t, FULL)
        if m is not None:
            models[int(t)] = (m, te[te["lead"] <= 2].copy())
    H = pd.concat([te for _, te in models.values()])
    Dk = D[D["lead"] <= 2][["t", "lead", "province_code", "y", "q", "pi_H4", "P0H4_p3"]]

    def score(Hx):
        fr = [models[t][0].predict(g) for t, g in Hx.groupby("t")]
        pp = np.concatenate(fr)
        P = Hx.sort_values("t", kind="stable")[["t", "lead", "province_code"]].assign(pp=pp)
        A = Dk.merge(P, on=["t", "lead", "province_code"])
        A["p"] = A["pi_H4"] * A["pp"]
        return {int(k): float(np.mean((g["p"] - g["y"]) ** 2)) for k, g in A.groupby("lead")}
    H = H.sort_values("t", kind="stable")
    base = score(H)
    rng = np.random.default_rng(2031)
    ts = sorted(H["t"].unique())
    out = {"baseline_brier": base, "groups": {}}
    for name, fams in {**DASH, **USER}.items():
        cols = gcols(fams)
        deltas = {1: [], 2: []}
        for _ in range(reps):
            mp = dict(zip(ts, rng.permutation(ts)))
            src = H.set_index(["t", "lead", "province_code"])[cols]
            Hp = H.copy()
            keys = list(zip(Hp["t"].map(mp), Hp["lead"], Hp["province_code"]))
            vals = src.reindex(keys).to_numpy()
            Hp[cols] = np.where(np.isnan(vals.astype(float)), Hp[cols].to_numpy(float), vals)
            s = score(Hp)
            for k in (1, 2):
                deltas[k].append(s[k] - base[k])
        out["groups"][name] = {int(k): {"mean_brier_increase": float(np.mean(v)), "sd": float(np.std(v)),
                                        "share_of_shuffles_worse": float(np.mean(np.array(v) > 0))}
                               for k, v in deltas.items()}
        print(f"{name:34s} " + " | ".join(f"L{k}: dBrier {np.mean(v):+.4f} (sd {np.std(v):.4f}, worse in "
                                          f"{np.mean(np.array(v) > 0):.0%})" for k, v in deltas.items()), flush=True)
    FM.write_json(OUT / "permutation_importance.json", out)


# ================================================================================================ composition
def phase_composition():
    U.setup()
    R = pd.read_csv(SERVED / "rows.csv", dtype={"province_code": str})
    fams = ["A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"]
    G = {"market": ["A1", "A2", "A3"], "climate": ["C1", "C2", "C3"], "fish_kill": ["C4"], "employment": ["E1"],
         "ofw_remittance": ["E2"]}
    sh = R[[f"shap_{f}" for f in fams]].astype(float)
    gs = pd.DataFrame({g: sh[[f"shap_{f}" for f in v]].sum(axis=1).abs() for g, v in G.items()})
    pct = gs.div(gs.sum(axis=1).replace(0, np.nan), axis=0) * 100
    pct["quarter"], pct["province"] = R["quarter"], R["province"]
    by_q = pct.groupby("quarter")[list(G)].mean()
    out = {"rows": int(len(R)), "group_columns": {g: len(gcols(set(v))) for g, v in G.items()},
           "mean_share_pct": {g: float(pct[g].mean()) for g in G},
           "sd_across_quarters_pct": {g: float(by_q[g].std()) for g in G},
           "top_group_counts": pct[list(G)].idxmax(axis=1).value_counts().to_dict(),
           "quarters_where_top_group_changes": int((by_q.idxmax(axis=1) != by_q.idxmax(axis=1).shift()).sum() - 1)}
    tot = sh.abs().sum(axis=1).replace(0, np.nan)
    out["shared_value_families_share_of_abs_shap"] = float((sh[[f"shap_{f}" for f in SHARED]].abs().sum(axis=1) / tot).mean())
    v1 = R.assign(v=sh["shap_V1"]).groupby("province")["v"]
    out["V1_shap_between_province_var"] = float(v1.mean().var())
    out["V1_shap_within_province_var"] = float(v1.var().mean())
    S = U.stack(2)
    S = S[S["lead"] == 1]
    mk = gcols({"A1", "A2", "A3"})
    out["market_column_spearman"] = S[mk].corr(method="spearman").round(2).to_dict()
    out["missing_share_by_group"] = {g: float(S[gcols(set(v))].isna().all(axis=1).mean()) for g, v in G.items()}
    out["by_quarter_mean_share_pct"] = by_q.round(1).to_dict(orient="index")
    FM.write_json(OUT / "composition.json", out)
    print(json.dumps({k: v for k, v in out.items() if k not in ("market_column_spearman", "by_quarter_mean_share_pct")},
                     indent=1, default=float))


# ================================================================================================ sensitivity
def phase_sensitivity():
    S, D = data()
    out = []
    for q in ("2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"):
        t = L.qi(q)
        m, te = fit_origin(S, t, FULL)
        te = te[te["lead"] <= 2]
        p0 = m.predict(te)
        h = D.set_index(["t", "lead", "province_code"])["pi_H4"]
        hv = np.array([h.get((t, int(k), p), np.nan) for k, p in zip(te["lead"], te["province_code"])])
        for col, delta in (("A1_food", 0.5), ("A1_food", -0.5), ("A1_gap", 0.5), ("A2", 0.5), ("A3", 2.0),
                           ("E1", 0.2), ("C3", 5.0), ("C4", 5.0), ("V1", 0.05), ("H1", 0.05)):
            tp = te.copy()
            tp[col] = tp[col] + delta
            p1 = m.predict(tp)
            flips = int(np.nansum(((hv * p0) >= .5) != ((hv * p1) >= .5)))
            out.append({"origin": q, "input": col, "delta": delta, "max_abs_change_pi_P": float(np.max(np.abs(p1 - p0))),
                        "mean_abs_change_pi_P": float(np.mean(np.abs(p1 - p0))), "class_flips": flips, "rows": int(len(te))})
    O = pd.DataFrame(out)
    O.to_csv(OUT / "sensitivity.csv", index=False, lineterminator="\n", float_format="%.4g")
    print(O.groupby(["input", "delta"])[["max_abs_change_pi_P", "mean_abs_change_pi_P", "class_flips"]].agg(
        {"max_abs_change_pi_P": "max", "mean_abs_change_pi_P": "mean", "class_flips": "sum"}).round(3).to_string())


# ================================================================================================ predictive bias
def phase_predictive():
    U.setup()
    D = pd.read_csv(L2OUT / "predictions_addendum3.csv", dtype={"province_code": str})
    lab = C.labels().set_index(["province_code", "q"])["y"]
    out = {}
    for k in (1, 2):
        g = D[D["lead"] == k].copy()
        g["p"] = g["P0H4_p3"]
        g["prev"] = [lab.get((p, q - 1), np.nan) for p, q in zip(g["province_code"], g["q"])]
        g["event"] = np.select([(g["prev"] == 0) & (g["y"] == 1), (g["prev"] == 1) & (g["y"] == 1),
                                (g["prev"] == 1) & (g["y"] == 0)], ["onset", "sustained HIGH", "exit to LOW"],
                               "LOW after LOW or unknown")
        res = {}
        for dim, col in (("province", "province_code"), ("year", None), ("event", "event"), ("design", None)):
            if dim == "year":
                key = g["q"] // 4
            elif dim == "design":
                key = np.where(g["q"] >= L.qi("2025-Q2"), "adult base (>= 2025-Q2)", "household heads (< 2025-Q2)")
            else:
                key = g[col]
            rows = {}
            for kv, h in g.groupby(key):
                y = h["y"].astype(int).to_numpy()
                yh = (h["p"] >= .5).astype(int).to_numpy()
                ci = FM.boot_diff(h, h["p"].to_numpy(), y.astype(float)) if h["q"].nunique() > 1 else None
                rows[L.NAMES.get(kv, str(kv))] = {"rows": int(len(h)), "quarters": int(h["q"].nunique()), "high": int(y.sum()),
                                                  "mean_p": float(h["p"].mean()), "observed_rate": float(y.mean()),
                                                  "calibration_in_the_large": float(h["p"].mean() - y.mean()),
                                                  "cal_ci90": None if ci is None else ci["ci90"],
                                                  "acc": float((yh == y).mean()), "fn": int(((yh == 0) & (y == 1)).sum()),
                                                  "fp": int(((yh == 1) & (y == 0)).sum())}
            res[dim] = rows
            print(f"Lead {k} by {dim}:", {a: (round(b['calibration_in_the_large'], 3), b['acc'], b['fn'], b['fp'], b['high'])
                                         for a, b in rows.items()}, flush=True)
        out[k] = res
    FM.write_json(OUT / "predictive_bias.json", out)


# ================================================================================================ masking by Market
def _refit(S, D, keep):
    fr = []
    for t in RL._origins():
        m, te = fit_origin(S, t, keep)
        if m is not None:
            fr.append(te[["t", "lead", "province_code"]].assign(pp=m.predict(te)))
    A = D.merge(pd.concat(fr), on=["t", "lead", "province_code"], how="left")
    assert A["pp"].notna().all()
    A["p"] = A["pi_H4"] * A["pp"]
    return A


def phase_conditional():
    """Each non-market group's held-out value inside a model WITHOUT market (refit), vs its value in the full model."""
    S, D = data()
    base_keep = [c for c in FULL if FAM[c] not in DASH["market"]]
    B0 = _refit(S, D, base_keep)
    out = {"no_market_model": {int(k): metrics(g, g["p"]) for k, g in B0.groupby("lead") if k <= 2}, "groups": {}}
    for name, fams in {k: v for k, v in {**DASH, **USER}.items() if k != "market"}.items():
        keep = [c for c in base_keep if FAM[c] not in fams]
        A = _refit(S, D, keep)
        out["groups"][name] = {}
        for k in (1, 2):
            g0, g1 = B0[B0["lead"] == k], A[A["lead"] == k].set_index(["t", "province_code"]).loc[
                list(zip(B0[B0["lead"] == k]["t"], B0[B0["lead"] == k]["province_code"]))].reset_index()
            y = g0["y"].astype(int).to_numpy()
            t_ = FM.boot_diff(g0, (g0["p"].to_numpy() - y) ** 2, (g1["p"].to_numpy() - y) ** 2)
            out["groups"][name][k] = {"acc_without": float(((g1["p"] >= .5).astype(int) == g1["y"]).mean()),
                                      "brier_nomarket_minus_also_without_group": t_}
        print(f"{name:34s} inside no-market model: " + " | ".join(
            f"L{k} Brier d {out['groups'][name][k]['brier_nomarket_minus_also_without_group']['diff']:+.4f} "
            f"CI {[round(x, 4) for x in out['groups'][name][k]['brier_nomarket_minus_also_without_group']['ci90']]}"
            for k in (1, 2)), flush=True)
    ps = {(n, k): v[k]["brier_nomarket_minus_also_without_group"]["p_two"] for n, v in out["groups"].items() for k in (1, 2)}
    for (n, k), h in FM.holm(ps).items():
        out["groups"][n][k]["brier_nomarket_minus_also_without_group"]["holm_p"] = h
    m = out["no_market_model"]
    print("no-market model:", {k: (round(v["acc"], 3), round(v["brier"], 4)) for k, v in m.items()})
    FM.write_json(OUT / "conditional_ablation.json", out)


def phase_fairshare():
    """SHAP share per column (group size) and on rows where the group's inputs were present (missingness)."""
    U.setup()
    S = U.stack(RL._K())
    rows = []
    for t in RL._origins():
        m, te = fit_origin(S, t, FULL)
        if m is None:
            continue
        te = te[te["lead"] <= 2]
        sv = m.shap(te)
        if sv is None:
            continue
        df = pd.DataFrame(sv[:, :len(FULL)], columns=FULL)
        df["t"], df["lead"] = te["t"].to_numpy(), te["lead"].to_numpy()
        for c in FULL:
            df[f"present_{c}"] = te[c].notna().to_numpy()
        rows.append(df)
    A = pd.concat(rows, ignore_index=True)
    groups = {**DASH}
    out = {}
    tot = A[FULL].abs().sum(axis=1).replace(0, np.nan)
    for name, fams in groups.items():
        cs = gcols(fams)
        share = A[cs].abs().sum(axis=1) / tot
        present = A[[f"present_{c}" for c in cs]].any(axis=1)
        by_origin = share.groupby(A["t"]).mean()
        out[name] = {"columns": len(cs), "mean_share_all_rows": float(share.mean()),
                     "mean_share_per_column": float(share.mean() / len(cs)),
                     "mean_share_rows_with_inputs": float(share[present].mean()) if present.any() else None,
                     "rows_with_inputs": float(present.mean()),
                     "share_sd_across_origins": float(by_origin.std()),
                     "share_range_across_origins": [float(by_origin.min()), float(by_origin.max())]}
        print(f"{name:26s} cols {len(cs)} share {out[name]['mean_share_all_rows']:.3f} per-col "
              f"{out[name]['mean_share_per_column']:.3f} | with inputs {out[name]['mean_share_rows_with_inputs']} "
              f"(present {out[name]['rows_with_inputs']:.2f}) | sd across origins {out[name]['share_sd_across_origins']:.3f}",
              flush=True)
    FM.write_json(OUT / "fair_share.json", out)


if __name__ == "__main__":
    {"ablation": phase_ablation, "permutation": phase_permutation, "composition": phase_composition,
     "sensitivity": phase_sensitivity, "predictive": phase_predictive,
     "conditional": phase_conditional, "fairshare": phase_fairshare}[sys.argv[1]]()
