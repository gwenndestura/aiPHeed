"""
E147 news panel: merges the E145 Rappler corpus with the extension, then reuses the E145 tiers with E147's paths. No outcome is read.

    python -m app.e147.news merge | build
"""
from __future__ import annotations

import json
import re
import shutil
import sys

import numpy as np
import pandas as pd

from app.e137 import features as F
from app.e145 import RAW as R145
from app.e145 import features as X
from app.e145 import news as N
from app.e147 import OUT, RAW

ORIGINS = {"O2": ["FNRI2015", "ENNS2018"], "O3": ["FNRI2015", "ENNS2018", "ENNS2019"], "F": ["FNRI2015", "ENNS2018", "ENNS2019", "ENNS2021"]}
YEAR = {"NNS2013": 2013, "FNRI2015": 2015, "ENNS2018": 2018, "ENNS2019": 2019, "ENNS2021": 2021}
PREV = {"FNRI2015": "NNS2013", "ENNS2018": "FNRI2015", "ENNS2019": "FNRI2015", "ENNS2021": "FNRI2015"}
LEADS = [1, 2, 3, 4]


def _paths():
    N.RAW = RAW
    X.RAW = RAW


def merge():
    _paths()
    with open(RAW / "articles.jsonl", "w", encoding="utf-8", newline="\n") as out:
        with open(R145 / "articles.jsonl", encoding="utf-8", newline="\n") as f:
            for x in f:
                try:
                    r = json.loads(x)
                except json.JSONDecodeError:
                    continue
                if r["date"] < "2021-07-02":
                    r["id"], r["site"] = f"rappler:{r['id']}", "rappler"
                    out.write(json.dumps(r, ensure_ascii=False) + "\n")
        with open(RAW / "articles_more.jsonl", encoding="utf-8", newline="\n") as f:
            for x in f:
                out.write(x)
    shutil.copyfile(R145 / "xlmr_scores.parquet", RAW / "xlmr_scores.parquet")
    N.prepare()


def attribution_audit(a: pd.DataFrame) -> dict:
    """Is the province named in the title or excerpt text, rather than only somewhere in the unseen article body?"""
    g = a[a["gated"]].drop_duplicates(["key", "id"]).copy()
    named = [bool(re.search(re.escape(k.replace(" ", " ")), t.lower())) for k, t in zip(g["key"], g["text"])]
    g["named"] = named
    return {"gated_province_article_rows": int(len(g)), "named_in_title_or_excerpt": float(np.mean(named)), "articles_per_source": a.drop_duplicates("id")["id"].str.split(":").str[0].value_counts().to_dict(),
            "stress_rate_named": float(g[g["named"]]["stress"].mean()), "stress_rate_not_named": float(g[~g["named"]]["stress"].mean())}


def build():
    from joblib import Parallel, delayed

    from app.e141 import panel as P
    _paths()
    a = X.articles()
    a["published"] = pd.to_datetime(a["published"])
    keys = sorted(P.outcomes()["key"].unique())
    idx, emb = pd.read_parquet(RAW / "embeddings_index.parquet"), np.load(RAW / "embeddings.npy")
    base = []
    for s, y in YEAR.items():
        for h in LEADS:
            t = X.window_stats(a, keys, F.issue_date(y, h))
            t["survey"], t["lead"] = s, h
            base.append(t)
    base = pd.concat(base, ignore_index=True)
    pv = base[["key", "survey", "lead", "nb_fssi"]].rename(columns={"survey": "ps", "nb_fssi": "pf"})
    base["ps"] = base["survey"].map(PREV)
    base = base.merge(pv, on=["key", "ps", "lead"], how="left")
    base["nb_fssi_delta"] = base["nb_fssi"] - base["pf"]
    base = base.drop(columns=["ps", "pf"])

    def one(o, h):
        tp = X.topic_assign(F.issue_date(YEAR[ORIGINS[o][-1]], h), a, idx, emb)
        rows = []
        for s in ORIGINS[o]:
            d = F.issue_date(YEAR[s], h)
            w = a[a["gated"] & (a["published"] < d) & (a["published"] >= d - pd.DateOffset(months=X.W_MONTHS))].copy()
            w["topic"] = w["hash"].map(tp)
            w = w[w["topic"].notna()]
            nat = w["topic"].value_counts(normalize=True)
            n = w.groupby("key").size().reindex(keys).fillna(0)
            for i in range(X.N_TOPICS):
                c = w[w["topic"] == i].groupby("key").size().reindex(keys).fillna(0)
                rho = float(nat.get(i, 0.0))
                rows.append(pd.DataFrame({"key": keys, "survey": s, "t": f"nb_topic_{i}", "v": (c + X.K * rho).values / (n + X.K).values - rho}))
        r = pd.concat(rows).pivot_table(index=["key", "survey"], columns="t", values="v").reset_index()
        r["origin"], r["lead"] = o, h
        return r

    T = pd.concat(Parallel(n_jobs=8)(delayed(one)(o, h) for o in ORIGINS for h in LEADS), ignore_index=True)
    res = T.merge(base, on=["key", "survey", "lead"], how="left")
    OUT.mkdir(parents=True, exist_ok=True)
    res.to_parquet(OUT / "news_features.parquet", index=False)
    from scipy.stats import spearmanr
    aud = {"attribution": attribution_audit(a), "rows": int(len(res))}
    one_ = res[res["lead"] == 1].drop_duplicates(["key", "survey"])
    aud["volume_dependence_by_survey"] = {s: {"fssi_vs_articles": float(spearmanr(g["nb_fssi"], g["n"]).statistic), "raw_count_vs_articles": float(spearmanr(g["nr_count"], g["n"]).statistic)} for s, g in one_.groupby("survey")}
    aud["articles_by_year"] = a.drop_duplicates("id").groupby(a["published"].dt.year)["id"].size().to_dict()
    (OUT / "news_audit.json").write_text(json.dumps(aud, indent=1, default=float), newline="\n")
    print(json.dumps(aud, indent=1, default=float)[:1800])


if __name__ == "__main__":
    {"merge": merge, "build": build}[sys.argv[1]]()
