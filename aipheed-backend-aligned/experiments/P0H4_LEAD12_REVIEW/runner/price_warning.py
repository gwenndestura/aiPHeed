"""Addendum 1: Lead-2 food-price-pressure warning (served pi_price vs the price part of the label). Read-only inputs;
writes out/price_warning.json. Refuses to run if the addendum differs from its frozen hash."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from reproduce import HERE, OUT, SEED, B, load, cm

COL = "P0_price"


def frozen_ok() -> None:
    want = (HERE / "ADDENDUM_1_SHA256.txt").read_text().split()[0]
    have = hashlib.sha256((HERE.parent / "ADDENDUM_1_PRICE_WARNING.md").read_bytes()).hexdigest()
    assert want == have, "ADDENDUM_1_PRICE_WARNING.md changed after freezing"


def with_baselines(d: pd.DataFrame) -> pd.DataFrame:
    # ADDENDUM_1_NOTE.md: price labels for every quarter (CPI only) from the E68 label table (70/70 equal to `price`)
    e = pd.read_csv(HERE.parents[1] / "E68_Resolve_E67_Critical_Failures" / "tables" / "r2_labels_all.csv")
    names = {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000",
             "Batangas": "PH040500000"}
    lab = {(names[r.province], int(r.quarter[:4]) * 4 + int(r.quarter[-1]) - 1): int(r.PS) for r in e.itertuples()}
    d = d.copy()
    d["persist"] = [lab.get((p, t - 1), np.nan) for p, t in zip(d["province_code"], d["t"])]
    clim = {}
    for t in d["t"].unique():
        known = [v for (p, q), v in lab.items() if q <= t - 1]
        clim[t] = float(np.mean(known)) if known else np.nan
    d["clim"] = d["t"].map(clim)
    d["lo"], d["hi"] = 0.0, 1.0
    return d


def boot(g, stat):
    rng = np.random.default_rng(SEED)
    qv = g["q"].unique()
    by = {q: h for q, h in g.groupby("q")}
    return np.asarray([stat(pd.concat([by[q] for q in rng.choice(qv, len(qv))])) for _ in range(B)])


def evaluate(g: pd.DataFrame) -> dict:
    y, p = g["y"].to_numpy(int), g[COL].to_numpy(float)
    s = cm(y, p)
    from sklearn.metrics import roc_auc_score
    s.update({"quarters": int(g["q"].nunique()), "auc": float(roc_auc_score(y, p)), "brier": float(np.mean((p - y) ** 2)),
              "baseRate": float(y.mean())})
    acc = lambda h, c: float(((h[c] >= .5).astype(int) == h["y"]).mean())  # noqa: E731
    base = {b: acc(g, c) for b, c in (("always-LOW", "lo"), ("always-HIGH", "hi"), ("price persistence", "persist"))}
    r5 = {}
    for b, c in (("price persistence", "persist"), ("price climatology", "clim")):
        diff = float(np.mean((g[COL] - g["y"]) ** 2 - (g[c] - g["y"]) ** 2))
        bs = boot(g, lambda h, c=c: float(np.mean((h[COL] - h["y"]) ** 2 - (h[c] - h["y"]) ** 2)))
        r5[b] = (diff, float(np.mean(bs >= 0)))
    qs = sorted(g["q"].unique())
    thirds = [acc(g[g["q"].isin(t)], COL) for t in np.array_split(np.array(qs), 3)]
    loqo = min(acc(g[g["q"] != q], COL) for q in qs)
    s["baselines"] = base
    s["rules"] = {
        "R1": (s["quarters"] >= 10 and s["n"] >= 40, f"{s['quarters']} q, {s['n']} rows"),
        "R2": (s["accuracy"] >= .75, round(s["accuracy"], 4)),
        "R3": (s["balanced"] >= .70, round(s["balanced"], 4)),
        "R4": (all(s["accuracy"] > v for v in base.values()), {k: round(v, 4) for k, v in base.items()}),
        "R5": (all(dv < 0 and pv < .10 for dv, pv in r5.values()), {k: f"diff {dv:+.4f} p {pv:.3f}" for k, (dv, pv) in r5.items()}),
        "R6": ((s["precision"] or 0) >= .6 and s["recall"] >= .6, f"P {s['precision'] or 0:.3f} R {s['recall']:.3f}"),
        "R7": (min(thirds) >= .6 and loqo >= .7, f"thirds {[round(x, 3) for x in thirds]}, LOQO {loqo:.3f}"),
    }
    return s


def main():
    frozen_ok()
    d = with_baselines(load())
    d["y"] = d["price"].astype(int)
    assert d[["persist", "clim", COL]].notna().all().all(), "a baseline or forecast is missing"
    out = {"addendumSha256": (HERE / "ADDENDUM_1_SHA256.txt").read_text().split()[0]}
    for k in (1, 2):
        s = evaluate(d[d["lead"] == k])
        s["verdict"] = ("reliable price warning (development evidence)" if all(v[0] for v in s["rules"].values())
                        else "not reliable")
        out[f"lead{k}"] = s
        print(f"LEAD {k}: n {s['n']} q {s['quarters']} priceHIGH {s['pos']} base {s['baseRate']:.2f} | acc {s['accuracy']:.4f} "
              f"bal {s['balanced']:.4f} P {s['precision'] or 0:.3f} R {s['recall']:.3f} spec {s['specificity']:.3f} F1 {s['f1']:.3f} "
              f"AUC {s['auc']:.3f} Brier {s['brier']:.4f} TP/FP/FN/TN {s['TP']}/{s['FP']}/{s['FN']}/{s['TN']}")
        for r, (ok, v) in s["rules"].items():
            print(f"   {'PASS' if ok else 'FAIL'} {r}: {v}")
        print("   ->", s["verdict"])
    (OUT / "price_warning.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
