"""FINAL_UNIFIED_LGBM library (PROTOCOL_UNIFIED_LGBM.md): one LightGBM price model trained on the rows of every lead
(UNI-LGBM), the World Bank world-price columns, the four-area hunger LightGBM (HG), evaluation rows and baselines.

Reused unchanged: the CH1 feature rows per lead (FINAL_THESIS_OBJECTIVES ch1_lib.build_X) on the audited inputs
(FIRI_V2_DATA_AUDIT Addendum 1), labels (T43c), pi_H, same-information persistence, metrics and the reliability rule.
"""
from __future__ import annotations

import functools
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
UNI = HERE.parent
EXP = UNI.parent
OUT = UNI / "out"
DATA = UNI / "data"
sys.path.insert(0, str(EXP / "FIRI_V2_DATA_AUDIT" / "runner"))
import rerun_ch1 as R  # noqa: E402

C, FM, B, E, L, np, pd = R.C, R.FM, R.B, R.E, R.L, R.np, R.pd
SEED = 2027
H_LINE = C.H_LINE
NEWS_COLS = list(C.NEWS_COLS)
WORLD_COLS = ["W_rice_yoy", "W_rice_mom", "W_cereal_yoy", "W_crude_yoy", "W_urea_yoy"]
FAMILY_OF = {**C.FAMILY_OF, "lead": "lead", "W_rice_yoy": "A3", "W_rice_mom": "A3", "W_cereal_yoy": "A1",
             "W_crude_yoy": "A2", "W_urea_yoy": "C3"}
MONO_UP = ["A1_food", "A1_gap", "A_mom"]
VARIANTS = {"U0": dict(world=False, mono=False), "U1": dict(world=True, mono=False), "U2": dict(world=True, mono=True)}
DEV_LAST = L.qi("2024-Q4")
CONFIRM = [L.qi(q) for q in ("2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3")]


def setup():
    R._check()
    R.use_corrected()


def cols(variant: str, news: bool = True) -> list[str]:
    c = list(C.COLS) + ["lead"] + (WORLD_COLS if VARIANTS[variant]["world"] else [])
    return c if news else [x for x in c if x not in NEWS_COLS]


# ================================================================================================ world prices
@functools.lru_cache(maxsize=1)
def pinksheet() -> pd.DataFrame:
    return pd.read_csv(DATA / "pinksheet_monthly.csv").set_index("ym").sort_index()


def world_features(t: int, w: pd.DataFrame | None = None) -> dict:
    """Pink Sheet months <= m0 (month 2 of quarter t; published ~3rd business day of month 3, before O(t))."""
    w = pinksheet() if w is None else w
    m0 = L.m0_of(t)
    w = w[w.index <= m0]

    def yoy(c):
        return float(100 * (w.loc[m0, c] / w.loc[m0 - 12, c] - 1)) if m0 in w.index and m0 - 12 in w.index else np.nan
    mom = (float(100 * (math.log(w.loc[m0, "rice_thai5"]) - math.log(w.loc[m0 - 3, "rice_thai5"])))
           if m0 in w.index and m0 - 3 in w.index else np.nan)
    return {"W_rice_yoy": yoy("rice_thai5"), "W_rice_mom": mom,
            "W_cereal_yoy": float(np.nanmean([yoy("rice_thai5"), yoy("wheat_hrw"), yoy("maize")])),
            "W_crude_yoy": yoy("crude_avg"), "W_urea_yoy": yoy("urea")}


# ================================================================================================ stacked table
def stack(K: int, d=None, x=None, last_origin: int | None = None, w=None) -> pd.DataFrame:
    """CH1 rows of every lead 1..K (origins up to last_origin), with `lead` and the world columns."""
    parts = []
    for k in range(1, K + 1):
        if d is None:
            X = C.build_X(k)
        else:
            X = C.build_X(k, d, x, origins=range(E.FIRST_ORIGIN, last_origin + 1))
        if last_origin is not None:
            X = X[X["t"] <= last_origin]
        parts.append(X.assign(lead=k))
    S = pd.concat(parts, ignore_index=True)
    wf = {int(t): world_features(int(t), w) for t in S["t"].unique()}
    for c in WORLD_COLS:
        S[c] = S["t"].map(lambda t: wf[int(t)][c])
    return S


def train_rows(S: pd.DataFrame, t: int, d=None) -> pd.DataFrame:
    tr = S[(S["t"] < t) & (S["target_q"] <= t - 1)].rename(columns={"target_q": "q"})
    return tr.merge(B.known_ps(t, d), on=["province_code", "q"], how="inner")


# ================================================================================================ model
class UniPrice:
    def __init__(self, cfg: dict, cols_: list[str], mono: bool, min_child: int = 15):
        self.cfg, self.cols, self.mono, self.min_child = cfg, cols_, mono, min_child
        self.m = self.const = None

    def fit(self, tr: pd.DataFrame):
        import lightgbm as lgb
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        kw = {}
        if self.mono:
            kw["monotone_constraints"] = [1 if c in MONO_UP else 0 for c in self.cols]
            kw["monotone_constraints_method"] = "basic"
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, reg_lambda=5.0, deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=SEED, n_jobs=1,
                                    verbose=-1, max_depth=self.cfg["depth"], num_leaves=self.cfg["leaves"],
                                    n_estimators=self.cfg["trees"], class_weight=self.cfg["cw"],
                                    min_child_samples=self.min_child, **kw)
        self.m.fit(tr[self.cols].astype(float), y)
        return self

    def predict(self, te: pd.DataFrame) -> np.ndarray:
        if self.m is None:
            return np.full(len(te), self.const)
        return self.m.predict_proba(te[self.cols].astype(float))[:, 1]

    def shap(self, te: pd.DataFrame):
        return None if self.m is None else self.m.booster_.predict(te[self.cols].astype(float), pred_contrib=True)


def select(tr: pd.DataFrame, cols_: list[str], mono: bool) -> tuple[dict, dict]:
    """Inner chronological validation by origin: each of the last 4 training origins held out, fitted on rows whose
    target precedes it."""
    origins = sorted(tr["t"].unique())[-4:]
    folds = [(tr[tr["q"] <= o - 1], tr[tr["t"] == o]) for o in origins]
    folds = [(f, h) for f, h in folds if f["q"].nunique() >= 3 and f["y"].nunique() == 2 and len(h)]
    if not folds:
        return B.GRID[0], {}
    sc = {}
    for c in B.GRID:
        ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
        ps = np.concatenate([UniPrice(c, cols_, mono).fit(f).predict(h) for f, h in folds])
        p = np.clip(ps, 1e-6, 1 - 1e-6)
        sc[c["id"]] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
    return min(B.GRID, key=lambda c: (round(sc[c["id"]], 9), c["id"])), sc


def fit_predict(S: pd.DataFrame, t: int, variant: str, news: bool = True, d=None, explain: bool = False):
    """One unified model at origin t; predictions for the rows of origin t at every lead. None if not eligible."""
    tr = train_rows(S, t, d)
    te = S[S["t"] == t]
    if not B.eligible(tr) or not len(te):
        return None
    cc = cols(variant, news)
    mono = VARIANTS[variant]["mono"]
    cfg, _ = select(tr, cc, mono)
    mdl = UniPrice(cfg, cc, mono).fit(tr)
    out = te[["t", "lead", "province_code", "target_q", "H1", "h_last"]].copy()
    out["pi_price"] = mdl.predict(te)
    out["cfg"] = cfg["id"]
    if explain:
        sv = mdl.shap(te)
        if sv is not None:
            for j, c in enumerate(cc):
                out[f"shap_{c}"] = sv[:, j]
    return out


# ================================================================================================ hunger model (HG)
AREAS = ("NCR", "BL", "VIS", "MIN")


@functools.lru_cache(maxsize=1)
def _rounds() -> pd.DataFrame:
    return FM.rounds("primary")


def complete_quarters(iss: str, area: str, rounds: pd.DataFrame | None = None) -> dict[int, float]:
    """Area quarters whose every round was published before iss -> final quarter mean."""
    r = _rounds() if rounds is None else rounds
    r = r[r["area"] == area]
    return {int(q): float(g["H"].mean()) for q, g in r.groupby("q") if (g["published"] < iss).all()}


def hunger_features(t: int, k: int, area: str, rounds=None, d=None, w=None) -> dict | None:
    iss = E.issue(t)
    r = _rounds() if rounds is None else rounds
    kn = r[(r["area"] == area) & (r["published"] < iss)].groupby("q")["H"].mean().sort_index()
    if len(kn) < 2:
        return None
    dd = (E.data()[0] if d is None else d).cut(t)
    m0 = L.m0_of(t)
    fy = dd.yoy[(dd.yoy["commodity"] == "food") & (dd.yoy["ym"].isin([m0 - 1, m0]))]["yoy"]
    return {"h_last": float(kn.iloc[-1]), "h_change": float(kn.iloc[-1] - kn.iloc[-2]),
            "h_mean4": float(kn.iloc[-4:].mean()), "true_h": int(t + k - kn.index[-1]), "lead": k,
            **{f"area_{a}": int(a == area) for a in AREAS},
            "food_yoy_region": float(fy.mean()) if len(fy) else np.nan,
            "W_rice_yoy": world_features(t, w)["W_rice_yoy"]}


HG_COLS = ["h_last", "h_change", "h_mean4", "true_h", "lead"] + [f"area_{a}" for a in AREAS] + \
          ["food_yoy_region", "W_rice_yoy"]


def hunger_table(K: int, last_origin: int, rounds=None, d=None, w=None) -> pd.DataFrame:
    rows = []
    for t in range(E.FIRST_ORIGIN, last_origin + 1):
        for k in range(1, K + 1):
            for a in AREAS:
                f = hunger_features(t, k, a, rounds, d, w)
                if f is not None:
                    rows.append({"t": t, "q": t + k, "area": a, **f})
    return pd.DataFrame(rows)


def hg_predict(Hs: pd.DataFrame, t: int, rounds=None) -> pd.DataFrame | None:
    """LightGBM P(area hunger(t+k) > 11.3) at origin t for BL, trained on all four areas' rows with targets complete
    before O(t)."""
    iss = E.issue(t)
    lab = {a: complete_quarters(iss, a, rounds) for a in AREAS}
    tr = Hs[(Hs["t"] < t)].copy()
    tr["y"] = [None if q not in lab[a] else int(lab[a][q] > H_LINE) for a, q in zip(tr["area"], tr["q"])]
    tr = tr[tr["y"].notna()]
    tr["y"] = tr["y"].astype(int)
    te = Hs[(Hs["t"] == t) & (Hs["area"] == "BL")]
    if tr["y"].sum() < 5 or (1 - tr["y"]).sum() < 5 or not len(te):
        return None
    cfg, _ = select(tr.assign(t=tr["t"]), HG_COLS, False)
    mdl = UniPrice(cfg, HG_COLS, False).fit(tr)
    return te[["t", "q", "lead"]].assign(pi_h_hg=mdl.predict(te))


# ================================================================================================ evaluation rows
def baselines(D: pd.DataFrame) -> pd.DataFrame:
    """ALWAYS-LOW, PERSIST-SI and CLIM on every evaluation row (same information as the model)."""
    d, _ = E.data()
    out = []
    for t, g in D.groupby("t"):
        ps = C.persist_si(d, int(t), g["province_code"])
        lab = C.known_t43c(int(t))
        clim = float(lab["y"].mean()) if len(lab) else 0.0
        out.append(g.assign(**{"ALWAYS-LOW_p": 0.0, "CLIM_p": clim,
                               "PERSIST-SI_p": [ps[p] if not np.isnan(ps[p]) else clim for p in g["province_code"]]}))
    return pd.concat(out, ignore_index=True)
