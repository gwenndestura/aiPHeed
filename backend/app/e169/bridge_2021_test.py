"""E169: test the 2019-fitted FIES->HFIAS bridge (frozen, from fies_bridge.py) on 2021 same-household pairs from the
FNRI 2021 ENNS Facts and Figures (national + socio-demographic subgroups). No refitting on 2021 for the verdict.

    python -m app.e169.bridge_2021_test -> data/e169/out/bridge_2021_test.json
"""
import json

import numpy as np
import pandas as pd

from app.paths import BACKEND_DIR

D = BACKEND_DIR / "data" / "e169"
lg = lambda p: np.log(np.asarray(p, float) / (100 - np.asarray(p, float)))
ex = lambda z: 100 / (1 + np.exp(-np.asarray(z, float)))


def main():
    B = json.loads((D / "out" / "fies_bridge_feasibility.json").read_text())["bridge_logit"]
    a, b = B["intercept"], B["slope"]
    P = pd.read_csv(D / "raw" / "enns2021_fies_hfias_subgroup_pairs.csv")
    P["bridged"] = ex(a + b * lg(P.fies_modsev_pct))
    P["err_pts"] = P.bridged - P.hfias_modsev_pct
    P["naive_err_pts"] = P.fies_modsev_pct - P.hfias_modsev_pct          # using FIES as if it were HFIAS
    s21, i21 = np.polyfit(lg(P.fies_modsev_pct), lg(P.hfias_modsev_pct), 1)
    nat = P[P.subgroup == "Philippines"].iloc[0]
    out = {
        "frozen_2019_bridge": B,
        "national_2021": {"fies": nat.fies_modsev_pct, "hfias_observed": nat.hfias_modsev_pct, "hfias_bridged": round(float(nat.bridged), 1), "error_pts": round(float(nat.err_pts), 1)},
        "subgroups_n": int(len(P)),
        "mean_error_pts": round(float(P.err_pts.mean()), 2),
        "mean_abs_error_pts": round(float(P.err_pts.abs().mean()), 2),
        "max_abs_error_pts": round(float(P.err_pts.abs().max()), 1),
        "naive_mean_abs_error_pts_FIES_as_HFIAS": round(float(P.naive_err_pts.abs().mean()), 2),
        "HIGH50_agreement": round(float(((P.bridged >= 50) == (P.hfias_modsev_pct >= 50)).mean()), 3),
        "2021_own_fit_for_comparison_only": {"intercept": round(float(i21), 3), "slope": round(float(s21), 3)},
        "rows": P[["group", "subgroup", "fies_modsev_pct", "hfias_modsev_pct", "bridged", "err_pts"]].round(1).to_dict("records"),
    }
    (D / "out" / "bridge_2021_test.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1, default=float))
    print(P[["subgroup", "fies_modsev_pct", "hfias_modsev_pct", "bridged", "err_pts"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
