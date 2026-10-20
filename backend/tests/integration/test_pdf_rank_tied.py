"""
tests/integration/test_pdf_rank_tied.py
---------------------------------------
The province PDF prints the same competition rank as GET /api/v1/provinces and /ranking: tied scores share a rank
and the PDF says "(tied)". (A province tied at rank 1 once printed "4 of 5" because the PDF re-sorted the scores.)
"""

from __future__ import annotations

import io
import re

from fastapi.testclient import TestClient
from pdfminer.high_level import extract_text

from app.main import app
from app.services import report as R

QUARTER = "2027-Q1"
PROVINCES = ("batangas", "cavite", "laguna", "quezon", "rizal")


def _rank_text(pdf: bytes) -> str:
    flat = " ".join(extract_text(io.BytesIO(pdf)).split())
    m = re.search(r"\b(\d) of (\d)( \(tied\))?", flat)
    assert m, "no rank in the PDF"
    return m.group(0)


def test_pdf_rank_equals_api_rank():
    c = TestClient(app)
    api = {p["id"]: p for p in c.get(f"/api/v1/provinces?quarter={QUARTER}").json()["data"]}
    ranking = {r["id"]: r["rank"] for r in c.get(f"/api/v1/ranking?quarter={QUARTER}").json()["data"]}
    n = sum(1 for p in api.values() if not p.get("withheld"))
    for slug in PROVINCES:
        assert api[slug]["rank"] == ranking[slug]
        r = c.get(f"/api/v1/report?scope=province&id={slug}&quarter={QUARTER}")
        assert r.status_code == 200
        want = f"{api[slug]['rank']} of {n}" + (" (tied)" if api[slug]["rankTied"] else "")
        assert _rank_text(r.content) == want, slug


def test_pdf_rank_tied_shares_the_competition_rank(monkeypatch):
    real = R.svc.province_summary

    def tied(quarter, withheld=frozenset(), *args, **kwargs):
        rows = [dict(p) for p in real(quarter, withheld, *args, **kwargs)]
        top = max(p["riskScore"] for p in rows if not p["withheld"])
        for p in rows:                                     # four provinces tied at the top score
            if p["id"] != "batangas" and not p["withheld"]:
                p["riskScore"] = top
        pub = [p for p in rows if not p["withheld"]]
        for p in pub:
            p["rank"] = 1 + sum(1 for o in pub if o["riskScore"] > p["riskScore"])
            p["rankTied"] = sum(1 for o in pub if o["riskScore"] == p["riskScore"]) > 1
        return rows

    monkeypatch.setattr(R.svc, "province_summary", tied)
    rows = {p["id"]: p for p in tied(QUARTER)}
    assert rows["quezon"]["rank"] == 1 and rows["quezon"]["rankTied"]
    assert _rank_text(R.build_province_report("quezon", QUARTER)) == "1 of 5 (tied)"
    assert _rank_text(R.build_province_report("batangas", QUARTER)) == f"{rows['batangas']['rank']} of 5"
