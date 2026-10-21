"""E83: the plain-language headline names the right place, quarter and class, is one sentence (the approved panel shows
only the first), and every reason it gives matches the sign of that indicator's exact push on the served index."""
import re

import pytest

from app.ml.inference import e41_lead2 as LD
from app.ml.inference import thesis_system as T

SPLIT = re.compile(r"(?<=\.)\s+(?=[A-Z])")          # frontend/src/lib/summaryHeadline.ts


@pytest.fixture(scope="module")
def rec():
    # thesis mode only for this module: the environment is restored afterwards so other tests keep their default mode
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("AIPHEED_LEAD2_MODEL", "thesis")
        if LD.mode() != "thesis":
            pytest.skip("thesis mode not selectable")
        yield LD.record()


def test_headline_is_one_sentence_with_place_quarter_class_and_action(rec):
    q = rec["targetQuarter"]
    for code, v in rec["provinces"].items():
        res = T.firi_for(rec, q, code)
        text = T.firi_text(res, v["name"], q)
        head = SPLIT.split(text)[0]
        assert head == T.plain_headline(res, v["name"], q)
        assert head.startswith(f"ESTIMATED FOOD-INSECURITY RISK for {v['name']}, {q}: {res['class']} (risk index")
        assert ("watch list" in head) == (res["class"] == "HIGH")
        assert "FIRI" not in head and "SHAP" not in head and "logit" not in head


def test_every_plain_reason_matches_its_push(rec):
    q = rec["targetQuarter"]
    for code, v in rec["provinces"].items():
        res = T.firi_for(rec, q, code)
        pu = T.pushes(res)
        up, down = T.plain_reasons(res)
        for phrase in up:
            k = next(k for k, s in T.PLAIN_UP.items() if s == phrase)
            assert pu[k] > 0 and res["indicators"][k]["score"] is not None
        for phrase in down:
            k = next(k for k, s in T.PLAIN_DOWN.items() if s == phrase)
            assert pu[k] < 0 and res["indicators"][k]["score"] is not None


def test_pushes_are_an_exact_split_of_the_index(rec):
    q = rec["targetQuarter"]
    for code in rec["provinces"]:
        res = T.firi_for(rec, q, code)
        assert abs(sum(T.pushes(res).values()) - (res["firi"] - 0.5)) < 1e-9
