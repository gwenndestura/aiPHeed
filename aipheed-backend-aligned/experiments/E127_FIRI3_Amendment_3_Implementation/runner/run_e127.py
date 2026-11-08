"""E127: implement Amendment 3 (verified zero-storm PAR quarters) through the data layer, rebuild FIRI3 history (v1.3),
reconcile with v1.2, reproduce the 2026-Q4 regional PAR percentile, freeze the v1.3 validation configuration and
record versions and hashes. No forecast is issued; E121-E126 outputs are not modified.

    python run_e127.py [--today YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
REPO = EXP.parent.parent
B = REPO / "backend"
E124, E125, E126 = EXP / "E124_FIRI3_Prospective_Validation", EXP / "E125_FIRI3_Pre_Issuance", EXP / "E126_FIRI3_Pre_Issuance_Maintenance"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(E124 / "runner"))
import firi3_inputs as I                      # noqa: E402
from app.ml.inference import firi3 as F3      # noqa: E402
import store as S                             # noqa: E402
import run_e124 as R124                       # noqa: E402

ORIGINS = list(range(F3.START_Q, 2026 * 4 + 3))
T = F3.qindex("2026-Q4")
CONFIG = ROOT / "E127_FROZEN_VALIDATION_CONFIGURATION_v1_3.json"


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def config_v13() -> dict:
    cfg = R124.frozen_config()                                   # built from firi3 constants (now v1.3)
    cfg["name"] = "FIRI3 prospective validation configuration (v1.3)"
    cfg["amendment_3"] = {"file": "experiments/E127_FIRI3_Amendment_3_Implementation/E127_FIRI3_PROTOCOL_AMENDMENT_3.md", "sha256": F3.AMENDMENT_3_SHA256,
                          "rule": "PAR count: every quarter the IBTrACS file covers completely is recorded, 0 when no storm qualifies; uncovered quarters stay missing",
                          "data_layer": "experiments/E127_FIRI3_Amendment_3_Implementation/runner/par_counts.py", "approved": "owner, E127 instruction section 1"}
    cfg["inputs_builder"] = "experiments/E127_FIRI3_Amendment_3_Implementation/runner/firi3_inputs.py"
    cfg["supersedes"] = {"file": "experiments/E124_FIRI3_Prospective_Validation/E124_FROZEN_VALIDATION_CONFIGURATION.json",
                         "canonical_sha256": (E124 / "E124_FROZEN_VALIDATION_CONFIGURATION.sha256").read_text().strip(), "version": "FIRI3-candidate-1.2"}
    return cfg


def write_config() -> str:
    cfg = config_v13()
    blob = S.canonical(cfg)
    h = hashlib.sha256(blob).hexdigest()
    if CONFIG.exists():
        assert S.canonical(json.loads(CONFIG.read_text())) == blob, "v1.3 configuration differs from the module: a new version is required (refused)"
    else:
        CONFIG.write_text(json.dumps(cfg, indent=1, sort_keys=True))
        (ROOT / "E127_FROZEN_VALIDATION_CONFIGURATION_v1_3.sha256").write_text(h + "\n")
    assert (ROOT / "E127_FROZEN_VALIDATION_CONFIGURATION_v1_3.sha256").read_text().strip() == h
    return h


def main(today: date):
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    hashes = {"protocol": sha(EXP / "E121_FIRI3_Implementation" / "E121_FIRI3_PROTOCOL.md"), "amendment_1": sha(EXP / "E122_Data_Cutoff_Audit" / "E122_FIRI3_PROTOCOL_AMENDMENT_1.md"),
              "amendment_2": sha(EXP / "E123_FIRI3_Design_Resolution" / "E123_FIRI3_PROTOCOL_AMENDMENT_2.md"), "amendment_3": sha(ROOT / "E127_FIRI3_PROTOCOL_AMENDMENT_3.md")}
    hashes_ok = (hashes["protocol"] == F3.PROTOCOL_SHA256 and hashes["amendment_1"] == F3.AMENDMENT_1_SHA256 and hashes["amendment_2"] == F3.AMENDMENT_2_SHA256
                 and hashes["amendment_3"] == F3.AMENDMENT_3_SHA256 == (HERE / "AMENDMENT_3_SHA256.txt").read_text().strip())
    assert hashes_ok
    cfg_sha = write_config()

    # ---------------- inputs: v1.2 (E125 state) and v1.3
    o12, ann, _ = I.build(amendment_3=False)
    o13, _, prov = I.build(amendment_3=True)
    pq = prov["par_quarterly"]
    ev126 = pd.read_csv(E126 / "E126_PAR_ZERO_STORM_VERIFICATION.csv")
    e114 = pd.read_csv(EXP / "E114_Final_Run" / "data" / "cov_ibtracs_par.csv").set_index("q")["tc_par"]
    pq["e114_series_value"] = [("absent" if int(q) not in e114.index else int(e114[int(q)])) for q in pq["q"]]
    pq["matches_e114_where_present"] = [(v == "absent") or (c == v) for c, v in zip(pq["count"], pq["e114_series_value"])]
    pq["note"] = ["E114 value counts WP172026 (SAUDEL) twice under two SIDs; one storm under the E125 storm key; E119 never used this E114 value (series cut at 2026-Q2)"
                  if (v != "absent" and c == c and c != v and q == 2026 * 4 + 2) else "" for q, c, v in zip(pq["q"], pq["count"], pq["e114_series_value"])]
    pq["e126_verification"] = pq["quarter"].map(lambda q: "; ".join(f"{r.source}: {r.verdict}" for r in ev126[ev126["quarter"] == q].itertuples()))
    pq["explicit_zero_added"] = pq["covered"] & (pq["count"] == 0) & (pq["e114_series_value"] == "absent")
    pq.to_csv(ROOT / "E127_PAR_ZERO_STORM_DATA.csv", index=False, lineterminator="\n")
    added = sorted(pq.loc[pq["explicit_zero_added"], "quarter"])
    par_diff = o12[o12["feature"] == "typhoons_PAR"][["period", "value"]].merge(o13[o13["feature"] == "typhoons_PAR"][["period", "value"]], on="period", how="outer", suffixes=("_v12", "_v13"))
    par_diff = par_diff[par_diff["period"] >= F3.START_Q]
    only_zeros_changed = bool(set(par_diff.loc[(par_diff["value_v12"] != par_diff["value_v13"]), "period"].map(F3.qlabel)) == set(added))
    others_equal = bool(((par_diff["value_v12"] == par_diff["value_v13"]) | par_diff["period"].map(F3.qlabel).isin(added)).all())
    rest_equal = o12[o12["feature"] != "typhoons_PAR"].sort_values(["feature", "unit", "period"]).reset_index(drop=True)[["feature", "unit", "period", "value", "avail"]].equals(
        o13[o13["feature"] != "typhoons_PAR"].sort_values(["feature", "unit", "period"]).reset_index(drop=True)[["feature", "unit", "period", "value", "avail"]])

    # ---------------- recompute
    R12 = F3.compute(o12, ann, ORIGINS)
    R13 = F3.compute(o13, ann, ORIGINS)
    R13b = F3.compute(o13.sample(frac=1, random_state=13), ann, ORIGINS)
    deterministic = R13["overall"].to_csv(index=False) == R13b["overall"].to_csv(index=False)
    e125 = pd.read_csv(E125 / "E125_SCORE_RECONCILIATION.csv")
    e125["t"] = e125["origin"].map(F3.qindex)
    m12 = e125.merge(R12["overall"], on=["scope", "unit", "t"])
    v12_reproduces_e125 = bool(len(m12) == 138 and np.allclose(m12["firi3_refreshed"].fillna(-9), m12["firi3"].fillna(-9), atol=1e-8) and (m12["band_refreshed"] == m12["band"]).all())
    e126 = pd.read_csv(E126 / "E126_HISTORICAL_SCORE_RECONCILIATION.csv")
    m13 = e126.merge(R13["overall"], on=["scope", "unit", "t"])
    v13_reproduces_e126_proposal = bool(len(m13) == 138 and np.allclose(m13["e126_proposed_a3"].fillna(-9), m13["firi3"].fillna(-9), atol=1e-8)
                                        and (m13["band_e126_proposed"] == m13["band"]).all())

    # ---------------- reconciliation (all 138 unit-origins)
    f12 = R12["features"][R12["features"]["feature"] == "CEC_cyclones_R"][["unit", "t", "period", "raw_value", "score", "prior_n"]]
    f13 = R13["features"][R13["features"]["feature"] == "CEC_cyclones_R"][["unit", "t", "period", "raw_value", "score", "prior_n"]]
    rec = R12["overall"][["scope", "unit", "t", "origin", "firi3", "band", "indicators_used"]].merge(
        R13["overall"][["scope", "unit", "t", "firi3", "band", "indicators_used"]], on=["scope", "unit", "t"], suffixes=("_v12", "_v13"))
    rec = rec.merge(f12.rename(columns={"period": "par_quarter_v12", "raw_value": "par_value_v12", "score": "par_score_v12", "prior_n": "par_prior_n_v12"}), on=["unit", "t"], how="left")
    rec = rec.merge(f13.rename(columns={"period": "par_quarter_v13", "raw_value": "par_value_v13", "score": "par_score_v13", "prior_n": "par_prior_n_v13"}), on=["unit", "t"], how="left")
    rec["abs_difference"] = (rec["firi3_v13"] - rec["firi3_v12"]).abs()
    rec["changed"] = (rec["abs_difference"].fillna(0) > 1e-12) | (rec["band_v12"] != rec["band_v13"])
    def why(r):
        if r.scope == "provincial":
            return "unchanged: provincial scores do not use the PAR count"
        if not r.changed:
            return "unchanged: regional FIRI3 not computable" if pd.isna(r.firi3_v12) else "unchanged"
        parts = []
        if str(r.par_quarter_v12) != str(r.par_quarter_v13) or (r.par_value_v12 != r.par_value_v13):
            parts.append(f"as-of PAR value: {r.par_quarter_v12} = {r.par_value_v12:g} -> {r.par_quarter_v13} = {r.par_value_v13:g} (zero quarter now recorded)")
        if r.par_prior_n_v12 != r.par_prior_n_v13 or abs((r.par_score_v12 or 0) - (r.par_score_v13 or 0)) > 1e-12:
            parts.append(f"percentile reference history {int(r.par_prior_n_v12)} -> {int(r.par_prior_n_v13)} values (explicit zeros added); PAR score {r.par_score_v12:.4f} -> {r.par_score_v13:.4f}")
        return "Amendment 3: " + "; ".join(parts)
    rec["explanation"] = [why(r) for r in rec.itertuples()]
    rec.to_csv(ROOT / "E127_HISTORICAL_SCORE_RECONCILIATION.csv", index=False, lineterminator="\n", float_format="%.10g")
    ch = rec[rec["changed"]]
    fs_cmp = R12["features"].merge(R13["features"], on=["scope", "unit", "t", "feature"], suffixes=("_v12", "_v13"))
    other_feature_changes = fs_cmp[(fs_cmp["feature"] != "CEC_cyclones_R") & ~np.isclose(fs_cmp["score_v12"].fillna(-9), fs_cmp["score_v13"].fillna(-9), atol=1e-12)]
    ind_cmp = R12["indicators"].merge(R13["indicators"], on=["scope", "unit", "t", "indicator"], suffixes=("_v12", "_v13"))
    other_ind_changes = ind_cmp[(ind_cmp["indicator"] != "CEC") & ~np.isclose(ind_cmp["score_v12"].astype(float).fillna(-9), ind_cmp["score_v13"].astype(float).fillna(-9), atol=1e-12)]
    ccs12 = F3.subscore(R12["indicators"], F3.CONDITIONS, "CCS")
    ccs13 = F3.subscore(R13["indicators"], F3.CONDITIONS, "CCS")
    cm = ccs12.merge(ccs13, on=["scope", "unit", "t"], suffixes=("_v12", "_v13"))
    ccs_changed = cm[~np.isclose(cm["score_v12"].astype(float).fillna(-9), cm["score_v13"].astype(float).fillna(-9), atol=1e-12)]
    impact = {"changed": int(len(ch)), "scopes": sorted(set(ch["scope"])), "origins": sorted(ch["origin"]), "provincial_changed": int((ch["scope"] == "provincial").sum()),
              "max_abs_change": round(float(ch["abs_difference"].max()), 6), "band_changes": ch.loc[ch["band_v12"] != ch["band_v13"], ["origin", "band_v12", "band_v13"]].to_dict("records"),
              "other_feature_score_changes": int(len(other_feature_changes)), "other_indicator_changes": int(len(other_ind_changes)), "ccs_changed": int(len(ccs_changed)),
              "computable_v12": R12["overall"].groupby("scope")["firi3"].apply(lambda s: int(s.notna().sum())).to_dict(),
              "computable_v13": R13["overall"].groupby("scope")["firi3"].apply(lambda s: int(s.notna().sum())).to_dict()}
    # FIRI v2 comparison: provincial only
    v2 = pd.read_csv(B / "data" / "thesis" / "firi2_history.csv")
    impact["firi_v2_comparison_rows_changed"] = int(len(ch[(ch["scope"] == "provincial")]))

    # ---------------- leakage
    s13 = R13["features"][R13["features"]["score"].notna()]
    leak = {"scored_values_available_before_issue": bool((s13["avail_date"].astype(str) < s13["issue_date"].astype(str)).all()),
            "par_rows_only_covered_quarters": bool(pq.loc[pq["status"] == "verified", "covered"].all() and not (o13[o13["feature"] == "typhoons_PAR"]["period"] == 2026 * 4 + 3).any()),
            "par_zero_avail_after_quarter": bool(all(F3.issue_date(F3.qindex(q)) > F3.issue_date(F3.qindex(q) - 1) for q in added)),
            "no_pre2021": bool((s13["period"].astype(str).str[:4].astype(int) >= 2021).all()),
            "amendment_1_rows": R13["log"]["pre2021_base_rows_rejected"], "amendment_1_by_series": R13["log"]["pre2021_base_rows_by_series"]}
    ehs = R13["features"][R13["features"]["feature"].isin(["EHS_unemployment_prov", "EHS_underemployment_prov"]) & (R13["features"]["origin"].isin(["2026-Q2", "2026-Q3"]))]
    leak["amendment_2_year_2026_origins"] = sorted(set(ehs["period"].astype(str)))
    leak["amendment_2_note"] = sorted(set(ehs["note"].dropna()) - {""})

    # ---------------- 2026-Q4 regional PAR feature (dry run; nothing issued or kept as a forecast)
    q4 = {}
    for name, o in (("v1.2", o12), ("v1.3", o13)):
        clean = F3.validate_inputs(o, ann)[0]
        f = next(x for x in F3.FEATURES if x.code == "CEC_cyclones_R")
        r = F3._dynamic(clean, f, T)[0]
        s_ = clean[(clean["feature"] == "typhoons_PAR") & (clean["avail"].astype(str) < F3.issue_date(T))]
        prior = s_[s_["period"] < F3.qindex(r["period"])]["value"].to_numpy()
        rep = F3.midrank(float(r["aligned_value"]), prior)
        q4[name] = {"period_used": r["period"], "count": r["raw_value"], "avail": r["avail_date"], "score": round(r["score"], 6), "prior_n": int(len(prior)),
                    "prior_values_sorted": sorted(float(v) for v in prior), "below": int((prior < r["aligned_value"]).sum()), "equal": int((prior == r["aligned_value"]).sum()),
                    "independent_midrank": round(rep, 6), "reproduces": abs(rep - r["score"]) < 1e-12,
                    "future_values_in_reference": int((s_["period"] >= T).sum())}
    fs4_12 = F3.feature_scores(*F3.validate_inputs(o12, ann)[:2], [T])
    fs4_13 = F3.feature_scores(*F3.validate_inputs(o13, ann)[:2], [T])
    m4 = fs4_12.merge(fs4_13, on=["scope", "unit", "feature"], suffixes=("_v12", "_v13"))
    q4["other_features_changed_at_2026q4"] = sorted(set(m4.loc[~np.isclose(m4["score_v12"].fillna(-9), m4["score_v13"].fillna(-9), atol=1e-12), "feature"]) - {"CEC_cyclones_R"})
    q4["provincial_features_changed_at_2026q4"] = int(((m4["scope"] == "provincial") & ~np.isclose(m4["score_v12"].fillna(-9), m4["score_v13"].fillna(-9), atol=1e-12)).sum())

    # ---------------- store and baseline state
    st = S.Store(E124 / "store")
    state = {"forecasts": sorted(p.name for p in (E124 / "store" / "forecasts").iterdir()), "events": [(e["event"], e.get("attempt_date"), e.get("forecast_id")) for e in st.events()],
             "next_forecast_id": S.forecast_id("2026-Q4")}
    v2h = {str(p.relative_to(REPO)): sha(p) for p in (B / "app" / "ml" / "inference" / "firi.py", B / "data" / "thesis" / "firi2_history.csv", B / "data" / "thesis" / "firi2_reference.json")}
    summary = {"today": today.isoformat(), "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip(),
               "firi3_version": F3.VERSION, "hashes": hashes, "hashes_ok": hashes_ok, "config_v13_sha256": cfg_sha,
               "config_v12_sha256": (E124 / "E124_FROZEN_VALIDATION_CONFIGURATION.sha256").read_text().strip(), "provenance": {k: v for k, v in prov.items() if k != "par_quarterly"},
               "explicit_zeros_added": added, "only_zero_quarters_changed": only_zeros_changed, "other_par_quarters_equal": others_equal, "other_inputs_identical": rest_equal,
               "v12_reproduces_e125": v12_reproduces_e125, "v13_reproduces_e126_proposal": v13_reproduces_e126_proposal, "deterministic": deterministic,
               "impact": impact, "leakage": leak, "q4_2026": q4, "store": state, "firi_v2": v2h,
               "e126_outputs_sha256": {p.name: sha(p) for p in sorted(E126.glob("E126_*"))}}
    json.dump(summary, open(out / "summary.json", "w"), indent=1, default=str)
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=date.today().isoformat())
    main(date.fromisoformat(ap.parse_args().today))
