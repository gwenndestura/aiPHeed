"""E42 Phase 2 audit (no model is fitted or scored here): labels, SWS/CPI reference periods, NLP store, triggers.

    backend/venv/Scripts/python.exe -B runner/e42_audit.py   -> runs/audit/{audit.json, label_table.csv}

E40 holdout quarters (2025-Q4..2026-Q3) are exposed (E41 CONTAMINATION_LOG C-1); every row of them is flagged.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E42 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E42.parent / "E41_Lead2_Audit" / "runner"))
import e41_lib as L  # noqa: E402

np, pd = L.np, L.pd
ROOT = L.ROOT
NEWS = ROOT / "backend" / "data" / "news_e31"
EXPOSED = {L.qi(q) for q in ("2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3")}
OUT = E42 / "runs" / "audit"


def v1_labels(d: L.Data) -> pd.DataFrame:
    """v1/T1_A: S1 = H + 2D; HIGH if S1 > tau, tau = median S1 of province-quarters whose rounds were posted
    before the origin of the quarter's own forecast (here: before the start of the quarter after it)."""
    s = pd.read_csv(ROOT / "backend" / "data" / "inputs" / "s1_labels.csv", dtype={"province_code": str})
    s["q"] = s["quarter"].map(L.qi)
    posted = L.h_quarters(d).merge(d.sws.groupby("q")["published"].max().reset_index(), on="q")
    rows = []
    for q in sorted(s["q"].unique()):
        O = L.origin(q)                                         # first day of q+1
        prior = s[s["q"].isin(posted[posted["published"] < O]["q"]) & (s["q"] < q)]
        tau = prior["S1"].median() if len(prior) else np.nan
        for _, r in s[s["q"] == q].iterrows():
            rows.append({"province_code": r["province_code"], "q": q, "S1": r["S1"], "tau": tau,
                         "y": int(r["S1"] > tau) if pd.notna(tau) else np.nan})
    return pd.DataFrame(rows)


def prevalence(df: pd.DataFrame, name: str, meaning: str, level: str) -> dict:
    g = df.dropna(subset=["y"])
    byq = g.groupby("q")["y"].agg(["mean", "nunique"])
    return {"label": name, "measures": meaning, "level": level, "rows": int(len(g)), "quarters": int(g["q"].nunique()),
            "HIGH_share": float(g["y"].mean()),
            "by_year": {str(y): float(v) for y, v in g.groupby(g["q"] // 4)["y"].mean().items()},
            "by_province": {L.NAMES[p]: float(v) for p, v in g.groupby("province_code")["y"].mean().items()},
            "quarters_all_five_identical": int((byq["nunique"] == 1).sum()),
            "exposed_rows_included": int(g["q"].isin(EXPOSED).sum())}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = L.load()
    out = {}

    # ------------------------------------------------------------------ labels
    v1 = v1_labels(d)
    F = L.fpp_labels(d)
    e40 = L.e40_labels(d)
    hq = L.h_quarters(d).set_index("q")["H"]
    labs = {"v1_T1A_relative": (v1, "S1 = H + 2D above the trailing median of earlier S1 (relative composite)",
                                "province (H regional)"),
            "E39_FPP_4pct": (F, "provincial food inflation > 4.0% (price pressure)", "province"),
            "E40_P60_sustain2": (e40, "SWS H > 11.3 and (food or gap above 2021-22 P60) in q and q-1", "province (H regional)")}
    for thr in (3.0, 5.0):
        labs[f"FPP_{thr:g}pct_sensitivity"] = (F.assign(y=(F["F"] > thr).astype(int)), f"food inflation > {thr:g}%",
                                               "province")
    out["labels"] = [prevalence(df, n, m, lv) for n, (df, m, lv) in labs.items()]
    # agreement between labels on common rows
    k = ["province_code", "q"]
    m = v1[k + ["y"]].rename(columns={"y": "v1"}).merge(F[k + ["y"]].rename(columns={"y": "fpp"}), on=k) \
        .merge(e40[k + ["y"]].rename(columns={"y": "e40"}), on=k, how="left").dropna(subset=["v1"])
    out["label_agreement"] = {"rows": int(len(m)), "v1_vs_fpp": float((m["v1"] == m["fpp"]).mean()),
                              "v1_vs_e40": float((m.dropna()["v1"] == m.dropna()["e40"]).mean()),
                              "fpp_vs_e40": float((m.dropna()["fpp"] == m.dropna()["e40"]).mean())}

    # ------------------------------------------------------------------ v1 root-cause tests
    v = v1.dropna(subset=["y"]).copy()
    v["H"] = v["q"].map(hq)
    v["dH"] = v["q"].map(hq.diff())
    h0 = hq[hq.index <= L.qi("2022-Q4")].median()
    v["H_above_2122_median"] = (v["H"] > h0).astype(int)
    vd = v.dropna(subset=["dH"])
    tau_by_q = v.groupby("q")[["tau", "H"]].first()
    out["v1_root_cause"] = {
        "H_median_2021_22": float(h0),
        "H_mean_by_year": {str(y): float(x) for y, x in hq.groupby(hq.index // 4).mean().items()},
        "tau_by_year": {str(y): float(x) for y, x in tau_by_q["tau"].groupby(tau_by_q.index // 4).mean().items()},
        "share_v1_HIGH_when_H_above_2021_22_median": float(v[v["H_above_2122_median"] == 1]["y"].mean()),
        "share_v1_HIGH_when_H_at_or_below": float(v[v["H_above_2122_median"] == 0]["y"].mean()),
        "v1_HIGH_but_H_fell_since_previous_quarter": float(vd[(vd["y"] == 1)]["dH"].lt(0).mean()),
        "agreement_v1_with_deterioration_dH_gt_0": float(((vd["dH"] > 0).astype(int) == vd["y"]).mean()),
        "share_of_S1_variance_from_regional_H": float(np.var(v["H"]) / np.var(v["S1"])),
        "v1_HIGH_with_food_inflation_below_4pct": float(
            v.merge(F[k + ["F"]], on=k).query("y == 1")["F"].lt(4).mean()),
        "note": "S1 = H + 2D with D = food YoY minus the five-province mean, so a province can be HIGH with "
                "falling or negative food inflation when regional hunger is high.",
    }

    # ------------------------------------------------------------------ circularity
    X = pd.read_csv(sorted((E42.parent / "E41_Lead2_Audit" / "runs").glob("2026*/features_asof.csv"))[0],
                    dtype={"province_code": str})
    from sklearn.metrics import roc_auc_score
    circ = {}
    for name, df in (("v1", v1), ("FPP", F), ("E40", e40)):
        j = X.assign(q=X["t"] + 2).merge(df[k + ["y"]], on=k).dropna(subset=["y"])
        j = j[~j["q"].isin(EXPOSED)] if name == "E40" else j
        circ[name] = {f: float(roc_auc_score(j["y"], j[f])) for f in ("H_last", "F_last", "F_now", "F_hat_M1")
                      if j[f].notna().all() and j["y"].nunique() == 2}
    out["circularity_lead2_single_input_auc"] = circ

    # ------------------------------------------------------------------ SWS / CPI reference periods
    r = pd.read_csv(L.SWS_FILE)
    r["published"] = pd.to_datetime(r["published"])
    r["q"] = r["quarter"].map(L.qi)
    r["quarter_end"] = r["q"].map(lambda q: L.origin(q) - pd.Timedelta(days=1))
    r["lag_days_after_quarter_end"] = (r["published"] - r["quarter_end"]).dt.days
    out["sws_audit"] = {
        "rounds": int(len(r)), "approved_rounds": int((r["definition_A"].astype(str) == "True").sum()),
        "supplementary_excluded": r[r["definition_A"].astype(str) != "True"]["quarter"].tolist(),
        "quarters_without_approved_round": sorted(set(L.qs(q) for q in range(L.FIRST_Q, L.qi("2026-Q3") + 1))
                                                  - set(L.qs(q) for q in L.h_quarters(d)["q"])),
        "posted_before_quarter_end": int((r["lag_days_after_quarter_end"] < 0).sum()),
        "lag_days_min_median_max": [int(r["lag_days_after_quarter_end"].min()),
                                    int(r["lag_days_after_quarter_end"].median()),
                                    int(r["lag_days_after_quarter_end"].max())],
        "geography": "Balance Luzon (Luzon outside NCR), one value for all five provinces; never provincial",
        "quarter_assignment": "fieldwork date (round names carry the fieldwork dates)",
    }
    I = d.idx.set_index(["province_code", "commodity", "ym"])["index"]
    y = d.yoy.copy()
    y["implied"] = [100 * (I.get((p, c, mm), np.nan) / I.get((p, c, mm - 12), np.nan) - 1)
                    for p, c, mm in zip(y["province_code"], y["commodity"], y["ym"])]
    e = (y["implied"] - y["yoy"]).abs().dropna()
    out["cpi_audit"] = {"months_compared": int(len(e)), "max_abs_diff_pp": float(e.max()),
                        "label_uses": "published YoY (not index level, not month-on-month)",
                        "release_rule": "month m usable from the 5th-13th of m+1: at O(t) months <= month 2 of t"}

    # ------------------------------------------------------------------ NLP store
    arts = [json.loads(line) for line in open(NEWS / "articles.jsonl", encoding="utf-8")]
    scores = {}
    for line in open(NEWS / "scores.jsonl", encoding="utf-8"):
        s = json.loads(line)
        scores[s["article_key"]] = s.get("status")
    titles = collections.Counter(a["title"].strip().lower() for a in arts)
    attributed = [a for a in arts if a.get("geo_province_code")]
    fv = pd.read_csv(NEWS / "fssi_v2_panel.csv")
    out["nlp_audit"] = {
        "articles": len(arts), "province_attributed": len(attributed),
        "date_kind": dict(collections.Counter(a["date_kind"] for a in arts)),
        "quarter_matches_publication_date": int(sum(a["quarter"] == f"{a['ph_date'][:4]}-Q{(int(a['ph_date'][5:7]) - 1) // 3 + 1}"
                                                    for a in arts)),
        "collected_retroactively_first_seen": sorted({a["first_seen_at"][:10] for a in arts}),
        "outside_requested_window": int(sum(bool(a.get("outside_requested_window")) for a in arts)),
        "duplicate_titles_extra_copies": int(sum(v - 1 for v in titles.values() if v > 1)),
        "score_status_counts": dict(collections.Counter(scores.values())),
        "fssi_v2_evidence_status": fv["evidence_status"].value_counts().to_dict(),
        "fssi_v2_admitted_articles": int(fv["n_admitted"].sum()),
        "fssi_v2_non_missing_province_quarters": int(fv["FSSI_v2"].notna().sum()),
        "source": "Google News RSS titles only (no article text); publisher publication date",
    }

    # ------------------------------------------------------------------ trigger taxonomy issues
    tc = (ROOT / "backend" / "app" / "ml" / "nlp" / "trigger_classifier.py").read_text(encoding="utf-8")
    emp = tc[tc.index('"employment": ['):tc.index('"ofw_remittance": [')]
    out["trigger_taxonomy_issues"] = {
        "employment_list_contains_hunger_or_poverty_words": [w for w in ("gutom", "kahirapan", "economic hardship")
                                                            if f'"{w}"' in emp],
        "market_list_contains_supply_word_palay": '"palay"' in tc,
        "chapter_I_definition": "Chapter I names 'trigger composition scores' (news-derived) and data from PSA, "
                                "DOST-FNRI, SWS, PAGASA, PhilRice, BSP and DOE; it does not define government "
                                "indicators per trigger. E41/E42 government series per trigger are an extension.",
    }

    # ------------------------------------------------------------------ data staleness at each origin
    X["sws_age_quarters"] = X["H_age"]
    out["staleness"] = {"H_age_quarters_distribution": X.drop_duplicates("t")["H_age"].value_counts().sort_index()
                        .to_dict(),
                        "supply_feature_missing_share": float(X["palay_yoy"].isna().mean()),
                        "news_province_quarters_with_zero_articles": int((X["news_n"].fillna(0) == 0).sum())}

    tab = pd.DataFrame([{k2: v2 for k2, v2 in x.items() if not isinstance(v2, dict)} for x in out["labels"]])
    tab.to_csv(OUT / "label_table.csv", index=False)
    (OUT / "audit.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float)[:9000])


if __name__ == "__main__":
    main()
