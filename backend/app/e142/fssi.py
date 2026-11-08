"""
FSSI v2 for the FI6-N publisher archive (CALABARZON provinces), separating news ATTENTION from news COMPOSITION, with
every baseline computed from earlier quarters only (as-of, no look-ahead).

    python -m app.e142.fssi     -> data/e142/out/fssi_v2_province_quarter.csv, fssi_v2_validity.json

For province p and quarter t, with n = articles mentioning p, r = de-duplicated food-stress events (FI6-N event_id):
    p0(p, t)     as-of baseline rate: (sum r over quarters < t + k x regional prior rate) / (sum n over quarters < t + k)
    share_eb     (r + k x p0) / (n + k)                         empirical-Bayes shrinkage of thin cells, k = 10
    composition  logit(share_eb) - logit(p0)                    food-stress share relative to the province's own past;
                                                               under no change its expectation is ~0 for any n
    attention    log(1 + n) - mean of log(1 + n) over the province's earlier quarters
FSSI_v2 = composition. Attention is reported separately: more coverage is not evidence of food stress by itself.

Validity tests (descriptive; no forecasting claim):
    T1 volume dependence: Spearman(FSSI, articles) for raw share, FI6-N corrected share, FSSI_v2
    T2 stability: mean and SD of FSSI_v2 within article-volume terciles
    T3 convergent validity retained: Spearman(FSSI_v2, cyclones within 150 km that quarter), one-sided
    T4 coverage: province-quarters with articles, outlet concentration (from the FI6-N audit)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from app.e140.nlp_validity import CAL, cyclones, test
from app.e142 import OUT
from app.paths import BACKEND_DIR

K = 10.0
SRC = BACKEND_DIR / "data" / "fi6" / "news_archive"


def _logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def build() -> pd.DataFrame:
    a = pd.read_csv(SRC / "fssi_archive_province_quarter.csv")
    a = a[a["province"].isin(CAL)].sort_values(["province", "quarter"]).reset_index(drop=True)
    rows = []
    for q in sorted(a["quarter"].unique()):
        past = a[a["quarter"] < q]
        reg_prior = (past["risk_events"].sum() / past["articles"].sum()) if past["articles"].sum() > 0 else np.nan
        for p in CAL:
            cur = a[(a["quarter"] == q) & (a["province"] == p)]
            if cur.empty:
                continue
            n, r = int(cur["articles"].iloc[0]), int(cur["risk_events"].iloc[0])
            pp = past[past["province"] == p]
            if np.isnan(reg_prior) or pp["articles"].sum() == 0:
                rows.append({"province": p, "quarter": q, "articles": n, "risk_events": r, "p0": np.nan,
                             "fssi_v2": np.nan, "attention": np.nan})
                continue
            p0 = (pp["risk_events"].sum() + K * reg_prior) / (pp["articles"].sum() + K)
            share_eb = (r + K * p0) / (n + K)
            att = np.log1p(n) - np.log1p(pp["articles"]).mean()
            rows.append({"province": p, "quarter": q, "articles": n, "risk_events": r, "p0": p0,
                         "fssi_v2": float(_logit(share_eb) - _logit(p0)), "attention": float(att),
                         "risk_share_raw": cur["risk_share_raw"].iloc[0], "risk_share_fi6n": cur["risk_share_corrected"].iloc[0]})
    return pd.DataFrame(rows)


def validity(d: pd.DataFrame) -> dict:
    v = d[(d["articles"] > 0) & d["fssi_v2"].notna()].copy()
    v["tc"] = [cyclones(p, q) for p, q in zip(v["province"], v["quarter"])]
    v["tercile"] = pd.qcut(v["articles"].rank(method="first"), 3, labels=["low", "mid", "high"])
    audit = json.loads((SRC / "audit.json").read_text())
    return {
        "T1_volume_dependence": {"raw_share": test(v["articles"], v["risk_share_raw"]),
                                 "fi6n_shrunk_share": test(v["articles"], v["risk_share_fi6n"]),
                                 "fssi_v2": test(v["articles"], v["fssi_v2"]),
                                 "attention_vs_articles": test(v["articles"], v["attention"])},
        "T2_stability_by_volume_tercile": v.groupby("tercile", observed=True)["fssi_v2"].agg(["count", "mean", "std"]).round(4).reset_index().to_dict(orient="records"),
        "T3_convergent_validity": {"fssi_v2_vs_cyclones": test(v["tc"], v["fssi_v2"]),
                                   "attention_vs_cyclones": test(v["tc"], v["attention"]),
                                   "fi6n_shrunk_share_vs_cyclones": test(v["tc"], v["risk_share_fi6n"])},
        "T4_coverage": {"province_quarters": int(len(v)), "quarters": [v["quarter"].min(), v["quarter"].max()],
                        "outlets": audit.get("by_site"), "multi_source_events": audit.get("multi_source_events"),
                        "note": "one outlet supplies about 95 % of articles, so outlet bias cannot be corrected by re-weighting"},
        "not_established": ["sentiment classification accuracy (no human-labelled set; owner rule)",
                            "provincial forecasting contribution (no news outside CALABARZON for the training rounds; "
                            "8 measured CALABARZON rows cannot test it)"],
    }


def run() -> dict:
    d = build()
    OUT.mkdir(parents=True, exist_ok=True)
    d.to_csv(OUT / "fssi_v2_province_quarter.csv", index=False)
    res = validity(d)
    (OUT / "fssi_v2_validity.json").write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str))
