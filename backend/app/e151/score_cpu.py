"""
E151 extra CPU workers for event scoring, added to shorten the run. Reads no outcome.

The GPU job walks the hash-sorted article list from the front. Each worker here takes every K-th article from the back, so the two meet in the middle.
Same model, same hypotheses, same truncation as app/e151/score.py. Values are written with the corrected sign (entailment minus contradiction, deviation D1);
the GPU file still holds the negative until `merge` runs.

    <xpu python> -m app.e151.score_cpu <ov_dir> <k> <K> <threads> -> data/e151/raw/events_cpu_<k>.parquet
    <xpu python> -m app.e151.score_cpu merge                      -> data/e151/raw/events.parquet (once only)
"""
from __future__ import annotations

import shutil
import sys

import numpy as np
import pandas as pd

from app.e151 import RAW
from app.e151.score import BATCH, HYP, MAXLEN

ENT, CON = 2, 0                 # config id2label: 0 contradiction, 1 neutral, 2 entailment


def nli(cm, tok, prem, hyp):
    ids = tok(prem, hyp, truncation=True, max_length=MAXLEN)
    order = np.argsort([len(x) for x in ids["input_ids"]], kind="stable")
    out = np.empty(len(prem))
    for j in range(0, len(order), BATCH):
        idx = order[j:j + BATCH]
        b = tok.pad({"input_ids": [ids["input_ids"][i] for i in idx], "attention_mask": [ids["attention_mask"][i] for i in idx]}, return_tensors="np")
        lg = cm({"input_ids": b["input_ids"], "attention_mask": b["attention_mask"]})[0]
        out[idx] = lg[:, ENT] - lg[:, CON]
    return out


def work(ov_dir, k, K, threads):
    import openvino as ov
    from transformers import AutoTokenizer
    target = RAW / f"events_cpu_{k}.parquet"
    todo = pd.read_parquet(RAW / "to_score.parquet").sort_values("hash", ascending=False).reset_index(drop=True).iloc[k::K]
    parts = [pd.read_parquet(target)] if target.exists() else []
    have = set(parts[0]["hash"]) if parts else set()
    todo = todo[~todo["hash"].isin(have)].reset_index(drop=True)
    tok = AutoTokenizer.from_pretrained(ov_dir)
    cm = ov.Core().compile_model(ov_dir + "/openvino_model.xml", "CPU", {"INFERENCE_PRECISION_HINT": "f32", "INFERENCE_NUM_THREADS": threads})
    names = list(HYP)
    for i in range(0, len(todo), 25):
        c = todo.iloc[i:i + 25].reset_index(drop=True)
        v = nli(cm, tok, [t for t in c["score_text"] for _ in names], [HYP[n] for _ in c["score_text"] for n in names]).reshape(len(c), len(names))
        r = pd.DataFrame(v, columns=[f"l_{n}" for n in names])
        r.insert(0, "hash", c["hash"])
        parts.append(r)
        parts = [pd.concat(parts, ignore_index=True)]
        tmp = target.with_suffix(".tmp")
        parts[0].to_parquet(tmp, index=False)
        tmp.replace(target)
        print(len(parts[0]), flush=True)
    print("done", flush=True)


def rest(ov_dir):
    """Last stretch on the GPU: only articles nobody has scored yet, with the corrected sign."""
    import openvino as ov
    from transformers import AutoTokenizer
    target = RAW / "events_cpu_gpu.parquet"
    done = set()
    for f in [RAW / "events.parquet"] + sorted(RAW.glob("events_cpu_*.parquet")):
        done |= set(pd.read_parquet(f, columns=["hash"])["hash"])
    todo = pd.read_parquet(RAW / "to_score.parquet")
    todo = todo[~todo["hash"].isin(done)].sort_values("hash").reset_index(drop=True)
    print("to score", len(todo), flush=True)
    parts = [pd.read_parquet(target)] if target.exists() else []
    tok = AutoTokenizer.from_pretrained(ov_dir)
    cm = ov.Core().compile_model(ov_dir + "/openvino_model.xml", "GPU", {"INFERENCE_PRECISION_HINT": "f32"})
    names = list(HYP)
    for i in range(0, len(todo), 200):
        c = todo.iloc[i:i + 200].reset_index(drop=True)
        v = nli(cm, tok, [t for t in c["score_text"] for _ in names], [HYP[n] for _ in c["score_text"] for n in names]).reshape(len(c), len(names))
        r = pd.DataFrame(v, columns=[f"l_{n}" for n in names])
        r.insert(0, "hash", c["hash"])
        parts.append(r)
        parts = [pd.concat(parts, ignore_index=True)]
        tmp = target.with_suffix(".tmp")
        parts[0].to_parquet(tmp, index=False)
        tmp.replace(target)
        print(i + len(c), flush=True)
    print("done", flush=True)


def merge():
    marker = RAW / "events_sign_fixed.txt"
    if marker.exists():
        raise SystemExit("already merged")
    gpu = pd.read_parquet(RAW / "events.parquet")
    shutil.copy(RAW / "events.parquet", RAW / "events_gpu_wrong_sign.parquet")
    cols = [c for c in gpu.columns if c.startswith("l_")]
    gpu[cols] = -gpu[cols]                                      # D1: contradiction minus entailment becomes entailment minus contradiction
    cpu = [pd.read_parquet(p) for p in sorted(RAW.glob("events_cpu_*.parquet"))]
    a = pd.concat([gpu] + cpu, ignore_index=True).drop_duplicates("hash")
    want = set(pd.read_parquet(RAW / "to_score.parquet", columns=["hash"])["hash"])
    missing = want - set(a["hash"])
    if missing:
        raise SystemExit(f"{len(missing)} articles unscored; nothing written")
    a.to_parquet(RAW / "events.parquet", index=False)
    marker.write_text(f"gpu {len(gpu)} cpu {sum(map(len, cpu))} merged {len(a)}\n")
    print("merged", len(a))


if __name__ == "__main__":
    if sys.argv[1] == "merge":
        merge()
    elif sys.argv[1] == "rest":
        rest(sys.argv[2])
    else:
        work(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
