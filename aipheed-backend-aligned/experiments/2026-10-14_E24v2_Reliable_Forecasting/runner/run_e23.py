"""E23 runner (E23_PROTOCOL.md, frozen; hashes checked first).
Phase 1 predicts every model at every feasible (lead, origin) and SEALS the predictions (SHA-256).
Phase 2 scores the sealed predictions, runs the paired tests, SHAP / permutation importance / ablation,
and applies the predeclared H1-H3 decision rules. Phase 3: leave-one-quarter-out (descriptive).
Usage: python -B runner/run_e23.py [--threshold-mode origin|fixed]  (default: both, origin = primary)"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e23_lib as L  # noqa: E402

EXP = guard.EXP
qk, qs = L.qk, L.qs


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def jd(o):
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if np.isnan(o) else float(o)
    if isinstance(o, float) and np.isnan(o):
        return None
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    raise TypeError(type(o))


def check_frozen():
    for ln in (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").splitlines():
        p = ln.split()
        if len(p) == 2 and len(p[0]) == 64:
            got = sha_bytes((EXP / p[1]).read_bytes())
            if got != p[0]:
                raise SystemExit(f"E23: {p[1]} differs from its frozen hash; stop.")


# ================================================================================ data
def load(log):
    comp = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.E12_RUN / "realized_components_2021_2025.csv")),
                       dtype={"province_code": str})
    det = json.loads(guard.read_allowed_text(guard.E12_RUN / "details.json"))
    rounds = pd.DataFrame(det["two_layer"]["regional_layer_rounds"])
    rounds["published"] = pd.to_datetime(rounds["published"])
    gov = json.loads(guard.read_allowed_text(guard.AL / "config" / "governing_model.json"))
    cand = gov["feature_set"]["candidates_section_3_3_2_6"]
    ff = guard.read_allowed_parquet(guard.PROC / "features_fused.parquet", ["province_code", "quarter"] + cand + ["cpi_dev"])
    cpi26 = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.COLL / "provincial_food_cpi_yoy_2026H1_raw.csv")),
                        dtype={"province_code": str})
    sws26 = guard.read_allowed_parquet(guard.PROD_SWS, ["quarter", "pct_total_hunger", "stratum"])
    for name, col, mx in (("components", comp["quarter"], "2025-Q4"), ("rounds", rounds["quarter"], "2025-Q4"),
                          ("features_fused", ff["quarter"], "2025-Q4"), ("sws_2026", sws26["quarter"], "2026-Q2")):
        bad = int((col.map(qk) > qk(mx)).sum())
        log.append({"assert": f"{name} <= {mx}", "rows": int(len(col)), "violations": bad})
        if bad:
            raise guard.AccessDenied(f"E23: {name} beyond {mx}")
    months = sorted(cpi26["reference_month"].unique())
    if months != [f"2026-0{m}" for m in range(1, 7)] or len(cpi26) != 30:
        raise guard.AccessDenied("E23: CPI 2026 file outside the authorized Jan-Jun range")
    log.append({"assert": "CPI 2026 = 2026-01..2026-06, 30 rows", "ok": True})
    log.append({"assert": "SWS 2026 stratum balance_luzon", "ok": bool((sws26["stratum"] == "balance_luzon").all())})
    gov_cols = [c for c in cand if c not in L.NLP and c != "poverty_incidence"] + ["cpi_dev"]
    # 2026 labels: F = mean of monthly YoY, D = F - five-province mean (all five present), H = production round
    c = cpi26.copy()
    c["quarter"] = c["reference_month"].map(lambda m: f"{m[:4]}-Q{(int(m[5:7]) - 1) // 3 + 1}")
    F = c.groupby(["province_code", "quarter"])["food_cpi_yoy_pct_raw"].mean().reset_index(name="F")
    H = sws26.drop_duplicates("quarter").set_index("quarter")["pct_total_hunger"]
    rows = []
    for q, g in F.groupby("quarter"):
        m5 = g["F"].mean() if (len(g) == 5 and g["F"].notna().all()) else np.nan
        for r in g.itertuples():
            D = r.F - m5
            rows.append({"province_code": r.province_code, "quarter": q, "S1": float(H[q]) + 2 * D})
    S = pd.concat([comp[comp["S1"].notna()][["province_code", "quarter", "S1"]], pd.DataFrame(rows)], ignore_index=True)
    S["tq"] = S["quarter"].map(qk)
    return comp, rounds, ff, gov_cols, S


# ================================================================================ phase 1
def run_predictions(X, S, rounds, gov_cols, mode: str):
    combined = L.NLP + gov_cols + ["sws_hunger"]
    gov_only = gov_cols + ["sws_hunger"]
    pairs = {k: L.pairs_for(X, S, k) for k in L.POOLED_LEADS}
    allpairs = pd.concat(pairs.values(), ignore_index=True)
    preds, meta, keep = [], {}, {}
    tmin, tmax = qk(L.FIRST_Q), qk(L.LAST_FEATURE_Q)
    for k in L.LEADS:
        P = pairs[k]
        for t in range(tmin, tmax + 1):
            te = P[P["t"] == t].sort_values("province_code").reset_index(drop=True)
            if len(te) != 5:
                continue
            tau, n_tau = L.threshold_at(S, rounds, t) if mode == "origin" else (L.FIXED_THRESHOLD, None)
            ok_q = {q: L.label_published(rounds, q, t) for q in allpairs["target_quarter"].unique()}
            pub = allpairs[allpairs["target_quarter"].map(ok_q) & (allpairs["t"] >= tmin)].copy()
            pub["y"] = (pub["S1"] > tau).astype(int)
            tr_s = pub[pub["lead"] == k].copy()
            tr_p = pub.copy()
            if tr_s["target_q"].nunique() < L.MIN_TRAIN_QUARTERS:
                continue
            te = te.assign(y=(te["S1"] > tau).astype(int))
            y = tr_s["y"].to_numpy()
            key = f"k{k}_{qs(t)}"
            m = {"lead": k, "feature_quarter": qs(t), "origin": L.origin_of(t).isoformat(),
                 "target_quarter": te["target_quarter"].iloc[0], "threshold": tau, "threshold_n_labels": n_tau,
                 "n_train_rows": int(len(tr_s)), "n_train_quarters": int(tr_s["target_q"].nunique()),
                 "train_HIGH": int(y.sum()), "train_LOW": int((1 - y).sum()),
                 "n_train_rows_pooled": int(len(tr_p)), "test_HIGH": int(te["y"].sum()), "test_LOW": int((1 - te["y"]).sum()),
                 "max_train_target_quarter": qs(int(tr_s["target_q"].max()))}
            # leakage assertions: every training label published before the origin; no training target >= test target
            assert tr_p["target_q"].max() <= t - 1, key
            assert all(L.label_published(rounds, q, t) for q in tr_p["target_quarter"].unique()), key
            s = {}
            # B1 persistence: latest published label of the province (same threshold)
            last = pub.drop_duplicates(["province_code", "target_quarter"]).sort_values("target_q")
            lastS = last.groupby("province_code")["S1"].last()
            s["B1_naive_persistence"] = te["province_code"].map(lambda p: float(lastS.get(p, np.nan) > tau)).to_numpy(float)
            s["B2_lr_combined"] = L.fit_lr(tr_s, combined, te)
            s["B3_lr_gov_only"] = L.fit_lr(tr_s, gov_only, te)
            s["B4_lr_nlp_only"] = L.fit_lr(tr_s, L.NLP, te)
            s["S_lr_psa_only"] = L.fit_lr(tr_s, L.PSA, te)
            for name, cols in (("B5_lgbm_gov_only", gov_only), ("B6_lgbm_nlp_only", L.NLP), (L.PROPOSED, combined)):
                sel = L.inner_select(tr_s, tr_p, cols, k)
                p, mdl, use = L.lgbm_predict(tr_s, tr_p, cols, sel["config"], te, k)
                s[name] = p
                m[f"selection_{name}"] = sel
                if name == L.PROPOSED:
                    m["proposed_n_splits"] = int(mdl.booster_.trees_to_dataframe()["split_feature"].notna().sum()) if mdl else 0
                    keep[key] = {"model": mdl, "use": use, "te": te, "cfg": sel["config"], "tr_s": tr_s, "tr_p": tr_p,
                                 "combined": combined}
                    if mdl is not None:
                        sh = L.shap_abs(mdl, te, use, k)
                        m["shap_mean_abs"] = sh.abs().mean().to_dict()
                        m["shap_rows"] = sh.assign(province_code=te["province_code"].values).to_dict("records")
                        for drop in ("FSSI", "cpi_dev"):
                            pa, _, _ = L.lgbm_predict(tr_s, tr_p, [c for c in combined if c != drop], sel["config"], te, k)
                            s[f"ABL_no_{drop}"] = pa
            meta[key] = m
            for arm, v in s.items():
                for i, r in te.iterrows():
                    preds.append({"threshold_mode": mode, "lead": k, "feature_quarter": qs(t),
                                  "origin": L.origin_of(t).date().isoformat(), "target_quarter": r["target_quarter"],
                                  "province_code": r["province_code"], "model": arm, "score": float(v[i]),
                                  "y": int(r["y"]), "S1": float(r["S1"]), "threshold": float(tau)})
    return pd.DataFrame(preds), meta, keep


# ================================================================================ phase 2
def score(P: pd.DataFrame, meta: dict, keep: dict, mode: str):
    out = {"by_lead": {}, "mode": mode}
    models = [L.PROPOSED] + L.BASELINES + L.SUPPLEMENTARY
    persist_p = {}
    for k in L.LEADS:
        d = P[(P["lead"] == k) & P["model"].isin(models)]
        if d.empty:
            out["by_lead"][str(k)] = {"evaluable": False, "n_origins": 0, "reason": "no origin with >= 8 training quarters"}
            continue
        prop = d[d["model"] == L.PROPOSED].sort_values(["origin", "province_code"])
        n_orig = prop["origin"].nunique()
        nH, nL = int(prop["y"].sum()), int((1 - prop["y"]).sum())
        ev = n_orig >= L.MIN_ORIGINS and nH >= L.MIN_PER_CLASS and nL >= L.MIN_PER_CLASS
        res = {"n_origins": n_orig, "origins": sorted(prop["origin"].unique().tolist()),
               "target_quarters": sorted(prop["target_quarter"].unique().tolist(), key=qk),
               "test_HIGH": nH, "test_LOW": nL, "evaluable": bool(ev),
               "reason": None if ev else f"needs >= {L.MIN_ORIGINS} origins and >= {L.MIN_PER_CLASS} HIGH and LOW test rows"}
        res["metrics"] = {}
        for mdl in models:
            dm = d[d["model"] == mdl].sort_values(["origin", "province_code"])
            res["metrics"][mdl] = L.cls_metrics(dm["y"], dm["score"])
        # per-origin table
        po = []
        for o, g in d.groupby("origin"):
            row = {"origin": o, "target_quarter": g["target_quarter"].iloc[0], "HIGH": int(g[g["model"] == L.PROPOSED]["y"].sum())}
            for mdl in models:
                gm = g[g["model"] == mdl]
                row[f"brier_{mdl}"] = float(((gm["score"] - gm["y"]) ** 2).mean())
                row[f"acc_{mdl}"] = float(((gm["score"] >= 0.5).astype(int) == gm["y"]).mean())
            po.append(row)
        res["per_origin"] = po
        # paired tests vs each baseline (identical origins and rows by construction)
        tests = {}
        groups = prop["origin"].to_numpy()
        yv = prop["y"].to_numpy()
        sa = prop["score"].to_numpy()
        for b in L.BASELINES + L.SUPPLEMENTARY:
            db = d[d["model"] == b].sort_values(["origin", "province_code"])
            assert (db["province_code"].to_numpy() == prop["province_code"].to_numpy()).all()
            sb = db["score"].to_numpy()
            dO = pd.DataFrame({"o": groups, "d": (sa - yv) ** 2 - (sb - yv) ** 2}).groupby("o")["d"].mean().to_numpy()
            t_b = L.signflip_brier(dO)
            t_a = L.paired_auc_perm(groups, yv, sa, sb) if ev else {"auc_diff": None, "p_one_sided": None,
                                                                    "note": "lead not evaluable"}
            tests[b] = {"brier": t_b, "auc": t_a}
        hb = L.BASELINES
        adj_auc = L.holm({b: tests[b]["auc"].get("p_one_sided") for b in hb})
        adj_brier = L.holm({b: tests[b]["brier"]["p_one_sided"] for b in hb})
        for b in hb:
            tests[b]["auc"]["p_holm"] = adj_auc[b]
            tests[b]["brier"]["p_holm"] = adj_brier[b]
        res["paired_tests"] = tests
        res["proposed_auc_ci"] = L.cluster_boot_auc(groups, yv, sa) if ev else None
        persist_p[k] = tests["B1_naive_persistence"]["brier"]["p_one_sided"] if ev else None
        # leave-one-origin-out influence on the proposed-vs-baseline AUC difference
        if ev:
            infl = {}
            for b in hb:
                sb = d[d["model"] == b].sort_values(["origin", "province_code"])["score"].to_numpy()
                diffs = []
                for o in np.unique(groups):
                    mk = groups != o
                    a1, a2 = L.auc(yv[mk], sa[mk]), L.auc(yv[mk], sb[mk])
                    if a1 is not None and a2 is not None:
                        diffs.append(a1 - a2)
                infl[b] = {"min_diff": float(min(diffs)) if diffs else None, "max_diff": float(max(diffs)) if diffs else None,
                           "sign_changes": bool(diffs and min(diffs) < 0 < max(diffs))}
            res["leave_one_origin_out_auc_diff"] = infl
        out["by_lead"][str(k)] = res
    # reliability rule (Holm across evaluable leads on the persistence Brier test)
    adj = L.holm({str(k): p for k, p in persist_p.items()})
    rel = {}
    for k in L.LEADS:
        r = out["by_lead"][str(k)]
        if not r.get("evaluable"):
            rel[str(k)] = {"evaluable": False, "reliable": False}
            continue
        ci = r["proposed_auc_ci"] or {}
        c1 = ci.get("ci_low") is not None and ci["ci_low"] > 0.5
        c2 = adj.get(str(k)) is not None and adj[str(k)] < 0.05
        rel[str(k)] = {"evaluable": True, "auc_ci_low_gt_0.5": bool(c1), "brier_better_than_persistence_holm_p": adj.get(str(k)),
                       "brier_beats_persistence": bool(c2), "reliable": bool(c1 and c2)}
    out["reliability"] = rel
    rel_leads = [int(k) for k, v in rel.items() if v["reliable"]]
    out["max_reliable_lead"] = max(rel_leads) if rel_leads else None
    ev_leads = [int(k) for k, v in rel.items() if v["evaluable"]]
    out["evaluable_leads"] = ev_leads
    # hypothesis decisions
    out["hypotheses"] = decide(out, meta, keep, P)
    return out


def perm_importance(keep: dict, k: int, feats: list[str]) -> dict:
    items = [(key, v) for key, v in keep.items() if key.startswith(f"k{k}_") and v["model"] is not None]
    if not items:
        return {}
    te_all = pd.concat([v["te"].assign(_key=key) for key, v in items], ignore_index=True)
    rng = np.random.default_rng(L.SEED)

    def predict(df):
        out = np.empty(len(df))
        for key, v in items:
            mk = (df["_key"] == key).to_numpy()
            out[mk] = v["model"].predict_proba(df.loc[mk].assign(lead=k)[v["use"]])[:, 1]
        return out
    base = predict(te_all)
    y = te_all["y"].to_numpy()
    res = {}
    for f in feats:
        if f not in te_all.columns:
            continue
        d_rep = np.zeros((L.PERM_REPEATS, len(items)))
        for r in range(L.PERM_REPEATS):
            pdf = te_all.copy()
            pdf[f] = rng.permutation(pdf[f].to_numpy())
            pp = predict(pdf)
            per = pd.DataFrame({"k": te_all["_key"], "d": (pp - y) ** 2 - (base - y) ** 2}).groupby("k")["d"].mean()
            d_rep[r] = per.reindex([key for key, _ in items]).to_numpy()
        d_orig = d_rep.mean(0)
        boot = rng.integers(0, len(d_orig), size=(L.N_BOOT, len(d_orig)))
        bm = d_orig[boot].mean(1)
        res[f] = {"delta_brier_mean": float(d_orig.mean()), "ci_low": float(np.quantile(bm, 0.025)),
                  "ci_high": float(np.quantile(bm, 0.975))}
    return res


def decide(out, meta, keep, P) -> dict:
    H = {}
    ev = out["evaluable_leads"]
    # H2
    nrel = sum(1 for v in out["reliability"].values() if v["reliable"])
    if len(ev) < 2:
        H["H2"] = {"decision": "not testable", "why": f"{len(ev)} evaluable lead(s); the rule needs >= 2"}
    else:
        H["H2"] = {"decision": "rejected" if nrel >= 2 else "not rejected",
                   "why": f"{nrel} reliable lead(s) among {len(ev)} evaluable"}
    kp = 1 if 1 in ev else (min(ev) if ev else None)
    H["primary_lead_for_H1_H3"] = kp
    if kp is None:
        H["H3"] = {"decision": "not testable", "why": "no evaluable lead"}
        H["H1"] = {"decision": "not testable", "why": "no evaluable lead"}
    else:
        r = out["by_lead"][str(kp)]
        per = {}
        for b in L.BASELINES:
            t = r["paired_tests"][b]
            ok = (t["auc"]["p_holm"] is not None and t["auc"]["p_holm"] < 0.05 and t["brier"]["mean_diff"] < 0)
            per[b] = {"auc_diff": t["auc"]["auc_diff"], "p_holm_auc": t["auc"]["p_holm"],
                      "brier_diff": t["brier"]["mean_diff"], "significantly_better": bool(ok)}
        H["H3"] = {"decision": "rejected" if all(v["significantly_better"] for v in per.values()) else "not rejected",
                   "lead": kp, "per_baseline": per}
        # H1
        shap_rows = [m for key, m in meta.items() if key.startswith(f"k{kp}_") and "shap_mean_abs" in m]
        tot = {}
        for m in shap_rows:
            for f, v in m["shap_mean_abs"].items():
                tot.setdefault(f, []).append(v)
        mean_abs = {f: float(np.mean(v)) for f, v in tot.items() if f != "lead"}
        rank = sorted(mean_abs, key=lambda f: -mean_abs[f])
        stab = {}
        for f in ("FSSI", "cpi_dev"):
            inside = [f in sorted({g: v for g, v in m["shap_mean_abs"].items() if g != "lead"},
                                  key=lambda g: -m["shap_mean_abs"][g])[:L.TOP_K_STRONGEST] for m in shap_rows]
            stab[f] = float(np.mean(inside)) if inside else 0.0
        pim = perm_importance(keep, kp, ["FSSI", "cpi_dev"] + rank[:10])
        conds = {f: {"rank": (rank.index(f) + 1) if f in rank else None,
                     "top5_pooled": f in rank[:L.TOP_K_STRONGEST], "top5_share_of_origins": stab.get(f),
                     "perm_delta_brier": pim.get(f, {}).get("delta_brier_mean"),
                     "perm_ci_low": pim.get(f, {}).get("ci_low")} for f in ("FSSI", "cpi_dev")}
        okf = {f: bool(c["top5_pooled"] and (c["top5_share_of_origins"] or 0) >= 0.5 and
                       c["perm_ci_low"] is not None and c["perm_ci_low"] > 0) for f, c in conds.items()}
        pm = out["by_lead"][str(kp)]["metrics"]
        abl = {}
        for f in ("FSSI", "cpi_dev"):
            dd = P[(P["lead"] == kp) & (P["model"] == f"ABL_no_{f}")]
            if len(dd):
                abl[f] = {"brier_without": float(((dd["score"] - dd["y"]) ** 2).mean()),
                          "brier_with": pm[L.PROPOSED]["Brier"], "auc_without": L.auc(dd["y"], dd["score"]),
                          "auc_with": pm[L.PROPOSED]["ROC_AUC"]}
        H["H1"] = {"decision": "rejected" if all(okf.values()) else "not rejected", "lead": kp,
                   "conditions": conds, "shap_rank_top10": [(f, mean_abs[f]) for f in rank[:10]],
                   "n_features_ranked": len(rank), "permutation_importance": pim, "drop_column_ablation": abl}
    H["H4"] = {"decision": "awaiting participant data", "why": "requires DA Region IV-A evaluator responses"}
    H["H5"] = {"decision": "awaiting participant data", "why": "requires DA Region IV-A evaluator responses"}
    return H


# ================================================================================ phase 3
def loqo(X, S):
    """Leave-one-quarter-out, lead 1, global median threshold. NON-CHRONOLOGICAL; descriptive only."""
    P = L.pairs_for(X, S, 1)
    tau = float(S["S1"].median())
    P["y"] = (P["S1"] > tau).astype(int)
    rows = []
    for q in sorted(P["target_quarter"].unique(), key=qk):
        te = P[P["target_quarter"] == q].sort_values("province_code")
        tr = P[P["target_quarter"] != q]
        if tr["y"].nunique() < 2:
            continue
        rows.append((q, te, tr))
    return tau, rows


def main():
    check_frozen()
    runid = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rd = EXP / "runs" / runid
    rd.mkdir(parents=True)
    log = []
    allow = guard.verify_allowlist()
    comp, rounds, ff, gov_cols, S = load(log)
    X = L.build_frame(ff, rounds, gov_cols)
    combined = L.NLP + gov_cols + ["sws_hunger"]
    results, all_preds, all_meta = {}, [], {}
    for mode in ("origin", "fixed"):
        P, meta, keep = run_predictions(X, S, rounds, gov_cols, mode)
        all_preds.append(P)
        all_meta[mode] = meta
        # SEAL before scoring
        b = P.to_csv(index=False, lineterminator="\n").encode("utf-8")
        (rd / f"predictions_{mode}.csv").write_bytes(b)
        seal = {"file": f"predictions_{mode}.csv", "sha256": sha_bytes(b), "rows": int(len(P)),
                "sealed_utc": datetime.now(timezone.utc).isoformat()}
        (rd / f"SEAL_{mode}.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
        # re-read the sealed file and verify before scoring
        Pr = pd.read_csv(rd / f"predictions_{mode}.csv", dtype={"province_code": str})
        assert sha_bytes((rd / f"predictions_{mode}.csv").read_bytes()) == seal["sha256"]
        results[mode] = score(Pr, meta, keep, mode)
        # 2026-target exclusion sensitivity (primary mode only)
        if mode == "origin":
            P25 = Pr[Pr["target_quarter"].map(qk) <= qk("2025-Q4")]
            results["origin_excluding_2026_targets"] = score(P25, meta, keep, "origin_excl_2026")
    # LOQO descriptive
    tau, folds = loqo(X, S)
    lq = []
    for q, te, tr in folds:
        r = {"target_quarter": q, "HIGH": int(te["y"].sum()), "LOW": int((1 - te["y"]).sum())}
        p, _, _ = L.lgbm_predict(tr, tr, combined, L.GRID[0], te, 1)
        r["proposed_scores"] = p.tolist()
        r["lr_combined_scores"] = L.fit_lr(tr, combined, te).tolist()
        r["y"] = te["y"].tolist()
        lq.append(r)
    yy = np.concatenate([r["y"] for r in lq])
    loqo_out = {"threshold_global_median": tau, "note": "non-chronological, descriptive only (uses future quarters)",
                "auc_proposed": L.auc(yy, np.concatenate([r["proposed_scores"] for r in lq])),
                "auc_lr_combined": L.auc(yy, np.concatenate([r["lr_combined_scores"] for r in lq])),
                "folds": lq}
    # data audit facts used by the reports
    audit = {
        "constant_columns_2021_2025": [c for c in combined if X[c].dropna().nunique() <= 1],
        "all_zero_columns": [c for c in combined if X[c].notna().any() and (X[c].fillna(0) == 0).all()],
        "missing_share": {c: float(X[c].isna().mean()) for c in combined if X[c].isna().any()},
        "sws_shared_across_provinces": True,
        "label_variance_shared_across_provinces": float(
            S.groupby("quarter")["S1"].transform("mean").var() / S["S1"].var()),
        "labelled_quarters": sorted(S["quarter"].unique().tolist(), key=qk),
        "n_feature_columns": len(combined),
    }
    for mode, m in all_meta.items():
        (rd / f"fold_meta_{mode}.json").write_text(json.dumps(m, default=jd, indent=1), encoding="utf-8")
    (rd / "results.json").write_text(json.dumps(results, default=jd, indent=1), encoding="utf-8")
    (rd / "loqo.json").write_text(json.dumps(loqo_out, default=jd, indent=1), encoding="utf-8")
    (rd / "data_audit.json").write_text(json.dumps(audit, default=jd, indent=1), encoding="utf-8")
    man = {"run_id": runid, "allowlist_verification": allow, "integrity_log": log, "access_log": guard.ACCESS_LOG,
           "protocol_hashes": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8"),
           "outputs": {p.name: sha_bytes(p.read_bytes()) for p in sorted(rd.iterdir()) if p.is_file()}}
    (rd / "manifest.json").write_text(json.dumps(man, default=jd, indent=1), encoding="utf-8")
    print(runid)
    for mode in ("origin", "fixed"):
        r = results[mode]
        print(mode, "evaluable", r["evaluable_leads"], "MRL", r["max_reliable_lead"],
              {h: v["decision"] for h, v in r["hypotheses"].items() if h.startswith("H")})


if __name__ == "__main__":
    main()
