"""E65 shared library: the E56 code path (read-only), the climate variants of PROTOCOL.md section 4, the PAGASA ENSO
status at each issue date, and small statistics.

E65 never writes into E56-E62, backend/data or the sealed files; every output goes under E65/out and E65/tables.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E65 = Path(__file__).resolve().parents[1]
EXP = E65.parent
ROOT = EXP.parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, I7, L, P2, np, pd = G.E, G.F, G.I7, G.L, G.P2, G.np, G.pd
CLIMATE_FILE = ROOT / "aipheed-backend-aligned" / "data" / "processed" / "pagasa_climate.parquet"
E57_SEALED = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"
E58_SEALED = EXP / "E58_Rising_Stress_Early_Warning" / "sealed" / "predictions.csv"
E58_EVENTS = EXP / "E58_Rising_Stress_Early_Warning" / "data" / "events.csv"
E58_RECORD = BACKEND / "data" / "e58" / "e58_record.json"
ART = BACKEND / "data" / "e56" / "model"
OUT, TABLES = E65 / "out", E65 / "tables"
EVAL_ORIGINS = list(range(L.qi("2023-Q4"), L.qi("2026-Q1") + 1))     # E57: targets 2024-Q2..2026-Q3, 50 rows
FORWARD_ORIGINS = [L.qi("2026-Q2"), L.qi("2026-Q3")]                  # targets 2026-Q4 (issued 07-01), 2027-Q1 (10-01)

# ------------------------------------------------------------------------------------------------ PAGASA ENSO status
# Official PAGASA ENSO Alert and Warning System status in force on the issue date O(t) (exclusive), from the dated
# press releases and advisories in sources/SOURCES.md. Ordinal: El Nino Advisory +2, Alert +1, Watch +0.5, none 0,
# La Nina Watch -0.5, Alert -1, Advisory -2. When an El Nino Advisory and a La Nina Watch are both in force
# (2024-04-01), the condition present (the advisory) is coded.
PAGASA_STATUS = {   # key: issue date O(t)
    "2021-10-01": (-1.0, "La Nina Alert (2021-09-14)"),
    "2022-01-01": (-2.0, "La Nina Advisory (onset 2021-10-15)"),
    "2022-04-01": (-2.0, "La Nina Advisory (inferred: La Nina persisted through 2022, PAGASA 2022 climate summary)"),
    "2022-07-01": (-2.0, "La Nina Advisory (inferred, as above)"),
    "2022-10-01": (-2.0, "La Nina Advisory (inferred, as above)"),
    "2023-01-01": (-2.0, "La Nina Advisory (inferred, as above)"),
    "2023-04-01": (0.5, "El Nino Watch (2023-03-24)"),
    "2023-07-01": (1.0, "El Nino Alert (2023-05-02); 'El Nino is present' came 2023-07-04, after the issue date"),
    "2023-10-01": (2.0, "El Nino Advisory (El Nino present since 2023-07-04)"),
    "2024-01-01": (2.0, "El Nino Advisory"),
    "2024-04-01": (2.0, "El Nino Advisory No. 9 / La Nina Watch (2024-03-07)"),
    "2024-07-01": (-0.5, "El Nino Final Advisory (2024-06-07); La Nina Watch in force"),
    "2024-10-01": (-1.0, "La Nina Alert (2024-07-12)"),
    "2025-01-01": (-1.0, "La Nina Alert; 'La Nina present' came 2025-01-06, after the issue date"),
    "2025-04-01": (-2.0, "La Nina Advisory (2025-01-06); terminated 2025-04-04, after the issue date"),
    "2025-07-01": (0.0, "none (La Nina Alert terminated 2025-04-04)"),
    "2025-10-01": (-1.0, "La Nina Alert (2025-09-15); 'La Nina present' came 2025-10-10, after the issue date"),
    "2026-01-01": (-2.0, "La Nina Advisory (2025-10-10; Advisory #1 2025-12-04)"),
    "2026-04-01": (0.5, "El Nino Watch (2026-03-25); La Nina Final Advisory 2026-03-09"),
    "2026-07-01": (2.0, "El Nino Advisory No. 1 (2026-06-09): El Nino present, >80% full-blown, until early 2027"),
    "2026-10-01": (2.0, "El Nino Advisory No. 4 (2026-09-07): moderate to strong, may reach very strong, until H1 "
                        "2027; Climate Advisory 2026-09-23: intensifying to very strong in SOND 2026"),
}
INTENSITY = {"NEUTRAL": 0, "WEAK": 1, "MODERATE": 2, "STRONG": 3, "VERY_STRONG": 4}
CLIMATE_PRICE = list(P2.PRICE_GROUPS["climate"])
CLIMATE_HUNGER = list(P2.HUNGER_GROUPS["climate"])


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_sealed() -> dict:
    out = {}
    for p in (E57_SEALED, E58_SEALED):
        want = (p.parent / "predictions.csv.sha256").read_text().split()[0]
        if sha(p) != want:
            raise SystemExit(f"{p} changed after sealing")
        out[str(p.relative_to(EXP))] = want
    return out


def verify_protocol() -> str:
    want = (E65 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E65 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("PROTOCOL.md changed after freezing")
    return got


def dump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(obj, indent=1, default=float).encode("utf-8"))


def write_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(df.to_csv(index=False, float_format="%.6g").encode("utf-8"))


def climate_raw() -> pd.DataFrame:
    """The climate parquet (window-checked from its column statistics before loading, as in E43)."""
    import pyarrow.parquet as pq
    f = pq.ParquetFile(CLIMATE_FILE)
    i = f.schema_arrow.names.index("year")
    if min(f.metadata.row_group(r).column(i).statistics.min for r in range(f.metadata.num_row_groups)) < 2021:
        raise L.WindowViolation("climate parquet holds pre-2021 rows")
    c = pd.read_parquet(CLIMATE_FILE)
    c["q"] = c["quarter"].map(L.qi)
    return c


def signed_intensity(row) -> float:
    s = INTENSITY.get(row["enso_intensity"], np.nan)
    return float(-s if row["enso_phase"] == "LA_NINA" else s)


def official_status(t: int) -> float:
    return PAGASA_STATUS[str(L.origin(t).date())][0]


def add_climate_variants(X: pd.DataFrame) -> pd.DataFrame:
    """Columns for arms B1/B2 (PROTOCOL 4): signed ENSO intensity at t-1 and t-2 (same timing as the served phase
    code), its CPI-momentum interaction, and the PAGASA status on the issue date O(t)."""
    c = climate_raw()
    reg = c.drop_duplicates("q").set_index("q")
    si = reg.apply(signed_intensity, axis=1)
    X = X.copy()
    X["enso_int"] = X["t"].map(lambda t: si.get(t - 1, np.nan))
    X["enso_int_l2"] = X["t"].map(lambda t: si.get(t - 2, np.nan))
    X["enso_int_x_mom"] = X["enso_int"] * X["mom3"]
    X["pagasa_enso"] = X["t"].map(official_status)
    return X


ARMS = {
    # name: (price climate columns, hunger climate columns, drop news_climate)
    "A": (CLIMATE_PRICE, CLIMATE_HUNGER, False),
    "B1": ([c for c in CLIMATE_PRICE if c not in ("enso", "enso_l2", "enso_x_mom")] + ["enso_int", "enso_int_l2",
                                                                                     "enso_int_x_mom"],
           [c for c in CLIMATE_HUNGER if c not in ("enso", "enso_l2")] + ["enso_int", "enso_int_l2"], False),
    "B2": ([c for c in CLIMATE_PRICE if c not in ("enso", "enso_l2", "enso_x_mom")] + ["enso_int", "enso_int_l2",
                                                                                     "enso_int_x_mom", "pagasa_enso"],
           [c for c in CLIMATE_HUNGER if c not in ("enso", "enso_l2")] + ["enso_int", "enso_int_l2", "pagasa_enso"],
           False),
    "B3": (CLIMATE_PRICE + ["pagasa_enso"], CLIMATE_HUNGER + ["pagasa_enso"], False),
    "C": ([], [], True),
}


@contextlib.contextmanager
def arm_groups(arm: str):
    """Temporarily set the E44 climate groups (dicts shared by e44/e53/e55/e56 code) to an arm's columns."""
    saved = copy.deepcopy((P2.PRICE_GROUPS, P2.HUNGER_GROUPS))
    pc, hc, drop_news = ARMS[arm]
    P2.PRICE_GROUPS["climate"][:] = pc
    P2.HUNGER_GROUPS["climate"][:] = hc
    if drop_news:
        P2.PRICE_GROUPS["news"][:] = [c for c in P2.PRICE_GROUPS["news"] if c != "news_climate"]
    try:
        yield
    finally:
        for k in P2.PRICE_GROUPS:
            P2.PRICE_GROUPS[k][:] = saved[0][k]
        for k in P2.HUNGER_GROUPS:
            P2.HUNGER_GROUPS[k][:] = saved[1][k]


def run_arm(d, X, B, arm: str, origins, space=None, keep_models=False) -> list[dict]:
    space = space or G.search_space()
    out = []
    with arm_groups(arm):
        for t in origins:
            fx = G.tuned_forecast(d, X, B, t, space)
            for i, p in enumerate(L.PROVS):
                out.append({"arm": arm, "t": t, "origin_quarter": L.qs(t), "issue_date": str(L.origin(t).date()),
                            "target": L.qs(t + 2), "province_code": p, "province": L.NAMES[p],
                            "p": float(fx["p"][i]), "p_price": float(fx["p_price"][i]),
                            "p_hunger": float(fx["p_hunger"]), "H_hat": float(fx["H_hat"]), "config": int(fx["cfg"]["id"]),
                            "cols": "|".join(fx["cols"]),
                            "hunger_cols": "|".join(fx["hc"]["model"].cols) if fx["hc"]["model"] is not None else ""})
            if keep_models:
                out[-1]["_fx"] = fx
            print(arm, L.qs(t), "config", fx["cfg"]["id"], flush=True)
    return out


# ------------------------------------------------------------------------------------------------ statistics
def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [float(max(0, c - h)), float(min(1, c + h))]


def rows50() -> pd.DataFrame:
    S = pd.read_csv(E58_SEALED, dtype={"province_code": str})
    ev = pd.read_csv(E58_EVENTS, dtype={"province_code": str})
    R = S.merge(ev[["t", "province_code", "HIGH", "ONSET", "RISEP", "last_known_T43"]], on=["t", "province_code"],
                how="left")
    S57 = pd.read_csv(E57_SEALED, dtype={"province_code": str})[["t", "province_code", "E56_p", "MAJORITY_p"]]
    R = R.merge(S57.rename(columns={"E56_p": "E56_p_e57"}), on=["t", "province_code"], how="left")
    assert len(R) == 50 and R["HIGH"].notna().all() and (R["E56_p"] - R["E56_p_e57"]).abs().max() < 1e-9
    return R.drop(columns=["E56_p_e57"])
