"""Completion checks for the selected model (FINAL) and the sealed challengers. Run: python -m pytest -q tests/test_final_completion.py"""
import glob, hashlib, json
from pathlib import Path
import numpy as np, pandas as pd
import pytest
from sklearn.metrics import roc_auc_score, average_precision_score

RN = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
K = ["key", "survey", "lead"]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["y_high"]]
LAB = LAB[LAB.lead == 1]


def final_preds():
    d = pd.concat([pd.read_csv(f, usecols=K + ["seed", "p"]) for f in glob.glob(str(RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd" / "FINAL__ENNS20*__1__*.csv"))])
    return d


def test_official_final_seal_unchanged():
    assert sha(RN / "aiPHeed_final_official_20261113" / "evidence" / "SEALED_FINAL_2027Q1_2028Q1.json").startswith("80b20aed")


def test_official_final_reproduced_by_independent_rerun():
    r = json.load(open(RN / "aiPHeed_final_seals_20261113" / "evidence" / "REPRO_official_FINAL.json"))
    assert r["PASS"] and r["rows"] == 25 and r["max_abs_diff_raw"] < 1e-4


@pytest.mark.parametrize("name", ["SEALED_FINAL_LG_2027Q1_2028Q1", "SEALED_ATTR_2027Q1_2028Q1"])
def test_experimental_seal_hashes(name):
    ev = RN / "aiPHeed_final_seals_20261113" / "evidence"
    assert (ev / f"{name}.sha256").read_text().split()[0] == sha(ev / f"{name}.json")


def test_final_five_seeds_three_rounds_present():
    d = final_preds()
    assert sorted(d.seed.unique()) == [1, 2, 3, 4, 168]
    assert d.groupby("survey").key.nunique().to_dict() == {"ENNS2018": 22, "ENNS2019": 25, "ENNS2021": 25}


EXPECTED = {"ENNS2018": "8/3/0/11", "ENNS2019": "11/2/2/10", "ENNS2021": "1/0/3/21", "POOLED": "20/5/5/42"}


@pytest.mark.parametrize("rnd", list(EXPECTED))
def test_final_confusion_matrices_as_reported(rnd):
    x = LAB.merge(final_preds().groupby(K, as_index=False).p.mean(), on=K)
    if rnd != "POOLED":
        x = x[x.survey == rnd]
    h, y = x.p >= .5, x.y_high == 1
    cm = f"{int((h & y).sum())}/{int((h & ~y).sum())}/{int((~h & y).sum())}/{int((~h & ~y).sum())}"
    assert cm == EXPECTED[rnd]


def test_final_pooled_probability_metrics_as_reported():
    x = LAB.merge(final_preds().groupby(K, as_index=False).p.mean(), on=K)
    assert abs(float(np.mean((x.p - x.y_high) ** 2)) - 0.1233) < 5e-4
    assert abs(roc_auc_score(x.y_high, x.p) - 0.8979) < 5e-4
    assert abs(average_precision_score(x.y_high, x.p) - 0.8462) < 5e-4


def test_no_training_round_violates_release_lag():
    r = json.load(open(RN / "aiPHeed_final_reliability_20261113" / "evidence" / "LEAK_origin_check.json"))
    assert r["fits_checked"] >= 110 and r["violations"] == []


def test_dromic_features_use_reports_published_before_cutoff():
    v = pd.read_csv(RN / "aiPHeed_final_dromic_20261113" / "evidence" / "DROMIC_LEADQ_province_values.csv")
    cut = json.load(open(RN / "aiPHeed_final_dromic_20261113" / "evidence" / "lead_cutoffs.json"))
    assert (pd.to_datetime(v.report_date) < pd.to_datetime(v.window.map(cut))).all()
    assert (pd.to_datetime(v.event_date) < pd.to_datetime(v.window.map(cut))).all()
