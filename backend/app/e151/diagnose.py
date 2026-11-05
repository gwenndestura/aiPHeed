"""
E151 error diagnosis at Lead 1. Reads outcomes already read, so nothing here is evidence of accuracy; it only ranks where accuracy could come from.
Oracle rows use the true answer on purpose: they show the most a perfect fix could add, not what any real input can achieve.

    python -m app.e151.diagnose -> data/e151/out/diagnosis.json
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import OUT
from app.e151 import prov as Pv

warnings.filterwarnings("ignore")
pct = lambda v: 100 / (1 + np.exp(-np.asarray(v, float)))


def acc(mu, y):
    return float(((np.asarray(mu) >= 0) == (np.asarray(y) == 1)).mean())


def _drop(survey, cols_by_name):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    P = M.Pipeline(S, M8.RQ[survey] - 1, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = Pv.add_inputs(S, M.rows_for(S, tg, [1], Pv.ORIGIN[survey]))
    tr = Pv.add_inputs(S, P.tr)
    base, _ = P.hier.predict(te, te["T"].values)
    o = te[["key", "survey"]].copy()
    for nm, cols in cols_by_name.items():
        o[nm] = base + Pv.Res2(cols).fit(tr).predict(te)
    return o


def main():
    F = pd.read_csv(OUT / "prov_oof.csv")
    x = F[F["lead"] == 1].reset_index(drop=True).copy()
    x["pt"], x["ps"], x["pa"], x["pp"] = pct(x["y_true"]), pct(x["mu_GNT"]), pct(x["mu_ANCHOR"]), pct(x["mu_PERS"])
    x["err"] = x["mu_GNT"] - x["y_true"]
    x["ok"] = (x["mu_GNT"] >= 0) == (x["y_high"] == 1)
    res = {}
    # 1. where the 20 errors are
    w = x[~x["ok"]]
    res["errors"] = {"n": int(len(w)), "false_high": int((w["y_high"] == 0).sum()), "false_low": int((w["y_high"] == 1).sum()), "by_survey": w["survey"].value_counts().to_dict(), "by_island": w["island"].value_counts().to_dict(), "rate_by_island": (1 - x.groupby("island")["ok"].mean()).round(3).to_dict(), "rows": w[["province", "survey", "island", "pt", "ps", "pa", "pp"]].round(1).to_dict(orient="records")}
    res["errors"]["within_5_points_of_50_true"] = int((np.abs(w["pt"] - 50) < 5).sum())
    res["errors"]["within_5_points_of_50_forecast"] = int((np.abs(w["ps"] - 50) < 5).sum())
    res["errors"]["within_10_points_of_50_true"] = int((np.abs(w["pt"] - 50) < 10).sum())
    res["errors"]["model_error_mean_abs_points"] = float((w["ps"] - w["pt"]).abs().mean())
    # 2. where the error comes from
    tot = float(np.mean(x["err"] ** 2))
    rnd = x.groupby("survey")["err"].transform("mean")
    isl = x.groupby(["survey", "island"])["err"].transform("mean")
    reg = x.groupby(["survey", "region"])["err"].transform("mean")
    noise = float(np.mean(x["se_true"] ** 2))
    res["error_sources"] = {"mse_logit": tot, "survey_noise_share": noise / tot, "round_level_share": float(np.mean(rnd ** 2)) / tot, "island_within_round_share": float(np.mean((isl - rnd) ** 2)) / tot, "region_within_island_share": float(np.mean((reg - isl) ** 2)) / tot, "within_region_share": float(np.mean((x["err"] - reg) ** 2)) / tot, "mean_error_by_round": x.groupby("survey")["err"].mean().round(3).to_dict(), "note": "Shares are of squared error and include noise; regions hold few rows, so region shares are inflated."}
    # 3. oracle ceilings
    y = x["y_high"]
    res["oracle_accuracy"] = {"current": acc(x["mu_GNT"], y), "round_level_known": acc(x["mu_GNT"] - rnd, y), "island_level_known": acc(x["mu_GNT"] - isl, y), "region_level_known": acc(x["mu_GNT"] - reg, y), "noise_only": float(np.mean(np.maximum(x["q_true"], 1 - x["q_true"])))}
    res["correlation_with_truth"] = {"between_provinces_within_round": {a: float(np.mean([np.corrcoef(g[a], g["y_true"])[0, 1] for _, g in x.groupby("survey")])) for a in ("mu_GNT", "mu_ANCHOR", "mu_PERS")}, "change_since_last_survey_within_round": {a: float(np.mean([np.corrcoef(g[a] - g["y_anchor"], g["y_true"] - g["y_anchor"])[0, 1] for _, g in x.groupby("survey")])) for a in ("mu_GNT", "mu_ANCHOR")}}
    res["adjustment"] = {"mean_abs_logit": float((x["mu_GNT"] - x["mu_ANCHOR"]).abs().mean()), "needed_mean_abs_logit": float((x["y_true"] - x["mu_ANCHOR"]).abs().mean()), "rows_class_changed": int(((x["mu_GNT"] >= 0) != (x["mu_ANCHOR"] >= 0)).sum()), "changes_right": int((((x["mu_GNT"] >= 0) != (x["mu_ANCHOR"] >= 0)) & x["ok"]).sum())}
    # 4. dropping one group of inputs, refit on the same rows
    groups = {g: cols for g, cols in M.GROUPS.items()}
    sets = {"full": Pv.GNT_COLS, "no_news": [c for c in Pv.GNT_COLS if c not in Pv.NEWS_ALL]}
    for g, cols in groups.items():
        sets["no_" + g] = [c for c in Pv.GNT_COLS if c not in cols]
        sets["only_" + g] = list(cols) + ["gap_q", "lead"]
    R = pd.concat(Parallel(n_jobs=3)(delayed(_drop)(s, sets) for s in ("ENNS2018", "ENNS2019", "ENNS2021")), ignore_index=True).merge(x[["key", "survey", "y_high", "y_true"]], on=["key", "survey"])
    res["input_groups"] = {k: {"accuracy": acc(R[k], R["y_high"]), "low_recall": float((R[k][R["y_high"] == 0] < 0).mean()), "high_recall": float((R[k][R["y_high"] == 1] >= 0).mean()), "mae_points": float(np.abs(pct(R[k]) - pct(R["y_true"])).mean())} for k in sets}
    # 5. training size: same model family, rows per round and result
    res["training_rows"] = {"ENNS2018": 156, "ENNS2019": 156, "ENNS2021": 532}
    (OUT / "diagnosis.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, default=float))


if __name__ == "__main__":
    main()
