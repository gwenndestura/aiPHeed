"""LOCAL DEMO export of C-B6P (province-quarter, Eq. 3, + E1/E2/D1) for viewing on localhost.

Copies the C-B6 export layout (backend/data/foodinsecurity_engine_cb6/) and replaces, per province row, the probability,
class, score, observed Eq. 3 label, SHAP and relative driver bars with C-B6P's; evaluation.json gets C-B6P's metrics.
Writes backend/data/foodinsecurity_engine_cb6p/. The served C-B6 export is not touched. C-B6P FAILED its pre-registered
acceptance (out/cb6p_results.json); served only when the backend runs with AIPHEED_FI_DATA_DIR pointing at the folder.

    python export_cb6p.py
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[3]
SRC = ROOT / "backend" / "data" / "foodinsecurity_engine_cb6"
OUT = ROOT / "backend" / "data" / "foodinsecurity_engine_cb6p"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cb6p_model as M  # noqa: E402

H = M.H
BARS = ("market", "climate", "fish_kill", "employment", "ofw_remittance")


def metrics_full(y, p) -> dict:
    m = M.metrics(y, p)
    c, y = (np.asarray(p) >= .5).astype(int), np.asarray(y, int)
    m.update(TP=int(((c == 1) & (y == 1)).sum()), FP=int(((c == 1) & (y == 0)).sum()),
             FN=int(((c == 0) & (y == 1)).sum()), TN=int(((c == 0) & (y == 0)).sum()))
    return m


def main(name: str = "C-B6P"):
    p2 = name == "C-B6P2"
    if p2:
        import cb6p2_model as P2
        pre = P2.check()
        OUT_ = ROOT / "backend" / "data" / "foodinsecurity_engine_cb6p2"
    else:
        pre = M.check()
        OUT_ = OUT
    res = json.loads((HERE / "out" / ("cb6p2_results.json" if p2 else "cb6p_results.json")).read_text(encoding="utf-8"))
    F = pd.concat([pd.read_csv(HERE / "out" / "cb6p_fits.csv")] + ([pd.read_csv(HERE / "out" / "cb6p2_fits.csv")] if p2 else []),
                  ignore_index=True)
    Fall = F
    F = F[F["name"] == name].copy()
    L = pd.read_csv(HERE / "out" / "cb6p_labels.csv").set_index(["province", "q"])
    if p2:
        M.GROUPS["province_history"] = ["S_last", "y_last"]
    for g, cs in M.GROUPS.items():
        F[f"g_{g}"] = sum(F[f"shap_{c}"].fillna(0) for c in cs)
    R = pd.read_csv(SRC / "rows.csv", dtype={"province_code": str})
    out = []
    for r in R.to_dict("records"):
        t, k, q = H.qi(r["origin"]), int(r["lead"]), H.qi(r["quarter"])
        f = F[(F["t"] == t) & (F["lead"] == k) & (F["province"] == r["province_code"])]
        assert len(f) == 1, (r["province"], r["quarter"])
        f = f.iloc[0]
        p = float(f["p"])
        key = (r["province_code"], q)
        obs = ("HIGH" if L.loc[key, "y"] == 1 else "LOW") if key in L.index and q < H.qi("2026-Q4") else ""
        win = F[(F["lead"] == k) & (F["t"] <= t) & (F["province"] == r["province_code"])]
        r.update(probability=round(p, 6), pi_hunger=round(p, 6), score=round(p * float(r["pov_weight"]), 6),
                 **{"class": "HIGH" if p >= .5 else "LOW"}, observed=obs,
                 observed_hunger=round(float(L.loc[key, "H"]), 2) if obs else "",
                 fallback=bool(str(f["fallback"]).lower() == "true"), model="CB6P2-PROVINCE" if p2 else "CB6P-PROVINCE", seal_sha256="")
        for g in M.GROUPS:
            r[f"shap_{g}"] = round(float(f[f"g_{g}"]), 6)
        for g in BARS:
            typ = float(win[f"g_{g}"].abs().mean()) if len(win) else 0.0
            r[f"avg8_shap_{g}"] = round(float(f[f"g_{g}"]) / typ, 6) if typ > 0 else 0.0
        r["avg8_n"] = int(len(win))
        r["avail_employment"] = r["avail_ofw_remittance"] = 1
        out.append(r)
    OUT_.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out).to_csv(OUT_ / "rows.csv", index=False)
    shutil.copyfile(SRC / "lgu_vulnerability.csv", OUT_ / "lgu_vulnerability.csv")

    ev = json.loads((SRC / "evaluation.json").read_text(encoding="utf-8"))
    Lb = pd.read_csv(HERE / "out" / "cb6p_labels.csv")
    G = Fall[Fall["name"].isin([name, "PERSIST"])].pivot_table(index=["t", "lead", "q", "province"], columns="name",
                                                                  values="p").reset_index()
    G = G.merge(Lb[["province", "q", "y"]], on=["province", "q"])
    leads = {}
    for k in (1, 2, 3):
        W = G[(G["lead"] == k) & (G["q"] >= M.Q0)].dropna(subset=[name])
        m = metrics_full(W["y"], W[name])
        sh = res["leads"][str(k)].get("shap_share_pct_mean" if p2 else "C-B6P_shap_share_pct_mean")
        leads[str(k)] = {"n": int(len(W)), "n_quarters": int(W["q"].nunique()),
                         "period": f"{H.qs(int(W['q'].min()))}..{H.qs(int(W['q'].max()))}",
                         "metrics": {x: m[x] for x in ("accuracy", "balanced", "precision", "recall", "f1", "auc", "brier",
                                                        "TP", "FP", "FN", "TN")},
                         "persistence_accuracy": float(((W["PERSIST"] >= .5) == W["y"]).mean()),
                         "alg3_pass": bool(m["accuracy"] >= .75), "reliable": bool(k <= res["algorithm3"][name]),
                         "rules": {}, "failed": ["R1-R7 not evaluated for province-quarters"],
                         "shap_shares": ({"H1 Hunger (SWS)": sh["hunger"], "Market and prices": sh["market"],
                                          "N1 News": sh["news"], "E1 Employment": sh["employment"],
                                          "E2 OFW remittances": sh["ofw_remittance"], "D1 Province food price": sh["province_price"],
                                          "S Rice stocks (supply)": sh["supply"], "Climate": sh["climate"],
                                          "C4 Fisheries": sh["fish_kill"]} if sh else None),
                         "vs_REF": None}
    m1, m2 = leads["1"]["metrics"], leads["2"]["metrics"]
    ev.update({
        "model": "CB6P2-PROVINCE" if p2 else "CB6P-PROVINCE",
        "target": "Chapter III Eq. 3 per province-quarter: SWS Balance Luzon hunger + 2 x province food CPI YoY deviation "
                  f"from the five-province mean > {json.loads((HERE / 'out' / 'cb6p_checks.json').read_text(encoding='utf-8'))['THR']:.1f} (2021-22 median)",
        "decision_rule": "HIGH when the province's own P >= 0.50",
        "design": "LOCAL DEMO, NOT THE MAIN MODEL: C-B6P = C-B6's procedure on province-quarter rows (Eq. 3) with "
                  "C-B6's 23 inputs + E1 employment + E2 OFW remittances + D1 province food-price deviation "
                  "(OBJECTIVES_AUDIT/CB6P/PREREGISTRATION.md)",
        "chosen": f"NOT adopted: {name} failed its pre-registered acceptance (CB6P/RESULTS.md). C-B6 stays the main model.",
        "max_reliable_lead": res["algorithm3"][name], "max_reliable_lead_r1_r7": 0, "leads": leads,
        "news_shap_share_lead1": leads["1"]["shap_shares"], "not_input_groups": [], "plan_sha256": pre,
        "seal_sha256": "", "seal_file": "none (local demo)",
        "news_effect_text": f"the NLP input (FSSI anomaly) carries {leads['1']['shap_shares']['N1 News']:.1f}% of SHAP influence",
        "model_description": "one LightGBM per origin trained walk-forward on SWS hunger since 1998 and on province "
                             "food-price deviations since 2021, with prices, climate, production, world-price, news, "
                             "rice stock, employment and OFW remittance inputs",
        "sources_extra": "PSA provincial food CPI (2021+), PSA LFS unemployment, BSP OFW personal remittances",
        "model_line": (f"{name} (LOCAL DEMO, failed acceptance): province-quarter LightGBM (Eq. 3) with employment and OFW "
                       f"remittances{' and the province last known stress score' if p2 else ''}. Development accuracy Lead 1 {m1['accuracy']:.3f}, Lead 2 {m2['accuracy']:.3f} on "
                       f"{leads['1']['n']} province-quarters; Maximum Reliable Lead Time {res['algorithm3']['C-B6P']} "
                       "quarter(s). Not the main model."),
    })
    (OUT_ / "evaluation.json").write_text(json.dumps(ev, indent=1, default=str), encoding="utf-8")
    D = pd.DataFrame(out)
    print(f"rows {len(D)} -> {OUT_}")
    print(D[D["quarter"] == "2027-Q1"][["province", "probability", "class", "score"]].to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "C-B6P")
