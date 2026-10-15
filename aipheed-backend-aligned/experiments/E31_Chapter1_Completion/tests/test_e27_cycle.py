"""E27 regression tests for the automatic quarterly cycle (app/quarterly/cycle.py), on SYNTHETIC files only.

The synthetic 'future' inputs (September 2026 round, July-November 2026 CPI) are invented numbers in a temporary
directory; they stand in for files the researcher would authorize later and never touch real protected data."""
import hashlib
import json
import shutil

import numpy as np
import pandas as pd
import pytest

import _paths  # noqa: F401
from _paths import EXP
from app.quarterly.cycle import derive_evidence, run_cycle
from app.quarterly.forecaster_v2 import make_pcf_forecaster
from app.quarterly.ledger import Ledger
from app.quarterly.periods import Quarter

PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
REAL = _paths.BD


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _drop(inbox, sid, kind, df, obs_end, avail, start="2021-Q1", end_date=None, **extra):
    f = inbox / f"{sid}.csv"
    df.to_csv(f, index=False)
    m = {"source_id": sid, "kind": kind, "path": f.name, "sha256": _sha(f), "observation_start": start,
         "observation_end": obs_end, "available_at": avail, "authorized_by": "synthetic test",
         "authorization_ref": "test", **extra}
    if end_date:
        m["observation_end_date"] = end_date
    (inbox / f"{sid}.manifest.json").write_text(json.dumps(m))
    return f


@pytest.fixture
def root(tmp_path):
    r = tmp_path / "backend"
    (r / "config").mkdir(parents=True)
    (r / "data" / "inbox").mkdir(parents=True)
    (r / "data" / "ledger").mkdir(parents=True)
    fp = json.loads((REAL / "config" / "forecast_period.json").read_text(encoding="utf-8"))
    (r / "config" / "forecast_period.json").write_text(json.dumps(fp))
    (r / "config" / "quarterly_sources.json").write_text(json.dumps({"sources": []}))
    (r / "config" / "authorization.json").write_text(json.dumps(
        {"window_start": "2021-Q1", "authorized_until": "2026-Q4", "authorized_by": "synthetic"}))
    (r / "config" / "adviser_approvals.json").write_text(json.dumps({"A1_approved": False, "A3_approved": False}))
    shutil.copy(REAL / "config" / "evidence_status.json", r / "config" / "evidence_status.json")
    rng = np.random.default_rng(1)
    qs = [str(Quarter.parse("2021-Q1").shift(i)) for i in range(24)]            # 2021-Q1 .. 2026-Q4
    rounds = pd.DataFrame([{"quarter": q, "round": q, "H": 14 + rng.normal(), "published":
                            str(Quarter.parse(q).next().start().date()), "published_eff":
                            str(Quarter.parse(q).next().start().date()), "date_type": "verified",
                            "definition_A": True, "source": "production"} for q in qs[1:-1]])   # through 2026-Q3
    D = pd.DataFrame([{"province_code": p, "quarter": q, "D": rng.normal(), "F": 3.0} for q in qs[:-1] for p in PROVS])
    D["D"] -= D.groupby("quarter")["D"].transform("mean")
    S1 = D.merge(rounds[["quarter", "H"]], on="quarter").assign(S1=lambda x: x["H"] + 2 * x["D"])[
        ["province_code", "quarter", "S1"]]
    N = D[D["quarter"] >= "2022-Q1"].assign(Dnow=lambda x: x["D"])[["province_code", "quarter", "Dnow"]]
    N = pd.concat([N, pd.DataFrame([{"province_code": p, "quarter": "2026-Q4", "Dnow": 0.1} for p in PROVS])])
    ib = r / "data" / "inbox"
    _drop(ib, "sws_rounds", "label", rounds, "2026-Q3", "2026-11-20T00:00:00+08:00", start="2021-Q2")
    _drop(ib, "s1_labels", "label", S1, "2026-Q3", "2026-11-20T00:00:00+08:00")
    _drop(ib, "d_quarterly_panel", "indicator", D, "2026-Q3", "2026-10-07T00:00:00+08:00")
    _drop(ib, "dnow_panel", "indicator", N, "2026-Q4", "2026-12-05T00:00:00+08:00", start="2022-Q1",
          end_date="2026-11-30T23:59:59+08:00")
    lg = pd.read_csv(REAL / "data" / "inputs" / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    _drop(ib, "lgu_vulnerability", "static", lg, "2021-Q1", "2026-10-14T00:00:00+08:00")
    card = ib / "card.json"
    card.write_text('{"name": "PCF21 (synthetic test)"}')
    (ib / "card.manifest.json").write_text(json.dumps(
        {"source_id": "pcf_model_card", "kind": "model", "path": "card.json", "sha256": _sha(card),
         "observation_start": "2021-Q1", "observation_end": "2026-Q2", "available_at": "2026-10-14T00:00:00+08:00",
         "authorized_by": "synthetic", "authorization_ref": "test"}))
    return r


def _cycle(root, now):
    return run_cycle(root, now=pd.Timestamp(now, tz="Asia/Manila"), forecaster=lambda ev: make_pcf_forecaster(ev))


def test_cycle_waits_for_the_cutoff_then_forecasts_seals_and_advances(root):
    early = _cycle(root, "2026-12-15")
    assert {x["result"] for x in early["inbox"]} == {"REGISTERED"}
    assert early["update"]["status"] == "INSUFFICIENT_DATA"
    deps = early["update"]["dependencies"]
    assert [d["id"] for d in deps if d["blocking"]] == ["information_cutoff"]
    assert all(d["affects"] == "forecast for Q1 2027 (January–March 2027)" for d in deps)
    assert early["seals"] == []
    rec = _cycle(root, "2027-01-02")
    assert rec["update"]["status"] == "READY"
    assert {s["result"] for s in rec["seals"]} == {"SEALED"}
    assert {s["arm"] for s in rec["seals"]} == {"PCF21:lead1", "B1:lead1", "B1p:lead1", "CLIM:lead1"}
    assert rec["advanced_to"] == "2027-Q2"
    L = Ledger(root / "data" / "ledger" / "T1_A.jsonl")
    seals = L.seals()
    assert len(seals) == 4 and all(e["payload"]["threshold"] is not None for e in seals)
    assert all(e["payload"]["target_quarter"] == "2027-Q1" for e in seals)
    again = _cycle(root, "2027-01-03")                    # next period: inputs stale, nothing new is sealed
    assert again["update"]["status"] == "INSUFFICIENT_DATA" and again["update"]["target_quarter"] == "2027-Q2"
    assert len(Ledger(root / "data" / "ledger" / "T1_A.jsonl").seals()) == 4
    ev = json.loads((root / "data" / "evidence_status_derived.json").read_text())
    assert ev["T1"]["1"]["status"] == "EXPERIMENTAL"


def test_cycle_refuses_to_seal_after_the_target_quarter_ended(root):
    rec = _cycle(root, "2027-04-02")                     # forecast for 2027-Q1 attempted after it ended
    assert rec["update"]["status"] == "READY"
    assert {s["result"] for s in rec["seals"]} == {"REFUSED"}
    assert "advanced_to" not in rec                       # not rolled forward: the cycle failed visibly


def test_inbox_refuses_never_filters(root):
    ib = root / "data" / "inbox"
    bad = pd.DataFrame([{"province_code": PROVS[0], "quarter": "2020-Q4", "D": 1.0, "F": 2.0},
                        {"province_code": PROVS[0], "quarter": "2021-Q1", "D": 1.0, "F": 2.0}])
    _drop(ib, "x_pre2021", "indicator", bad, "2021-Q1", "2021-05-01T00:00:00+08:00")
    late = pd.DataFrame([{"province_code": PROVS[0], "quarter": "2027-Q1", "D": 1.0, "F": 2.0}])
    _drop(ib, "x_unauthorized", "indicator", late, "2027-Q1", "2027-05-01T00:00:00+08:00")
    early_pub = pd.DataFrame([{"province_code": PROVS[0], "quarter": "2026-Q3", "D": 1.0, "F": 2.0}])
    _drop(ib, "x_early", "indicator", early_pub, "2026-Q3", "2026-09-15T00:00:00+08:00")
    f = _drop(ib, "x_tampered", "indicator", early_pub, "2026-Q3", "2026-10-15T00:00:00+08:00")
    f.write_text(f.read_text() + "\n" + f"{PROVS[1]},2026-Q3,9,9\n")
    res = {x["source_id"]: x for x in _cycle(root, "2026-12-15")["inbox"]}
    assert res["x_pre2021"]["result"] == "REFUSED" and "outside" in res["x_pre2021"]["reason"]
    assert res["x_unauthorized"]["result"] == "REFUSED" and "authorized limit" in res["x_unauthorized"]["reason"]
    assert res["x_early"]["result"] == "REFUSED" and "precedes" in res["x_early"]["reason"]
    assert res["x_tampered"]["result"] == "REFUSED" and "SHA-256" in res["x_tampered"]["reason"]


def test_outcome_ingestion_records_measured_values_and_refuses_unpublished(root):
    _cycle(root, "2027-01-02")                           # seals 2027-Q1
    od = root / "data" / "outcomes"
    a = json.loads((root / "config" / "authorization.json").read_text())
    a["authorized_until"] = "2027-Q1"                    # the researcher authorizes 2027-Q1 outcomes
    (root / "config" / "authorization.json").write_text(json.dumps(a))
    rows = [{"province_code": p, "target_quarter": "2027-Q1", "H": 15.0, "D": d, "H_round": "March 2027 (synthetic)",
             "H_publication_date": "2027-03-25", "D_publication_date": "2027-04-07"}
            for p, d in zip(PROVS, [1, -1, .5, -.5, 0])]
    f = od / "o.csv"
    pd.DataFrame(rows).to_csv(f, index=False)
    m = {"target_quarter": "2027-Q1", "target": "T1", "path": "o.csv", "sha256": _sha(f), "authorized_by": "test",
         "authorized_on": "2027-05-01"}
    (od / "o.manifest.json").write_text(json.dumps(m))
    r1 = _cycle(root, "2027-05-02")
    assert r1["outcomes"] == [{"target_quarter": "2027-Q1", "result": "REFUSED",
                               "reason": "H_publication_date precedes the end of 2027-Q1: not a published outcome"}]
    rows = [{**x, "H_publication_date": "2027-04-20"} for x in rows]
    pd.DataFrame(rows).to_csv(f, index=False)
    m["sha256"] = _sha(f)
    (od / "o.manifest.json").write_text(json.dumps(m))
    r2 = _cycle(root, "2027-05-03")
    assert r2["outcomes"] == [{"target_quarter": "2027-Q1", "result": "OUTCOME_RECORDED"}]
    L = Ledger(root / "data" / "ledger" / "T1_A.jsonl")
    s = L.score("PCF21:lead1")
    assert s["scored_dates"] == 1 and set(s["baselines"]) >= {"baseline_persistence", "reference_always_high"}


def test_evidence_is_validated_only_with_adviser_approval_and_a_successful_look(tmp_path):
    L = Ledger(tmp_path / "l.jsonl")
    ev = derive_evidence(L, {"A1_approved": True}, {})
    assert {v["status"] for v in ev.values()} == {"EXPERIMENTAL"}   # approved rule, but no look has been taken
    ev = derive_evidence(L, {}, {})
    assert ev["1"]["a1_approved_by_adviser"] is False


def test_missing_price_pressure_input_does_not_block_the_risk_forecast(root):
    """E27 fix: Dnow (October-November CPI) feeds only the constructed price-pressure indicator."""
    ib = root / "data" / "inbox"
    m = json.loads((ib / "dnow_panel.manifest.json").read_text())
    N = pd.read_csv(ib / "dnow_panel.csv", dtype={"province_code": str})
    N = N[N["quarter"] <= "2026-Q3"]
    _drop(ib, "dnow_panel", "indicator", N, "2026-Q3", "2026-10-07T00:00:00+08:00", start=m["observation_start"])
    rec = _cycle(root, "2027-01-02")
    assert rec["update"]["status"] == "READY"
    dep = {d["id"]: d for d in rec["update"]["dependencies"]}
    assert dep["provincial_D_now"]["blocking"] is False and dep["provincial_D_now"]["status"] == "STALE"
    full = json.loads((root / "data" / "quarterly_runs" / "2027-Q1" / "forecast_record.json").read_text())
    prov = full["forecast"]["leads"]["1"]["provinces"]
    assert all(v["price_pressure"]["status"] == "MISSING_INPUT" for v in prov.values())
    assert all(0 <= v["risk"]["p_high"] <= 1 for v in prov.values())
    assert {s["result"] for s in rec["seals"]} == {"SEALED"}
