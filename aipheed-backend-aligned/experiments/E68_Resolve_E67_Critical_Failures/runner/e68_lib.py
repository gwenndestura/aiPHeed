"""E68 library (PROTOCOL.md): the E56-TUNED procedure with the pre-registered corrections
  M1  missing/stale handling (incomplete typhoon quarter -> NaN; news shares NaN when news_n < 10; stale-hunger RMSE
      widening),
  N1  provincial-only (employment and ofw_remittance removed),
  K1  El Nino projection-error shift at origins with a PAGASA El Nino status in force at issue,
  C1  M1 + K1,
and the exploratory revised target T-AFF (headline instead of the food-minus-headline gap).

E68 reads E38-E67 files and never writes into them; outputs go under E68/out, E68/tables and E68/sealed.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E68 = Path(__file__).resolve().parents[1]
EXP = E68.parent
sys.path.insert(0, str(EXP / "E67_Lead2_Best_Model_Objectives_1_4" / "runner"))
import e67_lib as K  # noqa: E402

H, G, F, L, E, P2, I7, np, pd = K.H, K.G, K.F, K.L, K.E, K.P2, K.I7, K.np, K.pd
sys.path.insert(0, str(H.BACKEND))
from app.ml.inference import climate_watch as CW  # noqa: E402

OUT, TABLES, SEALED = E68 / "out", E68 / "tables", E68 / "sealed"
EVAL_ORIGINS, FORWARD_ORIGINS = K.EVAL_ORIGINS, K.FORWARD_ORIGINS
NEWS_SHARES = ["news_market", "news_climate", "news_fish_kill", "news_employment", "news_ofw_remittance"]
NEWS_MIN = 10
INCOMPLETE_TC_QUARTERS = ["2026-Q3"]          # fetched 2026-09-09 (E56 data_freshness / E66 D-E66-5)
# T-AFF headline P60 (2021-Q1..2022-Q4, numpy.percentile, PROTOCOL section 3); recomputed and asserted in r0
HEADLINE_P60 = {"PH040100000": 5.013333, "PH040200000": 4.653333, "PH040300000": 5.060000,
                "PH040400000": 6.073333, "PH040500000": 5.546667}
ARMS = {"A0": {}, "M1": {"missing": True}, "N1": {"drop": ("employment", "ofw_remittance")},
        "K1": {"elnino": True}, "C1": {"missing": True, "elnino": True}, "TAFF": {"taff": True}}


def verify_protocol() -> str:
    want = (E68 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E68 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("E68 PROTOCOL.md changed after freezing")
    return got


def issue_date(t: int) -> str:
    return str(L.origin(t).date())


def elnino_in_force(date: str) -> bool:
    return CW.hazard(date)[0]


def elnino_quarter(q: int) -> bool:
    """A quarter belongs to an El Nino-advisory period if a PAGASA El Nino status is in force at its mid-point."""
    start = L.origin(q - 1)                       # origin(q-1) = first day of quarter q
    mid = (start + pd.Timedelta(days=45)).date()
    return elnino_in_force(str(mid))


def missing_X(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    for q in INCOMPLETE_TC_QUARTERS:
        X.loc[X["t"] == L.qi(q), "tc_count"] = np.nan
    thin = X["news_n"] < NEWS_MIN
    for c in NEWS_SHARES:
        X.loc[thin, c] = np.nan
    return X


def taff_spec() -> dict:
    th = dict(L.e40_spec())
    th["gap"] = dict(HEADLINE_P60)
    return th


def to_taff(df: pd.DataFrame) -> pd.DataFrame:
    """Replace the gap channel by headline inflation (projection, truth, distance) and the label by the T-AFF price
    condition. Called before the threshold patch, with the frozen headline P60."""
    df = df.copy()
    thF = df["province_code"].map(L.e40_spec()["food"])
    thH = df["province_code"].map(HEADLINE_P60)
    for m in P2.MULTS:
        df[f"gbase_{m}"] = df[f"hl_{m}"]
        df[f"dgap_{m}"] = df[f"hl_{m}"] - thH
    if "HL_true" in df:
        df["G_true"] = df["HL_true"]
        df["PS"] = ((df["F_true"] > thF) | (df["HL_true"] > thH)).astype(int)
    return df


def elnino_shift(tr: pd.DataFrame, te: pd.DataFrame, t: int) -> tuple[pd.DataFrame, dict]:
    """K1: shift the test projections by the province's mean projection error over earlier El Nino-period targets."""
    info = {"in_force": elnino_in_force(issue_date(t)), "n_rows": 0, "shift_food_m1": None}
    if not info["in_force"]:
        return te, info
    past = tr[tr["q"].map(elnino_quarter)]
    info["n_rows"] = int(len(past))
    if past.empty:
        return te, info
    te = te.copy()
    th = L.e40_spec()
    for m in P2.MULTS:
        eF = (past["F_true"] - past[f"base_{m}"]).groupby(past["province_code"]).mean()
        eH = (past["HL_true"] - past[f"hl_{m}"]).groupby(past["province_code"]).mean()
        te[f"base_{m}"] = te[f"base_{m}"] + te["province_code"].map(eF).fillna(0.0)
        te[f"hl_{m}"] = te[f"hl_{m}"] + te["province_code"].map(eH).fillna(0.0)
        te[f"gbase_{m}"] = te[f"base_{m}"] - te[f"hl_{m}"]
        te[f"dfood_{m}"] = te[f"base_{m}"] - te["province_code"].map(th["food"])
        te[f"dgap_{m}"] = te[f"gbase_{m}"] - te["province_code"].map(th["gap"])
        if m == 1.0:
            info["shift_food_m1"] = {L.NAMES[p]: float(v) for p, v in eF.items()}
    return te, info


def hunger(d, X, t, drop=(), widen=False):
    hc = K.hunger_cols(drop)
    htr, hte = P2.hunger_frame(X, P2.h_series(d, t, False), t, hc)
    if len(htr) < P2.MIN_H_PAIRS or not len(hte):
        return None
    out = P2.hunger_component(htr, hte, hc)
    out["widen"] = 1.0
    if widen:
        age = X.groupby("t")["H_age"].mean()
        ref = float(np.mean(2 + age.reindex(htr["t"]).to_numpy(float)))
        a_t = float(age.get(t, np.nan))
        if np.isfinite(ref) and np.isfinite(a_t) and ref > 0:
            f = float(np.sqrt(max(2 + a_t, 1e-6) / ref))
            out["widen"] = f
            out["p"] = float(1 - P2.norm.cdf((L.e40_spec()["H"] - out["H_hat"]) / max(out["rmse"] * f, 1e-6)))
    return out


def tuned_forecast(d, X, B, t, missing=False, drop=(), elnino=False, taff=False):
    from joblib import Parallel, delayed
    Xu = missing_X(X) if missing else X
    tr, te = F.frame(d, Xu, B, t, "AS")
    if not E.ok(tr, te):
        return None
    kinfo = None
    if elnino:
        te, kinfo = elnino_shift(tr, te, t)
    if taff:
        tr, te = to_taff(tr), to_taff(te)
    hc = hunger(d, Xu, t, drop, widen=missing)
    if hc is None:
        return None
    g = G.search_space()
    orig = L.e40_spec
    try:
        if taff:                                   # the bivariate offset must use the headline thresholds: serial
            spec = taff_spec()
            L.e40_spec = lambda: spec
            scores = [K._inner((tr, c, drop)) for c in g]
        else:
            scores = Parallel(n_jobs=8, backend="loky")(delayed(K._inner)((tr, c, drop)) for c in g)
        best = min(range(len(g)), key=lambda i: (round(scores[i], 10), G.simplicity(g[i])))
        c = g[best]
        fit = tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
        mdl = G.PriceLGB2(G.cols_for(c, drop), c).fit(fit)
        pp = mdl.predict(te)
    finally:
        L.e40_spec = orig
    return {"t": t, "p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"], "widen": hc["widen"], "cfg": c,
            "elnino": kinfo, "te": te, "model": mdl}


# ------------------------------------------------------------------------------------------------ labels
def labels(d) -> pd.DataFrame:
    """T43, PS, T-AFF price condition and T-AFF per province-quarter (all SWS rounds, as T43)."""
    Y = F.t43_labels(d)
    HLq = L.quarter_F(d, "all_items").rename(columns={"F": "HL_q"})
    Y = Y.merge(HLq, on=["province_code", "q"], how="left")
    thF = Y["province_code"].map(L.e40_spec()["food"])
    thH = Y["province_code"].map(HEADLINE_P60)
    Y["PS_AFF"] = ((Y["F"] > thF) | (Y["HL_q"] > thH)).astype(int)
    Y["TAFF"] = np.where(Y["H_all"].notna(), ((Y["H_all"] > L.e40_spec()["H"]) & (Y["PS_AFF"] == 1)).astype(float), np.nan)
    return Y
