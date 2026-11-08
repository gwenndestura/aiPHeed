"""
v2 Step 4: nested chronological validation of the pre-registered method (docs/aipheed/v2/PREREGISTRATION.md).

  1. walk-forward forecasts of every candidate at every P-DASH issue (parameters re-estimated from data known there)
  2. at each outer issue: inner-fold selection (Lead 2) and split-conformal intervals per lead -> the V2 forecast
  3. outer S-U rows scored once: V2, the 3 candidates and the context baselines (E136), Leads 1-4
  4. frozen N1-N7 per lead (DEVELOPMENT labels), overfitting / stability / period checks, leakage controls

    python -I backend/scripts/v2_validate.py

Outputs: docs/aipheed/v2/results/v2_*.csv, v2_verdict.json, v2_validate_run.txt. All rows are DEVELOPMENT.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.models import T0  # noqa: E402
from app.forecasting.v2 import models as V  # noqa: E402
from app.forecasting.v2 import select as S  # noqa: E402
from app.forecasting.v2 import verdict as VD  # noqa: E402

OUT = REPO / "docs" / "aipheed" / "v2" / "results"
PREREG = REPO / "docs" / "aipheed" / "v2" / "PREREGISTRATION.md"
E136 = REPO / "aipheed-backend-aligned" / "experiments" / "E136_Methodology_Review" / "out" / "e136_predictions.csv"
LAST_ISSUE = date(2026, 10, 1)
OUTER_DRAWS = 10000
CONTEXT = ["TREND-D", "CLIM", "RIDGE-ALL", "SEAS-LLM", "HFM-X"]
SURGE, POST = T.qi("2024-Q1"), T.qi("2025-Q1")


def sha(p: Path, normalise: bool = False) -> str:
    b = p.read_bytes()
    return hashlib.sha256(b.replace(b"\r\n", b"\n") if normalise else b).hexdigest()


def v2_procedure(rr: pd.DataFrame, wf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """At each issue: select on inner folds, take the selected model's walk-forward forecast, conformal interval.
    Also conformal intervals for each fixed candidate (its own residuals)."""
    sel_logs, picks, rows = [], [], []
    for I in S.issues(LAST_ISSUE):
        chosen, log = S.select(wf, rr, I)
        sel_logs += log
        picks.append({"issue": I.isoformat(), "selected": chosen})
        g = wf[wf.issue == I.isoformat()]
        for k in S.LEADS:
            for m in (*V.CANDIDATES, "V2"):
                mm = chosen if m == "V2" else m
                half, n_res = S.conformal_halfwidth(wf, rr, I, mm, k)
                for r in g[(g.model == mm) & (g.lead == k)].itertuples():
                    lo, hi, how = S.interval(r.f, r.sd, half)
                    rows.append({"issue": r.issue, "area": r.area, "lead": k, "tqi": r.tqi, "model": m, "source_model": mm,
                                 "f": r.f, "lo80": lo, "hi80": hi, "interval": how, "n_residuals": n_res,
                                 "y_latest": r.latest, "n_obs": r.n_obs, "h": r.h})
    return pd.DataFrame(rows), pd.DataFrame(sel_logs), pd.DataFrame(picks)


def outer_table(rr: pd.DataFrame, fc: pd.DataFrame) -> pd.DataFrame:
    full = T.quarter_table(rr)[["area", "qi", "y", "se", "tol"]].rename(columns={"qi": "tqi"})
    W = fc.pivot_table(index=["issue", "area", "lead", "tqi", "n_obs", "h", "y_latest"], columns="model",
                       values=["f", "lo80", "hi80"], aggfunc="first")
    W.columns = [f"{a}_{b}" for a, b in W.columns]
    W = W.reset_index().merge(full, on=["area", "tqi"], how="inner")
    return W


def attach_context(W: pd.DataFrame) -> pd.DataFrame:
    P = pd.read_csv(E136)
    P = P[P.policy == "P-DASH"][["area", "issue", "lead", "target", "y_true", "y_latest", "h", "n_obs"] + [f"f_{m}" for m in CONTEXT]
                                + ["f_PERSIST"]].rename(columns={"f_PERSIST": "f_PERSIST_e136"})
    m = W.merge(P, on=["area", "issue", "lead"], how="left", suffixes=("", "_e136"))
    # the v2 outer rows must be exactly the frozen rows (DIAGNOSIS Q6)
    assert m["target"].notna().all(), "row without an E136 match"
    assert (m["target"].map(T.qi) == m["tqi"]).all() and np.allclose(m["y"], m["y_true"])
    assert (m["h"] == m["h_e136"]).all() and (m["n_obs"] == m["n_obs_e136"]).all()
    assert np.allclose(m["f_PERSIST"], m["f_PERSIST_e136"]), "backend persistence differs from research persistence"
    return m


def boot_index(clusters: np.ndarray, rng, draws=OUTER_DRAWS):
    u = np.unique(clusters)
    pos = {q: np.where(clusters == q)[0] for q in u}
    return [np.concatenate([pos[q] for q in rng.choice(u, len(u))]) for _ in range(draws)]


def metrics(g: pd.DataFrame, m: str, boots) -> dict:
    y, f, se = g.y.to_numpy(), g[f"f_{m}"].to_numpy(), g.se.to_numpy()
    w = np.abs(f - y) <= T.Z90 * se
    wp = np.abs(g.f_PERSIST.to_numpy() - y) <= T.Z90 * se
    bw = np.array([w[b].mean() for b in boots])
    bd = np.array([w[b].mean() - wp[b].mean() for b in boots])
    e = f - y
    top = y >= np.quantile(y, 2 / 3)
    sharp = (y - g.y_latest.to_numpy()) > 2 * se
    rec = {"n": len(g), "n_quarters": int(g.tqi.nunique()), "n_within": int(w.sum()), "within": float(w.mean()),
           "within_ci_lo": float(np.quantile(bw, 0.025)), "within_ci_hi": float(np.quantile(bw, 0.975)),
           "diff_vs_persist": float(w.mean() - wp.mean()), "diff_ci_lo": float(np.quantile(bd, 0.025)),
           "diff_ci_hi": float(np.quantile(bd, 0.975)),
           "mae": float(np.abs(e).mean()), "rmse": float(np.sqrt((e ** 2).mean())), "bias": float(e.mean()),
           "high_tercile_bias": float(e[top].mean()), "sharp_increases": int(sharp.sum()),
           "sharp_within": int((w & sharp).sum()), "var_ratio": float(np.var(f) / np.var(y)),
           "corr": float(np.corrcoef(f, y)[0, 1]) if np.std(f) > 0 else float("nan")}
    if f"lo80_{m}" in g and g[f"lo80_{m}"].notna().all():
        rec["coverage80"] = float(((y >= g[f"lo80_{m}"]) & (y <= g[f"hi80_{m}"])).mean())
        rec["mean_width80"] = float((g[f"hi80_{m}"] - g[f"lo80_{m}"]).mean())
    return rec


def evaluate(SU: pd.DataFrame, models: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(S.SEED)
    M_, R_ = [], []
    for k in S.LEADS:
        g = SU[SU.lead == k].reset_index(drop=True)
        boots = boot_index(g.tqi.to_numpy(), rng)
        for m in models:
            sub = g[g[f"f_{m}"].notna()].reset_index(drop=True)
            if len(sub) < len(g):          # e.g. RIDGE-ALL, which needs >= 20 training rows: scored on its own rows
                M_.append({"lead": k, "model": m, "rows_note": f"only {len(sub)} of {len(g)} S-U rows have a forecast",
                           **(metrics(sub, m, boot_index(sub.tqi.to_numpy(), rng)) if len(sub) >= 8 else {"n": len(sub)})})
                continue
            M_.append({"lead": k, "model": m, **metrics(g, m, boots)})
            if f"lo80_{m}" in g:
                d = g.assign(f_persistence=g.f_PERSIST, f_climatology=g["f_CLIM"])
                r = VD.reliability(d, m)
                R_.append({"lead": k, "model": m, **{n: bool(v) for n, v in r["rules"].items()}, "all_pass": bool(r["passed"]),
                           "n_rows": r["n_rows"], "n_quarters": r["n_target_quarters"], "within_thirds": r["within_thirds"],
                           "loqo_min": r["loqo_min_within"], "p_vs_persistence": r["p_sq_error_vs_persistence"],
                           "p_vs_climatology": r["p_sq_error_vs_climatology"], "coverage80": r["coverage_80"],
                           "label": VD.label(bool(r["passed"]), r["n_target_quarters"], r["n_rows"], future=False)})
    return pd.DataFrame(M_), pd.DataFrame(R_)


def overfitting(rr, wf, picks, SU) -> pd.DataFrame:
    out = []
    for m in (*V.CANDIDATES, "V2"):
        tr, inn = [], []
        for p in picks.itertuples():
            I = date.fromisoformat(p.issue)
            mm = p.selected if m == "V2" else m
            if p.issue not in set(SU[SU.lead == 2].issue):
                continue
            known = T.known_at(rr, I)
            tr.append(V.training_mae(known, V.fit(mm, known)))
            g = S.inner_rows(wf, rr, I, 2)
            g = g[g.model == mm]
            inn.append(float(np.abs(g.f - g.y).mean()))
        o = SU[SU.lead == 2]
        out.append({"model": m, "train_one_step_mae": float(np.mean(tr)), "inner_lead2_mae": float(np.mean(inn)),
                    "outer_lead2_mae": float(np.abs(o[f"f_{m}"] - o.y).mean())})
    return pd.DataFrame(out)


def by_period(SU: pd.DataFrame, models) -> pd.DataFrame:
    g = SU[SU.lead == 2].copy()
    g["period"] = np.where(g.tqi < SURGE, "pre-surge", np.where(g.tqi < POST, "surge 2024", "2025-26"))
    rows = []
    for (p,), gg in g.groupby(["period"]):
        for m in models:
            rows.append({"period": p, "model": m, "n": len(gg),
                         "within": float((np.abs(gg[f"f_{m}"] - gg.y) <= gg.tol).mean()),
                         "mae": float(np.abs(gg[f"f_{m}"] - gg.y).mean()), "bias": float((gg[f"f_{m}"] - gg.y).mean())})
    return pd.DataFrame(rows)


def run_procedure(rr: pd.DataFrame, start: int = T0) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    wf = S.walk_forward(rr, LAST_ISSUE, start=start)
    fc, logs, picks = v2_procedure(rr, wf)
    return wf, fc, logs, picks


def lead2_within(rr: pd.DataFrame, fc: pd.DataFrame) -> pd.DataFrame:
    W = outer_table(rr, fc)
    g = W[(W.lead == 2) & (W.n_obs >= 8)]
    return pd.DataFrame([{"model": m, "n": len(g), "within": float((np.abs(g[f"f_{m}"] - g.y) <= g.tol).mean()),
                          "mae": float(np.abs(g[f"f_{m}"] - g.y).mean())} for m in (*V.CANDIDATES, "V2")])


def leakage_controls(rr: pd.DataFrame, SU: pd.DataFrame) -> dict:
    res = {}
    # shuffle-target: (value, se) pairs permuted within area across rounds; publication dates kept
    rng = np.random.default_rng(S.SEED)
    sh = rr.copy()
    for a in sh.area.unique():
        ix = sh.index[sh.area == a]
        perm = rng.permutation(ix)
        sh.loc[ix, ["value", "se"]] = sh.loc[perm, ["value", "se"]].to_numpy()
    _, fc_s, _, picks_s = run_procedure(sh)
    res["shuffle_target_lead2"] = lead2_within(sh, fc_s).to_dict("records")
    res["shuffle_target_selected_counts"] = picks_s.selected.value_counts().to_dict()
    # future-shift positive control: cutoff = the day after the target's publication (the model sees the target)
    full = T.quarter_table(rr).set_index(["area", "qi"])
    rows = []
    for r in SU[SU.lead == 2].itertuples():
        cut = full.loc[(r.area, r.tqi), "published"] + timedelta(days=1)
        known = T.known_at(rr, cut)
        for m in ("PERSIST", "LL"):
            p = V.fit(m, known)
            f = V.forecast(known, p, r.tqi)[r.area]["f"]
            rows.append({"model": m, "within": abs(f - r.y) <= r.tol})
    d = pd.DataFrame(rows)
    res["future_shift_lead2_within"] = d.groupby("model").within.mean().to_dict()
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rr = T.load_rounds()
    wf, fc, logs, picks = run_procedure(rr)
    wf.to_csv(OUT / "v2_walk_forward.csv", index=False)
    logs.to_csv(OUT / "v2_selection_log.csv", index=False)
    picks.to_csv(OUT / "v2_selected_by_issue.csv", index=False)
    W = attach_context(outer_table(rr, fc))
    SU = W[W.n_obs >= 8].reset_index(drop=True)
    SU.to_csv(OUT / "v2_outer_predictions.csv", index=False)
    models = ["V2", *V.CANDIDATES, *CONTEXT]
    met, rel = evaluate(SU, models)
    met.to_csv(OUT / "v2_metrics.csv", index=False)
    rel.to_csv(OUT / "v2_reliability.csv", index=False)
    ov = overfitting(rr, wf, picks, SU)
    ov.to_csv(OUT / "v2_overfitting.csv", index=False)
    per = by_period(SU, ["V2", *V.CANDIDATES, "SEAS-LLM", "HFM-X"])
    per.to_csv(OUT / "v2_by_period.csv", index=False)
    # training-window sensitivity: estimation and filtering start at 2022-Q1 instead of 2021-Q2
    _, fc22, _, picks22 = run_procedure(rr, start=T.qi("2022-Q1"))
    sens = lead2_within(rr, fc22).assign(window_start="2022-Q1")
    sens = pd.concat([lead2_within(rr, fc).assign(window_start="2021-Q2"), sens])
    sens.to_csv(OUT / "v2_window_sensitivity.csv", index=False)
    leak = leakage_controls(rr, SU)
    # the served choice: the same rule at the latest issue
    served, served_log = S.select(wf, rr, LAST_ISSUE)
    v2rel = rel[rel.model == "V2"].set_index("lead")
    dev = {int(k): v2rel.loc[k, "label"] for k in S.LEADS}
    future = {k: VD.label(False, 0, 0, future=True) for k in S.LEADS}
    verdict = {
        "status": "DEVELOPMENT (all 2021-2026-Q3 SWS quarters were seen before v2 was designed)",
        "preregistration_sha256_lf": sha(PREREG, normalise=True), "data_sha256": sha(T.SWS_ROUNDS),
        "seed": S.SEED, "outer_draws": OUTER_DRAWS,
        "selected_by_issue_counts": picks.selected.value_counts().to_dict(),
        "served_model_at": LAST_ISSUE.isoformat(), "served_model": served, "served_selection_log": served_log,
        "development_label_by_lead": dev, "future_label_by_lead": future,
        "served_reliability_status_by_lead": {k: VD.served_status(dev[k], future[k]) for k in S.LEADS},
        "maximum_reliable_lead_future": VD.maximum_reliable_lead(future),
        "lead2_v2": met[(met.model == "V2") & (met.lead == 2)].iloc[0].to_dict(),
        "leakage_controls": leak,
        "future_unseen_lead2_quarters": 0,
    }
    (OUT / "v2_verdict.json").write_text(json.dumps(verdict, indent=1, default=float) + "\n", encoding="utf-8", newline="\n")
    pd.set_option("display.width", 250)
    print(picks.selected.value_counts().to_string())
    print(logs.round(3).to_string())
    print(met.round(3).to_string())
    print(rel.to_string())
    print(ov.round(3).to_string())
    print(per.round(3).to_string())
    print(sens.round(3).to_string())
    print(json.dumps(verdict, indent=1, default=float))


if __name__ == "__main__":
    main()
