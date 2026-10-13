"""E15 two-layer prototype builder (development only; not connected to any production API).

build_two_layer(f_rows, rounds, quarters) -> dict that follows TWO_LAYER_SCHEMA.json.
  f_rows : DataFrame [quarter, province_code, F]  (provincial food inflation, % YoY; NaN = missing)
  rounds : DataFrame [quarter, H, published, date_type, definition_A, source, round]  (SWS rounds)
No file is opened here. No value is imputed: a missing F stays null and removes D and the rank for that quarter.
"""
from __future__ import annotations

import math
import re

import pandas as pd

SCHEMA_VERSION = "e15-two-layer-0.1"
PROVINCES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon",
             "PH040400000": "Rizal", "PH040500000": "Batangas"}
TAU0 = 10.84335                      # recorded/served legacy threshold, displayed as 10.843
TIE_DECIMALS = 9
SCOPE = "Balance Luzon"
PROVINCIAL_LABEL = "relative food-price pressure"
LEGACY_LABEL = "legacy composite, not validated as food insecurity"
CAVEATS = [
    "A ranking always yields a top province, even when conditions are uniform across provinces.",
    "The five-province mean is unweighted: each province counts equally, regardless of population.",
    "Balance Luzon is wider than CALABARZON; the regional hunger value is not a provincial measurement "
    "and is shown once per quarter.",
    "No independent provincial outcome exists; neither layer has been validated against a measured "
    "provincial outcome.",
    "D and its rank describe relative food-price pressure only.",
    "The legacy composite (S1) is shown for continuity, in a secondary position, and is not validated.",
]
BANNED = [re.compile(r"food[\s_-]*insecure(?!ity)", re.I), re.compile(r"risk", re.I)]


def qkey(q: str) -> int:
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def _num(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) or pd.isna(x) else float(x)


def regional_layer(rounds: pd.DataFrame, q: str, prev: tuple[str, float] | None) -> dict:
    r = rounds[rounds["quarter"] == q].sort_values("published")
    if r.empty:
        return {"indicator": "SWS involuntary hunger (total), % of families", "scope": SCOPE, "status": "NO_ROUND",
                "level_pct": None, "rounds": [], "latest_publication_date": None, "trend": None}
    level = float(r["H"].mean())
    trend = None
    if prev is not None:
        trend = {"change_pct_points": level - prev[1], "compared_with_quarter": prev[0],
                 "quarters_apart": qkey(q) - qkey(prev[0])}
    return {"indicator": "SWS involuntary hunger (total), % of families", "scope": SCOPE, "status": "AVAILABLE",
            "level_pct": level,
            "rounds": [{"round": str(x.round), "value_pct": float(x.H), "published": x.published.strftime("%Y-%m-%d"),
                        "date_status": str(x.date_type), "series": "production" if bool(x.definition_A) else "supplementary"}
                       for x in r.itertuples()],
            "latest_publication_date": r["published"].max().strftime("%Y-%m-%d"), "trend": trend}


def rank_desc(values: dict[str, float]) -> tuple[dict[str, int], dict[str, list[str]]]:
    """Competition ranking (1 = highest). Values equal after rounding to TIE_DECIMALS share the lowest rank of the
    tied group; the next rank is skipped (1, 2, 2, 4)."""
    rv = {k: round(v, TIE_DECIMALS) for k, v in values.items()}
    ranks, ties = {}, {}
    for k, v in rv.items():
        ranks[k] = 1 + sum(1 for w in rv.values() if w > v)
        ties[k] = sorted(PROVINCES.get(j, j) for j, w in rv.items() if w == v and j != k)
    return ranks, ties


def provincial_layer(f_rows: pd.DataFrame, q: str) -> dict:
    fq = f_rows[f_rows["quarter"] == q].set_index("province_code")["F"]
    F = {pc: _num(fq.get(pc)) for pc in PROVINCES}
    missing = sorted(PROVINCES[pc] for pc, v in F.items() if v is None)
    complete = not missing
    mean5 = sum(F.values()) / 5 if complete else None
    D = {pc: F[pc] - mean5 for pc in PROVINCES} if complete else {}
    ranks, ties = rank_desc(D) if complete else ({}, {})
    provs = []
    for pc in sorted(PROVINCES, key=lambda c: PROVINCES[c]):
        provs.append({"province_code": pc, "province": PROVINCES[pc], "food_inflation_yoy_pct": F[pc],
                      "relative_pressure_D_pp": D.get(pc), "relative_pressure_rank": ranks.get(pc),
                      "tied_with": ties.get(pc, [])})
    return {"label": PROVINCIAL_LABEL, "status": "COMPLETE" if complete else "INCOMPLETE_NO_D_OR_RANK",
            "missing_provinces": missing, "five_province_mean_F_pct_unweighted": mean5,
            "rank_rule": f"1 = highest D; values equal after rounding to {TIE_DECIMALS} decimals share the lowest "
                         f"rank of the group (1, 2, 2, 4); tied provinces listed alphabetically",
            "provinces": provs}


def legacy_layer(rounds: pd.DataFrame, prov: dict, q: str, tau0: float = TAU0) -> dict:
    rA = rounds[(rounds["quarter"] == q) & (rounds["definition_A"])]
    hA = float(rA["H"].mean()) if len(rA) else None
    if hA is None:
        status = "UNAVAILABLE_NO_PRODUCTION_ROUND"
    elif prov["status"] != "COMPLETE":
        status = "UNAVAILABLE_INCOMPLETE_PROVINCES"
    else:
        status = "AVAILABLE"
    rows = []
    for p in prov["provinces"]:
        s1 = hA + 2 * p["relative_pressure_D_pp"] if status == "AVAILABLE" else None
        rows.append({"province_code": p["province_code"], "province": p["province"], "S1": s1,
                     "label": None if s1 is None else ("HIGH" if s1 > tau0 else "LOW")})
    return {"label": LEGACY_LABEL, "placement": "secondary", "formula": "S1 = H_A + 2 * D",
            "threshold": tau0, "threshold_display": "10.843", "rule": "HIGH if S1 > threshold (strict), else LOW",
            "H_A_production_rounds_pct": hA, "status": status, "provinces": rows}


def build_two_layer(f_rows: pd.DataFrame, rounds: pd.DataFrame, quarters: list[str], data_through: str,
                    tau0: float = TAU0) -> dict:
    out_q, prev = [], None
    for q in sorted(quarters, key=qkey):
        reg = regional_layer(rounds, q, prev)
        if reg["level_pct"] is not None:
            prev = (q, reg["level_pct"])
        prov = provincial_layer(f_rows, q)
        out_q.append({"quarter": q, "regional_layer": reg, "provincial_layer": prov,
                      "legacy_layer": legacy_layer(rounds, prov, q, tau0)})
    return {"schema_version": SCHEMA_VERSION,
            "status": "development prototype; not connected to the production API or dashboard",
            "data_through": data_through, "caveats": CAVEATS, "quarters": out_q}


def wording_violations(obj, path="$") -> list[str]:
    """Every key or string value that contains banned wording."""
    bad = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(b.search(str(k)) for b in BANNED):
                bad.append(f"{path}.{k} (key)")
            bad += wording_violations(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            bad += wording_violations(v, f"{path}[{i}]")
    elif isinstance(obj, str) and any(b.search(obj) for b in BANNED):
        bad.append(f"{path}: {obj!r}")
    return bad


def to_tables(out: dict) -> dict[str, pd.DataFrame]:
    reg, prov, leg = [], [], []
    for q in out["quarters"]:
        r = q["regional_layer"]
        t = r["trend"] or {}
        reg.append({"quarter": q["quarter"], "scope": r["scope"], "status": r["status"], "level_pct": r["level_pct"],
                    "n_rounds": len(r["rounds"]), "series": "|".join(sorted({x["series"] for x in r["rounds"]})),
                    "latest_publication_date": r["latest_publication_date"],
                    "trend_change_pct_points": t.get("change_pct_points"),
                    "compared_with_quarter": t.get("compared_with_quarter"), "quarters_apart": t.get("quarters_apart")})
        pl = q["provincial_layer"]
        for p in pl["provinces"]:
            prov.append({"quarter": q["quarter"], "status": pl["status"], "province_code": p["province_code"],
                         "province": p["province"], "food_inflation_yoy_pct": p["food_inflation_yoy_pct"],
                         "five_province_mean_F_pct_unweighted": pl["five_province_mean_F_pct_unweighted"],
                         "relative_pressure_D_pp": p["relative_pressure_D_pp"],
                         "relative_pressure_rank": p["relative_pressure_rank"], "tied_with": "|".join(p["tied_with"])})
        lg = q["legacy_layer"]
        for p in lg["provinces"]:
            leg.append({"quarter": q["quarter"], "status": lg["status"], "province_code": p["province_code"],
                        "province": p["province"], "H_A_production_rounds_pct": lg["H_A_production_rounds_pct"],
                        "S1": p["S1"], "label": p["label"], "threshold": lg["threshold"]})
    return {"regional_layer": pd.DataFrame(reg), "provincial_layer": pd.DataFrame(prov),
            "legacy_layer": pd.DataFrame(leg)}
