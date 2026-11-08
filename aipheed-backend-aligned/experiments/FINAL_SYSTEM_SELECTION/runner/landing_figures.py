"""Every number the Landing page states about the served P0H4 forecast (frontend/src/pages/Landing.tsx), from the served
evaluation and the matched comparison, so the copy can be checked against files.

  * per-lead metrics: backend/data/ch1_engine/evaluation.json (walk-forward, development evidence);
  * Lead-1 Brier against the six Chapter I SOP 3 comparators on the same 70 province-quarters, paired cluster
    bootstrap by target quarter (DASHBOARD_SELECTION/runner/compare.py inputs), Holm over the six;
  * the latest data period of each source at the 2026-10-01 issue date (the P0H4 stack and the served rows).

    python landing_figures.py   # out/landing_figures.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
ROOT = EXP.parents[1]
OUT = HERE.parent / "out"
sys.path.insert(0, str(EXP / "DASHBOARD_SELECTION" / "runner"))
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))
import compare as K  # noqa: E402
import run_l2 as RL  # noqa: E402

np, pd, FM, L, U = K.np, K.pd, K.FM, K.L, K.X.U
COMPARATORS = {"I. Naive persistence": "PERSIST-SI_p", "Logistic regression, combined": "LR-COMB_p",
               "Logistic regression, government data only": "LR-GOV_p", "Logistic regression, news only": "LR-NLP_p",
               "LightGBM, government data only": "LGBM-GOV_p", "LightGBM, news only": "LGBM-NLP_p"}


def main():
    U.setup()
    ev = json.loads((ROOT / "backend" / "data" / "ch1_engine" / "evaluation.json").read_text(encoding="utf-8"))
    leads = {}
    for k in ("1", "2", "3"):
        v, m = ev["leads"][k], ev["leads"][k]["metrics"]
        leads[k] = {"rows": m["n"], "quarters": v["n_quarters"], "reliable": v["reliable"],
                    **{x: round(m[x], 2) for x in ("accuracy", "precision", "recall", "f1", "auc")},
                    "brier": round(m["brier"], 3), "always_low": round(v["baseline_accuracy"]["ALWAYS-LOW"], 2)}
    D = pd.read_csv(EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    v1 = pd.read_csv(EXP / "FINAL_VERIFICATION" / "out" / "horizon_predictions_lead1.csv", dtype={"province_code": str})
    g = D[D["lead"] == 1].merge(v1[["t", "lead", "province_code"] + list(K.COMP.values())],
                                on=["t", "lead", "province_code"])
    y = g["y"].astype(int).to_numpy()
    rows = {"LightGBM (served, P0H4)": {"brier": round(float(np.mean((g["P0H4_p3"] - y) ** 2)), 3)}}
    raw = {}
    for name, col in COMPARATORS.items():
        t = FM.boot_diff(g, (g["P0H4_p3"] - y) ** 2, (g[col] - y) ** 2)
        rows[name] = {"brier": round(float(np.mean((g[col] - y) ** 2)), 3), "p0h4_minus": round(t["diff"], 3),
                      "p_two": t["p_two"]}
        raw[name] = t["p_two"]
    run = 0.0
    for i, (name, p) in enumerate(sorted(raw.items(), key=lambda kv: kv[1])):
        run = max(run, min(1.0, (len(raw) - i) * p))
        rows[name]["holm_p"] = round(run, 3)
        rows[name]["established"] = run < 0.05
    S = U.stack(RL._K())
    s = S[(S["t"] == L.qi("2026-Q3")) & (S["lead"] == 1)]
    avail = {c: bool(s[c].notna().any()) for c in ("A3", "C2", "C3", "C4", "E1", "E2", "N1", "G_pri_yoy")}
    r = pd.read_csv(ROOT / "backend" / "data" / "ch1_engine" / "rows.csv", dtype=str)
    r = r[r["issue_date"] == "2026-10-01"].iloc[0]
    out = {"leads": leads, "lead1_brier": {"rows": int(len(g)), "quarters": int(g["q"].nunique()), "models": rows},
           "issue_2026_10_01": {"psa_cpi_through": r["psa_newest_month"], "sws_latest": r["sws_newest_q"],
                                "sws_latest_value": float(r["h_last"]), "news_latest": r["news_latest_published"],
                                "quarterly_inputs_quarter": "2026-Q2 (t-1)", "typhoon_quarter": "2026-Q3 (t)",
                                "available_at_issue": avail},
           "seal": ev["seal_sha256"][:8]}
    FM.write_json(OUT / "landing_figures.json", out)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
