"""PROTOCOL v3: the poverty input V1 split into population-weighted poverty (monotone increasing, D1) and density;
D2 = the same split without the constraint. Same unified LightGBM, rows, hunger term and criteria as B0 (P0H4-U).

    python poverty_v3.py        # ../out/poverty_v3.json, ../out/poverty_v3_rows.csv
"""
from __future__ import annotations

import csv
import json

import numpy as np
import pandas as pd

import improve as IM
import lt_lib as T

F, M, KEY = T.F, T.M, T.KEY
VULN = T.EXP.parents[1] / "backend" / "data" / "inputs" / "lgu_vulnerability.csv"
NAMES = {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000",
         "Batangas": "PH040500000"}


def components() -> tuple[dict, dict, dict]:
    acc = {}
    with open(VULN, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            a = acc.setdefault(NAMES[r["province"]], {"pov": [], "w": [], "pop": 0.0, "area": 0.0})
            try:
                v = float(r["poverty_lgu_estimate"])
                if np.isfinite(v):
                    a["pov"].append(v)
                    a["w"].append(float(r["population_2024"]))
            except ValueError:
                pass
            a["pop"] += float(r["population_2024"])
            a["area"] += float(r["land_area_km2"])
    pov = {p: float(np.average(a["pov"], weights=a["w"])) for p, a in acc.items()}
    den = {p: a["pop"] / a["area"] for p, a in acc.items()}
    mm = lambda d: {k: (v - min(d.values())) / (max(d.values()) - min(d.values())) for k, v in d.items()}  # noqa: E731
    return pov, mm(pov), mm(den)


def main():
    assert T.sha256(T.LT / "PROTOCOL_LEAD2_POVERTY_V3.md") == (T.HERE / "V3_SHA256.txt").read_text().strip()
    pov, pn, dn = components()
    S = T.stack().copy()
    S["V1_pov"], S["V1_den"] = S["province_code"].map(pn), S["province_code"].map(dn)
    cols = [c for c in T.U2 if c != "V1"] + ["V1_pov", "V1_den"]
    C = pd.read_csv(T.OUT / "improve_rows.csv", dtype={"province_code": str})
    E = C[KEY + ["q", "y", "price", "pi_H_AB", "PERS_AB", "CLIM_p", "ALWAYS-LOW_p", "B0_price", "B0_p"]].copy()
    origins = sorted(E["t"].unique())
    models = {}
    for name, mono in (("D1", T.MONO_UP + ["V1_pov"]), ("D2", T.MONO_UP)):
        mods = {}
        P = IM.run(S, cols, mono, (None,), origins, models=mods)
        models[name] = mods
        E = E.merge(P[KEY + ["pi_P"]].rename(columns={"pi_P": f"{name}_price"}), on=KEY, how="left")
        assert E[f"{name}_price"].notna().all()
        E[f"{name}_p"] = E["pi_H_AB"] * E[f"{name}_price"]
    res = {"protocol_sha256": T.sha256(T.LT / "PROTOCOL_LEAD2_POVERTY_V3.md"),
           "poverty_weighted": pov, "V1_pov": pn, "V1_den": dn, "V1_old": S.drop_duplicates("province_code").set_index("province_code")["V1"].to_dict(),
           "cands": {}}
    for c in ("B0", "D1", "D2"):
        dec = {}
        for k, g in E.groupby("lead"):
            d = F.evaluate(g, f"{c}_p", "PERS_AB")
            dv = g["q"] <= F.DEV_LAST
            d["dev"], d["conf"] = M.cls(g.loc[dv, "y"], g.loc[dv, f"{c}_p"]), M.cls(g.loc[~dv, "y"], g.loc[~dv, f"{c}_p"])
            d["vs_B0"] = M.boot_diff(g["q"], (g[f"{c}_p"] - g["y"]) ** 2, (g["B0_p"] - g["y"]) ** 2)
            dec[int(k)] = d
        q24 = E[(E["lead"] == 2) & (E["province_code"] == "PH040300000") & (E["q"] == 2024 * 4 + 2)]
        res["cands"][c] = {"leads": dec, "max_reliable_lead": F.max_reliable(dec),
                           "dev_L1": dec[1]["dev"]["brier"], "dev_L2": dec[2]["dev"]["brier"],
                           "quezon_2024Q3_lead2_p": float(q24[f"{c}_p"].iloc[0])}
    b0 = res["cands"]["B0"]

    def harmless(c):
        r = res["cands"][c]
        lost = [f"L{k}:{x}" for k in (1, 2) for x, v in b0["leads"][k]["criteria"].items() if v and not r["leads"][k]["criteria"][x]]
        return (r["max_reliable_lead"] >= b0["max_reliable_lead"] and r["dev_L1"] <= b0["dev_L1"] + .002
                and r["dev_L2"] <= b0["dev_L2"] + .002 and not lost), lost
    adopt = None
    for c in ("D1", "D2"):
        ok, lost = harmless(c)
        res["cands"][c]["harmless"], res["cands"][c]["criteria_lost"] = ok, lost
        if ok and adopt is None:
            adopt = c
    res["decision"] = {"adopted": adopt or "B0"}
    # SHAP direction of the poverty inputs for Quezon (D1, every origin, lead 2)
    sh = []
    for t, m in models["D1"].items():
        te = S[(S["t"] == t) & (S["lead"] == 2) & (S["province_code"] == "PH040300000")]
        if m.m is not None and len(te):
            v = m.shap(te)[0]
            sh.append({"origin": F.qs(t), "V1_pov": float(v[cols.index("V1_pov")]), "V1_den": float(v[cols.index("V1_den")])})
    res["D1_quezon_lead2_shap"] = sh
    E.to_csv(T.OUT / "poverty_v3_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    T.OUT.joinpath("poverty_v3.json").write_text(json.dumps(res, indent=1, default=float))
    print({k: round(v, 2) for k, v in pov.items()}, {k: round(v, 2) for k, v in pn.items()}, {k: round(v, 2) for k, v in dn.items()})
    for c, r in res["cands"].items():
        print(f"{c} maxrel {r['max_reliable_lead']} devL1 {r['dev_L1']:.4f} devL2 {r['dev_L2']:.4f} Quezon24Q3 p {r['quezon_2024Q3_lead2_p']:.3f} harmless {r.get('harmless')} lost {r.get('criteria_lost')}")
        for k in (1, 2, 3):
            d = r["leads"][k]
            m = d["metrics"]
            print(f"   L{k} acc {m['accuracy']:.3f} bal {m['balanced_accuracy']:.3f} P {m['precision']:.2f} R {m['recall']:.2f} TP{m['tp']} FP{m['fp']} FN{m['fn']} TN{m['tn']} "
                  f"Br {m['brier']:.3f} vsB0 {d['vs_B0']['diff']:+.4f}[{d['vs_B0']['ci90'][0]:+.3f},{d['vs_B0']['ci90'][1]:+.3f}] conf {d['conf']['accuracy']:.3f} {d['criteria']} ")
    print("decision", res["decision"])
    print("Quezon SHAP", [(x["origin"], round(x["V1_pov"], 3)) for x in sh])


if __name__ == "__main__":
    main()
