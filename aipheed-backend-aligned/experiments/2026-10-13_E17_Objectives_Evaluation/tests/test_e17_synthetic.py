"""E17 synthetic tests (no project data): timing frame, label publication, fold rules, persistence, metrics, guard."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e17_lib as L  # noqa: E402
import guard  # noqa: E402

PROV = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
FEATS = L.NLP + [c for c in L.PSA] + ["tc_count", "poverty_incidence"]


def synth():
    rng = np.random.default_rng(0)
    qs = [L.qs(i) for i in range(L.qk("2021-Q1"), L.qk("2025-Q4") + 1)]
    f = pd.DataFrame([{"province_code": p, "quarter": q, **{c: float(rng.normal()) for c in FEATS}}
                      for q in qs for p in PROV])
    rounds = pd.DataFrame([{"quarter": q, "H": 10 + i % 7, "published": L.qstart(L.qs(L.qk(q) + 1)) + pd.Timedelta(days=45),
                            "definition_A": True} for i, q in enumerate(qs)])
    comp = pd.DataFrame([{"province_code": p, "quarter": q, "S1": float(rng.normal(12, 3))} for q in qs for p in PROV])
    return f, rounds, comp


def test_frame_timing_news_t_gov_t_minus_1():
    f, rounds, _ = synth()
    X = L.build_frame(f, rounds, [c for c in FEATS if c != "poverty_incidence"])
    t = L.qk("2023-Q2")
    row = X[(X["t"] == t) & (X["province_code"] == PROV[0])].iloc[0]
    src_t = f[(f["quarter"] == "2023-Q2") & (f["province_code"] == PROV[0])].iloc[0]
    src_t1 = f[(f["quarter"] == "2023-Q1") & (f["province_code"] == PROV[0])].iloc[0]
    assert row["FSSI"] == src_t["FSSI"] and row["food_cpi"] == src_t1["food_cpi"]
    assert "poverty_incidence" not in X.columns
    first = X[X["t"] == L.qk("2021-Q1")]
    assert first["food_cpi"].isna().all()                    # missing, never 0


def test_sws_feature_uses_only_rounds_published_before_origin():
    f, rounds, _ = synth()
    X = L.build_frame(f, rounds, [c for c in FEATS if c != "poverty_incidence"])
    # round of quarter q is published 45 days after q ends; origin of row t is start(t+1) -> latest = t-1
    row = X[X["quarter"] == "2024-Q2"].iloc[0]
    want = rounds.loc[rounds["quarter"] == "2024-Q1", "H"].iloc[0]
    assert row["sws_hunger"] == want


def test_label_publication_rule():
    _, rounds, _ = synth()
    t = L.qk("2024-Q2")
    assert L.label_published(rounds, "2024-Q1", t)           # q = t-1, round published 45 days after -> before start(t+1)
    assert not L.label_published(rounds, "2024-Q2", t)       # q = t is never known at start(t+1)


def test_strict_training_never_contains_unpublished_labels_and_r0_does():
    f, rounds, comp = synth()
    X = L.build_frame(f, rounds, [c for c in FEATS if c != "poverty_incidence"])
    lab = L.label_table(comp, 12.0)
    t = L.qk("2024-Q3")
    for k in (1, 3):
        tr, te = L.fold_data(X, lab, rounds, k, t, "strict")
        assert all(L.label_published(rounds, q, t) for q in tr["target_quarter"].unique())
        assert te["target_quarter"].iloc[0] == L.qs(t + k)
    tr0, _ = L.fold_data(X, lab, rounds, 1, t, "r0")
    assert L.qs(t) in set(tr0["target_quarter"])           # R0 admits the unpublished label of quarter t


def test_persistence_uses_latest_published_label():
    _, rounds, comp = synth()
    lab = L.label_table(comp, 12.0)
    t = L.qk("2024-Q3")
    p = L.persistence(lab, rounds, t, PROV)
    want = lab[(lab["quarter"] == "2024-Q2")].set_index("province_code")["y"]
    assert all(p[pc] == want[pc] for pc in PROV)


def test_single_class_training_predicts_constant():
    X = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    s, flag = L.fit_lgbm(X, np.array([1, 1, 1]), X)
    assert flag and (s == 1.0).all()
    s, flag = L.fit_lr(X, np.array([0, 0, 0]), X)
    assert flag and (s == 0.0).all()


def test_metrics_confusion_auc():
    y = np.array([1, 1, 0, 0, 1])
    p = np.array([1, 0, 0, 1, 1])
    s = np.array([0.9, 0.4, 0.2, 0.6, 0.8])
    m = L.cls_metrics(y, p, s)
    assert (m["TP"], m["FP"], m["FN"], m["TN"]) == (2, 1, 1, 1)
    assert m["accuracy"] == pytest.approx(0.6) and m["precision_HIGH"] == pytest.approx(2 / 3)
    assert m["ROC_AUC"] == pytest.approx(5 / 6)
    one = L.cls_metrics(np.array([1, 1]), np.array([1, 0]), np.array([0.9, 0.1]))
    assert one["ROC_AUC"] is None and one["balanced_accuracy"] is None


def test_bootstrap_identity():
    c = np.array([1, 0, 1, 1])
    q = np.array(["a", "a", "b", "b"])
    r = L.boot_acc_diff(c, c, q, n_boot=100)
    assert r["diff"] == 0 and r["ci_low"] == 0 and r["ci_high"] == 0


@pytest.mark.parametrize("path,write,want", [
    (guard.PROC / "fssi_quarterly.parquet", False, "deny"),
    (guard.PROC / "labels.parquet", False, "deny"),
    (guard.PROC / "psa_rice_prices.parquet", False, "allow" if False else "deny"),
    (guard.PROC / "features_fused.parquet", False, "allow"),
    (guard.ROOT / "backend" / "models" / "lgbm_best.pkl", False, "deny"),
    (guard.AL / "experiments" / "2026-10-13_E13_DA_Predictive_Accuracy" / "x.md", True, "deny"),
    (guard.EXP / "runs" / "x.csv", True, "allow"),
])
def test_guard(path, write, want):
    assert guard.decide(path, write) == want
