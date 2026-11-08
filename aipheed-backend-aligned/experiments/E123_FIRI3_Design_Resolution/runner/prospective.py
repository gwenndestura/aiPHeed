"""E123 prospective FIRI3 snapshots (E123_FIRI3_PROSPECTIVE_VALIDATION_PROTOCOL.md).

issue_snapshot(): on or after the issue date O(t), compute FIRI3 for origin t from the inputs available then and write
prospective/<origin>/ once (refuses before O(t) and refuses to overwrite). record_observation(): later, recompute the same
origin with newer inputs and save it beside the snapshot as observation_<date>.csv plus a comparison; the snapshot is
never changed. verify(): every snapshot file still matches its manifest.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend"))
from app.ml.inference import firi3 as F3      # noqa: E402


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _scores(obs, ann, t):
    R = F3.compute(obs, ann, [t])
    ind, ov = R["indicators"], R["overall"]
    ccs = F3.subscore(ind, F3.CONDITIONS, "CCS").rename(columns={"score": "ccs", "band": "ccs_band", "status": "ccs_status", "members_used": "ccs_members"})
    svs = F3.subscore(ind, F3.STRUCTURAL, "SVS").rename(columns={"score": "svs", "band": "svs_band", "status": "svs_status"})
    core = F3.common_core(ind, ov)
    pv = ind.pivot_table(index=["scope", "unit", "t"], columns="indicator", values="score").reset_index()
    sc = (ov.merge(pv, on=["scope", "unit", "t"], how="left")
            .merge(ccs[["scope", "unit", "t", "ccs", "ccs_band", "ccs_status", "ccs_members"]], on=["scope", "unit", "t"])
            .merge(svs[["scope", "unit", "t", "svs", "svs_band", "svs_status"]], on=["scope", "unit", "t"])
            .merge(core[["scope", "unit", "t", "fixed_core", "fixed_core_status", "cross_core", "cross_core_indicators", "cross_core_status"]], on=["scope", "unit", "t"]))
    return R["features"], ind, sc


def issue_snapshot(origin: str, obs: pd.DataFrame, ann: pd.DataFrame, root: Path, today: date | None = None,
                   source_hashes: dict | None = None, firi_v2: pd.DataFrame | None = None) -> Path:
    t = F3.qindex(origin)
    iss = F3.issue_date(t)
    today = today or date.today()
    if today.isoformat() < iss:
        raise RuntimeError(f"{origin}: cannot issue before its issue date {iss} (later releases before {iss} would be missed)")
    d = Path(root) / "prospective" / origin
    if (d / "manifest.json").exists():
        raise FileExistsError(f"{origin}: snapshot already issued; it is never overwritten (use record_observation)")
    fs, ind, sc = _scores(obs, ann, t)
    if firi_v2 is not None and len(firi_v2):
        sc = sc.merge(firi_v2, on=["unit", "t"], how="left")
    blobs = {"features.csv": fs, "indicators.csv": ind.assign(component_scores=ind["component_scores"].map(json.dumps)), "scores.csv": sc}
    blobs = {k: v.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode() for k, v in blobs.items()}
    d.mkdir(parents=True)
    for k, b in blobs.items():
        (d / k).write_bytes(b)
    man = {"origin": origin, "issue_date": iss, "kind": "prospective", "issued_on": today.isoformat(), "firi3_version": F3.VERSION,
           "protocol_sha256": F3.PROTOCOL_SHA256, "amendment_1_sha256": F3.AMENDMENT_1_SHA256, "amendment_2_sha256": F3.AMENDMENT_2_SHA256,
           "source_sha256": source_hashes or {}, "files": {k: _sha(b) for k, b in blobs.items()},
           "written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (d / "manifest.json").write_text(json.dumps(man, indent=1))
    return d


def verify(root: Path) -> dict:
    res = {}
    for m in sorted((Path(root) / "prospective").glob("*/manifest.json")):
        man = json.loads(m.read_text())
        res[man["origin"]] = all(_sha((m.parent / k).read_bytes()) == h for k, h in man["files"].items())
    return res


def record_observation(origin: str, obs: pd.DataFrame, ann: pd.DataFrame, root: Path, today: date | None = None) -> Path:
    """Recompute an issued origin with later inputs; save beside the snapshot (never over it) with a comparison."""
    d = Path(root) / "prospective" / origin
    if not (d / "manifest.json").exists():
        raise FileNotFoundError(f"{origin}: no issued snapshot")
    if not verify(root).get(origin):
        raise RuntimeError(f"{origin}: snapshot files do not match their manifest")
    today = today or date.today()
    _, _, sc = _scores(obs, ann, F3.qindex(origin))
    out = d / f"observation_{today.isoformat()}.csv"
    if out.exists():
        raise FileExistsError(out)
    sc.to_csv(out, index=False, lineterminator="\n", float_format="%.12g")
    snap = pd.read_csv(d / "scores.csv")
    cmpf = snap[["scope", "unit", "firi3", "band", "ccs", "svs"]].merge(sc[["scope", "unit", "firi3", "band", "ccs", "svs"]], on=["scope", "unit"], suffixes=("_issued", "_observed"))
    cmpf.to_csv(d / f"comparison_{today.isoformat()}.csv", index=False, lineterminator="\n", float_format="%.12g")
    return out
