"""PROTOCOL_LEAD2_SUBGROUP: K2 = P0H4-U + K_diff (the subgroup column not explained by the aggregate price columns),
scored against B0 from LEAD2_FINAL with the unchanged LEAD2_FINAL adoption rule.

    python subgroup_k2.py       # ../out/subgroup_k2.json, ../out/subgroup_k2_rows.csv
"""
from __future__ import annotations

import json

import pandas as pd

import final as FN
import lt_lib as T

F, KEY = T.F, T.KEY
COLS = T.U2 + ["K_diff"]
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}


def main():
    proto = T.LT / "PROTOCOL_LEAD2_SUBGROUP.md"
    assert T.sha256(proto) == (T.HERE / "SUBGROUP_SHA256.txt").read_text().strip(), "protocol changed after freezing"
    S = pd.read_csv(T.DATA / "stack_v4.csv", dtype={"province_code": str})
    E = pd.read_csv(T.OUT / "final_rows.csv", dtype={"province_code": str})
    P = FN.run(S, COLS, sorted(E["t"].unique()))
    E = E.merge(P[KEY + ["pi_P", "cfg"]].rename(columns={"pi_P": "K2_price", "cfg": "K2_cfg"}), on=KEY, how="left")
    assert E["K2_price"].notna().all()
    E["K2_p"] = E["pi_H_AB"] * E["K2_price"]
    res = {"protocol_sha256": T.sha256(proto), "cols": COLS, "cands": {c: FN.lead_eval(E, c) for c in ("B0", "K1", "K2")}}
    rule = FN.adoption_rule(res["cands"]["B0"]["leads"], res["cands"]["K2"]["leads"])
    adopt = all(rule.values())
    final = "K2" if adopt else "B0"
    res["adoption"] = {"rule": rule, "adopted": adopt, "FINAL": final,
                       "lead2_reliable": res["cands"][final]["leads"][2]["reliable"],
                       "lead2_failed": res["cands"][final]["leads"][2]["failed"]}
    g = E[E["lead"] == 2]
    eb, ek = (g["B0_p"] >= .5).astype(int) != g["y"], (g["K2_p"] >= .5).astype(int) != g["y"]
    lst = lambda m: [f"{NAMES[r.province_code]} {F.qs(int(r.q))} ({'FN' if r.y else 'FP'}; B0 {r.B0_p:.3f} -> K2 {r.K2_p:.3f})"  # noqa: E731
                     for r in g[m].itertuples()]
    res["lead2_errors"] = {"fixed_by_K2": lst(eb & ~ek), "new_errors_K2": lst(~eb & ek), "kept": lst(eb & ek)}
    miss = g[(g["y"] == 1) & (g["B0_p"] < .5)]
    res["lead2_missed_probabilities"] = {f"{NAMES[r.province_code]} {F.qs(int(r.q))}": {"B0": r.B0_p, "K1": r.K1_p, "K2": r.K2_p}
                                         for r in miss.itertuples()}
    E.to_csv(T.OUT / "subgroup_k2_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    T.OUT.joinpath("subgroup_k2.json").write_text(json.dumps(res, indent=1, default=float))
    for c, r in res["cands"].items():
        print(c, "max reliable lead", r["max_reliable_lead"])
        for k in (1, 2):
            d = r["leads"][k]
            m = d["metrics"]
            print(f"  L{k} acc {m['accuracy']:.3f} {[round(x, 2) for x in d['acc_ci90']]} bal {m['balanced_accuracy']:.3f} "
                  f"P {m['precision']:.3f} R {m['recall']:.3f} TP{m['tp']} FP{m['fp']} FN{m['fn']} TN{m['tn']} Br {m['brier']:.4f} "
                  f"vsB0 {d['vs_B0']['diff']:+.4f} {[round(x, 4) for x in d['vs_B0']['ci90']]} p{d['vs_B0'].get('p_less', 1):.3f} "
                  f"devBr {d['dev']['brier']:.4f} devBal {d['dev']['balanced_accuracy']:.3f} conf {d['conf']['accuracy']:.3f} "
                  f"thirds {[round(x, 2) for x in d['acc_thirds']]} loqo {d['loqo_min']:.3f} "
                  f"pers p{d['brier_vs_persist']['p_less']:.3f} clim p{d['brier_vs_clim']['p_less']:.3f} "
                  f"price acc {d['price_term']['accuracy']:.3f} years {d['acc_by_year']} fail {d['failed']}")
    print(json.dumps(res["adoption"], indent=1))
    print(json.dumps(res["lead2_errors"], indent=1))
    print(json.dumps(res["lead2_missed_probabilities"], indent=1, default=float))


if __name__ == "__main__":
    main()
