"""
E151 relevance hypotheses, added after the label check (deviation D3). Reads no outcome.

The negatively worded "not about food" hypothesis removed nothing, so off-topic reporting is asked about directly, in positive form.

    <xpu python> -m app.e151.relevance <ov_dir> -> data/e151/raw/relevance.parquet
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from app.e151 import RAW
from app.e151.score_cpu import BATCH, CON, ENT, MAXLEN

HYP = {"offtopic": "This is mainly about politics, elections, business, finance, crime, sports or entertainment.",
       "foreign": "This is mainly about events in a foreign country, not the Philippines.",
       "weather": "This is a weather forecast or a storm bulletin, with no report of harm to people."}


def main(ov_dir):
    import openvino as ov
    from transformers import AutoTokenizer
    todo = pd.read_parquet(RAW / "to_score.parquet").sort_values("hash").reset_index(drop=True)
    target = RAW / "relevance.parquet"
    parts = [pd.read_parquet(target)] if target.exists() else []
    if parts:
        todo = todo[~todo["hash"].isin(parts[0]["hash"])].reset_index(drop=True)
    print("to score", len(todo), flush=True)
    tok = AutoTokenizer.from_pretrained(ov_dir)
    cm = ov.Core().compile_model(ov_dir + "/openvino_model.xml", "GPU", {"INFERENCE_PRECISION_HINT": "f32"})
    names = list(HYP)
    for i in range(0, len(todo), 400):
        c = todo.iloc[i:i + 400].reset_index(drop=True)
        prem = [t for t in c["score_text"] for _ in names]
        hyp = [HYP[n] for _ in c["score_text"] for n in names]
        ids = tok(prem, hyp, truncation=True, max_length=MAXLEN)
        order = np.argsort([len(x) for x in ids["input_ids"]], kind="stable")
        out = np.empty(len(prem))
        for j in range(0, len(order), BATCH):
            idx = order[j:j + BATCH]
            b = tok.pad({"input_ids": [ids["input_ids"][k] for k in idx], "attention_mask": [ids["attention_mask"][k] for k in idx]}, return_tensors="np")
            lg = cm({"input_ids": b["input_ids"], "attention_mask": b["attention_mask"]})[0]
            out[idx] = lg[:, ENT] - lg[:, CON]
        r = pd.DataFrame(out.reshape(len(c), len(names)), columns=[f"l_{n}" for n in names])
        r.insert(0, "hash", c["hash"])
        parts.append(r)
        parts = [pd.concat(parts, ignore_index=True)]
        tmp = target.with_suffix(".tmp")
        parts[0].to_parquet(tmp, index=False)
        tmp.replace(target)
        print(i + len(c), flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
