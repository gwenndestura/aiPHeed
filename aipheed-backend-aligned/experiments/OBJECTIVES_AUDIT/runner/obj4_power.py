"""Objective 4: power and sample-size analysis for C-E2 vs the 7 baselines (paired Brier; analysis only).

For each comparison (lead k, baseline b), d_q = Brier_b(q) - Brier_C-E2(q) on the same quarters as the Holm family
(news-only baselines: the news era). Assumptions (stated, not tested):
- the observed mean gain mu and SD sigma of d are the true values for future quarters;
- serial dependence is AR(1) with the observed lag-1 autocorrelation rho (floored at 0), so the effective sample
  size is n (1 - rho) / (1 + rho);
- a one-sided z test at 80% power, at two Holm levels: the strictest step (alpha/14 = 0.0036) and the loosest
  (alpha = 0.05). The real Holm level for one comparison lies between them.

Required n = ((z_{1-a} + z_{0.8}) sigma / mu)^2 * (1 + rho) / (1 - rho). Additional quarters = required - current.
A non-positive mu (C-E2 not better on average) means no sample size makes the claim true.

    python obj4_power.py      # -> ../out/obj4_power.json
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
POWER, ALPHA, M = 0.80, 0.05, 14


def main():
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    F = pd.read_csv(OUT / "ce2_fits.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]], L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      F[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    held = json.loads((OUT / "ce2_results.json").read_text(encoding="utf-8"))["holm_family_14"]
    holm = {(f["lead"], f["comparator"]): f for f in held}
    zb = norm.ppf(POWER)
    rows = []
    for k in (1, 2):
        W = R.frame(comp, k, lab_bl)
        for b in PC.COMPS:
            g = (W[W["t"] >= V.NEWS_ERA] if b in A.NLP_ONLY else W).dropna(subset=["C-E2"])
            pb = g[b] if b in g else None
            if b == "ALWAYS-HIGH":
                pb = pd.Series(1.0, index=g.index)
            g = g[pb.notna()]
            pb = pb[pb.notna()]
            dq = ((pb - g["y"]) ** 2 - (g["C-E2"] - g["y"]) ** 2).to_numpy(float)
            n, mu, sd = len(dq), float(dq.mean()), float(dq.std(ddof=1))
            rho = max(0.0, float(np.corrcoef(dq[:-1], dq[1:])[0, 1])) if n > 3 else 0.0
            infl = (1 + rho) / (1 - rho) if rho < 1 else float("inf")
            need = {}
            for lvl, a in (("strictest_alpha_0.0036", ALPHA / M), ("loosest_alpha_0.05", ALPHA)):
                req = ((norm.ppf(1 - a) + zb) * sd / mu) ** 2 * infl if mu > 0 else None
                need[lvl] = {"required_n": int(np.ceil(req)) if req else None,
                             "additional_quarters": max(0, int(np.ceil(req)) - n) if req else None,
                             "years_at_4_per_year": round(max(0, req - n) / 4, 1) if req else None}
            f = holm.get((k, b), {})
            rows.append({"lead": k, "baseline": b, "n_quarters": n, "mean_gain": round(mu, 4), "sd": round(sd, 4),
                         "effect_size_d": round(mu / sd, 3) if sd else None, "lag1_rho": round(rho, 3),
                         "p_holm_14": f.get("p_holm_14"), "significant": f.get("significant"),
                         "ci95": f.get("ci95"), **need})
    res = {"assumptions": __doc__.split("Assumptions (stated, not tested):")[1].split("Required n")[0].strip(),
           "power": POWER, "comparisons": rows}
    (OUT / "obj4_power.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for r in rows:
        s, l_ = r["strictest_alpha_0.0036"], r["loosest_alpha_0.05"]
        print(f"L{r['lead']} {r['baseline']:12s} n {r['n_quarters']:2d} gain {r['mean_gain']:+.4f} d {r['effect_size_d']} "
              f"rho {r['lag1_rho']} sig {r['significant']} | need n {l_['required_n']}-{s['required_n']} "
              f"(+{l_['additional_quarters']}..+{s['additional_quarters']} q, {l_['years_at_4_per_year']}-{s['years_at_4_per_year']} y)")


if __name__ == "__main__":
    main()
