"""E43 library (PROTOCOL.md): five-trigger as-of features, T43/L4 labels with publication-aware availability,
structural simulations (SIM-0, SIM-5T) and the GOV/NLP/COMB models. Core data, timing and scoring come from e41_lib."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E43 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E43.parent / "E41_Lead2_Audit" / "runner"))
import e41_lib as L  # noqa: E402

np, pd = L.np, L.pd
PROC = L.ROOT / "aipheed-backend-aligned" / "data" / "processed"
FSSI = L.ROOT / "backend" / "data" / "news_e31" / "fssi_v2_panel.csv"
EXTRA_FILES = {"climate": PROC / "pagasa_climate.parquet", "ofw": PROC / "bsp_macro.parquet",
               "rice": PROC / "psa_rice_prices.parquet"}
ENSO = {"EL_NINO": 1.0, "NEUTRAL": 0.0, "LA_NINA": -1.0}
GROUPS = {
    "market": ["F_last", "F_now", "gap_now", "mom3", "F_hat_M1", "D_now", "rice_whsl_yoy"],
    "climate": ["tc_count", "tc_max_signal", "tc_severe", "enso", "palay_yoy", "corn_yoy"],
    "fish_kill": ["fish_yoy", "aqua_yoy"],
    "employment": ["ur_last", "ur_yoy", "under_last"],
    "ofw_remittance": ["remit_usd_yoy", "fx_yoy"],
    "hunger_history": ["H_last", "H_chg", "H_age"],
}
NEWS = {"market": "news_market", "climate": "news_climate", "fish_kill": "news_fish_kill",
        "employment": "news_employment", "ofw_remittance": "news_ofw_remittance"}
NLP = list(NEWS.values()) + ["news_n", "fssi_v2", "fssi_admitted"]
GOV = [c for g in GROUPS.values() for c in g]
COMB = GOV + NLP
SETS = {"GOV": GOV, "NLP": NLP, "COMB": COMB}
TRIGGER_COLS = {g: GROUPS[g] + [NEWS[g]] for g in NEWS}            # for single-group / drop-group tests
LGBM = dict(objective="binary", num_leaves=4, max_depth=2, min_child_samples=5, n_estimators=100, learning_rate=0.05,
            reg_lambda=5.0, random_state=42, deterministic=True, n_jobs=1, force_row_wise=True, verbosity=-1)
MIN_TRAIN_Q, MIN_TRAIN_HIGH = 6, 5


# ================================================================================================ extra data
def assert_meta_in_window(path: Path) -> None:
    """Check parquet column statistics BEFORE loading rows: no year < 2021 (study-window rule)."""
    import pyarrow.parquet as pq
    f = pq.ParquetFile(path)
    i = f.schema_arrow.names.index("year")
    mins = [f.metadata.row_group(r).column(i).statistics.min for r in range(f.metadata.num_row_groups)]
    if min(mins) < 2021:
        raise L.WindowViolation(f"{path.name} holds pre-2021 rows; not loaded")


def load_extra() -> dict:
    out = {}
    for k, p in EXTRA_FILES.items():
        assert_meta_in_window(p)
        d = pd.read_parquet(p)
        d["q"] = d["quarter"].map(L.qi)
        L._assert_window(k, q=d["q"])
        out[k] = d
    f = pd.read_csv(FSSI, dtype={"province_code": str})
    f["q"] = f["quarter"].map(L.qi)
    L._assert_window("fssi", q=f["q"])
    out["fssi"] = f
    return out


def cut_extra(x: dict, t: int) -> dict:
    """PROTOCOL 2: typhoons and news up to t; ENSO, remittances, FX and rice up to t-1."""
    c = x["climate"]
    tc = c[c["q"] <= t][["province_code", "q", "tc_count", "tc_max_signal", "tc_severe_flag"]]
    en = c[c["q"] <= t - 1][["province_code", "q", "enso_phase"]]
    return {"tc": tc, "enso": en, "ofw": x["ofw"][x["ofw"]["q"] <= t - 1], "rice": x["rice"][x["rice"]["q"] <= t - 1],
            "fssi": x["fssi"][x["fssi"]["q"] <= t]}


# ================================================================================================ features
def features(d_full: L.Data, x_full: dict, origins: list[int]) -> pd.DataFrame:
    base = L.feature_table(d_full, origins)
    rows = []
    for t in origins:
        cx = cut_extra(x_full, t)
        tc = cx["tc"].set_index(["province_code", "q"])
        en = cx["enso"].set_index(["province_code", "q"])["enso_phase"]
        of = cx["ofw"].drop_duplicates("q").set_index("q")
        rc = cx["rice"].set_index(["province_code", "q"])["price_php_per_kg"]
        fs = cx["fssi"].set_index(["province_code", "q"])
        for p in L.PROVS:
            r = {"t": t, "province_code": p}
            if (p, t) in tc.index:
                r.update(tc_count=float(tc.loc[(p, t), "tc_count"]), tc_max_signal=float(tc.loc[(p, t), "tc_max_signal"]),
                         tc_severe=float(tc.loc[(p, t), "tc_severe_flag"]))
            r["enso"] = ENSO.get(en.get((p, t - 1)), np.nan)

            def yoy(s, a, b):
                va, vb = s.get(a, np.nan), s.get(b, np.nan)
                return float(100 * (va / vb - 1)) if pd.notna(va) and pd.notna(vb) and vb else np.nan
            r["remit_usd_yoy"] = yoy(of["ofw_cash_remit_usd_bn"], t - 1, t - 5) if t - 5 >= L.FIRST_Q else np.nan
            r["fx_yoy"] = yoy(of["fx_usd_php_avg"], t - 1, t - 5) if t - 5 >= L.FIRST_Q else np.nan
            r["rice_whsl_yoy"] = yoy(rc, (p, t - 1), (p, t - 5)) if t - 5 >= L.FIRST_Q else np.nan
            r["fssi_v2"] = fs["FSSI_v2"].get((p, t), np.nan)
            r["fssi_admitted"] = float(fs["n_admitted"].get((p, t), 0) or 0)
            rows.append(r)
    X = base.merge(pd.DataFrame(rows), on=["t", "province_code"], how="left")
    return X.drop(columns=["HL_now"])


# ================================================================================================ labels
def label_frame(d: L.Data, which: str = "T43") -> pd.DataFrame:
    """T43 (= L3: E40 signals in the quarter) or L4 (H > 11.3 and food YoY > 4) for every labelled quarter in d."""
    th = L.e40_spec()
    F, HL = L.quarter_F(d, "food"), L.quarter_F(d, "all_items").rename(columns={"F": "HL"})
    q = F.merge(HL, on=["province_code", "q"])
    q["H"] = q["q"].map(L.h_quarters(d).set_index("q")["H"])
    q = q.dropna(subset=["H"]).copy()
    sws = q["H"] > th["H"]
    if which == "T43":
        price = (q["F"] > q["province_code"].map(th["food"])) | ((q["F"] - q["HL"]) > q["province_code"].map(th["gap"]))
    else:
        price = q["F"] > 4.0
    q["y"] = (sws & price).astype(int)
    q["signals"] = sws.astype(int) + price.astype(int)
    return q[["province_code", "q", "y", "signals", "H", "F", "HL"]]


def available_labels(d_full: L.Data, t: int, which: str = "T43") -> pd.DataFrame:
    """Labels whose SWS rounds were all posted, and whose CPI quarter was complete, before O(t)."""
    c = d_full.cut(t)
    lab = label_frame(c, which)
    full_n = d_full.sws.groupby("q").size()
    cut_n = c.sws.groupby("q").size()
    complete = {q for q in cut_n.index if cut_n[q] == full_n.get(q, -1)}
    return lab[lab["q"].isin(complete) & (lab["q"] <= t - 1)]


def training_pairs(X: pd.DataFrame, d_full: L.Data, t: int, which: str = "T43", k: int = 2) -> pd.DataFrame:
    lab = available_labels(d_full, t, which)
    tr = X[X["t"] + k <= t - 1].assign(q=lambda f: f["t"] + k)
    return tr.merge(lab[["province_code", "q", "y"]], on=["province_code", "q"], how="inner")


def eligible(tr: pd.DataFrame) -> bool:
    return tr["q"].nunique() >= MIN_TRAIN_Q and tr["y"].sum() >= MIN_TRAIN_HIGH and tr["y"].nunique() == 2


# ================================================================================================ structural
def simulate(d_cut: L.Data, t: int, which: str = "T43", h_shift: float = 0.0, n: int = 20000, seed: int = 43,
             components: bool = False) -> dict:
    """P(label HIGH at t+2) per province: H random walk (+ h_shift mean change per quarter), food/headline RW+drift."""
    th = L.e40_spec()
    rng = np.random.default_rng(seed + t)
    hq = L.h_quarters(d_cut).sort_values("q")
    if len(hq) < 5:
        return {}
    qq, hh = hq["q"].to_numpy(), hq["H"].to_numpy()
    sig = float(np.sqrt(np.mean((np.diff(hh) / np.sqrt(np.diff(qq))) ** 2)))
    h = t + 2 - int(qq[-1])
    H2 = float(hh[-1]) + h_shift * h + rng.normal(0, sig * math.sqrt(h), n)
    sws = H2 > th["H"]
    m0 = L.m0_of(t)
    ms = L.target_months(t, 2)
    out = {}
    for p in L.PROVS:
        lf, lh = np.log(L._series(d_cut, p, "food")), np.log(L._series(d_cut, p, "all_items"))
        win = lambda s: s.diff()[(s.index > m0 - 12) & (s.index <= m0) & (s.index - 1 >= L.FIRST_YM)].dropna()  # noqa: E731
        cf, ch = win(lf), win(lh)
        j = cf.index.intersection(ch.index)
        if len(j) < 6 or any((m - 12) not in lf.index for m in ms):
            continue
        Z = np.column_stack([cf[j], ch[j]])
        inc = rng.multivariate_normal(Z.mean(axis=0), np.cov(Z.T, ddof=1), size=(n, 7))
        pf, ph = lf[m0] + np.cumsum(inc[:, :, 0], axis=1), lh[m0] + np.cumsum(inc[:, :, 1], axis=1)
        Fq = np.mean([100 * (np.exp(pf[:, m - m0 - 1]) / np.exp(lf[m - 12]) - 1) for m in ms], axis=0)
        Hq = np.mean([100 * (np.exp(ph[:, m - m0 - 1]) / np.exp(lh[m - 12]) - 1) for m in ms], axis=0)
        price = ((Fq > th["food"][p]) | ((Fq - Hq) > th["gap"][p])) if which == "T43" else (Fq > 4.0)
        out[p] = (float(np.mean(sws & price)) if not components else
                  {"joint": float(np.mean(sws & price)), "hunger": float(np.mean(sws)), "price": float(np.mean(price))})
    return out


H_SIGNALS = ["tc_count", "enso", "ur_yoy", "remit_usd_yoy", "fx_yoy", "F_now", "news_n"]


def h_shift_5t(X: pd.DataFrame, d_full: L.Data, t: int) -> tuple[float, dict]:
    """SIM-5T: ridge of the per-quarter H change (from origin t' to the next approved quarter) on regional trigger
    signals, fitted on pairs posted before O(t); returns the predicted per-quarter shift at t and the coefficients."""
    from sklearn.linear_model import Ridge
    reg = X.groupby("t")[H_SIGNALS].mean()
    hq = L.h_quarters(d_full.cut(t)).set_index("q")["H"]
    rows = []
    for tp in reg.index:
        if tp >= t:
            continue
        prev = hq[hq.index <= tp - 1]
        nxt = hq[(hq.index > tp - 1) & (hq.index <= tp + 2)]
        if len(prev) and len(nxt):
            q0, q1 = prev.index[-1], nxt.index[-1]
            rows.append({"t": tp, "dH": (nxt.iloc[-1] - prev.iloc[-1]) / (q1 - q0)})
    tr = pd.DataFrame(rows)
    if len(tr) < 8:
        return 0.0, {}
    Z = reg.loc[tr["t"]]
    keep = [c for c in H_SIGNALS if Z[c].notna().all() and Z[c].std() > 0 and pd.notna(reg.loc[t, c])]
    if not keep:
        return 0.0, {}
    mu, sd = Z[keep].mean(), Z[keep].std(ddof=0)
    m = Ridge(alpha=1.0).fit((Z[keep] - mu) / sd, tr["dH"])
    shift = float(m.predict(((reg.loc[[t], keep] - mu) / sd))[0])
    return shift, dict(zip(keep, map(float, m.coef_)))


# ================================================================================================ models
class LRModel:
    def __init__(self, cols):
        self.cols = cols

    def fit(self, tr):
        from sklearn.linear_model import LogisticRegression
        X = tr[self.cols].astype(float)
        self.med = X.median()
        self.miss = [c for c in self.cols if X[c].isna().any()]
        Z = self._design(X)
        self.mu, self.sd = Z.mean(), Z.std(ddof=0).replace(0, 1)
        self.keep = [c for c in Z if Z[c].std(ddof=0) > 0]
        self.m = LogisticRegression(C=0.5, class_weight="balanced", max_iter=5000).fit(
            ((Z - self.mu) / self.sd)[self.keep], tr["y"].astype(int))
        return self

    def _design(self, X):
        Z = X.fillna(self.med).fillna(0.0)
        for c in self.miss:
            Z[f"{c}__missing"] = X[c].isna().astype(float)
        return Z

    def predict(self, te):
        Z = self._design(te[self.cols].astype(float))
        return self.m.predict_proba(((Z - self.mu) / self.sd)[self.keep])[:, 1]


class GBModel:
    def __init__(self, cols):
        self.cols = cols

    def fit(self, tr):
        from lightgbm import LGBMClassifier
        p = tr["y"].mean()
        self.m = LGBMClassifier(**LGBM, scale_pos_weight=(1 - p) / p).fit(tr[self.cols].astype(float), tr["y"].astype(int))
        return self

    def predict(self, te):
        return self.m.predict_proba(te[self.cols].astype(float))[:, 1]

    def group_shap(self, te) -> dict:
        c = self.m.booster_.predict(te[self.cols].astype(float), pred_contrib=True)[:, :-1]
        out = {}
        for g, fs in {**{k: v for k, v in TRIGGER_COLS.items()}, "hunger_history": GROUPS["hunger_history"],
                      "news_totals": ["news_n", "fssi_v2", "fssi_admitted"]}.items():
            j = [self.cols.index(f) for f in fs if f in self.cols]
            out[g] = float(np.abs(c[:, j].sum(axis=1)).mean()) if j else None
        return out

    def row_shap(self, te) -> np.ndarray:
        return self.m.booster_.predict(te[self.cols].astype(float), pred_contrib=True)
