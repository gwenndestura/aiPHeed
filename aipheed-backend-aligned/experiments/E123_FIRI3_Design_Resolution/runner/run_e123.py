"""E123: FIRI3 design resolution (Amendment 2), data verification and prospective-validation preparation.
No model is trained; FIRI v2, production and earlier experiment outputs are not modified.

    python run_e123.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
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
from app.ml.inference import firi3 as F3      # noqa: E402
from app.ml.inference import firi as FI       # noqa: E402  (read only)
import e120 as E120                           # noqa: E402

P = E120.P
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
ORIGINS = list(range(F3.START_Q, 2026 * 4 + 3))
E122 = EXP / "E122_Data_Cutoff_Audit"


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verify_hashes():
    ok = (sha(EXP / "E121_FIRI3_Implementation" / "E121_FIRI3_PROTOCOL.md") == F3.PROTOCOL_SHA256
          and sha(E122 / "E122_FIRI3_PROTOCOL_AMENDMENT_1.md") == F3.AMENDMENT_1_SHA256
          and sha(ROOT / "E123_FIRI3_PROTOCOL_AMENDMENT_2.md") == F3.AMENDMENT_2_SHA256 == (HERE / "AMENDMENT_2_SHA256.txt").read_text().strip())
    assert ok, "protocol / amendment hash mismatch"
    return ok


def inputs():
    L, ann = E120.load()
    return L.assign(source=L["feature"] + " @ " + L["unit"]), ann.assign(source=ann["feature"] + " @ " + ann["unit"] + " (" + ann["ref"] + ")")


def band_of(v, k):
    return F3.band(v, int(k)) if v is not None and not pd.isna(v) else "not_computable"


def cmp(base, alt, label, scope):
    m = base.merge(alt, on=["scope", "unit", "t"], suffixes=("", "_alt"))
    m = m[(m["scope"] == scope)].dropna(subset=["firi3", "firi3_alt"])
    rk = [g["firi3"].rank().corr(g["firi3_alt"].rank()) for _, g in m.groupby("t") if len(g) == 5 and g["firi3"].nunique() > 1 and g["firi3_alt"].nunique() > 1]
    top = [g.loc[g["firi3"].idxmax(), "unit"] == g.loc[g["firi3_alt"].idxmax(), "unit"] for _, g in m.groupby("t") if len(g) == 5]
    return {"variant": label, "scope": scope, "rows": int(len(m)),
            "mean_abs_change": round(float((m["firi3"] - m["firi3_alt"]).abs().mean()), 4) if len(m) else None,
            "max_abs_change": round(float((m["firi3"] - m["firi3_alt"]).abs().max()), 4) if len(m) else None,
            "band_change_pct": round(100 * float((m["band"] != m["band_alt"]).mean()), 1) if len(m) else None,
            "rank_spearman_mean": round(float(np.mean(rk)), 3) if rk else None,
            "same_top_province_pct": round(100 * float(np.mean(top)), 1) if top else None}


def main():
    verify_hashes()
    watched = [B / "app" / "ml" / "inference" / "firi.py", B / "data" / "thesis" / "firi2_history.csv", B / "data" / "thesis" / "firi2_reference.json"]
    before = {str(p.relative_to(REPO)): sha(p) for p in watched}
    obs, ann = inputs()
    R1 = F3.compute(obs, ann, ORIGINS)
    R2 = F3.compute(obs.sample(frac=1, random_state=11), ann, ORIGINS)
    deterministic = all(R1[k].to_csv(index=False) == R2[k].to_csv(index=False) for k in ("features", "overall"))
    FS, IND, OV = R1["features"], R1["indicators"], R1["overall"]
    CCS = F3.subscore(IND, F3.CONDITIONS, "CCS")
    SVS = F3.subscore(IND, F3.STRUCTURAL, "SVS")
    CORE = F3.common_core(IND, OV)

    # ---------------- state checks against E122 (Amendment 1 kept; only DI-3 rows may differ)
    e122 = pd.read_csv(E122 / "out" / "firi3_amended_overall.csv")
    m = e122[["scope", "unit", "t", "firi3", "indicators_used"]].merge(OV[["scope", "unit", "t", "firi3", "indicators_used"]], on=["scope", "unit", "t"], suffixes=("_e122", "_a2"))
    m["changed"] = ~np.isclose(m["firi3_e122"].fillna(-9), m["firi3_a2"].fillna(-9), atol=1e-12)
    changed = m[m["changed"]]
    a2_effect = {"rows_changed": int(len(changed)), "origins": sorted(set(F3.qlabel(int(t)) for t in changed["t"])),
                 "scopes": sorted(set(changed["scope"])), "computable_e122": int(m["firi3_e122"].notna().sum()), "computable_a2": int(m["firi3_a2"].notna().sum()),
                 "max_abs_change": round(float((changed["firi3_e122"] - changed["firi3_a2"]).abs().max()), 4) if changed["firi3_e122"].notna().any() else None,
                 "detail": changed[["unit", "t", "firi3_e122", "firi3_a2", "indicators_used_e122", "indicators_used_a2"]].assign(t=lambda d: d["t"].map(F3.qlabel)).to_dict("records")}
    log = R1["log"]
    state = {"amendment_1_rows_rejected": log["pre2021_base_rows_rejected"], "amendment_1_by_series": log["pre2021_base_rows_by_series"],
             "e122_scores_changed_vs_e121": json.loads((E122 / "out" / "summary.json").read_text())["effect_vs_e121"]["changed"], "a2_effect": a2_effect}

    # ---------------- DI-3 annual
    ehs = FS[FS["normalization"] == "rank5"][["origin", "t", "issue_date", "unit", "feature", "period", "avail_date", "status", "score", "raw_value", "note"]]
    di3 = ehs.groupby(["feature", "origin"]).agg(reference_year=("period", "first"), status=("status", "first"), note=("note", "first"),
                                                  avail=("avail_date", "first"), issue=("issue_date", "first")).reset_index()
    di3_checks = {"year_shown": bool(ehs.loc[ehs["score"].notna(), "period"].astype(str).str.fullmatch(r"\d{4}").all()),
                  "published_before_issue": bool((ehs.loc[ehs["score"].notna(), "avail_date"].astype(str) < ehs.loc[ehs["score"].notna(), "issue_date"].astype(str)).all()),
                  "complete_years_only": True, "skipped_incomplete": sorted(set(ehs["note"].dropna()) - {""})}
    ann_c = F3.validate_inputs(obs, ann)[1]
    for (f, o), g in ehs[ehs["score"].notna()].groupby(["feature", "origin"]):
        series = next(x.series for x in F3.FEATURES if x.code == f)
        y = g["period"].iloc[0]
        if set(ann_c[(ann_c["feature"] == series) & (ann_c["ref"].astype(str) == str(y))]["unit"]) != set(F3.PROVINCES):
            di3_checks["complete_years_only"] = False

    # ---------------- DI-4 publication classification (four categories)
    EVID = {  # source evidence available in the repository (no web evidence could be retrieved in E123: PSA sites 403, Internet Archive offline)
        "D01": ("provisionally eligible", "PSA CPI release rule (about day 5-10 of m+1); 32 province-months archived (ledger V1/V2) but no quarter has all 3 months archived"),
        "D02": ("provisionally eligible", "as D01"), "D03": ("provisionally eligible", "PSA CPI release rule; no archive"),
        "D05": ("provisionally eligible", "PSA quarterly wholesale price release rule; no archive"),
        "D07": ("provisionally eligible", "PSA monthly farmgate price release rule; no archive"),
        "D08": ("provisionally eligible", "PSA monthly retail price release rule; no archive"), "D09": ("provisionally eligible", "as D08"), "D10": ("provisionally eligible", "as D08"),
        "D20": ("provisionally eligible", "PSA quarterly palay/corn production release rule; no archive"), "D21": ("provisionally eligible", "as D20"),
        "D22": ("provisionally eligible", "PSA quarterly crop production release rule; no archive"), "D23": ("provisionally eligible", "as D22"),
        "D24": ("provisionally eligible", "PSA quarterly fisheries release rule; no archive"),
        "D26": ("provisionally eligible", "PSA quarterly livestock and poultry release rule; no archive"), "D27": ("provisionally eligible", "as D26"),
        "D33": ("verified", "IBTrACS track positions are real-time observations; count complete at quarter end"),
        "D34": ("verified", "as D33"),
        "D36": ("provisionally eligible", "NASA POWER documented latency (monthly values within about two months); values may be revised"),
        "D37": ("provisionally eligible", "as D36"),
        "D40": ("provisionally eligible", "PSA monthly LFS release rule (about 5-6 weeks); no archive"),
        "D41": ("unverified", "owner-compiled from PSA provincial LFS tables / infographics; the '30 June of Y+1' date is an assumption, not a documented PSA rule; 2023 Batangas value corroborated by a PSA RSSO IV-A release found by search (document not retrievable: 403)"),
        "D42": ("provisionally eligible", "first dated news report for 25% of quarters (verified rows); others by BSP release rule"),
        "D50": ("unverified", "SAE 2021 poverty: availability from 2025-07-01 is the V1 assumption in firi.py, not an archived release date"),
        "D60": ("verified", "articles carry publication timestamps; FSSI recomputed exactly from articles published before each issue"),
        "D62": ("verified", "GDELT dated articles; quarter complete before the issue (vintage caveat: queried 2026-10-25)"),
    }
    pub = []
    for f in F3.FEATURES:
        s = FS[(FS["feature"] == f.code) & FS["score"].notna()]
        cls, why = EVID[f.dataset]
        late = int((s["avail_date"].astype(str) >= s["issue_date"].astype(str)).sum())
        pub.append({"feature": f.code, "indicator": f.indicator, "dataset": f.dataset, "classification": "ineligible" if late else cls, "evidence": why,
                    "scored_rows": int(len(s)), "rows_with_archived_date": int((s["status"] == "verified").sum()),
                    "rows_available_after_issue": late, "change_from_e122": ("downgraded: provisional -> unverified (date is an assumption)" if cls == "unverified" else "unchanged")})
    PUB = pd.DataFrame(pub)
    unver = set(PUB.loc[PUB["classification"] == "unverified", "feature"])
    alt_fs = FS[~FS["feature"].isin(unver)]
    strict_ind = F3.indicator_scores(alt_fs)
    strict_ov = F3.overall(strict_ind, alt_fs)
    doc_view = {"excluded_unverified_features": sorted(unver),
                "computable": {sc: int(g["firi3"].notna().sum()) for sc, g in strict_ov.groupby("scope")},
                "verified_only_view": "not computable: only 4 features have verified dates (cyclones x2, FSSI, GDELT)"}

    # ---------------- DI-5 news / GDELT
    fr = pd.read_csv(ROOT / "out" / "fssi_recompute.csv")
    both = fr.dropna(subset=["stack_n1", "recomputed"])
    g = pd.read_csv(P.INPUTS["gdelt"])
    g["d"] = pd.to_datetime(g["Date"], errors="coerce")
    g = g[(g["d"] >= "2021-01-01")]
    g["period"] = g["d"].dt.year * 4 + (g["d"].dt.month - 1) // 3
    gq = g[g["category"] == "shortage"].groupby("period").agg(v=("Value", "mean"), days=("Value", "size"), last=("d", "max")).reset_index()
    mine = obs[(obs["feature"] == "news_gdelt_shortage_share")][["period", "value", "avail"]]
    gm = mine.merge(gq, on="period", how="left")
    gm["quarter_end"] = gm["period"].map(lambda q: (pd.Timestamp(F3.issue_date(int(q))) - pd.Timedelta(days=1)))
    news = {"fssi_rows": int(len(fr)), "fssi_sufficient": int(len(both)), "fssi_max_abs_diff": float((both["stack_n1"] - both["recomputed"]).abs().max()) if len(both) else None,
            "fssi_article_count_mismatch": int((fr["n"] != fr["stack_n"]).sum()),
            "gdelt_quarters": int(len(gm)), "gdelt_max_abs_diff": float((gm["value"] - gm["v"]).abs().max()),
            "gdelt_first_quarter": F3.qlabel(int(gm["period"].min())), "gdelt_last_quarter": F3.qlabel(int(gm["period"].max())),
            "gdelt_days_per_quarter_min": int(gm["days"].min()), "gdelt_avail_after_quarter_end": bool((pd.to_datetime(gm["avail"]) > gm["quarter_end"]).all()),
            "gdelt_daily_rows_pre2021_in_file": int((pd.to_datetime(pd.read_csv(P.INPUTS["gdelt"])["Date"], errors="coerce") < "2021-01-01").sum())}

    # ---------------- DI-6 Batangas
    owner = pd.read_csv(P.INPUTS["emp_owner"])
    bt = owner[owner["province"] == "Batangas"][["year", "data_status", "employment_rate_pct", "unemployment_rate_pct", "underemployment_rate_pct",
                                                 "employed_persons_thousands", "underemployed_persons_thousands", "source_status"]].copy()
    bt["implied_underemployment_pct"] = (100 * bt["underemployed_persons_thousands"] / bt["employed_persons_thousands"]).round(1)
    a_e119 = pd.read_csv(EXP / "E119_Preprocessing" / "E119_PROVINCIAL_ANNUAL_INDICATORS.csv")
    a_e119 = a_e119[(a_e119["province"] == "Batangas") & a_e119["feature"].str.contains("employment")]
    fsb = FS[(FS["unit"] == "Batangas") & FS["feature"].str.startswith("EHS_")][["origin", "feature", "period", "raw_value", "score"]].dropna(subset=["score"])
    chain = []
    for r in fsb.drop_duplicates(["feature", "period"]).itertuples():
        col = "underemployment_rate_pct" if "under" in r.feature else "unemployment_rate_pct"
        src = owner[(owner["province"] == "Batangas") & (owner["year"] == int(r.period))][col]
        src_v = float(src.iloc[0]) if len(src) and not pd.isna(src.iloc[0]) else None
        e119_v = a_e119[(a_e119["feature"].str.startswith("provincial_under" if "under" in r.feature else "provincial_unemp")) & (a_e119["reference_year"].astype(str) == str(r.period))]["value"]
        chain.append({"feature": r.feature, "reference_year": r.period, "owner_file_value": src_v, "e119_value": float(e119_v.iloc[0]) if len(e119_v) else None,
                      "firi3_raw_value": r.raw_value, "matches": src_v is not None and abs(src_v - r.raw_value) < 1e-9})
    CH = pd.DataFrame(chain)
    # rank with and without Batangas 2023/2024 underemployment (sensitivity, not an adjustment)
    no_bu = FS[~((FS["unit"] == "Batangas") & (FS["feature"] == "EHS_underemployment_prov"))]
    bt_sens = cmp(OV, F3.overall(F3.indicator_scores(no_bu)), "without Batangas underemployment", "provincial")

    # ---------------- comparisons: supplementary scores vs overall
    pv = IND.pivot_table(index=["scope", "unit", "t"], columns="indicator", values="score").reset_index()
    X = OV.merge(CCS[["scope", "unit", "t", "score", "band", "members_used", "status"]].rename(columns={"score": "ccs", "band": "ccs_band", "members_used": "ccs_members", "status": "ccs_status"}),
                 on=["scope", "unit", "t"]).merge(SVS[["scope", "unit", "t", "score", "band", "status"]].rename(columns={"score": "svs", "band": "svs_band", "status": "svs_status"}),
                                                  on=["scope", "unit", "t"]).merge(CORE[["scope", "unit", "t", "fixed_core", "cross_core", "cross_core_indicators", "cross_core_status"]], on=["scope", "unit", "t"])
    po = X[(X["scope"] == "provincial")]

    def kendall_w(col, sub):
        R = sub.pivot_table(index="t", columns="unit", values=col).dropna()
        if len(R) < 2:
            return None, len(R)
        Rk = R.rank(axis=1)
        n, mm = Rk.shape[1], Rk.shape[0]
        S = ((Rk.sum(axis=0) - Rk.sum(axis=0).mean()) ** 2).sum()
        return round(float(12 * S / (mm ** 2 * (n ** 3 - n))), 3), mm

    def top(col, sub):
        R = sub.pivot_table(index="t", columns="unit", values=col).dropna()
        return R.idxmax(axis=1).value_counts().to_dict()

    rank_cmp = {c: {"kendall_w": kendall_w(c, po)[0], "origins": kendall_w(c, po)[1], "times_top": top(c, po)} for c in ("firi3", "ccs", "svs", "fixed_core")}
    corr = {f"{a} vs {b}": round(float(po[[a, b]].dropna().corr(method="spearman").iloc[0, 1]), 3) for a, b in
            (("firi3", "ccs"), ("firi3", "svs"), ("ccs", "svs"), ("firi3", "fixed_core"), ("firi3", "cross_core"))}
    reg = X[X["scope"] == "regional"]
    corr["regional firi3 vs ccs"] = round(float(reg[["firi3", "ccs"]].dropna().corr(method="spearman").iloc[0, 1]), 3)

    # ---------------- A. dominance
    dom = []
    okr = OV[OV["firi3"].notna()].merge(pv, on=["scope", "unit", "t"])
    for sc, g in okr.groupby("scope"):
        for i in [x for x in F3.INDICATORS if x in g.columns]:
            gi = g[g[i].notna()]
            if gi.empty:
                continue
            share = (gi[i] / gi["indicators_available"]) / gi["firi3"]
            push = (gi[i] - 0.5) / gi["indicators_available"]
            loo = cmp(OV, F3.overall(IND, drop_indicators=(i,)), f"without {i}", sc)
            # between-province variance explained per origin (same indicator set rows only)
            expl = []
            if sc == "provincial":
                for t, gg in g.groupby("t"):
                    if len(gg) == 5 and gg["indicators_used"].nunique() == 1 and gg["firi3"].var() > 0 and gg[i].notna().all():
                        expl.append(float(np.cov(gg[i] / gg["indicators_available"], gg["firi3"], ddof=0)[0, 1] / gg["firi3"].var(ddof=0)))
            most = gi.assign(p=push.abs()).sort_values("p", ascending=False).head(3)
            dom.append({"scope": sc, "indicator": i, "rows": int(len(gi)), "score_mean": round(float(gi[i].mean()), 3), "score_sd": round(float(gi[i].std()), 3),
                        "score_min": round(float(gi[i].min()), 3), "score_max": round(float(gi[i].max()), 3),
                        "share_of_firi3_mean": round(float(share.mean()), 3), "share_min": round(float(share.min()), 3), "share_max": round(float(share.max()), 3),
                        "mean_abs_push_from_0_5": round(float(push.abs().mean()), 4),
                        "between_province_variance_explained": round(float(np.mean(expl)), 3) if expl else None, "comparable_origins": len(expl),
                        "loo_mean_abs_change": loo["mean_abs_change"], "loo_band_change_pct": loo["band_change_pct"], "loo_rank_spearman": loo["rank_spearman_mean"],
                        "most_affected": "; ".join(f"{r.unit} {F3.qlabel(int(r.t))} ({(r[i] - .5) / r.indicators_available:+.3f})" for _, r in most.iterrows())})
    DOM = pd.DataFrame(dom)

    # ---------------- B. weighting sensitivity
    W = {"redundancy-adjusted (E120 rule)": None, "conditions 1/2 : structure 1/2": None, "structure 2/3 : conditions 1/3": None}
    ppiv = pv[pv["scope"] == "provincial"].set_index(["unit", "t"])[list(F3.INDICATORS)]
    rc = ppiv.corr(method="spearman", min_periods=8)
    W["redundancy-adjusted (E120 rule)"] = {d: 1 / (1 + sum(max(0, rc.loc[d, e]) for e in rc.columns if e != d and not np.isnan(rc.loc[d, e]))) for d in rc.columns}
    # equal indicator weights already give conditions 4/6 and structure 2/6; these shift that balance
    W["conditions 1/2 : structure 1/2"] = {**{i: 1 / 2 / 4 for i in F3.CONDITIONS}, **{i: 1 / 2 / 2 for i in F3.STRUCTURAL}}
    W["structure 2/3 : conditions 1/3"] = {**{i: 1 / 3 / 4 for i in F3.CONDITIONS}, **{i: 2 / 3 / 2 for i in F3.STRUCTURAL}}
    for i in F3.INDICATORS:
        W[f"{i} x2"] = {**{j: 1.0 for j in F3.INDICATORS}, i: 2.0}
        W[f"{i} x0.5"] = {**{j: 1.0 for j in F3.INDICATORS}, i: 0.5}
    WS = []
    for name, w in W.items():
        alt = F3.overall(IND, weights=w)
        WS += [cmp(OV, alt, name, "provincial"), cmp(OV, alt, name, "regional")]
    rng = np.random.default_rng(123)
    rr = {"provincial": [], "regional": []}
    for _ in range(300):
        alt = F3.overall(IND, weights=dict(zip(F3.INDICATORS, rng.dirichlet(np.ones(6)))))
        for sc in rr:
            rr[sc].append(cmp(OV, alt, "r", sc))
    for sc, xs in rr.items():
        WS.append({"variant": "random Dirichlet(1) x300 (median)", "scope": sc, "rows": xs[0]["rows"],
                   **{k: float(np.median([x[k] for x in xs if x[k] is not None])) if any(x[k] is not None for x in xs) else None
                      for k in ("mean_abs_change", "max_abs_change", "band_change_pct", "rank_spearman_mean", "same_top_province_pct")}})
    WSD = pd.DataFrame(WS)
    # stability across quarters: per-origin rank agreement under the conditions/structure re-weights
    stab_q = []
    for name in ("conditions 1/2 : structure 1/2", "structure 2/3 : conditions 1/3"):
        alt = F3.overall(IND, weights=W[name])
        mm_ = OV.merge(alt, on=["scope", "unit", "t"], suffixes=("", "_alt"))
        mm_ = mm_[(mm_["scope"] == "provincial")].dropna(subset=["firi3", "firi3_alt"])
        for t, gg in mm_.groupby("t"):
            if len(gg) == 5:
                stab_q.append({"variant": name, "origin": F3.qlabel(int(t)), "rank_spearman": round(float(gg["firi3"].rank().corr(gg["firi3_alt"].rank())), 3),
                               "band_changes": int((gg["band"] != gg["band_alt"]).sum())})
    STQ = pd.DataFrame(stab_q)

    # ---------------- C. missingness
    miss = []
    pr = X[(X["scope"] == "provincial") & X["firi3"].notna()]
    for k, g in pr.groupby("indicators_available"):
        gc = g[g["fixed_core"].notna()]
        miss.append({"k": int(k), "rows": int(len(g)), "origins": f"{F3.qlabel(int(g['t'].min()))}..{F3.qlabel(int(g['t'].max()))}",
                     "mean_firi3": round(float(g["firi3"].mean()), 3), "rows_with_fixed_core": int(len(gc)),
                     "mean_fixed_core": round(float(gc["fixed_core"].mean()), 3) if len(gc) else None,
                     "mean_firi3_minus_core": round(float((gc["firi3"] - gc["fixed_core"]).mean()), 4) if len(gc) else None,
                     "mean_abs_firi3_minus_core": round(float((gc["firi3"] - gc["fixed_core"]).abs().mean()), 4) if len(gc) else None,
                     "max_abs_firi3_minus_core": round(float((gc["firi3"] - gc["fixed_core"]).abs().max()), 4) if len(gc) else None,
                     "band_differs_from_core_pct": round(100 * float((gc["band"] != [band_of(v, 4) for v in gc["fixed_core"]]).mean()), 1) if len(gc) else None,
                     "sets": "; ".join(f"{s}: {n}" for s, n in g["indicators_used"].value_counts().items())})
    MISS = pd.DataFrame(miss)
    # quarter-to-quarter changes: availability vs feature changes (same unit, consecutive computed origins)
    dec = []
    for (sc, u), g in X[X["firi3"].notna()].sort_values("t").groupby(["scope", "unit"]):
        g = g.set_index("t")
        for t in g.index:
            if t - 1 in g.index:
                a, b = g.loc[t - 1, "indicators_used"].split(), g.loc[t, "indicators_used"].split()
                q = pv[(pv["scope"] == sc) & (pv["unit"] == u)].set_index("t")
                common = sorted(set(a) & set(b))
                d = float(g.loc[t, "firi3"] - g.loc[t - 1, "firi3"])
                dc = float(q.loc[t, common].mean() - q.loc[t - 1, common].mean())
                dec.append({"scope": sc, "unit": u, "origin": F3.qlabel(int(t)), "change": d, "feature_change_part": dc, "availability_part": d - dc, "set_changed": a != b})
    DEC = pd.DataFrame(dec)
    dec_sum = {sc: {"pairs": int(len(g)), "mean_abs_change": round(float(g["change"].abs().mean()), 4),
                    "mean_abs_feature_part": round(float(g["feature_change_part"].abs().mean()), 4), "mean_abs_availability_part": round(float(g["availability_part"].abs().mean()), 4),
                    "pairs_with_set_change": int(g["set_changed"].sum()),
                    "availability_share_of_abs_change": round(float(g["availability_part"].abs().sum() / g["change"].abs().sum()), 3)} for sc, g in DEC.groupby("scope")}

    # ---------------- D. classification stability
    cls = []
    base = OV[OV["firi3"].notna()][["scope", "unit", "t", "firi3", "band", "indicators_available"]]
    tests = {f"remove {i}": F3.overall(IND, drop_indicators=(i,)) for i in F3.INDICATORS}
    tests.update({k: F3.overall(IND, weights=v) for k, v in W.items() if not k.endswith(("x2", "x0.5"))})
    for name, alt in tests.items():
        for sc in ("provincial", "regional"):
            if name == "remove PSV" and sc == "regional":
                continue
            c = cmp(OV, alt, name, sc)
            cls.append({"perturbation": name, "scope": sc, "rows": c["rows"], "band_change_pct": c["band_change_pct"]})
    fc = X[X["firi3"].notna() & X["fixed_core"].notna()]
    for sc, g in fc.groupby("scope"):
        cls.append({"perturbation": "common core (fixed FMA AFP CEC EHS) vs overall", "scope": sc, "rows": int(len(g)),
                    "band_change_pct": round(100 * float((g["band"] != [band_of(v, 4) for v in g["fixed_core"]]).mean()), 1)})
    xc = X[X["firi3"].notna() & X["cross_core"].notna()]
    cls.append({"perturbation": "cross-province core vs overall", "scope": "provincial", "rows": int(len(xc)),
                "band_change_pct": round(100 * float((xc["band"] != [band_of(v, len(s.split())) for v, s in zip(xc["cross_core"], xc["cross_core_indicators"])]).mean()), 1) if len(xc) else None})
    CLS = pd.DataFrame(cls)
    near = OV[OV["firi3"].notna()]
    near_share = {sc: round(float(((g["firi3"] - .5).abs() < g["indicators_available"].map(F3.chance_sd)).mean()), 3) for sc, g in near.groupby("scope")}

    # ---------------- snapshots (retrospective, v1.2; write once) with all required fields
    src_hash = {k: sha(v) for k, v in P.INPUTS.items() if Path(v).exists()}
    snap_log = []
    for t in ORIGINS:
        o_ = F3.qlabel(t)
        d = ROOT / "snapshots" / o_
        blobs = {"features.csv": FS[FS["t"] == t], "indicators.csv": IND[IND["t"] == t].assign(component_scores=lambda x: x["component_scores"].map(json.dumps)),
                 "scores.csv": X[X["t"] == t]}
        blobs = {k: v.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode() for k, v in blobs.items()}
        files = {k: hashlib.sha256(b).hexdigest() for k, b in blobs.items()}
        if (d / "manifest.json").exists():
            assert json.loads((d / "manifest.json").read_text())["files"] == files, f"snapshot {o_} would change: refused"
            snap_log.append("verified unchanged")
            continue
        d.mkdir(parents=True)
        for k, b in blobs.items():
            (d / k).write_bytes(b)
        (d / "manifest.json").write_text(json.dumps({"origin": o_, "issue_date": F3.issue_date(t), "kind": "retrospective", "firi3_version": F3.VERSION,
                                                     "protocol_sha256": F3.PROTOCOL_SHA256, "amendment_1_sha256": F3.AMENDMENT_1_SHA256,
                                                     "amendment_2_sha256": F3.AMENDMENT_2_SHA256, "source_sha256": src_hash, "files": files,
                                                     "written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=1))
        snap_log.append("written")

    # ---------------- write
    CCS.merge(OV[["scope", "unit", "t", "firi3", "band"]].rename(columns={"band": "firi3_band"}), on=["scope", "unit", "t"]).to_csv(
        ROOT / "E123_CURRENT_CONDITIONS_RESULTS.csv", index=False, lineterminator="\n", float_format="%.10g")
    SVS.merge(OV[["scope", "unit", "t", "firi3", "band"]].rename(columns={"band": "firi3_band"}), on=["scope", "unit", "t"]).to_csv(
        ROOT / "E123_STRUCTURAL_VULNERABILITY_RESULTS.csv", index=False, lineterminator="\n", float_format="%.10g")
    CORE.to_csv(ROOT / "E123_COMMON_CORE_RESULTS.csv", index=False, lineterminator="\n", float_format="%.10g")
    PUB.to_csv(ROOT / "E123_PUBLICATION_DATE_AUDIT.csv", index=False, lineterminator="\n")
    for name, df in (("features", FS), ("overall", OV), ("indicator_dominance", DOM), ("weighting_sensitivity", WSD), ("weighting_by_quarter", STQ),
                     ("missingness_by_k", MISS), ("change_decomposition", DEC), ("classification_stability", CLS), ("batangas_chain", CH), ("di3_annual", di3),
                     ("scores_all", X)):
        df.to_csv(OUT / f"{name}.csv", index=False, lineterminator="\n", float_format="%.10g")
    pd.DataFrame(bt).to_csv(OUT / "batangas_owner_rows.csv", index=False, lineterminator="\n")
    cov = {}
    for nm, D in (("FIRI3", OV.rename(columns={"firi3": "score"})), ("CCS", CCS), ("SVS", SVS), ("fixed_core", CORE.rename(columns={"fixed_core": "score"})),
                  ("cross_core", CORE.rename(columns={"cross_core": "score"}))):
        cov[nm] = {sc: f"{int(g['score'].notna().sum())}/{len(g)}" + (f" (from {g.loc[g['score'].notna(), 'origin'].min()})" if g["score"].notna().any() else "") for sc, g in D.groupby("scope")}
    summary = {"hashes_ok": True, "deterministic": deterministic, "state": state, "di3": di3_checks, "doc_view": doc_view, "news": news,
               "batangas": {"chain_all_match": bool(CH["matches"].all()), "chain": CH.to_dict("records"), "sensitivity": bt_sens,
                            "implied_vs_reported": bt[["year", "underemployment_rate_pct", "implied_underemployment_pct"]].to_dict("records")},
               "coverage": cov, "rank_comparison": rank_cmp, "correlations": corr, "change_decomposition": dec_sum, "near_threshold_share": near_share,
               "snapshots": {k: snap_log.count(k) for k in set(snap_log)}, "firi_v2_unchanged": before == {k: sha(REPO / k) for k in before}}
    json.dump(summary, open(OUT / "summary.json", "w"), indent=1, default=str)
    pd.set_option("display.width", 250)
    print(json.dumps(summary, indent=1, default=str))
    print(DOM.drop(columns=["most_affected"]).to_string()); print(WSD.to_string()); print(MISS.to_string()); print(CLS.to_string())
    assert deterministic and summary["firi_v2_unchanged"] and di3_checks["complete_years_only"] and di3_checks["published_before_issue"]


if __name__ == "__main__":
    main()
