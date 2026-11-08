"""
E174 Step A (docs/e174/PROTOCOL.md): pure zero-shot XLM-RoBERTa Tier 1. Builds the zero-shot news panel and FSSI into
data/e174/ with the unchanged E151 code; only the story event probabilities and the topic-to-trigger mapping use the
XLM-RoBERTa zero-shot scores alone. E151's own files are never written.

    python -m app.e174.zero_shot build   -> data/e174/raw/topic_assign_*.parquet, data/e174/out/{topic_report.csv, news_panel.parquet, fssi/}
"""
from __future__ import annotations

import shutil
import sys

import numpy as np
import pandas as pd

from app.paths import BACKEND_DIR

E151_RAW = BACKEND_DIR / "data" / "e151" / "raw"
E151_OUT = BACKEND_DIR / "data" / "e151" / "out"
RAW = BACKEND_DIR / "data" / "e174" / "raw"
OUT = BACKEND_DIR / "data" / "e174" / "out"


def event_probs_zs() -> pd.DataFrame:
    """app.e151.topics.event_probs with the XLM-RoBERTa zero-shot reader only (nz_*); off-topic filter unchanged."""
    from app.e151.topics import EVENTS
    e = pd.read_parquet(E151_RAW / "labels_raw.parquet").drop_duplicates("hash").reset_index(drop=True)
    ev = [k for k in EVENTS if k != "none"]
    Z = np.nan_to_num(e[[f"nz_{k}" for k in ev]].values)
    p = np.exp(Z - Z.max(axis=1, keepdims=True))
    p = p / p.sum(axis=1, keepdims=True)
    off = ((e["for_lex"] > 0) & (e["ph_lex"] == 0)) | (e["off_lex"] > 0)
    o = pd.DataFrame(p, columns=[f"pr_{k}" for k in ev])
    o["pr_none"] = off.astype(float).values
    o["hash"] = e["hash"].values
    o["problem"] = 1 / (1 + np.exp(-e["z_problem"].fillna(0.0).values))
    o["plan"] = 1 / (1 + np.exp(-e["z_plan"].fillna(0.0).values))
    return o


def remap_topics() -> pd.DataFrame:
    """Re-map each fitted E151 topic to a trigger group from the zero-shot probabilities of the stories fitted at that
    origin (published before it), with the E151 rule (top event; off-topic if mean pr_none >= 0.5)."""
    from app.e151.topics import EVENTS, GROUP, ORIGINS
    st = pd.read_parquet(E151_RAW / "stories.parquet", columns=["id", "hash", "published"])
    ev = event_probs_zs()
    old = pd.read_csv(E151_OUT / "topic_report.csv")
    cols = [f"pr_{e}" for e in EVENTS]
    rows = []
    for o in ORIGINS:
        a = pd.read_parquet(E151_RAW / f"topic_assign_{o}.parquet")
        x = a.merge(st, on="id").merge(ev, on="hash", how="left")
        fit = x[(x["published"] < pd.Timestamp(o)) & (x["topic"] >= 0)]
        mp = {}
        for t, g in fit.groupby("topic"):
            means = g[cols].mean()
            top = means.drop("pr_none")
            e_top = top.idxmax().replace("pr_", "")
            off = bool(means["pr_none"] >= 0.5)
            mp[int(t)] = None if off else GROUP[e_top]
            r = old[(old["origin"] == o) & (old["topic"] == t)]
            rows.append({"origin": o, "topic": int(t), "n": int(len(g)), "keywords": r["keywords"].iloc[0] if len(r) else "",
                         "top_event": e_top, "group": mp[int(t)], "off_topic": off, "mean_none": float(means["pr_none"]),
                         "mean_top_event": float(top.max()),
                         "e151_group": r["group"].iloc[0] if len(r) else None})
        a["t_group"] = a["topic"].map(mp)
        a.to_parquet(RAW / f"topic_assign_{o}.parquet", index=False)
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "topic_report.csv", index=False, lineterminator="\n")
    return R


def build():
    RAW.mkdir(parents=True, exist_ok=True)
    (OUT / "fssi").mkdir(parents=True, exist_ok=True)
    for f in ("stories.parquet", "province_targets.parquet"):
        if (E151_RAW / f).exists() and not (RAW / f).exists():
            shutil.copy2(E151_RAW / f, RAW / f)
    shutil.copy2(E151_OUT / "h2_signal.parquet", OUT / "h2_signal.parquet")   # SWS signal, no news reader involved
    R = remap_topics()
    print("topics re-mapped:", len(R), "changed group vs E151:", int((R["group"].fillna("-") != R["e151_group"].fillna("-")).sum()), flush=True)
    from app.e151 import features as F
    from app.e151 import fssi as S
    F.RAW, F.OUT, F.event_probs = RAW, OUT, event_probs_zs
    F.build()
    S.RAW, S.OUT, S.DIR = RAW, OUT, OUT / "fssi"
    S.main() if hasattr(S, "main") else S.build()
    print("zero-shot news panel and FSSI written to", OUT, flush=True)


if __name__ == "__main__":
    {"build": build}[sys.argv[1]]()
