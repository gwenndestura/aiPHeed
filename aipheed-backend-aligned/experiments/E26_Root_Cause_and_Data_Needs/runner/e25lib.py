"""E25 library: in-window data with runtime window assertions, the three SWS readings, strict publication timing,
pre-2021 masking, Dnow and monthly relative inflation from in-window data, and every E25 model.
FROZEN_EVALUATION_PROTOCOL.md sections 1-6. Import after guard.install(). No file is written here."""
from __future__ import annotations

import io
import json
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

import e23_lib as L
import guard
import pcf

qk, qs = L.qk, L.qs
FIRST_Q, LAST_Q = "2021-Q1", "2026-Q2"              # AUTHORIZED_LAST_QUARTER
LAST_FEATURE_Q = "2025-Q4"                          # news + government features exist through 2025-Q4
FIRST_M, LAST_M = (2021, 1), (2026, 6)
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
PNAME = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
CODE2PSGC = {"33": "PH040500000", "34": "PH040100000", "35": "PH040200000", "36": "PH040300000", "37": "PH040400000"}
MONTH = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
                                         "Dec"])}
READINGS = ("A", "B", "C")          # A = production rounds only (approved, primary); B, C = disputed-round readings
C_REASSIGN = "First Quarter 2025 Social Weather Survey"   # reading C: assigned to 2025-Q1 by its name
MIN_TRAIN_QUARTERS = L.MIN_TRAIN_QUARTERS          # 8
LEADS = L.LEADS                                     # 1..8
Z80 = float(norm.ppf(0.9))
WINDOW_LOG: list[dict] = []


class WindowViolation(RuntimeError):
    pass


def assert_quarters(name: str, quarters, lo=FIRST_Q, hi=LAST_Q):
    q = pd.Series(list(quarters)).dropna()
    bad = int(((q.map(qk) < qk(lo)) | (q.map(qk) > qk(hi))).sum())
    WINDOW_LOG.append({"table": name, "rows": int(len(q)), "min": min(q, key=qk) if len(q) else None,
                       "max": max(q, key=qk) if len(q) else None, "outside_window": bad})
    if bad:
        raise WindowViolation(f"{name}: {bad} rows outside {lo}..{hi}")


def assert_months(name: str, years, months):
    ym = pd.Series(np.asarray(years, int) * 100 + np.asarray(months, int))
    lo, hi = FIRST_M[0] * 100 + FIRST_M[1], LAST_M[0] * 100 + LAST_M[1]
    bad = int(((ym < lo) | (ym > hi)).sum())
    WINDOW_LOG.append({"table": name, "rows": int(len(ym)), "min": int(ym.min()), "max": int(ym.max()),
                       "outside_window": bad})
    if bad:
        raise WindowViolation(f"{name}: {bad} monthly rows outside 2021-01..2026-06")


def origin(t: int) -> pd.Timestamp:
    """O(t) = 00:00 PHT on the first day of quarter t+1 (naive timestamps are PHT)."""
    return L.origin_of(t)


# ================================================================================================ SWS rounds
def load_rounds() -> pd.DataFrame:
    """E12 rounds 2021-2025 (verified publication dates) + the two authorized 2026 production rounds.
    2026 rounds have no verified publication date: published_eff = the time the production file shows they had
    been fetched (an upper bound). A round is usable at origin O only if published_eff < O (strict rule)."""
    det = json.loads(guard.read_allowed_text(guard.E12_DETAILS))
    r = pd.DataFrame(det["two_layer"]["regional_layer_rounds"])
    r["published"] = pd.to_datetime(r["published"])
    r["published_eff"] = r["published"]
    r["fieldwork_quarter"] = r["quarter"]
    s = guard.read_allowed_parquet(guard.PROD_SWS, ["quarter", "survey_quarter_label", "pct_total_hunger", "stratum",
                                                    "fetched_at"])
    assert (s["stratum"] == "balance_luzon").all()
    rows = []
    for q, g in s.groupby("quarter"):
        assert g["pct_total_hunger"].nunique() == 1 and g["survey_quarter_label"].nunique() == 1
        ub = pd.to_datetime(g["fetched_at"], utc=True).max().tz_convert("Asia/Manila").tz_localize(None)
        rows.append({"quarter": q, "round": g["survey_quarter_label"].iloc[0], "H": float(g["pct_total_hunger"].iloc[0]),
                     "published": pd.NaT, "published_eff": ub.ceil("D"), "fieldwork_quarter": q,
                     "date_type": "unverified; upper bound = fetch time in the production file",
                     "definition_A": True, "source": "production_2026_authorized"})
    out = pd.concat([r, pd.DataFrame(rows)], ignore_index=True)
    assert_quarters("SWS rounds", out["quarter"])
    return out


def rounds_for(rounds: pd.DataFrame, reading: str) -> pd.DataFrame:
    """Rounds used for the LABEL under each reading (quarter column = assigned quarter)."""
    r = rounds.copy()
    if reading == "A":
        r = r[r["definition_A"]]
    elif reading == "B":
        pass                                         # every round, E12 quarter assignment
    elif reading == "C":
        m = r["round"].str.contains(C_REASSIGN, regex=False)
        assert m.sum() == 1
        r.loc[m, "quarter"] = "2025-Q1"              # assignment by the round's name
    else:
        raise ValueError(reading)
    return r.reset_index(drop=True)


def h_inputs(rounds: pd.DataFrame, O: pd.Timestamp, include_supp: bool):
    """Rounds usable as PCF inputs at origin O (production; plus supplementary when include_supp)."""
    r = rounds[rounds["published_eff"] < O]
    r = r[r["definition_A"] | (include_supp & (r["source"] == "supplementary"))]
    assert (r["published_eff"] < O).all()
    return r["fieldwork_quarter"].map(qk).to_numpy(float), r["H"].to_numpy(float), int(r["fieldwork_quarter"].nunique())


# ================================================================================================ D, Dnow, monthly
def load_components():
    comp = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.E12_COMPONENTS)), dtype={"province_code": str})
    assert_quarters("E12 components", comp["quarter"], hi="2025-Q4")
    c26 = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.CPI_2026H1)), dtype={"province_code": str})
    assert_months("CPI 2026 H1 (authorized)", c26["reference_month"].str[:4].astype(int),
                  c26["reference_month"].str[5:7].astype(int))
    assert sorted(c26["reference_month"].unique()) == [f"2026-0{m}" for m in range(1, 7)] and len(c26) == 30
    c26["quarter"] = c26["reference_month"].map(lambda m: f"{m[:4]}-Q{(int(m[5:7]) - 1) // 3 + 1}")
    F = c26.groupby(["province_code", "quarter"])["food_cpi_yoy_pct_raw"].mean().reset_index(name="F")
    F["D"] = F["F"] - F.groupby("quarter")["F"].transform("mean")
    D = pd.concat([comp[comp["D"].notna()][["province_code", "quarter", "D", "F"]],
                   F[["province_code", "quarter", "D", "F"]]], ignore_index=True)
    assert D.groupby("quarter").size().eq(5).all() and not D.duplicated(["province_code", "quarter"]).any()
    assert_quarters("D", D["quarter"])
    return comp, c26, D


def load_monthly(c26: pd.DataFrame, comp: pd.DataFrame):
    """Monthly provincial food YoY: 2022-01..2025-12 from in-window indices (first YoY needs 2021 indices),
    2026-01..06 = authorized published YoY. d = YoY - five-province mean (monthly relative inflation)."""
    d = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.CPI_INDEX_2021_2025)), dtype=str)
    d = d[d["Commodity Description_code"] == "2"].copy()                         # 01.1 FOOD
    d["province_code"] = d["Geolocation_code"].map(CODE2PSGC)
    d["year"], d["month"] = d["Year"].astype(int), d["Period"].map(MONTH)
    d["value"] = pd.to_numeric(d["value"])
    assert_months("CPI indices 2021-2025 (E24v2 acquisition)", d["year"], d["month"])
    w = d.set_index(["province_code", "year", "month"])["value"]
    rows = [{"province_code": p, "year": y, "month": m, "yoy": 100 * (v / w[(p, y - 1, m)] - 1), "src": "index"}
            for (p, y, m), v in w.items() if (p, y - 1, m) in w.index]
    y = pd.DataFrame(rows)
    c = c26.copy()
    c["year"], c["month"] = c["reference_month"].str[:4].astype(int), c["reference_month"].str[5:7].astype(int)
    y = pd.concat([y, c.rename(columns={"food_cpi_yoy_pct_raw": "yoy"})[["province_code", "year", "month", "yoy"]]
                   .assign(src="published_2026")], ignore_index=True)
    y["ym"] = y["year"] * 12 + y["month"] - 1
    y["quarter"] = y["year"].astype(str) + "-Q" + ((y["month"] - 1) // 3 + 1).astype(str)
    y["d"] = y["yoy"] - y.groupby("ym")["yoy"].transform("mean")
    assert y.groupby("ym").size().eq(5).all()
    # comparability: quarterly D from index YoY vs approved E12 D (2022-2025) - reported, never used to select
    fq = y[y["src"] == "index"].groupby(["province_code", "quarter"])["yoy"].agg(["mean", "count"]).reset_index()
    fq = fq[fq["count"] == 3]
    fq["Dq"] = fq["mean"] - fq.groupby("quarter")["mean"].transform("mean")
    m = fq.merge(comp[["province_code", "quarter", "D"]], on=["province_code", "quarter"]).dropna()
    cmp = {"rows": int(len(m)), "max_abs_dD": float((m["Dq"] - m["D"]).abs().max()),
           "mean_abs_dD": float((m["Dq"] - m["D"]).abs().mean()),
           "sign_agreement_absD_ge_0.05": float((np.sign(m.loc[m["D"].abs() >= .05, "Dq"]) ==
                                                np.sign(m.loc[m["D"].abs() >= .05, "D"])).mean())}
    y12 = y[((y["month"] - 1) % 3) < 2]
    a = y12.groupby(["province_code", "quarter"])["d"].agg(["mean", "count"]).reset_index()
    Dnow = a[a["count"] == 2].rename(columns={"mean": "Dnow"})[["province_code", "quarter", "Dnow"]]
    assert_quarters("Dnow", Dnow["quarter"], lo="2022-Q1")
    return y.sort_values(["province_code", "ym"]).reset_index(drop=True), Dnow, cmp


# ================================================================================================ features
def mask_pre2021(ff: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Remove the 2020 information carried by in-window rows (protocol section 2)."""
    f = ff.copy()
    q = f["quarter"].map(qk)
    counts = {}
    for c in f.columns:
        if c.endswith("_lag1") or c.endswith("_accel"):
            m = (q <= qk("2021-Q1")) & f[c].notna()
        elif c.endswith("_lag2"):
            m = (q <= qk("2021-Q2")) & f[c].notna()
        else:
            continue
        counts[c] = int(m.sum())
        f.loc[m, c] = np.nan
    f = f.sort_values(["province_code", "quarter"]).reset_index(drop=True)
    new = []
    for _, g in f.groupby("province_code", sort=False):
        yv = dict(zip(g["quarter"].map(qk), g["food_cpi_yoy"]))
        for qq, val in zip(g["quarter"].map(qk), g["food_cpi_yoy"]):
            prev = [yv[j] for j in range(qq - 4, qq) if j >= qk(FIRST_Q) and j in yv and pd.notna(yv[j])]
            new.append(val - np.mean(prev) if len(prev) >= 2 and pd.notna(val) else np.nan)
    old = f["cpi_dev"].copy()
    f["cpi_dev"] = new
    counts["cpi_dev_rows_changed"] = int((~np.isclose(old.fillna(-9e9), f["cpi_dev"].fillna(-9e9))).sum())
    return f, counts


def load_features(rounds_A: pd.DataFrame):
    gov = json.loads(guard.read_allowed_text(guard.GOVERNING))
    cand = gov["feature_set"]["candidates_section_3_3_2_6"]
    ff = guard.read_allowed_parquet(guard.FEATURES_FUSED, ["province_code", "quarter"] + cand + ["cpi_dev"])
    assert_quarters("features_fused", ff["quarter"], hi=LAST_FEATURE_Q)
    ff, masked = mask_pre2021(ff)
    gov_cols = [c for c in cand if c not in L.NLP and c != "poverty_incidence"] + ["cpi_dev"]
    r = rounds_A[rounds_A["quarter"].map(qk) <= qk("2025-Q4")].rename(columns={"published_eff": "pub"})
    r = r.assign(published=r["pub"])           # E23 sws_at_origin reads 'published' and 'definition_A'
    X = L.build_frame(ff, r, gov_cols)
    const = {}
    for c in gov_cols + L.NLP:
        v = ff.groupby("quarter")[c].nunique()
        const[c] = {"share_quarters_province_invariant": float((v <= 1).mean()),
                    "constant_2021_2025": bool(ff[c].nunique() <= 1)}
    return X, gov_cols, masked, const


# ================================================================================================ labels
class Target:
    """T1 label under one SWS reading, or T2 (D > 0). Holds values, publication rule and threshold rule."""

    def __init__(self, name: str, reading: str, rounds: pd.DataFrame, D: pd.DataFrame, fixed_tau: float | None = None):
        self.name, self.reading, self.fixed_tau = name, reading, fixed_tau
        self.D = D
        if name.startswith("T1"):
            ru = rounds_for(rounds, reading)
            self.ru = ru
            H = ru.groupby("quarter")["H"].mean()
            self.maxpub = ru.groupby("quarter")["published_eff"].max()
            v = D.merge(H.rename("H").reset_index(), on="quarter", how="inner")
            v["v"] = v["H"] + 2 * v["D"]
            self.H = H
        else:
            v = D.assign(v=D["D"])
            self.maxpub = None
        v = v[["province_code", "quarter", "v"]].copy()
        v["tq"] = v["quarter"].map(qk)
        assert_quarters(f"{name}/{reading} labels", v["quarter"])
        self.V = v.sort_values(["tq", "province_code"]).reset_index(drop=True)
        self._pub = {}

    def pub(self, q: str, t: int) -> bool:
        key = (q, t)
        if key not in self._pub:
            ok = qk(q) <= t - 1
            if ok and self.maxpub is not None:
                ok = q in self.maxpub.index and bool(self.maxpub[q] < origin(t))
            self._pub[key] = ok
        return self._pub[key]

    def published(self, t: int) -> pd.DataFrame:
        return self.V[self.V["quarter"].map(lambda q: self.pub(q, t))]

    def tau(self, t: int) -> float:
        if self.name == "T2":
            return 0.0
        if self.fixed_tau is not None:
            return float(self.fixed_tau)
        return float(self.published(t)["v"].median())


# ================================================================================================ label history
def last_values(T: Target, t: int) -> dict:
    """Per province: (last published value, mean of last 4, last - previous) at origin O(t)."""
    out = {}
    P = T.published(t)
    for p in PROVS:
        g = P[P["province_code"] == p].sort_values("tq")
        if g.empty:
            out[p] = (np.nan, np.nan, np.nan)
        else:
            v = g["v"].to_numpy()
            out[p] = (v[-1], v[-4:].mean(), v[-1] - v[-2] if len(v) > 1 else np.nan)
    return out


P_COLS = ["v_last", "margin_last", "y_last", "v_mean4", "v_diff"]


def training_pairs(T: Target, t: int, k: int, tau: float, cache: dict) -> pd.DataFrame:
    """Lead-k training pairs usable at O(t): label of t'+k published before O(t), t' >= 2021-Q1, with the label
    history (P block) as known at each pair's own origin O(t') (threshold = the outer threshold tau)."""
    rows = []
    for r in T.V.itertuples():
        tp = r.tq - k
        if tp < qk(FIRST_Q) or not T.pub(r.quarter, t):
            continue
        key = (tp, r.province_code)
        if key not in cache:
            cache[key] = last_values(T, tp)[r.province_code]
        last, m4, dif = cache[key]
        rows.append({"province_code": r.province_code, "t": tp, "target_quarter": r.quarter, "target_q": r.tq,
                     "v": r.v, "y": int(r.v > tau), "v_last": last, "margin_last": last - tau,
                     "y_last": float(last > tau) if last == last else np.nan, "v_mean4": m4, "v_diff": dif})
    tr = pd.DataFrame(rows)
    if len(tr):
        assert tr["target_q"].max() <= t - 1 and all(T.pub(q, t) for q in tr["target_quarter"].unique())
    return tr


def test_rows(T: Target, t: int, k: int, tau: float) -> pd.DataFrame | None:
    """The five test rows (target t+k) with the label history known at O(t); None if the target has no label."""
    tg = T.V[T.V["tq"] == t + k]
    if len(tg) != 5:
        return None
    lv = last_values(T, t)
    rows = []
    for r in tg.sort_values("province_code").itertuples():
        last, m4, dif = lv[r.province_code]
        rows.append({"province_code": r.province_code, "t": t, "target_quarter": r.quarter, "target_q": r.tq,
                     "v": r.v, "y": int(r.v > tau), "v_last": last, "margin_last": last - tau,
                     "y_last": float(last > tau) if last == last else np.nan, "v_mean4": m4, "v_diff": dif})
    return pd.DataFrame(rows)


def calibrated_persistence(tr: pd.DataFrame, y_last_te) -> np.ndarray:
    """B1p: Laplace rate of HIGH among training pairs with the same last label."""
    out = []
    for yl in y_last_te:
        g = tr[tr["y_last"] == yl]
        out.append((g["y"].sum() + 1.0) / (len(g) + 2.0))
    return np.asarray(out, float)


def climatology(tr: pd.DataFrame, n: int) -> np.ndarray:
    return np.full(n, (tr["y"].sum() + 1.0) / (len(tr) + 2.0))


def lr_p(tr: pd.DataFrame, te: pd.DataFrame) -> np.ndarray:
    """E24-frozen ABL_lr_P: logistic regression (C = 1) on the label-history block."""
    return L.fit_lr(tr, P_COLS, te)


# ================================================================================================ D models
def d_ols(Dm, Nm, t: int, k: int, now: bool):
    """M3/M4: OLS without intercept of D(t'+k) on [D(t'-1)] or [Dnow(t'), D(t'-1)], pairs with t'+k <= t-1,
    every value in window (first t' = 2021-Q2, or 2022-Q1 with Dnow)."""
    first = qk("2022-Q1") if now else qk("2021-Q2")
    X, y = [], []
    for tp in range(first, t - k):
        for p in PROVS:
            dl, dt = Dm.get((p, tp - 1)), Dm.get((p, tp + k))
            dn = Nm.get((p, tp)) if now else 0.0
            if dl is None or dt is None or dn is None:
                continue
            X.append([dn, dl] if now else [dl])
            y.append(dt)
    if len(y) < 10:
        return None
    beta, sig = pcf.d_fit(np.asarray(X, float), np.asarray(y, float))
    return {"kind": "ols_now" if now else "ols", "beta": [float(b) for b in beta], "sigma": sig, "n_pairs": len(y)}


def d_ols_predict(m, Dm, Nm, p, t):
    x = [Nm.get((p, t)), Dm.get((p, t - 1))] if m["kind"] == "ols_now" else [Dm.get((p, t - 1))]
    if any(v is None for v in x):
        return None
    return float(np.dot(m["beta"], x)), m["sigma"]


def d_hier(Dm, Nm, t: int, now: bool):
    """D_HIER: province means shrunk toward 0 (empirical Bayes), AR(1) on deviations pooled over provinces and
    consecutive quarters <= t-1 (one model for every lead). With now=True, Dnow(t) updates the one-step state as a
    noisy measurement (error variance from quarters <= t-1 where both are known)."""
    last = t - 1
    series = {p: [(q, Dm[(p, q)]) for q in range(qk(FIRST_Q), last + 1) if (p, q) in Dm] for p in PROVS}
    m = {p: np.mean([v for _, v in s]) for p, s in series.items()}
    n = {p: len(s) for p, s in series.items()}
    s2 = {p: np.var([v for _, v in s], ddof=1) for p, s in series.items()}
    between = max(0.0, float(np.var(list(m.values()), ddof=1) - np.mean([s2[p] / n[p] for p in PROVS])))
    mu = {p: (between / (between + s2[p] / n[p]) if between > 0 else 0.0) * m[p] for p in PROVS}
    xs, ys = [], []
    for p, s in series.items():
        d = dict(s)
        for q in range(qk(FIRST_Q) + 1, last + 1):
            if q in d and q - 1 in d:
                xs.append(d[q - 1] - mu[p])
                ys.append(d[q] - mu[p])
    xs, ys = np.asarray(xs), np.asarray(ys)
    phi = float(np.clip((xs @ ys) / (xs @ xs), -0.99, 0.99))
    sig2 = float(np.sum((ys - phi * xs) ** 2) / max(len(ys) - 1, 1))
    out = {"kind": "hier_now" if now else "hier", "phi": phi, "sigma2": sig2, "mu": mu, "between_var": between,
           "n_pairs": int(len(ys))}
    if now:
        e = [Dm[(p, q)] - Nm[(p, q)] for p in PROVS for q in range(qk("2022-Q1"), last + 1)
             if (p, q) in Dm and (p, q) in Nm]
        out["meas_var"] = float(np.var(e, ddof=1)) if len(e) > 2 else None
    return out


def d_hier_predict(m, Dm, Nm, p, t, k):
    """Forecast D(t+k) from D(t-1) (and Dnow(t)); returns (mean, sd)."""
    if (p, t - 1) not in Dm:
        return None
    mu, phi, s2 = m["mu"][p], m["phi"], m["sigma2"]
    x, P = Dm[(p, t - 1)] - mu, 0.0
    x, P = phi * x, phi * phi * P + s2                         # state D(t)
    if m["kind"] == "hier_now":
        if (p, t) not in Nm or not m.get("meas_var"):
            return None
        R = m["meas_var"]
        K = P / (P + R)
        x, P = x + K * ((Nm[(p, t)] - mu) - x), (1 - K) * P
    for _ in range(k):                                         # D(t+1) .. D(t+k)
        x, P = phi * x, phi * phi * P + s2
    return float(mu + x), float(np.sqrt(P))


def d_forecast(spec: str, Dm, Nm, t, k, cache):
    key = (spec, t, k if spec.startswith("ols") else None)
    if key not in cache:
        if spec == "ols":
            cache[key] = d_ols(Dm, Nm, t, k, False)
        elif spec == "ols_now":
            cache[key] = d_ols(Dm, Nm, t, k, True)
        elif spec == "hier":
            cache[key] = d_hier(Dm, Nm, t, False)
        elif spec == "hier_now":
            cache[key] = d_hier(Dm, Nm, t, True)
        else:
            raise ValueError(spec)
    m = cache[key]
    if m is None:
        return None, None
    out = {}
    for p in PROVS:
        r = d_ols_predict(m, Dm, Nm, p, t) if spec.startswith("ols") else d_hier_predict(m, Dm, Nm, p, t, k)
        if r is None:
            return None, m
        out[p] = r
    return out, m


# ================================================================================================ H models
def h_forecast(spec: str, rounds: pd.DataFrame, t: int, k: int, extras: dict, cache: dict):
    """Forecast distribution of the published Balance Luzon hunger value for quarter t+k at origin O(t).
    LL      : local level (random walk + sampling noise), E24v2 engine, production rounds.
    LL_SUPP : LL with the supplementary rounds also used as inputs (clearly labelled).
    MR      : AR(1) mean reversion of the round values toward the mean of the rounds usable at O(t)
              (phi by least squares on consecutive usable rounds, gap-adjusted phi^gap; sampling noise added).
    LI      : LL plus a ridge-shrunk effect of the latest change in regional (five-province mean) food inflation."""
    key = (spec, t, k)
    if key in cache:
        return cache[key]
    O = origin(t)
    times, ys, nq = h_inputs(rounds, O, include_supp=(spec == "LL_SUPP"))
    if nq < MIN_TRAIN_QUARTERS:
        cache[key] = None
        return None
    target = float(t + k)
    if spec in ("LL", "LL_SUPP"):
        out = pcf.h_forecast(times, ys, target)
    elif spec == "MR":
        o = np.argsort(times, kind="stable")
        tt, yy = times[o], ys[o]
        mbar = float(yy.mean())
        gaps = np.diff(tt)
        ok = gaps > 0
        a, b, g = yy[:-1][ok] - mbar, yy[1:][ok] - mbar, gaps[ok]
        # fit phi (per quarter) on a grid by least squares with the gap power
        grid = np.round(np.arange(0.0, 1.0001, 0.01), 2)
        sse = [float(np.sum((b - (ph ** g) * a) ** 2)) for ph in grid]
        phi = float(grid[int(np.argmin(sse))])
        resid = b - (phi ** g) * a
        s2 = float(np.sum(resid ** 2) / max(len(resid) - 1, 1))
        gap = target - tt[-1]
        mu = mbar + (phi ** gap) * (yy[-1] - mbar)
        V = s2 * (1 - phi ** (2 * gap)) / max(1 - phi ** 2, 1e-6) if phi < 0.999 else s2 * gap
        out = {"mu_H": float(mu), "V_H": float(V + pcf.samp_var(mu)), "phi": phi, "mean_level": mbar, "gap": float(gap),
               "n_rounds": int(len(yy))}
    elif spec == "LI":
        base = pcf.h_forecast(times, ys, target)
        z = extras["regional_food_change"]               # dict t -> change in five-province mean food YoY (t-1 vs t-2)
        o = np.argsort(times, kind="stable")
        tt, yy = times[o], ys[o]
        xs, dy = [], []
        for i in range(1, len(tt)):
            if tt[i] > tt[i - 1] and int(tt[i - 1]) in z:
                xs.append(z[int(tt[i - 1])])
                dy.append(yy[i] - yy[i - 1])
        xs, dy = np.asarray(xs), np.asarray(dy)
        if len(xs) >= 5 and t in z:
            sx = xs.std() or 1.0
            xz = (xs - xs.mean()) / sx
            beta = float((xz @ (dy - dy.mean())) / (xz @ xz + 1.0 * len(xz)))     # ridge, lambda = 1 per row
            shift = beta * (z[t] - xs.mean()) / sx
        else:
            beta, shift = 0.0, 0.0
        out = dict(base, mu_H=base["mu_H"] + shift, li_beta=beta, li_shift=float(shift))
    else:
        raise ValueError(spec)
    out["n_round_quarters"] = nq
    cache[key] = out
    return out


# ================================================================================================ PCF family
PCF_SPECS = {   # name -> (H spec, D spec)
    "PCF21": ("LL", "ols"),
    "PCF21_NOW": ("LL", "ols_now"),
    "PCF21_SUPP": ("LL_SUPP", "ols"),
    "PCF21_HIER": ("LL", "hier_now"),
    "PCF21_MR": ("MR", "ols"),
    "PCF21_LI": ("LI", "ols"),
}


def pcf_t1(name, rounds, Dm, Nm, t, k, tau, extras, hcache, dcache):
    hs, ds = PCF_SPECS[name]
    hf = h_forecast(hs, rounds, t, k, extras, hcache)
    if hf is None:
        return None
    dd, dm = d_forecast(ds, Dm, Nm, t, k, dcache)
    if dd is None:
        return None
    out = {}
    for p in PROVS:
        muD, sdD = dd[p]
        mu = hf["mu_H"] + 2 * muD
        sd = float(np.sqrt(hf["V_H"] + 4 * sdD ** 2))
        out[p] = {"p": pcf.p_high(tau, hf["mu_H"], hf["V_H"], muD, sdD), "mu_S1": mu, "sd_S1": sd,
                  "mu_H": hf["mu_H"], "sd_H": float(np.sqrt(hf["V_H"])), "mu_D": muD, "sd_D": sdD, "tau": tau,
                  "z": (mu - tau) / sd, "regional_part": hf["mu_H"] - tau, "provincial_part": 2 * muD,
                  "var_share_regional": hf["V_H"] / (hf["V_H"] + 4 * sdD ** 2)}
    return out


def t2_prob(spec, Dm, Nm, t, k, dcache):
    dd, _ = d_forecast(spec, Dm, Nm, t, k, dcache)
    if dd is None:
        return None
    return {p: {"p": pcf.p_pos(mu, sd), "mu_D": mu, "sd_D": sd} for p, (mu, sd) in dd.items()}


# ================================================================================================ scoring rules
def brier(y, p):
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def log_score(y, p):
    return L.logloss(y, p)


def crps_gauss(x, mu, sd):
    sd = np.maximum(np.asarray(sd, float), 1e-9)
    z = (np.asarray(x, float) - np.asarray(mu, float)) / sd
    return sd * (z * (2 * norm.cdf(z) - 1) + 2 * norm.pdf(z) - 1 / np.sqrt(np.pi))


def temperature(p_inner, y_inner):
    """One-parameter calibration: logit(p') = a * logit(p), a on a grid by inner log loss (a = 1 is identity)."""
    p = np.clip(np.asarray(p_inner, float), 1e-4, 1 - 1e-4)
    lg = np.log(p / (1 - p))
    best, bs = 1.0, np.inf
    for a in np.round(np.arange(0.2, 2.0001, 0.05), 2):
        q = 1 / (1 + np.exp(-a * lg))
        s = L.logloss(y_inner, q)
        if s < bs - 1e-12:
            best, bs = float(a), s
    return best


def apply_temperature(p, a):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return 1 / (1 + np.exp(-a * np.log(p / (1 - p))))
