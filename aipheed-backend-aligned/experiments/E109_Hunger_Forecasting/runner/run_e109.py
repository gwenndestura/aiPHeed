"""E109 runner (PROTOCOL.md). Phases:

    python run_e109.py score        every method at Leads 1-4 (primary series), decisions, sensitivities, diagnostics
    python run_e109.py prospective  sealed Lead 1-4 forecasts from origin 2026-Q3 (issue 2026-10-01)
    python run_e109.py export       read-only API files in backend/data/e109/ (evaluation, forecast, LGU status)
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

import e109_lib as H

E, np, pd = H.E, H.np, H.pd
OUT = H.OUT


def git_state() -> dict:
    def g(*a):
        return subprocess.run(["git", *a], cwd=E.REPO, capture_output=True, text=True).stdout.strip()
    return {"commit": g("rev-parse", "HEAD"), "branch": g("branch", "--show-current"),
            "runner_dirty": bool(g("status", "--porcelain", "--", str(H.HERE))),
            "protocol_sha256": H.sha256(H.E109 / "PROTOCOL.md"),
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def check() -> dict:
    st = git_state()
    assert st["protocol_sha256"] == (H.HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "PROTOCOL.md changed"
    assert H.sha256(H.E109 / "ADDENDUM_1.md") == (H.HERE / "ADDENDUM_1_SHA256.txt").read_text().strip(), "ADDENDUM_1 changed"
    for line in filter(None, (H.HERE / "INPUT_SHA256SUMS.txt").read_text().split("\n")):
        h, name = line.split(" *")
        assert H.sha256((H.E109 / name).resolve()) == h, name
    return st


def lead_block(df: pd.DataFrame, k: int) -> dict:
    out = {"quarters": list(df["quarter"]), "n_quarters": len(df), "continuous": {}, "decision": {}, "binary": {},
           "binary_decision": {}, "per_quarter": df[["quarter", "origin", "y", "h_last"] + H.METHODS].round(3).to_dict("records")}
    for m in H.METHODS:
        out["continuous"][m] = H.cont_metrics(df, m, k)
        out["continuous"][m]["last4_mae"] = float(np.abs(df[m].iloc[-4:] - df["y"].iloc[-4:]).mean())
        if m in H.CANDIDATES:
            out["decision"][m] = H.decide_cont(df, m, k)
            out["continuous"][m]["dm_vs_rw"] = H.dm_test((df[m] - df["y"]).to_numpy(), (df["RW"] - df["y"]).to_numpy(), k)
    for b in ("B1", "B2", "B3", "B4"):
        out["binary"][b] = {m: H.bin_metrics(df, f"{m}_p{b}", f"y{b}") for m in H.METHODS + ["PERSIST", "CLIM"]}
        out["binary_decision"][b] = {m: H.decide_bin(df, m, b) for m in H.CANDIDATES + ["RW"]}
    return out


def family_usage(k: int) -> dict:
    """LGBM: which columns received splits and mean |SHAP| per family over the evaluated origins."""
    df = pd.read_csv(OUT / f"predictions_lead{k}.csv")
    gain = {c: 0.0 for c in E.COLUMNS}
    shap = {c: [] for c in E.COLUMNS}
    for t in df["t"]:
        f = H.forecast("LGBM", int(t), k)
        for c in E.COLUMNS:
            gain[c] += f["gain"][c]
            shap[c].append(abs(f["shap"][c]))
    fam = {f: float(sum(np.mean(shap[c]) for c in E.COLUMNS if E.FAMILY_OF[c] == f)) for f in E.FAMILIES}
    tot = sum(fam.values()) or 1.0
    return {"gain": gain, "family_mean_abs_shap": fam, "family_share": {f: v / tot for f, v in fam.items()},
            "families_never_split": sorted({E.FAMILY_OF[c] for c in E.COLUMNS if gain[c] == 0}
                                           - {E.FAMILY_OF[c] for c in E.COLUMNS if gain[c] > 0}),
            "mean_abs_delta_points": float(np.mean([abs(H.forecast("LGBM", int(t), k)["delta"]) for t in df["t"]]))}


def ablation(k: int) -> dict:
    """LGBM without one domain at a time (diagnostic): MAE on the same quarters."""
    df = pd.read_csv(OUT / f"predictions_lead{k}.csv")
    res = {"full": float(np.abs(df["LGBM"] - df["y"]).mean())}
    keep_all = list(E.COLUMNS)
    for dom in E.DOMAINS:
        cols = [c for c in keep_all if E.DOMAIN_OF[c] != dom]
        errs = []
        for t, y in zip(df["t"], df["y"]):
            tr = H.pairs(int(t), k)
            n = H.lgbm_select(tr, k)
            m = H._lgbm(n).fit(tr[cols].astype(float), tr["dy"].to_numpy())
            x = H.regional_features(k).loc[int(t), cols].astype(float)
            errs.append(abs(H.h_last(int(t))[1] + float(m.predict(pd.DataFrame([x]))[0]) - y))
        res[f"-{dom}"] = float(np.mean(errs))
    return res


def phase_score() -> None:
    st = check()
    OUT.mkdir(exist_ok=True)
    res = {"run": st, "leads": {}, "sensitivity": {}, "family_usage": {}, "ablation": {}}
    for k in H.LEADS:
        df = H.evaluate(k)
        df.to_csv(OUT / f"predictions_lead{k}.csv", index=False, lineterminator="\n", float_format="%.10g")
        res["leads"][str(k)] = lead_block(df, k)
        print(f"lead {k}: {len(df)} quarters")
    for k in H.LEADS:
        res["family_usage"][str(k)] = family_usage(k)
        res["ablation"][str(k)] = ablation(k)
    for rule in ("ALL", "PROD", "HH"):
        res["sensitivity"][rule] = {}
        for k in H.LEADS:
            df = H.evaluate(k, rule, methods=H.BASELINES + ["LGBM", "LL"])
            if len(df) >= 3:
                res["sensitivity"][rule][str(k)] = {
                    "n_quarters": len(df), **{m: H.cont_metrics(df, m, k) for m in H.BASELINES + ["LGBM", "LL"]},
                    "LGBM_decision": H.decide_cont(df, "LGBM", k) if len(df) else None}
    status = {m: {str(k): res["leads"][str(k)]["decision"][m]["status"] for k in H.LEADS} for m in H.CANDIDATES}
    res["status"] = status

    def max_lead(m, wanted):
        best = None
        for k in H.LEADS:
            if status[m][str(k)] in wanted:
                best = k
            else:
                break
        return best
    res["max_reliable_lead"] = {m: max_lead(m, ("reliable",)) for m in H.CANDIDATES}
    res["max_provisional_lead"] = {m: max_lead(m, ("reliable", "provisional")) for m in H.CANDIDATES}
    d1 = res["leads"]["1"]["decision"]
    rec = "LGBM"
    for m in ("LL", "RIDGE"):
        more = len(d1[m]["failed"]) < len(d1["LGBM"]["failed"])
        df1 = pd.read_csv(OUT / "predictions_lead1.csv")
        better = H.dm_test((df1[m] - df1["y"]).to_numpy(), (df1["LGBM"] - df1["y"]).to_numpy(), 1)
        if more and d1[m]["mae"] < d1["LGBM"]["mae"] and (better.get("p") or 1) < 0.10:
            rec = m
    res["recommended_candidate"] = rec
    H.write_json(OUT / "results.json", res)


# ================================================================================================ prospective
def phase_prospective() -> None:
    st = check()
    t = E.LAST_ORIGIN
    rows = []
    for k in H.LEADS:
        for m in H.METHODS:
            f = H.forecast(m, t, k)
            if f is None:
                continue
            s = H.sigma(m, t, k)
            rows.append({"method": m, "lead": k, "origin": E.qs(t), "issue_date": E.issue(t), "target_quarter": E.qs(t + k),
                         "area": "Balance Luzon (SWS)", "h_last": f["h_last"], "h_last_quarter": f["h_last_quarter"],
                         "forecast_pct": round(f["forecast"], 4), "pi80_low": round(f["forecast"] - 1.2816 * s, 4),
                         "pi80_high": round(f["forecast"] + 1.2816 * s, 4), "sigma": round(s, 4),
                         **{f"p_{b}_gt_{c}": round(H.p_above(f["forecast"], c, s), 4) for b, c in H.THRESHOLDS.items()},
                         "p_B4_rise_gt_4pts": round(H.p_above(f["forecast"], f["h_last"] + H.RISE, s), 4),
                         "n_pairs": f["n_pairs"]})
    df = pd.DataFrame(rows)
    f = OUT / "sealed_prospective.csv"
    df.to_csv(f, index=False, lineterminator="\n")
    (OUT / "sealed_prospective.csv.sha256").write_text(H.sha256(f) + "\n", encoding="utf-8", newline="\n")
    src = {"outcome_rounds.csv": H.sha256(H.ROUNDS), "sws_rounds.csv": H.sha256(E.BACKEND / "data/inputs/sws_rounds.csv"),
           **{p.name: H.sha256(p) for p in sorted(E.DATA_IN.glob("*.parquet"))}}
    H.write_json(OUT / "prospective_record.json", {
        "git": st, "sealed_sha256": H.sha256(f), "origin": E.qs(t), "issue_date": E.issue(t),
        "data_cutoff": "data published before 2026-10-01 (SWS 2026-Q3 round published 2026-10-14 is NOT used)",
        "target": "SWS Balance Luzon Total Hunger, non-commissioned rounds, quarter mean (PROTOCOL section 1)",
        "thresholds": {**H.THRESHOLDS, "B4": "rise > 4.0 points over h_last"}, "feature_columns": E.COLUMNS,
        "source_hashes": src, "scoring": "runner/score_prospective.py once SWS publishes each target quarter",
        "e107_seal": H.sha256(H.E109.parent / "E107_Twelve_Indicator_LightGBM/out/sealed_prospective.csv"),
        "e108_seal": H.sha256(H.E109.parent / "E108_Best_Defensible_Forecasting/out/sealed_prospective.csv")})
    print(df[["method", "lead", "target_quarter", "h_last", "forecast_pct", "pi80_low", "pi80_high"]].to_string())


# ================================================================================================ export
def phase_export() -> None:
    res = json.loads((OUT / "results.json").read_text())
    pro = json.loads((OUT / "prospective_record.json").read_text())
    serve = E.BACKEND / "data" / "e109"
    serve.mkdir(parents=True, exist_ok=True)
    ev = {"schema": "aipheed.e109.evaluation/1",
          "outcome": "SWS Balance Luzon Total Hunger (% of families that experienced involuntary hunger at least once in "
                     "the past three months); regional, not provincial",
          "status": "Development evidence: every evaluated quarter was seen before the protocol was frozen; no lead "
                    "is confirmed on unseen outcomes",
          "protocol_sha256": res["run"]["protocol_sha256"], "status_by_lead": res["status"],
          "max_reliable_lead": res["max_reliable_lead"], "max_provisional_lead": res["max_provisional_lead"],
          "leads": {k: {"n_quarters": v["n_quarters"],
                        "mae": {m: round(x["mae"], 3) for m, x in v["continuous"].items()},
                        "decision": {m: {"status": d["status"], "failed": d["failed"]} for m, d in v["decision"].items()}}
                    for k, v in res["leads"].items()}}
    H.write_json(serve / "evaluation_summary.json", ev)
    rows = pd.read_csv(OUT / "sealed_prospective.csv")
    H.write_json(serve / "forecast.json", {"schema": "aipheed.e109.forecast/1", **pro,
                                           "note": "Regional forecast; identical for the five provinces. Not validated.",
                                           "forecasts": rows.to_dict("records")})
    vul = pd.read_csv(E.BACKEND / "data/inputs/lgu_vulnerability.csv", dtype=str)
    lgus = [{"lgu_code": r.lgu_code, "lgu": r.lgu_name, "lgu_type": r.lgu_type, "province": r.province,
             "status": "INSUFFICIENT LOCAL EVIDENCE",
             "explanation": "No LGU or provincial hunger observation exists. The regional SWS Balance Luzon forecast "
                            "applies to the whole area; no LOW/HIGH label is assigned to this LGU.",
             "context_poverty_lgu_estimate": r.poverty_lgu_estimate, "context_poverty_source": r.poverty_source}
            for r in vul.itertuples()]
    H.write_json(serve / "lgu_status.json", {"schema": "aipheed.e109.lgu_status/1", "n_lgus": len(lgus), "lgus": lgus})
    print("exported", len(lgus), "LGUs")


if __name__ == "__main__":
    {"score": phase_score, "prospective": phase_prospective, "export": phase_export}[sys.argv[1]]()
