"""
E132 (protocol 4b880f0): SEAS-LLM, ENS, HYB-RIDGE and HYB-LGBM against the E131 models (with the new area income
features), under the unchanged E131 target, primary tolerance and N1-N7; oracle and SWS-vs-OCTA diagnostics; seal.

    python -I runner/e132_run.py      (backend venv; a few minutes)
"""
from __future__ import annotations

import sys
import warnings
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
OUT = ROOT / "out"
sys.path.insert(0, str(EXP / "E131_Objectives_Resolution" / "runner"))
import e131_x1 as X  # noqa: E402

L = X.L
warnings.filterwarnings("ignore")
BREAK = L.qi("2025-Q2")
B_GRID = [0.0, 4.0, 9.0, 16.0, 25.0, 49.0]
SEAL_DATE = date(2026, 11, 1)
NEW = ["SEAS-LLM", "ENS", "HYB-RIDGE", "HYB-LGBM"]
E131_MODELS = list(X.MODELS)
ALL_MODELS = E131_MODELS + NEW
INC = ["real_pay_growth", "unemp_area", "unemp_area_chg"]
HYB_RIDGE_FEATS = ["riceaff_chg4", "real_pay_growth", "unemp_area_chg"]
PAY = ROOT / "data" / "raw" / "psa_sdg_daily_basic_pay_region.csv"
UNEMP = ROOT / "data" / "raw" / "psa_sdg_unemployment_region.csv"
OCTA = EXP / "FORECAST_RESEARCH_II" / "data" / "octa_bl.csv"


# ------------------------------------------------------------------ new area features (H3, H5)
def _annual_cpi_all() -> pd.DataFrame:
    c = pd.read_csv(X.CPI, encoding="utf-8-sig")
    c["region"] = c["Geolocation"].str.lstrip(". ")
    c = c[c["Commodity Description"].str.startswith("0 - ALL ITEMS")]
    long = c.melt(id_vars=["region"], value_vars=[x for x in c.columns if x[:4].isdigit()], var_name="ym", value_name="v")
    long["v"] = pd.to_numeric(long["v"], errors="coerce")
    long["year"] = long["ym"].str[:4].astype(int)
    return long.groupby(["region", "year"])["v"].mean().unstack()


def income_area() -> pd.DataFrame:
    """Area real daily basic pay growth and unemployment by year, with availability 30 June of the next year."""
    def regional(path, first_cols):
        d = pd.read_csv(path, encoding="utf-8-sig")
        d["region"] = d["Geolocation"].str.lstrip(". ").str.replace(r"\s+\d/$", "", regex=True)
        d = d[d["region"] != "PHILIPPINES"]
        yrs = [c for c in d.columns if c[:4].isdigit()]
        out = d.set_index("region")[yrs].apply(pd.to_numeric, errors="coerce")
        out.columns = [int(c[:4]) for c in yrs]
        return out
    pay, un = regional(PAY, 1), regional(UNEMP, 3)
    cpi = _annual_cpi_all()
    rows = []
    for a, keys in X.REGIONS.items():
        regs = [r for r in pay.index if X._match(r.split(" (")[0] if r.startswith("Region") else r, keys) or X._match(r, keys)]
        for y in range(2021, 2027):
            rp = []
            for r in regs:
                cr = [c for c in cpi.index if c.split(" (")[0] == r.split(" (")[0] or c == r]
                if y in pay.columns and y in cpi.columns and cr and pd.notna(pay.loc[r, y]) and pd.notna(cpi.loc[cr[0], y]):
                    rp.append(pay.loc[r, y] / cpi.loc[cr[0], y])
            ur = [un.loc[r, y] for r in un.index if (X._match(r, keys) or X._match(r.split(" (")[0], keys)) and y in un.columns and pd.notna(un.loc[r, y])]
            rows.append({"area": a, "year": y, "real_pay": float(np.mean(rp)) if rp else np.nan,
                         "unemp_area": float(np.mean(ur)) if ur else np.nan, "n_regions_pay": len(rp)})
    d = pd.DataFrame(rows).sort_values(["area", "year"])
    d["real_pay_growth"] = d.groupby("area")["real_pay"].pct_change() * 100
    d["unemp_area_chg"] = d.groupby("area")["unemp_area"].diff()
    d["available"] = d["year"].map(lambda y: date(y + 1, 6, 30))
    return d


def rice_affordability() -> pd.DataFrame:
    c = pd.read_csv(X.CPI, encoding="utf-8-sig")
    c["region"] = c["Geolocation"].str.lstrip(". ")
    c["comm"] = c["Commodity Description"].str.split(" - ").str[0].map({"0": "all", "01.1.1.12": "rice"})
    c = c[c["comm"].notna()]
    long = c.melt(id_vars=["region", "comm"], value_vars=[x for x in c.columns if x[:4].isdigit()], var_name="ym", value_name="v")
    long["v"] = pd.to_numeric(long["v"], errors="coerce")
    long["date"] = pd.to_datetime(long["ym"], format="%Y %b")
    w = long.pivot_table(index=["region", "date"], columns="comm", values="v").reset_index()
    w["ratio"] = w["rice"] / w["all"] * 100
    w["quarter"] = w["date"].dt.year.astype(str) + "-Q" + ((w["date"].dt.month - 1) // 3 + 1).astype(str)
    q = w.groupby(["region", "quarter"]).agg(ratio=("ratio", "mean"), n=("ratio", "count")).reset_index()
    q = q[q["n"] == 3]
    rows = []
    for a, keys in X.REGIONS.items():
        g = q[q["region"].apply(lambda r: X._match(r, keys))].groupby("quarter")["ratio"].mean().reset_index()
        g["area"] = a
        rows.append(g)
    out = pd.concat(rows)
    out["qi"] = out["quarter"].map(L.qi)
    out = out.sort_values(["area", "qi"])
    out["riceaff_chg4"] = out.groupby("area")["ratio"].diff(4)
    out["available"] = out["quarter"].map(lambda s: L.qend(s) + timedelta(days=10))
    return out


INCOME = None
RICE = None
GROUPS132: dict = {}


def feat_cols132(spec) -> list[str]:
    """E131 feature sets with the E132 additions (rice affordability in A, area income in E); E131's own feature
    builder keeps its original lists."""
    if spec is None:
        return list(dict.fromkeys(X.HIST + sum(GROUPS132.values(), [])))
    if spec == "PSA":
        return X.HIST + GROUPS132["A"] + GROUPS132["C"] + GROUPS132["E"] + GROUPS132["V"]
    if spec == "NLP":
        return X.HIST + GROUPS132["N"]
    return list(spec)
_orig_features = X.features


def features132(issue, rr, cpi, reg, pov, target):
    F = _orig_features(issue, rr, cpi, reg, pov, target)
    if F.empty:
        return F
    for col in ("riceaff_chg4", *INC):
        F[col] = np.nan
    for i, a in enumerate(F["area"]):
        ra = RICE[(RICE.area == a) & (RICE.available <= issue)].tail(1)
        if len(ra):
            F.loc[F.index[i], "riceaff_chg4"] = ra["riceaff_chg4"].iloc[0]
        ia = INCOME[(INCOME.area == a) & (INCOME.available < issue)]
        for col in INC:
            v = ia[col].dropna()
            if len(v):
                F.loc[F.index[i], col] = float(v.iloc[-1])
    return F


# ------------------------------------------------------------------ SEAS-LLM (H1)
def _kf_break(y, R, s2, bvar, idx, out_innov=False):
    mu, P, ll, started, innov = None, None, 0.0, False, {}
    for t, yt, rt in zip(idx, y, R):
        if not started:
            if yt == yt:
                mu, P, started = yt, rt, True
            continue
        P = P + s2 + (bvar if t == BREAK else 0.0)
        if yt == yt:
            S = P + rt
            ll += -0.5 * (np.log(2 * np.pi * S) + (yt - mu) ** 2 / S)
            innov[t] = yt - mu
            K = P / S
            mu, P = mu + K * (yt - mu), (1 - K) * P
    return (mu, P, ll, innov) if out_innov else (mu, P, ll)


_SEAS_CACHE: dict = {}


def seas_fit(qa: pd.DataFrame, upto: int):
    key = (len(qa), float(qa["y"].sum()), upto)
    if key in _SEAS_CACHE:
        return _SEAS_CACHE[key]
    data = {a: X.series(qa, a, upto) for a in X.AREAS}

    def best_fit(series_map):
        best = (-np.inf, None, None)
        for b in B_GRID:
            for s2 in X.S2_GRID:
                ll = sum(_kf_break(series_map[a][1], series_map[a][2], s2, b, series_map[a][0])[2] for a in X.AREAS)
                if ll > best[0]:
                    best = (ll, s2, b)
        return best[1], best[2]
    s2, b = best_fit(data)
    resid = {q: [] for q in range(4)}
    for a in X.AREAS:
        idx, y, R = data[a]
        _, _, _, innov = _kf_break(y, R, s2, b, idx, out_innov=True)
        for t, v in innov.items():
            if t >= BREAK:
                resid[t % 4].append(v)
    seas = {q: (sum(v) / (len(v) + 2)) for q, v in resid.items()}
    adj = {}
    for a in X.AREAS:
        idx, y, R = data[a]
        y2 = np.array([yt - seas[t % 4] if (t >= BREAK and yt == yt) else yt for t, yt in zip(idx, y)])
        adj[a] = (idx, y2, R)
    s2b, bb = best_fit(adj)
    _SEAS_CACHE[key] = (s2b, bb, seas, adj)
    return _SEAS_CACHE[key]


def seas_forecast(qa: pd.DataFrame, upto: int, target: int) -> dict:
    s2, b, seas, adj = seas_fit(qa, upto)
    out = {}
    for a in X.AREAS:
        idx, y2, R = adj[a]
        obs = np.where(~np.isnan(y2))[0]
        if not len(obs):
            continue
        mu, P, _ = _kf_break(y2[: obs[-1] + 1], R[: obs[-1] + 1], s2, b, idx[: obs[-1] + 1])
        h = target - idx[obs[-1]]
        extra = b if idx[obs[-1]] < BREAK <= target else 0.0
        f = mu + (seas[target % 4] if target >= BREAK else 0.0)
        out[a] = {"f": f, "sd": float(np.sqrt(P + h * s2 + extra + np.nanmedian(R))), "seas": seas[target % 4] if target >= BREAK else 0.0}
    return out


# ------------------------------------------------------------------ walk-forward with the new models
def run132(policy: str, rr, qt, cpi, reg, pov, ablate: dict | None = None) -> pd.DataFrame:
    final = qt.set_index(["area", "quarter"])
    feats = {}
    for D, issue in X.schedule(rr, policy):
        qa = X.asof(rr, issue)
        if qa.empty:
            continue
        upto = int(qa["qi"].max())
        for k in L.LEADS:
            T = L.qs(L.qi(D) - 1 + k)
            F = X.features(issue, rr, cpi, reg, pov, L.qi(T))
            if F.empty:
                continue
            ll = X.llm_forecast(qa, upto, L.qi(T), damped=False)
            F["D"], F["issue"], F["lead"], F["target"] = D, issue, k, T
            F["published_target"] = [final.loc[(a, T), "published"] if (a, T) in final.index else None for a in F["area"]]
            F["y_true"] = [final.loc[(a, T), "y"] if (a, T) in final.index else np.nan for a in F["area"]]
            F["delta"] = F["y_true"] - F["y_latest"]
            F["f_LLM_row"] = [ll[a]["f"] for a in F["area"]]
            F["resid_llm"] = F["y_true"] - F["f_LLM_row"]
            feats[(D, k)] = F
    preds = []
    for (D, k), F in feats.items():
        issue, target = F["issue"].iloc[0], L.qi(F["target"].iloc[0])
        ev = F[F["y_true"].notna()].copy()
        if ev.empty:
            continue
        qa = X.asof(rr, issue)
        upto = int(qa["qi"].max())
        ll, dl, se = (X.llm_forecast(qa, upto, target, False), X.llm_forecast(qa, upto, target, True), seas_forecast(qa, upto, target))
        tr = pd.concat([G for (D2, k2), G in feats.items() if k2 == k and G["issue"].iloc[0] < issue] + [pd.DataFrame()], ignore_index=True)
        if len(tr):
            tr = tr[np.array([isinstance(d, date) and d < issue for d in tr["published_target"]], dtype=bool)]
        nq = tr["target"].nunique() if len(tr) else 0
        base = ev[["area", "D", "issue", "lead", "target", "y_true", "y_latest", "h", "n_obs", "published_target"]].copy()
        base["policy"] = policy
        base["f_PERSIST"], base["f_CLIM"] = ev["y_latest"].values, ev["area_mean"].values
        for nm, fc in (("LLM", ll), ("DLLM", dl), ("SEAS-LLM", se)):
            base[f"f_{nm}"] = [fc[a]["f"] for a in ev["area"]]
            base[f"sd_{nm}"] = [fc[a]["sd"] for a in ev["area"]]
        base["seas_effect"] = [se[a]["seas"] for a in ev["area"]]
        base["f_ENS"] = (base["f_PERSIST"] + base["f_LLM"] + base["f_SEAS-LLM"]) / 3
        base["n_train_rows"], base["n_train_quarters"] = len(tr), nq
        if len(tr) >= 20 and nq >= 8:
            for name, (kind, spec) in X.LEARNED.items():
                cols = X.feat_cols(spec)
                p, ptr, trees = X.fit_predict(kind, cols, tr, ev)
                base[f"f_{name}"] = ev["y_latest"].values + p
                base[f"q80_{name}"] = float(np.quantile(np.abs(tr["delta"].to_numpy() - ptr), 0.8))
                base[f"train_mae_{name}"] = float(np.mean(np.abs(tr["delta"].to_numpy() - ptr)))
            trh = tr.copy()
            trh["delta"] = trh["resid_llm"]
            evh = ev.copy()
            hr = [c for c in HYB_RIDGE_FEATS if not (ablate and c in ablate.get("HYB-RIDGE", []))]
            hl = [c for c in dict.fromkeys(X.feat_cols(None) + ["riceaff_chg4"] + INC) if not (ablate and c in ablate.get("HYB-LGBM", []))]
            for name, kind, cols in (("HYB-RIDGE", "ridge", hr), ("HYB-LGBM", "lgbm", hl)):
                p, ptr, trees = X.fit_predict(kind, cols, trh, evh)
                base[f"f_{name}"] = base["f_LLM"].values + p
                base[f"q80_{name}"] = float(np.quantile(np.abs(trh["delta"].to_numpy() - ptr), 0.8))
                base[f"train_mae_{name}"] = float(np.mean(np.abs(trh["delta"].to_numpy() - ptr)))
        preds.append(base)
    return pd.concat(preds, ignore_index=True)


# ------------------------------------------------------------------ diagnostics
def oracle(qt: pd.DataFrame, P: pd.DataFrame) -> pd.DataFrame:
    """Ex-post Kalman (RTS) smoothed level per area with the pooled s2 fitted on all data: the 'true' level a perfect
    forecaster would know. ORACLE-LEVEL = smoothed level at the target; ORACLE-NOW = smoothed level at the latest
    observed quarter at the issue date (perfect denoising, no change foreseen)."""
    upto = int(qt["qi"].max())
    s2, _, _, data = X.fit_llm(qt, upto, damped=False)
    sm = {}
    for a in X.AREAS:
        idx, y, R = data[a]
        mus, Ps, mup, Pp, started = [], [], [], [], False
        mu = P_ = None
        for yt, rt in zip(y, R):
            if not started:
                if yt == yt:
                    mu, P_, started = yt, rt, True
                mup.append(mu if started else np.nan); Pp.append(P_ if started else np.nan)
                mus.append(mu if started else np.nan); Ps.append(P_ if started else np.nan)
                continue
            mpred, ppred = mu, P_ + s2
            mup.append(mpred); Pp.append(ppred)
            if yt == yt:
                K = ppred / (ppred + rt)
                mu, P_ = mpred + K * (yt - mpred), (1 - K) * ppred
            else:
                mu, P_ = mpred, ppred
            mus.append(mu); Ps.append(P_)
        n = len(mus)
        smv = list(mus)
        for t in range(n - 2, -1, -1):
            if np.isnan(mus[t]) or np.isnan(Pp[t + 1]):
                continue
            J = Ps[t] / Pp[t + 1]
            smv[t] = mus[t] + J * (smv[t + 1] - mup[t + 1])
        sm[a] = dict(zip(idx, smv))
    out = P.copy()
    out["f_ORACLE-LEVEL"] = [sm[a].get(L.qi(t), np.nan) for a, t in zip(out["area"], out["target"])]
    out["f_ORACLE-NOW"] = [sm[a].get(int(L.qi(t) - h), np.nan) for a, t, h in zip(out["area"], out["target"], out["h"])]
    return out


def octa_vs_sws(qt: pd.DataFrame) -> dict:
    o = pd.read_csv(OCTA)
    o = o[~o["fieldwork"].str.contains("previous round")].copy()
    o["start"] = pd.to_datetime(o["fieldwork"].str[:10])
    o["quarter"] = o["start"].dt.year.astype(str) + "-Q" + ((o["start"].dt.month - 1) // 3 + 1).astype(str)
    s = qt[qt.area == "balance_luzon"].set_index("quarter")
    m = o[o["quarter"].isin(s.index)].drop_duplicates("quarter")
    d = pd.DataFrame({"quarter": m["quarter"], "octa": m["value"].astype(float).values,
                      "sws": [s.loc[q, "y"] for q in m["quarter"]], "tol": [s.loc[q, "tol"] for q in m["quarter"]]})
    d["diff"] = d["sws"] - d["octa"]
    d.to_csv(OUT / "d2_sws_vs_octa.csv", index=False)
    return {"matched_quarters": int(len(d)), "mae": float(d["diff"].abs().mean()), "mean_diff_sws_minus_octa": float(d["diff"].mean()),
            "share_within_sws_primary_tolerance": float((d["diff"].abs() <= d["tol"]).mean()),
            "corr": float(np.corrcoef(d["sws"], d["octa"])[0, 1]) if len(d) > 2 else None}


def seal(rr, qt, cpi, reg, pov) -> pd.DataFrame:
    qa = X.asof(rr, SEAL_DATE)
    upto = int(qa["qi"].max())
    rows = []
    for k in L.LEADS:
        T = L.qs(L.qi("2026-Q4") - 1 + k)
        F = X.features(SEAL_DATE, rr, cpi, reg, pov, L.qi(T))
        ll, se = X.llm_forecast(qa, upto, L.qi(T), False), seas_forecast(qa, upto, L.qi(T))
        train = []
        for D2, issue in X.schedule(rr, "P-DASH"):
            T2 = L.qs(L.qi(D2) - 1 + k)
            G = X.features(issue, rr, cpi, reg, pov, L.qi(T2))
            if G.empty:
                continue
            t = qt.set_index(["area", "quarter"])
            G["y_true"] = [t.loc[(a, T2), "y"] if (a, T2) in t.index and t.loc[(a, T2), "published"] < SEAL_DATE else np.nan for a in G["area"]]
            qa2 = X.asof(rr, issue)
            l2 = X.llm_forecast(qa2, int(qa2["qi"].max()), L.qi(T2), False)
            G["delta"] = G["y_true"] - [l2[a]["f"] for a in G["area"]]
            train.append(G[G["y_true"].notna()])
        tr = pd.concat(train, ignore_index=True)
        hr = X.fit_predict("ridge", HYB_RIDGE_FEATS, tr, F)[0]
        hl = X.fit_predict("lgbm", list(dict.fromkeys(X.feat_cols(None) + ["riceaff_chg4"] + INC)), tr, F)[0]
        for i, a in enumerate(F["area"]):
            fl = ll[a]["f"]
            rows.append({"area": a, "issue": SEAL_DATE.isoformat(), "lead": k, "target": T, "y_latest": float(F["y_latest"].iloc[i]),
                         "latest_quarter": L.qs(int(F["q_latest"].iloc[i])), "PERSIST": float(F["y_latest"].iloc[i]), "LLM": fl,
                         "SEAS-LLM": se[a]["f"], "SEAS-LLM_lo80": se[a]["f"] - X.Z80 * se[a]["sd"], "SEAS-LLM_hi80": se[a]["f"] + X.Z80 * se[a]["sd"],
                         "ENS": (float(F["y_latest"].iloc[i]) + fl + se[a]["f"]) / 3, "HYB-RIDGE": fl + hr[i], "HYB-LGBM": fl + hl[i]})
    return pd.DataFrame(rows)


def main():
    global INCOME, RICE
    OUT.mkdir(exist_ok=True)
    rr = X.rounds()
    qt = X.quarter_table(rr)
    cpi, reg, pov = X.cpi_quarterly(), X.regional_covariates(), X.poverty_area()
    INCOME, RICE = income_area(), rice_affordability()
    INCOME.to_csv(OUT / "area_income_features.csv", index=False)
    RICE.to_csv(OUT / "area_rice_affordability.csv", index=False)
    X.features = features132
    GROUPS132.update({k: list(v) for k, v in X.GROUPS.items()})
    GROUPS132["A"] = GROUPS132["A"] + ["riceaff_chg4"]
    GROUPS132["E"] = GROUPS132["E"] + INC
    X.feat_cols = feat_cols132
    X.MODELS = ALL_MODELS
    P = pd.concat([run132(p, rr, qt, cpi, reg, pov) for p in ("P-DASH", "P-REL")], ignore_index=True)
    P = X.intervals(X.add_truth(P, qt))
    P = oracle(qt, P)
    P.to_csv(OUT / "e132_predictions.csv", index=False)
    M, R = X.evaluate(P)
    M.to_csv(OUT / "e132_metrics.csv", index=False)
    L.dump(R, OUT / "e132_rules.json")
    o = P[P["n_obs"] >= 8].copy()
    rows = []
    for (pol, k), g in o.groupby(["policy", "lead"]):
        for m in ["PERSIST", "LLM", "SEAS-LLM", "ENS", "ORACLE-NOW", "ORACLE-LEVEL"]:
            gg = g.dropna(subset=[f"f_{m}"])
            rows.append({"policy": pol, "lead": k, "model": m, "n": len(gg), "quarters": gg["target"].nunique(),
                         "within": float((np.abs(gg[f"f_{m}"] - gg["y_true"]) <= gg["tol"]).mean()),
                         "mae": float(np.abs(gg[f"f_{m}"] - gg["y_true"]).mean())})
    U = pd.DataFrame(rows)
    U.to_csv(OUT / "e132_univariate_and_oracle.csv", index=False)
    abl = []
    for name, groups in (("HYB-RIDGE", {"price": ["riceaff_chg4"], "income": ["real_pay_growth", "unemp_area_chg"]}),
                         ("HYB-LGBM", {g: GROUPS132[g] for g in ("A", "C", "E", "N", "V")})):
        for gname, cols in groups.items():
            Pa = X.add_truth(run132("P-DASH", rr, qt, cpi, reg, pov, ablate={name: cols}), qt)
            for k in (1, 2):
                full = P[(P.policy == "P-DASH") & (P.lead == k)].dropna(subset=[f"f_{m}" for m in ALL_MODELS])
                b = Pa[Pa.lead == k].set_index(["area", "D"]).reindex(full.set_index(["area", "D"]).index)
                ok = b[f"f_{name}"].notna().to_numpy()
                y, tol = full["y_true"].to_numpy()[ok], full["tol"].to_numpy()[ok]
                fa, fb = full[f"f_{name}"].to_numpy()[ok], b[f"f_{name}"].to_numpy()[ok]
                abl.append({"model": name, "lead": k, "group_removed": gname, "rows": int(ok.sum()),
                            "delta_mae_when_removed": float(np.mean(np.abs(fb - y)) - np.mean(np.abs(fa - y))),
                            "delta_within_when_removed": float(np.mean(np.abs(fb - y) <= tol) - np.mean(np.abs(fa - y) <= tol))})
    pd.DataFrame(abl).to_csv(OUT / "e132_ablation.csv", index=False)
    L.dump(octa_vs_sws(qt), OUT / "d2_sws_vs_octa.json")
    print(M[M.policy == "P-DASH"].pivot_table(index="model", columns="lead", values="within_tolerance").round(3).to_string())
    print(M[M.policy == "P-REL"].pivot_table(index="model", columns="lead", values="within_tolerance").round(3).to_string())
    print(U.pivot_table(index=["policy", "model"], columns="lead", values="within").round(3).to_string())


if __name__ == "__main__":
    main()
