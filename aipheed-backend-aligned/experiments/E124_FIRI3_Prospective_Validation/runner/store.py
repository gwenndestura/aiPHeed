"""E124 append-only FIRI3 forecast store (E124_SNAPSHOT_SCHEMA.md).

    <root>/registry.jsonl                    append-only event log (attempt_blocked, issued, correction, observation)
    <root>/forecasts/<forecast_id>/snapshot.json, feature_trace.csv, manifest.json      written once
    <root>/forecasts/<forecast_id>/corrections/C###.json (+ corrected snapshot)           never replaces the original
    <root>/forecasts/<forecast_id>/observations/O###_<date>.json                          later recomputations

The content hash covers everything except wall-clock fields, so recomputing the same origin from the same inputs with
the same configuration reproduces it exactly.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from app.ml.inference import firi3 as F3      # noqa: E402

WALL_CLOCK = ("created_utc", "issued_on")


def _clean(v):
    if isinstance(v, float):
        return None if math.isnan(v) else round(v, 12)
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if hasattr(v, "item"):
        return _clean(v.item())
    return v


def canonical(obj) -> bytes:
    return json.dumps(_clean(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def content_hash(snapshot: dict) -> str:
    return hashlib.sha256(canonical({k: v for k, v in snapshot.items() if k not in WALL_CLOCK})).hexdigest()


def forecast_id(origin: str) -> str:
    return f"FIRI3-{F3.VERSION.split('-')[-1]}-{origin}"


def _records(df: pd.DataFrame) -> list[dict]:
    return [_clean(r) for r in df.to_dict("records")]


def build(origin: str, obs: pd.DataFrame, ann: pd.DataFrame, config_sha: str, source_sha: dict, firi_v2: dict | None = None) -> tuple[dict, pd.DataFrame]:
    """Deterministic snapshot content for one origin (no wall-clock fields)."""
    t = F3.qindex(origin)
    R = F3.compute(obs, ann, [t])
    fs, ind, ov = R["features"], R["indicators"], R["overall"]
    ccs = F3.subscore(ind, F3.CONDITIONS, "CCS")
    svs = F3.subscore(ind, F3.STRUCTURAL, "SVS")
    core = F3.common_core(ind, ov)
    units = []
    for r in ov.sort_values(["scope", "unit"]).itertuples():
        i = ind[(ind["scope"] == r.scope) & (ind["unit"] == r.unit)].set_index("indicator")
        c = ccs[(ccs["scope"] == r.scope) & (ccs["unit"] == r.unit)].iloc[0]
        s = svs[(svs["scope"] == r.scope) & (svs["unit"] == r.unit)].iloc[0]
        k = core[(core["scope"] == r.scope) & (core["unit"] == r.unit)].iloc[0]
        units.append({"scope": r.scope, "unit": r.unit, "firi3": r.firi3, "band": r.band, "status": r.status,
                      "indicators_available": r.indicators_available, "indicators_defined": r.indicators_defined,
                      "completeness_pct": round(100 * r.indicators_available / r.indicators_defined, 1), "indicators_used": r.indicators_used,
                      "indicators_missing": r.indicators_missing, "verification_share": r.verification_share, "loo_min": r.loo_min, "loo_max": r.loo_max,
                      "indicator_scores": {x: (None if x not in i.index or not i.loc[x, "available"] else i.loc[x, "score"]) for x in F3.INDICATORS},
                      "ccs": c["score"], "ccs_band": c["band"], "ccs_status": c["status"], "svs": s["score"], "svs_position": s["band"], "svs_status": s["status"],
                      "fixed_core": k["fixed_core"], "cross_core": k["cross_core"], "cross_core_indicators": k["cross_core_indicators"],
                      "firi_v2": (firi_v2 or {}).get(r.unit)})
    trace = fs.assign(eligibility=fs["score"].notna().map({True: "scored", False: "not scored"}),
                      exclusion_reason=fs["status"].where(fs["score"].isna(), ""))
    snap = {"forecast_id": forecast_id(origin), "origin": origin, "target_observation_period": origin, "issue_date": F3.issue_date(t),
            "issue_time": f"{F3.issue_date(t)}T00:00:00+08:00", "firi3_version": F3.VERSION, "protocol_sha256": F3.PROTOCOL_SHA256,
            "amendment_1_sha256": F3.AMENDMENT_1_SHA256, "amendment_2_sha256": F3.AMENDMENT_2_SHA256, "config_sha256": config_sha,
            "source_sha256": dict(sorted(source_sha.items())), "input_log": R["log"], "units": units,
            "feature_trace_sha256": hashlib.sha256(trace.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode()).hexdigest()}
    return snap, trace


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)
        (self.root / "forecasts").mkdir(parents=True, exist_ok=True)

    # ---------------- log
    def _log(self, event: dict):
        with open(self.root / "registry.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({**event, "logged_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}, sort_keys=True) + "\n")

    def events(self) -> list[dict]:
        p = self.root / "registry.jsonl"
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []

    def dir(self, fid: str) -> Path:
        return self.root / "forecasts" / fid

    # ---------------- issue
    def blocked(self, origin: str, reasons: list[str], missing: list[dict], today: date):
        self._log({"event": "attempt_blocked", "forecast_id": forecast_id(origin), "origin": origin, "attempt_date": today.isoformat(),
                   "reasons": reasons, "missing_inputs": missing})

    def issue(self, origin: str, obs, ann, config_sha: str, source_sha: dict, today: date, eligibility: dict, firi_v2: dict | None = None) -> Path:
        fid = forecast_id(origin)
        iss = F3.issue_date(F3.qindex(origin))
        reasons = []
        if today.isoformat() < iss:
            reasons.append(f"today {today.isoformat()} is before the issue date {iss}")
        reasons += [f"{k}: {v}" for k, v in eligibility.get("failed", {}).items()]
        if reasons:
            self.blocked(origin, reasons, eligibility.get("missing_inputs", []), today)
            raise RuntimeError("issuance blocked: " + "; ".join(reasons))
        d = self.dir(fid)
        if (d / "manifest.json").exists():
            raise FileExistsError(f"{fid} already issued; a forecast is never re-issued or overwritten (use correct())")
        snap, trace = build(origin, obs, ann, config_sha, source_sha, firi_v2)
        h = content_hash(snap)
        snap.update(created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), issued_on=today.isoformat())
        d.mkdir(parents=True)
        (d / "snapshot.json").write_bytes(json.dumps(_clean(snap), sort_keys=True, indent=1).encode())
        (d / "feature_trace.csv").write_text(trace.to_csv(index=False, lineterminator="\n", float_format="%.12g"), encoding="utf-8")
        (d / "manifest.json").write_text(json.dumps({"forecast_id": fid, "content_sha256": h, "files": {
            n: hashlib.sha256((d / n).read_bytes()).hexdigest() for n in ("snapshot.json", "feature_trace.csv")}}, indent=1))
        self._log({"event": "issued", "forecast_id": fid, "origin": origin, "content_sha256": h, "issued_on": today.isoformat()})
        return d

    # ---------------- integrity
    def verify(self, fid: str) -> dict:
        d = self.dir(fid)
        man = json.loads((d / "manifest.json").read_text())
        files_ok = all(hashlib.sha256((d / n).read_bytes()).hexdigest() == h for n, h in man["files"].items())
        snap = json.loads((d / "snapshot.json").read_text())
        return {"files_ok": files_ok, "content_ok": content_hash(snap) == man["content_sha256"], "content_sha256": man["content_sha256"]}

    def reproduce(self, fid: str, obs, ann, config_sha: str, source_sha: dict, firi_v2: dict | None = None) -> bool:
        snap = json.loads((self.dir(fid) / "snapshot.json").read_text())
        again, _ = build(snap["origin"], obs, ann, config_sha, source_sha, firi_v2)
        return content_hash(again) == json.loads((self.dir(fid) / "manifest.json").read_text())["content_sha256"]

    # ---------------- corrections (never replace the original)
    def correct(self, fid: str, reason: str, obs, ann, config_sha: str, source_sha: dict, today: date, firi_v2: dict | None = None) -> Path:
        v = self.verify(fid)
        if not (v["files_ok"] and v["content_ok"]):
            raise RuntimeError(f"{fid}: original snapshot fails verification; corrections refused")
        d = self.dir(fid) / "corrections"
        d.mkdir(exist_ok=True)
        n = len(list(d.glob("C*.json"))) + 1
        snap = json.loads((self.dir(fid) / "snapshot.json").read_text())
        new, trace = build(snap["origin"], obs, ann, config_sha, source_sha, firi_v2)
        rec = {"correction_id": f"C{n:03d}", "forecast_id": fid, "reason": reason, "date": today.isoformat(),
               "original_content_sha256": v["content_sha256"], "corrected_content_sha256": content_hash(new), "corrected_snapshot": _clean(new)}
        p = d / f"C{n:03d}.json"
        p.write_bytes(json.dumps(rec, sort_keys=True, indent=1).encode())
        trace.to_csv(d / f"C{n:03d}_feature_trace.csv", index=False, lineterminator="\n", float_format="%.12g")
        self._log({"event": "correction", "forecast_id": fid, "correction_id": rec["correction_id"], "reason": reason,
                   "original_content_sha256": v["content_sha256"], "corrected_content_sha256": rec["corrected_content_sha256"]})
        return p

    # ---------------- later observations: forecast stability vs data revision vs new information
    def observe(self, fid: str, obs, ann, config_sha: str, source_sha: dict, today: date) -> dict:
        v = self.verify(fid)
        d = self.dir(fid)
        orig = pd.read_csv(d / "feature_trace.csv")
        snap = json.loads((d / "snapshot.json").read_text())
        new, trace = build(snap["origin"], obs, ann, config_sha, source_sha)
        m = orig.merge(trace, on=["scope", "unit", "feature"], suffixes=("_issued", "_later"))
        same_p = m["period_issued"].astype(str) == m["period_later"].astype(str)
        same_v = (m["raw_value_issued"].fillna(-1e18) - m["raw_value_later"].fillna(-1e18)).abs() < 1e-9
        m["change_type"] = [("unchanged" if sp and sv and str(a) == str(b) else "data revision (same period, new value)" if sp and not sv else
                             "availability change" if (pd.isna(x)) != (pd.isna(y)) and sp else "new information (later period)" if not sp else "status change")
                            for sp, sv, a, b, x, y in zip(same_p, same_v, m["status_issued"], m["status_later"], m["score_issued"], m["score_later"])]
        u_old = {(u["scope"], u["unit"]): u for u in snap["units"]}
        units = [{"scope": u["scope"], "unit": u["unit"], "firi3_issued": u_old[(u["scope"], u["unit"])]["firi3"], "firi3_later": u["firi3"],
                  "band_issued": u_old[(u["scope"], u["unit"])]["band"], "band_later": u["band"],
                  "indicators_issued": u_old[(u["scope"], u["unit"])]["indicators_used"], "indicators_later": u["indicators_used"]} for u in new["units"]]
        od = d / "observations"
        od.mkdir(exist_ok=True)
        n = len(list(od.glob("O*.json"))) + 1
        rec = {"observation_id": f"O{n:03d}", "forecast_id": fid, "date": today.isoformat(),
               "forecast_stability": {"original_unchanged": v["files_ok"] and v["content_ok"], "content_sha256": v["content_sha256"]},
               "data_revision_sensitivity": {"features_revised": int((m["change_type"] == "data revision (same period, new value)").sum())},
               "prospective_measurement": {"features_new_period": int((m["change_type"] == "new information (later period)").sum()),
                                           "availability_changes": int((m["change_type"] == "availability change").sum())},
               "later_content_sha256": content_hash(new), "units": _clean(units),
               "feature_changes": _clean(m[["scope", "unit", "feature", "period_issued", "period_later", "raw_value_issued", "raw_value_later", "change_type"]].to_dict("records"))}
        (od / f"O{n:03d}_{today.isoformat()}.json").write_bytes(json.dumps(rec, sort_keys=True, indent=1).encode())
        self._log({"event": "observation", "forecast_id": fid, "observation_id": rec["observation_id"], "original_unchanged": rec["forecast_stability"]["original_unchanged"]})
        return rec
