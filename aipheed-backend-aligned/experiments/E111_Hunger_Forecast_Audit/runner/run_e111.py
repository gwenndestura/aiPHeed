"""E111 runner (PROTOCOL.md). Phases: score | prospective | export."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

import e111_lib as G

E, F, H9, np, pd = G.E, G.F, G.H9, G.np, G.pd
OUT = G.OUT


def git_state() -> dict:
    def g(*a):
        return subprocess.run(["git", *a], cwd=E.REPO, capture_output=True, text=True).stdout.strip()
    return {"commit": g("rev-parse", "HEAD"), "branch": g("branch", "--show-current"),
            "runner_dirty": bool(g("status", "--porcelain", "--", str(G.HERE))),
            "protocol_sha256": G.sha256(G.E111 / "PROTOCOL.md"), "utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def check() -> dict:
    st = git_state()
    assert st["protocol_sha256"] == (G.HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "PROTOCOL.md changed"
    return st


def panel_block(k: int):
    df = G.evaluate_panel(k)
    if not len(df):
        return {"rows": 0}, df
    bl = df[df["area"] == "BL"]
    out = {"rows": len(df), "quarters": int(df["q"].nunique()), "first": E.qs(int(df["q"].min())), "last": E.qs(int(df["q"].max())),
           "true_horizons": df["true_horizon"].value_counts().sort_index().to_dict(),
           "continuous": {m: F.cont(df, m, k) for m in G.PANEL},
           "continuous_BL": {m: F.cont(bl, m, k) for m in G.PANEL} if len(bl) else {},
           "by_change_class": {m: G.by_class(df, m) for m in G.PANEL},
           "surge": {m: G.surge(df, m) for m in G.PANEL}, "coverage80": {m: G.coverage(df, m) for m in G.PANEL},
           "decision": {m: G.decide(df, m, k, bl) for m in G.NEW + ["LLR", "MA2"]},
           "per_quarter_diff_vs_rw": {m: {E.qs(int(q)): float(v) for q, v in F.quarter_diff(df, m).items()} for m in G.NEW + ["LLR"]}}
    return out, df


def bl_block(k: int, rule: str = "primary"):
    df = G.evaluate_bl(k, rule)
    if not len(df):
        return {"rows": 0}, df
    fams = [f"FAM-{f}" for f in E.FAMILIES]
    out = {"rows": len(df), "first": E.qs(int(df["q"].min())), "last": E.qs(int(df["q"].max())),
           "mae": {m: float(np.abs(df[m] - df["y"]).mean()) for m in ["RW", "LGBM12"] + fams},
           "surge": {m: G.surge(df, m) for m in ["RW", "LGBM12"]}, "coverage80": {m: G.coverage(df, m) for m in ["RW", "LGBM12"]},
           "decision": {"LGBM12": G.decide(df, "LGBM12", k, df)}}
    ps = {f: F._dm_signed(F.quarter_diff(df, f).to_numpy(), k).get("p") for f in fams}
    out["family_screen"] = {"dm_p": ps, "holm_p": G.holm(ps),
                            "mean_diff_vs_rw": {f: float(F.quarter_diff(df, f).mean()) for f in fams}}
    return out, df


def sens_panel(**opts) -> dict:
    G.set_sensitivity(**opts)
    try:
        out = {}
        for k in (1, 2):
            df = G.evaluate_panel(k)
            bl = df[df["area"] == "BL"]
            out[str(k)] = {"quarters": int(df["q"].nunique()), "mae": {m: F.cont(df, m, k)["mae"] for m in G.PANEL},
                           "status": {m: G.decide(df, m, k, bl)["status"] for m in G.NEW}}
        return out
    finally:
        G.set_sensitivity()


def phase_score() -> None:
    st = check()
    OUT.mkdir(exist_ok=True)
    res = {"run": st, "panel": {}, "bl": {}, "bl_sensitivity": {}}
    frames = []
    for k in G.LEADS_PANEL:
        s, df = panel_block(k)
        res["panel"][str(k)] = s
        if len(df):
            frames.append(df)
            df.to_csv(OUT / f"panel_lead{k}.csv", index=False, lineterminator="\n", float_format="%.10g")
        print(f"panel lead {k}: {s.get('rows', 0)} rows / {s.get('quarters', 0)} quarters")
    res["by_true_horizon"] = G.by_true_horizon(frames, G.PANEL)
    for k in G.LEADS_BL:
        s, df = bl_block(k)
        res["bl"][str(k)] = s
        if len(df):
            df.to_csv(OUT / f"bl_lead{k}.csv", index=False, lineterminator="\n", float_format="%.10g")
        print(f"BL lead {k}: {s.get('rows', 0)} quarters")
    for rule in ("ALL", "HH"):
        res["bl_sensitivity"][rule] = {str(k): bl_block(k, rule)[0] for k in (1, 2)}
    res["sensitivity"] = {"S-NOINF": sens_panel(noinf=True), "S-VOTERS": sens_panel(voters=True)}
    status = {m: {k: v["decision"][m]["status"] for k, v in res["panel"].items() if v.get("decision")} for m in G.NEW + ["LLR"]}
    status["LGBM12"] = {k: v["decision"]["LGBM12"]["status"] for k, v in res["bl"].items() if v.get("decision")}
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
    sig = {}
    for k in ("1", "2"):
        b = res["bl"].get(k, {})
        hp = b.get("family_screen", {}).get("holm_p", {})
        for f, p in hp.items():
            if p < 0.10:
                surv = all(res["bl_sensitivity"][r].get(k, {}).get("family_screen", {}).get("mean_diff_vs_rw", {}).get(f, 1) < 0
                           for r in ("ALL", "HH") if res["bl_sensitivity"][r].get(k, {}).get("rows", 0) >= 8)
                sig.setdefault(f, []).append({"lead": int(k), "holm_p": p, "survives_sensitivity": surv})
    res["families_adding_value"] = sig
    rec = "RW (latest published SWS reading)"
    for m in ("ASYM", "DT", "BRK", "LGBM12"):
        if status[m].get("1") == "provisional":
            rec = m
            break
    res["recommended_operational_forecast"] = rec
    G.write_json(OUT / "results.json", res)


def phase_prospective() -> None:
    st = check()
    t = E.LAST_ORIGIN
    rows = []
    for a in F.AREAS:
        for k in G.LEADS_PANEL:
            for m in G.PANEL:
                f = G.forecast(m, t, k, a)
                if f is None:
                    continue
                s = G.sigma(m, t, k, a)
                rows.append({"area": a, "method": m, "lead": k, "true_horizon": f["true_horizon"], "origin": E.qs(t),
                             "issue_date": E.issue(t), "target_quarter": E.qs(t + k), "h_last": f["h_last"],
                             "forecast_pct": round(f["forecast"], 4), "pi80_low": round(f["forecast"] - 1.2816 * s, 4),
                             "pi80_high": round(f["forecast"] + 1.2816 * s, 4)})
    for k in G.LEADS_BL:
        f = H9.forecast("LGBM", t, k)
        if f is not None:
            s = H9.sigma("LGBM", t, k)
            rows.append({"area": "BL", "method": "LGBM12", "lead": k, "true_horizon": t + k - E.qi(f["h_last_quarter"]),
                         "origin": E.qs(t), "issue_date": E.issue(t), "target_quarter": E.qs(t + k), "h_last": f["h_last"],
                         "forecast_pct": round(f["forecast"], 4), "pi80_low": round(f["forecast"] - 1.2816 * s, 4),
                         "pi80_high": round(f["forecast"] + 1.2816 * s, 4)})
    df = pd.DataFrame(rows)
    p = OUT / "sealed_prospective.csv"
    df.to_csv(p, index=False, lineterminator="\n")
    (OUT / "sealed_prospective.csv.sha256").write_text(G.sha256(p) + "\n", encoding="utf-8", newline="\n")
    ex = G.E111.parent
    G.write_json(OUT / "prospective_record.json", {
        "git": st, "sealed_sha256": G.sha256(p), "origin": E.qs(t), "issue_date": E.issue(t),
        "data_cutoff": "SWS rounds published before 2026-10-01; newest = 2026-Q2 (true horizon of Lead 1 = 2 quarters)",
        "earlier_seals": {e: G.sha256(ex / e / "out/sealed_prospective.csv") for e in
                          ("E107_Twelve_Indicator_LightGBM", "E108_Best_Defensible_Forecasting", "E109_Hunger_Forecasting",
                           "E110_Hunger_Generalization")}})
    print(df[(df["area"] == "BL") & (df["lead"] <= 2)].to_string())


def phase_export() -> None:
    res = json.loads((OUT / "results.json").read_text())
    pro = json.loads((OUT / "prospective_record.json").read_text())
    serve = E.BACKEND / "data" / "e111"
    serve.mkdir(parents=True, exist_ok=True)
    G.write_json(serve / "evaluation_summary.json", {
        "schema": "aipheed.e111.evaluation/1",
        "outcome": "SWS Total Hunger (Balance Luzon primary; 4-area panel); regional, not provincial",
        "status": "Development evidence; no quarter unseen", "protocol_sha256": res["run"]["protocol_sha256"],
        "status_by_lead": res["status"], "max_reliable_lead": res["max_reliable_lead"],
        "max_provisional_lead": res["max_provisional_lead"],
        "recommended_operational_forecast": res["recommended_operational_forecast"],
        "families_adding_value": res["families_adding_value"],
        "panel_mae": {k: {m: round(v["mae"], 3) for m, v in s["continuous"].items()} for k, s in res["panel"].items() if s.get("continuous")}})
    rows = pd.read_csv(OUT / "sealed_prospective.csv")
    G.write_json(serve / "forecast.json", {"schema": "aipheed.e111.forecast/1", **pro, "forecasts": rows.to_dict("records")})
    print("exported")


if __name__ == "__main__":
    {"score": phase_score, "prospective": phase_prospective, "export": phase_export}[sys.argv[1]]()
