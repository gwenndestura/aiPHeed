"""E25 step 2: simulated power for each idea, on synthetic data only (no observed outcome is used).

Design quantities (number of forecast dates, rows per date, leads, months) mirror this study; process parameters
are a declared GRID of plausible values, not estimates from the test quarters. Every test is the one the frozen
protocol uses: exact one-sided sign-flip over forecast dates (Monte Carlo above 16 dates, blocked for monthly
overlap), alpha = 0.05.
Writes runs/power_sim.json and docs/POWER_SIMULATION.md.  Seed 20261014."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
from scipy.stats import norm

EXP = Path(__file__).resolve().parents[1]
SEED = 20261014
REPS = 2000
ALPHA = 0.05
_SIGNS = {}


def signs(n):
    if n not in _SIGNS:
        if n <= 16:
            _SIGNS[n] = np.array(list(itertools.product([1.0, -1.0], repeat=n)))
        else:
            _SIGNS[n] = np.random.default_rng(SEED).choice([1.0, -1.0], size=(20000, n))
    return _SIGNS[n]


def pval(d):
    d = np.asarray(d, float)
    S = signs(len(d))
    return float(((S * d[None, :]).mean(1) >= d.mean() - 1e-12).mean())


# ------------------------------------------------------------------------------------------ A: accuracy vs persistence
def sim_accuracy(n_dates, change_rate, anticipate, false_flip, rng):
    hits = 0
    for _ in range(REPS):
        diffs = []
        for _d in range(n_dates):
            ch = rng.random(5) < change_rate                 # rows whose label changed (persistence wrong)
            fixed = ch & (rng.random(5) < anticipate)        # model right where persistence is wrong
            broke = (~ch) & (rng.random(5) < false_flip)     # model wrong where persistence is right
            diffs.append((fixed.sum() - broke.sum()) / 5.0)
        hits += pval(diffs) < ALPHA
    return hits / REPS


# ------------------------------------------------------------------------------------------ B: structural (H + 2D)
def sim_structural(n_dates, sigma_eta, phi_d, sd_d, leads, rng, n_hist=12, se_s=1.5):
    """Latent regional level H (random walk, innovation sd sigma_eta) observed with SWS sampling error se_s;
    provincial D AR(1); label = 1[H_obs + 2 D > tau], tau = median of the history. Forecasters at each date:
    B1 (last label), B1p (Laplace rate given last label, from the simulated history), PCF-like (correct structure,
    parameters known: P(H+2D>tau) from the last observation). Returns power of PCF vs B1 and vs B1p (Brier), and
    of PCF vs B1 on accuracy, pooling the given leads per date (each date once)."""
    res = {"vsB1_brier": 0, "vsB1p_brier": 0, "vsB1_acc": 0}
    for _ in range(REPS):
        T = n_hist + n_dates + max(leads) + 2
        h = 12 + np.cumsum(rng.normal(0, sigma_eta, T))
        hobs = h + rng.normal(0, se_s, T)
        D = np.zeros((5, T))
        for t in range(1, T):
            D[:, t] = phi_d * D[:, t - 1] + rng.normal(0, sd_d * np.sqrt(1 - phi_d ** 2), 5)
        S = hobs[None, :] + 2 * D
        dB1, dB1p, aB1 = [], [], []
        for j in range(n_dates):
            t = n_hist + j                                   # origin: last known quarter t-1
            tau = np.median(S[:, :t])
            ylast = (S[:, t - 1] > tau).astype(float)
            # B1p from history pairs (lead 1 transitions) at this origin
            yh = (S[:, :t] > tau).astype(float)
            pr = {}
            for yl in (0.0, 1.0):
                m = yh[:, :-1] == yl
                pr[yl] = (yh[:, 1:][m].sum() + 1) / (m.sum() + 2)
            db, dbp, da = [], [], []
            for k in leads:
                tgt = t - 1 + k + 1                          # lead k: target t+k (last known t-1)
                y = (S[:, tgt] > tau).astype(float)
                gap = tgt - (t - 1)
                vH = sigma_eta ** 2 * gap + se_s ** 2 + se_s ** 2
                muD = phi_d ** gap * D[:, t - 1]
                vD = sd_d ** 2 * (1 - phi_d ** (2 * gap))
                p = 1 - norm.cdf((tau - hobs[t - 1] - 2 * muD) / np.sqrt(vH + 4 * vD))
                b1p = np.where(ylast == 1, pr[1.0], pr[0.0])
                db.append(np.mean((ylast - y) ** 2) - np.mean((p - y) ** 2))
                dbp.append(np.mean((b1p - y) ** 2) - np.mean((p - y) ** 2))
                da.append(np.mean((p >= .5) == y) - np.mean(ylast == y))
            dB1.append(np.mean(db)); dB1p.append(np.mean(dbp)); aB1.append(np.mean(da))
        res["vsB1_brier"] += pval(dB1) < ALPHA
        res["vsB1p_brier"] += pval(dB1p) < ALPHA
        res["vsB1_acc"] += pval(aB1) < ALPHA
    return {k: v / REPS for k, v in res.items()}


# ------------------------------------------------------------------------------------------ D: monthly D (block sign-flip)
def sim_monthly(n_origins, phi_m, rng, block=3):
    """Monthly relative inflation AR(1); target = sign of the mean of the next 3 months; AR forecaster vs sign
    persistence on Brier; per-origin differences averaged within non-overlapping blocks of 3 origins."""
    hits = 0
    for _ in range(REPS):
        T = n_origins + 30
        x = np.zeros((5, T))
        for t in range(1, T):
            x[:, t] = phi_m * x[:, t - 1] + rng.normal(0, np.sqrt(1 - phi_m ** 2), 5)
        d = []
        for j in range(n_origins):
            t = 24 + j
            fut = x[:, t + 1:t + 4].mean(1)
            y = (fut > 0).astype(float)
            mu = np.mean([phi_m ** h for h in (1, 2, 3)]) * x[:, t]
            var = np.var([0]) + 1 / 3 * (1 - phi_m ** 2)       # rough predictive variance of the 3-month mean
            p = norm.cdf(mu / np.sqrt(max(var, 1e-6)))
            pers = (x[:, t] > 0).astype(float)
            d.append(np.mean((pers - y) ** 2) - np.mean((p - y) ** 2))
        d = np.asarray(d)
        nb = len(d) // block
        hits += pval(d[:nb * block].reshape(nb, block).mean(1)) < ALPHA
    return hits / REPS


# ------------------------------------------------------------------------------------------ E: leading indicator for H
def sim_leading(n_trans, rho, rng):
    """n_trans round-to-round hunger changes; indicator correlated rho with the next change. Permutation test of
    the slope (one-sided), and the share of runs where a ridge-shrunk indicator lowers out-of-sample MSE."""
    hits, better = 0, 0
    for _ in range(REPS):
        z = rng.normal(size=n_trans)
        dy = rho * z + np.sqrt(1 - rho ** 2) * rng.normal(size=n_trans)
        obs = float(z @ dy)
        perm = np.array([rng.permutation(z) @ dy for _ in range(400)])
        hits += (perm >= obs).mean() < ALPHA
        half = n_trans // 2
        b = float(z[:half] @ dy[:half] / (z[:half] @ z[:half] + half))
        better += np.mean((dy[half:] - b * z[half:]) ** 2) < np.mean(dy[half:] ** 2)
    return hits / REPS, better / REPS


# ------------------------------------------------------------------------------------------ F: T2 (D > 0) model vs persistence
def sim_t2(n_dates, phi_d, rng):
    hits_b, hits_a = 0, 0
    for _ in range(REPS):
        T = n_dates + 14
        D = np.zeros((5, T))
        for t in range(1, T):
            D[:, t] = phi_d * D[:, t - 1] + rng.normal(0, np.sqrt(1 - phi_d ** 2), 5)
        db, da = [], []
        for j in range(n_dates):
            t = 12 + j
            y = (D[:, t + 1] > 0).astype(float)                 # lead 1 target from last known t-1
            mu = phi_d ** 2 * D[:, t - 1]
            sd = np.sqrt(1 - phi_d ** 4)
            p = norm.cdf(mu / sd)
            pers = (D[:, t - 1] > 0).astype(float)
            db.append(np.mean((pers - y) ** 2) - np.mean((p - y) ** 2))
            da.append(np.mean((p >= .5) == y) - np.mean(pers == y))
        hits_b += pval(db) < ALPHA
        hits_a += pval(da) < ALPHA
    return hits_b / REPS, hits_a / REPS


def main():
    rng = np.random.default_rng(SEED)
    out = {"seed": SEED, "reps": REPS, "alpha": ALPHA, "A_accuracy_vs_persistence": [], "B_structural": [],
           "D_monthly": [], "E_leading_indicator": [], "F_T2": []}
    for n in (8, 10):
        for c in (0.05, 0.10, 0.20):
            for a in (0.5, 0.75, 1.0):
                for f in (0.0, 0.02, 0.05):
                    out["A_accuracy_vs_persistence"].append(
                        {"n_dates": n, "change_rate": c, "anticipated": a, "false_flip": f,
                         "power": sim_accuracy(n, c, a, f, rng)})
    for n, leads in ((8, (1,)), (10, (1, 2, 3))):
        for se in (1.5, 2.5, 4.0):
            for phi in (0.3, 0.6):
                r = sim_structural(n, se, phi, 1.0, leads, rng)
                out["B_structural"].append({"n_dates": n, "leads_pooled": list(leads), "sigma_eta": se,
                                            "phi_D": phi, **r})
    for phi in (0.7, 0.9):
        out["D_monthly"].append({"n_origins": 51, "phi_month": phi, "power_brier_vs_sign_persistence":
                                 sim_monthly(51, phi, rng)})
    for nt in (12, 16):
        for rho in (0.2, 0.4, 0.6):
            pw, bt = sim_leading(nt, rho, rng)
            out["E_leading_indicator"].append({"n_transitions": nt, "rho": rho, "power_slope": pw,
                                               "share_mse_improves": bt})
    for phi in (0.3, 0.6):
        pb, pa = sim_t2(11, phi, rng)
        out["F_T2"].append({"n_dates": 11, "phi_D": phi, "power_brier_vs_persistence": pb,
                            "power_accuracy_vs_persistence": pa})
    (EXP / "runs" / "power_sim.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    L = ["# Simulated power (synthetic data only; no observed outcome used)", "",
         f"`runner/power_sim.py`, seed {SEED}, {REPS} replications per cell, one-sided exact sign-flip over forecast "
         "dates at alpha = 0.05 (Monte Carlo above 16 dates; monthly origins averaged in blocks of 3).", "",
         "## A. Accuracy versus naive persistence (ideas 1, 3)", "",
         "Per date: 5 rows; a row's label changes with probability *change rate* (persistence is wrong there); the "
         "model anticipates a change with probability *anticipated* and wrongly flips an unchanged row with "
         "probability *false flip*.", "",
         "| Dates | Change rate | Anticipated | False flip | Power |", "|---|---|---|---|---|"]
    for r in out["A_accuracy_vs_persistence"]:
        L.append(f"| {r['n_dates']} | {r['change_rate']} | {r['anticipated']} | {r['false_flip']} | {r['power']:.3f} |")
    L += ["", "## B. Structural simulation: probabilistic H + 2D forecaster with the right structure (ideas 1, 2, 3, 5)",
          "", "Latent regional hunger random walk (innovation sd sigma_eta) + SWS sampling error sd 1.5; provincial D "
          "AR(1) (sd 1, phi_D); label = 1[H_obs + 2D > median]. Power of the correctly specified probabilistic "
          "forecaster against B1 and B1p.", "",
          "| Dates | Leads pooled | sigma_eta | phi_D | Brier vs B1 | Brier vs B1p | Accuracy vs B1 |", "|---|---|---|---|---|---|---|"]
    for r in out["B_structural"]:
        L.append(f"| {r['n_dates']} | {r['leads_pooled']} | {r['sigma_eta']} | {r['phi_D']} | {r['vsB1_brier']:.3f} | "
                 f"{r['vsB1p_brier']:.3f} | {r['vsB1_acc']:.3f} |")
    L += ["", "## D. Monthly-origin evaluation of the provincial price component (idea 9)", "",
          "| Monthly origins | phi (monthly) | Power, Brier vs sign persistence |", "|---|---|---|"]
    for r in out["D_monthly"]:
        L.append(f"| {r['n_origins']} | {r['phi_month']} | {r['power_brier_vs_sign_persistence']:.3f} |")
    L += ["", "## E. Leading indicator for regional hunger (idea 11)", "",
          "| Round-to-round changes | True correlation | Power (slope) | Share of runs where it lowers MSE |",
          "|---|---|---|---|"]
    for r in out["E_leading_indicator"]:
        L.append(f"| {r['n_transitions']} | {r['rho']} | {r['power_slope']:.3f} | {r['share_mse_improves']:.3f} |")
    L += ["", "## F. Exploratory provincial target D > 0, 11 dates (ideas 5, 6)", "",
          "| phi_D | Power, Brier vs persistence | Power, accuracy vs persistence |", "|---|---|---|"]
    for r in out["F_T2"]:
        L.append(f"| {r['phi_D']} | {r['power_brier_vs_persistence']:.3f} | {r['power_accuracy_vs_persistence']:.3f} |")
    (EXP / "docs" / "POWER_SIMULATION.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
