"""
E161 overfitting and bias audit, per docs/e161/CRITERIA.md (fixed before results).

    python -m app.e161.audit
"""
from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e158 import model as E8
from app.e160 import arms as A
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e161" / "out"
ARMS = ["E158", "RP_R", "OH_R"]
# gap_q and lead are timing columns used by the interval model, not trigger or news inputs; they are left in place (see report).
SHUF = [c for c in E8.COLS if c not in ("gap_q", "lead")]
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def brier(p, q):
    return float(np.mean((p - q) ** 2))


def shuffled(survey, seed, H):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - 1
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [1], Pv.ORIGIN[survey])), H).reset_index(drop=True)
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    r = np.random.default_rng(seed)
    for fr in (tr, te):
        for _, g in fr.groupby(["survey", "lead"]):
            fr.loc[g.index, SHUF] = fr.loc[r.permutation(g.index.values), SHUF].values
    o, _ = A.fit_arms(A.Cache(S), tr, te)
    base, _ = P.hier.predict(te, te["T"].values)
    m = Pv.Res2(E8.COLS).fit(tr)
    mu = base + m.predict(te)
    sd, _, _ = m.scale(te["gap_q"].values)
    out = te[["key", "survey"]].copy()
    out["seed"] = seed
    out["E158"] = norm.cdf(mu / sd)
    out["RP_R"], out["OH_R"] = o["RP_R"][1], o["OH_R"][1]
    return out


def boot_mean(x, groups, rng, n=2000):
    g = list(pd.Series(range(len(x))).groupby(groups.values).indices.values())
    v = [np.mean(x[np.concatenate([g[j] for j in rng.integers(0, len(g), len(g))])]) for _ in range(n)]
    return [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    F = pd.read_csv(D / "e160" / "out" / "oof_arms.csv")
    x = F[F["lead"] == 1].reset_index(drop=True)
    y = x["y_high"].values == 1
    acc = lambda a, g=x: float(((g[a] >= .5) == (g["y_high"] == 1)).mean())
    res = {}

    # A1 nested selection
    picks, hits = {}, []
    for s in sorted(x["survey"].unique()):
        trn, tst = x[x["survey"] != s], x[x["survey"] == s]
        best = min(ARMS, key=lambda a: brier(trn[a], trn["q_true"]))
        picks[s] = best
        hits += list(((tst[best] >= .5) == (tst["y_high"] == 1)).values)
    nested = float(np.mean(hits))
    best_single = max(ARMS, key=acc)
    res["nested_selection"] = {"picks_by_heldout_round": picks, "nested_accuracy": round(nested, 3), "best_single_arm": best_single, "best_single_accuracy": round(acc(best_single), 3), "OVERFIT_SELECTION": bool(acc(best_single) - nested > 0.05)}

    # A3 round stability
    res["by_round_accuracy"] = {a: {s: round(acc(a, g), 3) for s, g in x.groupby("survey")} for a in ARMS}
    res["UNSTABLE"] = {a: bool(max(v.values()) - min(v.values()) > 0.20) for a, v in res["by_round_accuracy"].items()}

    # A2 shuffled-input null
    H = E154.income()
    Sh = pd.concat(Parallel(n_jobs=9)(delayed(shuffled)(s, k, H) for s in ("ENNS2018", "ENNS2019", "ENNS2021") for k in (1, 2, 3)), ignore_index=True)
    Sh = Sh.groupby(["key", "survey"])[ARMS].mean().reset_index()
    m = x.merge(Sh, on=["key", "survey"], suffixes=("", "_shuf"))
    assert len(m) == len(x)
    rng = np.random.default_rng(161)
    null = {}
    for a in ARMS:
        d = E7.diff_ci(m, a, f"{a}_shuf", "q_true", rng, n=2000)
        null[a] = {"brier_real": round(brier(m[a], m["q_true"]), 4), "brier_shuffled": round(brier(m[f"{a}_shuf"], m["q_true"]), 4), "accuracy_real": round(acc(a, m), 3), "accuracy_shuffled": round(float(((m[f"{a}_shuf"] >= .5) == y).mean()), 3),
                   "real_minus_shuffled": round(d["diff"], 4), "ci95": [round(v, 4) for v in d["ci95"]], "NO_SIGNAL": bool(not d["ci95"][1] < 0)}
    res["shuffled_null"] = null

    # B bias
    bias = {}
    for a in ARMS:
        e = pd.Series(pct(x[f"mu_{a}"]) - pct(x["y_true"]))
        b = {}
        for name, mask in [("overall", np.ones(len(x), bool)), *[(f"island:{k}", (x["island"] == k).values) for k in ("Luzon", "Visayas", "Mindanao")], ("observed:HIGH", y), ("observed:LOW", ~y), ("CALABARZON", (x["region"] == "CALABARZON").values)]:
            ev = e.values[mask]
            ci = boot_mean(ev, x["region"][mask].reset_index(drop=True), np.random.default_rng(161)) if mask.sum() > 1 else [np.nan, np.nan]
            mse = float(np.mean(ev))
            b[name] = {"n": int(mask.sum()), "mean_signed_error_pts": round(mse, 2), "ci95": ci, "BIAS": bool((ci[0] > 0 or ci[1] < 0) and abs(mse) > 3)}
        p = x[a].values >= .5
        isl = {}
        for k in ("Luzon", "Visayas", "Mindanao"):
            mk = (x["island"] == k).values
            fa = float(np.mean(p[mk & ~y])) if (mk & ~y).any() else np.nan
            mi = float(np.mean(~p[mk & y])) if (mk & y).any() else np.nan
            fo = float(np.mean(p[~mk & ~y])) if (~mk & ~y).any() else np.nan
            mo = float(np.mean(~p[~mk & y])) if (~mk & y).any() else np.nan
            isl[k] = {"observed_low": int((mk & ~y).sum()), "observed_high": int((mk & y).sum()), "false_alarm_rate": round(fa, 3), "miss_rate": None if mi != mi else round(mi, 3), "false_alarm_others": round(fo, 3), "miss_others": None if mo != mo else round(mo, 3),
                      "UNEQUAL_ERROR": bool((fa == fa and fo == fo and abs(fa - fo) > .25) or (mi == mi and mo == mo and abs(mi - mo) > .25))}
        bias[a] = {"signed_error": b, "error_rates_by_island": isl}
    res["bias"] = bias
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    run()
