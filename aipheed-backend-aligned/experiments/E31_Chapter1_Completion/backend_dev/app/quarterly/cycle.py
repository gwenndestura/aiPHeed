"""
app/quarterly/cycle.py  (E27)
-----------------------------
The automatic quarterly cycle. Safe to run as often as wanted (daily, or by hand): every step is idempotent.

  1. INBOX     Authorized files dropped in data/inbox/ with a manifest (<name>.manifest.json) are validated and
               registered. A file is REFUSED, never filtered, if its hash differs from the manifest, if any row lies
               before the study window or after the authorized limit, if it has no publication time, or if that time
               precedes the end of its observation period. Refusals are recorded with the reason.
  2. UPDATE    run_update() for the configured period. A forecast exists only when every blocking input is OK and
               the information cutoff has passed; otherwise the record lists each missing dependency, the forecast
               period it blocks, who supplies it and when it is normally released.
  3. SEAL      A READY forecast is sealed in the ledger BEFORE its outcome can exist (PCF21 candidate plus the
               persistence, calibrated-persistence and climatology references at the same origin, with the threshold
               in force). The ledger refuses a seal once the target quarter has ended.
  4. OUTCOMES  Authorized outcome files (data/outcomes/<name>.manifest.json) are validated and recorded as MEASURED
               H and D; a quarter with no production round is declared NO_OUTCOME (final).
  5. EVIDENCE  The validation status shown to users is DERIVED from the ledger: a lead becomes VALIDATED only after a
               pre-registered A1 look claims success AND the adviser approval file approves amendment A1 (and A3,
               if approved, is also met). Otherwise every forecast is EXPERIMENTAL.
  6. ADVANCE   After a READY forecast is sealed and the cutoff has passed, the period rolls to the next quarter.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.quarterly.config import ForecastPeriod, load_period, save_period
from app.quarterly.ledger import Ledger, LedgerRefused
from app.quarterly.periods import PH_TZ, Quarter, to_ph
from app.quarterly.registry import Registry, SnapshotStore, sha256_file
from app.quarterly.update import run_update

PROVINCES = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
QUARTER_COLUMNS = ("quarter", "target_quarter")
MONTH_COLUMNS = ("month",)


class InboxRefused(Exception):
    pass


# ============================================================================================ 1. inbox
def _quarter_end(q: str) -> pd.Timestamp:
    return Quarter.parse(q).end()


def validate_inbox_item(manifest: dict, auth: dict, base: Path) -> dict:
    """Check one researcher-supplied file against its manifest and the authorization window. Raises InboxRefused."""
    need = ("source_id", "kind", "path", "sha256", "observation_start", "observation_end", "available_at",
            "authorized_by", "authorization_ref")
    miss = [k for k in need if not manifest.get(k)]
    if miss:
        raise InboxRefused(f"manifest fields missing: {miss}")
    p = Path(manifest["path"])
    p = p if p.is_absolute() else base / p
    if not p.exists():
        raise InboxRefused(f"file not found: {p}")
    if len(manifest["sha256"]) != 64 or sha256_file(p) != manifest["sha256"].lower():
        raise InboxRefused("file bytes do not match the manifest SHA-256 (full 64-character hash required)")
    lo, hi = Quarter.parse(auth["window_start"]), Quarter.parse(auth["authorized_until"])
    os_, oe = Quarter.parse(manifest["observation_start"]), Quarter.parse(manifest["observation_end"])
    if os_ < lo:
        raise InboxRefused(f"observation period starts {os_} before the study window {lo}: refused, not filtered")
    if oe > hi:
        raise InboxRefused(f"observation period ends {oe} after the authorized limit {hi}: refused, not filtered")
    avail = to_ph(manifest["available_at"])
    # data that end inside a quarter (e.g. October-November CPI) give their exact last date
    obs_end = to_ph(manifest["observation_end_date"]) if manifest.get("observation_end_date") \
        else _quarter_end(str(oe)).floor("s")
    if manifest.get("observation_end_date") and Quarter.of(obs_end) != oe:
        raise InboxRefused("observation_end_date is not inside observation_end")
    if manifest["kind"] in ("label", "indicator", "news") and avail < obs_end:
        raise InboxRefused("publication time precedes the end of the observation period")
    if p.suffix.lower() == ".csv":
        df = pd.read_csv(p, dtype=str)
        for c in QUARTER_COLUMNS:
            if c in df.columns:
                qq = df[c].dropna().map(Quarter.parse)
                if (qq < lo).any() or (qq > hi).any():
                    raise InboxRefused(f"column {c!r} holds quarters outside {lo}..{hi}: refused, not filtered")
        for c in MONTH_COLUMNS:
            if c in df.columns:
                mm = pd.to_datetime(df[c].dropna() + "-01", errors="coerce")
                if mm.isna().any() or (mm < lo.start().tz_localize(None)).any() or \
                        (mm > hi.end().tz_localize(None)).any():
                    raise InboxRefused(f"column {c!r} holds months outside the authorized window: refused")
        for c in manifest.get("required_columns", []):
            if c not in df.columns:
                raise InboxRefused(f"required column {c!r} missing")
    return {"path": str(p), "sha256": manifest["sha256"].lower()}


def ingest_inbox(inbox: Path, reg: Registry, auth: dict) -> list[dict]:
    log = inbox / "processed.jsonl"
    done = set()
    if log.exists():
        done = {json.loads(l)["sha256"] for l in log.read_text(encoding="utf-8").splitlines() if l.strip()}
    out = []
    for mf in sorted(inbox.glob("*.manifest.json")):
        m = json.loads(mf.read_text(encoding="utf-8"))
        if m.get("sha256", "").lower() in done:
            continue
        rec = {"manifest": mf.name, "source_id": m.get("source_id"), "sha256": m.get("sha256", "").lower(),
               "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        try:
            v = validate_inbox_item(m, auth, inbox)
            e = reg.register(m["source_id"], m["kind"], v["path"], observation_start=m["observation_start"],
                             observation_end=m["observation_end"], available_at=m["available_at"], authorized=True,
                             authorized_by=m["authorized_by"], authorization_ref=m["authorization_ref"],
                             revision_note=m.get("revision_note"), granularity=m.get("granularity"),
                             required_columns=m.get("required_columns", []))
            rec.update(result="REGISTERED", vintage=e.vintage)
        except (InboxRefused, ValueError) as ex:
            rec.update(result="REFUSED", reason=str(ex))
        out.append(rec)
        with open(log, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(rec) + "\n")
    reg.save()
    return out


# ============================================================================================ 3. seal
def _laplace(y: pd.Series) -> float:
    return float((y.sum() + 1.0) / (len(y) + 2.0))


def reference_probabilities(labels: pd.DataFrame, tau: float, reference_quarter: str, lead: int = 1) -> dict:
    """Persistence (last published label), calibrated persistence (Laplace rate of HIGH after the same last label,
    over published label pairs k quarters apart) and climatology (Laplace rate), from S1 labels <= reference-1."""
    t = Quarter.parse(reference_quarter).index
    S = labels.copy()
    S["qi"] = S["quarter"].map(lambda q: Quarter.parse(q).index)
    S = S[S["qi"] <= t - 1]
    S["y"] = (S["S1"] > tau).astype(int)
    piv = S.pivot_table(index="qi", columns="province_code", values="y")
    last_q = int(S["qi"].max())
    pairs = []
    for q0 in piv.index:
        if q0 + lead in piv.index:
            for p in piv.columns:
                a, b = piv.loc[q0, p], piv.loc[q0 + lead, p]
                if pd.notna(a) and pd.notna(b):
                    pairs.append((int(a), int(b)))
    pr = pd.DataFrame(pairs, columns=["y_last", "y"]) if pairs else pd.DataFrame(columns=["y_last", "y"])
    out = {"persistence": {}, "calibrated_persistence": {}, "climatology": {}}
    clim = _laplace(S["y"])
    for p in PROVINCES:
        yl = int(piv.loc[last_q, p])
        out["persistence"][p] = float(yl)
        out["calibrated_persistence"][p] = _laplace(pr[pr["y_last"] == yl]["y"]) if len(pr) else 0.5
        out["climatology"][p] = clim
    out["last_label_quarter"] = str(Quarter(last_q // 4, last_q % 4 + 1))
    return out


def seal_record(rec: dict, ledger: Ledger, labels: pd.DataFrame, now: datetime | None = None) -> list[dict]:
    """Seal the READY forecast of a record and its references. Idempotent: an existing seal is reported, not
    duplicated; a refused seal (e.g. target already ended) is reported with the reason."""
    fc = rec.get("forecast") or {}
    res = []
    origin = fc.get("origin")
    cutoff = rec["period"]["cutoff"]
    tau = fc.get("threshold")
    model_sha = hashlib.sha256(json.dumps(fc.get("model", {}), sort_keys=True).encode()).hexdigest()
    inputs = [{**i, "authorized": True} for i in fc.get("inputs", [])]
    for k, blk in (fc.get("leads") or {}).items():
        q = blk["target_quarter"]
        refs = reference_probabilities(labels, tau, fc["reference_quarter"], int(k))
        arms = [(f"PCF21:lead{k}", "candidate", {p: v["risk"]["p_high"] for p, v in blk["provinces"].items()}),
                (f"B1:lead{k}", "baseline_persistence", refs["persistence"]),
                (f"B1p:lead{k}", "baseline_calibrated_persistence", refs["calibrated_persistence"]),
                (f"CLIM:lead{k}", "reference_climatology", refs["climatology"])]
        for arm, role, probs in arms:
            try:
                e = ledger.seal(arm=arm, role=role, target_quarter=q, origin=origin, info_cutoff=cutoff,
                                probabilities=probs, model_sha256=model_sha, inputs=inputs, now=now, threshold=tau)
                res.append({"arm": arm, "target_quarter": q, "result": "SEALED", "seq": e["seq"],
                            "entry_hash": e["entry_hash"]})
            except LedgerRefused as ex:
                res.append({"arm": arm, "target_quarter": q, "result": "ALREADY_SEALED" if "already sealed" in str(ex)
                            else "REFUSED", "reason": str(ex)})
    return res


# ============================================================================================ 4. outcomes
OUTCOME_COLUMNS = ("province_code", "target_quarter", "H", "D", "H_round", "H_publication_date", "D_publication_date")


def ingest_outcomes(outdir: Path, ledger: Ledger, auth: dict) -> list[dict]:
    res = []
    for mf in sorted(outdir.glob("*.manifest.json")):
        m = json.loads(mf.read_text(encoding="utf-8"))
        q = m.get("target_quarter")
        if q in ledger.outcomes() or q in ledger.missing():
            continue
        try:
            if Quarter.parse(q) > Quarter.parse(auth["authorized_until"]):
                raise InboxRefused(f"{q} is after the authorized limit {auth['authorized_until']}")
            if m.get("kind") == "no_outcome":
                ledger.record_missing(target_quarter=q, reason=m["reason"], evidence=m["evidence"])
                res.append({"target_quarter": q, "result": "NO_OUTCOME"})
                continue
            p = Path(m["path"]) if Path(m["path"]).is_absolute() else outdir / m["path"]
            df = pd.read_csv(p, dtype={"province_code": str})
            miss = [c for c in OUTCOME_COLUMNS if c not in df.columns]
            if miss:
                raise InboxRefused(f"outcome columns missing {miss}")
            if set(df["target_quarter"]) != {q} or sorted(df["province_code"]) != PROVINCES:
                raise InboxRefused("outcome file must hold exactly the five provinces of its one target quarter")
            end = _quarter_end(q).tz_localize(None)
            for c in ("H_publication_date", "D_publication_date"):
                if (pd.to_datetime(df[c]) < end.normalize()).any():
                    raise InboxRefused(f"{c} precedes the end of {q}: not a published outcome")
            measured = {r.province_code: {"H": float(r.H), "D": float(r.D)} for r in df.itertuples()}
            ledger.record_outcome_measured(target_quarter=q, target=m.get("target", "T1"), measured=measured,
                                           authorization={"path": str(p), "sha256": m["sha256"],
                                                          "authorized_by": m["authorized_by"],
                                                          "authorized_on": m["authorized_on"]})
            res.append({"target_quarter": q, "result": "OUTCOME_RECORDED"})
        except (InboxRefused, LedgerRefused, KeyError, ValueError) as ex:
            res.append({"target_quarter": q, "result": "REFUSED", "reason": str(ex)})
    return res


# ============================================================================================ 5. evidence
def derive_evidence(ledger: Ledger, approvals: dict, development_basis: dict, target: str = "T1",
                    arm_prefix: str = "PCF21") -> dict:
    """Status per lead: VALIDATED only if the adviser approved amendment A1 AND the A1 look for that lead's arm
    claimed success (and, if A3 is approved, also beat every reference). Everything else is EXPERIMENTAL."""
    out = {}
    a1_ok, a3_ok = bool(approvals.get("A1_approved")), bool(approvals.get("A3_approved"))
    for k in range(1, 9):
        arm = f"{arm_prefix}:lead{k}"
        looks = ledger.looks(arm)
        scored = ledger.score(arm)["scored_dates"] if any(e["payload"]["arm"] == arm for e in ledger.seals()) else 0
        look = looks[0]["payload"] if looks else None
        validated = bool(a1_ok and look and look["claim"] and (look["claim_vs_all_references"] if a3_ok else True))
        dev = development_basis.get(target, {}).get(str(k), {})
        out[str(k)] = {"status": "VALIDATED" if validated else "EXPERIMENTAL",
                       "unseen_scored_dates": scored, "a1_look": "taken" if look else "not yet eligible",
                       "a1_approved_by_adviser": a1_ok,
                       "basis": (f"pre-registered A1 look at {look['year_end']}: claim={look['claim']}" if look else
                                 f"{scored} unseen scored date(s); A1 look not yet eligible (needs >= 12 scored dates, "
                                 f">= 5 HIGH and >= 5 LOW). Development evidence: {dev.get('basis', 'n/a')}")}
    return out


# ============================================================================================ cycle
def run_cycle(root: Path, now: pd.Timestamp | None = None, forecaster=None, news_loader=None) -> dict:
    """root = backend_dev/. Reads config/forecast_period.json, config/quarterly_sources.json,
    config/authorization.json, config/adviser_approvals.json; writes data/quarterly_runs, data/ledger, data/inbox."""
    now = to_ph(now if now is not None else pd.Timestamp.now(tz=PH_TZ))
    auth = json.loads((root / "config" / "authorization.json").read_text(encoding="utf-8"))
    approvals_p = root / "config" / "adviser_approvals.json"
    approvals = json.loads(approvals_p.read_text(encoding="utf-8")) if approvals_p.exists() else {}
    dev_p = root / "config" / "evidence_status.json"
    dev = json.loads(dev_p.read_text(encoding="utf-8")) if dev_p.exists() else {}
    reg = Registry(root / "config" / "quarterly_sources.json")
    (root / "data" / "inbox").mkdir(parents=True, exist_ok=True)
    (root / "data" / "outcomes").mkdir(parents=True, exist_ok=True)
    report = {"run_clock": now.isoformat(), "inbox": ingest_inbox(root / "data" / "inbox", reg, auth)}
    ledger = Ledger(root / "data" / "ledger" / "T1_A.jsonl")
    report["outcomes"] = ingest_outcomes(root / "data" / "outcomes", ledger, auth)
    evidence = {"T1": derive_evidence(ledger, approvals, dev), "T2": dev.get("T2", {}),
                "derived_from": "ledger data/ledger/T1_A.jsonl + config/adviser_approvals.json"}
    (root / "data" / "evidence_status_derived.json").write_text(json.dumps(evidence, indent=1), encoding="utf-8")
    period = load_period(root / "config" / "forecast_period.json")
    fc = forecaster(evidence) if forecaster is not None else None
    rec = run_update(period, reg, root / "data" / "quarterly_runs", store=SnapshotStore(root / "data" / "quarterly_store"),
                     news_loader=news_loader, forecaster=fc, now=now)
    report["update"] = {"status": rec["status"], "target_quarter": rec["period"]["target_quarter"],
                        "content_sha256": rec["content_sha256"], "dependencies": rec.get("dependencies", [])}
    report["seals"] = []
    if rec["status"] == "READY" and rec.get("forecast"):
        S1 = pd.read_csv(reg.latest("s1_labels").path, dtype={"province_code": str})
        report["seals"] = seal_record(rec, ledger, S1, now=now.tz_convert("UTC").to_pydatetime())
        sealed = all(s["result"] in ("SEALED", "ALREADY_SEALED") for s in report["seals"])
        if sealed and rec.get("cutoff_reached"):
            save_period(period.advanced(), root / "config" / "forecast_period.json")
            report["advanced_to"] = str(period.advanced().target_quarter)
    (root / "data" / "cycle_log.jsonl").parent.mkdir(parents=True, exist_ok=True)
    with open(root / "data" / "cycle_log.jsonl", "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(report, default=str) + "\n")
    return report
