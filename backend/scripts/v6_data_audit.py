"""
v6 Stage 1 data audit (docs/aipheed/v6/DATA_AUDIT.md): re-derive from raw sources held locally, never trust a stored file.

  A  SWS target: copies, validation, fieldwork/quarter alignment, duplicates, revisions against an independent extraction
     of SWS's 14 Oct 2026 release tables (branch aiPHeed/e114-genuine-forecast, PDF sha recorded there), true lead in months
  B  CPI: rice YoY recomputed from the raw OpenSTAT file with independent code vs E131 and the v4 snapshots
  C  E119 point-in-time features: period strictly before the issue quarter; missingness types
  D  Poverty: raw file vs snapshot
  E  FIRI v2: recomputed with app.ml.inference.firi.score_v2 at 3 historical issues from the stored raw indicators
  F  NLP: FSSI-v3 recomputed from stored articles + intensities; XLM-R re-scoring of a sample of articles (offline cache)

    python -I backend/scripts/v6_data_audit.py [--skip-xlmr]
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.evidence import AREAS  # noqa: E402
from app.forecasting.validation import validate_sws_rounds  # noqa: E402
from app.forecasting.v4 import features as F  # noqa: E402

EXP = REPO / "aipheed-backend-aligned" / "experiments"
OUT = REPO / "docs" / "aipheed" / "v6" / "results"
CPI_RAW = EXP / "E131_Objectives_Resolution" / "data" / "raw" / "psa_cpi_regional_2021_2026.csv"
POV_RAW = EXP / "E131_Objectives_Resolution" / "data" / "raw" / "psa_poverty_population_2021_2023_2025.csv"
REGIONS = {"metro_manila": ["National Capital Region"],
           "balance_luzon": ["Cordillera", "Region I ", "Region II ", "Region III ", "Region IV-A", "MIMAROPA", "Region V "],
           "visayas": ["Region VI ", "Region VII ", "Region VIII ", "Negros Island"],
           "mindanao": ["Region IX ", "Region X ", "Region XI ", "Region XII ", "Region XIII", "Bangsamoro"]}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------ A  SWS
def audit_sws() -> dict:
    res = {}
    raw = pd.read_csv(T.SWS_ROUNDS)
    src = EXP / "E110_Hunger_Generalization" / "data" / "sws_area_rounds.csv"
    res["backend_copy_equals_E110_source"] = sha(T.SWS_ROUNDS) == sha(src)
    res["validation_problems"] = validate_sws_rounds(raw)
    fs = pd.to_datetime(raw.fieldwork.str.split("/").str[0])
    fe = pd.to_datetime(raw.fieldwork.str.split("/").str[1])
    mid = fs + (fe - fs) / 2
    lab = mid.dt.year.astype(str) + "-Q" + ((mid.dt.month - 1) // 3 + 1).astype(str)
    res["fieldwork_midpoint_quarter_equals_label"] = int((lab == raw.quarter).sum())
    res["rounds"] = int(len(raw))
    res["duplicate_rounds"] = int(raw.duplicated(["quarter", "fieldwork"]).sum())
    res["commissioned_kept"] = int(raw.commissioned.astype(str).str.lower().eq("true").sum())
    res["publication_lag_days"] = (pd.to_datetime(raw.published) - fe).dt.days.describe()[["min", "50%", "max"]].to_dict()
    # independent extraction from the official 14 Oct 2026 release tables
    txt = subprocess.run(["git", "show", "aiPHeed/e114-genuine-forecast:aipheed-backend-aligned/experiments/E114_Final_Run/data/"
                          "sws_rounds_1998_2026.csv"], cwd=REPO, capture_output=True, text=True, encoding="utf-8").stdout
    ind = pd.read_csv(io.StringIO(txt))
    ind = ind[ind.year >= 2021]
    rows = []
    for r in raw.itertuples():
        m = ind[(ind.year == fs[r.Index].year) & (ind.month.isin([fs[r.Index].month, fe[r.Index].month]))]
        for a in AREAS:
            rows.append({"quarter": r.quarter, "fieldwork": r.fieldwork, "area": a, "stored": getattr(r, a),
                         "release_table": float(m[a].iloc[0]) if len(m) else np.nan, "matched": len(m) == 1})
    cmp_ = pd.DataFrame(rows)
    cmp_["diff"] = cmp_.stored - cmp_.release_table
    cmp_.to_csv(OUT / "audit_sws_vs_release_tables.csv", index=False)
    res["independent_source"] = ("SWS media release 14 Oct 2026, Tables 1-6 (sha256 recorded in the E114 file; PDF not "
                                 "re-opened this session)")
    res["independent_rows_compared"] = int(cmp_.matched.sum())
    res["independent_max_abs_diff"] = float(cmp_[cmp_.matched]["diff"].abs().max())
    res["independent_mismatches_gt_0.05"] = cmp_[cmp_.matched & (cmp_["diff"].abs() > 0.05)].to_dict("records")
    res["unmatched_rounds"] = sorted(set(cmp_[~cmp_.matched].fieldwork))
    # true lead in months: issue date (first day of D) to the target's fieldwork midpoint, Lead 2 S-U rows
    qt = T.quarter_table(T.load_rounds())
    midq = raw.assign(mid=mid).groupby("quarter").mid.mean()
    su = pd.read_csv(REPO / "docs" / "aipheed" / "v2" / "results" / "v2_outer_predictions.csv")
    su2 = su[su.lead == 2].assign(target=lambda d: d.tqi.map(T.qs))
    lead_m = [(midq[t] - pd.Timestamp(i)).days / 30.44 for i, t in zip(su2.issue, su2.target)]
    lat_m = [(pd.Timestamp(i) - midq[T.qs(int(q))]).days / 30.44 for i, q in
             zip(su2.issue, su2.tqi - su2.h)]
    res["lead2_months_issue_to_target_fieldwork"] = {"min": float(np.min(lead_m)), "median": float(np.median(lead_m)), "max": float(np.max(lead_m))}
    res["lead2_months_latest_fieldwork_to_issue"] = {"median": float(np.median(lat_m))}
    res["lead2_months_latest_fieldwork_to_target_fieldwork_median"] = float(np.median(np.add(lead_m, lat_m)))
    return res


# ------------------------------------------------------------------ B  CPI
def audit_cpi() -> dict:
    c = pd.read_csv(CPI_RAW, encoding="utf-8-sig")
    c["region"] = c["Geolocation"].str.lstrip(". ")
    rice = c[c["Commodity Description"].str.startswith("01.1.1.12")]
    months = [x for x in c.columns if x[:4].isdigit()]
    long = rice.melt(id_vars="region", value_vars=months, var_name="ym", value_name="v")
    long["v"] = pd.to_numeric(long.v, errors="coerce")
    long["date"] = pd.to_datetime(long.ym, format="%Y %b")
    long = long.sort_values(["region", "date"])
    long["yoy"] = long.groupby("region").v.pct_change(12, fill_method=None) * 100
    long = long[long.date >= "2022-01-01"]
    long["quarter"] = long.date.dt.year.astype(str) + "-Q" + ((long.date.dt.month - 1) // 3 + 1).astype(str)
    q = long.groupby(["region", "quarter"]).agg(yoy=("yoy", "mean"), n=("v", "count")).reset_index()
    q = q[q.n == 3]
    snap = F.table()
    rows = []
    for issue in ("2023-07-01", "2024-10-01", "2026-10-01"):
        s = snap[snap.issue == issue].set_index("area")
        for a in AREAS:
            per = s.loc[a, "rice_yoy__period"]
            sel = q[(q.quarter == per) & q.region.apply(lambda r: any(r == k.strip() or r.startswith(k) for k in REGIONS[a]))]
            rows.append({"issue": issue, "area": a, "period": per, "snapshot": s.loc[a, "rice_yoy"],
                         "recomputed": float(sel.yoy.mean()), "regions": int(sel.region.nunique()),
                         "period_before_issue": pd.Period(per.replace("-", ""), freq="Q").end_time.date() < date.fromisoformat(issue)})
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "audit_cpi_recompute.csv", index=False)
    return {"rows": len(d), "max_abs_diff": float((d.snapshot - d.recomputed).abs().max()),
            "all_periods_before_issue": bool(d.period_before_issue.all()), "regions_per_area": d.groupby("area").regions.first().to_dict()}


# ------------------------------------------------------------------ C/D  E119 features and poverty
def audit_features() -> dict:
    snap = F.table()
    out = {"snapshot_rows": len(snap)}
    bad = 0
    for f in ("typhoons_PAR", "oni_quarter_mean", "E1_unemployment_change_pp", "news_gdelt_shortage_share", "rice_yoy"):
        ok = snap[f].notna()
        per = snap.loc[ok, f"{f}__period"].astype(str)
        iq = snap.loc[ok, "issue"].map(lambda i: T.qi(f"{i[:4]}-Q{(int(i[5:7]) - 1) // 3 + 1}"))
        bad += int((per.map(T.qi) >= iq).sum())
        out[f"{f}_missing"] = int((~ok).sum())
    out["values_with_period_not_before_issue_quarter"] = bad
    e119 = pd.read_csv(EXP / "E119_Preprocessing" / "E119_REGIONAL_MODELING_DATASET.csv")
    st = pd.concat([e119[c] for c in e119.columns if c.endswith("__status")]).astype(str).str.split(" ").str[0]
    out["E119_status_types"] = st.value_counts().to_dict()
    pov = pd.read_csv(POV_RAW)
    s = snap[snap.issue == "2026-10-01"].set_index("area")
    ncr = float(pov[pov.geography.str.startswith("National Capital Region")]["pov_2025"].iloc[0])
    out["poverty_ncr_2025_raw_vs_snapshot"] = [ncr, float(s.loc["metro_manila", "poverty"])]
    return out


# ------------------------------------------------------------------ E/F  FIRI v2 and NLP
def audit_firi_nlp(skip_xlmr: bool) -> dict:
    from app.ml.inference import firi as FI
    from app.ml.inference import thesis_system as TS
    from app.news import pipeline_v3 as P3
    h = pd.read_csv(REPO / "backend" / "data" / "thesis" / "firi2_history.csv")
    h = h[h.FIRI.notna()]
    picks = sorted(h.issue_date.unique())
    picks = [picks[0], picks[len(picks) // 2], picks[-1]]
    rows = []
    for issue in picks:
        for r in h[h.issue_date == issue].itertuples():
            raw = {k: {"x": v.get("x"), "status": v.get("status")} for k, v in json.loads(r.indicators_json).items()}
            for k in raw:
                if raw[k]["status"] == "insufficient_history":
                    raw[k]["status"] = "ok"
            res = FI.score_v2(raw, TS.prior_for(r.origin_quarter), TS.reference()["weightsLead2"].get(r.origin_quarter))
            n1 = json.loads(r.indicators_json).get("N1", {}).get("x")
            fs = P3.fssi_v3(r.province_code, T.qi(r.origin_quarter))
            rows.append({"issue": issue, "province": r.province_code, "stored_FIRI": r.FIRI, "recomputed_FIRI": res["firi"],
                         "stored_N1": n1, "recomputed_FSSI_v3": fs["fssi"], "n_articles": fs["n"]})
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "audit_firi_nlp.csv", index=False)
    out = {"firi_issues": picks, "firi_rows": len(d),
           "firi_max_abs_diff": float((d.stored_FIRI - d.recomputed_FIRI).abs().max()),
           "fssi_rows_with_value": int(d.stored_N1.notna().sum()),
           "fssi_max_abs_diff": float((d.stored_N1 - d.recomputed_FSSI_v3).abs().max()) if d.stored_N1.notna().any() else None}
    if skip_xlmr:
        out["xlmr"] = "skipped"
        return out
    os.environ["HF_HUB_OFFLINE"] = "1"
    from app.news import scoring as SC
    key = SC.current_model_key()
    arts = {json.loads(l)["article_key"]: json.loads(l) for l in (REPO / "backend" / "data" / "news_e31" / "articles.jsonl")
            .read_text(encoding="utf-8").splitlines()}
    scored = [json.loads(l) for l in (REPO / "backend" / "data" / "news_e31" / "scores.jsonl").read_text(encoding="utf-8").splitlines()]
    scored = [s for s in scored if s.get("model_key") == key and s.get("status") == "OK" and s["article_key"] in arts]
    sample = sorted(scored, key=lambda s: s["article_key"])[:: max(1, len(scored) // 12)][:12]
    scorer = SC.xlmr_scorer()
    res = []
    for s in sample:
        a = arts[s["article_key"]]
        new = scorer(a.get("title", ""), a.get("summary", "") or "")
        res.append({"article_key": s["article_key"], "stored": s["score"], "rescored": new["score"], "status": new["status"]})
    x = pd.DataFrame(res)
    x.to_csv(OUT / "audit_xlmr_rescore.csv", index=False)
    out["xlmr"] = {"model_key": key, "scored_rows_matching_key": len(scored), "sample": len(x),
                   "max_abs_diff": float((x.stored - x.rescored).abs().max())}
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"A_sws": audit_sws(), "B_cpi": audit_cpi(), "C_D_features": audit_features(),
           "E_F_firi_nlp": audit_firi_nlp("--skip-xlmr" in sys.argv)}
    (OUT / "data_audit.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
