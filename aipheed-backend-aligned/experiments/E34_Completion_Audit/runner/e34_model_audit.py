"""E34: re-assessment of the E32 walk-forward predictions (no refit, no new scoring of outcomes).

Input: E32 runs/20261014T165201Z/predictions.csv (byte-identical repeat …165320Z). Every row is an out-of-sample
walk-forward prediction made with data published before its origin (E32 PROTOCOL, frozen 8bea43d2).

Outputs (runs/e34_model_audit.json):
  1. per arm and lead: n, confusion, accuracy (+ Wilson 95% CI, exact one-sided binomial p for accuracy > 0.75),
     balanced accuracy, Brier; the always-HIGH share as the no-skill accuracy
  2. exact McNemar tests of each model arm against always-HIGH and against persistence (B1) on correctness
  3. NESTED (online) selection: at each target date the E32 candidate with the lowest mean per-date Brier on strictly
     earlier dates is used (first date: E32-PCFN, the protocol's primary). This scores the whole "fit four, pick the
     best" procedure honestly, instead of the candidate picked after seeing all selection dates.
  4. power: per-date Brier-difference SD vs persistence and the number of future dates needed to detect a given gain
"""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
PRED = HERE.parent / "E32_New_Model" / "runs" / "20261014T165201Z" / "predictions.csv"
CANDS = ["E32-PCFN", "E32-LR", "E32-LGBM", "E32-ENS"]
MODELS = CANDS + ["PCF21", "P45"]


def wilson(k, n, z=1.959964):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 4), round(c + h, 4))


def binom_sf(k, n, p):          # P(X >= k)
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def mcnemar_exact(b, c):        # two-sided exact on discordant pairs
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n)


def metrics(rows):
    n = len(rows)
    tp = sum(1 for r in rows if r["yhat"] == 1 and r["y"] == 1)
    tn = sum(1 for r in rows if r["yhat"] == 0 and r["y"] == 0)
    fp = sum(1 for r in rows if r["yhat"] == 1 and r["y"] == 0)
    fn = sum(1 for r in rows if r["yhat"] == 0 and r["y"] == 1)
    acc = (tp + tn) / n
    sens = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    bal = (sens + spec) / 2 if sens is not None and spec is not None else None
    brier = sum((r["p"] - r["y"]) ** 2 for r in rows) / n
    return {"n": n, "TP": tp, "FP": fp, "TN": tn, "FN": fn, "accuracy": round(acc, 4),
            "accuracy_wilson95": wilson(tp + tn, n), "p_accuracy_gt_0.75": round(binom_sf(tp + tn, n, 0.75), 4),
            "balanced_accuracy": None if bal is None else round(bal, 4),
            "recall_HIGH": None if sens is None else round(sens, 4),
            "specificity_LOW": None if spec is None else round(spec, 4), "brier": round(brier, 4)}


def main():
    rows = []
    with open(PRED, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = float(r["p"])
            rows.append({"lead": int(r["lead"]), "target": r["target_quarter"], "prov": r["province_code"],
                         "arm": r["arm"], "p": p, "y": int(r["y"]), "yhat": 1 if p >= 0.5 else 0})
    by = defaultdict(list)
    for r in rows:
        by[(r["lead"], r["arm"])].append(r)
    out = {"input": str(PRED.relative_to(HERE.parent)), "threshold": 0.5, "leads": {}}
    for lead in (1, 2):
        L = {}
        arms = sorted({a for (l, a) in by if l == lead})
        for a in arms:
            L[a] = metrics(by[(lead, a)])
        # McNemar on common rows
        def keyed(a):
            return {(r["target"], r["prov"]): r for r in by[(lead, a)]}
        mc = {}
        for a in MODELS:
            if (lead, a) not in by:
                continue
            A = keyed(a)
            for ref in ("ALWAYS_HIGH", "B1"):
                R = keyed(ref)
                common = sorted(set(A) & set(R))
                b = sum(1 for k in common if A[k]["yhat"] == A[k]["y"] and R[k]["yhat"] != R[k]["y"])
                c = sum(1 for k in common if A[k]["yhat"] != A[k]["y"] and R[k]["yhat"] == R[k]["y"])
                mc[f"{a}_vs_{ref}"] = {"rows": len(common), "model_right_ref_wrong": b, "model_wrong_ref_right": c,
                                       "p_exact_two_sided": round(mcnemar_exact(b, c), 4)}
        # nested online selection
        dates = sorted({r["target"] for r in rows if r["lead"] == lead and r["arm"] in CANDS})
        per_date = defaultdict(dict)
        for a in CANDS + ["PCF21", "B1", "B1p", "ALWAYS_HIGH"]:
            for d in dates:
                rr = [r for r in by[(lead, a)] if r["target"] == d]
                if rr:
                    per_date[a][d] = sum((r["p"] - r["y"]) ** 2 for r in rr) / len(rr)

        def nested(pool, first):
            used, chosen = [], []
            for i, d in enumerate(dates):
                hist = dates[:i]
                ok = [a for a in pool if all(h in per_date[a] for h in hist) and d in per_date[a]]
                if not hist:
                    pick = first
                else:
                    pick = min(ok, key=lambda a: (sum(per_date[a][h] for h in hist) / len(hist), pool.index(a)))
                chosen.append([d, pick])
                used += [r for r in by[(lead, pick)] if r["target"] == d]
            m = metrics(used)
            m["chosen_per_date"] = chosen
            m["mean_per_date_brier"] = round(sum(per_date[p][d] for d, p in chosen) / len(chosen), 4)
            return m
        nest = {"E32_candidates_only": nested(CANDS, "E32-PCFN"),
                "E32_candidates_plus_PCF21_persistence_alwaysHIGH": nested(CANDS + ["PCF21", "B1p", "ALWAYS_HIGH"],
                                                                            "E32-PCFN")}
        mpd = {a: round(sum(v.values()) / len(v), 4) for a, v in per_date.items() if v}
        # power vs probabilistic persistence (B1p) and B1
        pw = {}
        for ref in ("B1", "B1p", "ALWAYS_HIGH"):
            for a in ("E32-PCFN", "E32-ENS", "PCF21"):
                common = [d for d in dates if d in per_date[a] and d in per_date[ref]]
                diffs = [per_date[ref][d] - per_date[a][d] for d in common]
                if len(diffs) < 3:
                    continue
                mu = sum(diffs) / len(diffs)
                sd = math.sqrt(sum((x - mu) ** 2 for x in diffs) / (len(diffs) - 1))
                need = {}
                for delta in (0.01, 0.02, 0.05):
                    need[str(delta)] = math.ceil(((1.644854 + 0.841621) * sd / delta) ** 2) if sd > 0 else None
                pw[f"{a}_vs_{ref}"] = {"dates": len(diffs), "mean_gain": round(mu, 4), "sd_per_date": round(sd, 4),
                                       "dates_needed_for_80pct_power_one_sided_0.05_at_gain": need}
        out["leads"][str(lead)] = {"dates": dates, "arms": L, "mcnemar": mc, "nested_selection": nest,
                                   "mean_per_date_brier": mpd, "power": pw}
    p = HERE / "runs" / "e34_model_audit.json"
    p.write_bytes(json.dumps(out, indent=1).encode("utf-8"))
    l1 = out["leads"]["1"]
    for a, m in sorted(l1["arms"].items(), key=lambda x: x[1]["brier"]):
        print(f"{a:12s} n={m['n']} acc={m['accuracy']} CI={m['accuracy_wilson95']} p>.75={m['p_accuracy_gt_0.75']} "
              f"bal={m['balanced_accuracy']} brier={m['brier']}")
    for k, v in l1["nested_selection"].items():
        print("NESTED", k, v["accuracy"], v["balanced_accuracy"], v["brier"], v["mean_per_date_brier"], v["chosen_per_date"])
    print(json.dumps(l1["mcnemar"], indent=0)[:1500])
    print(json.dumps(l1["power"], indent=0)[:2000])


if __name__ == "__main__":
    main()
