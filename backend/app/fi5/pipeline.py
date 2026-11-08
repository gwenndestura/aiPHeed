"""FI5 command line. Run from backend/:

    python -m app.fi5.pipeline acquire     # copy/fetch raw public data -> data/fi5/raw (+ MANIFEST.csv)
    python -m app.fi5.pipeline nlp         # XLM-R scoring (cached), BERTopic, FSSI -> data/fi5/nlp
    python -m app.fi5.pipeline lock        # write METHOD_LOCK.json (protocol + code hashes) before evaluating
    python -m app.fi5.pipeline evaluate    # walk-forward evaluation, baselines, audits -> data/fi5/out
    python -m app.fi5.pipeline issue       # final models, live forecasts, SHAP sentences, 142-LGU rankings, seal
    python -m app.fi5.pipeline verify      # independent recomputation of metrics and rankings
    python -m app.fi5.pipeline all         # everything above in order

The API only reads data/fi5/out; nothing is retrained on a dashboard refresh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.fi5 import VERSION
from app.fi5 import evaluate as E
from app.fi5 import explain as X
from app.fi5 import rankings as R
from app.fi5.features import ALL, FeatureBuilder
from app.fi5.models import LGBM_COMMON, LGBM_CONFIGS, LOGIT_C, Model
from app.fi5.nlp import FSSI, PROVINCES
from app.fi5.paths import BACKEND_DIR, MODELS, OUT
from app.fi5.sources import REG, acquire
from app.fi5.target import labels, q_end, qindex, qlabel

CODE_FILES = ["__init__.py", "sources.py", "target.py", "nlp.py", "features.py", "models.py", "evaluate.py",
              "rankings.py", "explain.py", "pipeline.py"]
LOCK = OUT / "METHOD_LOCK.json"


def _code_hash() -> dict:
    d = BACKEND_DIR / "app" / "fi5"
    # LF-normalised so the hash does not depend on git's line-ending conversion
    return {f: hashlib.sha256((d / f).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for f in CODE_FILES}


def lock() -> dict:
    body = {"version": VERSION, "written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "target": "SWS involuntary hunger, Balance Luzon; HIGH = above the mean of the preceding 20 quarters "
                      "(>= 8 readings); quarters without a round unlabeled",
            "issue_rule": "last day of issue quarter; features with available_from <= issue date",
            "leads": E.LEADS, "eval_targets": f"{E.EVAL_FIRST_TARGET}..latest", "eras": E.ERAS,
            "reliability": E.RELIABILITY, "models": {k: list(v) if v else None for k, v in E.SPECS.items()},
            "lgbm_configs": LGBM_CONFIGS, "lgbm_common": LGBM_COMMON, "logit_C": LOGIT_C,
            "features": ALL, "code_sha256": _code_hash(),
            "note": "Pre-2021 and 2021-2026 SWS quarters were seen by earlier aiPHeed experiments (E114, v12x, v13); "
                    "they are development evidence for this design. Only quarters after 2026-Q3 are untouched."}
    body["lock_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    LOCK.write_text(json.dumps(body, indent=1, default=str))
    return body


def evaluate() -> dict:
    res = E.run()
    lk = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    res["lock"] = {"lock_sha256": lk.get("lock_sha256"), "code_matches_lock": lk.get("code_sha256") == _code_hash()}
    (OUT / "evaluation.json").write_text(json.dumps(res, indent=1, default=str))
    return res


def _issue_quarter(today: pd.Timestamp | None = None) -> int:
    today = today or pd.Timestamp.now().normalize()
    qi = today.year * 4 + (today.month - 1) // 3
    return qi - 1 if q_end(qi) > today else qi


def issue(issue_qi: int | None = None) -> dict:
    issue_qi = issue_qi if issue_qi is not None else _issue_quarter()
    d = q_end(issue_qi)
    lab = labels()
    fb = FeatureBuilder()
    ev = json.loads((OUT / "evaluation.json").read_text()) if (OUT / "evaluation.json").exists() else {}
    forecasts, importance = [], []
    for lead in E.LEADS:
        Xd = E.design(lead, fb, lab)
        L = Xd[Xd["y"].notna()]
        tr = L[L["target_published"] <= d]
        m = Model("lgbm", E.feature_list("full")).fit(tr, tr["y"].to_numpy(int))
        live = pd.DataFrame([fb.row(issue_qi, issue_qi + lead)])
        for c in ALL:
            if c not in live:
                live[c] = np.nan
        p = float(m.predict_proba(live)[0])
        sv_live = X.shap_values(m.est, live[m.cols])[0]
        sv_tr = X.shap_values(m.est, tr[m.cols])
        blocks = X.by_block(m.cols, sv_live)
        imp = X.global_importance(m.cols, sv_tr).assign(lead=lead)
        importance.append(imp)
        m.est.booster_.save_model(str(MODELS / f"fi5_lead{lead}.txt"))
        pers = float(Model("persistence").predict_proba(live)[0]) if pd.notna(live["hunger_last_anom"].iloc[0]) else None
        lg = Model("logit", E.feature_list("full")).fit(tr, tr["y"].to_numpy(int))
        rel = ev.get("summary", {}).get(str(lead), {}).get("reliability", {})
        tq = qlabel(issue_qi + lead)
        forecasts.append({
            "lead": lead, "issue_quarter": qlabel(issue_qi), "issue_date": d.date().isoformat(), "target_quarter": tq,
            "p_high": round(p, 4), "class": "HIGH" if p >= 0.5 else "LOW",
            "persistence_class": None if pers is None else ("HIGH" if pers >= .5 else "LOW"),
            "logistic_p_high": round(float(lg.predict_proba(live)[0]), 4),
            "latest_hunger_reading": live["hunger_last"].iloc[0], "latest_reading_quarter": live.get("last_reading_quarter", pd.Series([None])).iloc[0],
            "five_year_average": live.get("baseline_known", pd.Series([np.nan])).iloc[0],
            "observed_hunger": float(lab.set_index("quarter")["hunger"].get(tq)) if tq in set(lab["quarter"]) else None,
            "reliable_lead": bool(rel.get("reliable", False)),
            "explanation": X.sentence(blocks, tq),
            "block_contributions": {k: round(v, 4) for k, v in sorted(blocks.items(), key=lambda kv: -abs(kv[1]))},
            "top_features": [{"feature": c, "block": X.block_of(c), "value": None if pd.isna(live[c].iloc[0]) else float(live[c].iloc[0]),
                              "shap": round(float(s), 4)} for c, s in sorted(zip(m.cols, sv_live), key=lambda kv: -abs(kv[1]))[:6]],
            "model": {"config": m.choice, "n_train": int(len(tr)), "train_targets": f"{tr['target_quarter'].iloc[0]}..{tr['target_quarter'].iloc[-1]}",
                      "features_used": m.cols, "file": f"data/fi5/models/fi5_lead{lead}.txt"},
        })
    imp = pd.concat(importance, ignore_index=True)
    imp.to_csv(OUT / "shap_importance.csv", index=False, lineterminator="\n")
    dom_imp = imp.groupby(["lead", "block"])["mean_abs_shap"].sum().unstack("lead").round(4)
    dom_imp.to_csv(OUT / "shap_importance_by_block.csv", lineterminator="\n")

    # Objective 3: rankings from the lead-1 forecast; every lead's probability is carried alongside.
    p1 = forecasts[0]["p_high"]
    meta = {f"p_high_lead{f['lead']}": f["p_high"] for f in forecasts} | {"forecast_target_quarter": forecasts[0]["target_quarter"]}
    lgus = R.rank_lgus(p1, meta)
    lgus.to_csv(OUT / "lgu_rankings.csv", index=False, lineterminator="\n")
    prov = R.province_priority(lgus)
    if FSSI.exists():
        f = pd.read_csv(FSSI)
        lastq = f[f["n_articles"].fillna(0) > 0]["quarter"].max()
        fl = f[(f["quarter"] == qlabel(issue_qi))]
        prov = prov.merge(fl[["geo", "fssi_all", "n_events", "coverage_flag"]].rename(
            columns={"geo": "province_name", "fssi_all": "fssi_corrected_all", "n_events": "news_events"}),
            on="province_name", how="left")
    prov["forecast_basis"] = "regional (Balance Luzon) forecast; province figures are vulnerability-adjusted priority, not a province measurement"
    prov.to_csv(OUT / "province_priority.csv", index=False, lineterminator="\n")
    R.sensitivity(lgus).to_csv(OUT / "lgu_weight_sensitivity.csv", index=False, lineterminator="\n")

    unseen = [f for f in forecasts if f["observed_hunger"] is None]
    seal = pd.DataFrame([{k: f[k] for k in ["issue_quarter", "target_quarter", "lead", "p_high", "class", "persistence_class"]} for f in unseen])
    seal_csv = seal.to_csv(index=False, lineterminator="\n")
    (OUT / "SEAL_fi5.csv").write_text(seal_csv)
    body = {"version": VERSION, "issued_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "issue_quarter": qlabel(issue_qi), "forecasts": forecasts,
            "max_reliable_lead": ev.get("max_reliable_lead"),
            "seal_sha256": hashlib.sha256(seal_csv.encode()).hexdigest(),
            "what_is_forecast": "Probability that SWS involuntary hunger in Balance Luzon (the SWS area containing "
                                "CALABARZON) is above its five-year average in the target quarter."}
    (OUT / "forecast.json").write_text(json.dumps(body, indent=1, default=str))
    return body


def verify() -> dict:
    """Independent recomputation: metrics from the stored predictions (plain numpy) and LGU scores (pure Python)."""
    ev = json.loads((OUT / "evaluation.json").read_text())
    pr = pd.read_csv(OUT / "walkforward_predictions.csv")
    checks = {}
    for lead, g in pr.groupby("lead"):
        y = g["y"].to_numpy(int)
        for name in E.SPECS:
            p = g[name].to_numpy(float)
            acc = float(np.mean((p >= 0.5).astype(int) == y))
            brier = float(np.mean((p - y) ** 2))
            m = ev["summary"][str(lead)]["models"][name]
            checks[f"lead{lead}:{name}"] = abs(acc - m["accuracy"]) < 1e-12 and abs(brier - m["brier"]) < 1e-12
    t = pd.read_csv(OUT / "lgu_rankings.csv", dtype={"lgu_psgc": str})

    def pct_rank(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        ranks = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            for k in range(i, j + 1):
                ranks[order[k]] = ((i + 1) + (j + 1)) / 2 / len(vals)
            i = j + 1
        return ranks

    pov, den = t["poverty_incidence_2021"].tolist(), (t["population_2024"] / t["land_area_km2"]).tolist()
    rp, rd = pct_rank(pov), pct_rank(den)
    score = [100 * t["p_high_region"].iloc[0] * (0.5 * a + 0.5 * b) for a, b in zip(rp, rd)]
    max_diff = max(abs(a - b) for a, b in zip(score, t["priority_score"]))
    out = {"metrics_reproduced": all(checks.values()), "n_metric_checks": len(checks),
           "lgu_count": int(len(t)), "lgu_unique": int(t["lgu_psgc"].nunique()),
           "lgu_missing_poverty": int(t["poverty_incidence_2021"].isna().sum()),
           "lgu_score_max_abs_diff": float(max_diff), "lgu_scores_reproduced": bool(max_diff < 1e-9),
           "provinces": t["province_name"].value_counts().to_dict()}
    src = "\n".join((BACKEND_DIR / "app" / "fi5" / f).read_text(encoding="utf-8") for f in CODE_FILES)
    import re
    out["no_firi_dependency"] = not re.search(r"^\s*(from|import)\s+\S*fir" + "i", src.lower(), re.M)
    (OUT / "verification.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["acquire", "nlp", "lock", "evaluate", "issue", "verify", "all"])
    ap.add_argument("--issue-quarter", default=None)
    a = ap.parse_args(argv)
    iq = qindex(a.issue_quarter) if a.issue_quarter else None
    steps = ["acquire", "nlp", "lock", "evaluate", "issue", "verify"] if a.cmd == "all" else [a.cmd]
    for s in steps:
        if s == "acquire":
            print(acquire().to_string())
        elif s == "nlp":
            from app.fi5 import nlp
            print(json.dumps(nlp.run(skip_scoring=False), indent=1, default=str))
        elif s == "lock":
            print(lock()["lock_sha256"])
        elif s == "evaluate":
            r = evaluate()
            print("max reliable lead:", r["max_reliable_lead"])
        elif s == "issue":
            print(json.dumps(issue(iq), indent=1, default=str)[:4000])
        elif s == "verify":
            print(json.dumps(verify(), indent=1))


if __name__ == "__main__":
    sys.exit(main())
