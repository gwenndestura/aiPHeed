"""FINAL_ARCHITECTURE library (PROTOCOL_FINAL_ARCHITECTURE.md): the S3 single LightGBM with optional climate
representation (D), lags and changes (E) and climate interactions (F); family map for ablations.

Reused unchanged: LEAD2_ONE_MODEL one_lib (stacked table, S3 model, structural offset, inner validation).
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FA = HERE.parent
EXP = FA.parent
OUT = FA / "out"
sys.path.insert(0, str(EXP / "LEAD2_ONE_MODEL" / "runner"))
import one_lib as O  # noqa: E402

X, U, C, FM, B, E, L, np, pd = O.X, O.U, O.C, O.FM, O.B, O.E, O.L, O.np, O.pd
from app.ml.inference import climate_watch as CW  # noqa: E402
from app.ml.inference import enso_context as EC  # noqa: E402

CLIM_D = ["ONI_last", "ONI_max12", "ONI_pos12", "C1_level", "C1_dur", "C2_prev", "C2_2q", "C3_prev"]
LAG_E = ["A2_chg", "A3_chg", "E1_chg", "C4_prev", "E2_prev"]
INT_F = ["ONIpos_x_A3", "ONIpos_x_C3", "C2_2q_x_C3"]
BASE = O.cols("S3")
CANDS = {"C": BASE, "D": BASE + CLIM_D, "E": BASE + LAG_E, "F": BASE + INT_F, "G": BASE + CLIM_D + LAG_E + INT_F}
NEW_FAMILY = {"ONI_last": "C1", "ONI_max12": "C1", "ONI_pos12": "C1", "C1_level": "C1", "C1_dur": "C1",
              "C2_prev": "C2", "C2_2q": "C2", "C3_prev": "C3", "A2_chg": "A2", "A3_chg": "A3", "E1_chg": "E1",
              "C4_prev": "C4", "E2_prev": "E2", "ONIpos_x_A3": "C1", "ONIpos_x_C3": "C1", "C2_2q_x_C3": "C2",
              "O_rice_yoy": "A3", "O_food_yoy": "A1", "true_horizon": "H1", "h_last": "H1"}
FAMILY = {**{c: X.FAMILY_OF.get(c, "H1" if c.startswith(("h_", "NCR_", "VIS_", "MIN_")) else c) for c in BASE},
          **NEW_FAMILY}
GROUPS = {"Market (A1-A3)": {"A1", "A2", "A3"}, "Climate stress (C1-C4)": {"C1", "C2", "C3", "C4"},
          "Employment and remittances (E1-E2)": {"E1", "E2"}, "News (N1)": {"N1"},
          "Poverty and vulnerability (V1)": {"V1"}, "Regional hunger inputs (H1)": {"H1"}}
FAMILIES = ["A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"]


# ================================================================================================ inputs
@functools.lru_cache(maxsize=1)
def oni() -> pd.Series:
    """NOAA CPC ONI by the end month of its 3-month season (ym)."""
    o = pd.read_csv(X.LONG / "cov_oni.csv")
    return pd.Series(o["oni"].to_numpy(float), index=(o["end_year"] * 12 + o["end_month"] - 1).to_numpy()).sort_index()


def _level(issue: str, items) -> int:
    el = [s for d, s in items if d < issue and CW._el_nino_item(s)]
    if not el:
        return 0
    s = el[-1]
    if "Final" in s:
        return 0
    if s.startswith("El Nino Watch"):
        return 1
    if s.startswith("El Nino Alert"):
        return 2
    return 3


def origin_climate(t: int, o: pd.Series, items) -> dict:
    """Issue-time climate values at origin t: ONI seasons ending <= m0; PAGASA El Nino items dated before O(t)."""
    m0 = L.m0_of(t)
    w = o[(o.index <= m0) & (o.index > m0 - 12)]
    dur = 0
    tt = t
    while _level(E.issue(tt), items) >= 2:
        dur += 1
        tt -= 1
    return {"ONI_last": float(o[m0]) if m0 in o.index else np.nan,
            "ONI_max12": float(w.max()) if len(w) else np.nan,
            "ONI_pos12": float((w >= 0.5).sum()) if len(w) else np.nan,
            "C1_level": float(_level(E.issue(t), items)), "C1_dur": float(dur)}


def add_features(S: pd.DataFrame, o: pd.Series | None = None, items=None) -> pd.DataFrame:
    o = oni() if o is None else o
    items = EC.PAGASA_ENSO if items is None else items
    S = S.copy()
    clim = {int(t): origin_climate(int(t), o, items) for t in S["t"].unique()}
    for c in ("ONI_last", "ONI_max12", "ONI_pos12", "C1_level", "C1_dur"):
        S[c] = [clim[int(t)][c] for t in S["t"]]
    # previous origin's lead-independent values (published before O(t-1) < O(t))
    prev = S.drop_duplicates(["t", "province_code"]).set_index(["t", "province_code"])[["C2", "C3", "C4", "A2", "A3",
                                                                                         "E1", "E2"]]
    for c in ("C2", "C3", "C4", "A2", "A3", "E1", "E2"):
        S[f"_{c}_p"] = [prev[c].get((int(t) - 1, p), np.nan) for t, p in zip(S["t"], S["province_code"])]
    S["C2_prev"], S["C3_prev"], S["C4_prev"], S["E2_prev"] = S["_C2_p"], S["_C3_p"], S["_C4_p"], S["_E2_p"]
    S["C2_2q"] = S["C2"] + S["_C2_p"]
    for c in ("A2", "A3", "E1"):
        S[f"{c}_chg"] = S[c] - S[f"_{c}_p"]
    S = S.drop(columns=[c for c in S.columns if c.startswith("_") and c.endswith("_p")])
    pos = S["ONI_last"].clip(lower=0)
    S["ONIpos_x_A3"], S["ONIpos_x_C3"] = pos * S["A3"], pos * S["C3"]
    S["C2_2q_x_C3"] = S["C2_2q"] * S["C3"]
    return S


def build(K: int, d=None, x=None, last_origin=None, w=None, cpi=None, rice=None, o=None, items=None) -> pd.DataFrame:
    return add_features(O.build(K, d, x, last_origin, w, cpi, rice), o, items)


# ================================================================================================ model
class FOne(O.One):
    def __init__(self, cfg: dict, cols: list[str]):
        super().__init__(cfg, "S3")
        self.cols = list(cols)


def forecast(S: pd.DataFrame, t: int, cols: list[str], name: str, d=None) -> pd.DataFrame:
    """The S3 design on an explicit column list at origin t (same training rows, grid, offset and selection)."""
    lab = C.known_t43c(t, d)[["province_code", "q", "y"]]
    tr = S[(S["t"] < t) & (S["target_q"] <= t - 1)].rename(columns={"target_q": "q"}).merge(
        lab, on=["province_code", "q"], how="inner")
    pr = U.train_rows(S, t, d)
    te = S[S["t"] == t]
    out = te[["t", "lead", "province_code", "target_q"]].copy()
    if not B.eligible(tr):
        out[f"{name}_p"], out[f"{name}_cfg"] = float(tr["y"].mean()) if len(tr) else 0.0, "base-rate"
        return out
    origins = sorted(tr["t"].unique())[-4:]
    folds = [(tr[tr["q"] <= q0 - 1], tr[tr["t"] == q0], pr[pr["q"] <= q0 - 1]) for q0 in origins]
    folds = [f for f in folds if f[0]["q"].nunique() >= 3 and f[0]["y"].nunique() == 2 and len(f[1])]
    G = O.grid("S3")
    best = G[0]
    if folds:
        ys = np.concatenate([h["y"].to_numpy(int) for _, h, _ in folds])
        sc = {}
        for c in G:
            ps = np.concatenate([FOne(c, cols).fit(f, p).predict(h) for f, h, p in folds])
            sc[c["id"]] = O._ll(ys, ps)
        best = min(G, key=lambda c: (round(sc[c["id"]], 9), G.index(c)))
    m = FOne(best, cols).fit(tr, pr)
    out[f"{name}_p"], out[f"{name}_cfg"] = m.predict(te), best["id"]
    out.attrs["model"] = m
    return out


def group_cols(cols: list[str], fams: set) -> list[str]:
    return [c for c in cols if FAMILY.get(c) in fams]
