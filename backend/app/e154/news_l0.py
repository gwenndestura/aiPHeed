"""
One check of the owner's idea: does the latest quarter's news add accuracy when the forecast is issued at the end of that quarter?
E151's models at internal lead 0 (issued on the first day of the target quarter, so news and government data run to the end of the previous quarter). GNT (with news) against GOV (same inputs without news). Nothing is tuned. Retrospective.

    python -m app.e154.news_l0 -> data/e154/out/news_l0.json
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from app.e147 import evaluate as E7
from app.e151 import prov as Pv
from app.e154.model import OUT

warnings.filterwarnings("ignore")


def main():
    R = [x for x in Parallel(n_jobs=3)(delayed(Pv.task)(s, 0) for s in ("ENNS2018", "ENNS2019", "ENNS2021")) if x is not None]
    F = Pv.label_2021(pd.concat(R, ignore_index=True))
    rng = np.random.default_rng(154)
    out = {"definition": "issued on the first day of the target quarter: news and government data to the end of the previous quarter", "n": int(len(F)), "n_high": int(F["y_high"].sum())}
    for a in ("GNT", "GOV", "NEWS", "ANCHOR", "PERS"):
        ok = (F[a] >= .5) == (F["y_high"] == 1)
        out[a] = {"correct": int(ok.sum()), "accuracy": float(ok.mean()), "high_recall": float(ok[F["y_high"] == 1].mean()), "low_recall": float(ok[F["y_high"] == 0].mean()), "brier_soft": float(np.mean((F[a] - F["q_true"]) ** 2)), "by_round": {s: int(((g[a] >= .5) == (g["y_high"] == 1)).sum()) for s, g in F.groupby("survey")}}
    out["news_gain_brier"] = E7.diff_ci(F, "GNT", "GOV", "q_true", rng, n=2000)
    out["gnt_vs_persistence"] = E7.diff_ci(F, "GNT", "PERS", "q_true", rng, n=2000)
    (OUT / "news_l0.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(out, default=float))


if __name__ == "__main__":
    main()
