"""E43: E36 + ONE composite feature per driver (lead 1).

E36's walk-forward (e36_lib.walk_forward) runs unchanged; E43 arms are extra pools in memory only. Inputs are the
refreshed E43 files (backend/experiments/e43/data/), plus pagasa_climate.parquet (storms) and the E31 news store
(fish-kill titles, via e38_lib's trigger shares), all read only.

Timing: at origin O(t) a composite uses data of quarter t-1 (news: quarter t). Every reference statistic (percent rank,
mean, standard deviation) is EXPANDING over 2021-Q1..t-1, pooled over provinces. No quarter before 2021-Q1 is used
(the study's data authorization), so year-on-year changes start at 2022-Q1.

  CLIM = max( PR(|rain_anom_{p,t-1}|), PR(tc_max_signal_{p,t-1}) )
  FISH = max( PR(max(0, -ln(V_{p,t-1}/V_{p,t-5}))), 1[fish-kill titles_{p,t} >= 1] )   (production = proxy)
  EMP  = 0.5 z(u_{t-1}) + 0.5 z(u_{t-1} - u_{t-5}),  u = quarterly MEAN unemployment, observed quarters only
  OFW  = max(0, -g_real_{p,t-1})                                                       (PROVISIONAL data)
PR(x) = #{r < x} / (n - 1) over the reference values (0..1). Missing -> NaN. LightGBM fits with monotone constraint +1
on the composites and 0 on E36's inputs.
"""
from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path

E43 = Path(__file__).resolve().parents[1]
ROOT = E43.parents[2]
E38_RUNNER = ROOT / "aipheed-backend-aligned" / "experiments" / "E38_Lead2_Diagnosis_Tuning" / "runner"
sys.path.insert(0, str(E38_RUNNER))
import e38_lib as L8  # noqa: E402

L7, L6 = L8.L7, L8.L7.L6
L6.guard32.EXP = E43                       # writes confined to E43 (and the OS temp directory)
C, np, pd = L8.C, L8.np, L8.pd
qk, qs, PROVS = C.qk, C.qs, C.PROVS
DATA = E43 / "data"
INPUTS = {"rain": DATA / "rainfall_daily_province.parquet", "fish": DATA / "fisheries_production.parquet",
          "unemp": DATA / "unemployment_quarterly.parquet", "ofw": DATA / "real_peso_inputs.parquet",
          "tc": ROOT / "backend" / "data" / "processed" / "pagasa_climate.parquet"}
FIRST_Q = qk("2021-Q1")

COMPOSITES = ["CLIM", "FISH", "EMP", "OFW"]
GROUPS = {"market": ["D_last", "Dnow", "rice_rel"], "climate": ["CLIM"], "fish_kill": ["FISH"],
          "employment": ["EMP"], "ofw_remittance": ["OFW"]}          # every other model input = "other"


def _qcol(df):
    q = df["quarter"].astype(str)
    if q.str.contains("Q").all():
        return q.map(qk)
    return (df["year"].astype(int).astype(str) + "-Q" + df["quarter"].astype(int).astype(str)).map(qk)


def pr(x, ref) -> float:
    """Percent rank of x among the reference values (0..1); NaN if x is missing or fewer than 2 references."""
    ref = [v for v in ref if v == v]
    if x != x or len(ref) < 2:
        return np.nan
    return sum(1 for v in ref if v < x) / (len(ref) - 1)


class Data(L8.Data):
    """E36 features + e38 news-trigger shares + the four E43 composites; lead 1 by default."""

    def __init__(self):
        super().__init__()
        r = pd.read_parquet(INPUTS["rain"])
        r = r[r["observed"] == 1].assign(tq=r["quarter"].map(qk))
        self.rain = {(p, int(t)): abs(float(v)) for p, t, v in zip(r["province_code"], r["tq"], r["value"])}
        c = pd.read_parquet(INPUTS["tc"])
        c = c.assign(tq=_qcol(c))
        self.tc = {(p, int(t)): float(v) for p, t, v in zip(c["province_code"], c["tq"], c["tc_max_signal"])}
        f = pd.read_parquet(INPUTS["fish"])
        f = f[(f["subsector"] == "FISHERIES") & (f["province_code"] != "REGION") & (f["observed"] == 1)]
        vol = {(p, qk(q)): float(v) for p, q, v in zip(f["province_code"], f["quarter"], f["value"])}
        self.fish_decline = {}
        for (p, t), v in vol.items():
            prev = vol.get((p, t - 4))
            if t - 4 >= FIRST_Q and prev and prev > 0 and v > 0:
                self.fish_decline[(p, t)] = max(0.0, -math.log(v / prev))
        u = pd.read_parquet(INPUTS["unemp"])
        u = u[u["observed"] == 1]
        self.u = {qk(q): float(v) for q, v in zip(u["quarter"], u["value"]) if qk(q) >= FIRST_Q}
        self.du = {t: self.u[t] - self.u[t - 4] for t in self.u if (t - 4) in self.u}
        o = pd.read_parquet(INPUTS["ofw"])
        o = o[o["observed"] == 1]
        self.greal = {(p, qk(q)): float(v) for p, q, v in zip(o["province_code"], o["quarter"], o["g_real_pct"])}
        self._cache: dict = {}

    def train(self, t, k=1):
        return super().train(t, k)

    def test(self, t, k=1):
        return super().test(t, k)

    # ---------------------------------------------------------------- composites for one (province, origin t)
    def composites(self, p: str, t: int) -> dict:
        key = (p, t)
        if key in self._cache:
            return self._cache[key]
        q = t - 1                                          # data quarter
        prov_ref = lambda table: [v for (pp, tt), v in table.items() if FIRST_Q <= tt <= q]
        out = {}
        # CLIM
        rain = self.rain.get((p, q), np.nan) if q >= FIRST_Q else np.nan
        tc = self.tc.get((p, q), np.nan) if q >= FIRST_Q else np.nan
        parts = [pr(rain, prov_ref(self.rain)), pr(tc, prov_ref(self.tc))]
        parts = [v for v in parts if v == v]
        out["CLIM"] = max(parts) if parts else np.nan
        out["CLIM_src"] = q
        # FISH
        dec = self.fish_decline.get((p, q), np.nan)
        dec_pr = pr(dec, prov_ref(self.fish_decline))
        news = 1.0 if self.trig.get((p, t), {}).get("trig_fish_kill", 0.0) > 0 else 0.0
        out["FISH"] = max(dec_pr, news) if dec_pr == dec_pr else (1.0 if news else np.nan)
        out["FISH_src"] = q
        # EMP (national)
        ref_u = [v for tt, v in self.u.items() if tt <= q]
        ref_du = [v for tt, v in self.du.items() if tt <= q]
        if q in self.u and q in self.du and len(ref_u) >= 2 and len(ref_du) >= 2:
            z1 = (self.u[q] - np.mean(ref_u)) / np.std(ref_u, ddof=1)
            z2 = (self.du[q] - np.mean(ref_du)) / np.std(ref_du, ddof=1)
            out["EMP"] = 0.5 * z1 + 0.5 * z2
        else:
            out["EMP"] = np.nan
        out["EMP_src"] = q
        # OFW (provisional)
        g = self.greal.get((p, q), np.nan)
        out["OFW"] = max(0.0, -g) if g == g else np.nan
        out["OFW_src"] = q
        out["ref_max"] = q                                   # every reference above stops at t-1
        self._cache[key] = out
        return out

    def _add(self, X: pd.DataFrame, tcol: str) -> pd.DataFrame:
        X = super()._add(X, tcol)
        comp = [self.composites(p, int(t)) for p, t in zip(X["province_code"], X[tcol])]
        for k in COMPOSITES + [f"{c}_src" for c in COMPOSITES] + ["ref_max"]:
            X[k] = [c[k] for c in comp]
        return X


def leakage_check(X: pd.DataFrame, tcol: str = "t") -> list[str]:
    t = X[tcol].astype(int)
    problems = []
    for c in COMPOSITES + ["ref"]:
        col = "ref_max" if c == "ref" else f"{c}_src"
        bad = (X[col] > t - 1) | (X[col] < FIRST_Q - 1)
        if bad.any():
            problems.append(f"{c}: {int(bad.sum())} rows use data after t-1")
    return problems


def install_monotone():
    """Fit with monotone_constraints = +1 for composites, 0 otherwise; untouched when no composite is in the set."""
    original = L6.fit_lgbm

    def fit(tr, feats, g):
        cons = [1 if f in COMPOSITES else 0 for f in feats]
        if not any(cons):
            return original(tr, feats, g)
        import lightgbm as lgb

        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            return None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return lgb.LGBMClassifier(**L6._BASE, **L6.GRID[g], monotone_constraints=cons).fit(tr[feats].astype(float), y)

    L6.fit_lgbm = fit


ARM_SETS = {"E43-all4": COMPOSITES, "E43-noOFW": ["CLIM", "FISH", "EMP"], "E43-CLIM": ["CLIM"], "E43-FISH": ["FISH"],
            "E43-EMP": ["EMP"], "E43-OFW": ["OFW"]}
PROVISIONAL = {"E43-all4", "E43-all4-fixed", "E43-OFW"}


def register_pools():
    for arm, extra in ARM_SETS.items():
        tag = arm.split("-", 1)[1]
        L6.FEATURE_SETS[f"COMPACT_{tag}"] = L6.COMPACT + extra
        L6.FEATURE_SETS[f"COMB_{tag}"] = L6.COMB + extra
        L6.POOLS[arm] = ([(f"COMPACT_{tag}", g) for g in L6.COMPLEXITY] + [(f"COMB_{tag}", g) for g in L6.COMPLEXITY],
                         (f"COMB_{tag}", "G1"))
    L6.POOLS["E43-all4-fixed"] = ([("COMB_all4", "G2")], ("COMB_all4", "G2"))
