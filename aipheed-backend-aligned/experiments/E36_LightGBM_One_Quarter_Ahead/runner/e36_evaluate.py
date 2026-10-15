"""E36 walk-forward evaluation under the frozen protocol (PROTOCOL.md; sha in runner/PROTOCOL_SHA256.txt).

    python -B runner/e36_evaluate.py   -> runs/<UTC stamp>/{predictions.csv, results.json, summary.md}

Lead 1, development targets 2022-Q4..2026-Q3 (14 dates). The proposed model and the LightGBM ablations are scored
under the nested rule; the six Chapter I baselines and the diagnostics on identical rows.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e36_lib as L  # noqa: E402
import e28_metrics as M  # noqa: E402

C, np, pd = L.C, L.np, L.pd
EXPS = L.EXPS
E25RUN = EXPS / "E25_Reliable_Forecasts_2021_2026" / "runs" / "20261014T002026Z" / "predictions_T1_A.csv"
EXT = EXPS / "2026-10-14_P45_2026_Extension" / "runs" / "20261014T105026Z" / "predictions.csv"
F12RUN = EXPS / "2026-10-14_Model_Selection_45_vs_12" / "runs" / "20261014T101104Z" / "predictions.csv"

BASELINES = ["B1_PERSISTENCE", "B2_LR_COMB", "B3_LR_GOV", "B4_LR_NLP", "B5_LGBM_GOV", "B6_LGBM_NLP"]
PROPOSED = "E36-LGBM"


def verify_protocol() -> str:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((L.E36 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit(f"protocol changed after freezing ({got} != {want})")
    return want


def stored_candidates() -> pd.DataFrame:
    """P45 (E25 run + 2026 extension) and F12 (45-vs-12 selection run), lead 1, as stored."""
    rows = []
    a = pd.read_csv(E25RUN, dtype={"province_code": str})
    a = a[(a["model"] == "PROPOSED_lgbm_combined") & (a["lead"] == 1)]
    rows += [("P45", r.target_quarter, r.province_code, float(r.score)) for r in a.itertuples()]
    b = pd.read_csv(EXT, dtype={"province_code": str})
    b = b[(b["model"] == "P45") & (b["lead"] == 1)]
    rows += [("P45", r.target_quarter, r.province_code, float(r.score)) for r in b.itertuples()]
    f = pd.read_csv(F12RUN, dtype={"province_code": str})
    f = f[(f["model"] == "F12") & (f["lead"] == 1)]
    rows += [("F12", r.target_quarter, r.province_code, float(r.score)) for r in f.itertuples()]
    return pd.DataFrame(rows, columns=["arm", "target_quarter", "province_code", "p"]).drop_duplicates(
        ["arm", "target_quarter", "province_code"], keep="last")


# ------------------------------------------------------------------ statistics
def wilson(k: int, n: int, z: float = 1.959964) -> list[float]:
    if n == 0:
        return [None, None]
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return [c - h, c + h]


def binom_upper_p(k: int, n: int, p0: float = 0.75) -> float:
    """One-sided exact P(X >= k | n, p0): evidence that accuracy exceeds p0 (rows treated as independent)."""
    return float(sum(math.comb(n, i) * p0 ** i * (1 - p0) ** (n - i) for i in range(k, n + 1)))


def mcnemar_exact(a_ok: np.ndarray, b_ok: np.ndarray) -> dict:
    b = int((a_ok & ~b_ok).sum())      # arm right, reference wrong
    c = int((~a_ok & b_ok).sum())
    n = b + c
    if n == 0:
        return {"arm_only_correct": b, "ref_only_correct": c, "p_two_sided": 1.0}
    tail = sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
    return {"arm_only_correct": b, "ref_only_correct": c, "p_two_sided": float(min(1.0, 2 * tail))}


def signflip_two(diffs) -> float | None:
    d = np.asarray(diffs, float)
    if len(d) == 0:
        return None
    pr, ng = M.signflip_p(d), M.signflip_p(-d)
    return float(min(1.0, 2 * min(pr, ng)))


def discrimination(g: pd.DataFrame) -> dict:
    sd, mixed_pred, w_auc = [], 0, []
    for _, h in g.groupby("t"):
        sd.append(float(h["p"].std(ddof=0)))
        mixed_pred += int((h["p"] >= .5).nunique() > 1)
        if h["y"].nunique() > 1:
            w_auc.append(M._auc(h["y"].to_numpy(int), h["p"].to_numpy(float)))
    nd = g["t"].nunique()
    return {"mean_within_date_sd_p": float(np.mean(sd)), "dates_with_mixed_predicted_labels": mixed_pred,
            "dates": int(nd), "within_date_auc_mean": float(np.mean(w_auc)) if w_auc else None,
            "dates_with_mixed_observed_labels": len(w_auc)}


def arm_metrics(g: pd.DataFrame) -> dict:
    m = M.point_metrics(g["y"], g["p"])
    nd = g["t"].nunique()
    k = int(round(m["accuracy"] * m["n"]))
    m.update({"correct": k, "dates": int(nd), "accuracy_wilson95": wilson(k, m["n"]),
              "p_accuracy_gt_0.75_exact_rows_independent": binom_upper_p(k, m["n"]),
              "flags": M.flags(m, nd), "confusion_matrix": {"rows_observed_cols_predicted": [[m["TN"], m["FP"]],
                                                                                              [m["FN"], m["TP"]]],
                                                            "order": ["LOW", "HIGH"]}})
    m.update(M.bootstrap(g))
    m["discrimination"] = discrimination(g)
    return m


def main():
    proto = verify_protocol()
    d = L.Data()
    Pr, info = L.walk_forward(d)
    st = stored_candidates()
    lab = Pr[Pr["arm"] == "ALWAYS_HIGH"][["t", "origin", "target_quarter", "province_code", "y", "period"]]
    st = st.merge(lab, on=["target_quarter", "province_code"], how="inner").assign(lead=1)
    Pr = pd.concat([Pr, st[Pr.columns]], ignore_index=True)

    res = {"protocol_sha256": proto, "inputs": C.inputs_manifest(), "rice_sha256": C.sha(L.L32.RICE),
           "dates": info["dates"], "selections": info["selections"], "metrics": {}, "paired": {}, "per_date": {},
           "per_province": {}, "per_quarter": {}, "common_rows": {}}
    full_arms = sorted(a for a in Pr["arm"].unique() if a not in ("P45", "F12"))
    for period in ("all", "P-early", "P-late"):
        s = Pr if period == "all" else Pr[Pr["period"] == period]
        for arm, g in s.groupby("arm"):
            res["metrics"].setdefault(period, {})[arm] = arm_metrics(g)
    # stored candidates on their common rows, with the proposed model and baselines on the same rows
    for cand in ("P45", "F12"):
        keys = set(map(tuple, Pr[Pr["arm"] == cand][["target_quarter", "province_code"]].to_numpy()))
        sub = Pr[[(q, p) in keys for q, p in zip(Pr["target_quarter"], Pr["province_code"])]]
        res["common_rows"][cand] = {"rows": len(keys), "metrics": {
            a: arm_metrics(g) for a, g in sub.groupby("arm") if a in [cand, PROPOSED, "ALWAYS_HIGH"] + BASELINES}}
    # per-date losses and paired tests (all dates)
    pdl = {a: M.per_date_losses(g) for a, g in Pr.groupby("arm")}
    res["per_date"] = {a: {"brier": v["bri"].round(6).to_dict(), "error_rate": v["err"].round(6).to_dict()}
                       for a, v in pdl.items()}
    for arm in [PROPOSED, "B5_LGBM_GOV", "B6_LGBM_NLP", "B2_LR_COMB"]:
        out, praw = {}, {}
        a_rows = Pr[Pr["arm"] == arm].sort_values(["t", "province_code"])
        for ref in BASELINES + ["ALWAYS_HIGH", "PCF21", "B1p_CAL_PERSISTENCE", "CLIMATOLOGY"]:
            if ref == arm:
                continue
            common = pdl[arm].index.intersection(pdl[ref].index)
            diff = (pdl[ref]["bri"][common] - pdl[arm]["bri"][common]).to_numpy()
            r_rows = Pr[Pr["arm"] == ref]
            j = a_rows.merge(r_rows, on=["t", "province_code"], suffixes=("_a", "_r"))
            a_ok = ((j["p_a"].to_numpy() >= .5).astype(int) == j["y_a"].to_numpy())
            r_ok = ((j["p_r"].to_numpy() >= .5).astype(int) == j["y_r"].to_numpy())
            out[ref] = {"dates": int(len(common)), "rows": int(len(j)), "mean_brier_gain_vs_ref": float(diff.mean()),
                        "p_one_sided_arm_better": M.signflip_p(diff), "p_two_sided": signflip_two(diff),
                        "mcnemar": mcnemar_exact(a_ok, r_ok),
                        "accuracy_diff": float(a_ok.mean() - r_ok.mean())}
            if ref in BASELINES:
                praw[ref] = out[ref]["p_two_sided"]
        hb = M.holm(praw)
        for ref, v in hb.items():
            out[ref]["holm_two_sided_over_six_baselines"] = v
        res["paired"][arm] = out
    for arm, g in Pr.groupby("arm"):
        res["per_province"][arm] = {C.NAMES[p]: {"n": int(len(h)), "correct": int(((h.p >= .5).astype(int) == h.y).sum()),
                                                 "HIGH": int(h.y.sum()), "brier": float(((h.p - h.y) ** 2).mean())}
                                    for p, h in g.groupby("province_code")}
        res["per_quarter"][arm] = {q: {"HIGH": int(h.y.sum()), "correct": int(((h.p >= .5).astype(int) == h.y).sum()),
                                       "n": int(len(h)), "brier": float(((h.p - h.y) ** 2).mean()),
                                       "mean_p": float(h.p.mean())} for q, h in g.groupby("target_quarter")}
    # the operational choice (origin 2026-10-01)
    (fs, g), sel = L.operational_choice(d, Pr[Pr["arm"].isin(full_arms)])
    res["operational_choice"] = {"origin": "2026-10-01", "chosen": L.cfg_name(fs, g), "feature_set": fs,
                                 "features": L.FEATURE_SETS[fs], "params": {**L._BASE, **L.GRID[g]}, **sel}
    # the 75% reading (PROTOCOL.md section 7)
    m = res["metrics"]["all"][PROPOSED]
    res["target_75"] = {
        "correct": m["correct"], "n": m["n"], "accuracy": m["accuracy"],
        "statement1_point_ge_0.75": m["accuracy"] >= 0.75,
        "date_bootstrap_ci95": m["accuracy_ci95"],
        "statement2_demonstrated_lower_bound_ge_0.75": (m["accuracy_ci95"] or [0])[0] >= 0.75,
        "wilson95_rows": m["accuracy_wilson95"],
        "always_high_accuracy": res["metrics"]["all"]["ALWAYS_HIGH"]["accuracy"],
        "persistence_accuracy": res["metrics"]["all"]["B1_PERSISTENCE"]["accuracy"],
        "balanced_accuracy": m["balanced_accuracy"]}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = L.E36 / "runs" / stamp
    run.mkdir(parents=True)
    Pr = Pr.sort_values(["arm", "target_quarter", "province_code"])
    (run / "predictions.csv").write_bytes(Pr.to_csv(index=False, float_format="%.10g", lineterminator="\n").encode())
    C.write_json(run / "results.json", C.clean(res))
    print(run.name, "predictions sha", hashlib.sha256((run / "predictions.csv").read_bytes()).hexdigest()[:16])
    print("operational choice:", res["operational_choice"]["chosen"])
    for period in ("all", "P-early", "P-late"):
        mm = res["metrics"][period]
        print(f"--- {period}")
        for a in sorted(mm, key=lambda a: mm[a]["brier"]):
            x = mm[a]
            print(f"{a:24s} {x['correct']:3d}/{x['n']:<3d} acc {x['accuracy']:.3f} bal {x['balanced_accuracy'] or 0:.3f} "
                  f"brier {x['brier']:.4f} auc {x['roc_auc'] if x['roc_auc'] is None else round(x['roc_auc'], 3)}")
    print("75%:", res["target_75"])


if __name__ == "__main__":
    main()
