"""FI6 command line (run from backend/; FI5's raw data and NLP caches must exist: python -m app.fi5.pipeline acquire nlp):

    python -m app.fi6.pipeline lock        # METHOD_LOCK.json: target, features, monotone signs, rules, code hashes
    python -m app.fi6.pipeline evaluate    # walk-forward, baselines, ablations, audits (all cores)
    python -m app.fi6.pipeline issue       # final models, live forecasts, SHAP sentences, 142-LGU rankings, seal
    python -m app.fi6.pipeline verify      # independent recomputation
    python -m app.fi6.pipeline all
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.fi5 import rankings as R
from app.fi5.explain import PHRASES, _cap, _join
from app.fi5.features import FeatureBuilder
from app.fi5.paths import BACKEND_DIR
from app.fi5.target import q_end, qindex, qlabel
from app.fi6 import VERSION
from app.fi6 import evaluate as E
from app.fi6 import models as M
from app.fi6.features import ALL, DOMAIN, MONOTONE, SETS, design, live_row
from app.fi6.paths import MODELS, OUT
from app.fi6.target import candidates, labels

FILES = {"fi6": ["__init__.py", "target.py", "features.py", "models.py", "evaluate.py", "pipeline.py"],
         "fi5": ["sources.py", "target.py", "nlp.py", "features.py", "models.py", "rankings.py"]}
LOCK = OUT / "METHOD_LOCK.json"
MIN_EFFECT_PP = 0.3       # SHAP contributions smaller than 0.3 percentage points are not mentioned


def _code_hash() -> dict:
    return {f"{p}/{f}": hashlib.sha256((BACKEND_DIR / "app" / p / f).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for p, fs in FILES.items() for f in fs}


def lock() -> dict:
    body = {"version": VERSION, "written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "target": "HIGH = SWS Balance Luzon hunger above the mean of the preceding 20 quarters (>= 8 readings) by more "
                      "than the round's published 95% margin of error; unobserved quarters unlabeled",
            "target_choice_basis": candidates().to_dict("records"),
            "proposed_model": "LightGBM regression of change in hunger from the latest published reading, monotone constraints, "
                              "config and sigma from expanding inner folds; P(HIGH)=1-Phi((threshold_known-level_hat)/sigma); class at 0.5",
            "features": ALL, "monotone": MONOTONE, "domains": DOMAIN, "feature_sets": SETS,
            "leads": E.LEADS, "eval_first_target": E.EVAL_FIRST_TARGET, "eras": E.ERAS, "reliability": E.RELIABILITY,
            "models": {k: list(v) for k, v in E.SPECS.items()}, "code_sha256": _code_hash(),
            "note": "All SWS quarters 1998-2026-Q3 have been seen by earlier aiPHeed work (FI5, E114, v12x, v13); this is "
                    "development evidence. The FI6 target, features and model were fixed from label-reliability statistics "
                    "and a-priori reasoning, not from FI6 model results. Untouched test = SWS quarters after 2026-Q3."}
    body["lock_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    LOCK.write_text(json.dumps(body, indent=1, default=str))
    return body


def evaluate() -> dict:
    res = E.run()
    lk = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    res["lock"] = {"lock_sha256": lk.get("lock_sha256"), "code_matches_lock": lk.get("code_sha256") == _code_hash()}
    (OUT / "evaluation.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def sentence(blocks: dict[str, float], tq: str) -> str:
    up = [b for b, v in sorted(blocks.items(), key=lambda kv: -kv[1]) if v >= MIN_EFFECT_PP][:2]
    down = [b for b, v in sorted(blocks.items(), key=lambda kv: kv[1]) if v <= -MIN_EFFECT_PP][:2]
    up_w, down_w = [PHRASES[b]["up"] for b in up], [PHRASES[b]["down"] for b in down]
    what = f"the hunger forecast for {tq}"
    if up_w and down_w:
        s = f"{_cap(_join(up_w))} pushed {what} up, while {_join(down_w)} pulled it down."
    elif up_w:
        s = f"{_cap(_join(up_w))} pushed {what} up."
    elif down_w:
        s = f"{_cap(_join(down_w))} pulled {what} down."
    else:
        s = f"No single factor stood out for {tq}; the forecast stays close to the latest survey reading."
    return s + " These are the factors the model leaned on, not proven causes."


def reliability_all(ev: dict) -> dict:
    """The pre-declared reliability rule applied to every model and lead (Objective 4), and each model's furthest
    reliable lead."""
    tab = {name: {L: E.reliability(s["models"][name]) for L, s in ev["summary"].items()} for name in E.SPECS}
    furthest = {}
    for name, per in tab.items():
        best = None
        for L in sorted(per, key=int):
            if per[L]["reliable"]:
                best = int(L)
            else:
                break
        furthest[name] = best
    return {"by_model": tab, "furthest_reliable_lead": furthest}


def issue(issue_qi: int) -> dict:
    import shap
    d = q_end(issue_qi)
    lab = labels()
    fb = FeatureBuilder()
    ev = json.loads((OUT / "evaluation.json").read_text()) if (OUT / "evaluation.json").exists() else {}
    rel_all = reliability_all(ev) if ev else {"by_model": {}, "furthest_reliable_lead": {}}
    (OUT / "reliability_all_models.json").write_text(json.dumps(rel_all, indent=1))
    out, imps = [], []
    for lead in E.LEADS:
        X = design(lead, fb, lab)
        L = X[X["y"].notna()]
        tr = L[L["target_published"] <= d]
        m = M.DeltaModel(SETS["full"]).fit(tr, tr["delta_target"].to_numpy(float))
        live = live_row(issue_qi, lead, fb)
        p = float(m.predict_proba(live)[0])
        dh = float(m.predict_delta(live)[0])
        ex = shap.TreeExplainer(m.est)
        sv = np.asarray(ex.shap_values(live[m.cols]))[0]
        blocks: dict[str, float] = {}
        for c, s in zip(m.cols, sv):
            blocks[DOMAIN[c]] = blocks.get(DOMAIN[c], 0.0) + float(s)
        svt = np.abs(np.asarray(ex.shap_values(tr[m.cols])))
        imps.append(pd.DataFrame({"lead": lead, "feature": m.cols, "domain": [DOMAIN[c] for c in m.cols],
                                  "mean_abs_shap_pp": svt.mean(axis=0)}))
        m.est.booster_.save_model(str(MODELS / f"fi6_lead{lead}.txt"))
        pers = M.Persistence().fit(tr, tr["delta_target"])
        lg = M.fit(M.make("logit", SETS["full"]), "logit", tr)
        rel = ev.get("summary", {}).get(str(lead), {}).get("reliability", {})
        tq = qlabel(issue_qi + lead)
        obs = lab.set_index("quarter")
        out.append({
            "lead": lead, "issue_quarter": qlabel(issue_qi), "issue_date": d.date().isoformat(), "target_quarter": tq,
            "p_high": round(p, 4), "class": "HIGH" if p >= .5 else "LOW",
            "forecast_hunger_pct": round(float(live["hunger_last"].iloc[0]) + dh, 2), "forecast_sigma_pp": round(m.sigma, 2),
            "threshold_pct": round(float(live["threshold_known"].iloc[0]), 2),
            "latest_hunger_pct": float(live["hunger_last"].iloc[0]), "latest_reading_quarter": live["last_reading_quarter"].iloc[0],
            "persistence_p_high": round(float(pers.predict_proba(live)[0]), 4),
            "persistence_reliable_lead": bool(rel_all["by_model"].get("Naive persistence", {}).get(str(lead), {}).get("reliable", False)),
            "persistence_explanation": (f"The latest survey reading ({float(live['hunger_last'].iloc[0]):.1f}%) is "
                                        f"{'above' if float(live['hunger_last'].iloc[0]) > float(live['threshold_known'].iloc[0]) else 'below'} "
                                        f"the significantly-above-normal line ({float(live['threshold_known'].iloc[0]):.1f}%), so the simple "
                                        f"forecast is {'HIGH' if float(live['hunger_last'].iloc[0]) > float(live['threshold_known'].iloc[0]) else 'LOW'}."),
            "logistic_p_high": round(float(lg.predict_proba(live)[0]), 4),
            "observed_hunger_pct": float(obs.loc[tq, "hunger"]) if tq in obs.index else None,
            "reliable_lead": bool(rel.get("reliable", False)),
            "explanation": sentence(blocks, tq),
            "domain_contributions_pp": {k: round(v, 3) for k, v in sorted(blocks.items(), key=lambda kv: -abs(kv[1]))},
            "model": {"config": m.choice, "n_train": int(len(tr)), "features_used": m.cols, "file": f"data/fi6/models/fi6_lead{lead}.txt"},
        })
    imp = pd.concat(imps)
    imp.to_csv(OUT / "shap_importance.csv", index=False, lineterminator="\n")
    imp.groupby(["domain", "lead"])["mean_abs_shap_pp"].sum().unstack("lead").round(4).to_csv(OUT / "shap_importance_by_domain.csv", lineterminator="\n")
    f1 = out[0]
    # Objective 3 uses a *validated* regional forecast: the lead-1 method that passed the pre-declared reliability rule.
    if f1["reliable_lead"]:
        p_rank, basis = f1["p_high"], "LightGBM (proposed), lead 1, passed the reliability rules"
    elif f1["persistence_reliable_lead"]:
        p_rank, basis = f1["persistence_p_high"], ("naive persistence, lead 1: the only method that passed the reliability "
                                                   "rules; LightGBM did not")
    else:
        p_rank, basis = f1["p_high"], "indicative: no method passed the reliability rules at lead 1"
    status = basis + "; the order of LGUs comes from vulnerability (every LGU shares the regional probability)"
    lgus = R.rank_lgus(p_rank, {"p_high_lgbm_lead1": f1["p_high"], "p_high_persistence_lead1": f1["persistence_p_high"]} |
                       {"forecast_target_quarter": f1["target_quarter"], "forecast_status": status})
    lgus.to_csv(OUT / "lgu_rankings.csv", index=False, lineterminator="\n")
    prov = R.province_priority(lgus)
    prov["forecast_basis"] = ("Balance Luzon (area containing all 5 provinces) forecast; no province-quarter food-insecurity "
                              "observation exists, so province figures are vulnerability-adjusted priority, not province forecasts")
    prov["forecast_status"] = status
    prov.to_csv(OUT / "province_priority.csv", index=False, lineterminator="\n")
    R.sensitivity(lgus).to_csv(OUT / "lgu_weight_sensitivity.csv", index=False, lineterminator="\n")
    unseen = [f for f in out if f["observed_hunger_pct"] is None]
    seal_csv = pd.DataFrame([{k: f[k] for k in ["issue_quarter", "target_quarter", "lead", "p_high", "class", "forecast_hunger_pct",
                                                 "threshold_pct", "persistence_p_high", "logistic_p_high"]} for f in unseen]).to_csv(index=False, lineterminator="\n")
    (OUT / "SEAL_fi6.csv").write_text(seal_csv)
    body = {"version": VERSION, "issued_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "issue_quarter": qlabel(issue_qi), "forecasts": out, "max_reliable_lead": ev.get("max_reliable_lead"),
            "furthest_reliable_lead_by_model": rel_all["furthest_reliable_lead"], "ranking_forecast_basis": basis,
            "seal_sha256": hashlib.sha256(seal_csv.encode()).hexdigest(),
            "what_is_forecast": "Probability that SWS involuntary hunger in Balance Luzon (the SWS area containing CALABARZON) "
                                "is above its five-year average by more than the survey's margin of error in the target quarter."}
    (OUT / "forecast.json").write_text(json.dumps(body, indent=1, default=str))
    return body


def verify() -> dict:
    ev = json.loads((OUT / "evaluation.json").read_text())
    pr = pd.read_csv(OUT / "walkforward_predictions.csv")
    ok = []
    for lead, g in pr.groupby("lead"):
        y = g["y"].to_numpy(int)
        for name in E.SPECS:
            p = g[name].to_numpy(float)
            m = ev["summary"][str(lead)]["models"][name]
            ok.append(abs(float(np.mean((p >= .5) == y)) - m["accuracy"]) < 1e-12 and abs(float(np.mean((p - y) ** 2)) - m["brier"]) < 1e-12)
    lab = labels().set_index("quarter")
    lab_ok = bool(((pr["target_quarter"].map(lab["y"]) == pr["y"])).all())
    t = pd.read_csv(OUT / "lgu_rankings.csv", dtype={"lgu_psgc": str})
    pov, den = t["poverty_incidence_2021"], t["population_2024"] / t["land_area_km2"]
    score = 100 * t["p_high_region"] * (0.5 * pov.rank(pct=True, method="average") + 0.5 * den.rank(pct=True, method="average"))
    src = "\n".join((BACKEND_DIR / "app" / p / f).read_text(encoding="utf-8") for p, fs in FILES.items() for f in fs)
    out = {"metrics_reproduced": all(ok), "n_metric_checks": len(ok), "labels_reproduced": lab_ok,
           "lgu_count": int(len(t)), "lgu_unique": int(t["lgu_psgc"].nunique()),
           "lgu_missing_poverty": int(t["poverty_incidence_2021"].isna().sum()),
           "lgu_scores_reproduced": bool(np.abs(score - t["priority_score"]).max() < 1e-9),
           "no_firi_dependency": not re.search(r"^\s*(from|import)\s+\S*fir" + "i", src.lower(), re.M)}
    (OUT / "verification.json").write_text(json.dumps(out, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["lock", "evaluate", "issue", "verify", "all"])
    ap.add_argument("--issue-quarter", default="2026-Q3")
    a = ap.parse_args(argv)
    for s in (["lock", "evaluate", "issue", "verify"] if a.cmd == "all" else [a.cmd]):
        if s == "lock":
            print(lock()["lock_sha256"])
        elif s == "evaluate":
            print("max reliable lead:", evaluate()["max_reliable_lead"])
        elif s == "issue":
            print(json.dumps(issue(qindex(a.issue_quarter)), indent=1, default=str)[:3000])
        else:
            print(json.dumps(verify(), indent=1))


if __name__ == "__main__":
    sys.exit(main())
