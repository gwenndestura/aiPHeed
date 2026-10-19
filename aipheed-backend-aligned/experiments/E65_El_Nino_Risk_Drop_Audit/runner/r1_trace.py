"""E65 r1 (PROTOCOL section 2): province-by-province trace of the E56/E58 forecasts for 2026-Q3 (back-test, issued
2026-04-01), 2026-Q4 (issued 2026-07-01) and 2027-Q1 (issued 2026-10-01), from inputs to the served value, with
  (1) the across-origin decomposition of each change (each origin's own model), and
  (2) the fixed-model decomposition: exact Shapley values over input blocks with the LATER origin's model held fixed
      (input effect), the remainder being the model/configuration change (model effect).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E65_El_Nino_Risk_Drop_Audit/runner/r1_trace.py
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e65_lib as H  # noqa: E402

L, P2, F, G, np, pd = H.L, H.P2, H.F, H.G, H.np, H.pd
from scipy.stats import norm  # noqa: E402

ORIG = {"2026-Q3": L.qi("2026-Q1"), "2026-Q4": L.qi("2026-Q2"), "2027-Q1": L.qi("2026-Q3")}
POLICY = list(H.F.M.POLICY)
BLOCKS = {   # input blocks for the fixed-model Shapley decomposition (every model input belongs to exactly one)
    "cpi_market": P2.PRICE_GROUPS["market"] + [f"base_{m}" for m in P2.MULTS] + [f"gbase_{m}" for m in P2.MULTS]
                  + ["news_market"],
    "climate": P2.PRICE_GROUPS["climate"] + ["news_climate"],
    "fish_kill": P2.PRICE_GROUPS["fish_kill"] + ["news_fish_kill"],
    "employment": P2.PRICE_GROUPS["employment"] + ["news_employment"],
    "ofw_fx": P2.PRICE_GROUPS["ofw_remittance"] + ["news_ofw_remittance"],
    "news_volume": ["news_n"],
    "policy": POLICY,
    "poverty": ["pov"],
    "hunger_base": ["H_base"],
}
E62_CHRON = H.EXP / "E62_Final_System_Audit" / "tables" / "r3_chronology_by_province.csv"


def block_of(col: str) -> str:
    for b, cs in BLOCKS.items():
        if col in cs:
            return b
    if col.endswith("__missing"):
        return block_of(col[:-9])
    return "other"


def origin_parts(d, X, B, t, space):
    fx = G.tuned_forecast(d, X, B, t, space)
    hcols = [c for g in P2.ALL_GROUPS if g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]
    _, hte = P2.hunger_frame(X, P2.h_series(d, t, False), t, hcols)
    fx["hte"] = hte.reset_index(drop=True)
    return fx


def hunger_terms(hc, hte):
    """Ridge terms of the hunger part on the standardized design (coef x z), the intercept and H_hat."""
    m = hc["model"]
    Z = hte[m.cols].astype(float)
    D = m._design(Z)
    zz = ((D - m.mu) / m.sd)[m.keep]
    coef = m.m.coef_
    terms = {c: float(coef[i] * zz.iloc[0][c]) for i, c in enumerate(m.keep)}
    return terms, float(m.m.intercept_), float(hte["H_base"].iloc[0]), {c: float(Z.iloc[0][c]) for c in m.cols}


def p_hunger(hc, hte) -> float:
    h = float(hte["H_base"].iloc[0] + hc["model"].predict(hte)[0])
    return float(1 - norm.cdf((L.e40_spec()["H"] - h) / max(hc["rmse"], 1e-6)))


def logP(fx, te_row: pd.DataFrame, hte_row: pd.DataFrame) -> float:
    pp = float(fx["model"].predict(te_row)[0])
    ph = p_hunger(fx["hc"], hte_row)
    return math.log(max(pp, 1e-300)) + math.log(max(ph, 1e-300))


def hybrid(later: pd.DataFrame, earlier: pd.DataFrame, take: set, cols_of) -> pd.DataFrame:
    h = earlier.copy()
    for b in take:
        for c in cols_of(b):
            if c in later.columns:
                h[c] = later[c].values
    return h


def shapley(fx_late, te_late, te_early, hte_late, hte_early):
    """Exact Shapley over BLOCKS of v(S) = log P under the later model, blocks in S at their later values."""
    names = list(BLOCKS)
    n = len(names)
    cache = {}

    def v(S):
        k = frozenset(S)
        if k not in cache:
            te = hybrid(te_late, te_early, k, lambda b: BLOCKS[b])
            hte = hybrid(hte_late, hte_early, k, lambda b: [c for c in hte_late.columns if block_of(c) == b])
            cache[k] = logP(fx_late, te, hte)
        return cache[k]
    phi = {}
    for b in names:
        others = [x for x in names if x != b]
        s = 0.0
        for r in range(n):
            for S in itertools.combinations(others, r):
                w = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
                s += w * (v(set(S) | {b}) - v(set(S)))
        phi[b] = s
    return phi, v(set()), v(set(names))


def main():
    H.verify_protocol()
    d, X, B = H.E.load()
    space = G.search_space()
    rec = json.loads(H.E58_RECORD.read_text())
    parts = {k: origin_parts(d, X, B, t, space) for k, t in ORIG.items()}
    rows, decomp, shap_rows, hunger_rows = [], [], [], []
    for k, fx in parts.items():
        te = fx["te"].reset_index(drop=True)
        contrib = fx["model"].contributions(te)
        init = F.struct_logit(te, fx["cfg"]["m"], fx["model"].scale)
        hterms, hint, hbase, hvals = hunger_terms(fx["hc"], fx["hte"])
        for c, v in hterms.items():
            base = c.replace("__missing", "")
            val = hvals.get(base, np.nan)
            if c.endswith("__missing"):
                val = float(pd.isna(val))                      # the indicator's own value (1 = missing at this origin)
            hunger_rows.append({"target": k, "feature": c, "block": block_of(c), "value": val, "H_points": v})
        for i, p in enumerate(L.PROVS):
            pr = rec["provinces"][p]
            served = (pr["forecast"]["probability"] if k == "2027-Q1" else
                      next(e["probability"] for e in pr["earlierForecasts"] if e["targetQuarter"] == k) if k == "2026-Q4"
                      else next(e["probability"] for e in pr["pastForecasts"] if e["targetQuarter"] == k))
            sh = contrib.iloc[i]
            g = {}
            for c, v in sh.items():
                if c == "tree_bias":
                    continue
                g[block_of(c)] = g.get(block_of(c), 0.0) + float(v)
            rows.append({"target": k, "issue_date": str(L.origin(ORIG[k]).date()), "province": L.NAMES[p],
                         "province_code": p, "config": int(fx["cfg"]["id"]), "drift_m": fx["cfg"]["m"],
                         "trees": fx["cfg"]["trees"], "depth": fx["cfg"]["depth"],
                         "P": float(fx["p"][i]), "P_served_record": served, "P_hunger": float(fx["p_hunger"]),
                         "P_price": float(fx["p_price"][i]), "H_base_latest_sws": hbase, "H_hat": float(fx["H_hat"]),
                         "hunger_rmse": float(fx["hc"]["rmse"]),
                         "F_now": float(te.loc[i, "F_now"]), "gap_now": float(te.loc[i, "gap_now"]),
                         "food_projection": float(te.loc[i, f"base_{fx['cfg']['m']}"]),
                         "gap_projection": float(te.loc[i, f"gbase_{fx['cfg']['m']}"]),
                         "threshold_food": L.e40_spec()["food"][p], "threshold_gap": L.e40_spec()["gap"][p],
                         "offset_logit_cpi_projection": float(init[i]), "tree_bias": float(sh["tree_bias"]),
                         **{f"trees_{b}": round(v, 6) for b, v in g.items()},
                         "logit_P_price": float(init[i] + sh.sum()),
                         "enso": float(te.loc[i, "enso"]), "enso_l2": float(te.loc[i, "enso_l2"]),
                         "tc_count": float(te.loc[i, "tc_count"]), "palay_yoy": float(te.loc[i, "palay_yoy"]),
                         "corn_yoy": float(te.loc[i, "corn_yoy"]), "news_climate": float(te.loc[i, "news_climate"])})
            for c, v in sh.items():
                if abs(v) > 1e-12:
                    shap_rows.append({"target": k, "province": L.NAMES[p], "feature": c, "block": block_of(c),
                                      "logit_contribution": float(v), "value": float(te.loc[i, c]) if c in te else np.nan})
    T = pd.DataFrame(rows)
    T["abs_err_vs_record"] = (T["P"] - T["P_served_record"]).abs()
    assert T["abs_err_vs_record"].max() < 1e-3, T[["target", "province", "P", "P_served_record"]]
    # across-origin and fixed-model decomposition of each change
    for a, b in (("2026-Q3", "2026-Q4"), ("2026-Q4", "2027-Q1"), ("2026-Q3", "2027-Q1")):
        fa, fb = parts[a], parts[b]
        tea, teb = fa["te"].reset_index(drop=True), fb["te"].reset_index(drop=True)
        for i, p in enumerate(L.PROVS):
            ra, rb = T[(T.target == a) & (T.province_code == p)].iloc[0], T[(T.target == b) & (T.province_code == p)].iloc[0]
            phi, v0, v1 = shapley(fb, teb.iloc[[i]], tea.iloc[[i]], fb["hte"], fa["hte"])
            total = math.log(rb.P) - math.log(ra.P)
            input_effect = v1 - v0
            model_effect = v0 - math.log(ra.P)          # later model on earlier inputs, minus earlier model on them
            row = {"from": a, "to": b, "province": L.NAMES[p], "P_from": ra.P, "P_to": rb.P, "dP": rb.P - ra.P,
                   "dlogP_total": total, "dlogP_hunger": math.log(rb.P_hunger) - math.log(ra.P_hunger),
                   "dlogP_price": math.log(rb.P_price) - math.log(ra.P_price),
                   "dlogit_price": rb.logit_P_price - ra.logit_P_price,
                   "d_offset_cpi_projection": rb.offset_logit_cpi_projection - ra.offset_logit_cpi_projection,
                   "d_tree_bias": rb.tree_bias - ra.tree_bias,
                   **{f"d_trees_{g}": rb.get(f"trees_{g}", 0) - ra.get(f"trees_{g}", 0) if pd.notna(rb.get(f"trees_{g}", 0)) else np.nan
                      for g in BLOCKS if g not in ("hunger_base",)},
                   "config_from": int(ra.config), "config_to": int(rb.config),
                   "fixed_model_input_effect_dlogP": input_effect, "model_change_effect_dlogP": model_effect,
                   "P_later_model_on_earlier_inputs": math.exp(v0),
                   **{f"shapley_dlogP_{bk}": phi[bk] for bk in BLOCKS},
                   "shapley_sum_check": sum(phi.values()) - input_effect}
            decomp.append(row)
    D = pd.DataFrame(decomp).fillna(0.0)
    assert D["shapley_sum_check"].abs().max() < 1e-9
    assert (D["dlogP_total"] - D["fixed_model_input_effect_dlogP"] - D["model_change_effect_dlogP"]).abs().max() < 1e-9
    # E62 independent raw-input columns for the same rows
    C62 = pd.read_csv(E62_CHRON)
    C62 = C62[C62["target"].isin(ORIG)][["province", "target", "cpi_through", "food_yoy_latest", "headline_yoy_latest",
                                         "gap_latest", "observed_T43", "observed_food_yoy", "observed_headline_yoy",
                                         "observed_hunger", "sws_latest_posted_H", "sws_latest_posted_quarter",
                                         "sws_latest_posted_on", "rice_wholesale_yoy_prevq", "unemployment_change_pts",
                                         "remittance_input_missing", "news_articles_q", "news_climate_share"]]
    T = T.merge(C62, on=["province", "target"], how="left")
    H.write_csv(T, H.TABLES / "r1_trace_by_province.csv")
    H.write_csv(D, H.TABLES / "r1_change_decomposition.csv")
    H.write_csv(pd.DataFrame(shap_rows), H.TABLES / "r1_price_treeshap_by_feature.csv")
    H.write_csv(pd.DataFrame(hunger_rows), H.TABLES / "r1_hunger_ridge_terms.csv")
    split_use = {}
    for k, fx in parts.items():
        bst = fx["model"].model.booster_
        split_use[k] = {"config": int(fx["cfg"]["id"]), "cfg": fx["cfg"],
                        "price_splits": {f: int(s) for f, s in zip(bst.feature_name(), bst.feature_importance("split")) if s},
                        "hunger_alpha": fx["hc"]["alpha"], "hunger_rmse": fx["hc"]["rmse"]}
    H.dump({"protocol_sha256": H.verify_protocol(), "max_abs_err_vs_served_record": float(T["abs_err_vs_record"].max()),
            "split_use": split_use}, H.OUT / "r1_trace.json")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    print(T[["target", "province", "config", "P", "P_served_record", "P_hunger", "P_price", "F_now", "gap_now",
             "food_projection", "gap_projection", "threshold_food", "threshold_gap", "offset_logit_cpi_projection",
             "tree_bias"] + [c for c in T.columns if c.startswith("trees_")]].round(3).to_string(index=False))
    print(D[["from", "to", "province", "P_from", "P_to", "dlogP_total", "dlogP_hunger", "dlogP_price",
             "fixed_model_input_effect_dlogP", "model_change_effect_dlogP"]
            + [c for c in D.columns if c.startswith("shapley_dlogP_")]].round(3).to_string(index=False))
    print(json.dumps(split_use, default=str)[:3000])


if __name__ == "__main__":
    main()
