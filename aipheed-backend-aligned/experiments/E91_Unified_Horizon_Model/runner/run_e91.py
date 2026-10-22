"""E91 (PROTOCOL.md): one unified, horizon-conditioned food-insecurity risk model, evaluated at K = 1..4 on the E84 rows.

Run from backend/:
  python .../run_e91.py build      # build the K = 1..4 feature tables and baselines (no metrics printed)
  python .../run_e91.py score      # fit every unified candidate walk-forward and score it (after the protocol freeze)
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
E91 = HERE.parent
EXP = E91.parent
for p in ("E89_Model_Optimization", "E84_Objective_Continuation", "E83_Deep_Reconstruction"):
    sys.path.insert(0, str(EXP / p / "runner"))
import run_e83 as R  # noqa: E402  (chdir to backend/, loads app.news.events)
import e84_lib as C  # noqa: E402
import run_e89 as R9  # noqa: E402

E, L, np, pd = C.E, C.L, C.np, C.pd
EV = R.EV
KS = (1, 2, 3, 4)
E84_RUN = EXP / "E84_Objective_Continuation" / "runs" / "20261021T093234Z"
TABLES = E91 / "tables"
TH = L.e40_spec()
SAE = L.ROOT / "backend" / "data" / "reference" / "sae2021_calabarzon_municipal.csv"
POV_KNOWN_FROM = pd.Timestamp("2025-01-01")
SELECT_TO = "2024-Q4"                                      # selection block: targets 2023-Q1..2024-Q4
KDEP = ["F_hat_k", "G_hat_k", "tariff_yoy_regime", "import_suspension_share", "price_ceiling_share", "food_emergency_share",
        "sim_p", "sim_p_hunger", "sim_p_price", "seas_p", "seas_p_hunger", "seas_p_price", "comp_p", "comp_p_price",
        "comp_p_hunger", "comp_F_hat", "comp_G_hat", "comp_beta", "compnow_p", "compnow_p_price"]
BASELINES = R.BASELINES
GROUPS = {
    "prices": ["F_rel", "G_rel", "mom3", "F_hat_k", "G_hat_k", "D_now", "rice_whsl_yoy", "rice_yoy_now", "rice_mom3",
               "w_rice_chg6", "tariff_yoy_regime", "import_suspension_share", "price_ceiling_share", "food_emergency_share"],
    "climate": ["tc_count", "tc_max_signal", "tc_severe", "enso"],
    "supply": ["palay_yoy", "corn_yoy", "fish_yoy", "aqua_yoy"],
    "employment_remittances": ["ur_last", "ur_yoy", "under_last", "remit_usd_yoy", "fx_yoy"],
    "hunger_history": ["H_rel", "H_chg", "H_age"],
    "poverty": ["pov"],
}
NEWS = list(EV.N3_COLS)
GB_RES = dict(objective="binary", num_leaves=4, max_depth=2, n_estimators=60, learning_rate=0.05, min_child_samples=5,
              reg_lambda=5.0, random_state=91, deterministic=True, n_jobs=1, force_row_wise=True, verbosity=-1)
GB_RAW = dict(GB_RES, n_estimators=100)


def lg(p):
    p = np.clip(np.asarray(p, float), 1e-3, 1 - 1e-3)
    return np.log(p / (1 - p))


# ------------------------------------------------------------------------------------------------ tables
def pov_values() -> dict:
    """Province mean of the PSA 2021 municipal SAE poverty incidence (E54/E55 encoding), centred across provinces."""
    s = pd.read_csv(SAE, dtype={"lgu_code": str})
    s = s[s["poverty_incidence_2021"].notna()].assign(province_code=lambda f: f["province"].map(L.BY_NAME))
    assert s["province_code"].notna().all() and len(s) == 141
    v = s.groupby("province_code")["poverty_incidence_2021"].mean()
    return (v - v.mean()).to_dict()


def table(k: int, d, x, sub, W, w) -> pd.DataFrame:
    """Origin-time features for lead k at every origin 2021-Q2..2026-Q3. Leads 1-3: the E84 tables plus the E89 coverage
    fill (hunger walk from 3 posted rounds). Lead 4: the same k-independent columns, with every k-dependent column
    recomputed by the same E83/E84 functions."""
    origins = list(range(R.FIRST_ORIGIN, R.LAST_ORIGIN + 1))
    if k <= 3:
        X = pd.read_csv(E84_RUN / f"features_k{k}.csv", dtype={"province_code": str})
        return R9.coverage_fill(X, d, x, sub, W, w, k, origins)
    import e46_lib as P46
    events = P46.load_events()
    X = pd.read_csv(E84_RUN / "features_k1.csv", dtype={"province_code": str}).drop(columns=KDEP)
    rows = []
    for t in origins:
        c = d.cut(t)
        pol = E._policy_k(P46, events, t, k)
        s = E.simulate(c, t, k)
        fx = x["ofw"][x["ofw"]["q"] <= t - 1].drop_duplicates("q").set_index("q")["fx_usd_php_avg"]
        cp = C.simulate_comp(c, sub, W, C.world_cut(w, t), fx, t, k, passthrough=True, min_h=3)
        for p in L.PROVS:
            F, H = E.proj(c, t, k, p, "food"), E.proj(c, t, k, p, "all_items")
            v, cv = s.get(p, (np.nan, np.nan, np.nan)), cp.get(p, {})
            rows.append({"t": t, "province_code": p, "F_hat_k": F,
                         "G_hat_k": F - H if np.isfinite(F) and np.isfinite(H) else np.nan, **pol,
                         "sim_p": v[0], "sim_p_hunger": v[1], "sim_p_price": v[2],
                         "comp_p": cv.get("p", np.nan), "comp_p_price": cv.get("p_price", np.nan),
                         "comp_p_hunger": cv.get("p_hunger", np.nan), "comp_F_hat": cv.get("F_hat", np.nan),
                         "comp_G_hat": cv.get("G_hat", np.nan), "comp_beta": cv.get("beta", np.nan)})
    return X.merge(pd.DataFrame(rows), on=["t", "province_code"], how="left")


def lead_frame(k: int, X: pd.DataFrame, d, lab) -> pd.DataFrame:
    """Evaluation rows (targets 2023-Q1..2026-Q3) with the E83 baselines, computed exactly as run_e83.run_lead does."""
    rows = []
    for q in sorted(q for q in lab["q"].unique() if q >= E.EVAL_FROM):
        t = q - k
        te = X[X["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
        tr = E.pairs(X, d, t, k)
        av = E.available(d, t)
        last = av.sort_values("q").groupby("province_code").last()
        y = lab[lab["q"] == q].set_index("province_code")["y"]
        prev = float(av["y"].mean()) if len(av) else np.nan
        hq = L.h_quarters(d.cut(t)).sort_values("q")
        H_last = float(hq["H"].iloc[-1]) if len(hq) else np.nan
        out = pd.DataFrame({"k": k, "t": t, "origin": str(L.origin(t).date()), "target_q": L.qs(q),
                            "province_code": te["province_code"], "y": [int(y.get(p, -1)) for p in te["province_code"]]})
        out["B-PERSIST"] = [float(last["y"].get(p, np.nan)) for p in te["province_code"]]
        st = (H_last > TH["H"]) & ((te["F_now"] > te["province_code"].map(TH["food"])) |
                                   (te["gap_now"] > te["province_code"].map(TH["gap"])))
        out["B-STATE"] = st.astype(float).where(te["F_now"].notna()).to_numpy()
        out["B-MAJ"] = float(prev >= 0.5) if np.isfinite(prev) else np.nan
        out["B-CLIM"] = prev
        out["B-AH"], out["B-AL"] = 1.0, 0.0
        for name, cols in (("B-PSA", E.DRIVERS["D1_prices"]), ("B-NLP", EV.N3_COLS)):
            p = R.fit_predict("LR", cols, tr, te)
            out[name] = p if p is not None else np.nan
        out["S-SIM"] = te["sim_p"].to_numpy()
        out["S-COV"] = te["comp_p"].to_numpy()
        rows.append(out)
    P = pd.concat(rows, ignore_index=True)
    assert (P["y"] >= 0).all()
    return P


# ------------------------------------------------------------------------------------------------ unified design
def design(D: pd.DataFrame, pv: dict) -> pd.DataFrame:
    Z = D.copy()
    Z["k"] = D["k"].astype(float)
    Z["lh"], Z["lp"] = lg(D["comp_p_hunger"]), lg(D["comp_p_price"])
    Z["lh_k"], Z["lp_k"] = Z["lh"] * Z["k"], Z["lp"] * Z["k"]
    Z["l_comp"] = lg(D["comp_p"])
    Z["H_rel"] = D["H_last"] - TH["H"]
    Z["F_rel"] = D["F_now"] - D["province_code"].map(TH["food"])
    Z["G_rel"] = D["gap_now"] - D["province_code"].map(TH["gap"])
    Z["pov"] = D["province_code"].map(pv)
    Z.loc[D["t"].map(L.origin) < POV_KNOWN_FROM, "pov"] = np.nan          # as published (E54 POV-AS)
    Z["rice_pos"] = D["rice_yoy_now"].clip(lower=0)
    Z["rice_pos_k"] = Z["rice_pos"] * Z["k"]
    return Z


CAL = ["k", "lh", "lp", "lh_k", "lp_k"]
DRIVER_COLS = [c for g in GROUPS.values() for c in g]
SPECS = {
    # name: (kind, columns, uses structural init)
    "U-CAL": ("LR", CAL, False),
    "U-LR": ("LR", CAL + DRIVER_COLS, False),
    "U-LR-RICE": ("LR", CAL + ["rice_pos", "rice_pos_k", "H_rel"], False),
    "U-GB": ("GB", ["k", "lh", "lp"] + DRIVER_COLS, True),
    "U-GB-RAW": ("GB", ["k"] + DRIVER_COLS, False),
}
SELECTABLE = ["U-STRUCT", "U-CAL", "U-LR", "U-GB", "U-GB-RAW"]       # U-LR-RICE is selection-informed (E90 diagnostic)


def pooled_pairs(T: dict, d, t: int) -> pd.DataFrame:
    """Training pairs (X_k(t'), y(t'+k)) for every k in KS whose label was complete and posted before O(t)."""
    return pd.concat([E.pairs(T[k], d, t, k).assign(k=k) for k in KS], ignore_index=True)


def eligible(tr: pd.DataFrame) -> bool:
    return tr["q"].nunique() >= 6 and tr["y"].sum() >= 5 and tr["y"].nunique() == 2


def fit_predict(kind, cols, init, tr, te):
    A, B = tr[cols].astype(float), te[cols].astype(float)
    med = A.median()
    A, B = A.fillna(med).fillna(0.0), B.fillna(med).fillna(0.0)
    if kind == "LR":
        from sklearn.linear_model import LogisticRegression
        mu, sd = A.mean(), A.std(ddof=0).replace(0, 1)
        m = LogisticRegression(C=0.5, max_iter=5000).fit((A - mu) / sd, tr["y"])
        return m.predict_proba((B - mu) / sd)[:, 1]
    from lightgbm import LGBMClassifier
    if init:
        m = LGBMClassifier(**GB_RES).fit(A, tr["y"], init_score=tr["l_comp"].to_numpy())
        return 1 / (1 + np.exp(-(m.predict_proba(B, raw_score=True) + te["l_comp"].to_numpy())))
    p = tr["y"].mean()
    m = LGBMClassifier(**GB_RAW, scale_pos_weight=(1 - p) / p).fit(A, tr["y"])
    return m.predict_proba(B)[:, 1]


def unified(T: dict, Ps: dict, d, pv, specs: dict) -> dict:
    """One model per origin t, trained on pooled multi-horizon pairs, predicting every horizon issued from t."""
    out = {k: Ps[k].copy() for k in KS}
    for k in KS:
        out[k]["U-STRUCT"] = out[k]["S-COV"]
        for n in specs:
            out[k][n], out[k][n + "_fitted"] = np.nan, False
    origins = sorted({int(t) for k in KS for t in Ps[k]["t"]})
    for t in origins:
        tr_all = design(pooled_pairs(T, d, t), pv)
        for k in KS:
            m = out[k]["t"] == t
            if not m.any():
                continue
            te = design(T[k][T[k]["t"] == t].set_index("province_code").loc[L.PROVS].reset_index().assign(k=k), pv)
            for n, (kind, cols, init) in specs.items():
                struct = init or any(c in cols for c in ("lh", "lp", "lh_k", "lp_k"))
                # arms built on the structural core train only on rows where it exists and issue only where it exists
                tr = tr_all[tr_all["comp_p"].notna()] if struct else tr_all
                if struct and te["comp_p"].isna().any():
                    continue                                                 # unissued (counts as wrong)
                if eligible(tr):
                    out[k].loc[m, n] = fit_predict(kind, cols, init, tr, te)
                    out[k].loc[m, n + "_fitted"] = True
                else:
                    out[k].loc[m, n] = te["comp_p"].to_numpy()             # fallback: the structural core
    return out


# ------------------------------------------------------------------------------------------------ evaluation
def quarter_table(P, arm):
    yh = (P[arm] >= 0.5).astype(int)
    D = P.assign(c=(yh == P["y"]).astype(int), r=((P["B-PERSIST"] >= 0.5).astype(int) == P["y"]).astype(int),
                 tp=((yh == 1) & (P["y"] == 1)).astype(int))
    g = D.groupby("target_q").agg(correct=("c", "sum"), persist=("r", "sum"), high=("y", "sum"), caught=("tp", "sum"))
    return g


def calib_bins(P, arm, edges=(0, 0.2, 0.4, 0.6, 0.8, 1.0001)):
    b = pd.cut(P[arm], edges, right=False)
    g = P.groupby(b, observed=True).agg(n=("y", "size"), mean_p=(arm, "mean"), obs=("y", "mean"))
    return [{"bin": str(i), "n": int(r.n), "mean_p": float(r.mean_p), "observed": float(r.obs)} for i, r in g.iterrows()]


def evaluate_k(P, arms):
    # an arm that issues no row at this horizon (structural core at K = 4) is recorded as unissued, all rows wrong (D3)
    none = [a for a in arms if P[a].notna().sum() == 0]
    arms = [a for a in arms if a not in none]
    out, base = _evaluate_k(P.drop(columns=none), arms)
    for a in none:
        m = R.score(P, a)
        out[a] = {"metrics": m, "pass": {"acc_gt_75": False, "bal_beats_baselines": False, "brier_beats_sig": False,
                                         "recall_ge_50": False, "PASS": False, "TARGET_80": False},
                  "generalization": R9.quarter_generalization(P, a), "tests": {}, "issued": 0,
                  "not_issued_reason": "structural core not computable at this horizon"}
    return out, base


def _evaluate_k(P, arms):
    # run_e83.evaluate scores columns by prefix; give the U- arms a recognised prefix and map the results back (D2)
    ren = {a: "HYB-" + a for a in arms if a.startswith("U-")}
    R.PRIMARY[:] = [ren.get(a, a) for a in arms]
    res, tests = R.evaluate(P.rename(columns=ren))
    back = {v: k for k, v in ren.items()}
    res = {back.get(a, a): v for a, v in res.items()}
    tests = {" vs ".join(back.get(s, s) for s in n.split(" vs ")): v for n, v in tests.items()}
    out = {}
    for a in arms:
        m = res[a]["all_rows_unissued_wrong"]
        gen = R9.quarter_generalization(P, a)
        q = quarter_table(P, a)
        prov = {L.NAMES[p]: {"accuracy": float(((g[a] >= 0.5).astype(int) == g["y"]).mean()), "high": int(g["y"].sum()),
                             "caught": int(((g[a] >= 0.5) & (g["y"] == 1)).sum())} for p, g in P.groupby("province_code")}
        sel = P["target_q"] <= SELECT_TO
        missed = P[(P[a] < 0.5) & (P["y"] == 1)][["target_q", "province_code"]].assign(
            province=lambda f: f["province_code"].map(L.NAMES))[["target_q", "province"]].values.tolist()
        out[a] = {"metrics": m, "pass": R.passes(res, tests, a), "generalization": gen,
                  "tests": {b: tests[f"{a} vs {b}"] for b in ("B-PERSIST", "B-CLIM", "B-AH") if f"{a} vs {b}" in tests},
                  "selection_block_brier": float(((P.loc[sel, a] - P.loc[sel, "y"]) ** 2).mean()),
                  "confirmation_block": E.metrics(P.loc[~sel, "y"], (P.loc[~sel, a] >= 0.5).astype(int), P.loc[~sel, a]),
                  "quarter_accuracy_sd": float((q["correct"] / 5).std(ddof=1)),
                  "per_quarter": q.astype(int).to_dict(orient="index"), "by_province": prov,
                  "province_accuracy_sd": float(np.std([v["accuracy"] for v in prov.values()], ddof=1)),
                  "calibration": calib_bins(P, a), "missed_high": missed,
                  "fitted_share": float(P[a + "_fitted"].mean()) if a + "_fitted" in P else None}
    base = {b: res[b]["all_rows_unissued_wrong"] for b in BASELINES if b in res}
    return out, base


def k_validated(per_k: dict, arm: str) -> dict:
    """PROTOCOL section 5: the largest K with PASS (E83 rule, unchanged) and the temporal-generalization requirement at
    every horizon 1..K; also the E83 reading (every lead from 2 to K)."""
    ok = {k: per_k[k][arm]["pass"]["PASS"] and per_k[k][arm]["generalization"]["criteria"]["b"] and
          per_k[k][arm]["generalization"]["majority_quarters"] >= 0.6 for k in KS}
    K = 0
    for k in KS:
        if not ok[k]:
            break
        K = k
    K83 = 0
    for k in KS[1:]:
        if not per_k[k][arm]["pass"]["PASS"]:
            break
        K83 = k
    return {"per_k_ok": ok, "K": K, "K_e83_reading": K83}


def ablation(T, Ps, d, pv, base_name):
    """Drop one driver group (or add news) from a fitted unified learner; change in mean Brier / accuracy over K."""
    kind, cols, init = SPECS[base_name]
    specs = {}
    for g, gc in GROUPS.items():
        specs[f"{base_name}-DROP-{g}"] = (kind, [c for c in cols if c not in gc], init)
    specs[f"{base_name}+news"] = (kind, cols + NEWS, init)
    U = unified(T, Ps, d, pv, specs)
    out = {}
    for n in specs:
        b = [float(((U[k][n] - U[k]["y"]) ** 2).mean()) for k in KS]
        a = [float(((U[k][n] >= 0.5).astype(int) == U[k]["y"]).mean()) for k in KS]
        out[n] = {"brier_by_k": b, "accuracy_by_k": a}
    return out


def load_tables():
    T = {k: pd.read_csv(TABLES / f"features_k{k}.csv", dtype={"province_code": str}) for k in KS}
    Ps = {k: pd.read_csv(TABLES / f"baselines_k{k}.csv", dtype={"province_code": str}) for k in KS}
    return T, Ps


if __name__ == "__main__":
    mode = sys.argv[1]
    d, x = E.data()
    lab = E.labels_all(d)
    if mode == "build":
        sub, W = C.load_sub()
        w = C.load_world()
        TABLES.mkdir(exist_ok=True)
        for k in KS:
            X = table(k, d, x, sub, W, w)
            P = lead_frame(k, X, d, lab)
            if k <= 3:                                     # reproducibility: identical baselines and S-SIM to E84
                P84 = pd.read_csv(E84_RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
                for c in BASELINES + ["S-SIM", "y"]:
                    a, b = P[c].to_numpy(float), P84[c].to_numpy(float)
                    assert np.allclose(a, b, equal_nan=True), (k, c)
            X.to_csv(TABLES / f"features_k{k}.csv", index=False)
            P.to_csv(TABLES / f"baselines_k{k}.csv", index=False)
            print(f"k={k} rows={len(P)} targets={P['target_q'].min()}..{P['target_q'].max()} "
                  f"S-COV issued={int(P['S-COV'].notna().sum())} S-SIM issued={int(P['S-SIM'].notna().sum())}", flush=True)
        sys.exit(0)

    assert mode == "score"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = E91 / "runs" / stamp
    o.mkdir(parents=True, exist_ok=True)
    pv = pov_values()
    T, Ps = load_tables()
    U = unified(T, Ps, d, pv, SPECS)
    arms = ["U-STRUCT"] + list(SPECS) + ["S-SIM", "S-COV"]
    per_k, base = {}, {}
    for k in KS:
        U[k].to_csv(o / f"predictions_k{k}.csv", index=False)
        per_k[k], base[k] = evaluate_k(U[k], arms)
    # D3: selection averages the horizons that every selectable candidate issues (the core cannot issue K = 4)
    KSEL = [k for k in KS if all("selection_block_brier" in per_k[k][a] for a in SELECTABLE)]
    sel = {a: float(np.mean([per_k[k][a]["selection_block_brier"] for k in KSEL])) for a in SELECTABLE}
    chosen = min(sel, key=sel.get)
    summ = {"stamp": stamp, "protocol_sha256": (E91 / "PROTOCOL.sha256").read_text().split()[0],
            "selection_horizons": KSEL, "selection_mean_brier": sel, "selected": chosen,
            "K": {a: k_validated(per_k, a) for a in arms}, "per_k": per_k, "baselines": base}
    learned = chosen if chosen in SPECS else "U-LR"
    summ["ablation_on"] = learned
    summ["ablation"] = ablation(T, Ps, d, pv, learned)
    if learned != "U-GB":
        summ["ablation_gb"] = ablation(T, Ps, d, pv, "U-GB")
    (o / "metrics.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8")
    print("selection (mean Brier, targets <= 2024-Q4):", {a: round(v, 4) for a, v in sel.items()}, "->", chosen)
    for k in KS:
        print(f"k={k}")
        for b in ("B-PERSIST", "B-CLIM", "B-AL", "B-PSA"):
            m = base[k][b]
            print(f"  {b:10s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} brier={m.get('brier', float('nan')):.3f}")
        for a in arms:
            r = per_k[k][a]
            m, g, ps = r["metrics"], r["generalization"], r["pass"]
            th = {b: round(v.get("p_holm", 1), 3) for b, v in r["tests"].items()}
            print(f"  {a:10s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} P/R/F1={m['precision'] or 0:.2f}/"
                  f"{m['recall_HIGH'] or 0:.2f}/{m['f1']:.2f} TP/FP/FN/TN={m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} "
                  f"brier={m['brier']:.3f} PASS={ps['PASS']} {[c for c, v in ps.items() if not v and c not in ('PASS', 'TARGET_80')]} "
                  f"holm={th} W/L={g['wins']}/{g['losses']} early/late={g['early_acc']:.2f}/{g['late_acc']:.2f} "
                  f"fitted={r.get('fitted_share')} issued={int(U[k][a].notna().sum())}", flush=True)
    print("K:", {a: (v["K"], v["K_e83_reading"]) for a, v in summ["K"].items()})
    print("ablation", learned, {n: [round(x, 4) for x in v["brier_by_k"]] for n, v in summ["ablation"].items()})
    print(o)
