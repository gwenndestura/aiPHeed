"""E93 (PROTOCOL.md): one unified, news-informed LightGBM framework for K = 1..4. Run from backend/.

Every probability is P(hunger condition at t+K) x P(price condition at t+K), both from LightGBM models fitted once per
origin on the pooled horizons K = 1..4, with K as an input and the ten news indicators as required inputs.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
E93 = HERE.parent
EXP = E93.parent
sys.path.insert(0, str(EXP / "E92_LightGBM_Lead2" / "runner"))
import run_e92 as G  # noqa: E402

U, E, L, np, pd, R9 = G.U, G.E, G.L, G.np, G.pd, G.R9
from scipy.stats import norm  # noqa: E402

TH = G.TH
KS = (1, 2, 3, 4)
NEWS = G.NEWS
SELECT_TO = "2024-Q4"
E92_RUN = EXP / "E92_LightGBM_Lead2" / "runs" / "20261022T055421Z"
E91_RUN = EXP / "E91_Unified_Horizon_Model" / "runs" / "20261022T045201Z"

# direction / acceleration / cumulative features, from the same origin-time tables at earlier origins (all <= O(t))
DIR_SRC = ["F_now", "gap_now", "rice_yoy_now", "rice_mom3", "ur_yoy", "remit_usd_yoy", "enso", "tc_count", "H_last"]
NEWS_DIR = ["n3_market_rw", "n3_climate_rw", "n3_employment_rw", "n3_fish_kill_rw", "n3_fssi", "n3_cov"]
DIR_F = ["dF1", "dF2", "dG1", "rice_acc", "cumF4", "d_ur", "d_remit", "enso_run3", "tc_run3", "dH1",
         "rice_x_H", "enso_x_rice"]
NEWS_DIR_F = [f"d_{c}" for c in NEWS_DIR] + [f"run2_{c}" for c in NEWS_DIR]
PRICE_BASE = [c for c in G.PRICE_F] + G.PRICE_S
HUNGER_BASE = list(G.HUNGER_F)
GB = dict(objective="binary", num_leaves=4, max_depth=2, n_estimators=100, learning_rate=0.05, min_child_samples=5,
          reg_lambda=5.0, random_state=93, deterministic=True, n_jobs=1, force_row_wise=True, verbosity=-1)
REG = dict(objective="regression", num_leaves=4, max_depth=2, n_estimators=100, learning_rate=0.05, min_child_samples=3,
           reg_lambda=5.0, linear_tree=True, linear_lambda=1.0, random_state=93, deterministic=True, n_jobs=1,
           force_row_wise=True, verbosity=-1)
SPW_GRID = (1.0, 2.0, 4.0)


# ------------------------------------------------------------------------------------------------ features
def direction_frame(T1: pd.DataFrame) -> pd.DataFrame:
    """Per (t, province): changes against the same province's features at origins t-1, t-2, t-3 (k-independent)."""
    out = []
    for p, g in T1.sort_values("t").groupby("province_code"):
        g = g.set_index("t")
        lag = lambda c, n: g[c].shift(n)  # noqa: E731 (t is consecutive in the tables)
        f = pd.DataFrame(index=g.index)
        f["dF1"], f["dF2"] = g["F_now"] - lag("F_now", 1), g["F_now"] - lag("F_now", 2)
        f["dG1"] = g["gap_now"] - lag("gap_now", 1)
        f["rice_acc"] = g["rice_yoy_now"] - lag("rice_yoy_now", 1)
        f["cumF4"] = g["F_now"].rolling(4, min_periods=4).sum()
        f["d_ur"], f["d_remit"] = g["ur_yoy"] - lag("ur_yoy", 1), g["remit_usd_yoy"] - lag("remit_usd_yoy", 1)
        f["enso_run3"], f["tc_run3"] = g["enso"].rolling(3, min_periods=1).sum(), g["tc_count"].rolling(3, min_periods=1).sum()
        f["dH1"] = g["H_last"] - lag("H_last", 1)
        f["rice_x_H"] = g["rice_yoy_now"] * (g["H_last"] - TH["H"])
        f["enso_x_rice"] = f["enso_run3"] * g["rice_yoy_now"]
        for c in NEWS_DIR:
            f[f"d_{c}"] = g[c] - lag(c, 1)
            f[f"run2_{c}"] = g[c].rolling(2, min_periods=1).sum()
        out.append(f.reset_index().assign(province_code=p))
    return pd.concat(out, ignore_index=True)


def tables() -> dict:
    T = {k: G.prep(pd.read_csv(U.TABLES / f"features_k{k}.csv", dtype={"province_code": str})) for k in KS}
    D = direction_frame(T[1])
    return {k: T[k].merge(D, on=["t", "province_code"], how="left") for k in KS}


# ------------------------------------------------------------------------------------------------ parts
def _clf(cols, tr, y, te, spw=1.0, w=None):
    from lightgbm import LGBMClassifier
    mono = [1 if c in G.MONO_UP else 0 for c in cols]
    m = LGBMClassifier(**GB, scale_pos_weight=spw, monotone_constraints=mono)
    m.fit(tr[cols].astype(float), y, sample_weight=w)                       # native missing-value handling
    return m.predict_proba(te[cols].astype(float))[:, 1]


def _logloss(y, p):
    p = np.clip(p, 1e-3, 1 - 1e-3)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def price_training(T, d, t):
    lab = R9.price_labels(d.cut(t))
    lab = lab[lab["q"] <= t - 1]
    tr = pd.concat([T[k][T[k]["t"] + k <= t - 1].assign(k=k, q=lambda f: f["t"] + f["k"]) for k in KS])
    return tr.merge(lab, on=["province_code", "q"])


def price_part(tr, te, cols, weighted: bool):
    ok = tr["q"].nunique() >= 6 and tr["y_price"].sum() >= 5 and (1 - tr["y_price"]).sum() >= 5
    if not ok:
        return np.full(len(te), G.freq(tr["y_price"]) if len(tr) else 0.5), False, 1.0
    spw = 1.0
    if weighted:                                       # inner chronological validation: the last 3 label quarters
        qs = sorted(tr["q"].unique())
        inner, hold = tr[tr["q"] < qs[-3]], tr[tr["q"] >= qs[-3]]
        if inner["y_price"].nunique() == 2 and hold["y_price"].nunique() == 2 and inner["q"].nunique() >= 4:
            ll = {s: _logloss(hold["y_price"].to_numpy(), _clf(cols, inner, inner["y_price"], hold, s)) for s in SPW_GRID}
            spw = min(SPW_GRID, key=lambda s: (round(ll[s], 10), s))
    return _clf(cols, tr, tr["y_price"], te, spw), True, spw


def hunger_rows(T, d, t, cols):
    hq = L.h_quarters(d.cut(t)).set_index("q")["H"]
    rows = []
    for k in KS:
        R = T[k][T[k]["t"] + k <= t - 1]
        g = R.groupby("t")[[c for c in cols if c != "k"]].mean().reset_index()
        for _, r in g.iterrows():
            q = int(r["t"]) + k
            if q in hq.index:
                rows.append({**r.to_dict(), "k": k, "q": q, "H": hq[q], "y": int(hq[q] > TH["H"])})
    return pd.DataFrame(rows)


def hunger_clf(tr, te_row, cols):
    if len(tr) < 8 or tr["y"].sum() < 2 or (1 - tr["y"]).sum() < 2:
        return G.freq(tr["y"]) if len(tr) else 0.5, False
    from lightgbm import LGBMClassifier
    mono = [1 if c in G.MONO_UP else 0 for c in cols]
    m = LGBMClassifier(**dict(GB, min_child_samples=3), monotone_constraints=mono).fit(tr[cols].astype(float), tr["y"])
    return float(m.predict_proba(te_row[cols].astype(float))[0, 1]), True


def hunger_lin(tr, te_row, cols, d, t, k, recency: bool):
    """Linear-tree LightGBM regression of the hunger change; P(H > 11.3) from a normal with the larger of the residual
    RMSE and the posted-history random-walk sd for the gap."""
    from lightgbm import LGBMRegressor
    hs = L.h_quarters(d.cut(t)).sort_values("q")
    qq, hh = hs["q"].to_numpy(), hs["H"].to_numpy()
    sig = float(np.sqrt(np.mean((np.diff(hh) / np.sqrt(np.diff(qq))) ** 2)))
    s_min = sig * math.sqrt(max(t + k - int(qq[-1]), 1))
    H_last = float(te_row["H_rel"].iloc[0]) + TH["H"]
    if len(tr) < 8:
        dh = float((tr["H"] - tr["H_rel"] - TH["H"]).mean()) if len(tr) else 0.0
        return float(1 - norm.cdf((TH["H"] - (H_last + dh)) / s_min)), False, 0.0
    y = tr["H"] - (tr["H_rel"] + TH["H"])
    med = tr[cols].median()
    A, B = tr[cols].astype(float).fillna(med).fillna(0.0), te_row[cols].astype(float).fillna(med).fillna(0.0)
    hl = 0.0
    if recency:                                        # inner choice: no weighting vs half-life 4 quarters
        qs = sorted(tr["q"].unique())
        if len(qs) >= 7:
            inner, hold = tr["q"] < qs[-3], tr["q"] >= qs[-3]
            err = {}
            for h in (0.0, 4.0):
                w = None if h == 0 else 0.5 ** ((tr.loc[inner, "q"].max() - tr.loc[inner, "q"]) / h)
                m = LGBMRegressor(**REG).fit(A[inner], y[inner], sample_weight=w)
                err[h] = float(np.sqrt(np.mean((y[hold] - m.predict(A[hold])) ** 2)))
            hl = min(err, key=lambda h: (round(err[h], 10), h))
    w = None if hl == 0 else 0.5 ** ((tr["q"].max() - tr["q"]) / hl)
    m = LGBMRegressor(**REG).fit(A, y, sample_weight=w)
    rmse = float(np.sqrt(np.mean((y - m.predict(A)) ** 2)))
    Hh = H_last + float(m.predict(B)[0])
    return float(1 - norm.cdf((TH["H"] - Hh) / max(s_min, rmse))), True, hl


# ------------------------------------------------------------------------------------------------ arms
def arm_cols(news: bool, direction: bool):
    nf = NEWS if news else []
    df = DIR_F if direction else []
    ndf = NEWS_DIR_F if (news and direction) else []
    return PRICE_BASE + nf + df + ndf, HUNGER_BASE + nf + df + ndf


ARMS = {  # name: (hunger part, direction features, weighting/recency by inner validation, news)
    "M-U93-DIR": ("clf", True, False, True),
    "M-U93-LINDIR": ("lin", True, False, True),
    "M-U93-LINDIR-W": ("lin", True, True, True),
}
ABLATIONS = {
    "M-U93-LINDIR-W-NONEWS": ("lin", True, True, False),
    "M-U93-LIN-W-NODIR": ("lin", False, True, True),
}


def run(d, Ps, T, arms: dict) -> dict:
    out = {k: Ps[k].copy() for k in KS}
    origins = sorted({int(t) for k in KS for t in Ps[k]["t"]})
    for name, (hp, direction, weighted, news) in arms.items():
        pc, hc = arm_cols(news, direction)
        for k in KS:
            out[k][name] = np.nan
        for t in origins:
            ptr = price_training(T, d, t)
            htr = hunger_rows(T, d, t, hc)
            for k in KS:
                m = out[k]["t"] == t
                if not m.any():
                    continue
                te = T[k][T[k]["t"] == t].set_index("province_code").loc[L.PROVS].reset_index().assign(k=k)
                te_row = te[[c for c in hc if c != "k"]].mean().to_frame().T.assign(k=k)
                pp, fp, spw = price_part(ptr, te, pc, weighted)
                if hp == "clf":
                    ph, fh = hunger_clf(htr, te_row, hc)
                    hl = 0.0
                else:
                    ph, fh, hl = hunger_lin(htr, te_row, hc, d, t, k, weighted)
                out[k].loc[m, name] = ph * pp
                if name == "M-U93-LINDIR-W":
                    out[k].loc[m, "p_hunger"], out[k].loc[m, "p_price"] = ph, pp
                    out[k].loc[m, "fit_price"], out[k].loc[m, "fit_hunger"] = fp, fh
                    out[k].loc[m, "spw"], out[k].loc[m, "half_life"] = spw, hl
    return out


def hunger_outcome_eval(P: pd.DataFrame, d) -> dict:
    """The hunger part alone against the regional food-insecurity outcome (SWS hunger > 11.3), one row per target
    quarter, against hunger persistence (last posted reading above the line)."""
    hq = L.h_quarters(d).set_index("q")["H"]
    g = P.groupby("target_q").agg(p=("p_hunger", "first"), t=("t", "first")).reset_index()
    g["y"] = [int(hq[L.qi(q)] > TH["H"]) for q in g["target_q"]]
    g["persist"] = [int(L.h_quarters(d.cut(int(t))).sort_values("q")["H"].iloc[-1] > TH["H"]) for t in g["t"]]
    return {"n": len(g), "high": int(g["y"].sum()),
            "model": E.metrics(g["y"], (g["p"] >= 0.5).astype(int), g["p"]),
            "persistence": E.metrics(g["y"], g["persist"], g["persist"].astype(float))}


if __name__ == "__main__":
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = E93 / "runs" / stamp
    o.mkdir(parents=True, exist_ok=True)
    d, _ = E.data()
    _, Ps = U.load_tables()
    T = tables()
    Pr = run(d, Ps, T, {**ARMS, **ABLATIONS})
    names = list(ARMS) + list(ABLATIONS)
    summ = {"stamp": stamp, "protocol_sha256": (E93 / "PROTOCOL.sha256").read_text().split()[0], "per_k": {}, "baselines": {}}
    for k in KS:
        P = Pr[k]
        if k <= 3:
            P92 = pd.read_csv(E92_RUN / f"predictions_round2_k{k}.csv", dtype={"province_code": str})
            P["M-E92-DEC-S"], P["M-E92-LIN-posthoc"] = P92["M-LGB-DEC-S"].to_numpy(), P92["M-LGB-LIN"].to_numpy()
        else:
            P["M-E92-DEC-S"], P["M-E92-LIN-posthoc"] = np.nan, np.nan
        P.to_csv(o / f"predictions_k{k}.csv", index=False)
        arms = names + ["M-E92-DEC-S", "M-E92-LIN-posthoc", "S-COV", "S-SIM"]
        summ["per_k"][k], summ["baselines"][k] = U.evaluate_k(P, arms)
        summ["per_k"][k]["_hunger_outcome"] = hunger_outcome_eval(P, d)
        summ["per_k"][k]["_inner_choices"] = {"spw": P["spw"].value_counts().to_dict(), "half_life": P["half_life"].value_counts().to_dict(),
                                              "fit_price": float(P["fit_price"].mean()), "fit_hunger": float(P["fit_hunger"].mean())}
    KSEL = [1, 2, 3]
    sel = {a: float(np.mean([summ["per_k"][k][a]["selection_block_brier"] for k in KSEL])) for a in ARMS}
    chosen = min(sel, key=sel.get)
    summ["selection_mean_brier"], summ["selected"] = sel, chosen
    summ["K"] = {a: U.k_validated(summ["per_k"], a) for a in names + ["S-COV"]}
    (o / "metrics.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8")
    print("selection (mean Brier K=1..3, targets <= 2024-Q4):", {a: round(v, 4) for a, v in sel.items()}, "->", chosen)
    for k in KS:
        print(f"K={k}  inner:", summ["per_k"][k]["_inner_choices"])
        for b in ("B-PERSIST", "B-AL"):
            m = summ["baselines"][k][b]
            print(f"  {b:22s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} brier={m['brier']:.3f}")
        for a in names + ["M-E92-DEC-S", "M-E92-LIN-posthoc", "S-COV"]:
            r = summ["per_k"][k][a]
            m, g, ps = r["metrics"], r["generalization"], r["pass"]
            th = {b: round(v.get("p_holm", 1), 3) for b, v in r["tests"].items()}
            print(f"  {a:22s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} P/R/F1={m['precision'] or 0:.2f}/"
                  f"{m['recall_HIGH'] or 0:.2f}/{m['f1']:.2f} TP/FP/FN/TN={m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} "
                  f"brier={m['brier']:.3f} PASS={ps['PASS']} {[c for c, v in ps.items() if not v and c not in ('PASS', 'TARGET_80')]} "
                  f"holm={th} W/L={g['wins']}/{g['losses']} e/l={g['early_acc']:.2f}/{g['late_acc']:.2f}", flush=True)
        ho = summ["per_k"][k]["_hunger_outcome"]
        print(f"  hunger part vs SWS hunger>11.3 (n={ho['n']}, high={ho['high']}): model acc={ho['model']['accuracy']:.3f} "
              f"brier={ho['model']['brier']:.3f} | persistence acc={ho['persistence']['accuracy']:.3f} brier={ho['persistence']['brier']:.3f}")
    print("K:", {a: v["K"] for a, v in summ["K"].items()})
    print(o)
