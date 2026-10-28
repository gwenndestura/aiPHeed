"""LEAD2_FINAL step 1: limits of the available data at Lead 2 (diagnostic only; nothing is fitted on evaluation outcomes).

For the served research candidate P0H4-U (= C0) on the 65 Lead-2 rows:
- oracle decomposition: perfect hunger term x model price term, and model hunger term x perfect price term;
- price-term discrimination (AUC) at Leads 1-2;
- analog test: for every evaluation row, the 10 nearest training rows (same lead, outcome known at the origin, the 21
  model inputs standardised on those training rows) vote on the price condition. It asks whether rows that looked the
  same at the cut-off went the way this one did, i.e. whether the indicators carried the information at all;
- every Lead-2 error gets one primary category (precedence as listed):
    1. hunger information absent at the cut-off (pi_H <= 0.5 and hunger realised HIGH): data cannot anticipate;
    2. uncertain label: realised price margin within +-0.10 point (CPI rounding);
    3. model behaviour: the flat projection was on the realised side, the model was not;
    4. price surprise, split by the analog vote: 'indicators could plausibly anticipate' if the analogs voted for the
       realised side, else 'sudden change the data cannot anticipate'.
  Margins 0.10-0.50 are flagged borderline as a secondary attribute.

    python limits.py            # ../out/limits.json, ../out/limits_errors.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T

F, M, KEY = T.F, T.M, T.KEY
FEATS = [c for c in T.U2 if c != "lead"]
K_NN = 10


def auc(y, p) -> float:
    y, p = np.asarray(y, int), np.asarray(p, float)
    pos, neg = p[y == 1], p[y == 0]
    if not len(pos) or not len(neg):
        return float("nan")
    return float(np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg]))


def analog_vote(S: pd.DataFrame, t: int, lead: int, rows: pd.DataFrame) -> np.ndarray:
    tr = T.train_rows(S, t)
    tr = tr[tr["lead"] == lead]
    X = tr[FEATS].astype(float)
    med, sd = X.median(), X.std().replace(0, np.nan)
    Z = ((X.fillna(med) - med) / sd).fillna(0).to_numpy()
    Q = ((rows[FEATS].astype(float).fillna(med) - med) / sd).fillna(0).to_numpy()
    y = tr["y"].to_numpy(int)
    out = []
    for z in Q:
        d = np.sqrt(((Z - z) ** 2).sum(axis=1))
        out.append(float(y[np.argsort(d, kind="stable")[:K_NN]].mean()) if len(y) >= K_NN else np.nan)
    return np.array(out)


def main():
    S = T.stack()
    C = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    E = C[KEY + ["q", "y", "price", "hunger", "pi_H_AB", "C0_price", "C0_p"]].copy()
    lab = pd.read_csv(T.EXP / "FORECAST_RESEARCH_II" / "out" / "labels_rebuilt.csv", dtype={"province_code": str})
    E = E.merge(lab[["province_code", "q", "m_food", "m_gap"]], on=["province_code", "q"], how="left")
    E = E.merge(S[KEY + FEATS], on=KEY, how="left")
    E["proj"], E["real"] = E[["A1_food", "A1_gap"]].max(axis=1), E[["m_food", "m_gap"]].max(axis=1)
    E["analog"] = np.nan
    for (t, k), g in E[E["lead"] <= 2].groupby(["t", "lead"]):
        E.loc[g.index, "analog"] = analog_vote(S, int(t), int(k), g)
    res = {"k_nn": K_NN, "leads": {}}
    for k in (1, 2):
        g = E[E["lead"] == k]
        a = g["analog"].notna()
        res["leads"][k] = {
            "rows": int(len(g)), "high": int(g["y"].sum()),
            "model": M.cls(g["y"], g["C0_p"]),
            "oracle_hunger_x_model_price": M.cls(g["y"], g["hunger"] * g["C0_price"]),
            "model_hunger_x_oracle_price": M.cls(g["y"], g["pi_H_AB"] * g["price"]),
            "price_term_auc_model": auc(g["price"], g["C0_price"]),
            "price_term_auc_analog": auc(g.loc[a, "price"], g.loc[a, "analog"]),
            "price_term_auc_flat_projection": auc(g["price"], g["proj"]),
            "price_term_acc_model": float(((g["C0_price"] >= .5) == g["price"]).mean()),
            "price_term_acc_analog": float(((g.loc[a, "analog"] >= .5) == g.loc[a, "price"]).mean()),
            "price_term_acc_flat_projection": float(((g["proj"] >= 0) == g["price"]).mean()),
            "price_base_rate": float(g["price"].mean()),
        }
    g = E[E["lead"] == 2].copy()
    err = g[(g["C0_p"] >= .5).astype(int) != g["y"]].copy()
    cats = []
    for _, r in err.iterrows():
        side = r["real"] >= 0
        if r["pi_H_AB"] <= .5 + 1e-9 and r["hunger"] == 1:
            c = "sudden: hunger information absent at cut-off"
        elif abs(r["real"]) <= .10:
            c = "uncertain label (within CPI rounding)"
        elif (r["proj"] >= 0) == side:
            c = "model behaviour"
        elif pd.notna(r["analog"]) and (r["analog"] >= .5) == side:
            c = "price surprise: indicators could plausibly anticipate"
        else:
            c = "price surprise: sudden, data cannot anticipate"
        cats.append(c)
    err["category"] = cats
    err["type"] = np.where(err["y"] == 1, "FN", "FP")
    err["borderline_0.5"] = err["real"].abs() < .5
    err["target"] = err["q"].map(F.qs)
    cols = ["province_code", "target", "type", "category", "borderline_0.5", "pi_H_AB", "C0_price", "C0_p", "proj", "real", "analog"]
    err[cols].to_csv(T.OUT / "limits_errors.csv", index=False, lineterminator="\n", float_format="%.4g")
    res["lead2_error_categories"] = err.groupby(["category", "type"]).size().rename(lambda x: x).to_dict()
    res["lead2_error_categories"] = {f"{a}|{b}": int(v) for (a, b), v in res["lead2_error_categories"].items()}
    res["lead2_errors_borderline_0.5"] = int(err["borderline_0.5"].sum())
    # the analog vote on the 52 correct rows too: does nearest-neighbour information separate the classes at all?
    ok = g[(g["C0_p"] >= .5).astype(int) == g["y"]]
    res["lead2_analog_on_correct_rows_acc"] = float(((ok["analog"] >= .5) == ok["price"]).mean())
    (T.OUT / "limits.json").write_text(json.dumps(res, indent=1, default=float))
    for k, d in res["leads"].items():
        print(f"L{k}", {x: (round(v["accuracy"], 3), round(v["recall"], 2)) if isinstance(v, dict) and "accuracy" in v else
                        (round(v, 3) if isinstance(v, float) else v) for x, v in d.items()})
    print(err[cols].to_string())
    print(res["lead2_error_categories"], "borderline<0.5:", res["lead2_errors_borderline_0.5"])


if __name__ == "__main__":
    main()
