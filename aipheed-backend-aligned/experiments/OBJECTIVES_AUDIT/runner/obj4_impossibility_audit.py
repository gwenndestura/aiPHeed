"""Audit of the claim (obj4_feasibility.py / CE6 report) that beating some baselines needs a Brier score below the
irreducible noise floor. Analysis only; nothing fitted.

1. Noise floor, re-derived. The earlier floor plugged the observed H into p* = Phi((H - 11.3)/SE). Here the true
   quarter hunger is integrated over its sampling distribution (flat prior: H_true ~ N(H_obs, SE^2)), and the floor
   is E[p(1 - p)] with p = P(observed label HIGH | H_true) = Phi((H_true - 11.3)/SE). Sensitivity: n = 600 / 300 per
   round, design effect 1 / 2 (SE x sqrt(deff)).
2. Holm logic. Holm does not test every comparison at alpha/14: the i-th smallest p is compared with alpha/(14-i+1).
   The binding requirement is the largest candidate Brier B at which the expected p-values pass Holm jointly.
3. Joint requirement. For a candidate Brier B (applied to every comparison; news-era comparisons scaled by C-E6's
   era/full Brier ratio), mu_b = Brier_b - B, z_b = mu_b / (sd_b / sqrt(n_eff_b)), power-adjusted p_b = 1 - Phi(z_b -
   z_0.8). Search B. Assumption: sd_b and the lag-1 rho of the per-quarter differences stay at C-E6's observed values
   (scaled 0.75 / 1.25 as sensitivity).

    python obj4_impossibility_audit.py   # -> ../out/obj4_impossibility_audit.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
OUT = HERE / "out"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_model as CE  # noqa: E402

PC, N, V, H, R, A = CE.PC, CE.N, CE.V, CE.H, CE.R, CE.A
LINE, Z80 = 11.3, norm.ppf(.8)


def floor(E: pd.DataFrame, n: int, deff: float) -> float:
    g = np.linspace(-6, 6, 241)
    w = norm.pdf(g)
    w = w / w.sum()
    out = []
    for r in E.itertuples():
        se = 100 * np.sqrt((r.observed_H / 100) * (1 - r.observed_H / 100) / (n * r.rounds) * deff)
        ht = r.observed_H + g * se
        p = norm.cdf((ht - LINE) / se)
        out.append(float((w * p * (1 - p)).sum()))
    return float(np.mean(out))


def holm_pass(ps: list[float], a: float = .05) -> bool:
    s = sorted(ps)
    return all(p <= a / (len(s) - i) for i, p in enumerate(s))


def main():
    E = pd.read_csv(OUT / "obj2_error_level.csv")
    E1 = E[E["lead"] == 1]
    floors = {f"n{n}_deff{d}": round(floor(E1, n, d), 4) for n in (600, 300) for d in (1.0, 2.0)}
    plug_in = round(float((E1["P_true_high_n600"] * (1 - E1["P_true_high_n600"])).mean()), 4)
    # per-quarter paired differences for C-E6 (same samples as the Holm family)
    d = H.load()
    lab = V.area_labels(d)
    lb = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    F6 = pd.read_csv(OUT / "ce6_fits.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]], L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      F6[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    stats = []
    for k in (1, 2):
        W = R.frame(comp, k, lb)
        full = float(((W["C-E6"] - W["y"]) ** 2).mean())
        for b in PC.COMPS:
            g = (W[W["t"] >= V.NEWS_ERA] if b in A.NLP_ONLY else W)
            g = g[g[b].notna() & g["C-E6"].notna()]
            dq = ((g[b] - g["y"]) ** 2 - (g["C-E6"] - g["y"]) ** 2).to_numpy(float)
            rho = max(0.0, float(np.corrcoef(dq[:-1], dq[1:])[0, 1]))
            stats.append({"lead": k, "baseline": b, "n": len(dq), "brier_b": float(((g[b] - g["y"]) ** 2).mean()),
                          "brier_c": float(((g["C-E6"] - g["y"]) ** 2).mean()), "scale": float(((g["C-E6"] - g["y"]) ** 2).mean()) / full,
                          "sd": float(dq.std(ddof=1)), "rho": rho, "n_eff": len(dq) * (1 - rho) / (1 + rho)})
    joint = {}
    for s_mult in (0.75, 1.0, 1.25):
        best = None
        for B in np.arange(0.20, 0.0, -0.0005):
            ps = []
            for s in stats:
                mu = s["brier_b"] - B * s["scale"]
                z = mu / (s["sd"] * s_mult / np.sqrt(s["n_eff"]))
                ps.append(1 - norm.cdf(z - Z80))
            if holm_pass(ps):
                best = round(float(B), 4)
                break
        joint[f"sd_x{s_mult}"] = best
    single = {f"L{s['lead']} {s['baseline']}": round(s["brier_b"] / s["scale"] - (norm.ppf(.95) + Z80) * s["sd"] /
                                                    np.sqrt(s["n_eff"]) / s["scale"], 4) for s in stats}
    res = {"noise_floor": {"plug_in_previous": plug_in, "posterior_integrated": floors,
                           "note": "Expected Brier of a forecaster that knows true quarterly hunger; a valid lower bound on "
                                   "EXPECTED Brier under SRS + normal sampling (deff=1 understates it). A 62-quarter "
                                   "realisation can fall below it by chance."},
           "holm_logic": "Holm tests the i-th smallest p at alpha/(14-i+1): only one comparison faces alpha/14, so a "
                         "comparison is not required to reach the alpha/14 Brier target unless it is the strongest.",
           "single_comparison_required_brier_at_alpha_0.05_80pct": single,
           "joint_holm_required_brier_80pct_power": joint,
           "current_C-E6_brier_L1": round(next(s["brier_c"] for s in stats if s["lead"] == 1 and s["baseline"] == "PERSIST"), 4),
           "inputs": stats}
    (OUT / "obj4_impossibility_audit.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "inputs"}, indent=1))


if __name__ == "__main__":
    main()
