"""LEAD2_ROOTCAUSE_II (PROTOCOL_LEAD2_ROOTCAUSE_II.md, hash checked): why Lead 2 fails, measured. No model is fitted and
no candidate is scored; it reads the saved as-of predictions (asof_reeval_rows.csv) and the stack.

1. Error trace: every Lead-2 error of B0, CR-ANC (verified) and CR-ANC (day 10) back to label, issue-time features,
   missing data and output; attributed to the hunger part, the price part or both; price errors typed.
2. Sample: quarter clustering (ICC, design effect, effective n), quarter-cluster bootstrap of the R2 / R6 quantities and
   of the R6 pass rate, single-row margins, class transitions available to training.
3. Target: what each component measures (regional observed hunger vs provincial price proxy).
4. Price predictability ceiling: a Gaussian projection-error reference (not a candidate). Errors of the CPI
   projections are estimated on target quarters before the evaluation period only; the best attainable price-call
   accuracy from the projection is computed and compared with LightGBM.
5. Point-in-time audit of the 12 indicators.

    python lead2_rootcause.py   # ../out/lead2_rootcause.json, ../out/lead2_error_trace.csv, ../out/pit_audit.csv
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal, norm

import final as FN  # noqa: F401  (sys.path order)
import lt_lib as T
import asof_reeval as A

F, KEY = T.F, T.KEY
NAMES = A.NAMES
FIRST_EVAL_Q = 2023 * 4 + 1                                   # first Lead-2 evaluation target quarter (2023-Q2)
CANDS = {"B0": "base m0", "CRANCVER": "verified", "CRANCD10": "day 10 (provisional)"}


def labels() -> pd.DataFrame:
    L = pd.read_csv(T.EXP / "FORECAST_RESEARCH" / "data" / "labels_t43c.csv", dtype={"province_code": str})
    L["mf"] = L["F"] - L["province_code"].map(F.TH_F)
    L["mg"] = L["F"] - L["HL"] - L["province_code"].map(F.TH_G)
    assert ((((L["mf"] > 0) | (L["mg"] > 0)).astype(int)) == L["price"]).all()      # the price label, re-derived
    assert ((L["H"] > F.H_LINE).astype(int) == L["hunger"]).all() and ((L["price"] & L["hunger"]) == L["y"]).all()
    return L


# ------------------------------------------------------------------------------------------------------ 1. errors
def error_trace(E, S, Lb):
    g = E[E["lead"] == 2].merge(S[KEY + ["A1_food", "A1_gap", "A_mom", "h_last", "N1", "A3", "E2", "m0r"]], on=KEY, how="left")
    g = g.merge(Lb[["province_code", "q", "H", "mf", "mg"]], on=["province_code", "q"], how="left")
    rows = []
    for c in CANDS:
        call = (g[f"{c}_p"] >= .5).astype(int)
        for r, k in zip(g.itertuples(), call):
            if k == r.y:
                continue
            hw = int(r.pi_H_AB >= .5) != r.hunger
            pw = int(getattr(r, f"{c}_price") >= .5) != r.price
            proj = max(r.A1_food, r.A1_gap) if pd.notna(r.A1_food) else np.nan
            real = max(r.mf, r.mg)
            if pw and r.price == 1:
                kind = "price rose after issue (projection < 0 <= realised)" if proj < 0 else "model under-called a positive projection"
            elif pw and r.price == 0:
                kind = "price fell after issue (projection >= 0 > realised)" if proj >= 0 else "model over-called a negative projection"
            else:
                kind = "hunger part" if hw else "product of two correct-sign parts crosses 0.5"
            rows.append({"candidate": c, "timing": CANDS[c], "province": NAMES[r.province_code], "target": F.qs(int(r.q)),
                         "y": int(r.y), "call": int(k), "error": "missed HIGH" if r.y else "false alarm",
                         "hunger_label": int(r.hunger), "H_target": r.H, "h_last_at_issue": r.h_last, "pi_H": round(r.pi_H_AB, 3),
                         "price_label": int(r.price), "price_p": round(getattr(r, f"{c}_price"), 3), "p": round(getattr(r, f"{c}_p"), 3),
                         "proj_margin_max": round(proj, 2), "realised_margin_max": round(real, 2),
                         "cpi_cutoff_months_beyond_m0": None if c == "B0" else (int(r.m0r) - A.CF.L.m0_of(int(r.t)) if pd.notna(r.m0r) else 0),
                         "missing": ",".join(x for x in ("N1", "A3", "E2") if pd.isna(getattr(r, x))),
                         "part_wrong": "both" if hw and pw else "hunger" if hw else "price" if pw else "neither (sign)", "price_error_type": kind})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------------ 2. sample
def cluster_stats(g, c, draws=4000, seed=2031):
    y, k = g["y"].to_numpy(int), (g[f"{c}_p"] >= .5).astype(int).to_numpy()
    q = g["q"].to_numpy()
    ok = (k == y).astype(float)
    uq = np.unique(q)
    m = len(g) / len(uq)
    grp = [ok[q == u] for u in uq]
    msb = m * np.var([x.mean() for x in grp], ddof=1)
    msw = np.mean([x.var(ddof=1) for x in grp])
    icc = float((msb - msw) / (msb + (m - 1) * msw)) if msb + (m - 1) * msw > 0 else 0.0
    rng = np.random.default_rng(seed)
    idx = {u: np.where(q == u)[0] for u in uq}
    acc, rec, prec, r6, r2 = [], [], [], [], []
    for _ in range(draws):
        ii = np.concatenate([idx[u] for u in rng.choice(uq, len(uq))])
        yy, kk = y[ii], k[ii]
        tp, fp, fn = ((kk == 1) & (yy == 1)).sum(), ((kk == 1) & (yy == 0)).sum(), ((kk == 0) & (yy == 1)).sum()
        a = (kk == yy).mean()
        rc = tp / (tp + fn) if tp + fn else np.nan
        pr = tp / (tp + fp) if tp + fp else np.nan
        acc.append(a), rec.append(rc), prec.append(pr)
        r6.append(bool(rc >= .6 and pr >= .6)), r2.append(bool(a >= .75))
    tp, fp, fn = int(((k == 1) & (y == 1)).sum()), int(((k == 1) & (y == 0)).sum()), int(((k == 0) & (y == 1)).sum())
    ci = lambda v: [float(np.nanquantile(v, .05)), float(np.nanquantile(v, .95))]  # noqa: E731
    # single-row margins of R6 (precision, recall >= 0.60)
    need_tp = max(0, int(np.ceil(.6 * (tp + fn) - tp)))
    return {"rows": int(len(g)), "quarters": int(len(uq)), "high_rows": int(y.sum()), "high_quarters": int(len(np.unique(q[y == 1]))),
            "icc_correct_within_quarter": icc, "design_effect": float(1 + (m - 1) * icc),
            "effective_n": float(len(g) / (1 + (m - 1) * icc)), "accuracy_ci90_cluster": ci(acc), "recall_ci90_cluster": ci(rec),
            "precision_ci90_cluster": ci(prec), "R6_pass_rate_cluster_bootstrap": float(np.mean(r6)),
            "R2_pass_rate_cluster_bootstrap": float(np.mean(r2)), "tp_fp_fn": [tp, fp, fn],
            "recall_slack_rows": tp - int(np.ceil(.6 * (tp + fn))), "precision_slack_rows": int(np.floor(tp / .6 - tp - fp + 1e-9)) if tp else -fp,
            "extra_hits_needed_for_R6_recall": need_tp}


def transitions(Lb):
    out = {}
    for name in ("price", "hunger", "y"):
        tr = {"onsets": 0, "offsets": 0}
        for p, h in Lb.sort_values("q").groupby("province_code"):
            v = h[name].to_numpy()
            tr["onsets"] += int(((v[1:] == 1) & (v[:-1] == 0)).sum())
            tr["offsets"] += int(((v[1:] == 0) & (v[:-1] == 1)).sum())
        pre = Lb[Lb["q"] < FIRST_EVAL_Q - 1]
        tr["high_rows_before_first_eval_issue"] = int(pre[name].sum())
        tr["rows_before_first_eval_issue"] = int(len(pre))
        out[name] = tr
    hq = Lb.groupby("q")["hunger"].first()
    out["hunger_regional_crossings"] = int((hq.diff().abs() == 1).sum())
    out["hunger_quarters"] = {"high": int(hq.sum()), "total": int(len(hq))}
    return out


# ------------------------------------------------------------------------------------------------------ 4. ceiling
def ceiling(S, Lb, E):
    """P(price = 1 | projected margins) under a bivariate-normal projection error, estimated on targets before the
    evaluation period (2021-Q2 .. 2023-Q1) for the same lead; Bayes call p >= 0.5."""
    X = S.merge(Lb[["province_code", "q", "mf", "mg", "price"]].rename(columns={"q": "target_q"}), on=["province_code", "target_q"])
    X = X[X["A1_food"].notna() & X["A1_gap"].notna()]
    X["ef"], X["eg"] = X["mf"] - X["A1_food"], X["mg"] - X["A1_gap"]
    out = {}
    for k in (1, 2):
        est = X[(X["lead"] == k) & (X["target_q"] < FIRST_EVAL_Q)]
        mu = est[["ef", "eg"]].mean().to_numpy()
        cov = np.cov(est[["ef", "eg"]].to_numpy().T)
        ev = X[X["lead"] == k].merge(E[E["lead"] == k][KEY + ["q", "y", "pi_H_AB", "B0_price", "CRANCVER_price", "CRANCD10_price"]],
                                     left_on=KEY, right_on=KEY)
        mvn = multivariate_normal(mean=[0, 0], cov=cov)
        p = np.array([1 - mvn.cdf([-(a + mu[0]), -(b + mu[1])]) for a, b in zip(ev["A1_food"], ev["A1_gap"])])
        pr = ev["price"].to_numpy(int)
        yy = ev["y"].to_numpy(int)
        call = (ev["pi_H_AB"].to_numpy() * p >= .5).astype(int)
        tp, fp, fn = int(((call == 1) & (yy == 1)).sum()), int(((call == 1) & (yy == 0)).sum()), int(((call == 0) & (yy == 1)).sum())
        out[k] = {"estimation_rows": int(len(est)), "estimation_targets": f"{F.qs(int(est['target_q'].min()))}..{F.qs(int(est['target_q'].max()))}",
                  "error_sd_food_gap": [float(np.sqrt(cov[0, 0])), float(np.sqrt(cov[1, 1]))], "error_mean": mu.tolist(),
                  "eval_rows": int(len(ev)), "price_base_rate_low": float(1 - pr.mean()),
                  "share_rows_margin_within_1sd": float(((np.abs(ev[["mf", "mg"]].max(axis=1)) < np.sqrt(cov[0, 0])).mean())),
                  "reference_price_accuracy_expected": float(np.mean(np.maximum(p, 1 - p))),
                  "reference_price_accuracy_realised": float(((p >= .5).astype(int) == pr).mean()),
                  "lgbm_price_accuracy": {c: float(((ev[f"{c}_price"] >= .5).astype(int) == pr).mean()) for c in ("B0", "CRANCVER", "CRANCD10")},
                  "reference_T43_accuracy": float((call == yy).mean()), "reference_T43_tp_fp_fn": [tp, fp, fn],
                  "reference_T43_recall_precision": [tp / max(1, tp + fn), tp / max(1, tp + fp)]}
    return out


# ------------------------------------------------------------------------------------------------------ 5. PIT audit
PIT = [  # indicator, columns, rule in the stack, evidence for the rule, revision / vintage risk, status
    ("A1 food-price projection", "A1_food, A1_gap, A_mom", "CPI months <= m0 (month 2 of t) at O(t); Lead 2+ refresh only under the verified ledger",
     "35 of 36 archived m0 releases precede O(t); refresh months: 32 verified, 61 owner-reported, 79 unresolved",
     "final-vintage index; 3 of 29 archived headline rates differ (<= 0.4 pp); 375 training rows predate the 2018=100 series",
     "verified for m0 with one exception (Batangas 2025-02 unverified); refresh partly unresolved"),
    ("A2 headline above usual", "A2", "all-items YoY months 1-2 of t", "same CPI release as A1", "as A1", "as A1"),
    ("A3 wholesale rice", "A3", "quarter t-1 at O(t)", "rule only; no dated releases saved", "PSA wholesale price revisions not checked", "unresolved (assumed lag)"),
    ("V1 poverty and density", "V1", "static profile at every origin", "SAE 2021 and POPCEN 2024 were published 2024-2025",
     "uses values published after every origin before 2025 (time-invariant)", "point-in-time violation, disclosed; constant over time so it cannot carry temporal signal"),
    ("C1 El Nino advisory", "C1", "PAGASA items issued strictly before O(t)", "dated items", "none", "verified by construction"),
    ("C2 typhoons within 300 km", "C2", "quarter t, complete at O(t)", "IBTrACS track dates", "best-track revisions after real time not checked", "rule plausible; vintage unverified"),
    ("C3 palay / corn drop", "C3", "quarter t-1 at O(t)", "rule only", "PSA production revisions not checked", "unresolved (assumed lag)"),
    ("C4 fisheries drop", "C4", "quarter t-1 at O(t)", "rule only", "PSA production revisions not checked", "unresolved (assumed lag)"),
    ("E1 unemployment change", "E1", "LFS months of t-1 at O(t)", "rule only", "LFS revisions not checked", "unresolved (assumed lag)"),
    ("E2 remittance decline", "E2", "BSP quarter t-1 at O(t)", "rule only", "BSP revisions not checked", "unresolved (assumed lag)"),
    ("N1 FSSI-v3 news", "N1, G_pri_yoy, NG_gap_price", "headlines published before O(t)", "1,575 dated rows, all before issue", "none (fixed scoring model)", "verified"),
    ("H1 regional hunger outlook", "H1 (and pi_H)", "SWS rounds posted before the issue", "published dates in sws_rounds_primary.csv", "none", "verified"),
]


def pit_checks(S):
    iss = pd.to_datetime(S["issue_date"])
    psa = pd.to_datetime(S["psa_newest_month"] + "-01")
    return {"psa_newest_month_end_before_issue": bool(((psa + pd.offsets.MonthEnd(0)) < iss).all()),
            "sws_published_before_issue": bool((pd.to_datetime(S["sws_newest_published"]).dropna() < iss[S["sws_newest_published"].notna()]).all()),
            "news_published_before_issue": bool((pd.to_datetime(S["news_latest_published"]).dropna() < iss[S["news_latest_published"].notna()]).all()),
            "target_after_origin": bool((S["target_q"] > S["t"]).all()),
            "missing_share_lead2": {c: float(S.loc[S["lead"] == 2, c].isna().mean()) for c in T.U2 if c != "lead"},
            "lightgbm_missing_handling": "native NaN branches; no imputation, no scaling fitted on future rows (lt_lib.Uni)",
            "threshold_window_end": "2022-12 (2021-22 P60; label definition, frozen)",
            "training_rows_using_thresholds_before_they_were_computable": int((S["issue_date"] < "2023-01-06").sum())}


def main():
    proto = T.LT / "PROTOCOL_LEAD2_ROOTCAUSE_II.md"
    assert T.sha256(proto) == (T.HERE / "ROOTCAUSE_II_SHA256.txt").read_text().strip(), "protocol changed after freezing"
    E = pd.read_csv(T.OUT / "asof_reeval_rows.csv", dtype={"province_code": str})
    C = pd.read_csv(T.OUT / "asof_reeval_cutoffs.csv", dtype={"province_code": str})
    Lb = labels()
    S0 = T.stack()
    SV = A.scenario_stack(C, "VER")
    res = {"protocol_sha256": T.sha256(proto)}
    tr = error_trace(E, SV, Lb)
    tr.to_csv(T.OUT / "lead2_error_trace.csv", index=False, lineterminator="\n")
    res["error_attribution"] = {c: {"errors": int((tr["candidate"] == c).sum()),
                                    "by_part": tr[tr["candidate"] == c]["part_wrong"].value_counts().to_dict(),
                                    "by_type": tr[tr["candidate"] == c]["price_error_type"].value_counts().to_dict(),
                                    "by_quarter": tr[tr["candidate"] == c]["target"].value_counts().sort_index().to_dict()} for c in CANDS}
    g2 = E[E["lead"] == 2]
    res["cluster"] = {c: cluster_stats(g2, c) for c in ("B0", "CRVER", "CRANCVER", "CRANCD10")}
    res["transitions"] = transitions(Lb)
    res["target_components"] = {
        "hunger": "Balance Luzon SWS involuntary hunger > 11.3: observed food insecurity, regional, one value per quarter for all five provinces",
        "price": "province food YoY > 2021-22 P60 or food-minus-headline > gap P60: a provincial food-price-pressure proxy, not observed food insecurity",
        "T43c": "hunger AND price: a composite risk proxy; no provincial observed food-insecurity series exists in the repository (outcome_gap_resolution: NOT EVALUABLE)",
        "what_lightgbm_predicts": "the price label only; pi_H is the latest-reading rule, not learned",
        "lead2_label_shares": {"hunger_high": float(g2["hunger"].mean()), "price_high": float(g2["price"].mean()), "T43_high": float(g2["y"].mean())}}
    res["ceiling_on_stack_m0"] = ceiling(S0, Lb, E)
    res["ceiling_on_stack_verified"] = ceiling(SV, Lb, E)
    pd.DataFrame(PIT, columns=["indicator", "columns", "rule", "evidence", "revision_or_vintage", "status"]).to_csv(
        T.OUT / "pit_audit.csv", index=False, lineterminator="\n")
    res["pit_checks"] = pit_checks(S0)
    (T.OUT / "lead2_rootcause.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({k: res[k] for k in ("error_attribution", "cluster", "transitions", "ceiling_on_stack_m0", "ceiling_on_stack_verified")}, indent=1, default=float))


if __name__ == "__main__":
    sys.exit(main())
