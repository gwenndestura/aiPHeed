"""ADDENDUM 2: decision threshold chosen per origin and lead from earlier, already-published outcomes only (balanced
accuracy, grid 0.10..0.50, ties -> closest to 0.50, minimum 4 quarters / 3 HIGH / 3 LOW), applied to C0 (P0H4-U).
R1-R7 unchanged; the Brier score does not depend on the threshold.

    python threshold.py         # ../out/threshold.json, ../out/threshold_rows.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T

F, M = T.F, T.M
GRID = [round(x, 2) for x in np.arange(0.10, 0.501, 0.05)]


def bal(y, c):
    y, c = np.asarray(y, int), np.asarray(c, int)
    r = ((c == 1) & (y == 1)).sum() / max((y == 1).sum(), 1)
    s = ((c == 0) & (y == 0)).sum() / max((y == 0).sum(), 1)
    return (r + s) / 2


def choose(v: pd.DataFrame) -> float:
    if v["q"].nunique() < 4 or v["y"].sum() < 3 or (1 - v["y"]).sum() < 3:
        return 0.5
    sc = {th: bal(v["y"], v["p"] >= th) for th in GRID}
    best = max(sc.values())
    return min((th for th, s in sc.items() if abs(s - best) < 1e-12), key=lambda th: abs(th - 0.5))


def cls_metrics(y, c, p) -> dict:
    y, c, p = np.asarray(y, int), np.asarray(c, int), np.asarray(p, float)
    tp, tn = int(((c == 1) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum())
    fp, fn = int(((c == 1) & (y == 0)).sum()), int(((c == 0) & (y == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    spec = tn / (tn + fp) if tn + fp else float("nan")
    return {"n": len(y), "high": int(y.sum()), "accuracy": float((c == y).mean()), "balanced_accuracy": float(np.nanmean([rec, spec])),
            "precision": prec, "recall": rec, "f1": (2 * prec * rec / (prec + rec)) if tp else 0.0,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn, "brier": float(np.mean((p - y) ** 2))}


def evaluate(g: pd.DataFrame, ccol: str, pcol: str, pers: str) -> dict:
    """F.evaluate (R1-R7) with an explicit class column; Brier on the probability column."""
    y = g["y"].to_numpy(int)
    m = cls_metrics(y, g[ccol], g[pcol])
    base = {"ALWAYS-LOW": float((g["y"] == 0).mean()), "PERSIST": float(((g[pers] >= .5).astype(int) == g["y"]).mean())}
    bs = (g[pcol] - y) ** 2
    tp_ = M.boot_diff(g["q"], bs, (g[pers] - y) ** 2)
    tc = M.boot_diff(g["q"], bs, (g["CLIM_p"] - y) ** 2)
    uq = np.array(sorted(g["q"].unique()))
    acc3 = [float((g[g["q"].isin(th)][ccol] == g[g["q"].isin(th)]["y"]).mean()) for th in np.array_split(uq, 3)]
    loqo = [float((g[g["q"] != q][ccol] == g[g["q"] != q]["y"]).mean()) for q in uq]
    c = {"R1": len(uq) >= 10 and len(g) >= 40, "R2": m["accuracy"] >= .75, "R3": m["balanced_accuracy"] >= .70,
         "R4": m["accuracy"] > base["ALWAYS-LOW"] and m["accuracy"] > base["PERSIST"],
         "R5": tp_["diff"] < 0 and tc["diff"] < 0 and tp_["p_less"] < .10 and tc["p_less"] < .10,
         "R6": m["precision"] >= .60 and m["recall"] >= .60, "R7": min(acc3) >= .60 and min(loqo) >= .70}
    return {"metrics": m, "acc_ci90": M.acc_ci(g["q"], y, g[ccol].astype(float)), "baseline_accuracy": base,
            "brier_vs_persist": tp_, "brier_vs_clim": tc, "acc_thirds": acc3, "loqo_min": min(loqo), "criteria": c,
            "failed": [k for k, v in c.items() if not v], "reliable": all(c.values())}


def main():
    T.check_protocol(addendum=True)
    assert T.sha256(T.LT / "ADDENDUM_2_VALIDATION_THRESHOLD.md") == (T.HERE / "ADDENDUM_2_SHA256.txt").read_text().strip()
    E = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    E = E[T.KEY + ["q", "y", "price", "hunger", "pi_H_AB", "C0_price", "C0_p", "PERS_AB", "CLIM_p"]].rename(columns={"C0_p": "p"})
    kn = pd.read_csv(F.DATA / "known_by_origin.csv", dtype={"province_code": str})
    kn = kn[kn["y"].notna()][["t", "province_code", "q"]]
    known = {t: set(zip(g["province_code"], g["q"])) for t, g in kn.groupby("t")}
    th = {}
    for t in sorted(E["t"].unique()):
        ks = known.get(int(t), set())
        for k in sorted(E["lead"].unique()):
            v = E[(E["lead"] == k) & (E["t"] < t)]
            v = v.loc[np.array([(p, q) in ks for p, q in zip(v["province_code"], v["q"])], dtype=bool)]
            th[(int(t), int(k))] = choose(v)
    E["thr"] = [th[(int(t), int(k))] for t, k in zip(E["t"], E["lead"])]
    E["cls_T"] = (E["p"] >= E["thr"]).astype(int)
    E["cls_05"] = (E["p"] >= .5).astype(int)
    res = {"addendum_sha256": T.sha256(T.LT / "ADDENDUM_2_VALIDATION_THRESHOLD.md"), "grid": GRID, "arms": {}}
    for name, ccol in (("C0 (0.50)", "cls_05"), ("C0-T (validation threshold)", "cls_T")):
        dec = {}
        for k, g in E.groupby("lead"):
            d = evaluate(g, ccol, "p", "PERS_AB")
            dv = g["q"] <= F.DEV_LAST
            d["dev"] = cls_metrics(g.loc[dv, "y"], g.loc[dv, ccol], g.loc[dv, "p"])
            d["conf"] = cls_metrics(g.loc[~dv, "y"], g.loc[~dv, ccol], g.loc[~dv, "p"])
            d["thresholds_by_origin"] = {F.qs(int(t)): float(h["thr"].iloc[0]) for t, h in g.groupby("t")} if ccol == "cls_T" else None
            dec[int(k)] = d
        res["arms"][name] = {"leads": dec, "max_reliable_lead": F.max_reliable(dec)}
    a0, aT = res["arms"]["C0 (0.50)"], res["arms"]["C0-T (validation threshold)"]
    res["adopt_C0T"] = bool(aT["max_reliable_lead"] >= a0["max_reliable_lead"] and aT["leads"][1]["reliable"]
                            and aT["leads"][2]["dev"]["balanced_accuracy"] >= a0["leads"][2]["dev"]["balanced_accuracy"] - 1e-12)
    E.to_csv(T.OUT / "threshold_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    T.OUT.joinpath("threshold.json").write_text(json.dumps(res, indent=1, default=float))
    for name, a in res["arms"].items():
        print(name, "maxrel", a["max_reliable_lead"])
        for k, d in a["leads"].items():
            m = d["metrics"]
            print(f"  L{k} acc {m['accuracy']:.3f} [{d['acc_ci90'][0]:.2f},{d['acc_ci90'][1]:.2f}] bal {m['balanced_accuracy']:.3f} "
                  f"P {m['precision']:.2f} R {m['recall']:.2f} F1 {m['f1']:.2f} TP{m['tp']} FP{m['fp']} FN{m['fn']} TN{m['tn']} "
                  f"Br {m['brier']:.3f} dev bal {d['dev']['balanced_accuracy']:.3f} conf acc {d['conf']['accuracy']:.3f} fail {d['failed']}")
            if d["thresholds_by_origin"] and k <= 2:
                print("     thresholds", d["thresholds_by_origin"])
    print("adopt C0-T:", res["adopt_C0T"])


if __name__ == "__main__":
    main()
