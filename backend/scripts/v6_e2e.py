"""
v6 end-to-end on real data, run twice (byte-identical digests required): validation -> feature snapshots -> walk-forward
with LightGBM and inner selection -> artifact (temp dir; hash equals the committed one) -> Leads 1-4 -> explanations ->
geography -> store (temp; equals committed) -> API -> seal reproduction.

    python -I backend/scripts/v6_e2e.py      -> docs/aipheed/v6/results/v6_e2e_run.json
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "backend" / "scripts"))
from fastapi.testclient import TestClient  # noqa: E402

from app.forecasting import geography as G  # noqa: E402
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.validation import validate_sws_rounds  # noqa: E402
from app.forecasting.v4 import features as F  # noqa: E402
from app.forecasting.v6 import serving as SV  # noqa: E402
import v6_seal  # noqa: E402

ISSUE = date(2026, 10, 1)
ART = REPO / "backend" / "data" / "forecasting" / "artifacts" / f"v6_{ISSUE}.json"
OUT = REPO / "docs" / "aipheed" / "v6" / "results" / "v6_e2e_run.json"


def digest(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def run_once() -> dict:
    s = {"validation_problems": validate_sws_rounds(pd.read_csv(T.SWS_ROUNDS))}
    with tempfile.TemporaryDirectory() as tmp:
        body = SV.build(ISSUE)
        p = SV.write(body, Path(tmp))
        s["artifact_sha256"] = body["artifact_sha256"]
        s["artifact_equals_committed"] = body["artifact_sha256"] == json.loads(ART.read_text())["artifact_sha256"]
        recs = SV.forecast(ISSUE, p)
        st = SV.save(recs, Path(tmp) / "store")
        s["store_equals_committed"] = json.loads(st.read_text())["records"] == SV.latest(ISSUE)["records"]
    snap = F.snapshot(F.table(), ISSUE.isoformat())
    ex = [SV.explain(r, snap.loc[r["area"]].to_dict()) for r in recs]
    s["max_decomposition_error"] = max(abs(e["contributions_sum"] - r["score"]) for e, r in zip(ex, recs))
    s["explanation_hash_equals_forecast_hash"] = all(e["explanation_model_sha256"] == r["artifact_sha256"] for e, r in zip(ex, recs))
    geo = G.geography_view(recs, 2)
    s["lgus"], s["provinces"], s["model"], s["records"] = len(geo["lgus"]), len(geo["provinces"]), recs[0]["model"], len(recs)
    from app.main import app
    s["api_equals_inference"] = TestClient(app).get("/api/v1/hunger-forecast/v6", params={"issue_date": ISSUE.isoformat()}).json()["records"] == recs
    rr, feats = T.load_rounds(), F.table()
    fresh = pd.concat([v6_seal.seal_rows(rr, feats, date(2026, 7, 1)), v6_seal.seal_rows(rr, feats, ISSUE)], ignore_index=True)
    sealed = pd.read_csv(REPO / "docs" / "aipheed" / "v6" / "sealed" / "V6_PROSPECTIVE_SEAL.csv")
    s["seal_reproduced"] = bool(len(fresh) == len(sealed) and np.allclose(fresh.f, sealed.f))
    s["records_digest"] = digest(recs)
    return s


def main() -> None:
    a, b = run_once(), run_once()
    ok = (digest(a) == digest(b) and a["artifact_equals_committed"] and a["store_equals_committed"] and a["api_equals_inference"]
          and a["seal_reproduced"] and not a["validation_problems"] and a["lgus"] == 142 and a["provinces"] == 5
          and a["max_decomposition_error"] <= SV.SUM_TOLERANCE and a["explanation_hash_equals_forecast_hash"])
    res = {"run1_digest": digest(a), "run2_digest": digest(b), "identical": digest(a) == digest(b), "passed": bool(ok), "steps": a}
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res, indent=1, default=str))
    if not ok:
        sys.exit("E2E FAILED")


if __name__ == "__main__":
    main()
