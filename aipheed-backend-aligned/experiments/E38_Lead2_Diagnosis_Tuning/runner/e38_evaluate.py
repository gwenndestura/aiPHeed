"""E38 outer evaluation (lead 2) under the frozen protocol; applies the adoption rule of PROTOCOL.md section 6.

    python -B runner/e38_evaluate.py   -> runs/<UTC stamp>/{predictions.csv, results.json}
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e38_lib as L  # noqa: E402
import e36_evaluate as E6  # noqa: E402

C, np, pd, M = L.C, L.np, L.pd, E6.M
BASELINES = E6.BASELINES
DIAG = ["ALWAYS_HIGH", "CLIMATOLOGY"]


def verify_protocol():
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((L.E38 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("protocol changed after freezing")
    return want


def metrics(g: pd.DataFrame) -> dict:
    """Probability metrics from p; classification metrics from the row's own threshold."""
    m = E6.arm_metrics(g)
    yh = (g["p"] >= g["threshold"]).astype(int).to_numpy()
    y = g["y"].to_numpy(int)
    tp, tn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    fp, fn = int(((yh == 1) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    m.update({"TP": tp, "TN": tn, "FP": fp, "FN": fn, "correct": tp + tn, "accuracy": (tp + tn) / len(y),
              "precision": prec, "recall": rec, "specificity": spec,
              "f1": (2 * prec * rec / (prec + rec)) if prec and rec else 0.0,
              "balanced_accuracy": (rec + spec) / 2 if rec is not None and spec is not None else None,
              "accuracy_wilson95": E6.wilson(tp + tn, len(y))})
    rng = np.random.default_rng(M.SEED)
    ds = sorted(g["t"].unique())
    acc = []
    for _ in range(M.B):
        s = pd.concat([g[g["t"] == ds[i]] for i in rng.choice(len(ds), len(ds))])
        acc.append(((s["p"] >= s["threshold"]).astype(int) == s["y"]).mean())
    m["accuracy_ci95"] = [float(np.percentile(acc, 2.5)), float(np.percentile(acc, 97.5))]
    return m


def main():
    proto = verify_protocol()
    d = L.Data()
    P38, info = L.walk_forward(d)
    P37, _ = L.L7.walk_forward(d, L.K)                         # E37 arms incl. the six baselines, recomputed
    P37 = P37.assign(threshold=0.5)
    Pr = pd.concat([P38, P37], ignore_index=True)
    res = {"protocol_sha256": proto, "lead": L.K, "dates": info["dates"], "path": info["path"], "metrics": {},
           "paired": {}}
    for arm in ["E38-LGBM", "E36-LGBM"] + BASELINES + DIAG + sorted(a for a in Pr["arm"].unique() if a.startswith("FIXED:")):
        res["metrics"][arm] = metrics(Pr[Pr["arm"] == arm])
    pdl = {a: M.per_date_losses(Pr[Pr["arm"] == a]) for a in ["E38-LGBM", "E36-LGBM"] + BASELINES + DIAG}
    me = Pr[Pr["arm"] == "E38-LGBM"]
    raw = {}
    for ref in ["E36-LGBM"] + BASELINES + DIAG:
        diff = (pdl[ref]["bri"] - pdl["E38-LGBM"]["bri"]).to_numpy()
        j = me.merge(Pr[Pr["arm"] == ref], on=["t", "province_code"], suffixes=("_a", "_r"))
        ok_a = ((j["p_a"] >= j["threshold_a"]).astype(int) == j["y_a"]).to_numpy()
        ok_r = ((j["p_r"] >= j["threshold_r"]).astype(int) == j["y_r"]).to_numpy()
        res["paired"][ref] = {"mean_brier_gain_vs_ref": float(diff.mean()), "p_two_sided": E6.signflip_two(diff),
                              "mcnemar": E6.mcnemar_exact(ok_a, ok_r), "accuracy_diff": float(ok_a.mean() - ok_r.mean()),
                              "formal_thesis_baseline": ref in BASELINES}
        if ref in BASELINES:
            raw[ref] = res["paired"][ref]["p_two_sided"]
    for ref, v in M.holm(raw).items():
        res["paired"][ref]["holm_two_sided_over_six_baselines"] = v
    a, b = res["metrics"]["E38-LGBM"], res["metrics"]["E36-LGBM"]          # E36-LGBM arm here = the E37 procedure
    mb_a, mb_b = float(pdl["E38-LGBM"]["bri"].mean()), float(pdl["E36-LGBM"]["bri"].mean())
    rule = {"accuracy_ge_E37": a["accuracy"] >= b["accuracy"], "balanced_ge_E37": (a["balanced_accuracy"] or 0) >= (b["balanced_accuracy"] or 0),
            "mean_date_brier_le_E37": mb_a <= mb_b, "E38_mean_date_brier": mb_a, "E37_mean_date_brier": mb_b}
    rule["adopt_E38"] = rule["accuracy_ge_E37"] and rule["balanced_ge_E37"] and rule["mean_date_brier_le_E37"]
    lo = a["accuracy_ci95"][0]
    rule["validation_status"] = ("INCONCLUSIVE / INSUFFICIENT EVIDENCE" if min(a["HIGH"], a["LOW"]) < 5 or a["dates"] < 8
                                 else "NOT DEMONSTRATED" if lo < 0.75 else "INTERVAL >= 0.75 ON DEVELOPMENT DATES (not validation)")
    res["adoption"] = rule
    cfg, th, oinfo = L.operational(d, Pr)
    res["operational"] = {"origin": "2026-10-01", "target": "2027-Q1", "chosen": L.name(cfg), "threshold": th, **oinfo}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = L.E38 / "runs" / stamp
    run.mkdir(parents=True)
    Pr = Pr.sort_values(["arm", "target_quarter", "province_code"])
    (run / "predictions.csv").write_bytes(Pr.to_csv(index=False, float_format="%.10g", lineterminator="\n").encode())
    C.write_json(run / "results.json", C.clean(res))
    print(run.name, hashlib.sha256((run / "predictions.csv").read_bytes()).hexdigest()[:16])
    for arm in ["E38-LGBM", "E36-LGBM"] + BASELINES + DIAG:
        m = res["metrics"][arm]
        print(f"{arm:16s} {m['correct']}/{m['n']} acc {m['accuracy']:.3f} ci {[round(x, 3) for x in m['accuracy_ci95']]} "
              f"bal {m['balanced_accuracy'] if m['balanced_accuracy'] is None else round(m['balanced_accuracy'], 3)} "
              f"LOW {m['TN']}/{m['TN'] + m['FP']} brier {m['brier']:.4f}")
    print("path", {q: (v["chosen"], v["threshold"]) for q, v in info["path"].items()})
    print("adoption", rule)
    print("operational", res["operational"]["chosen"], res["operational"]["threshold"])
    print("paired", {k: (round(v["mean_brier_gain_vs_ref"], 4), v["p_two_sided"], v.get("holm_two_sided_over_six_baselines")) for k, v in res["paired"].items()})


if __name__ == "__main__":
    main()
