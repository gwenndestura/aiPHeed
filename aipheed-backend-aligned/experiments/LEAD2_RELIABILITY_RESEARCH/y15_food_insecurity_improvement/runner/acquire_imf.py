"""Y15 Investigation B: Philippine remittances, quarterly, from the IMF Balance of Payments (BPM6) public SDMX API
(no login, no access restriction). National series only. Saves each raw SDMX-ML response and a tidy CSV in
data_acquired/, with data_acquired/manifest.json (URL, UTC fetch time, SHA-256, coverage).

Series (BOP_ACCOUNTING_ENTRY = CD_T credit, UNIT = USD, FREQUENCY = Q):
  D752_S1W  Personal transfers (current transfers between resident and nonresident households)  <- remittance driver
  D1        Compensation of employees (credit; mostly earnings of Filipinos working abroad short-term)
  R1_S1W    Personal remittances (supplementary item = D752 + D1 + capital transfers between households)

    python -B acquire_imf.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import urllib.request
from pathlib import Path

ACQ = Path(__file__).resolve().parents[1] / "data_acquired"
BASE = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,BOP/{key}?startPeriod=1999"
KEYS = {"personal_transfers": "PHL.CD_T.D752_S1W.USD.Q", "compensation_of_employees": "PHL.CD_T.D1.USD.Q",
        "personal_remittances": "PHL.CD_T.R1_S1W.USD.Q"}


def main():
    ACQ.mkdir(parents=True, exist_ok=True)
    man, rows = [], {}
    for name, key in KEYS.items():
        url = BASE.format(key=key)
        b = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "aiPHeed-research"}), timeout=120).read()
        (ACQ / f"imf_bop_{name}.xml").write_bytes(b)
        s = b.decode("utf-8")
        obs = re.findall(r'<Obs TIME_PERIOD="([^"]+)" OBS_VALUE="([^"]+)"', s)
        upd = re.search(r'UPDATE_DATE="([^"]+)"', s)
        for q, v in obs:
            rows.setdefault(q, {})[name] = float(v) / 1e6
        man.append({"file": f"imf_bop_{name}.xml", "url": url, "fetchedUtc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "sha256": hashlib.sha256(b).hexdigest(), "observations": len(obs),
                    "coverage": [obs[0][0], obs[-1][0]] if obs else None, "imfDatasetUpdate": upd.group(1) if upd else None,
                    "geography": "Philippines (national)", "unit": "USD million (converted from USD)"})
    lines = ["quarter," + ",".join(KEYS)]
    for q in sorted(rows):
        lines.append(q + "," + ",".join("" if k not in rows[q] else f"{rows[q][k]:.3f}" for k in KEYS))
    (ACQ / "remittances_quarterly_usd_mn.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    man.append({"file": "remittances_quarterly_usd_mn.csv", "derivedFrom": [m["file"] for m in man],
                "sha256": hashlib.sha256((ACQ / "remittances_quarterly_usd_mn.csv").read_bytes()).hexdigest()})
    (ACQ / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    for m in man:
        print(json.dumps(m))


if __name__ == "__main__":
    main()
