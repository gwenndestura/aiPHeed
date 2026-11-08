"""E128 deliverable tables from the run_e128 outputs (no fitting here).

    python report_e128.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
X = ROOT.parent
sys.path.insert(0, str(HERE))
import build_panel as BP  # noqa: E402

GROUP_OF = {f: g for g, fl in BP.GROUPS.items() for f in fl}
FIRI_GROUP = {"A1": "market", "A2": "market", "A3": "market", "C3": "market (agriculture supply)", "C4": "market (fish supply)",
              "C1": "climate", "C2": "climate", "E1": "employment_ofw", "E2": "employment_ofw", "N1": "news_nlp",
              "V1": "poverty_vulnerability", "H1": "target / hunger history"}
SOURCE = {"H1": "SWS (verified rounds)", "region_cpi": "PSA CPI (Region IV-A)", "farmgate": "PSA farmgate prices", "C3": "PSA palay/corn production",
          "C4": "PSA fisheries production", "aquaculture": "PSA aquaculture production", "vegetables": "PSA vegetables/root crops production",
          "food_yoy": "derived from PSA CPI", "C1": "PAGASA El Nino advisories", "oni": "NOAA ONI", "typhoons": "IBTrACS (E114)",
          "rainfall": "NASA POWER / PAGASA (E119)", "temperature": "NASA POWER (E119)", "unemployment": "PSA LFS (national)",
          "E1": "PSA LFS (national)", "E2": "BSP via dated reports (national)", "news_gdelt": "GDELT DOC (national)",
          "news_local": "aiPHeed news corpus (5 provinces; E119 N1 counts)"}


def src(f):
    for k, v in SOURCE.items():
        if f.startswith(k):
            return v
    return ""


def inventory():
    inv = pd.read_csv(X / "E119R2_Indicator_Framework_Redesign/E119R2_COMPLETE_DATASET_INVENTORY.csv")
    rows = []
    for _, d in inv.iterrows():
        geo = str(d["geography"])
        firi = str(d["original_firi"]).split(" ")[0]
        regional_ok = geo in ("region", "national", "Balance Luzon", "regional")
        used = False
        rows.append(dict(level="dataset", feature=d["dataset"], dataset_id=d["dataset_id"], feature_group=FIRI_GROUP.get(firi, str(d["original_firi"])),
                         source=d["source"], geographic_level=geo, frequency=d["frequency"],
                         coverage=f"{d['first_period']}..{d['last_period']}", observations_2021plus=d["observations_2021plus"],
                         missing_pct=d["missing_pct_province_quarters"], publication_delay="see E128_FEATURE_AVAILABILITY_AUDIT.csv for model features",
                         availability_date_status=d["availability_reliability"],
                         usable_lead1=used, usable_lead2=used, usable_lead3=used, usable_lead4=used,
                         leakage_or_proxy_concern=("target source" if firi == "H1" else ""), e128_use=d["role"], note=d["reason"]))
    inv_df = pd.DataFrame(rows)
    fa = pd.read_csv(OUT / "feature_availability.csv")
    frows = []
    for _, f in fa.iterrows():
        frows.append(dict(level="model_feature", feature=f["feature"], dataset_id="", feature_group=f["group"], source=f["source"],
                          geographic_level=f["geographic_level"], frequency="quarterly (as of issue)", coverage=f"{f['first_origin_available']}..2026-Q3",
                          observations_2021plus=f["origins_available"], missing_pct=f["missing_pct_origins"],
                          publication_delay=f"median {f['median_lag_quarters']} quarter(s) between observation and issue",
                          availability_date_status=f["status_counts"], usable_lead1=True, usable_lead2=True, usable_lead3=True, usable_lead4=True,
                          leakage_or_proxy_concern=f["leakage_or_proxy_concern"], e128_use="E128 model input", note=f["note"]))
    extra = [dict(level="excluded", feature="FSSI-v3 regional (article-weighted)", feature_group="news_nlp", source="aiPHeed news corpus",
                  geographic_level="region (from provinces)", frequency="quarterly", coverage="2022-Q4..2026-Q3", observations_2021plus=11,
                  missing_pct=52.2, publication_delay="quarter t-1 at issue", availability_date_status="verified (dated articles)",
                  usable_lead1=False, usable_lead2=False, usable_lead3=False, usable_lead4=False, leakage_or_proxy_concern="",
                  e128_use="excluded (> 40% missing)", note="article volume used instead"),
             dict(level="excluded", feature="subsistence incidence 2021/2023 (regional)", feature_group="poverty_vulnerability", source="PSA",
                  geographic_level="province -> region", frequency="triennial", coverage="2021, 2023 (both published 2024-08-15)",
                  observations_2021plus=2, missing_pct="", publication_delay="2021 value published 2024-08-15 in this file",
                  availability_date_status="verified", usable_lead1=False, usable_lead2=False, usable_lead3=False, usable_lead4=False,
                  leakage_or_proxy_concern="would act as a time dummy (missing before 2024-10, constant after)", e128_use="excluded", note="poverty group not testable"),
             dict(level="excluded", feature="V1 vulnerability profile / population density", feature_group="poverty_vulnerability", source="PSA SAE 2021 / POPCEN 2024",
                  geographic_level="province", frequency="static", coverage="published 2025-07-01", observations_2021plus=5, missing_pct="",
                  publication_delay="", availability_date_status="verified", usable_lead1=False, usable_lead2=False, usable_lead3=False, usable_lead4=False,
                  leakage_or_proxy_concern="static; no regional time variation", e128_use="excluded", note=""),
             dict(level="excluded", feature="FIES 2023 CALABARZON", feature_group="poverty_vulnerability / context", source="PSA FIES 2023",
                  geographic_level="region", frequency="triennial", coverage="2023", observations_2021plus=1, missing_pct="", publication_delay="",
                  availability_date_status="verified", usable_lead1=False, usable_lead2=False, usable_lead3=False, usable_lead4=False,
                  leakage_or_proxy_concern="descriptive; not a quarterly label", e128_use="context only", note="no FIES food-insecurity items (see psa_fies2023_puf)"),
             dict(level="excluded", feature="FIRI3 / FIRI v2 scores and bands", feature_group="composite index", source="aiPHeed",
                  geographic_level="province / region", frequency="quarterly", coverage="2021+", observations_2021plus="", missing_pct="",
                  publication_delay="", availability_date_status="", usable_lead1=False, usable_lead2=False, usable_lead3=False, usable_lead4=False,
                  leakage_or_proxy_concern="composite of the same inputs; not ground truth", e128_use="excluded by E128 §2", note=""),
             dict(level="target", feature="SWS Balance Luzon involuntary hunger (quarter mean of non-commissioned rounds)", feature_group="target",
                  source="SWS (verified)", geographic_level="Balance Luzon (regional proxy)", frequency="quarterly", coverage="2021-Q2..2026-Q3",
                  observations_2021plus=20, missing_pct=13.0, publication_delay="1-3 months after fieldwork", availability_date_status="verified (publication dates)",
                  usable_lead1=True, usable_lead2=True, usable_lead3=True, usable_lead4=True, leakage_or_proxy_concern="regional proxy; not provincial or LGU",
                  e128_use="target (T1, T4) and hunger-history features", note="2021-Q1, 2022-Q1, 2025-Q1 have no non-commissioned round")]
    return pd.concat([pd.DataFrame(extra), pd.DataFrame(frows), inv_df], ignore_index=True)


def feature_availability(panel):
    base = pd.read_csv(X / "E119_Preprocessing/E119_REGIONAL_MODELING_DATASET.csv")
    base = base[base["lead"] == 1].reset_index(drop=True)
    o = panel[panel["lead"] == 1].reset_index(drop=True)
    F = BP.ALL_FEATURES
    corr = o[F].corr().abs()
    rows = []
    for f in F:
        s = o[f]
        st = base[f + "__status"].fillna("").map(lambda x: x.split(" ")[0]).value_counts().to_dict() if f + "__status" in base else {"derived": int(s.notna().sum())}
        lag = []
        if f + "__period" in base:
            for t, per in zip(base["origin"].map(BP.qparse), base[f + "__period"]):
                if isinstance(per, str) and "-Q" in per:
                    lag.append(t - BP.qparse(per))
        c = corr[f].drop(f).dropna()
        mx = c.idxmax() if len(c) else ""
        geo = "national" if f.startswith(("unemployment", "E1", "E2", "news_gdelt", "oni", "C1")) else (
            "Balance Luzon" if f.startswith("H1") else ("PAR basin" if f.startswith("typhoons") else "Region IV-A"))
        concern = []
        if f.startswith("H1"):
            concern.append("lagged target (hunger history; same source as the target, observed before issue)")
        if f in ("region_cpi_food_yoy_pct", "region_cpi_headline_yoy_pct") or f == "food_yoy_change_1q":
            concern.append("CPI release dates partly rule-based (rule_unverified)")
        if s.nunique() <= 2 and f != "C1_el_nino_in_force":
            concern.append("near-constant")
        if len(c) and c.max() > 0.9:
            concern.append(f"|r|={c.max():.2f} with {mx} (redundant)")
        rows.append(dict(feature=f, group=GROUP_OF[f], source=src(f), geographic_level=geo,
                         first_origin_available=o.loc[s.notna(), "origin"].iloc[0] if s.notna().any() else "",
                         origins_available=int(s.notna().sum()), missing_pct_origins=round(100 * s.isna().mean(), 1),
                         n_unique=int(s.nunique()), min=s.min(), max=s.max(), status_counts=json.dumps(st),
                         median_lag_quarters=float(np.median(lag)) if lag else (0.0 if f.startswith("H1") else np.nan),
                         max_abs_corr=round(float(c.max()), 3) if len(c) else np.nan, max_corr_with=mx,
                         available_at_issue="yes (E119 rule: available strictly before the issue date)",
                         usable_leads="1, 2, 3, 4 (features are taken at the issue date; identical for every lead)",
                         leakage_or_proxy_concern="; ".join(concern), note="E119 leakage checks passed; transforms use earlier-issue values only"))
    return pd.DataFrame(rows)


def main():
    panel = pd.read_csv(OUT / "panel.csv")
    pr = pd.read_csv(OUT / "predictions_raw.csv")
    summ = pd.read_csv(OUT / "summary_metrics.csv")
    s = json.load(open(OUT / "summary.json"))
    fa = feature_availability(panel)
    fa.to_csv(OUT / "feature_availability.csv", index=False)
    fa.to_csv(ROOT / "E128_FEATURE_AVAILABILITY_AUDIT.csv", index=False)
    inventory().to_csv(ROOT / "E128_DATA_INVENTORY.csv", index=False)

    # target class distribution
    lab = panel[panel["y_bl_hunger"].notna()]
    q1 = lab[lab["lead"] == 1][["target_quarter", "y_bl_hunger", "y_published", "y_n_rounds", "T1", "T4", "trail4_mean_at_issue"]].copy()
    rows = [dict(scope="quarters (independent)", target="T1", n=len(q1), n_high=int(q1["T1"].sum()), n_low=int((q1["T1"] == 0).sum()))]
    for tg in ("T1", "T4"):
        for k in BP.LEADS:
            d = lab[(lab["lead"] == k) & lab[tg].notna()]
            ev = pr[(pr["target"] == tg) & (pr["lead"] == k) & (pr["model"] == "M2_Persistence")]
            rows.append(dict(scope=f"lead {k} labelled rows", target=tg, n=len(d), n_high=int(d[tg].sum()), n_low=int((d[tg] == 0).sum()),
                             outer_eval_rows=len(ev), outer_high=int(ev["y"].sum()), outer_low=int((ev["y"] == 0).sum())))
    cd = pd.DataFrame(rows)
    q1 = q1.rename(columns={"y_bl_hunger": "bl_hunger_pct", "y_published": "final_round_published", "y_n_rounds": "rounds"})
    with open(ROOT / "E128_TARGET_CLASS_DISTRIBUTION.csv", "w", newline="") as fh:
        cd.to_csv(fh, index=False, lineterminator="\n")
        fh.write("\n")
        q1.to_csv(fh, index=False, lineterminator="\n")

    # issue-date and lead mapping
    cols = ["origin", "issue_date", "lead", "target_quarter", "target_quarter_end", "months_issue_to_target_end", "latest_sws_quarter",
            "latest_sws_published", "true_sws_horizon_q", "latest_cpi_period", "latest_news_period", "y_bl_hunger", "y_published", "T1", "T4"]
    panel[cols].to_csv(ROOT / "E128_ISSUE_DATE_AND_LEAD_MAPPING.csv", index=False)

    # splits, training results, predictions
    m1 = pr[pr["model"] == "M1_LightGBM"]
    sp = m1[["target", "lead", "origin", "issue_date", "n_train", "n_train_high", "train_first_target", "train_last_target", "target_quarter", "y_published"]].copy()
    sp["inner_validation"] = "last 3 training rows by publication date (expanding)"
    sp["block"] = np.where(m1["target_q"] <= 2024 * 4 + 3, "DEV", "LATER")
    sp.rename(columns={"target_quarter": "outer_eval_target"}).to_csv(ROOT / "E128_WALK_FORWARD_SPLITS.csv", index=False)
    tr = pr[pr["model"] != "M2_Persistence"][["target", "model", "lead", "origin", "n_train", "params", "inner_logloss", "inner_points_scored",
                                              "train_accuracy", "train_brier", "train_auc", "n_trees_with_splits", "q", "y"]]
    tr.to_csv(ROOT / "E128_MODEL_TRAINING_RESULTS.csv", index=False)
    pm = pr.merge(panel[["origin", "lead", "latest_cpi_period", "latest_news_period", "latest_sws_quarter", "latest_sws_published"]], on=["origin", "lead"])
    pm["geographic_unit"] = "Balance Luzon (regional proxy for CALABARZON)"
    pm["model_version"] = "E128-" + pm["target"] + "-" + pm["model"] + "-L" + pm["lead"].astype(str) + "-" + pm["origin"]
    pm["feature_snapshot"] = "out/panel.csv (origin, lead)"
    pm = pm.rename(columns={"q": "predicted_probability", "cls": "predicted_class", "y": "actual_class", "y_published": "actual_target_observed"})
    pm[["geographic_unit", "target", "model", "model_version", "origin", "issue_date", "latest_cpi_period", "latest_news_period", "latest_sws_quarter",
        "latest_sws_published", "target_quarter", "lead", "actual_target_observed", "predicted_probability", "predicted_class", "actual_class",
        "y_bl_hunger", "feature_snapshot"]].to_csv(ROOT / "E128_MODEL_PREDICTIONS.csv", index=False)
    pd.read_csv(OUT / "artifacts.csv").to_csv(ROOT / "E128_MODEL_ARTIFACT_MANIFEST.csv", index=False)

    # lead comparison and horizon comparison
    keep = ["target", "lead", "model", "block", "n", "n_pos", "n_neg", "tp", "fp", "tn", "fn", "accuracy", "balanced_accuracy", "precision", "recall",
            "low_recall", "f1", "roc_auc", "pr_auc", "brier", "mean_prob", "high_share", "acc_majority", "acc_persistence", "brier_persistence",
            "brier_clim", "p_brier_vs_persistence", "p_brier_vs_clim", "acc_thirds", "loqo_min_acc"] + [c for c in summ.columns if c.startswith("pass_")] + [
            "reliable", "reliable_if_R1_quarters_only"]
    summ[keep].to_csv(ROOT / "E128_LEAD_1_TO_4_COMPARISON.csv", index=False)
    hz = []
    for tg in ("T1", "T4"):
        for mname, K in s["max_reliable_lead"][tg].items():
            a = summ[(summ["target"] == tg) & (summ["model"] == mname) & (summ["block"] == "ALL")].set_index("lead")
            fails = {k: [c.replace("pass_", "") for c in a.columns if c.startswith("pass_R") and "sensitivity" not in c and not a.loc[k, c]] for k in a.index}
            hz.append(dict(target=tg, model=mname, max_reliable_lead_q=K, calendar=("none established" if K == 0 else f"{3 * K} months"),
                           max_lead_if_R1_quarters_only=s["max_lead_if_R1_quarters_only"][tg][mname], first_unreliable_lead=K + 1,
                           failed_at_first_unreliable=";".join(fails.get(K + 1, [])),
                           **{f"L{k}_acc": a.loc[k, "accuracy"] for k in a.index}, **{f"L{k}_brier": a.loc[k, "brier"] for k in a.index},
                           **{f"L{k}_failed": ";".join(fails[k]) for k in a.index},
                           status="inconclusive (no lead passes; all rows previously inspected)"))
    pd.DataFrame(hz).to_csv(ROOT / "E128_RELIABLE_HORIZON_COMPARISON.csv", index=False)

    ab = pd.read_csv(OUT / "ablation.csv")
    ab.to_csv(ROOT / "E128_FEATURE_GROUP_ABLATION.csv", index=False)

    # SHAP: mean |SHAP| by feature and group per target x lead
    sh = pd.read_csv(OUT / "shap_outer_rows.csv")
    F = [f for f in BP.ALL_FEATURES if f in sh.columns]
    srows = []
    for (tg, k), g in sh.groupby(["target", "lead"]):
        a = g[F].abs().mean()
        tot = a.sum()
        for f in F:
            srows.append(dict(target=tg, lead=k, feature=f, group=GROUP_OF[f], mean_abs_shap=a[f], share=a[f] / tot if tot else np.nan))
    sr = pd.DataFrame(srows)
    sr.to_csv(OUT / "shap_feature_summary.csv", index=False)
    sr.groupby(["target", "lead", "group"])["share"].sum().unstack().to_csv(OUT / "shap_group_shares.csv")

    # temporal tags (ex post conditions of the target quarter, for analysis only)
    o = panel[panel["lead"] == 1].set_index("t")
    tag = {}
    for t in o.index:
        nxt = o.loc[t + 1] if (t + 1) in o.index else None
        tag[t] = dict(food_infl_high=(nxt is not None and nxt["region_cpi_food_yoy_pct"] >= 5),
                      typhoon_heavy=(nxt is not None and nxt["typhoons_PAR"] >= 8),
                      unemployment_rising=(nxt is not None and nxt["E1_unemployment_change_pp"] > 0),
                      hunger_high=(o.loc[t, "y_bl_hunger"] >= 15) if False else None)
    lab_y = panel[panel["lead"] == 1].set_index("target_q")["y_bl_hunger"]
    trows = []
    for (tg, k, mname), g in pr.groupby(["target", "lead", "model"]):
        g = g.copy()
        g["correct"] = ((g["q"] >= 0.5) == g["y"]).astype(float)
        for cond in ("food_infl_high", "typhoon_heavy", "unemployment_rising", "hunger_ge_15", "regime_2023Q4_on", "before_2023Q4"):
            if cond == "hunger_ge_15":
                mask = g["target_q"].map(lambda q: lab_y.get(q, np.nan) >= 15)
            elif cond == "regime_2023Q4_on":
                mask = g["target_q"] >= 2023 * 4 + 3
            elif cond == "before_2023Q4":
                mask = g["target_q"] < 2023 * 4 + 3
            else:
                mask = g["target_q"].map(lambda q: bool(tag.get(q, {}).get(cond, False)))
            sub = g[mask.astype(bool)]
            trows.append(dict(target=tg, lead=k, model=mname, condition=cond, n=len(sub), accuracy=sub["correct"].mean() if len(sub) else np.nan,
                              brier=float(((sub["q"] - sub["y"]) ** 2).mean()) if len(sub) else np.nan, high_share=sub["y"].mean() if len(sub) else np.nan))
    pd.DataFrame(trows).to_csv(OUT / "temporal_conditions.csv", index=False)
    print("tables written")


if __name__ == "__main__":
    main()
