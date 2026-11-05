"""
E151 upgrade 1: province-target scoring. Reads no outcome.

The event scores read a whole article, so two provinces named in one article get the same reading. Here each article attributed to a CALABARZON province or to any other province is
read again per province: only the sentences naming that province (or one of its CALABARZON LGUs) form the premise, and the hypothesis names the province.

    python -m app.e151.target prep          -> data/e151/raw/target_premises.parquet (backend venv)
    <xpu python> -m app.e151.target <ov_dir> -> data/e151/raw/province_targets.parquet
"""
from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd

from app.e151 import RAW
from app.e151.score_cpu import BATCH, ENT, CON, MAXLEN

HYP = {"hard": "People in {p} are facing hunger, food shortage, high food prices, lost income or disaster damage.",
       "resp": "People in {p} are receiving food aid or assistance, or conditions in {p} are improving.",
       "none": "This is not about the living conditions of people in {p}."}


def targets() -> pd.DataFrame:
    """One row per story and province; the premise is what the article says about that province, or its lead if no sentence can be isolated."""
    from app.e147 import features as Fe
    from app.e150.news_v2 import name_rx
    from app.e151.corpus import CAL, DATA, SENT, STRICT
    st = pd.read_parquet(RAW / "stories.parquet", columns=["id", "story", "provinces", "geo_level", "score_text", "title"])
    st = st[st["geo_level"].isin(["province", "lgu", "province_body_only"]) & (st["provinces"] != "")].drop_duplicates("story")
    body = pd.read_parquet(RAW / "corpus.parquet", columns=["id", "body", "text"]).set_index("id")
    st["full"] = (st["id"].map(body["text"]).fillna("") + " " + st["id"].map(body["body"]).fillna("")).str.strip()
    base = Fe.base_rows().drop_duplicates("key").set_index("key")
    rx = {k: STRICT.get(k, name_rx(k)) for k in base.index}
    lg = pd.read_csv(DATA / "reference" / "calabarzon_lgus.csv")
    lg["pkey"] = lg["province_name"].str.lower()
    lgu = {}
    for p, g in lg.groupby("pkey"):
        names = {re.sub(r"\s*\(.*\)|\s+City$", "", n).strip() for n in g["lgu_name"]}
        lgu[p] = re.compile(r"\b(" + "|".join(sorted(map(re.escape, (n for n in names if len(n) >= 4)), key=len, reverse=True)) + r")\b")
    rows = []
    for r in st.itertuples(index=False):
        sents = SENT.split(r.full)[:80]
        for k in r.provinces.split("|"):
            if not k or k not in rx:
                continue
            hit = [s for s in sents if rx[k].search(s) or (k in lgu and lgu[k].search(s))]
            rows.append({"id": r.id, "story": r.story, "key": k, "province": base.at[k, "province"], "isolated": bool(hit), "premise": (" ".join(hit[:3]) if hit else r.score_text)[:500]})
    t = pd.DataFrame(rows)
    t.to_parquet(RAW / "target_premises.parquet", index=False)
    print("rows", len(t), "isolated", float(t["isolated"].mean()), "calabarzon", int(t["key"].isin(CAL).sum()), "calabarzon isolated", float(t[t["key"].isin(CAL)]["isolated"].mean()), flush=True)
    return t


def main(ov_dir):
    import openvino as ov
    from transformers import AutoTokenizer
    t = pd.read_parquet(RAW / "target_premises.parquet")
    tok = AutoTokenizer.from_pretrained(ov_dir)
    cm = ov.Core().compile_model(ov_dir + "/openvino_model.xml", "GPU", {"INFERENCE_PRECISION_HINT": "f32"})
    names = list(HYP)
    res = np.empty((len(t), len(names)))
    for i in range(0, len(t), 200):
        c = t.iloc[i:i + 200]
        prem = [p for p in c["premise"] for _ in names]
        hyp = [HYP[n].format(p=q) for q in c["province"] for n in names]
        ids = tok(prem, hyp, truncation=True, max_length=MAXLEN)
        order = np.argsort([len(x) for x in ids["input_ids"]], kind="stable")
        out = np.empty(len(prem))
        for j in range(0, len(order), BATCH):
            idx = order[j:j + BATCH]
            b = tok.pad({"input_ids": [ids["input_ids"][k] for k in idx], "attention_mask": [ids["attention_mask"][k] for k in idx]}, return_tensors="np")
            lg = cm({"input_ids": b["input_ids"], "attention_mask": b["attention_mask"]})[0]
            out[idx] = lg[:, ENT] - lg[:, CON]
        res[i:i + len(c)] = out.reshape(len(c), len(names))
        if (i // 200) % 5 == 0:
            print(i + len(c), flush=True)
    for j, n in enumerate(names):
        t["l_" + n] = res[:, j]
    t.drop(columns=["premise"]).to_parquet(RAW / "province_targets.parquet", index=False)
    print("done", flush=True)


if __name__ == "__main__":
    targets() if sys.argv[1] == "prep" else main(sys.argv[1])
