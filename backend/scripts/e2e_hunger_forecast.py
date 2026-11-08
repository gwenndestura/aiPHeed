"""
Phase 11 end-to-end acceptance on real data, run twice in fresh temporary stores:
  source file (SWS rounds) -> validate -> as_of (issue date) -> artifact build (training cutoff) -> artifact load
  (hash check) -> inference Leads 1-4 -> explanations -> geography -> write-once store -> API (TestClient, reading
  the temporary store). The two runs must give byte-identical stored JSON and identical API bodies.
Writes docs/aipheed/results/e2e_run.json.

    python -I backend/scripts/e2e_hunger_forecast.py 2026-10-01
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
os.chdir(REPO / "backend")
os.environ["PYTEST_CURRENT_TEST"] = "e2e"

from fastapi.testclient import TestClient  # noqa: E402

from app.forecasting import artifact as A  # noqa: E402
from app.forecasting import explain as X  # noqa: E402
from app.forecasting import geography as G  # noqa: E402
from app.forecasting import inference as I  # noqa: E402
from app.forecasting import store as S  # noqa: E402
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.validation import validate_sws_rounds  # noqa: E402


def one_run(issue: date, workdir: Path) -> dict:
    import pandas as pd
    raw = pd.read_csv(T.SWS_ROUNDS)
    problems = validate_sws_rounds(raw)
    assert not problems, problems
    known = T.known_at(T.load_rounds(), issue)
    body = A.build(issue)                                  # training cutoff = issue date (data published before it)
    art = workdir / f"seas_llm_{issue}.json"
    art.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    recs = I.forecast(issue, art)
    exps = [X.explain(r) for r in recs]
    geo = {k: G.geography_view(recs, k) for k in I.LEADS}
    S.STORE = workdir / "forecasts"
    stored = S.save(recs)
    sys.path.insert(0, str(REPO / "backend" / "tests"))
    import conftest  # noqa: F401  (in-memory database)
    from app.main import app
    from app.api.v1 import hunger_forecast as H
    H.S.STORE = S.STORE
    c = TestClient(app)
    api = {p: c.get(p, params={"issue_date": issue.isoformat()}).json() for p in
           ("/api/v1/hunger-forecast", "/api/v1/hunger-forecast/explanation", "/api/v1/hunger-forecast/geography")}
    return {"rows_validated": int(len(raw)), "quarters_known": int(known["quarter"].nunique()),
            "latest_known_quarter": T.qs(int(known["qi"].max())), "artifact_sha256": body["artifact_sha256"],
            "records": len(recs), "explanations": len(exps), "lgus_per_lead": {k: len(v["lgus"]) for k, v in geo.items()},
            "stored_sha256": hashlib.sha256(stored.read_bytes()).hexdigest(),
            "api_sha256": {p: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest() for p, v in api.items()},
            "api_records": len(api["/api/v1/hunger-forecast"]["records"]),
            "balance_luzon_lead2": next(r for r in recs if r["area"] == "balance_luzon" and r["lead"] == 2)}


def main(arg: str):
    issue = date.fromisoformat(arg)
    runs = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as d:
            runs.append(one_run(issue, Path(d)))
    same = runs[0] == runs[1]
    out = {"issue": issue.isoformat(), "identical": same, "tolerance": "exact (byte-identical stored JSON and API bodies)",
           "run1": runs[0], "run2_equals_run1": same}
    p = REPO / "docs" / "aipheed" / "results" / "e2e_run.json"
    p.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "run1"}, indent=1))
    print(json.dumps(runs[0]["balance_luzon_lead2"], indent=1))
    if not same:
        sys.exit("E2E runs differ")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2026-10-01")
