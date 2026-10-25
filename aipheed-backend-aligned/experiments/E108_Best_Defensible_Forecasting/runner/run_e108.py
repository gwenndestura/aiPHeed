"""E108 runner (PROTOCOL.md). Phases:

    python run_e108.py score        all candidates and baselines at Leads 1-4, the regional analysis, section 7 decisions
    python run_e108.py diag         ablations, grouped permutation importance, SHAP stability, price-only, S1, S2
    python run_e108.py prospective  sealed Lead 1-4 forecasts from origin 2026-Q3 (issue 2026-10-01)
    python run_e108.py export       read-only API files in backend/data/e108/
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

import e108_lib as F

E, M, np, pd = F.E, F.M, F.np, F.pd
OUT = F.OUT
CANDS = list(F.CANDIDATES)
ARMS = ["PERSIST_p", "CLIM_p", "STRUCT_p", "PSA_LR_p", "NLP_LR_p", "LR12_p", "E56_p", "FIRI_score", "E107_p"]


def git_state() -> dict:
    def g(*a):
        return subprocess.run(["git", *a], cwd=E.REPO, capture_output=True, text=True).stdout.strip()
    return {"commit": g("rev-parse", "HEAD"), "branch": g("branch", "--show-current"),
            "runner_dirty": bool(g("status", "--porcelain", "--", str(F.HERE))),
            "protocol_sha256": F.sha256(F.E108 / "PROTOCOL.md"),
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def check() -> dict:
    st = git_state()
    assert st["protocol_sha256"] == (F.HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "PROTOCOL.md changed"
    for line in filter(None, (E.DATA_IN / "SHA256SUMS.txt").read_text().split("\n")):
        h, name = line.split(" *")
        assert E.sha256(E.DATA_IN / name.split("/")[-1]) == h
    return st


def per_quarter(df, col) -> list[dict]:
    pq = M.per_quarter(df, col)
    out = []
    for q, r in pq.iterrows():
        g = df[df["q"] == q]
        out.append({"quarter": E.qs(int(q)), "n": int(r["n"]), "high": int(r["n_high"]), "correct": int(round(r["accuracy"] * r["n"])),
                    "brier_mean": float(r["brier_mean"]), "hunger_elevated": int(g["hunger_elevated"].iloc[0]),
                    "mean_p": float(g[col].mean())})
    return out


def lead_summary(df: pd.DataFrame) -> dict:
    out = {"quarters": [E.qs(int(q)) for q in sorted(df["q"].unique())], "n_rows": len(df),
           "candidates": {}, "arms": {}, "paired": {}, "decision": {}, "per_quarter": {}, "onsets": {}}
    for c in CANDS:
        col = f"{c}_p"
        out["candidates"][c] = F.summary(df, col)
        out["candidates"][c]["hunger_elevated"] = F.summary(df[df["hunger_elevated"] == 1], col)
        out["candidates"][c]["recent_four"] = F.summary(df[df["q"].isin(E.FINAL_BLOCK)], col)
        out["decision"][c] = F.decide(df, col)
        out["per_quarter"][c] = per_quarter(df, col)
        out["onsets"][c] = F.onsets(df, col)
        out["paired"][c] = {a: M.paired(df.dropna(subset=[a]), col, a) for a in ARMS + [f"{x}_p" for x in CANDS if x != c]
                            if a in df and df[a].notna().any()}
    for a in ARMS:
        if a in df and df[a].notna().any():
            d = df.dropna(subset=[a])
            out["arms"][a] = F.summary(df, a)
            out["arms"][a]["F1_on_same_rows"] = M.metrics(d["y"], d["F1_p"])
            if a in ("E107_p", "E56_p", "STRUCT_p"):           # comparators judged by the same rule on their own rows
                out["decision"][a] = F.decide(d, a)
    out["always_low_accuracy"] = float(1 - df["y"].mean())
    out["price_only_on_PS"] = {c: M.metrics(df["PS_y"], df[f"{c}_price"]) for c in CANDS}
    return out


def regional_summary(r: pd.DataFrame) -> dict:
    if not len(r):
        return {"n": 0}
    out = {"quarters": [E.qs(int(q)) for q in r["q"]], "n_quarters": len(r), "n_high": int(r["y"].sum())}
    for a in ("H1_p", "PERSIST_p", "CLIM_p", "E107_R_p"):
        if a in r and r[a].notna().any():
            d = r.dropna(subset=[a])
            out[a] = M.metrics(d["y"], d[a])
    out["paired_H1_vs_persistence"] = M.paired(r, "H1_p", "PERSIST_p")
    out["level_mae"] = {a: float(np.mean(np.abs(r[a] - r["H"]))) for a in ("RW_level", "MA2_level", "MEAN_level")}
    both = 0 < r["y"].sum() < len(r)
    m, p = out["H1_p"], out["PERSIST_p"]
    out["H1_rule"] = {"R1": len(r) >= 6, "R2": m["accuracy"] >= 0.75, "R3": m["accuracy"] > p["accuracy"],
                      "R4": m["brier"] < p["brier"] and out["paired_H1_vs_persistence"]["signflip_p_one_sided"] < 0.10,
                      "R5": bool(both and m["recall_high"] >= 0.5 and m["recall_low"] >= 0.5),
                      "both_classes": bool(both)}
    return out


def phase_score() -> None:
    st = check()
    OUT.mkdir(exist_ok=True)
    res = {"run": st, "leads": {}, "regional": {}}
    recs = {}
    for k in E.LEADS:
        df, rr = F.run(k, explain=True)
        F.write_csv(OUT / f"predictions_T43_lead{k}.csv", df)
        recs[str(k)] = rr
        res["leads"][str(k)] = lead_summary(df) if len(df) else {"n_rows": 0}
        r = F.regional(k)
        F.write_csv(OUT / f"regional_lead{k}.csv", r)
        res["regional"][str(k)] = regional_summary(r)
        print(f"lead {k}: {len(df)} rows / {df['q'].nunique() if len(df) else 0} quarters; regional {len(r)} quarters")
    for c in CANDS:
        dec = {str(k): res["leads"][str(k)]["decision"][c] for k in E.LEADS if res["leads"][str(k)].get("decision")}
        res.setdefault("max_reliable_lead", {})[c] = F.max_reliable(dec) if len(dec) == 4 else None
    p = res["leads"]
    rep = {}
    for c in ("F0", "F2"):
        ok = all(p[k]["paired"][c].get("F1_p", {}).get("mean_quarter_brier_diff", 1) < 0 and
                 p[k]["paired"][c]["F1_p"]["signflip_p_one_sided"] < 0.10 for k in ("1", "2"))
        more = all(len(p[k]["decision"][c]["failed"]) <= len(p[k]["decision"]["F1"]["failed"]) for k in map(str, E.LEADS))
        rep[c] = {"brier_better_L1_L2_p<0.10": ok, "passes_at_least_as_many_criteria": more, "replaces_F1": ok and more}
    res["replacement_rule"] = rep
    res["recommended"] = next((c for c, v in rep.items() if v["replaces_F1"]), "F1")
    F.write_json(OUT / "origin_records.json", recs)
    F.write_json(OUT / "results.json", res)


# ================================================================================================ diagnostics
ABL = {"-A": "A", "-V": "V", "-C": "C", "-E": "E", "-N": "N", "-H": "H"}


def phase_diag() -> None:
    res = json.loads((OUT / "results.json").read_text())
    diag = {"ablations": {}, "permutation": {}, "shap_stability": {}, "sensitivity": {}}
    rng = np.random.default_rng(F.SEED)
    for k in E.LEADS:
        base = pd.read_csv(OUT / f"predictions_T43_lead{k}.csv", dtype={"province_code": str})
        qset = sorted(base["q"].unique())
        arms = {"full": M.metrics(base["y"], base["F1_p"])}
        for name, dom in list(ABL.items()) + [("A-only", None)]:
            cols = [c for c in E.COLUMNS if E.DOMAIN_OF[c] != dom] if dom else [c for c in E.COLUMNS if E.DOMAIN_OF[c] == "A"]
            df, _ = F.run(k, cands={"F1": F.CANDIDATES["F1"]}, cols=cols, quarters=qset, baselines=False)
            j = base[["q", "province_code", "y", "F1_p"]].merge(df[["q", "province_code", "F1_p"]].rename(
                columns={"F1_p": "abl"}), on=["q", "province_code"])
            arms[name] = {**M.metrics(j["y"], j["abl"]), "paired_full_vs_ablation": M.paired(j, "F1_p", "abl")}
        diag["ablations"][str(k)] = arms
        # grouped permutation importance: refit each origin's F1 once, permute a family across evaluation rows
        X = E.feature_table(k)
        fits = {}
        for q in qset:
            r = F.forecast_at(q - k, k)
            fits[q] = r[1]
        te = pd.concat([X[X["t"] == q - k].assign(q=q) for q in qset], ignore_index=True)
        te = te.merge(base[["q", "province_code", "y"]], on=["q", "province_code"])
        def pred(frame):
            return np.concatenate([fits[q].predict(frame[frame["q"] == q]) * frame.loc[frame["q"] == q, "H1"].to_numpy()
                                   for q in qset])
        order = pd.concat([te[te["q"] == q] for q in qset])
        b0 = float(np.mean((pred(order) - order["y"].to_numpy()) ** 2))
        perm = {}
        for fam in E.FAMILIES:
            cols = [c for c in E.COLUMNS if E.FAMILY_OF[c] == fam]
            vals = []
            for _ in range(200):
                sh = order.copy()
                idx = rng.permutation(len(sh))
                sh[cols] = sh[cols].to_numpy()[idx]
                vals.append(float(np.mean((pred(sh) - sh["y"].to_numpy()) ** 2)) - b0)
            perm[fam] = {"mean_brier_increase": float(np.mean(vals)), "p05": float(np.percentile(vals, 5)),
                         "p95": float(np.percentile(vals, 95))}
        diag["permutation"][str(k)] = {"base_brier": b0, "families": perm}
        recs = json.loads((OUT / "origin_records.json").read_text())[str(k)]
        shares = []
        for r in recs:
            sv = r["cand"]["F1"].get("shap") or {}
            if not sv:
                continue
            fam = {f: np.mean([abs(v[c]) for v in sv.values() for c in E.COLUMNS if E.FAMILY_OF[c] == f]) for f in E.FAMILIES}
            tot = sum(fam.values()) or 1.0
            shares.append({f: v / tot for f, v in fam.items()})
        sdf = pd.DataFrame(shares)
        diag["shap_stability"][str(k)] = {"mean_share": sdf.mean().to_dict(), "sd_share": sdf.std().to_dict(),
                                          "origins": len(sdf), "never_used": [f for f in E.FAMILIES if sdf[f].max() == 0]}
    diag["sensitivity"] = sensitivities()
    F.write_json(OUT / "diagnostics.json", diag)


def sensitivities() -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location("r7", E.E107 / "runner" / "run_e107.py")
    r7 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r7)
    d_all = r7.all_rounds_data()
    out = {"S1_all_rounds": {}, "S2_v1_strict": {}}
    obs = E.t43_frame(d_all)
    for k in E.LEADS:
        df, _ = F.run(k, cands={"F1": F.CANDIDATES["F1"]}, obs=obs, baselines=False)
        if len(df):
            lab_t = {t: r7._known_all(d_all, t, "T43") for t in df["t"].unique()}
            df["CLIM_p"] = df["t"].map({t: float(v["y"].mean()) for t, v in lab_t.items()})
            df["PERSIST_p"] = [float(lab_t[t][lab_t[t]["province_code"] == p].sort_values("q")["y"].iloc[-1])
                               for t, p in zip(df["t"], df["province_code"])]
            out["S1_all_rounds"][str(k)] = {"metrics": M.metrics(df["y"], df["F1_p"], quarters=df["q"]),
                                            "decision": F.decide(df, "F1_p")}
        X = E.feature_table(k)
        X.loc[X["issue_date"] < "2025-07-01", "V1"] = np.nan
        df, _ = F.run(k, cands={"F1": F.CANDIDATES["F1"]}, X=X, baselines=False)
        if len(df):
            out["S2_v1_strict"][str(k)] = {"metrics": M.metrics(df["y"], df["F1_p"], quarters=df["q"])}
    return out


# ================================================================================================ prospective, export
def phase_prospective() -> None:
    st = check()
    t, rows = E.LAST_ORIGIN, []
    for k in E.LEADS:
        for c in CANDS:
            r = F.forecast_at(t, k, c)
            if r is None:
                continue
            for x in r[0].itertuples():
                rows.append({"candidate": c, "lead": k, "origin": E.qs(t), "issue_date": E.issue(t),
                             "target_quarter": E.qs(t + k), "province_code": x.province_code,
                             "province": E.NAMES[x.province_code], "hunger_outlook_H1": round(x.H1, 6),
                             "price_pressure_prob": round(float(x.price), 6), "p_high": round(float(x.p), 6),
                             "class": "HIGH" if x.p >= 0.5 else "LOW", "config": int(x.cfg), "n_train": int(x.n_train)})
    df = pd.DataFrame(rows)
    f = OUT / "sealed_prospective.csv"
    F.write_csv(f, df)
    (OUT / "sealed_prospective.csv.sha256").write_text(F.sha256(f) + "\n", encoding="utf-8", newline="\n")
    F.write_json(OUT / "prospective_record.json", {"git": st, "sealed_sha256": F.sha256(f), "origin": E.qs(t),
                                                   "issue_date": E.issue(t)})
    print(df[df["candidate"] == "F1"].to_string())


def phase_export() -> None:
    res = json.loads((OUT / "results.json").read_text())
    serve = E.BACKEND / "data" / "e108"
    serve.mkdir(parents=True, exist_ok=True)
    keep = ("n", "n_quarters", "n_high", "accuracy", "balanced_accuracy", "recall_high", "recall_low", "precision_high",
            "auc", "brier", "false_alarm_rate", "missed_high_rate", "share_pred_high")
    ev = {"schema": "aipheed.e108.evaluation/1",
          "status": "Development evidence (all evaluated quarters were examined earlier). Not served on the dashboard.",
          "forecast": "P(T43 HIGH) = H1 (regional SWS hunger outlook) x LightGBM probability of provincial food-price "
                      "pressure on all 12 indicators; T43 is a composite risk proxy, not a measured prevalence",
          "protocol_sha256": res["run"]["protocol_sha256"], "max_reliable_lead": res["max_reliable_lead"],
          "recommended": res["recommended"], "leads": {}, "regional": {}}
    for k, s in res["leads"].items():
        ev["leads"][k] = {"quarters": s["quarters"], "decision": {c: {x: s["decision"][c][x] for x in
                                                                      ("class", "failed", "meets_75")} for c in CANDS},
                          "metrics": {c: {x: s["candidates"][c].get(x) for x in keep} for c in CANDS},
                          "baselines": {a: {x: m.get(x) for x in keep} for a, m in s["arms"].items()}}
    for k, s in res["regional"].items():
        ev["regional"][k] = {x: s.get(x) for x in ("n_quarters", "n_high", "level_mae", "H1_rule")}
    F.write_json(serve / "evaluation_summary.json", ev)
    pro = json.loads((OUT / "prospective_record.json").read_text())
    rows = pd.read_csv(OUT / "sealed_prospective.csv", dtype={"province_code": str})
    F.write_json(serve / "forecast.json", {"schema": "aipheed.e108.forecast/1", **pro,
                                           "status": "Sealed research forecasts; no reliable lead time was established.",
                                           "forecasts": rows.to_dict("records")})
    F.write_json(serve / "indicators.json", {"schema": "aipheed.e108.indicators/1", "families": E.INVENTORY,
                                             "columns": E.COLUMNS, "n_families": 12, "n_columns": len(E.COLUMNS)})


if __name__ == "__main__":
    {"score": phase_score, "diag": phase_diag, "prospective": phase_prospective, "export": phase_export}[sys.argv[1]]()
