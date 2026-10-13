"""
scripts/build_revised_forecasts.py
----------------------------------
Builds the time-valid historical forecasts of the revised LightGBM forecaster
(app/ml/training/revised_trainer.py) for every quarter of the approved window, and
writes them to a NEW artifact (never overwrites). No target-quarter label is read.

    PYTHONPATH=. python scripts/build_revised_forecasts.py --reference retrospective
        -> data/revised/revised_forecasts_retrospective.parquet  (+ _meta.json)   [served by /api/v1/assessments]
    PYTHONPATH=. python scripts/build_revised_forecasts.py --reference approved --out <experiment folder>
        -> evaluation-only artifact using 14.345 (leakage-affected on 2021-2025; never served)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import scripts.supplementary.devprotocol_rule_l as D
from app.ml.training import datadriven_trainer as DD
from app.ml.training import revised_trainer as RT

QUARTERS = [f"{y}-Q{k}" for y in range(2021, 2026) for k in (1, 2, 3, 4)][1:]   # 2021-Q2 .. 2025-Q4
OUT_DIR = Path("data/revised")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(reference: str, out_dir: Path, model: str = "revised") -> Path:
    labels = RT.TrainingLabels(RT.load_stress())
    as_of = RT.RETROSPECTIVE_AS_OF if reference == "retrospective" else RT.PROSPECTIVE_AS_OF
    tau, ref_q = labels.reference(as_of)
    frame, _ = D.development_frame()
    rows, cal = [], {}
    for q in QUARTERS:
        f = RT.forecast_quarter(frame, labels, q, tau) if model == "revised" else DD.forecast_quarter(frame, labels, q, tau)
        ev = RT.price_evidence(q)
        r = f.rows.merge(ev, on="province_code", how="left")
        r["tau"], r["n_train_quarters"] = tau, f.n_train_quarters
        rows.append(r)
        cal[q] = f.calibration
    out = pd.concat(rows, ignore_index=True)
    out["origin"] = out["origin"].astype(str)
    out["sws_published"] = out["sws_published"].astype(str)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "revised_forecasts" if model == "revised" else "datadriven_forecasts"
    path = out_dir / f"{stem}_{reference}.parquet"
    if path.exists():
        raise FileExistsError(f"{path} exists; refusing to overwrite")
    out.to_parquet(path, index=False)
    meta = {"generated_utc": datetime.now(timezone.utc).isoformat(), "reference": reference,
            "tau": tau, "tau_as_of": str(as_of.date()), "tau_quarters": ref_q,
            "served": reference == "retrospective",
            "leakage_note": None if reference == "retrospective" else
            "14.345 uses labels up to 2025-Q4; on 2021-2025 quarters it is leakage-affected (evaluation only)",
            "model": ({"family": "LightGBM", "params": RT.LGBM_PARAMS, "inputs": RT.INPUTS,
                       "monotone": RT.MONOTONE, "class_weight": None} if model == "revised" else
                      {"family": "LightGBM", "params": DD.PARAMS, "groups": DD.GROUPS, "monotone_up": sorted(DD.MONOTONE_UP),
                       "class_weight": None, "selection": "training-only inner walk-forward (E7 protocol)"}),
            "model_variant": model,
            "calibration_by_quarter": cal if model == "revised" else {q: {"applied": False, "reason": "not evaluated for this variant"} for q in cal},
            "selection_by_quarter": cal if model == "datadriven" else None,
            "sha256": {"artifact": sha(path), "labels": sha(RT.LABELS_PATH), "psa": sha(RT.PSA_PATH),
                       "revised_trainer": sha(Path(RT.__file__)), "datadriven_trainer": sha(Path(DD.__file__)), "risk_score_v2": sha(Path(RT.R.__file__))}}
    path.with_name(path.stem + "_meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", choices=["retrospective", "approved"], default="retrospective")
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--model", choices=["revised", "datadriven"], default="revised")
    a = ap.parse_args(argv)
    print(build(a.reference, Path(a.out), a.model))
    return 0


if __name__ == "__main__":
    sys.exit(main())
