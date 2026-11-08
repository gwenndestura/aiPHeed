"""Reliability analysis of E168 (Lead 1). Reads saved out-of-sample rows only; fits nothing on test outcomes
except explicitly labelled ORACLE bounds (diagnostic ceilings, never deployable)."""
import json, sys
import numpy as np, pandas as pd
from scipy.stats import norm

from app.paths import BACKEND_DIR
B = str(BACKEND_DIR / "data")
G = pd.read_csv(f"{B}/e158/out/oof.csv")
G = G[G.lead == 1]
E = pd.read_csv(f"{B}/e168/out/all_rows.csv")
E = E[(E["mode"] == "main") & (E.lead == 1)][["key", "survey", "mu", "p"]]
X = G.merge(E, on=["key", "survey"]).reset_index(drop=True)
assert len(X) == 72
sig = lambda z: 1 / (1 + np.exp(-z))
SHARED, PER_CELL = 0.726, 1.8
NE = 72 / (1 + (PER_CELL - 1) * SHARED)
rng = np.random.default_rng(169)
regs = list(X.groupby("region").indices.values())


def c1(acc, major):
    lo = acc - 1.96 * np.sqrt(acc * (1 - acc) / NE)
    return acc > major and lo > major, lo


def slope_ci(mu, y, n=2000):
    sl = []
    for _ in range(n):
        i = np.concatenate([regs[j] for j in rng.integers(0, len(regs), len(regs))])
        if np.std(mu[i]) > 0:
            sl.append(np.polyfit(mu[i], y[i], 1)[0])
    return [float(np.percentile(sl, 2.5)), float(np.percentile(sl, 97.5))]


y, mu, yh = X.y_true.values, X.mu.values, X.y_high.values == 1
major = max(yh.mean(), 1 - yh.mean())
out = {"n": 72, "effective_n": round(NE, 1), "majority": round(major, 3), "high_rows": int(yh.sum())}


def report(name, m):
    acc = float(((sig(m) >= .5) == yh).mean())
    ok, lo = c1(acc, major)
    s = slope_ci(m, y)
    out[name] = {"accuracy": round(acc, 3), "correct": int(round(acc * 72)), "C1": bool(ok), "acc_low": round(lo, 3),
                 "slope": round(float(np.polyfit(m, y, 1)[0]), 2), "slope_ci95": [round(v, 2) for v in s], "C4": bool(s[0] <= 1 <= s[1]),
                 "mean_abs_err_pts": round(float(np.mean(np.abs(100 * sig(m) - 100 * sig(y)))), 2)}


report("E168_actual", mu)
# Error decomposition (logit)
e = mu - y
rnd = X.groupby("survey")["mu"].transform("mean") - X.groupby("survey")["y_true"].transform("mean")
out["error_decomposition"] = {"total_mse": round(float(np.mean(e ** 2)), 4), "round_offset_share": round(float(np.mean(rnd ** 2) / np.mean(e ** 2)), 3),
                              "sampling_noise_share(se_true^2)": round(float(np.mean(X.se_true ** 2) / np.mean(e ** 2)), 3),
                              "by_round_mean_err_pts": {s: round(float(100 * sig(g.mu).mean() - 100 * sig(g.y_true).mean()), 1) for s, g in X.groupby("survey")},
                              "by_round_slope": {s: round(float(np.polyfit(g.mu, g.y_true, 1)[0]), 2) for s, g in X.groupby("survey")},
                              "by_round_sd_pred_vs_obs": {s: [round(float(g.mu.std()), 2), round(float(g.y_true.std()), 2)] for s, g in X.groupby("survey")}}
# ORACLE bounds (use test outcomes; ceilings only)
report("ORACLE_round_offset_known", mu - rnd.values)
mw = X.assign(c=mu - rnd.values)
mo = np.zeros(72)
for s, g in mw.groupby("survey"):
    b = np.polyfit(g.c, g.y_true, 1)
    mo[g.index] = np.polyval(b, g.c)
report("ORACLE_round_offset_and_slope_known", mo)
# Measurement-noise ceiling: a forecaster that knows each province's TRUE prevalence perfectly is still scored against a noisy survey.
# Approximate true = observed (logit); P(observed side = true side) = Phi(|y|/se).
pc = norm.cdf(np.abs(y) / X.se_true.values)
out["noise_ceiling"] = {"expected_accuracy_perfect_forecaster": round(float(pc.mean()), 3), "rows_within_1se_of_50": int((np.abs(y) < X.se_true).sum()),
                        "P_perfect_forecaster_passes_C1": None}
# Simulate: perfect-knowledge forecaster, survey noise only -> how often C1 passes
passes = 0
for _ in range(4000):
    obs = y + rng.normal(0, X.se_true.values)
    a = float(((y >= 0) == (obs >= 0)).mean())
    m2 = max((obs >= 0).mean(), 1 - (obs >= 0).mean())
    passes += c1(a, m2)[0]
out["noise_ceiling"]["P_perfect_forecaster_passes_C1"] = round(passes / 4000, 3)

# Power simulation: a model that IS calibrated (slope 1, no bias) but has E168-sized honest error,
# with round-level and region-level shared error like the real data. How often do C1 and C4 pass on 72 rows?
sd_round = float(np.sqrt(np.mean(rnd ** 2)))
resid = e - rnd.values
sd_reg = float(np.sqrt(max(1e-6, np.mean(X.assign(r=resid).groupby(["survey", "region"])["r"].transform("mean") ** 2))))
sd_ind = float(np.sqrt(max(1e-6, np.mean(resid ** 2) - sd_reg ** 2)))


def sim(scale, R=600):
    c1p = c4p = both = 0
    for _ in range(R):
        err = np.zeros(72)
        for s, g in X.groupby("survey"):
            err[g.index] += rng.normal(0, sd_round * scale)
        for k, g in X.groupby(["survey", "region"]):
            err[g.index] += rng.normal(0, sd_reg * scale)
        err += rng.normal(0, sd_ind * scale, 72)
        truth = mu - err        # outcomes generated so that forecast mu is calibrated around truth
        yh2 = truth >= 0
        a = float(((mu >= 0) == yh2).mean())
        m2 = max(yh2.mean(), 1 - yh2.mean())
        p1 = c1(a, m2)[0]
        sl = []
        for _ in range(300):
            i = np.concatenate([regs[j] for j in rng.integers(0, len(regs), len(regs))])
            sl.append(np.polyfit(mu[i], truth[i], 1)[0])
        lo, hi = np.percentile(sl, [2.5, 97.5])
        p4 = lo <= 1 <= hi
        c1p += p1; c4p += p4; both += p1 and p4
    return {"C1": round(c1p / R, 2), "C4": round(c4p / R, 2), "both": round(both / R, 2)}


out["power_sim_components_logit_sd"] = {"round": round(sd_round, 3), "region": round(sd_reg, 3), "province": round(sd_ind, 3)}
out["power_calibrated_model_pass_rate"] = {f"error_x{s}": sim(s) for s in (1.0, 0.75, 0.5)}
json.dump(out, sys.stdout, indent=1, default=float)
