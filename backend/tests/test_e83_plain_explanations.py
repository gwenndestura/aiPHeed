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


def test_factor_card_sentences_state_the_model_inputs(rec):
    """Each factor card's sentence states the served FIRI input values of its group (numbers taken from the index the
    forecast was computed from), names national figures as national, and is absent only when no input was observed."""
    import re as _re
    q = rec["targetQuarter"]
    for code in rec["provinces"]:
        res = T.firi_for(rec, q, code)
        for key, ks in T.FIVE_GROUPS.items():
            text = T.plain_evidence(rec, q, code, key)
            observed = [k for k in ks if res["indicators"][k]["score"] is not None and res["indicators"][k]["x"] is not None]
            assert (text is None) == (not observed), (code, key)
            if text is None:
                continue
            assert "FIRI" not in text and "score" not in text
            if key in ("employment", "ofw_remittance"):
                assert "(national figure)" in text
            nums = [float(n) for n in _re.findall(r"(\d+(?:\.\d+)?)%", text)]
            xs = [abs(float(res["indicators"][k]["x"])) for k in observed]
            for k in observed:
                x = float(res["indicators"][k]["x"])
                if k == "A1":
                    # E99 (G6): the price model's output is stated on its 0-1 scale, never as a "% chance"
                    assert (f"{x:.2f}" in text and "% chance" not in text) or k not in observed[:2]
                elif k in ("A3", "C3", "C4", "E2") and k in sorted(observed, key=lambda kk: -abs(T.pushes(res).get(kk, 0)))[:2]:
                    assert any(abs(n - abs(x)) < 0.6 for n in nums), (code, key, k, x, text)


def test_factor_card_sentences_name_the_quarters_used(rec):
    """Year-on-year facts name the quarter the model used (t-1) and the same quarter a year before (t-5)."""
    q = rec["targetQuarter"]
    t = T.qi(q) - 2
    assert rec["originQuarter"] == T.qs(t)
    used, before = T._ql(t - 1), T._ql(t - 5)
    for code in rec["provinces"]:
        for key in ("employment", "fish_kill"):
            text = T.plain_evidence(rec, q, code, key)
            if text:
                assert f"in {used}" in text and f"in {before}" in text, (code, key, text)


def test_firi_explanations_are_shap_values(rec):
    """The served FIRI explanation uses the SHAP library (exact Shapley values, background = every indicator at its
    historical middle): the explained function reproduces the served index, the values add up to index - 0.5, they
    equal the exact weight x (score - 0.5) split, and each dashboard bar is the SHAP sum of its group."""
    q = rec["targetQuarter"]
    for code in rec["provinces"]:
        res = T.firi_for(rec, q, code)
        keys = T.shap_keys(res)
        x = [res["indicators"][k]["score"] for k in keys]
        assert abs(T.firi_value(res, [x])[0] - res["firi"]) < 1e-12
        sv = T.shap_values(res)
        assert abs(sum(sv.values()) - (res["firi"] - 0.5)) < 1e-9
        pu = T.pushes(res)
        assert all(abs(sv[k] - pu[k]) < 1e-9 for k in keys)
        bars = {d["driver_group"]: d["group_shap"] for d in T.firi_drivers(rec, q, code, {"drivers": []})["drivers"]}
        for g, ks in T.FIVE_GROUPS.items():
            assert abs(bars[g] - round(sum(sv.get(k, 0.0) for k in ks), 6)) < 1e-6, (code, g)
