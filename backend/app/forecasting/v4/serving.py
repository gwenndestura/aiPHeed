"""
v4 serving: frozen artifact (canonical JSON + SHA-256, write-once), inference that never re-estimates, exact
explanation and a write-once store. The artifact holds the rule-selected model at the cutoff, its parameters (local
level q, kappa; DELTA-X features / means / sds / betas per lead when selected), conformal half-widths, and the
mechanical statuses from docs/aipheed/v4/results/v4_verdict.json (development label, sealed claims).

    python -m app.forecasting.v4.serving build 2026-10-01
    python -m app.forecasting.v4.serving run 2026-10-01 data/forecasting/artifacts/v4_2026-10-01.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from app.forecasting import sws as T
from app.forecasting.as_of import issue_instant
from app.forecasting.evidence import AREAS, CALABARZON_SWS_AREA, DataState, EvidenceStatus
from app.forecasting.explain import TRIGGER_GROUPS
from app.forecasting.store import key
from app.forecasting.v2 import models as V
from app.forecasting.v2 import select as S2
from app.forecasting.v4 import features as F
from app.forecasting.v4 import models as DX
from app.forecasting.v4 import select as S4

BACKEND = Path(__file__).resolve().parents[3]
ART_DIR = BACKEND / "data" / "forecasting" / "artifacts"
STORE = BACKEND / "data" / "forecasting" / "forecasts_v4"
DOCS = BACKEND.parent / "docs" / "aipheed" / "v4"
SCHEMA, METHOD = 4, "AIPHEED-V4"
PREPROCESSING_VERSION = "sws-quarter-mean+binomial-se/1;v4-feature-snapshots/1"
SUM_TOLERANCE = 1e-3


class ArtifactError(RuntimeError):
    pass


class InferenceError(RuntimeError):
    pass


def _canonical(d: dict) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(p: Path, lf: bool = False) -> str:
    b = Path(p).read_bytes()
    return hashlib.sha256(b.replace(b"\r\n", b"\n") if lf else b).hexdigest()


# ---------------------------------------------------------------- artifact
def build(cutoff: date, verdict_path: Path = DOCS / "results" / "v4_verdict.json") -> dict:
    if cutoff.day != 1 or cutoff.month not in (1, 4, 7, 10):
        raise ArtifactError("the training cutoff must be a quarter-start issue date")
    rr, feats = T.load_rounds(), F.table()
    wf = S4.walk_forward(rr, feats, cutoff)
    model, log = S4.select(wf, rr, cutoff)
    known = T.known_at(rr, cutoff)
    anchor = S4.ANCHOR.get(model, model)
    p = V.fit(anchor, known)
    delta = {}
    if model in S4.ANCHOR:
        for k in S2.LEADS:
            d = DX.fit_delta(S4.training_rows(wf, rr, feats, cutoff, k, anchor))
            delta[str(k)] = {"features": d.features, "mean": d.mean, "sd": d.sd, "beta": d.beta}
    conformal = {}
    for k in S2.LEADS:
        half, n = S2.conformal_halfwidth(wf, rr, cutoff, model, k)
        conformal[str(k)] = {"halfwidth80": half, "n_residuals": n}
    v = json.loads(Path(verdict_path).read_text(encoding="utf-8"))
    body = {"schema": SCHEMA, "method": METHOD, "model": model, "anchor": anchor, "candidates": list(S4.CANDIDATES),
            "training_cutoff": cutoff.isoformat(), "latest_quarter_used": T.qs(p.upto),
            "params": {"q": p.q, "kappa": p.kappa, "upto": p.upto, "loglik": p.loglik}, "delta": delta,
            "selection_log": log, "conformal": conformal,
            "reliability_status_by_lead": {str(k): s for k, s in v["served_reliability_status_by_lead"].items()},
            "claims": {"75pct_frozen_sealed": v["claim_75_sealed"]["frozen"]["verdict"],
                       "75pct_amended_sealed": v["claim_75_sealed"]["amended"]["verdict"],
                       "75pct_amended_status": "PROPOSED_NOT_ADOPTED (needs adviser sign-off)",
                       "beats_all_sealed": v["beats_all_sealed"]["verdict"],
                       "75pct_frozen_development_share": v["claim_75_frozen_development"]["share"]},
            "verdict_file_sha256": _sha(verdict_path), "features": ["sws_hunger_history", *F.FEATURES],
            "preprocessing_version": PREPROCESSING_VERSION, "data_sha256": _sha(T.SWS_ROUNDS),
            "feature_snapshots_sha256": _sha(F.SNAPSHOTS), "preregistration_sha256_lf": _sha(DOCS / "PREREGISTRATION.md", lf=True),
            "evidence_scope": "SWS area level (4 areas); CALABARZON lies in Balance Luzon"}
    body["artifact_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body


def write(body: dict, art_dir: Path = ART_DIR) -> Path:
    art_dir.mkdir(parents=True, exist_ok=True)
    out = art_dir / f"v4_{body['training_cutoff']}.json"
    if out.exists():
        raise ArtifactError(f"{out.name} exists: artifacts are write-once")
    out.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return out


def load(path: Path) -> tuple[dict, V.Params]:
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    if body.get("schema") != SCHEMA or body.get("method") != METHOD or body.get("model") not in S4.CANDIDATES:
        raise ArtifactError("unsupported v4 artifact schema, method or model")
    if body.get("preprocessing_version") != PREPROCESSING_VERSION or body.get("features") != ["sws_hunger_history", *F.FEATURES]:
        raise ArtifactError("artifact feature config or preprocessing version does not match this code")
    if hashlib.sha256(_canonical({k: v for k, v in body.items() if k != "artifact_sha256"})).hexdigest() != body.get("artifact_sha256"):
        raise ArtifactError("artifact hash mismatch: the file was edited")
    pr = body["params"]
    if not (0 < float(pr["q"]) < 1e3) or float(pr["kappa"]) not in V.KAPPA_GRID:
        raise ArtifactError("parameter out of range")
    if body["model"] in S4.ANCHOR and set(body["delta"]) != {"1", "2", "3", "4"}:
        raise ArtifactError("DELTA model without per-lead change parameters")
    return body, V.Params(body["anchor"], float(pr["q"]), float(pr["kappa"]), int(pr["upto"]), float(pr["loglik"]))


# ---------------------------------------------------------------- inference
def _limitation(model: str, status: str, k: int) -> str:
    what = ("Latest published SWS hunger reading carried forward (persistence)" if model == "PERSIST" else
            f"{model}: latest SWS reading{' (denoised)' if 'LLK' in model or model == 'LL-K' else ''} plus a predicted change")
    return (f"{what}. SWS area value, not a provincial or LGU measurement. Lead {k} status {status}. The 75 % and "
            "'beats every model' claims are pre-declared hypotheses: NOT YET TESTABLE until 10 unseen SWS quarters "
            "(about 2029-05); development share at Lead 2 was 40 %.")


def forecast(issue: date, artifact_path: Path) -> list[dict]:
    if issue.day != 1 or issue.month not in (1, 4, 7, 10):
        raise InferenceError(f"{issue} is not a quarter start")
    body, p = load(artifact_path)
    if issue < date.fromisoformat(body["training_cutoff"]):
        raise InferenceError("issue date precedes the artifact's training cutoff")
    known = T.known_at(T.load_rounds(), issue)
    if known.empty:
        raise InferenceError(f"no SWS round published before {issue}")
    snap = F.snapshot(F.table(), issue.isoformat(), used_at=issue.isoformat()) if body["model"] in S4.ANCHOR else None
    if snap is not None and snap.empty:
        raise InferenceError(f"no feature snapshot for {issue}")
    D, vintage, out = S2.dashboard_quarter(issue), max(known["published"]).isoformat(), []
    for k in S2.LEADS:
        fc = V.forecast(known, p, D - 1 + k)
        conf, status = body["conformal"][str(k)], body["reliability_status_by_lead"][str(k)]
        for a in AREAS:
            if a not in fc:
                raise InferenceError(f"no forecast for {a}")
            r = fc[a]
            chg, contrib = 0.0, {}
            if snap is not None:
                dp = body["delta"][str(k)]
                chg, contrib = DX.predict_delta(DX.DeltaParams(dp["features"], dp["mean"], dp["sd"], dp["beta"]), snap.loc[a])
            f = r["f"] + chg
            lo, hi, how = S2.interval(f, r["sd"], conf["halfwidth80"])
            if not (0.0 <= f <= 100.0):
                raise InferenceError(f"{a}: forecast {f:.2f} outside 0-100")
            out.append({"issue_date": issue.isoformat(), "feature_cutoff": issue_instant(issue).isoformat() + " (exclusive)",
                        "dashboard_quarter": T.qs(D), "target_quarter": T.qs(D - 1 + k), "lead": k, "area": a,
                        "score": round(f, 4), "lo80": round(max(lo, 0.0), 4), "hi80": round(min(hi, 100.0), 4),
                        "interval_method": how, "interval_residuals": conf["n_residuals"],
                        "unit": "% of families, SWS involuntary hunger",
                        "components": {"latest_reading": round(r["latest"], 4),
                                       "noise_filter_adjustment": round(r["noise_adjustment"], 4),
                                       "predicted_change": {g: round(v, 4) for g, v in DX.by_group(contrib).items()}},
                        "horizon_quarters_from_latest_data": r["h"], "latest_data_quarter": T.qs(r["latest_qi"]),
                        "data_vintage_published": vintage, "method": METHOD, "model": body["model"],
                        "model_version": body["training_cutoff"], "artifact_sha256": body["artifact_sha256"],
                        "preprocessing_version": PREPROCESSING_VERSION,
                        "evidence_status": EvidenceStatus.AWAITING_GROUND_TRUTH.value,
                        "geography_note": "SWS area value; CALABARZON lies in this area" if a == CALABARZON_SWS_AREA else "SWS area value",
                        "reliability_status": status, "claims": body["claims"],
                        "limitation": _limitation(body["model"], status, k)})
    return out


# ---------------------------------------------------------------- explanation
def explain(record: dict, snap_row: dict | None = None) -> dict:
    c = record["components"]
    parts = [("latest_reading", c["latest_reading"], f"latest published SWS reading ({record['latest_data_quarter']})"),
             ("noise_filter_adjustment", c["noise_filter_adjustment"], "survey sampling noise removed (0 for persistence)")]
    parts += [(f"predicted_change:{g}", v, f"change predicted from the {g} group (learned weights)") for g, v in
              c["predicted_change"].items()]
    total = sum(v for _, v, _ in parts)
    if abs(total - record["score"]) > SUM_TOLERANCE:
        raise ValueError(f"contributions sum to {total:.4f}, not the score {record['score']:.4f}")
    ctx, missing = [], []
    for g, lab in TRIGGER_GROUPS.items():
        fs = [f for f, gg in F.GROUP.items() if gg == g]
        vals = {f: (snap_row or {}).get(f) for f in fs}
        present = {f: v for f, v in vals.items() if v is not None and v == v}
        state = DataState.OBSERVED if present else DataState.UNAVAILABLE
        if not present:
            missing.append(f"{lab}: {state.value}")
        ctx.append({"group": g, "label": lab, "values": present, "data_state": state.value,
                    "contribution": c["predicted_change"].get(g, 0.0),
                    "role": "model input" if g in c["predicted_change"] else "contextual indicator (not used by the served model)"})
    warn = []
    if record["reliability_status"] != "RELIABLE":
        warn.append(f"Lead {record['lead']} status {record['reliability_status']}")
    return {"score": record["score"],
            "summary": "last observed value carried forward" if record["model"] == "PERSIST" else
                       "latest reading plus learned change",
            "predictive_contributions": [{"component": n, "value": v, "meaning": m} for n, v, m in parts],
            "contributions_sum": round(total, 4), "sum_tolerance": SUM_TOLERANCE,
            "five_group_summary": ctx, "data_quality_warnings": warn, "missing_information": missing,
            "explanation_model_sha256": record["artifact_sha256"],
            "uncertainty": {"lo80": record["lo80"], "hi80": record["hi80"], "method": record["interval_method"]}}


# ---------------------------------------------------------------- store
def save(records: list[dict], store: Path = STORE) -> Path:
    store.mkdir(parents=True, exist_ok=True)
    out = store / f"{key(records)}.json"
    text = json.dumps({"key": key(records), "records": records}, indent=1, sort_keys=True) + "\n"
    if out.exists():
        if out.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"{out.name} exists with different content: the store is write-once")
        return out
    out.write_text(text, encoding="utf-8", newline="\n")
    return out


def latest(issue: date | None = None, store: Path = STORE) -> dict | None:
    bodies = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(store.glob("*.json"))] if store.exists() else []
    if issue is not None:
        bodies = [b for b in bodies if b["records"][0]["issue_date"] == issue.isoformat()]
    return max(bodies, key=lambda b: (b["records"][0]["issue_date"], b["records"][0]["data_vintage_published"])) if bodies else None


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "build":
        print(write(build(date.fromisoformat(sys.argv[2]))))
    elif len(sys.argv) == 4 and sys.argv[1] == "run":
        print(save(forecast(date.fromisoformat(sys.argv[2]), Path(sys.argv[3]))))
    else:
        sys.exit("usage: python -m app.forecasting.v4.serving build YYYY-MM-DD | run YYYY-MM-DD <artifact>")
