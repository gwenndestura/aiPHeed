"""E124: freeze the FIRI3 prospective-validation configuration, audit source release status and feature eligibility for
the 2026-Q4 origin (issue 2027-01-01), record the (blocked) issuance attempt, and build the FIRI3 vs FIRI v2 comparison.
No forecast is issued before its issue date; nothing here fabricates observations.

    python run_e124.py [--today YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
REPO = EXP.parent.parent
B = REPO / "backend"
sys.path.insert(0, str(B))
sys.path.insert(0, str(EXP / "E120_FIRI_Consolidated_Design" / "runner"))
sys.path.insert(0, str(HERE))
from app.ml.inference import firi3 as F3      # noqa: E402
from app.ml.inference import firi as FI       # noqa: E402  (read only)
import e120 as E120                           # noqa: E402
import store as S                             # noqa: E402

P = E120.P
ORIGIN = "2026-Q4"
T = F3.qindex(ORIGIN)
ISSUE = F3.issue_date(T)
CONFIG = ROOT / "E124_FROZEN_VALIDATION_CONFIGURATION.json"
E123 = EXP / "E123_FIRI3_Design_Resolution"
PUBCLASS = pd.read_csv(E123 / "E123_PUBLICATION_DATE_AUDIT.csv").set_index("feature")["classification"].to_dict()


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def source_files() -> dict:
    files = dict(P.INPUTS)
    for p in (B / "data" / "news_e31" / "articles.jsonl", B / "data" / "news_e60" / "articles.jsonl", B / "data" / "news_v3" / "scores.jsonl"):
        files[f"news:{p.parent.name}/{p.name}"] = p
    return {k: Path(v) for k, v in files.items() if Path(v).exists()}


# ------------------------------------------------------------------------------------------------ frozen configuration
def frozen_config() -> dict:
    return {
        "name": "FIRI3 prospective validation configuration", "firi3_version": F3.VERSION, "module": "backend/app/ml/inference/firi3.py",
        "protocol": {"file": "experiments/E121_FIRI3_Implementation/E121_FIRI3_PROTOCOL.md", "sha256": F3.PROTOCOL_SHA256},
        "amendment_1": {"file": "experiments/E122_Data_Cutoff_Audit/E122_FIRI3_PROTOCOL_AMENDMENT_1.md", "sha256": F3.AMENDMENT_1_SHA256,
                        "rule": "change-type series admitted only from 2022-Q1 (2021+ comparison base)", "base_required_series": sorted(F3.BASE_REQUIRED)},
        "amendment_2": {"file": "experiments/E123_FIRI3_Design_Resolution/E123_FIRI3_PROTOCOL_AMENDMENT_2.md", "sha256": F3.AMENDMENT_2_SHA256,
                        "rules": ["annual features: latest COMPLETE published year; newer incomplete years skipped",
                                  "supplementary CCS (FMA AFP CEC FIS, >= 3 of 4) and SVS (EHS PSV, both, provincial only)",
                                  "fixed core FMA AFP CEC EHS; cross-province core (>= 3 common indicators)"]},
        "indicators": F3.INDICATORS,
        "features": [{"code": f.code, "indicator": f.indicator, "component": f.component, "scope": f.scope, "series": f.series, "series_unit": f.unit,
                      "direction": f.direction, "transform": f.transform, "normalization": f.normalization, "dataset": f.dataset} for f in F3.FEATURES],
        "weights": {i: 1.0 for i in F3.INDICATORS}, "component_weights": "equal (mean of scored features), components equal within an indicator",
        "aggregation": {"feature": "expanding mid-rank percentile among earlier available 2021+ observations of the scope (>= %d), or cross-province mid-rank (rank5)" % F3.MIN_PRIOR,
                        "indicator": "mean of available components; needs >= ceil(defined/2)", "firi3": "equal-weighted mean of available indicators"},
        "completeness": {"provincial": "4 of 6", "regional": "4 of 5", "ccs": "3 of 4", "svs": "2 of 2 (provincial only)", "max_staleness_quarters": F3.MAX_STALE},
        "risk_bands": {"sd_k": "sqrt(1/12)/sqrt(k)", "usual or below": "< 0.5", "above usual": "< 0.5 + sd_k", "elevated": "< 0.5 + 1.645 sd_k", "high": ">= 0.5 + 1.645 sd_k",
                       "meaning": "relative to the 2021+ usual level; not a probability"},
        "cutoff": {"first_period": "2021-Q1", "first_change_period": "2022-Q1", "last_period": "2026-Q4", "rule": "pre-2021 rows rejected; change rows need a 2021+ base"},
        "publication_eligibility": {"rule": "a value is used only if its availability date is strictly before the issue date",
                                    "classes": ["verified", "provisionally eligible", "unverified", "ineligible"], "by_feature": PUBCLASS},
        "geography": {"provincial_units": list(F3.PROVINCES), "regional_units": list(F3.REGIONAL_UNITS), "regional_label": F3.REGION_LABEL,
                      "rule": "provincial scores from provincial observations only; national values never copied into provinces"},
        "issue": {"issue_date_rule": "O(t) = first day of quarter t+1, 00:00 PHT", "first_prospective_origin": ORIGIN, "first_issue_date": ISSUE},
        "issuance_conditions": ["C1: the run date is on or after the issue date",
                                "C2: firi3 version and protocol / amendment hashes equal this configuration",
                                "C3: every source was retrieved on or after the date its rule makes the needed period available (or is documented as not yet released / discontinued)",
                                "C4: no input value with availability date on or after the issue date is scored"],
        "snapshot_schema": "experiments/E124_FIRI3_Prospective_Validation/E124_SNAPSHOT_SCHEMA.md",
        "evaluation_rules": ["forecast stability: issued snapshot files and content hash unchanged",
                             "data revision sensitivity: same observation period, different value, in a later recomputation",
                             "prospective measurement behaviour: later periods or availability changes in a later recomputation",
                             "SWS: descriptive external comparison only; never used to tune",
                             "no tuning from prospective results; any change is a new version and never overwrites issued snapshots"],
    }


def write_config() -> str:
    cfg = frozen_config()
    blob = S.canonical(cfg)
    h = hashlib.sha256(blob).hexdigest()
    if CONFIG.exists():
        old = json.loads(CONFIG.read_text())
        assert S.canonical(old) == blob, "frozen configuration differs from firi3: a new version is required (refused)"
    else:
        CONFIG.write_text(json.dumps(cfg, indent=1, sort_keys=True))
        (ROOT / "E124_FROZEN_VALIDATION_CONFIGURATION.sha256").write_text(h + "\n")
    assert (ROOT / "E124_FROZEN_VALIDATION_CONFIGURATION.sha256").read_text().strip() == h
    return h


# ------------------------------------------------------------------------------------------------ release status / eligibility
RETRIEVED = {"cpi_yoy_prov": None, "cpi_region_index": "2026-10-25", "rice_whsl": None, "stack": None, "par": "2026-10-25", "lfs": "2026-10-25",
             "gdelt": "2026-10-25", "remit": "2026-10-30", "profile": "2026-10-30", "emp_owner": "2026-10-30", "vuln": None}
SERIES_SOURCE = {"cpi_food_yoy_pct": "cpi_yoy_prov", "cpi_headline_yoy_pct": "cpi_yoy_prov", "region_cpi_food_yoy_pct": "cpi_region_index",
                 "region_cpi_headline_yoy_pct": "cpi_region_index", "rice_wholesale_yoy_pct": "rice_whsl", "retail_chicken_yoy_pct": "e118_retail_poultry",
                 "retail_pork_yoy_pct": "e118_retail_livestock", "retail_tilapia_yoy_pct": "e118_retail_fish", "farmgate_palay_yoy_pct": "e118_farmgate_cereals",
                 "palay_production_yoy_pct": "e118_prod_palay_corn", "corn_production_yoy_pct": "e118_prod_palay_corn",
                 "vegetables_only_production_yoy_pct": "e118_prod_vegetables_rootcrops", "rootcrops_only_production_yoy_pct": "e118_prod_vegetables_rootcrops",
                 "fisheries_production_yoy_pct": "e118_prod_fisheries", "chicken_production_yoy_pct": "e118_prod_chicken", "livestock_production_yoy_pct": "e118_prod_livestock",
                 "rainfall_anomaly_mm": "e118_nasa_power_monthly", "temperature_anomaly_c": "e118_nasa_power_monthly", "typhoons_local_100km": "profile",
                 "typhoons_PAR": "par", "E1_unemployment_change_pp": "lfs", "E2_remittance_decline_pct": "remit", "N1_fssi_v3": "stack",
                 "news_gdelt_shortage_share": "gdelt", "provincial_unemployment_rate_pct_annual": "emp_owner",
                 "provincial_underemployment_rate_pct_annual": "emp_owner", "poverty_incidence_popweighted_pct": "vuln"}


def _qend_month_day(q, months_after, day):
    """Day `day` of the month `months_after` months after the quarter's last month."""
    y, m = q // 4, (q % 4) * 3 + 3 + months_after
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    return date(y, m, day)


def _qstart(q):
    return date.fromisoformat(F3.issue_date(q - 1))


RULES = {  # exact documented availability rules used by E119 (period -> availability date), checked against the inputs below
    **{s_: (lambda q: _qend_month_day(q, 1, 10), "CPI: day 10 of the month after the quarter's last month") for s_ in
       ("cpi_food_yoy_pct", "cpi_headline_yoy_pct", "region_cpi_food_yoy_pct", "region_cpi_headline_yoy_pct")},
    **{s_: (lambda q: _qend_month_day(q, 1, 15), "retail / farmgate prices: day 15 of the following month") for s_ in
       ("retail_chicken_yoy_pct", "retail_pork_yoy_pct", "retail_tilapia_yoy_pct", "farmgate_palay_yoy_pct")},
    **{s_: (lambda q: _qstart(q + 2), "start of quarter q+2") for s_ in
       ("rice_wholesale_yoy_pct", "palay_production_yoy_pct", "corn_production_yoy_pct", "vegetables_only_production_yoy_pct", "rootcrops_only_production_yoy_pct",
        "fisheries_production_yoy_pct", "chicken_production_yoy_pct", "livestock_production_yoy_pct", "E2_remittance_decline_pct")},
    **{s_: (lambda q: _qend_month_day(q, 2, 1), "NASA POWER: first day of month m+2") for s_ in ("rainfall_anomaly_mm", "temperature_anomaly_c")},
    **{s_: (lambda q: _qstart(q + 1), "start of quarter q+1 (quarter complete)") for s_ in ("typhoons_local_100km", "typhoons_PAR", "N1_fssi_v3", "news_gdelt_shortage_share")},
    "E1_unemployment_change_pp": (lambda q: _qend_month_day(q, 3, 1), "LFS: first day of month m+3"),
}


def rules_reproduce_inputs(obs) -> dict:
    """Share of input rows whose availability date equals the documented rule (archived dates may be earlier)."""
    out = {}
    for s_, (fn, _) in RULES.items():
        r = obs[obs["feature"] == s_]
        if len(r):
            eq = [str(a)[:10] == fn(int(p)).isoformat() for a, p in zip(r["avail"], r["period"])]
            le = [str(a)[:10] <= fn(int(p)).isoformat() for a, p in zip(r["avail"], r["period"])]
            out[s_] = {"rows": len(r), "equal_rule_pct": round(100 * float(np.mean(eq)), 1), "not_later_than_rule_pct": round(100 * float(np.mean(le)), 1)}
    return out


def retrieved_on(key: str) -> str:
    if key.startswith("e118_"):
        return "2026-10-31"
    if RETRIEVED.get(key):
        return RETRIEVED[key]
    p = Path(P.INPUTS[key])
    out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%ad", "--date=short", "--", str(p)], cwd=REPO, capture_output=True, text=True).stdout.split()
    return out[-1] if out else "unknown"


def release_status(obs, ann, today: date):
    rows = []
    for f in F3.FEATURES:
        src = SERIES_SOURCE[f.series]
        units = list(F3.PROVINCES) if f.scope == "P" else [f.unit]
        ret = retrieved_on(src)
        if f.normalization == "rank5":
            a = ann[ann["feature"] == f.series]
            yrs = a.groupby("ref")["unit"].agg(lambda s: set(s) >= set(F3.PROVINCES))
            needed = str(int(ISSUE[:4]) - 2) if f.series != "poverty_incidence_popweighted_pct" else "2021"   # Y published by 30 June Y+1 (rule)
            complete = sorted(y for y, ok in yrs.items() if ok)
            if f.series == "poverty_incidence_popweighted_pct":
                status, note = "not applicable", "static profile (SAE 2021); no new release expected for the issue"
            elif needed in yrs.index and not yrs[needed]:
                status, note = "retrieved but incomplete", f"{needed} lacks: {sorted(set(F3.PROVINCES) - set(a[a['ref'] == needed]['unit']))}; latest complete {complete[-1] if complete else '-'}"
            elif needed in yrs.index:
                status, note = "released (publication date unverified)", ""
            else:
                status, note = "not yet released", ""
            rows.append({"feature": f.code, "dataset": f.dataset, "source_key": src, "scope": "provincial", "target_observation_period": needed,
                         "expected_release_rule": "30 June of Y+1 (assumption)" if "employment" in f.series else "2025-07-01 (V1 assumption)",
                         "expected_available_on": f"{int(needed) + 1}-06-30" if "employment" in f.series else "2025-07-01", "latest_in_hand": max(yrs.index) if len(yrs) else "",
                         "latest_complete_in_hand": complete[-1] if complete else "", "retrieved_on": ret, "actual_publication_date": "not verified",
                         "availability_status": status, "verification_status": PUBCLASS.get(f.code, ""), "note": note})
            continue
        s = obs[(obs["feature"] == f.series) & obs["unit"].isin(units)]
        rule = RULES[f.series]
        avail_of = rule[0]
        need = max(q for q in range(T - 8, T + 1) if avail_of(q).isoformat() < ISSUE)            # latest period the rule makes available before the issue
        released_by_today = max(q for q in range(T - 8, T + 1) if avail_of(q) <= today)
        have = s.groupby("unit")["period"].max()
        have_min = int(have.min()) if len(have) else None
        if f.series == "N1_fssi_v3":                                                              # sparse by design (>= 5 articles): coverage = corpus end date
            corpus_end = "2026-10-14"
            have_min = max(q for q in range(T - 8, T + 1) if F3.issue_date(q) <= corpus_end)
        exp_on = avail_of(need)
        partial_note = ""
        if f.series == "E1_unemployment_change_pp":                                               # E119 uses the mean of the survey months held
            lf = pd.read_csv(P.INPUTS["lfs"], encoding="latin-1")
            mon = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            held = lf[(lf["Year"] == need // 4) & lf["Month"].isin(mon[(need % 4) * 3:(need % 4) * 3 + 3])]
            n_held = int(pd.to_numeric(held["Unemployment Rate Both sexes"], errors="coerce").notna().sum())
            if n_held < 3:
                partial_note = f"{n_held} of 3 survey months of {F3.qlabel(need)} held; the last is due {exp_on.isoformat()}"
        if partial_note:
            status = "retrieved but incomplete"
        elif have_min is not None and have_min < min(released_by_today, need) and src not in ("profile", "par"):
            status = "released per rule but not retrieved (refresh needed)"
        elif src in ("profile", "par") and (have_min is None or have_min < need):
            status = "retrieved but incomplete"
        elif have_min is not None and have_min >= need:
            status = "released (publication date unverified)" if PUBCLASS.get(f.code) != "verified" else "released and verified"
        else:
            status = "not yet released"
        rows.append({"feature": f.code, "dataset": f.dataset, "source_key": src, "scope": "provincial" if f.scope == "P" else "regional",
                     "target_observation_period": F3.qlabel(need), "expected_release_rule": rule[1], "latest_released_by_today_per_rule": F3.qlabel(released_by_today),
                     "expected_available_on": exp_on.isoformat(), "latest_in_hand": F3.qlabel(have_min) if have_min is not None else "",
                     "latest_complete_in_hand": F3.qlabel(int(have.min())) if len(have) else "", "retrieved_on": ret,
                     "actual_publication_date": "verified (dated source)" if PUBCLASS.get(f.code) == "verified" else "not verified",
                     "availability_status": status, "verification_status": PUBCLASS.get(f.code, ""),
                     "note": ("NASA POWER monthly endpoint returned data only to 2025-12 at retrieval (E118)" if "nasa" in src else
                              "2026-Q3 count was incomplete at retrieval (quarter in progress)" if src == "profile" else
                              "E119 kept PAR to 2026-Q2 (2026-Q3 incomplete at retrieval)" if src == "par" else
                              "article corpus collected to 2026-10-14" if src == "stack" else partial_note)})
    return pd.DataFrame(rows)


def eligibility_dry_run(obs, ann, rs) -> pd.DataFrame:
    """With the inputs held today, which value each feature WOULD take at the 2026-Q4 issue (diagnostic only; no scores kept)."""
    fs = F3.feature_scores(F3.validate_inputs(obs, ann)[0], F3.validate_inputs(obs, ann)[1], [T])
    out = []
    for f in F3.FEATURES:
        r = fs[fs["feature"] == f.code]
        exp = rs.set_index("feature").loc[f.code]
        per = sorted(set(r["period"].dropna().astype(str)))
        st = r["status"].value_counts().to_dict()
        ok = r["score"].notna().any()
        out.append({"feature": f.code, "indicator": f.indicator, "scope": "provincial" if f.scope == "P" else "regional", "dataset": f.dataset,
                    "series_unit": f.unit or "province (5)", "transformation": ("|x|" if f.transform == "abs" else "x") + (" x -1" if f.direction < 0 else ""),
                    "normalization": f.normalization, "period_used_with_current_holdings": "; ".join(per), "period_expected_by_release_rule": exp["target_observation_period"],
                    "statuses_with_current_holdings": "; ".join(f"{k}: {v}" for k, v in st.items()),
                    "eligible_with_current_holdings": bool(ok), "publication_class": PUBCLASS.get(f.code, ""),
                    "cutoff_2021": True, "amendment_1_base_ok": f.series not in F3.BASE_REQUIRED or bool((r["period"].dropna().map(lambda p: F3.qindex(p) if "-Q" in str(p) else 9e9) >= F3.FIRST_CHANGE_Q).all()),
                    "gap": "" if exp["availability_status"].startswith("released") else exp["availability_status"],
                    "exclusion_reason_if_issued_now": "" if ok else "; ".join(sorted(set(r["status"])))})
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------ main
def main(today: date):
    hashes_ok = (sha(EXP / "E121_FIRI3_Implementation" / "E121_FIRI3_PROTOCOL.md") == F3.PROTOCOL_SHA256
                 and sha(EXP / "E122_Data_Cutoff_Audit" / "E122_FIRI3_PROTOCOL_AMENDMENT_1.md") == F3.AMENDMENT_1_SHA256
                 and sha(E123 / "E123_FIRI3_PROTOCOL_AMENDMENT_2.md") == F3.AMENDMENT_2_SHA256)
    assert hashes_ok
    cfg_sha = write_config()
    L, ann = E120.load()
    obs = L.assign(source=L["feature"] + " @ " + L["unit"])
    ann = ann.assign(source=ann["feature"] + " @ " + ann["unit"] + " (" + ann["ref"] + ")")
    # reproduce E123 exactly (formula unchanged since the amendments)
    R = F3.compute(obs, ann, list(range(F3.START_Q, 2026 * 4 + 3)))
    e123 = pd.read_csv(E123 / "out" / "overall.csv")
    m = e123.merge(R["overall"], on=["scope", "unit", "t"], suffixes=("_e123", "_now"))
    reproduces_e123 = bool(len(m) == len(e123) and np.allclose(m["firi3_e123"].fillna(-9), m["firi3_now"].fillna(-9), atol=1e-12))
    src_sha = {k: sha(v) for k, v in source_files().items()}
    rule_check = rules_reproduce_inputs(obs)
    rs = release_status(obs, ann, today)
    el = eligibility_dry_run(obs, ann, rs)
    rs.to_csv(ROOT / "E124_SOURCE_RELEASE_STATUS.csv", index=False, lineterminator="\n")
    el.to_csv(ROOT / "E124_FEATURE_ELIGIBILITY_AUDIT.csv", index=False, lineterminator="\n")

    # issuance attempt (recorded once per date; blocked before the issue date)
    st = S.Store(ROOT / "store")
    OK = {"released (publication date unverified)", "released and verified", "not applicable"}
    missing = rs[~rs["availability_status"].isin(OK)][["feature", "source_key", "target_observation_period", "availability_status", "note"]].copy()
    # blocking: a refreshable source that is stale or was retrieved before its quarter was complete; an annual year that is
    # incomplete in the source itself is a documented gap (Amendment 2 uses the latest complete year), not a refresh failure
    missing["blocking"] = ~((missing["source_key"] == "emp_owner") & (missing["availability_status"] == "retrieved but incomplete")) & (missing["availability_status"] != "not yet released")
    elig = {"failed": {}, "missing_inputs": missing.to_dict("records")}
    if missing["blocking"].any():
        elig["failed"]["C3"] = "inputs to refresh: " + ", ".join(sorted(set(missing.loc[missing["blocking"], "source_key"])))
    attempt = "issued"
    if not any(e.get("event") == "attempt_blocked" and e.get("attempt_date") == today.isoformat() for e in st.events()):
        try:
            st.issue(ORIGIN, obs, ann, cfg_sha, src_sha, today, elig)
        except RuntimeError as e:
            attempt = f"blocked: {e}"
    else:
        attempt = "blocked (already recorded for this date)"

    # FIRI3 versions vs FIRI v2
    v121 = pd.read_csv(EXP / "E121_FIRI3_Implementation" / "E121_FIRI3_OVERALL_RESULTS.csv")
    v122 = pd.read_csv(EXP / "E122_Data_Cutoff_Audit" / "out" / "firi3_amended_overall.csv")
    v123 = R["overall"]
    h = pd.read_csv(B / "data" / "thesis" / "firi2_history.csv")
    h["t"] = h["origin_quarter"].map(F3.qindex)
    h["unit"] = h["province_code"].map(FI.PROVINCES)
    c = v123[["scope", "unit", "t", "origin", "firi3", "band", "indicators_available", "indicators_used"]].rename(columns={"firi3": "firi3_v1_2", "band": "band_v1_2", "indicators_available": "k_v1_2", "indicators_used": "indicators_v1_2"})
    c = c.merge(v122[["scope", "unit", "t", "firi3", "band", "indicators_available"]].rename(columns={"firi3": "firi3_v1_1_A1", "band": "band_v1_1", "indicators_available": "k_v1_1"}), on=["scope", "unit", "t"])
    c = c.merge(v121[["scope", "unit", "t", "firi3", "band"]].rename(columns={"firi3": "firi3_v1_0_E121", "band": "band_v1_0"}), on=["scope", "unit", "t"])
    c = c.merge(h[["t", "unit", "FIRI", "class", "domainsAvailable", "kind"]].rename(columns={"FIRI": "firi_v2", "class": "class_v2", "domainsAvailable": "v2_domains", "kind": "v2_kind"}), on=["t", "unit"], how="left")
    c.loc[c["scope"] == "regional", ["firi_v2", "class_v2", "v2_domains", "v2_kind"]] = np.nan
    for col in ("firi3_v1_2", "firi_v2"):
        c[f"rank_{col}"] = c[c["scope"] == "provincial"].groupby("t")[col].rank(ascending=False)
    c["effect_amendment_1"] = (c["firi3_v1_1_A1"] - c["firi3_v1_0_E121"]).where(lambda x: x.abs() > 1e-8, 0.0)     # CSV values carry 10 digits
    c["effect_amendment_2"] = (c["firi3_v1_2"] - c["firi3_v1_1_A1"]).where(lambda x: x.abs() > 1e-8, 0.0)
    c.to_csv(ROOT / "E124_FIRI3_VS_FIRI2_COMPARISON.csv", index=False, lineterminator="\n", float_format="%.10g")
    both = c[(c["scope"] == "provincial") & c["firi3_v1_2"].notna() & c["firi_v2"].notna()]
    comp = {"rows_both": int(len(both)), "spearman": round(float(both["firi3_v1_2"].corr(both["firi_v2"], method="spearman")), 3),
            "side_agreement_pct": round(100 * float(((both["firi3_v1_2"] >= .5) == (both["class_v2"] == "HIGH")).mean()), 1),
            "v2_high_pct": round(100 * float((both["class_v2"] == "HIGH").mean()), 1), "firi3_ge_0_5_pct": round(100 * float((both["firi3_v1_2"] >= .5).mean()), 1),
            "rank_spearman_mean": round(float(np.mean([g["rank_firi3_v1_2"].corr(g["rank_firi_v2"]) for _, g in both.groupby("t") if len(g) == 5])), 3),
            "amendment_1_rows_changed": int((c["effect_amendment_1"].abs() > 1e-8).sum()), "amendment_2_rows_changed": int((c["effect_amendment_2"].abs() > 1e-8).sum()),
            "v2_rows_firi3_not_computable": int((c["firi_v2"].notna() & c["firi3_v1_2"].isna()).sum()),
            "firi3_computable": {sc: int(g["firi3_v1_2"].notna().sum()) for sc, g in c.groupby("scope")}}
    watched = [B / "app" / "ml" / "inference" / "firi.py", B / "data" / "thesis" / "firi2_history.csv", B / "data" / "thesis" / "firi2_reference.json"]
    v2 = {str(p.relative_to(REPO)): sha(p) for p in watched}
    prod = subprocess.run(["git", "status", "--porcelain", "--", "backend/app", "frontend/src", "backend/data"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    summary = {"today": today.isoformat(), "origin": ORIGIN, "issue_date": ISSUE, "hashes_ok": hashes_ok, "config_sha256": cfg_sha, "reproduces_e123": reproduces_e123,
               "attempt": attempt, "rule_check": rule_check, "release_status_counts": rs["availability_status"].value_counts().to_dict(),
               "eligible_with_current_holdings": {sc: int(g["eligible_with_current_holdings"].sum()) for sc, g in el.groupby("scope")},
               "features": {sc: int(len(g)) for sc, g in el.groupby("scope")}, "missing_inputs": missing.to_dict("records"),
               "comparison": comp, "firi_v2_sha256": v2, "production_tree_clean": prod == "", "source_sha256": src_sha}
    (ROOT / "out").mkdir(exist_ok=True)
    json.dump(summary, open(ROOT / "out" / "summary.json", "w"), indent=1, default=str)
    pd.set_option("display.width", 250)
    print(json.dumps({k: v for k, v in summary.items() if k != "source_sha256"}, indent=1, default=str))
    print(rs[["feature", "target_observation_period", "latest_in_hand", "expected_available_on", "retrieved_on", "availability_status"]].to_string())
    print(el[["feature", "period_used_with_current_holdings", "period_expected_by_release_rule", "statuses_with_current_holdings", "eligible_with_current_holdings"]].to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=date.today().isoformat())
    main(date.fromisoformat(ap.parse_args().today))
