"""Y1 (diagnostic): how stable are the Lead-2 rule verdicts under SWS sampling error in the outcome?

(a) Borderline flips: every test quarter whose observed BL hunger is within 1.0 point of 11.3 has its hunger label flipped,
    one quarter at a time and all at once.
(b) Monte Carlo: the true BL level of each test quarter is drawn from N(observed, SE^2), SE = MoE / 1.96 / sqrt(rounds);
    labels are recomputed (y = hunger* AND price) and R2, R3, R4, R6, R7 and the R5 point conditions are re-evaluated
    (baselines held at their published values; R5 p-values not recomputed per draw). 2000 draws, seed 2036.

Applied to P0H4 Lead 2 (served), H3BxP4 Lead 2 (the near-pass from Y5) and FIRI v2 Lead 2.
Writes out/sensitivity.json.

    python -B sensitivity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import p2lib as P  # noqa: E402

R = P.R
OUT = Path(__file__).resolve().parent / "out"
N_DRAWS = 2000


def fast(y, p, q, base):
    yh = (p >= .5).astype(int)
    tp, fp = ((yh == 1) & (y == 1)).sum(), ((yh == 1) & (y == 0)).sum()
    fn, tn = ((yh == 0) & (y == 1)).sum(), ((yh == 0) & (y == 0)).sum()
    acc = (tp + tn) / len(y)
    rec = tp / (tp + fn) if tp + fn else 0.0
    spec = tn / (tn + fp) if tn + fp else 0.0
    prec = tp / (tp + fp) if tp + fp else 0.0
    out = {"R2": acc >= .75, "R3": (rec + spec) / 2 >= .70, "R6": prec >= .6 and rec >= .6}
    if base is not None:
        out["R4"] = acc > float((y == 0).mean()) and acc > float(((base["PERSIST-SI_p"] >= .5).astype(int) == y).mean())
        out["R5pt"] = np.mean((p - y) ** 2) < np.mean((base["PERSIST-SI_p"] - y) ** 2) and \
            np.mean((p - y) ** 2) < np.mean((base["CLIM_p"] - y) ** 2)
    qs = np.unique(q)
    th = np.array_split(qs, 3)
    a = lambda m: float((yh[m] == y[m]).mean())  # noqa: E731
    out["R7"] = min(a(np.isin(q, t)) for t in th) >= .6 and min(a(q != u) for u in qs) >= .7
    return out


def level_se() -> dict:
    r = R.rounds()
    bl = r[r["area"] == "BL"]
    return {int(q): (float(g["H"].mean()), float((g["moe"].fillna(6.0).mean() / 1.96) / np.sqrt(len(g)))) for q, g in bl.groupby("q")}


def analyse(name: str, g: pd.DataFrame, col: str, has_price: bool, base: bool) -> dict:
    lv = level_se()
    y0 = g["y"].to_numpy(int)
    p = g[col].to_numpy(float)
    q = g["q"].to_numpy(int)
    price = g["price"].to_numpy(int) if has_price else np.ones(len(g), int)
    b = g[["PERSIST-SI_p", "CLIM_p"]].reset_index(drop=True) if base else None
    out = {"observed": {k: bool(v) for k, v in fast(y0, p, q, b).items()}}
    border = sorted({int(x) for x in q if abs(lv[int(x)][0] - R.H_LINE) <= 1.0})
    out["borderlineQuarters"] = [(R.qs(x), lv[x][0]) for x in border]
    flips = {}
    for x in border + ["all"]:
        sel = np.isin(q, border) if x == "all" else (q == x)
        hung = (np.array([lv[int(u)][0] for u in q]) > R.H_LINE).astype(int)
        hung = np.where(sel, 1 - hung, hung)
        flips[R.qs(x) if x != "all" else "all"] = {k: bool(v) for k, v in fast(hung * price, p, q, b).items()}
    out["flips"] = flips
    rng = np.random.default_rng(P.SEED)
    uq = np.unique(q)
    pas = {k: 0 for k in out["observed"]}
    allpass = 0
    for _ in range(N_DRAWS):
        draw = {u: rng.normal(lv[int(u)][0], lv[int(u)][1]) for u in uq}
        y = (np.array([draw[u] for u in q]) > R.H_LINE).astype(int) * price
        if y.sum() == 0 or y.sum() == len(y):
            continue
        f = fast(y, p, q, b)
        for k, v in f.items():
            pas[k] += int(v)
        allpass += int(all(f.values()))
    out["monteCarloPassRate"] = {k: round(v / N_DRAWS, 3) for k, v in pas.items()}
    out["monteCarloAllListedPass"] = round(allpass / N_DRAWS, 3)
    print(name, json.dumps(out, default=str))
    return out


def main():
    d = P.load_p0h4()
    g = d[d["lead"] == 2].copy()
    res = {"P0H4_L2": analyse("P0H4_L2", g, P.RV.P, True, True)}
    c = pd.read_csv(P.RES / "y5_confirm" / "out" / "confirm_rows.csv", dtype={"province_code": str})
    c = c[c["lead"] == 2].merge(g[["province_code", "q", "PERSIST-SI_p", "CLIM_p"]], on=["province_code", "q"])
    res["H3BxP4_L2"] = analyse("H3BxP4_L2", c, "H3BxP4", True, True)
    fr = pd.read_csv(P.EXP / "FIRI_LEAD2_FEASIBILITY" / "out" / "firi_l2_rows.csv")
    fr["q"] = fr["target"].map(R.qi)
    res["FIRI_L2"] = analyse("FIRI_L2", fr, "F2", False, False)
    res["note"] = ("R5 p-values and R1 are not recomputed per draw; R5pt = the Brier point conditions only. Baselines are held at "
                   "their published values. FIRI has no PERSIST-SI/CLIM columns here (R4/R5 omitted).")
    OUT.mkdir(exist_ok=True)
    (OUT / "sensitivity.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
