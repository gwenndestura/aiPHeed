"""
E135 feature-influence optimization (protocol ca2269e): driver influence controlled through group prior scales and
inclusion, every choice made inside the walk-forward from past out-of-sample errors only. Candidates X-RED, X-NSD,
X-SEL, X-GREG, X-STACK, X-COMB (+ post-hoc reference X-EXCL), feature audit and trigger-group ablation.

    python -I runner/e135_run.py      (after E134 runner/e134_run.py)
"""
from __future__ import annotations

import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
OUT = ROOT / "out"
sys.path.insert(0, str(EXP / "E134_Information_Bottleneck" / "runner"))
import e134_run as E  # noqa: E402

R, M, X, L = E.R, E.M, E.X, E.L
warnings.filterwarnings("ignore")
POOL = ("A", "C", "E", "N", "V", "aR", "aP")
HFMX = ("A", "C", "E", "N", "V")
SGRID = (0.25, 0.5, 1.0, 2.0)
WGRID = (0.0, 0.25, 0.5, 0.75, 1.0)
MIN_PAST = 8
SELECTABLE = ["HFM-X", "SEAS-LLM", "FULL7", "X-RED", "X-NSD", "X-SEL", "X-GREG", "X-STACK", "X-COMB"]
NEW = ["FULL7", "X-RED", "X-NSD", "X-SEL", "X-GREG", "X-STACK", "X-COMB", "X-EXCL"]


# ------------------------------------------------------------------ fitting with group-specific prior scales
def fit_beta_vec(Y, Rr, idx, base, Z, w, groups, sds):
    if not groups:
        return base
    s2 = np.array([sds[g] for g in groups]) ** 2

    def obj(bv):
        f = M.Fit(**{**base.__dict__, "beta": dict(zip(groups, bv))})
        return -M.kfilter(Y, Rr, idx, f, R.BRK, Z, w)[2] + 0.5 * float(np.sum(np.square(bv) / s2))

    r = minimize(obj, np.full(len(groups), 0.1), method="L-BFGS-B", bounds=[(0.0, 10.0)] * len(groups))
    out = M.Fit(**{**base.__dict__, "beta": dict(zip(groups, map(float, r.x)))})
    out.ll = -float(r.fun)
    return out


_F: dict = {}


def predict_cfg(qa, issue, target, drv, adrv, groups: tuple, sds: dict):
    key = (issue, groups, tuple(sorted(sds.items())), len(qa))
    b = R.base_fits(qa)
    idx, Yd, Rr = b["idx"], b["Yd"], b["R"]
    if key not in _F:
        vals, last, w = drv["rice"].at(issue)
        av, al = adrv.at(issue)
        Z = [{**R.Drivers.z_for(vals, last, int(t) - 1), **E.AreaDrivers.z_for(av, al, int(t) - 1)} for t in idx]
        fit = fit_beta_vec(Yd, Rr, idx, b["HFM-NS-DES"], Z, w, groups, sds)
        x, P_, _, _ = M.kfilter(Yd, Rr, idx, fit, R.BRK, Z, w)
        _F[key] = (fit, x, P_, vals, last, w, av, al)
    fit, x, P_, vals, last, w, av, al = _F[key]
    upto = int(idx.max())
    steps = target - upto
    Zf = [{**R.Drivers.z_for(vals, last, upto + j), **E.AreaDrivers.z_for(av, al, upto + j)} for j in range(steps)]
    mean, var = M.forecast(x, P_, fit, steps, Zf, w, [upto + 1 + j == R.BRK for j in range(steps)])
    if target >= R.BRK:
        mean = mean + b["seas"][target % 4]
    Rm = np.array([np.nanmedian(Rr[:, a]) for a in range(M.NA)])
    return mean, np.sqrt(var + fit.tau2 + Rm), fit


def fixed_configs() -> dict:
    c = {"FULL7": (POOL, 1.0), "HFMX-s1": (HFMX, 1.0)}
    for g in POOL:
        c[f"FULL7-minus-{g}"] = (tuple(x for x in POOL if x != g), 1.0)
        c[f"only-{g}"] = ((g,), 1.0)
    for s in SGRID:
        c[f"HFMX-s{s:g}"] = (HFMX, s)
    return c


# ------------------------------------------------------------------ walk-forward
def _past(P, pol, k, issue):
    m = (P.policy == pol) & (P.lead == k) & (P.issue < issue) & (P.pub < issue)
    return P[m]


def _mse(g, col):
    return float(np.mean((g[col] - g["y_true"]) ** 2))


def run(P: pd.DataFrame, rr, drv, adrv) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = fixed_configs()
    for name in list(cfg) + ["X-SEL", "X-GREG"]:
        P[f"f_{name}"], P[f"sd_{name}"] = np.nan, np.nan
    groups_iter = list(P.groupby(["policy", "D", "lead"]))
    for (pol, D, k), g in groups_iter:
        issue, target = g["issue"].iloc[0], L.qi(g["target"].iloc[0])
        qa = X.asof(rr, issue)
        for name, (grp, s) in cfg.items():
            mean, sd, _ = predict_cfg(qa, issue, target, drv, adrv, grp, {x: s for x in grp})
            ai = [X.AREAS.index(a) for a in g["area"]]
            P.loc[g.index, f"f_{name}"], P.loc[g.index, f"sd_{name}"] = mean[ai], sd[ai]
    choices = []
    for (pol, k), gk in P.groupby(["policy", "lead"]):
        for D in sorted(gk["D"].unique(), key=L.qi):
            g = gk[gk.D == D]
            issue, target = g["issue"].iloc[0], L.qi(g["target"].iloc[0])
            qa = X.asof(rr, issue)
            past = _past(P, pol, k, issue)
            ai = [X.AREAS.index(a) for a in g["area"]]
            enough = len(past) >= MIN_PAST
            # X-NSD: global prior scale
            s_best = 1.0
            if enough:
                s_best = min(SGRID, key=lambda s: (_mse(past, f"f_HFMX-s{s:g}"), s))
            P.loc[g.index, "f_X-NSD"] = P.loc[g.index, f"f_HFMX-s{s_best:g}"]
            P.loc[g.index, "sd_X-NSD"] = P.loc[g.index, f"sd_HFMX-s{s_best:g}"]
            # X-SEL / X-GREG: lead-specific group inclusion
            incl = list(POOL)
            if enough:
                full = _mse(past, "f_FULL7")
                incl = [x for x in POOL if full < _mse(past, f"f_FULL7-minus-{x}")]
            grp = tuple(incl)
            mean, sd, _ = predict_cfg(qa, issue, target, drv, adrv, grp, {x: 1.0 for x in grp})
            P.loc[g.index, "f_X-SEL"], P.loc[g.index, "sd_X-SEL"] = mean[ai], sd[ai]
            sds = {x: (1.0 if x in incl else 0.25) for x in POOL}
            mean, sd, _ = predict_cfg(qa, issue, target, drv, adrv, POOL, sds)
            P.loc[g.index, "f_X-GREG"], P.loc[g.index, "sd_X-GREG"] = mean[ai], sd[ai]
            # X-STACK and X-COMB: regime-aware weights from past errors
            for name, a_col in (("X-STACK", "HFM-X"), ("X-COMB", "X-SEL")):
                w = 1.0
                ok = past[f"f_{a_col}"].notna() & past["f_SEAS-LLM"].notna() if enough else None
                if enough and ok.sum() >= MIN_PAST:
                    pp = past[ok]
                    w = min(WGRID, key=lambda w_: (float(np.mean((w_ * pp[f"f_{a_col}"] + (1 - w_) * pp["f_SEAS-LLM"] - pp["y_true"]) ** 2)), -w_))
                P.loc[g.index, f"f_{name}"] = w * P.loc[g.index, f"f_{a_col}"] + (1 - w) * P.loc[g.index, "f_SEAS-LLM"]
                P.loc[g.index, f"sd_{name}"] = w * P.loc[g.index, f"sd_{a_col}"] + (1 - w) * P.loc[g.index, "sd_SEAS-LLM"]
                choices.append({"policy": pol, "lead": int(k), "D": D, "issue": issue, "past_rows": len(past),
                                "procedure": name, "choice": w})
            choices.append({"policy": pol, "lead": int(k), "D": D, "issue": issue, "past_rows": len(past),
                            "procedure": "X-NSD", "choice": s_best})
            choices.append({"policy": pol, "lead": int(k), "D": D, "issue": issue, "past_rows": len(past),
                            "procedure": "X-SEL", "choice": "+".join(incl) or "none"})
    P["f_X-RED"], P["sd_X-RED"] = P["f_HFMX-s0.5"], P["sd_HFMX-s0.5"]
    P["f_X-EXCL"], P["sd_X-EXCL"] = P["f_X-minus-C"], P["sd_X-minus-C"]
    for m in NEW + [c for c in cfg]:
        P[f"lo80_{m}"] = P[f"f_{m}"] - X.Z80 * P[f"sd_{m}"]
        P[f"hi80_{m}"] = P[f"f_{m}"] + X.Z80 * P[f"sd_{m}"]
    return P, pd.DataFrame(choices)


# ------------------------------------------------------------------ evaluation helpers
def period_metrics(P, models):
    rows = []
    for (pol, k, per), g in P[P.policy == "P-DASH"].groupby(["policy", "lead", "period"]):
        for m in models:
            e = g[f"f_{m}"] - g["y_true"]
            rows.append({"set": f"period:{per}", "policy": pol, "lead": int(k), "model": m, "n": len(g),
                         "n_quarters": int(g["target"].nunique()), "mae": float(e.abs().mean()),
                         "rmse": float(np.sqrt((e ** 2).mean())), "bias": float(e.mean()),
                         "within_tolerance": float((e.abs() <= g["tol"]).mean())})
    return rows


def loo_audit(P) -> pd.DataFrame:
    """Leave-one-out from FULL7 and each-alone, P-DASH, S-U, Leads 1-4: effect on MAE, within, bias, high-tercile
    bias, by period and area, with the paired cluster bootstrap."""
    su = P[(P.policy == "P-DASH") & (P.n_obs >= 8)]
    rows = []
    for k, g in su.groupby("lead"):
        y, tol, tq = g["y_true"].to_numpy(), g["tol"].to_numpy(), g["target_q"].to_numpy()
        high = (pd.qcut(g["y_true"], 3, labels=False) == 2).to_numpy()
        full = g["f_FULL7"].to_numpy()
        for x in POOL:
            for kind, col in (("removed from FULL7", f"f_FULL7-minus-{x}"), ("alone (with history)", f"f_only-{x}")):
                f = g[col].to_numpy()
                rec = {"lead": int(k), "group": x, "test": kind, "rows": len(g),
                       "mae_full7": float(np.mean(np.abs(full - y))), "mae_variant": float(np.mean(np.abs(f - y))),
                       "rmse_full7": float(np.sqrt(np.mean((full - y) ** 2))), "rmse_variant": float(np.sqrt(np.mean((f - y) ** 2))),
                       "within_full7": float(np.mean(np.abs(full - y) <= tol)), "within_variant": float(np.mean(np.abs(f - y) <= tol)),
                       "bias_full7": float(np.mean(full - y)), "bias_variant": float(np.mean(f - y)),
                       "high_bias_full7": float(np.mean((full - y)[high])), "high_bias_variant": float(np.mean((f - y)[high])),
                       "p_full7_better_sq_error": L.cluster_boot_p((full - y) ** 2, (f - y) ** 2, tq)}
                for per, gp in g.groupby("period"):
                    ix = g.index.get_indexer(gp.index)
                    rec[f"dmae_{per}"] = float(np.mean(np.abs(f[ix] - y[ix])) - np.mean(np.abs(full[ix] - y[ix])))
                for a, ga in g.groupby("area"):
                    ix = g.index.get_indexer(ga.index)
                    rec[f"dmae_{a}"] = float(np.mean(np.abs(f[ix] - y[ix])) - np.mean(np.abs(full[ix] - y[ix])))
                rows.append(rec)
    d = pd.DataFrame(rows)
    d["delta_mae_variant_minus_full7"] = d["mae_variant"] - d["mae_full7"]
    d["delta_within_variant_minus_full7"] = d["within_variant"] - d["within_full7"]
    rem = d["test"] == "removed from FULL7"
    d["demonstrated_contribution"] = rem & (d["delta_mae_variant_minus_full7"] > 0) & (d["delta_within_variant_minus_full7"] < 0) & (d["p_full7_better_sq_error"] < 0.10)
    d["harmful"] = rem & (d["delta_mae_variant_minus_full7"] < 0) & (d["delta_within_variant_minus_full7"] >= 0) & (1 - d["p_full7_better_sq_error"] < 0.10)
    return d


def main():
    OUT.mkdir(exist_ok=True)
    P = pd.read_csv(EXP / "E134_Information_Bottleneck" / "out" / "e134_predictions.csv")
    P["issue"] = pd.to_datetime(P["issue"]).dt.date
    P["pub"] = pd.to_datetime(P["published_target"]).dt.date
    rr = X.rounds()
    drv = {"rice": R.Drivers("rice")}
    adrv = E.AreaDrivers()
    P, C = run(P, rr, drv, adrv)
    assert np.nanmax(np.abs(P["f_FULL7"] - P["f_E134-AREA-T"])) < 1e-6, "FULL7 must reproduce E134-AREA-T"
    assert np.nanmax(np.abs(P["f_HFMX-s1"] - P["f_HFM-X"])) < 1e-6, "HFMX-s1 must reproduce HFM-X"
    P.to_csv(OUT / "e135_predictions.csv", index=False)
    C.to_csv(OUT / "e135_nested_choices.csv", index=False)
    refs = ["PERSIST", "CLIM", "LLM", "SEAS-LLM", "HFM-X"]
    shared = P.dropna(subset=["f_RIDGE-ALL", "f_PSA-ONLY", "f_NLP-ONLY", "f_LGBM-ALL", "f_HYB-LGBM"])
    keys = set(zip(shared.policy, shared.area, shared.D, shared.lead))
    in_e132 = np.array([k in keys for k in zip(P.policy, P.area, P.D, P.lead)])
    r1, q1 = R.metrics(P, refs + NEW, "S-U", P.n_obs >= 8)
    r2, q2 = R.metrics(P, refs + R.E132_BASE + NEW, "S-E132", in_e132)
    Mt = pd.DataFrame(r1 + r2 + period_metrics(P, refs + NEW))
    Mt.to_csv(OUT / "e135_metrics.csv", index=False)
    L.dump({**q1, **q2}, OUT / "e135_rules.json")
    loo_audit(P).to_csv(OUT / "e135_loo_audit.csv", index=False)
    for st in ("S-U", "S-E132"):
        g = Mt[(Mt.set == st) & (Mt.policy == "P-DASH")]
        print(st)
        print(g.pivot_table(index="model", columns="lead", values="within_tolerance").round(3).to_string())
        print(g.pivot_table(index="model", columns="lead", values="mae").round(2).to_string())


if __name__ == "__main__":
    main()
