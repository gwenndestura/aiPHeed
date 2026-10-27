"""Score the blind news review (DASHBOARD_SELECTION/out/news_review_*), and a human second annotator when one exists.

Reference labels = the adjudicated single-AI review (news_review_reference.csv). Weighted v3 metrics re-weight the
stratified sample (10 relevant headlines per trigger + 40 not relevant) to the corpus counts of app.news.pipeline_v3.
If annotation/news_review_human.csv exists (same columns as the template, filled by a person who has not seen the
pipeline labels or the reference), it also reports Cohen's kappa human vs reference and the v3 metrics under the human
labels. Run from backend/:

    python ../aipheed-backend-aligned/experiments/FINAL_SYSTEM_SELECTION/runner/score_news.py    # out/news_scores.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.news import pipeline_v3 as P  # noqa: E402

HERE = Path(__file__).resolve().parent
DS = HERE.parents[1] / "DASHBOARD_SELECTION" / "out"
OUT = HERE.parent / "out"
ANN = HERE.parent / "annotation"
SEED = 2041


def kappa(a: pd.Series, b: pd.Series) -> float:
    a, b = a.astype(str).str.strip().str.upper(), b.astype(str).str.strip().str.upper()
    po = float((a == b).mean())
    cats = sorted(set(a) | set(b))
    pe = sum(float((a == c).mean()) * float((b == c).mean()) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def v3_weighted(m: pd.DataFrame, rel_col: str, counts: dict) -> dict:
    """Precision of v3's relevant flag (per trigger, weighted by corpus counts) and recall (relevant headlines the
    classifier rejected, estimated from the not-relevant stratum)."""
    v = m[m["source"] == "v3"]
    pos, neg = v[v["v3_relevant"] == 1], v[v["v3_relevant"] == 0]
    n_rel = sum(counts["relevant_by_trigger"].values())
    prec_t = {t: float((g[rel_col] == "Y").mean()) for t, g in pos.groupby("v3_trigger")}
    prec = sum(counts["relevant_by_trigger"][t] / n_rel * p for t, p in prec_t.items())
    miss_rate = float((neg[rel_col] == "Y").mean())
    tp, fn = n_rel * prec, counts["not_relevant"] * miss_rate
    rec = tp / (tp + fn) if tp + fn else float("nan")
    return {"precision": prec, "recall": rec, "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
            "precision_by_trigger": prec_t, "relevant_share_in_rejected": miss_rate,
            "sample": {"relevant": int(len(pos)), "not_relevant": int(len(neg))}}


def boot(m: pd.DataFrame, rel_col: str, counts: dict, draws: int = 2000) -> dict:
    rng = np.random.default_rng(SEED)
    v = m[m["source"] == "v3"]
    strata = [g for _, g in v.groupby(["v3_relevant", "v3_trigger"], dropna=False)]
    ps, rs = [], []
    for _ in range(draws):
        bs = pd.concat([g.sample(len(g), replace=True, random_state=int(rng.integers(1 << 31))) for g in strata])
        r = v3_weighted(bs, rel_col, counts)
        ps.append(r["precision"])
        rs.append(r["recall"])
    return {"precision_ci90": [float(np.quantile(ps, .05)), float(np.quantile(ps, .95))],
            "recall_ci90": [float(np.quantile(rs, .05)), float(np.quantile(rs, .95))]}


def main():
    c = pd.DataFrame(P.corpus())
    counts = {"relevant_by_trigger": c[c["relevant"] == 1]["trigger"].value_counts().to_dict(),
              "not_relevant": int((c["relevant"] == 0).sum()), "corpus": int(len(c))}
    key = pd.read_csv(DS / "news_review_key.csv")
    ref = pd.read_csv(DS / "news_review_reference.csv")
    p1 = pd.read_csv(DS / "news_review_pass1.csv")
    p2 = pd.read_csv(DS / "news_review_pass2.csv")
    m = key.merge(ref, on="id")
    disp = {P.norm_title(a["title"]) for a in P.admitted() if a.get("province_code")}
    m["displayed"] = m["title"].map(P.norm_title).isin(disp)
    out = {"counts": counts,
           "self_consistency_single_ai": {"kappa_relevant": kappa(p1.set_index("id")["relevant"], p2.set_index("id")["relevant"]),
                                          "kappa_type": kappa(p1.set_index("id")["type"], p2.set_index("id")["type"]),
                                          "note": "two passes by one AI reviewer; consistency, not inter-annotator agreement"},
           "v3_reference": {**v3_weighted(m, "relevant", counts), **boot(m, "relevant", counts)}}
    d = m[(m["source"] == "v3") & (m["v3_relevant"] == 1) & m["displayed"]]
    out["dashboard_displayed_subset"] = {"sampled": int(len(d)), "relevant": int((d["relevant"] == "Y").sum()),
                                         "false_positive_types": d[d["relevant"] == "N"]["title"].tolist(),
                                         "note": "v3-relevant sampled headlines that the dashboard news panel shows "
                                                 "(province-attributed); stratified by trigger, so not a population estimate"}
    out["direct_food_insecurity_headlines"] = m[m["type"] == "DIRECT"][["id", "source", "title"]].to_dict("records")
    hf = ANN / "news_review_human.csv"
    if hf.exists():
        h = pd.read_csv(hf).dropna(subset=["relevant"])
        hm = m.merge(h[["id", "type", "relevant"]].rename(columns={"type": "type_h", "relevant": "relevant_h"}), on="id")
        hm["relevant_h"] = hm["relevant_h"].astype(str).str.strip().str.upper()
        out["human"] = {"annotated": int(len(hm)),
                        "kappa_relevant_human_vs_reference": kappa(hm["relevant_h"], hm["relevant"]),
                        "kappa_type_human_vs_reference": kappa(hm["type_h"], hm["type"]),
                        "v3_under_human_labels": v3_weighted(hm, "relevant_h", counts)}
    else:
        out["human"] = "no human annotation yet (annotation/news_review_human.csv absent): results are preliminary"
    (OUT / "news_scores.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1, default=float)[:3500])


if __name__ == "__main__":
    main()
