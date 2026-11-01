"""PSA OpenSTAT (PXWeb) client used by acquire.py. Read-only GET/POST against openstat.psa.gov.ph; every response
that is saved is written under data_acquired/ with its URL, query, UTC fetch time and SHA-256 (see acquire.py)."""
from __future__ import annotations

import json
import time
import urllib.request

API = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/"
UA = {"User-Agent": "Mozilla/5.0 (research; aiPHeed LEAD2_RELIABILITY_RESEARCH y12)", "Accept": "application/json"}


def _open(req, tries=3):
    for i in range(tries):
        try:
            return urllib.request.urlopen(req, timeout=120).read()
        except Exception:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))


def get(path: str):
    return json.loads(_open(urllib.request.Request(API + path, headers=UA)).decode("utf-8-sig"))


def post(path: str, query: dict) -> bytes:
    body = json.dumps(query).encode()
    return _open(urllib.request.Request(API + path, data=body, headers={**UA, "Content-Type": "application/json"}))


def ls(path: str):
    return [(x["id"].strip(), x["type"], x["text"]) for x in get(path)]
