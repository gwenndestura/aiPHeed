"""E35 nested hyperparameter tuning of E32-PCFN under the frozen protocol (PROTOCOL.md; sha in PROTOCOL_SHA256.txt).

    python -B runner/e35_tune.py   -> runs/<UTC stamp>/{predictions.csv, config_scores.csv, inner_scores.csv,
                                                         selection_log.csv, results.json, RESULTS_TABLE.md}

Deterministic: no timestamp or path is written inside the run files, so a repeat run is byte-identical.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone

import e35_common as E
import e35_grid as G

np, pd, C, L, M = E.np, E.pd, E.C, E.L, E.M
E32RUN = E.E32 / "runs" / "20261014T165201Z"
DATES = {1: ["2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"],
         2: ["2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]}
OPERATIONAL_T = C.qk("2026-Q3")
MIN_INNER, TIE, SEED_SEL, B_SEL = 3, 0.005, 35, 2000
COMPARATORS = ("E32-PCFN", "PCF21", "B1", "ALWAYS_HIGH")
CFG = {c.id: c for c in G.GRID}
DEFAULT_ID = G.DEFAULT_CFG.id


def verify_protocol() -> str:
    want = (E.E35 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = E.sha(E.E35 / "PROTOCOL.md")
    if got != want:
        raise SystemExit(f"protocol changed after freezing ({got} != {want})")
    return want


def select(scores: dict[str, float]) -> tuple[str, list[str]]:
    """PROTOCOL 4.4: lowest score; every config within TIE of the best is tied; ties by Config.tie_key."""
    best = min(scores.values())
    tied = [c for c, v in scores.items() if v <= best + TIE]
    return min(tied, key=lambda c: (CFG[c].tie_key(), c)), tied


def inner_dates(d, k: int, t: int, pool: list[str]) -> list[str]:
    posted = set(d.posted_quarters(L.origin(t)))
    return [T for T in pool if C.qk(T) <= t - 1 and C.qk(T) in posted]


def per_date_brier(df: pd.DataFrame) -> pd.Series:
    return M.per_date_losses(df)["bri"]


def main():
    proto = verify_protocol()
    d = L.Data()
    e32 = pd.read_csv(E32RUN / "predictions.csv", dtype={"province_code": str})
    rows, grid_rows = [], []
    for k, dates in DATES.items():
        for T in dates:
            t = C.qk(T) - k
            labs = {p: d.label(p, C.qk(T), t) for p in C.PROVS}
            gp = G.all_probs(d, t, k)
            refs = L.references(d, t, k)
            arms = {"E32-PCFN": gp[DEFAULT_ID], "PCF21": L.pcf21(d, t, k), **refs,
                    "E32-ENS": {p: 0.5 * (gp[DEFAULT_ID][p] + refs["B1p"][p]) for p in C.PROVS}}
            for cid, pr in gp.items():
                for p in C.PROVS:
                    grid_rows.append({"lead": k, "t": C.qs(t), "target_quarter": T, "province_code": p,
                                      "config": cid, "p": pr[p], "y": labs[p]})
            for arm, pr in arms.items():
                for p in C.PROVS:
                    rows.append({"lead": k, "t": C.qs(t), "target_quarter": T, "province_code": p, "arm": arm,
                                 "p": float(pr[p]), "y": labs[p]})
    Pr, Gr = pd.DataFrame(rows), pd.DataFrame(grid_rows)

    # ---- recomputed arms must equal E32's stored predictions (PROTOCOL 5)
    chk = Pr.merge(e32, on=["lead", "t", "target_quarter", "province_code", "arm"], suffixes=("", "_e32"))
    repro = {"rows_compared": int(len(chk)), "max_abs_diff": float((chk["p"] - chk["p_e32"]).abs().max()),
             "label_mismatches": int((chk["y"] != chk["y_e32"]).sum())}
    if len(chk) != len(Pr) or repro["max_abs_diff"] > 5e-10 or repro["label_mismatches"]:
        raise SystemExit(f"recomputed arms differ from E32: {repro}")
    p45 = e32[e32["arm"] == "P45"][Pr.columns]
    Pr = pd.concat([Pr, p45], ignore_index=True)

    # ---- per-date Brier of every configuration
    Gr["bri"] = (np.clip(Gr["p"].to_numpy(float), M.EPS, 1 - M.EPS) - Gr["y"].to_numpy(float)) ** 2
    PDB = {k: Gr[Gr["lead"] == k].groupby(["config", "t"])["bri"].mean().unstack()
           for k in DATES}                                   # rows: config, columns: t (origin quarter)
    Gr = Gr.drop(columns="bri")
    t_of = {k: {T: C.qs(C.qk(T) - k) for T in DATES[k]} for k in DATES}

    # ---- nested selection (primary), LODO and FULL (sensitivity)
    sel_log, inner_rows, tuned = [], [], []
    for k, dates in DATES.items():
        full_scores = PDB[k].mean(axis=1).to_dict()
        full_pick, full_tied = select(full_scores)
        for T in dates:
            t = C.qk(T) - k
            inner = inner_dates(d, k, t, dates)
            if len(inner) >= MIN_INNER:
                sc = PDB[k][[t_of[k][x] for x in inner]].mean(axis=1).to_dict()
                pick, tied = select(sc)
                for cid, v in sc.items():
                    inner_rows.append({"lead": k, "outer_target": T, "config": cid, "inner_mean_brier": v,
                                       "n_inner": len(inner)})
            else:
                pick, tied, sc = DEFAULT_ID, [], {}
            lodo_sc = PDB[k][[t_of[k][x] for x in dates if x != T]].mean(axis=1).to_dict()
            lodo_pick, _ = select(lodo_sc)
            sel_log.append({"lead": k, "outer_target": T, "origin": str(L.origin(t).date()), "n_inner": len(inner),
                            "inner_dates": " ".join(inner), "selected": pick, "n_tied": len(tied),
                            "best_inner_brier": min(sc.values()) if sc else None,
                            "default_inner_brier": sc.get(DEFAULT_ID), "lodo_selected": lodo_pick,
                            "full_selected": full_pick})
            for arm, cid in (("E35-TUNED", pick), ("S-LODO", lodo_pick), ("S-FULL", full_pick)):
                g = Gr[(Gr["lead"] == k) & (Gr["target_quarter"] == T) & (Gr["config"] == cid)]
                tuned += [{"lead": k, "t": r.t, "target_quarter": T, "province_code": r.province_code, "arm": arm,
                           "p": r.p, "y": r.y} for r in g.itertuples()]
    Pr = pd.concat([Pr, pd.DataFrame(tuned)], ignore_index=True)
    SL = pd.DataFrame(sel_log)

    res = {"protocol_sha256": proto, "dataset_sha256": E.dataset_manifest(), "seeds": {
        "date_bootstrap_metrics": M.SEED, "selection_bootstrap": SEED_SEL, "model": "none (deterministic)"},
        "search_space": {"lambda": list(G.LAMBDAS), "D_sets": {k: list(v) for k, v in G.D_SETS.items()},
                         "c": list(G.SCALES), "n_configs": len(G.GRID), "default": DEFAULT_ID},
        "reproduces_E32": repro, "metrics": {}, "per_date_brier": {}, "tests": {}, "selection": {},
        "acceptance": {}}

    # ---- metrics, per-date Brier, skill scores
    for k in DATES:
        s = Pr[Pr["lead"] == k]
        for arm, g in s.groupby("arm"):
            m = M.point_metrics(g["y"], g["p"])
            m["flags"] = M.flags(m, g["t"].nunique())
            m.update(M.bootstrap(g))
            m["mean_per_date_brier"] = float(per_date_brier(g).mean())
            res["metrics"].setdefault(f"lead{k}", {})[arm] = m
        mpd = {a: v["mean_per_date_brier"] for a, v in res["metrics"][f"lead{k}"].items()}
        for arm in mpd:
            res["metrics"][f"lead{k}"][arm]["BSS_vs_ALWAYS_HIGH"] = 1 - mpd[arm] / mpd["ALWAYS_HIGH"]
            res["metrics"][f"lead{k}"][arm]["BSS_vs_CLIM"] = 1 - mpd[arm] / mpd["CLIM"]
        pdb = {a: per_date_brier(g) for a, g in s.groupby("arm")}
        res["per_date_brier"][f"lead{k}"] = {a: v.round(8).to_dict() for a, v in pdb.items()}
        raw = {}
        for ref in COMPARATORS:
            diff = (pdb[ref] - pdb["E35-TUNED"]).dropna().to_numpy()
            raw[ref] = M.signflip_p(diff)
            res["tests"].setdefault(f"lead{k}", {})[f"vs_{ref}"] = {
                "dates": int(len(diff)), "mean_brier_gain": float(diff.mean()), "dates_better": int((diff > 0).sum()),
                "dates_worse": int((diff < 0).sum()), "dates_equal": int((diff == 0).sum()), "p_one_sided": raw[ref]}
        for ref, p in M.holm(raw).items():
            res["tests"][f"lead{k}"][f"vs_{ref}"]["p_holm"] = p

        # ---- selection uncertainty (PROTOCOL 8)
        mat = PDB[k][[t_of[k][T] for T in DATES[k]]]
        full = mat.mean(axis=1)
        rng = np.random.default_rng(SEED_SEL)
        wins, boot_means = {}, []
        A = mat.to_numpy()
        for _ in range(B_SEL):
            idx = rng.integers(0, A.shape[1], A.shape[1])
            mb = A[:, idx].mean(axis=1)
            boot_means.append(mb)
            c, _ = select(dict(zip(mat.index, mb)))
            wins[c] = wins.get(c, 0) + 1
        boot_means = np.array(boot_means)
        ci = {cid: [float(np.percentile(boot_means[:, i], 2.5)), float(np.percentile(boot_means[:, i], 97.5))]
              for i, cid in enumerate(mat.index)}
        g = SL[SL["lead"] == k]
        full_pick = g["full_selected"].iloc[0]
        res["selection"][f"lead{k}"] = {
            "nested_selected_per_origin": dict(zip(g["outer_target"], g["selected"])),
            "nested_distinct_selections": int(g["selected"].nunique()),
            "nested_origins_using_default_for_lack_of_inner_dates": int((g["n_inner"] < MIN_INNER).sum()),
            "nested_origins_selecting_default": int((g["selected"] == DEFAULT_ID).sum()),
            "full_selected": full_pick, "full_selected_brier": float(full[full_pick]),
            "min_config": str(full.idxmin()), "full_best_brier": float(full.min()), "default_full_brier": float(full[DEFAULT_ID]),
            "configs_within_tie_of_best": int((full <= full.min() + TIE).sum()),
            "bootstrap_selection_frequency": {c: v / B_SEL for c, v in sorted(wins.items(), key=lambda x: -x[1])},
            "bootstrap_default_selected_share": wins.get(DEFAULT_ID, 0) / B_SEL,
            "optimism_nested_minus_full_selected": res["metrics"][f"lead{k}"]["E35-TUNED"]["mean_per_date_brier"] - float(full[full_pick]),
            "optimism_nested_minus_min_config": res["metrics"][f"lead{k}"]["E35-TUNED"]["mean_per_date_brier"] - float(full.min()),
            "config_full_brier": {c: {"brier": float(full[c]), "ci95": ci[c]} for c in full.sort_values().index},
            "range_of_config_brier": [float(full.min()), float(full.max())]}

    # ---- acceptance (lead 1) and verdict (PROTOCOL 9)
    m1 = {a: v["mean_per_date_brier"] for a, v in res["metrics"]["lead1"].items()}
    tu = res["metrics"]["lead1"]["E35-TUNED"]
    t1 = res["tests"]["lead1"]
    A = {"A1_brier_below_PCF21": m1["E35-TUNED"] < m1["PCF21"],
         "A2_brier_not_worse_than_persistence": m1["E35-TUNED"] <= m1["B1"],
         "A3_accuracy_at_least_0.75": tu["accuracy"] >= 0.75,
         "A4_operational_inference": "verified by verification/VERIFICATION.json V5/V6 and the prospective step below",
         "T_brier_below_E32_PCFN": m1["E35-TUNED"] < m1["E32-PCFN"]}
    passed = A["A1_brier_below_PCF21"] and A["A2_brier_not_worse_than_persistence"] and A["A3_accuracy_at_least_0.75"] \
        and A["T_brier_below_E32_PCFN"]
    sig = all(t1[f"vs_{r}"]["p_holm"] is not None and t1[f"vs_{r}"]["p_holm"] < 0.05 for r in ("E32-PCFN", "PCF21", "B1"))
    verdict = "GENUINE IMPROVEMENT" if (passed and sig) else ("NOMINAL, WITHIN VALIDATION NOISE" if passed else "NO IMPROVEMENT")
    res["acceptance"] = {**A, "mean_per_date_brier_lead1": m1, "accuracy_lead1": tu["accuracy"], "verdict": verdict,
                         "production": "PCF21 remains served (PROTOCOL 9)"}

    # ---- prospective selection at the operational origin (PROTOCOL 10); frozen separately by e35_freeze.py
    prosp = {}
    for k, dates in DATES.items():
        inner = inner_dates(d, k, OPERATIONAL_T, dates)
        sc = PDB[k][[t_of[k][x] for x in inner]].mean(axis=1).to_dict()
        pick, tied = select(sc)
        prosp[str(k)] = {"origin": str(L.origin(OPERATIONAL_T).date()), "target_quarter": C.qs(OPERATIONAL_T + k),
                         "inner_dates": inner, "selected": pick, "n_tied": len(tied),
                         "p_high": G.all_probs(d, OPERATIONAL_T, k)[pick],
                         "default_p_high": G.all_probs(d, OPERATIONAL_T, k)[DEFAULT_ID]}
    res["prospective_selection"] = prosp

    # ---- write
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = E.E35 / "runs" / stamp
    run.mkdir(parents=True)
    Pr = Pr.sort_values(["lead", "arm", "target_quarter", "province_code"])
    Gr = Gr.sort_values(["lead", "config", "target_quarter", "province_code"])
    w = dict(index=False, float_format="%.10g", lineterminator="\n")
    (run / "predictions.csv").write_bytes(Pr.to_csv(**w).encode())
    (run / "grid_predictions.csv").write_bytes(Gr.to_csv(**w).encode())
    cs = []
    for k in DATES:
        for cid in CFG:
            g = Gr[(Gr["lead"] == k) & (Gr["config"] == cid)]
            m = M.point_metrics(g["y"], g["p"])
            cs.append({"lead": k, "config": cid, "lambda": CFG[cid].lam, "D_set": CFG[cid].dset, "c": CFG[cid].c,
                       "mean_per_date_brier": float(PDB[k].loc[cid].mean()), "accuracy": m["accuracy"],
                       "balanced_accuracy": m["balanced_accuracy"], "precision": m["precision"], "recall": m["recall"],
                       "f1": m["f1"], "roc_auc": m["roc_auc"], "log_loss": m["log_loss"], "ece_3bin": m["ece_3bin"],
                       "calibration_in_the_large": m["calibration_in_the_large"], "TP": m["TP"], "FP": m["FP"],
                       "TN": m["TN"], "FN": m["FN"]})
    (run / "config_scores.csv").write_bytes(pd.DataFrame(cs).to_csv(**w).encode())
    (run / "inner_scores.csv").write_bytes(pd.DataFrame(inner_rows).to_csv(**w).encode())
    (run / "selection_log.csv").write_bytes(SL.to_csv(**w).encode())
    C.write_json(run / "results.json", C.clean(res))
    (run / "RESULTS_TABLE.md").write_bytes(results_table(res).encode())
    print(run.name, hashlib.sha256((run / "predictions.csv").read_bytes()).hexdigest()[:16],
          hashlib.sha256((run / "results.json").read_bytes()).hexdigest()[:16])
    print("verdict:", verdict, {k: v for k, v in A.items() if k[0] in "AT" and isinstance(v, bool)})
    for k in DATES:
        mm = res["metrics"][f"lead{k}"]
        print(f"lead {k}", {a: (round(v["mean_per_date_brier"], 4), round(v["accuracy"], 3)) for a, v in
                            sorted(mm.items(), key=lambda x: x[1]["mean_per_date_brier"])})
        print("  selected per origin", res["selection"][f"lead{k}"]["nested_selected_per_origin"])


def f(x, n=4):
    return "—" if x is None else (f"{x:.{n}f}" if isinstance(x, float) else str(x))


def results_table(res: dict) -> str:
    order = ["E35-TUNED", "E32-PCFN", "PCF21", "B1", "B1p", "ALWAYS_HIGH", "CLIM", "E32-ENS", "S-LODO", "S-FULL", "P45"]
    out = ["# E35 results table (generated by runner/e35_tune.py)", "",
           f"Protocol sha `{res['protocol_sha256'][:16]}…`. Outer dates: lead 1 = 10, lead 2 = 8. "
           "S-LODO and S-FULL are sensitivity arms (not temporally valid / in-sample); P45 is on its common rows only.", ""]
    for k in ("lead1", "lead2"):
        mm, tt = res["metrics"][k], res["tests"][k]
        out += [f"## {k}", "",
                "| Arm | Dates | n | HIGH/LOW | Brier (per date) | 95% CI | BSS vs ALWAYS_HIGH | Accuracy | Bal. acc | Precision | Recall | F1 | ROC-AUC | ECE | CITL | TP/FP/TN/FN |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for a in order:
            if a not in mm:
                continue
            m = mm[a]
            auc = f(m["roc_auc"], 3) + (" (UNSTABLE)" if m["flags"]["roc_auc"] == "UNSTABLE" else "")
            out.append(f"| {a} | {m['n_dates']} | {m['n']} | {m['HIGH']}/{m['LOW']} | {f(m['mean_per_date_brier'])} | "
                       f"{f(m['brier_ci95'][0], 3)}–{f(m['brier_ci95'][1], 3)} | {f(m['BSS_vs_ALWAYS_HIGH'], 3)} | "
                       f"{f(m['accuracy'], 3)} | {f(m['balanced_accuracy'], 3)} | {f(m['precision'], 3)} | "
                       f"{f(m['recall'], 3)} | {f(m['f1'], 3)} | {auc} | {f(m['ece_3bin'], 3)} | "
                       f"{f(m['calibration_in_the_large'], 3)} | {m['TP']}/{m['FP']}/{m['TN']}/{m['FN']} |")
        out += ["", "| E35-TUNED vs | Mean per-date Brier gain | Better/worse/equal dates | p (one-sided) | p (Holm) |",
                "|---|---|---|---|---|"]
        for r in COMPARATORS:
            x = tt[f"vs_{r}"]
            out.append(f"| {r} | {f(x['mean_brier_gain'], 5)} | {x['dates_better']}/{x['dates_worse']}/{x['dates_equal']} | "
                       f"{f(x['p_one_sided'], 3)} | {f(x['p_holm'], 3)} |")
        s = res["selection"][k]
        out += ["", f"Nested selections: {s['nested_selected_per_origin']}", "",
                f"In-sample (S-FULL) selection {s['full_selected']} (Brier {f(s['full_selected_brier'])}; the lowest of the 36 is "
                f"{s['min_config']} at {f(s['full_best_brier'])}, inside the 0.005 tie); E32 default {f(s['default_full_brier'])}; "
                f"{s['configs_within_tie_of_best']} configurations within 0.005 of the lowest; "
                f"bootstrap: default selected in {s['bootstrap_default_selected_share']:.1%} of resamples; "
                f"optimism (nested E35-TUNED − S-FULL) {f(s['optimism_nested_minus_full_selected'])} "
                f"(− lowest configuration: {f(s['optimism_nested_minus_min_config'])}).", ""]
    a = res["acceptance"]
    out += ["## Acceptance (lead 1)", "", f"Verdict: **{a['verdict']}**", ""] + \
        [f"- {k}: {v}" for k, v in a.items() if k[:2] in ("A1", "A2", "A3", "A4", "T_")]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.exit(main())
