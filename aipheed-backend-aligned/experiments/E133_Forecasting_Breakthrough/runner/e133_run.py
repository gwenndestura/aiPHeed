"""
E133 walk-forward (protocol 9683aad): HFM, HFM-NS, HFM-NS-DES, HFM-TREND, HFM-X, HFM-X-B30, ENS133 against the
reproduced E132 models, under the unchanged target, primary tolerance, leads and N1-N7; group ablation; metrics on
S-U and S-E132; prospective seal inputs.

    python -I runner/e133_reproduce.py   (first; writes the reproduced E132 predictions)
    python -I runner/e133_run.py         (backend venv; several minutes)
"""
from __future__ import annotations

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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(EXP / "E132_Final_Methodology" / "runner"))
import e132_run as S  # noqa: E402
import e133_models as M  # noqa: E402

X, L = S.X, S.L
warnings.filterwarnings("ignore")
BRK = L.qi("2025-Q2")
T0 = L.qi("2021-Q2")
E119 = EXP / "E119_Preprocessing" / "E119_REGIONAL_MODELING_DATASET.csv"
B30 = ROOT / "data" / "raw" / "psa_cpi_bottom30_region_2021_2026.csv"
B30_REGIONS = {"metro_manila": ["NCR"],
               "balance_luzon": ["CAR", "Region 1", "Region 2", "Region 3", "Region 4A", "MIMAROPA REGION", "Region 5"],
               "visayas": ["Region 6", "Region 7", "Region 8", "NIR"],
               "mindanao": ["Region 9", "Region 10", "Region 11", "Region 12", "CARAGA", "BARMM"]}
E119_DRIVERS = {"C": "typhoons_PAR", "E": "E1_unemployment_change_pp", "N": "news_gdelt_shortage_share"}
NEW = ["HFM", "HFM-NS", "HFM-NS-DES", "HFM-TREND", "HFM-X", "HFM-X-B30", "ENS133"]
POSTHOC = "HFM-X-PH1"      # post-hoc, exploratory, never selectable (DEVIATIONS V3): drivers as shocks max(z, 0)
POSTHOC2 = "HFM-X-PH2"     # post-hoc, exploratory, never selectable (DEVIATIONS V3): ONI as the climate driver
REF = ["PERSIST", "CLIM", "LLM", "SEAS-LLM"]
E132_BASE = ["PSA-ONLY", "NLP-ONLY", "RIDGE-ALL"]
ALL_GROUPS = ("A", "C", "E", "N", "V")


# ------------------------------------------------------------------ drivers (quarter value + availability date)
def _qq_change(long: pd.DataFrame, regions: dict, match) -> pd.DataFrame:
    """Quarter-on-quarter % change of a monthly index (complete quarters only), mean over each area's regions, then
    mean over the 4 areas. Available 10 days after the quarter's last month."""
    long = long.copy()
    long["quarter"] = long["date"].dt.year.astype(str) + "-Q" + ((long["date"].dt.month - 1) // 3 + 1).astype(str)
    q = long.groupby(["region", "quarter"]).agg(v=("v", "mean"), n=("v", "count")).reset_index()
    q = q[q["n"] == 3]
    q["qi"] = q["quarter"].map(L.qi)
    q = q.sort_values(["region", "qi"])
    q["chg"] = q.groupby("region")["v"].pct_change() * 100
    q.loc[q.groupby("region")["qi"].diff() != 1, "chg"] = np.nan
    areas = []
    for a, keys in regions.items():
        g = q[q["region"].apply(lambda r: match(r, keys))].groupby("qi")["chg"].mean().rename(a)
        areas.append(g)
    d = pd.concat(areas, axis=1)
    out = pd.DataFrame({"qi": d.index, "value": d.mean(axis=1, skipna=True).values})
    out["available"] = out["qi"].map(lambda i: L.qend(L.qs(int(i))) + timedelta(days=10))
    return out.dropna()


def driver_rice() -> pd.DataFrame:
    c = pd.read_csv(X.CPI, encoding="utf-8-sig")
    c["region"] = c["Geolocation"].str.lstrip(". ")
    c = c[c["Commodity Description"].str.startswith("01.1.1.12")]
    long = c.melt(id_vars=["region"], value_vars=[x for x in c.columns if x[:4].isdigit()], var_name="ym", value_name="v")
    long["v"] = pd.to_numeric(long["v"], errors="coerce")
    long["date"] = pd.to_datetime(long["ym"], format="%Y %b")
    return _qq_change(long.dropna(), X.REGIONS, X._match)


def driver_b30() -> pd.DataFrame:
    c = pd.read_csv(B30, encoding="utf-8-sig")
    c["region"] = c["Geolocation"].str.strip()
    c = c[c["Commodity Description"].str.startswith("01 -")]
    cols = [x for x in c.columns if x[:4].isdigit() and not x.endswith("Ave")]
    long = c.melt(id_vars=["region"], value_vars=cols, var_name="ym", value_name="v")
    long["v"] = pd.to_numeric(long["v"], errors="coerce")
    long["date"] = pd.to_datetime(long["ym"], format="%Y %b")
    assert long["date"].min() >= pd.Timestamp("2021-01-01")
    return _qq_change(long.dropna(), B30_REGIONS, lambda r, keys: r in keys)


def driver_e119(col: str) -> pd.DataFrame:
    r = pd.read_csv(E119)
    r = r[(r["lead"] == 1) & r[f"{col}__period"].astype(str).str.match(r"^\d{4}-Q\d$")].copy()
    r["issue"] = pd.to_datetime(r["issue_date"]).dt.date
    r = r.sort_values("issue").drop_duplicates(f"{col}__period", keep="first")
    out = pd.DataFrame({"qi": r[f"{col}__period"].map(L.qi).values, "value": pd.to_numeric(r[col], errors="coerce").values,
                        "available": r["issue"].values})
    return out.dropna()


class Drivers:
    def __init__(self, market: str = "rice", climate: str = "typhoons_PAR"):
        self.tab = {"A": driver_rice() if market == "rice" else driver_b30()}
        for g, col in {**E119_DRIVERS, "C": climate}.items():
            self.tab[g] = driver_e119(col)
        self.pov = X.poverty_area()

    def at(self, issue: date):
        """Standardized (in-fold) driver values by quarter index, the latest available quarter per group, and the
        area vulnerability weights w_a = pov_a / mean(pov) - 1 (zeros before any poverty round is published)."""
        vals, last = {}, {}
        for g, t in self.tab.items():
            k = t[(t["available"] <= issue) & (t["qi"] >= L.qi("2021-Q1"))]
            if len(k) < 3:
                vals[g], last[g] = {}, None
                continue
            mu, sd = k["value"].mean(), k["value"].std() or 1.0
            vals[g] = dict(zip(k["qi"].astype(int), (k["value"] - mu) / sd))
            last[g] = int(k["qi"].max())
        yrs = [y for y, d in X.POV_PUBLISHED.items() if d < issue]
        if yrs:
            p = np.array([self.pov[a][max(yrs)] for a in X.AREAS])
            w = p / p.mean() - 1
        else:
            w = np.zeros(M.NA)
        return vals, last, w

    @staticmethod
    def z_for(vals, last, q: int) -> dict:
        """Driver dict for the transition INTO quarter q+1: the quarter-q value if published, else the latest held."""
        out = {}
        for g, v in vals.items():
            if q in v:
                out[g] = float(v[q])
            elif last.get(g) is not None and q > last[g]:
                out[g] = float(v[last[g]])
            else:
                out[g] = 0.0
        return out


# ------------------------------------------------------------------ fitting at an issue date
def matrices(qa: pd.DataFrame):
    upto = int(qa["qi"].max())
    idx = np.arange(T0, upto + 1)
    Y = np.full((len(idx), M.NA), np.nan)
    R = np.full((len(idx), M.NA), np.nan)
    for j, a in enumerate(X.AREAS):
        s = qa[qa.area == a].set_index("qi")
        Y[:, j] = s["y"].reindex(idx).to_numpy(float)
        R[:, j] = (s["se"] ** 2).reindex(idx).to_numpy(float)
    return idx, Y, R


_BASE: dict = {}


def base_fits(qa: pd.DataFrame) -> dict:
    """HFM, HFM-NS, HFM-NS-DES (and its design effect), HFM-TREND for one as-of data set."""
    key = (len(qa), round(float(qa["y"].sum()), 6))
    if key in _BASE:
        return _BASE[key]
    idx, Y, R = matrices(qa)
    out = {"idx": idx, "Y": Y, "R": R}
    out["HFM"] = M.fit_variances(Y, R, idx, BRK, M.Spec())
    ns = M.fit_variances(Y, R, idx, BRK, M.Spec(tau=True))
    out["HFM-NS"] = ns
    seas = {q: 0.0 for q in range(4)}
    if idx.max() >= BRK:
        innov = M.kfilter(Y, R, idx, ns, BRK)[3]
        seas = M.design_effect(innov, BRK)
    Yd = Y.copy()
    for j, t in enumerate(idx):
        if t >= BRK:
            Yd[j] -= seas[t % 4]
    out["seas"], out["Yd"] = seas, Yd
    out["HFM-NS-DES"] = M.fit_variances(Yd, R, idx, BRK, M.Spec(tau=True)) if idx.max() >= BRK else ns
    tr = [M.fit_variances(Yd, R, idx, BRK, M.Spec(tau=True, trend=True, phi=p)) for p in (0.5, 0.8)]
    out["HFM-TREND"] = max(tr, key=lambda f: f.ll)
    _BASE[key] = out
    return out


_XFIT: dict = {}


def x_fit(qa, issue, drv: Drivers, tag: str, groups: tuple):
    key = (tag, issue, groups, len(qa))
    if key in _XFIT:
        return _XFIT[key]
    b = base_fits(qa)
    idx, Yd, R = b["idx"], b["Yd"], b["R"]
    vals, last, w = drv.at(issue)
    Z = [Drivers.z_for(vals, last, int(t) - 1) for t in idx]
    fit = M.fit_beta(Yd, R, idx, BRK, b["HFM-NS-DES"], Z, w, groups, asym=tag.endswith("-asym"))
    _XFIT[key] = (fit, Z, vals, last, w)
    return _XFIT[key]


def predict(qa, issue, target: int, drv: dict, ablations: dict | None = None) -> dict:
    """Point forecasts and predictive SDs for every E133 model (and ablation variants) at one issue and target."""
    b = base_fits(qa)
    idx, Y, Yd, R = b["idx"], b["Y"], b["Yd"], b["R"]
    upto = int(idx.max())
    steps = target - upto
    brk_in = [upto + 1 + j == BRK for j in range(steps)]
    Rm = np.array([np.nanmedian(R[:, a]) for a in range(M.NA)])
    res = {}

    def one(name, fit, Yuse, Z=None, w=None, Zf=None, add_seas=False):
        x, P, _, _ = M.kfilter(Yuse, R, idx, fit, BRK, Z, w)
        Zf = Zf if Zf is not None else [{}] * steps
        mean, var = M.forecast(x, P, fit, steps, Zf, w, brk_in)
        if add_seas and target >= BRK:
            mean = mean + b["seas"][target % 4]
        res[name] = (mean, np.sqrt(var + fit.tau2 + Rm), fit)

    one("HFM", b["HFM"], Y)
    one("HFM-NS", b["HFM-NS"], Y)
    one("HFM-NS-DES", b["HFM-NS-DES"], Yd, add_seas=True)
    one("HFM-TREND", b["HFM-TREND"], Yd, add_seas=True)
    variants = {"HFM-X": ("rice", ALL_GROUPS), "HFM-X-B30": ("b30", ALL_GROUPS), POSTHOC: ("rice-asym", ALL_GROUPS),
                POSTHOC2: ("oni", ALL_GROUPS)}
    variants.update(ablations or {})
    for name, (tag, groups) in variants.items():
        fit, Z, vals, last, w = x_fit(qa, issue, drv[tag.split("-")[0]], tag, groups)
        Zf = [Drivers.z_for(vals, last, upto + j) for j in range(steps)]
        one(name, fit, Yd, Z, w, Zf, add_seas=True)
    return res


# ------------------------------------------------------------------ walk-forward
ABLATIONS = {}
for _g in ALL_GROUPS:
    ABLATIONS[f"X-minus-{_g}"] = ("rice", tuple(x for x in ALL_GROUPS if x != _g))
    ABLATIONS[f"X-only-{_g}"] = ("rice", (_g,) if _g != "V" else ("V",))
ABLATIONS["X-B30-minus-A"] = ("b30", tuple(x for x in ALL_GROUPS if x not in ("A", "V")))


def run(P0: pd.DataFrame, rr, drv: dict) -> pd.DataFrame:
    P = P0.copy()
    names = NEW[:-1] + [POSTHOC, POSTHOC2] + list(ABLATIONS)
    for m in names:
        P[f"f_{m}"], P[f"sd_{m}"] = np.nan, np.nan
    P["beta_A"] = P["beta_C"] = P["beta_E"] = P["beta_N"] = P["beta_V"] = np.nan
    P["tau2"] = P["q_c"] = P["q_d"] = P["rho"] = P["b"] = np.nan
    for (pol, D, k), g in P.groupby(["policy", "D", "lead"]):
        issue = g["issue"].iloc[0]
        issue = issue if isinstance(issue, date) else pd.Timestamp(issue).date()
        qa = X.asof(rr, issue)
        target = L.qi(g["target"].iloc[0])
        res = predict(qa, issue, target, drv, ABLATIONS)
        for i in g.index:
            a = X.AREAS.index(P.at[i, "area"])
            for m in names:
                P.at[i, f"f_{m}"] = float(res[m][0][a])
                P.at[i, f"sd_{m}"] = float(res[m][1][a])
            fx = res["HFM-X"][2]
            for gg in ALL_GROUPS:
                P.at[i, f"beta_{gg}"] = fx.beta.get(gg, np.nan)
            fn = res["HFM-NS-DES"][2]
            P.at[i, "tau2"], P.at[i, "q_c"], P.at[i, "q_d"], P.at[i, "rho"], P.at[i, "b"] = fn.tau2, fn.q_c, fn.q_d, fn.rho, fn.b
    P["f_ENS133"] = (P["f_SEAS-LLM"] + P["f_HFM-NS-DES"]) / 2
    P["sd_ENS133"] = (P["sd_SEAS-LLM"] + P["sd_HFM-NS-DES"]) / 2
    for m in names + ["ENS133"]:
        P[f"lo80_{m}"] = P[f"f_{m}"] - X.Z80 * P[f"sd_{m}"]
        P[f"hi80_{m}"] = P[f"f_{m}"] + X.Z80 * P[f"sd_{m}"]
    return P


# ------------------------------------------------------------------ evaluation
def _frame(d: pd.DataFrame) -> pd.DataFrame:
    return d.rename(columns={"y_true": "y", "area": "province", "f_PERSIST": "f_persistence", "f_CLIM": "f_climatology",
                             "lo80_PERSIST": "lo80_persistence", "hi80_PERSIST": "hi80_persistence"})


def metrics(P: pd.DataFrame, models: list[str], set_name: str, mask) -> tuple[list, dict]:
    rows, rules = [], {}
    for (pol, k), g in P[mask].groupby(["policy", "lead"]):
        d = _frame(g)
        for m in models:
            col = {"PERSIST": "f_persistence", "CLIM": "f_climatology"}.get(m, f"f_{m}")
            if col not in d or d[col].isna().any():
                continue
            met = L.numeric_metrics(d["y"], d[col], d["se"], prev=d["y_latest"], clim=d["f_climatology"])
            lo, hi = (f"lo80_{m}", f"hi80_{m}") if m not in ("PERSIST",) else ("lo80_persistence", "hi80_persistence")
            met["coverage80"] = float(np.mean((d["y"] >= d[lo]) & (d["y"] <= d[hi]))) if lo in d else np.nan
            terc = pd.qcut(d["y"], 3, labels=["low", "mid", "high"])
            for t in ("low", "mid", "high"):
                met[f"bias_{t}"] = float((d.loc[terc == t, col] - d.loc[terc == t, "y"]).mean())
            jump = (d["y"] - d["y_latest"]) > 2 * d["se"]
            met["sharp_n"] = int(jump.sum())
            met["sharp_within"] = int((np.abs(d.loc[jump, col] - d.loc[jump, "y"]) <= d.loc[jump, "tol"]).sum())
            for a, ga in d.groupby("province"):
                met[f"within_{a}"] = float(np.mean(np.abs(ga[col] - ga["y"]) <= ga["tol"]))
            met.update(set=set_name, policy=pol, lead=int(k), model=m, n_quarters=int(d["target_q"].nunique()))
            rows.append(met)
            if m in ("PERSIST", "CLIM"):
                continue
            base = ["LLM", "SEAS-LLM"] if set_name == "S-U" else E132_BASE
            base = [b for b in base if b != m and f"f_{b}" in d and not d[f"f_{b}"].isna().any()]
            rel = L.numeric_reliability(d.assign(**{f"f_{m}": d[col]}), m, ["persistence", "climatology"] + base)
            rules[f"{set_name}|{pol}|{k}|{m}"] = {"rules": rel["rules"], "passed": rel["passed"], "baselines": base,
                                                  "within": rel["metrics"]["within_tolerance"], "mae": rel["metrics"]["mae"],
                                                  "rmse": rel["metrics"]["rmse"], "within_thirds": rel["within_thirds"],
                                                  "loqo_min_within": rel["loqo_min_within"],
                                                  "p_vs_persistence": rel["p_sq_error_vs_persistence"],
                                                  "p_vs_climatology": rel["p_sq_error_vs_climatology"],
                                                  "per_area": rel["per_province"], "coverage80": rel["coverage_80"],
                                                  "n_rows": rel["n_rows"], "n_quarters": rel["n_target_quarters"]}
    return rows, rules


def ablation_table(P: pd.DataFrame) -> pd.DataFrame:
    rows = []
    su = P[(P.n_obs >= 8)]
    for (pol, k), g in su.groupby(["policy", "lead"]):
        y, tol, tq = g["y_true"].to_numpy(), g["tol"].to_numpy(), g["target_q"].to_numpy()
        full = g["f_HFM-X"].to_numpy()
        for v in ABLATIONS:
            f = g[f"f_{v}"].to_numpy()
            p = L.cluster_boot_p((full - y) ** 2, (f - y) ** 2, tq)
            rows.append({"policy": pol, "lead": int(k), "variant": v, "rows": len(g),
                         "mae_full": float(np.mean(np.abs(full - y))), "mae_variant": float(np.mean(np.abs(f - y))),
                         "within_full": float(np.mean(np.abs(full - y) <= tol)),
                         "within_variant": float(np.mean(np.abs(f - y) <= tol)),
                         "p_full_better_sq_error": p})
        base = g["f_HFM-NS-DES"].to_numpy()
        rows.append({"policy": pol, "lead": int(k), "variant": "no-drivers (HFM-NS-DES)", "rows": len(g),
                     "mae_full": float(np.mean(np.abs(full - y))), "mae_variant": float(np.mean(np.abs(base - y))),
                     "within_full": float(np.mean(np.abs(full - y) <= tol)),
                     "within_variant": float(np.mean(np.abs(base - y) <= tol)),
                     "p_full_better_sq_error": L.cluster_boot_p((full - y) ** 2, (base - y) ** 2, tq)})
    d = pd.DataFrame(rows)
    d["delta_mae_when_removed"] = d["mae_variant"] - d["mae_full"]
    d["delta_within_when_removed"] = d["within_variant"] - d["within_full"]
    return d


def main():
    OUT.mkdir(exist_ok=True)
    rr = X.rounds()
    qt = X.quarter_table(rr)
    P0 = pd.read_csv(OUT / "e133_e132_reproduced_predictions.csv")
    P0["issue"] = pd.to_datetime(P0["issue"]).dt.date
    P0 = S.oracle(qt, P0)
    drv = {"rice": Drivers("rice"), "b30": Drivers("b30"), "oni": Drivers("rice", "oni_quarter_mean")}
    for tag, d in drv.items():
        pd.concat([t.assign(group=g) for g, t in d.tab.items()]).to_csv(OUT / f"e133_drivers_{tag}.csv", index=False)
    P = run(P0, rr, drv)
    P.to_csv(OUT / "e133_predictions.csv", index=False)
    models = REF + E132_BASE + NEW
    shared = P.dropna(subset=[f"f_{m}" for m in S.ALL_MODELS])
    shared_keys = set(zip(shared.policy, shared.area, shared.D, shared.lead))
    in_e132 = np.array([k in shared_keys for k in zip(P.policy, P.area, P.D, P.lead)])
    r1, q1 = metrics(P, REF + NEW + [POSTHOC, POSTHOC2], "S-U", P.n_obs >= 8)
    r2, q2 = metrics(P, models + [POSTHOC, POSTHOC2], "S-E132", in_e132)
    Mt = pd.DataFrame(r1 + r2)
    Mt.to_csv(OUT / "e133_metrics.csv", index=False)
    L.dump({**q1, **q2}, OUT / "e133_rules.json")
    A = ablation_table(P)
    A.to_csv(OUT / "e133_ablation.csv", index=False)
    for st in ("S-U", "S-E132"):
        for pol in ("P-DASH", "P-REL"):
            g = Mt[(Mt.set == st) & (Mt.policy == pol)]
            print(st, pol)
            print(g.pivot_table(index="model", columns="lead", values="within_tolerance").round(3).to_string())
            print(g.pivot_table(index="model", columns="lead", values="mae").round(2).to_string())
    print(A[(A.policy == "P-DASH") & (A.lead == 2)].round(3).to_string())


if __name__ == "__main__":
    main()
