"""E26 section D + amendments A1/A2 (FROZEN_ANALYSIS_PROTOCOL.md): when can unseen quarters first support a valid
claim, and what information would make that plausible?

Monte Carlo from parameters fitted on authorized 2021-2026 data only:
  H  local level (sigma_eta by ML on the production rounds, sampling n = 600), started from the filtered state at
     2026-Q2; a quarter has no production round with the observed 2021-Q2..2026-Q2 frequency;
  D  D_HIER (shrunk province means, pooled AR(1)) fitted on 2021-Q1..2026-Q2, started from D(2026-Q2);
  label  S1 = H + 2D > tau, tau = median of every label published before the origin (actual 2021-2026 labels + the
     simulated ones); a quarter's label is published one quarter later (E23 rule).
Lead-1 evaluation dates accrue from target 2026-Q4. Baselines per date: persistence (last published label) and
calibrated persistence (Laplace rate of lag-1 label transitions under the current tau; an approximation of B1p).
The forecaster is CORRECTLY SPECIFIED (knows the true parameters; Kalman filter on the rounds it may see): an
optimistic upper bound for any real model. Scenarios (A2): S0 baseline; S_timely (one-quarter-fresher regional
reading); S_signal(rho) (a leading signal with correlation rho to the unknown regional change).
Claim rules: frozen e-process (section E: aGRAPA, lambda <= 0.5, e >= 40 vs both baselines) and A1 single look
(first year end with >= 12 unseen dates and evaluability; one-sided sign-flip, normal approximation, p < 0.025 vs
both baselines). Amendment A3 adds two references at the same look: always-HIGH and climatology (the published HIGH
share under the current tau); success needs p < 0.05/4 and a positive mean against all four. A3 adds no random draw,
so every A1/e-process number is unchanged by it.
Usage: python -B runner/horizon.py   -> runs/horizon.json, docs/HORIZON.md"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402

import numpy as np  # noqa: E402
from scipy.stats import norm  # noqa: E402

import e25lib as E  # noqa: E402
import pcf  # noqa: E402

EXP = guard.EXP
sys.path.insert(0, str(EXP / "backend_dev"))
from app.quarterly.ledger import E_THRESHOLD, LAMBDA_FIRST, LAMBDA_MAX, MIN_DATES, MIN_PER_CLASS  # noqa: E402

qk, qs = E.qk, E.qs
SEED, NPATH = 20261014, 10000
FIRST_TARGET, LAST_Q = qk("2026-Q4"), qk("2031-Q4")
SCENARIOS = [("S0", None), ("S_timely", None)] + [(f"S_signal_rho{r}", r) for r in (0.3, 0.5, 0.7, 0.9)]


def check_frozen():
    for ln in (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").splitlines():
        p = ln.split()
        if len(p) == 2 and len(p[0]) == 64 and hashlib.sha256((EXP / p[1]).read_bytes()).hexdigest() != p[0]:
            raise SystemExit(f"E26: {p[1]} differs from its frozen hash; stop.")


def samp_var(h):
    h = np.clip(h, 0.5, 99.5)
    return h * (100 - h) / 600.0


class EProc:
    """Vectorized aGRAPA e-process (identical rule to ledger.eprocess), updated only where a date exists."""

    def __init__(self, n):
        self.e = np.ones(n); self.k = np.zeros(n); self.mean = np.zeros(n); self.m2 = np.zeros(n)

    def update(self, d, mask):
        var = np.where(self.k > 0, self.m2 / np.maximum(self.k, 1), 0.0)
        den = var + self.mean ** 2
        lam = np.where(self.k == 0, LAMBDA_FIRST,
                       np.clip(np.divide(self.mean, den, out=np.zeros_like(den), where=den > 0), 0.0, LAMBDA_MAX))
        self.e = np.where(mask, self.e * (1 + lam * d), self.e)
        k1 = self.k + mask
        delta = d - self.mean
        newmean = np.where(mask, self.mean + delta / np.maximum(k1, 1), self.mean)
        self.m2 = np.where(mask, self.m2 + delta * (d - newmean), self.m2)
        self.mean, self.k = newmean, k1


def fit():
    rounds = E.load_rounds()
    comp, c26, D = E.load_components()
    T = E.Target("T1", "A", rounds, D)
    prod = rounds[rounds["definition_A"]]
    times, ys = prod["fieldwork_quarter"].map(qk).to_numpy(float), prod["H"].to_numpy(float)
    hf = pcf.h_forecast(times, ys, float(qk("2026-Q3")))
    window = [qs(i) for i in range(qk("2021-Q2"), qk("2026-Q2") + 1)]
    p_miss = 1 - len(set(prod["quarter"]) & set(window)) / len(window)
    Dm = {(r.province_code, qk(r.quarter)): float(r.D) for r in D.itertuples()}
    dh = E.d_hier(Dm, {}, qk("2026-Q3"), False)
    hist = T.V.pivot(index="tq", columns="province_code", values="v")[E.PROVS]
    return {"se": hf["sigma_eta"], "L0": hf["mu_H"], "P0": hf["filtered_var"], "p_miss": p_miss,
            "mu": np.array([dh["mu"][p] for p in E.PROVS]), "phi": dh["phi"], "s2": dh["sigma2"],
            "D0": np.array([Dm[(p, qk("2026-Q2"))] for p in E.PROVS]), "hist": hist.to_numpy()}


def simulate_truth(F, rng, n, Q):
    nQ = len(Q)
    eta = np.empty((n, nQ)); Hobs = np.full((n, nQ), np.nan); Dsim = np.empty((n, nQ, 5))
    e_prev = F["L0"] + rng.normal(0, np.sqrt(F["P0"]), n)
    d_prev = np.tile(F["D0"], (n, 1))
    for j in range(nQ):
        e_prev = e_prev + rng.normal(0, F["se"], n)
        eta[:, j] = e_prev
        has = rng.random(n) >= F["p_miss"]
        Hobs[:, j] = np.where(has, e_prev + rng.normal(0, 1, n) * np.sqrt(samp_var(e_prev)), np.nan)
        d_prev = F["mu"] + F["phi"] * (d_prev - F["mu"]) + rng.normal(0, np.sqrt(F["s2"]), (n, 5))
        Dsim[:, j, :] = d_prev
    xi = rng.normal(0, 1, (n, nQ))                       # signal noise (shared by every rho scenario)
    return eta, Hobs, Dsim, xi


def filter_states(F, Hobs, Q, n):
    Lk = np.full(n, F["L0"]); Pk = np.full(n, F["P0"]); last_t = np.full(n, float(qk("2026-Q2")))
    filt = {qk("2026-Q2"): (Lk.copy(), Pk.copy(), last_t.copy())}
    for j, q in enumerate(Q):
        obs = Hobs[:, j]
        has = ~np.isnan(obs)
        Pp = Pk + F["se"] ** 2 * (q - last_t)
        Fv = Pp + samp_var(np.where(has, obs, 15.0))
        K = Pp / Fv
        Lk = np.where(has, Lk + K * (np.nan_to_num(obs) - Lk), Lk)
        Pk = np.where(has, (1 - K) * Pp, Pk)
        last_t = np.where(has, q, last_t)
        filt[q] = (Lk.copy(), Pk.copy(), last_t.copy())
    return filt


def run_scenario(name, rho, F, eta, Hobs, Dsim, xi, filt, Q, n):
    se, mu, phi, s2, hist = F["se"], F["mu"], F["phi"], F["s2"], F["hist"]
    S1 = Hobs[:, :, None] + 2 * Dsim
    ep = {k: EProc(n) for k in ("a1", "b1", "ap", "bp", "aa", "ba", "ac", "bc")}   # a* accuracy, b* Brier
    sums = {k: np.zeros(n) for k in ep}; sq = {k: np.zeros(n) for k in ep}
    looked = np.zeros(n, bool); claim_a = np.zeros(n, bool); claim_b = np.zeros(n, bool)
    succ_a = np.zeros(n, bool); succ_b = np.zeros(n, bool)                       # A3
    dates = np.zeros(n, int); nH = np.zeros(n, int); nL = np.zeros(n, int)
    out = {}
    for tgt in range(FIRST_TARGET, LAST_Q + 1):
        jt, jl = Q.index(tgt), tgt - 2 - Q[0]                    # labels published at O(tgt-1): quarters <= tgt-2
        # jl = -1 for the first target (2026-Q4): only the actual 2021-2026-Q2 labels are published
        sim_lab = S1[:, : jl + 1, :]
        allv = np.concatenate([np.broadcast_to(hist.reshape(1, -1), (n, hist.size)), sim_lab.reshape(n, -1)], axis=1)
        tau = np.nanmedian(allv, axis=1)
        last = np.full((n, 5), np.nan)
        for jj in range(jl, -1, -1):
            m = np.isnan(last[:, 0]) & ~np.isnan(S1[:, jj, 0])
            last[m] = S1[m, jj, :]
        m = np.isnan(last[:, 0])
        last[m] = hist[-1]
        ylast = (last > tau[:, None]).astype(float)
        seq = np.concatenate([np.broadcast_to(hist, (n,) + hist.shape), sim_lab], axis=1)
        lab, valid = seq > tau[:, None, None], ~np.isnan(seq)
        prev, nxt, vv = lab[:, :-1, :], lab[:, 1:, :], valid[:, :-1, :] & valid[:, 1:, :]
        n1, k1 = (vv & prev).sum((1, 2)), (vv & prev & nxt).sum((1, 2))
        n0, k0 = (vv & ~prev).sum((1, 2)), (vv & ~prev & nxt).sum((1, 2))
        b1p = np.where(ylast == 1, ((k1 + 1) / (n1 + 2))[:, None], ((k0 + 1) / (n0 + 2))[:, None])
        clim = ((lab & valid).sum((1, 2)) / valid.sum((1, 2)))[:, None] * np.ones((1, 5))   # A3 climatology
        # forecaster information
        qinfo = tgt - 1 if name == "S_timely" else tgt - 2
        Lf, Pf, lt = filt[qinfo]
        gap = tgt - lt
        VH = Pf + se ** 2 * gap + samp_var(Lf)
        muH = Lf.copy()
        if rho is not None:                                       # leading signal of the change since the last round
            jlast = (lt - Q[0]).astype(int)
            eta_last = np.where(jlast >= 0, eta[np.arange(n), np.maximum(jlast, 0)], F["L0"])
            change = eta[:, jt] - eta_last
            sd_c = se * np.sqrt(gap)
            z = rho * change / sd_c + np.sqrt(1 - rho ** 2) * xi[:, jt]
            muH = muH + rho * sd_c * z
            VH = VH - (rho ** 2) * sd_c ** 2
        h = 2
        Dlast = Dsim[:, jl, :] if jl >= 0 else np.tile(F['D0'], (n, 1))    # D(2026-Q2) actual for the first target
        muD = mu + phi ** h * (Dlast - mu)
        VD = s2 * (1 - phi ** (2 * h)) / (1 - phi ** 2)
        pm = 1 - norm.cdf((tau[:, None] - muH[:, None] - 2 * muD) / np.sqrt(VH[:, None] + 4 * VD))
        exists = ~np.isnan(S1[:, jt, 0])
        y = np.where(np.isnan(S1[:, jt, :]), 0, (S1[:, jt, :] > tau[:, None])).astype(float)
        d = {"a1": ((ylast >= .5) != y).mean(1) - ((pm >= .5) != y).mean(1),
             "b1": ((ylast - y) ** 2).mean(1) - ((pm - y) ** 2).mean(1),
             "ap": ((b1p >= .5) != y).mean(1) - ((pm >= .5) != y).mean(1),
             "bp": ((b1p - y) ** 2).mean(1) - ((pm - y) ** 2).mean(1),
             "aa": (1 != y).mean(1) - ((pm >= .5) != y).mean(1),
             "ba": ((1 - y) ** 2).mean(1) - ((pm - y) ** 2).mean(1),
             "ac": ((clim >= .5) != y).mean(1) - ((pm >= .5) != y).mean(1),
             "bc": ((clim - y) ** 2).mean(1) - ((pm - y) ** 2).mean(1)}
        for k in ep:
            ep[k].update(d[k], exists)
            sums[k] += np.where(exists, d[k], 0.0); sq[k] += np.where(exists, d[k] ** 2, 0.0)
        dates += exists
        nH += np.where(exists, y.sum(1), 0).astype(int); nL += np.where(exists, (1 - y).sum(1), 0).astype(int)
        if tgt % 4 == 3:                                          # year end (Q4 target scored)
            ev = (dates >= MIN_DATES) & (nH >= MIN_PER_CLASS) & (nL >= MIN_PER_CLASS)
            look_now = ~looked & ev & (dates >= 12)

            def p1(k):
                return 1 - norm.cdf(np.divide(sums[k], np.sqrt(sq[k]), out=np.zeros(n), where=sq[k] > 0))
            claim_a |= look_now & (p1("a1") < 0.025) & (p1("ap") < 0.025)
            claim_b |= look_now & (p1("b1") < 0.025) & (p1("bp") < 0.025)
            succ_a |= look_now & np.all([(p1(k) < 0.05 / 4) & (sums[k] > 0) for k in ("a1", "ap", "aa", "ac")], axis=0)
            succ_b |= look_now & np.all([(p1(k) < 0.05 / 4) & (sums[k] > 0) for k in ("b1", "bp", "ba", "bc")], axis=0)
            looked |= look_now
            out[str(tgt // 4)] = {
                "scored_dates_median": float(np.median(dates)), "LOW_rows_median": float(np.median(nL)),
                "LOW_rows_p10_p90": [float(np.quantile(nL, .1)), float(np.quantile(nL, .9))],
                "P_evaluable": float(ev.mean()),
                "eprocess_P_claim_accuracy": float((ev & (ep["a1"].e >= E_THRESHOLD) & (ep["ap"].e >= E_THRESHOLD)).mean()),
                "eprocess_P_claim_brier": float((ev & (ep["b1"].e >= E_THRESHOLD) & (ep["bp"].e >= E_THRESHOLD)).mean()),
                "A1_P_look_done": float(looked.mean()), "A1_P_claim_accuracy": float(claim_a.mean()),
                "A1_P_claim_brier": float(claim_b.mean()),
                "A3_P_success_accuracy": float(succ_a.mean()), "A3_P_success_brier": float(succ_b.mean()),
                "mean_per_date_advantage": {k: float(np.nanmean(np.where(ep[k].k > 0, ep[k].mean, np.nan))) for k in ep},
                "e_median": {k: float(np.median(ep[k].e)) for k in ep}}
    return out


def main():
    check_frozen()
    F = fit()
    rng = np.random.default_rng(SEED)
    Q = list(range(qk("2026-Q3"), LAST_Q + 1))
    eta, Hobs, Dsim, xi = simulate_truth(F, rng, NPATH, Q)
    filt = filter_states(F, Hobs, Q, NPATH)
    res = {"params": {"sigma_eta": F["se"], "H_level_2026Q2": F["L0"], "H_filtered_var": F["P0"],
                      "p_missing_round": F["p_miss"], "D_phi": F["phi"], "D_sigma2": F["s2"],
                      "D_mu": dict(zip(E.PROVS, F["mu"].tolist())), "paths": NPATH, "seed": SEED},
           "scenarios": {}, "note": "optimistic: the simulated forecaster knows the true parameters"}
    for name, rho in SCENARIOS:
        res["scenarios"][name] = run_scenario(name, rho, F, eta, Hobs, Dsim, xi, filt, Q, NPATH)
    (EXP / "runs" / "horizon.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    L = ["# Evaluability horizon and signal requirements (Monte Carlo; parameters from authorized 2021-2026 data only)", "",
         f"`runner/horizon.py`, {NPATH} paths, seed {SEED}. Lead-1 dates accrue from target 2026-Q4. Fitted: regional "
         f"hunger random-walk innovation sd {F['se']:.2f} pp per quarter; level at 2026-Q2 {F['L0']:.2f}; P(no round in a "
         f"quarter) {F['p_miss']:.3f}; provincial D AR(1) phi {F['phi']:.2f}.",
         "", "The simulated forecaster KNOWS the true parameters, so every probability below is an upper bound for a real model.",
         "", "| Scenario | Year end | Dates (median) | LOW rows (median) | P(evaluable) | e-process: P(acc claim) | P(Brier claim) | A1 single look: P(acc claim) | P(Brier claim) | A3 success (all 4 references): P(acc) | P(Brier) | Mean Brier advantage vs persistence / vs calibrated / vs always-HIGH |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, by in res["scenarios"].items():
        for yr, v in by.items():
            L.append(f"| {name} | {yr} | {v['scored_dates_median']:.0f} | {v['LOW_rows_median']:.0f} | {v['P_evaluable']:.2f} | "
                     f"{v['eprocess_P_claim_accuracy']:.3f} | {v['eprocess_P_claim_brier']:.3f} | {v['A1_P_claim_accuracy']:.3f} | "
                     f"{v['A1_P_claim_brier']:.3f} | {v['A3_P_success_accuracy']:.3f} | {v['A3_P_success_brier']:.3f} | "
                     f"{v['mean_per_date_advantage']['b1']:.3f} / {v['mean_per_date_advantage']['bp']:.3f} / "
                     f"{v['mean_per_date_advantage']['ba']:.3f} |")
    (EXP / "docs" / "HORIZON.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
