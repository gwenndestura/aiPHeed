"""E28 section 4.4: does the FSSI capture food-related conditions or news availability? And is it reproducible?

    python -B runner/e28_fssi_diagnostics.py   ->  runs/e28_fssi_diagnostics.json

  * coverage dependence: Spearman of FSSI, fssi_raw (unweighted mean score) and bias_weight with the number of
    attributable articles, over province-quarters with evidence;
  * source composition: share of the top publisher per province-quarter and over time;
  * scoring reproducibility: 40 already-scored articles (fixed seed) are re-scored with the same model and compared;
  * FSSI reproducibility: the panel is rebuilt in memory from the store and its SHA-256 compared with the manifest.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard28  # noqa: E402

guard28.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

EXP = guard28.EXP
BD = EXP / "backend_dev"
sys.path.insert(0, str(BD))
from app.news.collector import all_quarters  # noqa: E402
from app.news.fssi import build_fssi  # noqa: E402
from app.news.scoring import current_model_key, xlmr_scorer  # noqa: E402
from app.news.store import NewsStore  # noqa: E402


def spearman(a, b):
    a, b = pd.Series(a), pd.Series(b)
    m = a.notna() & b.notna()
    if m.sum() < 5:
        return None
    return float(a[m].rank().corr(b[m].rank()))


def main():
    store = NewsStore(BD / "data" / "news_e28")
    mk = current_model_key()
    man = json.loads((store.root / "fssi_manifest.json").read_text(encoding="utf-8"))
    rebuilt = build_fssi(store, all_quarters("2026-Q2"), model_key=mk, write=False)
    out = {"model_key": mk, "fssi_rebuild_sha256": rebuilt["summary"]["panel_sha256"],
           "fssi_manifest_sha256": man["panel_sha256"],
           "fssi_reproducible": rebuilt["summary"]["panel_sha256"] == man["panel_sha256"]}
    p = rebuilt["panel"]
    ev = p[p["FSSI"].notna()]
    out["coverage_dependence"] = {
        "province_quarters_with_fssi": int(len(ev)),
        "spearman_FSSI_vs_n_geocoded": spearman(ev["FSSI"], ev["n_geocoded"]),
        "spearman_FSSI_vs_n_in_fssi": spearman(ev["FSSI"], ev["n_in_fssi"]),
        "spearman_fssi_raw_vs_n_in_fssi": spearman(ev["fssi_raw"], ev["n_in_fssi"]),
        "spearman_bias_weight_vs_n_geocoded": spearman(ev["bias_weight"], ev["n_geocoded"]),
        "share_of_FSSI_variance_explained_by_weight": (
            float(np.corrcoef(np.log(ev["FSSI"]), np.log(ev["bias_weight"]))[0, 1] ** 2) if len(ev) > 5 else None),
        "interpretation": ("FSSI = bias_weight x mean score. The weight is a decreasing function of the article count by "
                           "construction (log(1+median)/log(1+n)), so a strong negative FSSI-count correlation shows the "
                           "index tracks news volume; fssi_raw is the coverage-free part.")}
    art = rebuilt["articles"]
    a = art[art["score_status"].isin(["OK", "NO_FOOD_NEXUS"])]
    comp = a.groupby(["quarter"])["source_domain"].agg(lambda s: float(s.value_counts(normalize=True).iloc[0]))
    yearly = a.assign(year=a["quarter"].str[:4]).groupby("year")["source_domain"].agg(
        lambda s: s.value_counts(normalize=True).head(3).round(3).to_dict())
    per_q = a.groupby("quarter").size()
    out["source_composition"] = {"top_publisher_share_by_quarter": comp.round(3).to_dict(),
                                 "top3_publishers_by_year": yearly.to_dict(),
                                 "attributable_scored_articles_by_quarter": per_q.to_dict(),
                                 "spearman_articles_vs_time": spearman(np.arange(len(per_q)), per_q.values)}
    # scoring reproducibility on a fixed sample of OK-scored articles
    scores = [json.loads(l) for l in store.path("scores").read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [s for s in scores if s.get("model_key") == mk and s["status"] == "OK"]
    rng = np.random.default_rng(20261014)
    pick = [ok[i] for i in sorted(rng.choice(len(ok), size=min(40, len(ok)), replace=False))] if ok else []
    sc = xlmr_scorer() if pick else None
    diffs = []
    for s in pick:
        r = sc(store.articles[s["article_key"]]["title"], "")
        diffs.append(abs(r["score"] - s["score"]))
    out["scoring_reproducibility"] = {"articles_rescored": len(pick), "max_abs_diff": max(diffs) if diffs else None,
                                      "identical_at_4dp": bool(diffs) and max(diffs) == 0.0}
    (EXP / "runs" / "e28_fssi_diagnostics.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "source_composition"}, indent=1, default=str))


if __name__ == "__main__":
    main()
