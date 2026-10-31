"""E126: verify the E125 baseline; verify the PAR zero-storm quarters (D-E125-2) from raw IBTrACS; analyse the impact
of the proposed Amendment 3 (kept separate, not applied); compare LFS quarterly methods; update source status and
2026-Q4 readiness; reconcile historical versions. No forecast is issued; no earlier output is modified.

    python run_e126.py [--today YYYY-MM-DD]
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
E124, E125 = EXP / "E124_FIRI3_Prospective_Validation", EXP / "E125_FIRI3_Pre_Issuance"
sys.path.insert(0, str(B))
for p in (EXP / "E120_FIRI_Consolidated_Design" / "runner", E124 / "runner", E125 / "runner"):
    sys.path.insert(0, str(p))
from app.ml.inference import firi3 as F3      # noqa: E402
import e120 as E120                           # noqa: E402
import store as S                             # noqa: E402
import run_e124 as R124                       # noqa: E402
import run_e125 as R125                       # noqa: E402

P = E120.P
ORIGINS = list(range(F3.START_Q, 2026 * 4 + 3))
T = F3.qindex("2026-Q4")
ISSUE = F3.issue_date(T)
ZERO_Q = ["2023-Q1", "2024-Q1", "2025-Q1"]
BOX = (5, 25, 115, 135)                                     # approved (E114) simplified PAR box
PAR_POLY = [(115, 5), (115, 15), (120, 21), (120, 25), (135, 25), (135, 5)]   # official PAR outline (lon, lat), cross-check only


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def in_poly(lon, lat, poly=PAR_POLY):
    x, y = np.asarray(lon, float), np.asarray(lat, float)
    inside = np.zeros(len(x), bool)
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        cond = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / np.where(y2 - y1 == 0, 1e-12, y2 - y1) + x1)
        inside ^= cond
    return inside


def load_tracks(path: Path) -> pd.DataFrame:
    t = pd.read_csv(path, skiprows=[1], usecols=["SID", "SEASON", "NAME", "ISO_TIME", "LAT", "LON", "USA_ATCF_ID"], low_memory=False)
    t["LAT"], t["LON"] = pd.to_numeric(t["LAT"], errors="coerce"), pd.to_numeric(t["LON"], errors="coerce")
    t["ISO_TIME"] = pd.to_datetime(t["ISO_TIME"], errors="coerce")
    t["q"] = t["ISO_TIME"].dt.year * 4 + (t["ISO_TIME"].dt.month - 1) // 3
    atcf = t["USA_ATCF_ID"].where(t["USA_ATCF_ID"].astype(str).str.strip().ne("") & t["USA_ATCF_ID"].notna())
    key = atcf.groupby(t["SID"]).agg(lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None)
    t["STORM"] = t["SID"].map(key).fillna(t["SID"])
    return t


def par_verify(tracks: dict) -> pd.DataFrame:
    rows = []
    for src, t in tracks.items():
        last = t["ISO_TIME"].max()
        box = t[(t["SEASON"] >= 1996) & t["LAT"].between(BOX[0], BOX[1]) & t["LON"].between(BOX[2], BOX[3])]
        first = box.sort_values("ISO_TIME").groupby("STORM").first().reset_index()
        poly = t[(t["SEASON"] >= 1996) & in_poly(t["LON"], t["LAT"])]
        pfirst = poly.sort_values("ISO_TIME").groupby("STORM").first().reset_index()
        for ql in ZERO_Q:
            q = F3.qindex(ql)
            qs, qe = pd.Timestamp(F3.issue_date(q - 1)), pd.Timestamp(F3.issue_date(q))
            covered = (t["ISO_TIME"].min() <= qs) and (last >= qe)
            entering = first[first["q"] == q]
            active = box[box["q"] == q]
            carried = sorted(set(active["STORM"]) - set(entering["STORM"]))
            near = t[(t["ISO_TIME"] >= qs) & (t["ISO_TIME"] < qe)]
            # nearest approach to the box during the quarter (degrees outside the box edges)
            if len(near):
                dlat = np.maximum(0, np.maximum(BOX[0] - near["LAT"], near["LAT"] - BOX[1]))
                dlon = np.maximum(0, np.maximum(BOX[2] - near["LON"], near["LON"] - BOX[3]))
                dist = np.sqrt(dlat ** 2 + dlon ** 2)
                i = int(np.argmin(dist.to_numpy()))
                nearest = f"{near.iloc[i]['NAME']} {near.iloc[i]['ISO_TIME']:%Y-%m-%d} at {near.iloc[i]['LAT']:.1f}N {near.iloc[i]['LON']:.1f}E ({dist.iloc[i]:.1f} deg outside)"
            else:
                nearest = "no WP track points in the quarter"
            sids_entering = entering["SID"].nunique() if len(entering) else 0
            rows.append({"source": src, "quarter": ql, "file_covers_quarter": bool(covered), "last_fix_in_file": str(last),
                         "storms_first_entering_box": int(len(entering)), "sids_first_entering_box": int(sids_entering),
                         "storms_active_in_box_entered_earlier": len(carried), "carried_storms": "; ".join(carried),
                         "storms_first_entering_official_polygon": int((pfirst["q"] == q).sum()), "track_points_in_quarter_basin": int(len(near)),
                         "nearest_track_point": nearest, "e114_series_value": "absent (quarter omitted)",
                         "verdict": ("source does not cover the full quarter" if not covered else
                                     "true zero" if len(entering) == 0 and int((pfirst["q"] == q).sum()) == 0 else "storm entered: not zero")})
    return pd.DataFrame(rows)


def refreshed_obs():
    """The E125 refreshed inputs (same construction as run_e125: NASA POWER 2026, IBTrACS 2026-Q3 de-duplicated)."""
    L, ann = E120.load()
    obs = L.assign(source=L["feature"] + " @ " + L["unit"])
    ann = ann.assign(source=ann["feature"] + " @ " + ann["unit"] + " (" + ann["ref"] + ")")
    nasa_new = R125.nasa_features(R125.nasa_monthly_refreshed())
    ref = pd.concat([obs[~obs["feature"].isin(R125.NASA_SERIES)], nasa_new.assign(source=lambda d: d["feature"] + " @ " + d["unit"])])
    loc_new, par_new, _, _ = R125.cyclones(R125.RAW / "ibtracs.last3years.list.v04r01.csv")
    addq = 2026 * 4 + 2
    for feat, new, units in (("typhoons_local_100km", loc_new, list(R125.PF_CENTROIDS)), ("typhoons_PAR", par_new, ["PHILIPPINES"])):
        for u in units:
            if ((ref["feature"] == feat) & (ref["unit"] == u) & (ref["period"] == addq)).any():
                continue
            n = new[(new["unit"] == u) & (new["period"] == addq)]
            ref = pd.concat([ref, pd.DataFrame([{"feature": feat, "unit": u, "period": addq, "value": float(n["count"].iloc[0]) if len(n) else 0.0,
                                                 "avail": F3.issue_date(addq), "status": "verified", "resolution": "province" if feat.endswith("100km") else "national",
                                                 "source": f"{feat} @ {u} (IBTrACS refreshed 2026-10-31)"}])])
    return obs, ref, ann


def with_par_zeros(df: pd.DataFrame, quarters) -> pd.DataFrame:
    z = pd.DataFrame([{"feature": "typhoons_PAR", "unit": "PHILIPPINES", "period": F3.qindex(q), "value": 0.0, "avail": F3.issue_date(F3.qindex(q)),
                       "status": "verified", "resolution": "national", "source": "typhoons_PAR @ PHILIPPINES (verified zero-storm quarter, Amendment 3 proposal)"} for q in quarters])
    return pd.concat([df, z], ignore_index=True)


def main(today: date):
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    # ---------------- baseline
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    cfg = json.loads((E124 / "E124_FROZEN_VALIDATION_CONFIGURATION.json").read_text())
    cfg_sha = hashlib.sha256(S.canonical(cfg)).hexdigest()
    s125 = json.loads((E125 / "out" / "summary.json").read_text())
    base = {"head": head, "config_sha256": cfg_sha, "config_frozen": cfg_sha == (E124 / "E124_FROZEN_VALIDATION_CONFIGURATION.sha256").read_text().strip()
            and S.canonical(cfg) == S.canonical(R124.frozen_config()),
            "protocol_ok": sha(EXP / "E121_FIRI3_Implementation" / "E121_FIRI3_PROTOCOL.md") == F3.PROTOCOL_SHA256,
            "amendment_1_ok": sha(EXP / "E122_Data_Cutoff_Audit" / "E122_FIRI3_PROTOCOL_AMENDMENT_1.md") == F3.AMENDMENT_1_SHA256,
            "amendment_2_ok": sha(EXP / "E123_FIRI3_Design_Resolution" / "E123_FIRI3_PROTOCOL_AMENDMENT_2.md") == F3.AMENDMENT_2_SHA256,
            "firi3_sha256": sha(B / "app" / "ml" / "inference" / "firi3.py"), "firi3_version": F3.VERSION,
            "firi_v2": {str(p.relative_to(REPO)): sha(p) for p in (B / "app" / "ml" / "inference" / "firi.py", B / "data" / "thesis" / "firi2_history.csv", B / "data" / "thesis" / "firi2_reference.json")},
            "production_clean": subprocess.run(["git", "status", "--porcelain", "--", "backend/app", "frontend/src", "backend/data"], cwd=REPO, capture_output=True, text=True).stdout.strip() == "",
            "store_forecasts": sorted(p.name for p in (E124 / "store" / "forecasts").iterdir()),
            "registry_events": [(e["event"], e.get("attempt_date")) for e in S.Store(E124 / "store").events()],
            "e125_outputs_sha256": {p.name: sha(p) for p in sorted(E125.glob("E125_*"))},
            "e125_refreshed": {"nasa_2026_months": s125["nasa"]["months_2026_present"], "par_2026q3": [x["count_refreshed"] for x in s125["cyclones"]["q3_2026"] if x["scope"] == "PAR"],
                               "local_2026q3": {x["unit"]: x["count_refreshed"] for x in s125["cyclones"]["q3_2026"] if x["scope"] == "local 100 km"},
                               "lfs_q3_months": s125["lfs"]["q3_months_present"]},
            "e125_blockers": [k for k, v in s125["conditions"].items() if not v]}

    # ---------------- PAR zero-storm verification
    tracks = {"E114 ibtracs.WP.list.v04r01.csv": load_tracks(EXP / "E114_Final_Run" / "data" / "raw" / "ibtracs.WP.list.v04r01.csv"),
              "E125 ibtracs.last3years.list.v04r01.csv": load_tracks(R125.RAW / "ibtracs.last3years.list.v04r01.csv")}
    PV = par_verify(tracks)
    PV.to_csv(ROOT / "E126_PAR_ZERO_STORM_VERIFICATION.csv", index=False, lineterminator="\n")
    cov = PV[PV["verdict"] != "source does not cover the full quarter"]
    confirmed = sorted(q for q in ZERO_Q if len(cov[cov["quarter"] == q]) and (cov[cov["quarter"] == q]["verdict"] == "true zero").all())
    all_confirmed = confirmed == ZERO_Q                                  # every covering source agrees, and at least one covers each quarter
    # extraction defect: E114 builds the series with groupby(q).size(), which has no row for a quarter without storms
    e114_par = pd.read_csv(P.INPUTS["par"])
    absent = [F3.qlabel(q) for q in range(F3.START_Q, 2026 * 4 + 2) if q not in set(e114_par["q"])]
    # all other 2021-2026 PAR quarters: E114 values equal the de-duplicated recount from the WP file
    wp = tracks["E114 ibtracs.WP.list.v04r01.csv"]
    box = wp[(wp["SEASON"] >= 1996) & wp["LAT"].between(BOX[0], BOX[1]) & wp["LON"].between(BOX[2], BOX[3])]
    rc = box.sort_values("ISO_TIME").groupby("STORM").first().reset_index().groupby("q").size()
    hist = [{"quarter": F3.qlabel(q), "e114": int(e114_par.set_index("q")["tc_par"].get(q, -1)), "recount": int(rc.get(q, 0))} for q in range(F3.START_Q, 2026 * 4 + 2)]
    hist_match = all(h["e114"] == h["recount"] or (h["e114"] == -1 and h["recount"] == 0) for h in hist)

    # ---------------- impact of the proposed Amendment 3 (separate outputs)
    obs, ref, ann = refreshed_obs()
    states = {"E123 inputs (pre-refresh)": obs, "E125 refreshed inputs": ref}
    impact = {}
    rec_rows = {}
    for name, df in states.items():
        base_r = F3.compute(df, ann, ORIGINS)
        a3 = F3.compute(with_par_zeros(df, ZERO_Q if all_confirmed else confirmed), ann, ORIGINS)
        m = base_r["overall"].merge(a3["overall"], on=["scope", "unit", "t", "origin"], suffixes=("", "_a3"))
        ch = m[~np.isclose(m["firi3"].fillna(-9), m["firi3_a3"].fillna(-9), atol=1e-12) | (m["band"] != m["band_a3"])]
        fsb, fsa = base_r["features"], a3["features"]
        fch = fsb.merge(fsa, on=["scope", "unit", "t", "feature"], suffixes=("", "_a3"))
        fch = fch[(fch["period"].astype(str) != fch["period_a3"].astype(str)) | ~np.isclose(fch["score"].fillna(-9), fch["score_a3"].fillna(-9), atol=1e-12)]
        ccs_b = F3.subscore(base_r["indicators"], F3.CONDITIONS, "CCS")
        ccs_a = F3.subscore(a3["indicators"], F3.CONDITIONS, "CCS")
        cm = ccs_b.merge(ccs_a, on=["scope", "unit", "t"], suffixes=("", "_a3"))
        cch = cm[~np.isclose(cm["score"].astype(float).fillna(-9), cm["score_a3"].astype(float).fillna(-9), atol=1e-12)]
        impact[name] = {"scores_changed": int(len(ch)), "scopes": sorted(set(ch["scope"])), "max_abs_change": float((ch["firi3"] - ch["firi3_a3"]).abs().max()) if len(ch) else 0.0,
                        "band_changes": int((ch["band"] != ch["band_a3"]).sum()),
                        "detail": ch[["scope", "unit", "origin", "firi3", "firi3_a3", "band", "band_a3"]].to_dict("records"),
                        "features_changed": fch.groupby("feature").size().to_dict(),
                        "feature_rows": fch[["unit", "t", "feature", "period", "period_a3", "raw_value", "raw_value_a3", "score", "score_a3"]].assign(t=lambda d: d["t"].map(F3.qlabel)).to_dict("records"),
                        "ccs_changed": int(len(cch)), "provincial_changed": int((ch["scope"] == "provincial").sum()),
                        "origin_2026q4_feature": None}
        rec_rows[name] = (base_r, a3)
    # 2026-Q4: which PAR quarter would the issue use, with and without A3
    for name, df in states.items():
        b4 = F3.feature_scores(*F3.validate_inputs(df, ann)[:2], [T])
        a4 = F3.feature_scores(*F3.validate_inputs(with_par_zeros(df, ZERO_Q), ann)[:2], [T])
        rb = b4[b4["feature"] == "CEC_cyclones_R"].iloc[0]
        ra = a4[a4["feature"] == "CEC_cyclones_R"].iloc[0]
        impact[name]["origin_2026q4_feature"] = {"period_without_a3": rb["period"], "period_with_a3": ra["period"], "score_without_a3": rb["score"], "score_with_a3": ra["score"],
                                                 "affected": not (str(rb["period"]) == str(ra["period"]) and np.isclose(rb["score"] if rb["score"] == rb["score"] else -9, ra["score"] if ra["score"] == ra["score"] else -9))}

    # ---------------- LFS quarterly methods (frozen mean of rates vs level-based), historical comparison
    lfs = json.loads((ROOT / "data" / "lfs_refresh_result.json").read_text())
    rates = pd.read_csv(ROOT / "data" / "raw" / "psa_lfs_0021B3FKEI2_rates.csv")
    levels = pd.read_csv(ROOT / "data" / "raw" / "psa_lfs_0011B3FKEI1_levels.csv")
    mon = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    lv = levels.merge(rates, on=["Year", "Month"])
    lv = lv[lv["Month"].isin(mon) & (lv["Year"] >= 2021)].copy()
    lv["q"] = lv["Year"] * 4 + lv["Month"].map(mon.index) // 3
    for c in ("Persons in the Labor Force Both sexes", "Unemployed Persons Both sexes", "Unemployment Rate Both sexes"):
        lv[c] = pd.to_numeric(lv[c], errors="coerce")
    gq = lv.groupby("q").agg(months=("Unemployment Rate Both sexes", lambda s: int(s.notna().sum())), mean_of_rates=("Unemployment Rate Both sexes", "mean"),
                             lf=("Persons in the Labor Force Both sexes", "sum"), un=("Unemployed Persons Both sexes", "sum"))
    gq["level_based_rate"] = 100 * gq["un"] / gq["lf"]
    full = gq[gq["months"] == 3]
    lfs_cmp = {"quarters_complete": int(len(full)), "max_abs_rate_difference_pp": round(float((full["mean_of_rates"] - full["level_based_rate"]).abs().max()), 4),
               "mean_abs_rate_difference_pp": round(float((full["mean_of_rates"] - full["level_based_rate"]).abs().mean()), 4),
               "frozen_input_equals_mean_of_rates": bool(np.allclose(obs[obs["feature"] == "unemployment_rate_pct"].set_index("period")["value"].reindex(full.index).dropna(),
                                                                     full["mean_of_rates"].reindex(obs[obs["feature"] == "unemployment_rate_pct"].set_index("period").index).dropna(), atol=1e-9)),
               "q3_2026": lfs}
    # sensitivity: E1 change built from level-based rates (not applied)
    e1_lv = full["level_based_rate"].to_frame("v")
    e1_lv["chg"] = e1_lv["v"] - e1_lv["v"].reindex(e1_lv.index - 4).to_numpy()
    e1_cur = obs[obs["feature"] == "E1_unemployment_change_pp"].set_index("period")["value"]
    j = e1_lv["chg"].dropna().to_frame().join(e1_cur.rename("cur"), how="inner")
    lfs_cmp["e1_change_max_abs_difference_pp"] = round(float((j["chg"] - j["cur"]).abs().max()), 4) if len(j) else None
    alt = ref.copy()
    mask = alt["feature"] == "E1_unemployment_change_pp"
    alt.loc[mask, "value"] = alt.loc[mask, "period"].map(e1_lv["chg"]).astype(float)
    alt = alt[~(mask & alt["value"].isna())]
    ra_ = F3.compute(alt, ann, ORIGINS)["overall"]
    rb_ = rec_rows["E125 refreshed inputs"][0]["overall"]
    mm = rb_.merge(ra_, on=["scope", "unit", "t"], suffixes=("", "_lv"))
    mm = mm[~np.isclose(mm["firi3"].fillna(-9), mm["firi3_lv"].fillna(-9), atol=1e-12)]
    lfs_cmp["firi3_sensitivity_level_based"] = {"scores_changed": int(len(mm)), "max_abs_change": float((mm["firi3"] - mm["firi3_lv"]).abs().max()) if len(mm) else 0.0,
                                                "band_changes": int((mm["band"] != mm["band_lv"]).sum())}
    full.assign(quarter=full.index.map(F3.qlabel)).to_csv(out / "lfs_quarter_methods.csv", lineterminator="\n", float_format="%.6g")

    # ---------------- source status (34 features) and 2026-Q4 readiness
    st125 = pd.read_csv(E125 / "out" / "release_status_refreshed.csv")
    el125 = pd.read_csv(E125 / "E125_FEATURE_ELIGIBILITY_AUDIT.csv").set_index("feature")
    pub = pd.read_csv(E125 / "E125_PUBLICATION_DATE_VERIFICATION.csv").set_index("feature")
    reg_cpi = None
    try:                                                                # revision check: re-query the PSA Region IV-A CPI index (E114 client)
        sys.path.insert(0, str(EXP / "E114_Final_Run" / "runner"))
        import collect_covariates as CC                                 # noqa: E402
        c_new = CC.cpi()
        c_new.to_csv(ROOT / "data" / "raw" / "psa_cpi_region_index_recheck.csv", index=False)
        c_old = pd.read_csv(P.INPUTS["cpi_region_index"])
        k = ["geolocation", "commodity_description", "ym"]
        cm = c_old[c_old["ym"] >= 2021 * 12].merge(c_new[c_new["ym"] >= 2021 * 12], on=k, suffixes=("_old", "_new"), how="outer", indicator=True)
        both = cm[cm["_merge"] == "both"]
        reg_cpi = {"rows_compared": int(len(both)), "revised": int((pd.to_numeric(both["value_old"], errors="coerce") - pd.to_numeric(both["value_new"], errors="coerce")).abs().gt(1e-9).sum()),
                   "new_rows": int((cm["_merge"] == "right_only").sum()), "latest_month": int(c_new["ym"].max()), "sha256": sha(ROOT / "data" / "raw" / "psa_cpi_region_index_recheck.csv")}
    except Exception as e:                                              # noqa: BLE001
        reg_cpi = {"error": f"{type(e).__name__}: {e}"}
    revision = {"cpi_region_index": f"re-queried {today}: {reg_cpi.get('revised', '?')} revised rows, {reg_cpi.get('new_rows', '?')} new rows" if "error" not in reg_cpi else reg_cpi["error"],
                "e118_nasa_power_monthly": "refreshed 2026-10-31 (E125): 0 revisions 2021-2025", "profile": "recounted 2026-10-31 (E125): history matches",
                "par": "recounted 2026-10-31 (E125): history matches except omitted zero quarters", "lfs": f"re-queried {today}: September 2026 still unpublished",
                "e118_retail_poultry": "retrieved 2026-10-31 (E118)", "e118_retail_livestock": "retrieved 2026-10-31 (E118)", "e118_retail_fish": "retrieved 2026-10-31 (E118)",
                "e118_farmgate_cereals": "retrieved 2026-10-31 (E118)", "e118_prod_palay_corn": "retrieved 2026-10-31 (E118)", "e118_prod_vegetables_rootcrops": "retrieved 2026-10-31 (E118)",
                "e118_prod_fisheries": "retrieved 2026-10-31 (E118)", "e118_prod_chicken": "retrieved 2026-10-31 (E118)", "e118_prod_livestock": "retrieved 2026-10-31 (E118)"}
    srs, rdy = [], []
    for r in st125.itertuples():
        f = next(x for x in F3.FEATURES if x.code == r.feature)
        dec = el125.loc[r.feature, "decision"]
        srs.append({"feature": r.feature, "indicator": f.indicator, "source": r.source_key, "geographic_level": "province (5)" if f.scope == "P" else f.unit,
                    "observation_period_needed": r.target_observation_period, "expected_release_rule": r.expected_release_rule, "expected_available_on": r.expected_available_on,
                    "actual_publication_date": "verified (dated source)" if pub.loc[r.feature, "classification"] == "verified" else "not verified",
                    "retrieval_date": today.isoformat() if r.source_key in ("lfs", "cpi_region_index") else r.retrieved_on, "latest_period_in_hand": r.latest_in_hand,
                    "completeness": r.availability_status, "revision_status": revision.get(r.source_key, "not re-queried in E126 (retrieved within the last 11 days)"),
                    "publication_class": pub.loc[r.feature, "classification"], "eligibility": dec, "required_for_2026q4": True})
        # readiness category
        if dec == "BLOCKED":
            cat = "incomplete (expected before the issue: September LFS by rule 2026-12-01)" if r.feature == "EHS_unemployment_change_R" else "incomplete"
        elif str(r.latest_in_hand) >= str(r.target_observation_period) or r.availability_status == "not applicable":
            cat = "already available"
        else:
            cat = "incomplete"
        stale_ok = (f.normalization == "pct" and r.target_observation_period not in ("", None) and "-Q" in str(r.target_observation_period)
                    and T - F3.qindex(r.target_observation_period) >= 2)
        rdy.append({"feature": r.feature, "indicator": f.indicator, "period_used_by_rule": r.target_observation_period, "latest_in_hand": r.latest_in_hand,
                    "category": cat, "q4_2026_observation": "cannot be available by 2027-01-01 (release rule)" if f.normalization == "pct" else "annual: 2025/2026 reference years per rule",
                    "stale_but_eligible": bool(stale_ok), "staleness_quarters_at_issue": (T - F3.qindex(r.target_observation_period)) if "-Q" in str(r.target_observation_period) else None,
                    "decision": dec, "note": el125.loc[r.feature, "reason"] if isinstance(el125.loc[r.feature, "reason"], str) else ""})
    SRS, RDY = pd.DataFrame(srs), pd.DataFrame(rdy)
    SRS.to_csv(ROOT / "E126_SOURCE_RELEASE_STATUS.csv", index=False, lineterminator="\n")
    RDY.to_csv(ROOT / "E126_2026Q4_DATA_READINESS.csv", index=False, lineterminator="\n")

    # ---------------- historical reconciliation: five versions side by side
    v121 = pd.read_csv(EXP / "E121_FIRI3_Implementation" / "E121_FIRI3_OVERALL_RESULTS.csv")[["scope", "unit", "t", "firi3", "band"]]
    v122 = pd.read_csv(EXP / "E122_Data_Cutoff_Audit" / "out" / "firi3_amended_overall.csv")[["scope", "unit", "t", "firi3", "band"]]
    v123 = pd.read_csv(EXP / "E123_FIRI3_Design_Resolution" / "out" / "overall.csv")[["scope", "unit", "t", "firi3", "band"]]
    v125 = pd.read_csv(E125 / "E125_SCORE_RECONCILIATION.csv")
    v125["t"] = v125["origin"].map(F3.qindex)
    v125 = v125[["scope", "unit", "t", "firi3_refreshed", "band_refreshed", "causes"]]
    v126 = rec_rows["E125 refreshed inputs"][1]["overall"][["scope", "unit", "t", "origin", "firi3", "band"]]
    H = (v126.rename(columns={"firi3": "e126_proposed_a3", "band": "band_e126_proposed"})
         .merge(v121.rename(columns={"firi3": "e121_v1_0", "band": "band_e121"}), on=["scope", "unit", "t"])
         .merge(v122.rename(columns={"firi3": "e122_v1_1_a1", "band": "band_e122"}), on=["scope", "unit", "t"])
         .merge(v123.rename(columns={"firi3": "e123_v1_2_a2", "band": "band_e123"}), on=["scope", "unit", "t"])
         .merge(v125.rename(columns={"firi3_refreshed": "e125_refreshed", "band_refreshed": "band_e125", "causes": "e125_causes"}), on=["scope", "unit", "t"]))
    def d(a, b):
        return (H[a] - H[b]).abs().fillna(0) > 1e-8
    H["change_e121_to_e122"] = np.where(d("e122_v1_1_a1", "e121_v1_0"), "Amendment 1 (2021 CPI comparison base removed)", "")
    H["change_e122_to_e123"] = np.where(d("e123_v1_2_a2", "e122_v1_1_a1"), "Amendment 2 (latest complete annual year)", "")
    H["change_e123_to_e125"] = np.where(d("e125_refreshed", "e123_v1_2_a2"), "new source observations (NASA POWER 2026)", "")
    zchg = {(r["unit"], r["origin"]) for r in impact["E125 refreshed inputs"]["detail"]}
    H["change_e125_to_e126_proposed"] = [("proposed processing correction (Amendment 3: verified zero-storm PAR quarters)" if (u, o) in zchg else "")
                                         for u, o in zip(H["unit"], H["origin"])]
    H["status_e126_proposed"] = "PROPOSED (not applied; awaits owner approval)"
    H.to_csv(ROOT / "E126_HISTORICAL_SCORE_RECONCILIATION.csv", index=False, lineterminator="\n", float_format="%.10g")

    # ---------------- decision
    blockers = []
    if today.isoformat() < ISSUE:
        blockers.append(f"B1 issue date {ISSUE} not reached (today {today})")
    if not lfs["complete"]:
        blockers.append("B2 September 2026 national unemployment not published (PSA tables end August 2026)")
    result = "BLOCKED" if blockers else ("READY WITH WARNINGS" if (RDY["decision"] == "READY WITH WARNING").any() else "READY FOR FINAL PRE-ISSUANCE CHECK")
    summary = {"today": today.isoformat(), "baseline": base, "par_verification": {"confirmed_true_zero": confirmed, "all_confirmed": all_confirmed, "e114_absent_quarters_2021plus": absent,
                                                                                     "e114_other_quarters_match_recount": hist_match},
               "impact": impact, "lfs": lfs_cmp, "cpi_region_recheck": reg_cpi, "readiness_counts": RDY["category"].value_counts().to_dict(),
               "decisions": RDY["decision"].value_counts().to_dict(), "blockers": blockers, "result": result}
    json.dump(summary, open(out / "summary.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "impact"}, indent=1, default=str))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("detail", "feature_rows")} for k, v in impact.items()}, indent=1, default=str))
    print(PV[["source", "quarter", "file_covers_quarter", "storms_first_entering_box", "storms_active_in_box_entered_earlier", "storms_first_entering_official_polygon", "nearest_track_point", "verdict"]].to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=date.today().isoformat())
    main(date.fromisoformat(ap.parse_args().today))
