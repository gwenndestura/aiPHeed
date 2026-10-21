"""Factor cards state the served FIRI input values behind each driver group (thesis mode)."""
import re

import pytest

from app.ml.inference import e41_lead2 as LD
from app.ml.inference import thesis_system as T


@pytest.fixture(scope="module")
def rec():
    # thesis mode only for this module: the environment is restored afterwards so other tests keep their default mode
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("AIPHEED_LEAD2_MODEL", "thesis")
        if LD.mode() != "thesis":
            pytest.skip("thesis mode not selectable")
        yield LD.record()


def test_factor_card_sentences_state_the_model_inputs(rec):
    """Each sentence states the group's served input values, names national figures as national, and is absent only
    when no input was observed."""
    q = rec["targetQuarter"]
    for code in rec["provinces"]:
        res = T.firi_for(rec, q, code)
        pu = T.pushes(res)
        for key, ks in T.FIVE_GROUPS.items():
            text = T.plain_evidence(rec, q, code, key)
            observed = [k for k in ks if res["indicators"][k]["score"] is not None and res["indicators"][k]["x"] is not None]
            assert (text is None) == (not observed), (code, key)
            if text is None:
                continue
            assert "FIRI" not in text and "score" not in text
            if key in ("employment", "ofw_remittance"):
                assert "(national figure)" in text
            nums = [float(n) for n in re.findall(r"(\d+(?:\.\d+)?)%", text)]
            top = sorted(observed, key=lambda k: -abs(pu.get(k, 0)))[:2]
            for k in top:
                x = float(res["indicators"][k]["x"])
                if k in ("A3", "C3", "C4", "E2"):
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
