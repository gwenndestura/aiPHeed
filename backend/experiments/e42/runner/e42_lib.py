"""E42: do the four other risk drivers add to E36 when KEPT ON TOP of its 13 inputs? (lead 1 only)

E36's walk-forward is run unchanged (e36_lib.walk_forward: target S1 = H + 2D above the trailing-median tau, labels,
origins = targets 2022-Q4..2026-Q3, training-row rule, LightGBM settings G1/G4/G3/G2 with seed 36, the nested rule
"lowest mean per-date Brier on eligible prior dates, tie 0.002 -> simpler", threshold 0.5, the six baselines). E42
adds pools in memory only; no E36 file is modified. The E39-E41 builders were removed with the bf94bb3 revert, so the
driver features are rebuilt here from backend/data/processed (read only).

Driver features (2 per driver, 8 in total). Timing rule = E36's: at origin O(t) (00:00 PHT on the first day of
quarter t+1) a province/national series contributes its value for quarter t-1, news its titles published in quarter t.
  Climate Stress   rain_absanom_l1  |rainfall anomaly| (% vs 1991-2020 normal), NASA POWER, province, quarter t-1
                   tc_max_l1        strongest tropical-cyclone signal within 300 km, NOAA IBTrACS, province, t-1
  Fish Kill        fish_chg_l1      PROXY: total fisheries production YoY log change, PSA, province, t-1
                   trig_fish_kill   share of the province's news titles classified as fish kill, quarter t
  Employment       u_nat_l1         national unemployment rate, PSA LFS, t-1; observed through 2025-Q4, carried forward
                   u_stale          1 when u_nat_l1 is a carried-forward 2025-Q4 value
  OFW Remittance   remit_l1         national OFW cash remittances YoY growth, BSP, t-1; observed through 2025-Q4,
                                    carried forward
                   remit_stale      1 when remit_l1 is carried forward
No quarter before 2021-Q1 enters a feature (the 1991-2020 rainfall normal is a fixed reference, not data of a quarter).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

E42 = Path(__file__).resolve().parents[1]
ROOT = E42.parents[2]
E38_RUNNER = ROOT / "aipheed-backend-aligned" / "experiments" / "E38_Lead2_Diagnosis_Tuning" / "runner"
sys.path.insert(0, str(E38_RUNNER))
import e38_lib as L8  # noqa: E402

L7, L6 = L8.L7, L8.L7.L6
L6.guard32.EXP = E42                       # writes confined to E42 (and the OS temp directory)
C, np, pd = L8.C, L8.np, L8.pd
qk, qs, PROVS = C.qk, C.qs, C.PROVS
PROC = ROOT / "backend" / "data" / "processed"
INPUTS = {"rain": PROC / "province_rainfall.parquet", "tc": PROC / "pagasa_climate.parquet",
          "fish": PROC / "food_availability_panel.parquet", "unemp": PROC / "psa_indicators.parquet",
          "bsp": PROC / "bsp_macro.parquet"}
FIRST_Q, LAST_NAT = qk("2021-Q1"), qk("2025-Q4")

DRIVERS = {"climate": ["rain_absanom_l1", "tc_max_l1"], "fish_kill": ["fish_chg_l1", "trig_fish_kill"],
           "employment": ["u_nat_l1", "u_stale"], "ofw_remittance": ["remit_l1", "remit_stale"]}
DRV8 = [f for v in DRIVERS.values() for f in v]
MARKET = ["D_last", "Dnow", "rice_rel"]
GROUPS = {"market": MARKET, **DRIVERS}                        # everything else in a model = "other"
SRC = {"rain_absanom_l1": "rain_src", "tc_max_l1": "tc_src", "fish_chg_l1": "fish_src", "u_nat_l1": "u_src",
       "remit_l1": "remit_src"}                               # data quarter each lagged value came from


def _quarter(df: pd.DataFrame) -> pd.Series:
    q = df["quarter"].astype(str)
    if q.str.contains("Q").all():
        return q.map(qk)
    return (df["year"].astype(int).astype(str) + "-Q" + df["quarter"].astype(int).astype(str)).map(qk)


class Data(L8.Data):
    """E36 features (E32 builder), E38's news trigger shares, and the E42 driver features; lead 1 by default."""

    def __init__(self):
        super().__init__()
        r = pd.read_parquet(INPUTS["rain"])
        r = r.assign(tq=_quarter(r))
        self.rain = {(p, int(t)): abs(float(v)) for p, t, v in zip(r["province_code"], r["tq"], r["rainfall_anomaly_pct"])}
        self.rain_daily = {(p, int(t)) for p, t, u in zip(r["province_code"], r["tq"], r["source_url"]) if "/daily/" in str(u)}
        c = pd.read_parquet(INPUTS["tc"])
        c = c.assign(tq=_quarter(c))
        self.tc = {(p, int(t)): float(v) for p, t, v in zip(c["province_code"], c["tq"], c["tc_max_signal"])}
        f = pd.read_parquet(INPUTS["fish"])
        f = f[f["group"] == "fisheries"]
        vol = f.assign(tq=f["quarter"].map(qk)).groupby(["province_code", "tq"])["volume"].sum().to_dict()
        self.fish = {}
        for (p, t), v in vol.items():
            prev = vol.get((p, t - 4))
            if t - 4 >= FIRST_Q and prev and prev > 0 and v > 0:
                self.fish[(p, int(t))] = math.log(v / prev)
        u = pd.read_parquet(INPUTS["unemp"])
        u = u.assign(tq=_quarter(u))
        per_q = u.groupby("tq")["unemployment_rate"].agg(["first", "nunique"])
        assert (per_q["nunique"] == 1).all(), "unemployment differs between provinces: not the national series"
        self.u = {int(t): float(v) for t, v in per_q["first"].items() if FIRST_Q <= t <= LAST_NAT}
        b = pd.read_parquet(INPUTS["bsp"])
        b = b.assign(tq=b["quarter"].map(qk))
        g = b.groupby("tq")["ofw_remit_yoy_pct"].first().dropna()
        self.remit = {int(t): float(v) for t, v in g.items() if FIRST_Q <= t <= LAST_NAT}

    # lead 1 (E36 calls train(t) / test(t))
    def train(self, t, k=1):
        return super().train(t, k)

    def test(self, t, k=1):
        return super().test(t, k)

    @staticmethod
    def _carry(table: dict, t: int):
        """National value of t-1; after the series ends, the last observed value at or before t-1 (stale)."""
        want = t - 1
        if want in table:
            return table[want], want, 0
        older = [q for q in table if q <= want]
        if not older:
            return np.nan, np.nan, 0
        q = max(older)
        return table[q], q, 1

    def _add(self, X: pd.DataFrame, tcol: str) -> pd.DataFrame:
        X = super()._add(X, tcol)                          # E38: trig_* (news titles of quarter t)
        ts = X[tcol].astype(int).tolist()
        codes = X["province_code"].tolist()

        def lag(table, p, t):
            key = (p, t - 1)
            return (table[key], t - 1) if t - 1 >= FIRST_Q and key in table else (np.nan, np.nan)

        for name, table in (("rain_absanom_l1", self.rain), ("tc_max_l1", self.tc), ("fish_chg_l1", self.fish)):
            vals = [lag(table, p, t) for p, t in zip(codes, ts)]
            X[name] = [v for v, _ in vals]
            X[SRC[name]] = [s for _, s in vals]
        X["rain_daily_service"] = [int((p, t - 1) in self.rain_daily) for p, t in zip(codes, ts)]
        for name, flag, table in (("u_nat_l1", "u_stale", self.u), ("remit_l1", "remit_stale", self.remit)):
            vals = [self._carry(table, t) for t in ts]
            X[name] = [v for v, _, _ in vals]
            X[SRC[name]] = [s for _, s, _ in vals]
            X[flag] = [float(st) for _, _, st in vals]
        return X


def leakage_check(X: pd.DataFrame, tcol: str = "t") -> list[str]:
    """Every lagged value must come from a data quarter <= t-1 and >= 2021-Q1; news triggers are of quarter t."""
    problems = []
    for f, s in SRC.items():
        src, t = X[s], X[tcol].astype(int)
        bad = src.notna() & ((src > t - 1) | (src < FIRST_Q))
        if bad.any():
            problems.append(f"{f}: {int(bad.sum())} rows use a quarter after t-1 or before 2021-Q1")
    return problems


def register_pools():
    """E42 arms as extra e36_lib pools (in memory only). Nested arms use E36's grid and rule."""
    base = {"COMPACT": L6.COMPACT, "COMB": L6.COMB}
    extra = {"D8": DRV8, "CLIM": DRIVERS["climate"], "FISH": DRIVERS["fish_kill"], "EMP": DRIVERS["employment"],
             "OFW": DRIVERS["ofw_remittance"]}
    for bk, bf in base.items():
        for ek, ef in extra.items():
            L6.FEATURE_SETS[f"{bk}_{ek}"] = bf + ef
    nested = lambda ek: ([(f"COMPACT_{ek}", g) for g in L6.COMPLEXITY] + [(f"COMB_{ek}", g) for g in L6.COMPLEXITY],
                         (f"COMB_{ek}", "G1"))
    L6.POOLS.update({
        "E42-nested": nested("D8"),
        "E42-fixed": ([("COMB_D8", "G2")], ("COMB_D8", "G2")),
        "E36-fixed-COMBxG2": ([("COMB", "G2")], ("COMB", "G2")),     # diagnostic: E36's served setting, no selection
        "E42-abl-Climate": nested("CLIM"),
        "E42-abl-FishKill": nested("FISH"),
        "E42-abl-Employment": nested("EMP"),
        "E42-abl-OFW": nested("OFW"),
    })
