"""
app/api/v1/quarterly.py
-----------------------
Read-only endpoint for the current forecast period and its status. It serves the SAME forecast record the
dashboard and the PDF report read (app.quarterly.update.load_latest), so the target quarter, supporting-news
window and cutoff are identical everywhere. No database access.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.quarterly.update import load_latest

RECORDS_DIR = Path(os.getenv("AIPHEED_QUARTERLY_RECORDS", "data/quarterly_runs"))
E25_RECORD = Path(os.getenv("AIPHEED_E25_RECORD", "data/e25/e25_forecast_record.json"))
E27_RECORD = Path(os.getenv("AIPHEED_E27_RECORD", "data/e27/timeline_record.json"))
E27_PDF = Path(os.getenv("AIPHEED_E27_PDF", "data/e27/aiPHeed_E27_forecast_report.pdf"))
router = APIRouter(prefix="/quarterly", tags=["quarterly"])


def _verified_e27() -> dict:
    if not E27_RECORD.exists():
        raise HTTPException(status_code=404, detail="no E27 timeline record has been generated")
    rec = json.loads(E27_RECORD.read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest() != rec.get("content_sha256"):
        raise HTTPException(status_code=500, detail="E27 timeline record failed its integrity check")
    return rec


@router.get("/timeline")
def timeline():
    """E27 timeline record (schema 2): the SAME bytes the dashboard and the PDF are built from."""
    return _verified_e27()


@router.get("/timeline.pdf")
def timeline_pdf():
    """The PDF rendered from the current record. Refused (409) if the PDF was rendered from a different record, so a
    stale PDF can never be served beside a newer record."""
    rec = _verified_e27()
    if not E27_PDF.exists():
        raise HTTPException(status_code=404, detail="no E27 PDF has been rendered")
    b = E27_PDF.read_bytes()
    m = re.search(rb"/Subject \(([0-9a-f]{64})\)", b)
    if not m or m.group(1).decode() != rec["content_sha256"]:
        raise HTTPException(status_code=409, detail="PDF does not match the current timeline record")
    return Response(content=b, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="aiPHeed_E27_forecast_report.pdf"',
                             "X-Record-SHA256": rec["content_sha256"], "Cache-Control": "no-store"})


E28_RECORD = Path(os.getenv("AIPHEED_E28_RECORD", "data/e28/da_brief_record.json"))
E28_PDF = Path(os.getenv("AIPHEED_E28_PDF", "data/e28/aiPHeed_E28_DA_brief.pdf"))
NEWS_STORE = Path(os.getenv("AIPHEED_NEWS_STORE", "data/news_e28"))


def _verified_e28() -> dict:
    if not E28_RECORD.exists():
        raise HTTPException(status_code=404, detail="no E28 DA brief record has been generated")
    rec = json.loads(E28_RECORD.read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest() != rec.get("content_sha256"):
        raise HTTPException(status_code=500, detail="E28 DA brief record failed its integrity check")
    return rec


@router.get("/e28/brief")
def e28_brief():
    """E28 DA brief (schema 3): the SAME bytes the dashboard page and the PDF are built from."""
    return _verified_e28()


@router.get("/e28/brief.pdf")
def e28_brief_pdf():
    rec = _verified_e28()
    if not E28_PDF.exists():
        raise HTTPException(status_code=404, detail="no E28 PDF has been rendered")
    b = E28_PDF.read_bytes()
    m = re.search(rb"/Subject \(([0-9a-f]{64})\)", b)
    if not m or m.group(1).decode() != rec["content_sha256"]:
        raise HTTPException(status_code=409, detail="PDF does not match the current DA brief record")
    return Response(content=b, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="aiPHeed_E28_DA_brief.pdf"',
                             "X-Record-SHA256": rec["content_sha256"], "Cache-Control": "no-store"})


@router.get("/e28/lgu-ranking")
def e28_lgu_ranking(province: str | None = None):
    """The 142-LGU ranking stored in the record (never recomputed here, so it cannot drift from the PDF)."""
    lr = _verified_e28()["lgu_ranking"]
    rows = [r for r in lr["rows"] if province is None or r["province"].lower() == province.lower()]
    return {"meaning": lr["meaning"], "does_not_mean": lr["does_not_mean"], "method": lr["method"],
            "probability_source": lr["probability_source"], "rows_sha256": lr["rows_sha256"], "rows": rows}


@router.get("/e28/news-coverage")
def e28_news_coverage():
    return _verified_e28()["news_coverage"]


E29_RECORD = Path(os.getenv("AIPHEED_E29_RECORD", "data/e29/da_brief_record.json"))
E29_PDF = Path(os.getenv("AIPHEED_E29_PDF", "data/e29/aiPHeed_E29_DA_brief.pdf"))


def _verified_e29() -> dict:
    if not E29_RECORD.exists():
        raise HTTPException(status_code=404, detail="no E29 DA brief record has been generated")
    rec = json.loads(E29_RECORD.read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest() != rec.get("content_sha256"):
        raise HTTPException(status_code=500, detail="E29 DA brief record failed its integrity check")
    return rec


@router.get("/e29/brief")
def e29_brief():
    """E29 DA brief (schema 4): observed evidence separated from experimental estimates; same bytes as dashboard/PDF."""
    return _verified_e29()


@router.get("/e29/brief.pdf")
def e29_brief_pdf():
    rec = _verified_e29()
    if not E29_PDF.exists():
        raise HTTPException(status_code=404, detail="no E29 PDF has been rendered")
    b = E29_PDF.read_bytes()
    m = re.search(rb"/Subject \(([0-9a-f]{64})\)", b)
    if not m or m.group(1).decode() != rec["content_sha256"]:
        raise HTTPException(status_code=409, detail="PDF does not match the current DA brief record")
    return Response(content=b, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="aiPHeed_E29_DA_brief.pdf"',
                             "X-Record-SHA256": rec["content_sha256"], "Cache-Control": "no-store"})


@router.get("/targets")
def targets():
    """What each target measures (food insecurity vs hunger vs price pressure); never redefined, only versioned."""
    from app.quarterly.targets import TARGETS

    return TARGETS


@router.get("/news/status")
def news_status():
    """Operational status of quarterly news collection: last runs, interrupted runs, failed/open windows, staleness."""
    from app.news.audit import status_view
    from app.news.store import NewsStore

    if not NEWS_STORE.exists():
        raise HTTPException(status_code=404, detail="no news store")
    au = json.loads(Path("config/authorization.json").read_text(encoding="utf-8"))["authorized_until"]
    return status_view(NewsStore(NEWS_STORE), au)


@router.get("/e25-timeline")
def e25_timeline():
    """E25 timeline record (2025-Q1..2027-Q1): the SAME bytes the dashboard and the PDF read. The record's content
    SHA-256 is recomputed; a mismatch is an integrity failure (500), never served as data."""
    if not E25_RECORD.exists():
        raise HTTPException(status_code=404, detail="no E25 forecast record has been generated")
    rec = json.loads(E25_RECORD.read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    got = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    if got != rec.get("content_sha256"):
        raise HTTPException(status_code=500, detail="E25 forecast record failed its integrity check")
    return rec


@router.get("/forecast-period")
def forecast_period():
    rec = load_latest(RECORDS_DIR)
    if rec is None:
        raise HTTPException(status_code=404, detail="no quarterly forecast record has been generated")
    return {k: rec[k] for k in ("period", "status", "missing", "labels", "supporting_news", "forecast",
                                "content_sha256", "generated_at", "cutoff_reached") if k in rec}


# ============================================================================================ E31
# E36: the served record (same endpoints); see app/ml/inference/e31_engine.RECORD_PATH
E31_RECORD = Path(os.getenv("AIPHEED_E31_RECORD", "data/e36/e36_record.json"))
E31_PDF = Path(os.getenv("AIPHEED_E31_PDF", "data/e36/aiPHeed_E36_assessment_report.pdf"))
E31_NEWS_STORE = Path(os.getenv("AIPHEED_E31_NEWS_STORE", "data/news_e31"))
_E31_CACHE: dict = {}


def _verified_e31() -> dict:
    """The E31 record, after its integrity check (same bytes as the dashboard copy and the PDF subject)."""
    if not E31_RECORD.exists():
        raise HTTPException(status_code=404, detail="no E31 record has been generated")
    mtime = E31_RECORD.stat().st_mtime
    if _E31_CACHE.get("mtime") != mtime:
        rec = json.loads(E31_RECORD.read_text(encoding="utf-8"))
        body = {k: v for k, v in rec.items() if k != "content_sha256"}
        if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest() != rec.get("content_sha256"):
            raise HTTPException(status_code=500, detail="E31 record failed its integrity check")
        _E31_CACHE.update(mtime=mtime, rec=rec)
    return _E31_CACHE["rec"]


@router.get("/e31/record")
def e31_record():
    """The full E31 record: quarters (backtest / retrospective-blind / nowcast / forecast with provenance), province
    summaries, LGU ranking, news funnel and validated articles, validation results and limitations."""
    return _verified_e31()


@router.get("/e31/summary")
def e31_summary():
    rec = _verified_e31()
    keep = ("schema", "title", "generated_at", "information_cutoff", "data_authorization", "served_engine",
            "target_definition", "regional_hunger", "quarters", "provinces_now", "limitations", "disclaimer",
            "content_sha256")
    return {k: rec[k] for k in keep}


@router.get("/e31/news")
def e31_news(province: str | None = None, quarter: str | None = None, relevance: str = "relevant",
             page: int = 1, page_size: int = 50):
    """Articles behind the news evidence. relevance = relevant (validated R1 DIRECT/INDIRECT, default) | DIRECT |
    INDIRECT | all (every province-attributed article with its R1 label, for transparency)."""
    rec = _verified_e31()
    if relevance not in ("relevant", "DIRECT", "INDIRECT", "all"):
        raise HTTPException(status_code=422, detail="relevance must be relevant, DIRECT, INDIRECT or all")
    if page < 1 or not 1 <= page_size <= 200:
        raise HTTPException(status_code=422, detail="page >= 1 and 1 <= page_size <= 200")
    if relevance == "all":
        from app.news.relevance import classify_deployed as classify
        from app.news.store import NewsStore

        names = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
                 "PH040500000": "Batangas"}
        store = NewsStore(E31_NEWS_STORE)
        items = [{"article_key": a["article_key"], "title": a["title"], "outlet": a["source_domain"],
                  "published_ph": a["published_ph"], "quarter": a["quarter"], "province_code": a["geo_province_code"],
                  "province": names[a["geo_province_code"]], "relevance": classify(a["title"]), "link": a["link"]}
                 for a in store.articles.values() if a.get("geo_province_code") in names]
        items.sort(key=lambda a: a["published_ph"], reverse=True)
    else:
        items = rec["news"]["articles"]
        if relevance in ("DIRECT", "INDIRECT"):
            items = [a for a in items if a["relevance"] == relevance]
    if province:
        p = province.strip().lower()
        items = [a for a in items if a["province"].lower() == p or a["province_code"].lower() == p]
    if quarter:
        items = [a for a in items if a["quarter"] == quarter]
    total = len(items)
    s = (page - 1) * page_size
    return {"total": total, "page": page, "page_size": page_size, "relevance": relevance,
            "relevance_rule": rec["news"]["relevance_rule"], "items": items[s:s + page_size],
            "record_sha256": rec["content_sha256"]}


@router.get("/e31/news/funnel")
def e31_news_funnel(province: str | None = None):
    n = _verified_e31()["news"]
    rows = n["by_province_quarter"]
    if province:
        rows = [r for r in rows if r["province"].lower() == province.strip().lower()]
    return {"totals": n["totals"], "rows": rows, "windows": n["windows"], "source": n["source"]}


@router.get("/e31/lgu-ranking")
def e31_lgu_ranking(province: str | None = None):
    rk = _verified_e31()["lgu_ranking"]
    rows = rk["rows"]
    if province:
        rows = [r for r in rows if r["province"].lower() == province.strip().lower()]
    return {**{k: v for k, v in rk.items() if k != "rows"}, "rows": rows}


@router.get("/e31/report.pdf")
def e31_report_pdf():
    rec = _verified_e31()
    if not E31_PDF.exists():
        raise HTTPException(status_code=404, detail="no E31 PDF has been rendered")
    b = E31_PDF.read_bytes()
    m = re.search(rb"/Subject \(([0-9a-f]{64})\)", b)
    if not m or m.group(1).decode() != rec["content_sha256"]:
        raise HTTPException(status_code=409, detail="PDF does not match the current E31 record")
    return Response(content=b, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="aiPHeed_assessment_report.pdf"',
                             "X-Record-SHA256": rec["content_sha256"], "Cache-Control": "no-store"})
