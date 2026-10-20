"""
tests/integration/test_rebuild_record.py
----------------------------------------
Rule 1 rebuild (scripts/rebuild_served_record.py): at the current cutoff it reproduces the served E49 probabilities
(within 1e-4), writes only to its output directory, never to data/e49 (or another served record, or
frontend/public), and the scheduler job is off by default and dry-runs under AIPHEED_SCHEDULER_DRY_RUN=1.
The full rebuild takes about two minutes; it runs once per module.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
WATCH = ["data/e36", "data/e48", "data/e49", "data/e53", "../frontend/public"]


def _snapshot() -> dict:
    out = {}
    for rel in WATCH:
        for f in sorted((BACKEND / rel).rglob("*")):
            if f.is_file():
                out[str(f)] = hashlib.md5(f.read_bytes()).hexdigest()
    return out


@pytest.fixture(scope="module")
def rebuilt(tmp_path_factory):
    sys.path.insert(0, str(BACKEND / "scripts"))
    import rebuild_served_record as RB

    out = tmp_path_factory.mktemp("rebuild") / "20261018"
    before = _snapshot()
    res = RB.rebuild(out_dir=out)
    return res, before, _snapshot(), out


def test_rebuild_reproduces_served_e49_probabilities(rebuilt):
    res, *_ = rebuilt
    served = json.loads((BACKEND / "data/e49/e49_record.json").read_text(encoding="utf-8"))
    sp = {(q["quarter"], c): v["p_high"] for q in served["quarters"] if q.get("lead", 1) == 1
          for c, v in q["provinces"].items()}
    assert len(sp) == 70 and set(res["probabilities"]) == set(sp)          # 13 backtests + 2026-Q4, x 5 provinces
    assert max(abs(sp[k] - res["probabilities"][k]) for k in sp) <= 1e-4
    assert res["origin"] == "2026-10-01" and res["forecast_quarter"] == "2026-Q4"


def test_rebuild_writes_only_its_output_directory(rebuilt):
    res, before, after, out = rebuilt
    assert before == after                                                   # nothing under data/e49 etc.
    for name in ("e49_record.json", "aiPHeed_E49_assessment_report.pdf", "model/E49_C2_calibration.json",
                 "model/E48_SERVING_BUNDLE.json", "model/E48-A1-LGBM_O2026-10-01.txt"):
        assert (out / name).is_file(), name
    rec = json.loads((out / "e49_record.json").read_text(encoding="utf-8"))
    se = rec["served_engine"]
    assert se["rebuild"]["served"] is False and se["rebuild"]["probabilities_replaced"] == 70
    assert "PREVIEW" not in se["name"] and "official system serves E36" not in se["why_served"]


def test_rebuild_calibration_matches_the_served_parameters(rebuilt):
    *_, out = rebuilt
    mine = json.loads((out / "model/E49_C2_calibration.json").read_text(encoding="utf-8"))["params_by_target_quarter"]
    served = json.loads((BACKEND / "data/e49/model/E49_C2_calibration.json").read_text(encoding="utf-8"))
    assert mine == served["params_by_target_quarter"]


def test_rebuild_refuses_a_served_directory():
    sys.path.insert(0, str(BACKEND / "scripts"))
    import rebuild_served_record as RB

    with pytest.raises(SystemExit, match="served record directory"):
        RB.rebuild(out_dir=BACKEND / "data" / "e49" / "rebuild")


def test_scheduler_rebuild_job_off_by_default_and_dry_run(monkeypatch):
    from app.tasks import scheduler as S

    assert S.REBUILD_ENABLED is False
    import scripts.rebuild_served_record as RB

    seen = {}

    def fake(dry_run=False, **_):
        seen["dry_run"] = dry_run
        return {"out_dir": "x", "dry_run": dry_run, "origin": "2026-10-01", "forecast_quarter": "2026-Q4",
                "content_sha256": "0"}

    monkeypatch.setattr(RB, "rebuild", fake)
    monkeypatch.setenv("AIPHEED_SCHEDULER_DRY_RUN", "1")
    assert S.run_rebuild_record()["dry_run"] is True and seen["dry_run"] is True
    monkeypatch.delenv("AIPHEED_SCHEDULER_DRY_RUN")
    S.run_rebuild_record()
    assert seen["dry_run"] is False
    text = (BACKEND / "deploy/scheduler.env.example").read_text(encoding="utf-8").splitlines()
    assert "AIPHEED_REBUILD_RECORD=0" in text
