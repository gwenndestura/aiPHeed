"""
E184 deployment (docs/e184/PROTOCOL.md): E168 + synthetic training data balanced 50/50, in E168's artifact schema.

    python -m app.e184.serve stage                          live forecasts for the production issue (Leads 1-3, SHAP
                                                            groups, missing-input flags) -> data/e184/issues/<folder>/;
                                                            registered in the registry as a CANDIDATE (production unchanged)
    python -m app.e184.serve promote --approver "<name>"    OWNER ONLY: E184 becomes the production model
    python -m app.e184.serve rollback --approver "<name>"   OWNER ONLY: E168's registered issue becomes production again
    python -m app.e184.serve status

stage refuses unless data/e184/out/results.json says the owner's deployment rule holds. After promote or rollback,
restart the backend so every cached page uses the new production model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.e178 import common as K

warnings.filterwarnings("ignore")
E184_ID = "e184-lgbm-syn50-1.0"
E168_ID = "e168-lgbm-1.0"
ROOT = K.D / "e184"
ISSUES = ROOT / "issues"
OUT = ROOT / "out"
NAME = "E184 LightGBM (E168 + synthetic training data balanced 50/50 with the real survey rows)"
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))
logit = lambda s: np.log(np.asarray(s, float) / (100 - np.asarray(s, float)))


def _sha(p) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _lead(lead: int, issue: str) -> pd.DataFrame:
    """One lead of the live forecast: the frozen E168 frames (serve._forecast, E183 filling included), E168's selection,
    the 50/50 synthetic rows, mean over five seeds; dashboard rows as app.e168.dashboard_export._lead."""
    from app.e163 import model as C163
    from app.e168 import dashboard_export as X
    from app.e168 import lgbm_only as E
    from app.e168 import robust as RB
    from app.e168 import serve as SV
    from app.e178 import retrain as RT
    from app.e179 import tuned as T
    from app.e182 import candidate as C182
    from app.e184 import candidate as C
    from app.fi5.target import qindex, qlabel
    cap = {}
    orig_fill = RB.fill_unseen_missing

    def fill(tr, te, cols=None):
        out = orig_fill(tr, te, cols)
        cap["filled"] = out[1]
        return out

    def stop(tr, te, AN, ablate=False):
        raise RT._Captured(tr, te, AN)

    with K.sun_standin(), K.patched(RB, "fill_unseen_missing", fill), K.patched(E, "run_proc", stop):
        try:
            SV._forecast(lead, issue)
            raise RuntimeError("serve._forecast did not reach run_proc")
        except RT._Captured as c_:
            tr, te, AN = c_.args
    te = te.reset_index(drop=True)
    r = C182.fixed(tr, te, AN, T.SEEDS, f"LIVE|{issue}|L{lead}", setting=C.SETTING, contrib=True)
    mu, p, half = r[C182.NAME]
    contrib, cols = r["contrib"], r["contrib_cols"]
    tag = f"{r['cfg']}|cal={'/'.join(r['cal_seeds'])}|aug={T.setting_name(C.SETTING)}|seeds=17901-17905"
    used = RB.used_by(tag, cap.get("filled", [[] for _ in range(len(te))]))
    news = set(E.NEWS)
    grp = [X.OWN_BAR.get(c) or (X.GROUPS.get(C163.gmap(c)) if C163.gmap(c) else None) for c in cols]
    out = []
    for k in range(len(te)):
        g, gn, other = {b: 0.0 for b in X.BARS}, {b: 0.0 for b in X.BARS}, 0.0
        for i, c in enumerate(cols):
            if grp[i] is None:
                other += contrib[k][i]
            else:
                g[grp[i]] += contrib[k][i]
                if c in news:
                    gn[grp[i]] += contrib[k][i]
        change = float(contrib[k].sum())
        score = round(float(pct(mu[k])), 1)
        o = {"province_code": X.CODES[te["province"].iloc[k]], "province": te["province"].iloc[k], "quarter": qlabel(qindex(issue) + lead),
             "lead": lead, "issue_date": X._cutoff(issue), "probability": round(float(p[k]), 3), "class": "HIGH" if p[k] >= .5 else "LOW",
             "score_pct": score, "range90_low": round(float(pct(mu[k] - half[k])), 1), "range90_high": round(float(pct(mu[k] + half[k])), 1),
             "config": tag, "baseline_pct": round(float(pct(logit(score) - change)), 2), "change_logit": round(change, 6),
             "bias_logit": round(float(contrib[k][-1]), 6), "shap_other": round(float(other), 6), "model": E184_ID,
             "inputs_filled": len(used[k]), "inputs_filled_names": ";".join(used[k]), "data_complete": not used[k]}
        for b in X.BARS:
            o[f"shap_{b}"], o[f"shap_news_{b}"] = round(g[b], 6), round(gn[b], 6)
        for c in X.VALUES:
            o[f"val_{c}"] = None if c not in te or pd.isna(te.at[k, c]) else float(te.at[k, c])
        out.append(o)
    return pd.DataFrame(out)


def _horizon(res: dict) -> dict:
    """data/e184/out/lead_horizon.json in E168's schema (what the dashboard adapter reads for the served model)."""
    leads, ok = {}, []
    for k, v in res["served_leads"].items():
        m, pm = v["metrics"]["E184"], v["metrics"]["PERS"]
        c = m["confusion"]
        beats = v["brier_minus_persistence"]["ci95"][1] < 0
        leads[str(k)] = {"rows": c["tp"] + c["fp"] + c["fn"] + c["tn"], "correct": c["tp"] + c["tn"], "accuracy": m["accuracy"],
                         "high_recall": m["high_recall"], "low_recall": m["low_recall"], "precision": m["high_precision"], "brier": m["brier"],
                         "persistence_accuracy": pm["accuracy"], "brier_minus_persistence": v["brier_minus_persistence"]["diff"],
                         "brier_minus_persistence_ci95": v["brier_minus_persistence"]["ci95"], "beats_persistence_C2": beats}
        ok.append(m["accuracy"] >= 0.75 and beats)
    rl = 0
    for good in ok:
        if not good:
            break
        rl += 1
    return {"model": E184_ID, "threshold_accuracy": 0.75, "leads": leads, "skill_horizon_beats_persistence": rl,
            "horizon_75pct_and_beats_persistence": rl, "maximum_reliable_lead_E156": None}


def stage() -> dict:
    prod = K.production_issue()
    if prod["model_id"] not in (E168_ID, E184_ID):
        raise SystemExit(f"production model is {prod['model_id']}; E184 stages against an E168 production issue")
    if not K.at_production_cutoff(prod):
        sys.exit(K.rerun_at_cutoff("app.e184.serve", ["stage"], prod))
    from joblib import Parallel, delayed
    from app import registry as R
    from app.e168 import regenerate as RG
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    if not res.get("deployable"):
        raise SystemExit(f"E184 does not meet the owner's deployment rule: {res.get('deployment_rule')}; nothing staged")
    seal = OUT / "sealed_enns2022.json"
    if not seal.exists():
        raise SystemExit("E184's ENNS 2022 forecasts are not sealed yet (python -m app.e184.candidate seal)")
    issue, folder = prod["issue"], prod["folder"]
    final = ISSUES / folder
    if (final / "live.json").exists():
        return {"status": "exists", "path": str(final)}
    dash = pd.concat(Parallel(n_jobs=3)(delayed(_lead)(l, issue) for l in (1, 2, 3)), ignore_index=True)
    H = _horizon(res)
    K.dump_json(H, OUT / "lead_horizon.json")
    acc = {int(k): {"accuracy": v["accuracy"], "high_recall": v["high_recall"], "persistence_accuracy": v["persistence_accuracy"],
                    "beats_persistence": v["beats_persistence_C2"]} for k, v in H["leads"].items()}
    rows = [{"province": r["province"], "lead": int(r["lead"]), "target_quarter": r["quarter"], "score_pct": float(r["score_pct"]),
             "range90_pct": [float(r["range90_low"]), float(r["range90_high"])], "p_high": float(r["probability"]), "risk_class": r["class"],
             "config": r["config"], "inputs_filled": int(r["inputs_filled"]), "data_complete": bool(r["data_complete"])} for _, r in dash.iterrows()]
    with K.patched(RG, "MODEL_ID", E184_ID):
        RG.validate(issue, rows, dash)
    live = prod["live"]
    doc = {"model": E184_ID, "name": NAME, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "issue_quarter": issue,
           "information_cutoff": live.get("information_cutoff"), "data_published_by": live.get("data_published_by"),
           "target": "HFIAS moderate+severe household food insecurity, HIGH at 50 %", "provinces": rows, "accuracy_by_lead": acc,
           "acceptance_basis": "owner-defined (2026-11-07): accuracy >= 75 % and significantly better than reusing the latest survey (Brier CI < 0) at each served lead",
           "served_leads": [l for l in (1, 2, 3) if acc[l]["accuracy"] >= 0.75 and acc[l]["beats_persistence"]],
           "statistical_reliability": ("Validated on the same 72 provincial forecasts from 3 survey rounds as E168; not better than E168 on the "
                                       "strict pre-registered rule (docs/e184/REPORT.md). Synthetic rows are training data only."),
           "synthetic_training": {"ratio_synthetic_to_real": 1.0, "weight": 1.0, "generator": "jitter 0.5 SD, boundary focus, classes balanced",
                                  "seeds": [17901, 17902, 17903, 17904, 17905], "never_used_for_testing": True},
           "seals": {"ENNS2022": _sha(seal)[:8]}}
    tmp = ISSUES / f".{folder}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    (tmp / "live.json").write_text(json.dumps(doc, indent=1), newline="\n")
    dash.to_csv(tmp / "dashboard_rows.csv", index=False, lineterminator="\n")
    news = prod["artifact"].parent / "news_used.json"
    if news.exists():                                                    # same issue and cut-off: the same stories were read
        shutil.copy2(news, tmp / "news_used.json")
    man = {"issue": issue, "folder": folder, "model": E184_ID, "status": "staged", "information_cutoff": doc["information_cutoff"],
           "created_utc": doc["created_utc"], "inputs_sha256": prod["inputs_sha256"], "live_sha256": _sha(tmp / "live.json"),
           "e168_issue_it_replaces": prod["folder"] if prod["model_id"] == E168_ID else None,
           "promote": 'python -m app.e184.serve promote --approver "<name>"', "rollback": 'python -m app.e184.serve rollback --approver "<name>"'}
    (tmp / "manifest.json").write_text(json.dumps(man, indent=1), newline="\n")
    os.replace(tmp, final)
    art = str((final / "live.json").relative_to(K.BACKEND_DIR)).replace("\\", "/")
    sha = R.file_sha256(final / "live.json")
    R.register(E184_ID, {"version": f"E184 (E168 + synthetic 50/50), issue {folder}", "artifact_path": art, "artifact_sha256": sha,
                         "target": "HFIAS moderate+severe household food insecurity by province; HIGH at 50 %",
                         "note": "Candidate staged by app.e184.serve; promote only by the owner (docs/e184/PROTOCOL.md)."}, "candidate")
    rule = res["deployment_rule"]
    gate = {"model_id": E184_ID, "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "passed": all(rule.values()),
            "rule": "owner production rule (accuracy >= 75 % and Brier CI vs persistence < 0 at each served lead) + leakage < 1e-9",
            "checks": [{"id": k, "name": k, "status": "pass" if v else "fail", "critical": True} for k, v in rule.items()],
            "artifact_file_sha256": sha, "results_sha256": _sha(OUT / "results.json"),
            "decision": "eligible for promotion by the owner" if all(rule.values()) else "not eligible"}
    R.record_gate(E184_ID, gate)
    return {"status": "staged", "path": str(final), "registered": E184_ID, "gate_passed": gate["passed"], "artifact_sha256": sha}


def promote(approver: str) -> dict:
    from app import registry as R
    if not approver.strip():
        raise SystemExit("--approver is required")
    m = R.load()["models"].get(E184_ID)
    if not m:
        raise SystemExit("E184 is not staged (python -m app.e184.serve stage)")
    man = json.loads((K.BACKEND_DIR / m["artifact_path"]).with_name("manifest.json").read_text())
    if _sha(K.BACKEND_DIR / m["artifact_path"]) != man["live_sha256"]:
        raise SystemExit("the staged E184 artifact changed after staging; refusing")
    rec = R.promote(E184_ID, approver)
    return {"status": "promoted", "production": E184_ID, "approver": approver, "approved_utc": rec["approved_utc"],
            "next": "restart the backend so every page uses E184"}


def rollback(approver: str) -> dict:
    from app import registry as R
    if not approver.strip():
        raise SystemExit("--approver is required")
    rec = R.promote(E168_ID, approver)
    return {"status": "rolled back", "production": E168_ID, "artifact": rec["artifact_path"], "approver": approver,
            "next": "restart the backend so every page uses E168"}


def status() -> dict:
    from app import registry as R
    reg = R.load()
    return {"production": reg.get("production"), "e184": {k: (reg["models"].get(E184_ID) or {}).get(k) for k in ("status", "artifact_path", "version")},
            "e184_gate_passed": ((reg["models"].get(E184_ID) or {}).get("gate") or {}).get("passed")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stage", "promote", "rollback", "status"])
    ap.add_argument("--approver", default="")
    a = ap.parse_args()
    out = {"stage": stage, "status": status}.get(a.cmd)
    print(json.dumps(out() if out else (promote if a.cmd == "promote" else rollback)(a.approver), indent=1, default=str))
