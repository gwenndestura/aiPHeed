"""
E143 audit of E142 (reads E142's locked out-of-fold files; E137-E142 code and results are not modified).

    python -m app.e143.audit      -> data/e143/out/audit.json

A  gate decomposition by origin (what each origin adds to the pooled difference vs persistence / region's previous)
B  noise floor (irreducible expected Brier from survey error) and power (minimum detectable difference)
C  transition identification: deviation correlations for EVERY measured pair of rounds (gaps 8, 12, 16, 20, 24
   quarters), the Markov product test, and fits of three transition forms
D  DIAGNOSTIC counterfactual at O1 (persistence a model trained on 2013 alone could not estimate)
E  sensitivity of the O2/O3 forecasts to persistence, transition form, survey error and reference-quarter assignment
F  structural-level instability (region-bootstrap spread of the level vs the deviation spread)
G  feature audit: province-specificity, within-province variation, between-round change vs measured change
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm, spearmanr
from sklearn.model_selection import GroupKFold

from app.e137 import model as M137
from app.e138 import where as WH
from app.e139 import model as M9
from app.e140 import model as M140
from app.e141 import evaluate as E141
from app.e141 import panel as P
from app.e142 import OUT as O142
from app.e142 import evaluate as E142
from app.e142 import model as M
from app.e143 import OUT

SEED = 20261106
FEATS = {"market": M9.MKT, "climate": M9.CLI, "poverty": M9.POV + M9.DENS}
PAIRS = [("NNS2013", "FNRI2015"), ("FNRI2015", "ENNS2018"), ("FNRI2015", "ENNS2019"),
         ("NNS2013", "ENNS2018"), ("NNS2013", "ENNS2019")]
H_LIVE = {"Batangas (2015)": 46, "Laguna (2018)": 34, "Quezon (2019)": 30}


def eb(p, q):
    return M137.expected_brier(p, q)


def _boot_regions(d, fn, rng, n=1000):
    regs = d["region"].unique()
    g = {r: d[d["region"] == r] for r in regs}
    v = [fn(pd.concat([g[r] for r in rng.choice(regs, len(regs))])) for _ in range(n)]
    return [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]


# --- A, B -------------------------------------------------------------------------------------------------------
def gate_decomposition(R, res, rng):
    out, N = {}, len(R)
    for o, g in R.groupby("origin"):
        d = {"n": int(len(g)), "noise_floor": float(np.mean(g["q"] * (1 - g["q"]))),
             "eb": {m: eb(g[m], g["q"]) for m in ("STATE-LGBM", "PERS", "REGPREV", "LGBM", "NAT")}}
        for b in ("PERS", "REGPREV"):
            bb = WH.boot(g, "STATE-LGBM", b, rng)
            d[f"vs_{b}"] = {"diff": bb["diff"], "ci95": bb["ci95"], "contribution_to_pooled": bb["diff"] * len(g) / N}
        out[o] = d
    floor = float(np.mean(R["q"] * (1 - R["q"])))
    vs = res["rolling"]["vs"]["STATE-LGBM"]
    power = {}
    for b in ("PERS", "REGPREV"):
        se, diff = vs[b]["se"], vs[b]["diff"]
        mde = 2.80 * se                                   # two-sided 5 %, 80 % power
        power[b] = {"diff": diff, "se": se, "mde80": mde,
                    "evidence_multiple_needed_for_observed_diff": (mde / abs(diff)) ** 2 if diff < 0 else None}
    return {"by_origin": out, "pooled_noise_floor": floor,
            "pooled_reducible": {m: res["rolling"]["pooled"][m]["expected_brier"] - floor for m in ("STATE-LGBM", "PERS", "REGPREV")},
            "power": power, "n_regions": int(R["region"].nunique())}


# --- C ------------------------------------------------------------------------------------------------------------
def _dev(X, kind="lgbm"):
    g = X["region"].values
    mu = np.full(len(X), np.nan)
    for a, b in GroupKFold(5).split(X, groups=g):
        mu[b] = M._Mu(kind).make().fit(X.iloc[a]).predict_y(X.iloc[b])
    return X.assign(mu=mu, dev=X["y"].values - mu)


def _pair_stats(D, a, b):
    A = D[D["survey"] == a].set_index("key")
    B = D[D["survey"] == b].set_index("key")
    k = A.index.intersection(B.index)
    A, B = A.loc[k], B.loc[k]
    ta = max(0.01, float(np.mean(A["dev"] ** 2 - A["se_y"] ** 2)))
    tb = max(0.01, float(np.mean(B["dev"] ** 2 - B["se_y"] ** 2)))
    return k, A, B, float(np.mean(A["dev"].values * B["dev"].values) / np.sqrt(ta * tb))


def transition_identification(X, rng):
    out = {}
    for kind in ("lgbm", "ridge"):
        D = _dev(X, kind)
        pairs = []
        for a, b in PAIRS:
            k, A, B, c = _pair_stats(D, a, b)
            h = M.ROUND_QUARTER[b] - M.ROUND_QUARTER[a]
            DD = pd.DataFrame({"region": A["region"].values, "da": A["dev"].values, "db": B["dev"].values,
                               "sa": A["se_y"].values, "sb": B["se_y"].values})

            def f(s):
                ta = max(0.01, np.mean(s["da"] ** 2 - s["sa"] ** 2))
                tb = max(0.01, np.mean(s["db"] ** 2 - s["sb"] ** 2))
                return np.mean(s["da"] * s["db"]) / np.sqrt(ta * tb)
            pairs.append({"from": a, "to": b, "gap_quarters": int(h), "n": int(len(k)), "corr": c,
                          "ci95": _boot_regions(DD, f, rng)})
        P_ = {(p["from"], p["to"]): p for p in pairs}
        markov = {}
        for mid, end in (("ENNS2018", "ENNS2018"), ("ENNS2019", "ENNS2019")):
            c8, cmid, clong = P_[("NNS2013", "FNRI2015")]["corr"], P_[("FNRI2015", mid)]["corr"], P_[("NNS2013", end)]["corr"]
            markov[f"2013->{end[-4:]}"] = {"measured": clong, "markov_prediction_c(2013,2015)xc(2015,%s)" % end[-4:]: c8 * cmid,
                                          "excess_over_markov": clong - c8 * cmid}
        h = np.array([p["gap_quarters"] for p in pairs], float)
        c = np.array([p["corr"] for p in pairs])
        w = np.array([p["n"] for p in pairs], float)
        fits = {}
        e = minimize(lambda t: np.sum(w * (c - t[0] ** h) ** 2), [0.93], bounds=[(0, 1)]).x
        fits["EXP (AR(1))"] = {"phi": float(e[0]), "sse": float(np.sum(w * (c - e[0] ** h) ** 2))}
        pm = minimize(lambda t: np.sum(w * (c - (t[0] + (1 - t[0]) * t[1] ** h)) ** 2), [0.4, 0.8], bounds=[(0, 1), (0, 1)]).x
        fits["PERM+AR (permanent share rho)"] = {"rho": float(pm[0]), "phi": float(pm[1]),
                                                 "sse": float(np.sum(w * (c - (pm[0] + (1 - pm[0]) * pm[1] ** h)) ** 2))}
        cc = float(np.sum(w * c) / np.sum(w))
        fits["CONST (no decay)"] = {"c": cc, "sse": float(np.sum(w * (c - cc) ** 2))}
        live = {}
        for prov, hh in H_LIVE.items():
            live[prov] = {"EXP": float(e[0] ** hh), "PERM+AR": float(pm[0] + (1 - pm[0]) * pm[1] ** hh), "CONST": cc,
                          "E142 final (phi 0.935)": float(0.935 ** hh)}
        out[kind] = {"pairs": pairs, "markov_test": markov, "fits": fits, "weight_on_last_survey_live": live,
                     "max_observed_gap_quarters": int(h.max())}
    return out


# --- D, E ---------------------------------------------------------------------------------------------------------
def _state_eb(sm, te, prev, h=None, phi=None, form=None, se_scale=1.0):
    """EB of a fitted StateModel on target rows, with persistence / form / survey error overridden (sensitivity)."""
    phi0 = sm.phi_
    mu, mu_prev = sm._mu(te), sm._mu(prev)
    se_p = te["prev_se_y"].values * se_scale
    t2 = sm.tau2_
    k = t2 / (t2 + se_p ** 2)
    m0 = k * (te["prev_y"].values - mu_prev)
    p0 = t2 * se_p ** 2 / (t2 + se_p ** 2)
    hh = np.asarray(M.gap_quarters(te) if h is None else h, float)
    ph = phi0 if phi is None else phi
    wgt = form(hh) if form is not None else ph ** hh
    yhat = mu + wgt * m0
    V = wgt ** 2 * p0 + t2 * (1 - wgt ** 2)
    return eb(norm.cdf(yhat / np.sqrt(V)), te["q"].values), yhat, V


def o1_counterfactual(X, R, phi_full, rng):
    tr, te = X[X["survey"] == "NNS2013"], X[X["survey"] == "FNRI2015"].copy()
    prev = E142._prev_rows(X, te)
    sm = M.StateModel("lgbm").fit(tr)
    out = {"label": "DIAGNOSTIC ONLY: an O1 model cannot estimate persistence (no transition in 2013 alone)"}
    Rs = R.copy()
    for name, ph in (("phi 0 (E142, structural only)", 0.0), (f"phi {phi_full} (estimated from LATER rounds: leaky)", phi_full),
                     ("phi 1 (assumed: deviation fully persists, shrunk for survey error)", 1.0)):
        e, yhat, V = _state_eb(sm, te, prev, phi=ph)
        Rs.loc[Rs["origin"] == "O1", "CF"] = norm.cdf(yhat / np.sqrt(V))
        Rs.loc[Rs["origin"] != "O1", "CF"] = Rs.loc[Rs["origin"] != "O1", "STATE-LGBM"]
        out[name] = {"O1_eb": e, "pooled_eb": eb(Rs["CF"], Rs["q"]),
                     "pooled_vs_PERS": WH.boot(Rs, "CF", "PERS", rng), "pooled_vs_REGPREV": WH.boot(Rs, "CF", "REGPREV", rng)}
    return out


def sensitivity(X):
    out = {}
    for oid, train_rounds, target in E141.ORIGINS[1:]:
        tr, te = X[X["survey"].isin(train_rounds)], X[X["survey"] == target]
        prev = E142._prev_rows(X, te)
        sm = M.StateModel("lgbm").fit(tr)
        d = {"fitted_phi": sm.phi_, "tau2": sm.tau2_, "target_gap": int(M.gap_quarters(te).iloc[0]),
             "eb_fitted": _state_eb(sm, te, prev)[0]}
        d["phi_grid"] = {str(ph): _state_eb(sm, te, prev, phi=ph)[0] for ph in (0.0, 0.85, 0.9, 0.935, 0.95, 0.97, 0.99, 1.0)}
        d["survey_error_scale"] = {str(s): _state_eb(sm, te, prev, se_scale=s)[0] for s in (0.5, 0.75, 1.25, 1.5)}
        d["no_horizon_growth (weight phi^8 regardless of gap)"] = _state_eb(sm, te, prev, h=np.full(len(te), 8.0))[0]
        out[oid] = d
    # reference-quarter assignment: ENNS rounds shifted by -2..+2 quarters (fieldwork months not printed); refit O3
    shifts = {}
    saved = dict(M.ROUND_QUARTER)
    try:
        for s in (-2, -1, 1, 2):
            M.ROUND_QUARTER.update({"ENNS2018": saved["ENNS2018"] + s, "ENNS2019": saved["ENNS2019"] + s})
            tr, te = X[X["survey"] != "ENNS2019"], X[X["survey"] == "ENNS2019"]
            sm = M.StateModel("lgbm").fit(tr)
            shifts[f"ENNS {s:+d} q"] = {"phi": sm.phi_, "O3_eb": _state_eb(sm, te, E142._prev_rows(X, te))[0]}
    finally:
        M.ROUND_QUARTER.clear()
        M.ROUND_QUARTER.update(saved)
    out["reference_quarter_shift_O3"] = shifts
    return out


# --- F, G ---------------------------------------------------------------------------------------------------------
def level_instability(X, rng, B=20):
    tr, te = X[X["survey"] != "ENNS2019"], X[X["survey"] == "ENNS2019"]
    regs = tr["region"].unique()
    out = {}
    for kind in ("lgbm", "ridge"):
        preds = []
        for _ in range(B):
            b = pd.concat([tr[tr["region"] == r] for r in rng.choice(regs, len(regs))]).reset_index(drop=True)
            preds.append(M._Mu(kind).make().fit(b).predict_y(te))
        sd = np.asarray(preds).std(axis=0)
        out[kind] = {"mean_sd_of_level_across_refits": float(sd.mean()), "max_sd": float(sd.max())}
    out["deviation_sd_sqrt_tau2_O3"] = float(np.sqrt(M.StateModel("lgbm").fit(tr).tau2_))
    return out


def feature_audit(X, rng):
    D = _dev(X)
    T = D.merge(D[["key", "survey"] + sum(FEATS.values(), []) + ["y", "se_y", "dev"]], left_on=["key", "prev_survey"],
                right_on=["key", "survey"], suffixes=("", "_p"))
    dy = T["y"] - T["y_p"]
    noise = float(np.mean(T["se_y"] ** 2 + T["se_y_p"] ** 2))
    rel = {"var_measured_change": float(dy.var()), "mean_survey_error_var_of_change": noise,
           "share_of_change_variance_that_is_real": float(max(0.0, 1 - noise / dy.var())),
           "level_reliability_tau2_over_tau2_plus_se2": float(M137.tau2(X) / (M137.tau2(X) + np.mean(X["se_y"] ** 2)))}
    feats = {}
    for grp, cols in FEATS.items():
        for c in cols:
            v = X[["key", "region", "survey", c]].dropna()
            tot = v[c].var()
            within_prov = v.groupby("key")[c].transform(lambda s: s - s.mean()).var() / tot if tot else np.nan
            within_reg_round = v.groupby(["region", "survey"])[c].transform(lambda s: s - s.mean()).var() / tot if tot else np.nan
            dx = (T[c] - T[f"{c}_p"])
            ok = dx.notna() & dy.notna()
            S = pd.DataFrame({"region": T["region"][ok], "dx": dx[ok], "dy": dy[ok], "dd": (T["dev"] - T["dev_p"])[ok]})
            rho = float(spearmanr(S["dx"], S["dy"]).statistic) if S["dx"].nunique() > 2 else np.nan
            feats[c] = {"group": grp, "coverage": float(X[c].notna().mean()),
                        "share_variance_within_province": float(within_prov),
                        "share_variance_between_provinces_within_region_round": float(within_reg_round),
                        "transitions_where_feature_changed": int((dx[ok].abs() > 1e-9).sum()), "n_transitions": int(ok.sum()),
                        "rank_corr_change_vs_measured_change": rho,
                        "ci95": _boot_regions(S, lambda s: spearmanr(s["dx"], s["dy"]).statistic, rng, 500)
                        if S["dx"].nunique() > 2 else None}
    return {"change_reliability": rel, "features": feats}


def run():
    E142.verify_lock()
    rng = np.random.default_rng(SEED)
    res = json.loads((O142 / "results.json").read_text())
    R = pd.read_csv(O142 / "oof_rolling.csv")
    X = P.data(1)
    out = {"inputs": "E142 locked results.json and oof_rolling.csv; E141 panel (Lead 1)"}
    out["A_B_gate_decomposition_noise_power"] = gate_decomposition(R, res, rng)
    print("A/B", flush=True)
    out["C_transition_identification"] = ti = transition_identification(X, rng)
    print("C", flush=True)
    out["D_o1_counterfactual"] = o1_counterfactual(X, R, 0.935, rng)
    print("D", flush=True)
    out["E_sensitivity"] = sensitivity(X)
    print("E", flush=True)
    out["F_level_instability"] = level_instability(X, rng)
    out["G_feature_audit"] = feature_audit(X, rng)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "audit.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    return out


if __name__ == "__main__":
    run()
