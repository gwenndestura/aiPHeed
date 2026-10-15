"""
scripts/quarterly_update.py
---------------------------
The single documented quarterly update process (E23). Run from aipheed-backend-aligned/.

    # 1. register each new input (hash computed from the bytes; authorization recorded)
    python -m scripts.quarterly_update register --id news_2027Q1 --kind news --path <file> \
        --obs-start 2027-Q1 --obs-end 2027-Q1 --available-at 2027-03-31T23:59:59+08:00 \
        --authorized-by "<name>" --authorization-ref "<email/date>"
    # 2. run the cycle for the configured period (writes ONE forecast record for API, dashboard and PDF)
    python -m scripts.quarterly_update run
    # 3. after the cycle closes, roll the configuration to the next quarter
    python -m scripts.quarterly_update advance
    # E24v2: reconstruct a PAST cycle from authorized files (labelled REPLAY; never the live record)
    python -m scripts.quarterly_update replay --config config/replay_2026Q3.json

Nothing here trains, promotes or publishes a model. A forecast is attached only when every requirement
passes, the cutoff has passed and a promoted forecaster exists; otherwise the record says what is missing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from app.quarterly.config import load_period, save_period
from app.quarterly.forecaster_v2 import make_pcf_forecaster
from app.quarterly.registry import Registry, SnapshotStore
from app.quarterly.update import run_update

PERIOD = Path("config/forecast_period.json")
REGISTRY = Path("config/quarterly_sources.json")
STORE = Path("data/quarterly_store")
RECORDS = Path("data/quarterly_runs")
EVIDENCE = Path("config/evidence_status.json")


def forecaster():
    ev = json.loads(EVIDENCE.read_text(encoding="utf-8")) if EVIDENCE.exists() else {}
    return make_pcf_forecaster(ev)


def news_loader(entry):
    p = Path(entry.path)
    return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p, dtype={"province_code": str})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register")
    for a in ("--id", "--kind", "--path"):
        r.add_argument(a, required=True)
    for a in ("--obs-start", "--obs-end", "--available-at", "--authorized-by", "--authorization-ref",
              "--revision-note", "--granularity"):
        r.add_argument(a, default=None)
    r.add_argument("--unauthorized", action="store_true")
    run = sub.add_parser("run")
    run.add_argument("--now", default=None, help="override the clock (testing / reproducing a past run)")
    sub.add_parser("advance")
    rp = sub.add_parser("replay")
    rp.add_argument("--config", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "register":
        reg = Registry(REGISTRY)
        e = reg.register(a.id, a.kind, a.path, observation_start=a.obs_start, observation_end=a.obs_end,
                         available_at=a.available_at, authorized=not a.unauthorized, authorized_by=a.authorized_by,
                         authorization_ref=a.authorization_ref, revision_note=a.revision_note, granularity=a.granularity)
        reg.save()
        print(json.dumps({"source_id": e.source_id, "vintage": e.vintage, "sha256": e.sha256}, indent=2))
    elif a.cmd == "run":
        period = load_period(PERIOD)
        rec = run_update(period, Registry(REGISTRY), RECORDS, store=SnapshotStore(STORE), news_loader=news_loader,
                         forecaster=forecaster(), now=pd.Timestamp(a.now) if a.now else None)
        print(json.dumps({k: rec[k] for k in ("status", "missing", "labels", "content_sha256")}, indent=2,
                         ensure_ascii=False))
    elif a.cmd == "replay":
        period = load_period(Path(a.config))
        rec = run_update(period, Registry(REGISTRY), RECORDS, store=SnapshotStore(STORE), news_loader=news_loader,
                         forecaster=forecaster(), replay=True)
        print(json.dumps({k: rec[k] for k in ("status", "mode", "missing", "context_missing", "content_sha256")},
                         indent=2, ensure_ascii=False))
    elif a.cmd == "advance":
        p = load_period(PERIOD)
        save_period(p.advanced(), PERIOD)
        print(f"advanced: reference {p.reference_quarter} -> {p.advanced().reference_quarter}; "
              f"target {p.target_quarter} -> {p.advanced().target_quarter}. Re-declare the cutoff if needed.")


if __name__ == "__main__":
    main()
