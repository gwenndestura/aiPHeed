"""Post-hoc diagnostic (not part of the FI10 lock): LightGBM regression with library-default hyperparameters, same
walk-forward, features, threshold rule and evaluation as the tuned model, to measure what tuning changed.

    python -m app.fi10.tuning_check
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.fi10 import OUT
from app.fi10 import study as S
from app.fi9z.classmetrics import class_metrics

DEFAULT = {"num_leaves": 31, "min_child_samples": 20, "learning_rate": 0.1, "n_estimators": 100, "reg_lambda": 0.0, "colsample_bytree": 1.0}


def run() -> dict:
    D = S.load()
    feats = S.CONFIGS["LightGBM regression (tuned)"][1]
    out = {}
    for lead in (1, 2):
        L = D[D["lead"] == lead].sort_values(["issue_date", "province"]).reset_index(drop=True)
        rows, cache = [], {}
        for d in sorted(L.loc[L["target_quarter"] >= "2005-Q1", "issue_date"].unique()):
            d = pd.Timestamp(d)
            tr, te = L[L["target_published"] <= d], L[L["issue_date"] == d]
            if len(tr) < 100:
                continue
            if d.year not in cache:
                a, b = S._split(tr)
                fa, _ = S.fit("lgb_reg", feats, a, {**DEFAULT, "sd": 1.0})
                res = b["delta"].to_numpy() - (fa(b)[1] - b["f_m"].to_numpy())
                prm = {**DEFAULT, "sd": max(float(np.sqrt(np.mean(res ** 2))), 0.25)}
                fa, _ = S.fit("lgb_reg", feats, a, prm)
                cache[d.year] = (S.fit("lgb_reg", feats, tr, prm)[0], S._tau(fa(b)[0], b["y"].to_numpy(int)))
            fn, tau = cache[d.year]
            p, _ = fn(te)
            rows += [{"target_quarter": t, "y": int(y), "p": float(pi), "cls": int(pi >= tau)} for t, y, pi in zip(te["target_quarter"], te["y"], p)]
        W = pd.DataFrame(rows)
        test = W[W["target_quarter"].str[:4].astype(int) >= 2016]
        ev = json.loads((OUT / "evaluation.json").read_text())["by_lead"][str(lead)]["LightGBM regression (tuned)"]["test"]
        out[lead] = {"default_test": class_metrics(test["y"], test["cls"], test["p"]), "tuned_test": ev, "default_params": DEFAULT}
    (OUT / "tuning_check.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    for lead, v in run().items():
        a, b = v["default_test"], v["tuned_test"]
        print(f"Lead {lead}: default BA {a['balanced_accuracy']:.3f} Brier {a['brier']:.3f} | tuned BA {b['balanced_accuracy']:.3f} Brier {b['brier']:.3f}")
