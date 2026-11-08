"""
Incremental XLM-RoBERTa (XNLI) scoring of newly collected news for the live refresh: only stories whose hash is not
yet scored. Same model, hypotheses, truncation and sign (entailment minus contradiction) as app.e151.score_cpu and
app.e151.relevance, so a new story is read exactly like the stories the model was validated on.

    <openvino python> -m app.e168.news_score <ov_dir>   -> appends to data/e151/raw/events.parquet, relevance.parquet
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from app.e151 import RAW
from app.e151.relevance import HYP as REL_HYP
from app.e151.score import HYP as EV_HYP
from app.e151.score_cpu import nli


def _append(target, todo, hyp, cm, tok) -> int:
    have = pd.read_parquet(target) if target.exists() else pd.DataFrame(columns=["hash"])
    todo = todo[~todo["hash"].isin(set(have["hash"]))].reset_index(drop=True)
    if not len(todo):
        return 0
    names = list(hyp)
    parts = [have]
    for i in range(0, len(todo), 100):
        c = todo.iloc[i:i + 100].reset_index(drop=True)
        v = nli(cm, tok, [t for t in c["score_text"] for _ in names], [hyp[n] for _ in c["score_text"] for n in names]).reshape(len(c), len(names))
        r = pd.DataFrame(v, columns=[f"l_{n}" for n in names])
        r.insert(0, "hash", c["hash"])
        parts.append(r)
    out = pd.concat(parts, ignore_index=True).drop_duplicates("hash")
    tmp = target.with_suffix(".tmp")
    out.to_parquet(tmp, index=False)
    tmp.replace(target)
    return int(len(todo))


def main(ov_dir: str) -> dict:
    import openvino as ov
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(ov_dir)
    core = ov.Core()
    dev = "GPU" if "GPU" in core.available_devices else "CPU"
    cm = core.compile_model(ov_dir + "/openvino_model.xml", dev, {"INFERENCE_PRECISION_HINT": "f32"})
    todo = pd.read_parquet(RAW / "to_score.parquet")
    res = {"device": dev, "events_scored": _append(RAW / "events.parquet", todo, EV_HYP, cm, tok),
           "relevance_scored": _append(RAW / "relevance.parquet", todo, REL_HYP, cm, tok)}
    print(json.dumps(res), flush=True)
    return res


if __name__ == "__main__":
    main(sys.argv[1])
