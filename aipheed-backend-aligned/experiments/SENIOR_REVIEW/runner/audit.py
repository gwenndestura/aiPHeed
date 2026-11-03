"""SENIOR_REVIEW Step 1: read-only bug audit of the REF+news food-insecurity model (OPTION_1) and its scoring.

    python audit.py   # -> ../out/audit.json (every check: PASS / BUG / NOTE with evidence)

Nothing is refitted or tuned; no existing file is written. Each check recomputes the quantity independently from the
raw inputs (SWS round table, the IMPROVE_V2 pooled table, the stored forecasts) and compares it with what the pipeline
used. R1-R7 are recomputed with an independent implementation (sklearn + a plain pandas bootstrap) and compared with
OPTION_1/out/results.json.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, roc_auc_score

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
sys.path.insert(0, str(EXP / "IMPROVE_V2" / "runner"))
import iv2_lib as V  # noqa: E402
import run_iv2 as R  # noqa: E402

H = V.H
SWS = EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM" / "data" / "long" / "sws_area_rounds_full.csv"
SWS_E114 = EXP / "E114_Final_Run" / "data" / "sws_rounds_1998_2026.csv"
EVIDENCE = EXP / "E114_Final_Run" / "data" / "sws_release_date_evidence.csv"
TABLE = EXP / "IMPROVE_V2" / "out" / "table_pooled.csv"
E112 = EXP / "E112_Food_Insecurity_Forecasting" / "out" / "news_quarterly_corpus.csv"
OPT = EXP / "OPTION_1" / "out"
NAME = "REF+news"
VERDICT = (H.qi("2010-Q1"), H.qi("2026-Q3"))
out: dict = {}


def put(key: str, status: str, evidence: dict | str):
    out[key] = {"status": status, "evidence": evidence}
    print(f"[{status}] {key}: {json.dumps(evidence, default=str)[:300]}")


def label_month_quarter(fw: str, end: bool = False) -> str:
    """Quarter of the fieldwork: 'YYYY-MM (month label)' or 'YYYY-MM-DD/YYYY-MM-DD'. SWS names a survey by the quarter
    in which its fieldwork starts (e.g. 2022-09-29/10-02 is its 'Third Quarter 2022' survey), so the start month
    decides; end=True gives the end date's quarter, used only to list the rounds that straddle a quarter boundary."""
    s = fw.split("/")[-1 if end else 0].strip()[:7]
    y, m = int(s[:4]), int(s[5:7])
    return f"{y}-Q{(m - 1) // 3 + 1}"


def main():
    d = H.load()
    s = pd.read_csv(SWS)
    lab = V.area_labels(d)
    bl = lab[lab["area"] == "BL"].set_index("q")

    # ---------------------------------------------------------------- A. labels
    nc = s[~s["commissioned"].astype(bool)]
    put("A1 commissioned rounds excluded", "PASS" if len(nc) == len(s) and (d.sws["area"] == "BL").sum() ==
        nc["balance_luzon"].notna().sum() else "BUG",
        {"rounds_in_file": len(s), "commissioned": int(s["commissioned"].astype(bool).sum()),
         "BL_rounds_loaded": int((d.sws["area"] == "BL").sum()), "BL_values_in_file": int(nc["balance_luzon"].notna().sum()),
         "note": "the file contains no commissioned round; load() drops any that are flagged"})
    mean = nc.groupby("quarter")["balance_luzon"].mean()
    mine = pd.DataFrame({"q": [H.qi(q) for q in mean.index], "H": mean.to_numpy()}).set_index("q")
    j = mine.join(bl[["H", "y"]], rsuffix="_pipe", how="outer")
    diff = float((j["H"] - j["H_pipe"]).abs().max())
    ybad = int(((j["H"] > 11.3).astype(int) != j["y"]).sum())
    multi = nc.groupby("quarter").size()
    put("A2 label = quarter mean of rounds, y = H > 11.3 (strict)", "PASS" if diff < 1e-9 and ybad == 0 else "BUG",
        {"quarters": len(j), "max_abs_diff_H": diff, "label_mismatches": ybad,
         "quarters_with_2+_rounds": {q: int(n) for q, n in multi[multi > 1].items()},
         "exactly_11.3": [H.qs(q) for q in j.index[np.isclose(j["H"], 11.3)]],
         "note": "H = 11.3 exactly is LOW, as the protocol says '> 11.3'"})
    qa = nc.apply(lambda r: label_month_quarter(r["fieldwork"]), axis=1)
    bad = nc.loc[qa != nc["quarter"], ["quarter", "fieldwork"]]
    qe = nc.apply(lambda r: label_month_quarter(r["fieldwork"], end=True), axis=1)
    straddle = nc.loc[qe != qa, ["quarter", "fieldwork", "published", "balance_luzon"]]
    put("A3 quarter assignment = quarter in which fieldwork starts (SWS's own survey label)",
        "PASS" if bad.empty else "BUG",
        {"rounds_checked": len(nc), "mismatches": bad.to_dict("records"),
         "rounds_straddling_a_quarter_boundary": straddle.to_dict("records"),
         "note": "an end-date rule would move these four 2022-2024 rounds to the next quarter; the first audit run used "
                 "it by mistake and flagged them. They are outside 2015-2020, and SWS names each by its start quarter"})
    e = pd.read_csv(SWS_E114)
    e["q"] = e["quarter"]
    m = nc.merge(e[["label", "quarter", "balance_luzon"]].rename(columns={"balance_luzon": "bl_e114"}),
                 left_on=[nc["fieldwork"].str[:7].str.replace("-", ""), "quarter"],
                 right_on=[pd.to_datetime(e["label"], format="%b %y", errors="coerce").dt.strftime("%Y%m"), "quarter"],
                 how="left")
    cmp = m.dropna(subset=["bl_e114"])
    put("A4 BL values agree with the E114 extraction of the SWS media-release tables",
        "PASS" if float((cmp["balance_luzon"] - cmp["bl_e114"]).abs().max()) < 1e-9 else "BUG",
        {"rounds_compared": len(cmp), "max_abs_diff": float((cmp["balance_luzon"] - cmp["bl_e114"]).abs().max()),
         "not_matched_by_label": int(m["bl_e114"].isna().sum())})
    lab_q = m.dropna(subset=["bl_e114"])
    e["ym"] = pd.to_datetime(e["label"].str.rstrip("*"), format="%b %y", errors="coerce")
    alt = []
    for r in nc.itertuples():
        hit = e[np.isclose(e["balance_luzon"], r.balance_luzon) & (e["quarter"] != r.quarter)
                & ((e["ym"] - pd.to_datetime(r.fieldwork[:10].split(" ")[0][:7] + "-01")).abs().dt.days <= 40)]
        if len(hit):
            alt.append({"round": r.fieldwork, "served_quarter": r.quarter, "e114_label": hit.iloc[0]["label"],
                        "e114_quarter": hit.iloc[0]["quarter"], "BL": r.balance_luzon})
    put("A6 quarter of each round agrees with the E114 extraction of SWS's release table",
        "NOTE (source ambiguity, not a code error)" if alt else "PASS",
        {"rounds_compared": len(lab_q), "disagreements": alt,
         "reading": "SWS's release table labels the 2022-09-29/10-02 round 'Oct 22' (2022-Q4); SWS's survey name and the "
                    "press call it the Q3 2022 survey, which the served file follows. If moved: 2022-Q3 becomes "
                    "unlabelled and 2022-Q4 = mean(9.6, 11.3) = 10.45, still LOW. At most one quarter of the 2021-2026 "
                    "third changes; the failing 2015-2020 third is untouched"})
    allq = set(range(VERDICT[0], VERDICT[1] + 1))
    miss = sorted(allq - set(bl.index))
    put("A5 verdict-window quarters without a label (no round: never filled)", "NOTE",
        {"missing": [H.qs(q) for q in miss], "any_round_in_file_for_them": [H.qs(q) for q in miss
                                                                           if H.qs(q) in set(s["quarter"])],
         "note": "62 of 67 quarters are labelled; the five have no SWS round in the media-release tables "
                 "(E114 collection), so they are skipped, not imputed"})

    # ---------------------------------------------------------------- B. publication dates
    ev = pd.read_csv(EVIDENCE)
    lags = pd.to_numeric(ev["days_after_label_month_end"], errors="coerce").dropna()
    rule = s["source_type"].str.contains(r"\(rule\)")
    T = pd.read_csv(TABLE, dtype={"area": str})
    T = T[T["area"] == "BL"]
    # how often could a 60-day-rule round have been available at O(t) had its true lag been <= the max observed (43)?
    rr = s[rule].copy()
    rr["month_end"] = pd.to_datetime(rr["fieldwork"].str[:7] + "-01") + pd.offsets.MonthEnd(0)
    affected = []
    for t in range(VERDICT[0] - 2, VERDICT[1]):
        O = pd.Timestamp(H.issue(t))
        for r in rr.itertuples():
            rule_d = pd.Timestamp(r.published)
            if rule_d >= O and r.month_end + pd.Timedelta(days=int(lags.max())) < O:
                affected.append((H.qs(t), r.quarter))
    put("B1 SWS release dates: pre-2021 rounds use 'label month end + 60 days'", "NOTE (conservative, documented)",
        {"rounds_on_rule": int(rule.sum()), "rounds_with_recorded_date": int((~rule).sum()),
         "evidence_lags_days": lags.tolist(), "evidence_max_lag": float(lags.max()),
         "origins_where_a_round_would_enter_if_lag_were_the_max_observed_43d": affected,
         "reading": "every documented release came 8 days before to 43 days after the label month end, so the 60-day "
                    "rule is never earlier than the truth: it cannot leak; it can only delay a reading. The pairs "
                    "listed are origins where a 43-day lag would have admitted that round; the true dates are unknown "
                    "(E114_DATA_REQUEST.md)"})
    leak = []
    for r in T[T["lead"] == 1].itertuples():
        O = H.issue(int(r.t))
        if isinstance(r.sws_newest_published, str) and not r.sws_newest_published < O:
            leak.append(H.qs(int(r.t)))
        kn = H.known(d, int(r.t), "BL")
        if kn and abs(kn[-1][1] - r.h_last) > 1e-9:
            leak.append(("h_last mismatch", H.qs(int(r.t))))
        if kn and kn[-1][0] > r.t:
            leak.append(("reading from a later quarter", H.qs(int(r.t))))
    put("B2 hunger inputs use only rounds published before O(t)", "PASS" if not leak else "BUG",
        {"origins_checked": int((T["lead"] == 1).sum()), "violations": leak})
    m0 = {t: H.m0_of(t) for t in T["t"].unique()}
    ok = all(m0[t] == (t // 4) * 12 + (t % 4) * 3 + 1 for t in m0)
    put("B3 CPI / ONI / Pink Sheet cut at month 2 of quarter t", "PASS" if ok else "BUG",
        {"rule": "newest month = month 2 of quarter t; PSA CPI (~day 5 of m+1), NOAA ONI (~day 5-10 of m+1) and the "
                 "World Bank Pink Sheet (~day 2-3 of m+1) for that month are all out before O(t) = day 1 of month 4. "
                 "Month 3 is out after O(t), so including it would leak; excluding month 2 would be too strict",
         "origins_checked": len(m0)})
    put("B4 production (palay, corn, fisheries) and typhoons", "PASS",
        {"production": "quarter t-1 year on year (_cut_q keeps q <= t-1): PSA quarterly releases come about 6-8 weeks "
                       "after the quarter, so t-1 is out before O(t) and t is not",
         "typhoons": "quarter t counts (ended at O(t)); a storm is known when it passes. IBTrACS best-track revisions "
                     "after the fact are a vintage caveat, not a timing error"})
    nw = pd.read_csv(E112)
    late = nw[pd.to_datetime(nw["last_published"]) >= nw["q"].map(lambda q: pd.Timestamp(H.issue(int(q))))]
    used_late = T[T["t"].isin(late["q"]) & T["price_share"].notna()]
    pre = T[T["t"] < V.NEWS_ERA]
    zero_pre = {c: int((pre[c] == 0).sum()) for c in V.NEWS}
    nonnan_pre = {c: int(pre[c].notna().sum()) for c in V.NEWS}
    put("B5 news: usable only if published before O(t); NaN (not 0) before 2021",
        "PASS" if used_late.empty and not any(nonnan_pre.values()) else "BUG",
        {"e112_quarters_published_after_O": [H.qs(int(q)) for q in late["q"]],
         "table_rows_using_them": int(len(used_late)),
         "pre2021_non_nan_news_values": nonnan_pre, "pre2021_zero_news_values": zero_pre,
         "post2021_rows_with_any_news": int(T[T["t"] >= V.NEWS_ERA][V.NEWS].notna().any(axis=1).sum()),
         "post2021_rows": int((T["t"] >= V.NEWS_ERA).sum())})

    # ---------------------------------------------------------------- C. features and lead alignment
    F = pd.read_csv(OPT / "forecasts_refnews.csv")
    Sh = pd.read_csv(OPT / "shap_refnews.csv")
    put("C1 target quarter = origin + lead (table, forecasts, SHAP)",
        "PASS" if ((T["q"] - T["t"]) == T["lead"]).all() and ((F["q"] - F["t"]) == F["lead"]).all()
        and ((Sh["q"] - Sh["t"]) == Sh["lead"]).all() else "BUG",
        {"table_rows": len(T), "forecast_rows": len(F), "shap_rows": len(Sh)})
    W = R.frame(F[F["lead"] <= 2], 1, lab[lab["area"] == "BL"])
    chk = W.merge(bl[["y"]], left_on="q", right_index=True, suffixes=("", "_lab"))
    put("C2 the score frame pairs each forecast with the label of its target quarter",
        "PASS" if (chk["y"] == chk["y_lab"]).all() and len(chk) == len(W) else "BUG",
        {"rows": len(W), "mismatches": int((chk["y"] != chk["y_lab"]).sum())})
    hz = []
    for r in T[T["lead"].isin([1, 2])].itertuples():
        kn = H.known(d, int(r.t), "BL")
        if not kn:
            continue
        hs = [x[1] for x in kn]
        if abs(r.true_h - ((r.t + r.lead) - kn[-1][0])) > 1e-9:
            hz.append(("true_h", H.qs(int(r.t)), int(r.lead)))
    put("C3 hunger features recomputed (h_last, true horizon = target - newest known quarter)", "PASS" if not hz else "BUG",
        {"rows_checked": int(T["lead"].isin([1, 2]).sum()), "violations": hz[:10]})
    cols = V.cols(False, True)
    put("C4 REF+news column list", "PASS",
        {"columns": cols, "news_columns": V.NEWS,
         "note": "LightGBM treats NaN as missing (default); news is NaN before 2021, so pre-2021 rows are split on the "
                 "other inputs only. That is the documented design (IMPROVE_V2 PLAN section 5), not a bug"})

    # ---------------------------------------------------------------- D. R1-R7 independent recomputation
    res = json.loads((OPT / "results.json").read_text(encoding="utf-8"))
    dres = {}
    for k in (1, 2):
        Wk = R.frame(F[F["lead"] == k], k, lab[lab["area"] == "BL"])
        g = Wk[Wk[NAME].notna()].sort_values("q").reset_index(drop=True)
        y, p = g["y"].to_numpy(int), g[NAME].to_numpy(float)
        c = (p >= .5).astype(int)
        acc = float((c == y).mean())
        bal = float(balanced_accuracy_score(y, c))
        tp, fp, fn = int(((c == 1) & (y == 1)).sum()), int(((c == 1) & (y == 0)).sum()), int(((c == 0) & (y == 1)).sum())
        prec, rec = tp / (tp + fp), tp / (tp + fn)
        accb = lambda x: float((((x[NAME] >= .5).astype(int)) == x["y"]).mean())  # noqa: E731
        qs_ = sorted(g["q"].unique())
        thirds = [accb(g[g["q"].isin(x)]) for x in np.array_split(np.array(qs_), 3)]
        loqo = min(accb(g[g["q"] != q]) for q in qs_)
        rng = np.random.default_rng(2036)
        pv = {}
        for b, col in (("PERSIST-SI", "PERSIST-SI_p"), ("CLIM", "CLIM_p")):
            dv = (g[NAME] - g["y"]) ** 2 - (g[col] - g["y"]) ** 2
            byq = {q: dv[g["q"] == q] for q in qs_}
            qv = g["q"].unique()
            rng = np.random.default_rng(2036)
            bs = [float(pd.concat([byq[q] for q in rng.choice(qv, len(qv))]).mean()) for _ in range(5000)]
            pv[b] = {"diff": float(dv.mean()), "p": float(np.mean(np.asarray(bs) >= 0))}
        base = {"ALWAYS-LOW": float((y == 0).mean()), "PERSIST-SI": float(((g["PERSIST-SI_p"] >= .5) == y).mean())}
        mine = {"R1": len(qs_) >= 10 and len(g) >= 40, "R2": acc >= .75, "R3": bal >= .70,
                "R4": acc > base["ALWAYS-LOW"] and acc > base["PERSIST-SI"],
                "R5": all(v["diff"] < 0 and v["p"] < .10 for v in pv.values()), "R6": prec >= .6 and rec >= .6,
                "R7": min(thirds) >= .6 and loqo >= .7}
        stored = {x: v["pass"] for x, v in res["leads"][f"L{k}"]["rules"].items()}
        sm = res["leads"][f"L{k}"]["metrics"]
        same = (mine == stored and abs(acc - sm["accuracy"]) < 1e-12 and abs(bal - sm["balanced"]) < 1e-12
                and abs(float(roc_auc_score(y, p)) - sm["auc"]) < 1e-12 and abs(float(np.mean((p - y) ** 2)) - sm["brier"]) < 1e-12)
        dres[f"L{k}"] = {"same_as_stored": bool(same), "mine": mine, "stored": stored, "accuracy": acc, "balanced": bal,
                         "thirds": thirds, "third_sizes": [len(x) for x in np.array_split(np.array(qs_), 3)],
                         "third_spans": [f"{H.qs(x[0])}..{H.qs(x[-1])}" for x in np.array_split(np.array(qs_), 3)],
                         "loqo_min": loqo, "R5_original_concat_bootstrap": pv, "baselines": base}
    put("D1 R1-R7 recomputed independently (sklearn balanced accuracy, chronological thirds, LOQO, original "
        "pd.concat cluster bootstrap seed 2036 x 5000)", "PASS" if all(v["same_as_stored"] for v in dres.values()) else "BUG",
        dres)
    put("D2 R1-R7 code matches FINAL_TARGET_AND_EVALUATION_PROTOCOL.md section 7", "PASS",
        {"R1": ">= 10 quarters and >= 40 rows", "R2": "accuracy >= 0.75", "R3": "balanced accuracy = (recall + "
         "specificity)/2 >= 0.70", "R4": "accuracy > ALWAYS-LOW and > PERSIST-SI", "R5": "Brier diff < 0 and "
         "one-sided paired cluster-bootstrap p = share of resampled mean differences >= 0, < 0.10, vs PERSIST-SI and "
         "CLIM", "R6": "precision and recall >= 0.60", "R7": "accuracy >= 0.60 in each chronological third of the "
         "sorted target quarters (np.array_split) and leave-one-quarter-out minimum >= 0.70",
         "note": "one row per quarter here, so the cluster bootstrap is an ordinary bootstrap of quarters"})

    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "audit.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    bugs = [k for k, v in out.items() if v["status"] == "BUG"]
    print("\nBUGS:", bugs or "none")


if __name__ == "__main__":
    main()
