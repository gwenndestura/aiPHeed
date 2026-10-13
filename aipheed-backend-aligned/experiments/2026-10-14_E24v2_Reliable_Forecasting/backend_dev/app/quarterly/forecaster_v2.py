"""
app/quarterly/forecaster_v2.py
------------------------------
Forecaster callable for run_update (E24v2). It reads ONLY registered, authorized, hash-verified inputs, applies
the origin information rule inside pcf_engine, and returns one forecast block that the API, dashboard and PDF
all read. It never uses news (the E23/E24 ablations found no measurable gain from it); the supporting-news
block of the record is display context only.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.quarterly import pcf_engine as E
from app.quarterly.lgu_poverty import rank_lgus
from app.quarterly.registry import Registry

INPUT_IDS = ("sws_rounds_verified", "s1_labels", "d_quarterly_panel", "dnow_panel", "lgu_vulnerability")
NAME2CODE = {v: k for k, v in E.PROVINCE_NAMES.items()}


def _read(reg: Registry, sid: str) -> pd.DataFrame:
    e = reg.latest(sid)
    if e is None or not e.authorized or not e.verify():
        raise PermissionError(f"{sid}: not registered, not authorized or hash mismatch")
    return pd.read_csv(e.path, dtype={"province_code": str, "lgu_code": str})


def lgu_table(lg: pd.DataFrame, province_probability: dict | None) -> pd.DataFrame:
    census = lg[["lgu_code", "lgu_name", "lgu_type", "province", "population_2020", "land_area_km2"]].copy()
    census["province_code"] = census["province"].map(NAME2CODE)
    assert census["province_code"].notna().all() and len(census) == 142
    pov = lg[["lgu_code", "poverty_lgu_estimate", "poverty_source"]].copy()
    pov["poverty_province_value"] = np.where(lg["poverty_lgu_estimate"].isna(), lg["poverty_value_used"], np.nan)
    return rank_lgus(census, pov, province_probability)


def make_pcf_forecaster(evidence: dict, leads=(1,)):
    def forecaster(period, reg: Registry) -> dict:
        rounds = _read(reg, "sws_rounds_verified")
        S1 = _read(reg, "s1_labels")
        Dm, Nm = E.panels_from_tables(_read(reg, "d_quarterly_panel"), _read(reg, "dnow_panel"))
        t = E.qk(str(period.reference_quarter))
        origin = period.target_quarter.start()
        fc = E.forecast(origin, t, list(leads), rounds, S1, Dm, Nm, evidence)
        k1 = fc["leads"][str(leads[0])]
        prob = {p: v["risk"]["p_high"] for p, v in k1["provinces"].items()}
        rk = lgu_table(_read(reg, "lgu_vulnerability"), prob)
        cols = ["lgu_code", "lgu_name", "lgu_type", "province", "risk_index", "rank_region", "rank_in_province",
                "vulnerability_index", "poverty_value_used", "poverty_value_kind", "density", "limitation"]
        fc["lgu_ranking"] = json.loads(rk[cols].to_json(orient="records"))
        fc["model"] = json.loads(Path(reg.latest("pcf_model_card").path).read_text(encoding="utf-8"))
        fc["inputs"] = [{"source_id": s, "sha256": reg.latest(s).sha256, "vintage": reg.latest(s).vintage}
                        for s in INPUT_IDS + ("pcf_model_card",)]
        fc["reading_guide"] = {
            "p_high": "model probability that the approved composite label S1 = H + 2D exceeds the threshold",
            "measured": "official PSA / SWS values, shown as published",
            "model": "estimates produced by aiPHeed; not official food-insecurity classifications",
            "signal": "STRONG (p<=0.20 or >=0.80), MODERATE, UNCERTAIN (0.35-0.65)",
            "evidence": "validation status of this lead; NOT_ESTABLISHED means the forecast is indicative only"}
        return fc
    return forecaster
