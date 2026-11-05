"""LOCAL DEMO export of C-B6D-E-X (decomposed Eq. 3 provincial model, extended history) for viewing on localhost.

Writes backend/data/foodinsecurity_engine_cb6dex/ in the C-B6 export layout. The served exports are not touched. Every
quarter up to 2026-Q4 is shown at Lead 1 (the reliable lead); 2027-Q1 at Lead 2 (issued 2026-10-01). Probabilities,
classes and observed Eq. 3 labels are per province; driver bars come from the regional hunger part (C-B6E SHAP, incl.
employment E1 and OFW E2), which is shared by the five provinces; the province price term is in shap_province_price.

    python export_cb6dex.py
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
import shutil
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[3]
SRC = ROOT / "backend" / "data" / "foodinsecurity_engine_cb6"
MODE = sys.argv[1] if len(sys.argv) > 1 else ""  # "pm": paper median (PREREGISTRATION_PM.md); "ad": + all drivers (_AD.md)
AD = MODE == "ad"
PM = MODE in ("pm", "ad")
IN = HERE / "out" / MODE
OUT = ROOT / "backend" / "data" / f"foodinsecurity_engine_cb6dex{MODE}"
MODEL = {"pm": "CB6DEX-PM-PROVINCE", "ad": "CB6DEX-PM-AD-PROVINCE"}.get(MODE, "CB6DEX-PROVINCE")
SUFFIX = {"pm": "-PM", "ad": "-PM-AD"}.get(MODE, "")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fi_provincial as FP  # noqa: E402

H, D = FP.H, FP.D
GROUPS = {"market": ["R_food_yoy", "R_head_yoy", "R_food_mom", "R_rice_yoy"] + H.WORLD,
          "climate": ["ONI_last", "ONI_max12", "tc_mean", "R_C3"], "fish_kill": ["R_C4"],
          "hunger": ["h_last", "h_change", "h_mean4", "true_h", "pi_H4L"], "news": ["z_N1R"], "lead": ["lead"],
          "employment": ["E1"], "ofw_remittance": ["E2"], "supply": ["ST1", "ST2"]}
BARS = ("market", "climate", "fish_kill", "employment", "ofw_remittance")


def main():
    F = pd.read_csv(IN / "fi_provincial_fits.csv")
    F = F[F["name"] == "C-B6D-E-X"]
    L = pd.read_csv(IN / "fi_labels_ext.csv").set_index(["province", "q"])
    res = json.loads((IN / "fi_provincial_results.json").read_text(encoding="utf-8"))
    E = pd.read_csv(IN / "cb6e_ad_fits.csv") if AD else pd.read_csv(HERE.parent / "FIXES_2026-11-04" / "out" / "cb6e_fits.csv")
    for g, cs in GROUPS.items():
        E[f"g_{g}"] = sum(E[f"shap_{c}"].fillna(0) for c in cs if f"shap_{c}" in E)
    R = pd.read_csv(SRC / "rows.csv", dtype={"province_code": str})
    out = []
    for r in R.to_dict("records"):
        q = H.qi(r["quarter"])
        k = 2 if r["quarter"] == "2027-Q1" else 1
        t = q - k
        f = F[(F["t"] == t) & (F["lead"] == k) & (F["province"] == r["province_code"])]
        e = E[(E["t"] == t) & (E["lead"] == k)]
        assert len(f) == 1 and len(e) == 1, (r["province"], r["quarter"])
        f, e = f.iloc[0], e.iloc[0]
        p = float(f["p"])
        key = (r["province_code"], q)
        obs = ("HIGH" if L.loc[key, "y"] == 1 else "LOW") if key in L.index and q < H.qi("2026-Q4") else ""
        win = E[(E["lead"] == k) & (E["t"] <= t)]
        if PM and not AD:  # bars = this forecast and the 7 before it (real SHAP, trailing-8 view), not this forecast alone
            win = win.sort_values("t").tail(8)
        r.update(lead=k, origin=H.qs(t), issue_date=H.issue(t), probability=round(p, 6), pi_hunger=round(float(f["p_hunger_part"]), 6),
                 score=round(p, 6), **{"class": "HIGH" if p >= .5 else "LOW"}, observed=obs,
                 observed_hunger=round(float(L.loc[key, "H"]), 2) if obs else "", model=MODEL, seal_sha256="",
                 fallback=False, shap_province_price=round(float(f["D_hat"]), 6))
        for g in GROUPS:
            r[f"shap_{g}"] = round(float(e[f"g_{g}"]), 6)
        for g in BARS:
            typ = float(win[f"g_{g}"].abs().mean()) if len(win) else 0.0
            if PM and not AD:
                r[f"avg8_shap_{g}"] = round(float((1 if win[f"g_{g}"].mean() >= 0 else -1) * typ), 6)
            else:
                r[f"avg8_shap_{g}"] = round(float(e[f"g_{g}"]) / typ, 6) if typ > 0 else 0.0
        r["avg8_n"] = int(len(win))
        r["avail_employment"] = r["avail_ofw_remittance"] = 1
        out.append(r)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(out).to_csv(OUT / "rows.csv", index=False)
    shutil.copyfile(SRC / "lgu_vulnerability.csv", OUT / "lgu_vulnerability.csv")
    ev = json.loads((SRC / "evaluation.json").read_text(encoding="utf-8"))
    leads = {}
    for k in ("1", "2", "3"):
        m = res["B_ext"][k]["C-B6D-E-X"]
        g = F[(F["lead"] == int(k)) & (F["q"] >= FP.Q_EXT)].merge(
            L.reset_index()[["province", "q", "y"]], on=["province", "q"])
        c, y = (g["p"] >= .5).astype(int), g["y"].astype(int)
        cm = {"TP": int(((c == 1) & (y == 1)).sum()), "FP": int(((c == 1) & (y == 0)).sum()),
              "FN": int(((c == 0) & (y == 1)).sum()), "TN": int(((c == 0) & (y == 0)).sum())}
        assert len(g) == m["n"] and abs((cm["TP"] + cm["TN"]) / len(g) - m["accuracy"]) < 1e-12
        leads[k] = {"n": m["n"], "n_quarters": 50, "period": "2013-Q1..2026-Q3",
                    "metrics": {**{x: m[x] for x in ("accuracy", "balanced", "precision", "recall", "f1", "auc", "brier")}, **cm},
                    "persistence_accuracy": res["B_ext"][k].get("PERSIST-X", {}).get("accuracy"),
                    "alg3_pass": bool(m["accuracy"] >= .75), "reliable": bool(int(k) <= res["algorithm3_ext"]["C-B6D-E-X"]),
                    "rules": m.get("rules", {}), "failed": m.get("failed", ["not evaluated"]), "shap_shares": None, "vs_REF": None}
    m1, m2 = leads["1"]["metrics"], leads["2"]["metrics"]
    ev.update({
        "model": MODEL,
        "target": "Chapter III Eq. 3 per province-quarter: SWS Balance Luzon hunger + 2 x province food CPI YoY deviation "
                  f"from the five-province mean > {res['THR']:g} ({'paper: median of S, 2013-2026' if PM else '2021-22 median'})",
        "decision_rule": "HIGH when the province's own P >= 0.50",
        "design": "LOCAL DEMO, NOT THE SERVED MODEL: C-B6D-E-X = Eq. 3 decomposed: regional hunger part (C-B6E LightGBM, with "
                  "employment and OFW) + province food-price deviation part, combined as S = H + 2D (CB6P/PREREGISTRATION_FI.md)",
        "chosen": "Strongest provincial candidate (development evidence); not adopted for serving. C-B6 stays the served model.",
        "max_reliable_lead": res["algorithm3_ext"]["C-B6D-E-X"], "max_reliable_lead_r1_r7": 0 if PM else 1, "served_leads": [1, 2],
        "leads": leads, "not_input_groups": [], **({"driver_view": "trailing8"} if PM and not AD else {}), "seal_sha256": "", "seal_file": "out/seal_prospective_X2.csv (2c1ff50a...)",
        "model_line": (f"C-B6D-E-X{SUFFIX} (LOCAL DEMO, cut-off {res['THR']:g}): provincial Eq. 3 forecast = regional SWS hunger part + province food-price part. "
                       f"Accuracy Lead 1 {m1['accuracy']:.3f}, Lead 2 {m2['accuracy']:.3f} (failed rules L1 {leads['1']['failed']}, L2 {leads['2']['failed']}) on 250 "
                       "province-quarters 2013-2026. Not the served model."),
    })
    if AD:  # every driver is in every forecast: bars show this forecast's own SHAP shares
        ev["driver_view"] = "five"
        ev["design"] += "; regional part = logistic driver base + LightGBM (CB6P/PREREGISTRATION_AD.md, owner directive, EXPLORATORY)"
    (OUT / "evaluation.json").write_text(json.dumps(ev, indent=1, default=str), encoding="utf-8")
    D_ = pd.DataFrame(out)
    print(f"rows {len(D_)} -> {OUT}")
    print(D_[D_["quarter"].isin(["2026-Q4", "2027-Q1"])][["province", "quarter", "lead", "probability", "class"]].to_string(index=False))


if __name__ == "__main__":
    main()
