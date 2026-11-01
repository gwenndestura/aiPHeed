"""P0H4 Lead 1 / Lead 2: independent reproduction, the seven frozen reliability rules (FINAL_TARGET_AND_EVALUATION_
PROTOCOL.md section 7) and error analysis. Read-only inputs; writes out/reproduce.json only.

Inputs: FINAL_ARCHITECTURE/out/predictions.csv (walk-forward P0H4 probabilities, T43c labels, baselines),
        backend/data/ch1_engine/rows.csv (served rows; Lead 1 must equal the evaluated probabilities).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
EXP = HERE.parents[1]
ROOT = EXP.parents[1]
SEED, B = 2036, 5000
P = "P0H4_p3"


def qs(i: int) -> str:
    return f"{int(i) // 4}-Q{int(i) % 4 + 1}"


def load() -> pd.DataFrame:
    d = pd.read_csv(EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    d = d[d["lead"].isin([1, 2])].copy()
    d["target"] = d["q"].map(qs)
    d["origin"] = d["t"].map(qs)
    assert not d.duplicated(["lead", "province_code", "q"]).any(), "duplicate forecast rows"
    assert d[[P, "y", "PERSIST-SI_p", "CLIM_p", "ALWAYS-LOW_p"]].notna().all().all(), "missing values"
    assert ((d["q"] - d["t"]) == d["lead"]).all(), "target != origin + lead"
    return d


def cm(y, p, thr=0.5) -> dict:
    y, yh = np.asarray(y, int), (np.asarray(p, float) >= thr).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    fn, tn = int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    r = lambda a, b: a / b if b else None  # noqa: E731
    rec, spec, prec = r(tp, tp + fn), r(tn, tn + fp), r(tp, tp + fp)
    return {"n": len(y), "pos": tp + fn, "neg": tn + fp, "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "accuracy": r(tp + tn, len(y)), "balanced": (rec + spec) / 2, "precision": prec, "recall": rec,
            "specificity": spec, "f1": 2 * prec * rec / (prec + rec) if prec and rec else 0.0}


def scores(g: pd.DataFrame, col: str = P, thr: float = 0.5) -> dict:
    y, p = g["y"].to_numpy(int), g[col].to_numpy(float)
    out = cm(y, p, thr)
    out.update({"quarters": int(g["q"].nunique()), "period": f"{g['target'].min()}..{g['target'].max()}",
                "auc": float(roc_auc_score(y, p)), "prAuc": float(average_precision_score(y, p)),
                "brier": float(np.mean((p - y) ** 2)), "meanP": float(p.mean()), "baseRate": float(y.mean())})
    return out


def boot_quarters(g: pd.DataFrame, stat) -> list[float]:
    rng = np.random.default_rng(SEED)
    qv = g["q"].unique()
    by = {q: h for q, h in g.groupby("q")}
    return [stat(pd.concat([by[q] for q in rng.choice(qv, len(qv))])) for _ in range(B)]


def rules(g: pd.DataFrame) -> dict:
    """The frozen rule (protocol section 7), recomputed here."""
    s = scores(g)
    acc = lambda h: float(((h[P] >= .5).astype(int) == h["y"]).mean())  # noqa: E731
    base = {b: float(((g[c] >= .5).astype(int) == g["y"]).mean()) for b, c in (("ALWAYS-LOW", "ALWAYS-LOW_p"),
                                                                              ("PERSIST-SI", "PERSIST-SI_p"))}
    r5 = {}
    for b, c in (("PERSIST-SI", "PERSIST-SI_p"), ("CLIM", "CLIM_p")):
        diff = float(np.mean((g[P] - g["y"]) ** 2 - (g[c] - g["y"]) ** 2))
        bs = boot_quarters(g, lambda h, c=c: float(np.mean((h[P] - h["y"]) ** 2 - (h[c] - h["y"]) ** 2)))
        r5[b] = {"brierDiff": diff, "p_one_sided": float(np.mean(np.asarray(bs) >= 0))}
    qsorted = sorted(g["q"].unique())
    k = len(qsorted)
    thirds = [list(t) for t in np.array_split(np.array(qsorted), 3)]        # the frozen implementation (ch1_lib.py)
    third_acc = [acc(g[g["q"].isin(t)]) for t in thirds]
    alt = [qsorted[: k // 3], qsorted[k // 3: 2 * k // 3], qsorted[2 * k // 3:]]   # sensitivity: the other split
    alt_acc = [acc(g[g["q"].isin(t)]) for t in alt]
    loqo = min(acc(g[g["q"] != q]) for q in qsorted)
    res = {
        "R1 >=10 quarters and >=40 rows": (s["quarters"] >= 10 and s["n"] >= 40, f"{s['quarters']} q, {s['n']} rows"),
        "R2 accuracy >= 0.75": (s["accuracy"] >= .75, round(s["accuracy"], 4)),
        "R3 balanced accuracy >= 0.70": (s["balanced"] >= .70, round(s["balanced"], 4)),
        "R4 accuracy > always-LOW and > PERSIST-SI": (s["accuracy"] > base["ALWAYS-LOW"] and s["accuracy"] > base["PERSIST-SI"],
                                                       f"{s['accuracy']:.4f} vs {base['ALWAYS-LOW']:.4f} / {base['PERSIST-SI']:.4f}"),
        "R5 Brier < PERSIST-SI and < CLIM, one-sided cluster p < 0.10": (
            all(v["brierDiff"] < 0 and v["p_one_sided"] < .10 for v in r5.values()),
            {b: f"diff {v['brierDiff']:+.4f}, p {v['p_one_sided']:.3f}" for b, v in r5.items()}),
        "R6 precision >= 0.60 and recall >= 0.60": ((s["precision"] or 0) >= .6 and s["recall"] >= .6,
                                                   f"P {s['precision']:.3f}, R {s['recall']:.3f}"),
        "R7 each third >= 0.60 and leave-one-quarter-out min >= 0.70": (
            min(third_acc) >= .6 and loqo >= .7,
            f"thirds {[round(x, 3) for x in third_acc]} (sizes {[len(t) for t in thirds]}), LOQO min {loqo:.3f}; "
            f"other split {[round(x, 3) for x in alt_acc]} (sizes {[len(t) for t in alt]})"),
    }
    return {k: {"pass": bool(v[0]), "value": v[1]} for k, v in res.items()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = load()
    served = pd.read_csv(ROOT / "backend" / "data" / "ch1_engine" / "rows.csv", dtype={"province_code": str})
    s1 = served[(served["lead"] == 1) & served["observed"].isin(["HIGH", "LOW"])]
    j = s1.merge(d[d["lead"] == 1], left_on=["province_code", "quarter"], right_on=["province_code", "target"])
    out = {"servedEqualsEvaluatedLead1": {"rows": len(j), "maxAbsDiff": float((j["probability"] - j[P]).abs().max()),
                                          "labelsAgree": bool(((j["observed"] == "HIGH").astype(int) == j["y"]).all())}}
    ev = json.loads((ROOT / "backend" / "data" / "ch1_engine" / "evaluation.json").read_text(encoding="utf-8"))
    for k in (1, 2):
        g = d[d["lead"] == k]
        s = scores(g)
        acc_b = boot_quarters(g, lambda h: float(((h[P] >= .5).astype(int) == h["y"]).mean()))
        rec_b = [x for x in boot_quarters(g, lambda h: float(((h[P] >= .5) & (h["y"] == 1)).sum() / max(h["y"].sum(), 1))
                                          if h["y"].sum() else np.nan) if not np.isnan(x)]
        s["accuracyCI95_quarters"] = [float(np.quantile(acc_b, .025)), float(np.quantile(acc_b, .975))]
        s["recallCI95_quarters"] = [float(np.quantile(rec_b, .025)), float(np.quantile(rec_b, .975))]
        st = ev["leads"][str(k)]["metrics"]
        s["matchesStoredEvaluation"] = all(abs(s[a] - st[b]) < 1e-6 for a, b in (("accuracy", "accuracy"), ("balanced", "balanced_accuracy"),
                                                                                    ("recall", "recall"), ("brier", "brier")))
        bins = pd.cut(g[P], [0, .1, .2, .35, .5, 1.0])
        s["calibration"] = {str(b): {"n": int(len(h)), "meanP": round(float(h[P].mean()), 3), "observed": round(float(h["y"].mean()), 3)}
                            for b, h in g.groupby(bins, observed=True)}
        prev = {(r.province_code, r.q): r.y for r in d[d["lead"] == 1].itertuples()}
        lab = d.drop_duplicates(["province_code", "q"]).set_index(["province_code", "q"])["y"].to_dict()
        g = g.assign(onset=[int(y == 1 and lab.get((pc, q - 1)) == 0) for pc, q, y in zip(g["province_code"], g["q"], g["y"])])
        errs = g[((g[P] >= .5).astype(int) != g["y"])]
        s["errors"] = [{"target": r.target, "issue_origin": r.origin, "province": r.province_code, "y": int(r.y),
                        "p": round(r.P0H4_p3, 3), "pi_hunger": round(r.pi_H4, 3), "pi_price": round(r.P0_price, 3),
                        "price_true": int(r.price), "hunger_true": int(r.hunger), "onset": int(r.onset),
                        "type": "FN" if r.y == 1 else "FP"} for r in errs.itertuples()]
        s["onsetsCaught"] = f"{int(((g[P] >= .5) & (g['onset'] == 1)).sum())}/{int(g['onset'].sum())}"
        s["baselines"] = {b: scores(g, c) for b, c in (("always-LOW", "ALWAYS-LOW_p"), ("PERSIST-SI", "PERSIST-SI_p"),
                                                        ("climatology", "CLIM_p"))}
        s["rules"] = rules(d[d["lead"] == k])
        s["storedRules"] = ev["leads"][str(k)]["criteria"]
        out[f"lead{k}"] = s
    (OUT / "reproduce.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("served==evaluated L1:", out["servedEqualsEvaluatedLead1"])
    for k in (1, 2):
        s = out[f"lead{k}"]
        print(f"\nLEAD {k}: n {s['n']} q {s['quarters']} pos {s['pos']} | acc {s['accuracy']:.4f} {[round(x, 3) for x in s['accuracyCI95_quarters']]} "
              f"bal {s['balanced']:.4f} P {s['precision']:.3f} R {s['recall']:.3f} {[round(x, 2) for x in s['recallCI95_quarters']]} spec {s['specificity']:.3f} "
              f"F1 {s['f1']:.3f} AUC {s['auc']:.3f} PR {s['prAuc']:.3f} Brier {s['brier']:.4f} meanP {s['meanP']:.3f} base {s['baseRate']:.3f} "
              f"TP/FP/FN/TN {s['TP']}/{s['FP']}/{s['FN']}/{s['TN']} matchesStored {s['matchesStoredEvaluation']} onsets {s['onsetsCaught']}")
        for r, v in s["rules"].items():
            print(f"   {'PASS' if v['pass'] else 'FAIL'}  {r}: {v['value']}")
        print("   stored:", s["storedRules"])
        print("   calibration:", s["calibration"])
        for e in s["errors"]:
            print("   ", e)


if __name__ == "__main__":
    main()
