"""FINAL library (FINAL_PROTOCOL.md): one pooled LightGBM (FIL) forecasting SWS hunger by area, the ELEVATED label,
baselines, ablations, the long-history arm, metrics and the reliability rule.

Time words. Quarters qi = year*4 + quarter-1. Origin t is issued at O(t) = day 1 of quarter t+1. Lead k: target t+k.
Every feature of origin t uses data published before O(t): SWS rounds by publication date, the E107 12-family table by
its own cut-offs (E107 lib), CPI months up to month 2 of quarter t, news headlines published before O(t).
"""
from __future__ import annotations

import functools
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FINAL = HERE.parent
EXP = FINAL.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(EXP / "E109_Hunger_Forecasting" / "runner"))
import e109_lib as H9  # noqa: E402  (imports E107: the verified 12-family feature table; chdir to backend)
import news_features as NF  # noqa: E402

E, L, np, pd = H9.E, H9.E.L, H9.np, H9.pd
from scipy.stats import norm, spearmanr  # noqa: E402

DATA = FINAL / "data"
OUT = FINAL / "out"
SEED = 2026
AREAS = {"NCR": "metro_manila", "BL": "balance_luzon", "VIS": "visayas", "MIN": "mindanao"}
AREA_CODE = {a: i for i, a in enumerate(AREAS)}
LEADS = (1, 2, 3, 4)
qi, qs = L.qi, L.qs
PRIMARY_FIRST = qi("2021-Q1")
LAST_ORIGIN = qi("2026-Q3")
LAST_OUTCOME = qi("2026-Q3")
LONG_FIRST = qi("1998-Q3")
UNTOUCHED = (qi("2003-Q1"), qi("2020-Q4"))

# ================================================================================================ feature families
H_COLS = ["h_last", "h_anom", "h_chg", "h_age_q", "area", "lead"]
NEWS_COLS = ["N1"] + NF.news_cols("NC")
E107_COLS = list(E.COLUMNS)                                            # A1_food A1_gap A2 A3 V1 C1-C4 E1 E2 N1 H1
PRIMARY_COLS = H_COLS + E107_COLS + ["A_since"] + NF.news_cols("NC")
FAMILY_COLS = {                                                        # FINAL_PROTOCOL 3.2: the 12 FIRI families
    "A1": ["A1_food", "A1_gap", "A_since"], "A2": ["A2"], "A3": ["A3"], "V1": ["V1"], "C1": ["C1"], "C2": ["C2"],
    "C3": ["C3"], "C4": ["C4"], "E1": ["E1"], "E2": ["E2"], "N1": NEWS_COLS, "H1": ["H1"]}
FAMILY_NAMES = {"A1": "Food-price pressure (PSA CPI)", "A2": "Headline inflation (PSA CPI)",
                "A3": "Wholesale rice price (PSA)", "V1": "Poverty and density (PSA)", "C1": "El Nino alert (PAGASA)",
                "C2": "Typhoons within 300 km (IBTrACS)", "C3": "Palay/corn production drop (PSA)",
                "C4": "Fisheries production drop (PSA)", "E1": "Unemployment change (PSA LFS)",
                "E2": "Remittance decline (BSP)", "N1": "News signals (FSSI-v3 + dated news events)",
                "H1": "Regional hunger outlook (SWS)"}
PSA_COLS = ["A1_food", "A1_gap", "A2", "A3", "C3", "C4", "E1", "A_since"]
LONG_COLS = H_COLS + ["L_food", "L_all", "L_gap", "L_rice", "L_since", "L_oni", "L_tc", "L_palay", "L_unemp"] + \
    [f"ND_gap_{c}" for c in NF.DOC_CATS]
LONG_FAMILY = {"A1": ["L_food", "L_gap", "L_since"], "A2": ["L_all"], "A3": ["L_rice"], "C1": ["L_oni"],
               "C2": ["L_tc"], "C3": ["L_palay"], "E1": ["L_unemp"], "N1": [f"ND_gap_{c}" for c in NF.DOC_CATS]}
SMOOTH_COLS = ["ma2_anom", "ma4_anom", "kf_anom", "kf_level"]          # ADDENDUM_1 A1.2 (FIL-LONG-S)
LONG_S_COLS = LONG_COLS + SMOOTH_COLS
GRID = [(3, 100), (3, 300), (7, 100), (7, 300)]                        # (num_leaves, n_estimators)
MIN_ROWS, MIN_TQ, MIN_CLASS, MIN_FIT = 40, 6, 10, 25


# ================================================================================================ SWS rounds
def _fw_end(s: str) -> str:
    s = str(s)
    if "/" in s:
        return s.split("/")[1][:10]
    y, m = int(s[:4]), int(s[5:7])                                     # "1998-07 (month label)": month end
    return (pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0)).date().isoformat()


@functools.lru_cache(maxsize=2)
def rounds(dataset: str = "primary") -> pd.DataFrame:
    """One row per (round, area): q, H, published, fieldwork end, margin. Primary = 2021+ file only."""
    f = DATA / ("sws_area_rounds_2021.csv" if dataset == "primary" else "long/sws_area_rounds_full.csv")
    r = pd.read_csv(f)
    rows = []
    for x in r.itertuples():
        for a, col in AREAS.items():
            h = getattr(x, col)
            if pd.isna(h):
                continue
            rows.append({"area": a, "q": qi(x.quarter), "H": float(h), "published": str(x.published)[:10],
                         "fw_end": _fw_end(x.fieldwork), "moe": float(x.area_moe_bl if a == "BL" else x.area_moe_other)})
    d = pd.DataFrame(rows)
    if dataset == "primary":
        assert d["q"].min() >= PRIMARY_FIRST and d["published"].min() >= "2021-01-01", "study window violated"
    return d


@functools.lru_cache(maxsize=200000)
def known(issue: str, area: str, dataset: str = "primary") -> tuple:
    """(q, vintage mean H, latest fieldwork end, latest publication, margin) of the area's quarters published < issue."""
    r = rounds(dataset)
    r = r[(r["area"] == area) & (r["published"] < issue)]
    return tuple((int(q), float(g["H"].mean()), g["fw_end"].max(), g["published"].max(), float(g["moe"].max()))
                 for q, g in sorted(r.groupby("q"), key=lambda x: x[0]))


@functools.lru_cache(maxsize=4)
def final_values(dataset: str = "primary") -> dict:
    r = rounds(dataset)
    return {(a, int(q)): float(g["H"].mean()) for (a, q), g in r.groupby(["area", "q"])}


def outcome(area: str, q: int, dataset: str = "primary") -> float | None:
    return final_values(dataset).get((area, q))


def ref_final(area: str, q: int, dataset: str = "primary") -> float | None:
    """REF(a,q): mean of the final readings of q-4..q-1 (at least two)."""
    v = [outcome(area, x, dataset) for x in range(q - 4, q)]
    v = [x for x in v if x is not None]
    return float(np.mean(v)) if len(v) >= 2 else None


def label_final(area: str, q: int, dataset: str = "primary") -> int | None:
    y, r = outcome(area, q, dataset), ref_final(area, q, dataset)
    return None if y is None or r is None else int(y > r)


def ref_hat(kn: tuple, q: int) -> float | None:
    """REF-hat(a,q | O): known vintage values for quarters <= newest known; persistence fill after it (section 2.3)."""
    if not kn:
        return None
    d = {x[0]: x[1] for x in kn}
    q_last, h_last = kn[-1][0], kn[-1][1]
    v = []
    for x in range(q - 4, q):
        if x <= q_last:
            if x in d:
                v.append(d[x])
        else:
            v.append(h_last)
    return float(np.mean(v)) if len(v) >= 2 else None


def issue(t: int) -> str:
    return L.origin(t).date().isoformat()


# ================================================================================================ features
@functools.lru_cache(maxsize=1)
def _cpi_region() -> pd.Series:
    """CALABARZON food CPI YoY (mean of the five provinces' PSA-published YoY), by month ym."""
    d, _ = E.data()
    y = d.yoy[d.yoy["commodity"] == "food"]
    return y.groupby("ym")["yoy"].mean().sort_index()


def a_since(t: int, fw_end: str) -> float:
    s = _cpi_region()
    m0 = L.m0_of(t)
    fw = pd.Timestamp(fw_end)
    mf = fw.year * 12 + fw.month - 1
    if m0 not in s.index or mf not in s.index or mf > m0:
        return np.nan
    return float(s[m0] - s[mf])


@functools.lru_cache(maxsize=8)
def e107_table(k: int) -> pd.DataFrame:
    return H9.regional_features(k)


@functools.lru_cache(maxsize=1)
def _long_cov() -> dict:
    c = pd.read_csv(DATA / "long" / "cov_cpi.csv")
    c = c[c["geolocation"].str.contains("IV-A")]
    cpi = {k: c[c["commodity_description"] == v].set_index("ym")["yoy"].dropna()
           for k, v in (("food", "01.1 - FOOD"), ("all", "0 - ALL ITEMS"), ("rice", "01.1.1.12 - Rice"))}
    o = pd.read_csv(DATA / "long" / "cov_oni.csv")
    oni = pd.Series(o["oni"].to_numpy(), index=o["end_year"] * 12 + o["end_month"] - 1).sort_index()
    tc = pd.read_csv(DATA / "long" / "cov_ibtracs_par.csv").set_index("q")["tc_par"]
    p = pd.read_csv(DATA / "long" / "cov_palay.csv").dropna(subset=["yoy"]).set_index("q")["yoy"]
    lf = pd.read_csv(DATA / "long" / "cov_lfs.csv")
    lf = lf[lf["Month"] != "Annual"].copy()
    lf["v"] = pd.to_numeric(lf["Unemployment Rate Both sexes"], errors="coerce")
    lf["ym"] = lf["Year"].astype(int) * 12 + lf["Month"].map(L.FULL_MONTHS)
    lfs = lf.dropna(subset=["v"]).set_index("ym")["v"].sort_index()
    return {"cpi": cpi, "oni": oni, "tc": tc, "palay": p, "lfs": lfs}


def long_features(t: int, fw_end: str, iss: str) -> dict:
    """Long-history covariates at O(t) (FINAL_PROTOCOL section 7 publication rules)."""
    c = _long_cov()
    m0 = L.m0_of(t)                                       # CPI / ONI: month m usable from day 10 of m+1
    fw = pd.Timestamp(fw_end)
    mf = fw.year * 12 + fw.month - 1

    def at(s, m):
        return float(s[m]) if m in s.index else np.nan
    food, al = at(c["cpi"]["food"], m0), at(c["cpi"]["all"], m0)
    out = {"L_food": food, "L_all": al, "L_gap": food - al, "L_rice": at(c["cpi"]["rice"], m0),
           "L_since": food - at(c["cpi"]["food"], mf) if mf <= m0 else np.nan, "L_oni": at(c["oni"], m0),
           "L_tc": float(c["tc"][t]) if t in c["tc"].index else np.nan,
           "L_palay": at(c["palay"], t - 1)}
    lfs = c["lfs"]
    usable = lfs[lfs.index <= L.m0_of(t) - 1]              # LFS round m usable from day 1 of m+3
    if len(usable):
        m = int(usable.index[-1])
        prev = lfs[(lfs.index <= m - 12) & (lfs.index >= m - 14)]
        out["L_unemp"] = float(usable.iloc[-1] - prev.iloc[-1]) if len(prev) else np.nan
    else:
        out["L_unemp"] = np.nan
    out.update(dict(zip([f"ND_gap_{c_}" for c_ in NF.DOC_CATS], NF.doc_gap(fw_end, iss))))
    return out


@functools.lru_cache(maxsize=20000)
def pooled_q(iss: str, dataset: str) -> float:
    """ADDENDUM_1: level-innovation variance by moments over consecutive known quarters of all four areas."""
    vals = []
    for a in AREAS:
        s = known(iss, a, dataset)
        for x0, x1 in zip(s, s[1:]):
            r0, r1 = (x0[4] / 1.959964) ** 2, (x1[4] / 1.959964) ** 2
            vals.append(((x1[1] - x0[1]) ** 2 - r0 - r1) / (x1[0] - x0[0]))
    return max(float(np.mean(vals)) if vals else 0.25, 0.25)


def kf_filter(kn: tuple, Q: float) -> float:
    """Local-level Kalman filter with each reading's own sampling variance; filtered level at the newest quarter."""
    a, P = kn[0][1], (kn[0][4] / 1.959964) ** 2
    for x0, x1 in zip(kn, kn[1:]):
        P += Q * (x1[0] - x0[0])
        R = (x1[4] / 1.959964) ** 2
        K = P / (P + R)
        a, P = a + K * (x1[1] - a), (1 - K) * P
    return float(a)


def row_features(area: str, t: int, k: int, dataset: str = "primary", variant: str = "primary") -> dict | None:
    """Features of (area, origin t, lead k) at O(t), plus the issue-time bookkeeping. None if no SWS reading known."""
    iss = issue(t)
    kn = known(iss, area, dataset)
    if not kn:
        return None
    q = t + k
    rh = ref_hat(kn, q)
    if rh is None:
        return None
    q_last, h_last, fw_end, pub, moe = kn[-1]
    row = {"area_name": area, "t": t, "lead": k, "q": q, "issue_date": iss, "target_quarter": qs(q),
           "sws_newest_q": qs(q_last), "sws_newest_fieldwork_end": fw_end, "sws_newest_published": pub,
           "true_horizon": q - q_last, "h_age_days": (pd.Timestamp(iss) - pd.Timestamp(fw_end)).days,
           "lead_days": (L.origin(q) - pd.Timestamp(iss)).days, "margin_last": moe, "ref_hat": rh,
           "h_last": h_last, "h_anom": h_last - rh, "h_chg": h_last - kn[-2][1] if len(kn) > 1 else np.nan,
           "h_age_q": q - q_last, "area": AREA_CODE[area],
           "ma2": float(np.mean([x[1] for x in kn[-2:]]))}
    if variant in ("long", "long_s"):
        row.update(long_features(t, fw_end, iss))
        if variant == "long_s":
            kfl = kf_filter(kn, pooled_q(iss, dataset))
            row.update(ma2_anom=row["ma2"] - rh, ma4_anom=float(np.mean([x[1] for x in kn[-4:]])) - rh,
                       kf_anom=kfl - rh, kf_level=kfl)
        row["psa_newest_month"] = L.ym_s(L.m0_of(t))
        return row
    if t < PRIMARY_FIRST or t > LAST_ORIGIN:
        return None
    X = e107_table(k)
    row.update({c: float(X.loc[t, c]) if t in X.index else np.nan for c in E107_COLS})
    row["A_since"] = a_since(t, fw_end)
    v = NF.gap_features(fw_end, iss, "C")
    row.update(dict(zip(NF.news_cols("NC"), v[:7])))
    row["news_n_window"], row["news_latest_published"] = v[7], (str(v[8]) if v[8] is not None else None)
    row["psa_newest_month"] = L.ym_s(L.m0_of(t))
    return row


@functools.lru_cache(maxsize=4)
def panel(dataset: str = "primary", variant: str = "primary") -> pd.DataFrame:
    """Every (area, origin, lead) row with its features and its final outcome, label and z."""
    first = PRIMARY_FIRST if dataset == "primary" else LONG_FIRST
    rows = []
    for t in range(first, LAST_ORIGIN + 1):
        for a in AREAS:
            for k in LEADS:
                r = row_features(a, t, k, dataset, variant)
                if r is None:
                    continue
                y, lab = outcome(a, r["q"], dataset), label_final(a, r["q"], dataset)
                r.update(y=y, label=lab, z=(y - r["ref_hat"]) if y is not None else None)
                rows.append(r)
    return pd.DataFrame(rows)


# ================================================================================================ training data
def training(P: pd.DataFrame, t: int, dataset: str) -> pd.DataFrame:
    """Rows (a, t', k') whose target quarter's rounds were published before O(t): target value and label as known
    at O(t) (vintage), z from the row's own issue-time reference."""
    iss = issue(t)
    cand = P[(P["t"] < t) & (P["q"] <= t)]
    if not len(cand):
        return cand
    out = []
    for a, g in cand.groupby("area_name"):
        kn = {x[0]: x[1] for x in known(iss, a, dataset)}
        g = g[g["q"].isin(kn)].copy()
        if not len(g):
            continue
        g["y_tr"] = g["q"].map(kn)
        g["z_tr"] = g["y_tr"] - g["ref_hat"]
        ref = {q: np.mean(v) if len(v := [kn[x] for x in range(q - 4, q) if x in kn]) >= 2 else np.nan
               for q in g["q"].unique()}
        g["label_tr"] = [int(y > ref[q]) if not np.isnan(ref[q]) else np.nan for y, q in zip(g["y_tr"], g["q"])]
        out.append(g)
    return pd.concat(out) if out else cand.iloc[:0]


# ================================================================================================ LightGBM
def _lgbm(leaves: int, trees: int):
    import lightgbm as lgb
    return lgb.LGBMRegressor(objective="regression", n_estimators=trees, learning_rate=0.03, num_leaves=leaves,
                             max_depth=-1, min_child_samples=10, reg_lambda=5.0, colsample_bytree=0.8,
                             subsample=1.0, deterministic=True, force_row_wise=True, feature_pre_filter=False,
                             min_data_in_bin=3, random_state=SEED, n_jobs=1, verbose=-1)


def _X(df: pd.DataFrame, cols) -> pd.DataFrame:
    X = df[list(cols)].astype(float)
    if "area" in X:
        X["area"] = X["area"].astype("category").cat.set_categories(list(range(len(AREAS))))
    return X


def _fit(tr, cols, cfg):
    return _lgbm(*cfg).fit(_X(tr, cols), tr["z_tr"].to_numpy())


def select_config(tr: pd.DataFrame, cols) -> tuple:
    qv = sorted(tr["q"].unique())[-4:]
    score = {}
    for cfg in GRID:
        errs = []
        for v in qv:
            fit, hold = tr[tr["q"] <= v - 2], tr[tr["q"] == v]
            if len(fit) < MIN_FIT or not len(hold):
                continue
            errs += list(np.abs(_fit(fit, cols, cfg).predict(_X(hold, cols)) - hold["z_tr"].to_numpy()))
        score[cfg] = float(np.mean(errs)) if errs else float("inf")
    return min(GRID, key=lambda c: (round(score[c], 9), c[0], c[1]))


def issuable(tr: pd.DataFrame) -> bool:
    lab = tr["label_tr"].dropna()
    return (len(tr) >= MIN_ROWS and tr["q"].nunique() >= MIN_TQ and (lab == 1).sum() >= MIN_CLASS
            and (lab == 0).sum() >= MIN_CLASS)


def fil_forecasts(P: pd.DataFrame, cols, dataset: str, areas_train=None, shap: bool = False,
                  news_perm: dict | None = None, origins=None) -> pd.DataFrame:
    """Rolling origin: at each origin t fit one LightGBM on all issuable training rows, predict every lead/area."""
    out = []
    cols = list(cols)
    for t in (sorted(P["t"].unique()) if origins is None else origins):
        tr = training(P, t, dataset)
        if areas_train is not None and len(tr):
            tr = tr[tr["area_name"].isin(areas_train)]
        if not len(tr) or not issuable(tr):
            continue
        te = P[P["t"] == t]
        if news_perm is not None:
            tr, te = _permute_news(tr, news_perm), _permute_news(te, news_perm)
        cfg = select_config(tr, cols)
        m = _fit(tr, cols, cfg)
        zh = m.predict(_X(te, cols))
        res = pd.DataFrame({"area_name": te["area_name"].to_numpy(), "t": t, "lead": te["lead"].to_numpy(),
                            "zhat": zh, "leaves": cfg[0], "trees": cfg[1], "n_train": len(tr)})
        if shap:
            sv = m.booster_.predict(_X(te, cols), pred_contrib=True)
            for j, c in enumerate(cols):
                res[f"shap_{c}"] = sv[:, j]
        out.append(res)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def _permute_news(df: pd.DataFrame, perm: dict) -> pd.DataFrame:
    """Replace every row's news columns by those of origin perm[t] (whole-quarter blocks; same lead and area)."""
    df = df.copy()
    src = perm["_table"]
    cols = perm["_cols"]
    keys = list(zip(df["area_name"], df["t"].map(lambda x: perm.get(x, x)), df["lead"]))
    vals = src.reindex(keys)[cols].to_numpy()
    df[cols] = vals
    return df


# ================================================================================================ baselines
def logit_forecasts(P: pd.DataFrame, cols, dataset: str, origins) -> dict:
    """L2 logistic regression (C = 1) on standardised, median-imputed columns; area one-hot. Falls back to the
    training base rate if either class has fewer than 5 rows."""
    from sklearn.linear_model import LogisticRegression
    out = {}
    cols = [c for c in cols if c not in ("area",)]
    use_area = "area" in P.columns
    for t in origins:
        tr = training(P, t, dataset)
        tr = tr[tr["label_tr"].notna()]
        te = P[P["t"] == t]
        lab = tr["label_tr"].astype(int)
        if (lab == 1).sum() < 5 or (lab == 0).sum() < 5:
            p = np.full(len(te), lab.mean() if len(lab) else 0.5)
        else:
            A = tr[cols].astype(float)
            med = A.median().fillna(0.0)
            keep = [c for c in cols if A[c].fillna(med[c]).nunique() > 1]
            A = A[keep].fillna(med[keep])
            mu, sd = A.mean(), A.std().replace(0, 1.0)
            Z = (A - mu) / sd
            Zt = (te[keep].astype(float).fillna(med[keep]) - mu) / sd
            if use_area and "h_last" in cols:
                for i in range(1, len(AREAS)):
                    Z[f"area_{i}"] = (tr["area"] == i).astype(float).to_numpy()
                    Zt[f"area_{i}"] = (te["area"] == i).astype(float).to_numpy()
            m = LogisticRegression(C=1.0, max_iter=2000).fit(Z.to_numpy(), lab.to_numpy())
            p = m.predict_proba(Zt.to_numpy())[:, 1]
        for a, k, pp in zip(te["area_name"], te["lead"], p):
            out[(a, t, k)] = float(pp)
    return out


def maj_forecasts(P: pd.DataFrame, dataset: str, origins) -> dict:
    out = {}
    for t in origins:
        lab = training(P, t, dataset)["label_tr"].dropna()
        p = float(lab.mean()) if len(lab) else 0.5
        for a, k in zip(P.loc[P["t"] == t, "area_name"], P.loc[P["t"] == t, "lead"]):
            out[(a, t, k)] = p
    return out


def add_sigma_prob(R: pd.DataFrame, P: pd.DataFrame, zcol: str, dataset: str, train_sd: dict) -> pd.Series:
    """P = Phi(zhat / sigma); sigma = RMSE of the method's earlier same-lead z errors whose target was published
    before O(t) (>= 6), else the SD of the training z at that origin."""
    sig = {}
    for t in R["t"].unique():
        iss = issue(t)
        kn = {a: {x[0]: x[1] for x in known(iss, a, dataset)} for a in AREAS}
        prev = R[(R["t"] < t) & (R["q"] <= t)]
        yv = np.array([kn[a].get(q, np.nan) for a, q in zip(prev["area_name"], prev["q"])])
        err = yv - prev["ref_hat"].to_numpy() - prev[zcol].to_numpy()
        for k in LEADS:
            e = err[(prev["lead"].to_numpy() == k) & ~np.isnan(err)]
            sig[(t, k)] = math.sqrt(np.mean(e ** 2)) if len(e) >= 6 else train_sd.get(t, 4.0)
    s = np.array([sig[(t, k)] for t, k in zip(R["t"], R["lead"])])
    return pd.Series(norm.cdf(R[zcol].to_numpy() / np.maximum(s, 1e-6)), index=R.index)


# ================================================================================================ evaluation table
def evaluate(dataset: str = "primary", variant: str = "primary", cols=None, extra: dict | None = None,
             areas_train=None, shap: bool = True) -> pd.DataFrame:
    """Prediction-level table: FIL (given columns) and every baseline on the rows where FIL is issued."""
    P = panel(dataset, variant)
    cols = cols or (PRIMARY_COLS if variant == "primary" else LONG_COLS)
    F = fil_forecasts(P, cols, dataset, areas_train=areas_train, shap=shap)
    if not len(F):
        return P.iloc[:0]
    R = P.merge(F, on=["area_name", "t", "lead"], how="inner")
    R = R[R["y"].notna() & R["label"].notna() & (R["q"] <= LAST_OUTCOME)].reset_index(drop=True)
    sd = {t: float(training(P, t, dataset)["z_tr"].std()) for t in R["t"].unique()}
    R["FIL_level"] = R["ref_hat"] + R["zhat"]
    R["FIL_p"] = add_sigma_prob(R, P, "zhat", dataset, sd)
    R["PERSIST_z"] = R["h_anom"]
    R["PERSIST_level"] = R["h_last"]
    R["PERSIST_p"] = add_sigma_prob(R, P, "PERSIST_z", dataset, sd)
    R["MA2_z"] = R["ma2"] - R["ref_hat"]
    R["MA2_level"] = R["ma2"]
    R["MA2_p"] = add_sigma_prob(R, P, "MA2_z", dataset, sd)
    origins = sorted(R["t"].unique())
    maj = maj_forecasts(P, dataset, origins)
    R["MAJ_p"] = [maj[(a, t, k)] for a, t, k in zip(R["area_name"], R["t"], R["lead"])]
    R["ALWAYS_p"] = 1.0
    logit_sets = {"LOGIT": [c for c in cols if c != "lead"] + ["lead"]}
    if variant == "primary":
        logit_sets.update({"PSA-ONLY": PSA_COLS, "NLP-ONLY": NEWS_COLS})
    for name, lc in logit_sets.items():
        lf = logit_forecasts(P, lc, dataset, origins)
        R[f"{name}_p"] = [lf[(a, t, k)] for a, t, k in zip(R["area_name"], R["t"], R["lead"])]
    for name, (z, p) in (extra or {}).items():
        R[f"{name}_z"] = z
        R[f"{name}_p"] = p
    return R


# ================================================================================================ metrics
def _auc(y, s):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, s)) if len(set(y)) == 2 else float("nan")


def cls_metrics(y, p, score=None) -> dict:
    y = np.asarray(y, int)
    p = np.asarray(p, float)
    yh = (p > 0.5).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    tn, fn = int(((yh == 0) & (y == 0)).sum()), int(((yh == 0) & (y == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    spec = tn / (tn + fp) if tn + fp else 0.0
    return {"n": int(len(y)), "accuracy": float((yh == y).mean()), "balanced_accuracy": (rec + spec) / 2,
            "precision": prec, "recall": rec, "specificity": spec,
            "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
            "auc": _auc(y, p if score is None else score), "brier": float(np.mean((p - y) ** 2)),
            "base_rate": float(y.mean()), "tp": tp, "fp": fp, "tn": tn, "fn": fn}


def cont_metrics(y, f) -> dict:
    e = np.asarray(f, float) - np.asarray(y, float)
    return {"mae": float(np.mean(np.abs(e))), "rmse": float(np.sqrt(np.mean(e ** 2))), "bias": float(np.mean(e))}


def method_prob(R: pd.DataFrame, m: str) -> pd.Series:
    return R[f"{m}_p"]


def boot_diff(R: pd.DataFrame, a: np.ndarray, b: np.ndarray, draws: int = 2000, seed: int = SEED) -> dict:
    """Paired cluster bootstrap over target quarters of mean(a) - mean(b). p_less = P(diff >= 0) (one-sided, a
    better if smaller); p_two = two-sided."""
    rng = np.random.default_rng(seed)
    qv = R["q"].to_numpy()
    uq = np.unique(qv)
    d = np.asarray(a, float) - np.asarray(b, float)
    by = {q: d[qv == q] for q in uq}
    obs = float(d.mean())
    bs = []
    for _ in range(draws):
        pick = rng.choice(uq, size=len(uq), replace=True)
        x = np.concatenate([by[q] for q in pick])
        bs.append(x.mean())
    bs = np.asarray(bs)
    return {"diff": obs, "p_less": float(np.mean(bs >= 0)), "p_two": float(min(1.0, 2 * min(np.mean(bs >= 0),
                                                                                         np.mean(bs <= 0)))),
            "ci90": [float(np.quantile(bs, 0.05)), float(np.quantile(bs, 0.95))]}


def mcnemar(y, pa, pb) -> float:
    from scipy.stats import binomtest
    a, b = (np.asarray(pa) > 0.5) == np.asarray(y), (np.asarray(pb) > 0.5) == np.asarray(y)
    n01, n10 = int((a & ~b).sum()), int((~a & b).sum())
    return float(binomtest(n01, n01 + n10, 0.5).pvalue) if n01 + n10 else 1.0


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda x: x[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


BASES_PRIMARY = ["PERSIST", "MA2", "MAJ", "LOGIT", "PSA-ONLY", "NLP-ONLY"]
BASES_LONG = ["PERSIST", "MA2", "MAJ", "LOGIT"]


def decide(R: pd.DataFrame, k: int, model: str = "FIL", bases=None) -> dict:
    """FINAL_PROTOCOL section 6, criteria R1-R8 at lead k."""
    bases = bases or BASES_PRIMARY
    D = R[R["lead"] == k]
    if not len(D):
        return {"lead": k, "n": 0, "pass": False, "criteria": {"R1": False}}
    y = D["label"].astype(int).to_numpy()
    has_z = model == "FIL" or f"{model}_z" in D
    mz = D["zhat"] if model == "FIL" else (D[f"{model}_z"] if has_z else None)
    m = cls_metrics(y, D[f"{model}_p"], score=mz)
    bm = {b: cls_metrics(y, D[f"{b}_p"]) for b in bases + ["ALWAYS"]}
    nq = int(D["q"].nunique())
    c = {"R1": nq >= 10 and len(D) >= 30, "R2": m["accuracy"] >= 0.75}
    c["R3"] = m["balanced_accuracy"] >= 0.70 and all(m["balanced_accuracy"] > bm[b]["balanced_accuracy"] for b in bases)
    bp = (D[f"{model}_p"] - y) ** 2
    t_p = boot_diff(D, bp, (D["PERSIST_p"] - y) ** 2)
    t_m = boot_diff(D, bp, (D["MAJ_p"] - y) ** 2)
    c["R4"] = t_p["diff"] < 0 and t_m["diff"] < 0 and t_p["p_less"] < 0.10 and t_m["p_less"] < 0.10
    c["R5"] = m["precision"] >= 0.60 and m["recall"] >= 0.60
    thirds = np.array_split(np.array(sorted(D["q"].unique())), 3)
    acc3 = []
    for th in thirds:
        Dt = D[D["q"].isin(th)]
        acc3.append(float(((Dt[f"{model}_p"] > 0.5).astype(int) == Dt["label"].astype(int)).mean()) if len(Dt) else
                    float("nan"))
    c["R6"] = all(len(th) >= 3 for th in thirds) and all(a >= 0.60 for a in acc3)
    Db = D[D["area_name"] == "BL"]
    acc_bl = float(((Db[f"{model}_p"] > 0.5).astype(int) == Db["label"].astype(int)).mean()) if len(Db) else float("nan")
    c["R7"] = bool(acc_bl >= 0.70)
    mae_p = cont_metrics(D["y"], D["PERSIST_level"])["mae"]
    if has_z:
        lvl = D["FIL_level"] if model == "FIL" else D["ref_hat"] + D[f"{model}_z"]
        mae = cont_metrics(D["y"], lvl)["mae"]
    else:
        mae = float("nan")                                  # a classifier gives no level forecast
    c["R8"] = bool(mae <= mae_p)
    return {"lead": k, "model": model, "n": int(len(D)), "n_quarters": nq,
            "quarters": [qs(int(q)) for q in sorted(D["q"].unique())], "metrics": m, "baselines": bm,
            "brier_vs_persist": t_p, "brier_vs_maj": t_m, "acc_thirds": acc3,
            "thirds": [[qs(int(q)) for q in th] for th in thirds], "acc_BL": acc_bl, "n_BL": int(len(Db)),
            "mae": mae, "mae_persist": mae_p, "criteria": c, "pass": all(c.values())}


def max_reliable_lead(decisions: dict) -> int:
    k = 0
    for lead in LEADS:
        if decisions[lead]["pass"]:
            k = lead
        else:
            break
    return k


def write_json(p, o):
    import json

    def plain(x):
        if isinstance(x, dict):
            return {str(k): plain(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [plain(v) for v in x]
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, (np.floating,)):
            return None if np.isnan(x) else float(x)
        if isinstance(x, float) and math.isnan(x):
            return None
        if isinstance(x, (np.bool_,)):
            return bool(x)
        if isinstance(x, pd.Timestamp):
            return str(x)
        return x
    Path(p).write_text(json.dumps(plain(o), indent=1), encoding="utf-8")


def sha256(p) -> str:
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
