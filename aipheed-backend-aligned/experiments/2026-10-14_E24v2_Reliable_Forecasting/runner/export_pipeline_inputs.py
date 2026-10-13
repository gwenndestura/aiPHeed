"""Export the authorized / acquired inputs that the isolated quarterly pipeline (backend_dev) reads, and register
them (SHA-256 from the bytes) in backend_dev/config/quarterly_sources.json.  Usage: python -B runner/export_pipeline_inputs.py

Every exported row is traceable:
  sws_rounds_verified.csv   E12 run 20261012T151208Z (hash-pinned), verified publication dates, 2021-Q2..2025-Q4
  s1_labels.csv             E12 components 2021-2025 + authorized Jan-Jun 2026 CPI and SWS rounds (E18 record)
  d_quarterly_panel.csv     PSA OpenSTAT back-cast 1995-2020 (acquisition/), E12 2021-2025, authorized 2026 H1
  dnow_panel.csv            PSA OpenSTAT index-based months 1-2 per quarter 1995-2025, authorized 2026 H1
  lgu_vulnerability.csv     E24 LGU_RANKING_VALIDATION.csv (identity-verified 142 LGUs; substitute labels)
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import pandas as pd  # noqa: E402

import v2lib as V2  # noqa: E402

EXP = guard.EXP
BD = EXP / "backend_dev"
INP = BD / "data" / "inputs"
sys.path.insert(0, str(BD))
from app.quarterly.registry import Registry  # noqa: E402

AUTH = {
    "sws_rounds_verified": ("label", "2021-Q2", "2025-Q4", "2026-01-14T00:00:00+08:00", "region-round",
                            "eligible <=2025-Q4 (E17/E18 allowlist: E12 details.json)",
                            "available_at = latest verified publication date of a round in the file"),
    "s1_labels": ("label", "2021-Q1", "2026-Q2", "2026-10-09T14:40:00Z", "province-quarter",
                  "eligible <=2025-Q4 + researcher (Jan-Jun 2026 only)",
                  "E12 components; E18 DATA_AUTHORIZATION_RECORD.md (2026-10-13) for 2026-Q1/Q2"),
    "d_quarterly_panel": ("indicator", "1995-Q1", "2026-Q2", "2026-10-09T14:40:00Z", "province-quarter",
                          "public PSA OpenSTAT pre-2026 (E24v2 acquisition) + E12 + researcher (Jan-Jun 2026)",
                          "acquisition/ACQUISITION_MANIFEST.json; comparability gate passed"),
    "dnow_panel": ("indicator", "1995-Q1", "2026-Q2", "2026-10-09T14:40:00Z", "province-quarter",
                   "public PSA OpenSTAT pre-2026 (E24v2 acquisition) + researcher (Jan-Jun 2026)",
                   "months 1-2 of each quarter"),
    "lgu_vulnerability": ("static", None, None, None, "lgu", "E17 allowlist (lgu_census, lgu_poverty) via E24",
                          "E24 LGU_RANKING_VALIDATION.csv"),
}


def main():
    INP.mkdir(parents=True, exist_ok=True)
    data = V2.load_all()
    r = data["rounds"].copy()
    r["published"] = r["published"].dt.date.astype(str)
    r.to_csv(INP / "sws_rounds_verified.csv", index=False, lineterminator="\n")
    data["V"]["T1"].rename(columns={"v": "S1"})[["province_code", "quarter", "S1"]].to_csv(
        INP / "s1_labels.csv", index=False, lineterminator="\n")
    data["Dall"].sort_values(["quarter", "province_code"]).to_csv(INP / "d_quarterly_panel.csv", index=False,
                                                                 lineterminator="\n")
    data["Dnow"].sort_values(["quarter", "province_code"]).to_csv(INP / "dnow_panel.csv", index=False,
                                                                 lineterminator="\n")
    v2 = EXP / "data_v2" / "lgu_vulnerability_table.csv"          # rebuilt by lgu_rankings_v2.py (with --sae when supplied)
    lg = pd.read_csv(v2 if v2.exists() else guard.E24_DIR / "LGU_RANKING_VALIDATION.csv", dtype={"lgu_code": str})
    keep = ["lgu_code", "lgu_name", "lgu_type", "province", "population_2020", "land_area_km2", "density",
            "poverty_lgu_estimate", "poverty_value_used", "poverty_value_kind", "poverty_source"]
    lg[keep].to_csv(INP / "lgu_vulnerability.csv", index=False, lineterminator="\n")
    reg = Registry(BD / "config" / "quarterly_sources.json")
    reg.entries = []                                   # E24v2 registry: only the inputs the PCF engine reads
    for sid, (kind, a, b, avail, gran, by, ref) in AUTH.items():
        reg.register(sid, kind, str(INP / f"{sid}.csv"), observation_start=a, observation_end=b, available_at=avail,
                     authorized=True, authorized_by=by, authorization_ref=ref, granularity=gran)
    card = INP / "model_card_pcf_v2.json"
    card.write_text(json.dumps({
        "model": "PCF v2 (probabilistic component forecaster)", "status": "CANDIDATE - not adviser-approved",
        "protocol_sha256": (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[0],
        "engine": "backend_dev/app/quarterly/pcf_engine.py", "H": "local level, n=600, sigma_eta ML grid 0..8",
        "D": "OLS no intercept on latest published D (T1) and [Dnow, D] (price-pressure indicator)",
        "uses_news": False, "why_no_news": "E23/E24 ablations: news-only arms worst; no measurable gain from news"},
        indent=1), encoding="utf-8")
    reg.register("pcf_model_card", "model", str(card), authorized=True, authorized_by="E24v2 frozen protocol",
                 authorization_ref="FROZEN_EVALUATION_PROTOCOL.md", granularity="model")
    reg.save()
    for e in reg.entries:
        print(e.source_id, e.kind, e.observation_start, e.observation_end, e.sha256[:12])


if __name__ == "__main__":
    main()
