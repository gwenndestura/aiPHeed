"""E112 runner (PROTOCOL.md). Phases: score | prospective | export."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

import e112_lib as L

E, F, G, H9, np, pd = L.E, L.F, L.G, L.H9, L.np, L.pd
OUT = L.OUT
EARLIER = ("E107_Twelve_Indicator_LightGBM", "E108_Best_Defensible_Forecasting", "E109_Hunger_Forecasting",
           "E110_Hunger_Generalization", "E111_Hunger_Forecast_Audit")


def git_state() -> dict:
    def g(*a):
        return subprocess.run(["git", *a], cwd=E.REPO, capture_output=True, text=True).stdout.strip()
    return {"commit": g("rev-parse", "HEAD"), "branch": g("branch", "--show-current"),
            "protocol_sha256": L.sha256(L.E112 / "PROTOCOL.md"), "utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def check() -> dict:
    st = git_state()
    assert st["protocol_sha256"] == (L.HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "PROTOCOL.md changed"
    return st


def check_addendum() -> None:
    assert L.sha256(L.E112 / "ADDENDUM_1.md") == (L.HERE / "ADDENDUM_1_SHA256.txt").read_text().strip(), "ADDENDUM_1 changed"


def earlier_seals() -> dict:
    out = {}
    for e in EARLIER:
        p = L.E112.parent / e / "out" / "sealed_prospective.csv"
        want = (p.parent / "sealed_prospective.csv.sha256").read_text().strip()
        out[e] = {"sha256": L.sha256(p), "unchanged": L.sha256(p) == want}
    return out


def bl_block(k: int):
    df = L.evaluate_bl(k)
    methods = L.BASELINES + L.CANDIDATES
    out = {"rows": len(df), "first": E.qs(int(df["q"].min())), "last": E.qs(int(df["q"].max())),
           "true_horizons": {str(a): int(b) for a, b in df["true_horizon"].value_counts().sort_index().items()},
           "continuous": {m: F.cont(df, m, k) for m in methods},
           "by_change_class": {m: G.by_class(df, m) for m in methods},
           "surge": {m: G.surge(df, m) for m in methods}, "coverage80": {m: G.coverage(df, m) for m in methods},
           "warnings": {m: L.warnings_(df, m) for m in methods},
           "decision": {m: G.decide(df, m, k, df) for m in methods if m != "RW"},
           "per_quarter_diff_vs_rw": {m: {E.qs(int(q)): float(v) for q, v in F.quarter_diff(df, m).items()} for m in L.CANDIDATES},
           "N1": {m: L.dm(df, m, "RW", k) for m in ("NEWS-C", "NEWS-G")},
           "N2": L.dm(df, "LGBM12N", "LGBM12", k),
           "news_shap_share_mean": float(df["LGBM12N_news_shap_share"].mean()),
           "missing_share": L.missing_shares(k, sorted(df["t"].unique()))}
    return out, df


def contribution(k: int, rule: str = "primary", removals=None) -> dict:
    removals = L.REMOVALS if removals is None else removals
    df = L.evaluate_bl(k, rule, ["RW", "LGBM12N"] + [f"LGBM12N-{r}" for r in removals], with_sigma=False)
    res = {r: L.dm(df, "LGBM12N", f"LGBM12N-{r}", k) for r in removals}
    hp = G.holm({r: v["p"] for r, v in res.items()})
    for r in res:
        res[r]["holm_p"] = hp.get(r)
        res[r]["mae_without"] = float(np.abs(df[f"LGBM12N-{r}"] - df["y"]).mean())
    return {"rows": len(df), "mae_LGBM12N": float(np.abs(df["LGBM12N"] - df["y"]).mean()), "removals": res}


def rule_block(k: int, rule: str) -> dict:
    methods = L.BASELINES + L.CANDIDATES
    df = L.evaluate_bl(k, rule, methods, with_sigma=False)
    if not len(df):
        return {"rows": 0}
    return {"rows": len(df), "mae": {m: float(np.abs(df[m] - df["y"]).mean()) for m in methods},
            "mean_quarter_diff_vs_rw": {m: float(F.quarter_diff(df, m).mean()) for m in L.CANDIDATES},
            "LGBM12N_minus_LGBM12": float(F.quarter_diff(df, "LGBM12N", "LGBM12").mean())}


def panel_block(k: int):
    df = L.evaluate_panel(k)
    if not len(df):
        return {"rows": 0}, df
    bl = df[df["area"] == "BL"]
    ms = ["RW", "LLR", "ASYM", "NEWS-CP"]
    return {"rows": len(df), "quarters": int(df["q"].nunique()),
            "continuous": {m: F.cont(df, m, k) for m in ms}, "continuous_BL": {m: F.cont(bl, m, k) for m in ms},
            "by_change_class": {m: G.by_class(df, m) for m in ms}, "surge": {m: G.surge(df, m) for m in ms},
            "warnings": {m: L.warnings_(df, m) for m in ms}, "decision": {"NEWS-CP": G.decide(df, "NEWS-CP", k, bl)},
            "N1_panel": L.dm(df, "NEWS-CP", "RW", k)}, df


def phase_score() -> None:
    st = check()
    res = {"run": st, "earlier_seals": earlier_seals(), "validity": L.validity(), "advance": L.advance(), "bl": {}, "panel": {}}
    frames = []
    for k in L.LEADS:
        s, df = bl_block(k)
        res["bl"][str(k)] = s
        frames.append(df)
        df.to_csv(OUT / f"bl_lead{k}.csv", index=False, lineterminator="\n", float_format="%.10g")
        p, dfp = panel_block(k)
        res["panel"][str(k)] = p
        if len(dfp):
            dfp.to_csv(OUT / f"panel_lead{k}.csv", index=False, lineterminator="\n", float_format="%.10g")
        print(f"lead {k}: BL {s['rows']} quarters, panel {p.get('rows', 0)} rows")
    res["by_true_horizon"] = G.by_true_horizon(frames, L.BASELINES + L.CANDIDATES)

    # news tests (section 4.3)
    n1 = {f"{m}|{k}": res["bl"][str(k)]["N1"][m]["p"] for k in L.LEADS for m in ("NEWS-C", "NEWS-G")}
    n2 = {str(k): res["bl"][str(k)]["N2"]["p"] for k in L.LEADS}
    res["N1_holm"], res["N2_holm"] = G.holm(n1), G.holm(n2)
    res["N3"] = {str(k): contribution(k) for k in L.CONTRIB_LEADS}
    res["news_adds_measurable_value"] = any(v < 0.10 for v in list(res["N1_holm"].values()) + list(res["N2_holm"].values()))

    # survey-change sensitivity and family value (section 4.3 / 4.5)
    res["rule_sensitivity"] = {r: {str(k): rule_block(k, r) for k in L.CONTRIB_LEADS} for r in ("ALL", "HH")}
    fam = {}
    for k in L.CONTRIB_LEADS:
        for r, v in res["N3"][str(k)]["removals"].items():
            if v["holm_p"] is not None and v["holm_p"] < 0.10:
                keeps = all(contribution(k, rule, [r])["removals"][r]["mean_diff"] < 0 for rule in ("ALL", "HH"))
                fam.setdefault(r, []).append({"lead": k, "holm_p": v["holm_p"], "keeps_sign_ALL_HH": keeps})
    res["components_adding_value"] = fam

    # status, maximum provisional lead, final method (section 5)
    status = {m: {str(k): res["bl"][str(k)]["decision"][m]["status"] for k in L.LEADS} for m in L.CANDIDATES + ["MA2", "LL"]}
    status["NEWS-CP"] = {str(k): res["panel"][str(k)]["decision"]["NEWS-CP"]["status"] for k in L.LEADS
                         if res["panel"][str(k)].get("decision")}
    res["status"] = status

    def maxlead(m):
        best = None
        for k in L.LEADS:
            if status[m].get(str(k)) == "provisional":
                best = k
            else:
                break
        return best
    res["max_provisional_lead"] = {m: maxlead(m) for m in status}
    res["max_reliable_lead"] = None
    res["final_method"] = next((m for m in L.ORDER if status[m].get("1") == "provisional"), "RW")
    G.write_json(OUT / "results.json", res)
    print("final method:", res["final_method"], "| news adds value:", res["news_adds_measurable_value"])


def phase_obj4() -> None:
    """ADDENDUM_1: PSA-only and linear-regression baselines (comparison only; not in the final-method order)."""
    st = check()
    check_addendum()
    out = {"run": st, "addendum_sha256": L.sha256(L.E112 / "ADDENDUM_1.md"), "lead": {}}
    for k in L.LEADS:
        df = L.evaluate_bl(k, methods=["RW"] + L.OBJ4 + ["NEWS-C", "LGBM12", "LGBM12N"], with_sigma=False)
        out["lead"][str(k)] = {"rows": len(df), "mae": {m: float(np.abs(df[m] - df["y"]).mean()) for m in
                                                         ["RW"] + L.OBJ4 + ["NEWS-C", "LGBM12", "LGBM12N"]},
                               "vs_rw": {m: L.dm(df, m, "RW", k) for m in L.OBJ4},
                               "lgbm_vs": {f"{a}>{b}": L.dm(df, a, b, k) for a in ("LGBM12", "LGBM12N") for b in L.OBJ4}}
    for key in ["vs_rw|" + m for m in L.OBJ4] + ["lgbm_vs|" + f"{a}>{b}" for a in ("LGBM12", "LGBM12N") for b in L.OBJ4]:
        blk, name = key.split("|")
        hp = G.holm({k: out["lead"][k][blk][name]["p"] for k in out["lead"]})
        for k in out["lead"]:
            out["lead"][k][blk][name]["holm_p"] = hp.get(k)
    G.write_json(OUT / "objective4_baselines.json", out)
    for k, v in out["lead"].items():
        print(k, v["rows"], {m: round(x, 2) for m, x in v["mae"].items()})


def phase_prospective() -> None:
    st = check()
    t = E.LAST_ORIGIN
    rows = []
    for k in L.LEADS:
        for m in L.BASELINES + L.CANDIDATES:
            f = L.forecast(m, t, k)
            if f is None:
                continue
            s = L.sigma(m, t, k)
            rows.append({"area": "BL", "method": m, "lead": k, "true_horizon": t + k - E.qi(f["h_last_quarter"]),
                         "origin": E.qs(t), "issue_date": E.issue(t), "target_quarter": E.qs(t + k), "h_last": f["h_last"],
                         "forecast_pct": round(f["forecast"], 4), "pi80_low": round(f["forecast"] - 1.2816 * s, 4),
                         "pi80_high": round(f["forecast"] + 1.2816 * s, 4)})
        for a in F.AREAS:
            f, b = L.forecast_cp(t, k, a), G.forecast("RW", t, k, a)
            if f is None:
                continue
            s = L.sigma_cp(t, k, a)
            rows.append({"area": a, "method": "NEWS-CP", "lead": k, "true_horizon": b["true_horizon"], "origin": E.qs(t),
                         "issue_date": E.issue(t), "target_quarter": E.qs(t + k), "h_last": b["h_last"],
                         "forecast_pct": round(f, 4), "pi80_low": round(f - 1.2816 * s, 4), "pi80_high": round(f + 1.2816 * s, 4)})
    df = pd.DataFrame(rows)
    p = OUT / "sealed_prospective.csv"
    df.to_csv(p, index=False, lineterminator="\n")
    (OUT / "sealed_prospective.csv.sha256").write_text(L.sha256(p) + "\n", encoding="utf-8", newline="\n")
    G.write_json(OUT / "prospective_record.json", {
        "git": st, "sealed_sha256": L.sha256(p), "origin": E.qs(t), "issue_date": E.issue(t),
        "data_cutoff": "SWS rounds published before 2026-10-01 (newest 2026-Q2); news headlines published before "
                       "2026-10-01 (newest complete quarter 2026-Q3)",
        "news_used": L.news_at(t, "C"), "earlier_seals": earlier_seals()})
    print(df[(df["area"] == "BL") & (df["lead"] <= 2)].to_string())


def phase_export() -> None:
    res = json.loads((OUT / "results.json").read_text())
    pro = json.loads((OUT / "prospective_record.json").read_text())
    serve = E.BACKEND / "data" / "e112"
    serve.mkdir(parents=True, exist_ok=True)
    G.write_json(serve / "evaluation_summary.json", {
        "schema": "aipheed.e112.evaluation/1",
        "outcome": "SWS Total Hunger (Balance Luzon primary; 4-area panel for the news ridge); regional, not provincial",
        "status": "Development evidence; no quarter unseen", "protocol_sha256": res["run"]["protocol_sha256"],
        "final_method": res["final_method"], "status_by_lead": res["status"],
        "max_provisional_lead": res["max_provisional_lead"], "max_reliable_lead": res["max_reliable_lead"],
        "news_adds_measurable_value": res["news_adds_measurable_value"],
        "news_tests": {"N1_holm": res["N1_holm"], "N2_holm": res["N2_holm"],
                       "advance_warning": {s: v["advance_warning"] for s, v in res["advance"].items()},
                       "validity": {s: v["valid"] for s, v in res["validity"].items()}},
        "components_adding_value": res["components_adding_value"],
        "bl_mae": {k: {m: round(v["mae"], 3) for m, v in s["continuous"].items()} for k, s in res["bl"].items()},
        "objective4_baselines_mae": {k: {m: round(x, 3) for m, x in v["mae"].items()} for k, v in
                                     json.loads((OUT / "objective4_baselines.json").read_text())["lead"].items()}})
    G.write_json(serve / "forecast.json", {"schema": "aipheed.e112.forecast/1", **pro,
                                            "forecasts": pd.read_csv(OUT / "sealed_prospective.csv").to_dict("records")})
    nq = pd.read_csv(OUT / "news_quarterly_corpus.csv")
    G.write_json(serve / "news_indicators.json", {
        "schema": "aipheed.e112.news/1", "source": "project RSS corpus, de-duplicated, title lexicon (6 categories)",
        "rows": nq.replace({np.nan: None}).to_dict("records")})
    print("exported")


if __name__ == "__main__":
    {"score": phase_score, "obj4": phase_obj4, "prospective": phase_prospective, "export": phase_export}[sys.argv[1]]()
