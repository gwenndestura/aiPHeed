"""ALLBASE Phase A (read only, no training): root-cause numbers for "beat every baseline at both leads".

    python phase_a.py   # -> ../out/phase_a.json

From stored forecasts only (C-b: NEWS_V2; comparators: IMPROVE_V2, OBJECTIVES_COMPLETION, IMPROVE_V2_LEADS) and the BL
labels with their SWS round counts:
1. noise ceiling: the expected accuracy, against the published (noisy) labels, of a forecaster that knew TRUE hunger
   exactly, from SWS's +/-5.7-point 95% margin (se 2.908 / sqrt(rounds));
2. how often C-b's call equals persistence's, overall and per third, and where its errors are;
3. statistical power: per comparator and lead, the mean and SD of the paired Brier difference and the number of quarters
   needed for one-sided significance at the observed effect (alpha 0.05 raw; 0.05/6 as Holm's strictest step);
4. calibration (10-bin reliability, ECE) and AUC for C-b and every comparator.
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
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "NEW_MODEL" / "NEWS_V2" / "runner"))
import run_news_v2 as N  # noqa: E402
import align_cb as A  # noqa: E402

V, H, R = N.V, N.H, N.R
SE1, LINE = 5.7 / 1.96, 11.3
COMPS = ["PERSIST", "PSA-only", "LOGIT", "NLP-only", "LGBM-GOV", "LGBM-NLP", "ALWAYS-HIGH"]


def ece(p, y, bins=10):
    p, y = np.asarray(p, float), np.asarray(y, int)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).sum() for b in range(bins)
                     if (idx == b).any()) / len(p))


def main():
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    rounds = d.sws[d.sws["area"] == "BL"].groupby("q").size()
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    F = pd.read_csv(N.OUT / "forecasts.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      F[F["name"] == "C-b"][["name", "t", "lead", "q", "p"]]], ignore_index=True)
    out = {"leads": {}}
    for k in (1, 2):
        W = R.frame(comp, k, lab_bl).sort_values("q").reset_index(drop=True)
        W = W.merge(lab_bl[["q", "H"]], on="q")
        W["se"] = SE1 / np.sqrt(W["q"].map(rounds).astype(float))
        W["p_true_high"] = norm.cdf((W["H"] - LINE) / W["se"])
        W["ceiling"] = np.maximum(W["p_true_high"], 1 - W["p_true_high"])
        qs = sorted(W["q"].unique())
        thirds = [set(x) for x in np.array_split(np.array(qs), 3)]
        call = (W["C-b"] >= .5).astype(int)
        pers = (W["PERSIST"] >= .5).astype(int)
        Lk = {"noise_ceiling": {"all": float(W["ceiling"].mean())},
              "cb_accuracy": {"all": float((call == W["y"]).mean())},
              "cb_equals_persistence_call": {"all": float((call == pers).mean())},
              "persistence_accuracy": {"all": float((pers == W["y"]).mean())}}
        for i, t in enumerate(thirds):
            m = W["q"].isin(t)
            nm = f"third_{i + 1}_{H.qs(min(t))}..{H.qs(max(t))}"
            Lk["noise_ceiling"][nm] = float(W.loc[m, "ceiling"].mean())
            Lk["cb_accuracy"][nm] = float((call[m] == W.loc[m, "y"]).mean())
            Lk["cb_equals_persistence_call"][nm] = float((call[m] == pers[m]).mean())
            Lk["persistence_accuracy"][nm] = float((pers[m] == W.loc[m, "y"]).mean())
        err = W[call != W["y"]]
        Lk["cb_errors"] = [{"q": H.qs(int(W.loc[i_, "q"])), "H": round(float(W.loc[i_, "H"]), 1), "y": int(W.loc[i_, "y"]),
                            "p_cb": round(float(W.loc[i_, "C-b"]), 3),
                            "p_true_high": round(float(W.loc[i_, "p_true_high"]), 2),
                            "same_call_as_persistence": bool(call[i_] == pers[i_])} for i_ in err.index]
        era = W[W["t"] >= V.NEWS_ERA]
        pw = {}
        for c in COMPS:
            g = era if c in A.NLP_ONLY else W
            g = g[g[c].notna()]
            dv = ((g["C-b"] - g["y"]) ** 2 - (g[c] - g["y"]) ** 2).to_numpy(float)
            mu, sd, n = float(dv.mean()), float(dv.std(ddof=1)), len(dv)
            need = lambda z: (None if mu >= 0 else int(np.ceil((z * sd / -mu) ** 2)))  # noqa: E731
            pw[c] = {"n": n, "mean_diff": mu, "sd_diff": sd, "z_observed": float(-mu / (sd / np.sqrt(n))) if sd else None,
                     "n_needed_alpha_0.05": need(norm.ppf(.95)), "n_needed_holm_strictest_0.05/6": need(norm.ppf(1 - .05 / 6))}
        Lk["power_vs_comparators"] = pw
        cal = {}
        for c in ["C-b"] + [c for c in COMPS if c != "ALWAYS-HIGH"]:
            g = (era if c in A.NLP_ONLY else W).dropna(subset=[c])
            cal[c] = {"n": int(len(g)), "brier": float(((g[c] - g["y"]) ** 2).mean()), "ece": ece(g[c], g["y"]),
                      "auc": float(roc_auc_score(g["y"], g[c])) if g["y"].nunique() == 2 and g[c].nunique() > 1 else None,
                      "accuracy": float(((g[c] >= .5).astype(int) == g["y"]).mean())}
        Lk["calibration_auc"] = cal
        Lk["cb_vs_logit_same_call"] = float((call == (W["LOGIT"] >= .5).astype(int)).mean())
        Lk["cb_vs_psaonly_same_call"] = float((call == (W["PSA-only"] >= .5).astype(int)).mean())
        out["leads"][str(k)] = Lk
    (HERE / "out").mkdir(parents=True, exist_ok=True)
    (HERE / "out" / "phase_a.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for k, Lk in out["leads"].items():
        print(f"\n=== Lead {k}")
        for key in ("noise_ceiling", "cb_accuracy", "persistence_accuracy", "cb_equals_persistence_call"):
            print(f"{key}: " + ", ".join(f"{n}={v:.3f}" for n, v in Lk[key].items()))
        print("same call as LOGIT / PSA-only:", round(Lk["cb_vs_logit_same_call"], 3), round(Lk["cb_vs_psaonly_same_call"], 3))
        for c, v in Lk["power_vs_comparators"].items():
            print(f"  power vs {c}: n {v['n']}, diff {v['mean_diff']:+.4f}, sd {v['sd_diff']:.3f}, z {v['z_observed']:.2f}, "
                  f"n needed {v['n_needed_alpha_0.05']} (raw) / {v['n_needed_holm_strictest_0.05/6']} (Holm strictest)")
        for c, v in Lk["calibration_auc"].items():
            print(f"  {c}: n {v['n']} acc {v['accuracy']:.3f} AUC {v['auc'] if v['auc'] is None else round(v['auc'], 3)} "
                  f"Brier {v['brier']:.4f} ECE {v['ece']:.3f}")
        print("C-b errors:", [(e["q"], e["H"], e["y"], e["p_true_high"], e["same_call_as_persistence"]) for e in Lk["cb_errors"]])


if __name__ == "__main__":
    main()
