"""E110 runner (PROTOCOL.md). Phases:

    python run_e110.py score        panel Leads 1-6 and BL Leads 1-4, decisions, binary readings, diagnostics, sensitivities
    python run_e110.py prospective  sealed forecasts from origin 2026-Q3 (issue 2026-10-01)
    python run_e110.py export       read-only API files in backend/data/e110/
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

import e110_lib as F

E, H9, np, pd = F.E, F.H9, F.np, F.pd
OUT = F.OUT


def git_state() -> dict:
    def g(*a):
        return subprocess.run(["git", *a], cwd=E.REPO, capture_output=True, text=True).stdout.strip()
    return {"commit": g("rev-parse", "HEAD"), "branch": g("branch", "--show-current"),
            "runner_dirty": bool(g("status", "--porcelain", "--", str(F.HERE))),
            "protocol_sha256": F.sha256(F.E110 / "PROTOCOL.md"), "utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def check() -> dict:
    st = git_state()
    assert st["protocol_sha256"] == (F.HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "PROTOCOL.md changed"
    for line in filter(None, (F.HERE / "INPUT_SHA256SUMS.txt").read_text().split("\n")):
        h, name = line.split(" *")
        assert F.sha256(F.E110 / name) == h, name
    return st


def bin_block(df: pd.DataFrame, methods) -> dict:
    out = {}
    for b in ("B3", "B4"):
        out[b] = {m: F.binary(df, m, b) for m in list(methods) + ["PERSIST", "CLIM"]}
    return out


def bin_rule(df: pd.DataFrame, m: str, b: str) -> dict:
    mm, pe, cl = F.binary(df, m, b), F.binary(df, "PERSIST", b), F.binary(df, "CLIM", b)
    hq = df.loc[df[f"y{b}"] == 1, "q"].nunique()
    lq = df.loc[df[f"y{b}"] == 0, "q"].nunique()
    both = hq >= 2 and lq >= 2
    c = {"quarters>=8": df["q"].nunique() >= 8, "both_classes>=2q": both, "acc>=0.75": (mm["accuracy"] or 0) >= 0.75,
         "bal>=0.65": (mm["balanced_accuracy"] or 0) >= 0.65,
         "recalls>=0.5": bool(both and (mm["recall_high"] or 0) >= 0.5 and (mm["recall_low"] or 0) >= 0.5),
         "brier<persist&clim": mm["brier"] < pe["brier"] and mm["brier"] < cl["brier"]}
    st = ("insufficient evidence" if not (c["quarters>=8"] and both) else
          "provisional" if all(c.values()) else "not reliable")
    return {"status": st, "failed": [x for x, v in c.items() if not v], "metrics": mm}


def per_area(df: pd.DataFrame, methods) -> dict:
    return {a: {m: float(np.abs(g[m] - g["y"]).mean()) for m in methods} | {"rows": len(g)}
            for a, g in df.groupby("area")}


def lead_panel(k: int) -> tuple[dict, pd.DataFrame]:
    df = F.evaluate(k, F.PANEL_METHODS)
    if not len(df):
        return {"rows": 0}, df
    bl = df[df["area"] == "BL"]
    out = {"rows": len(df), "quarters": int(df["q"].nunique()), "first": E.qs(int(df["q"].min())),
           "last": E.qs(int(df["q"].max())), "continuous": {m: F.cont(df, m, k) for m in F.PANEL_METHODS},
           "continuous_BL": {m: F.cont(bl, m, k) for m in F.PANEL_METHODS} if len(bl) else {},
           "per_area_mae": per_area(df, F.PANEL_METHODS),
           "decision": {m: F.decide(df, m, k, bl) for m in ["LLR", "COMB", "NAT-R", "MA2", "MEAN"]},
           "binary": bin_block(df, F.PANEL_METHODS),
           "binary_rule": {b: {m: bin_rule(df, m, b) for m in ["LLR", "COMB", "NAT-R", "RW"]} for b in ("B3", "B4")},
           "per_quarter_diff_vs_rw": {m: {E.qs(int(q)): float(v) for q, v in F.quarter_diff(df, m).items()}
                                      for m in ["LLR", "COMB", "NAT-R", "MA2"]}}
    return out, df


def lead_bl(k: int) -> tuple[dict, pd.DataFrame]:
    df = F.evaluate(k, F.BL_METHODS, ("BL",))
    if not len(df):
        return {"rows": 0}, df
    out = {"rows": len(df), "quarters": int(df["q"].nunique()), "first": E.qs(int(df["q"].min())),
           "last": E.qs(int(df["q"].max())), "continuous": {m: F.cont(df, m, k) for m in F.BL_METHODS},
           "decision": {m: F.decide(df, m, k, df) for m in ["LGBM-R", "RIDGE-R", "LLR", "COMB", "NAT-R"]},
           "per_quarter": df[["quarter", "origin", "y", "h_last"] + F.BL_METHODS].round(3).to_dict("records")}
    return out, df


def family_ablation(k: int, df: pd.DataFrame) -> dict:
    """LGBM-R and RIDGE-R without one family at a time (BL, diagnostic): MAE on the same quarters."""
    res = {}
    for name in ("LGBM-R", "RIDGE-R"):
        res[name] = {"full": float(np.abs(df[name] - df["y"]).mean())}
        for fam in E.FAMILIES:
            cols = [c for c in E.COLUMNS if E.FAMILY_OF[c] != fam]
            errs = []
            for t, y in zip(df["t"], df["y"]):
                tr = F.residual_pairs(int(t), k, ("BL",))
                x = H9.regional_features(k).loc[int(t)]
                base = F.forecast("LLR", int(t), k, "BL")["forecast"]
                if name == "RIDGE-R":
                    d = F._ridge(tr, cols, x)
                else:
                    n = F._lgbm_trees(tr, k)
                    d = float(F._lgbm(n).fit(tr[cols].astype(float), tr["res"].to_numpy()).predict(
                        pd.DataFrame([x[cols].astype(float)]))[0])
                errs.append(abs(base + d - y))
            res[name][f"-{fam}"] = float(np.mean(errs))
    return res


def shap_shares(k: int, df: pd.DataFrame) -> dict:
    fam = {f: [] for f in E.FAMILIES}
    used = set()
    for t in df["t"]:
        f = F.forecast("LGBM-R", int(t), k, "BL")
        for c in E.COLUMNS:
            fam[E.FAMILY_OF[c]].append(abs(f["shap"][c]))
            if f["gain"][c] > 0:
                used.add(E.FAMILY_OF[c])
    tot = {f: float(np.sum(v)) for f, v in fam.items()}
    s = sum(tot.values()) or 1.0
    return {"share": {f: v / s for f, v in tot.items()}, "never_used": [f for f in E.FAMILIES if f not in used]}


def design_check() -> dict:
    """LLR Lead-1 residuals by round design (1,500 vs 1,200 surveys) for 2025-26 targets, all areas (descriptive)."""
    df = F.evaluate(1, ["RW", "LLR"])
    a = pd.read_csv(F.AREA_FILE)
    big = {E.qi(q) for q, n in zip(a["quarter"], a["bl_n"]) if n == 600 and q >= "2025-Q2"}
    small = {E.qi(q) for q, n in zip(a["quarter"], a["bl_n"]) if n == 300 and q >= "2025-Q2"}
    d = df[df["q"] >= E.qi("2025-Q2")].assign(res=lambda x: x["y"] - x["LLR"])
    only_big = {q for q in big if q not in small}
    only_small = {q for q in small if q not in big}
    return {"quarters_1500_design": sorted(E.qs(q) for q in only_big), "quarters_1200_design": sorted(E.qs(q) for q in only_small),
            "mean_residual_1500": {ar: float(g.loc[g["q"].isin(only_big), "res"].mean()) for ar, g in d.groupby("area")},
            "mean_residual_1200": {ar: float(g.loc[g["q"].isin(only_small), "res"].mean()) for ar, g in d.groupby("area")},
            "note": "1,500-sample rounds fall in March/September and 1,200 in June/November: design and season are confounded"}


def sensitivity(name: str, **opts) -> dict:
    F.set_options(**opts)
    try:
        out = {}
        for k in (1, 2):
            df = F.evaluate(k, F.PANEL_METHODS)
            bl = df[df["area"] == "BL"]
            out[str(k)] = {"panel_mae": {m: F.cont(df, m, k)["mae"] for m in F.PANEL_METHODS},
                           "bl_mae": {m: F.cont(bl, m, k)["mae"] for m in F.PANEL_METHODS} if len(bl) else {},
                           "LLR": F.decide(df, "LLR", k, bl)["status"], "COMB": F.decide(df, "COMB", k, bl)["status"]}
        return out
    finally:
        F.set_options()


def phase_score() -> None:
    st = check()
    OUT.mkdir(exist_ok=True)
    res = {"run": st, "panel": {}, "bl": {}, "ablation": {}, "shap": {}}
    for k in F.PANEL_LEADS:
        s, df = lead_panel(k)
        res["panel"][str(k)] = s
        if len(df):
            df.to_csv(OUT / f"panel_lead{k}.csv", index=False, lineterminator="\n", float_format="%.10g")
        print(f"panel lead {k}: {s.get('rows', 0)} rows / {s.get('quarters', 0)} quarters")
    for k in F.BL_LEADS:
        s, df = lead_bl(k)
        res["bl"][str(k)] = s
        if len(df):
            df.to_csv(OUT / f"bl_lead{k}.csv", index=False, lineterminator="\n", float_format="%.10g")
            if k <= 2:
                res["ablation"][str(k)] = family_ablation(k, df)
            res["shap"][str(k)] = shap_shares(k, df)
        print(f"BL lead {k}: {s.get('rows', 0)} quarters")
    res["design_check"] = design_check()
    res["sensitivity"] = {"S-VOTERS": sensitivity("S-VOTERS", voters=True), "S-R4": sensitivity("S-R4", const_r=4.0)}
    status = {}
    for m in ("LLR", "COMB", "NAT-R"):
        status[m] = {k: res["panel"][k]["decision"][m]["status"] for k in res["panel"] if res["panel"][k].get("decision")}
    for m in ("LGBM-R", "RIDGE-R"):
        status[m] = {k: res["bl"][k]["decision"][m]["status"] for k in res["bl"] if res["bl"][k].get("decision")}
    res["status"] = status

    def maxlead(m, ok):
        best = None
        for k in sorted(status[m], key=int):
            if status[m][k] in ok:
                best = int(k)
            else:
                break
        return best
    res["max_reliable_lead"] = {m: maxlead(m, ("reliable",)) for m in status}
    res["max_provisional_lead"] = {m: maxlead(m, ("reliable", "provisional")) for m in status}
    rec = "RW (latest published SWS reading)"
    for m in ("COMB", "LLR", "NAT-R", "RIDGE-R", "LGBM-R"):
        if status[m].get("1") == "provisional":
            rec = m
            break
    res["recommended_operational_forecast"] = rec
    F.write_json(OUT / "results.json", res)


def phase_prospective() -> None:
    st = check()
    t = E.LAST_ORIGIN
    rows = []
    for a in F.AREAS:
        for k in F.PANEL_LEADS:
            for m in F.BL_METHODS:
                if m in ("LGBM-R", "RIDGE-R") and (a != "BL" or k > 4):
                    continue
                f = F.forecast(m, t, k, a)
                if f is None:
                    continue
                s = F.sigma(m, t, k, a)
                rows.append({"area": a, "method": m, "lead": k, "origin": E.qs(t), "issue_date": E.issue(t),
                             "target_quarter": E.qs(t + k), "h_last": f["h_last"], "h_last_quarter": f["h_last_quarter"],
                             "forecast_pct": round(f["forecast"], 4), "pi80_low": round(f["forecast"] - 1.2816 * s, 4),
                             "pi80_high": round(f["forecast"] + 1.2816 * s, 4), "p_B3_gt_20": round(F.p_above(f["forecast"], 20.0, s), 4)})
    df = pd.DataFrame(rows)
    p = OUT / "sealed_prospective.csv"
    df.to_csv(p, index=False, lineterminator="\n")
    (OUT / "sealed_prospective.csv.sha256").write_text(F.sha256(p) + "\n", encoding="utf-8", newline="\n")
    ex = F.E110.parent
    F.write_json(OUT / "prospective_record.json", {
        "git": st, "sealed_sha256": F.sha256(p), "origin": E.qs(t), "issue_date": E.issue(t),
        "data_cutoff": "rounds published before 2026-10-01 (the September 2026 round, published 2026-10-14, is not used)",
        "source_hashes": {n: F.sha256(F.E110 / "data" / n) for n in ("sws_area_rounds.csv", "sws_area_rounds_excluded.csv")},
        "earlier_seals": {e: F.sha256(ex / e / "out/sealed_prospective.csv") for e in
                          ("E107_Twelve_Indicator_LightGBM", "E108_Best_Defensible_Forecasting", "E109_Hunger_Forecasting")}})
    print(df[(df["area"] == "BL") & (df["lead"] <= 2)][["method", "lead", "target_quarter", "forecast_pct", "pi80_low", "pi80_high"]].to_string())


def phase_export() -> None:
    res = json.loads((OUT / "results.json").read_text())
    pro = json.loads((OUT / "prospective_record.json").read_text())
    serve = E.BACKEND / "data" / "e110"
    serve.mkdir(parents=True, exist_ok=True)
    F.write_json(serve / "evaluation_summary.json", {
        "schema": "aipheed.e110.evaluation/1",
        "outcome": "SWS Total Hunger (% of families with involuntary hunger in the past three months); Balance Luzon primary, "
                   "4-area panel for generalization; regional, not provincial",
        "status": "Development evidence: every evaluated quarter was seen before the protocol was frozen",
        "protocol_sha256": res["run"]["protocol_sha256"], "status_by_lead": res["status"],
        "max_reliable_lead": res["max_reliable_lead"], "max_provisional_lead": res["max_provisional_lead"],
        "recommended_operational_forecast": res["recommended_operational_forecast"],
        "panel_mae": {k: {m: round(v["mae"], 3) for m, v in s["continuous"].items()} for k, s in res["panel"].items() if s.get("continuous")},
        "bl_mae": {k: {m: round(v["mae"], 3) for m, v in s["continuous"].items()} for k, s in res["bl"].items() if s.get("continuous")}})
    rows = pd.read_csv(OUT / "sealed_prospective.csv")
    F.write_json(serve / "forecast.json", {"schema": "aipheed.e110.forecast/1", **pro,
                                           "note": "Regional SWS hunger forecasts; not validated; not provincial.",
                                           "forecasts": rows.to_dict("records")})
    print("exported")


if __name__ == "__main__":
    {"score": phase_score, "prospective": phase_prospective, "export": phase_export}[sys.argv[1]]()
