"""E120 checks: every FIRI v2 indicator and dataset accounted for, every feature assigned with direction and method,
geography and the 2021+ window preserved, no SWS in the index, scores reproducible, nothing trained or changed.

    python validate.py    (after e120.py and reports.py)
"""
from __future__ import annotations

import subprocess

import numpy as np
import pandas as pd

import e120 as E

ROOT, OUT, P, FI = E.ROOT, E.OUT, E.P, E.FI


def checks() -> list[dict]:
    res = []

    def ok(name, cond, detail=""):
        res.append({"check": name, "result": "PASS" if cond else "FAIL", "detail": detail})

    D = pd.read_csv(ROOT / "E120_FEATURE_DICTIONARY.csv")
    M = pd.read_csv(ROOT / "E120_DATASET_TO_INDICATOR_MAPPING.csv")
    S1 = pd.read_csv(OUT / "level1_feature_scores.csv")
    W = pd.read_csv(OUT / "level3_firi_equal.csv")
    rev = pd.read_csv(E.EXP / "E119R2_Indicator_Framework_Redesign" / "E119R2_EXISTING_12_INDICATOR_REVIEW.csv")
    ok("all 12 FIRI v2 indicators evaluated (E119-R2 review) and placed", set(rev["indicator"]) == set(FI.LABELS))
    ok("all 54 E119-R2 datasets mapped to an E120 indicator or outside-FIRI role", len(M) == 54 and M["e120_indicator"].notna().all())
    ok("every feature has an indicator, direction or not-scored role, and a FIRI and ML role",
       D["indicator"].notna().all() and D["firi_role"].notna().all() and D["ml_role"].notna().all()
       and D.loc[D["calculation"] != "not scored", "direction"].str.len().gt(0).all(), f"{len(D)} features")
    ok("scored features are exactly the e120 definitions", set(D.loc[D["calculation"] != "not scored", "feature"]) == set(E.FEAT["feature"]))
    ok("SWS hunger is not a FIRI input", not E.FEAT["series"].str.contains("hunger|sws|H1_", case=False).any())
    ok("no FIRI v2 model output (A1) or FIRI v2 score among inputs", not E.FEAT["series"].str.contains("p_price|FIRI", case=False).any())
    ok("weights are equal (no SWS-derived weights)", "evidence" not in (ROOT / "runner" / "e120.py").read_text(encoding="utf-8").split("def firi(")[1].split("def compare(")[0])
    # geography
    prov = S1[S1["scope"] == "provincial"]
    ok("provincial units are exactly the five provinces", set(prov["unit"]) == set(P.PROVS))
    ok("provincial features use provincial series only", E.FEAT.loc[E.FEAT["scope"] == "P", "series_unit"].isna().all())
    ok("regional features use regional / national units only", set(E.FEAT.loc[E.FEAT["scope"] == "R", "series_unit"]) <=
       {"Region IV-A", "CALABARZON (mean of 5 province points)", "PHILIPPINES"})
    nat = E.FEAT[E.FEAT["series_unit"].isin(["PHILIPPINES"])]["feature"]
    ok("no national value appears in a provincial score", not prov["feature"].isin(nat).any())
    # time
    per = S1["period"].dropna().astype(str)
    q = per[per.str.fullmatch(r"\d{4}-Q[1-4]")]
    ok("no observation before 2021 in any scored value", bool((q.str[:4].astype(int) >= 2021).all()) and bool((per[~per.isin(q)].str[:4].astype(int) >= 2021).all()))
    dyn = S1[S1["score"].notna() & S1["period"].astype(str).str.fullmatch(r"\d{4}-Q[1-4]")]
    ok("every scored dynamic value was observed before its origin ended", bool((dyn["period"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1) <= dyn["t"]).all()))
    stale = dyn["t"] - dyn["period"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    ok("no scored value older than 3 quarters", bool((stale <= E.MAX_STALE).all()), f"max {int(stale.max())}")
    ok("missing never scored as 0 or filled", bool(S1.loc[S1["status"].isin(["missing", "stale", "insufficient_history", "unavailable_at_issue"]), "score"].isna().all()))
    ok("scores within [0, 1]", bool(S1["score"].dropna().between(0, 1).all()) and bool(W["firi"].dropna().between(0, 1).all()))
    # completeness rule and reproducibility
    ok("FIRI only where >= 2/3 of indicators available", bool((W.loc[W["firi"].notna(), "indicators_available"] >=
                                                               np.ceil(2 / 3 * W.loc[W["firi"].notna(), "indicators_total"])).all()))
    L, ann = E.load()
    again = E.firi(E.indicator_scores(E.level1(L, ann)))
    m = W.merge(again, on=["scope", "unit", "t"], suffixes=("", "_r"))
    ok("FIRI reproduces exactly from the inputs", bool(np.allclose(m["firi"].fillna(-1), m["firi_r"].fillna(-1), atol=1e-9)), f"{len(m)} rows")
    # nothing changed
    diff = subprocess.run(["git", "status", "--porcelain", "--", "backend/app", "frontend/src", "backend/data",
                           "aipheed-backend-aligned/experiments/E118_FAO_Data_Discovery", "aipheed-backend-aligned/experiments/E119_Preprocessing",
                           "aipheed-backend-aligned/experiments/E119R2_Indicator_Framework_Redesign"], cwd=E.REPO, capture_output=True, text=True).stdout.strip()
    ok("firi.py, production code, dashboard, data, E118, E119 and E119-R2 unchanged", diff == "", diff[:200])
    src = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "runner").glob("*.py") if p.name != "validate.py")
    ok("no model fitted in this phase", not any(t in src for t in ("lightgbm", "LGBM", ".fit(", "sklearn")))
    return res


if __name__ == "__main__":
    r = checks()
    pd.DataFrame(r).to_csv(OUT / "validation_results.csv", index=False, lineterminator="\n")
    for x in r:
        print(x["result"], x["check"], "|", x["detail"])
    assert all(x["result"] == "PASS" for x in r)
