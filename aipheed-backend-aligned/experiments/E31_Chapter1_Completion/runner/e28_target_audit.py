"""E28 Phase C: forecast-target validity audit of the approved T1 label (S1 = H + 2D > tau). Descriptive only; no model
is fitted and no label is changed.  python -B runner/e28_target_audit.py  ->  runs/e28_target_audit.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard28  # noqa: E402

guard28.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

EXP = guard28.EXP
E25RUN = guard28.E25 / "runs" / "20261014T002026Z"
E27 = guard28.E27
INP = EXP / "backend_dev" / "data" / "inputs"


def main():
    rounds = pd.read_csv(INP / "sws_rounds.csv")
    s1 = pd.read_csv(INP / "s1_labels.csv")
    d = pd.read_csv(INP / "d_quarterly_panel.csv")
    E = pd.read_csv(E25RUN / "predictions_T1_A.csv")
    b1 = E[E["model"] == "B1_naive_persistence"].copy()
    out = {}

    # 1. What the label measures
    prod = rounds[rounds["definition_A"].astype(str).str.lower().eq("true") & rounds["source"].str.startswith("production")]
    H = prod.groupby("quarter")["H"].mean()
    v = d.merge(H.rename("H").reset_index(), on="quarter")
    v["S1"] = v["H"] + 2 * v["D"]
    var_H = float(v.groupby("quarter")["H"].first().var(ddof=0))
    tot = float(v["S1"].var(ddof=0))
    out["components"] = {
        "H": "SWS self-rated involuntary hunger, Balance Luzon (Luzon outside Metro Manila): a MEASURED experience-based "
             "hunger rate, but REGIONAL - one value for all five provinces, not a CALABARZON or provincial estimate",
        "D": "relative provincial food inflation (provincial food CPI YoY minus the CALABARZON mean): a CONSTRUCTED "
             "price-pressure indicator, not a measure of food insecurity",
        "S1": "H + 2D: a composite proxy; Chapter I calls it 'a composite food stress label combining SWS quarterly "
              "hunger data and PSA province-level food CPI deviation'",
        "share_of_S1_variance_from_regional_H": round(float(v.groupby("quarter")["H"].transform("first").var(ddof=0)) / tot, 4),
        "share_of_S1_variance_from_2D": round(float((2 * v["D"]).var(ddof=0)) / tot, 4),
        "labelled_quarters": sorted(v["quarter"].unique().tolist()),
        "n_labelled_quarters": int(v["quarter"].nunique()),
        "independent_regional_hunger_values": int(H.shape[0]),
        "province_quarter_labels": int(len(v)),
        "quarters_without_label_2021Q1_2026Q2": sorted(set(f"{y}-Q{q}" for y in range(2021, 2027) for q in range(1, 5)
                                                           if (y, q) <= (2026, 2)) - set(v["quarter"])),
    }

    # 2. Do the five provinces carry independent outcomes? (test rows of the evaluation)
    agree = b1.groupby(["lead", "t"])["y"].agg(lambda s: int(s.nunique() == 1))
    out["provincial_independence"] = {
        "test_dates": int(len(agree)), "dates_where_all_five_provinces_share_the_label": int(agree.sum()),
        "share": round(float(agree.mean()), 4),
        "interpretation": "the five provinces of one date share one regional H draw; rows are not independent "
                          "observations. Sample size for any reliability claim is the number of dates, not rows."}

    # 3. Class balance and threshold drift
    bl = b1.groupby("lead").agg(rows=("y", "size"), HIGH=("y", "sum"), dates=("t", "nunique"))
    bl["LOW"] = bl["rows"] - bl["HIGH"]
    meta = json.loads((E25RUN / "fold_meta_T1_A.json").read_text(encoding="utf-8"))
    taus = sorted({(v_["t"], v_["tau"]) for v_ in meta.values() if "tau" in v_})
    tau_by_t = dict(taus)
    lastH = []
    for t, tau in taus:
        o = pd.Timestamp(year=int(t[:4]) + (1 if t.endswith("Q4") else 0),
                         month={"Q1": 4, "Q2": 7, "Q3": 10, "Q4": 1}[t[-2:]], day=1)
        r = prod[pd.to_datetime(prod["published_eff"]) < o]
        lastH.append({"t": t, "tau": round(tau, 3), "last_published_H": float(r.sort_values("published_eff")["H"].iloc[-1]),
                      "mean_H_usable": round(float(r["H"].mean()), 3)})
    tr_high = [v_["train_HIGH"] / max(1, v_["n_train_rows"]) for v_ in meta.values() if v_.get("lead") == 1 and "train_HIGH" in v_]
    out["class_balance"] = {
        "by_lead": {int(k): {kk: int(vv) for kk, vv in r.items()} for k, r in bl.iterrows()},
        "training_HIGH_share_lead1_mean": round(float(np.mean(tr_high)), 4) if tr_high else None,
        "test_HIGH_share_lead1": round(float(bl.loc[1, "HIGH"] / bl.loc[1, "rows"]), 4),
        "tau_and_hunger_level_by_origin": lastH,
        "mechanism": "tau is the median of the S1 labels usable at the origin, so training labels are ~50/50 by "
                     "construction; Balance Luzon hunger rose from about 9-12% (2021-2023) to 15-25% (2024-2026), so "
                     "almost every test quarter is above the trailing median and test labels are ~90% HIGH. LOW test "
                     "rows occur only where a quarter's H fell back below the trailing median."}

    # 4. Survey uncertainty versus the threshold
    n_tab = None
    p_n = E27 / "acquisition" / "validated" / "sws_round_sample_sizes_partial.csv"
    if p_n.exists():
        n_tab = pd.read_csv(p_n)
    se_rows = []
    for r in b1.itertuples():
        Hq = H.get(r.target_quarter, np.nan)
        for n in (300, 600):
            se = math.sqrt(Hq / 100 * (1 - Hq / 100) / n) * 100 if Hq == Hq else np.nan
            se_rows.append({"lead": r.lead, "n": n, "z": abs(r.value - r.threshold) / se if se else np.nan,
                            "y": r.y})
    se = pd.DataFrame(se_rows)
    out["survey_uncertainty"] = {
        "assumption": "simple random sampling SE of H = sqrt(H(1-H)/n); D has no sampling error (CPI). Balance "
                      "Luzon n per round is 300 or 600 (partly verified, E27 O5a); design effects would widen this.",
        "per_round_n_table_rows": None if n_tab is None else int(len(n_tab)),
        "share_of_test_labels_within_1.96_SE_of_tau": {
            int(n): round(float((g["z"] < 1.96).mean()), 4) for n, g in se.groupby("n")},
        "share_of_LOW_test_labels_within_1.96_SE_of_tau": {
            int(n): round(float((g[g["y"] == 0]["z"] < 1.96).mean()), 4) if (g["y"] == 0).any() else None
            for n, g in se.groupby("n")},
        "interpretation": "a label within about 2 standard errors of tau could flip under resampling of the survey; "
                          "such labels cannot discriminate a good forecast from a lucky one."}

    # 5. Publication delays and coverage changes
    pr = rounds.copy()
    pr["pub"] = pd.to_datetime(pr["published_eff"])
    qend = {q: pd.Period(q.replace("-Q", "Q"), freq="Q").end_time.normalize() for q in pr["quarter"]}
    pr["days_after_quarter_end"] = [(p - qend[q]).days for p, q in zip(pr["pub"], pr["quarter"])]
    out["publication_and_coverage"] = {
        "rounds": pr[["quarter", "round", "H", "published_eff", "date_type", "definition_A", "source",
                      "days_after_quarter_end"]].to_dict("records"),
        "median_days_after_quarter_end_verified": float(pr[pr["date_type"].str.startswith("verified")]["days_after_quarter_end"].median()),
        "notes": ["2026-Q1 and 2026-Q2 publication dates are unverified upper bounds (fetch time) - conservative for "
                  "eligibility, but the true release may be earlier",
                  "2025-Q2 and 2025-Q3 rounds are supplementary with definition_A = False and are excluded, leaving "
                  "two quarters without a label inside the evaluation window",
                  "2025-Q1 is a Stratbase-SWS commissioned survey published before the quarter ended",
                  "2021-Q2 and 2022-Q2 hold two rounds each; the label uses their mean and becomes usable only after "
                  "the second round's publication"]}

    # 6. Conclusions this target can and cannot support
    out["what_the_target_can_support"] = [
        "a regional (Balance Luzon) statement about whether self-rated hunger plus local food-price pressure is above "
        "its recent median, issued per province",
        "province-to-province differences only through the price term 2D (34-35% of the label variance)"]
    out["what_it_cannot_support"] = [
        "a measured provincial or municipal food-insecurity rate",
        "a horizon reliability claim under the C6 rule: no lead has >= 5 LOW rows (by lead: "
        + ", ".join(f"{k}: {int(r['LOW'])}" for k, r in bl.iterrows()) + ")",
        "five independent provincial evaluations per quarter"]
    out["what_would_be_needed"] = [
        "more quarters with LOW outcomes under the approved rule (each future quarter adds one regional date); at "
        "least 5 LOW and 8 dates per lead",
        "a provincial outcome measured with known sampling error: CBMS LGU FIES (O1) or NNS 2023 provincial FIES (O2)",
        "per-round Balance Luzon sample sizes (O5a) to quantify label noise exactly"]
    (EXP / "runs" / "e28_target_audit.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: (v if k not in ("publication_and_coverage", "class_balance") else "...") for k, v in out.items()},
                     indent=1, default=str)[:4000])
    print(json.dumps(out["class_balance"]["by_lead"]), out["class_balance"]["training_HIGH_share_lead1_mean"])


if __name__ == "__main__":
    main()
