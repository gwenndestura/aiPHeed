"""
E134 walk-forward (protocol 139ca7f): area-level climate (NASA POWER rainfall deficit) and agriculture (PSA palay
production drop) drivers added to E133's HFM-X, plus E134-AREA-O, E134-ONI (= E133 PH2) and E134-ENS, against the
reproduced E133/E132 models under the unchanged target, tolerance, leads, N1-N7 and P-DASH.

    python -I runner/e134_baseline.py   (first: exact E133 reproduction into out/baseline)
    python -I runner/e134_run.py
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
OUT = ROOT / "out"
RAW = ROOT / "data" / "raw"
sys.path.insert(0, str(EXP / "E133_Forecasting_Breakthrough" / "runner"))
import e133_models as M  # noqa: E402
import e133_run as R  # noqa: E402

X, L = R.X, R.L
warnings.filterwarnings("ignore")
AREA_GROUPS = ("aR", "aP")
PALAY_LAG = 75
REGION_AREA = {
    "metro_manila": ["NCR"],
    "balance_luzon": ["CAR", "Region I", "Region II", "Region III", "Region IV-A", "MIMAROPA", "Region V"],
    "visayas": ["Region VI", "Region VII", "Region VIII", "NIR"],
    "mindanao": ["Region IX", "Region X", "Region XI", "Region XII", "Region XIII", "BARMM"]}
PALAY_KEYS = {"CAR": "(CAR)", "Region I": "REGION I (", "Region II": "REGION II (", "Region III": "REGION III (",
              "Region IV-A": "REGION IV-A", "MIMAROPA": "MIMAROPA", "Region V": "REGION V (", "Region VI": "REGION VI (",
              "Region VII": "REGION VII (", "Region VIII": "REGION VIII (", "NIR": "NEGROS ISLAND", "Region IX": "REGION IX (",
              "Region X": "REGION X (", "Region XI": "REGION XI (", "Region XII": "REGION XII (", "Region XIII": "REGION XIII (",
              "BARMM": "BANGSAMORO"}
NEW = ["E134-AREA-T", "E134-AREA-O", "E134-ONI", "E134-ENS"]
ABL = {"AREA-T-minus-aR": ("rice", R.ALL_GROUPS + ("aP",), 0), "AREA-T-minus-aP": ("rice", R.ALL_GROUPS + ("aR",), 0),
       "AREA-T-delayed": ("rice", R.ALL_GROUPS + AREA_GROUPS, 1)}
VARIANTS = {"E134-AREA-T": ("rice", R.ALL_GROUPS + AREA_GROUPS, 0), "E134-AREA-O": ("oni", R.ALL_GROUPS + AREA_GROUPS, 0), **ABL}


# ------------------------------------------------------------------ area-level drivers in the state equation
_exog133 = getattr(M, "_exog_e133", M._exog)      # idempotent: never wrap an already wrapped function
M._exog_e133 = _exog133


def _exog134(fit, z, w):
    """E133 drivers plus area drivers: beta * z_a moves the area level c + d_a (area mean into c, deviation into d)."""
    u = _exog133(fit, z, w)
    for g in AREA_GROUPS:
        if g in fit.beta and g in z:
            za = np.asarray(z[g], float)
            u[M.IC] += fit.beta[g] * za.mean()
            u[M.ID] += fit.beta[g] * (za - za.mean())
    return u


M._exog = _exog134


def _q(d: pd.Timestamp) -> int:
    return d.year * 4 + (d.month - 1) // 3


def rainfall_regional() -> pd.DataFrame:
    """Quarterly precipitation total (mm) per regional centre, complete quarters only."""
    rows = []
    for region in sum(REGION_AREA.values(), []):
        j = json.loads((RAW / f"nasa_power_daily_{region.replace(' ', '_')}.json").read_text())
        s = pd.Series(j["properties"]["parameter"]["PRECTOTCORR"], dtype=float)
        s.index = pd.to_datetime(s.index, format="%Y%m%d")
        s = s[s >= 0]
        g = s.groupby(s.index.map(_q)).agg(["sum", "count"])
        for qi, r in g.iterrows():
            if r["count"] >= 88:
                rows.append({"region": region, "qi": int(qi), "rain": float(r["sum"])})
    d = pd.DataFrame(rows)
    assert d["qi"].min() >= L.qi("2021-Q1")
    d["available"] = d["qi"].map(lambda i: L.qend(L.qs(int(i))) + timedelta(days=10))
    return d


def palay_area() -> pd.DataFrame:
    """Area palay production YoY % (consistent region set per quarter pair), 2022+; drop = -YoY."""
    p = pd.read_csv(RAW / "psa_palay_corn_production_quarter_2021_2026.csv", encoding="utf-8-sig")
    p = p[(p["Ecosystem/Croptype"] == "Palay") & p["Geolocation"].str.match(r"^\.\.[A-Z]")]
    cols = [c for c in p.columns if c[:4].isdigit()]
    assert all(int(c[:4]) >= 2021 for c in cols)
    long = p.melt(id_vars=["Geolocation"], value_vars=cols, var_name="period", value_name="v")
    long["v"] = pd.to_numeric(long["v"], errors="coerce")
    long["qi"] = long["period"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    rows = []
    for a, regs in REGION_AREA.items():
        regs = [r for r in regs if r in PALAY_KEYS]          # NCR grows no palay: Metro Manila gets no aP value (0)
        sel = long[long["Geolocation"].apply(lambda g: any(PALAY_KEYS[r] in g for r in regs))]
        w = sel.pivot_table(index="qi", columns="Geolocation", values="v")
        for qi in w.index:
            if qi - 4 not in w.index:
                continue
            ok = w.loc[qi].notna() & w.loc[qi - 4].notna()
            if ok.any():
                rows.append({"area": a, "qi": int(qi), "palay_yoy": float(w.loc[qi, ok].sum() / w.loc[qi - 4, ok].sum() * 100 - 100)})
    d = pd.DataFrame(rows)
    d["value"] = -d["palay_yoy"]
    d["available"] = d["qi"].map(lambda i: L.qend(L.qs(int(i))) + timedelta(days=PALAY_LAG))
    return d


class AreaDrivers:
    def __init__(self):
        self.rain = rainfall_regional()
        self.palay = palay_area()

    def at(self, issue: date, delay_q: int = 0):
        """In-fold area drivers {g: {qi: array(4)}} and the latest available quarter per driver. delay_q adds whole
        quarters to every availability date (perturbation test)."""
        cut = issue - timedelta(days=92 * delay_q)
        vals, last = {}, {}
        r = self.rain[self.rain["available"] <= cut].copy()
        if len(r):
            r["cq"] = r["qi"] % 4
            clim = r.groupby(["region", "cq"])["rain"].agg(["mean", "count"])
            r = r.join(clim, on=["region", "cq"])
            r = r[r["count"] >= 2]
            r["anom"] = r["rain"] - r["mean"]
            r["area"] = r["region"].map({x: a for a, rs in REGION_AREA.items() for x in rs})
            ar = r.groupby(["area", "qi"])["anom"].mean().reset_index()
            ar["value"] = -ar["anom"]
        else:
            ar = pd.DataFrame(columns=["area", "qi", "value"])
        p = self.palay[self.palay["available"] <= cut]
        for g, t in (("aR", ar), ("aP", p)):
            if len(t) < 8:
                vals[g], last[g] = {}, None
                continue
            mu, sd = t["value"].mean(), t["value"].std() or 1.0
            piv = ((t.pivot_table(index="qi", columns="area", values="value") - mu) / sd).reindex(columns=X.AREAS)
            vals[g] = {int(q): np.nan_to_num(row.to_numpy(float)) for q, row in piv.iterrows()}
            last[g] = int(piv.index.max())
        return vals, last

    @staticmethod
    def z_for(vals, last, q: int) -> dict:
        out = {}
        for g, v in vals.items():
            if q in v:
                out[g] = v[q]
            elif last.get(g) is not None and q > last[g]:
                out[g] = v[last[g]]
            else:
                out[g] = np.zeros(M.NA)
        return out


_XF: dict = {}


def xfit(qa, issue, drv, adrv, tag, groups, delay):
    key = (tag, issue, groups, delay, len(qa))
    if key in _XF:
        return _XF[key]
    b = R.base_fits(qa)
    idx, Yd, Rr = b["idx"], b["Yd"], b["R"]
    vals, last, w = drv[tag].at(issue)
    av, al = adrv.at(issue, delay)
    Z = [{**R.Drivers.z_for(vals, last, int(t) - 1), **AreaDrivers.z_for(av, al, int(t) - 1)} for t in idx]
    fit = M.fit_beta(Yd, Rr, idx, R.BRK, b["HFM-NS-DES"], Z, w, groups)
    _XF[key] = (fit, Z, vals, last, w, av, al)
    return _XF[key]


def predict(qa, issue, target, drv, adrv, variants=VARIANTS) -> dict:
    b = R.base_fits(qa)
    idx, Yd, Rr = b["idx"], b["Yd"], b["R"]
    upto = int(idx.max())
    steps = target - upto
    brk_in = [upto + 1 + j == R.BRK for j in range(steps)]
    Rm = np.array([np.nanmedian(Rr[:, a]) for a in range(M.NA)])
    res = {}
    for name, (tag, groups, delay) in variants.items():
        fit, Z, vals, last, w, av, al = xfit(qa, issue, drv, adrv, tag, groups, delay)
        x, P, _, _ = M.kfilter(Yd, Rr, idx, fit, R.BRK, Z, w)
        Zf = [{**R.Drivers.z_for(vals, last, upto + j), **AreaDrivers.z_for(av, al, upto + j)} for j in range(steps)]
        mean, var = M.forecast(x, P, fit, steps, Zf, w, brk_in)
        if target >= R.BRK:
            mean = mean + b["seas"][target % 4]
        res[name] = (mean, np.sqrt(var + fit.tau2 + Rm), fit)
    return res


def period(tq: str) -> str:
    q = L.qi(tq)
    return "pre-surge (<=2023)" if q < L.qi("2024-Q1") else ("surge 2024" if q < R.BRK else "post-break 2025+")


def main():
    P = pd.read_csv(OUT / "baseline" / "e133_predictions.csv")
    P["issue"] = pd.to_datetime(P["issue"]).dt.date
    rr = X.rounds()
    drv = {"rice": R.Drivers("rice"), "oni": R.Drivers("rice", "oni_quarter_mean")}
    adrv = AreaDrivers()
    adrv.palay.to_csv(OUT / "e134_area_palay.csv", index=False)
    adrv.rain.to_csv(OUT / "e134_regional_rainfall.csv", index=False)
    names = list(VARIANTS)
    for m in names:
        P[f"f_{m}"], P[f"sd_{m}"] = np.nan, np.nan
    for g in AREA_GROUPS:
        P[f"beta_{g}"] = np.nan
    for (pol, D, k), g in P.groupby(["policy", "D", "lead"]):
        issue = g["issue"].iloc[0]
        res = predict(X.asof(rr, issue), issue, L.qi(g["target"].iloc[0]), drv, adrv)
        for i in g.index:
            a = X.AREAS.index(P.at[i, "area"])
            for m in names:
                P.at[i, f"f_{m}"], P.at[i, f"sd_{m}"] = float(res[m][0][a]), float(res[m][1][a])
            for gg in AREA_GROUPS:
                P.at[i, f"beta_{gg}"] = res["E134-AREA-T"][2].beta.get(gg, np.nan)
    P["f_E134-ONI"], P["sd_E134-ONI"] = P["f_HFM-X-PH2"], P["sd_HFM-X-PH2"]
    P["f_E134-ENS"] = (P["f_HFM-X"] + P["f_SEAS-LLM"]) / 2
    P["sd_E134-ENS"] = (P["sd_HFM-X"] + P["sd_SEAS-LLM"]) / 2
    for m in names + ["E134-ONI", "E134-ENS"]:
        P[f"lo80_{m}"] = P[f"f_{m}"] - X.Z80 * P[f"sd_{m}"]
        P[f"hi80_{m}"] = P[f"f_{m}"] + X.Z80 * P[f"sd_{m}"]
    P["period"] = P["target"].map(period)
    P.to_csv(OUT / "e134_predictions.csv", index=False)

    refs = ["PERSIST", "CLIM", "LLM", "SEAS-LLM", "HFM-NS-DES", "HFM-X"]
    shared = P.dropna(subset=["f_RIDGE-ALL", "f_PSA-ONLY", "f_NLP-ONLY", "f_LGBM-ALL", "f_HYB-LGBM"])
    keys = set(zip(shared.policy, shared.area, shared.D, shared.lead))
    in_e132 = np.array([k in keys for k in zip(P.policy, P.area, P.D, P.lead)])
    r1, q1 = R.metrics(P, refs + NEW, "S-U", P.n_obs >= 8)
    r2, q2 = R.metrics(P, refs + R.E132_BASE + NEW, "S-E132", in_e132)
    rows = r1 + r2
    for per in ("pre-surge (<=2023)", "surge 2024", "post-break 2025+"):
        mask = (P.n_obs >= 1) & (P.period == per)
        for (pol, k), g in P[mask].groupby(["policy", "lead"]):
            for m in refs + NEW:
                e = g[f"f_{m}"] - g["y_true"]
                if e.isna().any():
                    continue
                rows.append({"set": f"period:{per}", "policy": pol, "lead": int(k), "model": m, "n": len(g),
                             "mae": float(e.abs().mean()), "rmse": float(np.sqrt((e ** 2).mean())), "bias": float(e.mean()),
                             "within_tolerance": float((e.abs() <= g["tol"]).mean()),
                             "n_quarters": int(g["target"].nunique())})
    Mt = pd.DataFrame(rows)
    Mt.to_csv(OUT / "e134_metrics.csv", index=False)
    L.dump({**q1, **q2}, OUT / "e134_rules.json")

    ab = []
    su = P[(P.n_obs >= 8)]
    for (pol, k), g in su.groupby(["policy", "lead"]):
        y, tol, tq = g["y_true"].to_numpy(), g["tol"].to_numpy(), g["target_q"].to_numpy()
        full = g["f_E134-AREA-T"].to_numpy()
        for v, ref in (("AREA-T-minus-aR", "E134-AREA-T"), ("AREA-T-minus-aP", "E134-AREA-T"), ("AREA-T-delayed", "E134-AREA-T"),
                       ("HFM-X (no area drivers)", "E134-AREA-T"), ("E134-AREA-T vs E134-AREA-O", "E134-AREA-O")):
            col = {"HFM-X (no area drivers)": "f_HFM-X", "E134-AREA-T vs E134-AREA-O": "f_E134-AREA-T"}.get(v, f"f_{v}")
            fv = g[col].to_numpy()
            fr = g[f"f_{ref}"].to_numpy()
            ab.append({"policy": pol, "lead": int(k), "comparison": v, "reference": ref, "rows": len(g),
                       "mae_reference": float(np.mean(np.abs(fr - y))), "mae_variant": float(np.mean(np.abs(fv - y))),
                       "rmse_reference": float(np.sqrt(np.mean((fr - y) ** 2))), "rmse_variant": float(np.sqrt(np.mean((fv - y) ** 2))),
                       "within_reference": float(np.mean(np.abs(fr - y) <= tol)), "within_variant": float(np.mean(np.abs(fv - y) <= tol)),
                       "p_reference_better_sq_error": L.cluster_boot_p((fr - y) ** 2, (fv - y) ** 2, tq)})
    A = pd.DataFrame(ab)
    A["delta_mae_variant_minus_reference"] = A["mae_variant"] - A["mae_reference"]
    A["delta_within_variant_minus_reference"] = A["within_variant"] - A["within_reference"]
    A.to_csv(OUT / "e134_area_ablation.csv", index=False)
    for st in ("S-U", "S-E132"):
        g = Mt[(Mt.set == st) & (Mt.policy == "P-DASH")]
        print(st)
        print(g.pivot_table(index="model", columns="lead", values="within_tolerance").round(3).to_string())
        print(g.pivot_table(index="model", columns="lead", values="mae").round(2).to_string())
    print(A[A.policy == "P-DASH"].round(3).to_string())


if __name__ == "__main__":
    main()
