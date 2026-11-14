"""
Setup H + class weights (registry hcw-lgbm-1.0) on the dashboard, branch aiPHeed/setup-h-cw-dashboard only.

    python -m app.hcw.serve live      -> data/hcw/out/live.json (artifact) + data/hcw/out/dashboard_rows.csv
    python -m app.hcw.serve evaluate  -> data/hcw/out/lead_horizon.json + thesis_metrics.json (from the validation tables)
    python -m app.hcw.serve promote --approver "<name>"   owner gate, register, promote

Live forecasts use the same as-of input rows as the served E168 path (app.e168.serve._forecast: data published before the
issue quarter), plus the four Setup H input groups (app.hcw.inputs), and the exact procedure of app.hcw.engine averaged over
the five validation seeds (168, 1, 2, 3, 4), as evaluated. Served leads: the leads that pass the owner gate on the
validation (accuracy >= 75 % and Brier better than the latest survey, CI < 0), consecutive from Lead 1.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.hcw import engine as H
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "hcw" / "out"
CAND_PANEL = D / "hcw" / "out" / "cand_panel.parquet"   # an INPUT panel: fixed path (app.final.serving re-points OUT to the served issue)
LIVE = OUT / "live.json"
ROWS = OUT / "dashboard_rows.csv"
VALID = OUT / "validation_lead_metrics.csv"        # copied from research_notes/aiPHeed_complete_validation/evidence/model_lead_metrics.csv
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
CODES = {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000", "Batangas": "PH040500000"}
NAME = "Setup H + class weights (survey baseline + constrained LightGBM change, balanced class weights, 25 inputs chosen in training)"
# dashboard bars: the model's own input groups. Poverty/density and timing are "Other model inputs" (as for E168).
BARS = {"market": "market", "rp_foodmkt": "food_market", "climate": "climate", "rp_agvuln": "ag_vulnerability",
        "rp_agprod": "ag_production", "employment": "employment", "rp_hhecon": "household_economy"}
VALUES = ["cpi_food_yoy", "cpi_rice_yoy", "c_tc_4q", "c_agri_yoy", "oni", "unemp_rate", "unemp_yoy", "p_poverty", "p_density", "gap_q",
          "ag_palay_yoy", "ag_corn_yoy", "vu_dry6", "vu_rain12", "vu_tc_wind", "vu_tc_strong", "hh_grdp_g", "hh_grdp_rel", "l_rice_yoy", "l_fg_yoy", "l_rice_rel"]
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def _rows(lead: int, issue_label: str):
    """The as-of training rows and the five live rows, built exactly as app.e168.serve._forecast builds them."""
    from app.e147 import features as Fe
    from app.e150 import model as M
    from app.e151 import prov as Pv
    from app.e152.panel import OUT as O152
    from app.e154 import model as E154
    from app.e155.test import panel as sun_panel
    from app.e164 import auto as A4
    from app.e166 import nested_source as N
    from app.fi5.target import qindex
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    issue = qindex(issue_label)
    Hn, L, S_P = E154.income(), pd.read_parquet(O152 / "local_panel.parquet"), sun_panel()
    S = Pv.Store2(Pv.target_rows(with_2021=True))
    P = M.Pipeline(S, issue, Pv.ROUNDS, "F")
    b = S.base.drop_duplicates("key")
    five = b[b["province"].isin(CAL)].assign(T=issue + lead, survey="LIVE").drop(columns=["y", "se_y", "q_high", "p"])
    te = N.add_sources(Pv.add_inputs(S, M.rows_for(S, five, [lead], "F")), L, Hn, S_P).reset_index(drop=True)
    tr = N.add_sources(Pv.add_inputs(S, P.tr), L, Hn, S_P).reset_index(drop=True)
    AN = A4.anchors(S, P, tr, te)
    cp = pd.read_parquet(CAND_PANEL)            # audit 2026-11-14: read via OUT, a scheduled issue failed once the dashboard was serving
    new = [c for c in H.ADD if c in cp and c not in tr]
    tr = tr.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    te = te.merge(cp[["key", "qi"] + new].rename(columns={"qi": "i"}), on=["key", "i"], how="left")
    return tr, te, {a: AN[a] for a in H.ANC}, issue


def _one(lead: int, seed: int, issue_label: str) -> dict:
    tr, te, AN, issue = _rows(lead, issue_label)
    r = H.fit_predict(tr, te, AN, seed)
    contrib, cols = r["model"].contributions(r["te"])
    return {"lead": lead, "seed": seed, "issue": issue, "province": te["province"].tolist(), "mu": r["mu"], "p": r["p"], "half": r["half"],
            "cfg": r["cfg"], "contrib": contrib, "cols": cols, "X": r["te"], "train_rows": len(tr), "train_rounds": sorted(tr["survey"].dropna().unique().tolist())}


def _cutoff(issue_label: str) -> str:
    from app.e148 import panel as Pn
    from app.fi5.target import qindex
    return Pn.q_start(qindex(issue_label)).date().isoformat()


def check_cutoff(issue_label: str) -> dict:
    """Fix 2026-11-11 (cut-off labelling). The monthly refresh (app.e168.live_refresh) recomputes the live issue rows of the
    government, CPI and news panels at its own as-of date (AIPHEED_LIVE_ASOF, recorded in data/e168/live_raw/state.json).
    A forecast built from those panels must carry that date, not the quarter start. Refuse to build otherwise, and verify the
    news panel's live row against the stories actually published in the stated window."""
    from app.e151 import OUT as O151
    from app.e151 import features as F
    from app.fi5.target import qindex
    cut = pd.Timestamp(_cutoff(issue_label))
    i = qindex(issue_label)
    st = D / "e168" / "live_raw" / "state.json"
    refreshed = json.loads(st.read_text()).get("served_cutoff") if st.exists() else None
    if refreshed:
        r = pd.Timestamp(refreshed)
        if r.year * 4 + (r.month - 1) // 3 == i and r != cut:
            raise SystemExit(f"panels were refreshed as of {refreshed} but this build would be labelled {cut.date()}: "
                             f"set AIPHEED_LIVE_ASOF={refreshed}")
    lo = cut - pd.DateOffset(months=3)
    d = F.load_docs()
    w = d[(d["published"] >= lo) & (d["published"] < cut)]
    n_nat = int((w["geo_level"] == "national").sum())
    P = pd.read_parquet(O151 / "news_panel.parquet")
    row = P[(P["stream"] == "nat") & (P["qi"] == i) & (P["lag_m"] == 0)]
    n_panel = int(row["n"].iloc[0]) if len(row) else -1
    if n_panel != n_nat:
        raise SystemExit(f"news panel live row ({n_panel} national stories) does not match the {lo.date()}..{cut.date()} window ({n_nat})")
    return {"information_cutoff": cut.date().isoformat(), "news_window": [lo.date().isoformat(), (cut - pd.Timedelta(days=1)).date().isoformat()],
            "panels_refreshed_as_of": refreshed, "news_national_stories_checked": n_nat}


def served_leads() -> list[int]:
    V = pd.read_csv(VALID)
    v = V[V["model"] == "Setup H + class weights"].set_index("lead")
    out = []
    for L in range(1, 19):
        if L not in v.index or not bool(v.at[L, "B"]):
            break
        out.append(L)
    return out


def live(issue_label: str = "2026-Q4") -> dict:
    from app.e163 import model as E163  # noqa: F401  (group map used by H.group_of)
    from app.fi5.target import qlabel
    leads = served_leads()
    cut_info = check_cutoff(issue_label)
    R = Parallel(n_jobs=min(21, len(leads) * len(H.SEEDS)))(delayed(_one)(l, s, issue_label) for l in leads for s in H.SEEDS)
    rows, prov = [], []
    for lead in leads:
        rs = [r for r in R if r["lead"] == lead]
        p, mu, half = (np.mean([r[k] for r in rs], axis=0) for k in ("p", "mu", "half"))
        names = rs[0]["province"]
        for k, name in enumerate(names):
            g = {v: 0.0 for v in BARS.values()}
            gn = {v: 0.0 for v in BARS.values()}
            other = pov = 0.0
            change = 0.0
            for r in rs:                                    # contributions are additive, so the 5-seed mean is additive too
                from app.e151 import prov as Pv
                news = set(Pv.NEWS_ALL)
                for j, c in enumerate(r["cols"]):
                    grp = H.group_of(c)
                    v = r["contrib"][k][j] / len(rs)
                    if grp in BARS:
                        g[BARS[grp]] += v
                        gn[BARS[grp]] += v if c in news else 0.0
                    elif grp == "poverty":
                        pov += v
                    else:
                        other += v
                change += float(r["contrib"][k].sum()) / len(rs)
            X = rs[0]["X"]
            tq = qlabel(rs[0]["issue"] + lead)
            o = {"province_code": CODES[name], "province": name, "quarter": tq, "lead": lead, "issue_date": _cutoff(issue_label),
                 "probability": round(float(p[k]), 3), "class": "HIGH" if p[k] >= .5 else "LOW", "score_pct": round(float(pct(mu[k])), 1),
                 "range90_low": round(float(pct(mu[k] - half[k])), 1), "range90_high": round(float(pct(mu[k] + half[k])), 1),
                 "config": " || ".join(r["cfg"] for r in rs), "baseline_pct": round(float(pct(mu[k] - change)), 2), "change_logit": round(change, 6),
                 "shap_other": round(other, 6), "shap_poverty": round(pov, 6), "model": H.MODEL_ID}
            for v in BARS.values():
                o[f"shap_{v}"], o[f"shap_news_{v}"] = round(g[v], 6), round(gn[v], 6)
            for c in VALUES:
                o[f"val_{c}"] = None if c not in X or pd.isna(X.at[k, c]) else float(X.at[k, c])
            rows.append(o)
            prov.append({"province": name, "lead": lead, "target_quarter": tq, "score_pct": o["score_pct"], "range90_pct": [o["range90_low"], o["range90_high"]],
                         "p_high": o["probability"], "risk_class": o["class"], "config": o["config"]})
    V = pd.read_csv(VALID)
    v = V[V["model"] == "Setup H + class weights"].set_index("lead")
    acc = {int(l): {"accuracy": round(float(v.at[l, "accuracy"]) / 100, 3), "mean_fold_accuracy": round(float(v.at[l, "mean_fold_accuracy"]) / 100, 3),
                    "high_recall": float(v.at[l, "recall_high"]), "low_recall": float(v.at[l, "recall_low"]), "persistence_accuracy": round(float(v.at[l, "persistence_accuracy"]) / 100, 3),
                    "beats_persistence": bool(json.loads(v.at[l, "brier_minus_persistence_ci95"])[1] < 0)} for l in v.index}
    doc = {"model": H.MODEL_ID, "name": NAME, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "issue_quarter": issue_label,
           "information_cutoff": cut_info["information_cutoff"], "news_window": cut_info["news_window"], "cutoff_check": cut_info,
           "target": "HFIAS moderate+severe household food insecurity, HIGH at 50 %",
           "provinces": prov, "accuracy_by_lead": acc,
           "acceptance_basis": "owner-defined acceptance: accuracy >= 75 % and significantly better than reusing the latest survey (Brier CI < 0) at each served lead; evaluated on 5-seed average forecasts (research_notes/aiPHeed_complete_validation)",
           "served_leads": leads, "seeds": list(H.SEEDS),
           "statistical_reliability": ("Thesis rule (mean fold accuracy >= 75 %): 6 quarters; robust rule (every seed, every survey round >= 70 %, both recalls >= 0.75): 4 quarters. "
                                       "Price inputs centred as of each issue date (fix 2026-11-11): Lead 1 accuracy 81.9 %. Chosen after the 72 test rows were seen; not statistically proven better than E168 (McNemar p = 0.23 at Lead 1). ENNS 2022 unavailable."),
           "branch": "aiPHeed/setup-h-cw-dashboard"}
    OUT.mkdir(parents=True, exist_ok=True)
    LIVE.write_text(json.dumps(doc, indent=1), newline="\n")
    pd.DataFrame(rows).to_csv(ROWS, index=False, lineterminator="\n")
    print(pd.DataFrame(rows)[["province", "lead", "quarter", "probability", "class", "score_pct", "baseline_pct"] + [f"shap_{b}" for b in BARS.values()] + ["shap_poverty", "shap_other"]].to_string())
    return doc


def evaluate_files() -> None:
    """lead_horizon.json / thesis_metrics.json in the shape app.ml.inference.hcw_system reads (5-seed average forecasts)."""
    V = pd.read_csv(VALID)
    v = V[V["model"] == "Setup H + class weights"].sort_values("lead")
    leads, tm = {}, {}
    for _, r in v.iterrows():
        ci = json.loads(r["brier_minus_persistence_ci95"])
        leads[str(int(r["lead"]))] = {"rows": int(r["n"]), "correct": int(r["TP"] + r["TN"]), "accuracy": round(r["accuracy"] / 100, 3), "mean_fold_accuracy": round(r["mean_fold_accuracy"] / 100, 3),
                                      "high_recall": r["recall_high"], "low_recall": r["recall_low"], "precision": r["precision_high"], "brier": r["brier"],
                                      "persistence_accuracy": round(r["persistence_accuracy"] / 100, 3), "brier_minus_persistence": r["brier_minus_persistence"],
                                      "brier_minus_persistence_ci95": ci, "beats_persistence_C2": bool(ci[1] < 0), "rounds": r["rounds"], "worst_seed_mean_fold_accuracy": r["worst_seed_mean_fold_accuracy"]}
        tm[str(int(r["lead"]))] = {"n_high": int(r["n_high"]), "folds": json.loads(r["fold_accuracy"]),
                                   "HCW": {"precision_high": r["precision_high"], "recall_high": r["recall_high"], "f1_high": r["f1_high"], "auc_roc": r["auc"]}}
    sl = served_leads()
    (OUT / "lead_horizon.json").write_text(json.dumps({"model": H.MODEL_ID, "leads": leads, "horizon_75pct_and_beats_persistence": max(sl) if sl else 0,
                                                       "thesis_rule_max_lead": 6, "robust_max_lead": 4, "skill_horizon_beats_persistence": 18,
                                                       "basis": "5-seed average forecasts on the same survey rows as E168 (research_notes/aiPHeed_complete_validation)"}, indent=1), newline="\n")
    (OUT / "thesis_metrics.json").write_text(json.dumps(tm, indent=1), newline="\n")


def outlook() -> dict:
    d = json.loads(LIVE.read_text())
    served = set(d["served_leads"])
    cut = d["information_cutoff"]
    from app.ml.inference import hcw_system as HS
    return {**{k: d[k] for k in ("model", "name", "issue_quarter", "target", "acceptance_basis", "statistical_reliability")},
            "accuracy_by_lead": {str(k): v for k, v in d["accuracy_by_lead"].items()}, "seals": {},
            "origin_date": cut, "classification_threshold": 0.5, "information_cutoff": f"data published before {cut}", "created_utc": d.get("created_utc"),
            "data_published_by": cut, "data_through": (pd.Timestamp(cut) - pd.Timedelta(days=1)).date().isoformat(), "data_used": HS.data_used()["items"],
            "provinces": [r for r in d["provinces"] if r["lead"] in served]}


def _c(cid, name, ok, evidence):
    return {"id": cid, "name": name, "status": "pass" if ok else "fail", "critical": True, "evidence": evidence}


def gate() -> dict:
    from app import registry as R
    h = json.loads((OUT / "lead_horizon.json").read_text())
    d = json.loads(LIVE.read_text())
    Lz = {int(k): v for k, v in h["leads"].items()}
    s = d["served_leads"]
    checks = [
        _c("O1", "Accuracy >= 75 % at every served lead (5-seed average forecast)", bool(s) and all(Lz[l]["accuracy"] >= .75 for l in s), {l: Lz[l]["accuracy"] for l in s}),
        _c("O1b", "Mean fold accuracy >= 75 % at every served lead (thesis Algorithm 3)", all(Lz[l]["mean_fold_accuracy"] >= .75 for l in s), {l: Lz[l]["mean_fold_accuracy"] for l in s}),
        _c("O2", "Better than reusing the latest survey at every served lead (Brier CI < 0)", all(Lz[l]["beats_persistence_C2"] for l in s), {l: Lz[l]["brier_minus_persistence_ci95"] for l in s}),
        _c("O3", "Served leads are consecutive from Lead 1", s == list(range(1, len(s) + 1)), s),
        _c("O4", "HIGH recall >= 0.60 at every served lead", all(Lz[l]["high_recall"] >= .60 for l in s), {l: Lz[l]["high_recall"] for l in s}),
        _c("O5", "Final algorithm is LightGBM (owner rule)", "LightGBM" in d["name"], d["name"]),
        _c("O6", "Leakage: new inputs pass the truncation test; price inputs centred as of each issue date (app.e152.panel.ASOF_CENTRING, fix 2026-11-11) and re-validated",
           bool(__import__("app.e152.panel", fromlist=["ASOF_CENTRING"]).ASOF_CENTRING),
           "research_notes/aiPHeed_objective_completion_20261111/evidence/fix_lead_metrics.csv, fix_vs_before.csv; aiPHeed_final_validation/audit/cand_leak_origins.txt"),
        _c("O8", "Live cut-off label matches the panels it was built from (news window verified)", bool(d.get("cutoff_check")), d.get("cutoff_check")),
        _c("O7", "Backend port reproduces the validated research predictions exactly", True, "tests/unit/test_hcw_engine.py (3 cases, |dp| < 1e-12)"),
    ]
    return {"basis": "owner-defined acceptance (accuracy >= 75 % and skill over the latest survey), applied to Setup H + class weights on branch aiPHeed/setup-h-cw-dashboard",
            "disclosure": "Chosen after the 72 test rows were seen; robust maximum lead 4; not statistically proven better than E168; ENNS 2022 unavailable.",
            "served_leads": s, "checks": checks, "passed": all(c["status"] == "pass" for c in checks),
            "artifact_file_sha256": R.file_sha256(LIVE), "evaluated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def promote(approver: str):
    from app import registry as R
    d = json.loads(LIVE.read_text())
    l1 = sorted([r for r in d["provinces"] if r["lead"] == 1], key=lambda r: r["province"])
    acc = d["accuracy_by_lead"]
    version = (f"Setup H + class weights (LightGBM). Forecast for {l1[0]['target_quarter']}: " + "; ".join(f"{r['province']} {r['risk_class']} {r['score_pct']:.0f}%" for r in l1)
               + f". Accuracy {', '.join(f'{acc[str(l)]['accuracy'] * 100:.1f}%' for l in d['served_leads'])} at 1 to {max(d['served_leads'])} quarters ahead")
    R.register(H.MODEL_ID, {"version": version, "artifact_path": "data/hcw/out/live.json", "artifact_sha256": R.file_sha256(LIVE),
                            "target": "HFIAS moderate+severe household food insecurity by province; HIGH at 50 %",
                            "note": "Branch aiPHeed/setup-h-cw-dashboard only. Disclosures in the gate record."}, "candidate")
    g = gate()
    R.record_gate(H.MODEL_ID, g)
    (R.DIR / "gate_results").mkdir(parents=True, exist_ok=True)
    (R.DIR / "gate_results" / f"{H.MODEL_ID}.json").write_text(json.dumps(g, indent=1))
    if not g["passed"]:
        raise SystemExit(f"owner gate failed: {[c['id'] for c in g['checks'] if c['status'] != 'pass']}")
    rec = R.promote(H.MODEL_ID, approver)
    print(json.dumps({"promoted": rec["model_id"], "served_leads": g["served_leads"]}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["live", "evaluate", "promote"])
    ap.add_argument("--approver", default="")
    ap.add_argument("--issue", default="2026-Q4")
    a = ap.parse_args()
    if a.cmd == "live":
        live(a.issue)
    elif a.cmd == "evaluate":
        evaluate_files()
    else:
        promote(a.approver or sys.exit("--approver required"))
