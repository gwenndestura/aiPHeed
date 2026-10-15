"""E37 walk-forward evaluation, lead 2 (next calendar quarter), under the frozen protocol.

    python -B runner/e37_evaluate.py   -> runs/<UTC stamp>/{predictions.csv, results.json}
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e37_lib as L  # noqa: E402
import e36_evaluate as E6  # noqa: E402

C, np, pd, M = L.C, L.np, L.pd, E6.M
K = 2
BASELINES = E6.BASELINES
DIAGNOSTICS = ["ALWAYS_HIGH", "CLIMATOLOGY"]


def verify_protocol() -> str:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((L.E37 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit(f"protocol changed after freezing ({got} != {want})")
    return want


def status(m: dict) -> str:
    if min(m["HIGH"], m["LOW"]) < 5 or m["dates"] < 8:
        return "INCONCLUSIVE / INSUFFICIENT EVIDENCE"
    return "NOT DEMONSTRATED" if (m["accuracy_ci95"] or [0])[0] < 0.75 else "POINT AND INTERVAL >= 0.75 (development only)"


def main():
    proto = verify_protocol()
    d = L.Data()
    Pr, info = L.walk_forward(d, K)
    res = {"protocol_sha256": proto, "lead": K, "inputs": C.inputs_manifest(), "dates": info["dates"],
           "independent_dates": len(info["dates"]), "rows": int(len(Pr[Pr["arm"] == "ALWAYS_HIGH"])),
           "selections": info["selections"], "metrics": {}, "paired": {}, "per_quarter": {}}
    for arm, g in Pr.groupby("arm"):
        res["metrics"][arm] = E6.arm_metrics(g)
    pdl = {a: M.per_date_losses(g) for a, g in Pr.groupby("arm")}
    a_rows = Pr[Pr["arm"] == "E36-LGBM"]
    raw = {}
    for ref in BASELINES + DIAGNOSTICS:
        diff = (pdl[ref]["bri"] - pdl["E36-LGBM"]["bri"]).to_numpy()
        j = a_rows.merge(Pr[Pr["arm"] == ref], on=["t", "province_code"], suffixes=("_a", "_r"))
        ok_a = ((j["p_a"] >= .5).astype(int) == j["y_a"]).to_numpy()
        ok_r = ((j["p_r"] >= .5).astype(int) == j["y_r"]).to_numpy()
        res["paired"][ref] = {"dates": int(len(diff)), "rows": int(len(j)), "mean_brier_gain_vs_ref": float(diff.mean()),
                              "p_two_sided": E6.signflip_two(diff), "mcnemar": E6.mcnemar_exact(ok_a, ok_r),
                              "accuracy_diff": float(ok_a.mean() - ok_r.mean()),
                              "formal_thesis_baseline": ref in BASELINES}
        if ref in BASELINES:
            raw[ref] = res["paired"][ref]["p_two_sided"]
    for ref, v in M.holm(raw).items():
        res["paired"][ref]["holm_two_sided_over_six_baselines"] = v
    for arm, g in Pr.groupby("arm"):
        res["per_quarter"][arm] = {q: {"HIGH": int(h.y.sum()), "correct": int(((h.p >= .5).astype(int) == h.y).sum()),
                                       "brier": float(((h.p - h.y) ** 2).mean())} for q, h in g.groupby("target_quarter")}
    m = res["metrics"]["E36-LGBM"]
    res["target_75"] = {"correct": m["correct"], "n": m["n"], "accuracy": m["accuracy"],
                        "point_ge_0.75": m["accuracy"] >= .75, "date_bootstrap_ci95": m["accuracy_ci95"],
                        "demonstrated_lower_bound_ge_0.75": (m["accuracy_ci95"] or [0])[0] >= .75,
                        "balanced_accuracy": m["balanced_accuracy"], "low_recall": m["specificity"],
                        "validation_status": status(m)}
    (fs, g), sel = L.operational_choice(d, Pr, K)
    res["operational_choice"] = {"origin": "2026-10-01", "target": "2027-Q1", "chosen": L.cfg_name(fs, g), **sel}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = L.E37 / "runs" / stamp
    run.mkdir(parents=True)
    Pr = Pr.sort_values(["arm", "target_quarter", "province_code"])
    (run / "predictions.csv").write_bytes(Pr.to_csv(index=False, float_format="%.10g", lineterminator="\n").encode())
    C.write_json(run / "results.json", C.clean(res))
    print(run.name, hashlib.sha256((run / "predictions.csv").read_bytes()).hexdigest()[:16])
    print("dates", res["dates"], "rows", res["rows"])
    for a in ["E36-LGBM"] + BASELINES + DIAGNOSTICS:
        x = res["metrics"][a]
        print(f"{a:20s} {x['correct']}/{x['n']} acc {x['accuracy']:.3f} ci {x['accuracy_ci95']} bal {x['balanced_accuracy']} "
              f"lowrec {x['specificity']} brier {x['brier']:.4f} auc {x['roc_auc']}")
    print("paired", {k: (round(v["mean_brier_gain_vs_ref"], 4), v["p_two_sided"], v.get("holm_two_sided_over_six_baselines"))
                     for k, v in res["paired"].items()})
    print("75%:", res["target_75"]); print("operational:", res["operational_choice"]["chosen"])


if __name__ == "__main__":
    main()
