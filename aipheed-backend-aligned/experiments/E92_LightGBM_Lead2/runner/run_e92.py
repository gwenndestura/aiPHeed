"""E92 (PROTOCOL.md): LightGBM-only Lead-2 food-insecurity risk model on the E84/E91 rows. Run from backend/.

Every probability comes from a LightGBM model (or, where a LightGBM cannot be fitted yet, from that component's own
training-label frequency). No simulation probability is issued as a forecast.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
E92 = HERE.parent
EXP = E92.parent
sys.path.insert(0, str(EXP / "E91_Unified_Horizon_Model" / "runner"))
import run_e91 as U  # noqa: E402

E, L, np, pd, R9 = U.E, U.L, U.np, U.pd, U.R9
TH = U.TH
KS_TRAIN = (1, 2, 3)
LEADS = (2, 1, 3)                                         # Lead 2 primary; Leads 1 and 3 reported for the same model
PRICE_F = ["k", "F_rel", "G_rel", "mom3", "F_hat_rel", "G_hat_rel", "rice_yoy_now", "rice_mom3", "w_rice_chg3",
           "w_rice_chg6", "w_food_chg3", "w_food_chg6", "D_now", "rice_whsl_yoy", "tariff_yoy_regime",
           "import_suspension_share", "price_ceiling_share", "food_emergency_share"]
PRICE_S = ["compF_rel", "compG_rel"]                      # simulated mean projections, used as engineered features only
HUNGER_F = ["k", "H_rel", "H_chg", "H_age", "rice_yoy_now", "rice_mom3", "ur_yoy", "under_last", "remit_usd_yoy",
            "enso", "tc_count", "w_rice_chg6"]
STACK_F = ["k", "H_rel", "H_age", "F_rel", "G_rel", "F_hat_rel", "G_hat_rel", "compF_rel", "compG_rel", "rice_yoy_now",
           "rice_mom3", "w_rice_chg6", "ur_yoy", "remit_usd_yoy", "enso", "tc_count"]
MONO_UP = {"F_rel", "G_rel", "F_hat_rel", "G_hat_rel", "compF_rel", "compG_rel", "H_rel"}
GB = dict(objective="binary", num_leaves=4, max_depth=2, n_estimators=100, learning_rate=0.05, min_child_samples=5,
          reg_lambda=5.0, random_state=92, deterministic=True, n_jobs=1, force_row_wise=True, verbosity=-1)
SELECT_TO = "2024-Q4"
ARMS = ["M-LGB-DEC", "M-LGB-DEC-S", "M-LGB-STACK"]


def prep(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    fz, gz = X["province_code"].map(TH["food"]), X["province_code"].map(TH["gap"])
    X["F_rel"], X["G_rel"] = X["F_now"] - fz, X["gap_now"] - gz
    X["F_hat_rel"], X["G_hat_rel"] = X["F_hat_k"] - fz, X["G_hat_k"] - gz
    X["compF_rel"], X["compG_rel"] = X["comp_F_hat"] - fz, X["comp_G_hat"] - gz
    X["H_rel"] = X["H_last"] - TH["H"]
    return X


def lgbm(cols, tr, y, te, min_child=5):
    from lightgbm import LGBMClassifier
    A, B = tr[cols].astype(float), te[cols].astype(float)
    med = A.median()
    A, B = A.fillna(med).fillna(0.0), B.fillna(med).fillna(0.0)
    mono = [1 if c in MONO_UP else 0 for c in cols]
    m = LGBMClassifier(**dict(GB, min_child_samples=min_child), monotone_constraints=mono).fit(A, y)
    return m.predict_proba(B)[:, 1]


def freq(y) -> float:
    y = np.asarray(y)
    return float((y.sum() + 0.5) / (len(y) + 1))


def price_part(T, d, t, te, cols):
    """LightGBM P(price condition at the target) from pooled (X_k(t'), price label at t'+k), labels known at O(t)."""
    lab = R9.price_labels(d.cut(t))
    lab = lab[lab["q"] <= t - 1]
    tr = pd.concat([T[k][T[k]["t"] + k <= t - 1].assign(k=k, q=lambda f: f["t"] + f["k"]) for k in KS_TRAIN])
    tr = tr.merge(lab, on=["province_code", "q"])
    ok = tr["q"].nunique() >= 6 and tr["y_price"].sum() >= 5 and (1 - tr["y_price"]).sum() >= 5
    if not ok:
        return np.full(len(te), freq(tr["y_price"]) if len(tr) else 0.5), False
    return lgbm(cols, tr, tr["y_price"], te), True


def hunger_part(T, d, t, te_row):
    """LightGBM P(regional hunger > 11.3 at the target), one regional row per origin and horizon, posted before O(t)."""
    hq = L.h_quarters(d.cut(t)).set_index("q")["H"]
    rows = []
    for k in KS_TRAIN:
        R = T[k][T[k]["t"] + k <= t - 1]
        g = R.groupby("t")[HUNGER_F[1:]].mean().reset_index()
        for _, r in g.iterrows():
            q = int(r["t"]) + k
            if q in hq.index:
                rows.append({**r.to_dict(), "k": k, "y": int(hq[q] > TH["H"])})
    tr = pd.DataFrame(rows)
    if len(tr) < 8 or tr["y"].sum() < 2 or (1 - tr["y"]).sum() < 2:
        return freq(tr["y"]) if len(tr) else 0.5, False
    return float(lgbm(HUNGER_F, tr, tr["y"], te_row, min_child=3)[0]), True


def stack_part(T, d, t, te):
    """Direct LightGBM on pooled T43 labels (posted before O(t)), structural projections as engineered features."""
    tr = pd.concat([E.pairs(T[k], d, t, k).assign(k=k) for k in KS_TRAIN], ignore_index=True)
    if not U.eligible(tr):
        return None
    return lgbm(STACK_F, tr, tr["y"], te)


def run(d, Ps) -> dict:
    T = {k: prep(pd.read_csv(U.TABLES / f"features_k{k}.csv", dtype={"province_code": str})) for k in (1, 2, 3)}
    out = {}
    for k in LEADS:
        P = Ps[k].copy()
        for a in ARMS:
            P[a] = np.nan
        P["fit_price"], P["fit_hunger"], P["fit_stack"] = False, False, False
        for t in sorted(P["t"].unique()):
            m = P["t"] == t
            te = T[k][T[k]["t"] == t].set_index("province_code").loc[L.PROVS].reset_index().assign(k=k)
            te_row = te[HUNGER_F[1:]].mean().to_frame().T.assign(k=k)
            ph, fh = hunger_part(T, d, int(t), te_row)
            pp, fp = price_part(T, d, int(t), te, PRICE_F)
            pps, _ = price_part(T, d, int(t), te, PRICE_F + PRICE_S)
            dec, decs = ph * pp, ph * pps
            st = stack_part(T, d, int(t), te)
            P.loc[m, "M-LGB-DEC"], P.loc[m, "M-LGB-DEC-S"] = dec, decs
            P.loc[m, "M-LGB-STACK"] = st if st is not None else decs
            P.loc[m, "p_hunger_lgb"], P.loc[m, "p_price_lgb"], P.loc[m, "p_price_lgb_s"] = ph, pp, pps
            P.loc[m, "fit_price"], P.loc[m, "fit_hunger"], P.loc[m, "fit_stack"] = fp, fh, st is not None
        out[k] = P
    return out


if __name__ == "__main__":
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = E92 / "runs" / stamp
    o.mkdir(parents=True, exist_ok=True)
    d, _ = E.data()
    _, Ps = U.load_tables()
    Ps = {k: Ps[k] for k in (1, 2, 3)}
    E91_RUN = EXP / "E91_Unified_Horizon_Model" / "runs" / "20261022T045201Z"
    Pr = run(d, Ps)
    summ = {"stamp": stamp, "protocol_sha256": (E92 / "PROTOCOL.sha256").read_text().split()[0], "leads": {}}
    for k in LEADS:
        P = Pr[k]
        P91 = pd.read_csv(E91_RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
        P["HYB-GBA-SIM"] = pd.read_csv(EXP / "E89_Model_Optimization" / "runs" / "20261022T033435Z" / f"predictions_k{k}.csv",
                                       dtype={"province_code": str})["HYB-GBA-SIM"].to_numpy()
        P["U-GB"] = P91["U-GB"].to_numpy()
        P.to_csv(o / f"predictions_k{k}.csv", index=False)
        arms = ARMS + ["S-COV", "S-SIM", "HYB-GBA-SIM", "U-GB"]
        r, base = U.evaluate_k(P, arms)
        summ["leads"][k] = {"per_arm": r, "baselines": base,
                            "fitted_share": {c: float(P[c].mean()) for c in ("fit_price", "fit_hunger", "fit_stack")}}
    sel = {a: summ["leads"][2]["per_arm"][a]["selection_block_brier"] for a in ARMS}
    chosen = min(sel, key=sel.get)
    summ["selection_brier_lead2"], summ["selected"] = sel, chosen
    (o / "metrics.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8")
    print("selection (Lead-2 Brier, targets <= 2024-Q4):", {a: round(v, 4) for a, v in sel.items()}, "->", chosen)
    for k in LEADS:
        print(f"Lead {k}  fitted shares:", {c: round(v, 2) for c, v in summ["leads"][k]["fitted_share"].items()})
        for b in ("B-PERSIST", "B-CLIM", "B-AL"):
            m = summ["leads"][k]["baselines"][b]
            print(f"  {b:12s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} brier={m['brier']:.3f}")
        for a in ARMS + ["S-COV", "S-SIM", "HYB-GBA-SIM", "U-GB"]:
            rr = summ["leads"][k]["per_arm"][a]
            m, g, ps = rr["metrics"], rr["generalization"], rr["pass"]
            th = {b: round(v.get("p_holm", 1), 3) for b, v in rr["tests"].items()}
            print(f"  {a:12s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} P/R/F1={m['precision'] or 0:.2f}/"
                  f"{m['recall_HIGH'] or 0:.2f}/{m['f1']:.2f} TP/FP/FN/TN={m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} "
                  f"brier={m['brier']:.3f} PASS={ps['PASS']} {[c for c, v in ps.items() if not v and c not in ('PASS', 'TARGET_80')]} "
                  f"holm={th} W/L={g['wins']}/{g['losses']} early/late={g['early_acc']:.2f}/{g['late_acc']:.2f} {g['verdict']}",
                  flush=True)
    print(o)
