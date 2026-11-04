"""
E145 news pipeline (PROTOCOL.md section 4). No survey outcome is read in this module.

    python -m app.e145.news prepare                 # clean, deduplicate, gate -> data/e145/raw/{articles_clean,to_score}.parquet
    python -m app.e145.news score                   # zero-shot XLM-R on gated text, run in the OpenVINO venv (resumable)
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys

import numpy as np
import pandas as pd

from app.e145 import RAW

SURVEY_RX = re.compile(r"\bSWS\b|social weather|\bFNRI\b|hunger survey|food insecurity survey|national nutrition survey", re.I)
GATE_RX = re.compile(
    r"\b(rice|palay|bigas|food|foods|pagkain|hunger|hungry|gutom|malnutrition|malnourished|nutrition|price|prices|presyo|"
    r"farmer|farmers|magsasaka|fisher|fishers|fisherfolk|mangingisda|crop|crops|harvest|ani|agriculture|agricultural|typhoon|"
    r"bagyo|flood|flooding|baha|drought|tagtuyot|el ni.o|la ni.a|livelihood|kabuhayan|poverty|poor|kahirapan|mahirap|relief|"
    r"ayuda|unemployment|jobless|layoff|layoffs|retrenchment|shortage|kakulangan|inflation)\b", re.I)
TAG_RX = re.compile(r"<[^>]+>")
TEMPLATE = "This news is about {}."
DOMAINS = {"market": "food prices or food supply", "climate": "typhoons, floods or drought damaging crops",
           "employment": "jobs or job losses", "remittance": "overseas Filipino workers or remittances",
           "poverty": "poverty, hunger or food aid for families"}
STAGE2 = {"harder": "This news is about something that makes it harder for families to get enough food.",
          "easier": "This news is about something that makes it easier for families to get enough food.",
          "hardship": "This news reports families or people lacking food or going hungry.",
          "disruption": "This news reports damage or disruption that has already happened.",
          "warning": "This news warns of a possible future problem.",
          "response": "This news is about a government programme or assistance."}
REL_T = 0.30


def clean(s: str) -> str:
    return " ".join(html.unescape(TAG_RX.sub(" ", s or "")).split())


def prepare() -> pd.DataFrame:
    rows = [json.loads(x) for x in (RAW / "articles.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    d = pd.DataFrame(rows)
    d["title"], d["excerpt"] = d["title"].map(clean), d["excerpt"].map(clean)
    d["text"] = (d["title"] + ". " + d["excerpt"]).str.slice(0, 700)
    d["published"] = pd.to_datetime(d["date"])
    d = d.drop(columns=["date"]).drop_duplicates(["key", "id"])
    # the same story re-posted under another id: keep the earliest per province
    d["title_norm"] = d["title"].str.lower().str.replace(r"[^a-z0-9 ]", "", regex=True)
    d = d.sort_values("published").drop_duplicates(["key", "title_norm"])
    d["survey_report"] = d["text"].str.contains(SURVEY_RX)
    n_survey = int(d["survey_report"].sum())
    d = d[~d["survey_report"]].copy()
    d["gated"] = d["text"].str.contains(GATE_RX)
    d["hash"] = d["text"].map(lambda s: hashlib.sha1(s.encode("utf-8")).hexdigest())
    d.drop(columns=["excerpt", "title_norm", "survey_report"]).to_parquet(RAW / "articles_clean.parquet", index=False)
    d[d["gated"]].drop_duplicates("hash")[["hash", "text"]].to_parquet(RAW / "to_score.parquet", index=False)
    print({"rows": len(d), "unique_articles": int(d["id"].nunique()), "gated_rows": int(d["gated"].sum()),
           "to_score": int(d[d["gated"]]["hash"].nunique()), "survey_reports_removed": n_survey})
    return d


def _ov_nli(cm, tok, prem, hyp, batch=32):
    ids = tok(prem, hyp, truncation=True, max_length=96)
    order = np.argsort([len(x) for x in ids["input_ids"]], kind="stable")
    out = np.empty(len(prem))
    for j in range(0, len(order), batch):
        idx = order[j:j + batch]
        b = tok.pad({"input_ids": [ids["input_ids"][i] for i in idx], "attention_mask": [ids["attention_mask"][i] for i in idx]},
                    return_tensors="np")
        lg = cm({"input_ids": b["input_ids"], "attention_mask": b["attention_mask"]})[0][:, [0, 2]]
        e = np.exp(lg - lg.max(1, keepdims=True))
        out[idx] = (e / e.sum(1, keepdims=True))[:, 1]
    return out


def score(ov_dir: str) -> None:
    import openvino as ov
    from transformers import AutoTokenizer
    target = RAW / "xlmr_scores.parquet"
    todo = pd.read_parquet(RAW / "to_score.parquet")
    parts = [pd.read_parquet(target)] if target.exists() else []
    have = set(parts[0]["hash"]) if parts else set()
    todo = todo[~todo["hash"].isin(have)].sort_values("hash").reset_index(drop=True)
    print("to score", len(todo), flush=True)
    tok = AutoTokenizer.from_pretrained(ov_dir)
    cm = ov.Core().compile_model(ov_dir + "/openvino_model.xml", "GPU", {"INFERENCE_PRECISION_HINT": "f32"})
    dom = list(DOMAINS)
    for i in range(0, len(todo), 200):
        c = todo.iloc[i:i + 200].reset_index(drop=True)
        p1 = _ov_nli(cm, tok, [t for t in c["text"] for _ in dom], [TEMPLATE.format(DOMAINS[k]) for _ in c["text"] for k in dom])
        p1 = p1.reshape(len(c), len(dom))
        res = pd.DataFrame(p1, columns=[f"p_{k}" for k in dom])
        res.insert(0, "hash", c["hash"])
        for h in STAGE2:
            res[f"p_{h}"] = np.nan
        rel = np.where(p1.max(axis=1) >= REL_T)[0]
        if len(rel):
            p2 = _ov_nli(cm, tok, [c.at[k, "text"] for k in rel for _ in STAGE2], [STAGE2[h] for _ in rel for h in STAGE2])
            p2 = p2.reshape(len(rel), len(STAGE2))
            for j, h in enumerate(STAGE2):
                res.loc[rel, f"p_{h}"] = p2[:, j]
        parts.append(res)
        if (i // 200) % 25 == 0 or i + 200 >= len(todo):
            pd.concat(parts, ignore_index=True).to_parquet(target, index=False)
            parts = [pd.concat(parts, ignore_index=True)]
            print(i + len(c), flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "prepare":
        prepare()
    else:
        score(sys.argv[2])
