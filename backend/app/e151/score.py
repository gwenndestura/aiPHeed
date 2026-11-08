"""
E151 zero-shot event extraction with XLM-RoBERTa on the Arc GPU. Reads no outcome.

Each article is tested against events, not against generic sentiment, and reporting about a problem is kept apart from reporting about relief or recovery.
Entailment logits are stored raw, so features can use a softmax across events and ranks learned on earlier articles only, which avoids the saturation found in E150 (p_warning mean 0.93).

    <xpu python> -m app.e151.score <ov_dir> -> data/e151/raw/events.parquet
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from app.e151 import RAW

HYP = {"food_access": "People or families are going hungry or cannot get enough food.",
       "purchasing": "Households can no longer afford food or basic needs because prices rose or incomes fell.",
       "supply": "Food supply is disrupted, or there is a shortage of rice, fish, vegetables or other food.",
       "agri_loss": "Crops, farms, fisheries or livestock suffered damage or production losses.",
       "income": "Workers or families lost jobs, income or livelihoods.",
       "climate": "A typhoon, flood, drought or El Nino is harming people's food or livelihoods.",
       "displacement": "People were displaced or evacuated from their homes.",
       "ofw": "Overseas Filipino workers or their remittances are affected.",
       "assistance": "The government or an organization is giving food aid, cash aid or other assistance.",
       "recovery": "Food prices fell, food supply improved, or conditions recovered.",
       "none": "This is not about food, farming, livelihoods, prices or disasters.",
       "problem_now": "A problem is happening now and is harming people.",
       "plan_or_warning": "An official is announcing a plan, a policy or a warning about a possible future problem."}
BATCH = 40
MAXLEN = 128


def nli(cm, tok, prem, hyp):
    ids = tok(prem, hyp, truncation=True, max_length=MAXLEN)
    order = np.argsort([len(x) for x in ids["input_ids"]], kind="stable")
    out = np.empty(len(prem))
    for j in range(0, len(order), BATCH):
        idx = order[j:j + BATCH]
        b = tok.pad({"input_ids": [ids["input_ids"][i] for i in idx], "attention_mask": [ids["attention_mask"][i] for i in idx]}, return_tensors="np")
        lg = cm({"input_ids": b["input_ids"], "attention_mask": b["attention_mask"]})[0]
        out[idx] = lg[:, 2] - lg[:, 0]              # entailment minus contradiction; config id2label: 0 contradiction, 1 neutral, 2 entailment (deviation D1)
    return out


def main(ov_dir):
    import openvino as ov
    from transformers import AutoConfig, AutoTokenizer
    print("labels", AutoConfig.from_pretrained(ov_dir).id2label, flush=True)
    target = RAW / "events.parquet"
    todo = pd.read_parquet(RAW / "to_score.parquet")
    parts = [pd.read_parquet(target)] if target.exists() else []
    have = set(parts[0]["hash"]) if parts else set()
    todo = todo[~todo["hash"].isin(have)].sort_values("hash").reset_index(drop=True)
    print("to score", len(todo), flush=True)
    tok = AutoTokenizer.from_pretrained(ov_dir)
    cm = ov.Core().compile_model(ov_dir + "/openvino_model.xml", "GPU", {"INFERENCE_PRECISION_HINT": "f32"})
    names = list(HYP)
    for i in range(0, len(todo), 200):
        c = todo.iloc[i:i + 200].reset_index(drop=True)
        v = nli(cm, tok, [t for t in c["score_text"] for _ in names], [HYP[k] for _ in c["score_text"] for k in names]).reshape(len(c), len(names))
        r = pd.DataFrame(v, columns=[f"l_{k}" for k in names])
        r.insert(0, "hash", c["hash"])
        parts.append(r)
        if (i // 200) % 10 == 0 or i + 200 >= len(todo):
            parts = [pd.concat(parts, ignore_index=True)]
            parts[0].to_parquet(target, index=False)
            print(i + len(c), flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
