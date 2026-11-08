"""PROTOCOL_LEAD2_CPI_REFRESH: candidate CR = P0H4-U with the Lead-2+ CPI columns computed at each row's own
schedule-B issue date, against B0 = P0H4-U and the served P0H4, with the unchanged adoption rule.

    python cpi_refresh.py       # ../out/cpi_refresh.json, ../out/cpi_refresh_rows.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import final as FN
import lt_lib as T

F, M, KEY = T.F, T.M, T.KEY
CPI = ["A1_food", "A1_gap", "A_mom"]
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}


def main():
    proto = T.LT / "PROTOCOL_LEAD2_CPI_REFRESH.md"
    assert T.sha256(proto) == (T.HERE / "CPI_REFRESH_SHA256.txt").read_text().strip(), "protocol changed after freezing"
    S = T.stack().copy()
    R = pd.read_csv(T.DATA / "cpi_refresh.csv", dtype={"province_code": str})
    S2 = S.merge(R[KEY + ["m0r"] + [f"{c}_r" for c in CPI]], on=KEY, how="left")
    hit = S2["m0r"].notna()
    assert (S2.loc[hit, "lead"] >= 2).all() and int(hit.sum()) == int((S["lead"] >= 2).sum())
    changed_nan = {c: int((S2.loc[hit, c].notna() & S2.loc[hit, f"{c}_r"].isna()).sum()) for c in CPI}
    for c in CPI:
        S2.loc[hit, c] = S2.loc[hit, f"{c}_r"]
    E = pd.read_csv(T.OUT / "final_rows.csv", dtype={"province_code": str})
    E = E[KEY + ["q", "y", "price", "hunger", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p", "B0_price", "B0_p"]]
    C = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    E = E.merge(C[KEY + ["P0H4_p3", "P0_price"]].rename(columns={"P0H4_p3": "P0H4_p", "P0_price": "P0H4_price"}), on=KEY)
    origins = sorted(E["t"].unique())
    P = T.run(T.U2, origins, S=S2)
    E = E.merge(P[KEY + ["pi_P", "cfg"]].rename(columns={"pi_P": "CR_price", "cfg": "CR_cfg"}), on=KEY, how="left")
    assert E["CR_price"].notna().all()
    E["CR_p"] = E["pi_H_AB"] * E["CR_price"]
    res = {"protocol_sha256": T.sha256(proto), "refreshed_rows": int(hit.sum()), "refresh_made_nan": changed_nan,
           "cands": {c: FN.lead_eval(E, c) for c in ("P0H4", "B0", "CR")}}
    for c in ("P0H4", "B0", "CR"):
        for k, g in E.groupby("lead"):
            d = res["cands"][c]["leads"][int(k)]
            d["vs_P0H4"] = M.boot_diff(g["q"], (g[f"{c}_p"] - g["y"]) ** 2, (g["P0H4_p"] - g["y"]) ** 2)
            d["auc"] = M.auc(g["y"], g[f"{c}_p"])
            d["price_auc_hunger_rows"] = M.auc(g.loc[g["hunger"] == 1, "price"], g.loc[g["hunger"] == 1, f"{c}_price"])
    rule = FN.adoption_rule(res["cands"]["B0"]["leads"], res["cands"]["CR"]["leads"])
    adopt = all(rule.values())
    final = "CR" if adopt else "B0"
    res["adoption"] = {"rule": rule, "adopted": adopt, "FINAL": final,
                       "lead2_reliable": res["cands"][final]["leads"][2]["reliable"],
                       "lead2_failed": res["cands"][final]["leads"][2]["failed"],
                       "CR_lead2_failed": res["cands"]["CR"]["leads"][2]["failed"],
                       "CR_lead1_failed": res["cands"]["CR"]["leads"][1]["failed"],
                       "max_reliable_lead": res["cands"][final]["max_reliable_lead"]}
    g = E[E["lead"] == 2]
    eb, ek = (g["B0_p"] >= .5).astype(int) != g["y"], (g["CR_p"] >= .5).astype(int) != g["y"]
    lst = lambda m: [f"{NAMES[r.province_code]} {F.qs(int(r.q))} ({'FN' if r.y else 'FP'}; B0 {r.B0_p:.3f} -> CR {r.CR_p:.3f})"  # noqa: E731
                     for r in g[m].itertuples()]
    res["lead2_errors"] = {"fixed_by_CR": lst(eb & ~ek), "new_errors_CR": lst(~eb & ek), "kept": lst(eb & ek)}
    E.to_csv(T.OUT / "cpi_refresh_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    T.OUT.joinpath("cpi_refresh.json").write_text(json.dumps(res, indent=1, default=float))
    for c in ("P0H4", "B0", "CR"):
        print(c, "max reliable lead", res["cands"][c]["max_reliable_lead"])
        for k in (1, 2, 3):
            d = res["cands"][c]["leads"][k]
            m = d["metrics"]
            print(f"  L{k} acc {m['accuracy']:.3f} {[round(x, 2) for x in d['acc_ci90']]} bal {m['balanced_accuracy']:.3f} "
                  f"P {m['precision']:.3f} R {m['recall']:.3f} TP{m['tp']} FP{m['fp']} FN{m['fn']} TN{m['tn']} Br {m['brier']:.4f} "
                  f"vsB0 {d['vs_B0']['diff']:+.4f} {[round(x, 4) for x in d['vs_B0']['ci90']]} p{d['vs_B0'].get('p_less', 1):.3f} "
                  f"vsP0H4 {d['vs_P0H4']['diff']:+.4f} devBr {d['dev']['brier']:.4f} devBal {d['dev']['balanced_accuracy']:.3f} "
                  f"later acc {d['conf']['accuracy']:.3f} Br {d['conf']['brier']:.4f} thirds {[round(x, 2) for x in d['acc_thirds']]} "
                  f"loqo {d['loqo_min']:.3f} pers p{d['brier_vs_persist']['p_less']:.3f} clim p{d['brier_vs_clim']['p_less']:.3f} "
                  f"AUC {d['auc']:.3f} priceAUC {d['price_auc_hunger_rows']:.3f} fail {d['failed']}")
    print(json.dumps(res["adoption"], indent=1))
    print(json.dumps(res["lead2_errors"], indent=1))
    print("refresh made NaN:", changed_nan)


if __name__ == "__main__":
    main()
