"""The ISO/IEC 25010 scoring arithmetic (app.iso25010.score). The data below are SYNTHETIC, written only to check the
formulas; they are not evaluator responses and must never be reported."""
import pandas as pd
import pytest

from app.iso25010 import score as S


def test_refuses_without_responses():
    df = pd.read_csv("../docs/final/iso25010/responses_template.csv")
    assert df.empty
    with pytest.raises(SystemExit, match="no responses"):
        S.score(df)


def test_arithmetic_on_synthetic_rows():
    rows = []
    for i in range(6):
        r = {c: 4 for cs in S.CHAR.values() for c in cs}
        r.update({"FS1": 5, "PE1": 2, "PE2": 2, "MA1": None, "MA2": None})
        r.update({f"SUS{k}": (4 if k % 2 else 2) for k in range(1, 11)})
        r.update({"T1_done": "yes", "T1_seconds": 30 + i})
        rows.append(r)
    out = S.score(pd.DataFrame(rows))
    fs = out["characteristics"]["Functional suitability"]
    assert fs["mean"] == pytest.approx(13 / 3, abs=0.01) and fs["interpretation"].startswith("Strongly agree") and fs["acceptable"]
    pe = out["characteristics"]["Performance efficiency"]
    assert pe["mean"] == 2.0 and pe["interpretation"].startswith("Disagree") and not pe["acceptable"]
    assert out["characteristics"]["Maintainability"]["n"] == 0
    assert out["sus"]["mean"] == 75.0
    assert out["tasks"]["T1"]["completion_rate"] == 1.0


def test_rejects_out_of_range_values():
    r = {c: 4 for cs in S.CHAR.values() for c in cs}
    r["FS1"] = 7
    with pytest.raises(SystemExit, match="outside 1-5"):
        S.score(pd.DataFrame([r]))
