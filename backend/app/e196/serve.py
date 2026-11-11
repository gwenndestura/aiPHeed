"""
E196 local deployment, in E168's artifact schema (as app.e184.serve). Local only.

E196 live forecast for the production issue:
  E194 = mean over the top-5 Stage-A configurations x 20 synthetic draws (E184's augmentation, seeds 17901-17920).
  Lead 1 = mean of E194's Lead-1 forecast and the Lead-2 forecast for the same target issued one quarter earlier
           (issue - 1, training on outcomes released by then, past panel quarters unchanged); Leads 2-3 = E194.
  (The per-lead rule was chosen on training rows in E196: docs/e196/REPORT.md.)

    python -m app.e196.serve stage                          -> data/e196/issues/<folder>/ ; registered as CANDIDATE
    python -m app.e196.serve promote --approver "<name>"    OWNER ONLY: E196 becomes the production model (local)
    python -m app.e196.serve rollback --approver "<name>"   OWNER ONLY: E184's staged issue becomes production again
    python -m app.e196.serve status
After promote or rollback, restart the backend.
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
E196_ID = "e196-lgbm-avg5-laf-1.0"
E184_ID = "e184-lgbm-syn50-1.0"
E168_ID = "e168-lgbm-1.0"
ROOT = K.D / "e196"
ISSUES = ROOT / "issues"
OUT = ROOT / "out"
NAME = ("E196 LightGBM (E184 averaged over its 5 best configurations x 20 synthetic draws; Lead 1 also averages the "
        "previous quarter's Lead-2 forecast)")
SEEDS = tuple(range(17901, 17921))
TOPK = 5
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))
logit = lambda s: np.log(np.asarray(s, float) / (100 - np.asarray(s, float)))


def _sha(p) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _prev_issue(issue: str) -> str:
    y, q = map(int, issue.split("-Q"))
    return f"{y}-Q{q - 1}" if q > 1 else f"{y - 1}-Q4"


def _prep(lead: int, issue: str) -> dict:
    """The frozen live frames (serve._forecast up to run_proc, E183 filling included) and the top-5 configurations."""
    from sklearn.model_selection import GroupKFold
    from app.e168 import lgbm_only as E
    from app.e168 import robust as RB
    from app.e168 import serve as SV
    from app.e178 import retrain as RT
    from app.e194 import run as E194
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
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    ranked = [c for _, _, c in E194.stage_a_ranked(tr, AN, folds)[:TOPK]]
    return {"lead": lead, "issue": issue, "tr": tr, "te": te, "AN": AN, "folds": folds, "ranked": ranked,
            "filled": cap.get("filled", [[] for _ in range(len(te))])}


def _fit(prep: dict, rank: int) -> dict:
    """One configuration x 20 draws: mean (mu, p, half) and mean LightGBM contribution groups on the live rows."""
    from app.e163 import model as C163
    from app.e168 import dashboard_export as X
    from app.e168 import lgbm_only as E
    from app.e182 import candidate as C182
    from app.e184 import candidate as C184
    tr, te, AN, folds = prep["tr"], prep["te"], prep["AN"], prep["folds"]
    cfg = prep["ranked"][rank]
    stream = f"LIVE|{prep['issue']}|L{prep['lead']}"      # E184's live stream: rank 1 x draws 17901-17905 = E184's live rows
    news = set(E.NEWS)
    acc = {"mu": [], "p": [], "half": []}
    G = {f"shap_{b}": [] for b in X.BARS} | {f"shap_news_{b}": [] for b in X.BARS} | {"shap_other": [], "bias": [], "change": []}
    for k, s in enumerate(SEEDS):
        P, chosen, _, m = C182.seed_run(tr, te, AN, folds, cfg, C184.SETTING, s, stream)
        mu, p, half = P[chosen]
        acc["mu"].append(np.asarray(mu, float))
        acc["p"].append(np.asarray(p, float))
        acc["half"].append(np.asarray(half, float))
        contrib = m.m_.predict(te[m.use_], pred_contrib=True)
        cols = list(m.use_)
        grp = [X.OWN_BAR.get(c) or (X.GROUPS.get(C163.gmap(c)) if C163.gmap(c) else None) for c in cols]
        g = {key: np.zeros(len(te)) for key in G}
        for i, c in enumerate(cols):
            if grp[i] is None:
                g["shap_other"] += contrib[:, i]
            else:
                g[f"shap_{grp[i]}"] += contrib[:, i]
                if c in news:
                    g[f"shap_news_{grp[i]}"] += contrib[:, i]
        g["bias"] = contrib[:, -1]
        g["change"] = contrib.sum(axis=1)
        for key in G:
            G[key].append(g[key])
        if k == 4:
            first5 = np.mean(acc["p"], axis=0)
    a, f, pr, h = cfg
    tag = f"{a}|{f}|prune={pr}|leaves={h[0]},minchild={h[1]},lambda={h[2]},trees={h[3]}"
    return {"lead": prep["lead"], "issue": prep["issue"], "rank": rank, "tag": tag,
            **{k: np.mean(v, axis=0) for k, v in acc.items()}, **{k: np.mean(v, axis=0) for k, v in G.items()}, "p_first5": first5}


def _rows(issue: str, preps: dict, fits: list[dict], leads=(1, 2, 3)) -> pd.DataFrame:
    from app.e168 import dashboard_export as X
    from app.e168 import robust as RB
    from app.fi5.target import qindex, qlabel

    def e194(lead, iss):
        fs = [f for f in fits if f["lead"] == lead and f["issue"] == iss]
        assert len(fs) == TOPK, (lead, iss, len(fs))
        keys = [k for k in fs[0] if isinstance(fs[0][k], np.ndarray)]
        return {k: np.mean([f[k] for f in fs], axis=0) for k in keys}, [f["tag"] for f in fs]

    prev = _prev_issue(issue)
    out = []
    for lead in leads:
        cur, tags = e194(lead, issue)
        if lead == 1:                                    # E196 rule: Lead 1 = mean(Lead 1 now, Lead 2 issued a quarter earlier)
            old, tags_old = e194(2, prev)
            te_c, te_o = preps[(1, issue)]["te"], preps[(2, prev)]["te"]
            assert list(te_c["province"]) == list(te_o["province"]), "province order differs between issues"
            v = {k: (cur[k] + old[k]) / 2 for k in cur}
            tags = tags + [f"prev:{t}" for t in tags_old]
        else:
            v = cur
        te = preps[(lead, issue)]["te"]
        filled = preps[(lead, issue)]["filled"]
        used = [sorted(set().union(*[set(u) for u in us])) for us in zip(*[RB.used_by(t.removeprefix("prev:"), filled) for t in tags if not t.startswith("prev:")])]
        cfg = "E196: mean of top-5 configs x 20 draws" + (" (Lead 1: + previous issue's Lead 2)" if lead == 1 else "") + " | " + " ; ".join(tags)
        for k in range(len(te)):
            score = round(float(pct(v["mu"][k])), 1)
            o = {"province_code": X.CODES[te["province"].iloc[k]], "province": te["province"].iloc[k], "quarter": qlabel(qindex(issue) + lead),
                 "lead": lead, "issue_date": X._cutoff(issue), "probability": round(float(v["p"][k]), 3), "class": "HIGH" if v["p"][k] >= .5 else "LOW",
                 "score_pct": score, "range90_low": round(float(pct(v["mu"][k] - v["half"][k])), 1), "range90_high": round(float(pct(v["mu"][k] + v["half"][k])), 1),
                 "config": cfg, "baseline_pct": round(float(pct(logit(score) - v["change"][k])), 2), "change_logit": round(float(v["change"][k]), 6),
                 "bias_logit": round(float(v["bias"][k]), 6), "shap_other": round(float(v["shap_other"][k]), 6), "model": E196_ID,
                 "inputs_filled": len(used[k]), "inputs_filled_names": ";".join(used[k]), "data_complete": not used[k]}
            for b in X.BARS:
                o[f"shap_{b}"], o[f"shap_news_{b}"] = round(float(v[f"shap_{b}"][k]), 6), round(float(v[f"shap_news_{b}"][k]), 6)
            for c in X.VALUES:
                o[f"val_{c}"] = None if c not in te or pd.isna(te.at[k, c]) else float(te.at[k, c])
            out.append(o)
    return pd.DataFrame(out)


def _evaluation_files() -> dict:
    """lead_horizon.json and thesis_metrics.json for E196 from its validation rows (E196 rerun of E194 + the per-lead rule)."""
    from app.e168 import lgbm_only as E
    from app.e191 import run as R
    G = pd.read_csv(K.D / "e158" / "out" / "oof.csv")
    P = pd.read_csv(OUT / "e194_rerun_rows.csv")
    W = P.pivot_table(index=["key", "survey"], columns="lead", values="p")
    res = json.loads((OUT / "results.json").read_text())
    leads, tm, ok = {}, {}, []
    for L in (1, 2, 3, 4):
        s = (W[[1, 2]].mean(axis=1) if L == 1 else W[L]).rename("E196").reset_index()
        x = G[G["lead"] == L].merge(s, on=["key", "survey"])
        assert len(x) == 72
        y = x["y_high"].astype(bool)
        m = R.metrics(y, x["E196"], x["q_true"])
        mp = R.metrics(y, x["PERS"], x["q_true"])
        v = E.E7.diff_ci(x, "E196", "PERS", "q_true", np.random.default_rng(196), n=2000)
        beats = v["ci95"][1] < 0
        c = m["confusion"]
        leads[str(L)] = {"rows": 72, "correct": m["correct"], "accuracy": m["accuracy"], "high_recall": m["recall"], "low_recall": m["specificity"],
                         "precision": m["precision"], "brier": m["brier"], "persistence_accuracy": mp["accuracy"],
                         "brier_minus_persistence": round(v["diff"], 4), "brier_minus_persistence_ci95": [round(z, 4) for z in v["ci95"]],
                         "beats_persistence_C2": bool(beats)}
        # thesis_metrics.json keeps the adapter's schema key ("E168") for the served model's own metrics
        tm[str(L)] = {"n_high": int(c["tp"] + c["fn"]), "E168": {"precision_high": m["precision"], "recall_high": m["recall"], "f1_high": m["f1"], "auc_roc": m["roc_auc"]}}
        ok.append(m["accuracy"] >= 0.75 and beats)
    rl = 0
    for good in ok:
        if not good:
            break
        rl += 1
    H = {"model": E196_ID, "threshold_accuracy": 0.75, "leads": leads, "skill_horizon_beats_persistence": rl,
         "horizon_75pct_and_beats_persistence": rl, "maximum_reliable_lead_E156": None, "decision": res["decision"]}
    return H, tm


def stage() -> dict:
    prod = K.production_issue()
    if prod["model_id"] not in (E168_ID, E184_ID, E196_ID):
        raise SystemExit(f"production model is {prod['model_id']}; E196 stages against an E168/E184 production issue")
    if not K.at_production_cutoff(prod):
        sys.exit(K.rerun_at_cutoff("app.e196.serve", ["stage"], prod))
    from joblib import Parallel, delayed
    from app import registry as R
    from app.e168 import regenerate as RG
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    if not res["decision"].startswith("E196 preferred"):
        raise SystemExit("E196 did not meet its pre-registered rule; nothing staged")
    seal = OUT / "sealed_enns2022.json"
    if not seal.exists():
        raise SystemExit("E196's ENNS 2022 forecasts are not sealed (python -m app.e196.seal)")
    issue, folder = prod["issue"], prod["folder"]
    final = ISSUES / folder
    if (final / "live.json").exists():
        return {"status": "exists", "path": str(final)}
    prev = _prev_issue(issue)
    jobs = [(1, issue), (2, issue), (3, issue), (2, prev)]
    preps = {(p["lead"], p["issue"]): p for p in Parallel(n_jobs=4)(delayed(_prep)(l, i) for l, i in jobs)}
    fits = Parallel(n_jobs=min(7, max(1, (os.cpu_count() or 2) - 1)), verbose=5)(delayed(_fit)(preps[j], r) for j in jobs for r in range(TOPK))
    # reproduction: rank-1 configuration, draws 17901-17905, current issue = E184's staged live rows (same frames, same stream)
    e84 = pd.read_csv(K.D / "e184" / "issues" / folder / "dashboard_rows.csv") if (K.D / "e184" / "issues" / folder / "dashboard_rows.csv").exists() else None
    check = None
    if e84 is not None:
        d = []
        for f in fits:
            if f["rank"] == 0 and f["issue"] == issue:
                te = preps[(f["lead"], issue)]["te"]
                ref = e84[e84["lead"] == f["lead"]].set_index("province").loc[te["province"], "probability"].values
                d.append(float(np.max(np.abs(np.round(f["p_first5"], 3) - ref))))
        check = {"max_abs_diff_probability_vs_E184_live_3dp": max(d)}
    dash = _rows(issue, preps, fits)
    H, tm = _evaluation_files()
    K.dump_json(H, OUT / "lead_horizon.json")
    K.dump_json(tm, OUT / "thesis_metrics.json")
    acc = {int(k): {"accuracy": v["accuracy"], "high_recall": v["high_recall"], "persistence_accuracy": v["persistence_accuracy"],
                    "beats_persistence": v["beats_persistence_C2"]} for k, v in H["leads"].items()}
    rows = [{"province": r["province"], "lead": int(r["lead"]), "target_quarter": r["quarter"], "score_pct": float(r["score_pct"]),
             "range90_pct": [float(r["range90_low"]), float(r["range90_high"])], "p_high": float(r["probability"]), "risk_class": r["class"],
             "config": r["config"], "inputs_filled": int(r["inputs_filled"]), "data_complete": bool(r["data_complete"])} for _, r in dash.iterrows()]
    with K.patched(RG, "MODEL_ID", E196_ID):
        RG.validate(issue, rows, dash)
    live = prod["live"]
    doc = {"model": E196_ID, "name": NAME, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "issue_quarter": issue,
           "information_cutoff": live.get("information_cutoff"), "data_published_by": live.get("data_published_by"),
           "target": "HFIAS moderate+severe household food insecurity, HIGH at 50 %", "provinces": rows, "accuracy_by_lead": acc,
           "acceptance_basis": "owner-defined (2026-11-07): accuracy >= 75 % and significantly better than reusing the latest survey (Brier CI < 0) at each served lead",
           "served_leads": [l for l in (1, 2, 3) if acc[l]["accuracy"] >= 0.75 and acc[l]["beats_persistence"]],
           "statistical_reliability": ("Validated on the same 72 provincial forecasts per lead as E168/E184 (reused across many experiments); "
                                       "about 80 % pooled over Leads 1-3 after a winner's-curse adjustment (docs/e196/RELIABILITY.md); "
                                       "independent confirmation pending on the sealed ENNS 2022 forecasts. Synthetic rows are training data only."),
           "synthetic_training": {"ratio_synthetic_to_real": 1.0, "weight": 1.0, "generator": "jitter 0.5 SD, boundary focus, classes balanced",
                                  "configurations": TOPK, "seeds": [SEEDS[0], SEEDS[-1]], "never_used_for_testing": True},
           "lagged_averaging": {"lead_1": f"mean of this issue's Lead 1 and issue {prev}'s Lead 2 (same target)", "leads_2_3": "none"},
           "e184_live_reproduction": check, "seals": {"ENNS2022": _sha(seal)[:8]}}
    tmp = ISSUES / f".{folder}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    (tmp / "live.json").write_text(json.dumps(doc, indent=1, default=str), newline="\n")
    dash.to_csv(tmp / "dashboard_rows.csv", index=False, lineterminator="\n")
    news = prod["artifact"].parent / "news_used.json"
    if news.exists():
        shutil.copy2(news, tmp / "news_used.json")
    man = {"issue": issue, "folder": folder, "model": E196_ID, "status": "staged", "information_cutoff": doc["information_cutoff"],
           "created_utc": doc["created_utc"], "inputs_sha256": prod["inputs_sha256"], "live_sha256": _sha(tmp / "live.json"),
           "replaces": prod["model_id"], "promote": 'python -m app.e196.serve promote --approver "<name>"',
           "rollback": 'python -m app.e196.serve rollback --approver "<name>"'}
    (tmp / "manifest.json").write_text(json.dumps(man, indent=1), newline="\n")
    os.replace(tmp, final)
    art = str((final / "live.json").relative_to(K.BACKEND_DIR)).replace("\\", "/")
    sha = R.file_sha256(final / "live.json")
    R.register(E196_ID, {"version": f"E196 (E184 x top-5 configurations, Lead-1 lagged averaging), issue {folder}", "artifact_path": art,
                         "artifact_sha256": sha, "target": "HFIAS moderate+severe household food insecurity by province; HIGH at 50 %",
                         "note": "Local candidate staged by app.e196.serve; promote only by the owner."}, "candidate")
    rule = {f"lead{l}_accuracy_75_and_beats_persistence": bool(acc[l]["accuracy"] >= .75 and acc[l]["beats_persistence"]) for l in (1, 2, 3)}
    gate = {"model_id": E196_ID, "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "passed": all(rule.values()),
            "rule": "owner production rule at each served lead", "checks": [{"id": k, "name": k, "status": "pass" if v else "fail", "critical": True} for k, v in rule.items()],
            "artifact_file_sha256": sha, "results_sha256": _sha(OUT / "results.json"),
            "decision": "eligible for promotion by the owner" if all(rule.values()) else "not eligible"}
    R.record_gate(E196_ID, gate)
    return {"status": "staged", "path": str(final), "registered": E196_ID, "gate_passed": gate["passed"], "artifact_sha256": sha,
            "e184_live_reproduction": check, "served_leads": doc["served_leads"]}


def extend(leads=(4,)) -> dict:
    """Add further leads (default Lead 4) to the production E196 issue: computes them with the same procedure (top-5 x 20
    draws; no lagged averaging beyond Lead 1, as validated), writes a new revision folder with all leads, and registers it
    as a candidate. Promote it with `promote`; the previous revision stays on disk for rollback."""
    from joblib import Parallel, delayed
    from app import registry as R
    from app.e168 import regenerate as RG
    prod = K.production_issue()
    if prod["model_id"] != E196_ID:
        raise SystemExit(f"production model is {prod['model_id']}; promote E196 first")
    if not K.at_production_cutoff(prod):
        sys.exit(K.rerun_at_cutoff("app.e196.serve", ["extend"], prod))
    issue, src = prod["issue"], prod["artifact"].parent
    old = pd.read_csv(src / "dashboard_rows.csv")
    have = set(old["lead"].astype(int))
    new_leads = tuple(l for l in leads if l not in have)
    if not new_leads:
        return {"status": "nothing to add", "leads": sorted(have)}
    H = json.loads((OUT / "lead_horizon.json").read_text())
    for l in new_leads:
        v = H["leads"].get(str(l))
        if not v or not (v["accuracy"] >= 0.75 and v["beats_persistence_C2"]):
            raise SystemExit(f"Lead {l} does not meet the owner rule in data/e196/out/lead_horizon.json; not added")
    jobs = [(l, issue) for l in new_leads]
    preps = {(p["lead"], p["issue"]): p for p in Parallel(n_jobs=len(jobs))(delayed(_prep)(l, i) for l, i in jobs)}
    fits = Parallel(n_jobs=min(7, max(1, (os.cpu_count() or 2) - 1)), verbose=5)(delayed(_fit)(preps[j], r) for j in jobs for r in range(TOPK))
    add = _rows(issue, preps, fits, leads=new_leads)
    dash = pd.concat([old, add[old.columns]], ignore_index=True).sort_values(["lead", "province"]).reset_index(drop=True)
    acc = {int(k): {"accuracy": v["accuracy"], "high_recall": v["high_recall"], "persistence_accuracy": v["persistence_accuracy"],
                    "beats_persistence": v["beats_persistence_C2"]} for k, v in H["leads"].items()}
    rows = [{"province": r["province"], "lead": int(r["lead"]), "target_quarter": r["quarter"], "score_pct": float(r["score_pct"]),
             "range90_pct": [float(r["range90_low"]), float(r["range90_high"])], "p_high": float(r["probability"]), "risk_class": r["class"],
             "config": r["config"], "inputs_filled": int(r["inputs_filled"]), "data_complete": bool(r["data_complete"])} for _, r in dash.iterrows()]
    with K.patched(RG, "MODEL_ID", E196_ID):
        RG.validate(issue, rows, dash)
    doc = json.loads((src / "live.json").read_text())
    all_leads = sorted(int(l) for l in dash["lead"].unique())
    doc.update({"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "provinces": rows, "accuracy_by_lead": acc,
                "served_leads": [l for l in all_leads if acc[l]["accuracy"] >= 0.75 and acc[l]["beats_persistence"]],
                "lagged_averaging": {**doc.get("lagged_averaging", {}), **{f"lead_{l}": "none" for l in new_leads}},
                "extended_from": src.name})
    base = src.name.split("_r")[0] if "_r" in src.name else src.name
    rev = 2
    while (ISSUES / f"{base}_r{rev}").exists():
        rev += 1
    folder = f"{base}_r{rev}"
    tmp = ISSUES / f".{folder}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    (tmp / "live.json").write_text(json.dumps(doc, indent=1, default=str), newline="\n")
    dash.to_csv(tmp / "dashboard_rows.csv", index=False, lineterminator="\n")
    if (src / "news_used.json").exists():
        shutil.copy2(src / "news_used.json", tmp / "news_used.json")
    man = json.loads((src / "manifest.json").read_text())
    man.update({"folder": folder, "status": "staged", "created_utc": doc["created_utc"], "live_sha256": _sha(tmp / "live.json"),
                "leads": all_leads, "extends": src.name})
    (tmp / "manifest.json").write_text(json.dumps(man, indent=1), newline="\n")
    os.replace(tmp, ISSUES / folder)
    final = ISSUES / folder
    art = str((final / "live.json").relative_to(K.BACKEND_DIR)).replace("\\", "/")
    sha = R.file_sha256(final / "live.json")
    R.register(E196_ID, {"version": f"E196 (E184 x top-5 configurations, Lead-1 lagged averaging), issue {folder}, Leads {all_leads[0]}-{all_leads[-1]}",
                         "artifact_path": art, "artifact_sha256": sha, "target": "HFIAS moderate+severe household food insecurity by province; HIGH at 50 %",
                         "note": "Local candidate (extended leads) staged by app.e196.serve extend; promote only by the owner."}, "candidate")
    gate_extended(final)
    return {"status": "staged", "path": str(final), "leads": all_leads, "added": list(new_leads), "artifact_sha256": sha,
            "new_rows": add[["province", "quarter", "lead", "score_pct", "probability", "class"]].to_dict("records")}


def gate_extended(final: Path) -> dict:
    """Release gate for an extended revision: the owner's rule (accuracy >= 75 % and better than persistence) at every
    served lead, from the revision's own accuracy_by_lead. Same gate format as stage()."""
    from app import registry as R
    doc = json.loads((final / "live.json").read_text())
    acc = {int(k): v for k, v in doc["accuracy_by_lead"].items()}
    leads = sorted(int(l) for l in doc["served_leads"])
    rule = {f"lead{l}_accuracy_75_and_beats_persistence": bool(acc[l]["accuracy"] >= .75 and acc[l]["beats_persistence"]) for l in leads}
    sha = R.file_sha256(final / "live.json")
    gate = {"model_id": E196_ID, "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "passed": all(rule.values()),
            "rule": "owner production rule at each served lead", "checks": [{"id": k, "name": k, "status": "pass" if v else "fail", "critical": True} for k, v in rule.items()],
            "artifact_file_sha256": sha, "results_sha256": _sha(OUT / "results.json"),
            "decision": "eligible for promotion by the owner" if all(rule.values()) else "not eligible"}
    R.record_gate(E196_ID, gate)
    return gate


def promote(approver: str) -> dict:
    from app import registry as R
    if not approver.strip():
        raise SystemExit("--approver is required")
    m = R.load()["models"].get(E196_ID)
    if not m:
        raise SystemExit("E196 is not staged (python -m app.e196.serve stage)")
    man = json.loads((K.BACKEND_DIR / m["artifact_path"]).with_name("manifest.json").read_text())
    if _sha(K.BACKEND_DIR / m["artifact_path"]) != man["live_sha256"]:
        raise SystemExit("the staged E196 artifact changed after staging; refusing")
    rec = R.promote(E196_ID, approver)
    return {"status": "promoted", "production": E196_ID, "approver": approver, "approved_utc": rec["approved_utc"],
            "next": "restart the backend so every page uses E196"}


def rollback(approver: str) -> dict:
    from app import registry as R
    if not approver.strip():
        raise SystemExit("--approver is required")
    rec = R.promote(E184_ID, approver)
    return {"status": "rolled back", "production": E184_ID, "artifact": rec["artifact_path"], "approver": approver,
            "next": "restart the backend so every page uses E184"}


def status() -> dict:
    from app import registry as R
    reg = R.load()
    return {"production": reg.get("production"), "e196": {k: (reg["models"].get(E196_ID) or {}).get(k) for k in ("status", "artifact_path", "version")},
            "e196_gate_passed": ((reg["models"].get(E196_ID) or {}).get("gate") or {}).get("passed")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stage", "extend", "promote", "rollback", "status"])
    ap.add_argument("--approver", default="")
    a = ap.parse_args()
    out = {"stage": stage, "extend": extend, "status": status}.get(a.cmd)
    print(json.dumps(out() if out else (promote if a.cmd == "promote" else rollback)(a.approver), indent=1, default=str))
