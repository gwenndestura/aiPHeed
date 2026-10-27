"""PROTOCOL section 9: contributions. Structural ablations of FINAL (price projection -> price climatology,
pi_H -> hunger climatology, drift); the ten families through LJ (add-one, leave-one-out, permutation, Holm); SHAP
stability of LJ; power (MDE) per family.

    python contrib_ii.py        # out/contrib_ii.json, out/contrib_ii_rows.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import ii_lib as L
from price_arms import REG_GRID

F, M, KEY = L.F, L.M, L.KEY
TEN = ["A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1"]
FAM = ["A1"] + TEN + ["H1"]


def boot(q, a, b, draws=4000, seed=L.SEED) -> dict:
    """Mean of a - b, quarter-block bootstrap; also the bootstrap SD (for the MDE)."""
    q, d = np.asarray(q), np.asarray(a, float) - np.asarray(b, float)
    uq = np.unique(q)
    by = [d[q == u] for u in uq]
    rng = np.random.default_rng(seed)
    bs = np.array([np.concatenate([by[i] for i in rng.integers(0, len(uq), len(uq))]).mean() for _ in range(draws)])
    return {"diff": float(d.mean()), "ci90": [float(np.quantile(bs, .05)), float(np.quantile(bs, .95))], "sd": float(bs.std()),
            "p_less": float((bs >= 0).mean()), "p_greater": float((bs <= 0).mean()),
            "p_two": float(min(1.0, 2 * min((bs >= 0).mean(), (bs <= 0).mean())))}


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - i) * p))
        out[k] = run
    return out


def prepared() -> pd.DataFrame:
    S = F.stack().copy()
    A = pd.read_csv(L.OUT / "price_arms_ii.csv", dtype={"province_code": str})
    base = A[A["arm"] == "J3T"][KEY + ["pi_P"]].rename(columns={"pi_P": "base"})
    S = S.merge(base, on=KEY, how="inner")
    S["y_price"] = (((S["F"] - S["province_code"].map(F.TH_F)) > 0) | ((S["F"] - S["HL"] - S["province_code"].map(F.TH_G)) > 0)).astype(float)
    S.loc[S["F"].isna(), "y_price"] = np.nan
    b = np.clip(S["base"], .005, .995)
    S["init"] = np.log(b / (1 - b))
    return S


def _fit(tr, cols, cfg):
    import lightgbm as lgb
    m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, n_estimators=cfg["trees"], num_leaves=2, max_depth=1,
                           min_child_samples=25, reg_lambda=10.0, reg_alpha=1.0, colsample_bytree=0.7, subsample=1.0,
                           deterministic=True, force_row_wise=True, feature_pre_filter=False, random_state=L.SEED,
                           n_jobs=1, verbose=-1)
    m.fit(tr[cols].astype(float), tr["y_price"].astype(int), init_score=tr["init"].to_numpy())
    return m


def _pred(m, te, cols):
    if m is None:                                           # LJ = J3T when no model is fitted (price_arms.lj)
        return te["base"].to_numpy(float)
    raw = m.predict(te[cols].astype(float), raw_score=True) + te["init"].to_numpy()
    return 1 / (1 + np.exp(-raw))


def lj_run(S: pd.DataFrame, cols: list[str], origins) -> tuple[pd.DataFrame, dict]:
    """LJ with the given columns at each origin (same selection as price_arms.lj); returns predictions and models."""
    out, models = [], {}
    for t in origins:
        te = S[S["t"] == t]
        tr = S[(S["t"] < t) & (S["target_q"] <= t - 1) & S["y_price"].notna()]
        m = None
        if len(tr) >= 30 and tr["y_price"].nunique() == 2:
            folds = []
            for o in sorted(tr["t"].unique())[-4:]:
                f = tr[(tr["t"] < o) & (tr["target_q"] <= o - 1)]
                h = tr[tr["t"] == o]
                if len(f) >= 30 and f["y_price"].nunique() == 2 and len(h):
                    folds.append((f, h))
            best, best_ll = REG_GRID[0], None
            for cfg in REG_GRID:
                if not folds:
                    break
                ys = np.concatenate([h["y_price"].to_numpy(int) for _, h in folds])
                pp = np.clip(np.concatenate([_pred(_fit(f, cols, cfg), h, cols) for f, h in folds]), 1e-6, 1 - 1e-6)
                ll = float(-np.mean(ys * np.log(pp) + (1 - ys) * np.log(1 - pp)))
                if best_ll is None or round(ll, 10) < round(best_ll, 10):
                    best, best_ll = cfg, ll
            m = _fit(tr, cols, best)
        models[int(t)] = m
        out.append(te[KEY].assign(p=_pred(m, te, cols)))
    return pd.concat(out, ignore_index=True), models


def main():
    L.check_protocol()
    S = prepared()
    E = pd.read_csv(L.OUT / "predictions_ii.csv", dtype={"province_code": str})
    res = json.loads((L.OUT / "results_ii.json").read_text())
    final = res["selection"]["chosen_FINAL"]
    origins = sorted(E["t"].unique())
    all_origins = sorted(S["t"].unique())
    out = {"FINAL": final, "structural": {}, "families": {}, "shap": {}}
    # ------------------------------------------------------------ structural ablations of FINAL
    allS = S[S["y_price"].notna()]
    clim = []
    for t, k in zip(E["t"], E["lead"]):
        tr = allS[(allS["t"] < t) & (allS["target_q"] <= t - 1) & (allS["lead"] == k)]
        clim.append(float(tr["y_price"].mean()) if len(tr) else 0.5)
    E["price_clim"] = clim
    hc = []
    for t, k in zip(E["t"], E["lead"]):
        hc.append(F.hunger_climatology(F.issue(int(t), "A" if k == 1 else "B")))
    E["hunger_clim"] = hc
    fp = f"{final}_p"
    variants = {"no_price_projection": E["pi_H_AB"] * E["price_clim"], "no_hunger_term": E["hunger_clim"] * E[f"{final}_price"],
                "add_anchored_drift(J2)": E["J2_p"], "zero_drift_joint(J0)": E["J0_p"]}
    for name, v in variants.items():
        out["structural"][name] = {int(k): boot(g["q"], (v[g.index] - g["y"]) ** 2, (g[fp] - g["y"]) ** 2) for k, g in E.groupby("lead")}
    # ------------------------------------------------------------ ten families through LJ
    full, models = lj_run(S, F.F12, all_origins)
    E = E.merge(full.rename(columns={"p": "LJfull_price"}), on=KEY, how="left")
    print("LJ rerun max abs diff", float((E["LJfull_price"] - E["LJ_price"]).abs().max()))
    assert np.allclose(E["LJfull_price"], E["LJ_price"], atol=2e-5), "LJ re-run differs from price_arms"
    rows = E[KEY + ["q", "y", "pi_H_AB", "J3T_price", "LJ_price"]].copy()
    for f in FAM:
        cols_add = F.FAMILY_COLS[f] + ["lead"]
        cols_loo = [c for c in F.F12 if c not in F.FAMILY_COLS[f]]
        a, _ = lj_run(S, cols_add, all_origins)
        o, _ = lj_run(S, cols_loo, all_origins)
        rows = rows.merge(a.rename(columns={"p": f"add_{f}"}), on=KEY, how="left").merge(o.rename(columns={"p": f"loo_{f}"}), on=KEY, how="left")
        # permutation: LJ-full fixed, f's columns from a random other evaluation origin (same province and lead)
        rng = np.random.default_rng(L.SEED + FAM.index(f))
        perm = np.zeros(len(rows))
        Sev = S[S["t"].isin(origins)].set_index(KEY)
        for d in range(20):
            pr = []
            for t in origins:
                te = S[S["t"] == t].copy()
                others = [o_ for o_ in origins if o_ != t]
                src = int(rng.choice(others))
                for c in F.FAMILY_COLS[f]:
                    te[c] = [Sev[c].get((src, k, p), np.nan) for k, p in zip(te["lead"], te["province_code"])]
                pr.append(te[KEY].assign(p=_pred(models[int(t)], te, F.F12)))
            pr = rows[KEY].merge(pd.concat(pr), on=KEY, how="left")["p"].to_numpy()
            perm += pr / 20
        rows[f"perm_{f}"] = perm
        print(f, "done", flush=True)
    for name in ("add", "loo", "perm"):
        for f in FAM:
            rows[f"{name}_{f}_t43c"] = rows["pi_H_AB"] * rows[f"{name}_{f}"]
    rows["J3T_t43c"] = rows["pi_H_AB"] * rows["J3T_price"]
    rows["LJ_t43c"] = rows["pi_H_AB"] * rows["LJ_price"]
    for f in FAM:
        fam = {"add_one": {}, "leave_one_out": {}, "permutation": {}}
        for k in (1, 2, 3):
            g = rows[rows["lead"] == k]
            bJ, bL = (g["J3T_t43c"] - g["y"]) ** 2, (g["LJ_t43c"] - g["y"]) ** 2
            fam["add_one"][k] = boot(g["q"], bJ, (g[f"add_{f}_t43c"] - g["y"]) ** 2)        # > 0 = helps
            fam["leave_one_out"][k] = boot(g["q"], (g[f"loo_{f}_t43c"] - g["y"]) ** 2, bL)   # > 0 = f helped
            fam["permutation"][k] = boot(g["q"], (g[f"perm_{f}_t43c"] - g["y"]) ** 2, bL)    # > 0 = f helped
        out["families"][f] = fam
    for k in (1, 2, 3):
        hp = holm({f: out["families"][f]["add_one"][k]["p_greater"] for f in FAM})
        for f in FAM:
            out["families"][f]["add_one"][k]["holm_p_helps"] = hp[f]
    for f in FAM:
        a = out["families"][f]["add_one"]
        helps = [k for k in (1, 2, 3) if a[k]["ci90"][0] > 0]
        worse = [k for k in (1, 2, 3) if a[k]["ci90"][1] < 0]
        perm_ok = [k for k in helps if out["families"][f]["permutation"][k]["diff"] > 0]
        out["families"][f]["class"] = ("predictive" if perm_ok and not worse else
                                       "weak" if any(a[k]["diff"] > 0 for k in (1, 2, 3)) or
                                       any(out["families"][f]["leave_one_out"][k]["diff"] > 0 for k in (1, 2, 3)) else
                                       "no demonstrated value")
        out["families"][f]["worse_leads"] = worse
        out["families"][f]["mde_t43c"] = {k: 2.49 * a[k]["sd"] for k in (1, 2, 3)}
        out["families"][f]["best_case_improvement"] = {k: a[k]["ci90"][1] for k in (1, 2, 3)}
    # ------------------------------------------------------------ SHAP of LJ-full by thirds
    thirds = np.array_split(np.array(origins), 3)
    shp = []
    for th in thirds:
        acc = {f: [] for f in FAM + ["lead"]}
        for t in th:
            m = models[int(t)]
            if m is None:
                continue
            te = S[S["t"] == t]
            c = m.predict(te[F.F12].astype(float), pred_contrib=True)[:, :-1]
            for j, col in enumerate(F.F12):
                fam = F.FAMILY_OF.get(col, "lead")
                acc[fam].append(np.abs(c[:, j]).mean())
        shp.append({f: float(np.sum(v)) / max(len(th), 1) for f, v in acc.items()})
    out["shap"]["by_third"] = shp
    fams = FAM
    out["shap"]["spearman"] = {f"{a}-{b}": float(spearmanr([shp[a][f] for f in fams], [shp[b][f] for f in fams]).statistic)
                               for a, b in ((0, 1), (1, 2), (0, 2))}
    rows.to_csv(L.OUT / "contrib_ii_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    L.dump("contrib_ii.json", out)
    for n, v in out["structural"].items():
        print("STRUCT", n, {k: (round(x["diff"], 4), [round(c, 4) for c in x["ci90"]]) for k, x in v.items()})
    for f in FAM:
        r = out["families"][f]
        print(f"{f:3s} {r['class']:22s}", " | ".join(
            f"L{k} add {r['add_one'][k]['diff']:+.4f}[{r['add_one'][k]['ci90'][0]:+.3f},{r['add_one'][k]['ci90'][1]:+.3f}] "
            f"loo {r['leave_one_out'][k]['diff']:+.4f} perm {r['permutation'][k]['diff']:+.4f} mde {r['mde_t43c'][k]:.3f}"
            for k in (1, 2, 3)))
    print("SHAP", out["shap"])


if __name__ == "__main__":
    main()
