"""E13 runner. Implements EXPERIMENT_PROTOCOL.md (frozen; hash checked first).

Usage: python -B runner/run_e13.py [--deliverables]
  --deliverables  also write BASELINE_COMPARISON.csv and MODEL_COMPARISON.csv to the experiment root
                  (refuses to overwrite). Without it, outputs go only to runs/<utc>/ (replicate run).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "21")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e13_lib as L  # noqa: E402
import loaders  # noqa: E402

EXP = guard.EXP
PROTOCOL = EXP / "EXPERIMENT_PROTOCOL.md"
FROZEN = (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[0]
TAU0 = 10.84335
TAU_PROSPECTIVE = 14.345
E9_TEST_QUARTERS = ["2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q4"]

ARMS = {
    "A": [("A_cf", "baseline", "H_last (latest published regional hunger; S1 origin-rule regional term)"),
          ("A_mean", "baseline", "mean of fully published quarterly H since 2021-Q2"),
          ("A_ridge_H", "model", "ridge(H_last)"),
          ("A_ridge_HF", "model", "ridge(H_last, F5_lag2)")],
    "B1": [("B1_cf", "baseline", "F[p,T-2]"),
           ("B1_regional", "baseline", "five-province mean F of T-2 (regional only)"),
           ("B1_mean", "baseline", "pooled training mean of F"),
           ("B1_pmean", "baseline", "province historical mean of F, 2021-Q1..T-2"),
           ("B1_ridge_F", "model", "ridge(F_lag2)"),
           ("B1_ridge_FR", "model", "ridge(F_lag2, F5_lag2)"),
           ("B1_tree", "model", "tree depth 2 (F_lag2, F5_lag2)")],
    "B2": [("B2_zero", "baseline", "0 (no provincial difference; regional only)"),
           ("B2_cf", "baseline", "D[p,T-2] (S1 origin-rule provincial term)"),
           ("B2_pmean", "baseline", "province historical mean of D, 2021-Q1..T-2"),
           ("B2_ridge_D", "model", "ridge(D_lag2)"),
           ("B2_ridge_DP", "model", "ridge(D_lag2, Dbar_p)"),
           ("B2_tree", "model", "tree depth 2 (D_lag2, Dbar_p)")],
}
ARM_TYPE = {a: t for v in ARMS.values() for a, t, _ in v}
ARM_DESC = {a: d for v in ARMS.values() for a, _, d in v}


def jdefault(o):
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, (pd.Timestamp,)):
        return o.isoformat()
    raise TypeError(type(o))


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_path(p: Path) -> str:
    return sha_bytes(p.read_bytes())


# ======================================================================= forecasts
def forecast_A(rounds: pd.DataFrame, comp: pd.DataFrame, Ts: list[str] | None = None):
    qv = L.quarter_values(rounds)
    cand = qv["quarter"].tolist() if Ts is None else Ts
    rows, skipped, coefs = [], {}, {}
    for T in cand:
        tr = L.a_training(rounds, comp, T)
        if len(tr) < L.MIN_TRAIN_QUARTERS:
            skipped[T] = f"{len(tr)} training quarters (< {L.MIN_TRAIN_QUARTERS})"
            continue
        fe = L.a_features(rounds, comp, T)
        base = {"target": "A", "quarter": T, "province_code": "REGION", "province": "Balance Luzon (regional)",
                "n_train_quarters": int(len(tr)), "H_last": fe["H_last"], "H_last_quarter": fe["H_last_quarter"],
                "H_age": fe["H_age_quarters"], "F5_lag2": fe["F5_lag2"]}
        insufficient = fe["H_last"] is None or fe["H_age_quarters"] > 4 or fe["F5_lag2"] is None
        fc = {}
        if not insufficient:
            fc["A_cf"] = fe["H_last"]
            fc["A_mean"] = L.a_published_mean(rounds, T)
            p, c1 = L.ridge_fit_predict(tr[["H_last"]].to_numpy(float), tr["y"].to_numpy(float),
                                        np.array([[fe["H_last"]]]))
            fc["A_ridge_H"] = float(p[0])
            p, c2 = L.ridge_fit_predict(tr[["H_last", "F5_lag2"]].to_numpy(float), tr["y"].to_numpy(float),
                                        np.array([[fe["H_last"], fe["F5_lag2"]]]))
            fc["A_ridge_HF"] = float(p[0])
            coefs[T] = {"A_ridge_H": c1, "A_ridge_HF": c2, "train_quarters": tr["quarter"].tolist()}
        for arm, _, _ in ARMS["A"]:
            rows.append({**base, "arm": arm, "arm_type": ARM_TYPE[arm],
                         "forecast": fc.get(arm, np.nan), "status": "INSUFFICIENT_DATA" if insufficient else "OK"})
    return pd.DataFrame(rows), skipped, coefs


def forecast_B(comp: pd.DataFrame, Ts: list[str] | None = None):
    allq = sorted(comp["quarter"].unique(), key=L.qi)
    cand = [q for q in allq if L.qi(q) >= L.qi("2021-Q3")] if Ts is None else Ts
    rows, skipped, coefs = [], {}, {}
    for T in cand:
        tr = L.b_training(comp, T)
        ntq = int(tr["quarter"].nunique()) if len(tr) else 0
        if ntq < L.MIN_TRAIN_QUARTERS:
            skipped[T] = f"{ntq} training quarters (< {L.MIN_TRAIN_QUARTERS})"
            continue
        fe = L.b_features(comp, T)
        trF = tr.dropna(subset=["F_lag2", "F5_lag2", "F"])
        trD = tr.dropna(subset=["D_lag2", "Dbar_p", "D"])
        okF = fe["F_lag2"].notna() & fe["F5_lag2"].notna()
        okD = bool(fe["complete_five_lag2"].all())
        fcF = {"B1_cf": fe["F_lag2"].to_numpy(float), "B1_regional": fe["F5_lag2"].to_numpy(float),
               "B1_mean": np.full(5, trF["F"].mean()), "B1_pmean": fe["Fbar_p"].to_numpy(float)}
        Xte = fe[["F_lag2", "F5_lag2"]].fillna(0).to_numpy(float)   # rows with missing inputs are masked below
        fcF["B1_ridge_F"], c1 = L.ridge_fit_predict(trF[["F_lag2"]].to_numpy(float), trF["F"].to_numpy(float), Xte[:, :1])
        fcF["B1_ridge_FR"], c2 = L.ridge_fit_predict(trF[["F_lag2", "F5_lag2"]].to_numpy(float), trF["F"].to_numpy(float), Xte)
        fcF["B1_tree"], c3 = L.tree_fit_predict(trF[["F_lag2", "F5_lag2"]].to_numpy(float), trF["F"].to_numpy(float), Xte)
        XteD = fe[["D_lag2", "Dbar_p"]].fillna(0).to_numpy(float)
        fcD = {"B2_zero": np.zeros(5), "B2_cf": fe["D_lag2"].to_numpy(float), "B2_pmean": fe["Dbar_p"].to_numpy(float)}
        fcD["B2_ridge_D"], d1 = L.ridge_fit_predict(trD[["D_lag2"]].to_numpy(float), trD["D"].to_numpy(float), XteD[:, :1])
        fcD["B2_ridge_DP"], d2 = L.ridge_fit_predict(trD[["D_lag2", "Dbar_p"]].to_numpy(float), trD["D"].to_numpy(float), XteD)
        fcD["B2_tree"], d3 = L.tree_fit_predict(trD[["D_lag2", "Dbar_p"]].to_numpy(float), trD["D"].to_numpy(float), XteD)
        coefs[T] = {"B1_ridge_F": c1, "B1_ridge_FR": c2, "B1_tree": c3, "B2_ridge_D": d1, "B2_ridge_DP": d2,
                    "B2_tree": d3, "train_quarters": sorted(tr["quarter"].unique().tolist(), key=L.qi),
                    "n_train_rows_F": int(len(trF)), "n_train_rows_D": int(len(trD))}
        for i, r in fe.reset_index(drop=True).iterrows():
            base = {"quarter": T, "province_code": r["province_code"], "province": L.PROVINCES[r["province_code"]],
                    "n_train_quarters": ntq, "F_lag2": r["F_lag2"], "D_lag2": r["D_lag2"], "F5_lag2": r["F5_lag2"],
                    "Fbar_p": r["Fbar_p"], "Dbar_p": r["Dbar_p"]}
            for arm, _, _ in ARMS["B1"]:
                ok = bool(okF.iloc[i])
                rows.append({**base, "target": "B1", "arm": arm, "arm_type": ARM_TYPE[arm],
                             "forecast": float(fcF[arm][i]) if ok else np.nan,
                             "status": "OK" if ok else "INSUFFICIENT_DATA"})
            for arm, _, _ in ARMS["B2"]:
                rows.append({**base, "target": "B2", "arm": arm, "arm_type": ARM_TYPE[arm],
                             "forecast": float(fcD[arm][i]) if okD else np.nan,
                             "status": "OK" if okD else "INSUFFICIENT_DATA"})
    return pd.DataFrame(rows), skipped, coefs


def perturbation_check(rounds, comp, predA, predB) -> dict:
    """For each test quarter, overwrite everything not available at origin(T) with 999 and confirm
    every forecast for T is unchanged."""
    out = {"A": {}, "B": {}}
    for T in sorted(predA["quarter"].unique(), key=L.qi):
        r2 = rounds.copy()
        r2.loc[r2["published"] >= L.origin(T), "H"] = 999.0
        c2 = comp.copy()
        c2.loc[c2["quarter"].map(L.qi) >= L.qi(T) - 1, ["F", "mean5", "D", "H", "S1"]] = 999.0
        p2, _, _ = forecast_A(r2, c2, [T])
        a = predA[predA["quarter"] == T]["forecast"].to_numpy()
        b = p2["forecast"].to_numpy()
        out["A"][T] = bool(np.array_equal(a, b, equal_nan=True))
    for T in sorted(predB["quarter"].unique(), key=L.qi):
        c2 = comp.copy()
        c2.loc[c2["quarter"].map(L.qi) >= L.qi(T) - 1, ["F", "mean5", "D", "H", "S1"]] = 999.0
        p2, _, _ = forecast_B(c2, [T])
        a = predB[predB["quarter"] == T]["forecast"].to_numpy()
        b = p2["forecast"].to_numpy()
        out["B"][T] = bool(np.array_equal(a, b, equal_nan=True))
    if not all(out["A"].values()) or not all(out["B"].values()):
        raise RuntimeError(f"E13: future-perturbation check failed: {out}")
    return out


# ======================================================================= evaluation
def event_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    tA, tB1, tB2 = df["target"] == "A", df["target"] == "B1", df["target"] == "B2"
    df["event_y"] = np.nan
    df["event_pred"] = np.nan
    df["event_score"] = np.nan
    df.loc[tA, "event_y"] = (df.loc[tA, "y"] > df.loc[tA, "H_last"]).astype(float)
    df.loc[tA, "event_pred"] = (df.loc[tA, "forecast"] > df.loc[tA, "H_last"]).astype(float)
    df.loc[tA, "event_score"] = df.loc[tA, "forecast"] - df.loc[tA, "H_last"]
    df.loc[tB1, "event_y"] = (df.loc[tB1, "y"] > L.F_EVENT_THRESHOLD).astype(float)
    df.loc[tB1, "event_pred"] = (df.loc[tB1, "forecast"] > L.F_EVENT_THRESHOLD).astype(float)
    df.loc[tB1, "event_score"] = df.loc[tB1, "forecast"]
    df.loc[tB2, "event_y"] = (df.loc[tB2, "y"] > 0).astype(float)
    df.loc[tB2, "event_pred"] = (df.loc[tB2, "forecast"] > 0).astype(float)
    df.loc[tB2, "event_score"] = df.loc[tB2, "forecast"]
    return df


def mean_kendall(d: pd.DataFrame) -> tuple[float | None, int]:
    taus = []
    for _, g in d.groupby("quarter"):
        t = L.kendall_tau(g["forecast"], g["y"])
        if t is not None:
            taus.append(t)
    return (float(np.mean(taus)) if taus else None), len(taus)


def evaluate(scored: pd.DataFrame, target: str, analysis: str, quarters: list[str] | None = None) -> dict:
    d = scored[(scored["target"] == target) & (scored["analysis"] == analysis) & (scored["status"] == "OK")]
    if quarters is not None:
        d = d[d["quarter"].isin(quarters)]
    arms = [a for a, _, _ in ARMS[target]]
    res = {"target": target, "analysis": analysis, "quarters": sorted(d["quarter"].unique().tolist(), key=L.qi),
           "insufficient_rows": int(((scored["target"] == target) & (scored["analysis"] == analysis)
                                     & (scored["status"] != "OK")).sum() // len(arms)),
           "arms": {}}
    wide = d.pivot_table(index=["quarter", "province_code"], columns="arm", values="forecast").reset_index()
    yv = d.drop_duplicates(["quarter", "province_code"]).set_index(["quarter", "province_code"])["y"]
    wide["y"] = [yv[(q, p)] for q, p in zip(wide["quarter"], wide["province_code"])]
    for a in arms:
        da = d[d["arm"] == a]
        m = L.point_metrics(da["y"], da["forecast"])
        m["n_quarters"] = int(da["quarter"].nunique())
        if target != "A":
            m["mean_kendall_tau"], m["kendall_quarters"] = mean_kendall(da)
        ev = L.classification(da["event_y"].astype(bool), da["event_pred"].astype(bool))
        ev.update(L.auc_scores(da["event_y"].astype(bool), da["event_score"]))
        m["event"] = ev
        m["per_quarter_MAE"] = da.assign(ae=(da["forecast"] - da["y"]).abs()).groupby("quarter")["ae"].mean().to_dict()
        if target != "A":
            m["per_province_MAE"] = da.assign(ae=(da["forecast"] - da["y"]).abs()).groupby("province")["ae"].mean().to_dict()
        res["arms"][a] = m
    bases = [a for a in arms if ARM_TYPE[a] == "baseline"]
    models = [a for a in arms if ARM_TYPE[a] == "model"]
    best = min(bases, key=lambda a: res["arms"][a]["MAE"])
    res["best_baseline"] = best
    # comparisons vs every baseline (bootstrap) and the four-condition rule vs the best baseline
    comps, pv = {}, {}
    for mdl in models:
        c = {}
        for b in bases:
            c[b] = L.cluster_bootstrap_mae_diff(wide[["quarter", "y", mdl, b]], mdl, b)
        pq = wide.assign(dm=(wide[mdl] - wide["y"]).abs() - (wide[best] - wide["y"]).abs()).groupby("quarter")["dm"].mean()
        pv[mdl] = L.sign_flip_p(pq.to_numpy())
        loqo = []
        for q in res["quarters"]:
            w = wide[wide["quarter"] != q]
            loqo.append(bool((w[mdl] - w["y"]).abs().mean() < (w[best] - w["y"]).abs().mean()))
        comps[mdl] = {"vs": c, "per_quarter_diff_vs_best": pq.to_dict(), "loqo_better": loqo,
                      "quarters_better_than_best": int((pq < 0).sum()), "quarters_total": int(len(pq))}
    ph = L.holm(pv) if pv else {}
    for mdl in models:
        cm = comps[mdl]
        cond1 = all(res["arms"][mdl]["MAE"] < res["arms"][b]["MAE"] for b in bases)
        cond2 = cm["vs"][best]["ci_high"] < 0
        cond3 = ph[mdl] < 0.05
        cond4 = all(cm["loqo_better"])
        cm.update({"p_signflip_vs_best": pv[mdl], "p_holm": ph[mdl], "cond1_lower_than_all_baselines": cond1,
                   "cond2_ci_below_zero": cond2, "cond3_holm_p_below_0_05": cond3, "cond4_loqo_all": cond4,
                   "improvement_established": bool(cond1 and cond2 and cond3 and cond4)})
    res["comparisons"] = comps
    return res


def diagnosis(comp: pd.DataFrame) -> dict:
    lab = comp[comp["S1"].notna()].copy()
    lab["year"] = lab["quarter"].str[:4]
    lab["HIGH"] = lab["S1"] > TAU0
    lab["H_only_HIGH"] = lab["H"] > TAU0
    lab["test_period"] = lab["quarter"].isin(E9_TEST_QUARTERS)
    out = {"tau0": TAU0, "rows": int(len(lab)),
           "HIGH_share_by_year": lab.groupby("year")["HIGH"].agg(["sum", "size"]).astype(int).to_dict("index"),
           "HIGH_test_period": [int(lab.loc[lab["test_period"], "HIGH"].sum()), int(lab["test_period"].sum())],
           "agreement_with_H_only_call_all": float((lab["HIGH"] == lab["H_only_HIGH"]).mean()),
           "agreement_with_H_only_call_test": float((lab.loc[lab["test_period"], "HIGH"]
                                                     == lab.loc[lab["test_period"], "H_only_HIGH"]).mean())}
    per_q = []
    for q, g in lab.groupby("quarter"):
        h = float(g["H"].iloc[0])
        per_q.append({"quarter": q, "H": h, "H_minus_tau0": h - TAU0, "D_needed_for_LOW_below": (TAU0 - h) / 2,
                      "D_min": float(g["D"].min()), "D_max": float(g["D"].max()),
                      "provinces_LOW": g.loc[~g["HIGH"], "province"].tolist(), "n_HIGH": int(g["HIGH"].sum()),
                      "H_only_call": "HIGH" if h > TAU0 else "LOW"})
    out["per_quarter"] = sorted(per_q, key=lambda r: L.qi(r["quarter"]))
    reg = (lab["H"] - TAU0).abs()
    prov = (2 * lab["D"]).abs()
    out["mean_abs_regional_term"] = float(reg.mean())
    out["mean_abs_provincial_term"] = float(prov.mean())
    out["rows_regional_term_larger"] = float((reg > prov).mean())
    tp = lab["test_period"]
    out["test_mean_abs_regional_term"] = float(reg[tp].mean())
    out["test_mean_abs_provincial_term"] = float(prov[tp].mean())
    out["tau0_period_H"] = {"median_H_2021Q2_2023Q2": float(lab[lab["quarter"].map(L.qi) <= L.qi("2023-Q2")]
                                                            .drop_duplicates("quarter")["H"].median()),
                            "median_H_test_period": float(lab[tp].drop_duplicates("quarter")["H"].median())}
    out["informational_prospective_tau"] = {"tau": TAU_PROSPECTIVE,
                                            "HIGH_all": int((lab["S1"] > TAU_PROSPECTIVE).sum()),
                                            "HIGH_test_period": int((lab.loc[tp, "S1"] > TAU_PROSPECTIVE).sum()),
                                            "note": "information only; not evaluated or selected"}
    return out


def external(comp: pd.DataFrame, rounds: pd.DataFrame, ext: dict) -> dict:
    c = comp.copy()
    c["year"] = c["quarter"].str[:4].astype(int)
    ann = c.groupby(["year", "province_code", "province"])[["F", "D"]].mean().reset_index()
    sub = ext["subsistence"]
    subp = sub[sub["geographic_level"] == "province"].rename(columns={"psgc_code": "province_code"})
    j = ann.merge(subp[["year", "province_code", "subsistence_pct", "subsistence_cv", "subsistence_ci_low",
                        "subsistence_ci_high", "usable_for_validation"]], on=["year", "province_code"], how="inner")
    lg = ext["lgu_poverty"]
    lgmed = lg.groupby("province_code")["poverty_incidence_pct"].median()
    fallback = lg["source_note"].str.contains("fallback", case=False, na=False)
    out = {"C1_rows": j.sort_values(["year", "province"]).to_dict("records"), "C1_spearman": {}}
    for y, g in j.groupby("year"):
        out["C1_spearman"][int(y)] = {"meanF_vs_subsistence": L.spearman(g["F"], g["subsistence_pct"]),
                                      "meanD_vs_subsistence": L.spearman(g["D"], g["subsistence_pct"]),
                                      "n": int(len(g))}
    a21 = ann[ann["year"] == 2021].set_index("province_code")
    out["C1_lgu_poverty_2021"] = {
        "median_by_province": {L.PROVINCES[k]: float(v) for k, v in lgmed.items()},
        "spearman_meanD2021_vs_poverty_median": L.spearman(a21["D"].reindex(lgmed.index), lgmed),
        "spearman_meanF2021_vs_poverty_median": L.spearman(a21["F"].reindex(lgmed.index), lgmed),
        "rows": int(len(lg)), "rows_province_fallback": int(fallback.sum()),
        "rows_lgu_specific": int((~fallback).sum())}
    f = ext["fies"]
    r25 = rounds[rounds["quarter"].str.startswith("2025")]
    out["C2"] = {"fies_2025_regional_moderate_severe_pct": float(f["fies_moderate_severe_pct"].iloc[0]),
                 "fies_distinct_values_across_5_rows": int(f["fies_moderate_severe_pct"].nunique()),
                 "fies_geographic_level": f["geographic_level"].unique().tolist(),
                 "sws_2025_rounds": r25[["quarter", "round", "H", "published", "definition_A"]]
                 .assign(published=lambda x: x["published"].dt.strftime("%Y-%m-%d")).to_dict("records"),
                 "sws_2025_mean_all_rounds": float(r25["H"].mean()),
                 "sws_2025_mean_definition_A": float(r25.loc[r25["definition_A"], "H"].mean())}
    return out


def write_csv(df: pd.DataFrame, p: Path, new_only: bool = False):
    if new_only and p.exists():
        raise FileExistsError(p)
    df.to_csv(p, index=False, lineterminator="\n", float_format="%.10g")


def main(deliverables: bool):
    if sha_path(PROTOCOL) != FROZEN:
        raise SystemExit("E13: EXPERIMENT_PROTOCOL.md differs from the frozen hash; stop.")
    started = datetime.now(timezone.utc)
    ts = started.strftime("%Y%m%dT%H%M%SZ")
    out = EXP / "runs" / ts
    out.mkdir(parents=True)
    allow_start = guard.verify_allowlist()

    comp = loaders.load_components()
    det = loaders.load_details()
    rounds = loaders.load_rounds(det)
    ext = loaders.load_external()
    if abs(det["tau0_recorded"] - TAU0) > 1e-12:
        raise SystemExit("E13: tau0 mismatch")

    # ---------------------------------------------------------------- forecasts only
    pA, skA, coA = forecast_A(rounds, comp)
    pA["analysis"] = "primary"
    rA = rounds[rounds["definition_A"]].reset_index(drop=True)
    pAs, skAs, coAs = forecast_A(rA, comp)
    pAs["analysis"] = "S-A1_definition_A_only"
    pB, skB, coB = forecast_B(comp)
    pB["analysis"] = "primary"
    pert = {"primary_A_B": perturbation_check(rounds, comp, pA, pB),
            "S-A1": perturbation_check(rA, comp, pAs, pB)["A"]}
    preds = pd.concat([pA, pAs, pB], ignore_index=True)
    cols = ["target", "analysis", "quarter", "province_code", "province", "arm", "arm_type", "status", "forecast",
            "n_train_quarters", "H_last", "H_last_quarter", "H_age", "F5_lag2", "F_lag2", "D_lag2", "Fbar_p", "Dbar_p"]
    preds = preds[cols].sort_values(["target", "analysis", "quarter", "province_code", "arm"],
                                    key=lambda s: s.map(L.qi) if s.name == "quarter" else s).reset_index(drop=True)
    write_csv(preds, out / "predictions.csv")
    seal = {"predictions_sha256": sha_path(out / "predictions.csv"), "sealed_utc": datetime.now(timezone.utc).isoformat(),
            "protocol_sha256": FROZEN, "rows": int(len(preds)),
            "note": "Sealed before realized values were joined. All 2021-2025 values were seen in E1-E12, "
                    "so the seal documents the order of operations only."}
    (out / "SEAL.json").write_text(json.dumps(seal, indent=1), encoding="utf-8")

    # ---------------------------------------------------------------- realized values joined after the seal
    qvA = L.quarter_values(rounds).set_index("quarter")["H"]
    qvAs = L.quarter_values(rA).set_index("quarter")["H"]
    cy = comp.set_index(["quarter", "province_code"])
    y = []
    for r in preds.itertuples():
        if r.target == "A":
            y.append((qvA if r.analysis == "primary" else qvAs).get(r.quarter, np.nan))
        elif r.target == "B1":
            y.append(cy.loc[(r.quarter, r.province_code), "F"])
        else:
            y.append(cy.loc[(r.quarter, r.province_code), "D"])
    scored = preds.copy()
    scored["y"] = y
    scored["error"] = scored["forecast"] - scored["y"]
    scored = event_columns(scored)
    write_csv(scored, out / "scored_rows.csv")

    results = {}
    for tgt, an in [("A", "primary"), ("A", "S-A1_definition_A_only"), ("B1", "primary"), ("B2", "primary")]:
        results[f"{tgt}|{an}"] = evaluate(scored, tgt, an)
    for tgt in ["B1", "B2"]:
        results[f"{tgt}|S-B1_E9_test_quarters"] = evaluate(scored.assign(
            analysis=np.where(scored["target"] == tgt, "S-B1_E9_test_quarters", scored["analysis"])),
            tgt, "S-B1_E9_test_quarters", quarters=E9_TEST_QUARTERS)
    metrics = {"protocol_sha256": FROZEN, "predictions_sha256": seal["predictions_sha256"],
               "skipped": {"A_primary": skA, "A_S-A1": skAs, "B": skB},
               "perturbation_check": pert, "results": results, "diagnosis": diagnosis(comp),
               "external": external(comp, rounds, ext),
               "coefficients": {"A_primary": coA, "A_S-A1": coAs, "B": coB}}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1, default=jdefault), encoding="utf-8")

    # ---------------------------------------------------------------- comparison tables
    brow, mrow = [], []
    for key, res in results.items():
        tgt, an = key.split("|")
        for a, m in res["arms"].items():
            ev = m["event"]
            common = {"target": tgt, "analysis": an, "arm": a, "description": ARM_DESC[a], "n_rows": m["n"],
                      "n_quarters": m["n_quarters"], "MAE": m["MAE"], "RMSE": m["RMSE"], "bias": m["bias"],
                      "mean_kendall_tau": m.get("mean_kendall_tau"), "event_n": ev["n"], "event_positives": ev["positives"],
                      "event_TP": ev["TP"], "event_FP": ev["FP"], "event_FN": ev["FN"], "event_TN": ev["TN"],
                      "event_balanced_accuracy": ev["balanced_accuracy"], "event_ROC_AUC": ev["ROC_AUC"],
                      "event_PR_AUC": ev["PR_AUC"]}
            if ARM_TYPE[a] == "baseline":
                brow.append({**common, "is_best_baseline": a == res["best_baseline"]})
            else:
                c = res["comparisons"][a]
                b = res["best_baseline"]
                mrow.append({**common, "best_baseline": b, "best_baseline_MAE": res["arms"][b]["MAE"],
                             "MAE_diff_vs_best": c["vs"][b]["diff"], "ci_low": c["vs"][b]["ci_low"],
                             "ci_high": c["vs"][b]["ci_high"], "quarters_better": c["quarters_better_than_best"],
                             "quarters_total": c["quarters_total"], "p_signflip": c["p_signflip_vs_best"],
                             "p_holm": c["p_holm"], "loqo_better": f"{sum(c['loqo_better'])}/{len(c['loqo_better'])}",
                             "cond1": c["cond1_lower_than_all_baselines"], "cond2": c["cond2_ci_below_zero"],
                             "cond3": c["cond3_holm_p_below_0_05"], "cond4": c["cond4_loqo_all"],
                             "improvement_established": c["improvement_established"],
                             "rule_applies": an == "primary"})
    B = pd.DataFrame(brow)
    M = pd.DataFrame(mrow)
    write_csv(B, out / "baseline_comparison.csv")
    write_csv(M, out / "model_comparison.csv")
    if deliverables:
        write_csv(B, EXP / "BASELINE_COMPARISON.csv", new_only=True)
        write_csv(M, EXP / "MODEL_COMPARISON.csv", new_only=True)

    allow_end = guard.verify_allowlist()
    code = {p.name: sha_path(p) for p in sorted((EXP / "runner").glob("*.py"))}
    manifest = {"started_utc": started.isoformat(), "finished_utc": datetime.now(timezone.utc).isoformat(),
                "protocol_sha256": FROZEN, "allowlist_sha256_start": allow_start, "allowlist_sha256_end": allow_end,
                "code_sha256": code,
                "outputs_sha256": {p.name: sha_path(p) for p in sorted(out.glob("*")) if p.name != "manifest.json"},
                "deliverables_written": deliverables,
                "environment": {"python": platform.python_version(), "platform": platform.platform(),
                                "pandas": pd.__version__, "numpy": np.__version__,
                                "sklearn": __import__("sklearn").__version__},
                "access_log": guard.ACCESS_LOG}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main("--deliverables" in sys.argv)
