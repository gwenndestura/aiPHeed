"""E60 step N6: one-time evaluation of classifier v1 (deployed TRIGGER_KEYWORDS) and v2 (frozen n4_classifier.py) on the
EVAL annotation half (NEWS_ANNOTATION_PROTOCOL.md section 5). Rows with relevant = 9 (cannot tell) are excluded.

    backend/venv/Scripts/python.exe -B runner/n6_classifier_eval.py  -> NEWS_CLASSIFICATION_EVALUATION.csv, out/classifier_eval.json
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

E60 = Path(__file__).resolve().parents[1]
ROOT = E60.parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.ml.corpus.geocoder import geocode_to_province as g  # noqa: E402
from app.ml.nlp.trigger_classifier import TRIGGER_KEYWORDS  # noqa: E402
from n4_classifier import classify  # noqa: E402

RX = {c: [re.compile(r"\b" + re.escape(k) + r"\b", re.I) for k in kws] for c, kws in TRIGGER_KEYWORDS.items()}
PROVS = {"PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"}


def v1(t):
    hits = [c for c, rx in RX.items() if any(r.search(t or "") for r in rx)]
    return (1 if hits else 0), (hits[0] if hits else "none")


def prf(y, p):
    tp, fp, fn = int(((p == 1) & (y == 1)).sum()), int(((p == 1) & (y == 0)).sum()), int(((p == 0) & (y == 1)).sum())
    pr = tp / (tp + fp) if tp + fp else None
    rc = tp / (tp + fn) if tp + fn else None
    return {"TP": tp, "FP": fp, "FN": fn, "TN": int(((p == 0) & (y == 0)).sum()), "precision": pr, "recall": rc,
            "f1": (2 * pr * rc / (pr + rc)) if pr and rc else None}


def main():
    want = (E60 / "runner" / "CLASSIFIER_V2_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E60 / "runner" / "n4_classifier.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert got == want, "classifier v2 changed after freezing"
    A = pd.concat([pd.read_csv(E60 / "annotation" / f"sample_{w}.csv", dtype=str) for w in ("ACD", "B")])
    ev = A[(A["split"] == "EVAL")].copy()
    ev["v1_relevant"], ev["v1_trigger"] = zip(*ev["title"].map(v1))
    c = [classify(t, g) for t in ev["title"]]
    ev["v2_relevant"] = [x["relevant"] for x in c]
    ev["v2_trigger"] = [x["trigger"] for x in c]
    ev["v2_rule"] = [x["rule"] for x in c]
    ev["geocoder_province"] = ev["title"].map(g)
    ev["province_correct"] = [(gp == pt) if pt in PROVS else (gp is None) for gp, pt in zip(ev["geocoder_province"], ev["province_true"])]
    ev.to_csv(E60 / "NEWS_CLASSIFICATION_EVALUATION.csv", index=False)
    e = ev[ev["relevant"] != "9"]
    y = e["relevant"].astype(int)
    out = {"eval_rows": int(len(ev)), "excluded_cannot_tell": int((ev["relevant"] == "9").sum()), "relevant_rows": int(y.sum()),
           "relevance": {"v1": prf(y, e["v1_relevant"].astype(int)), "v2": prf(y, e["v2_relevant"].astype(int))},
           "trigger_on_relevant": {}, "province_attribution": {}}
    rel = e[y == 1]
    for v in ("v1", "v2"):
        out["trigger_on_relevant"][v] = {"correct": int((rel[f"{v}_trigger"] == rel["trigger"]).sum()), "of": int(len(rel))}
    pv = e[e["province_true"].isin(PROVS)]
    out["province_attribution"] = {"province_specific_rows": int(len(pv)),
                                   "geocoder_correct": int((pv["geocoder_province"] == pv["province_true"]).sum()),
                                   "non_province_rows_wrongly_attributed": int(e[~e["province_true"].isin(PROVS)]["geocoder_province"].notna().sum())}
    out["errors_v2"] = [{"title": r.title, "label": r.relevant, "v2": r.v2_relevant, "rule": r.v2_rule}
                        for r in e[e["v2_relevant"].astype(int) != y].itertuples()]
    out["errors_v1"] = [{"title": r.title, "label": r.relevant, "v1": r.v1_relevant, "v1_trigger": r.v1_trigger}
                        for r in e[e["v1_relevant"].astype(int) != y].itertuples()]
    (E60 / "out" / "classifier_eval.json").write_text(json.dumps(out, indent=1, default=float, ensure_ascii=False))
    print(json.dumps({k: v for k, v in out.items() if not k.startswith("errors")}, indent=1, default=float))
    print("v2 errors:"); [print("  ", x) for x in out["errors_v2"]]
    print("v1 errors:", len(out["errors_v1"]))


if __name__ == "__main__":
    main()
