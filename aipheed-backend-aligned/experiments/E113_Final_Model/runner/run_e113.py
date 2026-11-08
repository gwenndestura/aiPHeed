"""E113 runner (PROTOCOL_E113.md + ADDENDUM_1.md).

    python run_e113.py all        # news -> audit -> score -> analyses -> prospective -> export (one command)
    python run_e113.py <phase>    # one phase
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

import e113_lib as L

E, F, G, H9, np, pd = L.E, L.F, L.G, L.H9, L.np, L.pd
OUT = L.OUT
AUDIT_ORIGINS = ("2023-Q2", "2024-Q1", "2024-Q4", "2025-Q3", "2026-Q1")
EARLIER = ("E107_Twelve_Indicator_LightGBM", "E108_Best_Defensible_Forecasting", "E109_Hunger_Forecasting",
           "E110_Hunger_Generalization", "E111_Hunger_Forecast_Audit", "E112_Food_Insecurity_Forecasting")
SEAL_B_ISSUE = "2026-10-25"


def git_state() -> dict:
    def g(*a):
        return subprocess.run(["git", *a], cwd=E.REPO, capture_output=True, text=True).stdout.strip()
    return {"commit": g("rev-parse", "HEAD"), "branch": g("branch", "--show-current"),
            "protocol_sha256": L.sha256(L.E113 / "PROTOCOL_E113.md"), "addendum1_sha256": L.sha256(L.E113 / "ADDENDUM_1.md"),
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def check() -> dict:
    st = git_state()
    assert st["protocol_sha256"] == (L.HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "PROTOCOL_E113.md changed"
    assert st["addendum1_sha256"] == (L.HERE / "ADDENDUM_1_SHA256.txt").read_text().strip(), "ADDENDUM_1.md changed"
    return st


def earlier_seals() -> dict:
    out = {}
    for e in EARLIER:
        p = L.EXP / e / "out" / "sealed_prospective.csv"
        want = (p.parent / "sealed_prospective.csv.sha256").read_text().strip()
        out[e] = {"sha256": L.sha256(p), "unchanged": L.sha256(p) == want}
    return out


# ================================================================================================ phase: news
def phase_news() -> None:
    OUT.mkdir(exist_ok=True)
    for src, t in L.build_composites().items():
        t.to_csv(OUT / f"news_composites_{src}.csv", index=False, lineterminator="\n", float_format="%.8g")
        print(src, len(t), "quarters")
    L.composites.cache_clear()


# ================================================================================================ phase: leakage audit (§10)
def _snapshot(t: int, issue: str) -> dict:
    out = {}
    for k in (1, 2):
        for a in L.AREAS:
            for m in L.MODELS:
                f = L._forecast(m, t, k, a)
                out[(m, k, a)] = None if f is None else f["forecast"]
    return out


def phase_audit() -> None:
    check()
    rng = np.random.default_rng(L.SEED)
    res = {"future_data": [], "date_rules": {
        "SWS": "rounds with published < O(t) (string compare on ISO dates)",
        "news": "quarter q used only if its last headline was published before O(t); L=0 -> quarter t, L=1 -> t-1",
        "CPI": "month m used only from day 10 of month m+1",
        "rice": "quarter t-1 wholesale YoY (E107 A3)",
        "fits": "alpha, news lag, phi, rho, Q, scales from training pairs / vintages known at O(t) only"}}
    for qs in AUDIT_ORIGINS:
        t = E.qi(qs)
        issue = E.issue(t)
        L.clear_caches()
        base = _snapshot(t, issue)
        r0 = F.rounds()
        fake = r0.copy()
        fake["H"], fake["published"] = fake["H"] + 40, issue
        news = {}
        for src in ("C", "G"):
            tab = L.composites(src).copy()
            fut = tab.index > t
            for c in [c for c in tab.columns if c.endswith("_yoy") or c in ("dis", "sup", "pri", "ast", "agri")]:
                tab.loc[fut, c] = rng.normal(0, 5, int(fut.sum()))
            news[src] = tab
        cpi = L.cpi_monthly().copy()
        cpi[[not L.cpi_available(int(m), issue) for m in cpi.index]] += 50
        rice = L.rice_table().copy()
        rice[rice.index > t] += 50
        L._OVERRIDE.update({"rounds": pd.concat([r0, fake], ignore_index=True), ("news", "C"): news["C"],
                            ("news", "G"): news["G"], "cpi": cpi, "rice": rice})
        L.clear_caches()
        try:
            pert = _snapshot(t, issue)
        finally:
            L._OVERRIDE.clear()
            L.clear_caches()
        diffs = [abs(base[x] - pert[x]) for x in base if base[x] is not None]
        nn = sum(base[x] is None for x in base) == sum(pert[x] is None for x in pert)
        res["future_data"].append({"origin": qs, "forecasts_compared": len(diffs), "max_abs_change": max(diffs) if diffs else None,
                                   "same_eligibility": nn, "passed": nn and (not diffs or max(diffs) < 1e-9)})
        print(qs, res["future_data"][-1])
    res["passed"] = all(x["passed"] for x in res["future_data"])
    L.write_json(OUT / "leakage_audit.json", res)
    assert res["passed"], "LEAKAGE AUDIT FAILED"


# ================================================================================================ phase: score
def lead_block(k: int):
    df = L.evaluate(k)
    if not len(df):
        return {"rows": 0}, df
    out = {"rows": len(df), "quarters": int(df["q"].nunique()), "first": E.qs(int(df["q"].min())),
           "last": E.qs(int(df["q"].max())), "rows_by_area": df["area"].value_counts().to_dict(),
           "true_horizons": {str(a): int(b) for a, b in df["true_horizon"].value_counts().sort_index().items()},
           "metrics": {m: L.metrics(df, m) for m in L.MODELS},
           "metrics_BL": {m: L.metrics(df[df["area"] == "BL"], m) for m in L.MODELS},
           "regimes": {m: L.regime_diffs(df, m) for m in L.MODELS if m != "RW"},
           "surge": {m: L.surge_metrics(df, m) for m in L.MODELS},
           "dm_vs_rw": {m: L.dm(df, m, "RW", k) for m in L.MODELS if m != "RW"},
           "news_lag_chosen": {m: df[f"{m}_lag"].value_counts().to_dict() for m in ("SH-N", "SH-MRN", "SH-FULL")},
           "alpha_chosen": {m: df[f"{m}_alpha"].value_counts().to_dict() for m in L.CANDIDATES},
           "per_quarter_diff_vs_rw": {m: {E.qs(int(q)): float(v) for q, v in L.qdiff(df, m).items()} for m in L.CANDIDATES}}
    Lq = pd.DataFrame({m: L.sloss(df, m).groupby(df["q"]).mean() for m in L.MODELS})
    out["mcs"] = L.mcs(Lq, k)
    pre = df[df["post_break"] == 0]
    out["S-PRE"] = {"rows": len(pre), "quarters": int(pre["q"].nunique()),
                    "mase": {m: float(L.sloss(pre, m).mean()) for m in L.MODELS} if len(pre) else {}}
    return out, df


def phase_score() -> None:
    st = check()
    res = {"run": st, "earlier_seals": earlier_seals(), "lead": {}}
    frames = {}
    for k in L.LEADS:
        s, df = lead_block(k)
        res["lead"][str(k)] = s
        frames[k] = df
        if len(df):
            df.to_csv(OUT / f"panel_lead{k}.csv", index=False, lineterminator="\n", float_format="%.10g")
        print(f"lead {k}: {s.get('rows', 0)} rows / {s.get('quarters', 0)} quarters")
    allr = pd.concat([d for d in frames.values() if len(d)], ignore_index=True)
    res["by_true_horizon"] = {str(int(h)): {"rows": int(len(g)), **{m: float((g[m] - g["y"]).abs().mean()) for m in L.MODELS}}
                              for h, g in allr.groupby("true_horizon")}

    # 7.1 reliability family (Holm within lead over the six candidates), R1-R4, fixed sequence
    dec = {}
    for k in L.LEADS:
        b = res["lead"][str(k)]
        if not b.get("rows"):
            continue
        hp = L.holm({m: b["dm_vs_rw"][m]["p"] for m in L.CANDIDATES})
        b["holm_candidates"] = hp
        dec[str(k)] = {m: L.decide(frames[k], m, k, hp.get(m)) for m in L.CANDIDATES}
    res["decision"] = dec

    def maxlead(m):
        best = None
        for k in L.LEADS:
            if dec.get(str(k), {}).get(m, {}).get("reliable"):
                best = k
            else:
                break
        return best
    res["max_reliable_lead"] = {m: maxlead(m) for m in L.CANDIDATES}

    # 7.2 / 7.3 / 7.4 test families
    fams = {"news": [("SH-MRN", "SH-MR"), ("SH-FULL", "SH-MRP"), ("SH-N", "RW")],
            "cpi": [("SH-MRP", "SH-MR"), ("SH-FULL", "SH-MRN"), ("SH-P", "RW")]}
    for name, comps in fams.items():
        tests = {}
        for k in L.LEADS:
            if len(frames[k]):
                for a, b in comps:
                    tests[f"{a}>{b}|{k}"] = L.dm(frames[k], a, b, k)
        hp = L.holm({x: v["p"] for x, v in tests.items()})
        for x in tests:
            tests[x]["holm_p"] = hp.get(x)
        res[f"family_{name}"] = tests
    rep = {}
    for k in (1, 2):
        bl = frames[k][frames[k]["area"] == "BL"]
        for m in L.REPLICATION:
            rep[f"{m}|BL|{k}"] = L.dm(bl, m, "RW", k)
            rep[f"{m}|panel|{k}"] = L.dm(frames[k], m, "RW", k)
    hp = L.holm({x: v["p"] for x, v in rep.items() if "|BL|" in x})
    for x in rep:
        rep[x]["holm_p_BL_family"] = hp.get(x)
    res["replication_agri"] = rep
    res["agri_replicated_out_of_sample"] = any(v["holm_p_BL_family"] is not None and v["holm_p_BL_family"] < 0.10
                                               for x, v in rep.items() if x.startswith("REP-G|BL"))

    # news ablation by area and regime (descriptive)
    abl = {}
    for k in L.LEADS:
        df = frames[k]
        if not len(df):
            continue
        d = L.sloss(df, "SH-MRN") - L.sloss(df, "SH-MR")
        abl[str(k)] = {"by_area": {a: float(d[df["area"] == a].mean()) for a in L.AREAS},
                       "by_regime": {"surge": float(d[df["surge"] == 1].mean()) if (df["surge"] == 1).any() else None,
                                     "falling": float(d[df["falling"] == 1].mean()),
                                     "post_break": float(d[df["post_break"] == 1].mean()),
                                     "pre_break": float(d[df["post_break"] == 0].mean())}}
    res["news_ablation_detail"] = abl

    # zero-filled feature shares (ADDENDUM_1 item 1)
    df1 = frames[1]
    miss = {}
    for c in ["MR"] + [f"{n}@{lag}" for n in L.NEWS for lag in L.LAGS] + L.PSA + ["AGRI-C@0", "AGRI-G@0"]:
        vals = [L.feat(int(t), 1, a)[c] for t, a in zip(df1["t"], df1["area"])]
        miss[c] = float(np.mean([v is None or (isinstance(v, float) and np.isnan(v)) for v in vals]))
    res["zero_filled_share_lead1"] = miss

    # surge alert-skill claims (§6)
    claims = {}
    for k in L.LEADS:
        if not len(frames[k]):
            continue
        for m in L.CANDIDATES:
            s = res["lead"][str(k)]["surge"][m]
            ok = s["events"] >= 10 and (s["precision"] or 0) >= 0.5 and (s["recall"] or 0) >= 0.5
            if ok:
                ok = (L.brier_boot_p(frames[k], m, "clim_psurge") < 0.10 and L.brier_boot_p(frames[k], m, "RW_psurge") < 0.10)
            claims[f"{m}|{k}"] = ok
    res["surge_alert_claims"] = claims

    # selection (§9)
    d1 = dec.get("1", {})
    m1 = {m: res["lead"]["1"]["metrics"][m]["mase"] for m in L.CANDIDATES}
    tier1 = [m for m in L.CANDIDATES if d1.get(m, {}).get("reliable")]
    if tier1:
        adopted, tier = min(tier1, key=lambda m: (m1[m], len(L.SPECS[m]))), 1
    else:
        best = min(L.CANDIDATES, key=lambda m: (m1[m], len(L.SPECS[m])))
        if m1[best] < res["lead"]["1"]["metrics"]["RW"]["mase"] and d1[best]["criteria"]["R4"]:
            adopted, tier = best, 2
        else:
            adopted, tier = "RW", 3
    per_lead = {}
    for k in L.LEADS:
        b = res["lead"].get(str(k), {})
        if not b.get("rows") or adopted == "RW":
            per_lead[str(k)] = "RW"
            continue
        ok = b["metrics"][adopted]["mase"] < b["metrics"]["RW"]["mase"] and dec[str(k)][adopted]["criteria"]["R4"]
        per_lead[str(k)] = adopted if ok else "RW"
    res["selection"] = {"adopted": adopted, "tier": tier, "per_lead_output": per_lead,
                        "status": {1: "beats persistence (development)", 2: "shrinkage forecast; not significantly better "
                                   "than persistence", 3: "persistence (latest published reading)"}[tier]}

    # calibrated-persistence horizon (§8 secondary)
    cal = None
    for k in L.LEADS:
        b = res["lead"].get(str(k), {})
        cov = b.get("metrics", {}).get("RW", {}).get("coverage80")
        if b.get("quarters", 0) >= 8 and cov is not None and 0.70 <= cov <= 0.90:
            cal = k
        else:
            break
    res["calibrated_persistence_horizon"] = cal
    adopted_ml = res["max_reliable_lead"].get(adopted) if adopted != "RW" else None
    res["max_reliable_lead_adopted"] = adopted_ml
    L.write_json(OUT / "results.json", res)
    print("adopted:", adopted, "tier", tier, "| per lead", per_lead, "| max reliable", res["max_reliable_lead"])


# ================================================================================================ phase: analyses
def _spear(x, y):
    from scipy.stats import spearmanr
    m = ~(np.isnan(x) | np.isnan(y))
    if m.sum() < 6:
        return {"n": int(m.sum()), "rho": None, "p": None}
    r = spearmanr(x[m], y[m], alternative="greater")
    return {"n": int(m.sum()), "rho": float(r.statistic), "p": float(r.pvalue)}


def phase_analyses() -> None:
    check()
    out = {}
    # 7.5 CPI validation of price news
    cq = L.cpi_quarterly()
    qs_ = list(range(E.FIRST_ORIGIN, E.LAST_OUTCOME + 1))
    cpi_lvl = np.array([cq.get(q, np.nan) for q in qs_])
    cpi_chg = np.array([cq.get(q, np.nan) - cq.get(q - 4, np.nan) if q in cq.index and q - 4 in cq.index else np.nan for q in qs_])
    tests = {}
    for src in ("C", "G"):
        tab = L.composites(src)
        share = np.array([tab.loc[q, "pri"] if q in tab.index else np.nan for q in qs_])
        yoy = np.array([tab.loc[q, "pri_yoy"] if q in tab.index else np.nan for q in qs_])
        for lag in (-2, -1, 0, 1, 2):                    # news at q+lag vs CPI at q: negative lag = news leads CPI
            def sh(a):
                return np.array([a[i + lag] if 0 <= i + lag < len(a) else np.nan for i in range(len(a))])
            tests[f"{src}|price_share~cpi_food_yoy|lag{lag}"] = _spear(sh(share), cpi_lvl)
            tests[f"{src}|price_yoy~cpi_food_yoy_change|lag{lag}"] = _spear(sh(yoy), cpi_chg)
    hp = L.holm({x: v["p"] for x, v in tests.items()})
    for x in tests:
        tests[x]["holm_p"] = hp.get(x)
    out["cpi_validation"] = {"tests": tests, "price_news_validated": any(
        v["holm_p"] is not None and v["holm_p"] < 0.10 and v["rho"] > 0 and int(x.split("lag")[-1]) <= 0 for x, v in tests.items())}
    # severity: weighted vs plain disaster share against typhoon counts
    X = H9.regional_features(1)
    c2 = np.array([X.loc[q, "C2"] if q in X.index else np.nan for q in qs_])
    tab = L.composites("C")
    out["severity_validation"] = {
        c: _spear(np.array([tab.loc[q, c] if q in tab.index else np.nan for q in qs_]), c2) for c in ("dis_plain", "dis", "severe")}
    # 7.6 inflation regime check
    res = json.loads((OUT / "results.json").read_text())
    adopted = res["selection"]["adopted"]
    hi_cut = float(np.nanpercentile(cpi_lvl, 200 / 3))
    reg = {}
    from scipy.stats import mannwhitneyu
    for k in L.LEADS:
        p = OUT / f"panel_lead{k}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        hi = df["q"].map(lambda q: cq.get(q, np.nan) >= hi_cut)
        r = {"high_rows": int(hi.sum()), "other_rows": int((~hi).sum())}
        for m in sorted({"RW", adopted}):
            e = (df[m] - df["y"]).abs() / df["scale"]
            r[m] = {"mase_high": float(e[hi].mean()) if hi.any() else None, "mase_other": float(e[~hi].mean()),
                    "mw_p": float(mannwhitneyu(e[hi], e[~hi]).pvalue) if hi.sum() >= 3 else None}
        reg[str(k)] = r
    out["inflation_regime"] = {"high_cut_food_yoy": hi_cut, "by_lead": reg}
    # 7.9 spatial consistency check
    from app.ml.inference import firi as FI
    vul = FI.vulnerability()
    sub = pd.read_parquet(E.BACKEND / "data/processed/psa_subsistence.parquet")
    sub = sub[sub["geographic_level"] == "province"]
    code = {v: k for k, v in L.E.NAMES.items()}
    sp = {}
    for yr in (2021, 2023):
        s = sub[sub["year"] == yr].set_index("area_name")
        names = [n for n in s.index if n in code]
        from scipy.stats import spearmanr
        r = spearmanr([vul[code[n]] for n in names], s.loc[names, "subsistence_pct"].astype(float))
        sp[str(yr)] = {"n": len(names), "rho": float(r.statistic), "p_two_sided": float(r.pvalue),
                       "subsistence_cv_range": [float(s.loc[names, "subsistence_cv"].min()), float(s.loc[names, "subsistence_cv"].max())]}
    out["spatial_subsistence_check"] = sp
    # §10.2 shuffle placebo
    out["placebo"] = {"news_SH-MRN": placebo("news"), "psa_SH-MRP": placebo("psa")}
    L.write_json(OUT / "analyses.json", out)
    print(json.dumps({"price_news_validated": out["cpi_validation"]["price_news_validated"], "placebo": out["placebo"]}, indent=1))


def placebo(kind: str, n: int = 200) -> dict:
    model = "SH-MRN" if kind == "news" else "SH-MRP"
    rng = np.random.default_rng(L.SEED)
    L.clear_caches()
    real = L.evaluate(1, ["RW", model], with_band=False)
    real_mase = float(L.sloss(real, model).mean())
    vals = []
    for _ in range(n):
        if kind == "news":
            tab = L.composites("C").copy()
            perm = rng.permutation(len(tab))
            for c in [c for c in tab.columns if c.endswith("_yoy")]:
                tab[c] = tab[c].to_numpy()[perm]
            L._OVERRIDE[("news", "C")] = tab
        else:
            cpi = L.cpi_monthly().copy()
            L._OVERRIDE["cpi"] = pd.Series(rng.permutation(cpi.to_numpy()), index=cpi.index)
            rice = L.rice_table().copy()
            L._OVERRIDE["rice"] = pd.Series(rng.permutation(rice.to_numpy()), index=rice.index)
        L.clear_caches()
        try:
            d = L.evaluate(1, ["RW", model], with_band=False)
            vals.append(float(L.sloss(d, model).mean()))
        finally:
            L._OVERRIDE.clear()
    L.clear_caches()
    vals = np.array(vals)
    return {"real_mase": real_mase, "placebo_mean": float(vals.mean()), "placebo_p05": float(np.percentile(vals, 5)),
            "permutation_p": float((np.sum(vals <= real_mase) + 1) / (len(vals) + 1)), "n": n}


# ================================================================================================ phase: prospective seals (§11)
def phase_prospective() -> None:
    st = check()
    res = json.loads((OUT / "results.json").read_text())
    per_lead = res["selection"]["per_lead_output"]
    t = E.LAST_ORIGIN
    for name, issue in (("A", None), ("B", SEAL_B_ISSUE)):
        rows = []
        for k in L.LEADS:
            for a in L.AREAS:
                for m in L.MODELS:
                    f = L._forecast(m, t, k, a, issue)
                    if f is None:
                        continue
                    b = L.band(m, t, k, issue)
                    rows.append({"seal": name, "issue_date": issue or E.issue(t), "origin": E.qs(t), "area": a, "model": m,
                                 "lead": k, "target_quarter": E.qs(t + k), "h_last": f["h_last"],
                                 "h_last_quarter": E.qs(f["q_last"]), "true_horizon": f["true_horizon"],
                                 "forecast_pct": round(f["forecast"], 4), "pi80_low": round(f["forecast"] - b["half"], 4),
                                 "pi80_high": round(f["forecast"] + b["half"], 4), "band_method": b["method"],
                                 "adopted_output": m == per_lead[str(k)]})
        df = pd.DataFrame(rows)
        p = OUT / f"sealed_prospective_{name}.csv"
        df.to_csv(p, index=False, lineterminator="\n")
        (OUT / f"sealed_prospective_{name}.csv.sha256").write_text(L.sha256(p) + "\n", encoding="utf-8", newline="\n")
        print(name, len(df), L.sha256(p)[:8])
        print(df[df["adopted_output"] & (df["area"] == "BL")][["lead", "target_quarter", "model", "h_last", "true_horizon",
                                                                "forecast_pct", "pi80_low", "pi80_high"]].to_string(index=False))
    L.write_json(OUT / "prospective_record.json", {
        "git": st, "earlier_seals": earlier_seals(),
        "seal_A": {"sha256": L.sha256(OUT / "sealed_prospective_A.csv"), "issue": E.issue(t),
                   "cut": "SWS before 2026-10-01 (newest 2026-Q2); news quarters <= 2026-Q3; CPI months by day-10 rule"},
        "seal_B": {"sha256": L.sha256(OUT / "sealed_prospective_B.csv"), "issue": SEAL_B_ISSUE,
                   "cut": "SWS before 2026-10-25 (newest 2026-Q3); news quarters <= 2026-Q3; CPI months by day-10 rule"},
        "cpi_last_month": {"A": L.cpi_features(E.issue(t))["cpi_last_month"], "B": L.cpi_features(SEAL_B_ISSUE)["cpi_last_month"]}})


# ================================================================================================ phase: export
def phase_export() -> None:
    res = json.loads((OUT / "results.json").read_text())
    pro = json.loads((OUT / "prospective_record.json").read_text())
    serve = E.BACKEND / "data" / "e113"
    serve.mkdir(parents=True, exist_ok=True)
    L.write_json(serve / "evaluation_summary.json", {
        "schema": "aipheed.e113.evaluation/1",
        "outcome": "SWS Total Hunger, 4-area panel (Balance Luzon primary); regional, not provincial",
        "status": "Development evidence; no quarter unseen", "protocol_sha256": res["run"]["protocol_sha256"],
        "selection": res["selection"], "max_reliable_lead": res["max_reliable_lead"],
        "calibrated_persistence_horizon": res["calibrated_persistence_horizon"],
        "panel_mase": {k: {m: round(v["mase"], 4) for m, v in b["metrics"].items()} for k, b in res["lead"].items() if b.get("rows")},
        "coverage80": {k: {m: round(v.get("coverage80", float("nan")), 3) for m, v in b["metrics"].items()}
                       for k, b in res["lead"].items() if b.get("rows")}})
    rows = pd.concat([pd.read_csv(OUT / f"sealed_prospective_{s}.csv") for s in ("A", "B")])
    L.write_json(serve / "forecast.json", {"schema": "aipheed.e113.forecast/1", **pro,
                                            "adopted": rows[rows["adopted_output"]].to_dict("records"),
                                            "all_models": rows.to_dict("records")})
    print("exported")


def phase_all() -> None:
    for p in (phase_news, phase_audit, phase_score, phase_analyses, phase_prospective, phase_export):
        print("==", p.__name__)
        p()


if __name__ == "__main__":
    {"news": phase_news, "audit": phase_audit, "score": phase_score, "analyses": phase_analyses,
     "prospective": phase_prospective, "export": phase_export, "all": phase_all}[sys.argv[1]]()
