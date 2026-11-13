r"""Freeze record + seal of the official FINAL (RATE + MIND) forecasts, issue 2026-Q4 (information cut-off 2026-11-01), Leads 1-5
(= the thesis Algorithm 3 MRLT), five CALABARZON provinces. Writes evidence/FINAL_FROZEN_CONFIG.json and
evidence/SEALED_FINAL_2027Q1_2028Q1.json (+ .sha256). Never overwrites an existing seal. Run: python -I seal.py"""
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parents[1]; EV = HERE / "evidence"; RN = HERE.parent
PV = RN / "aiPHeed_final_dashboard_preview_20261113" / "out_final"
SEAL = EV / "SEALED_FINAL_2027Q1_2028Q1.json"
if SEAL.exists():
    sys.exit("seal exists; refusing to overwrite")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
CODE = {"final_engine": "C:/Users/admin/aipheed_hcw/backend/app/hcw/final_engine.py", "base_engine": "C:/Users/admin/aipheed_hcw/backend/app/hcw/engine.py",
        "inputs_builder": "C:/Users/admin/aipheed_hcw/backend/app/hcw/inputs.py", "serve_rows": "C:/Users/admin/aipheed_hcw/backend/app/hcw/serve.py",
        "live_build": str(RN / "aiPHeed_final_dashboard_preview_20261113" / "scripts" / "build_corrected.py"),
        "research_engine": str(RN / "aiPHeed_hcw_final_optimization_20261112" / "scripts" / "engine_final.py")}
DATA = {"labels_oof": "C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv", "fnri2015": "C:/Users/admin/aipheed_e145/backend/data/hfias/clean/fnri2015_hfias.csv",
        "enns_2018_2019": "C:/Users/admin/aipheed_e145/backend/data/hfias/clean/enns_hfias.csv", "nns2013": "C:/Users/admin/aipheed_e145/backend/data/e141/clean/nns2013_hfias.csv",
        "enns2021_heatmap": "C:/Users/admin/aipheed_e145/backend/data/e147/raw/sealed_2021_labels.csv",
        "cand_panel_live": "C:/Users/admin/aipheed_hcw/backend/data/hcw/out/cand_panel.parquet",
        "psa_palay_corn_live": "C:/Users/admin/aipheed_hcw/backend/data/e168/live_raw/psa/palay_corn_q.csv"}
live = json.loads((PV / "live.json").read_text())
A = pd.read_csv(PV / "correction_audit.csv"); R = pd.read_csv(PV / "dashboard_rows.csv")
cfg = {"model": "FINAL (RATE + MIND) LightGBM, final-rate-mind-1.0", "selected_by_owner": "2026-11-13",
       "procedure": "app.hcw.final_engine.fit_predict (= research engine_final rate='lin', miss='mind', cw='balanced'): per fit, anchor (H/OH/RSS), "
                    "input set (GOV/GOV+cons/FULL), 25-input selection + correlation pruning, 16-setting grid by inner GroupKFold over regions, "
                    "monotone constraints, survey-precision x balanced class weights, RATE target (y - anchor)/g with weight g^2, MIND median fill + "
                    "missing flags, raw-first calibration",
       "threshold": 0.50, "seeds": [168, 1, 2, 3, 4], "seed_aggregation": "mean probability",
       "target": "FNRI HFIAS moderate+severe share of households >= 50 % (HIGH), provincial",
       "training_rounds": ["FNRI2015", "ENNS2018", "ENNS2019", "ENNS2021"], "anchor_history_from": "NNS2013",
       "information_cutoff": live["information_cutoff"], "issue_quarter": live["issue_quarter"],
       "mrlt_thesis_algorithm3": 5, "served_leads": [1, 2, 3, 4, 5],
       "inputs_change_2026_11_13": "by-crop palay/corn inputs extended past 2023-Q4 with the PSA live download (same OpenSTAT table; 2023 overlap identical); "
                                   "affects live rows only (qi >= 2024-Q3); no historical training or test row changed",
       "code_sha256": {k: sha(v) for k, v in CODE.items()}, "data_sha256": {k: sha(v) for k, v in DATA.items()},
       "not_in_version_control": "app/hcw/ and research_notes/ are untracked in git (commit pending owner approval)"}
(EV / "FINAL_FROZEN_CONFIG.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8", newline="\n")
rows = []
for _, a in A.iterrows():
    r = R[(R.province == a.province) & (R.lead == a.lead)].iloc[0]
    contrib = {c[5:]: round(float(r[c]), 6) for c in R.columns if c.startswith("shap_") and not c.startswith("shap_news_")}
    rows.append({"province": a.province, "lead": int(a.lead), "target_quarter": r.quarter, "official_p_high_FINAL": float(a.p_FINAL_uncorrected),
                 "official_class": "HIGH" if a.p_FINAL_uncorrected >= .5 else "LOW", "own_survey_gap_q": float(a.g), "quarters_since_latest_round": float(a.s),
                 "dashboard_display_p_long_gap_corrected": float(a.p_corrected), "dashboard_display_share_pct": float(a.prevalence_pct), "dashboard_display_range90": a.range90,
                 "explanation_logit_contributions_mean_of_g_and_s_variants": contrib, "survey_baseline_pct": float(r.baseline_pct)})
doc = {"sealed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": cfg["model"], "config_sha256": sha(EV / "FINAL_FROZEN_CONFIG.json"),
       "issue_quarter": live["issue_quarter"], "information_cutoff": live["information_cutoff"],
       "note": ("Official forecasts = FINAL probability at the province's own-survey gap (the validated form). The dashboard preview displays the "
                "long-gap corrected variant (LONG_GAP_CORRECTION_PROTOCOL, untested); both are recorded. No provincial outcome for 2027-Q1..2028-Q1 exists."),
       "scoring_procedure": "09/16 reports: score once against the next FNRI provincial HFIAS round covering these provinces and quarters; HIGH at 50 %; no refit",
       "rows": rows}
SEAL.write_text(json.dumps(doc, indent=1), encoding="utf-8", newline="\n")
(EV / "SEALED_FINAL_2027Q1_2028Q1.sha256").write_text(f"{sha(SEAL)}  {SEAL.name}\n", newline="\n")
print(sha(SEAL)); print(pd.DataFrame(rows)[["province", "lead", "target_quarter", "official_p_high_FINAL", "official_class", "dashboard_display_share_pct"]].to_string(index=False))
