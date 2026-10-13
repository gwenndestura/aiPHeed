"""E12 step 1: S1 reproduction against the two reference outputs (labels.parquet stress_score; E9 s1_targets). Guarded."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import guard; guard.install()
import json
import numpy as np, pandas as pd
E9 = guard.AL / "experiments" / "2026-10-12_E9_S1_safe_training"
sys.path.insert(0, str(E9 / "runner")); sys.path.insert(0, str(guard.AL))
import scripts.supplementary.devprotocol_rule_l as D
from app.ml.features import risk_score_v2 as R
import safe_frame as F
out = {}
lab = guard.read_allowed_parquet("data/processed/labels.parquet", ["province_code", "quarter", "sws_hunger_pct", "food_cpi_yoy", "regional_food_cpi_yoy", "stress_score"])
lab = lab[(lab["quarter"] >= "2021-Q1") & (lab["quarter"] <= "2025-Q4")]
psa = guard.read_allowed_parquet("data/processed/psa_indicators.parquet", ["province_code", "quarter", "food_cpi_yoy"])
psa = psa[(psa["quarter"] >= "2021-Q1") & (psa["quarter"] <= "2025-Q4")]
e9 = pd.read_csv(E9 / "runs" / "20261012T140816Z" / "s1_targets_2021_2025.csv")
# (a) reproduce from the reference table's OWN stored components
own = R.compute_stress(lab.groupby("quarter", as_index=False)["sws_hunger_pct"].first(), lab[["province_code", "quarter", "food_cpi_yoy"]])
m = own.merge(lab[["province_code", "quarter", "stress_score"]], on=["province_code", "quarter"]).dropna(subset=["stress", "stress_score"])
out["labels_own_components_vs_stress_score"] = {"rows": int(len(m)), "max_abs_diff": float((m["stress"] - m["stress_score"]).abs().max())}
# (b) reproduce from registry SWS + psa_indicators (the E9 route)
st, rounds = F.s1_targets(D, R, psa)
m2 = st.merge(lab[["province_code", "quarter", "stress_score"]], on=["province_code", "quarter"])
out["registry_psa_vs_stress_score"] = {"rows": int(len(m2)), "max_abs_diff": float((m2["stress"] - m2["stress_score"]).abs().max())}
m3 = st.merge(e9[["province_code", "quarter", "stress"]], on=["province_code", "quarter"], suffixes=("", "_e9"))
out["registry_psa_vs_E9_reference"] = {"rows": int(len(m3)), "max_abs_diff": float((m3["stress"] - m3["stress_e9"]).abs().max())}
# (c) locate the component that differs
sws_reg = st.groupby("quarter")["sws_hunger_pct"].first()
sws_lab = lab.groupby("quarter")["sws_hunger_pct"].first().reindex(sws_reg.index)
dd = (sws_reg - sws_lab)
out["sws_component_diff_by_quarter"] = {q: float(v) for q, v in dd.items() if abs(v) > 1e-12}
fc = psa.merge(lab[["province_code", "quarter", "food_cpi_yoy"]], on=["province_code", "quarter"], suffixes=("_psa", "_lab")).dropna()
out["food_cpi_yoy_max_abs_diff_psa_vs_labels"] = float((fc["food_cpi_yoy_psa"] - fc["food_cpi_yoy_lab"]).abs().max())
multi = {q: len([r for r in rounds if r.quarter == q and r.in_label_definition_A]) for q in sws_reg.index}
out["definitionA_rounds_per_quarter_where_sws_differs"] = {q: multi[q] for q in out["sws_component_diff_by_quarter"]}
# (d) thresholds from each reference
pub = lambda q: D.label_published(q, "development")[0]
s_lab = lab.dropna(subset=["stress_score"]).rename(columns={"stress_score": "stress"})[["province_code", "quarter", "stress"]]
t_lab, q_lab = R.reference_threshold(s_lab, pub, pd.Timestamp("2023-10-01"))
t_e9, q_e9 = R.reference_threshold(st[["province_code", "quarter", "stress"]], pub, pd.Timestamp("2023-10-01"))
out["tau0_from_labels_parquet"] = {"value": t_lab, "quarters": q_lab}
out["tau0_from_E9_components"] = {"value": t_e9, "quarters": q_e9}
served_meta = json.loads((guard.AL / "data" / "revised" / "revised_forecasts_retrospective_meta.json").read_text(encoding="utf-8")) if False else None
(guard.EXP / "s1_reproduction_investigation.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
