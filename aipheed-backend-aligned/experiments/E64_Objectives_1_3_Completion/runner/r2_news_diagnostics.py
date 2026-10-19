"""E64 r2 (Objective 1 B): why news does or does not carry forecast signal. Diagnostics only (no model is chosen here).

Uses the backend N3 table (data/n3_features.csv, written by c1) and labels recomputed from raw files (E62 r1).
  * coverage: admitted province articles per province-quarter; share of zero / missing per N3 column; FSSI status counts
  * timing: age (days before the issue date) of the admitted articles; share published in the last 30 days of quarter t
  * association with the target two quarters later (PS at t+2, the provincial part of T43), origins 2021-Q3..2026-Q1:
    Spearman, AUC, and the partial correlation given the latest food YoY (F_now) - does news add anything beyond CPI?
    Rows in one quarter are not independent: a quarter-block permutation p-value is reported
  * volume dependence: Spearman of every trigger signal with n3_cov
  * per trigger, the number of admitted articles by quarter (are categories empty or duplicated?)

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E64_Objectives_1_3_Completion/runner/r2_news_diagnostics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e64_lib as K  # noqa: E402
from scipy import stats  # noqa: E402

L, np, pd = K.L, K.np, K.pd
LAB = K.EXP / "E62_Final_System_Audit" / "tables" / "r1_labels_independent.csv"
RNG = np.random.default_rng(64)


def main():
    from app.news import pipeline_v3 as P
    n3 = pd.read_csv(K.E64 / "data" / "n3_features.csv", dtype={"province_code": str})
    lab = pd.read_csv(LAB, dtype={"province_code": str})
    lab["t"] = lab["quarter"].map(L.qi) - 2
    d, X, B = K.E.load()
    fnow = []
    for t in sorted(n3["t"].unique()):
        if t < L.qi("2021-Q3"):
            continue
        _, te = K.F.frame(d, X, B, int(t), None)
        fnow += [{"t": int(t), "province_code": p, "F_now": f} for p, f in zip(te["province_code"], te["F_now"])]
    D = n3.merge(lab[["t", "province_code", "PS", "T43"]], on=["t", "province_code"], how="left").merge(
        pd.DataFrame(fnow), on=["t", "province_code"], how="left")
    cols = list(P.N3_COLS)
    res = {"coverage": {}, "association": [], "volume": {}}
    ev = D[(D["t"] >= L.qi("2023-Q4")) & (D["t"] <= L.qi("2026-Q1"))]
    res["coverage"]["eval_rows"] = int(len(ev))
    res["coverage"]["zero_share_eval"] = {c: round(float((ev[c] == 0).mean()), 3) for c in cols if c != "n3_fssi"}
    res["coverage"]["fssi_missing_eval"] = round(float(ev["n3_fssi"].isna().mean()), 3)
    res["coverage"]["fssi_status_all"] = D["fssi_status"].value_counts().to_dict()
    res["coverage"]["admitted_province_articles_by_year"] = D.assign(y=D["t"] // 4).groupby("y")["n_admitted"].sum().to_dict()
    res["coverage"]["province_quarters_with_0_admitted_eval"] = int((ev["n_admitted"] == 0).sum())
    # timing
    ages, late = [], []
    for t in range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1):
        O = P.origin(t)
        for a in P.asof(t):
            age = (O - P._ph(a)).days
            ages.append(age)
            late.append(age <= 30)
    res["timing"] = {"articles": len(ages), "median_age_days_at_issue": float(np.median(ages)),
                     "share_in_last_30_days": round(float(np.mean(late)), 3),
                     "note": "the target is 4-6 months after the issue date; an article is on average this old at issue"}
    # association with PS at t+2 (labels known), origins 2021-Q3..2026-Q1
    A = D[D["PS"].notna() & D["F_now"].notna()].copy()

    def resid(y, x):
        Z = np.c_[np.ones(len(x)), x]
        return y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    for c in cols:
        s = A[[c, "PS", "F_now", "t"]].dropna()
        if s[c].nunique() < 2:
            res["association"].append({"feature": c, "n": int(len(s)), "constant": True})
            continue
        rho = stats.spearmanr(s[c], s["PS"]).statistic
        from sklearn.metrics import roc_auc_score
        auc = roc_auc_score(s["PS"], s[c])
        pr = stats.pearsonr(resid(s[c].to_numpy(float), s["F_now"].to_numpy(float)),
                            resid(s["PS"].to_numpy(float), s["F_now"].to_numpy(float))).statistic
        # quarter-block permutation of the feature across quarters (keeps the within-quarter structure)
        qs = s["t"].to_numpy()
        uq = np.unique(qs)
        blocks = {q: s[c].to_numpy()[qs == q] for q in uq}
        null = []
        for _ in range(2000):
            perm = RNG.permutation(uq)
            vals = np.concatenate([blocks[pq][:np.sum(qs == q)] if len(blocks[pq]) >= np.sum(qs == q) else
                                   np.resize(blocks[pq], np.sum(qs == q)) for q, pq in zip(uq, perm)])
            order = np.concatenate([np.where(qs == q)[0] for q in uq])
            v = np.empty(len(s))
            v[order] = vals
            null.append(abs(stats.spearmanr(v, s["PS"]).statistic))
        res["association"].append({"feature": c, "n": int(len(s)), "spearman_PS_t2": round(float(rho), 3),
                                   "auc_PS_t2": round(float(auc), 3), "partial_r_given_F_now": round(float(pr), 3),
                                   "quarter_permutation_p": round(float(np.mean(np.array(null) >= abs(rho) - 1e-12)), 3)})
    base = A[["F_now", "PS"]].dropna()
    from sklearn.metrics import roc_auc_score
    res["reference_F_now"] = {"spearman_PS_t2": round(float(stats.spearmanr(base["F_now"], base["PS"]).statistic), 3),
                              "auc_PS_t2": round(float(roc_auc_score(base["PS"], base["F_now"])), 3)}
    for c in cols:
        if c not in ("n3_cov",) and D[c].nunique() > 1:
            res["volume"][c] = round(float(stats.spearmanr(D[c], D["n3_cov"], nan_policy="omit").statistic), 3)
    trig = pd.DataFrame([{"quarter": a["quarter"], "trigger": a["trigger"], "attributed": a["province_code"] is not None}
                         for a in P.admitted()])
    trig.groupby(["quarter", "trigger", "attributed"]).size().unstack(["trigger", "attributed"], fill_value=0).to_csv(
        K.E64 / "tables" / "r2_admitted_by_quarter_trigger.csv", lineterminator="\n")
    pd.DataFrame(res["association"]).to_csv(K.E64 / "tables" / "r2_news_association.csv", index=False, lineterminator="\n")
    (K.E64 / "out" / "r2_news_diagnostics.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
