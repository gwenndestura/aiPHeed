r"""Local dashboard PREVIEW of FINAL (RATE + MIND). Not served, not registered, not deployed.
Builds FINAL's live CALABARZON forecasts for issue 2026-Q4 with exactly the H_cw branch's as-of input rows (app.hcw.serve._rows,
unchanged) and FINAL's project engine (app.hcw.final_engine.fit_predict, reproduces the research FINAL to 1e-9), five seeds,
Leads 1-5 (the leads passing the owner gate on FINAL's walk-forward evaluation: accuracy >= 75 % and Brier better than persistence;
robust rule: Lead 4). Writes ONLY to this folder's out/ (live.json, dashboard_rows.csv, lead_horizon.json, thesis_metrics.json).
Run from C:\Users\admin\aipheed_hcw\backend with PYTHONPATH=. :  python build_final_live.py"""
import json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed

HERE = Path(__file__).resolve().parents[1]
RN = HERE.parent
PREV = HERE / "out"
LEADS = (1, 2, 3, 4, 5)
SEEDS = (168, 1, 2, 3, 4)
MODEL = "final-rate-mind-1.0-experimental"


def _one(lead, seed):
    from app.hcw import serve as SV
    from app.hcw import final_engine as FE
    SV.OUT = PREV                                   # cand_panel.parquet is read from here (a byte copy of the branch's panel)
    tr, te, AN, issue = SV._rows(lead, "2026-Q4")
    r = FE.fit_predict(tr, te, AN, seed)
    contrib, cols = r["model"].contributions(r["te"])
    return {"lead": lead, "seed": seed, "issue": issue, "province": te["province"].tolist(), "mu": r["mu"], "p": r["p"], "half": r["half"],
            "cfg": r["cfg"], "contrib": contrib, "cols": cols, "X": r["te"]}


def main():
    from app.hcw import engine as H
    from app.hcw import serve as SV
    from app.e151 import prov as Pv
    from app.fi5.target import qlabel
    PREV.mkdir(exist_ok=True)
    src = SV.OUT / "cand_panel.parquet"
    shutil.copy2(src, PREV / "cand_panel.parquet")
    cut_info = SV.check_cutoff("2026-Q4")
    R = Parallel(n_jobs=len(LEADS) * len(SEEDS))(delayed(_one)(l, s) for l in LEADS for s in SEEDS)
    news = set(Pv.NEWS_ALL)
    grp_of = lambda c: H.group_of(c[3:] if c.startswith("mi_") else c)     # MIND flags count with their input's group
    rows, prov = [], []
    for lead in LEADS:
        rs = [r for r in R if r["lead"] == lead]
        p, mu, half = (np.mean([r[k] for r in rs], axis=0) for k in ("p", "mu", "half"))
        for k, name in enumerate(rs[0]["province"]):
            g = {v: 0.0 for v in SV.BARS.values()}; gn = dict(g); other = pov = change = 0.0
            for r in rs:
                for j, c in enumerate(r["cols"]):
                    grp, v = grp_of(c), r["contrib"][k][j] / len(rs)
                    if grp in SV.BARS:
                        g[SV.BARS[grp]] += v; gn[SV.BARS[grp]] += v if c in news else 0.0
                    elif grp == "poverty":
                        pov += v
                    else:
                        other += v
                change += float(r["contrib"][k].sum()) / len(rs)
            X, tq = rs[0]["X"], qlabel(rs[0]["issue"] + lead)
            o = {"province_code": SV.CODES[name], "province": name, "quarter": tq, "lead": lead, "issue_date": SV._cutoff("2026-Q4"),
                 "probability": round(float(p[k]), 3), "class": "HIGH" if p[k] >= .5 else "LOW", "score_pct": round(float(SV.pct(mu[k])), 1),
                 "range90_low": round(float(SV.pct(mu[k] - half[k])), 1), "range90_high": round(float(SV.pct(mu[k] + half[k])), 1),
                 "config": " || ".join(r["cfg"] for r in rs), "baseline_pct": round(float(SV.pct(mu[k] - change)), 2), "change_logit": round(change, 6),
                 "shap_other": round(other, 6), "shap_poverty": round(pov, 6), "model": H.MODEL_ID}
            for v in SV.BARS.values():
                o[f"shap_{v}"], o[f"shap_news_{v}"] = round(g[v], 6), round(gn[v], 6)
            for c in SV.VALUES:
                o[f"val_{c}"] = None if c not in X or pd.isna(X.at[k, c]) else float(X.at[k, c])
            rows.append(o)
            prov.append({"province": name, "lead": lead, "target_quarter": tq, "score_pct": o["score_pct"], "range90_pct": [o["range90_low"], o["range90_high"]],
                         "p_high": o["probability"], "risk_class": o["class"], "config": o["config"]})
    # FINAL's own walk-forward evaluation (research_notes: completion audit B1/B3, stability study LEAD_baselines_paired)
    B1 = pd.read_csv(RN / "aiPHeed_completion_audit_20261113/evidence/B1_five_metrics_by_model_lead.csv")
    B3 = {r["lead"]: r for r in json.load(open(RN / "aiPHeed_completion_audit_20261113/evidence/B3_robust_rule_max_lead.json"))["by_lead"]}
    PP = pd.read_csv(RN / "aiPHeed_final_stability_lead_20261113/evidence/LEAD_baselines_paired.csv")
    leads, tm, acc = {}, {}, {}
    for L in range(1, 9):
        f = B1[(B1.model == "FINAL") & (B1.lead == L)].iloc[0]
        pers = B1[(B1.model == "PERS") & (B1.lead == L)].iloc[0]
        pp = PP[(PP.lead == L) & (PP.baseline == "PERS")].iloc[0]
        ci = json.loads(pp.ci95)
        fa = eval(f.fold_accuracy) if isinstance(f.fold_accuracy, str) else f.fold_accuracy
        leads[str(L)] = {"rows": int(f.n), "correct": int(f.TP + f.TN), "accuracy": round(float(f.accuracy), 3), "mean_fold_accuracy": round(float(f.mean_fold_accuracy), 3),
                         "high_recall": float(f.recall), "low_recall": round(float(f.TN / (f.TN + f.FP)), 3), "precision": float(f.precision), "brier": float(f.brier),
                         "persistence_accuracy": round(float(pers.accuracy), 3), "brier_minus_persistence": float(pp.brier_FINAL_minus_baseline),
                         "brier_minus_persistence_ci95": ci, "beats_persistence_C2": bool(ci[1] < 0), "rounds": int(len(fa)),
                         "worst_seed_mean_fold_accuracy": B3[L]["worst_seed"]}
        tm[str(L)] = {"n_high": int(f.HIGH), "folds": {f"ENNS{k}": v for k, v in fa.items()},
                      "HCW": {"precision_high": float(f.precision), "recall_high": float(f.recall), "f1_high": float(f.f1), "auc_roc": float(f.auc)}}
        acc[L] = {"accuracy": leads[str(L)]["accuracy"], "mean_fold_accuracy": leads[str(L)]["mean_fold_accuracy"], "high_recall": leads[str(L)]["high_recall"],
                  "low_recall": leads[str(L)]["low_recall"], "persistence_accuracy": leads[str(L)]["persistence_accuracy"], "beats_persistence": leads[str(L)]["beats_persistence_C2"]}
    (PREV / "lead_horizon.json").write_text(json.dumps({"model": H.MODEL_ID, "display_model": MODEL, "leads": leads, "horizon_75pct_and_beats_persistence": max(LEADS),
                                                        "thesis_rule_max_lead": 5, "robust_max_lead": 4, "skill_horizon_beats_persistence": 8,
                                                        "basis": "FINAL walk-forward, 5-seed average, 72 province-rounds (retrospective)"}, indent=1), newline="\n")
    (PREV / "thesis_metrics.json").write_text(json.dumps(tm, indent=1), newline="\n")
    doc = {"model": H.MODEL_ID, "display_model": MODEL, "name": "FINAL (RATE + MIND) LightGBM: LOCAL PREVIEW, not validated for deployment",
           "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "issue_quarter": "2026-Q4",
           "information_cutoff": cut_info["information_cutoff"], "news_window": cut_info["news_window"], "cutoff_check": cut_info,
           "target": "HFIAS moderate+severe household food insecurity, HIGH at 50 %", "provinces": prov, "accuracy_by_lead": acc,
           "acceptance_basis": "owner gate on FINAL's walk-forward evaluation (accuracy >= 75 % and Brier better than persistence): Leads 1-5; robust rule: Lead 4",
           "served_leads": list(LEADS), "seeds": list(SEEDS), "seals": {"ENNS2022": "71ebe142 (FINAL rows also in 4ad9267f)"},
           "statistical_reliability": "Retrospective on 72 reused province-rounds; 2021 HIGH recall 1 of 4; not independently validated. PREVIEW ONLY."}
    (PREV / "live.json").write_text(json.dumps(doc, indent=1), newline="\n")
    D = pd.DataFrame(rows)
    D.to_csv(PREV / "dashboard_rows.csv", index=False, lineterminator="\n")
    print(D[["province", "lead", "quarter", "probability", "class", "score_pct", "baseline_pct"] + [f"shap_{b}" for b in SV.BARS.values()] + ["shap_poverty", "shap_other"]].to_string())


if __name__ == "__main__":
    main()
