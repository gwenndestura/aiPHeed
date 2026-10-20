"""E62: robustness tests of the served E49 family (lead 1). Report only. Pre-registration: ../E62_results.md
(md5-stamped in ../preregistration_md5.txt before this ran).

    python -B backend/experiments/e62/runner/e62_run.py [test ...]     (tests: shap power seeds province calib)
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
E62 = Path(__file__).resolve().parents[1]
BACKEND = E62.parents[1]
sys.path.insert(0, str(BACKEND / "experiments" / "e59" / "runner"))
sys.path.insert(0, str(BACKEND))
import e59_run as S  # noqa: E402  (E59 run_lead; brings in the E49 family libraries)

X, R, L, L6, C, np, pd = S.X, S.R, S.L, S.L6, S.C, S.np, S.pd
L6.guard32.EXP = E62
E = R.E
PROVS, NAMES = S.PROVS, S.NAMES
PROTECTED = dict(S.PROTECTED) | {"data/e53/e53_record.json": "fa3d0a51939fae66d87bf77c3d15d738",
                                 "data/e53/model/E53_C2_calibration.json": "9986f6cb4b4a36a9e9d676709cb3aeee"}
SEED, B_PERM, N_DRAWS, B_BOOT = 62, 200, 5000, 2000
TESTED = ["Dnow", "D_last", "fssi_v2"]
BASELINES = ["B1_PERSISTENCE", "B2_LR_COMB", "B3_LR_GOV", "B4_LR_NLP", "B5_LGBM_GOV", "B6_LGBM_NLP"]


def md5s() -> dict:
    out = {p: hashlib.md5((BACKEND / p).read_bytes()).hexdigest() for p in PROTECTED}
    if out != PROTECTED:
        raise SystemExit(f"protected md5 mismatch: {[p for p in out if out[p] != PROTECTED[p]]}")
    return out


def record():
    return json.loads((BACKEND / "data/e49/e49_record.json").read_text(encoding="utf-8"))


def lead1(rec):
    return [q for q in rec["quarters"] if q.get("lead", 1) == 1]


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - i) * p))
        out[k] = run
    return out


# ------------------------------------------------------------------ test 1
def test_shap(rec) -> dict:
    X.register()
    d = L.Data(paper=False)
    rows = lead1(rec)
    feats_all = rec["served_engine"]["config"]["features"]
    # observed: stored drivers
    obs = {f: [] for f in feats_all}
    for q in rows:
        for v in q["provinces"].values():
            by = {x["key"]: x["contribution"] for x in v["drivers"]}
            for f in feats_all:
                obs[f].append(abs(by.get(f, 0.0)))
    obs_mean = {f: float(np.mean(v)) for f, v in obs.items()}
    obs_rank = {f: i + 1 for i, f in enumerate(sorted(obs_mean, key=lambda f: -obs_mean[f]))}
    origins = [(q["quarter"], L6.OPERATIONAL_T if q["mode"] == "FORECAST" else C.qk(q["quarter"]) - 1, q)
               for q in rows]

    def cfg(q):                                    # the served configuration, e.g. "COMB_T5xG1"
        return q["model_config"].split("x")

    data = {}
    maxdiff = 0.0
    for quarter, t, q in origins:
        fs, g = cfg(q)
        feats = L6.FEATURE_SETS[fs]
        tr, te = d.train(t), d.test(t).reset_index(drop=True)
        m = L6.fit_lgbm(tr, feats, g)
        sh = L6.shap_contributions(m, te[feats])
        for i, code in enumerate(te["province_code"]):
            by = {x["key"]: x["contribution"] for x in q["provinces"][code]["drivers"]}
            maxdiff = max(maxdiff, max(abs(float(sh.loc[i, f]) - by[f]) for f in feats))
        data[quarter] = (t, fs, g, feats, tr, te)
    if maxdiff > 5e-5:                             # stored contributions are rounded to 4 dp (deviation 1)
        raise SystemExit(f"unpermuted refit does not reproduce stored TreeSHAP (max diff {maxdiff})")
    rng = np.random.default_rng(SEED)
    null = {f: [] for f in TESTED}
    null_rank = {f: [] for f in TESTED}
    t0 = time.time()
    for b in range(B_PERM):
        for f in TESTED:
            per_input = {k: [] for k in feats_all}
            for quarter, (t, fs, g, feats, tr, te) in data.items():
                trp = tr.copy()
                if f in feats:
                    trp[f] = rng.permutation(trp[f].to_numpy())
                m = L6.fit_lgbm(trp, feats, g)
                sh = L6.shap_contributions(m, te[feats])
                for k in feats_all:
                    per_input[k].extend(np.abs(sh[k].to_numpy()) if k in feats else [0.0] * len(te))
            means = {k: float(np.mean(v)) for k, v in per_input.items()}
            null[f].append(means[f])
            null_rank[f].append(1 + sum(1 for k in feats_all if means[k] > means[f]))
        if b % 20 == 0:
            print(f"  perm {b}/{B_PERM} {time.time() - t0:.0f}s", flush=True)
    p = {f: (1 + sum(x >= obs_mean[f] for x in null[f])) / (B_PERM + 1) for f in TESTED}
    p_rank = {f: (1 + sum(r <= obs_rank[f] for r in null_rank[f])) / (B_PERM + 1) for f in TESTED}
    ph = holm(p)
    return {"null": "input-value permutation within each origin's training rows; served configuration per origin "
                    "fixed; TreeSHAP on the real test rows", "B": B_PERM, "seed": SEED, "rows": 70,
            "refit_reproduces_stored_shap_max_diff": maxdiff,
            "observed_mean_abs_shap": obs_mean, "observed_rank": obs_rank,
            "tested": {f: {"rank": obs_rank[f], "observed_mean_abs_shap": obs_mean[f],
                           "null_mean": float(np.mean(null[f])), "null_p95": float(np.percentile(null[f], 95)),
                           "p": p[f], "p_holm": ph[f], "rank_p": p_rank[f],
                           "null_rank_median": float(np.median(null_rank[f]))} for f in TESTED}}


# ------------------------------------------------------------------ test 2
def per_date_diffs(rec) -> dict:
    bundle = json.loads((BACKEND / "data/e49/model/E48_SERVING_BUNDLE.json").read_text(encoding="utf-8"))
    bb = {q["quarter"]: q["baselines_p_high"] for q in bundle["backtests"]}
    out = {b: [] for b in BASELINES}
    for q in lead1(rec):
        if q["mode"] != "BACKTEST":
            continue
        y = {c: 1 if v["observed_label"] == "HIGH" else 0 for c, v in q["provinces"].items()}
        arm = np.mean([(q["provinces"][c]["p_high"] - y[c]) ** 2 for c in PROVS])
        for b in BASELINES:
            out[b].append(float(np.mean([(float(bb[q["quarter"]][b][c]) - y[c]) ** 2 for c in PROVS]) - arm))
    return out


def test_power(rec) -> dict:
    diffs = per_date_diffs(rec)
    stored = rec["validation"]["model_evaluation"]["paired_vs_baselines"]
    for b in BASELINES:
        if abs(np.mean(diffs[b]) - stored[b]["mean_brier_gain_vs_ref"]) > 1e-4:
            raise SystemExit(f"per-date differences do not reproduce the record for {b}")
    n = 13
    signs = np.array(list(itertools.product((1, -1), repeat=n)), dtype=np.float32)        # 8192 x 13
    s_mean = signs.mean(axis=1)                                                           # (sum of signs) / n
    grid = np.round(np.arange(0, 0.2001, 0.001), 3)
    rng = np.random.default_rng(SEED)
    out = {}
    for b in BASELINES:
        d = np.array(diffs[b])
        assert len(d) == n
        cen = d - d.mean()
        draws = cen[rng.integers(0, n, size=(N_DRAWS, n))].astype(np.float32)             # centred resamples
        power = np.zeros(len(grid))
        for lo in range(0, N_DRAWS, 250):
            D = draws[lo:lo + 250]
            st = D @ signs.T / n                                                          # stats at delta = 0
            ob = D.mean(axis=1, keepdims=True)
            dev = st - ob                                                                 # stats0 - obs0
            for i, dl in enumerate(grid):
                # adding delta to every value moves a sign pattern's mean by delta * mean(signs), the observed
                # mean by delta: (stat - obs) at delta = dev + delta * (mean(signs) - 1)
                sh = dl * (s_mean[None, :] - 1.0)
                p_pos = (dev + sh >= -1e-7).mean(axis=1)                  # one-sided p, mean(d) > 0
                p_neg = (dev + sh <= 1e-7).mean(axis=1)                   # one-sided p, mean(d) < 0
                p2 = np.minimum(1.0, 2 * np.minimum(p_pos, p_neg))
                power[i] += float((p2 < 0.05).sum())
        power /= N_DRAWS
        mde = next((float(g) for g, pw in zip(grid, power) if pw >= 0.80), None)
        out[b] = {"observed_gain": float(d.mean()), "observed_p_two_sided": E.signflip_two(d),
                  "per_date_sd": float(d.std(ddof=1)), "mde_80pct_power": mde,
                  "power_at": {f"{g:.3f}": float(pw) for g, pw in zip(grid, power) if round(g * 1000) % 10 == 0}}
    return {"draws": N_DRAWS, "seed": SEED, "dates": n, "alpha": 0.05, "test": "exact two-sided sign-flip",
            "baselines": out}


# ------------------------------------------------------------------ test 3
def test_seeds() -> dict:
    X.register()
    d = L.Data(paper=False)
    S.POOL = "E48-T5"
    out = {}
    base_seed = L6._BASE["seed"]
    try:
        for s in [36] + list(range(1, 11)):
            L6._BASE["seed"] = s
            t0 = time.time()
            r, g = S.run_lead(d, 1)
            m = r["model"]
            out[s] = {k: m[k] for k in ("accuracy", "balanced_accuracy", "auc", "brier")} | {"accuracy_ci95": m["accuracy_ci95"]}
            print(f"  seed {s}: {out[s]} {time.time() - t0:.0f}s", flush=True)
            if s == 36 and (round(m["accuracy"], 3), round(m["balanced_accuracy"], 3), round(m["auc"], 3)) != \
                    (0.846, 0.841, 0.855):
                raise SystemExit(f"seed 36 does not reproduce E49: {m}")
    finally:
        L6._BASE["seed"] = base_seed
    others = [out[s] for s in range(1, 11)]
    summ = {k: {"mean": float(np.mean([o[k] for o in others])), "min": float(np.min([o[k] for o in others])),
                "max": float(np.max([o[k] for o in others]))} for k in ("accuracy", "balanced_accuracy", "auc", "brier")}
    return {"per_seed": {str(k): v for k, v in out.items()}, "seeds_1_10": summ,
            "all_seeds_accuracy_ge_075": all(o["accuracy"] >= 0.75 for o in others)}


# ------------------------------------------------------------------ test 4
def test_province(rec) -> dict:
    rows = []
    for q in lead1(rec):
        if q["mode"] != "BACKTEST":
            continue
        for c, v in q["provinces"].items():
            rows.append({"code": c, "p": v["p_high"], "pers": float(v["persistence_p"]),
                         "y": 1 if v["observed_label"] == "HIGH" else 0})
    df = pd.DataFrame(rows)
    out = {}
    for c in PROVS:
        g = df[df["code"] == c]
        low = g[g["y"] == 0]
        res = {"n": int(len(g)), "LOW_rows": int(len(low))}
        for name, col in (("E49", "p"), ("persistence", "pers")):
            res[name] = {"accuracy": float(((g[col] >= 0.5).astype(int) == g["y"]).mean()),
                         "LOW_recall": f"{int((low[col] < 0.5).sum())}/{len(low)}",
                         "brier": float(((g[col] - g["y"]) ** 2).mean())}
        out[NAMES[c]] = res
    return out


# ------------------------------------------------------------------ test 5
def ece_table(p, y, bins=10):
    p, y = np.asarray(p, float), np.asarray(y, int)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    tab, e = [], 0.0
    for b in range(bins):
        m = idx == b
        n = int(m.sum())
        mp = float(p[m].mean()) if n else None
        ob = float(y[m].mean()) if n else None
        if n:
            e += n / len(p) * abs(mp - ob)
        tab.append({"bin": f"{b / bins:.1f}-{(b + 1) / bins:.1f}", "n": n, "mean_p": mp, "observed_HIGH": ob})
    return tab, e


def test_calib(rec) -> dict:
    pr = pd.read_csv(BACKEND / "experiments/e49/runs/20261015T215405Z/predictions.csv", dtype={"province_code": str})
    c0 = pr[pr["arm"] == "C0"].set_index(["target_quarter", "province_code"]).sort_index()
    c2 = pr[pr["arm"] == "C2"].set_index(["target_quarter", "province_code"]).sort_index()
    served = {(q["quarter"], c): v["p_high"] for q in lead1(rec) if q["mode"] == "BACKTEST" for c, v in q["provinces"].items()}
    if max(abs(c2.loc[k, "p"] - v) for k, v in served.items()) > 1e-4:
        raise SystemExit("C2 run probabilities do not match the record")
    out = {}
    for name, g in (("C0", c0), ("C2", c2)):
        tab, e = ece_table(g["p"], g["y"])
        out[name] = {"reliability": tab, "ece": e}
    dates = sorted(c0.index.get_level_values(0).unique())
    rng = np.random.default_rng(SEED)
    e0s, e2s, dl = [], [], []
    for _ in range(B_BOOT):
        pick = rng.choice(dates, len(dates), replace=True)
        g0 = pd.concat([c0.loc[[q]] for q in pick])
        g2 = pd.concat([c2.loc[[q]] for q in pick])
        a, b = ece_table(g0["p"], g0["y"])[1], ece_table(g2["p"], g2["y"])[1]
        e0s.append(a), e2s.append(b), dl.append(b - a)
    ci = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    out["C0"]["ece_ci95"], out["C2"]["ece_ci95"] = ci(e0s), ci(e2s)
    out["difference_C2_minus_C0"] = {"value": out["C2"]["ece"] - out["C0"]["ece"], "ci95": ci(dl)}
    out["bootstrap"] = {"B": B_BOOT, "seed": SEED, "unit": "target date (13)"}
    return out


def main():
    os.chdir(BACKEND)
    want = sys.argv[1:] or ["province", "calib", "power", "shap", "seeds"]
    path = E62 / "E62_results.json"
    res = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    res.setdefault("preregistration", (E62 / "preregistration_md5.txt").read_text().split())
    res[f"md5_start_{'_'.join(want)}"] = md5s()
    rec = record()
    for t in want:
        print("test", t, flush=True)
        res[t] = {"province": lambda: test_province(rec), "calib": lambda: test_calib(rec),
                  "power": lambda: test_power(rec), "shap": lambda: test_shap(rec), "seeds": test_seeds}[t]()
        path.write_text(json.dumps(C.clean(res), indent=1, default=float), encoding="utf-8")
    res[f"md5_end_{'_'.join(want)}"] = md5s()
    path.write_text(json.dumps(C.clean(res), indent=1, default=float), encoding="utf-8")
    print("done", want)


if __name__ == "__main__":
    main()
