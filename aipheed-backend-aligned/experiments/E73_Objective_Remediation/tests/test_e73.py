"""E73 tests. Every survey / review / outcome value here is SYNTHETIC (generated in the test); none is a real
observation. Real-data checks: protocol freeze, OCTA provenance, seal register, results consistency."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E73 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E73 / "runner"))
import e73_expert_review as X  # noqa: E402
import e73_fies_survey as S  # noqa: E402
import e73_prospective as PR  # noqa: E402


def test_protocol_frozen():
    b = (E73 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(b).hexdigest() == (E73 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]


def test_octa_values_all_have_source_text():
    rows = list(csv.DictReader((E73 / "inputs" / "provenance.csv").open(encoding="utf-8")))
    assert len(rows) >= 8
    for r in rows:
        assert r["url"].startswith("https://") and r["source_text"] and str(int(float(r["value"]))) in r["source_text"].replace("seven", "7")


def test_octa_result_matches_rules():
    o = json.loads((E73 / "out" / "octa_validation.json").read_text())
    assert o["threshold"] == 11.0 and o["threshold_basis"] == "first 4 rounds"
    g = o["goal80_independent"]
    assert g["supported"] == (g["accuracy"] >= 0.8 and g["balanced"] >= 0.7 and g["rho_ci_lower"] > 0) and g["supported"] is False


def _synthetic_survey(rng, n=900, quarters=("2027-Q1", "2027-Q2", "2027-Q3"), shift=(0.0, 0.0, 0.25)):
    """SYNTHETIC household FIES responses (vectorised): P1 deteriorates in the third round, P2 stays flat."""
    frames = []
    cuts = (np.arange(len(S.ITEMS)) - 3.5) * 0.5
    for qi, q in enumerate(quarters):
        for p in ("P1", "P2"):
            lat = rng.normal(shift[qi] if p == "P1" else 0.0, 1, size=n)
            items = (lat[:, None] + rng.normal(0, 1, size=(n, len(S.ITEMS))) > cuts).astype(int)
            f = pd.DataFrame(items, columns=S.ITEMS)
            f.insert(0, "household_id", [f"{q}-{p}-{i}" for i in range(n)])
            f["province_code"], f["lgu_code"], f["quarter"], f["interview_date"] = p, "L", q, "2027-01-15"
            f["weight"], f["cluster_id"] = rng.uniform(0.5, 1.5, size=n), np.arange(n) // 20
            frames.append(f)
    return pd.concat(frames, ignore_index=True)


def test_fies_pipeline_on_synthetic_survey():
    df = _synthetic_survey(np.random.default_rng(1))
    assert S.validate(df) == []
    est = S.estimate(df)
    assert len(est) == 6 and est["prevalence_mod_sev"].between(0, 1).all()
    assert set(S.deterioration(est)["province_code"]) == {"P1", "P2"}
    bad = df.copy()
    bad.loc[0, "WORRIED"] = 3
    assert any("WORRIED" in e for e in S.validate(bad))


def test_deterioration_rule_operating_characteristics_synthetic():
    """Across 20 SYNTHETIC replicates: a real deterioration (P1) is detected almost always; the flat province (P2)
    is flagged only occasionally (the 5-point + 90%-bound rule still has a small false-positive rate)."""
    hit = fp = 0
    for seed in range(20):
        det = S.deterioration(S.estimate(_synthetic_survey(np.random.default_rng(seed)))).set_index("province_code")
        hit += int(det.loc["P1", "HIGH"])
        fp += int(det.loc["P2", "HIGH"])
    assert hit >= 18 and fp <= 3


def test_sample_size_is_monotone():
    assert S.sample_size(5) > S.sample_size(7) and S.sample_size(5, deff=1.0) < S.sample_size(5)


def test_expert_review_scoring_on_synthetic_ratings():
    rows = []
    for r in range(8):
        rows += [{"reviewer_id": r, "role": "DA", "item_type": "indicator_relevance", "item_id": "A1", "item_text": "", "rating": 4 if r < 7 else 2, "comment": ""},
                 {"reviewer_id": r, "role": "DA", "item_type": "category_plausibility", "item_id": "Q", "item_text": "", "rating": "agree", "comment": ""},
                 {"reviewer_id": r, "role": "DA", "item_type": "category_plausibility", "item_id": "R", "item_text": "", "rating": "agree" if r % 2 else "disagree", "comment": ""}]
    s = X.summary(pd.DataFrame(rows))
    assert s["items"][0]["i_cvi"] == pytest.approx(7 / 8) and s["items"][0]["acceptable"]
    assert s["fleiss_kappa_plausibility"] is not None


def test_prospective_register_and_no_outcome_yet(tmp_path):
    reg = PR.register()
    assert reg and all(v["verified"] for v in reg.values())
    empty = tmp_path / "outcomes.csv"
    empty.write_text("quarter,kind,province_code,value,published,source_url\n")
    res = PR.score(empty, reg)
    assert all(v["status"] == "NO ELIGIBLE OUTCOME YET" for v in res.values())


def test_prospective_scoring_ignores_outcomes_published_before_the_seal(tmp_path):
    reg = PR.register()
    f = tmp_path / "outcomes.csv"
    with f.open("w", newline="") as h:            # SYNTHETIC outcomes
        w = csv.writer(h)
        w.writerow(["quarter", "kind", "province_code", "value", "published", "source_url"])
        w.writerow(["2027-Q1", "SWS_H", "", "20.0", "2027-05-01", "synthetic"])
        w.writerow(["2027-Q1", "OCTA_BL", "", "5.0", "2020-01-01", "synthetic (published before the seal: must be ignored)"])
    res = PR.score(f, reg)
    firi = res["FIRI2_C3"]
    assert {r["unit"] for r in firi["rows"]} == {"region:SWS"}             # the pre-seal OCTA row was ignored
