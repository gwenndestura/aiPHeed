"""
E136 limited experiment set (protocol f12ea6b): TREND-D (fixed damped trend), SIMPLE (pooled measurement-aware level +
rice, unemployment, news at prior SD 0.5), training-start stability (T22), against PERSIST, RIDGE-ALL, LGBM-ALL, HFM-X,
SEAS-LLM and X-RED (reproduced from E135), Leads 1-4, both sets, the recommendation rule.

    python -I runner/e136_run.py      (after E135 runner/e135_run.py)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
OUT = ROOT / "out"
sys.path.insert(0, str(EXP / "E135_Feature_Influence" / "runner"))
import e135_run as S  # noqa: E402

E, R, X, L = S.E, S.R, S.X, S.L
SIMPLE = ("A", "E", "N")
SIMPLE_SD = 0.5
CANDS = ["PERSIST", "TREND-D", "RIDGE-ALL", "LGBM-ALL", "HFM-X", "SEAS-LLM", "X-RED", "SIMPLE"]
PARAMS = {"PERSIST": 0, "TREND-D": 0, "SEAS-LLM": 3, "SIMPLE": 8, "X-RED": 10, "HFM-X": 10,
          "RIDGE-ALL": 23, "LGBM-ALL": 100}   # estimated quantities (LightGBM: ~100 trees of 4 leaves; ridge: coefficients)


def trend_d(P, rr) -> np.ndarray:
    out = np.full(len(P), np.nan)
    cache = {}
    for i, (issue, a) in enumerate(zip(P["issue"], P["area"])):
        if issue not in cache:
            cache[issue] = X.asof(rr, issue)
        s = cache[issue][cache[issue].area == a].sort_values("qi")
        prev = float(s["y"].iloc[-2]) if len(s) > 1 else float(s["y"].iloc[-1])
        out[i] = float(s["y"].iloc[-1]) + 0.5 * (float(s["y"].iloc[-1]) - prev)
    return out


def fill(P, rr, drv, adrv, name, groups, sd):
    P[f"f_{name}"], P[f"sd_{name}"], P[f"betas_{name}"] = np.nan, np.nan, ""
    for (pol, D, k), g in P.groupby(["policy", "D", "lead"]):
        issue, target = g["issue"].iloc[0], L.qi(g["target"].iloc[0])
        qa = X.asof(rr, issue)
        if qa.empty or int(qa["qi"].max()) < R.T0 + 4:     # T22 runs: too few quarters after the moved start
            continue
        mean, sdv, fit = S.predict_cfg(qa, issue, target, drv, adrv, groups, {x: sd for x in groups})
        ai = [X.AREAS.index(a) for a in g["area"]]
        P.loc[g.index, f"f_{name}"], P.loc[g.index, f"sd_{name}"] = mean[ai], sdv[ai]
        P.loc[g.index, f"betas_{name}"] = json.dumps({x: round(fit.beta.get(x, 0.0), 4) for x in groups})
    P[f"lo80_{name}"] = P[f"f_{name}"] - X.Z80 * P[f"sd_{name}"]
    P[f"hi80_{name}"] = P[f"f_{name}"] + X.Z80 * P[f"sd_{name}"]


def main():
    OUT.mkdir(exist_ok=True)
    P = pd.read_csv(EXP / "E135_Feature_Influence" / "out" / "e135_predictions.csv")
    P["issue"] = pd.to_datetime(P["issue"]).dt.date
    rr = X.rounds()
    drv, adrv = {"rice": R.Drivers("rice")}, E.AreaDrivers()
    P["f_TREND-D"] = trend_d(P, rr)
    fill(P, rr, drv, adrv, "SIMPLE", SIMPLE, SIMPLE_SD)
    # Q8 stability: training from 2022-Q1 (fresh fits)
    R.T0 = L.qi("2022-Q1")
    R._BASE.clear(); S._F.clear()
    fill(P, rr, drv, adrv, "SIMPLE-T22", SIMPLE, SIMPLE_SD)
    fill(P, rr, drv, adrv, "HFM-X-T22", S.HFMX, 1.0)
    P.to_csv(OUT / "e136_predictions.csv", index=False)

    shared = P.dropna(subset=["f_RIDGE-ALL", "f_PSA-ONLY", "f_NLP-ONLY", "f_LGBM-ALL", "f_HYB-LGBM"])
    keys = set(zip(shared.policy, shared.area, shared.D, shared.lead))
    in_e132 = np.array([k in keys for k in zip(P.policy, P.area, P.D, P.lead)])
    su_models = [m for m in CANDS if m not in ("RIDGE-ALL", "LGBM-ALL")] + ["CLIM", "LLM", "SIMPLE-T22", "HFM-X-T22"]
    r1, q1 = R.metrics(P, su_models, "S-U", P.n_obs >= 8)
    r2, q2 = R.metrics(P, CANDS + ["CLIM", "LLM", "PSA-ONLY", "NLP-ONLY", "SIMPLE-T22", "HFM-X-T22"], "S-E132", in_e132)
    Mt = pd.DataFrame(r1 + r2 + S.period_metrics(P, su_models))
    Mt.to_csv(OUT / "e136_metrics.csv", index=False)
    L.dump({**q1, **q2}, OUT / "e136_rules.json")

    # training vs out-of-sample (learned models only have stored training MAE)
    tr = {m: float(P.loc[(P.policy == "P-DASH") & (P.lead == 2) & in_e132, f"train_mae_{m}"].mean()) for m in ("RIDGE-ALL", "LGBM-ALL")}
    # stability: forecast change from moving the training start
    su = P[(P.policy == "P-DASH") & (P.n_obs >= 8)]
    stab = {f"{m}|{k}": float((g[f"f_{m}-T22"] - g[f"f_{m}"]).abs().mean()) for m in ("SIMPLE", "HFM-X") for k, g in su.groupby("lead")}
    betas = su[su.lead == 2].groupby("D")["betas_SIMPLE"].first().to_dict()

    # recommendation rule
    g2 = Mt[(Mt.policy == "P-DASH") & (Mt.lead == 2)]
    rec_rows = []
    for m in CANDS:
        su_r = g2[(g2.set == "S-U") & (g2.model == m)]
        se_r = g2[(g2.set == "S-E132") & (g2.model == m)]
        rec_rows.append({"model": m, "params": PARAMS[m],
                         "su_within": float(su_r["within_tolerance"].iloc[0]) if len(su_r) else np.nan,
                         "su_mae": float(su_r["mae"].iloc[0]) if len(su_r) else np.nan,
                         "se_within": float(se_r["within_tolerance"].iloc[0]), "se_mae": float(se_r["mae"].iloc[0])})
    T = pd.DataFrame(rec_rows)
    pers = T.set_index("model").loc["PERSIST"]
    T["eligible"] = (T["su_mae"] < pers["su_mae"]) & (T["se_mae"] < pers["se_mae"]) & (T["model"] != "PERSIST")
    el = T[T.eligible].copy()
    el["rank_su"] = el["su_within"].rank(ascending=False)
    el["rank_se"] = el["se_within"].rank(ascending=False)
    el["mean_rank"] = (el["rank_su"] + el["rank_se"]) / 2
    el["mean_mae"] = (el["su_mae"] + el["se_mae"]) / 2
    el = el.sort_values(["mean_rank", "params", "mean_mae"])
    T = T.merge(el[["model", "rank_su", "rank_se", "mean_rank", "mean_mae"]], on="model", how="left")
    T.to_csv(OUT / "e136_recommendation_table.csv", index=False)
    s = {"recommended": el["model"].iloc[0] if len(el) else None, "eligible_order": el["model"].tolist(),
         "maximum_reliable_lead_any": [k for k, v in {**q1, **q2}.items() if v["passed"]],
         "any_within_75": bool((Mt.loc[Mt.set.isin(["S-U", "S-E132"]), "within_tolerance"] >= 0.75).any()),
         "train_mae_learned_lead2": tr, "training_start_stability_mean_abs_change": stab, "simple_betas_lead2_by_issue": betas}
    L.dump(s, OUT / "e136_summary.json")
    print(T.round(3).to_string())
    print(json.dumps(s, indent=1, default=str)[:2500])
    for st in ("S-U", "S-E132"):
        g = Mt[(Mt.set == st) & (Mt.policy == "P-DASH")]
        print(st)
        print(g.pivot_table(index="model", columns="lead", values=["within_tolerance", "mae"]).round(2).to_string())


if __name__ == "__main__":
    main()
