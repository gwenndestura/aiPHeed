"""PROTOCOL_E116 (hash checked): additive tests of each FIRI domain on SWS hunger by area, with E114's unified
LightGBM recipe and point-in-time inputs (area-level CPI, fisheries, palay; national rice, ONI, typhoons, LFS;
GDELT news 2018+). DEV 2003-12 is the primary evidence; TEST 2013-20 is a second use (confirmation only).

    python run_e116.py        # ../out/e116_results.json, ../out/e116_predictions.csv, ../out/e116_rows.csv
"""
from __future__ import annotations

import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
E114R = ROOT.parent / "E114_Final_Run" / "runner"
sys.path.insert(0, str(E114R))
import e114_lib as L  # noqa: E402
import run_e114 as R14  # noqa: E402

DATA, OUT = ROOT / "data", ROOT / "out"
AREAS = list(L.AREAS)
BASE = ["h_last", "MR", "d_last", "stale", "lead"] + [f"A-{a}" for a in AREAS]
DOM = {"market": ["AF_food", "AF_gap", "AF_dfood", "P-RICE"],
       "fish": ["F_yoy", "F_dyoy"],
       "climate": ["C-ONI", "C_nino", "C-TC", "PAL_yoy"],
       "employment": ["P-UNEMP"]}
NEWS = ["N-SUP", "N-AST"]
VARIANTS = {"V1_BASE": BASE, "V2_MARKET": BASE + DOM["market"], "V3_FISH": BASE + DOM["fish"],
            "V4_CLIMATE": BASE + DOM["climate"], "V5_EMPLOYMENT": BASE + DOM["employment"],
            "V6_ALL5": BASE + sum(DOM.values(), []), "V7_ALL5_ADD": BASE + sum(DOM.values(), []),
            "V8_FULL": BASE + sum(DOM.values(), []) + NEWS,
            "X1_MKTxEMP": BASE + DOM["market"] + DOM["employment"] + ["X_food_unemp"],
            "X2_FISHxCLIM": BASE + DOM["fish"] + DOM["climate"] + ["X_fish_oni"],
            "X3_CLIMxMKT": BASE + DOM["climate"] + DOM["market"] + ["X_oni_food"]}
PAIR_BASE = {"X1_MKTxEMP": BASE + DOM["market"] + DOM["employment"], "X2_FISHxCLIM": BASE + DOM["fish"] + DOM["climate"],
             "X3_CLIMxMKT": BASE + DOM["climate"] + DOM["market"]}
SPLITS = R14.SPLITS
GRID = R14.GRID


# ----------------------------------------------------------------------------------------------------------- features
def area_tables():
    c = pd.read_csv(DATA / "area_cpi.csv")
    f = pd.read_csv(DATA / "area_fish.csv")
    p = pd.read_csv(DATA / "area_palay.csv")
    cpi = {a: g.set_index("ym")[["food_yoy", "all_yoy"]] for a, g in c.groupby("area")}
    fish = {a: g.set_index("q")["yoy"] for a, g in f.groupby("area")}
    pal = {a: g.set_index("q")["yoy"] for a, g in p.groupby("area")}
    return cpi, fish, pal


def area_features(R, lag_shift=0):
    cpi, fish, pal = area_tables()
    out = {k: [] for k in ("AF_food", "AF_gap", "AF_dfood", "F_yoy", "F_dyoy", "PAL_yoy")}
    for a, t, iss in zip(R["area"], R["t"], R["issue"]):
        c = cpi.get(a)
        av = [m for m in c.index if R14.L._avail_month(int(m), iss)] if c is not None else []
        if len(av) >= 2:
            m = max(av)
            now = c.loc[[x for x in (m - 1, m) if x in c.index]]
            prev = c.loc[[x for x in (m - 13, m - 12) if x in c.index]]
            food, allv = float(now["food_yoy"].mean()), float(now["all_yoy"].mean())
            out["AF_food"].append(food)
            out["AF_gap"].append(food - allv)
            out["AF_dfood"].append(food - float(prev["food_yoy"].mean()) if len(prev) else np.nan)
        else:
            out["AF_food"].append(np.nan), out["AF_gap"].append(np.nan), out["AF_dfood"].append(np.nan)
        q = int(t) - 1 - lag_shift                                     # quarter t-1 published before O(t)
        fs = fish.get(a, pd.Series(dtype=float))
        out["F_yoy"].append(float(fs.get(q, np.nan)))
        out["F_dyoy"].append(float(fs.get(q, np.nan) - fs.get(q - 4, np.nan)))
        ps = pal.get(a, pd.Series(dtype=float))
        out["PAL_yoy"].append(float(ps.get(q, np.nan)))
    R = R.copy()
    for k, v in out.items():
        R[k] = v
    R["C_nino"] = (R["C-ONI"] >= .5).astype(float).where(R["C-ONI"].notna())
    R["X_food_unemp"] = R["AF_food"] * R["P-UNEMP"]
    R["X_fish_oni"] = R["F_yoy"] * R["C-ONI"]
    R["X_oni_food"] = R["C-ONI"] * R["AF_food"]
    return R


def rows(lag_shift=0):
    R = R14.build_rows()
    return area_features(R, lag_shift)


# ------------------------------------------------------------------------------------------------------------ model
def lgbm(cfg, cols=None, additive=False):
    import lightgbm as lgb
    kw = {}
    if additive:
        base = [cols.index(c) for c in BASE if c in cols]
        kw["interaction_constraints"] = [base + [cols.index(c) for c in g if c in cols] for g in DOM.values()]
    return lgb.LGBMRegressor(objective="l2", learning_rate=0.03, max_depth=cfg["depth"], num_leaves=2 ** cfg["depth"],
                             n_estimators=cfg["trees"], min_child_samples=20, reg_lambda=5.0, random_state=L.SEED,
                             deterministic=True, force_row_wise=True, n_jobs=1, verbose=-1, **kw)


def select(tr, cols, additive):
    origins = sorted(tr["t"].unique())[-4:]
    sc = {}
    for i, c in enumerate(GRID):
        err = []
        for o in origins:
            f = tr[(tr["t"] < o) & (tr["pub_target"] < L.issue(o))]
            h = tr[tr["t"] == o]
            if len(f) < 40 or not len(h):
                continue
            m = lgbm(c, cols, additive).fit(f[cols].astype(float), f["dy_known"])
            err.append(((m.predict(h[cols].astype(float)) - h["dy_known"]) ** 2).to_numpy())
        sc[i] = float(np.mean(np.concatenate(err))) if err else np.inf
    return GRID[min(sc, key=lambda i: (round(sc[i], 9), i))]


def rolling(job):
    name, cols, R, additive, keep_models, area_out = job
    out, models, train_mse = [], {}, []
    for t in sorted(R["t"].unique()):
        tr = R14.train_at(R, int(t))
        te = R[R["t"] == t]
        if area_out:
            tr, te = tr[tr["area"] != area_out], te[te["area"] == area_out]
        if len(tr) < 60 or tr["t"].nunique() < 8 or not len(te):
            continue
        cfg = select(tr, cols, additive)
        m = lgbm(cfg, cols, additive).fit(tr[cols].astype(float), tr["dy_known"])
        train_mse.append(float(np.mean((m.predict(tr[cols].astype(float)) - tr["dy_known"]) ** 2)))
        o = te[["area", "t", "lead"]].copy()
        o[name] = te["h_last"].to_numpy() + m.predict(te[cols].astype(float))
        out.append(o)
        if keep_models:
            models[int(t)] = m
    return name, pd.concat(out, ignore_index=True), models, float(np.mean(train_mse))


# ------------------------------------------------------------------------------------------------------- evaluation
def qdiff(g, a, b):
    return ((g[a] - g["y"]) ** 2 - (g[b] - g["y"]) ** 2).groupby(g["q"]).mean()


def compare(R, a, b, k, sp):
    g = R[(R["lead"] == k) & (R["split"] == sp) & R["y"].notna()].dropna(subset=[a, b])
    d = qdiff(g, a, b)
    dm = R14.dm(d, k)                                    # H1: a has lower MSE than b (mean d < 0 -> small p)
    return {"rows": int(len(g)), "quarters": int(d.size), "delta_mse": float(d.mean()), "ci90": R14.boot_q(d),
            "p_a_better": dm["p_one_sided"], "mse_a": float(((g[a] - g["y"]) ** 2).mean()), "mse_b": float(((g[b] - g["y"]) ** 2).mean())}


def holm(ps):
    items, run, out = sorted(ps.items(), key=lambda kv: kv[1]), 0.0, {}
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - i) * p))
        out[k] = run
    return out


def perm_importance(R, models, name, cols, sp, reps=20, seed=116):
    g = R[(R["split"] == sp) & R["y"].notna() & R["t"].isin(list(models))].copy()
    def pred(X):
        return np.concatenate([X.loc[X["t"] == t, "h_last"].to_numpy() + models[t].predict(X.loc[X["t"] == t, cols].astype(float)) for t in sorted(X["t"].unique())])
    g = g.sort_values("t")
    base = pred(g)
    base_mse = float(np.mean((base - g["y"].to_numpy()) ** 2))
    rng = np.random.default_rng(seed)
    out = {}
    for dname, dc in {**DOM, "news": NEWS, "hunger_history": ["h_last", "MR", "d_last", "stale"]}.items():
        dc = [c for c in dc if c in cols]
        if not dc:
            continue
        inc = []
        for _ in range(reps):
            X = g.copy()
            X[dc] = X[dc].to_numpy()[rng.permutation(len(X))]
            inc.append(float(np.mean((pred(X) - g["y"].to_numpy()) ** 2)) - base_mse)
        out[dname] = {"delta_mse_mean": float(np.mean(inc)), "delta_mse_p05_p95": [float(np.quantile(inc, .05)), float(np.quantile(inc, .95))]}
    return {"base_mse": base_mse, "rows": int(len(g)), "domains": out}


def shap_by_domain(R, models, cols, sp):
    g = R[(R["split"] == sp) & R["y"].notna() & R["t"].isin(list(models))]
    tot = {}
    for t, h in g.groupby("t"):
        sv = models[int(t)].booster_.predict(h[cols].astype(float), pred_contrib=True)[:, :-1]
        for j, c in enumerate(cols):
            tot[c] = tot.get(c, 0.0) + float(np.abs(sv[:, j]).sum())
    n = len(g)
    dmap = {c: d for d, cs in {**DOM, "news": NEWS, "base": BASE}.items() for c in cs}
    out = {}
    for c, v in tot.items():
        out[dmap.get(c, "interaction")] = out.get(dmap.get(c, "interaction"), 0.0) + v / n
    return out


def contributions(R):
    dom = {"market": "V2_MARKET", "fish": "V3_FISH", "climate": "V4_CLIMATE", "employment": "V5_EMPLOYMENT"}
    contrib = {}
    for k in (1, 2):
        for sp in SPLITS:
            key = f"L{k}|{sp}"
            contrib[key] = {d: compare(R, v, "V1_BASE", k, sp) for d, v in dom.items()}
            hp = holm({d: contrib[key][d]["p_a_better"] if contrib[key][d]["p_a_better"] is not None else 1.0 for d in dom})
            for d in dom:
                contrib[key][d]["holm_p"] = hp[d]
            for name, a, b in (("ALL5_vs_BASE", "V6_ALL5", "V1_BASE"), ("FULL_vs_BASE", "V8_FULL", "V1_BASE"),
                               ("ALL5_vs_ALL5_ADD", "V6_ALL5", "V7_ALL5_ADD"), ("BASE_vs_RW", "V1_BASE", "RW"),
                               ("ALL5_vs_RW", "V6_ALL5", "RW"), ("ALL5_vs_DAMP", "V6_ALL5", "DAMP"),
                               ("LOAO_ALL5_vs_LOAO_BASE", "LOAO_V6_ALL5", "LOAO_V1_BASE"),
                               ("SLAG_FISH_vs_BASE", "SLAG_V3_FISH", "V1_BASE"), ("SLAG_CLIMATE_vs_BASE", "SLAG_V4_CLIMATE", "V1_BASE"),
                               ("SLAG_ALL5_vs_ALL5", "SLAG_V6_ALL5", "V6_ALL5")):
                contrib[key][name] = compare(R, a, b, k, sp)
            for x in PAIR_BASE:
                contrib[key][f"{x}_vs_noX"] = compare(R, x, f"{x}_noX", k, sp)
    decision = {}
    for k in (1, 2):
        dv, ts = contrib[f"L{k}|DEV"], contrib[f"L{k}|TEST"]
        decision[k] = {d: ("adds information" if dv[d]["ci90"][1] < 0 and dv[d]["holm_p"] < .10 and ts[d]["delta_mse"] < 0
                           else "possible noise" if dv[d]["ci90"][0] > 0 else "not established") for d in dom}
    return contrib, decision


def eval_only():
    """Recompute the comparisons from the saved predictions (no refit): used after the p-value sign fix."""
    R = pd.read_csv(OUT / "e116_rows.csv")
    res = json.loads((OUT / "e116_results.json").read_text())
    res["contributions"], res["decision_domains"] = contributions(R)
    res["note_eval_fix"] = ("2026-10-30: compare() passed -d to the DM helper, inverting the one-sided p and Holm p; "
                            "fixed and recomputed from the saved predictions (e116_rows.csv). Point estimates, CIs, "
                            "permutation and SHAP results are unchanged.")
    (OUT / "e116_results.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res["decision_domains"], indent=1))


def main():
    proto = ROOT / "PROTOCOL_E116.md"
    sha = hashlib.sha256(proto.read_bytes()).hexdigest()
    assert sha == (HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "protocol changed"
    OUT.mkdir(exist_ok=True)
    res = {"protocol_sha256": sha, "data_sha256": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(DATA.glob("*.csv"))}}
    R = rows()
    RL = rows(lag_shift=1)
    R["RW"] = R["h_last"]
    R["DAMP"] = R["mean_known"] + 0.5 ** R["lead"] * (R["h_last"] - R["mean_known"])
    res["coverage_lead2"] = {c: float(R.loc[R["lead"] == 2, c].notna().mean()) for c in sum(DOM.values(), []) + NEWS}
    res["coverage_by_split_lead2"] = {sp: {c: float(R.loc[(R["lead"] == 2) & (R["split"] == sp), c].notna().mean()) for c in sum(DOM.values(), []) + NEWS} for sp in SPLITS}
    jobs = [(n, c, R, n == "V7_ALL5_ADD", n in ("V1_BASE", "V6_ALL5", "V8_FULL"), None) for n, c in VARIANTS.items()]
    jobs += [(f"{n}_noX", c, R, False, False, None) for n, c in PAIR_BASE.items()]
    jobs += [(f"LOAO_{n}_{a}", VARIANTS[n], R, False, False, a) for n in ("V1_BASE", "V6_ALL5") for a in AREAS]
    jobs += [(f"SLAG_{n}", VARIANTS[n], RL, False, False, None) for n in ("V3_FISH", "V4_CLIMATE", "V6_ALL5")]
    models, trains, preds = {}, {}, []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for name, P, M, tm in ex.map(rolling, jobs):
            preds.append(P.set_index(["area", "t", "lead"]))
            if M:
                models[name] = M
            trains[name] = tm
            print("done", name, flush=True)
    P = pd.concat(preds, axis=1).reset_index()
    loao = {n: [c for c in P.columns if c.startswith(f"LOAO_{n}_")] for n in ("V1_BASE", "V6_ALL5")}
    for n, cs in loao.items():
        P[f"LOAO_{n}"] = P[cs].bfill(axis=1).iloc[:, 0]
        P = P.drop(columns=cs)
    R = R.merge(P, on=["area", "t", "lead"], how="left")
    R.to_csv(OUT / "e116_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    names = list(VARIANTS) + [f"{n}_noX" for n in PAIR_BASE] + ["LOAO_V1_BASE", "LOAO_V6_ALL5", "SLAG_V3_FISH", "SLAG_V4_CLIMATE", "SLAG_V6_ALL5", "RW", "DAMP"]
    ev = {}
    for k in (1, 2):
        for sp in SPLITS:
            g = R[(R["lead"] == k) & (R["split"] == sp) & R["y"].notna()]
            ev[f"L{k}|{sp}"] = {n: {"mse": float(((g[n] - g["y"]) ** 2).mean()), "mae": float((g[n] - g["y"]).abs().mean()),
                                   "mse_BL": float(((g.loc[g["area"] == "BL", n] - g.loc[g["area"] == "BL", "y"]) ** 2).mean()),
                                   "rows": int(g[n].notna().sum())} for n in names if n in g}
    res["mse"] = ev
    dom = {"market": "V2_MARKET", "fish": "V3_FISH", "climate": "V4_CLIMATE", "employment": "V5_EMPLOYMENT"}
    contrib = {}
    for k in (1, 2):
        for sp in SPLITS:
            key = f"L{k}|{sp}"
            contrib[key] = {d: compare(R, v, "V1_BASE", k, sp) for d, v in dom.items()}
            hp = holm({d: contrib[key][d]["p_a_better"] if contrib[key][d]["p_a_better"] is not None else 1.0 for d in dom})
            for d in dom:
                contrib[key][d]["holm_p"] = hp[d]
            contrib[key]["ALL5_vs_BASE"] = compare(R, "V6_ALL5", "V1_BASE", k, sp)
            contrib[key]["FULL_vs_BASE"] = compare(R, "V8_FULL", "V1_BASE", k, sp)
            contrib[key]["ALL5_vs_ALL5_ADD"] = compare(R, "V6_ALL5", "V7_ALL5_ADD", k, sp)
            contrib[key]["BASE_vs_RW"] = compare(R, "V1_BASE", "RW", k, sp)
            contrib[key]["ALL5_vs_RW"] = compare(R, "V6_ALL5", "RW", k, sp)
            contrib[key]["ALL5_vs_DAMP"] = compare(R, "V6_ALL5", "DAMP", k, sp)
            for x in PAIR_BASE:
                contrib[key][f"{x}_vs_noX"] = compare(R, x, f"{x}_noX", k, sp)
            contrib[key]["LOAO_ALL5_vs_LOAO_BASE"] = compare(R, "LOAO_V6_ALL5", "LOAO_V1_BASE", k, sp)
            contrib[key]["SLAG_FISH_vs_BASE"] = compare(R, "SLAG_V3_FISH", "V1_BASE", k, sp)
            contrib[key]["SLAG_CLIMATE_vs_BASE"] = compare(R, "SLAG_V4_CLIMATE", "V1_BASE", k, sp)
    res["contributions"] = contrib
    res["decision_domains"] = {}
    for k in (1, 2):
        dv, ts = contrib[f"L{k}|DEV"], contrib[f"L{k}|TEST"]
        res["decision_domains"][k] = {d: ("adds information" if dv[d]["ci90"][1] < 0 and dv[d]["holm_p"] < .10 and ts[d]["delta_mse"] < 0
                                          else "possible noise" if dv[d]["ci90"][0] > 0 else "not established") for d in dom}
    res["train_mse"] = trains
    res["permutation"] = {f"{n}|{sp}": perm_importance(R, models[n], n, VARIANTS[n], sp) for n in models for sp in ("DEV", "TEST")}
    res["shap_mean_abs"] = {f"{n}|{sp}": shap_by_domain(R, models[n], VARIANTS[n], sp) for n in models for sp in ("DEV", "TEST")}
    # above-usual probabilities as E114 (sigma from own earlier errors)
    keep = ["V1_BASE", "V6_ALL5", "V8_FULL", "RW", "DAMP"]
    R14_models = R14.MODELS
    R14.MODELS = keep
    R2 = R14.add_probabilities(R.copy())
    R14.MODELS = R14_models
    res["above_usual"] = {f"L{k}|{sp}": {m: R14.binm(*(lambda h: (h["yU"], h[f"{m}_pU"]))(R2[(R2["lead"] == k) & (R2["split"] == sp) & R2["y"].notna()].dropna(subset=[f"{m}_pU"])))
                                        for m in keep} for k in (1, 2) for sp in SPLITS}
    (OUT / "e116_results.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res["decision_domains"], indent=1))
    for key in ("L1|DEV", "L2|DEV", "L1|TEST", "L2|TEST"):
        print(key, {d: (round(v["delta_mse"], 3), [round(x, 2) for x in v["ci90"]], v.get("holm_p") and round(v["holm_p"], 3)) for d, v in contrib[key].items()})


if __name__ == "__main__":
    eval_only() if sys.argv[1:] == ["--eval-only"] else main()
