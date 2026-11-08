"""
E175: can a statistical transformation of the official FNRI food-insecurity percentages give better targets for the 50 %
HIGH/LOW rule? Investigation only. The FNRI values are read, never modified; nothing here reaches the dashboard.

Key fact. E168 forecasts the provincial LEVEL (logit of the HFIAS moderate+severe share) and classifies afterwards. Any
order-preserving transformation T followed by "T(x) >= 0.5" is the same as "x >= T^-1(0.5)" on the original scale, so each
candidate is a different cut on the FNRI scale. Each is evaluated on E168's frozen as-of forecasts (no refit) against:
  persistence  the latest published survey value of the province, classified with the same cut
  majority     always predicting the more frequent class under that definition
and checked for leakage: the cut must be computable from data published before the forecast origin.

Candidates
  A  original FNRI share, cut 50 %                       (panel rule; E168 as approved)
  B  min-max per round, cut 0.5                          x' = (x - min) / (max - min)
  C  relative to the reference (national) level          x' = x / (x + ref): 0.5 <=> x = ref  (relative risk = 1)
  D  percentile rank within the round, cut 0.5           above the round median
  E  calibration to the FIES (SDG 2.1.2) scale, cut 50 % E169 bridge logit F = (logit H - a) / b
  F  logit (variance-stabilising, already used by E168)  monotone with cut at logit(0.5) = 0: identical to A
For B-D the parameters are taken either from the TARGET round (as in a naive implementation: leaks the outcome) or AS-OF
from the latest round published at the origin (the only leakage-free version).

    python -m app.e175.target_scaling -> data/e175/out/{values.csv, results.json}
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data"
OUT = D / "e175" / "out"
pct = lambda z: 100 / (1 + np.exp(-np.asarray(z, float)))
lg = lambda p: np.log(np.asarray(p, float) / (100 - np.asarray(p, float)))
CAL = ["batangas", "cavite", "laguna", "quezon", "rizal"]


def rounds() -> pd.DataFrame:
    from app.e150 import model as M
    from app.e151 import prov as Pv
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    T = Pv.target_rows(with_2021=True)[["key", "province", "region", "island", "survey", "year", "p", "y"]].copy()
    T["pct"] = pct(T["y"])
    return T


def released_before(survey: str, lead: int) -> list[str]:
    from app.e148 import model as M8
    from app.e150 import model as M
    from app.e151 import prov as Pv
    return M.released(M8.RQ[survey] - lead, Pv.ROUNDS)


def cuts(T: pd.DataFrame, survey: str, lead: int, bridge: dict) -> dict[str, tuple[float, bool]]:
    """Each candidate's cut on the original % scale for one target round: (cut, leakage_free)."""
    tgt = T[T["survey"] == survey]["pct"]
    rel = released_before(survey, lead)
    last = T[T["survey"] == rel[-1]]["pct"] if rel else tgt
    a, b = bridge["intercept"], bridge["slope"]
    return {
        "A_original_50": (50.0, True),
        "B_minmax_target_round": ((tgt.min() + tgt.max()) / 2, False),
        "B_minmax_asof": ((last.min() + last.max()) / 2, True),
        "C_relative_target_round": (float(tgt.mean()), False),
        "C_relative_asof": (float(last.mean()), True),
        "D_percentile_target_round": (float(tgt.median()), False),
        "D_percentile_asof": (float(last.median()), True),
        "E_fies_calibrated_50": (float(pct(a + b * 0.0)), True),          # FIES 50 % <=> logit H = a
        "F_logit_0": (50.0, True),
    }


def metrics(y, pred, score) -> dict:
    y, pred = np.asarray(y, int), np.asarray(pred, int)
    acc = float((y == pred).mean())
    maj = float(max(y.mean(), 1 - y.mean()))
    po, pe = acc, y.mean() * pred.mean() + (1 - y.mean()) * (1 - pred.mean())
    return {"accuracy": round(acc, 3), "majority_accuracy": round(maj, 3), "skill_over_majority": round(acc - maj, 3),
            "kappa": round(float((po - pe) / (1 - pe)) if pe < 1 else 0.0, 3),
            "precision_high": round(float(precision_score(y, pred, zero_division=0)), 3),
            "recall_high": round(float(recall_score(y, pred, zero_division=0)), 3),
            "f1_high": round(float(f1_score(y, pred, zero_division=0)), 3),
            "balanced_accuracy": round(float((recall_score(y, pred, zero_division=0) + recall_score(1 - y, 1 - pred, zero_division=0)) / 2), 3),
            "auc": round(float(roc_auc_score(y, score)), 3) if 0 < y.mean() < 1 else None, "high_share": round(float(y.mean()), 3)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    T = rounds()
    bridge = json.loads((D / "e169" / "out" / "fies_bridge_feasibility.json").read_text())["bridge_logit"]
    A = pd.concat([pd.read_csv(D / "e168" / "out" / "all_rows.csv"), pd.read_csv(D / "e168" / "out" / "all_rows_l3_8.csv")])
    A = A[A["mode"] == "main"][["key", "survey", "lead", "mu"]]
    G = pd.read_csv(D / "e158" / "out" / "oof.csv")[["key", "survey", "lead", "region", "island", "y_true", "y_anchor"]]
    res = {"bridge": bridge, "leads": {}}
    vals = []
    for L in (1, 2, 3):
        x = G[G["lead"] == L].merge(A[A["lead"] == L], on=["key", "survey", "lead"])
        x["obs"], x["fc"], x["pers"] = pct(x["y_true"]), pct(x["mu"]), pct(x["y_anchor"])
        out = {}
        for name in cuts(T, "ENNS2018", L, bridge):
            ys, pm, pp, sc, leakfree = [], [], [], [], True
            for s, g in x.groupby("survey"):
                c, lf = cuts(T, s, L, bridge)[name]
                leakfree &= lf
                ys += list((g["obs"] >= c).astype(int)); pm += list((g["fc"] >= c).astype(int))
                pp += list((g["pers"] >= c).astype(int)); sc += list(g["fc"] - c)
                if L == 1:
                    for _, r in g.iterrows():
                        vals.append({"survey": s, "key": r["key"], "region": r["region"], "fnri_pct": round(r["obs"], 1),
                                     "method": name, "cut_on_fnri_scale": round(c, 2), "class": "HIGH" if r["obs"] >= c else "LOW"})
            m, mp = metrics(ys, pm, sc), metrics(ys, pp, sc)
            # regional bias: share of HIGH labels and forecast error by island
            xx = x.assign(yy=ys, pr=pm)
            bias = {i: {"n": int(len(g)), "high_share": round(float(g["yy"].mean()), 2), "accuracy": round(float((g["yy"] == g["pr"]).mean()), 2)}
                    for i, g in xx.groupby("island")}
            out[name] = {"leakage_free": bool(leakfree), "E168": m, "persistence": mp,
                         "E168_minus_persistence_accuracy": round(m["accuracy"] - mp["accuracy"], 3), "by_island": bias}
        res["leads"][L] = out
    V = pd.DataFrame(vals)
    V.to_csv(OUT / "values.csv", index=False, lineterminator="\n")
    # transformed values for the CALABARZON rows of every FNRI round (original kept beside them)
    cal = T[T["key"].isin(CAL)].copy()
    rows = []
    for s, g in T.groupby("survey"):
        mn, mx, md, mean = g["pct"].min(), g["pct"].max(), g["pct"].median(), g["pct"].mean()
        for _, r in g[g["key"].isin(CAL)].iterrows():
            v = r["pct"]
            rows.append({"survey": s, "province": r["province"], "fnri_original_pct": round(v, 1),
                         "B_minmax": round((v - mn) / (mx - mn), 3), "C_relative_x_over_x_plus_ref": round(v / (v + mean), 3),
                         "C_relative_risk": round(v / mean, 3), "D_percentile": round(float((g["pct"] < v).mean()), 3),
                         "E_fies_scale_pct": round(float(pct((lg(v) - bridge["intercept"]) / bridge["slope"])), 1),
                         "round_min": round(mn, 1), "round_max": round(mx, 1), "round_mean": round(mean, 1), "round_median": round(md, 1)})
    pd.DataFrame(rows).to_csv(OUT / "calabarzon_transformed.csv", index=False, lineterminator="\n")
    (OUT / "results.json").write_text(json.dumps(res, indent=1), newline="\n")
    for L, out in res["leads"].items():
        print(f"\nLead {L}")
        for n, r in out.items():
            e, p = r["E168"], r["persistence"]
            print(f"  {n:28s} leakfree={r['leakage_free']!s:5} HIGHshare={e['high_share']:.2f} acc={e['accuracy']:.3f} maj={e['majority_accuracy']:.3f} "
                  f"skill={e['skill_over_majority']:+.3f} kappa={e['kappa']:.2f} prec={e['precision_high']:.2f} recH={e['recall_high']:.2f} F1={e['f1_high']:.2f} "
                  f"AUC={e['auc']} | pers acc={p['accuracy']:.3f} kappa={p['kappa']:.2f}")


if __name__ == "__main__":
    main()
