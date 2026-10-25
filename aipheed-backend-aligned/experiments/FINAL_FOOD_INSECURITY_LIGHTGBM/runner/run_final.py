"""FINAL runner (FINAL_PROTOCOL.md). One command reruns everything:

    python run_final.py all          # data -> audit -> score -> long -> news -> psa -> general -> seal
    python run_final.py <phase>      # one phase (score and later phases read out/ files written earlier)

The leakage audit must pass before scoring; scoring refuses to run if the protocol hash does not match.
"""
from __future__ import annotations

import json
import sys
import time

import fi_lib as M
import news_features as NF

np, pd = M.np, M.pd
OUT, DATA = M.OUT, M.DATA
OUT.mkdir(exist_ok=True)
KEYS = ["area_name", "t", "lead"]


def _check_protocol():
    want = (M.HERE / "PROTOCOL_SHA256.txt").read_text().strip()
    got = M.sha256(M.FINAL / "FINAL_PROTOCOL.md")
    assert got == want, f"protocol changed after freezing: {got} != {want}"


# ================================================================================================ phase: data
def phase_data():
    P = M.panel("primary", "primary")
    fam_of = {c: f for f, cs in M.FAMILY_COLS.items() for c in cs}
    src = {
        "A1": ("PSA CPI food and all-items index (OpenSTAT 0012M4ACP22) via E107; PSA provincial food YoY", "province->CALABARZON mean",
               "monthly", "months up to month 2 of the origin quarter (PSA releases about day 5 of the next month)"),
        "A2": ("PSA CPI all-items YoY", "province->CALABARZON mean", "monthly", "months up to month 2 of origin quarter"),
        "A3": ("PSA wholesale rice prices", "province->CALABARZON mean", "quarterly", "quarter t-1"),
        "V1": ("PSA SAE 2021 poverty, POPCEN 2024, land area", "province->CALABARZON mean", "static", "static profile"),
        "C1": ("PAGASA ENSO alert items", "national", "event", "items issued before the issue date"),
        "C2": ("IBTrACS tracks within 300 km", "province->CALABARZON mean", "quarterly", "quarter t (complete)"),
        "C3": ("PSA palay and corn production", "province->CALABARZON mean", "quarterly", "quarter t-1"),
        "C4": ("PSA fisheries production", "province->CALABARZON mean", "quarterly", "quarter t-1"),
        "E1": ("PSA LFS unemployment rate", "national", "monthly", "months of quarter t-1"),
        "E2": ("BSP OFW cash remittances", "national", "quarterly", "quarter t-1; not acquired after 2025-Q4"),
        "N1": ("FSSI-v3 (XLM-R zero-shot) and the project RSS headline corpus (E31+E60), CALABARZON news", "region",
               "daily headlines", "headlines published before the issue date"),
        "H1": ("SWS involuntary hunger, Balance Luzon (E107 H1) and the area's own rounds (h_*)", "SWS area",
               "quarterly rounds", "rounds published before the issue date"),
        None: ("design", "-", "-", "known at issue"),
    }
    rows = []
    for c in M.PRIMARY_COLS:
        f = fam_of.get(c, "H1" if c.startswith("h_") else None)
        s = src[f]
        sub = P[P["t"] >= M.qi("2023-Q3")]
        rows.append({"feature": c, "family": f or "design", "family_name": M.FAMILY_NAMES.get(f, "model structure"),
                     "source": s[0], "geographic_level": s[1], "frequency": s[2], "availability_rule": s[3],
                     "observation_period": f"{M.qs(int(P.loc[P[c].notna(), 't'].min()))}..{M.qs(int(P.loc[P[c].notna(), 't'].max()))}"
                     if P[c].notna().any() else "none",
                     "missing_share_all_origins": round(float(P[c].isna().mean()), 3),
                     "missing_share_scored_origins": round(float(sub[c].isna().mean()), 3),
                     "in_FIL": True, "drop_one_group": f if f in M.FAMILY_COLS and c in M.FAMILY_COLS[f] else ""})
    fm = pd.DataFrame(rows)
    fm.to_csv(DATA / "feature_map.csv", index=False, lineterminator="\n")
    missing = sorted(set(M.FAMILY_COLS) - set(fm["family"]))
    assert not missing and len(M.FAMILY_COLS) == 12, missing
    NF.save_flags(DATA / "news_headline_flags.csv")
    srcs = [
        ("SWS hunger by area 2021-2026 (primary outcome)", DATA / "sws_area_rounds_2021.csv", "SWS media releases",
         "https://sws.org.ph (per-row source column)", "SWS area (NCR, BL, VIS, MIN)", "2021-Q2..2026-Q3",
         "published column (release date); 23 non-commissioned rounds; values verified against SWS (E110, E114)"),
        ("SWS rounds excluded (commissioned / voter base)", DATA / "sws_area_rounds_2021_excluded.csv", "SWS / Stratbase",
         "per-row source", "SWS area", "2025-Q1..Q2", "not used"),
        ("SWS hunger by area 1998-2026 (secondary arm)", DATA / "long" / "sws_area_rounds_full.csv",
         "SWS media release 14 Oct 2026 tables (E114)", "https://sws.org.ph", "SWS area", "1998-Q3..2026-Q3",
         "pre-2021 release = label month end + 60 days (evidence: long/sws_release_date_evidence.csv)"),
        ("PSA CPI provincial food and all-items YoY", M.L.YOY_FILE, "PSA OpenSTAT", "openstat.psa.gov.ph",
         "province (5 CALABARZON)", "2021-01..2026-09", "month m used from O(t) if m <= month 2 of quarter t"),
        ("PSA CPI index provincial (2018=100)", M.L.ACQ / "cpi_index_ACP22.csv", "PSA OpenSTAT 0012M4ACP22",
         "openstat.psa.gov.ph", "province", "2021-01..2026-09", "as above"),
        ("PSA CPI CALABARZON/PH food, all items, rice (long)", DATA / "long" / "cov_cpi.csv", "PSA OpenSTAT "
         "0012M4ACP28 + 0012M4ACP22", "openstat.psa.gov.ph", "region / national", "1994-01..2026-09",
         "month m usable from day 10 of m+1"),
        ("PSA palay production (long)", DATA / "long" / "cov_palay.csv", "PSA OpenSTAT 0012E4EVCP0",
         "openstat.psa.gov.ph", "national", "1987-Q1..2026-Q2", "quarter t-1 at O(t)"),
        ("PSA LFS unemployment (long)", DATA / "long" / "cov_lfs.csv", "PSA OpenSTAT 0021B3FKEI2",
         "openstat.psa.gov.ph", "national", "2005..2026-08", "round m usable from day 1 of m+3"),
        ("NOAA ONI (long)", DATA / "long" / "cov_oni.csv", "NOAA CPC", "cpc.ncep.noaa.gov", "Nino 3.4",
         "1950..2026-09", "season ending m usable from day 10 of m+1"),
        ("IBTrACS PAR tropical cyclones (long)", DATA / "long" / "cov_ibtracs_par.csv", "NOAA IBTrACS v04r01",
         "ncei.noaa.gov", "Philippine Area of Responsibility", "1996-Q1..2026-Q4", "quarter t at O(t)"),
        ("GDELT DOC volume, 4 categories (long)", DATA / "long" / "cov_gdelt_doc.csv", "GDELT DOC 2.0 API",
         "api.gdeltproject.org", "Philippine sources", "2017-01-01..2026-10-01", "day d usable after d"),
        ("Project headline corpus flags (no titles)", DATA / "news_headline_flags.csv",
         "E31 + E60 RSS stores (backend app.news.pipeline_v3.corpus)", "per-article link in the backend store",
         "CALABARZON news", "2021-01..2026-10", "published time < issue date"),
        ("GDELT GKG CALABARZON documents", M.EXP.parents[1] / "backend" / "data" / "gdelt_e85" /
         "gkg_calabarzon_2021_2026.parquet", "GDELT GKG 2.1 (E85 BigQuery pull)", "gdeltproject.org",
         "CALABARZON-located", "2021-01-01..2026-10-14", "GDELT processing timestamp < issue date"),
    ]
    rec = [{"name": n, "file": str(p.relative_to(M.EXP.parents[1])).replace("\\", "/"), "publisher": pub, "url": u,
            "geography": g, "coverage": cov, "availability_rule": rule,
            "sha256": M.sha256(p) if p.exists() else "missing"} for n, p, pub, u, g, cov, rule in srcs]
    pd.DataFrame(rec).to_csv(DATA / "data_sources.csv", index=False, lineterminator="\n")
    P.drop(columns=[]).to_csv(OUT / "panel_features_primary.csv", index=False, lineterminator="\n", float_format="%.6g")
    print("feature map", len(fm), "rows; families", sorted(fm["family"].unique()))


# ================================================================================================ phase: audit
def _forecast_snapshot(t: int) -> dict:
    """FIL zhat, PERSIST z and LOGIT p at origin t, computed from scratch (caches cleared)."""
    for f in (M.known, M.final_values, M.panel, NF.gap_features):
        f.cache_clear()
    P = M.panel("primary", "primary")
    F = M.fil_forecasts(P, M.PRIMARY_COLS, "primary", origins=[t])
    lg = M.logit_forecasts(P, M.PRIMARY_COLS, "primary", [t])
    te = P[P["t"] == t].set_index(KEYS)
    return {"fil": {f"{a}|{k}": round(float(z), 10) for a, k, z in zip(F["area_name"], F["lead"], F["zhat"])},
            "persist": {f"{a}|{k}": round(float(v), 10) for (a, _, k), v in te["h_anom"].items()},
            "logit": {f"{a}|{k}": round(v, 10) for (a, _, k), v in lg.items()}}


def phase_audit():
    rng = np.random.default_rng(M.SEED)
    origins = [M.qi(q) for q in ("2023-Q3", "2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q2",
                                 "2025-Q3", "2026-Q1", "2026-Q2")]
    orig_rounds, orig_corpus = M.rounds.__wrapped__, NF.corpus.__wrapped__
    results = []
    for t in origins:
        base = _forecast_snapshot(t)
        iss = M.issue(t)
        r0 = orig_rounds("primary")
        fut = r0["published"] >= iss
        pert = r0.copy()
        pert.loc[fut, "H"] = rng.uniform(0, 50, int(fut.sum()))
        c0 = orig_corpus()
        cp = c0.copy()
        cf = cp["published"] >= pd.Timestamp(iss)
        for c in NF.CATS + ["anticipatory", "food_event"]:
            cp.loc[cf, c] = rng.permutation(cp.loc[cf, c].to_numpy())
        M.rounds = lambda dataset="primary", _p=pert: _p if dataset == "primary" else orig_rounds(dataset)
        M.rounds.cache_clear = lambda: None
        NF.corpus = lambda _c=cp: _c
        NF.corpus.cache_clear = lambda: None
        try:
            pb = _forecast_snapshot(t)
        finally:
            M.rounds = M.functools.lru_cache(maxsize=2)(orig_rounds)
            NF.corpus = M.functools.lru_cache(maxsize=1)(orig_corpus)
        same = base == pb
        results.append({"origin": M.qs(t), "issue": iss, "future_rounds_perturbed": int(fut.sum()),
                        "future_headlines_perturbed": int(cf.sum()), "n_fil": len(base["fil"]), "identical": same})
        print(M.qs(t), "identical" if same else "CHANGED")
    # negative control: perturbing rounds published BEFORE O(t) must change the forecasts
    t = origins[4]
    base = _forecast_snapshot(t)
    r0 = orig_rounds("primary")
    pert = r0.copy()
    past = r0["published"] < M.issue(t)
    pert.loc[past, "H"] = rng.uniform(0, 50, int(past.sum()))
    M.rounds = lambda dataset="primary", _p=pert: _p if dataset == "primary" else orig_rounds(dataset)
    M.rounds.cache_clear = lambda: None
    try:
        neg = _forecast_snapshot(t)
    finally:
        M.rounds = M.functools.lru_cache(maxsize=2)(orig_rounds)
    neg_changed = neg != base
    print("negative control (past data perturbed) changed:", neg_changed)
    for f in (M.known, M.final_values, M.panel, NF.gap_features):
        f.cache_clear()
    ok = all(r["identical"] for r in results) and all(r["n_fil"] > 0 for r in results) and neg_changed
    M.write_json(OUT / "leakage_audit.json", {"passed": ok, "origins": results,
                                              "negative_control": {"origin": M.qs(t), "changed": neg_changed},
                                              "note": "E107 12-family cut-offs audited in E107/E113 (passed)."})
    assert ok, "leakage audit failed"


# ================================================================================================ phase: score
def _summ(R: pd.DataFrame, model: str = "FIL", bases=None) -> dict:
    return {k: M.decide(R, k, model, bases) for k in M.LEADS}


def phase_score():
    _check_protocol()
    assert json.loads((OUT / "leakage_audit.json").read_text())["passed"], "run the audit first"
    t0 = time.time()
    R = M.evaluate("primary", "primary", M.PRIMARY_COLS)
    R["FIL_class"] = (R["FIL_p"] > 0.5).astype(int)
    R.to_csv(OUT / "predictions_primary.csv", index=False, lineterminator="\n", float_format="%.6g")
    res = {"protocol_sha256": M.sha256(M.FINAL / "FINAL_PROTOCOL.md"), "FIL": _summ(R)}
    res["max_reliable_lead"] = M.max_reliable_lead(res["FIL"])
    res["baseline_decisions"] = {b: _summ(R, b) for b in ["PERSIST", "MA2", "LOGIT"]}
    # pre-registered comparisons (section 5)
    variants = {"FIL-NONEWS": [c for c in M.PRIMARY_COLS if c not in M.NEWS_COLS],
                "FIL-H": M.H_COLS, "FIL-HN": M.H_COLS + M.NEWS_COLS}
    for f, cs in M.FAMILY_COLS.items():
        variants[f"FIL-drop-{f}"] = [c for c in M.PRIMARY_COLS if c not in cs]
    comp = {}
    for name, cols in variants.items():
        Rv = M.evaluate("primary", "primary", cols, shap=False)
        Rv[["area_name", "t", "lead", "q", "label", "y", "zhat", "FIL_p", "FIL_level"]].to_csv(
            OUT / f"pred_{name}.csv", index=False, lineterminator="\n", float_format="%.6g")
        comp[name] = _summ(Rv)
        print(name, [round(comp[name][k]["metrics"]["accuracy"], 3) for k in M.LEADS])
    Rb = M.evaluate("primary", "primary", M.PRIMARY_COLS, areas_train=["BL"], shap=False)
    Rb[["area_name", "t", "lead", "q", "label", "y", "zhat", "FIL_p", "FIL_level"]].to_csv(
        OUT / "pred_FIL-BL.csv", index=False, lineterminator="\n", float_format="%.6g")
    comp["FIL-BL"] = {k: M.decide(Rb[Rb["area_name"] == "BL"], k) if len(Rb) else None for k in M.LEADS}
    res["variants"] = comp
    # SHAP family shares of the issued FIL forecasts
    sh = {}
    for k in M.LEADS:
        D = R[R["lead"] == k]
        tot = sum(D[f"shap_{c}"].abs().mean() for c in M.PRIMARY_COLS)
        grp = {f: sum(D[f"shap_{c}"].abs().mean() for c in cs) / tot for f, cs in M.FAMILY_COLS.items()}
        grp["H (hunger history h_*)"] = sum(D[f"shap_{c}"].abs().mean() for c in M.H_COLS[:4]) / tot
        grp["structure (area, lead)"] = sum(D[f"shap_{c}"].abs().mean() for c in ["area", "lead"]) / tot
        sh[k] = grp
    res["shap_share"] = sh
    res["configs"] = R.groupby("t")[["leaves", "trees", "n_train"]].first().reset_index().assign(
        t=lambda d: d["t"].map(M.qs)).to_dict("records")
    res["runtime_s"] = round(time.time() - t0, 1)
    M.write_json(OUT / "results_primary.json", res)
    for k in M.LEADS:
        d = res["FIL"][k]
        print("lead", k, "n", d["n"], "q", d["n_quarters"], {x: round(d["metrics"][x], 3) for x in
              ("accuracy", "balanced_accuracy", "precision", "recall", "auc", "brier")}, d["criteria"])
    print("max reliable lead", res["max_reliable_lead"])


# ================================================================================================ phase: long
def phase_long():
    _check_protocol()
    R = M.evaluate("long", "long", M.LONG_COLS)
    R["FIL_class"] = (R["FIL_p"] > 0.5).astype(int)
    R.to_csv(OUT / "predictions_long.csv", index=False, lineterminator="\n", float_format="%.6g")
    a = R[(R["q"] >= M.UNTOUCHED[0]) & (R["q"] <= M.UNTOUCHED[1])]
    b = R[R["q"] >= M.PRIMARY_FIRST]
    res = {"untouched_2003_2020": _summ(a, bases=M.BASES_LONG), "y2021_plus": _summ(b, bases=M.BASES_LONG)}
    res["untouched_persist"] = _summ(a, "PERSIST", M.BASES_LONG)
    res["max_reliable_lead_untouched"] = M.max_reliable_lead(res["untouched_2003_2020"])
    res["max_reliable_lead_2021"] = M.max_reliable_lead(res["y2021_plus"])
    sh = {}
    for k in M.LEADS:
        D = a[a["lead"] == k]
        tot = sum(D[f"shap_{c}"].abs().mean() for c in M.LONG_COLS)
        sh[k] = {f: sum(D[f"shap_{c}"].abs().mean() for c in cs) / tot for f, cs in M.LONG_FAMILY.items()}
        sh[k]["H (hunger history)"] = sum(D[f"shap_{c}"].abs().mean() for c in M.H_COLS[:4]) / tot
    res["shap_share_untouched"] = sh
    # long arm without news (GDELT DOC) on 2017+ targets, same rows
    Rn = M.evaluate("long", "long", [c for c in M.LONG_COLS if not c.startswith("ND_")], shap=False)
    j = R.merge(Rn[KEYS + ["FIL_p"]], on=KEYS, suffixes=("", "_nonews"))
    j = j[j["q"] >= M.qi("2018-Q1")]
    nt = {}
    for k in M.LEADS:
        D = j[j["lead"] == k]
        y = D["label"].astype(int).to_numpy()
        nt[k] = {"n": len(D), "acc_news": float(((D["FIL_p"] > .5) == y).mean()),
                 "acc_nonews": float(((D["FIL_p_nonews"] > .5) == y).mean()),
                 "brier": M.boot_diff(D, (D["FIL_p"] - y) ** 2, (D["FIL_p_nonews"] - y) ** 2)}
    res["news_ablation_2018_plus"] = nt
    M.write_json(OUT / "results_long.json", res)
    for name in ("untouched_2003_2020", "y2021_plus"):
        for k in M.LEADS:
            d = res[name][k]
            print(name, "lead", k, "n", d["n"], "q", d["n_quarters"], round(d["metrics"]["accuracy"], 3),
                  round(d["metrics"]["balanced_accuracy"], 3), "persist acc",
                  round(d["baselines"]["PERSIST"]["accuracy"], 3), d["criteria"])


# ================================================================================================ phase: news
def phase_news():
    R = pd.read_csv(OUT / "predictions_primary.csv")
    P = M.panel("primary", "primary")
    res = {}
    # 8.1 ablations on identical rows
    abl = {}
    for a_name, b_name in (("FIL", "FIL-NONEWS"), ("FIL-HN", "FIL-H")):
        A = R[KEYS + ["q", "label", "FIL_p"]] if a_name == "FIL" else pd.read_csv(OUT / f"pred_{a_name}.csv")
        B = pd.read_csv(OUT / f"pred_{b_name}.csv")
        j = A[KEYS + ["q", "label", "FIL_p"]].merge(B[KEYS + ["FIL_p"]], on=KEYS, suffixes=("_a", "_b"))
        per, ps = {}, {}
        for k in M.LEADS:
            D = j[j["lead"] == k]
            y = D["label"].astype(int).to_numpy()
            bt = M.boot_diff(D, (D["FIL_p_a"] - y) ** 2, (D["FIL_p_b"] - y) ** 2)
            per[k] = {"n": len(D), "acc_with": float(((D["FIL_p_a"] > .5) == y).mean()),
                      "acc_without": float(((D["FIL_p_b"] > .5) == y).mean()), "brier_diff": bt,
                      "mcnemar_p": M.mcnemar(y, D["FIL_p_a"], D["FIL_p_b"])}
            ps[k] = bt["p_two"]
        hp = M.holm(ps)
        for k in M.LEADS:
            per[k]["holm_p"] = hp[k]
        abl[f"{a_name} vs {b_name}"] = per
    res["ablation"] = abl
    # 8.2 placebo: news columns permuted across origin quarters (whole blocks), 100 permutations
    rng = np.random.default_rng(M.SEED)
    origins = sorted(P["t"].unique())
    table = P.set_index(KEYS)
    real = {k: float(((R.loc[R["lead"] == k, "FIL_p"] - R.loc[R["lead"] == k, "label"]) ** 2).mean())
            for k in M.LEADS}
    perm_b = {k: [] for k in M.LEADS}
    n_perm = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "news" else 100
    sd = {t: float(M.training(P, t, "primary")["z_tr"].std()) for t in R["t"].unique()}
    for i in range(n_perm):
        mp = dict(zip(origins, rng.permutation(origins)))
        mp["_table"], mp["_cols"] = table, M.NEWS_COLS
        F = M.fil_forecasts(P, M.PRIMARY_COLS, "primary", news_perm=mp)
        j = R[KEYS + ["label", "ref_hat", "zhat", "q"]].merge(F[KEYS + ["zhat"]], on=KEYS, suffixes=("", "_perm"))
        j["p_perm"] = M.add_sigma_prob(j, P, "zhat_perm", "primary", sd)       # FIL's own sigma rule
        for k in M.LEADS:
            D = j[j["lead"] == k]
            perm_b[k].append(float(((D["p_perm"] - D["label"]) ** 2).mean()))
        if i % 10 == 9:
            print("placebo", i + 1)
    res["placebo"] = {k: {"real_brier": real[k], "perm_mean": float(np.mean(perm_b[k])),
                          "p_perm_le_real": float(np.mean(np.array(perm_b[k]) <= real[k])), "n": n_perm}
                      for k in M.LEADS}
    # 8.4 leading and concurrent associations (origin-level means of the 4 areas; BL separately)
    Z = P[P["z"].notna()].copy()
    for c, f in (("ANT_share", 0), ("REP_share", 1)):
        Z[c] = [NF.ant_rep_gap(fw, iss, "C")[f] for fw, iss in zip(Z["sws_newest_fieldwork_end"], Z["issue_date"])]
    gk = {(fw, iss): NF.features(fw, iss, "G") for fw, iss in set(zip(Z["sws_newest_fieldwork_end"], Z["issue_date"]))}
    for c in NF.news_cols("NG"):
        Z[c] = [gk[(fw, iss)][c] for fw, iss in zip(Z["sws_newest_fieldwork_end"], Z["issue_date"])]
    cols_c = M.NEWS_COLS + ["ANT_share", "REP_share"]
    lead_assoc, ps = {}, {}
    for src_cols, tag in ((cols_c, "corpus"), (NF.news_cols("NG"), "gdelt_gkg")):
        for k in M.LEADS:
            D = Z[Z["lead"] == k].groupby("t").agg(z=("z", "mean"), **{c: (c, "first") for c in src_cols})
            Db = Z[(Z["lead"] == k) & (Z["area_name"] == "BL")].set_index("t")
            for c in src_cols:
                d = D[["z", c]].dropna()
                db = Db[["z", c]].dropna()
                if len(d) < 6:
                    continue
                rho, p = M.spearmanr(d[c], d["z"])
                rb = M.spearmanr(db[c], db["z"])[0] if len(db) >= 6 else np.nan
                key = f"{tag}|{c}|lead{k}"
                lead_assoc[key] = {"rho_panel_mean": float(rho), "p": float(p), "n_origins": len(d),
                                   "rho_BL": float(rb)}
                if c in M.NEWS_COLS[1:] and tag == "corpus" or c in ("ANT_share", "REP_share"):
                    ps[key] = float(p)
    hp = M.holm({k: v for k, v in ps.items() if k.split("|")[1] in NF.news_cols("NC")})
    for k, v in hp.items():
        lead_assoc[k]["holm_p_7x4"] = v
    res["leading_association"] = lead_assoc
    # concurrent: quarterly YoY category shares (E112 table) vs the quarter's own hunger anomaly (H - REF), 4-area mean
    qt = pd.read_csv(M.EXP / "E112_Food_Insecurity_Forecasting" / "out" / "news_quarterly_corpus.csv").set_index("q")
    conc = {}
    an = {q: np.mean([M.outcome(a, q) - M.ref_final(a, q) for a in M.AREAS if M.label_final(a, q) is not None])
          for q in sorted({q for (_, q) in M.final_values()}) if any(M.label_final(a, q) is not None for a in M.AREAS)}
    for c in NF.CATS:
        x = pd.DataFrame({"anom": pd.Series(an), "news": qt[f"{c}_yoy"]}).dropna()
        rho, p = M.spearmanr(x["news"], x["anom"])
        conc[c] = {"rho": float(rho), "p": float(p), "n_quarters": len(x)}
    res["concurrent_association"] = conc
    # anticipatory vs reporting, leading vs concurrent (quarterly shares)
    d = NF.corpus()
    d = d[~d["event_dup"]]
    g = d.groupby("q").agg(n=("food_event", "size"), ant=("anticipatory", "sum"),
                           rep=("food_event", "sum"))
    g["rep"] = g["rep"] - g["ant"]
    g["ant_share"], g["rep_share"] = g["ant"] / g["n"], g["rep"] / g["n"]
    g["ant_yoy"], g["rep_yoy"] = g["ant_share"] - g["ant_share"].reindex(g.index - 4).to_numpy(), \
        g["rep_share"] - g["rep_share"].reindex(g.index - 4).to_numpy()
    ar = {}
    for c in ("ant_yoy", "rep_yoy"):
        for shift, nm in ((0, "concurrent"), (1, "news_one_quarter_earlier"), (2, "news_two_quarters_earlier")):
            x = pd.DataFrame({"anom": pd.Series(an), "news": g[c].reindex(pd.Series(an).index - shift).to_numpy()}
                             ).dropna()
            rho, p = M.spearmanr(x["news"], x["anom"]) if len(x) >= 6 else (np.nan, np.nan)
            ar[f"{c}|{nm}"] = {"rho": float(rho), "p": float(p), "n_quarters": len(x)}
    res["anticipatory_vs_reporting"] = ar
    res["corpus_counts"] = {"headlines": int(len(NF.corpus())), "food_event": int(NF.corpus()["food_event"].sum()),
                            "anticipatory": int(NF.corpus()["anticipatory"].sum()),
                            "event_duplicates_removed": int(NF.corpus()["event_dup"].sum()),
                            "gkg_docs": int(len(NF.gkg())), "gkg_event_dups": int(NF.gkg()["event_dup"].sum()),
                            "by_quarter": NF.corpus().groupby("q").size().rename(M.qs).to_dict(),
                            "with_province_code": float(NF.corpus()["province_code"].notna().mean())}
    # surge window examples: news before the 2024 surge (origins 2023-Q4..2024-Q2)
    ex = P[(P["area_name"] == "BL") & (P["lead"] == 1) & P["t"].isin([M.qi(q) for q in
                                                                         ("2023-Q3", "2023-Q4", "2024-Q1",
                                                                          "2024-Q2", "2024-Q3")])]
    res["surge_window_examples"] = ex[["issue_date", "target_quarter", "h_last", "y"] + M.NEWS_COLS].to_dict("records")
    M.write_json(OUT / "results_news.json", res)
    print(json.dumps(res["ablation"], default=str)[:1500])
    print(res["placebo"])


# ================================================================================================ phase: psa
def phase_psa():
    d, _ = M.E.data()
    y = d.yoy.pivot_table(index=["province_code", "ym"], columns="commodity", values="yoy").reset_index()
    y["fpd"] = y["food"] - y["all_items"]
    y["q"] = y["ym"].map(M.L.q_of_ym)
    g = y.groupby(["province_code", "q"]).agg(fpd=("fpd", "mean"), months=("fpd", "count")).reset_index()
    g = g[g["months"] == 3]
    g["squeeze"] = (g["fpd"] > 0).astype(int)
    g["province"] = g["province_code"].map(M.L.NAMES)
    g["quarter"] = g["q"].map(M.qs)
    g.to_csv(OUT / "psa_fpd_province_quarter.csv", index=False, lineterminator="\n", float_format="%.4g")
    res = {"coverage": {"provinces": int(g["province_code"].nunique()), "quarters": [M.qs(int(g["q"].min())),
                                                                                    M.qs(int(g["q"].max()))],
                        "rows": len(g), "missing_months": int(y["fpd"].isna().sum()),
                        "squeeze_rate": float(g["squeeze"].mean()),
                        "by_province_squeeze_rate": g.groupby("province")["squeeze"].mean().round(3).to_dict()}}
    # forecastability of the squeeze sign by persistence (newest 3 published months at O(t))
    fc = {}
    for k in M.LEADS:
        hits = []
        for p_, gp in y.groupby("province_code"):
            s = gp.set_index("ym")["fpd"]
            for t in range(M.qi("2021-Q2"), M.LAST_ORIGIN + 1):
                m0 = M.L.m0_of(t)
                last3 = s.reindex([m0 - 2, m0 - 1, m0]).dropna()
                tgt = g[(g["province_code"] == p_) & (g["q"] == t + k)]
                if len(last3) == 3 and len(tgt):
                    hits.append(int((last3.mean() > 0) == bool(tgt["squeeze"].iloc[0])))
        fc[k] = {"n": len(hits), "persistence_accuracy": float(np.mean(hits)) if hits else None}
    res["persistence_forecastability"] = fc
    # link to hunger: CALABARZON mean FPD vs BL anomaly (concurrent) and FPD known at O(t) vs BL z (leading)
    reg = g.groupby("q")["fpd"].mean()
    conc = pd.DataFrame({"fpd": reg, "anom": pd.Series({q: M.outcome("BL", q) - M.ref_final("BL", q)
                                                        for q in reg.index if M.label_final("BL", q) is not None})}
                        ).dropna()
    rho, p = M.spearmanr(conc["fpd"], conc["anom"])
    tab = pd.crosstab(conc["fpd"] > 0, conc["anom"] > 0)
    res["concurrent_BL"] = {"rho": float(rho), "p": float(p), "n_quarters": len(conc), "crosstab": tab.to_dict()}
    P = M.panel("primary", "primary")
    regm = y.groupby("ym")["fpd"].mean()
    lead, ps = {}, {}
    for k in M.LEADS:
        D = P[(P["area_name"] == "BL") & (P["lead"] == k) & P["z"].notna()].copy()
        D["fpd_known"] = [regm.reindex([M.L.m0_of(t) - 2, M.L.m0_of(t) - 1, M.L.m0_of(t)]).mean() for t in D["t"]]
        rho, p = M.spearmanr(D["fpd_known"], D["z"])
        lead[k] = {"rho": float(rho), "p": float(p), "n": len(D)}
        ps[k] = float(p)
    hp = M.holm(ps)
    for k in M.LEADS:
        lead[k]["holm_p"] = hp[k]
    res["leading_BL"] = lead
    M.write_json(OUT / "results_psa.json", res)
    print(json.dumps(res, default=str)[:2500])


# ================================================================================================ phase: general
def phase_general():
    R = pd.read_csv(OUT / "predictions_primary.csv")
    R["period"] = np.where(R["q"] <= M.qi("2023-Q4"), "early (<=2023)",
                           np.where(R["q"] <= M.qi("2024-Q4"), "middle (2024)", "recent (2025+)"))
    R["direction"] = np.where(R["y"] > R["h_last"], "rising", "falling or flat")
    R["sharp_increase"] = (R["y"] - R["h_last"]) > R["margin_last"]
    methods = ["FIL", "PERSIST", "MA2", "MAJ", "LOGIT"]
    res = {}
    for split in ("period", "area_name", "direction", "true_horizon"):
        res[split] = {}
        for k in M.LEADS:
            for v, D in R[R["lead"] == k].groupby(split):
                y = D["label"].astype(int)
                res[split][f"lead{k}|{v}"] = {"n": len(D), **{m: float(((D[f"{m}_p"] > .5).astype(int) == y).mean())
                                                              for m in methods},
                                              "FIL_mae": float((D["FIL_level"] - D["y"]).abs().mean()),
                                              "PERSIST_mae": float((D["h_last"] - D["y"]).abs().mean())}
    sur = {}
    for k in M.LEADS:
        D = R[(R["lead"] == k) & R["sharp_increase"]]
        sur[k] = {"n_events": len(D), "events": [f"{a} {M.qs(int(q))}" for a, q in zip(D["area_name"], D["q"])],
                  "FIL_elevated_recall": float((D["FIL_p"] > .5).mean()) if len(D) else None,
                  "PERSIST_elevated_recall": float((D["PERSIST_p"] > .5).mean()) if len(D) else None,
                  "FIL_mean_error": float((D["FIL_level"] - D["y"]).mean()) if len(D) else None,
                  "PERSIST_mean_error": float((D["h_last"] - D["y"]).mean()) if len(D) else None}
    res["sharp_increases"] = sur
    lk = pd.read_csv(OUT / "predictions_long.csv")
    lk["sharp_increase"] = (lk["y"] - lk["h_last"]) > lk["margin_last"]
    lu = lk[(lk["q"] >= M.UNTOUCHED[0]) & (lk["q"] <= M.UNTOUCHED[1])]
    res["sharp_increases_long_untouched"] = {
        k: {"n_events": int(lu[(lu["lead"] == k) & lu["sharp_increase"]].shape[0]),
            "FIL_elevated_recall": float((lu[(lu["lead"] == k) & lu["sharp_increase"]]["FIL_p"] > .5).mean()),
            "PERSIST_elevated_recall": float((lu[(lu["lead"] == k) & lu["sharp_increase"]]["PERSIST_p"] > .5).mean())}
        for k in M.LEADS}
    res["by_quarter_lead1"] = R[R["lead"] == 1].groupby("q").apply(
        lambda D: pd.Series({"n": len(D), "FIL_correct": int(((D["FIL_p"] > .5).astype(int) == D["label"]).sum()),
                             "PERSIST_correct": int(((D["PERSIST_p"] > .5).astype(int) == D["label"]).sum())}),
        include_groups=False).rename(M.qs).to_dict("index")
    M.write_json(OUT / "results_general.json", res)
    print(json.dumps(res["sharp_increases"], default=str))


# ================================================================================================ phase: seal
def phase_seal():
    t = M.LAST_ORIGIN
    rows = []
    files = {"FIL": "predictions_primary.csv", "FIL-LONG": "predictions_long.csv",
             "FIL-LONG-S": "predictions_long_s.csv"}
    for dataset, variant, cols, name in (("primary", "primary", M.PRIMARY_COLS, "FIL"),
                                         ("long", "long", M.LONG_COLS, "FIL-LONG"),
                                         ("long", "long_s", M.LONG_S_COLS, "FIL-LONG-S")):
        P = M.panel(dataset, variant)
        F = M.fil_forecasts(P, cols, dataset, origins=[t])
        te = P[P["t"] == t].merge(F, on=KEYS)
        R = pd.read_csv(OUT / files[name])
        for r in te.itertuples():
            prev = R[(R["lead"] == r.lead) & (R["q"] < t)]
            err = prev["y"] - prev["ref_hat"] - prev["zhat"]
            s = float(np.sqrt(np.mean(err ** 2)))
            rows.append({"model": name, "area": r.area_name, "issue_date": r.issue_date, "lead": r.lead,
                         "target_quarter": r.target_quarter, "sws_newest_q": r.sws_newest_q, "h_last": r.h_last,
                         "ref_hat": round(r.ref_hat, 4), "forecast_level": round(r.ref_hat + r.zhat, 4),
                         "p_elevated": round(float(M.norm.cdf(r.zhat / s)), 4),
                         "persistence_level": r.h_last,
                         "persistence_elevated": int(r.h_anom > 0)})
    S = pd.DataFrame(rows)
    p = OUT / "sealed_prospective.csv"
    S.to_csv(p, index=False, lineterminator="\n")
    (OUT / "sealed_prospective.csv.sha256").write_text(M.sha256(p) + "\n")
    print(S.to_string(index=False))
    print("seal", M.sha256(p))


# ================================================================================================ phase: addendum 1
def _check_addendum():
    want = (M.HERE / "ADDENDUM_1_SHA256.txt").read_text().strip()
    assert M.sha256(M.FINAL / "ADDENDUM_1.md") == want, "ADDENDUM_1 changed after freezing"


def _bayes_accuracy(Q: float, R: float, phi: float, mu: float, rng, n_series=2000, T=100, burn=24) -> dict:
    """ADDENDUM_1 A1.1: accuracy of the Bayes rule for ELEVATED when the level process (Q, phi, mu) and the noise R
    are known exactly; true horizon h = lead + 1; REF = mean of the four observed quarters before the target."""
    hits = {k: [] for k in M.LEADS}
    base = {k: [] for k in M.LEADS}
    for _ in range(n_series):
        lv = np.empty(T)
        lv[0] = mu
        e = rng.normal(0, np.sqrt(Q), T)
        for i in range(1, T):
            lv[i] = mu + phi * (lv[i - 1] - mu) + e[i]
        y = lv + rng.normal(0, np.sqrt(R), T)
        a, P = y[0], R                                       # Kalman filter, filtered level after each observation
        filt = np.empty(T)
        filt[0] = a
        for i in range(1, T):
            a, P = mu + phi * (a - mu), phi ** 2 * P + Q
            K = P / (P + R)
            a, P = a + K * (y[i] - a), (1 - K) * P
            filt[i] = a
        for n in range(burn, T - 6):
            for k in M.LEADS:
                h = k + 1
                ex = lambda j: mu + phi ** j * (filt[n] - mu)        # noqa: E731  E[y_{n+j}] for j >= 1
                ref = np.mean([y[i] if i <= n else ex(i - n) for i in range(n + h - 4, n + h)])
                pred = ex(h) - ref > 0
                truth = y[n + h] > np.mean(y[n + h - 4:n + h])
                hits[k].append(pred == truth)
                base[k].append(truth)
    return {k: {"bayes_accuracy": float(np.mean(hits[k])), "base_rate": float(np.mean(base[k]))} for k in M.LEADS}


def phase_addendum1():
    _check_protocol()
    _check_addendum()
    rng = np.random.default_rng(M.SEED)
    r = M.rounds("long")
    pre = r[r["q"] < M.PRIMARY_FIRST]
    R6 = (6 / 1.959964) ** 2
    sim = {}
    for a in M.AREAS:
        s = pre[pre["area"] == a].groupby("q")["H"].mean()
        d = [(s[q] - s[q - 1], s[q - 1]) for q in s.index if q - 1 in s.index]
        dh = np.array([x[0] for x in d])
        lag = np.array([x[1] for x in d])
        Q = max(float(np.mean(dh ** 2)) - 2 * R6, 0.25)
        mu = float(s.mean())
        b = float(np.polyfit(lag - mu, dh, 1)[0])
        phi = float(min(max(1 + b, 0.0), 1.0))
        sim[a] = {"Q": Q, "R": R6, "mu": mu, "phi_ar1": phi, "n_pairs": len(d),
                  "random_walk": _bayes_accuracy(Q, R6, 1.0, mu, rng),
                  "ar1": _bayes_accuracy(Q, R6, phi, mu, rng)}
        print(a, {k: round(v["bayes_accuracy"], 3) for k, v in sim[a]["random_walk"].items()},
              {k: round(v["bayes_accuracy"], 3) for k, v in sim[a]["ar1"].items()}, "phi", round(phi, 3))
    res = {"addendum_sha256": M.sha256(M.FINAL / "ADDENDUM_1.md"), "simulation": sim}
    res["simulation_mean"] = {m: {k: float(np.mean([sim[a][m][k]["bayes_accuracy"] for a in M.AREAS]))
                                  for k in M.LEADS} for m in ("random_walk", "ar1")}
    # A1.2 FIL-LONG-S
    Rs = M.evaluate("long", "long_s", M.LONG_S_COLS)
    Rs.to_csv(OUT / "predictions_long_s.csv", index=False, lineterminator="\n", float_format="%.6g")
    a_ = Rs[(Rs["q"] >= M.UNTOUCHED[0]) & (Rs["q"] <= M.UNTOUCHED[1])]
    b_ = Rs[Rs["q"] >= M.PRIMARY_FIRST]
    out = {}
    for nm, D0 in (("2003_2020_second_use", a_), ("y2021_plus", b_)):
        out[nm] = {"decisions": _summ(D0, bases=M.BASES_LONG), "mae": {}}
        for k in M.LEADS:
            D = D0[D0["lead"] == k]
            e1, e0, e2 = (D["FIL_level"] - D["y"]).abs(), (D["h_last"] - D["y"]).abs(), (D["ma2"] - D["y"]).abs()
            out[nm]["mae"][k] = {"n": len(D), "FIL_LONG_S": float(e1.mean()), "PERSIST": float(e0.mean()),
                                 "MA2": float(e2.mean()),
                                 "vs_persist": M.boot_diff(D, e1.to_numpy(), e0.to_numpy()),
                                 "vs_ma2": M.boot_diff(D, e1.to_numpy(), e2.to_numpy())}
            print(nm, k, "acc", round(out[nm]["decisions"][k]["metrics"]["accuracy"], 3), "MAE",
                  round(e1.mean(), 2), round(e0.mean(), 2), round(e2.mean(), 2),
                  "p vs MA2", round(out[nm]["mae"][k]["vs_ma2"]["p_less"], 3))
    res["FIL_LONG_S"] = out
    # level-forecast comparison of every model on the long sets (protocol section 6 continuous metrics)
    Lk = pd.read_csv(OUT / "predictions_long.csv")
    lev = {}
    for nm, D0 in (("2003_2020_untouched", Lk[(Lk["q"] >= M.UNTOUCHED[0]) & (Lk["q"] <= M.UNTOUCHED[1])]),
                   ("y2021_plus", Lk[Lk["q"] >= M.PRIMARY_FIRST])):
        lev[nm] = {}
        for k in M.LEADS:
            D = D0[D0["lead"] == k]
            e1, e0, e2 = (D["FIL_level"] - D["y"]).abs(), (D["h_last"] - D["y"]).abs(), (D["ma2"] - D["y"]).abs()
            lev[nm][k] = {"n": len(D), "FIL_LONG": float(e1.mean()), "PERSIST": float(e0.mean()), "MA2": float(e2.mean()),
                          "rmse": {"FIL_LONG": float(np.sqrt(((D["FIL_level"] - D["y"]) ** 2).mean())),
                                   "PERSIST": float(np.sqrt(((D["h_last"] - D["y"]) ** 2).mean())),
                                   "MA2": float(np.sqrt(((D["ma2"] - D["y"]) ** 2).mean()))},
                          "vs_persist": M.boot_diff(D, e1.to_numpy(), e0.to_numpy()),
                          "vs_ma2": M.boot_diff(D, e1.to_numpy(), e2.to_numpy())}
    res["FIL_LONG_level"] = lev
    M.write_json(OUT / "results_addendum1.json", res)


# ================================================================================================ phase: addendum 2
def phase_addendum2():
    want = (M.HERE / "ADDENDUM_2_SHA256.txt").read_text().strip()
    assert M.sha256(M.FINAL / "ADDENDUM_2.md") == want, "ADDENDUM_2 changed after freezing"
    P = M.panel("long", "long")
    D = P[(P["lead"] == 1) & P["z"].notna()].groupby("t").agg(z=("z", "mean"), x=("ND_gap_agri_supply", "first"),
                                                               q=("q", "first")).dropna()
    res = {"addendum_sha256": want}
    for nm, lo, hi in (("a_2018_2020_untouched", M.qi("2018-Q1"), M.qi("2020-Q4")),
                       ("b_2021_plus", M.PRIMARY_FIRST, M.LAST_OUTCOME)):
        d = D[(D["q"] >= lo) & (D["q"] <= hi)]
        rho, p2 = M.spearmanr(d["x"], d["z"])
        p1 = p2 / 2 if rho > 0 else 1 - p2 / 2
        res[nm] = {"rho": float(rho), "p_one_sided": float(p1), "n_origins": len(d),
                   "targets": [M.qs(int(q)) for q in d["q"]]}
    res["replicated"] = res["a_2018_2020_untouched"]["rho"] > 0 and res["a_2018_2020_untouched"]["p_one_sided"] < 0.05
    res["consistent_2021"] = res["b_2021_plus"]["rho"] > 0
    M.write_json(OUT / "results_addendum2.json", res)
    print(json.dumps(res, indent=1))


PHASES = {"data": phase_data, "audit": phase_audit, "score": phase_score, "long": phase_long, "news": phase_news,
          "psa": phase_psa, "general": phase_general, "addendum1": phase_addendum1, "addendum2": phase_addendum2, "seal": phase_seal}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in PHASES.items():
        if which in ("all", name):
            print(f"===== {name}")
            fn()
