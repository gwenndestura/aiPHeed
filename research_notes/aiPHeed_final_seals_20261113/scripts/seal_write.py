r"""Experimental seals (NOT official, NOT served): FINAL-LG (absolute HIGH >= 50 %) and ATTR (above-national), issue 2026-Q4, cut-off 2026-11-01,
five CALABARZON provinces, target quarters 2027-Q1..2028-Q1. Refuses to seal unless the NOPAIR rerun reproduces the official FINAL seal.
Never overwrites a seal. Run: python -I seal_write.py"""
import glob, hashlib, json, pickle, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
from sklearn.linear_model import BayesianRidge
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; PARTS = HERE / "parts"; EV = HERE / "evidence"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
lg = lambda p: np.log(p / (1 - p)); ex = lambda z: 100 / (1 + np.exp(-z))
OFF = json.load(open(RN / "aiPHeed_final_official_20261113" / "evidence" / "SEALED_FINAL_2027Q1_2028Q1.json"))
SEAL_LG, SEAL_AT = EV / "SEALED_FINAL_LG_2027Q1_2028Q1.json", EV / "SEALED_ATTR_2027Q1_2028Q1.json"
if SEAL_LG.exists() or SEAL_AT.exists():
    sys.exit("a seal exists; refusing to overwrite")
rd = lambda arm: pd.concat([pd.read_csv(f) for f in glob.glob(str(PARTS / f"{arm}__L*__*.csv"))])
NP, LGp = rd("NOPAIR"), rd("LG")
assert len(NP) == 125 and len(LGp) == 125, (len(NP), len(LGp))
off = pd.DataFrame(OFF["rows"])[["province", "lead", "target_quarter", "official_p_high_FINAL"]]
m = NP.groupby(["province", "lead"], as_index=False).p.mean().merge(off, on=["province", "lead"])
repro = {"rows": len(m), "max_abs_diff_vs_official_rounded_4dp": float((m.p.round(4) - m.official_p_high_FINAL).abs().max()),
         "max_abs_diff_raw": float((m.p - m.official_p_high_FINAL).abs().max())}
repro["PASS"] = bool(repro["rows"] == 25 and repro["max_abs_diff_vs_official_rounded_4dp"] <= 1e-4)
json.dump(repro, open(EV / "REPRO_official_FINAL.json", "w"), indent=1)
if not repro["PASS"]:
    sys.exit(f"official FINAL not reproduced: {repro}")
CODE = {"seal_fits": HERE / "scripts" / "seal_fits.py", "seal_write": Path(__file__), "build_lg_make_pairs": RN / "aiPHeed_final_model_optimization_20261113" / "scripts" / "build_lg.py",
        "final_engine": Path("C:/Users/admin/aipheed_hcw/backend/app/hcw/final_engine.py"), "base_engine": Path("C:/Users/admin/aipheed_hcw/backend/app/hcw/engine.py"),
        "inputs_builder": Path("C:/Users/admin/aipheed_hcw/backend/app/hcw/inputs.py"), "attr_research": RN / "aiPHeed_final_detection_20261113" / "scripts" / "attr_run.py"}
DATA = {"cand_panel_live": RN / "aiPHeed_final_dashboard_preview_20261113" / "out_final" / "cand_panel.parquet",
        "labels_oof": Path("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv"), "official_FINAL_seal": RN / "aiPHeed_final_official_20261113" / "evidence" / "SEALED_FINAL_2027Q1_2028Q1.json"}
now = datetime.now(timezone.utc).isoformat(timespec="seconds")
info_lg = json.load(open(PARTS / "LG__info.json"))
# ---------------- FINAL-LG
g = LGp.groupby(["province", "lead"]).agg(p=("p", "mean"), mu=("mu", "mean"), half=("half", "mean"), gap_q=("gap_q", "first"), n_pairs=("n_pairs", "first")).reset_index()
g = g.merge(off, on=["province", "lead"])
rows = [{"province": r.province, "lead": int(r.lead), "target_quarter": r.target_quarter, "p_high_FINAL_LG": round(float(r.p), 6),
         "class_FINAL_LG": "HIGH" if r.p >= .5 else "LOW", "share_pct": round(float(ex(r.mu)), 2), "range90_pct": [round(float(ex(r.mu - r.half)), 1), round(float(ex(r.mu + r.half)), 1)],
         "own_survey_gap_q": float(r.gap_q), "official_FINAL_p_for_reference": float(r.official_p_high_FINAL)} for r in g.itertuples()]
cfg_lg = {"model": "FINAL-LG (experimental): FINAL (RATE + MIND) LightGBM + genuine long-gap pair rows", "status": "EXPERIMENTAL; not official; not served",
          "definition": "PROTOCOL_OPT2 (sha f3a6fdf7): training rows re-built with FNRI2015 withheld from the anchor (NNS2013 anchor) for every released "
                        "target round after 2015, added to FINAL's training table; engine app.hcw.final_engine.fit_predict unchanged",
          "pairs": info_lg, "threshold": 0.5, "seeds": [168, 1, 2, 3, 4], "seed_aggregation": "mean probability",
          "issue_quarter": OFF["issue_quarter"], "information_cutoff": OFF["information_cutoff"], "leads": [1, 2, 3, 4, 5],
          "reproduction_of_official_FINAL_without_pairs": repro, "retrospective_evidence": "aiPHeed_final_model_optimization_20261113 (OPT2), aiPHeed_final_reformulation_20261113",
          "code_sha256": {k: sha(v) for k, v in CODE.items()}, "data_sha256": {k: sha(v) for k, v in DATA.items()},
          "parts_sha256": {Path(f).name: sha(f) for f in sorted(glob.glob(str(PARTS / "LG__L*.csv")))}}
# ---------------- ATTR (above national)
T = pickle.load(open(PARTS / "ATTR_live_tables_L1.pkl", "rb")); tr, te = T["tr"], T["te"]
tr = tr[tr.lead == 1].copy()
NAT = {"NNS2013": 0.2432467540453589, "FNRI2015": lg(.538), "ENNS2018": lg(.416), "ENNS2019": lg(.469), "ENNS2021": lg(.410)}
RQ = {8054: "NNS2013", 8062: "FNRI2015", 8074: "ENNS2018", 8078: "ENNS2019", 8086: "ENNS2021"}
S = ["income_rel", "p_poverty", "p_poverty_gap", "hh_grdp_rel", "p_subsistence"]
for d in (tr, te):
    d["z_a"] = d.y_anchor - d.rq_anchor.map(RQ).map(NAT)
zT = tr.y_true - tr.survey.map(NAT)
med = tr[S].median(); Xtr, Xte = tr[["z_a"] + S].fillna(med), te[["z_a"] + S].fillna(med); mu_, sd_ = Xtr.mean(), Xtr.std().replace(0, 1)
br = BayesianRidge().fit(((Xtr - mu_) / sd_).values, zT.values, sample_weight=(1 / (tr.se_true ** 2 + 0.05)).values)
zh, sd = br.predict(((Xte - mu_) / sd_).values, return_std=True)
at = te[["province", "key", "y_anchor", "rq_anchor"] + S].assign(z_hat=zh, sd=sd, p_above_national=norm.cdf(zh / sd))
arows = [{"province": r.province, "target_quarters": ["2027-Q1", "2027-Q2", "2027-Q3", "2027-Q4", "2028-Q1"], "p_above_national_ATTR": round(float(r.p_above_national), 6),
          "class_ATTR": "ABOVE national" if r.p_above_national >= .5 else "NOT above national", "relative_logit_z_hat": round(float(r.z_hat), 4), "predictive_sd": round(float(r.sd), 4),
          "anchor_round": RQ[int(r.rq_anchor)], "anchor_pct": round(float(ex(r.y_anchor)), 1), "inputs": {c: (None if pd.isna(getattr(r, c)) else round(float(getattr(r, c)), 4)) for c in S},
          "context_only_implied_share_pct_if_national_stays_at_2021_value": round(float(ex(r.z_hat + NAT["ENNS2021"])), 1)} for r in at.itertuples()]
cfg_at = {"model": "ATTR (experimental): Bayesian structural-attractor regression (sklearn BayesianRidge, default priors) of the national-relative HFIAS logit",
          "status": "EXPERIMENTAL; not official; not served; NOT LightGBM", "protocol": "PROTOCOL_ATTR sha 79ebae22 (aiPHeed_final_detection_20261113)",
          "label": "province HFIAS mod+sev in the target round > national HFIAS mod+sev in that round (NOT the absolute 50 % label)",
          "inputs": ["z_anchor (latest survey relative to its round's national value)"] + S, "training_transitions": sorted(tr.survey.unique().tolist()), "n_train": len(tr),
          "coef_standardised": dict(zip(["z_a"] + S, np.round(br.coef_, 5).tolist())), "national_reference_pct": {k: round(float(ex(v)), 3) for k, v in NAT.items()},
          "nns2013_national": "estimated (not published)", "issue_quarter": OFF["issue_quarter"], "information_cutoff": OFF["information_cutoff"],
          "note": "Inputs as of the 2026-Q4 issue; identical for every lead, so one probability covers 2027-Q1..2028-Q1.",
          "code_sha256": {k: sha(v) for k, v in CODE.items()}, "data_sha256": {k: sha(v) for k, v in DATA.items()}, "live_tables_sha256": sha(PARTS / "ATTR_live_tables_L1.pkl")}
for f, cfg, rws, key in ((SEAL_LG, cfg_lg, rows, "FINAL_LG"), (SEAL_AT, cfg_at, arows, "ATTR")):
    cf = EV / f"{key}_FROZEN_CONFIG.json"; cf.write_text(json.dumps(cfg, indent=1, default=str), encoding="utf-8", newline="\n")
    doc = {"sealed_utc": now, "model": cfg["model"], "status": cfg["status"], "config_sha256": sha(cf), "issue_quarter": OFF["issue_quarter"],
           "information_cutoff": OFF["information_cutoff"], "scoring_procedure": "score once against the next FNRI provincial HFIAS round covering these provinces; no refit; "
           "compare with the official FINAL seal 80b20aed" + (" (absolute 50 % label)" if key == "FINAL_LG" else " (above-national label using that round's published national value)"),
           "rows": rws}
    f.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8", newline="\n")
    Path(str(f).replace(".json", ".sha256")).write_text(f"{sha(f)}  {f.name}\n", newline="\n")
    print(key, sha(f))
print(json.dumps(repro)); print(pd.DataFrame(rows)[["province", "lead", "p_high_FINAL_LG", "class_FINAL_LG", "share_pct", "official_FINAL_p_for_reference"]].to_string(index=False))
print(pd.DataFrame(arows)[["province", "anchor_round", "anchor_pct", "p_above_national_ATTR", "class_ATTR"]].to_string(index=False))
