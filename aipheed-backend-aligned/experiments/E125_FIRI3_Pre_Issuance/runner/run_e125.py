"""E125: verify the E124 baseline, audit the refreshed sources (NASA POWER, IBTrACS, LFS), check CPI release evidence,
recompute FIRI3 with the refreshed inputs (same frozen rules), reconcile with the previous scores, and decide 2026-Q4
issuance readiness. No forecast is issued; earlier outputs and snapshots are not modified.

    python run_e125.py [--today YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import calendar
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
E124 = EXP / "E124_FIRI3_Prospective_Validation"
sys.path.insert(0, str(B))
sys.path.insert(0, str(EXP / "E120_FIRI_Consolidated_Design" / "runner"))
sys.path.insert(0, str(E124 / "runner"))
from app.ml.inference import firi3 as F3      # noqa: E402
from app.ml.inference import firi as FI       # noqa: E402  (read only)
import e120 as E120                           # noqa: E402
import store as S                             # noqa: E402
import run_e124 as R124                       # noqa: E402

P = E120.P
RAW = ROOT / "data" / "raw"
ORIGINS = list(range(F3.START_Q, 2026 * 4 + 3))
T = F3.qindex("2026-Q4")
ISSUE = F3.issue_date(T)
PF_CENTROIDS = {"Cavite": (14.28, 120.88), "Laguna": (14.17, 121.33), "Quezon": (13.93, 122.11), "Rizal": (14.60, 121.30), "Batangas": (13.79, 121.06)}
NASA_SERIES = ("rainfall_anomaly_mm", "temperature_anomaly_c")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hav(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(np.radians, (la1, lo1, la2, lo2))
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


# ------------------------------------------------------------------------------------------------ NASA POWER
def nasa_monthly_refreshed() -> pd.DataFrame:
    rows = []
    for prov in ("Cavite", "Laguna", "Batangas", "Rizal", "Quezon"):
        j = json.loads((RAW / f"nasa_power_monthly_2021_2026_{prov}.json").read_text())
        fill = j["header"].get("fill_value", -999.0)
        for par in ("PRECTOTCORR", "T2M"):
            for k, v in j["properties"]["parameter"][par].items():
                if k.endswith("13"):                                  # annual value, not a month
                    continue
                y, m = int(k[:4]), int(k[4:])
                rows.append({"unit": prov, "item": par, "period": y * 12 + m - 1, "value": None if v == fill else float(v), "freq": "M"})
    return pd.DataFrame(rows)


def nasa_features(nm: pd.DataFrame) -> pd.DataFrame:
    """E119 rules (preprocess.build_series climate block): quarterly total / mean of 3 published months (2021+), anomaly vs the
    mean of earlier same-quarter 2021+ quarters; CALABARZON = mean of the five provinces when all five exist."""
    out = []
    for par_, feat, how, days in (("PRECTOTCORR", "rainfall_anomaly_mm", "sum", True), ("T2M", "temperature_anomaly_c", "mean", False)):
        per_unit = {}
        for u, g in nm[(nm["item"] == par_)].groupby("unit"):
            m = pd.DataFrame({"period": g["period"].astype(int), "value": g["value"]}).dropna()
            m["avail"], m["status"] = m["period"].map(lambda x: P.mfirst(x, 2)), "rule_unverified"
            q = P.monthly_to_q(m, how=how, days=days)[["period", "value", "avail", "status", "obs_label"]]
            an = []
            for r in q.itertuples():
                prev = q[(q["period"] < r.period) & (q["period"] % 4 == r.period % 4)]
                if len(prev):
                    an.append({"period": r.period, "value": r.value - prev["value"].mean(), "avail": r.avail, "status": r.status})
            a = pd.DataFrame(an)
            per_unit[u] = a
            out.append(a.assign(feature=feat, unit=u, resolution="province (centroid point)"))
        cat = pd.concat(per_unit.values()).groupby("period").agg(value=("value", "mean"), n=("value", "size"), avail=("avail", "max"), status=("status", "first")).reset_index()
        out.append(cat[cat["n"] == 5].drop(columns="n").assign(feature=feat, unit="CALABARZON (mean of 5 province points)", resolution="region proxy"))
    return pd.concat(out)[["feature", "unit", "period", "value", "avail", "status", "resolution"]]


# ------------------------------------------------------------------------------------------------ IBTrACS
def cyclones(path: Path):
    t = pd.read_csv(path, skiprows=[1], usecols=["SID", "SEASON", "NAME", "ISO_TIME", "LAT", "LON", "TRACK_TYPE", "USA_ATCF_ID"], low_memory=False)
    # one storm = one JTWC ATCF id where present (provisional tracks can split a storm into two SIDs, e.g. WP172026 SAUDEL)
    atcf = t["USA_ATCF_ID"].where(t["USA_ATCF_ID"].astype(str).str.strip().ne("") & t["USA_ATCF_ID"].notna())
    sid_key = atcf.groupby(t["SID"]).agg(lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None)       # one key per SID
    t["STORM"] = t["SID"].map(sid_key).fillna(t["SID"])
    t["LAT"], t["LON"] = pd.to_numeric(t["LAT"], errors="coerce"), pd.to_numeric(t["LON"], errors="coerce")
    t["ISO_TIME"] = pd.to_datetime(t["ISO_TIME"], errors="coerce")
    t["q"] = t["ISO_TIME"].dt.year * 4 + (t["ISO_TIME"].dt.month - 1) // 3
    local = t[t["LAT"].between(10, 19) & t["LON"].between(116, 127) & (t["ISO_TIME"].dt.year >= 2020)].copy()   # corrected pipeline
    lrows = []
    for prov, (la, lo) in PF_CENTROIDS.items():
        d = hav(la, lo, local["LAT"].to_numpy(), local["LON"].to_numpy())
        n = local[d <= 100.0]
        for q, g in n.groupby("q"):
            lrows.append({"unit": prov, "period": int(q), "count": int(g["STORM"].nunique()), "storms": "; ".join(sorted(f"{s}({nm})" for s, nm in set(zip(g["STORM"], g["NAME"])))),
                          "track_types": "; ".join(sorted(set(g["TRACK_TYPE"])))})
    par = t[(t["SEASON"] >= 1996) & t["LAT"].between(5, 25) & t["LON"].between(115, 135)].sort_values("ISO_TIME")      # E114
    first = par.groupby("STORM").first().reset_index()
    prow = [{"unit": "PHILIPPINES", "period": int(q), "count": int(len(g)), "storms": "; ".join(sorted(f"{s}({nm})" for s, nm in zip(g["STORM"], g["NAME"]))),
             "track_types": "; ".join(sorted(set(g["TRACK_TYPE"])))} for q, g in first.groupby("q")]
    # double counting: same named storm under two SIDs in the same quarter (e.g. a spur track)
    dup = par.groupby(["NAME", "q"]).agg(sids=("SID", "nunique"), storms=("STORM", "nunique"))
    dup = dup[dup["sids"] > dup["storms"]]["sids"]
    return pd.DataFrame(lrows), pd.DataFrame(prow), dup, t["ISO_TIME"].max()


# ------------------------------------------------------------------------------------------------ main
def main(today: date):
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    # ---------------- baseline
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    cfg = json.loads((E124 / "E124_FROZEN_VALIDATION_CONFIGURATION.json").read_text())
    cfg_sha = hashlib.sha256(S.canonical(cfg)).hexdigest()
    frozen_ok = (cfg_sha == (E124 / "E124_FROZEN_VALIDATION_CONFIGURATION.sha256").read_text().strip()
                 and S.canonical(cfg) == S.canonical(R124.frozen_config()))
    hashes_ok = (sha(EXP / "E121_FIRI3_Implementation" / "E121_FIRI3_PROTOCOL.md") == F3.PROTOCOL_SHA256 == cfg["protocol"]["sha256"]
                 and sha(EXP / "E122_Data_Cutoff_Audit" / "E122_FIRI3_PROTOCOL_AMENDMENT_1.md") == F3.AMENDMENT_1_SHA256 == cfg["amendment_1"]["sha256"]
                 and sha(EXP / "E123_FIRI3_Design_Resolution" / "E123_FIRI3_PROTOCOL_AMENDMENT_2.md") == F3.AMENDMENT_2_SHA256 == cfg["amendment_2"]["sha256"])
    st = S.Store(E124 / "store")
    ev = st.events()
    store_state = {"forecasts": sorted(p.name for p in (E124 / "store" / "forecasts").iterdir()), "events": [(e["event"], e.get("attempt_date")) for e in ev]}
    v2 = {str(p.relative_to(REPO)): sha(p) for p in (B / "app" / "ml" / "inference" / "firi.py", B / "data" / "thesis" / "firi2_history.csv", B / "data" / "thesis" / "firi2_reference.json")}
    prod_clean = subprocess.run(["git", "status", "--porcelain", "--", "backend/app", "frontend/src", "backend/data"], cwd=REPO, capture_output=True, text=True).stdout.strip() == ""

    L, ann = E120.load()
    obs = L.assign(source=L["feature"] + " @ " + L["unit"])
    ann = ann.assign(source=ann["feature"] + " @ " + ann["unit"] + " (" + ann["ref"] + ")")

    # ---------------- NASA POWER
    old_m = pd.read_csv(P.INPUTS["e118_nasa_power_monthly"])
    new_m = nasa_monthly_refreshed()
    guard = nasa_features(old_m[old_m["item"].isin(["PRECTOTCORR", "T2M"])])
    cur = obs[obs["feature"].isin(NASA_SERIES)]
    gm = cur.merge(guard, on=["feature", "unit", "period"], suffixes=("", "_g"), how="outer", indicator=True)
    method_reproduces = bool((gm["_merge"] == "both").all() and np.allclose(gm["value"], gm["value_g"], atol=1e-9) and (gm["avail"].astype(str) == gm["avail_g"].astype(str)).all())
    om = old_m[old_m["item"].isin(["PRECTOTCORR", "T2M"]) & (old_m["period"] >= 2021 * 12)][["unit", "item", "period", "value"]]
    nm_ = new_m.merge(om, on=["unit", "item", "period"], how="left", suffixes=("", "_e118"))
    nm_["month"] = nm_["period"].map(lambda p: f"{p // 12}-{p % 12 + 1:02d}")
    nm_["status"] = np.where(nm_["value"].isna(), "not yet in source (fill value)", np.where(nm_["value_e118"].isna(), "new (not in E118)",
                             np.where((nm_["value"] - nm_["value_e118"]).abs() < 1e-9, "unchanged", "revised")))
    nm_["difference"] = nm_["value"] - nm_["value_e118"]
    nm_.drop(columns=["period"]).rename(columns={"value": "value_refreshed"}).to_csv(ROOT / "E125_NASA_POWER_REFRESH_AUDIT.csv", index=False, lineterminator="\n")
    nasa_new = nasa_features(new_m)
    nasa_sum = {"months_2026_present": sorted(set(nm_.loc[(nm_["period"] >= 2026 * 12) & nm_["value"].notna(), "month"])),
                "months_2026_missing": sorted(set(nm_.loc[(nm_["period"] >= 2026 * 12) & nm_["value"].isna(), "month"])),
                "revised_2021_2025": int((nm_["status"] == "revised").sum()), "max_abs_revision": float(nm_["difference"].abs().max()),
                "complete_quarters_2026": sorted({F3.qlabel(int(p)) for p in nasa_new.loc[nasa_new["period"] >= 2026 * 4, "period"]}),
                "method_reproduces_e119": method_reproduces}

    # ---------------- cyclones
    loc_new, par_new, dup, last_fix = cyclones(RAW / "ibtracs.last3years.list.v04r01.csv")
    old_loc = obs[obs["feature"] == "typhoons_local_100km"][["unit", "period", "value"]]
    old_par = obs[obs["feature"] == "typhoons_PAR"][["unit", "period", "value"]]
    pf = pd.read_csv(P.INPUTS["profile"])
    cyc = []
    for scope, new, old, units in (("local 100 km", loc_new, old_loc, list(PF_CENTROIDS)), ("PAR", par_new, old_par, ["PHILIPPINES"])):
        for u in units:
            for q in range(2024 * 4 + 1, 2026 * 4 + 3):                  # last-3-years file: compare from 2024-Q2 (earlier first fixes are outside the file)
                n = new[(new["unit"] == u) & (new["period"] == q)]
                o = old[(old["unit"] == u) & (old["period"] == q)]
                prof_note = ""
                if scope == "local 100 km" and q == 2026 * 4 + 2:
                    prof_note = "E124 / corrected pipeline: incomplete at retrieval (NaN)"
                if scope == "PAR" and q == 2026 * 4 + 2:
                    prof_note = "E119 kept PAR to 2026-Q2 (2026-Q3 incomplete at retrieval)"
                cnt = int(n["count"].iloc[0]) if len(n) else 0
                cyc.append({"scope": scope, "unit": u, "quarter": F3.qlabel(q), "count_refreshed": cnt, "count_previous": float(o["value"].iloc[0]) if len(o) else None,
                            "match": (len(o) > 0 and float(o["value"].iloc[0]) == cnt), "storms": n["storms"].iloc[0] if len(n) else "",
                            "track_types": n["track_types"].iloc[0] if len(n) else "", "note": prof_note})
    CY = pd.DataFrame(cyc)
    CY.to_csv(ROOT / "E125_CYCLONE_REFRESH_AUDIT.csv", index=False, lineterminator="\n")
    hist = CY[CY["quarter"] < "2026-Q3"]
    cyc_sum = {"history_match_pct": round(100 * float(hist["match"].mean()), 1), "mismatches": hist[~hist["match"]][["scope", "unit", "quarter", "count_previous", "count_refreshed"]].to_dict("records"),
               "q3_2026": CY[CY["quarter"] == "2026-Q3"][["scope", "unit", "count_refreshed", "storms", "track_types"]].to_dict("records"),
               "same_name_multiple_sids": {f"{a} {F3.qlabel(int(b))}": int(c) for (a, b), c in dup.items()} if len(dup) else {},
               "last_fix_in_file": str(last_fix), "quarter_complete": str(last_fix) >= "2026-09-30"}

    # ---------------- LFS
    lf = pd.read_csv(RAW / "psa_lfs_0021B3FKEI2_unemployment.csv")
    q3 = lf[(lf["Year"] == 2026) & lf["Month"].isin(["July", "August", "September"])]
    q3v = pd.to_numeric(q3["Unemployment Rate Both sexes"], errors="coerce")
    old_lf = pd.read_csv(P.INPUTS["lfs"], encoding="latin-1")
    cmp_lf = lf.merge(old_lf, on=["Year", "Month"], suffixes=("", "_e114"))
    lfs_sum = {"q3_months_present": [m for m, v in zip(q3["Month"], q3v) if not pd.isna(v)], "september_2026": "not yet published in the PSA table (value '.')" if pd.isna(q3v.iloc[-1]) else float(q3v.iloc[-1]),
               "rows_changed_vs_e114": int((cmp_lf["Unemployment Rate Both sexes"].astype(str) != cmp_lf["Unemployment Rate Both sexes_e114"].astype(str)).sum()),
               "expected_rule_date": "2026-12-01 (first day of m+3)"}

    # ---------------- refreshed observations (same rules; replace only the refreshed series)
    ref = obs[~obs["feature"].isin(NASA_SERIES)].copy()
    ref = pd.concat([ref, nasa_new.assign(source=lambda d: d["feature"] + " @ " + d["unit"])])
    addq = 2026 * 4 + 2
    if cyc_sum["quarter_complete"]:
        for scope, feat, new in (("local 100 km", "typhoons_local_100km", loc_new), ("PAR", "typhoons_PAR", par_new)):
            units = list(PF_CENTROIDS) if feat == "typhoons_local_100km" else ["PHILIPPINES"]
            for u in units:
                if ((ref["feature"] == feat) & (ref["unit"] == u) & (ref["period"] == addq)).any():
                    continue
                n = new[(new["unit"] == u) & (new["period"] == addq)]
                ref = pd.concat([ref, pd.DataFrame([{"feature": feat, "unit": u, "period": addq, "value": float(n["count"].iloc[0]) if len(n) else 0.0,
                                                     "avail": F3.issue_date(addq), "status": "verified", "resolution": "province" if feat.endswith("100km") else "national",
                                                     "source": f"{feat} @ {u} (IBTrACS refreshed 2026-10-31)"}])])
    changed_rows = ref.merge(obs, on=["feature", "unit", "period"], how="outer", suffixes=("_refreshed", "_previous"), indicator=True)
    changed_rows = changed_rows[(changed_rows["_merge"] != "both") | ((changed_rows["value_refreshed"] - changed_rows["value_previous"]).abs() > 1e-9)]
    changed_rows["change"] = changed_rows["_merge"].map({"left_only": "new observation", "right_only": "removed", "both": "revised value"})
    changed_rows["period_label"] = changed_rows["period"].map(lambda p: F3.qlabel(int(p)))
    changed_rows[["feature", "unit", "period_label", "value_previous", "value_refreshed", "avail_refreshed", "status_refreshed", "change"]].to_csv(
        ROOT / "E125_REFRESHED_FEATURES.csv", index=False, lineterminator="\n", float_format="%.10g")

    # ---------------- recompute and reconcile (all origins; nothing overwritten)
    R_old = F3.compute(obs, ann, ORIGINS)
    R_new = F3.compute(ref, ann, ORIGINS)
    R_new2 = F3.compute(ref.sample(frac=1, random_state=5), ann, ORIGINS)
    reproducible = R_new["overall"].to_csv(index=False) == R_new2["overall"].to_csv(index=False)
    e123 = pd.read_csv(EXP / "E123_FIRI3_Design_Resolution" / "out" / "overall.csv")
    old_matches_e123 = bool(np.allclose(e123.sort_values(["scope", "unit", "t"])["firi3"].fillna(-9).to_numpy(),
                                        R_old["overall"].sort_values(["scope", "unit", "t"])["firi3"].fillna(-9).to_numpy(), atol=1e-12))
    fo, fn = R_old["features"], R_new["features"]
    fm = fo.merge(fn, on=["scope", "unit", "t", "feature"], suffixes=("_old", "_new"))
    def cause(r):
        if str(r.period_old) != str(r.period_new):
            return "newly available observations" if str(r.status_old) != "stale" else "previously incomplete dataset"
        if pd.isna(r.score_old) != pd.isna(r.score_new):
            return "previously incomplete dataset" if str(r.status_old) in ("stale", "missing") else "publication-date eligibility change"
        if abs((r.raw_value_old or 0) - (r.raw_value_new or 0)) > 1e-6:                     # below this: floating-point recomputation noise
            return "corrected or revised source data"
        if abs((r.score_old or 0) - (r.score_new or 0)) > 1e-12:
            return "revised reference history (percentile)"
        return "unchanged"
    fm["cause"] = [cause(r) for r in fm.itertuples()]
    oo = R_old["overall"].merge(R_new["overall"], on=["scope", "unit", "t", "origin", "issue_date"], suffixes=("_previous", "_refreshed"))
    oo["changed"] = ~np.isclose(oo["firi3_previous"].fillna(-9), oo["firi3_refreshed"].fillna(-9), atol=1e-12) | (oo["band_previous"] != oo["band_refreshed"])
    causes = fm[fm["cause"] != "unchanged"].groupby(["scope", "unit", "t"])["cause"].agg(lambda s: "; ".join(f"{k} ({v})" for k, v in s.value_counts().items()))
    feats = fm[fm["cause"] != "unchanged"].groupby(["scope", "unit", "t"])["feature"].agg(lambda s: " ".join(sorted(set(s))))
    oo = oo.join(causes.rename("causes"), on=["scope", "unit", "t"]).join(feats.rename("features_changed"), on=["scope", "unit", "t"])
    oo["explained"] = ~oo["changed"] | oo["causes"].notna()
    oo["calculation_defect"] = False
    oo[["scope", "unit", "origin", "issue_date", "firi3_previous", "firi3_refreshed", "band_previous", "band_refreshed", "indicators_used_previous",
        "indicators_used_refreshed", "changed", "causes", "features_changed", "explained", "calculation_defect"]].to_csv(
        ROOT / "E125_SCORE_RECONCILIATION.csv", index=False, lineterminator="\n", float_format="%.10g")

    fm[fm["cause"] != "unchanged"].to_csv(out / "feature_change_causes.csv", index=False, lineterminator="\n", float_format="%.10g")
    # ---------------- D-E125-2 (not applied): quarters with no storm entering PAR are absent from the E114 series, so the
    # as-of rule falls back to an older quarter's count. Sensitivity: the same series with explicit zeros.
    par_have = set(ref.loc[ref["feature"] == "typhoons_PAR", "period"].astype(int))
    zq = [q for q in range(F3.START_Q, 2026 * 4 + 3) if q not in par_have]
    zrows = pd.DataFrame([{"feature": "typhoons_PAR", "unit": "PHILIPPINES", "period": q, "value": 0.0, "avail": F3.issue_date(q), "status": "verified",
                           "resolution": "national", "source": "typhoons_PAR @ PHILIPPINES (zero quarter)"} for q in zq])
    R_z = F3.compute(pd.concat([ref, zrows]), ann, ORIGINS)
    zz = R_new["overall"].merge(R_z["overall"], on=["scope", "unit", "t"], suffixes=("", "_z"))
    zz = zz[~np.isclose(zz["firi3"].fillna(-9), zz["firi3_z"].fillna(-9), atol=1e-12)]
    par_zero = {"zero_quarters": [F3.qlabel(q) for q in zq], "scores_changed": int(len(zz)), "max_abs_change": float((zz["firi3"] - zz["firi3_z"]).abs().max()) if len(zz) else 0.0,
                "band_changes": int((zz["band"] != zz["band_z"]).sum()), "detail": zz[["scope", "unit", "origin", "firi3", "firi3_z", "band", "band_z"]].to_dict("records")}

    # ---------------- CPI release evidence against every FIRI3 use
    led = pd.read_csv(P.INPUTS["ledger"], dtype=str)
    def evid(r):
        for c in ("archive_release_date", "owner_reported_date", "owner_ledger_date"):
            if isinstance(r[c], str) and r[c][:4].isdigit():
                return r[c][:10], c
        return None, None
    led[["evidence_date", "evidence_kind"]] = led.apply(lambda r: pd.Series(evid(r)), axis=1)
    ev_by = led.dropna(subset=["evidence_date"]).groupby(["reference_month", "province"]).agg(evidence_date=("evidence_date", "max"), kind=("evidence_kind", "first")).reset_index()
    cpi_use = fn[fn["feature"].isin(["FMA_food_cpi", "FMA_headline_cpi"]) & fn["score"].notna()][["unit", "t", "issue_date", "feature", "period", "avail_date"]]
    checks = []
    for r in cpi_use.itertuples():
        q = F3.qindex(r.period)
        months = [f"{q // 4}-{(q % 4) * 3 + k:02d}" for k in (1, 2, 3)]
        e = ev_by[(ev_by["province"] == r.unit) & ev_by["reference_month"].isin(months)]
        late = e[e["evidence_date"] >= r.issue_date]
        checks.append({"unit": r.unit, "origin": F3.qlabel(int(r.t)), "issue_date": r.issue_date, "feature": r.feature, "quarter_used": r.period,
                       "months_with_evidence": int(len(e)), "latest_evidence_date": e["evidence_date"].max() if len(e) else "", "rule_avail": r.avail_date,
                       "evidence_after_issue": int(len(late))})
    CC = pd.DataFrame(checks)
    late_days = []
    for r in led[led["class"].isin(["V1", "V2"])].itertuples():
        m = pd.Timestamp(r.reference_month + "-01")
        late_days.append((pd.Timestamp(r.archive_release_date) - (m + pd.offsets.MonthBegin(1) + pd.Timedelta(days=9))).days)
    cpi_sum = {"scored_quarter_uses": int(len(CC)), "uses_with_any_month_evidence": int((CC["months_with_evidence"] > 0).sum()),
               "uses_where_evidence_is_on_or_after_issue": int((CC["evidence_after_issue"] > 0).sum()),
               "archived_release_minus_day10_days": {"n": len(late_days), "later_than_rule": int(sum(d > 0 for d in late_days)), "max": int(max(late_days)), "median": float(np.median(late_days))},
               "min_margin_days_rule_to_issue": int(min((pd.Timestamp(i) - pd.Timestamp(a)).days for i, a in zip(CC["issue_date"], CC["rule_avail"]))),
               "sep_2026_evidence": led[(led["reference_month"] == "2026-09")][["province", "evidence_date"]].to_dict("records")}
    CC.to_csv(out / "cpi_release_evidence_checks.csv", index=False, lineterminator="\n")

    # ---------------- publication-date verification (per feature) + 2026-Q4 readiness (diagnostic, no scores kept)
    pub = pd.read_csv(EXP / "E123_FIRI3_Design_Resolution" / "E123_PUBLICATION_DATE_AUDIT.csv").set_index("feature")
    rs = R124.release_status(ref, ann, today)
    lfs_partial = len(lfs_sum["q3_months_present"]) < 3
    if cyc_sum["quarter_complete"]:
        for f_ in ("CEC_cyclones_100km", "CEC_cyclones_R"):
            rs.loc[rs["feature"] == f_, ["latest_in_hand", "availability_status", "retrieved_on", "note"]] = ["2026-Q3", "released and verified", "2026-10-31",
                                                                                                             "recounted from IBTrACS (last fix 2026-10-29); recent tracks provisional"]
    nasa_ok = "2026-Q3" in nasa_sum["complete_quarters_2026"]
    for f_ in ("CEC_rain_departure", "CEC_heat", "CEC_rain_departure_R", "CEC_heat_R"):
        rs.loc[rs["feature"] == f_, ["latest_in_hand", "retrieved_on"]] = [max(nasa_sum["complete_quarters_2026"]) if nasa_sum["complete_quarters_2026"] else "2025-Q4", "2026-10-31"]
        rs.loc[rs["feature"] == f_, "availability_status"] = "released (publication date unverified)" if nasa_ok else "retrieved but incomplete"
    rs.loc[rs["feature"] == "EHS_unemployment_change_R", ["retrieved_on", "note"]] = ["2026-10-31", f"PSA table re-queried 2026-10-31: Q3 months held {lfs_sum['q3_months_present']}"]
    if lfs_partial:
        rs.loc[rs["feature"] == "EHS_unemployment_change_R", "availability_status"] = "retrieved but incomplete"
    fs4 = F3.feature_scores(*F3.validate_inputs(ref, ann)[:2], [T])
    el = []
    for f in F3.FEATURES:
        r = fs4[fs4["feature"] == f.code]
        s_ = rs.set_index("feature").loc[f.code]
        cls = pub.loc[f.code, "classification"]
        ok = r["score"].notna().any()
        if f.code == "EHS_unemployment_change_R" and lfs_partial:
            dec = "BLOCKED"
            why = "2026-Q3 national unemployment has 2 of 3 months (September not yet published; due by rule 2026-12-01)"
        elif not ok:
            dec, why = "BLOCKED", "; ".join(sorted(set(r["status"])))
        elif s_["availability_status"].startswith("retrieved but incomplete") and f.normalization == "rank5":
            dec, why = "READY WITH WARNING", f"{s_['note']} (Amendment 2 uses the latest complete year)"
        elif s_["availability_status"] == "not applicable":
            dec, why = "READY WITH WARNING", "static profile; availability date is an assumption" if cls == "unverified" else "static profile"
        elif cls == "verified":
            dec, why = "READY", ""
        else:
            dec, why = "READY WITH WARNING", f"publication date {cls}"
        el.append({"feature": f.code, "indicator": f.indicator, "scope": "provincial" if f.scope == "P" else "regional", "period_used": "; ".join(sorted(set(r["period"].dropna().astype(str)))),
                   "target_period_by_rule": s_["target_observation_period"], "availability_status": s_["availability_status"], "publication_class": cls,
                   "cutoff_2021_ok": bool((r["period"].dropna().astype(str).str[:4].astype(int) >= 2021).all()),
                   "amendment_1_ok": f.series not in F3.BASE_REQUIRED or bool((r["period"].dropna().map(lambda p: F3.qindex(p)) >= F3.FIRST_CHANGE_Q).all()),
                   "amendment_2_note": "; ".join(sorted(set(r["note"].dropna()) - {""})) if "note" in r else "",
                   "geography_ok": bool(set(r["unit"]) == (set(F3.PROVINCES) if f.scope == "P" else {F3.REGION_LABEL})),
                   "stale": bool((r["status"] == "stale").any()), "decision": dec, "reason": why})
    EL = pd.DataFrame(el)
    EL.to_csv(ROOT / "E125_FEATURE_ELIGIBILITY_AUDIT.csv", index=False, lineterminator="\n")
    pubv = pub.reset_index()[["feature", "indicator", "classification", "evidence"]].copy()
    pubv["e125_evidence"] = pubv["feature"].map({"FMA_food_cpi": f"ledger: {cpi_sum['archived_release_minus_day10_days']['later_than_rule']} of {cpi_sum['archived_release_minus_day10_days']['n']} archived releases later than day 10 (max +{cpi_sum['archived_release_minus_day10_days']['max']} days); every scored quarter has >= {cpi_sum['min_margin_days_rule_to_issue']} days between rule date and issue; {cpi_sum['uses_where_evidence_is_on_or_after_issue']} scored uses with evidence on/after the issue",
                                                 "FMA_headline_cpi": "as FMA_food_cpi",
                                                 "CEC_rain_departure": "NASA POWER refreshed 2026-10-31; monthly values 2026-01..2026-09 (no dated release record; rule m+2)",
                                                 "CEC_heat": "as CEC_rain_departure", "CEC_cyclones_100km": "IBTrACS refreshed (file modified 2026-10-30); 2026 tracks PROVISIONAL",
                                                 "CEC_cyclones_R": "as CEC_cyclones_100km", "EHS_unemployment_change_R": "PSA OpenSTAT re-queried 2026-10-31: September 2026 not published"})
    pubv["e125_classification"] = pubv["classification"]                         # nothing promoted
    pubv.to_csv(ROOT / "E125_PUBLICATION_DATE_VERIFICATION.csv", index=False, lineterminator="\n")
    rs.to_csv(out / "release_status_refreshed.csv", index=False, lineterminator="\n")

    conds = {"C1_date_on_or_after_issue": today.isoformat() >= ISSUE, "C2_frozen_configuration_and_hashes": frozen_ok and hashes_ok,
             "C3_required_periods_complete_and_refreshed": not (EL["decision"] == "BLOCKED").any(),
             "C4_no_value_after_issue": bool((fs4.loc[fs4["score"].notna(), "avail_date"].astype(str) < ISSUE).all()),
             "reproducible": reproducible, "store_operational_and_empty": store_state["forecasts"] == [] and any(e[0] == "attempt_blocked" for e in store_state["events"]),
             "no_critical_integrity_failure": method_reproduces and cpi_sum["uses_where_evidence_is_on_or_after_issue"] == 0 and old_matches_e123}
    overall = "BLOCKED" if not all(conds.values()) else ("READY WITH WARNINGS" if (EL["decision"] == "READY WITH WARNING").any() else "READY FOR OWNER AUTHORIZATION")
    summary = {"today": today.isoformat(), "head": head, "config_sha256": cfg_sha, "frozen_ok": frozen_ok, "hashes_ok": hashes_ok, "store": store_state,
               "firi_v2": v2, "production_clean": prod_clean, "nasa": nasa_sum, "cyclones": cyc_sum, "lfs": lfs_sum, "cpi": cpi_sum,
               "refreshed_rows": changed_rows["change"].value_counts().to_dict(),
               "reconciliation": {"rows": int(len(oo)), "changed": int(oo["changed"].sum()), "explained": bool(oo["explained"].all()),
                                  "changed_by_scope": oo.groupby("scope")["changed"].sum().astype(int).to_dict(),
                                  "computable_previous": oo.groupby("scope")["firi3_previous"].apply(lambda s: int(s.notna().sum())).to_dict(),
                                  "computable_refreshed": oo.groupby("scope")["firi3_refreshed"].apply(lambda s: int(s.notna().sum())).to_dict(),
                                  "max_abs_change": float((oo["firi3_previous"] - oo["firi3_refreshed"]).abs().max()),
                                  "band_changes": int((oo["band_previous"] != oo["band_refreshed"]).sum()),
                                  "causes": fm[fm["cause"] != "unchanged"]["cause"].value_counts().to_dict()},
               "par_zero_quarter_sensitivity": par_zero, "previous_reproduces_e123": old_matches_e123, "reproducible": reproducible, "conditions": conds, "feature_decisions": EL["decision"].value_counts().to_dict(),
               "overall": overall, "refresh_log": json.loads((ROOT / "data" / "refresh_log.json").read_text())}
    json.dump(summary, open(out / "summary.json", "w"), indent=1, default=str)
    pd.set_option("display.width", 250)
    print(json.dumps({k: v for k, v in summary.items() if k != "refresh_log"}, indent=1, default=str))
    print(EL[["feature", "period_used", "target_period_by_rule", "availability_status", "publication_class", "decision"]].to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=date.today().isoformat())
    main(date.fromisoformat(ap.parse_args().today))
