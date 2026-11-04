"""BERTopic topic-quality fix (PLAN_BERTOPIC_V2.md, hash checked). No forecasting model is fitted.

    python t2_topics.py main     # T0 (served, refitted) + T2, decision -> ../out/t2_topics.json
    python t2_topics.py ablate   # descriptive A1 (masking only), A2 (c-TF-IDF only); needs the T2 decision first

Reuses obj1_nlp (_names, _npmi, corpus, served settings) unchanged.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
import re
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
AUD = HERE.parent
PLAN = HERE / "PLAN_BERTOPIC_V2.md"
OUT = HERE / "out"
sys.path.insert(0, str(AUD / "runner"))
import obj1_nlp as O  # noqa: E402

FIL = """ang ng sa na mga at ay para si ni kay ito iyan yan may mayroon hindi din rin lang lamang po ba pa nang kung pero
dahil kasi siya sila kami tayo natin namin nila niya ko mo ka ako ikaw ating aming kanilang kanyang mula hanggang tungkol
bilang upang o kina nina sina ngayon raw daw naman pala bawat iba ibang isang ayon habang pag kapag nito doon dito roon
rito ano saan bakit paano sino kaya muna pati ilang lahat wala walang ating kanila sa ni nag mag mas pang""".split()
CONFIGS = {"T0": dict(mask=False, fil=False, ctfidf=False), "T2": dict(mask=True, fil=True, ctfidf=True),
           "A1": dict(mask=True, fil=False, ctfidf=False), "A2": dict(mask=False, fil=False, ctfidf=True)}
ENC = "paraphrase-multilingual-MiniLM-L12-v2"


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PLAN_BERTOPIC_V2 changed"
    return h


def mask_set() -> set[str]:
    return (O._names() | {"lucena"}) - {"pila"}


def masker(names: set[str]):
    rx = re.compile(r"\b(?:" + "|".join(sorted(map(re.escape, names), key=len, reverse=True)) + r")(?:'s|’s)?\b",
                    re.IGNORECASE)
    return lambda s: re.sub(r"\s+", " ", rx.sub(" ", s)).strip()


_W: dict = {}


def _winit():
    from sentence_transformers import SentenceTransformer
    _W["enc"] = SentenceTransformer(ENC)


def _fit(titles: list[str], emb: np.ndarray, cfg: dict):
    from bertopic import BERTopic
    from bertopic.representation import KeyBERTInspired
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
    from umap import UMAP
    sys.path.insert(0, str(O.BACKEND))
    from app.ml.nlp.topic_model import N_GRAM_RANGE, TOP_N_WORDS
    stop = "english" if not cfg["fil"] else sorted(set(ENGLISH_STOP_WORDS) | set(FIL))
    m = BERTopic(embedding_model=_W["enc"],
                 umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42),
                 hdbscan_model=HDBSCAN(min_cluster_size=10, metric="euclidean", cluster_selection_method="eom",
                                       prediction_data=True),
                 vectorizer_model=CountVectorizer(ngram_range=N_GRAM_RANGE, stop_words=stop, min_df=2),
                 representation_model=None if cfg["ctfidf"] else KeyBERTInspired(), top_n_words=TOP_N_WORDS,
                 verbose=False)
    topics, _ = m.fit_transform(titles, emb)
    return m, np.asarray(topics)


def _geo(topics: np.ndarray, prov: np.ndarray) -> dict:
    ok = pd.notna(prov) & (topics != -1)
    s = pd.DataFrame({"t": topics[ok], "p": prov[ok]})
    ev, drv = 0, 0
    for _, g in s.groupby("t"):
        if len(g) >= 10:
            ev += 1
            drv += int(g["p"].value_counts(normalize=True).iloc[0] >= 0.80)
    return {"geo_topics_evaluated": ev, "geography_driven_share": drv / ev if ev else None}


def _job(job):
    name, q, titles, emb, keys, prov = job
    cfg = CONFIGS[name]
    m, tp = _fit(titles, emb, cfg)
    met = O._metrics(m, tp, titles, _W["names"])
    met.update(_geo(tp, prov))
    met["top_words_first5"] = [", ".join(w for w, _ in (m.get_topic(t) or [])[:5])
                               for t in m.get_topic_info()["Topic"] if t != -1][:5]
    return name, q, met, keys, tp


def _winit2(names):
    _winit()
    _W["names"] = names


def run(names_cfg: list[str]) -> dict:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics import adjusted_rand_score
    pre = check()
    P = O._pipe()
    C = pd.DataFrame(P.corpus()).sort_values(["published_ph", "article_key"]).reset_index(drop=True)
    enc = SentenceTransformer(ENC)
    mk = masker(mask_set())
    raw = C["title"].tolist()
    masked = [mk(s) for s in raw]
    emb_raw = enc.encode(raw, batch_size=64, show_progress_bar=False, normalize_embeddings=False)
    emb_mask = enc.encode(masked, batch_size=64, show_progress_bar=False, normalize_embeddings=False)
    pub = pd.to_datetime(C["published_ph"].str[:19])
    prov = C["province_code"].to_numpy(object)
    keys_all = C["article_key"].to_numpy()
    qs = [f"{y}-Q{q}" for y in range(2022, 2027) for q in range(1, 5) if f"{y}-Q{q}" <= "2026-Q3"]
    jobs = []
    for name in names_cfg:
        tit, emb = (masked, emb_mask) if CONFIGS[name]["mask"] else (raw, emb_raw)
        for q in qs:
            y, k = int(q[:4]), int(q[-1])
            Ot = pd.Timestamp(year=y + (k == 4), month=1 if k == 4 else 3 * k + 1, day=1)
            mask = (pub < Ot).to_numpy()
            jobs.append((name, q, [t for t, b in zip(tit, mask) if b], emb[mask], keys_all[mask], prov[mask]))
    with Pool(6, initializer=_winit2, initargs=(O._names(),)) as pool:
        outs = pool.map(_job, jobs, chunksize=1)
    res = {"prereg_sha256": pre, "masked_examples": [{"raw": r, "masked": m} for r, m in zip(raw, masked)
                                                    if r != m][:8],
           "n_mask_words": len(mask_set()), "headlines_changed_by_mask": int(sum(r != m for r, m in zip(raw, masked))),
           "configs": {}}
    for name in names_cfg:
        o = sorted([x for x in outs if x[0] == name], key=lambda x: x[1])
        origins, prev = {}, None
        for _, q, met, keys, tp in o:
            if prev is not None:
                pk = dict(zip(prev[0], prev[1]))
                common = np.isin(keys, prev[0])
                met["ari_vs_previous_fit"] = float(adjusted_rand_score([pk[x] for x in keys[common]], tp[common]))
            prev = (keys, tp)
            origins[q] = met
        v = list(origins.values())
        mean = lambda k: float(np.nanmean([x[k] for x in v if x.get(k) is not None]))  # noqa: E731
        summ = {"npmi_mean": mean("npmi_mean"), "place_name_share_mean": mean("place_name_topic_share"),
                "ari_mean": mean("ari_vs_previous_fit"), "geography_driven_share_mean": mean("geography_driven_share"),
                "n_topics_mean": mean("n_topics"), "outlier_share_mean": mean("outlier_share")}
        summ["passes_all_four"] = bool(summ["npmi_mean"] > 0 and summ["place_name_share_mean"] < .5
                                       and summ["ari_mean"] >= .3 and summ["geography_driven_share_mean"] < .5)
        res["configs"][name] = {"settings": CONFIGS[name], "summary": summ, "origins": origins}
        print(name, json.dumps(summ), flush=True)
    return res


def main():
    res = run(["T0", "T2"])
    st = json.loads((O.OUT / "obj1_topics.json").read_text(encoding="utf-8"))["summary"]
    t0 = res["configs"]["T0"]["summary"]
    diffs = {"npmi": abs(t0["npmi_mean"] - st["npmi_mean"]), "place": abs(t0["place_name_share_mean"] - st["place_name_share_mean"]),
             "ari": abs(t0["ari_mean"] - st["ari_mean"])}
    res["T0_reproduction"] = {"stored": st, "abs_diff": diffs, "ok": all(x <= .01 for x in diffs.values())}
    res["decision"] = {"topic_quality_achieved": res["configs"]["T2"]["summary"]["passes_all_four"]
                       if res["T0_reproduction"]["ok"] else None,
                       "note": "decision void: T0 did not reproduce" if not res["T0_reproduction"]["ok"] else
                       "per PLAN_BERTOPIC_V2.md; no further variant"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t2_topics.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"T0_reproduction": res["T0_reproduction"], "decision": res["decision"]}, indent=1, default=str))


def ablate():
    main_res = json.loads((OUT / "t2_topics.json").read_text(encoding="utf-8"))
    assert main_res["decision"]["topic_quality_achieved"] is not None, "T2 decision must be recorded first"
    res = run(["A1", "A2"])
    res["label"] = "DESCRIPTIVE ABLATION; not used for any decision"
    (OUT / "t2_ablations.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    {"main": main, "ablate": ablate}[sys.argv[1]]()
