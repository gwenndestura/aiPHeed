"""E32 training, artifact and inference tests: the saved artifacts reproduce the frozen predictions, the frozen
record is intact, and the evaluation is reproducible."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E32 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E32 / "runner"))
import e32_common as C  # noqa: E402
import e32_lib as L  # noqa: E402

FROZEN = E32 / "frozen" / "E32_PROSPECTIVE.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(FROZEN.read_text(encoding="utf-8"))


def test_frozen_record_hash_and_protocol(rec):
    assert hashlib.sha256(FROZEN.read_bytes()).hexdigest() == (E32 / "frozen" / "E32_PROSPECTIVE.sha256").read_text().split()[0]
    assert rec["protocol_sha256"] == (E32 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert rec["origin"] == "2026-10-01" and {b["target_quarter"] for b in rec["leads"].values()} == {"2026-Q4", "2027-Q1"}


@pytest.mark.parametrize("k", [1, 2])
def test_saved_artifacts_reproduce_frozen_predictions(rec, k):
    import joblib
    import lightgbm as lgb

    blk = rec["leads"][str(k)]
    X = pd.DataFrame(blk["features"])
    Z = np.nan_to_num(X[L.FEATURES].to_numpy(float), nan=0.0)
    a = joblib.load(E32 / "models" / f"E32-LR_O2026-10-01_lead{k}.joblib")
    p_lr = a["model"].predict_proba(a["scaler"].transform(Z))[:, 1]
    assert np.allclose(p_lr, [blk["arms_p_high"]["E32-LR"][p] for p in X["province_code"]], atol=1e-9)
    b = lgb.Booster(model_file=str(E32 / "models" / f"E32-LGBM_O2026-10-01_lead{k}.txt"))
    p_gb = b.predict(X[L.FEATURES].astype(float))
    assert np.allclose(p_gb, [blk["arms_p_high"]["E32-LGBM"][p] for p in X["province_code"]], atol=1e-9)


def test_inference_recomputes_frozen_pcfn_and_ensemble(rec):
    d = L.Data()
    t = C.qk("2026-Q3")
    for k in (1, 2):
        blk = rec["leads"][str(k)]["arms_p_high"]
        for arm in ("E32-PCFN", "E32-ENS", "PCF21", "B1"):
            f = {"E32-PCFN": L.pcfn, "E32-ENS": L.ens, "PCF21": L.pcf21}.get(arm)
            got = f(d, t, k) if f else L.references(d, t, k)[arm]
            assert all(abs(got[p] - blk[arm][p]) < 1e-12 for p in C.PROVS), arm


def test_operational_inputs_are_available_at_origin(rec):
    """A4 data requirements: at O = 2026-10-01 the latest hunger value is 2026-Q2 (posted 2026-08-24, the September
    round was posted 2026-10-14), D is through 2026-Q2, Dnow/rice are July-August 2026 and news is 2026-Q3."""
    blk = rec["leads"]["1"]
    assert blk["H_last_quarter"] == "2026-Q2" and blk["last_label_quarter"] == "2026-Q2"
    X = pd.DataFrame(blk["features"])
    assert X[["D_last", "Dnow", "rice_rel"]].notna().all().all()
    assert blk["news_evidence_quarter"] == "2026-Q3"


def test_evaluation_runs_are_byte_identical():
    runs = sorted(p for p in (E32 / "runs").iterdir() if p.is_dir() and p.name.startswith("2026"))
    h = {hashlib.sha256((r / "predictions.csv").read_bytes()).hexdigest() for r in runs}
    assert len(runs) >= 2 and len(h) == 1


def test_selection_and_acceptance_follow_the_protocol():
    r = json.loads(sorted((E32 / "runs").glob("2026*/results.json"))[0].read_text())
    mb = r["selection"]["mean_per_date_brier_selection_lead1"]
    best = min(mb.values())
    assert r["selection"]["chosen"] == next(a for a in L.SIMPLICITY if mb[a] <= best + 0.005)
    acc = r["acceptance"]
    b = acc["mean_per_date_brier_all_lead1"]
    assert acc["A1_brier_below_PCF21"] == (b[acc["model"]] < b["PCF21"])
    assert acc["A2_brier_not_worse_than_persistence"] == (b[acc["model"]] <= b["B1"])
