"""Build the C-B7 news index z_G (CB7_PREREGISTRATION.md, hash checked) from the GDELT DOC headlines.

    python news_g_build.py classify   # classifier v2 + syndication de-duplication -> ../news_g/admitted.csv
    python news_g_build.py score      # XLM-RoBERTa intensity (FSSI-v2 scorer), resumable -> ../news_g/scores.jsonl
    python news_g_build.py index      # G(t), z_G(t), leakage check -> ../out/cb7_features.csv, ../out/cb7_checks.json
Run from backend/ (imports app.news / app.ml).
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
G = HERE / "news_g"
OUT = HERE / "out"
PREREG = HERE / "CB7_PREREGISTRATION.md"
ADDENDUM = HERE / "CB7_ADDENDUM_1.md"                # source switched to the teammate's FI6-N archive
WIN, MINP, MIN_N = 8, 4, 5          # as prospective_lib.add_news_anomaly (NEWS_WIN, NEWS_MINP) and pipeline_v3.MIN_ARTICLES
sys.path.insert(0, str(HERE.parents[2] / "backend"))  # app.news / app.ml


def check() -> str:
    for f in (PREREG, ADDENDUM):
        b = f.read_bytes()
        body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
        h = hashlib.sha256(body + b"\n").hexdigest()
        assert last.split()[-1].decode() == h, f"{f.name} changed"
    return h


def qi(ts: pd.Timestamp) -> int:
    return ts.year * 4 + (ts.month - 1) // 3


def classify():
    check()
    from app.ml.corpus.geocoder import geocode_to_province
    from app.news.classifier_v2 import classify as clf
    from app.news.pipeline_v3 import SYNDICATION_DAYS, norm_title
    # CB7_ADDENDUM_1.md: the teammate's FI6-N publisher archive replaces the GDELT DOC headlines
    H = pd.read_excel(G / "teammate" / "aiPHeed_Best_News_Dataset_FI6N.xlsx", sheet_name="Articles", dtype=str)
    H = H.rename(columns={"link": "url", "site": "domain"})
    H = H[H["title"].fillna("").str.strip() != ""].copy()
    H["published_ph"] = pd.to_datetime(H["published"], utc=True).dt.tz_convert("Asia/Manila")
    H["article_key"] = H["url"].map(lambda u: hashlib.sha256(str(u).encode()).hexdigest())
    c = H["title"].map(lambda t: clf(t, geocode_to_province))
    H["relevant"], H["trigger"] = c.map(lambda x: x["relevant"]), c.map(lambda x: x["trigger"])
    R = H[H["relevant"] == 1].sort_values(["published_ph", "article_key"])
    keep, seen = [], {}
    for r in R.itertuples():                                  # pipeline_v3.dedupe: earliest copy within the window
        n = norm_title(r.title)
        prev = seen.get(n)
        if prev is not None and (r.published_ph - prev).days <= SYNDICATION_DAYS:
            continue
        seen[n] = r.published_ph
        keep.append(r.Index)
    A = R.loc[keep]
    A.to_csv(G / "admitted.csv", index=False)
    print({"headlines": len(H), "relevant": int((H["relevant"] == 1).sum()), "admitted_after_dedupe": len(A)})


def score():
    check()
    import app.ml.nlp.classifier as C
    clf = C.load_classifier()
    if not isinstance(clf, C._XLMRobertaClassifier):
        raise RuntimeError("XLM-RoBERTa unavailable; refusing the keyword fallback")
    A = pd.read_csv(G / "admitted.csv")
    f = G / "scores.jsonl"
    done = {json.loads(x)["article_key"] for x in f.read_text(encoding="utf-8").splitlines()} if f.exists() else set()
    with f.open("a", encoding="utf-8") as fh:
        for i, r in enumerate(A.itertuples()):
            if r.article_key in done:
                continue
            raw = clf.classify(C.clean_text(r.title, "", limit=C.PREMISE_CHARS))
            s = {x["topic_id"]: x["score"] for x in raw}
            top = max(s, key=lambda k: s[k])
            fh.write(json.dumps({"article_key": r.article_key, "score": round(s[top], 4), "top_hypothesis": top}) + "\n")
            if i % 200 == 0:
                fh.flush()
                print(f"{i}/{len(A)}", flush=True)
    print("scored", len(A))


def index():
    pre = check()
    A = pd.read_csv(G / "admitted.csv")
    S = pd.DataFrame([json.loads(x) for x in (G / "scores.jsonl").read_text(encoding="utf-8").splitlines()])
    A = A.merge(S, on="article_key", how="left")
    assert A["score"].notna().all(), "unscored admitted headlines: run score first"
    A["published_ph"] = pd.to_datetime(A["published_ph"], utc=True).dt.tz_convert("Asia/Manila")
    A["q"] = A["published_ph"].map(qi)
    # origin t's issue date O(t) = first day of quarter t+1 (PH); quarter-t articles are all before it
    O = lambda t: pd.Timestamp(year=(t + 1) // 4, month=((t + 1) % 4) * 3 + 1, day=1, tz="Asia/Manila")  # noqa: E731
    rows = []
    for t in sorted(A["q"].unique()):
        g = A[(A["q"] == t) & (A["published_ph"] < O(t))]
        assert len(g) == (A["q"] == t).sum()                  # leakage check: nothing on or after O(t)
        rows.append({"t": int(t), "n": int(len(g)), "G": float(g["score"].mean()) if len(g) >= MIN_N else np.nan})
    F = pd.DataFrame(rows).set_index("t").sort_index()
    z = {}
    for t in F.index:
        past = F.loc[[x for x in range(t - WIN, t) if x in F.index], "G"].dropna()
        sd = float(past.std(ddof=1)) if len(past) >= 2 else np.nan
        z[t] = float((F.loc[t, "G"] - past.mean()) / sd) if pd.notna(F.loc[t, "G"]) and len(past) >= MINP and sd > 0 else np.nan
    F["z_G"] = pd.Series(z)
    F.reset_index().to_csv(OUT / "cb7_features.csv", index=False)
    vol = F[["n", "G"]].dropna()
    chk = {"prereg_sha256": pre, "quarters": int(len(F)), "with_z_G": int(F["z_G"].notna().sum()),
           "first_z_G": int(F["z_G"].dropna().index.min()) if F["z_G"].notna().any() else None,
           "corr_G_vs_volume": float(vol["G"].corr(vol["n"])) if len(vol) > 2 else None,
           "leakage_unchanged": True, "admitted_total": int(len(A))}
    (OUT / "cb7_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    print(chk)


if __name__ == "__main__":
    {"classify": classify, "score": score, "index": index}[sys.argv[1]]()
