"""E26 sections A-C (FROZEN_ANALYSIS_PROTOCOL.md): outcome information budget, regional signal-to-noise, and the
value of information (VOI) of observations that are missing at the forecast origin. Diagnostics on development
quarters only; nothing here selects a model, threshold or target.
Usage: python -B runner/root_cause.py   -> runs/root_cause.json, runs/voi_predictions.csv"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402

import e23_lib as L  # noqa: E402
import e25lib as E  # noqa: E402
import pcf  # noqa: E402

EXP = guard.EXP
qk, qs = E.qk, E.qs
E25RUN = guard.E25_RUNS / "20261014T002026Z"


def check_frozen():
    for ln in (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").splitlines():
        p = ln.split()
        if len(p) == 2 and len(p[0]) == 64 and hashlib.sha256((EXP / p[1]).read_bytes()).hexdigest() != p[0]:
            raise SystemExit(f"E26: {p[1]} differs from its frozen hash; stop.")


# ================================================================================================ A. budget
def budget(rounds, D, T):
    prod = rounds[rounds["definition_A"]]
    allq = [qs(i) for i in range(qk("2021-Q1"), qk("2026-Q2") + 1)]
    lab = sorted(T.V["quarter"].unique(), key=qk)
    v = T.V.merge(D[["province_code", "quarter", "D"]], on=["province_code", "quarter"])
    H = v["quarter"].map(T.H)
    var_s = float(v["v"].var(ddof=0))
    res = json.loads((E25RUN / "results.json").read_text(encoding="utf-8"))
    leads = {k: {"dates": r["n_dates"], "HIGH": r["HIGH"], "LOW": r["LOW"], "label_changes": r["label_change_rows"]}
             for k, r in res["T1_A"]["R_A"]["by_lead"].items()}
    return {"quarters_in_window_2021Q1_2026Q2": len(allq), "production_sws_rounds": int(len(prod)),
            "labelled_quarters_reading_A": len(lab), "quarters_without_label": sorted(set(allq) - set(lab), key=qk),
            "independent_regional_outcome_series": 1,
            "independent_provincial_food_insecurity_outcomes_in_authorized_data": 0,
            "T1_rows": int(len(T.V)), "T1_rows_LOW_at_median_of_all": int((T.V["v"] <= T.V["v"].median()).sum()),
            "label_variance_share_regional_H": float(H.var(ddof=0) / var_s),
            "label_variance_share_2D": float((2 * v["D"]).var(ddof=0) / var_s),
            "label_variance_share_2cov": float(2 * np.cov(H, 2 * v["D"], ddof=0)[0, 1] / var_s),
            "E25_lead_table_R_A": leads,
            "provincial_D_persistence": _d_persistence(D)}


def _d_persistence(D):
    """Is the provincial part a stable local difference or a transient price fluctuation? Between-province
    variance of the province means of D (empirical Bayes, as D_HIER) vs the total variance of D."""
    Dm = {(r.province_code, qk(r.quarter)): float(r.D) for r in D.itertuples()}
    h = E.d_hier(Dm, {}, qk("2026-Q3"), False)
    tot = float(D["D"].var(ddof=1))
    raw = D.groupby("province_code")["D"].mean()
    return {"between_province_variance_of_means_EB": h["between_var"], "total_variance_D": tot,
            "persistent_share": h["between_var"] / tot if tot > 0 else None, "ar1_phi": h["phi"],
            "raw_province_means": {E.PNAME[k]: float(v) for k, v in raw.items()}}


# ================================================================================================ B. signal-to-noise
def signal_noise(rounds):
    r = rounds[rounds["definition_A"]].sort_values(["fieldwork_quarter", "published_eff"]).reset_index(drop=True)
    h = r["H"].to_numpy(float)
    dh = np.diff(h)
    out = {"n_changes": int(len(dh)), "var_observed_change": float(dh.var(ddof=1)),
           "mean_abs_change": float(np.abs(dh).mean())}
    for n in (300, 600):
        sv = np.array([pcf.samp_var(a, n) + pcf.samp_var(b, n) for a, b in zip(h[:-1], h[1:])])
        noise = float(sv.mean())
        true_var = max(out["var_observed_change"] - noise, 0.0)
        rho = np.sqrt(true_var / out["var_observed_change"]) if out["var_observed_change"] > 0 else 0.0
        out[f"n{n}"] = {"mean_sampling_variance_of_a_change": noise,
                        "share_of_change_variance_from_sampling": float(min(noise / out["var_observed_change"], 1.0)),
                        "signal_to_noise_sd_ratio": float(np.sqrt(true_var / noise)) if noise > 0 else None,
                        "P_observed_sign_equals_true_sign": float(0.5 + np.arcsin(rho) / np.pi),
                        "sampling_sd_of_one_round_at_H15": float(np.sqrt(pcf.samp_var(15.0, n)))}
    return out


# ================================================================================================ C. VOI
class InfoSet:
    """What is known at O(t). rounds_pub: per-round usable-from times. lab_shift: 0 -> labels through t-1;
    1 -> labels through t (D(t) complete and H(t) known)."""

    def __init__(self, name, rounds, D, lab_shift):
        self.name, self.rounds, self.lab_shift = name, rounds, lab_shift
        ru = rounds[rounds["definition_A"]]
        self.H = ru.groupby("quarter")["H"].mean()
        self.maxpub = ru.groupby("quarter")["published_eff"].max()
        v = D.merge(self.H.rename("H").reset_index(), on="quarter")
        v["S1"] = v["H"] + 2 * v["D"]
        self.S1 = {(r.province_code, qk(r.quarter)): float(r.S1) for r in v.itertuples()}
        self.labq = sorted({qk(q) for q in v["quarter"]})

    def known_quarters(self, t):
        O = E.origin(t)
        return [q for q in self.labq if q <= t - 1 + self.lab_shift and self.maxpub[qs(q)] < O]

    def last_S1(self, t, p):
        kq = self.known_quarters(t)
        return self.S1[(p, kq[-1])] if kq else np.nan


def make_sets(rounds, D):
    r1 = rounds.copy()
    prod = r1["definition_A"]
    end = r1["fieldwork_quarter"].map(lambda q: E.origin(qk(q)) - pd.Timedelta(days=1))   # last day of fieldwork quarter
    r1.loc[prod, "published_eff"] = np.minimum(r1.loc[prod, "published_eff"], end[prod])
    return {"I0": InfoSet("I0", rounds, D, 0), "I1": InfoSet("I1", r1, D, 0), "I3": InfoSet("I3", r1, D, 1)}


def tau_I0(S0: InfoSet, t):
    kq = S0.known_quarters(t)
    return float(np.median([S0.S1[(p, q)] for q in kq for p in E.PROVS]))


def d_fit_lag(Dm, t, k, lag, last_known):
    """OLS without intercept of D(t'+k) on D(t'-lag) over pairs with t'+k <= last_known (2021+ values only)."""
    X, y = [], []
    for tp in range(qk("2021-Q1") + lag, last_known - k + 1):
        for p in E.PROVS:
            a, b = Dm.get((p, tp - lag)), Dm.get((p, tp + k))
            if a is not None and b is not None:
                X.append([a])
                y.append(b)
    beta, sig = pcf.d_fit(np.asarray(X, float), np.asarray(y, float))
    return float(beta[0]), sig


def voi(rounds, D, Dm, Nm):
    sets = make_sets(rounds, D)
    S0 = sets["I0"]
    rows = []
    for k in (1, 2, 3):
        for t in range(qk("2022-Q1"), qk("2026-Q1") + 1):
            if t + k > qk("2026-Q2") or (E.PROVS[0], t + k) not in S0.S1:
                continue
            # protocol C: >= 8 labelled training TARGET quarters at lead k under I0 (the smallest set), i.e. known
            # labelled quarters v whose feature quarter v - k is in the window (fix: first version used 8 + k)
            if len([v for v in S0.known_quarters(t) if v - k >= qk("2021-Q1")]) < E.MIN_TRAIN_QUARTERS:
                continue
            tau = tau_I0(S0, t)
            # PCF21_NOW (E25 definition): D on [Dnow(t'), D(t'-1)], pairs with t'+k <= t-1. Under I3 D(t) is complete
            # and supersedes its months 1-2, so PCF21_NOW is PCF21 by construction there.
            dm_now = E.d_ols(Dm, Nm, t, k, True)
            if dm_now is None:
                raise SystemExit(f"PCF21_NOW unavailable at {qs(t)} lead {k}: rows would differ across models")
            for nm, S in sets.items():
                last_known = t - 1 + S.lab_shift
                # H inputs usable at O(t) under the set
                O = E.origin(t)
                rr = S.rounds[(S.rounds["published_eff"] < O) & S.rounds["definition_A"]]
                hf = pcf.h_forecast(rr["fieldwork_quarter"].map(qk).to_numpy(float), rr["H"].to_numpy(float),
                                    float(t + k))
                beta, sig = d_fit_lag(Dm, t, k, 1 - S.lab_shift, last_known)
                # B1p: pairs (y_last at O(t'), y(t'+k)) with outer tau, targets known under the set at O(t)
                tr = []
                for v in S.known_quarters(t):
                    tp = v - k
                    if tp < qk("2021-Q1"):
                        continue
                    for p in E.PROVS:
                        ls = S.last_S1(tp, p)
                        if ls == ls:
                            tr.append({"y_last": float(ls > tau), "y": int(S.S1[(p, v)] > tau)})
                tr = pd.DataFrame(tr)
                for p in E.PROVS:
                    y = int(S0.S1[(p, t + k)] > tau)
                    ylast = float(S.last_S1(t, p) > tau)
                    xd = Dm.get((p, t - 1 + S.lab_shift))
                    muD = beta * xd
                    p_pcf = pcf.p_high(tau, hf["mu_H"], hf["V_H"], muD, sig)
                    Hr = S0.H[qs(t + k)]
                    p_or = float(1 - norm.cdf((tau - Hr - 2 * muD) / max(2 * sig, 1e-9)))
                    b1p = float(E.calibrated_persistence(tr, [ylast])[0]) if len(tr) else 0.5
                    if S.lab_shift:
                        p_now = p_pcf
                    else:
                        muDn, sdn = E.d_ols_predict(dm_now, Dm, Nm, p, t)
                        p_now = pcf.p_high(tau, hf["mu_H"], hf["V_H"], muDn, sdn)
                    for mdl, sc in (("B1", ylast), ("B1p", b1p), ("PCF21", p_pcf), ("PCF21_NOW", p_now),
                                    ("ORACLE_H", p_or)):
                        rows.append({"set": nm, "lead": k, "t": qs(t), "target_quarter": qs(t + k), "province_code": p,
                                     "model": mdl, "score": float(sc), "y": y, "y_last_set": ylast, "tau": tau,
                                     "n_rounds": int(len(rr))})
    P = pd.DataFrame(rows)
    P = P[~((P["model"] == "ORACLE_H") & (P["set"] != "I0"))].copy()
    P.loc[P["model"] == "ORACLE_H", "set"] = "IO"
    out = {"rows": int(len(P)), "by_lead": {}}
    for k, g in P.groupby("lead"):
        res = {}
        base0 = g[(g["set"] == "I0") & (g["model"] == "B1")].sort_values(["t", "province_code"])
        for (s, m), gm in g.groupby(["set", "model"]):
            gm = gm.sort_values(["t", "province_code"])
            mt = L.cls_metrics(gm["y"], gm["score"])
            chg = gm["y"].to_numpy() != gm["y_last_set"].to_numpy()
            cor = (gm["score"].to_numpy() >= .5).astype(int) == gm["y"].to_numpy()
            b_same = g[(g["set"] == (s if s != "IO" else "I0")) & (g["model"] == "B1")].sort_values(["t", "province_code"])
            d0 = pd.Series((gm["score"].to_numpy() - gm["y"].to_numpy()) ** 2 -
                           (base0["score"].to_numpy() - base0["y"].to_numpy()) ** 2).groupby(gm["t"].to_numpy()).mean()
            ds = pd.Series((gm["score"].to_numpy() - gm["y"].to_numpy()) ** 2 -
                           (b_same["score"].to_numpy() - b_same["y"].to_numpy()) ** 2).groupby(gm["t"].to_numpy()).mean()
            res[f"{s}|{m}"] = {"n_dates": int(gm["t"].nunique()), "HIGH": mt["HIGH"], "LOW": mt["LOW"],
                               "accuracy": mt["accuracy"], "brier": mt["Brier"], "auc": mt["ROC_AUC"],
                               "label_changes_vs_set_last_label": int(chg.sum()),
                               "changes_anticipated": int((cor & chg).sum()),
                               "brier_vs_B1_I0_p": L.signflip_brier(d0.to_numpy())["p_one_sided"],
                               "brier_vs_B1_I0_mean_diff": float(d0.mean()),
                               "brier_vs_B1_same_set_p": L.signflip_brier(ds.to_numpy())["p_one_sided"],
                               "brier_vs_B1_same_set_mean_diff": float(ds.mean())}
        out["by_lead"][str(int(k))] = res
    return out, P


def main():
    check_frozen()
    rounds = E.load_rounds()
    comp, c26, D = E.load_components()
    mon, Dnow, _ = E.load_monthly(c26, comp)
    T = E.Target("T1", "A", rounds, D)
    Dm = {(r.province_code, qk(r.quarter)): float(r.D) for r in D.itertuples()}
    Nm = {(r.province_code, qk(r.quarter)): float(r.Dnow) for r in Dnow.itertuples()}
    out = {"A_budget": budget(rounds, D, T), "B_signal_noise": signal_noise(rounds)}
    out["C_voi"], P = voi(rounds, D, Dm, Nm)
    b = P.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode()
    (EXP / "runs" / "voi_predictions.csv").write_bytes(b)
    out["C_voi"]["predictions_sha256"] = hashlib.sha256(b).hexdigest()
    out["window_log"] = E.WINDOW_LOG
    (EXP / "runs" / "root_cause.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "window_log"}, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
