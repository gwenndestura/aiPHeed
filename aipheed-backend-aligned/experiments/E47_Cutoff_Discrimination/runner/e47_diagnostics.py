"""E47 diagnostics (no model is fitted or selected here):
  1. label support: T43 HIGH counts per quarter, which condition switched each HIGH on, quarters with H > 11.3;
  2. province vs regional variation: share of each label/feature's variance that lies WITHIN quarters (between
     provinces) - national and regional inputs have none;
  3. trigger coverage: per feature, origins with a non-missing value and with variation across provinces;
  4. I7's missed HIGH rows: which condition was on, the forecast vs the outcome of food YoY and the gap.

    backend/venv/Scripts/python.exe -B runner/e47_diagnostics.py   -> runs/diagnostics.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
E47 = HERE.parent
EXP = E47.parent
sys.path.insert(0, str(EXP / "E46_Rice_Policy" / "runner"))
import e46_lib as M  # noqa: E402

L, K, P2, np, pd = M.L, M.K, M.P2, M.np, M.pd


def within_share(df, col):
    v = df[col].astype(float)
    if v.notna().sum() < 3 or v.var() == 0:
        return None
    w = df.assign(v=v).groupby("q")["v"].transform(lambda s: s - s.mean())
    return float((w ** 2).sum() / ((v - v.mean()) ** 2).sum())


def main():
    d = L.load()
    th = L.e40_spec()
    lab = K.label_frame(d)
    lab["food_on"] = (lab["F"] > lab["province_code"].map(th["food"])).astype(int)
    lab["gap_on"] = ((lab["F"] - lab["HL"]) > lab["province_code"].map(th["gap"])).astype(int)
    lab["sws_on"] = (lab["H"] > th["H"]).astype(int)
    out = {"labels": {
        "quarters_labelled": int(lab["q"].nunique()), "rows": int(len(lab)), "HIGH": int(lab["y"].sum()),
        "by_quarter": {L.qs(int(q)): {"HIGH": int(g["y"].sum()), "H": float(g["H"].iloc[0]), "sws_on": int(g["sws_on"].iloc[0])}
                       for q, g in lab.groupby("q")},
        "HIGH_switched_on_by": {"food_only": int(((lab.y == 1) & (lab.food_on == 1) & (lab.gap_on == 0)).sum()),
                                "gap_only": int(((lab.y == 1) & (lab.food_on == 0) & (lab.gap_on == 1)).sum()),
                                "both": int(((lab.y == 1) & (lab.food_on == 1) & (lab.gap_on == 1)).sum())},
        "by_province": {L.NAMES[p]: int(g["y"].sum()) for p, g in lab.groupby("province_code")},
        "within_quarter_share_of_label_variance": within_share(lab, "y"),
        "quarters_with_H_above_11_3_since_2023Q4": int(lab[lab["q"] >= L.qi("2023-Q4")].groupby("q")["sws_on"].first().sum()),
        "quarters_since_2023Q4": int(lab[lab["q"] >= L.qi("2023-Q4")]["q"].nunique())}}
    X = pd.read_csv(EXP / "E46_Rice_Policy" / "runs" / "20261016T225203Z" / "features_asof.csv", dtype={"province_code": str})
    X = X.rename(columns={"t": "q"})
    feats = {g: c for g, c in P2.PRICE_GROUPS.items()}
    feats["hunger"] = ["H_last", "H_chg"]
    feats["policy"] = M.POLICY
    cov = {}
    for g, cols in feats.items():
        for c in cols:
            if c not in X:
                continue
            nn = X.groupby("q")[c].apply(lambda s: s.notna().all())
            var = X.groupby("q")[c].apply(lambda s: s.nunique(dropna=True) > 1)
            cov[c] = {"group": g, "origins_complete": int(nn.sum()), "origins_total": int(len(nn)),
                      "origins_varying_across_provinces": int(var.sum()),
                      "within_quarter_variance_share": within_share(X, c),
                      "geography": "provincial" if var.sum() > 0 else "national/regional (identical for all provinces)"}
    out["trigger_coverage"] = cov
    runs = EXP / "E46_Rice_Policy" / "runs"
    P7 = pd.read_csv(runs / "i7_20261017T000111Z" / "predictions_i7.csv", dtype={"province_code": str})
    P7["q"] = P7["t"] + 2
    m = P7.merge(lab, on=["province_code", "q"])
    fn = m[(m["y"] == 1) & (m["I7_yhat"] == 0)]
    out["I7_missed_HIGH"] = [{"quarter": L.qs(int(r.q)), "province": L.NAMES[r.province_code], "p": round(r.I7_p, 3),
                              "food_on": int(r.food_on), "gap_on": int(r.gap_on),
                              "food_forecast": round(r.I7_F_hat, 2), "food_observed": round(r.F, 2),
                              "food_threshold": round(th["food"][r.province_code], 2),
                              "gap_forecast": round(r.I7_G_hat, 2), "gap_observed": round(r.F - r.HL, 2),
                              "gap_threshold": round(th["gap"][r.province_code], 2), "p_hunger": round(r.I7_p_hunger, 3)}
                             for r in fn.itertuples()]
    (E47 / "runs" / "diagnostics.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["labels"]["HIGH_switched_on_by"]), out["labels"]["by_province"],
          "within-quarter label var share", round(out["labels"]["within_quarter_share_of_label_variance"], 3),
          "H>11.3 quarters since 2023-Q4:", out["labels"]["quarters_with_H_above_11_3_since_2023Q4"], "/",
          out["labels"]["quarters_since_2023Q4"])
    for c, v in cov.items():
        print(f"  {v['group']:15s} {c:24s} complete {v['origins_complete']}/{v['origins_total']} varying {v['origins_varying_across_provinces']} within-share {v['within_quarter_variance_share']}")
    for r in out["I7_missed_HIGH"]:
        print("  MISS", r)


if __name__ == "__main__":
    main()
