"""E83 analysis of a completed run (round 1 + round 2 files): result tables, news and driver ablations, group
permutation importance, placebo, T43 audit. Writes RESULTS.json and RESULTS_TABLES.md into the run directory.

Run from backend/:  python .../analyze.py <run_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_e83 as R  # noqa: E402
import run_round2 as R2  # noqa: E402

E, L, np, pd = R.E, R.L, R.np, R.pd
SHOW = ["B-PERSIST", "B-STATE", "B-MAJ", "B-CLIM", "B-AH", "B-AL", "B-PSA", "B-NLP", "S-SIM", "S-SIM-SEAS", "S-SIM-THR",
        "S-SIM-SEAS-THR", "ST-LR", "ST-LR-N2", "ST-LR-N3", "M-LR-ALL", "M-GB-ALL", "M-GB-S"]


def fmt(x, d=3):
    return "–" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def lead_table(P, res, tests):
    lines = ["| Arm | issued/rows | correct | accuracy (unissued = wrong) | balanced acc | precision | recall HIGH | F1 | "
             "Brier | AUC | rising-row recall | acc 95% CI (issued, date bootstrap) | PASS |", "|" + "---|" * 13]
    for a in SHOW:
        if a not in res:
            continue
        m, mi = res[a]["all_rows_unissued_wrong"], res[a]["issued_rows"]
        rr = res[a].get("rising_rows", {})
        ps = R.passes(res, tests, a) if a in R.PRIMARY else {}
        lines.append(f"| {a} | {mi['issued']}/{m['n']} | {m['TP'] + m['TN']} | {fmt(m['accuracy'])} | {fmt(m['balanced_accuracy'])} | "
                     f"{fmt(m['precision'])} | {fmt(m['recall_HIGH'])} | {fmt(m['f1'])} | {fmt(m.get('brier'))} | "
                     f"{fmt(mi.get('roc_auc'))} | {fmt(rr.get('recall_HIGH'))} | "
                     f"[{fmt(res[a]['accuracy_ci95_issued'][0], 2)}, {fmt(res[a]['accuracy_ci95_issued'][1], 2)}] | "
                     f"{'PASS' if ps.get('PASS') else ('fail' if ps else 'baseline')} |")
    return "\n".join(lines)


def ablation(P, res, names):
    out = []
    for a in names:
        if a in res:
            mi = res[a]["issued_rows"]
            out.append({"arm": a, "issued": mi["issued"], "accuracy": mi["accuracy"], "balanced": mi["balanced_accuracy"],
                        "brier": mi.get("brier"), "recall_HIGH": mi["recall_HIGH"], "f1": mi["f1"],
                        "auc": mi.get("roc_auc")})
    return out


def paired_news_test(P, base, arm):
    D = P[P[base].notna() & P[arm].notna()]
    g = D.assign(da=(D[base] - D["y"]) ** 2 - (D[arm] - D["y"]) ** 2).groupby("target_q")["da"].mean().to_numpy()
    return E.sign_flip(g) if len(g) else None


def permutation_importance(X, d, k, P, kind="LR", reps=200, seed=83):
    """Within-quarter permutation of one driver group's columns across the five provinces of each test quarter, for
    the M-LR-ALL / M-GB-ALL learner fitted at each origin; importance = mean Brier increase on issued rows."""
    rng = np.random.default_rng(seed)
    cols = R.cols_of(R.BASE_GROUPS) + R.NEWS_V0
    groups = {g: [c for c in E.DRIVERS[g]] for g in R.BASE_GROUPS + ["D5_news_v0"]}
    base_b, inc = [], {g: [] for g in groups}
    for t in sorted(P["t"].unique()):
        tr = E.pairs(X, d, t, k)
        if not E.eligible(tr):
            continue
        te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        y = P[P["t"] == t].set_index("province_code").loc[L.PROVS]["y"].to_numpy()
        m = R.learner(kind, cols).fit(tr)
        b0 = np.mean((m.predict(te) - y) ** 2)
        base_b.append(b0)
        for g, gc in groups.items():
            vals = []
            for _ in range(reps):
                tp = te.copy()
                perm = rng.permutation(5)
                tp[gc] = te[gc].to_numpy()[perm]
                vals.append(np.mean((m.predict(tp) - y) ** 2) - b0)
            inc[g].append(float(np.mean(vals)))
    return {g: (float(np.mean(v)) if v else None) for g, v in inc.items()}, len(base_b)


def placebo(X, d, k, P, reps=50, seed=83):
    """ST-LR-N3 refitted on training labels permuted across rows: the Brier gain over B-CLIM must vanish."""
    rng = np.random.default_rng(seed)
    gains = []
    for r in range(reps):
        ps = []
        for t in sorted(P["t"].unique()):
            te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
            tr = E.pairs(X, d, t, k)
            tr = tr.assign(y=rng.permutation(tr["y"].to_numpy())) if len(tr) else tr
            p, _ = R2.stack(tr, te, ["n3_market_rw", "n3_climate_rw", "n3_fssi"])
            ps.extend(p)
        Pp = P.assign(PLACEBO=ps)
        D = Pp[Pp["PLACEBO"].notna()]
        gains.append(float(np.mean((D["B-CLIM"] - D["y"]) ** 2) - np.mean((D["PLACEBO"] - D["y"]) ** 2)))
    real = P[P["ST-LR-N3"].notna()]
    return {"placebo_brier_gain_vs_clim_mean": float(np.mean(gains)), "placebo_p95": float(np.percentile(gains, 95)),
            "real_brier_gain_vs_clim": float(np.mean((real["B-CLIM"] - real["y"]) ** 2) - np.mean((real["ST-LR-N3"] - real["y"]) ** 2))}


def t43_audit(d):
    lab = E.labels_all(d)
    th = L.e40_spec()
    lab["sws_hi"] = (lab["H"] > th["H"]).astype(int)
    lab["price_hi"] = ((lab["F"] > lab["province_code"].map(th["food"])) |
                       ((lab["F"] - lab["HL"]) > lab["province_code"].map(th["gap"]))).astype(int)
    ev = lab[lab["q"] >= E.EVAL_FROM]
    q = ev.groupby("q").agg(H=("H", "first"), F=("F", "mean"), high=("y", "sum")).reset_index()
    return {
        "labelled_quarters_all": int(lab["q"].nunique()), "eval_quarters": int(ev["q"].nunique()),
        "eval_rows": int(len(ev)), "eval_high": int(ev["y"].sum()),
        "share_eval_rows_with_hunger_above_line": float(ev["sws_hi"].mean()),
        "quarters_since_2023Q4_with_hunger_above_line": f"{int((ev[ev.q >= L.qi('2023-Q4')].groupby('q')['sws_hi'].first()).sum())}/"
                                                        f"{int(ev[ev.q >= L.qi('2023-Q4')]['q'].nunique())}",
        "agreement_T43_with_price_signal_since_2023Q4": float((ev[ev.q >= L.qi("2023-Q4")]["y"] ==
                                                              ev[ev.q >= L.qi("2023-Q4")]["price_hi"]).mean()),
        "corr_regional_H_vs_mean_province_food_yoy": float(np.corrcoef(q["H"], q["F"])[0, 1]),
        "high_by_province": {L.NAMES[p]: int(v) for p, v in ev.groupby("province_code")["y"].sum().items()},
        "high_by_year": {str(int(y)): int(v) for y, v in ev.assign(yr=ev["q"] // 4).groupby("yr")["y"].sum().items()},
    }


if __name__ == "__main__":
    run = Path(sys.argv[1])
    d, x = E.data()
    R.PRIMARY[:] = ["S-SIM", "S-SIM-SEAS", "S-SIM-THR", "S-SIM-SEAS-THR", "ST-LR", "ST-LR-N2", "ST-LR-N3", "M-LR-ALL",
                    "M-GB-ALL", "M-GB-S"]
    out, md = {"t43_audit": t43_audit(d), "leads": {}}, ["# E83 result tables (generated by runner/analyze.py)\n"]
    for k in E.LEADS:
        f = run / f"predictions_r2_k{k}.csv"
        if not f.exists():
            continue
        P = pd.read_csv(f, dtype={"province_code": str})
        X = pd.read_csv(run / f"features_r2_k{k}.csv", dtype={"province_code": str})
        res, tests = R.evaluate(P)
        lk = {"rows": len(P), "targets": sorted(P["target_q"].unique().tolist()), "prevalence": float(P["y"].mean()),
              "pass": {a: R.passes(res, tests, a) for a in R.PRIMARY if a in res},
              "news_ablation": {kind: ablation(P, res, [f"NA-{kind}", f"NB-{kind}", f"NC-{kind}", f"ND-{kind}", f"NN3-{kind}"])
                                for kind in ("LR", "GB")},
              "news_ablation_structural": ablation(P, res, ["ST-LR", "ST-LR-N2", "ST-LR-N3"]),
              "news_paired_tests": {f"{b}->{a}": paired_news_test(P, b, a) for b, a in
                                    [("NA-LR", "NB-LR"), ("NA-LR", "NC-LR"), ("NA-LR", "ND-LR"), ("NA-LR", "NN3-LR"),
                                     ("NA-GB", "NB-GB"), ("NA-GB", "NC-GB"), ("NA-GB", "ND-GB"), ("NA-GB", "NN3-GB"),
                                     ("ST-LR", "ST-LR-N2"), ("ST-LR", "ST-LR-N3")]},
              "driver_ablation": {kind: ablation(P, res, [f"{w}-{g}-{kind}" for w in ("DROP", "ONLY")
                                                           for g in R.BASE_GROUPS + ["NEWS"]]) for kind in ("LR", "GB")},
              "tests": tests}
        if k in (1, 2):
            lk["group_permutation_LR"], lk["perm_origins"] = permutation_importance(X, d, k, P, "LR")
            lk["group_permutation_GB"], _ = permutation_importance(X, d, k, P, "GB")
        if k == 2:
            lk["placebo_ST_LR_N3"] = placebo(X, d, k, P)
        out["leads"][k] = lk
        md += [f"\n## Lead {k}: {len(P)} rows, {P['target_q'].nunique()} target quarters, HIGH share {P['y'].mean():.3f}\n",
               lead_table(P, res, tests)]
        print(f"lead {k} done", flush=True)
    (run / "RESULTS.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    (run / "RESULTS_TABLES.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(out["t43_audit"], indent=1))
