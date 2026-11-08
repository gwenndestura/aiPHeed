"""
E155 one locked test: E151 required model with and without SunStar inputs (docs/e155/PROTOCOL.md).

    python -m app.e155.test -> data/e155/out/test_results.json, test_oof.csv
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e148 import panel as Pn
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e155.audit import EDITION, LEX, OUT, SUN
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
G = list(LEX)
SUNCOLS = [f"sun_{g}" for g in G] + [f"sun_{g}_chg" for g in G] + ["sun_n"]
FILES = [BACKEND_DIR / "app" / "e155" / "test.py", BACKEND_DIR / "app" / "e155" / "audit.py", BACKEND_DIR.parent / "docs" / "e155" / "PROTOCOL.md"]


def panel() -> pd.DataFrame:
    import re
    d = pd.read_parquet(SUN)
    d["key"] = d["edition"].map(EDITION)
    d = d.dropna(subset=["key"]).copy()
    d["date"] = pd.to_datetime(d["date"])
    for g, rx in LEX.items():
        d[g] = d["title"].str.contains(rx, flags=re.I, regex=True).astype(float)
    rows = []
    for k, x in d.groupby("key"):
        for i in range(Pn.FIRST, Pn.LAST + 1):
            hi = Pn.q_start(i)
            w = x[(x["date"] >= hi - pd.DateOffset(months=3)) & (x["date"] < hi)]
            if len(w) < 20:
                continue
            o = {"key": k, "qi": i, "sun_n": float(len(w))}
            for g in G:
                o[f"sun_{g}"] = float(w[g].mean())
            rows.append(o)
    P = pd.DataFrame(rows).sort_values(["key", "qi"])
    for g in G:
        P[f"sun_{g}_chg"] = P[f"sun_{g}"] - P.groupby("key")[f"sun_{g}"].transform(lambda s: s.shift(1).rolling(8, min_periods=4).mean())
    return P


def task(survey, S_P):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    P = M.Pipeline(S, M8.RQ[survey] - 1, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = Pv.add_inputs(S, M.rows_for(S, tg, [1], Pv.ORIGIN[survey]))
    tr = Pv.add_inputs(S, P.tr)
    tr = tr.merge(S_P, left_on=["key", "i"], right_on=["key", "qi"], how="left", suffixes=("", "_s")).drop(columns=["qi_s"], errors="ignore")
    te = te.merge(S_P, left_on=["key", "i"], right_on=["key", "qi"], how="left", suffixes=("", "_s")).drop(columns=["qi_s"], errors="ignore")
    base, _ = P.hier.predict(te, te["T"].values)
    o = te[["key", "province", "region", "survey", "T", "lead", "y_anchor"] + [x for x in ("y_true", "se_true", "q_true") if x in te]].copy()
    o["has_sunstar"] = te["sun_n"].notna().values
    for name, cols in (("GNT", Pv.GNT_COLS), ("GNT_SUN", Pv.GNT_COLS + SUNCOLS)):
        m = Pv.Res2(cols).fit(tr)
        mu = base + m.predict(te)
        sd, half, _ = m.scale(te["gap_q"].values)
        o[f"mu_{name}"], o[name], o[f"half_{name}"] = mu, norm.cdf(mu / sd), half
    o["train_rows_with_sunstar"] = int(tr["sun_n"].notna().sum())
    return o


def main():
    if (OUT / "test_results.json").exists():
        raise SystemExit("this test has already run; the protocol allows one")
    lock = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
    S_P = panel()
    F = Pv.label_2021(pd.concat(Parallel(n_jobs=3)(delayed(task)(s, S_P) for s in ("ENNS2018", "ENNS2019", "ENNS2021")), ignore_index=True))
    F.to_csv(OUT / "test_oof.csv", index=False, lineterminator="\n")
    rng = np.random.default_rng(155)
    def rep(g):
        out = {"n": int(len(g)), "n_high": int(g["y_high"].sum())}
        for a in ("GNT", "GNT_SUN"):
            ok = (g[a] >= .5) == (g["y_high"] == 1)
            out[a] = {"correct": int(ok.sum()), "accuracy": float(ok.mean()), "high_recall": float(ok[g["y_high"] == 1].mean()) if g["y_high"].sum() else None, "low_recall": float(ok[g["y_high"] == 0].mean()), "brier_soft": float(np.mean((g[a] - g["q_true"]) ** 2))}
        if g["region"].nunique() > 2:
            out["sun_minus_gnt_brier"] = E7.diff_ci(g.reset_index(drop=True), "GNT_SUN", "GNT", "q_true", rng, n=2000)
        return out
    res = {"lock": lock, "sunstar_panel_rows": int(len(S_P)), "sunstar_provinces": sorted(S_P["key"].unique().tolist()), "train_rows_with_sunstar": [int(x) for x in F.groupby("survey")["train_rows_with_sunstar"].first()], "all_rows": rep(F), "rows_with_sunstar": rep(F[F["has_sunstar"]]) if F["has_sunstar"].any() else None}
    a = res["all_rows"]
    res["sunstar_helps"] = bool(a.get("sun_minus_gnt_brier", {}).get("ci95", [0, 1])[1] < 0 and a["GNT_SUN"]["accuracy"] >= a["GNT"]["accuracy"])
    (OUT / "test_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
