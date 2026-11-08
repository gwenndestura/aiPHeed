"""E120 deliverable tables from the e120.py outputs and the framework definitions (no new scoring).

    python reports.py    (after e120.py)
"""
from __future__ import annotations

import pandas as pd

import e120 as E

ROOT, OUT, P = E.ROOT, E.OUT, E.P

SOURCE = {"D01": "PSA OpenSTAT CPI by province (E40)", "D02": "PSA OpenSTAT CPI by province (E40)", "D03": "PSA OpenSTAT CPI Region IV-A index (E114)",
          "D05": "PSA wholesale rice (E107)", "D07": "PSA farmgate prices (E118)", "D08": "PSA retail prices (E118)", "D09": "PSA retail prices (E118)",
          "D10": "PSA retail prices (E118)", "D20": "PSA palay and corn production (E118)", "D21": "PSA palay and corn production (E118)",
          "D22": "PSA vegetables and root crops production (E118)", "D23": "PSA vegetables and root crops production (E118)", "D24": "PSA fisheries production (E118)",
          "D26": "PSA chicken production (E118)", "D27": "PSA livestock production (E118)", "D33": "IBTrACS (corrected pipeline)", "D34": "IBTrACS (E114)",
          "D36": "NASA POWER (E118), derived", "D37": "NASA POWER (E118), derived", "D40": "PSA LFS (E114)", "D41": "PSA provincial LFS tables (owner file, E116)",
          "D42": "BSP via dated reports (corrected pipeline)", "D50": "PSA SAE 2021 (lgu_vulnerability.csv)", "D60": "aiPHeed news corpus (FSSI-v3)", "D62": "GDELT DOC (E114)"}
UNIT = {"pct": "% YoY", "rank5": "rate %"}
AVAIL = {"D01": "day 10 of m+1 (archived release where verified; quarters rule-based)", "D02": "day 10 of m+1", "D03": "day 10 of m+1",
         "D05": "start of q+2 (rule)", "D07": "day 15 of m+1 (rule)", "D08": "day 15 of m+1 (rule)", "D09": "day 15 of m+1 (rule)", "D10": "day 15 of m+1 (rule)",
         "D20": "start of q+2 (rule)", "D21": "start of q+2 (rule)", "D22": "start of q+2 (rule)", "D23": "start of q+2 (rule)", "D24": "start of q+2 (rule)",
         "D26": "start of q+2 (rule)", "D27": "start of q+2 (rule)", "D33": "start of q+1 (verified)", "D34": "start of q+1 (verified)",
         "D36": "first day of m+2 (rule; values may be revised)", "D37": "first day of m+2 (rule)", "D40": "first day of m+3 (rule)",
         "D41": "30 June of Y+1 (rule; no dates in file)", "D42": "first dated report (11% verified)", "D50": "2025-07-01 (V1 rule)", "D60": "start of q+1 (dated articles)",
         "D62": "start of q+1 (dated articles)"}


def ml_role(f) -> tuple[str, str]:
    if f.scope == "R":
        return ("regional forecasting predictor (candidate)",
                "regional / national series, as-of, no target information; the regional SWS model may use it (small n: pre-register a short list)")
    if f.normalization == "rank5":
        return ("provincial vulnerability profiling", "annual / static, provincial; no provincial label to train on")
    return ("provincial vulnerability profiling", "provincial series; the regional model uses its Region IV-A counterpart, never a provincial copy")


def main():
    FEAT = E.FEAT
    rows = []
    for f in FEAT.itertuples():
        mr, why = ml_role(f)
        rows.append({"feature": f.feature, "indicator": f.indicator, "indicator_name": E.INDICATORS[f.indicator], "component": f.component,
                     "definition": f.note, "series": f.series, "dataset_id": f.dataset_id, "source": SOURCE.get(f.dataset_id, ""),
                     "geographic_scope": "province (5)" if f.scope == "P" else f.series_unit, "frequency": "annual (latest published year)" if f.normalization == "rank5" else "quarterly (monthly -> 3-month mean where monthly)",
                     "unit": UNIT[f.normalization] if f.normalization == "rank5" else ("mm (absolute departure)" if f.transform == "abs" else "count" if "cyclones" in f.feature else
                                                                                       "degC" if "heat" in f.feature else "index" if "fssi" in f.feature or "news" in f.feature else "% YoY" if "decline" not in f.feature and "change" not in f.feature else "pp" if "change" in f.feature else "% (minus YoY)"),
                     "calculation": ("|x|" if f.transform == "abs" else "x") + (" x (-1)" if f.direction < 0 else "") + " as of the issue (latest observed quarter with availability < issue, at most 3 quarters old)",
                     "direction": "higher = more risk" if f.direction > 0 else "lower = more risk (sign reversed before scoring)",
                     "normalization": "expanding-window mid-rank percentile among earlier available 2021+ observations of the same feature (pooled over the scope's units); >= 8 earlier values" if f.normalization == "pct"
                                      else "mid-rank among the five provinces for the latest published year: (rank - 0.5) / 5",
                     "missing_handling": "missing / stale / insufficient history -> not scored (never 0, never filled)",
                     "availability_rule": AVAIL.get(f.dataset_id, ""), "firi_role": f"scored in the {'provincial' if f.scope == 'P' else 'regional'} FIRI", "ml_role": mr})
    for (code, ind, comp, sc, series, did, role, why) in E.NOT_SCORED:
        rows.append({"feature": code, "indicator": ind, "indicator_name": E.INDICATORS.get(ind, ind), "component": comp, "definition": why, "series": series,
                     "dataset_id": did, "source": "", "geographic_scope": "province (5)" if sc == "P" else "regional / national", "frequency": "", "unit": "",
                     "calculation": "not scored", "direction": "", "normalization": "", "missing_handling": "", "availability_rule": "",
                     "firi_role": {"profile": "provincial profile only (not scored)", "context": "context only", "alternative": "alternative / sensitivity series (not scored)",
                                   "target": "outside the FIRI (forecasting target)", "excluded": "excluded"}[role],
                     "ml_role": {"target": "regional forecasting target (its lagged readings may be predictors)", "excluded": "excluded"}.get(role,
                                "regional predictor candidate only if pre-registered" if sc == "R" and role == "alternative" else "profiling / context")})
    D = pd.DataFrame(rows)
    D.to_csv(ROOT / "E120_FEATURE_DICTIONARY.csv", index=False, lineterminator="\n")

    # dataset -> indicator (all 54 E119-R2 datasets)
    inv = pd.read_csv(E.EXP / "E119R2_Indicator_Framework_Redesign" / "E119R2_COMPLETE_DATASET_INVENTORY.csv")
    to6 = {"FP": "FMA", "PS": "AFP", "CH": "CEC", "HI": "EHS", "SV": "PSV", "NS": "FIS", "EH": "outside FIRI (target / validation)"}
    used = D.assign(ids=D["dataset_id"].str.split("/")).explode("ids").groupby("ids").apply(
        lambda g: "; ".join(f"{a} ({b})" for a, b in zip(g["feature"], g["firi_role"])), include_groups=False)
    M = inv[["dataset_id", "dataset", "proposed_indicator", "component", "original_firi", "geography", "frequency", "role", "reason"]].copy()
    M["e120_indicator"] = M["proposed_indicator"].map(to6)
    M["e120_features"] = M["dataset_id"].map(used).fillna("not used as a feature (see role)")
    M = M.rename(columns={"proposed_indicator": "e119r2_indicator", "role": "e119r2_role"})
    M.to_csv(ROOT / "E120_DATASET_TO_INDICATOR_MAPPING.csv", index=False, lineterminator="\n")

    # geography and time per scored feature
    S1 = pd.read_csv(OUT / "level1_feature_scores.csv")
    g = []
    for f in FEAT.itertuples():
        s = S1[S1["feature"] == f.feature]
        sc = s[s["score"].notna()]
        g.append({"feature": f.feature, "indicator": f.indicator, "scope": "provincial" if f.scope == "P" else "regional",
                  "units": "; ".join(sorted(s["unit"].unique())), "source_resolution": "province" if f.scope == "P" else f.series_unit,
                  "national_value_copied_to_provinces": False if f.scope == "R" or f.series_unit is None else True,
                  "frequency": "annual" if f.normalization == "rank5" else "quarterly", "first_scored_origin": sc["origin"].min() if len(sc) else "",
                  "last_scored_origin": sc["origin"].max() if len(sc) else "", "scored_unit_origins": int(len(sc)), "possible_unit_origins": int(len(s)),
                  "earliest_observation_used": s["period"].dropna().min() if s["period"].notna().any() else "",
                  "statuses": "; ".join(f"{k}: {v}" for k, v in s["status"].value_counts().items())})
    G = pd.DataFrame(g)
    G.to_csv(ROOT / "E120_GEOGRAPHIC_AND_TEMPORAL_VALIDATION.csv", index=False, lineterminator="\n")

    cov = pd.read_csv(OUT / "indicator_coverage.csv")
    fc = pd.read_csv(OUT / "feature_coverage.csv")
    fc = fc.merge(FEAT[["feature", "indicator", "component"]], on="feature")
    rep = pd.concat([cov.assign(level="indicator"), fc.rename(columns={"rows": "unit_origins_possible", "scored": "available", "scored_pct": "available_pct"})
                     .assign(level="feature", name=lambda d: d["feature"])], ignore_index=True)
    rep[["level", "scope", "indicator", "name", "component", "unit_origins_possible", "available", "available_pct", "first_available", "provinces_with_any", "statuses"]].to_csv(
        ROOT / "E120_FIRI_COVERAGE_REPORT.csv", index=False, lineterminator="\n")

    el = D[["feature", "indicator", "component", "geographic_scope", "frequency", "firi_role", "ml_role"]].copy()
    ind_rows = [{"feature": f"{i} indicator score ({sc})", "indicator": i, "component": "all", "geographic_scope": sc, "frequency": "quarterly",
                 "firi_role": "Level 2 score", "ml_role": ("regional forecasting predictor (candidate): built only from as-of features and earlier values, no target"
                                                          if sc == "regional" else "provincial vulnerability profiling (no provincial label)")}
                for i in E.INDICATORS for sc in ("regional", "provincial") if not (i == "PSV" and sc == "regional")]
    ind_rows += [{"feature": "overall FIRI (regional)", "indicator": "FIRI", "component": "all", "geographic_scope": "regional", "frequency": "quarterly",
                  "firi_role": "Level 3", "ml_role": "eligible as one summary predictor (no SWS input, equal weights, no target-derived weights); not alongside its own indicators"},
                 {"feature": "overall FIRI (provincial)", "indicator": "FIRI", "component": "all", "geographic_scope": "province (5)", "frequency": "quarterly",
                  "firi_role": "Level 3", "ml_role": "provincial vulnerability profiling (no provincial label)"},
                 {"feature": "served FIRI v2", "indicator": "FIRI v2", "component": "all", "geographic_scope": "province", "frequency": "quarterly",
                  "firi_role": "legacy", "ml_role": "excluded as a predictor: contains H1 (regional hunger) and SWS-derived walk-forward weights"}]
    pd.concat([el, pd.DataFrame(ind_rows)]).to_csv(ROOT / "E120_MODEL_FEATURE_ELIGIBILITY.csv", index=False, lineterminator="\n")
    print(len(D), len(M), M["e120_indicator"].value_counts().to_dict(), len(G))


if __name__ == "__main__":
    main()
