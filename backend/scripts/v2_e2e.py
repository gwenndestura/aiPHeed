"""
v2 end-to-end run on real data, twice (step 6): source -> validation -> as_of -> walk-forward + inner selection ->
artifact (built in a temp dir, hash compared with the committed artifact) -> load -> Leads 1-4 -> explanations ->
geography -> store (temp dir, compared with the committed store) -> API -> seal reproduction. The two runs must give
byte-identical digests.

    python -I backend/scripts/v2_e2e.py      -> docs/aipheed/v2/results/v2_e2e_run.json
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
from app.forecasting.v2 import artifact as A  # noqa: E402
from app.forecasting.v2 import explain as X  # noqa: E402
from app.forecasting.v2 import inference as I  # noqa: E402
from app.forecasting.v2 import store as ST  # noqa: E402
import v2_seal  # noqa: E402

ISSUE = date(2026, 10, 1)
ART = REPO / "backend" / "data" / "forecasting" / "artifacts" / f"v2_{ISSUE}.json"
SEAL = REPO / "docs" / "aipheed" / "v2" / "sealed" / "V2_PROSPECTIVE_SEAL.csv"
OUT = REPO / "docs" / "aipheed" / "v2" / "results" / "v2_e2e_run.json"


def digest(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def run_once() -> dict:
    steps = {}
    raw = pd.read_csv(T.SWS_ROUNDS)
    steps["validation_problems"] = validate_sws_rounds(raw)
    rr = T.load_rounds()
    known = T.known_at(rr, ISSUE)
    steps["rounds_used"] = int(len(T.as_of(rr, ISSUE)))
    steps["latest_quarter_known"] = T.qs(int(known.qi.max()))
    with tempfile.TemporaryDirectory() as tmp:
        body = A.build(ISSUE)
        p = A.write(body, Path(tmp))
        steps["artifact_sha256"] = body["artifact_sha256"]
        steps["artifact_equals_committed"] = body["artifact_sha256"] == json.loads(ART.read_text())["artifact_sha256"]
        recs = I.forecast(ISSUE, p)
        stored = ST.save(recs, Path(tmp) / "store")
        steps["store_equals_committed"] = (json.loads(stored.read_text())["records"]
                                           == ST.latest(ISSUE)["records"])
    steps["records"] = len(recs)
    steps["model"] = recs[0]["model"]
    ex = [X.explain(r) for r in recs]
    steps["max_decomposition_error"] = max(abs(sum(c["value"] for c in e["predictive_contributions"]) - r["score"])
                                           for e, r in zip(ex, recs))
    steps["explanation_hash_equals_forecast_hash"] = all(e["explanation_model_sha256"] == r["artifact_sha256"]
                                                         for e, r in zip(ex, recs))
    geo = G.geography_view(recs, 2)
    steps["lgus"], steps["provinces"] = len(geo["lgus"]), len(geo["provinces"])
    from app.main import app
    c = TestClient(app)
    api = c.get("/api/v1/hunger-forecast/v2", params={"issue_date": ISSUE.isoformat()}).json()["records"]
    steps["api_equals_inference"] = api == recs
    fresh = pd.concat([v2_seal.seal_rows(rr, date(2026, 7, 1)), v2_seal.seal_rows(rr, ISSUE)], ignore_index=True)
    sealed = pd.read_csv(SEAL)
    steps["seal_reproduced"] = bool(np.allclose(sealed.f, fresh.f) and (sealed.target == fresh.target).all())
    steps["lead2_balance_luzon"] = [r for r in recs if r["lead"] == 2 and r["area"] == "balance_luzon"][0]
    steps["records_digest"] = digest(recs)
    return steps


def main() -> None:
    a, b = run_once(), run_once()
    res = {"run1_digest": digest(a), "run2_digest": digest(b), "identical": digest(a) == digest(b), "steps": a}
    ok = (res["identical"] and a["artifact_equals_committed"] and a["store_equals_committed"] and a["api_equals_inference"]
          and a["seal_reproduced"] and not a["validation_problems"] and a["lgus"] == 142 and a["provinces"] == 5
          and a["max_decomposition_error"] <= X.SUM_TOLERANCE and a["explanation_hash_equals_forecast_hash"])
    res["passed"] = bool(ok)
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res, indent=1, default=str))
    if not ok:
        sys.exit("E2E FAILED")


if __name__ == "__main__":
    main()
