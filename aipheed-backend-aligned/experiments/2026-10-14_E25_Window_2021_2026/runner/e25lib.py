"""E25 library: in-window loading with runtime window assertions, pre-2021 masking, Dnow from in-window indices,
2021+ candidate models. FROZEN_EVALUATION_PROTOCOL.md (E25) sections 1-5. Import after guard.install()."""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

import e23_lib as L
import guard
import pcf
import run_e23 as R

qk, qs = L.qk, L.qs
FIRST_Q, LAST_Q = "2021-Q1", "2026-Q2"          # AUTHORIZED_LAST_QUARTER
FIRST_M, LAST_M = (2021, 1), (2026, 6)
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
CODE2PSGC = {"33": "PH040500000", "34": "PH040100000", "35": "PH040200000", "36": "PH040300000", "37": "PH040400000"}
MONTH = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
                                         "Dec"])}
WINDOW_LOG: list[dict] = []


class WindowViolation(RuntimeError):
    pass


def assert_quarters(name: str, quarters, lo=FIRST_Q, hi=LAST_Q):
    q = pd.Series(list(quarters)).dropna()
    bad = int(((q.map(qk) < qk(lo)) | (q.map(qk) > qk(hi))).sum())
    WINDOW_LOG.append({"table": name, "rows": int(len(q)), "min": q.min() if len(q) else None,
                       "max": q.max() if len(q) else None, "outside_window": bad})
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


# ------------------------------------------------------------------------------------------ masking (section 2)
def mask_pre2021(ff: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
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
    # cpi_dev: food_cpi_yoy(q) - mean over q-4..q-1 restricted to >= 2021-Q1 (min 2), else missing
    f = f.sort_values(["province_code", "quarter"]).reset_index(drop=True)
    new = []
    for _, g in f.groupby("province_code", sort=False):
        y = dict(zip(g["quarter"].map(qk), g["food_cpi_yoy"]))
        for qq, val in zip(g["quarter"].map(qk), g["food_cpi_yoy"]):
            prev = [y[j] for j in range(qq - 4, qq) if j >= qk(FIRST_Q) and j in y and pd.notna(y[j])]
            new.append(val - np.mean(prev) if len(prev) >= 2 and pd.notna(val) else np.nan)
    old = f["cpi_dev"].copy()
    f["cpi_dev"] = new
    counts["cpi_dev_recomputed_rows_changed"] = int((~np.isclose(old.fillna(-9e9), f["cpi_dev"].fillna(-9e9))).sum())
    return f, counts


# ------------------------------------------------------------------------------------------ load (section 1)
def load(mask: bool = True):
    log = []
    comp, rounds, ff, gov_cols, S = R.load(log)
    assert_quarters("E12 components", comp["quarter"], hi="2025-Q4")
    assert_quarters("SWS rounds (E12, verified dates)", rounds["quarter"], hi="2025-Q4")
    assert_quarters("features_fused", ff["quarter"], hi="2025-Q4")
    assert_quarters("S1 labels", S["quarter"])
    masked = {}
    if mask:
        ff, masked = mask_pre2021(ff)
    c26 = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.COLL / "provincial_food_cpi_yoy_2026H1_raw.csv")),
                      dtype={"province_code": str})
    assert_months("CPI 2026 H1 (authorized)", c26["reference_month"].str[:4].astype(int),
                  c26["reference_month"].str[5:7].astype(int))
    c26["quarter"] = c26["reference_month"].map(lambda m: f"{m[:4]}-Q{(int(m[5:7]) - 1) // 3 + 1}")
    F = c26.groupby(["province_code", "quarter"])["food_cpi_yoy_pct_raw"].mean().reset_index(name="F")
    F["D"] = F["F"] - F.groupby("quarter")["F"].transform("mean")
    D = pd.concat([comp[comp["D"].notna()][["province_code", "quarter", "D"]], F[["province_code", "quarter", "D"]]],
                  ignore_index=True)
    assert D.groupby("quarter").size().eq(5).all()
    assert_quarters("D labels", D["quarter"])
    V = {"T1": S.rename(columns={"S1": "v"})[["province_code", "quarter", "v"]],
         "T2": D.rename(columns={"D": "v"})}
    for k in V:
        V[k] = V[k].assign(tq=V[k]["quarter"].map(qk)).reset_index(drop=True)
    Dnow, cmp = build_dnow(c26, comp)
    Dm = {(r.province_code, qk(r.quarter)): float(r.v) for r in V["T2"].itertuples()}
    Nm = {(r.province_code, qk(r.quarter)): float(r.Dnow) for r in Dnow.itertuples()}
    return {"comp": comp, "rounds": rounds, "ff": ff, "gov_cols": gov_cols, "S": S, "V": V, "Dm": Dm, "Nm": Nm,
            "Dnow": Dnow, "masked": masked, "dnow_check": cmp, "integrity": log}


def build_dnow(c26: pd.DataFrame, comp: pd.DataFrame):
    """Dnow(p,q) = mean over months 1-2 of q of (YoY_p - five-province mean YoY).
    2022-2025: YoY from in-window indices (first YoY = 2022-01); 2026: authorized published YoY."""
    d = pd.read_csv(io.StringIO(guard.read_e24v2_cpi()), dtype=str)
    d = d[d["Commodity Description_code"] == "2"].copy()                         # 01.1 FOOD
    d["province_code"] = d["Geolocation_code"].map(CODE2PSGC)
    d["year"], d["month"] = d["Year"].astype(int), d["Period"].map(MONTH)
    d["value"] = pd.to_numeric(d["value"])
    assert_months("CPI indices 2021-2025 (E24v2 acquisition)", d["year"], d["month"])
    w = d.set_index(["province_code", "year", "month"])["value"]
    rows = []
    for (p, y, m), v in w.items():
        if (p, y - 1, m) in w.index:
            rows.append({"province_code": p, "year": y, "month": m, "yoy": 100 * (v / w[(p, y - 1, m)] - 1)})
    y = pd.DataFrame(rows)
    y["quarter"] = y["year"].astype(str) + "-Q" + ((y["month"] - 1) // 3 + 1).astype(str)
    # in-window comparability: quarterly D from index YoY vs approved E12 D (2022-2025)
    fq = y.groupby(["province_code", "quarter"])["yoy"].agg(["mean", "count"]).reset_index()
    fq = fq[fq["count"] == 3]
    fq["Dq"] = fq["mean"] - fq.groupby("quarter")["mean"].transform("mean")
    m = fq.merge(comp[["province_code", "quarter", "D"]], on=["province_code", "quarter"]).dropna()
    big = m["D"].abs() >= 0.05
    cmp = {"rows": int(len(m)), "quarters": f"{m['quarter'].min()}..{m['quarter'].max()}",
           "max_abs_dD": float((m["Dq"] - m["D"]).abs().max()),
           "sign_agreement_absD_ge_0.05": float((np.sign(m.loc[big, "Dq"]) == np.sign(m.loc[big, "D"])).mean())}
    y12 = y[((y["month"] - 1) % 3) < 2].copy()
    y12["dev"] = y12["yoy"] - y12.groupby(["year", "month"])["yoy"].transform("mean")
    a = y12.groupby(["province_code", "quarter"])["dev"].agg(["mean", "count"]).reset_index()
    a = a[a["count"] == 2].rename(columns={"mean": "Dnow"})[["province_code", "quarter", "Dnow"]]
    c = c26.copy()
    c["month"] = c["reference_month"].str[5:7].astype(int)
    c = c[((c["month"] - 1) % 3) < 2]
    c["dev"] = c["food_cpi_yoy_pct_raw"] - c.groupby("reference_month")["food_cpi_yoy_pct_raw"].transform("mean")
    b = c.groupby(["province_code", "quarter"])["dev"].mean().reset_index(name="Dnow")
    out = pd.concat([a, b], ignore_index=True)
    assert not out.duplicated(["province_code", "quarter"]).any()
    assert_quarters("Dnow", out["quarter"], lo="2022-Q1")
    return out, cmp


# ------------------------------------------------------------------------------------------ candidates (section 4)
def d_model(Dm, Nm, t: int, k: int, now: bool):
    """OLS without intercept of D(t'+k) on [Dnow(t'), D(t'-1)] (now) or [D(t'-1)], all pairs with t'+k <= t-1 and every
    value inside the window. Returns beta, sigma, n_pairs, n_training_target_quarters."""
    first = qk("2022-Q1") if now else qk("2021-Q2")
    X, y, tq = [], [], set()
    for tp in range(first, t - k):
        for p in PROVS:
            dl, dt = Dm.get((p, tp - 1)), Dm.get((p, tp + k))
            dn = Nm.get((p, tp)) if now else 0.0
            if dl is None or dt is None or dn is None:
                continue
            X.append([dn, dl] if now else [dl])
            y.append(dt)
            tq.add(tp + k)
    if len(tq) < L.MIN_TRAIN_QUARTERS:
        return None, None, len(y), len(tq)
    beta, sig = pcf.d_fit(np.asarray(X, float), np.asarray(y, float))
    return beta, sig, len(y), len(tq)


def d_point(Dm, Nm, p, t, beta, now):
    x = [Nm.get((p, t)), Dm.get((p, t - 1))] if now else [Dm.get((p, t - 1))]
    if any(v is None for v in x):
        return None
    return float(np.dot(beta, x))


def h_inputs(rounds: pd.DataFrame, t: int):
    o = L.origin_of(t)
    r = rounds[(rounds["published"] < o) & rounds["definition_A"]]
    assert (r["published"] < o).all()
    return r["quarter"].map(qk).to_numpy(float), r["H"].to_numpy(float), int(r["quarter"].nunique())
