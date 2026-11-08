"""E117 (EXPERIMENT_PROTOCOL.md, hash checked): grouped, individual and interaction feature-contribution tests on SWS
hunger by area with one unified LightGBM recipe, in strict (verified-only) and provisional modes; comparators; inspected
periods labelled; prospective forecasts for unpublished targets sealed.

    python run_e117.py    # ../out/*.csv, ../out/e117_results.json, ../out/prospective_forecasts.csv (+ .sha256)
"""
from __future__ import annotations

import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
X = ROOT.parent
sys.path.insert(0, str(X / "E116_FIRI_Domains" / "runner"))
import run_e116 as R16  # noqa: E402

R14, L = R16.R14, R16.L
OUT = ROOT / "out"
PANEL = X / "CORRECTED_PIPELINE" / "out" / "regional_forecast_panel.csv"
BASE = R16.BASE
MKT, FISH, CLIM, EMP, NEWS = ["AF_food", "AF_gap", "AF_dfood", "P-RICE"], ["F_yoy", "F_dyoy"], ["C-ONI", "C_nino", "C-TC", "PAL_yoy"], ["P-UNEMP"], ["N-SUP", "N-AST"]
UNVERIFIED = ["AF_food", "AF_gap", "AF_dfood", "P-RICE", "F_yoy", "F_dyoy", "C-ONI", "C_nino", "PAL_yoy", "P-UNEMP",
              "X_food_unemp", "X_fish_oni", "X_oni_food"]
PROV = {"A": BASE, "B": BASE + MKT, "C": BASE + FISH, "D": BASE + CLIM, "E": BASE + EMP, "G": BASE + NEWS,
        "H": BASE + MKT + FISH + CLIM + EMP, "I": BASE + MKT + FISH + CLIM + EMP + NEWS,
        "IA1": BASE + ["AF_food", "AF_dfood"], "IA2": BASE + ["AF_gap"], "IA3": BASE + ["P-RICE"], "IC1": BASE + ["C-ONI", "C_nino"],
        "IC2": BASE + ["C-TC"], "IC3": BASE + ["PAL_yoy"], "IC4": BASE + FISH, "IE1": BASE + EMP, "IN1": BASE + NEWS,
        "X1": BASE + MKT + EMP + ["X_food_unemp"], "X1n": BASE + MKT + EMP,
        "X2": BASE + FISH + CLIM + ["X_fish_oni"], "X2n": BASE + FISH + CLIM,
        "X3": BASE + CLIM + MKT + ["X_oni_food"], "X3n": BASE + CLIM + MKT}
STRICT = {"S_A": BASE, "S_G": BASE + NEWS, "S_C2": BASE + ["C-TC"], "S_ALL": BASE + NEWS + ["C-TC"]}
PERIODS = {"P1_2003_2012": (L.qi("2003-Q1"), L.qi("2012-Q4")), "P2_2013_2020": (L.qi("2013-Q1"), L.qi("2020-Q4")),
           "P3_2021_2026": (L.qi("2021-Q1"), L.qi("2026-Q3")), "POOLED_2003_2026": (L.qi("2003-Q1"), L.qi("2026-Q3"))}
DOMAINS = {"market_prices": "B", "fish_production": "C", "climate": "D", "employment": "E", "news_nlp": "G"}
INDIV = {"A1": "IA1", "A2": "IA2", "A3": "IA3", "C1": "IC1", "C2": "IC2", "C3": "IC3", "C4": "IC4", "E1": "IE1", "N1": "IN1"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ridge_job(args):
    name, cols, R = args
    P = R14.rolling(R, cols=cols, with_ridge=True)
    return name, P[["area", "t", "lead", "RIDGE"]].rename(columns={"RIDGE": name}), {}, None


def run_job(job):
    if job[0] == "RIDGE":
        return ridge_job(job[1:]) if False else ridge_job((job[0], job[1], job[2]))
    return R16.rolling(job)


def diff(R, a, b, k, lo, hi):
    g = R[(R["lead"] == k) & (R["q"] >= lo) & (R["q"] <= hi) & R["y"].notna()].dropna(subset=[a, b])
    d = ((g[a] - g["y"]) ** 2 - (g[b] - g["y"]) ** 2).groupby(g["q"]).mean()
    if len(d) < 4:
        return {"quarters": int(len(d)), "delta_mse": None, "ci90": [None, None], "p_a_better": None}
    dm = R14.dm(d, k)                                         # H1: a better (mean d < 0) -> small p
    return {"quarters": int(len(d)), "rows": int(len(g)), "delta_mse": float(d.mean()), "ci90": R14.boot_q(d),
            "p_a_better": dm["p_one_sided"], "mse_a": float(((g[a] - g["y"]) ** 2).mean()), "mse_b": float(((g[b] - g["y"]) ** 2).mean())}


def level(R, m, k, lo, hi):
    g = R[(R["lead"] == k) & (R["q"] >= lo) & (R["q"] <= hi) & R["y"].notna()].dropna(subset=[m])
    e = g[m] - g["y"]
    out = {"rows": int(len(g)), "quarters": int(g["q"].nunique()), "mse": float((e ** 2).mean()), "mae": float(e.abs().mean()),
           "rmse": float(np.sqrt((e ** 2).mean())), "bias": float(e.mean())}
    out.update({f"mae_{a}": float(e[g["area"] == a].abs().mean()) for a in R16.AREAS})
    return out


def event(R2, m, k, lo, hi):
    g = R2[(R2["lead"] == k) & (R2["q"] >= lo) & (R2["q"] <= hi) & R2["y"].notna()].dropna(subset=[f"{m}_pU"])
    return R14.binm(g["yU"], g[f"{m}_pU"]) if len(g) else {}


def decide(pooled, per, holm_p):
    if pooled["delta_mse"] is None:
        return "not testable"
    neg = sum(1 for v in per.values() if v["delta_mse"] is not None and v["delta_mse"] < 0)
    sig1 = sum(1 for v in per.values() if v["delta_mse"] is not None and v["ci90"][1] is not None and v["ci90"][1] < 0)
    if pooled["ci90"][1] < 0 and holm_p < .10 and neg >= 2:
        return "improves"
    if pooled["ci90"][0] > 0:
        return "possible noise"
    if sig1 == 1:
        return "conditional"
    return "no measurable value"


def main():
    proto = ROOT / "EXPERIMENT_PROTOCOL.md"
    assert sha(proto) == (HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "protocol changed"
    OUT.mkdir(exist_ok=True)
    R = R16.rows()
    committed = pd.read_csv(PANEL)
    chk = R.merge(committed[["area", "t", "lead", "AF_food", "F_yoy", "h_last", "y"]], on=["area", "t", "lead"], suffixes=("", "_c"))
    assert len(chk) == len(committed) == len(R)
    for c in ("AF_food", "F_yoy", "h_last", "y"):
        assert np.allclose(chk[c], chk[f"{c}_c"], rtol=1e-8, atol=1e-8, equal_nan=True), c
    RS = R.copy()
    RS[UNVERIFIED] = np.nan
    R["RW"], R["MEAN"] = R["h_last"], R["mean_known"]
    R["DAMP"] = R["mean_known"] + 0.5 ** R["lead"] * (R["h_last"] - R["mean_known"])
    assert "AR1" in R.columns                                   # E114's AR(1) forecast, built by the same row builder
    jobs = [(n, c, R, False, False, None) for n, c in PROV.items()] + [(n, c, RS, False, False, None) for n, c in STRICT.items()]
    jobs.append(("RIDGE", PROV["I"], R))
    cache = OUT / "refit_predictions.csv"
    if cache.exists() and json.loads((OUT / "refit_predictions.json").read_text())["protocol_sha256"] == sha(proto):
        P = pd.read_csv(cache)
        train = json.loads((OUT / "refit_predictions.json").read_text())["train_mse"]
    else:
        preds, train = [], {}
        with ProcessPoolExecutor(max_workers=6) as ex:
            for name, P, _, tm in ex.map(run_job, jobs):
                preds.append(P.set_index(["area", "t", "lead"]))
                train[name] = tm
                print("done", name, flush=True)
        P = pd.concat(preds, axis=1).reset_index()
        P.to_csv(cache, index=False, lineterminator="\n", float_format="%.10g")
        (OUT / "refit_predictions.json").write_text(json.dumps({"protocol_sha256": sha(proto), "train_mse": train}, default=float))
    R = R.merge(P, on=["area", "t", "lead"], how="left")
    models = list(PROV) + list(STRICT) + ["RIDGE", "RW", "MEAN", "DAMP", "AR1"]
    keep = R14.MODELS
    R14.MODELS = models
    R2 = R14.add_probabilities(R.copy())
    R14.MODELS = keep
    R2.to_csv(OUT / "e117_rows.csv", index=False, lineterminator="\n", float_format="%.10g")
    res = {"protocol_sha256": sha(proto), "panel_sha256": sha(PANEL), "train_mse": train}

    # 1. feature ablation table (all variants)
    abl = []
    for m in list(PROV) + list(STRICT):
        base = "S_A" if m.startswith("S_") else "A"
        for k in (1, 2):
            for per, (lo, hi) in PERIODS.items():
                lv, ev = level(R2, m, k, lo, hi), event(R2, m, k, lo, hi)
                d = diff(R2, m, base, k, lo, hi) if m != base else {}
                abl.append({"variant": m, "mode": "strict" if m.startswith("S_") else "provisional", "lead": k, "period": per,
                            **{f"level_{x}": lv[x] for x in ("rows", "quarters", "mse", "mae", "rmse", "bias")},
                            "level_mae_BL": lv["mae_BL"], "delta_mse_vs_base": d.get("delta_mse"), "ci90_low": (d.get("ci90") or [None])[0],
                            "ci90_high": (d.get("ci90") or [None, None])[1], "p_better": d.get("p_a_better"),
                            **{f"event_{x}": ev.get(x) for x in ("accuracy", "balanced_accuracy", "precision", "recall", "f1", "brier", "calibration_slope", "calibration_in_the_large")}})
    pd.DataFrame(abl).to_csv(ROOT / "FEATURE_ABLATION_RESULTS.csv", index=False, lineterminator="\n", float_format="%.6g")

    # 2. domains (provisional) and strict domains, with Holm across the testable domains of each mode
    dom_rows = []
    for mode, spec in (("provisional", DOMAINS), ("strict", {"news_nlp": "S_G", "climate (typhoon only)": "S_C2"})):
        base = "A" if mode == "provisional" else "S_A"
        for k in (1, 2):
            lo, hi = PERIODS["POOLED_2003_2026"]
            pooled = {d: diff(R2, v, base, k, lo, hi) for d, v in spec.items()}
            hp = R16.holm({d: (p["p_a_better"] if p["p_a_better"] is not None else 1.0) for d, p in pooled.items()})
            for d, v in spec.items():
                per = {p: diff(R2, v, base, k, *PERIODS[p]) for p in ("P1_2003_2012", "P2_2013_2020", "P3_2021_2026")}
                dom_rows.append({"domain": d, "mode": mode, "variant": v, "lead": k, "pooled_delta_mse": pooled[d]["delta_mse"],
                                 "pooled_ci90_low": pooled[d]["ci90"][0], "pooled_ci90_high": pooled[d]["ci90"][1], "pooled_p_better": pooled[d]["p_a_better"],
                                 "holm_p": hp[d], **{f"{p}_delta_mse": per[p]["delta_mse"] for p in per},
                                 **{f"{p}_ci90_high": per[p]["ci90"][1] for p in per},
                                 "decision": decide(pooled[d], per, hp[d])})
        if mode == "provisional":
            for k in (1, 2):
                dom_rows.append({"domain": "ofw_remittances", "mode": mode, "variant": "F", "lead": k, "decision": "not testable (no series before 2021; BSP blocks automated download)"})
                lo, hi = PERIODS["POOLED_2003_2026"]
                for name, a, b in (("all_testable_domains (H vs A)", "H", "A"), ("full (I vs A)", "I", "A")):
                    p = diff(R2, a, b, k, lo, hi)
                    dom_rows.append({"domain": name, "mode": mode, "variant": a, "lead": k, "pooled_delta_mse": p["delta_mse"], "pooled_ci90_low": p["ci90"][0],
                                     "pooled_ci90_high": p["ci90"][1], "pooled_p_better": p["p_a_better"], "decision": "see delta"})
                for x in ("X1", "X2", "X3"):
                    p = diff(R2, x, f"{x}n", k, lo, hi)
                    dom_rows.append({"domain": {"X1": "interaction food prices x employment", "X2": "interaction fish x climate", "X3": "interaction climate x food prices"}[x],
                                     "mode": mode, "variant": x, "lead": k, "pooled_delta_mse": p["delta_mse"], "pooled_ci90_low": p["ci90"][0],
                                     "pooled_ci90_high": p["ci90"][1], "pooled_p_better": p["p_a_better"],
                                     "decision": "improves" if p["ci90"][1] < 0 else "possible noise" if p["ci90"][0] > 0 else "no measurable value"})
                for name in ("interaction food prices x remittances", "interaction poverty x market"):
                    dom_rows.append({"domain": name, "mode": mode, "lead": k, "decision": "not testable (no time series)"})
    pd.DataFrame(dom_rows).to_csv(ROOT / "DOMAIN_CONTRIBUTION_RESULTS.csv", index=False, lineterminator="\n", float_format="%.6g")

    # 3. individual indicators
    ind = []
    for k in (1, 2):
        lo, hi = PERIODS["POOLED_2003_2026"]
        pooled = {c: diff(R2, v, "A", k, lo, hi) for c, v in INDIV.items()}
        hp = R16.holm({c: (p["p_a_better"] if p["p_a_better"] is not None else 1.0) for c, p in pooled.items()})
        for c, v in INDIV.items():
            per = {p: diff(R2, v, "A", k, *PERIODS[p]) for p in ("P1_2003_2012", "P2_2013_2020", "P3_2021_2026")}
            ind.append({"indicator": c, "variant": v, "lead": k, "timing_mode": "strict-eligible" if c in ("C2", "N1") else "provisional only",
                        "pooled_delta_mse": pooled[c]["delta_mse"], "ci90_low": pooled[c]["ci90"][0], "ci90_high": pooled[c]["ci90"][1],
                        "p_better": pooled[c]["p_a_better"], "holm_p": hp[c], **{f"{p}_delta_mse": per[p]["delta_mse"] for p in per},
                        "decision": decide(pooled[c], per, hp[c])})
        b = diff(R2, "A", "RW", k, lo, hi)
        ind.append({"indicator": "H1 (hunger history = base)", "variant": "A vs RW", "lead": k, "timing_mode": "strict", "pooled_delta_mse": b["delta_mse"],
                    "ci90_low": b["ci90"][0], "ci90_high": b["ci90"][1], "p_better": b["p_a_better"], "decision": "baseline (vs persistence)"})
        for c, why in (("E2", "no series before 2021"), ("V1", "no dated time-varying series")):
            ind.append({"indicator": c, "lead": k, "decision": f"not testable ({why})"})
    pd.DataFrame(ind).to_csv(ROOT / "INDIVIDUAL_INDICATOR_RESULTS.csv", index=False, lineterminator="\n", float_format="%.6g")

    # 4. model comparison
    mc = []
    for m in ("A", "H", "I", "S_A", "S_ALL", "RIDGE", "RW", "MEAN", "DAMP", "AR1"):
        for k in (1, 2):
            for per, (lo, hi) in PERIODS.items():
                lv, ev = level(R2, m, k, lo, hi), event(R2, m, k, lo, hi)
                d = diff(R2, m, "RW", k, lo, hi) if m != "RW" else {}
                mc.append({"model": m, "lead": k, "period": per, **{f"level_{x}": v for x, v in lv.items()},
                           "delta_mse_vs_persistence": d.get("delta_mse"), "p_better_than_persistence": d.get("p_a_better"),
                           **{f"event_{x}": ev.get(x) for x in ("accuracy", "balanced_accuracy", "precision", "recall", "f1", "brier", "calibration_slope", "calibration_in_the_large", "predicted_pos_rate", "observed_pos_rate")}})
    pd.DataFrame(mc).to_csv(ROOT / "MODEL_COMPARISON_RESULTS.csv", index=False, lineterminator="\n", float_format="%.6g")

    # 5. prospective seal (targets with no SWS reading in the data)
    pro = R2[(R2["q"] >= L.qi("2026-Q4")) & R2["y"].isna() & R2["pub_target"].isna()]
    cols = ["area", "t", "lead", "q", "issue", "h_last", "q_last"] + models + [f"{m}_sig" for m in models]
    pro = pro[cols].assign(origin=pro["t"].map(L.qs), target=pro["q"].map(L.qs))
    sealed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pro.to_csv(OUT / "prospective_forecasts.csv", index=False, lineterminator="\n", float_format="%.10g")
    (OUT / "prospective_forecasts.sha256").write_text(json.dumps({"file": "prospective_forecasts.csv", "sha256": sha(OUT / "prospective_forecasts.csv"),
                                                                  "sealed_at_utc": sealed_at, "targets": sorted(pro["target"].unique().tolist()),
                                                                  "latest_sws_published_in_data": str(L.rounds()["published"].max()),
                                                                  "protocol_sha256": res["protocol_sha256"]}, indent=1))
    res["prospective"] = {"rows": int(len(pro)), "targets": sorted(pro["target"].unique().tolist()), "sealed_at_utc": sealed_at}
    (OUT / "e117_results.json").write_text(json.dumps(res, indent=1, default=float))
    print(pd.read_csv(ROOT / "DOMAIN_CONTRIBUTION_RESULTS.csv")[["domain", "mode", "lead", "pooled_delta_mse", "pooled_ci90_low", "pooled_ci90_high", "holm_p", "decision"]].to_string())


if __name__ == "__main__":
    main()
