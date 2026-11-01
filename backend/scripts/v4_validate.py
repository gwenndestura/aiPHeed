"""
v4 Steps D-E: run the pre-registered v4 procedure (docs/aipheed/v4/PREREGISTRATION.md) on the DEVELOPMENT tiers.
Writes the tier files, the walk-forward forecasts, the selection log, DELTA-X feature entries, metrics under the frozen
and the proposed (not adopted) tolerance, the beats-all test, N1-N7, leave-one-area-out, overfitting, leakage controls,
sample size and the verdict file. Every number is DEVELOPMENT.

    python -I backend/scripts/v4_validate.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.v2 import models as V  # noqa: E402
from app.forecasting.v2 import select as S2  # noqa: E402
from app.forecasting.v2 import verdict as VD2  # noqa: E402
from app.forecasting.v4 import features as F  # noqa: E402
from app.forecasting.v4 import select as S4  # noqa: E402
from app.forecasting.v4 import verdict as VD  # noqa: E402

V4 = REPO / "docs" / "aipheed" / "v4"
OUT, TIERS = V4 / "results", V4 / "tiers"
E136 = REPO / "aipheed-backend-aligned" / "experiments" / "E136_Methodology_Review" / "out" / "e136_predictions.csv"
V2OUT = REPO / "docs" / "aipheed" / "v2" / "results" / "v2_outer_predictions.csv"
LAST = date(2026, 10, 1)
Z95 = 1.959963984540054
CONTEXT = ["TREND-D", "CLIM", "RIDGE-ALL", "SEAS-LLM", "HFM-X"]
BASELINES = ["PERSIST", "TREND-D", "CLIM", "RIDGE-ALL", "HFM-X", "SEAS-LLM", "V2"]
SURGE, POST = T.qi("2024-Q1"), T.qi("2025-Q1")


def sha(p: Path, lf=False) -> str:
    b = p.read_bytes()
    return hashlib.sha256(b.replace(b"\r\n", b"\n") if lf else b).hexdigest()


def procedure(rr, feats):
    wf2 = S2.walk_forward(rr, LAST)
    wf = S4.walk_forward(rr, feats, LAST, wf2)
    logs, picks, rows = [], [], []
    for I in S2.issues(LAST):
        chosen, log = S4.select(wf, rr, I)
        logs += log
        picks.append({"issue": I.isoformat(), "selected": chosen})
        g = wf[wf.issue == I.isoformat()]
        for k in S2.LEADS:
            for m in (*S4.CANDIDATES, "V4"):
                mm = chosen if m == "V4" else m
                half, n = S2.conformal_halfwidth(wf, rr, I, mm, k)
                for r in g[(g.model == mm) & (g.lead == k)].itertuples():
                    lo, hi, how = S2.interval(r.f, r.sd, half)
                    rows.append({"issue": r.issue, "area": r.area, "lead": k, "tqi": r.tqi, "model": m, "f": r.f,
                                 "lo80": lo, "hi80": hi, "n_obs": r.n_obs, "h": r.h, "y_latest": r.latest})
    return wf2, wf, pd.DataFrame(logs), pd.DataFrame(picks), pd.DataFrame(rows)


def outer(rr, fc):
    full = T.quarter_table(rr)[["area", "qi", "y", "se", "tol", "se_pub"]].rename(columns={"qi": "tqi"})
    W = fc.pivot_table(index=["issue", "area", "lead", "tqi", "n_obs", "h", "y_latest"], columns="model",
                       values=["f", "lo80", "hi80"], aggfunc="first")
    W.columns = [f"{a}_{b}" for a, b in W.columns]
    W = W.reset_index().merge(full, on=["area", "tqi"], how="inner")
    P = pd.read_csv(E136)
    P = P[P.policy == "P-DASH"][["area", "issue", "lead", "target", "f_PERSIST"] + [f"f_{m}" for m in CONTEXT]]
    W = W.merge(P.rename(columns={"f_PERSIST": "f_PERSIST_e136"}), on=["area", "issue", "lead"], how="left")
    assert W.target.notna().all() and np.allclose(W.f_PERSIST, W.f_PERSIST_e136)
    v2 = pd.read_csv(V2OUT)[["area", "issue", "lead", "f_V2"]]
    W = W.merge(v2, on=["area", "issue", "lead"], how="left")
    W["tol_amended"] = Z95 * W.se_pub
    return W


def hits(g, m, tol="tol"):
    return (np.abs(g[f"f_{m}"] - g.y) <= g[tol]).to_numpy()


def metrics(SU, models):
    rng = np.random.default_rng(S2.SEED)
    out = []
    for k in S2.LEADS:
        G = SU[SU.lead == k]
        for m in models:
            g = G[G[f"f_{m}"].notna()].reset_index(drop=True)
            if len(g) < 8:
                continue
            cl = g.tqi.to_numpy()
            boots = VD.block_indices(cl)
            u = np.unique(cl)
            cboots = [np.concatenate([np.where(cl == q)[0] for q in rng.choice(u, len(u))]) for _ in range(2000)]
            y, f = g.y.to_numpy(), g[f"f_{m}"].to_numpy()
            e = f - y
            rec = {"lead": k, "model": m, "n": len(g), "n_quarters": len(u)}
            for tl, lab in (("tol", "frozen"), ("tol_amended", "amended_proposed")):
                h = hits(g, m, tl)
                c = VD.share_ci(h, boots)
                rec.update({f"within_{lab}": c["share"], f"block_ci_lo_{lab}": c["ci95_lo"], f"block_ci_hi_{lab}": c["ci95_hi"]})
                if lab == "frozen":
                    cc = np.array([h[i].mean() for i in cboots])
                    rec.update({"cluster_ci_lo_frozen": float(np.quantile(cc, .025)), "cluster_ci_hi_frozen": float(np.quantile(cc, .975))})
            top = y >= np.quantile(y, 2 / 3)
            sharp = (y - g.y_latest.to_numpy()) > 2 * g.se.to_numpy()
            rec.update({"mae": float(np.abs(e).mean()), "rmse": float(np.sqrt((e ** 2).mean())), "bias": float(e.mean()),
                        "high_tercile_bias": float(e[top].mean()), "sharp_increases": int(sharp.sum()),
                        "sharp_within": int((hits(g, m) & sharp).sum()), "var_ratio": float(np.var(f) / np.var(y)),
                        "corr": float(np.corrcoef(f, y)[0, 1]) if np.std(f) > 0 else float("nan")})
            if f"lo80_{m}" in g and g[f"lo80_{m}"].notna().all():
                rec["coverage80"] = float(((y >= g[f"lo80_{m}"]) & (y <= g[f"hi80_{m}"])).mean())
                rec["width80"] = float((g[f"hi80_{m}"] - g[f"lo80_{m}"]).mean())
            out.append(rec)
    return pd.DataFrame(out)


def beats(SU, model="V4"):
    res = {}
    for k in S2.LEADS:
        G = SU[SU.lead == k]
        for lab, tl in (("frozen", "tol"), ("amended_proposed", "tol_amended")):
            p, diff = {}, {}
            for b in BASELINES:
                g = G[G[f"f_{b}"].notna()].reset_index(drop=True)
                hm, hb = hits(g, model, tl), hits(g, b, tl)
                p[b] = VD.paired_p(hm, hb, g.tqi.to_numpy())
                diff[b] = float(hm.mean() - hb.mean())
            res[f"lead{k}_{lab}"] = {**VD.beats_all(p), "diff_within": diff}
    return res


def reliability(SU, models):
    out = []
    for k in S2.LEADS:
        g = SU[SU.lead == k].reset_index(drop=True).assign(f_persistence=lambda d: d.f_PERSIST, f_climatology=lambda d: d.f_CLIM)
        for m in models:
            r = VD2.reliability(g, m)
            out.append({"lead": k, "model": m, **{n: bool(v) for n, v in r["rules"].items()}, "all_pass": bool(r["passed"]),
                        "label": VD2.label(bool(r["passed"]), r["n_target_quarters"], r["n_rows"], future=False)})
    return pd.DataFrame(out)


def loao(rr, feats, wf2, SU):
    g2 = SU[SU.lead == 2]
    rows = []
    for I in sorted(g2.issue.unique()):
        Id = date.fromisoformat(I)
        known = T.known_at(rr, Id)
        D = S2.dashboard_quarter(Id)
        for a in T.quarter_table(rr).area.unique():
            if not ((g2.issue == I) & (g2.area == a)).any():
                continue
            p = V.fit("LL-K", known[known.area != a])
            llk = V.forecast(known, p, D + 1)[a]["f"]
            dx = S4.delta_at(wf2, rr, feats, Id, exclude_area=a)
            dx = dx[(dx.lead == 2) & (dx.area == a) & (dx.model == "DELTA-X")]["f"].iloc[0]
            r = g2[(g2.issue == I) & (g2.area == a)].iloc[0]
            rows.append({"issue": I, "area": a, "y": r.y, "tol": r.tol, "LL-K_loao": llk, "DELTA-X_loao": dx,
                         "LL-K_pooled": r["f_LL-K"], "DELTA-X_pooled": r["f_DELTA-X"], "PERSIST": r.f_PERSIST})
    d = pd.DataFrame(rows)
    res = {c: float((np.abs(d[c] - d.y) <= d.tol).mean()) for c in ("LL-K_loao", "DELTA-X_loao", "LL-K_pooled", "DELTA-X_pooled", "PERSIST")}
    res["by_area_within"] = {a: {c: float((np.abs(g[c] - g.y) <= g.tol).mean()) for c in ("LL-K_loao", "DELTA-X_loao", "PERSIST")}
                             for a, g in d.groupby("area")}
    return d, res


def overfit(rr, wf, picks, SU):
    out = []
    for m in (*S4.CANDIDATES, "V4"):
        inn = []
        for p in picks.itertuples():
            if p.issue not in set(SU[SU.lead == 2].issue):
                continue
            g = S2.inner_rows(wf, rr, date.fromisoformat(p.issue), 2)
            g = g[g.model == (p.selected if m == "V4" else m)]
            inn.append(float(np.abs(g.f - g.y).mean()))
        o = SU[SU.lead == 2]
        out.append({"model": m, "inner_lead2_mae": float(np.mean(inn)), "outer_lead2_mae": float(np.abs(o[f"f_{m}"] - o.y).mean())})
    return pd.DataFrame(out)


def leakage(rr, feats, SU):
    rng = np.random.default_rng(S2.SEED)
    sh = rr.copy()
    for a in sh.area.unique():
        ix = sh.index[sh.area == a]
        sh.loc[ix, ["value", "se"]] = sh.loc[rng.permutation(ix), ["value", "se"]].to_numpy()
    _, _, _, picks, fc = procedure(sh, feats)
    # E136 rows refer to the real series, so the shuffled run is scored on its own (shuffled) truth
    full = T.quarter_table(sh)[["area", "qi", "y", "tol"]].rename(columns={"qi": "tqi"})
    g = fc[(fc.lead == 2) & (fc.n_obs >= 8)].merge(full, on=["area", "tqi"])
    shuffle = {m: float((np.abs(x.f - x.y) <= x.tol).mean()) for m, x in g.groupby("model")}
    real = T.quarter_table(rr).set_index(["area", "qi"])
    fut = []
    for r in SU[SU.lead == 2].itertuples():
        known = T.known_at(rr, real.loc[(r.area, r.tqi), "published"] + timedelta(days=1))
        fut.append(abs(V.forecast(known, V.fit("PERSIST", known), r.tqi)[r.area]["f"] - r.y) <= r.tol)
    return {"shuffle_target_lead2_within": shuffle, "shuffle_selected": picks.selected.value_counts().to_dict(),
            "future_shift_persist_lead2_within": float(np.mean(fut))}


def sample_size(SU):
    g = SU[SU.lead == 2].copy()
    g["w"] = hits(g, "PERSIST").astype(float)
    m_ = g.groupby("tqi").size().mean()
    msb = g.groupby("tqi").w.mean().var(ddof=1) * m_
    msw = g.groupby("tqi").w.var(ddof=1).mean()
    icc = max(0.0, (msb - msw) / (msb + (m_ - 1) * msw))
    deff = 1 + (m_ - 1) * icc
    out = {"icc": icc, "design_effect": deff}
    for hw in (0.10, 0.15):
        ne = Z95 ** 2 * .75 * .25 / hw ** 2
        rows_ = int(np.ceil(ne * deff))
        out[f"hw_{hw}"] = {"n_eff": ne, "rows_4_areas": rows_, "quarters_4_areas": int(np.ceil(rows_ / 4)),
                           "quarters_balance_luzon_only": int(np.ceil(ne))}
    out["unseen_rows_today"] = 0
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    TIERS.mkdir(parents=True, exist_ok=True)
    rr, feats = T.load_rounds(), F.table()
    wf2, wf, logs, picks, fc = procedure(rr, feats)
    W = outer(rr, fc)
    W["tier"] = np.where(W.n_obs >= 8, "DEVELOPMENT-TEST", "TRAIN")
    keys = ["issue", "area", "lead", "target"]
    W[W.tier == "TRAIN"][keys].sort_values(keys).to_csv(TIERS / "TRAIN_rows.csv", index=False, lineterminator="\n")
    W[W.tier == "DEVELOPMENT-TEST"][keys].sort_values(keys).to_csv(TIERS / "DEVTEST_rows.csv", index=False, lineterminator="\n")
    SU = W[W.tier == "DEVELOPMENT-TEST"].reset_index(drop=True)
    wf.to_csv(OUT / "v4_walk_forward.csv", index=False)
    logs.to_csv(OUT / "v4_selection_log.csv", index=False)
    picks.to_csv(OUT / "v4_selected_by_issue.csv", index=False)
    SU.to_csv(OUT / "v4_devtest_predictions.csv", index=False)
    entries = wf[wf.model == "DELTA-X"].groupby(["issue", "lead"]).features.first().reset_index()
    entries.to_csv(OUT / "v4_deltax_feature_entries.csv", index=False)
    models = ["V4", *S4.CANDIDATES, *CONTEXT, "V2"]
    met = metrics(SU, models)
    met.to_csv(OUT / "v4_metrics.csv", index=False)
    rel = reliability(SU, ["V4", *S4.CANDIDATES])
    rel.to_csv(OUT / "v4_reliability.csv", index=False)
    bt = beats(SU)
    lo_d, lo = loao(rr, feats, wf2, SU)
    lo_d.to_csv(OUT / "v4_loao_lead2.csv", index=False)
    ov = overfit(rr, wf, picks, SU)
    ov.to_csv(OUT / "v4_overfitting.csv", index=False)
    g2 = SU[SU.lead == 2]
    served, served_log = S4.select(wf, rr, LAST)
    v4dev = {int(k): rel[(rel.model == "V4") & (rel.lead == k)].label.iloc[0] for k in S2.LEADS}
    verdict = {
        "status": "DEVELOPMENT ONLY: every row was seen before v4; the sealed tier (future quarters) has 0 scorable rows",
        "preregistration_sha256_lf": sha(V4 / "PREREGISTRATION.md", lf=True), "data_sha256": sha(T.SWS_ROUNDS),
        "features_sha256": sha(F.SNAPSHOTS), "tier_sha256": {p.name: sha(p) for p in sorted(TIERS.glob("*.csv"))},
        "selected_by_issue_counts": picks.selected.value_counts().to_dict(),
        "deltax_entries_nonempty": int((entries.features != "[]").sum()), "deltax_entries_total": int(len(entries)),
        "served_model": served, "served_selection_log": served_log,
        "claim_75_frozen_development": VD.claim_75(hits(g2, "V4"), g2.tqi.to_numpy(), sealed=False),
        "claim_75_amended_development": VD.claim_75(hits(g2, "V4", "tol_amended"), g2.tqi.to_numpy(), sealed=False),
        "beats_all_development": bt,
        "claim_75_sealed": {"frozen": VD.claim_75(np.array([]), np.array([]), sealed=True),
                            "amended": VD.claim_75(np.array([]), np.array([]), sealed=True)},
        "beats_all_sealed": VD.beats_all({}, testable=False),
        "development_label_by_lead": v4dev,
        "served_reliability_status_by_lead": {k: VD2.served_status(v, "NOT_YET_TESTABLE") for k, v in v4dev.items()},
        "loao_lead2": lo, "leakage_controls": leakage(rr, feats, SU), "sample_size": sample_size(SU),
    }
    (OUT / "v4_verdict.json").write_text(json.dumps(verdict, indent=1, default=float) + "\n", encoding="utf-8", newline="\n")
    pd.set_option("display.width", 250)
    print(picks.selected.value_counts().to_string())
    print(entries[entries.lead == 2].to_string())
    print(logs.dropna().round(3).to_string())
    print(met[met.lead == 2].round(3).to_string())
    print(rel.to_string())
    print(ov.round(3).to_string())
    print(json.dumps({k: v for k, v in verdict.items() if k not in ("served_selection_log",)}, indent=1, default=float))


if __name__ == "__main__":
    main()
