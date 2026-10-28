"""LEAD2_OBJECTIVES_AUDIT: does Lead 2 meet the thesis objectives? (diagnostic only: nothing is trained to pass, selected,
adopted or served; the frozen 0.50 cut, R1-R7 and final.adoption_rule are unchanged)

1. reproduction: P0H4-U (B0) and CR price parts refitted from the committed stack against the committed evaluation
   rows; the served export's retrospective rows (Lead 1 only; its Lead-2 rows are the live forecast) against P0H4;
2. independent metrics (sklearn) on identical Lead-2 rows: accuracy, balanced accuracy, precision, recall, F1, confusion
   matrix, Brier, calibration (reliability bins, calibration-in-the-large, logistic slope), by province and by year;
3. every scored Lead-2 candidate from the committed result files, with its failed criteria and adoption status;
4. overfitting: in-sample vs out-of-sample price-part Brier and AUC at every origin (B0);
5. missing indicators: each trigger group blanked in the Lead-2 test rows only, models fixed (B0);
6. target validity: what part of the T43c label varies by province, and from which component.

    python lead2_objectives_audit.py   # ../out/lead2_objectives_audit.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, brier_score_loss, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)

import final as FN  # noqa: F401  (sys.path order as in cpi_refresh.py)
import lt_lib as T

F, KEY = T.F, T.KEY
ROOT = T.EXP.parents[1]
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
CPI = ["A1_food", "A1_gap", "A_mom"]


def metrics(y, p) -> dict:
    y, p = np.asarray(y, int), np.asarray(p, float)
    c = (p >= .5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, c, labels=[0, 1]).ravel()
    lp = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
    slope = float(LogisticRegression(C=1e6).fit(lp.reshape(-1, 1), y).coef_[0, 0]) if len(set(y)) == 2 else float("nan")
    bins = [0, .1, .3, .5, .7, 1.0001]
    rel = []
    for a, b in zip(bins[:-1], bins[1:]):
        m = (p >= a) & (p < b)
        if m.any():
            rel.append({"bin": f"{a:.1f}-{min(b, 1):.1f}", "n": int(m.sum()), "mean_p": float(p[m].mean()), "obs_rate": float(y[m].mean())})
    ece = sum(r["n"] * abs(r["mean_p"] - r["obs_rate"]) for r in rel) / len(y)
    return {"n": int(len(y)), "accuracy": accuracy_score(y, c), "balanced_accuracy": balanced_accuracy_score(y, c),
            "precision": precision_score(y, c, zero_division=0), "recall_high": recall_score(y, c, zero_division=0),
            "recall_low": recall_score(1 - y, 1 - c, zero_division=0), "f1_high": f1_score(y, c, zero_division=0),
            "tp_fp_fn_tn": [int(tp), int(fp), int(fn), int(tn)], "brier": brier_score_loss(y, p),
            "auc": roc_auc_score(y, p) if len(set(y)) == 2 else float("nan"),
            "calibration_in_the_large": float(p.mean() - y.mean()), "calibration_slope": slope, "ece": float(ece),
            "reliability": rel}


def by(g, col, key) -> dict:
    out = {}
    for k, h in g.groupby(key):
        c = (h[col] >= .5).astype(int)
        out[str(k)] = {"n": int(len(h)), "high": int(h["y"].sum()), "accuracy": float((c == h["y"]).mean()),
                       "false_negatives": int(((c == 0) & (h["y"] == 1)).sum()),
                       "false_positives": int(((c == 1) & (h["y"] == 0)).sum()),
                       "brier": float(((h[col] - h["y"]) ** 2).mean())}
    return out


def candidates() -> list[dict]:
    """Every Lead-2 candidate scored on these rows, from the committed result files."""
    files = {"improve.json": "LEAD2_IMPROVE", "final.json": "LEAD2_FINAL", "subgroup_k2.json": "LEAD2_SUBGROUP",
             "tune.json": "LEAD2_TUNING", "cpi_refresh.json": "LEAD2_CPI_REFRESH"}
    out, seen = [], set()
    for f, exp in files.items():
        d = json.loads((T.OUT / f).read_text())
        adopted = (d.get("adoption") or {}).get("adopted")
        for c, v in d["cands"].items():
            L = (v.get("leads") or v).get("2") if isinstance(v, dict) else None
            if not isinstance(L, dict) or "metrics" not in L:
                continue
            m = L["metrics"]
            key = (c, round(float(m["brier"]), 6))
            if key in seen:
                continue
            seen.add(key)
            out.append({"experiment": exp, "candidate": c, "accuracy": m["accuracy"], "balanced_accuracy": m["balanced_accuracy"],
                        "precision": m["precision"], "recall": m["recall"], "brier": m["brier"],
                        "tp_fp_fn_tn": [int(m[x]) for x in ("tp", "fp", "fn", "tn")], "failed": L.get("failed"),
                        "later_accuracy": (L.get("conf") or {}).get("accuracy"),
                        "adopted": None if c in ("B0", "P0H4") else bool(adopted) and c == (d.get("adoption") or {}).get("FINAL")})
    return out


def main():
    E = pd.read_csv(T.OUT / "cpi_refresh_rows.csv", dtype={"province_code": str})
    assert ((E["hunger"] * E["price"]) == E["y"]).all()                     # T43c = hunger AND price
    S = T.stack()
    out = {}

    # 1. reproduction
    origins = sorted(E["t"].unique())
    models = {}
    B = T.run(T.U2, origins, S=S, models=models)
    R = pd.read_csv(T.DATA / "cpi_refresh.csv", dtype={"province_code": str})
    S2 = S.merge(R[KEY + ["m0r"] + [f"{c}_r" for c in CPI]], on=KEY, how="left")
    hit = S2["m0r"].notna()
    for c in CPI:
        S2.loc[hit, c] = S2.loc[hit, f"{c}_r"]
    C = T.run(T.U2, origins, S=S2)
    chk = E[KEY + ["B0_price", "CR_price"]].merge(B[KEY + ["pi_P"]], on=KEY).merge(C[KEY + ["pi_P"]], on=KEY, suffixes=("_b", "_c"))
    srv = pd.read_csv(ROOT / "backend" / "data" / "ch1_engine" / "rows.csv", dtype={"province_code": str})
    s2 = srv[(srv["lead"] == 1) & (srv["issue_date"] < "2026-10-01")].copy()
    s2["q"] = s2["quarter"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    sv = E[E["lead"] == 1][["province_code", "q", "P0H4_p", "y"]].merge(s2[["province_code", "q", "probability", "observed"]],
                                                                       on=["province_code", "q"], how="inner")
    out["reproduction"] = {"B0_price_max_abs": float((chk["B0_price"] - chk["pi_P_b"]).abs().max()),
                           "CR_price_max_abs": float((chk["CR_price"] - chk["pi_P_c"]).abs().max()), "rows": int(len(chk)),
                           "served_export_lead1_rows_matched": int(len(sv)),
                           "served_vs_P0H4_prob_max_abs": float((sv["P0H4_p"] - sv["probability"].astype(float)).abs().max()) if len(sv) else None,
                           "served_observed_equals_label": bool((sv["observed"].map({"HIGH": 1, "LOW": 0}).fillna(sv["observed"]).astype(int) == sv["y"]).all()) if len(sv) else None}

    # 2. independent metrics
    g = E[E["lead"] == 2].copy()
    g["province"] = g["province_code"].map(NAMES)
    g["year"] = g["q"] // 4
    out["lead2"] = {}
    for c in ("P0H4", "B0", "CR"):
        col = f"{c}_p"
        dv = g["q"] <= F.DEV_LAST
        out["lead2"][c] = {"all": metrics(g["y"], g[col]), "dev": metrics(g.loc[dv, "y"], g.loc[dv, col]),
                           "later": metrics(g.loc[~dv, "y"], g.loc[~dv, col]),
                           "by_province": by(g, col, "province"), "by_year": by(g, col, "year")}
    committed = json.loads((T.OUT / "cpi_refresh.json").read_text())["cands"]
    for c in ("P0H4", "B0", "CR"):
        L = committed[c]["leads"]["2"]
        out["lead2"][c]["uncertainty"] = {"accuracy_ci90_quarter_block": L["acc_ci90"], "brier_vs_persistence": L["brier_vs_persist"],
                                          "brier_vs_climatology": L["brier_vs_clim"], "failed_R1_R7": L["failed"]}
        out["lead2"][c]["threshold_sweep_diagnostic"] = {
            f"{cut:.3f}": {"accuracy": float(((g[f"{c}_p"] >= cut).astype(int) == g["y"]).mean()),
                           "recall_high": float(((g[f"{c}_p"] >= cut) & (g["y"] == 1)).sum() / g["y"].sum()),
                           "precision": float(((g[f"{c}_p"] >= cut) & (g["y"] == 1)).sum() / max(int((g[f"{c}_p"] >= cut).sum()), 1))}
            for cut in np.arange(.30, .701, .05)}
    out["lead1_reference"] = {c: metrics(E.loc[E["lead"] == 1, "y"], E.loc[E["lead"] == 1, f"{c}_p"]) for c in ("P0H4", "B0", "CR")}
    out["baselines_lead2"] = {"always_low_accuracy": float((g["y"] == 0).mean()),
                              "persistence": metrics(g["y"], g["PERS_AB"]), "climatology_brier": float(((g["CLIM_p"] - g["y"]) ** 2).mean())}

    # 3. candidates
    out["candidates_lead2"] = candidates()

    # 4. overfitting: price part, in-sample vs out-of-sample (B0)
    rows = []
    for t, mdl in models.items():
        tr = T.train_rows(S, t)
        assert (tr["q"] <= t - 1).all()                                     # no training target after the origin
        te = S[S["t"] == t].merge(E[E["t"] == t][KEY + ["price"]], on=KEY).rename(columns={"price": "y_price"})
        p_tr, p_te = mdl.predict(tr), mdl.predict(te)
        rows.append({"origin": F.qs(int(t)), "train_rows": int(len(tr)), "train_brier": float(np.mean((p_tr - tr["y"]) ** 2)),
                     "test_rows": int(len(te)), "test_brier": float(np.mean((p_te - te["y_price"]) ** 2)) if len(te) else None})
    ov = pd.DataFrame(rows)
    out["overfitting_price_part"] = {"by_origin": rows, "mean_train_brier": float(ov["train_brier"].mean()),
                                     "mean_test_brier": float(ov["test_brier"].dropna().mean())}

    # 5. missing indicators at Lead 2 (models fixed, test rows only)
    te2 = S[S["lead"] == 2]
    base = pd.concat([te2[te2["t"] == t][KEY].assign(pp=models[t].predict(te2[te2["t"] == t])) for t in models])
    miss = {}
    for b, cols in T.GROUPS.items():
        parts = []
        for t, mdl in models.items():
            x = te2[te2["t"] == t].copy()
            x[cols] = np.nan
            parts.append(x[KEY].assign(pm=mdl.predict(x)))
        m = g[KEY + ["y", "pi_H_AB", "B0_p"]].merge(pd.concat(parts), on=KEY).merge(base, on=KEY)
        assert float((m["pi_H_AB"] * m["pp"] - m["B0_p"]).abs().max()) < 1e-5
        pm = m["pi_H_AB"] * m["pm"]
        miss[b] = {"calls_changed": int(((pm >= .5) != (m["B0_p"] >= .5)).sum()), "accuracy": float(((pm >= .5).astype(int) == m["y"]).mean()),
                   "recall_high": float(((pm >= .5) & (m["y"] == 1)).sum() / m["y"].sum()), "brier": float(((pm - m["y"]) ** 2).mean())}
    out["missing_indicator_lead2_B0"] = miss

    # 6. target validity
    lab = g.groupby("q").agg(hunger=("hunger", "first"), hunger_unique=("hunger", "nunique"), y_unique=("y", "nunique"),
                             high=("y", "sum"))
    out["target_validity"] = {
        "label": "T43c = 1[Balance Luzon SWS hunger > 11.3%] x 1[province food (or food-minus-headline) inflation above its 2021-22 60th percentile]",
        "hunger_component_identical_across_provinces_every_quarter": bool((lab["hunger_unique"] == 1).all()),
        "quarters_with_hunger_condition": int(lab["hunger"].sum()), "quarters": int(len(lab)),
        "quarters_where_provinces_differ": int((lab["y_unique"] > 1).sum()),
        "share_of_label_variance_within_quarter": float(g.groupby("q")["y"].var(ddof=0).mean() / g["y"].var(ddof=0)),
        "lead2_high_rows": int(g["y"].sum()),
        "provincial_measured_food_insecurity_outcome": "none in the evaluation data (CBMS 2024 FIES: one window, not held)"}
    (T.OUT / "lead2_objectives_audit.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: out[k] for k in ("reproduction", "target_validity", "overfitting_price_part")}, indent=1, default=float)[:3000])


if __name__ == "__main__":
    main()
