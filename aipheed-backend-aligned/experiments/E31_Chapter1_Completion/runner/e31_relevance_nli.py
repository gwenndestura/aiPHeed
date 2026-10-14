"""E31 relevance validation, candidate R-NLI: the same XLM-RoBERTa-large-XNLI model, but ONE direct relevance
hypothesis (EN and FIL) instead of the ten FSSI hypotheses, scored on the 355 review titles (all strata).

Hypotheses (fixed before scoring, from the annotation rubric):
  EN  "This news is about hunger, food shortage, high food prices, food aid, or losses of crops, livestock or fish."
  FIL "Ang balitang ito ay tungkol sa gutom, kakulangan sa pagkain, mataas na presyo ng pagkain, tulong na pagkain, o
       pagkalugi ng pananim, hayop o isda."
Score = max entailment probability over the two. The threshold is chosen on DEV only (e31_relevance_eval.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "runner"))
import guard31  # noqa: E402

guard31.install()
import torch  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402

MODEL = "joeddav/xlm-roberta-large-xnli"
HYP = ["This news is about hunger, food shortage, high food prices, food aid, or losses of crops, livestock or fish.",
       "Ang balitang ito ay tungkol sa gutom, kakulangan sa pagkain, mataas na presyo ng pagkain, tulong na pagkain, o "
       "pagkalugi ng pananim, hayop o isda."]


def main():
    sheet = json.loads((EXP / "validation" / "annotation_sheet_blind.json").read_text(encoding="utf-8"))
    tok = AutoTokenizer.from_pretrained(MODEL)
    mdl = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
    ent = [i for i, l in mdl.config.id2label.items() if l.lower().startswith("entail")][0]
    out = {}
    with torch.no_grad():
        for r in sheet:
            ps = []
            for h in HYP:
                x = tok(r["title"], h, return_tensors="pt", truncation=True, max_length=256)
                ps.append(float(torch.softmax(mdl(**x).logits[0], -1)[ent]))
            out[r["id"]] = max(ps)
    (EXP / "validation" / "nli_relevance_scores.json").write_bytes(
        json.dumps({"model": MODEL, "hypotheses": HYP, "scores": out}, indent=1, ensure_ascii=False).encode("utf-8"))
    print(len(out))


if __name__ == "__main__":
    main()
