"""
E131 acquisition (protocol sections 4 and 6). Public PSA OpenSTAT tables queried for 2021+ periods only, saved raw with
their query and hash; poverty incidence read from the owner-supplied PSA 2025 workbook (E130 data/owner_supplied).

    python -I runner/e131_acquire.py      -> data/raw/*.csv, data/raw/*_query.json, data/acquisition_log.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / "data" / "raw"
PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
UA = "Mozilla/5.0 (aiPHeed thesis research)"
CPI = "DB/2M/PI/CPI/2018NEW/0012M4ACP22.px"
THRESH = "DB/1F/FY/0071F3DF040.px"
E130_WB = (ROOT.parent / "E130_Provincial_Risk_Score_Forecasting" / "data" / "owner_supplied" / "psa_2025_fy_workbook" /
           "2025 Full Year Official Poverty Statistics_24Aug2026_0.xlsx")


def curl(url: str, data: str | None = None) -> bytes:
    cmd = ["curl", "-s", "-m", "300", "-A", UA, url]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", data]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def meta(path: str) -> dict:
    return json.loads(curl(f"{PX}/{path}").decode("utf-8-sig"))


def pick(var: dict, keep) -> list[str]:
    return [c for c, t in zip(var["values"], var["valueTexts"]) if keep(t)]


def fetch(path: str, selection: dict[str, list[str]], name: str, log: dict) -> None:
    q = {"query": [{"code": k, "selection": {"filter": "item", "values": v}} for k, v in selection.items()],
         "response": {"format": "csv"}}
    body = json.dumps(q)
    raw = curl(f"{PX}/{path}", body)
    assert raw[:1] not in (b"{", b"<") and len(raw) > 200, f"bad response for {name}: {raw[:200]!r}"
    (RAW / f"{name}.csv").write_bytes(raw)
    (RAW / f"{name}_query.json").write_text(json.dumps(q, indent=1), encoding="utf-8")
    log[name] = {"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                 "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    log: dict = {}
    # regional CPI levels: regions only, all items / food and non-alcoholic beverages / rice, 2021-2026 months
    m = meta(CPI)
    v = {x["code"]: x for x in m["variables"]}
    regions = pick(v["Geolocation"], lambda t: t.startswith("..") and not t.startswith("....") and "Areas Outside" not in t)
    years = pick(v["Year"], lambda t: t.strip().isdigit() and int(t) >= 2021)
    months = pick(v["Period"], lambda t: t != "Ave")
    comm = pick(v["Commodity Description"], lambda t: t.startswith(("0 - ALL ITEMS", "01 - FOOD AND NON", "01.1.1.12 - Rice")))
    fetch(CPI, {"Geolocation": regions, "Commodity Description": comm, "Year": years, "Period": months}, "psa_cpi_regional_2021_2026", log)
    log["psa_cpi_regional_2021_2026"].update(title=m.get("title"), regions=[t for c, t in zip(v["Geolocation"]["values"],
                                             v["Geolocation"]["valueTexts"]) if c in regions], years=years)
    # official provincial food thresholds and subsistence incidence, 2021 and 2023 only (Region IV-A and its provinces)
    m = meta(THRESH)
    v = {x["code"]: x for x in m["variables"]}
    geo = pick(v["Geolocation"], lambda t: t.lstrip(". ").split(" ")[0] in ("Region", "Batangas", "Cavite", "Laguna", "Quezon", "Rizal")
               and ("IV-A" in t or not t.lstrip(". ").startswith("Region")))
    assert len(geo) == 6, f"expected Region IV-A and 5 provinces, got {geo}"
    yrs = pick(v["Year"], lambda t: t.strip() in ("2021", "2023"))
    meas = v["Threshold/Incidence/Measures of Precision"]["values"]
    fetch(THRESH, {"Geolocation": geo, "Threshold/Incidence/Measures of Precision": meas, "Year": yrs},
          "psa_food_threshold_subsistence_2021_2023", log)
    # poverty incidence among the population (owner workbook, Table 2): regions and provinces, 2021/2023/2025
    sys.path.insert(0, str(ROOT.parent / "E130_Provincial_Risk_Score_Forecasting" / "runner"))
    import xlsx_lite as X
    name, member = [s for s in X.sheets(str(E130_WB)) if s[0] == "tab2"][0]
    cells = X.cells(str(E130_WB), member)
    rows = []
    for r in sorted({r for (r, c) in cells if r >= 8}):
        label = cells.get((r, 1))
        if not isinstance(label, str) or not label.strip() or label.strip().startswith(("Notes", "Source", "r1", "r2", "1/", "2/", "a/", "b/", "c/")):
            continue
        vals = [cells.get((r, c)) for c in range(5, 11)]
        if not all(isinstance(x, float) for x in vals[:3]):
            continue
        rows.append({"geography": label.strip(), "pov_2021": vals[0], "pov_2023": vals[1], "pov_2025": vals[2],
                     "cv_2021": vals[3], "cv_2023": vals[4], "cv_2025": vals[5], "notes": cells.get((r, 20), "")})
    import csv
    out = RAW / "psa_poverty_population_2021_2023_2025.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    log["psa_poverty_population_2021_2023_2025"] = {"source": E130_WB.name, "sheet": name,
                                                     "workbook_sha256": hashlib.sha256(E130_WB.read_bytes()).hexdigest(),
                                                     "rows": len(rows), "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
    (ROOT / "data" / "acquisition_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    for k, x in log.items():
        print(k, x.get("bytes", x.get("rows")), x["sha256"][:12])


if __name__ == "__main__":
    main()
