"""
E133 acquisition (protocol section 9): PSA OpenSTAT CPI for bottom-30 % income households (2018=100), regional
geolocations, items all / food / rice, Year >= 2021 only in the query (no pre-2021 row is downloaded). Saved raw with
the query and its hash.

    python -I runner/e133_acquire.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
UA = "Mozilla/5.0 (aiPHeed thesis research)"
PATH = "DB/2M/PI/BIH/2018NEW/0022M4ABIR1.px"
ITEMS = ("0", "01", "01.1.1.12")


def curl(url: str, data: str | None = None) -> bytes:
    cmd = ["curl", "-s", "-m", "300", "-A", UA, url]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", data]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    meta = json.loads(curl(f"{PX}/{PATH}").decode("utf-8-sig"))
    q = []
    for v in meta["variables"]:
        codes, texts = v["values"], v["valueTexts"]
        if v["code"] == "Year":
            keep = [c for c, t in zip(codes, texts) if t.strip()[:4].isdigit() and int(t.strip()[:4]) >= 2021]
        elif v["code"] == "Commodity Description":
            keep = [c for c in codes if c in ITEMS]
        elif v["code"] == "Geolocation":
            keep = [c for c, t in zip(codes, texts) if not t.startswith("....")]   # regions and national, no provinces
        else:
            keep = codes
        q.append({"code": v["code"], "selection": {"filter": "item", "values": keep}})
    body = json.dumps({"query": q, "response": {"format": "csv"}})
    raw = curl(f"{PX}/{PATH}", body)
    assert raw[:1] not in (b"{", b"<") and raw.count(b"\n") >= 10, "bad response"
    (RAW / "psa_cpi_bottom30_region_2021_2026.csv").write_bytes(raw)
    (RAW / "psa_cpi_bottom30_region_2021_2026_query.json").write_text(json.dumps(json.loads(body), indent=1), encoding="utf-8")
    log = {"psa_cpi_bottom30_region_2021_2026": {"path": PATH, "title": meta.get("title"), "bytes": len(raw),
                                                  "sha256": hashlib.sha256(raw).hexdigest(),
                                                  "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}}
    (ROOT / "data" / "acquisition_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(log)


if __name__ == "__main__":
    main()
