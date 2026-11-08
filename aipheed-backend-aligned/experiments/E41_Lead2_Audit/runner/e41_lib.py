"""E41 library: as-of data, Lead-2 methods (PROTOCOL.md section 4), trigger features (section 5).

Every forecast at origin O(t) is computed from `Data.cut(t)`, which drops everything published on or after O(t).
Quarters are integers qi = year*4 + quarter-1; months are ym = year*12 + month-1.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.dont_write_bytecode = True
E41 = Path(__file__).resolve().parents[1]
ROOT = E41.parents[2]
ACQ = E41 / "data_acquired"
E40 = E41.parent / "E40_SWS_CPI_Tiers"
YOY_FILE = E40 / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv"
SWS_FILE = ROOT / "backend" / "data" / "inputs" / "sws_rounds.csv"
NEWS_FILE = E40 / "runs" / "triggers" / "composition.csv"
E40_SPEC = E40 / "label_spec.json"

PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
BY_NAME = {v: k for k, v in NAMES.items()}
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
FULL_MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                           "September", "October", "November", "December"])}
FIRST_YM = 2021 * 12
FIRST_Q = 2021 * 4
FPP_THRESHOLD = 4.0                      # E39 label A (BSP 3 +/- 1 headline ceiling); not chosen from results
TRIGGERS = ["climate", "employment", "ofw_remittance", "fish_kill", "market"]
GROUPS = {
    "market": ["F_last", "F_now", "HL_now", "gap_now", "mom3", "F_hat_M1", "D_now"],
    "hunger_sws": ["H_last", "H_chg", "H_age"],
    "climate_supply": ["palay_yoy", "corn_yoy"],
    "fish_supply": ["fish_yoy", "aqua_yoy"],
    "employment": ["ur_last", "ur_yoy", "under_last"],
    "ofw_remittance": [],                # no official in-window series obtained (PROTOCOL section 5)
    "news": ["news_n"] + [f"news_{k}" for k in TRIGGERS],
}
FEATURES = [c for g in GROUPS.values() for c in g]
LR_FEATURES = ["F_hat_M1", "F_last", "F_now", "gap_now", "H_last"]
LGBM_PARAMS = dict(objective="binary", verbosity=-1, random_state=42, deterministic=True, n_jobs=1,
                   force_row_wise=True)  # P45: objective binary, LightGBM defaults, seed 42 (+ scale_pos_weight)
MIN_TRAIN_QUARTERS = 8


class WindowViolation(RuntimeError):
    pass


def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def q_of_ym(ym: int) -> int:
    return (ym // 12) * 4 + (ym % 12) // 3


def ym_s(ym: int) -> str:
    return f"{ym // 12}-{ym % 12 + 1:02d}"


def m0_of(t: int) -> int:
    """Latest CPI month allowed at O(t): month 2 of quarter t."""
    return (t // 4) * 12 + (t % 4) * 3 + 1


def origin(t: int) -> pd.Timestamp:
    """O(t) = 00:00 PHT on the first day of quarter t+1 (naive local timestamps throughout)."""
    n = t + 1
    return pd.Timestamp(year=n // 4, month=(n % 4) * 3 + 1, day=1)


# ======================================================================================================= data
@dataclass
class Data:
    idx: pd.DataFrame          # province_code, commodity(food|all_items), ym, index
    yoy: pd.DataFrame          # province_code, commodity, ym, yoy (PSA published)
    sws: pd.DataFrame          # quarter(qi), H, published(Timestamp)   approved rounds only
    prod: pd.DataFrame         # province_code, series(palay|corn|fish|aqua), q, value
    lfs: pd.DataFrame          # series(ur|under), ym, value
    news: pd.DataFrame         # province_code, q, news_n, hits_<trigger>
    cut_t: int | None = None
    meta: dict = field(default_factory=dict)

    def cut(self, t: int) -> "Data":
        """Everything published before O(t) (PROTOCOL section 3)."""
        m0, O = m0_of(t), origin(t)
        return Data(
            idx=self.idx[self.idx["ym"] <= m0],
            yoy=self.yoy[self.yoy["ym"] <= m0],
            sws=self.sws[self.sws["published"] < O],
            prod=self.prod[self.prod["q"] <= t - 1],
            lfs=self.lfs[self.lfs["ym"] <= (t - 1) // 4 * 12 + ((t - 1) % 4) * 3 + 2],
            news=self.news[self.news["q"] <= t],
            cut_t=t, meta=self.meta)


def _assert_window(name, ym=None, q=None):
    if ym is not None and len(ym) and int(np.min(ym)) < FIRST_YM:
        raise WindowViolation(f"{name}: value before 2021-01")
    if q is not None and len(q) and int(np.min(q)) < FIRST_Q:
        raise WindowViolation(f"{name}: value before 2021-Q1")


def load() -> Data:
    a = pd.read_csv(ACQ / "cpi_index_ACP22.csv")
    a = a[a["Period"].isin(MONTHS) & a["value"].notna()].copy()
    a["province_code"] = a["Geolocation"].str.strip(". ").map(BY_NAME)
    a["commodity"] = a["Commodity Description"].map({"0 - ALL ITEMS": "all_items", "01.1 - FOOD": "food"})
    a["ym"] = a["Year"].astype(int) * 12 + a["Period"].map(MONTHS)
    idx = a[["province_code", "commodity", "ym"]].assign(index=a["value"].astype(float))
    _assert_window("CPI index", ym=idx["ym"])
    assert not idx.duplicated(["province_code", "commodity", "ym"]).any() and idx["province_code"].notna().all()

    y = pd.read_csv(YOY_FILE, dtype={"province_code": str})
    y["ym"] = y["reference_month"].str[:4].astype(int) * 12 + y["reference_month"].str[5:7].astype(int) - 1
    yoy = y[["province_code", "commodity", "ym", "yoy_pct"]].rename(columns={"yoy_pct": "yoy"})
    _assert_window("CPI YoY", ym=yoy["ym"])

    r = pd.read_csv(SWS_FILE)
    r = r[r["definition_A"].astype(str) == "True"].copy()
    r["q"] = r["quarter"].map(qi)
    _assert_window("SWS", q=r["q"])
    sws = pd.DataFrame({"q": r["q"], "H": r["H"].astype(float), "published": pd.to_datetime(r["published"])})

    p = pd.read_csv(ACQ / "palay_corn_production.csv")
    p = p[p["Geolocation"].isin(BY_NAME) & p["value"].notna()].copy()
    p["q"] = p["Year"].astype(int) * 4 + p["Period"].str[-1].astype(int) - 1
    p = p.assign(province_code=p["Geolocation"].map(BY_NAME), series=p["Ecosystem/Croptype"].str.lower())
    f = pd.read_csv(ACQ / "fisheries_production.csv")
    f["Subsector"] = f["Subsector"].str.strip(". ")
    f = f[f["Geolocation"].isin(BY_NAME) & f["Subsector"].isin(["FISHERIES", "Aquaculture"]) & f["value"].notna()].copy()
    f["q"] = f["Year"].astype(int) * 4 + f["Quarter"].str[-1].astype(int) - 1
    f = f.assign(province_code=f["Geolocation"].map(BY_NAME), series=f["Subsector"].map({"FISHERIES": "fish",
                                                                                        "Aquaculture": "aqua"}))
    prod = pd.concat([p, f])[["province_code", "series", "q", "value"]].reset_index(drop=True)
    _assert_window("production", q=prod["q"])

    l = pd.read_csv(ACQ / "lfs_rates_national.csv")
    l = l[l["Month"].isin(FULL_MONTHS) & l["value"].notna()].copy()
    l["ym"] = l["Year"].astype(int) * 12 + l["Month"].map(FULL_MONTHS)
    lfs = pd.DataFrame({"series": l["Rates"].map({"Unemployment Rate": "ur", "Underemployment Rate": "under"}),
                        "ym": l["ym"], "value": l["value"].astype(float)})
    _assert_window("LFS", ym=lfs["ym"])

    n = pd.read_csv(NEWS_FILE, dtype={"province_code": str})
    n["q"] = n["quarter"].map(qi)
    news = n[["province_code", "q"]].assign(news_n=n["n_articles"].astype(float),
                                           **{f"hits_{k}": n[f"hits_{k}"].astype(float) for k in TRIGGERS})
    _assert_window("news", q=news["q"])
    return Data(idx, yoy, sws, prod, lfs, news)


# ================================================================================================ outcomes
def quarter_F(d: Data, commodity: str = "food") -> pd.DataFrame:
    """Quarter mean of the three published monthly YoY rates; only complete quarters."""
    y = d.yoy[d.yoy["commodity"] == commodity].assign(q=lambda x: x["ym"].map(q_of_ym))
    g = y.groupby(["province_code", "q"])["yoy"].agg(["mean", "size"]).reset_index()
    return g[g["size"] == 3].rename(columns={"mean": "F"})[["province_code", "q", "F"]]


def fpp_labels(d: Data) -> pd.DataFrame:
    F = quarter_F(d)
    return F.assign(y=(F["F"] > FPP_THRESHOLD).astype(int))


def h_quarters(d: Data) -> pd.DataFrame:
    """Approved quarters whose rounds are ALL in d (posted before the cut), mean H."""
    return d.sws.groupby("q")["H"].mean().reset_index()


# ================================================================================================ M1
def _series(d: Data, p: str, commodity: str) -> pd.Series:
    s = d.idx[(d.idx["province_code"] == p) & (d.idx["commodity"] == commodity)]
    return s.set_index("ym")["index"].sort_index()


def drift_sigma(lnI: pd.Series, m0: int) -> tuple[float, float, int]:
    ch = lnI.diff().dropna()
    ch = ch[(ch.index > m0 - 12) & (ch.index <= m0) & (ch.index - 1 >= FIRST_YM)]
    if len(ch) < 6:
        return float("nan"), float("nan"), int(len(ch))
    return float(ch.mean()), float(ch.std(ddof=1)), int(len(ch))


def target_months(t: int, k: int) -> list[int]:
    first = (t + k) // 4 * 12 + ((t + k) % 4) * 3
    return [first, first + 1, first + 2]


def var_factor(h: list[int]) -> float:
    """Var of the mean of random-walk errors at horizons h, in units of sigma^2."""
    return sum(min(a, b) for a in h for b in h) / len(h) ** 2


def m1_point(d: Data, t: int, k: int, p: str, zero_drift: bool = False) -> dict:
    """Base-effect projection of F(t+k) from the food index (PROTOCOL 4.1, M1 / M1z)."""
    m0 = m0_of(t)
    I = _series(d, p, "food")
    if m0 not in I.index:
        return {"F_hat": np.nan}
    lnI = np.log(I)
    g, sd, n = drift_sigma(lnI, m0)
    if zero_drift:
        g = 0.0 if n >= 6 else np.nan
    ms = target_months(t, k)
    if any((m - 12) not in I.index or (m - 12) < FIRST_YM for m in ms) or not np.isfinite(g):
        return {"F_hat": np.nan, "n_drift": n}
    yo = [100 * (math.exp(lnI[m0] + g * (m - m0)) / I[m - 12] - 1) for m in ms]
    s_theory = 100 * sd * math.sqrt(var_factor([m - m0 for m in ms]))
    return {"F_hat": float(np.mean(yo)), "g": g, "sigma": sd, "n_drift": n, "s_theory": float(s_theory)}


def m1_forecasts(d_full: Data, origins: list[int], k: int, zero_drift: bool = False) -> pd.DataFrame:
    """M1 at each origin from its own cut; s = max(s_theory, s_track) with s_track from earlier outcomes only."""
    rows = []
    for t in origins:
        d = d_full.cut(t)
        for p in PROVS:
            r = m1_point(d, t, k, p, zero_drift)
            rows.append({"t": t, "target_q": t + k, "province_code": p, **r})
    P = pd.DataFrame(rows)
    out = []
    for t in origins:
        d = d_full.cut(t)
        F = quarter_F(d).set_index(["province_code", "q"])["F"]
        prior = P[(P["target_q"] <= t - 1)].copy()
        prior["F"] = [F.get((p, q), np.nan) for p, q in zip(prior["province_code"], prior["target_q"])]
        prior = prior.dropna(subset=["F", "F_hat"])
        s_track = (float(np.sqrt(np.mean((prior["F"] - prior["F_hat"]) ** 2)))
                   if prior["target_q"].nunique() >= 4 else np.nan)
        cur = P[P["t"] == t].copy()
        cur["s_track"] = s_track
        cur["s"] = np.fmax(cur["s_theory"], cur["s_track"].fillna(-np.inf))
        cur["p"] = 1 - norm.cdf((FPP_THRESHOLD - cur["F_hat"]) / cur["s"])
        out.append(cur)
    return pd.concat(out, ignore_index=True)


# ================================================================================================ features
def features(d: Data, t: int) -> pd.DataFrame:
    """Section 5 features for every province at O(t); d must already be d_full.cut(t)."""
    assert d.cut_t == t
    m0 = m0_of(t)
    F = quarter_F(d).set_index(["province_code", "q"])["F"]
    yo = d.yoy.set_index(["province_code", "commodity", "ym"])["yoy"]
    hq = h_quarters(d).sort_values("q")
    H_last = H_chg = H_age = np.nan
    if len(hq):
        H_last, ql = float(hq["H"].iloc[-1]), int(hq["q"].iloc[-1])
        H_age = float(t - ql)
        H_chg = float(H_last - hq["H"].iloc[-2]) if len(hq) >= 2 else np.nan
    pr = d.prod.set_index(["province_code", "series", "q"])["value"]
    lf = d.lfs.set_index(["series", "ym"])["value"]

    def qmean_lfs(s, q):
        v = [lf.get((s, q // 4 * 12 + (q % 4) * 3 + j), np.nan) for j in range(3)]
        v = [x for x in v if pd.notna(x)]
        return float(np.mean(v)) if v else np.nan

    def pyoy(p, s):
        a, b = pr.get((p, s, t - 1), np.nan), pr.get((p, s, t - 5), np.nan)
        return float(100 * (a / b - 1)) if t - 5 >= FIRST_Q and pd.notna(a) and pd.notna(b) and b > 0 else np.nan

    ur, ur4 = qmean_lfs("ur", t - 1), (qmean_lfs("ur", t - 5) if t - 5 >= FIRST_Q else np.nan)
    nw = d.news[d.news["q"] == t].set_index("province_code")
    rows = []
    for p in PROVS:
        fn = [yo.get((p, "food", m), np.nan) for m in (m0 - 1, m0)]
        hn = [yo.get((p, "all_items", m), np.nan) for m in (m0 - 1, m0)]
        F_now = float(np.mean(fn)) if all(pd.notna(fn)) else np.nan
        HL_now = float(np.mean(hn)) if all(pd.notna(hn)) else np.nan
        I = _series(d, p, "food")
        mom3 = (float(100 * (np.log(I[m0]) - np.log(I[m0 - 3])))
                if m0 in I.index and (m0 - 3) in I.index and m0 - 3 >= FIRST_YM else np.nan)
        r = {"province_code": p, "t": t, "F_last": F.get((p, t - 1), np.nan), "F_now": F_now, "HL_now": HL_now,
             "gap_now": F_now - HL_now, "mom3": mom3, "F_hat_M1": m1_point(d, t, 2, p)["F_hat"],
             "H_last": H_last, "H_chg": H_chg, "H_age": H_age,
             "palay_yoy": pyoy(p, "palay"), "corn_yoy": pyoy(p, "corn"),
             "fish_yoy": pyoy(p, "fish"), "aqua_yoy": pyoy(p, "aqua"),
             "ur_last": ur, "ur_yoy": ur - ur4, "under_last": qmean_lfs("under", t - 1)}
        if p in nw.index and nw.loc[p, "news_n"] > 0:
            r["news_n"] = float(nw.loc[p, "news_n"])
            for k in TRIGGERS:
                r[f"news_{k}"] = float(nw.loc[p, f"hits_{k}"] / nw.loc[p, "news_n"])
        else:
            r["news_n"] = float(nw.loc[p, "news_n"]) if p in nw.index else np.nan
            for k in TRIGGERS:
                r[f"news_{k}"] = np.nan
        rows.append(r)
    X = pd.DataFrame(rows)
    X["D_now"] = X["F_now"] - X["F_now"].mean()
    return X


def feature_table(d_full: Data, origins: list[int]) -> pd.DataFrame:
    return pd.concat([features(d_full.cut(t), t) for t in origins], ignore_index=True)


# ================================================================================================ M2 / M3
def training_pairs(X_all: pd.DataFrame, d_cut: Data, t: int, k: int) -> pd.DataFrame:
    """(X(t'), FPP(t'+k)) with t'+k <= t-1; labels from the origin's own cut."""
    lab = fpp_labels(d_cut)
    lab = lab[lab["q"] <= t - 1]
    tr = X_all[X_all["t"] + k <= t - 1].copy()
    tr["q"] = tr["t"] + k
    return tr.merge(lab[["province_code", "q", "y", "F"]], on=["province_code", "q"], how="inner")


def fit_predict_lr(tr: pd.DataFrame, te: pd.DataFrame) -> np.ndarray | None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    tr = tr.dropna(subset=LR_FEATURES)
    if tr["q"].nunique() < MIN_TRAIN_QUARTERS or tr["y"].nunique() < 2 or te[LR_FEATURES].isna().any().any():
        return None
    m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
    m.fit(tr[LR_FEATURES].to_numpy(float), tr["y"].to_numpy(int))
    return m.predict_proba(te[LR_FEATURES].to_numpy(float))[:, 1]


def fit_lgbm(tr: pd.DataFrame, cols: list[str]):
    from lightgbm import LGBMClassifier
    if tr["q"].nunique() < MIN_TRAIN_QUARTERS or tr["y"].nunique() < 2:
        return None
    p = tr["y"].mean()
    m = LGBMClassifier(**LGBM_PARAMS, scale_pos_weight=(1 - p) / p)
    return m.fit(tr[cols].astype(float), tr["y"].to_numpy(int))


def group_shap(model, te: pd.DataFrame, cols: list[str]) -> dict:
    c = model.booster_.predict(te[cols].astype(float), pred_contrib=True)[:, :-1]
    out = {}
    for g, fs in GROUPS.items():
        j = [cols.index(f) for f in fs if f in cols]
        out[g] = float(np.abs(c[:, j].sum(axis=1)).mean()) if j else None
    return out


# ================================================================================================ T-H
def h_forecasts(d_full: Data, origins: list[int], k: int) -> pd.DataFrame:
    rows = []
    allq = h_quarters(d_full).set_index("q")["H"]
    for t in origins:
        hq = h_quarters(d_full.cut(t)).sort_values("q")
        if not len(hq):
            continue
        rows.append({"t": t, "target_q": t + k, "H_persist": float(hq["H"].iloc[-1]),
                     "H_mean": float(hq["H"].mean()), "H": allq.get(t + k, np.nan)})
    return pd.DataFrame(rows)


# ================================================================================================ T-E40
def e40_spec() -> dict:
    s = json.loads(E40_SPEC.read_text())
    return s["thresholds"]


def e40_labels(d: Data) -> pd.DataFrame:
    """The frozen E40 rule recomputed from d (quarters with an approved round only)."""
    th = e40_spec()
    F, HL = quarter_F(d, "food"), quarter_F(d, "all_items").rename(columns={"F": "HL"})
    q = F.merge(HL, on=["province_code", "q"])
    hq = h_quarters(d).set_index("q")["H"]
    q["H"] = q["q"].map(hq)
    q = q.dropna(subset=["H"])
    q["both"] = ((q["H"] > th["H"]) & ((q["F"] > q["province_code"].map(th["food"])) |
                                       ((q["F"] - q["HL"]) > q["province_code"].map(th["gap"])))).astype(int)
    b = q.set_index(["province_code", "q"])["both"]
    q["y"] = [int(v == 1 and b.get((p, qq - 1), 0) == 1) for p, qq, v in zip(q["province_code"], q["q"], q["both"])]
    return q[["province_code", "q", "y", "both"]]


def e40_simulate(d: Data, t: int, n: int = 20000, seed: int = 41) -> dict:
    """P(E40 HIGH at t+2) per province by component simulation (PROTOCOL 4.4). d = d_full.cut(t)."""
    th = e40_spec()
    rng = np.random.default_rng(seed + t)
    hq = h_quarters(d).sort_values("q")
    if len(hq) < 5:
        return {}
    qq, hh = hq["q"].to_numpy(), hq["H"].to_numpy()
    steps = np.diff(hh) / np.sqrt(np.diff(qq))
    sig_h = float(np.sqrt(np.mean(steps ** 2)))
    ql, Hl = int(qq[-1]), float(hh[-1])
    h1, h2 = t + 1 - ql, t + 2 - ql
    e1 = rng.normal(0, sig_h * math.sqrt(h1), n)
    H1 = Hl + e1
    H2 = H1 + rng.normal(0, sig_h * math.sqrt(h2 - h1), n)
    sws = (H1 > th["H"]) & (H2 > th["H"])
    m0 = m0_of(t)
    out = {}
    for p in PROVS:
        lf, lh = np.log(_series(d, p, "food")), np.log(_series(d, p, "all_items"))
        cf = lf.diff()[(lf.index > m0 - 12) & (lf.index <= m0) & (lf.index - 1 >= FIRST_YM)].dropna()
        ch = lh.diff()[(lh.index > m0 - 12) & (lh.index <= m0) & (lh.index - 1 >= FIRST_YM)].dropna()
        j = cf.index.intersection(ch.index)
        if len(j) < 6:
            continue
        Z = np.column_stack([cf[j], ch[j]])
        mu, cov = Z.mean(axis=0), np.cov(Z.T, ddof=1)
        inc = rng.multivariate_normal(mu, cov, size=(n, 7))            # months m0+1..m0+7
        pf = lf[m0] + np.cumsum(inc[:, :, 0], axis=1)
        ph = lh[m0] + np.cumsum(inc[:, :, 1], axis=1)

        def qyoy(path, base, months):
            return np.mean([100 * (np.exp(path[:, m - m0 - 1]) / np.exp(base[m - 12]) - 1) for m in months], axis=0)

        res = {}
        for kk in (1, 2):
            ms = target_months(t, kk)
            Fq, Hq = qyoy(pf, lf, ms), qyoy(ph, lh, ms)
            res[kk] = (Fq > th["food"][p]) | ((Fq - Hq) > th["gap"][p])
        out[p] = float(np.mean(sws & res[1] & res[2]))
    return out


# ================================================================================================ scoring
def cls_metrics(y, yhat, p=None) -> dict:
    y, yhat = np.asarray(y, int), np.asarray(yhat, int)
    tp, tn = int(((yhat == 1) & (y == 1)).sum()), int(((yhat == 0) & (y == 0)).sum())
    fp, fn = int(((yhat == 1) & (y == 0)).sum()), int(((yhat == 0) & (y == 1)).sum())
    rec = tp / (tp + fn) if tp + fn else None
    spec = tn / (tn + fp) if tn + fp else None
    prec = tp / (tp + fp) if tp + fp else None
    m = {"n": int(len(y)), "positives": int(y.sum()), "prevalence": float(y.mean()) if len(y) else None,
         "TP": tp, "TN": tn, "FP": fp, "FN": fn, "accuracy": (tp + tn) / len(y) if len(y) else None,
         "precision": prec, "recall_HIGH": rec, "recall_LOW": spec,
         "f1": 2 * prec * rec / (prec + rec) if prec and rec else 0.0,
         "balanced_accuracy": (rec + spec) / 2 if rec is not None and spec is not None else None}
    if p is not None:
        p = np.asarray(p, float)
        pc = np.clip(p, 1e-3, 1 - 1e-3)
        m["brier"] = float(np.mean((p - y) ** 2))
        m["log_loss"] = float(-np.mean(y * np.log(pc) + (1 - y) * np.log(1 - pc)))
        m["mean_p"] = float(p.mean())
        m["citl"] = float(y.mean() - p.mean())
        if 0 < y.sum() < len(y) and len(np.unique(p)) > 1:
            from sklearn.metrics import average_precision_score, roc_auc_score
            m["roc_auc"] = float(roc_auc_score(y, p))
            m["pr_auc"] = float(average_precision_score(y, p))
    return m


def date_bootstrap(df: pd.DataFrame, fn, B: int = 2000, seed: int = 41) -> list[float]:
    rng = np.random.default_rng(seed)
    ds = np.array(sorted(df["target_q"].unique()))
    groups = {d: df[df["target_q"] == d] for d in ds}
    vals = []
    for _ in range(B):
        s = pd.concat([groups[d] for d in rng.choice(ds, len(ds))])
        v = fn(s)
        if v is not None and np.isfinite(v):
            vals.append(v)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if vals else [None, None]


def sign_flip(diffs: np.ndarray, seed: int = 41, draws: int = 20000) -> dict:
    """Paired per-date test of mean(diff) > 0 (one-sided) and two-sided; exact for <= 20 dates."""
    diffs = np.asarray(diffs, float)
    n, obs = len(diffs), float(np.mean(diffs))
    if n <= 20:
        signs = ((np.arange(2 ** n)[:, None] >> np.arange(n)) & 1) * 2 - 1
    else:
        signs = np.random.default_rng(seed).choice([-1, 1], size=(draws, n))
    null = (signs * diffs).mean(axis=1)
    return {"dates": n, "mean_gain": obs, "p_one_sided": float(np.mean(null >= obs - 1e-12)),
            "p_two_sided": float(np.mean(np.abs(null) >= abs(obs) - 1e-12))}


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    out, run = {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, p * (len(items) - i)))
        out[k] = run
    return out
