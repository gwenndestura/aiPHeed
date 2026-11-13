"""
Permanent forecast history of the served model (append-only, hash-chained JSONL; mirrored into the database for queries).

    data/final/history/ledger.jsonl

Every line is one record with the SHA-256 of the previous line, so an edit, deletion or reordering is detected by verify().
Record types:
  forecast   one province x target quarter of one issue (model, issue quarter, lead, values, generation time, data version).
             Unique key: (model_id, issue_quarter, target_quarter, province). Appending the same key again is a no-op when the
             values are identical and an error when they differ: a forecast is never overwritten. A later issue for the same
             target quarter is a NEW record with its own issue quarter, so the original stays identifiable.
  outcome    an observed result (FNRI provincial HFIAS round) for a province and reference quarter, entered with the source
             file's SHA-256 and who authorized it. It is linked to forecasts at read time; forecasts are never edited.
  withdrawn  an administrator's rejection of a served forecast (kept; the forecast stays in history, marked withdrawn).

The file is the record of truth: it is committed with the code, so it survives redeploys of a host with an ephemeral disk.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.paths import BACKEND_DIR

GENESIS = "0" * 64
LEDGER = Path(os.getenv("AIPHEED_FINAL_LEDGER", str(BACKEND_DIR / "data" / "final" / "history" / "ledger.jsonl")))
FORECAST_FIELDS = ("model_id", "model_version", "issue_quarter", "information_cutoff", "target_quarter", "lead", "province",
                   "province_code", "p_high", "risk_class", "share_pct", "range90_pct", "generated_utc", "data_version", "issue_dir")


class HistoryError(RuntimeError):
    pass


def _canon(rec: dict) -> str:
    return json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _path(path: Path | None) -> Path:
    return Path(path) if path else LEDGER


def read(path: Path | None = None) -> list[dict]:
    p = _path(path)
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def verify(path: Path | None = None) -> dict:
    prev = GENESIS
    for n, r in enumerate(read(path)):
        body = {k: v for k, v in r.items() if k != "hash"}
        if body.get("prev") != prev:
            return {"ok": False, "line": n + 1, "reason": "chain broken (prev hash)"}
        if hashlib.sha256(_canon(body).encode()).hexdigest() != r.get("hash"):
            return {"ok": False, "line": n + 1, "reason": "record altered (hash)"}
        prev = r["hash"]
    return {"ok": True, "records": len(read(path)), "head": prev}


def _append(rec: dict, path: Path | None = None) -> dict:
    p = _path(path)
    rows = read(p)
    body = {**rec, "prev": rows[-1]["hash"] if rows else GENESIS}
    body["hash"] = hashlib.sha256(_canon(body).encode()).hexdigest()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(_canon(body) + "\n")
    return body


def _key(r: dict) -> tuple:
    return (r["model_id"], r["issue_quarter"], r["target_quarter"], r["province"])


def forecasts(path: Path | None = None) -> list[dict]:
    return [r for r in read(path) if r.get("type") == "forecast"]


def record_issue(rows: list[dict], path: Path | None = None) -> dict:
    """Append one issue's forecasts. Idempotent per key; refuses to change an existing forecast. All rows are checked before any is written."""
    existing = {_key(r): r for r in forecasts(path)}
    new, same = [], 0
    for r in rows:
        missing = [f for f in FORECAST_FIELDS if f not in r]
        if missing:
            raise HistoryError(f"forecast record lacks {missing}")
        rec = {"type": "forecast", **{f: r[f] for f in FORECAST_FIELDS}}
        k = _key(rec)
        if k in existing:
            old = {f: existing[k][f] for f in FORECAST_FIELDS}
            if _canon(old) != _canon({f: rec[f] for f in FORECAST_FIELDS}):
                raise HistoryError(f"forecast {k} already issued with different values; history is never overwritten")
            same += 1
            continue
        new.append(rec)
    for rec in new:
        _append(rec, path)
    return {"appended": len(new), "already_recorded": same}


def record_outcome(province: str, reference_quarter: str, observed_share_pct: float, source: str, source_sha256: str,
                   authorized_by: str, high_at_pct: float = 50.0, path: Path | None = None) -> dict:
    """An observed HFIAS moderate+severe share for one province and reference quarter. Requires the source file's hash and an
    authorizing person; the observed class is derived from the share (HIGH at 50 %), never from a forecast."""
    if not authorized_by or not source_sha256 or len(source_sha256) != 64:
        raise HistoryError("an outcome needs the source file's full SHA-256 and the person who authorized it")
    for r in read(path):
        if r.get("type") == "outcome" and r["province"] == province and r["reference_quarter"] == reference_quarter:
            if abs(float(r["observed_share_pct"]) - float(observed_share_pct)) < 1e-9 and r["source_sha256"] == source_sha256:
                return {"appended": 0, "already_recorded": 1}
            raise HistoryError(f"an outcome for {province} {reference_quarter} is already recorded")
    rec = {"type": "outcome", "province": province, "reference_quarter": reference_quarter,
           "observed_share_pct": float(observed_share_pct), "observed_class": "HIGH" if float(observed_share_pct) >= high_at_pct else "LOW",
           "source": source, "source_sha256": source_sha256, "authorized_by": authorized_by,
           "recorded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _append(rec, path)
    return {"appended": 1, "already_recorded": 0}


def record_withdrawal(model_id: str, issue_quarter: str, target_quarter: str, province: str, by: str, reason: str,
                      path: Path | None = None) -> dict:
    rec = {"type": "withdrawn", "model_id": model_id, "issue_quarter": issue_quarter, "target_quarter": target_quarter,
           "province": province, "by": by, "reason": reason, "recorded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _append(rec, path)
    return {"appended": 1}


def issues(model_id: str | None = None, path: Path | None = None) -> list[str]:
    return sorted({r["issue_quarter"] for r in forecasts(path) if model_id is None or r["model_id"] == model_id})


def latest_issue(model_id: str, path: Path | None = None) -> str | None:
    q = issues(model_id, path)
    return q[-1] if q else None


def has_issue(model_id: str, issue_quarter: str, path: Path | None = None) -> bool:
    return any(r["model_id"] == model_id and r["issue_quarter"] == issue_quarter for r in forecasts(path))


def with_outcomes(model_id: str | None = None, path: Path | None = None) -> list[dict]:
    """Every forecast with its validation status: 'validated' (an observed outcome exists for its province and target quarter),
    'awaiting outcome' (none yet). Correctness and error are computed only when an outcome exists."""
    rows = read(path)
    outs = {(r["province"], r["reference_quarter"]): r for r in rows if r.get("type") == "outcome"}
    wd = {(r["model_id"], r["issue_quarter"], r["target_quarter"], r["province"]) for r in rows if r.get("type") == "withdrawn"}
    out = []
    for r in rows:
        if r.get("type") != "forecast" or (model_id and r["model_id"] != model_id):
            continue
        o = outs.get((r["province"], r["target_quarter"]))
        x = {k: v for k, v in r.items() if k not in ("prev", "hash", "type")}
        x["withdrawn"] = _key(r) in wd
        if o is None:
            x.update({"validation_status": "awaiting outcome", "observed_share_pct": None, "observed_class": None, "correct": None, "error_pp": None})
        else:
            x.update({"validation_status": "validated", "observed_share_pct": o["observed_share_pct"], "observed_class": o["observed_class"],
                      "correct": r["risk_class"] == o["observed_class"],
                      "error_pp": None if r.get("share_pct") is None else round(float(r["share_pct"]) - float(o["observed_share_pct"]), 2),
                      "outcome_source": o["source"]})
        out.append(x)
    return out


def evaluation(model_id: str | None = None, path: Path | None = None) -> dict:
    """Forecast-versus-actual summary over validated forecasts only: overall, by lead, by province, by target quarter."""
    v = [r for r in with_outcomes(model_id, path) if r["validation_status"] == "validated" and not r["withdrawn"]]

    def summ(rows):
        if not rows:
            return {"n": 0}
        tp = sum(r["risk_class"] == "HIGH" and r["observed_class"] == "HIGH" for r in rows)
        fp = sum(r["risk_class"] == "HIGH" and r["observed_class"] == "LOW" for r in rows)
        fn = sum(r["risk_class"] == "LOW" and r["observed_class"] == "HIGH" for r in rows)
        tn = sum(r["risk_class"] == "LOW" and r["observed_class"] == "LOW" for r in rows)
        err = [abs(r["error_pp"]) for r in rows if r["error_pp"] is not None]
        return {"n": len(rows), "TP": tp, "FP": fp, "FN": fn, "TN": tn, "accuracy": round((tp + tn) / len(rows), 4),
                "precision_high": round(tp / (tp + fp), 4) if tp + fp else None, "recall_high": round(tp / (tp + fn), 4) if tp + fn else None,
                "mean_abs_error_pp": round(sum(err) / len(err), 2) if err else None}

    by = lambda k: {str(g): summ([r for r in v if r[k] == g]) for g in sorted({r[k] for r in v})}
    awaiting = sum(1 for r in with_outcomes(model_id, path) if r["validation_status"] != "validated")
    return {"overall": summ(v), "by_lead": by("lead"), "by_province": by("province"), "by_target_quarter": by("target_quarter"),
            "awaiting_outcome": awaiting,
            "note": "Computed only from forecasts whose target quarter has an authorized observed outcome (FNRI provincial HFIAS). "
                    "A forecast is a risk class, not a measurement; no forecast is marked correct without an observed outcome."}
