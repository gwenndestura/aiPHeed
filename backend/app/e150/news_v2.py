"""
E150 news panel, second generation. Attribution comes from sentences that name the province in the article's full text; every other link is dropped.
Zero-shot XLM-RoBERTa scores the province's sentences, so a story about Cebu is not scored as a story about every province it mentions. No outcome is read.

    python -m app.e150.news_v2 prepare | score <ov_dir> | panel | audit
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from collections import Counter

import numpy as np
import pandas as pd

from app.e145 import news as N
from app.e145.collect import SPECIAL
from app.e147 import RAW as R147
from app.e148 import panel as Pn
from app.e150 import OUT, RAW

K = 10.0
TAG = re.compile(r"<[^>]+>")
SENT = re.compile(r"(?<=[.!?])\s+")
DOMAINS = ["market", "climate", "employment", "remittance", "poverty"]


def name_rx(key: str):
    if key in SPECIAL:
        names = [q.strip('"') for q in SPECIAL[key]]
    else:
        names = ["Tawi-Tawi"] if key == "tawi tawi" else [key.title().replace(" Del ", " del ").replace(" De ", " de ")]
    return re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b", re.I)


def _rows():
    a = pd.read_parquet(R147 / "articles_clean.parquet")[["key", "id", "title", "text", "published", "gated"]]
    a = a[a["published"] < "2021-07-02"]
    m = pd.read_json(RAW / "articles_more.jsonl", lines=True, dtype={"id": str})
    m["title"], m["excerpt"] = m["title"].map(N.clean), m["excerpt"].map(N.clean)
    m["text"] = (m["title"] + ". " + m["excerpt"]).str.slice(0, 700)
    m["published"] = pd.to_datetime(m["date"])
    m = m[~m["text"].str.contains(N.SURVEY_RX)].copy()
    m["gated"] = m["text"].str.contains(N.GATE_RX)
    d = pd.concat([a, m[["key", "id", "title", "text", "published", "gated"]]], ignore_index=True)
    d["title_norm"] = d["title"].str.lower().str.replace(r"[^a-z0-9 ]", "", regex=True)
    d = d.sort_values("published").drop_duplicates(["key", "id"])
    return d.drop_duplicates(["key", "title_norm"])


def prepare():
    d = _rows()
    d["site"] = d["id"].str.split(":").str[0]
    all_counts = d.groupby("site")["id"].nunique().to_dict()
    ft = {}
    with open(RAW / "fulltext.jsonl", encoding="utf-8", newline="\n") as f:
        for x in f:
            r = json.loads(x)
            ft[r["id"]] = " ".join(html.unescape(TAG.sub(" ", r["content"])).split())
    g = d[d["gated"]].copy()
    rows, stats = [], Counter()
    rxs = {k: name_rx(k) for k in g["key"].unique()}
    for _, r in g.iterrows():
        rx = rxs[r["key"]]
        body = ft.get(r["id"], "")
        stats["with_fulltext" if body else "no_fulltext"] += 1
        in_title = bool(rx.search(r["title"]))
        sents = [s for s in SENT.split(body) if rx.search(s)]
        if not in_title and not sents and not rx.search(r["text"]):
            stats["dropped_no_province_sentence"] += 1
            continue
        strength = "title" if in_title else ("repeated" if len(sents) >= 2 else "single")
        stats[strength] += 1
        text = (r["title"] + ". " + " ".join(sents[:3]))[:700] if sents else r["text"]
        rows.append({"key": r["key"], "id": r["id"], "site": r["site"], "published": r["published"], "strength": strength, "n_mentions": len(sents), "text": text, "hash": hashlib.sha1(text.encode("utf-8")).hexdigest()})
    A = pd.DataFrame(rows)
    A.to_parquet(RAW / "articles_attributed.parquet", index=False)
    A.drop_duplicates("hash")[["hash", "text"]].to_parquet(RAW / "to_score.parquet", index=False)
    d[["key", "id", "published", "gated"]].to_parquet(RAW / "mentions.parquet", index=False)
    out = {"province_article_rows_all": int(len(d)), "unique_articles_all": int(d["id"].nunique()), "articles_by_outlet_all": all_counts, "gated_rows": int(len(g)), "attribution": dict(stats), "attributed_rows": int(len(A)), "to_score": int(A["hash"].nunique()), "attributed_by_outlet": A.groupby("site")["id"].nunique().to_dict()}
    (OUT / "news_v2_audit.json").write_text(json.dumps(out, indent=1), newline="\n")
    print(json.dumps(out, indent=1))


def score(ov_dir):
    N.RAW = RAW
    N.score(ov_dir)


def panel():
    A = pd.read_parquet(RAW / "articles_attributed.parquet")
    s = pd.read_parquet(RAW / "xlmr_scores.parquet")
    A = A.merge(s, on="hash", how="left")
    A["published"] = pd.to_datetime(A["published"])
    A["stress"] = A[["p_harder", "p_hardship"]].max(axis=1).fillna(0.0)
    A.loc[A["p_response"].fillna(0) >= 0.5, "stress"] *= 0.5                # assistance stories signal response more than hardship
    M_ = pd.read_parquet(RAW / "mentions.parquet")
    M_["published"] = pd.to_datetime(M_["published"])
    keys = sorted(M_["key"].unique())
    rows = []
    prev = {}
    for i in range(Pn.FIRST, Pn.LAST + 1):
        d = Pn.q_start(i)
        lo = d - pd.DateOffset(months=12)
        w = A[(A["published"] < d) & (A["published"] >= lo)].copy()
        ment = M_[(M_["published"] < d) & (M_["published"] >= lo)].groupby("key")["id"].nunique().reindex(keys).fillna(0)
        if w.empty:
            continue
        # outlet correction: each outlet's stress is centred on that outlet's own mean in the window, so a dominant or gloomier outlet does not set a province's level
        w["s_adj"] = w["stress"] - w.groupby("site")["stress"].transform("mean") + w["stress"].mean()
        g = w.groupby("key")
        n = g["id"].nunique().reindex(keys).fillna(0)
        S_ = g["s_adj"].sum().reindex(keys).fillna(0)
        rho = float(w["s_adj"].mean())
        f = N_logit((S_ + K * rho) / (n + K)) - N_logit(rho)
        att = np.log1p(n) - np.log1p(n).mean()
        share_nat = n.sum() / max(ment.sum(), 1)
        t = pd.DataFrame({"key": keys, "qi": i, "fv2_fssi": f.values, "fv2_attention": att.values, "fv2_named_share": (((n + K * share_nat) / (ment + K)) - share_nat).values, "fv2_n": n.values})
        for dm in DOMAINS:
            flag = (w[f"p_{dm}"] >= 0.5)
            cnt = flag.groupby(w["key"]).sum().reindex(keys).fillna(0)
            nat = float(flag.mean())
            t[f"fv2_{dm}"] = ((cnt + K * nat) / (n + K) - nat).values
        t["fv2_fssi_chg"] = [v - prev.get((k, i - 4), np.nan) for k, v in zip(keys, f.values)]
        for k, v in zip(keys, f.values):
            prev[(k, i)] = v
        rows.append(t)
    P = pd.concat(rows, ignore_index=True)
    P.to_parquet(OUT / "news_v2_panel.parquet", index=False)
    print(P.shape, P.drop(columns=["key", "qi"]).notna().mean().round(2).to_dict())


def N_logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prepare":
        prepare()
    elif cmd == "score":
        score(sys.argv[2])
    elif cmd == "panel":
        panel()
