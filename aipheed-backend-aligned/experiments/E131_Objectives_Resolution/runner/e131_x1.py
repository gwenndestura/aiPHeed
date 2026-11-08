"""
E131 X1 (protocol sections 1-5): numerical forecasting of measured hunger (SWS, 4 areas, 2021+) at operational Leads
1-4 under the dashboard (P-DASH) and release-anchored (P-REL) issue policies, with measurement-aware local-level
models, learned models with the five trigger groups, baselines, N1-N7, ablation, seed sensitivity and the seal.

    python -I runner/e131_x1.py      (backend venv; a few minutes)
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import date, timedelta
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
OUT = ROOT / "out"
sys.path.insert(0, str(EXP / "E130_Provincial_Risk_Score_Forecasting" / "runner"))
import e130_lib as L  # noqa: E402

warnings.filterwarnings("ignore")
SWS = EXP / "E110_Hunger_Generalization" / "data" / "sws_area_rounds.csv"
REGIONAL = EXP / "E119_Preprocessing" / "E119_REGIONAL_MODELING_DATASET.csv"
CPI = ROOT / "data" / "raw" / "psa_cpi_regional_2021_2026.csv"
POV = ROOT / "data" / "raw" / "psa_poverty_population_2021_2023_2025.csv"
AREAS = ["metro_manila", "balance_luzon", "visayas", "mindanao"]
REGIONS = {"metro_manila": ["National Capital Region"],
           "balance_luzon": ["Cordillera", "Region I ", "Region II ", "Region III ", "Region IV-A", "MIMAROPA", "Region V "],
           "visayas": ["Region VI ", "Region VII ", "Region VIII ", "Negros Island"],
           "mindanao": ["Region IX ", "Region X ", "Region XI ", "Region XII ", "Region XIII", "Bangsamoro"]}
SEAL_DATE = date(2026, 10, 31)
Z80 = 1.2815515655446004
SEED = 131
GROUPS = {"A": ["food_yoy", "rice_yoy", "relfood", "relfood_chg4"], "C": ["oni", "elnino", "typhoons_par"],
          "E": ["unemp", "unemp_chg", "remit_decline"], "N": [], "V": ["poverty"]}
HIST = ["y_latest", "llm_level", "area_mean", "h", "last_change", "area_code"]
LEARNED = {"RIDGE-H": ("ridge", HIST), "LGBM-H": ("lgbm", HIST), "RIDGE-ALL": ("ridge", None), "LGBM-ALL": ("lgbm", None),
           "PSA-ONLY": ("ridge", "PSA"), "NLP-ONLY": ("ridge", "NLP")}
MODELS = ["PERSIST", "CLIM", "LLM", "DLLM", *LEARNED]


# ------------------------------------------------------------------ target and sampling error
def rounds(path: Path = SWS) -> pd.DataFrame:
    r = pd.read_csv(path)
    r = r[~r["commissioned"].astype(bool)].copy()
    r["published"] = pd.to_datetime(r["published"]).dt.date
    assert (r["quarter"].map(L.qi) >= L.qi("2021-Q1")).all()
    rows = []
    for x in r.itertuples():
        for a in AREAS:
            moe = x.area_moe_bl if a == "balance_luzon" else x.area_moe_other
            moe = 6.0 if moe != moe else float(moe)
            n = 0.9604 / (moe / 100) ** 2
            p = getattr(x, a) / 100
            rows.append({"quarter": x.quarter, "published": x.published, "area": a, "value": getattr(x, a),
                         "se": 100 * np.sqrt(p * (1 - p) / n), "se_pub": moe / 1.96})
    return pd.DataFrame(rows)


def quarter_table(rr: pd.DataFrame) -> pd.DataFrame:
    g = rr.groupby(["area", "quarter"])
    q = g.agg(y=("value", "mean"), published=("published", "max"), k=("value", "size")).reset_index()
    q["se"] = g["se"].apply(lambda s: np.sqrt((s ** 2).sum()) / len(s)).values
    q["se_pub"] = g["se_pub"].apply(lambda s: np.sqrt((s ** 2).sum()) / len(s)).values
    q["tol"] = L.Z90 * q["se"]
    q["qi"] = q["quarter"].map(L.qi)
    return q


def asof(rr: pd.DataFrame, issue: date) -> pd.DataFrame:
    """Quarter values as known on the issue date (partial quarters use the rounds published by then)."""
    k = rr[rr["published"] < issue]
    if k.empty:
        return k.assign(y=[], se=[], qi=[])
    return quarter_table(k)


# ------------------------------------------------------------------ measurement-aware local level (Kalman)
def _kf(y, R, s2, phi=1.0, m=0.0):
    """Filter a (damped) local level with known observation variances R (NaN = missing). Returns final level, its
    variance and the log-likelihood of the observations after the first."""
    mu, P, ll, started = None, None, 0.0, False
    for yt, rt in zip(y, R):
        if not started:
            if yt == yt:
                mu, P, started = yt, rt, True
            continue
        mu = m + phi * (mu - m)
        P = phi ** 2 * P + s2
        if yt == yt:
            S = P + rt
            ll += -0.5 * (np.log(2 * np.pi * S) + (yt - mu) ** 2 / S)
            K = P / S
            mu, P = mu + K * (yt - mu), (1 - K) * P
    return mu, P, ll


S2_GRID = np.exp(np.linspace(np.log(0.05), np.log(80), 60))
PHI_GRID = np.round(np.linspace(0, 1, 21), 2)


def series(qt: pd.DataFrame, area: str, upto: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s = qt[(qt.area == area) & (qt.qi <= upto)].set_index("qi")
    idx = np.arange(L.qi("2021-Q2"), upto + 1)
    y = s["y"].reindex(idx).to_numpy(float)
    R = (s["se"] ** 2).reindex(idx).to_numpy(float)
    return idx, y, R


def fit_llm(qt: pd.DataFrame, upto: int, damped: bool):
    """Pooled maximum likelihood over the 4 areas: s2 (and phi, mean = expanding area mean, if damped)."""
    data = {a: series(qt, a, upto) for a in AREAS}
    means = {a: float(np.nanmean(data[a][1])) for a in AREAS}
    best = (-np.inf, None, None)
    for phi in (PHI_GRID if damped else [1.0]):
        for s2 in S2_GRID:
            ll = sum(_kf(data[a][1], data[a][2], s2, phi, means[a] if damped else 0.0)[2] for a in AREAS)
            if ll > best[0]:
                best = (ll, s2, phi)
    return best[1], best[2], means, data


_FIT_CACHE: dict = {}


def llm_forecast(qt, upto, target, damped):
    key = (len(qt), float(qt["y"].sum()), upto, damped)
    if key not in _FIT_CACHE:
        _FIT_CACHE[key] = fit_llm(qt, upto, damped)
    s2, phi, means, data = _FIT_CACHE[key]
    out = {}
    for a in AREAS:
        idx, y, R = data[a]
        obs = np.where(~np.isnan(y))[0]
        if not len(obs):
            continue
        last = idx[obs[-1]]
        mu, P, _ = _kf(y[: obs[-1] + 1], R[: obs[-1] + 1], s2, phi, means[a] if damped else 0.0)
        h = target - last
        m = means[a] if damped else 0.0
        f = m + phi ** h * (mu - m) if damped else mu
        var_state = (phi ** (2 * h)) * P + s2 * sum(phi ** (2 * j) for j in range(h)) if damped else P + h * s2
        r_t = float(np.nanmedian(R))
        out[a] = {"f": f, "sd": float(np.sqrt(var_state + r_t)), "level": mu, "h": h, "s2": s2, "phi": phi}
    return out


# ------------------------------------------------------------------ covariates (point-in-time)
def cpi_quarterly() -> pd.DataFrame:
    """Area quarterly food YoY, rice YoY and relative food price (food / all items), each with the date it became
    available (day 10 after the quarter's last month). YoY only from 2022-01 (no pre-2021 base)."""
    c = pd.read_csv(CPI, encoding="utf-8-sig")
    c["region"] = c["Geolocation"].str.lstrip(". ")
    c["comm"] = c["Commodity Description"].str.split(" - ").str[0].map({"0": "all", "01": "food", "01.1.1.12": "rice"})
    long = c.melt(id_vars=["region", "comm"], value_vars=[x for x in c.columns if x[:4].isdigit()], var_name="ym", value_name="v")
    long["v"] = pd.to_numeric(long["v"], errors="coerce")
    long["date"] = pd.to_datetime(long["ym"], format="%Y %b")
    w = long.pivot_table(index=["region", "date"], columns="comm", values="v").reset_index().sort_values(["region", "date"])
    for k in ("food", "rice"):
        w[f"{k}_yoy"] = w.groupby("region")[k].pct_change(12) * 100
    w.loc[w["date"] < "2022-01-01", ["food_yoy", "rice_yoy"]] = np.nan
    w["relfood"] = w["food"] / w["all"] * 100
    w["quarter"] = w["date"].dt.year.astype(str) + "-Q" + ((w["date"].dt.month - 1) // 3 + 1).astype(str)
    q = w.groupby(["region", "quarter"]).agg(food_yoy=("food_yoy", "mean"), rice_yoy=("rice_yoy", "mean"),
                                             relfood=("relfood", "mean"), n=("food", "count")).reset_index()
    q = q[q["n"] == 3]
    rows = []
    for a, keys in REGIONS.items():
        sel = q[q["region"].apply(lambda r: _match(r, keys))]
        g = sel.groupby("quarter")[["food_yoy", "rice_yoy", "relfood"]].mean().reset_index()
        g["area"] = a
        g["regions"] = sel.groupby("quarter")["region"].nunique().values
        rows.append(g)
    out = pd.concat(rows)
    out["qi"] = out["quarter"].map(L.qi)
    out = out.sort_values(["area", "qi"])
    out["relfood_chg4"] = out.groupby("area")["relfood"].diff(4)
    out["available"] = out["quarter"].map(lambda q: L.qend(q) + timedelta(days=10))
    return out


def regional_covariates() -> pd.DataFrame:
    r = pd.read_csv(REGIONAL)
    r = r[r["lead"] == 1].copy()
    r["issue"] = pd.to_datetime(r["issue_date"]).dt.date
    news = [c for c in r.columns if c.startswith("news_gdelt_") and not c.endswith(("__status", "__period"))]
    GROUPS["N"] = news
    keep = {"oni_quarter_mean": "oni", "C1_el_nino_in_force": "elnino", "typhoons_PAR": "typhoons_par",
            "unemployment_rate_pct": "unemp", "E1_unemployment_change_pp": "unemp_chg", "E2_remittance_decline_pct": "remit_decline"}
    out = r[["issue", *keep, *news]].rename(columns=keep)
    return out.sort_values("issue")


def poverty_area() -> dict[str, dict[int, float]]:
    p = pd.read_csv(POV)
    res = {}
    for a, keys in REGIONS.items():
        sel = p[p["geography"].apply(lambda g: _match(g, keys))]
        res[a] = {y: float(sel[f"pov_{y}"].mean()) for y in (2021, 2023, 2025)}
    return res


def _match(name: str, keys: list[str]) -> bool:
    return any(name == k.strip() or name.startswith(k) for k in keys)


POV_PUBLISHED = {2021: date(2024, 8, 15), 2023: date(2024, 8, 15), 2025: date(2026, 8, 24)}


def features(issue: date, rr, cpi, reg, pov, target: int) -> pd.DataFrame:
    qa = asof(rr, issue)
    rows = []
    if qa.empty:
        return pd.DataFrame()
    upto = int(qa["qi"].max())
    llm = llm_forecast(qa, upto, target, damped=False)
    c_av = cpi[cpi["available"] <= issue]
    regrow = reg[reg["issue"] <= issue].tail(1)
    for code, a in enumerate(AREAS):
        s = qa[qa.area == a].sort_values("qi")
        if s.empty or a not in llm:
            continue
        rec = {"area": a, "area_code": code, "y_latest": float(s["y"].iloc[-1]), "q_latest": int(s["qi"].iloc[-1]),
               "llm_level": llm[a]["level"], "area_mean": float(s["y"].mean()), "h": target - int(s["qi"].iloc[-1]),
               "last_change": float(s["y"].iloc[-1] - s["y"].iloc[-2]) if len(s) > 1 else 0.0, "n_obs": len(s)}
        ca = c_av[c_av.area == a].sort_values("qi").tail(1)
        for k in GROUPS["A"]:
            rec[k] = float(ca[k].iloc[0]) if len(ca) and ca[k].iloc[0] == ca[k].iloc[0] else np.nan
        for k in GROUPS["C"] + GROUPS["E"] + GROUPS["N"]:
            rec[k] = float(regrow[k].iloc[0]) if len(regrow) and regrow[k].iloc[0] == regrow[k].iloc[0] else np.nan
        yrs = [y for y, d in POV_PUBLISHED.items() if d < issue]
        rec["poverty"] = pov[a][max(yrs)] if yrs else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ issue schedules
def schedule(rr: pd.DataFrame, policy: str) -> list[tuple[str, date]]:
    out = []
    for d in range(L.qi("2021-Q3"), L.qi("2026-Q4") + 1):
        D = L.qs(d)
        if policy == "P-DASH":
            out.append((D, L.qstart(D)))
        else:
            prev = rr[rr["quarter"] == L.qs(d - 1)]
            if len(prev):
                pub = max(prev["published"])
                if L.qstart(D) <= pub <= L.qend(D):
                    out.append((D, pub + timedelta(days=1)))
    return out


# ------------------------------------------------------------------ learned models
def feat_cols(spec) -> list[str]:
    if spec is None:
        return HIST + sum(GROUPS.values(), [])
    if spec == "PSA":
        return HIST + GROUPS["A"] + GROUPS["C"] + GROUPS["E"] + GROUPS["V"]
    if spec == "NLP":
        return HIST + GROUPS["N"]
    return list(spec)


def fit_predict(kind, cols, tr, te, seed=SEED):
    X, y = tr[cols].astype(float), tr["delta"].to_numpy(float)
    if kind == "ridge":
        med = X.median()
        mu, sd = X.fillna(med).mean(), X.fillna(med).std().replace(0, 1).fillna(1)
        Z = ((X.fillna(med) - mu) / sd).fillna(0)
        m = Ridge(alpha=10.0).fit(Z, y)
        Zt = ((te[cols].astype(float).fillna(med) - mu) / sd).fillna(0)
        return m.predict(Zt), m.predict(Z), None
    m = lgb.LGBMRegressor(num_leaves=4, max_depth=2, learning_rate=0.05, n_estimators=100, min_child_samples=8,
                          reg_lambda=5, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=seed,
                          verbose=-1).fit(X, y)
    trees = sum(1 for t in m.booster_.dump_model()["tree_info"] if t["num_leaves"] > 1)
    return m.predict(te[cols].astype(float)), m.predict(X), trees


# ------------------------------------------------------------------ walk-forward
def run(policy: str, rr, qt, cpi, reg, pov, ablate: str | None = None, seeds=(SEED,)) -> pd.DataFrame:
    final = qt.set_index(["area", "quarter"])
    issues = schedule(rr, policy)
    feats, preds = {}, []
    for D, issue in issues:
        for k in L.LEADS:
            T = L.qs(L.qi(D) - 1 + k)
            F = features(issue, rr, cpi, reg, pov, L.qi(T))
            if F.empty:
                continue
            F["D"], F["issue"], F["lead"], F["target"] = D, issue, k, T
            F["published_target"] = [final.loc[(a, T), "published"] if (a, T) in final.index else None for a in F["area"]]
            F["y_true"] = [final.loc[(a, T), "y"] if (a, T) in final.index else np.nan for a in F["area"]]
            F["delta"] = F["y_true"] - F["y_latest"]
            feats[(D, k)] = F
    for (D, k), F in feats.items():
        issue = F["issue"].iloc[0]
        target = L.qi(F["target"].iloc[0])
        ev = F[F["y_true"].notna()].copy()
        if ev.empty:
            continue
        qa = asof(rr, issue)
        upto = int(qa["qi"].max())
        ll = llm_forecast(qa, upto, target, damped=False)
        dl = llm_forecast(qa, upto, target, damped=True)
        tr = pd.concat([G for (D2, k2), G in feats.items() if k2 == k and G["issue"].iloc[0] < issue]
                       + [pd.DataFrame()], ignore_index=True)
        if len(tr):
            tr = tr[np.array([isinstance(d, date) and d < issue for d in tr["published_target"]], dtype=bool)]
        n_train_q = tr["target"].nunique() if len(tr) else 0
        base = ev[["area", "D", "issue", "lead", "target", "y_true", "y_latest", "h", "n_obs", "published_target"]].copy()
        base["policy"] = policy
        base["f_PERSIST"] = ev["y_latest"].values
        base["f_CLIM"] = ev["area_mean"].values
        base["f_LLM"] = [ll[a]["f"] for a in ev["area"]]
        base["sd_LLM"] = [ll[a]["sd"] for a in ev["area"]]
        base["f_DLLM"] = [dl[a]["f"] for a in ev["area"]]
        base["sd_DLLM"] = [dl[a]["sd"] for a in ev["area"]]
        base["phi_DLLM"] = dl[ev["area"].iloc[0]]["phi"]
        base["n_train_rows"], base["n_train_quarters"] = len(tr), n_train_q
        if len(tr) >= 20 and n_train_q >= 8:
            for name, (kind, spec) in LEARNED.items():
                cols = [c for c in feat_cols(spec) if not (ablate and c in GROUPS.get(ablate, []))]
                out = []
                for s in seeds:
                    p, ptr, trees = fit_predict(kind, cols, tr, ev, s)
                    out.append(p)
                p = np.mean(out, axis=0)
                resid = np.abs(tr["delta"].to_numpy() - ptr)
                base[f"f_{name}"] = ev["y_latest"].values + p
                base[f"q80_{name}"] = float(np.quantile(resid, 0.8))
                base[f"train_mae_{name}"] = float(np.mean(resid))
                if trees is not None:
                    base[f"trees_{name}"] = trees
        preds.append(base)
    return pd.concat(preds, ignore_index=True)


def add_truth(P: pd.DataFrame, qt: pd.DataFrame) -> pd.DataFrame:
    t = qt.set_index(["area", "quarter"])
    P["se"] = [t.loc[(a, q), "se"] for a, q in zip(P["area"], P["target"])]
    P["se_pub"] = [t.loc[(a, q), "se_pub"] for a, q in zip(P["area"], P["target"])]
    P["tol"] = L.Z90 * P["se"]
    P["target_q"] = P["target"].map(L.qi)
    return P


def intervals(P: pd.DataFrame) -> pd.DataFrame:
    """80 % intervals: Kalman predictive SD for LLM/DLLM; earlier out-of-sample absolute errors (training residual
    quantile until enough) widened by the target SE for the others."""
    se = P["se"].to_numpy()
    for m in MODELS:
        if f"f_{m}" not in P:
            continue
        if m in ("LLM", "DLLM"):
            half = Z80 * P[f"sd_{m}"]
        else:
            half = np.full(len(P), np.nan)
            for (pol, k), g in P.groupby(["policy", "lead"]):
                past = []
                for i in g.sort_values("issue").index:
                    issue = P.at[i, "issue"]
                    prev = P[(P.policy == pol) & (P.lead == k) & (P.issue < issue) & P[f"f_{m}"].notna()]
                    prev = prev[np.array([isinstance(d, date) and d < issue for d in prev["published_target"]], dtype=bool)]
                    err = np.abs(prev["y_true"] - prev[f"f_{m}"]).to_numpy()
                    if len(err) >= 8:
                        half[P.index.get_loc(i)] = np.quantile(err, 0.8)
                    elif f"q80_{m}" in P and P.at[i, f"q80_{m}"] == P.at[i, f"q80_{m}"]:
                        half[P.index.get_loc(i)] = np.sqrt(P.at[i, f"q80_{m}"] ** 2 + se[P.index.get_loc(i)] ** 2)
        P[f"lo80_{m}"] = P[f"f_{m}"] - half
        P[f"hi80_{m}"] = P[f"f_{m}"] + half
    return P


# ------------------------------------------------------------------ evaluation
N3_BASE = ["PERSIST", "CLIM", "PSA-ONLY", "NLP-ONLY", "RIDGE-ALL"]


def evaluate(P: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    common = P.dropna(subset=[f"f_{m}" for m in MODELS])
    rows, rules = [], {}
    for (pol, k), g in common.groupby(["policy", "lead"]):
        d = g.rename(columns={"y_true": "y", "area": "province", "f_PERSIST": "f_persistence", "f_CLIM": "f_climatology"})
        for m in MODELS:
            col = {"PERSIST": "f_persistence", "CLIM": "f_climatology"}.get(m, f"f_{m}")
            met = L.numeric_metrics(d["y"], d[col], d["se"], prev=d["y_latest"], clim=d["f_climatology"])
            cover = float(np.mean((d["y"] >= d[f"lo80_{m}"]) & (d["y"] <= d[f"hi80_{m}"]))) if f"lo80_{m}" in d else np.nan
            met.update(policy=pol, lead=int(k), model=m, n_target_quarters=int(d["target_q"].nunique()), coverage80=cover,
                       within_half_tol=float(np.mean(np.abs(d[col] - d["y"]) <= 0.5 * d["tol"])),
                       within_double_tol=float(np.mean(np.abs(d[col] - d["y"]) <= 2 * d["tol"])),
                       within_published_moe_tol=float(np.mean(np.abs(d[col] - d["y"]) <= L.Z90 * d["se_pub"])))
            rows.append(met)
            if m in ("PERSIST", "CLIM"):
                continue
            dd = d.copy()
            dd[f"f_{m}"] = dd[col]
            base = [b for b in N3_BASE if b != m]
            for b in base:
                dd[f"f_{b}"] = dd[{"PERSIST": "f_persistence", "CLIM": "f_climatology"}.get(b, f"f_{b}")]
            rel = L.numeric_reliability(dd, m, ["persistence", "climatology"] + [b for b in base if b not in ("PERSIST", "CLIM")])
            rules[f"{pol}|{k}|{m}"] = {"rules": rel["rules"], "passed": rel["passed"], "within": rel["metrics"]["within_tolerance"],
                                       "mae": rel["metrics"]["mae"], "within_thirds": rel["within_thirds"],
                                       "loqo_min_within": rel["loqo_min_within"], "p_vs_persistence": rel["p_sq_error_vs_persistence"],
                                       "p_vs_climatology": rel["p_sq_error_vs_climatology"], "per_area": rel["per_province"],
                                       "coverage80": rel["coverage_80"], "n_rows": rel["n_rows"], "n_quarters": rel["n_target_quarters"]}
    return pd.DataFrame(rows), rules


def ablation(rr, qt, cpi, reg, pov, full: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for grp in GROUPS:
        P = add_truth(run("P-DASH", rr, qt, cpi, reg, pov, ablate=grp), qt)
        for k in (1, 2):
            for m in ("LGBM-ALL", "RIDGE-ALL"):
                a = full[(full.policy == "P-DASH") & (full.lead == k)].dropna(subset=[f"f_{x}" for x in MODELS])
                b = P[(P.lead == k)].set_index(["area", "D"]).reindex(a.set_index(["area", "D"]).index)
                fa, fb, y, tol = a[f"f_{m}"].to_numpy(), b[f"f_{m}"].to_numpy(), a["y_true"].to_numpy(), a["tol"].to_numpy()
                ok = ~np.isnan(fb)
                rows.append({"model": m, "lead": k, "group_removed": grp, "rows": int(ok.sum()),
                             "mae_full": float(np.mean(np.abs(fa[ok] - y[ok]))), "mae_without": float(np.mean(np.abs(fb[ok] - y[ok]))),
                             "within_full": float(np.mean(np.abs(fa[ok] - y[ok]) <= tol[ok])),
                             "within_without": float(np.mean(np.abs(fb[ok] - y[ok]) <= tol[ok]))})
    df = pd.DataFrame(rows)
    df["delta_mae_when_removed"] = df["mae_without"] - df["mae_full"]
    df["delta_within_when_removed"] = df["within_without"] - df["within_full"]
    return df


def seeds(rr, qt, cpi, reg, pov) -> pd.DataFrame:
    out = []
    for s in range(131, 136):
        P = add_truth(run("P-DASH", rr, qt, cpi, reg, pov, seeds=(s,)), qt)
        c = P.dropna(subset=["f_LGBM-ALL"])
        for k in (1, 2):
            g = c[c.lead == k]
            out.append({"seed": s, "lead": k, "rows": len(g), "mae": float(np.mean(np.abs(g["f_LGBM-ALL"] - g["y_true"]))),
                        "within": float(np.mean(np.abs(g["f_LGBM-ALL"] - g["y_true"]) <= g["tol"]))})
    return pd.DataFrame(out)


def seal(rr, qt, cpi, reg, pov) -> pd.DataFrame:
    """Prospective forecasts issued 2026-10-31 (all information published by then) for 2026-Q4 .. 2027-Q3."""
    D, rows = "2026-Q4", []
    t = qt.set_index(["area", "quarter"])
    qa = asof(rr, SEAL_DATE)
    upto = int(qa["qi"].max())
    for k in L.LEADS:
        T = L.qs(L.qi(D) - 1 + k)
        F = features(SEAL_DATE, rr, cpi, reg, pov, L.qi(T))
        ll, dl = llm_forecast(qa, upto, L.qi(T), False), llm_forecast(qa, upto, L.qi(T), True)
        train = []
        for D2, issue in schedule(rr, "P-DASH"):
            T2 = L.qs(L.qi(D2) - 1 + k)
            G = features(issue, rr, cpi, reg, pov, L.qi(T2))
            if G.empty:
                continue
            G["y_true"] = [t.loc[(a, T2), "y"] if (a, T2) in t.index and t.loc[(a, T2), "published"] < SEAL_DATE else np.nan
                           for a in G["area"]]
            G["delta"] = G["y_true"] - G["y_latest"]
            train.append(G[G["y_true"].notna()])
        tr = pd.concat(train, ignore_index=True)
        learned = {name: fit_predict(kind, feat_cols(spec), tr, F)[0] for name, (kind, spec) in LEARNED.items()}
        for i, a in enumerate(F["area"]):
            rec = {"area": a, "issue": SEAL_DATE.isoformat(), "dashboard_quarter": D, "lead": k, "target": T,
                   "y_latest": float(F["y_latest"].iloc[i]), "latest_quarter": L.qs(int(F["q_latest"].iloc[i])),
                   "h": int(F["h"].iloc[i]), "n_train_rows": len(tr), "PERSIST": float(F["y_latest"].iloc[i]),
                   "CLIM": float(F["area_mean"].iloc[i])}
            for nm, fc in (("LLM", ll), ("DLLM", dl)):
                rec[nm], rec[f"{nm}_lo80"], rec[f"{nm}_hi80"] = fc[a]["f"], fc[a]["f"] - Z80 * fc[a]["sd"], fc[a]["f"] + Z80 * fc[a]["sd"]
            for name, p in learned.items():
                rec[name] = float(F["y_latest"].iloc[i] + p[i])
            rows.append(rec)
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(exist_ok=True)
    rr = rounds()
    qt = quarter_table(rr)
    cpi, reg, pov = cpi_quarterly(), regional_covariates(), poverty_area()
    qt.to_csv(OUT / "x1_target_quarters.csv", index=False)
    cpi.to_csv(OUT / "x1_area_cpi_quarterly.csv", index=False)
    P = pd.concat([run(p, rr, qt, cpi, reg, pov) for p in ("P-DASH", "P-REL")], ignore_index=True)
    P = intervals(add_truth(P, qt))
    P.to_csv(OUT / "x1_predictions.csv", index=False)
    M, R = evaluate(P)
    M.to_csv(OUT / "x1_metrics.csv", index=False)
    L.dump(R, OUT / "x1_rules.json")
    ab = ablation(rr, qt, cpi, reg, pov, P)
    ab.to_csv(OUT / "x1_ablation.csv", index=False)
    sd = seeds(rr, qt, cpi, reg, pov)
    sd.to_csv(OUT / "x1_seed_sensitivity.csv", index=False)
    show = M[M.policy == "P-DASH"].pivot_table(index="model", columns="lead", values="within_tolerance").round(3)
    print(show.to_string())
    print(M[M.policy == "P-REL"].pivot_table(index="model", columns="lead", values="within_tolerance").round(3).to_string())
    print(M[M.policy == "P-DASH"].pivot_table(index="model", columns="lead", values="mae").round(2).to_string())


if __name__ == "__main__":
    main()
