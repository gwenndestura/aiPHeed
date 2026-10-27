"""System validation (post-hoc; cannot change any adoption): does the served unified model forecast the combined
food-insecurity proxy T43c, or mainly food-price stress? Controlled ablations and component baselines on the identical
UNI-FINAL evaluation rows, Leads 1-3.

    python validate.py ablations   # out/validation_ablations.json
"""
from __future__ import annotations

import json
import sys

import l2_lib as X
import run_l2 as RL
import a2 as A2

U, C, FM, B, E, L, np, pd = X.U, X.C, X.FM, X.B, X.E, X.L, X.np, X.pd
OUT = X.OUT
MARKET = {"A1", "A2", "A3"}


def metrics(g: pd.DataFrame, p: np.ndarray, label: str = "y") -> dict:
    from sklearn.metrics import roc_auc_score, average_precision_score
    y = g[label].astype(int).to_numpy()
    p = np.clip(np.asarray(p, float), 0, 1)
    yh = (p >= 0.5).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    fn, tn = int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    prec = tp / (tp + fp) if tp + fp else None
    two = len(set(y.tolist())) == 2 and len(set(p.tolist())) > 1
    return {"rows": int(len(g)), "quarters": int(g["q"].nunique()), "high": int(y.sum()),
            "acc": float((yh == y).mean()), "bal": (rec + spec) / 2 if rec is not None and spec is not None else None,
            "precision": prec, "recall": rec,
            "f1": 2 * prec * rec / (prec + rec) if prec and rec else 0.0,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "auc": float(roc_auc_score(y, p)) if two else None,
            "pr_auc": float(average_precision_score(y, p)) if two else None,
            "brier": float(np.mean((p - y) ** 2))}


def refit(S: pd.DataFrame, keep: list[str]) -> pd.DataFrame:
    """P0 (the served UNI-FINAL price LightGBM: U2 grid, monotone, inner validation) refitted on a column subset."""
    fr = []
    for t in RL._origins():
        tr, te = U.train_rows(S, t), S[S["t"] == t]
        if not B.eligible(tr) or not len(te):
            continue
        cfg, _ = U.select(tr, keep, True)
        fr.append(te[["t", "lead", "province_code"]].assign(p=U.UniPrice(cfg, keep, True).fit(tr).predict(te)))
    return pd.concat(fr, ignore_index=True)


def phase_ablations():
    U.setup()
    K = RL._K()
    S = X.add_fe(U.stack(K))
    D = pd.read_csv(OUT / "predictions_addendum2.csv", dtype={"province_code": str})
    D = D[D["lead"] <= 3].copy()
    full = X.base_cols(True)
    fam = {c: X.FAMILY_OF[c] for c in full}
    sets = {"no_market_A1_A3": [c for c in full if fam[c] not in MARKET],
            "no_H1_feature": [c for c in full if fam[c] != "H1"],
            "no_market_no_H1": [c for c in full if fam[c] not in MARKET | {"H1"}]}
    for name, keep in sets.items():
        P = refit(S, keep).rename(columns={"p": f"{name}_price"})
        D = D.merge(P, on=["t", "lead", "province_code"], how="left")
        assert D[f"{name}_price"].notna().all(), name
        print("refit", name, len(keep), "columns", flush=True)
    # last complete quarter's price condition (known at O(t)) for the price-persistence baseline
    lab = C.labels()
    ps = B.ps_frame(E.data()[0]).set_index(["province_code", "q"])["y"]
    D["price_persist"] = [float(ps.get((p, t - 1), np.nan)) for p, t in zip(D["province_code"], D["t"])]
    D["hunger_latest"] = (D["h_last"] > X.H_LINE).astype(float)
    cands = {
        "full (UNI-FINAL: pi_H x pi_P, 12 families)": D["P0H0_p"],
        "no market A1-A3 (pi_H x pi_P')": D["H1"] * D["no_market_A1_A3_price"],
        "no H1 feature (pi_H x pi_P')": D["H1"] * D["no_H1_feature_price"],
        "no hunger at all (pi_P' only, H1 feature removed)": D["no_H1_feature_price"],
        "no market and no H1 feature (pi_H x pi_P')": D["H1"] * D["no_market_no_H1_price"],
        "no market, no hunger at all (pi_P'' only)": D["no_market_no_H1_price"],
        "price-only model output (pi_P, no hunger multiplier)": D["P0_price"],
        "price-only structural rule (A1-only STRUCT)": D["P5_price"],
        "price-only persistence (last complete quarter's price condition)": D["price_persist"].fillna(0),
        "hunger-only: pi_H": D["H1"],
        "hunger-only: latest SWS reading > 11.3": D["hunger_latest"],
        "always-LOW": np.zeros(len(D)),
        "PERSIST-SI (latest hunger AND latest price condition)": D["PERSIST-SI_p"],
    }
    out = {"rows_per_lead": {int(k): int(len(g)) for k, g in D.groupby("lead")}, "candidates": {}, "components": {}}
    for name, p in cands.items():
        D["_p"] = np.asarray(p, float)
        out["candidates"][name] = {int(k): metrics(g, g["_p"]) for k, g in D.groupby("lead")}
        m = out["candidates"][name]
        print(f"{name:60s} " + " | ".join(f"L{k} acc {m[k]['acc']:.3f} bal {m[k]['bal'] or 0:.3f} R {m[k]['recall'] or 0:.2f} "
                                          f"Brier {m[k]['brier']:.3f}" for k in (1, 2)), flush=True)
    for k, g in D.groupby("lead"):
        qd = g.groupby("q").first()
        out["components"][int(k)] = {
            "price_condition_pi_P": metrics(g, g["P0_price"], "price"),
            "price_condition_structural": metrics(g, g["P5_price"], "price"),
            "hunger_condition_pi_H_per_quarter": metrics(qd.reset_index(), qd["H1"].to_numpy(), "hunger"),
            "hunger_condition_latest_reading_per_quarter": metrics(qd.reset_index(), (qd["h_last"] > X.H_LINE).astype(float).to_numpy(), "hunger"),
            "share_of_rows_where_T43c_equals_price_condition": float((g["y"] == g["price"]).mean()),
            "share_of_quarters_with_hunger_condition_true": float(qd["hunger"].mean())}
        print("components lead", k, {a: (round(b["acc"], 3), round(b["auc"] or 0, 3)) for a, b in out["components"][int(k)].items()
                                     if isinstance(b, dict)},
              round(out["components"][int(k)]["share_of_rows_where_T43c_equals_price_condition"], 3), flush=True)
    # how much of the variation of the served probability comes from each factor (log P = log pi_H + log pi_P)
    for k, g in D.groupby("lead"):
        lh, lp = np.log(np.clip(g["H1"], 1e-6, 1)), np.log(np.clip(g["P0_price"], 1e-6, 1))
        v = np.var(lh + lp)
        out["components"][int(k)]["logP_variance_share"] = {"hunger": float((np.var(lh) + np.cov(lh, lp)[0, 1]) / v),
                                                            "price": float((np.var(lp) + np.cov(lh, lp)[0, 1]) / v)}
    FM.write_json(OUT / "validation_ablations.json", out)


if __name__ == "__main__":
    {"ablations": phase_ablations}[sys.argv[1]]()
