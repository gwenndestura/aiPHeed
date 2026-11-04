"""Why does C-B6's R1-R7 pass depend on one forecast? (read only: stored fits and labels; nothing fitted)

1. The changed forecast: origin, C-b vs C-B6 probability, the rice-stock inputs and their SHAP at that origin, and
   whether the two affected labels are within SWS sampling noise (out/obj2_error_level.csv).
2. Label-noise robustness: for every verdict quarter whose label is uncertain (P(true HIGH) in 0.10..0.90, n = 600),
   flip that one label and recompute balanced accuracy (R3) and the thirds rule (R7 part 1) for C-b and C-B6.
3. Margin: how far each model's probabilities sit from 0.50 on the quarters that decide R3/R7.

    python obj2_cb6_fragility.py   # -> ../out/obj2_cb6_fragility.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "out"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_model as CE  # noqa: E402

N, V, H, R = CE.N, CE.V, CE.H, CE.R


def rules(p: np.ndarray, y: np.ndarray, q: np.ndarray) -> dict:
    c = (p >= .5).astype(int)
    rc, sp = ((c == 1) & (y == 1)).sum() / max(1, (y == 1).sum()), ((c == 0) & (y == 0)).sum() / max(1, (y == 0).sum())
    th = np.array_split(np.argsort(q), 3)
    thirds = [float((c[i] == y[i]).mean()) for i in th]
    return {"balanced": float((rc + sp) / 2), "R3": bool((rc + sp) / 2 >= .70), "thirds": thirds, "R7_thirds": bool(min(thirds) >= .60)}


def main():
    lab = V.area_labels(H.load())
    lb = lab[lab["area"] == "BL"]
    E = pd.read_csv(OUT / "obj2_error_level.csv")
    cb = pd.read_csv(N.OUT / "forecasts.csv")
    cb = cb[cb["name"] == "C-b"][["name", "t", "lead", "q", "p"]]
    F6 = pd.read_csv(OUT / "cb6_fits.csv")
    st = pd.read_csv(OUT / "ce6_features.csv").set_index("t")
    L = pd.read_csv(N.LEADS_FILE)
    comp = pd.concat([cb, F6[["name", "t", "lead", "q", "p"]], L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]]])
    res = {"leads": {}}
    for k in (1, 2):
        W = R.frame(comp, k, lb).dropna(subset=["C-b", "C-B6"]).sort_values("q").reset_index(drop=True)
        e = E[E["lead"] == k].set_index("target")
        W["target"] = W["q"].map(H.qs)
        W["P_true"] = W["target"].map(e["P_true_high_n600"])
        y, q = W["y"].to_numpy(int), W["q"].to_numpy()
        base = {m: rules(W[m].to_numpy(float), y, q) for m in ("C-b", "C-B6")}
        changed = W[(W["C-b"] >= .5) != (W["C-B6"] >= .5)]
        ch = []
        for r in changed.itertuples():
            f = F6[(F6["t"] == r.t) & (F6["lead"] == k)].iloc[0]
            ch.append({"origin": H.qs(int(r.t)), "target": r.target, "observed_label": int(r.y),
                       "observed_H": float(e.loc[r.target, "observed_H"]), "P_true_high_n600": float(r.P_true),
                       "p_C-b": round(float(W.loc[r.Index, "C-b"]), 4),
                       "p_C-B6": round(float(W.loc[r.Index, "C-B6"]), 4),
                       "ST1_total_stock_yoy_pct": round(float(st.loc[r.t, "ST1"]), 2),
                       "ST2_nfa_share_change_pts": round(float(st.loc[r.t, "ST2"]), 2),
                       "shap_ST1": round(float(f["shap_ST1"]), 4), "shap_ST2": round(float(f["shap_ST2"]), 4)})
        flips = []
        for i in np.where((W["P_true"] > .1) & (W["P_true"] < .9))[0]:
            y2 = y.copy()
            y2[i] = 1 - y2[i]
            a = {m: rules(W[m].to_numpy(float), y2, q) for m in ("C-b", "C-B6")}
            flips.append({"target": W.loc[i, "target"], "P_true_high": round(float(W.loc[i, "P_true"]), 3),
                          "C-b_R3": a["C-b"]["R3"], "C-b_R7": a["C-b"]["R7_thirds"],
                          "C-B6_R3": a["C-B6"]["R3"], "C-B6_R7": a["C-B6"]["R7_thirds"]})
        F_ = pd.DataFrame(flips)
        res["leads"][str(k)] = {
            "base": base, "changed_forecasts": ch, "uncertain_labels": int(len(F_)),
            "single_flips_that_break_C-B6_R3_or_R7": F_[~(F_["C-B6_R3"] & F_["C-B6_R7"])]["target"].tolist(),
            "single_flips_that_make_C-b_pass_R3_and_R7": F_[F_["C-b_R3"] & F_["C-b_R7"]]["target"].tolist(),
            "flips": flips}
    (OUT / "obj2_cb6_fragility.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res["leads"].items():
        print(f"Lead {k}: base {v['base']}")
        print("  changed:", v["changed_forecasts"])
        print(f"  uncertain labels {v['uncertain_labels']}; single flips breaking C-B6: {v['single_flips_that_break_C-B6_R3_or_R7']}; "
              f"single flips making C-b pass: {v['single_flips_that_make_C-b_pass_R3_and_R7']}")


if __name__ == "__main__":
    main()
