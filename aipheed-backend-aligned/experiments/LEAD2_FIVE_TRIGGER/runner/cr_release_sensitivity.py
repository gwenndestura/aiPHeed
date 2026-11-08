"""CR_REVIEW, sensitivity of candidate CR to the CPI release-day assumption (report only; not a candidate, nothing is
selected or adopted). CR assumes PSA's provincial CPI for month m is usable from day 10 of month m+1; the margins to
the re-issue dates are as small as 2 days (out/cr_review.json). This rebuilds the refreshed CPI columns with a later
release day and re-scores CR exactly as cpi_refresh.py does.

    python cr_release_sensitivity.py 15 20   # ../out/cr_release_sensitivity.json
"""
from __future__ import annotations

import json
import sys

import pandas as pd

import final as FN
import lt_lib as T
import cpi_refresh_features as CF  # noqa: I001  (after final: it puts the E107 runner first on sys.path)

F, KEY = T.F, T.KEY
CPI = ["A1_food", "A1_gap", "A_mom"]


def refreshed(day: int) -> pd.DataFrame:
    CF.RELEASE_DAY = day
    S = T.stack()
    d, _ = CF.E.data()
    th = CF.L.e40_spec()
    rows = []
    for t, k, p in zip(S["t"], S["lead"], S["province_code"]):
        t, k = int(t), int(k)
        if k < 2:
            continue
        m0 = CF.L.m0_of(t)
        m = CF.newest_month(F.issue(t, "B"), m0)
        rows.append({"t": t, "lead": k, "province_code": p, "m0r": m,
                     **dict(zip([f"{c}_r" for c in CPI], CF.cols(d, th, t, k, p, m)))})
    return pd.DataFrame(rows)


def score(R: pd.DataFrame) -> dict:
    S = T.stack().merge(R, on=KEY, how="left")
    hit = S["m0r"].notna()
    for c in CPI:
        S.loc[hit, c] = S.loc[hit, f"{c}_r"]
    E = pd.read_csv(T.OUT / "cpi_refresh_rows.csv", dtype={"province_code": str})
    E = E[KEY + ["q", "y", "price", "hunger", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p", "B0_price", "B0_p", "CR_p"]]
    P = T.run(T.U2, sorted(E["t"].unique()), S=S)
    E = E.merge(P[KEY + ["pi_P"]].rename(columns={"pi_P": "CRd_price"}), on=KEY, how="left")
    E["CRd_p"] = E["pi_H_AB"] * E["CRd_price"]
    ev = FN.lead_eval(E, "CRd")["leads"]
    b0 = FN.lead_eval(E, "B0")["leads"]
    out = {}
    for k in (1, 2, 3, 4):
        m = ev[k]["metrics"]
        out[k] = {"accuracy": m["accuracy"], "balanced_accuracy": m["balanced_accuracy"], "precision": m["precision"],
                  "recall": m["recall"], "tp_fp_fn_tn": [int(m[x]) for x in ("tp", "fp", "fn", "tn")], "brier": m["brier"],
                  "vs_B0": ev[k]["vs_B0"], "failed": ev[k]["failed"]}
    out["adoption_rule_vs_B0"] = FN.adoption_rule(b0, ev)
    g = E[E["lead"] == 2]
    out["lead2_calls_differ_from_CR"] = int(((g["CRd_p"] >= .5) != (g["CR_p"] >= .5)).sum())
    return out


def main():
    days = [int(x) for x in sys.argv[1:]] or [15]
    res = {}
    for day in days:
        R = refreshed(day)
        res[day] = {"rows_refreshed": int(len(R)), "extra_months": R["m0r"].sub(R["t"].map(CF.L.m0_of)).value_counts().sort_index().to_dict(),
                    **score(R)}
        print(day, json.dumps({k: res[day][k] for k in (2, "adoption_rule_vs_B0", "lead2_calls_differ_from_CR")}, default=float), flush=True)
    (T.OUT / "cr_release_sensitivity.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
