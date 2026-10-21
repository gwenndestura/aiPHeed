"""E83 round 2 (DEVIATIONS.md D2, post-hoc): seasonal structural simulation, in-origin thresholds and stacking.

Reads the round-1 run (predictions + features), adds the D2 arms on the same rows, and scores every arm with the
round-1 code. Run from backend/:  python .../run_round2.py <round1_run_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_e83 as R  # noqa: E402

E, L, np, pd = R.E, R.L, R.np, R.pd
GRID = [round(0.10 + 0.05 * i, 2) for i in range(11)]


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-3, 1 - 1e-3)
    return np.log(p / (1 - p))


def seasonal_sims(d, X, k):
    rows = []
    for t in sorted(X["t"].unique()):
        s = E.simulate(d.cut(t), t, k, seasonal=True)
        for p in L.PROVS:
            v = s.get(p, (np.nan, np.nan, np.nan))
            rows.append({"t": t, "province_code": p, "seas_p": v[0], "seas_p_hunger": v[1], "seas_p_price": v[2]})
    return X.merge(pd.DataFrame(rows), on=["t", "province_code"], how="left")


def past_pairs(X, d, t, k, col):
    tr = E.pairs(X, d, t, k)
    return tr[tr[col].notna()]


def threshold(tr, col):
    if tr["y"].sum() < 5 or (1 - tr["y"]).sum() < 5:
        return 0.5
    def bal(th):
        yh = (tr[col] >= th).astype(int)
        return ((yh[tr.y == 1] == 1).mean() + (yh[tr.y == 0] == 0).mean()) / 2
    return max(GRID, key=lambda th: (round(bal(th), 10), -abs(th - 0.5)))


def stack(tr, te, extra):
    from sklearn.linear_model import LogisticRegression
    cols = ["lh", "lp"] + extra
    f = lambda D: pd.DataFrame({"lh": logit(D["seas_p_hunger"]), "lp": logit(D["seas_p_price"]),  # noqa: E731
                                **{c: D[c].astype(float).fillna(0.0) for c in extra}})
    tr = tr[tr["seas_p_hunger"].notna() & tr["seas_p_price"].notna()]
    if tr["q"].nunique() < 6 or tr["y"].sum() < 3 or tr["y"].nunique() < 2:
        return te["seas_p"].to_numpy(), False
    A, B = f(tr), f(te)
    mu, sd = A.mean(), A.std(ddof=0).replace(0, 1)
    m = LogisticRegression(C=1.0, max_iter=5000).fit((A - mu) / sd, tr["y"].astype(int))
    p = m.predict_proba((B - mu) / sd)[:, 1]
    return np.where(te["seas_p"].notna(), p, np.nan), True


def run(run_dir: Path, k: int, d, lab):
    P = pd.read_csv(run_dir / f"predictions_k{k}.csv", dtype={"province_code": str})
    X = pd.read_csv(run_dir / f"features_k{k}.csv", dtype={"province_code": str})
    X = seasonal_sims(d, X, k)
    add = {c: [] for c in ["S-SIM-SEAS", "S-SIM-THR", "S-SIM-SEAS-THR", "ST-LR", "ST-LR-N2", "ST-LR-N3",
                           "thr_sim", "thr_seas", "stack_fitted"]}
    for t in P["t"].unique():
        te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        tr = E.pairs(X, d, t, k)
        ts, tss = threshold(tr[tr["sim_p"].notna()], "sim_p"), threshold(tr[tr["seas_p"].notna()], "seas_p")
        p_st, fitted = stack(tr, te, [])
        p_n2, _ = stack(tr, te, ["ev_net_prices", "ev_net_climate", "ev_net_all"])
        p_n3, _ = stack(tr, te, ["n3_market_rw", "n3_climate_rw", "n3_fssi"])
        for i in range(5):
            add["S-SIM-SEAS"].append(te["seas_p"].iloc[i])
            # thresholded arms are scored as hard 0/1 decisions; their probability for Brier is the raw p shifted so
            # that the chosen threshold maps to 0.5 (monotone, keeps the ranking)
            add["S-SIM-THR"].append(_shift(te["sim_p"].iloc[i], ts))
            add["S-SIM-SEAS-THR"].append(_shift(te["seas_p"].iloc[i], tss))
            add["ST-LR"].append(p_st[i]); add["ST-LR-N2"].append(p_n2[i]); add["ST-LR-N3"].append(p_n3[i])
            add["thr_sim"].append(ts); add["thr_seas"].append(tss); add["stack_fitted"].append(fitted)
    order = [(t, p) for t in P["t"].unique() for p in L.PROVS]
    A = pd.DataFrame(add).assign(t=[o[0] for o in order], province_code=[o[1] for o in order])
    P = P.merge(A, on=["t", "province_code"], how="left")
    return P, X


def _shift(p, th):
    if p is None or not np.isfinite(p):
        return np.nan
    return float(0.5 * p / th) if p < th else float(0.5 + 0.5 * (p - th) / (1 - th))


if __name__ == "__main__":
    run_dir = Path(sys.argv[1])
    d, x = E.data()
    lab = E.labels_all(d)
    R.PRIMARY[:] = ["S-SIM", "S-SIM-SEAS", "S-SIM-THR", "S-SIM-SEAS-THR", "ST-LR", "ST-LR-N2", "ST-LR-N3",
                    "M-GB-ALL", "M-LR-ALL"]
    summary = {}
    leads = [int(v) for v in (sys.argv[2].split(",") if len(sys.argv) > 2 else ["0", "1", "2", "3"])]
    for k in leads:
        if not (run_dir / f"predictions_k{k}.csv").exists():
            continue
        P, X = run(run_dir, k, d, lab)
        P.to_csv(run_dir / f"predictions_r2_k{k}.csv", index=False)
        X.to_csv(run_dir / f"features_r2_k{k}.csv", index=False)
        res, tests = R.evaluate(P)
        summary[k] = {"metrics": res, "tests": tests, "pass": {a: R.passes(res, tests, a) for a in R.PRIMARY}}
        print(f"k={k} rows={len(P)}")
        for a in R.BASELINES + R.PRIMARY:
            m, mi = res[a]["all_rows_unissued_wrong"], res[a]["issued_rows"]
            print(f"  {a:15s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} brier={m.get('brier', float('nan')):.3f}"
                  f" recH={m['recall_HIGH'] or 0:.2f} | issued {mi['issued']:3d} acc={mi['accuracy'] or 0:.3f}"
                  f" bal={mi['balanced_accuracy'] or 0:.3f} brier={mi.get('brier', float('nan')):.3f}  PASS={summary[k]['pass'].get(a, {}).get('PASS')}",
                  flush=True)
    (run_dir / "metrics_r2.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
