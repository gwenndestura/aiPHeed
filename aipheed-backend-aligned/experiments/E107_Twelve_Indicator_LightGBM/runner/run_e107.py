"""E107 runner (PROTOCOL.md). Phases, in order:

    python run_e107.py dev          development-block predictions and metrics (targets before 2025-Q4)
    python run_e107.py final        final-block predictions (2025-Q4..2026-Q3), combined metrics, section 8 decisions
    python run_e107.py diag         ablations, SHAP/gain, THR-INNER, common rows, sensitivities S1-S3 (diagnostic)
    python run_e107.py prospective  sealed Lead 1-4 forecasts from origin 2026-Q3 (issue 2026-10-01)

Run with the backend virtual environment. Outputs go to ../out/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

import e107_lib as E
import e107_model as M

np, pd = E.np, E.pd
OUT = E.E107 / "out"
TARGETS = ("T43", "R")
ARMS = {"T43": ["PERSIST_p", "CLIM_p", "PSA_LR_p", "NLP_LR_p", "LR12_p", "RULE_p", "E56_p", "FIRI_score"],
        "R": ["PERSIST_p", "CLIM_p", "H1_p", "E56_p", "FIRI_score"]}
GATE = {"T43": ["PERSIST_p", "CLIM_p"], "R": ["PERSIST_p", "CLIM_p", "H1_p"]}


def git_state() -> dict:
    def g(*a):
        return subprocess.run(["git", *a], cwd=E.REPO, capture_output=True, text=True).stdout.strip()
    return {"commit": g("rev-parse", "HEAD"), "branch": g("branch", "--show-current"),
            "runner_dirty": bool(g("status", "--porcelain", "--", str(E.E107 / "runner"))),
            "protocol_sha256": E.sha256(E.E107 / "PROTOCOL.md"),
            "protocol_frozen_sha256": (E.E107 / "runner" / "PROTOCOL_SHA256.txt").read_text().strip()}


def check_inputs() -> None:
    sums = (E.DATA_IN / "SHA256SUMS.txt").read_text().split("\n")
    for line in filter(None, sums):
        h, name = line.split(" *")
        assert E.sha256(E.DATA_IN / name.split("/")[-1]) == h, f"{name} changed"
    st = git_state()
    assert st["protocol_sha256"] == st["protocol_frozen_sha256"], "PROTOCOL.md changed after freezing"


# ================================================================================================ summaries
def summarize(df: pd.DataFrame, target: str) -> dict:
    if not len(df):
        return {"n": 0}
    out = {"primary": M.metrics(df["y"], df["p"], quarters=df["q"]),
           "quarters": [E.qs(int(q)) for q in sorted(df["q"].unique())]}
    out["primary"]["accuracy_cluster95"] = M.cluster_ci(df, "p")
    out["primary"]["reliability_table"] = M.reliability_table(df["y"], df["p"])
    thr = df.assign(c=(df["p"] >= df["thr_inner"]).astype(int))
    out["primary_thr_inner"] = {"accuracy": float((thr["c"] == thr["y"]).mean()),
                                "recall_high": float(thr.loc[thr["y"] == 1, "c"].mean()) if thr["y"].sum() else None,
                                "recall_low": float(1 - thr.loc[thr["y"] == 0, "c"].mean()) if (1 - thr["y"]).sum() else None,
                                "median_threshold": float(df["thr_inner"].median())}
    out["arms"], out["paired_vs_primary"] = {}, {}
    for a in ARMS[target]:
        if a not in df:
            continue
        d = df.dropna(subset=[a])
        if not len(d):
            continue
        rec = M.metrics(d["y"], d[a], quarters=d["q"])
        rec["rows_compared"] = len(d)
        rec["primary_on_same_rows"] = M.metrics(d["y"], d["p"])
        if a == "FIRI_score":
            rec["note"] = "FIRI is an index, not a probability; Brier/logloss shown for reference only"
        out["arms"][a] = rec
        out["paired_vs_primary"][a] = M.paired(d, "p", a)
    out["always_high_accuracy"] = float(df["y"].mean())
    out["always_low_accuracy"] = float(1 - df["y"].mean())
    pq = M.per_quarter(df, "p")
    pp = M.per_quarter(df, "PERSIST_p")
    out["per_quarter"] = [{"quarter": E.qs(int(q)), "block": "final" if q in E.FINAL_BLOCK else "dev",
                           **{k: (float(v) if k not in ("n", "n_high") else int(v)) for k, v in r.items()},
                           "persistence_accuracy": float(pp.loc[q, "accuracy"]),
                           "persistence_brier_sum": float(pp.loc[q, "brier_sum"])} for q, r in pq.iterrows()]
    out["configs_selected"] = {str(int(c)): int(n) for c, n in df.drop_duplicates("q")["cfg"].value_counts().items()}
    return out


def decide(df: pd.DataFrame, target: str) -> dict:
    """PROTOCOL section 8 for one lead on combined rows (G3 on final-block rows)."""
    if not len(df):
        return {"reliable": False, "assessable": False, "reason": "no evaluable rows"}
    m = M.metrics(df["y"], df["p"])
    nq = int(df["q"].nunique())
    acc = m["accuracy"]
    gate = GATE[target]
    base = {a: M.metrics(df["y"], df[a]) for a in gate}
    best = min(gate, key=lambda a: base[a]["brier"])
    pt = M.paired(df, "p", best)
    both = 0 < df["y"].sum() < len(df)
    c = {}
    c["R1_quarters>=6"] = nq >= 6
    c["R2_accuracy>=0.75"] = acc >= 0.75
    c["R3_acc>persist_and_majority"] = (acc > base["PERSIST_p"]["accuracy"] and acc > base["CLIM_p"]["accuracy"])
    c["R4_brier_below_baselines_and_p<0.10"] = (all(m["brier"] < base[a]["brier"] for a in gate)
                                                 and pt["signflip_p_one_sided"] < 0.10)
    c["R5_both_recalls>=0.5"] = bool(both and m["recall_high"] is not None and m["recall_low"] is not None
                                     and m["recall_high"] >= 0.5 and m["recall_low"] >= 0.5)
    c["R6_auc>=0.65"] = bool(both and m["auc"] is not None and m["auc"] >= 0.65)
    c["R7_share_high_in_[0.1,0.9]"] = 0.1 <= m["share_pred_high"] <= 0.9
    if target == "T43":
        pq = M.per_quarter(df, "p")
        c["G1_quarter_acc>=0.6_in_2/3"] = float((pq["accuracy"] >= 0.6).mean()) >= 2 / 3
    qs_ = sorted(df["q"].unique())
    h = (len(qs_) + 1) // 2
    halves = []
    for part in (qs_[:h], qs_[h:]):
        d = df[df["q"].isin(part)]
        if not len(d):
            halves.append(False)
            continue
        bb = min(M.metrics(d["y"], d[a])["brier"] for a in gate)
        halves.append(M.metrics(d["y"], d["p"])["brier"] < bb)
    c["G2_brier_better_both_halves"] = all(halves)
    fb = df[df["block"] == "final"]
    if len(fb):
        fm = M.metrics(fb["y"], fb["p"])
        g3a = fm["accuracy"] >= max(M.metrics(fb["y"], fb["PERSIST_p"])["accuracy"],
                                    M.metrics(fb["y"], fb["CLIM_p"])["accuracy"])
        g3b = fm["brier"] <= min(M.metrics(fb["y"], fb[a])["brier"] for a in gate)
        c["G3_final_block_not_worse"] = bool(g3a and g3b)
    else:
        c["G3_final_block_not_worse"] = False
    fails = [k for k, v in c.items() if not v]
    return {"reliable": not fails, "assessable": c["R1_quarters>=6"], "criteria": c, "failed": fails,
            "accuracy": acc, "meets_75": c["R2_accuracy>=0.75"], "lowest_brier_baseline": best,
            "paired_vs_lowest_baseline": pt, "baseline_metrics": {a: {"accuracy": base[a]["accuracy"],
                                                                       "brier": base[a]["brier"]} for a in gate},
            "n_quarters": nq, "n_rows": len(df), "both_classes": bool(both)}


def max_reliable(dec: dict) -> int | None:
    best = None
    for k in E.LEADS:
        if dec[str(k)]["reliable"]:
            best = k
        else:
            break
    return best


# ================================================================================================ phases
def labelled_quarters(target: str) -> list[int]:
    o = E.outcomes(target)
    return sorted(q for q in o["q"].unique() if q <= E.LAST_OUTCOME)


def phase_predict(block: str) -> None:
    check_inputs()
    st = git_state()
    d = OUT / block
    d.mkdir(parents=True, exist_ok=True)
    allrec = {}
    for target in TARGETS:
        qs_ = [q for q in labelled_quarters(target) if (q in E.FINAL_BLOCK) == (block == "final")]
        for k in E.LEADS:
            df, recs = M.run(k, target, quarters=qs_, explain=True)
            M.write_csv(d / f"predictions_{target}_lead{k}.csv", df)
            allrec[f"{target}_lead{k}"] = recs
            print(f"{block} {target} lead {k}: {len(df)} rows, {df['q'].nunique() if len(df) else 0} quarters")
    E.write_json(d / "origin_records.json", allrec)
    E.write_json(d / "run.json", {"phase": block, "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                  "git": st, "python": sys.version})


def load_block(block: str, target: str, k: int) -> pd.DataFrame:
    f = OUT / block / f"predictions_{target}_lead{k}.csv"
    if not f.exists() or f.stat().st_size < 5:
        return pd.DataFrame()
    return pd.read_csv(f, dtype={"province_code": str})


def phase_dev_metrics() -> None:
    res = {}
    for target in TARGETS:
        res[target] = {str(k): summarize(load_block("dev", target, k), target) for k in E.LEADS}
    E.write_json(OUT / "dev" / "metrics.json", res)


def phase_combined() -> None:
    assert (OUT / "dev" / "metrics.json").exists(), "development results must be recorded first"
    res = {"protocol_sha256": E.sha256(E.E107 / "PROTOCOL.md"),
           "dev_run": json.loads((OUT / "dev" / "run.json").read_text()),
           "final_run": json.loads((OUT / "final" / "run.json").read_text()), "targets": {}}
    for target in TARGETS:
        T = {"blocks": {}, "decision": {}}
        for k in E.LEADS:
            dv, fn = load_block("dev", target, k), load_block("final", target, k)
            cb = pd.concat([x for x in (dv, fn) if len(x)], ignore_index=True) if len(dv) or len(fn) else pd.DataFrame()
            M.write_csv(OUT / f"predictions_{target}_lead{k}.csv", cb)
            T["blocks"][str(k)] = {"dev": summarize(dv, target), "final": summarize(fn, target),
                                   "combined": summarize(cb, target)}
            T["decision"][str(k)] = decide(cb, target)
        T["max_reliable_lead"] = max_reliable(T["decision"])
        T["leads_passing"] = [k for k in E.LEADS if T["decision"][str(k)]["reliable"]]
        res["targets"][target] = T
    E.write_json(OUT / "results.json", res)


# ================================================================================================ diagnostics
ABLATIONS = {"-A": [c for c in E.COLUMNS if E.DOMAIN_OF[c] != "A"], "-V": [c for c in E.COLUMNS if E.DOMAIN_OF[c] != "V"],
             "-C": [c for c in E.COLUMNS if E.DOMAIN_OF[c] != "C"], "-E": [c for c in E.COLUMNS if E.DOMAIN_OF[c] != "E"],
             "-N": [c for c in E.COLUMNS if E.DOMAIN_OF[c] != "N"], "-H": [c for c in E.COLUMNS if E.DOMAIN_OF[c] != "H"],
             "A-only": [c for c in E.COLUMNS if E.DOMAIN_OF[c] == "A"], "H-only": ["H1"],
             "A+H": [c for c in E.COLUMNS if E.DOMAIN_OF[c] in "AH"]}


def importance(recs: list[dict]) -> dict:
    """Mean |SHAP| (log-odds) and total gain per column, family and domain over the evaluation predictions."""
    sh, gn = {c: [] for c in E.COLUMNS}, {c: 0.0 for c in E.COLUMNS}
    for r in recs:
        for row in (r.get("shap") or {}).values():
            for c in E.COLUMNS:
                sh[c].append(abs(row.get(c, 0.0)))
        for c, v in (r.get("gain") or {}).items():
            gn[c] += v
    col = {c: float(np.mean(v)) if v else 0.0 for c, v in sh.items()}
    fam = {f: sum(col[c] for c in E.COLUMNS if E.FAMILY_OF[c] == f) for f in E.FAMILIES}
    dom = {d: sum(v for f, v in fam.items() if f[0] == d) for d in E.DOMAINS}
    tot = sum(fam.values()) or 1.0
    gt = sum(gn.values()) or 1.0
    return {"mean_abs_shap_column": col, "mean_abs_shap_family": fam, "mean_abs_shap_domain": dom,
            "family_share": {f: v / tot for f, v in fam.items()}, "domain_share": {d: v / tot for d, v in dom.items()},
            "gain_share_column": {c: v / gt for c, v in gn.items()},
            "families_never_used": [f for f in E.FAMILIES if fam[f] == 0.0],
            "largest_family": max(fam, key=fam.get), "largest_family_share": max(fam.values()) / tot}


def phase_diag() -> None:
    res = json.loads((OUT / "results.json").read_text())
    diag = {"ablations": {}, "importance": {}, "common_rows": {}, "sensitivity": {}}
    for target in TARGETS:
        diag["importance"][target] = {str(k): importance(_recs(target, k)) for k in E.LEADS}
        diag["ablations"][target] = {}
        for k in E.LEADS:
            base = pd.read_csv(OUT / f"predictions_{target}_lead{k}.csv", dtype={"province_code": str}) \
                if (OUT / f"predictions_{target}_lead{k}.csv").stat().st_size > 5 else pd.DataFrame()
            if not len(base):
                continue
            qset = sorted(base["q"].unique())
            arm = {"full": M.metrics(base["y"], base["p"])}
            for name, cols in ABLATIONS.items():
                df, _ = M.run(k, target, cols=cols, quarters=qset, arms=False)
                j = base[["q", "province_code", "y", "p"]].merge(df[["q", "province_code", "p"]].rename(
                    columns={"p": "p_abl"}), on=["q", "province_code"])
                arm[name] = {**M.metrics(j["y"], j["p_abl"]), "paired_full_minus_ablation": M.paired(
                    j.rename(columns={"p_abl": "abl"}), "p", "abl")}
            diag["ablations"][target][str(k)] = arm
        assess = [k for k in E.LEADS if res["targets"][target]["decision"][str(k)]["assessable"]]
        if assess:
            frames = {k: pd.read_csv(OUT / f"predictions_{target}_lead{k}.csv", dtype={"province_code": str})
                      for k in assess}
            common = set.intersection(*[set(f["q"]) for f in frames.values()])
            diag["common_rows"][target] = {"quarters": [E.qs(int(q)) for q in sorted(common)],
                                           **{str(k): {"primary": M.metrics(f[f["q"].isin(common)]["y"],
                                                                            f[f["q"].isin(common)]["p"]),
                                                       "persistence": M.metrics(f[f["q"].isin(common)]["y"],
                                                                                f[f["q"].isin(common)]["PERSIST_p"])}
                                              for k, f in frames.items()}}
    diag["sensitivity"] = sensitivities()
    E.write_json(OUT / "diagnostics.json", diag)


def _recs(target, k):
    out = []
    for b in ("dev", "final"):
        out += json.loads((OUT / b / "origin_records.json").read_text()).get(f"{target}_lead{k}", [])
    return out


def all_rounds_data():
    """S1: the production data object with every SWS round in the file (supplementary 2025 rounds included)."""
    d, _ = E.data()
    r = pd.read_csv(E.L.SWS_FILE)
    r["q"] = r["quarter"].map(E.qi)
    sws = pd.DataFrame({"q": r["q"], "H": r["H"].astype(float), "published": pd.to_datetime(r["published"])})
    return E.L.Data(d.idx, d.yoy, sws, d.prod, d.lfs, d.news, meta=d.meta)


def sensitivities() -> dict:
    out = {"S1_all_rounds": {}, "S2_v1_strict": {}, "S3_a1_served": {}}
    d_all = all_rounds_data()
    for target in TARGETS:
        obs = E.t43_frame(d_all) if target == "T43" else pd.DataFrame(
            [{"province_code": p, "q": q, "y": y, "H": h} for q, y, h in zip(*[E.r_frame(d_all)[c] for c in
                                                                                ("q", "y", "H")]) for p in E.PROVS])
        lab = lambda t, target=target: _known_all(d_all, t, target)  # noqa: E731
        for k in E.LEADS:
            df, _ = M.run(k, target, labels=lab, outcome=obs)
            if len(df):
                out["S1_all_rounds"][f"{target}_lead{k}"] = {"metrics": M.metrics(df["y"], df["p"], quarters=df["q"]),
                                                             "decision": decide(df.assign(block=df["block"]), target)}
    for target in TARGETS:
        for k in E.LEADS:
            X = E.feature_table(k)
            X.loc[X["issue_date"] < "2025-07-01", "V1"] = np.nan
            df, _ = M.run(k, target, X=X)
            if len(df):
                out["S2_v1_strict"][f"{target}_lead{k}"] = {"metrics": M.metrics(df["y"], df["p"], quarters=df["q"])}
    s = M.e63()
    for k in (1, 2, 3):
        X = E.feature_table(k)
        sk = s[s["lead"] == k].assign(t=lambda f: f["origin_quarter"].map(E.qi)).set_index(["t", "province_code"])
        X["A1_served"] = [sk["E56_p_price"].get((t, p), np.nan) for t, p in zip(X["t"], X["province_code"])]
        cols = ["A1_served"] + [c for c in E.COLUMNS if not c.startswith("A1_")]
        df, _ = M.run(k, "T43", cols=cols, X=X, arms=False)
        if len(df):
            out["S3_a1_served"][f"T43_lead{k}"] = {"metrics": M.metrics(df["y"], df["p"], quarters=df["q"]),
                                                   "training_rows_with_A1_served": "only origins in the E63 range"}
    return out


def _known_all(d_all, t, target):
    c = d_all.cut(t)
    full_n, cut_n = d_all.sws.groupby("q").size(), c.sws.groupby("q").size()
    complete = {q for q in cut_n.index if cut_n[q] == full_n.get(q, -1) and q <= t - 1}
    if target == "T43":
        lab = E.t43_frame(c)
        return lab[lab["q"].isin(complete)]
    r = E.r_frame(c)
    r = r[r["q"].isin(complete)]
    return pd.DataFrame([{"province_code": p, "q": q, "y": y, "H": h}
                         for q, y, h in zip(r["q"], r["y"], r["H"]) for p in E.PROVS])


# ================================================================================================ prospective
def phase_prospective() -> None:
    check_inputs()
    t = E.LAST_ORIGIN
    rows, rec = [], {"origin": E.qs(t), "issue_date": E.issue(t), "git": git_state(), "forecasts": {}}
    for target in TARGETS:
        for k in E.LEADS:
            X = E.feature_table(k)
            Xr = M.regional(X) if target == "R" else X
            tr = M.train_rows(Xr, t, k, target)
            if not E.eligible(tr):
                rec["forecasts"][f"{target}_lead{k}"] = {"status": "not eligible"}
                continue
            cfg, _, _ = M.select(tr, k, target, E.COLUMNS)
            mdl = M.Model(cfg, target, E.COLUMNS).fit(tr)
            te = Xr[Xr["t"] == t]
            p = mdl.predict(te)
            sv = mdl.shap(te)
            for i, (pp, pr) in enumerate(zip(te["province_code"], p)):
                rows.append({"target": target, "lead": k, "origin": E.qs(t), "issue_date": E.issue(t),
                             "target_quarter": E.qs(t + k), "province_code": pp,
                             "province": E.NAMES.get(pp, "Balance Luzon (region)"), "p_high": round(float(pr), 6),
                             "class": "HIGH" if pr >= 0.5 else "LOW", "config": cfg["id"], "n_train": len(tr),
                             "n_train_quarters": int(tr["q"].nunique())})
            rec["forecasts"][f"{target}_lead{k}"] = {
                "config": cfg, "n_train": len(tr), "train_quarters": [E.qs(int(q)) for q in sorted(tr["q"].unique())],
                "features": te[["province_code"] + E.COLUMNS].to_dict("records"),
                "shap": None if sv is None else {pp: dict(zip(E.COLUMNS + ["_base"], map(float, r)))
                                                 for pp, r in zip(te["province_code"], sv)}}
    df = pd.DataFrame(rows)
    f = OUT / "sealed_prospective.csv"
    M.write_csv(f, df)
    (OUT / "sealed_prospective.csv.sha256").write_text(E.sha256(f) + "\n", encoding="utf-8", newline="\n")
    rec["sealed_sha256"] = E.sha256(f)
    rec["sealed_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    E.write_json(OUT / "prospective_record.json", rec)
    print(df.to_string())


if __name__ == "__main__":
    ph = sys.argv[1]
    if ph == "dev":
        phase_predict("dev")
        phase_dev_metrics()
    elif ph == "final":
        assert (OUT / "dev" / "metrics.json").exists()
        phase_predict("final")
        phase_combined()
    elif ph == "diag":
        phase_diag()
    elif ph == "prospective":
        phase_prospective()
    else:
        raise SystemExit(__doc__)
