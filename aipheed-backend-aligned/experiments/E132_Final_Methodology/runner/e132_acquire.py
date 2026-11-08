"""
E132 acquisition (protocol H5): PSA SDG regional income-side series, 2021+ only, saved raw with query and hash.
  8.5.1.p1 Average daily basic pay of wage and salary workers, by region (annual)
  8.5.2    Unemployment rate, 15 years and above, both sexes, by region (annual)

    python -I runner/e132_acquire.py
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
TABLES = {"psa_sdg_daily_basic_pay_region": "DB/3I/G08/0043I3F8511.px",
          "psa_sdg_unemployment_region": "DB/3I/G08/0053I3A0852.px"}


def curl(url: str, data: str | None = None) -> bytes:
    cmd = ["curl", "-s", "-m", "300", "-A", UA, url]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", data]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    log = {}
    for name, path in TABLES.items():
        meta = json.loads(curl(f"{PX}/{path}").decode("utf-8-sig"))
        q = []
        for v in meta["variables"]:
            codes, texts = v["values"], v["valueTexts"]
            if v["code"] == "Year":
                keep = [c for c, t in zip(codes, texts) if t.strip()[:4].isdigit() and int(t.strip()[:4]) >= 2021]
            elif v["code"] == "Age Group":
                keep = [c for c, t in zip(codes, texts) if t.startswith("15 years and above")]
            elif v["code"] == "Sex":
                keep = [c for c, t in zip(codes, texts) if t.startswith("Both")]
            else:
                keep = codes
            q.append({"code": v["code"], "selection": {"filter": "item", "values": keep}})
        body = json.dumps({"query": q, "response": {"format": "csv"}})
        raw = curl(f"{PX}/{path}", body)
        assert raw[:1] not in (b"{", b"<") and raw.count(b"\n") >= 10, f"bad response for {name}"
        (RAW / f"{name}.csv").write_bytes(raw)
        (RAW / f"{name}_query.json").write_text(json.dumps(json.loads(body), indent=1), encoding="utf-8")
        log[name] = {"path": path, "title": meta.get("title"), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                     "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        print(name, len(raw), log[name]["sha256"][:12])
    (ROOT / "data" / "acquisition_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
