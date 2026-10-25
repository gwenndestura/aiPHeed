"""E108 library (PROTOCOL.md): the factored forecast P(T43) = H1_k x P_price,k, its candidates, baselines and the
reliability rule. Data, issue-date cuts, the 13 columns and the metric code are E107's (imported unchanged)."""
from __future__ import annotations

import itertools
import math
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
E108 = HERE.parent
E107R = E108.parent / "E107_Twelve_Indicator_LightGBM" / "runner"
sys.path.insert(0, str(E107R))
import e107_lib as E  # noqa: E402
import e107_model as M  # noqa: E402

L, np, pd = E.L, E.np, E.pd
warnings.filterwarnings("ignore", message="X does not have valid feature names")
OUT = E108 / "out"
E107_OUT = E107R.parent / "out"
SEED = 108
GRID = [dict(id=i, depth=d, leaves=2 ** d, trees=n, cw=w)
        for i, (d, n, w) in enumerate(itertools.product((1, 2), (50, 150), (None, "balanced")))]
CANDIDATES = {"F1": dict(min_child=15, prior=False), "F0": dict(min_child=5, prior=False),
              "F2": dict(min_child=15, prior=True)}
PRIMARY = "F1"
MIN_Q, MIN_HIGH, MIN_LOW = 6, 5, 5
PSA_COLS = ["A1_food", "A1_gap", "A2", "A3", "V1", "C3", "C4", "E1"]
SIGMA_FALLBACK, SIGMA_MIN_Q, CLIP = 2.0, 4, 0.01


# ================================================================================================ labels
def ps_frame(d) -> pd.DataFrame:
    """PS for every complete CPI quarter in d: food YoY > P60 or food - headline > gap P60 (E40 thresholds)."""
    th = L.e40_spec()
    F = L.quarter_F(d)
    HL = L.quarter_F(d, "all_items").rename(columns={"F": "HL"})
    q = F.merge(HL, on=["province_code", "q"])
    q["y"] = ((q["F"] > q["province_code"].map(th["food"])) |
              ((q["F"] - q["HL"]) > q["province_code"].map(th["gap"]))).astype(int)
    return q[["province_code", "q", "y", "F", "HL"]]


def known_ps(t: int, d=None) -> pd.DataFrame:
    """PS labels complete before O(t): the CPI quarter is complete in Data.cut(t) and q <= t-1."""
    p = ps_frame((E.data()[0] if d is None else d).cut(t))
    return p[p["q"] <= t - 1]


def price_rows(X: pd.DataFrame, t: int, k: int, d=None) -> pd.DataFrame:
    tr = X[(X["t"] < t) & (X["target_q"] <= t - 1)].rename(columns={"target_q": "q"})
    return tr.merge(known_ps(t, d), on=["province_code", "q"], how="inner")


def forecast_at(t: int, k: int, cand: str = PRIMARY, d=None, x=None, cols=None):
    """The candidate's forecast for every province from origin t (H1, P_price, P = H1 x P_price), using only the data
    objects given (default: the study data). None when the origin is not eligible."""
    spec = CANDIDATES[cand]
    if d is None:
        d, x = E.data()
    X = E.feature_table(k, range(E.FIRST_ORIGIN, t + 1), d, x)
    tr = price_rows(X, t, k, d)
    te = X[X["t"] == t]
    if not eligible(tr) or te["H1"].isna().any():
        return None
    cfg, _ = select(tr, k, spec["min_child"], spec["prior"], cols)
    mdl = Price(cfg, spec["min_child"], spec["prior"], cols).fit(tr)
    pp = mdl.predict(te)
    return pd.DataFrame({"province_code": te["province_code"].to_numpy(), "H1": te["H1"].to_numpy(), "price": pp,
                         "p": te["H1"].to_numpy() * pp, "cfg": cfg["id"], "n_train": len(tr),
                         "n_train_q": int(tr["q"].nunique())}), mdl


def eligible(tr: pd.DataFrame) -> bool:
    return tr["q"].nunique() >= MIN_Q and int(tr["y"].sum()) >= MIN_HIGH and int((1 - tr["y"]).sum()) >= MIN_LOW


# ================================================================================================ price part
def sigmas(fit: pd.DataFrame) -> tuple[float, float]:
    if fit["q"].nunique() < SIGMA_MIN_Q:
        return SIGMA_FALLBACK, SIGMA_FALLBACK
    th = L.e40_spec()
    ef = (fit["F"] - fit["province_code"].map(th["food"])) - fit["A1_food"]
    eg = (fit["F"] - fit["HL"] - fit["province_code"].map(th["gap"])) - fit["A1_gap"]

    def rm(e):
        e = e.dropna()
        return float(np.sqrt(np.mean(e ** 2))) if len(e) else SIGMA_FALLBACK
    return rm(ef), rm(eg)


def struct_price(rows: pd.DataFrame, sig, fill: float) -> np.ndarray:
    from scipy.stats import norm
    pf = norm.cdf(rows["A1_food"].to_numpy(float) / sig[0])
    pg = norm.cdf(rows["A1_gap"].to_numpy(float) / sig[1])
    p = 1 - (1 - pf) * (1 - pg)
    return np.where(np.isfinite(p), p, fill)


def logit(p) -> np.ndarray:
    p = np.clip(np.asarray(p, float), CLIP, 1 - CLIP)
    return np.log(p / (1 - p))


class Price:
    """LightGBM price part (PS), optionally boosted from the structural prior."""

    def __init__(self, cfg: dict, min_child: int, prior: bool, cols=None):
        self.cfg, self.min_child, self.prior = cfg, min_child, prior
        self.cols = list(E.COLUMNS if cols is None else cols)
        self.m = self.const = self.sig = self.fill = None

    def _init(self, rows):
        return logit(struct_price(rows, self.sig, self.fill)) if self.prior else None

    def fit(self, tr: pd.DataFrame):
        import lightgbm as lgb
        y = tr["y"].to_numpy(int)
        self.sig, self.fill = sigmas(tr), float(y.mean()) if len(y) else 0.5
        if len(set(y)) < 2:
            self.const = self.fill
            return self
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, reg_lambda=5.0, colsample_bytree=1.0,
                                    subsample=1.0, deterministic=True, force_row_wise=True, feature_pre_filter=False,
                                    random_state=SEED, n_jobs=1, verbose=-1, max_depth=self.cfg["depth"],
                                    num_leaves=self.cfg["leaves"], n_estimators=self.cfg["trees"],
                                    class_weight=self.cfg["cw"], min_child_samples=self.min_child)
        init = self._init(tr)
        kw = {} if init is None else {"init_score": init}
        self.m.fit(tr[self.cols].astype(float), y, **kw)
        return self

    def raw(self, te: pd.DataFrame) -> np.ndarray:
        r = self.m.predict(te[self.cols].astype(float), raw_score=True)
        init = self._init(te)
        return r if init is None else r + init

    def predict(self, te: pd.DataFrame) -> np.ndarray:
        if self.m is None:
            return np.full(len(te), self.const)
        return 1.0 / (1.0 + np.exp(-self.raw(te)))

    def shap(self, te: pd.DataFrame) -> np.ndarray | None:
        return None if self.m is None else self.m.booster_.predict(te[self.cols].astype(float), pred_contrib=True)


def select(tr: pd.DataFrame, k: int, min_child: int, prior: bool, cols=None) -> tuple[dict, dict]:
    qv = sorted(tr["q"].unique())[-4:]
    folds = [(tr[tr["q"] <= q - k - 1], tr[tr["q"] == q]) for q in qv]
    folds = [(f, h) for f, h in folds if f["q"].nunique() >= 3 and f["y"].nunique() == 2 and len(h)]
    if not folds:
        return GRID[0], {}
    sc = {}
    for c in GRID:
        ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
        ps = np.concatenate([Price(c, min_child, prior, cols).fit(f).predict(h) for f, h in folds])
        sc[c["id"]] = M.logloss(ys, ps)
    return min(GRID, key=lambda c: (round(sc[c["id"]], 9), c["id"])), sc


# ================================================================================================ one lead
def run(k: int, cands=None, cols=None, X=None, obs=None, quarters=None, explain=False, baselines=True):
    """Rolling-origin forecasts of T43 at lead k for every candidate (identical rows). Returns (rows, records)."""
    cands = CANDIDATES if cands is None else cands
    X = E.feature_table(k) if X is None else X
    obs = E.outcomes("T43") if obs is None else obs
    obs = obs[obs["q"] <= E.LAST_OUTCOME]
    psall = ps_frame(E.data()[0])
    rows, recs = [], []
    for q in sorted(obs["q"].unique()) if quarters is None else sorted(quarters):
        t = q - k
        if t < E.FIRST_ORIGIN:
            continue
        tr = price_rows(X, t, k)
        te = X[X["t"] == t].merge(obs[obs["q"] == q][["province_code", "y"]], on="province_code")
        if not eligible(tr) or not len(te) or te["H1"].isna().any():
            continue
        out = te[["t", "province_code", "y", "H1"]].copy().assign(lead=k, q=q, issue_date=E.issue(t))
        out["PS_y"] = out["province_code"].map(psall[psall["q"] == q].set_index("province_code")["y"])
        out["hunger_elevated"] = int(obs.loc[obs["q"] == q, "H"].iloc[0] > E.HUNGER_LINE)
        rec = {"lead": k, "t": t, "q": q, "n_train": len(tr), "n_train_q": int(tr["q"].nunique()),
               "n_train_high": int(tr["y"].sum()), "cand": {}}
        for name, spec in cands.items():
            cfg, sc = select(tr, k, spec["min_child"], spec["prior"], cols)
            mdl = Price(cfg, spec["min_child"], spec["prior"], cols).fit(tr)
            pp = mdl.predict(te)
            out[f"{name}_price"], out[f"{name}_p"], out[f"{name}_cfg"] = pp, te["H1"].to_numpy() * pp, cfg["id"]
            r = {"cfg": cfg["id"], "inner_logloss": sc}
            if explain:
                sv = mdl.shap(te)
                r["shap"] = None if sv is None else {p: dict(zip(mdl.cols + ["_base"], map(float, v)))
                                                     for p, v in zip(te["province_code"], sv)}
            rec["cand"][name] = r
        if baselines:
            lab = E.known_labels(t, "T43")
            clim = float(lab["y"].mean()) if len(lab) else 0.0
            out["CLIM_p"] = clim
            per = E.persistence(t, "T43")
            out["PERSIST_p"] = [float(per[p][0]) if p in per else clim for p in out["province_code"]]
            sig, fill = sigmas(tr), float(tr["y"].mean())
            out["STRUCT_price"] = struct_price(te, sig, fill)
            out["STRUCT_p"] = te["H1"].to_numpy() * out["STRUCT_price"].to_numpy()
            for name, cc, fl in (("PSA_LR", PSA_COLS, False), ("NLP_LR", ["N1"], True), ("LR12", E.COLUMNS, True)):
                v = M.logistic(tr, te, cc, fl)
                out[f"{name}_p"] = te["H1"].to_numpy() * (fill if v is None else v)
        rows.append(out)
        recs.append(rec)
    df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if baselines and len(df):
        df = attach(df, k)
    return df, recs


def attach(df: pd.DataFrame, k: int) -> pd.DataFrame:
    s = M.e63()
    s = s[s["lead"] == k].set_index(["q", "province_code"])["E56_p"]
    df["E56_p"] = [s.get((q, p), np.nan) for q, p in zip(df["q"], df["province_code"])]
    f = M.firi()
    f = f[(f["q"] - f["t"]) == k].set_index(["q", "province_code"]) if k == 2 else None
    df["FIRI_score"] = np.nan if f is None else [f["FIRI"].get((q, p), np.nan) for q, p in zip(df["q"], df["province_code"])]
    e7 = E107_OUT / f"predictions_T43_lead{k}.csv"
    if e7.exists() and e7.stat().st_size > 5:
        e = pd.read_csv(e7, dtype={"province_code": str}).set_index(["q", "province_code"])["p"]
        df["E107_p"] = [e.get((q, p), np.nan) for q, p in zip(df["q"], df["province_code"])]
    else:
        df["E107_p"] = np.nan
    return df


# ================================================================================================ rule (PROTOCOL 7)
def _m(df, col):
    return M.metrics(df["y"], df[col])


def decide(df: pd.DataFrame, col: str) -> dict:
    if not len(df):
        return {"class": "inconclusive", "reliable": False, "reason": "no evaluable rows", "criteria": {}}
    m, nq = _m(df, col), int(df["q"].nunique())
    base = {a: _m(df, a) for a in ("PERSIST_p", "CLIM_p")}
    low = min(base, key=lambda a: base[a]["brier"])
    pt = M.paired(df, col, low)
    both = 0 < df["y"].sum() < len(df)
    c = {"R1": nq >= 6, "R2": m["accuracy"] >= 0.75,
         "R3": m["accuracy"] > base["PERSIST_p"]["accuracy"] and m["accuracy"] > base["CLIM_p"]["accuracy"],
         "R4": all(m["brier"] < base[a]["brier"] for a in base) and pt["signflip_p_one_sided"] < 0.10,
         "R5": bool(both and m["recall_high"] is not None and m["recall_low"] is not None
                    and m["recall_high"] >= 0.5 and m["recall_low"] >= 0.5),
         "R6": bool(both and m["auc"] is not None and m["auc"] >= 0.65),
         "R7": 0.1 <= m["share_pred_high"] <= 0.9}
    pq = M.per_quarter(df, col)
    c["G1"] = float((pq["accuracy"] >= 0.6).mean()) >= 2 / 3
    qs_ = sorted(df["q"].unique())
    h = (len(qs_) + 1) // 2
    halves = []
    for part in (qs_[:h], qs_[h:]):
        d = df[df["q"].isin(part)]
        halves.append(bool(len(d)) and _m(d, col)["brier"] < min(_m(d, a)["brier"] for a in base))
    c["G2"] = all(halves)
    fb = df[df["q"].isin(E.FINAL_BLOCK)]
    c["G3"] = bool(len(fb)) and (_m(fb, col)["accuracy"] >= max(_m(fb, a)["accuracy"] for a in base)
                                 and _m(fb, col)["brier"] <= min(_m(fb, a)["brier"] for a in base))
    he = df[df["hunger_elevated"] == 1]
    if len(he) and 0 < he["y"].sum() < len(he):
        mh = _m(he, col)
        c["G4"] = bool(mh["accuracy"] >= 0.75 and mh["recall_high"] >= 0.5 and mh["recall_low"] >= 0.5
                       and all(mh["brier"] < _m(he, a)["brier"] for a in base))
    else:
        c["G4"] = False
    fails = [k for k, v in c.items() if not v]
    point_ok = all(c[k] for k in ("R2", "R3", "R5", "R6", "R7", "G1", "G4"))
    if not fails:
        cls = "reliable"
    elif not c["R1"] or not both or (point_ok and set(fails) <= {"R4", "G2", "G3"}):
        cls = "inconclusive"
    else:
        cls = "not reliable"
    return {"class": cls, "reliable": not fails, "criteria": c, "failed": fails, "accuracy": m["accuracy"],
            "meets_75": c["R2"], "lowest_baseline": low, "paired_vs_lowest": pt, "n_quarters": nq, "n_rows": len(df),
            "hunger_elevated_quarters": int(he["q"].nunique()) if len(he) else 0}


def max_reliable(dec: dict) -> int | None:
    best = None
    for k in E.LEADS:
        if dec[str(k)]["reliable"]:
            best = k
        else:
            break
    return best


def summary(df: pd.DataFrame, col: str) -> dict:
    if not len(df) or col not in df or df[col].isna().all():
        return {"n": 0}
    d = df.dropna(subset=[col])
    m = M.metrics(d["y"], d[col], quarters=d["q"])
    cf = m["confusion"]
    m["false_alarm_rate"] = cf["fp"] / (cf["fp"] + cf["tn"]) if cf["fp"] + cf["tn"] else None
    m["missed_high_rate"] = cf["fn"] / (cf["fn"] + cf["tp"]) if cf["fn"] + cf["tp"] else None
    m["accuracy_cluster95"] = M.cluster_ci(d, col)
    m["reliability_table"] = M.reliability_table(d["y"], d[col])
    m["within_quarter_sd"] = float(d.groupby("q")[col].std().mean())
    m["rows_compared"] = len(d)
    return m


def onsets(df: pd.DataFrame, col: str) -> list[dict]:
    """Quarters where T43 HIGH appears after an evaluated quarter with none; did the forecast flag any province?"""
    g = df.groupby("q")
    qs_ = sorted(g.groups)
    out = []
    for a, b in zip(qs_, qs_[1:]):
        if g.get_group(a)["y"].sum() == 0 and g.get_group(b)["y"].sum() > 0:
            gb = g.get_group(b)
            out.append({"quarter": E.qs(int(b)), "high_provinces": int(gb["y"].sum()),
                        "flagged_high": int((gb[col] >= 0.5).sum()),
                        "flagged_correctly": int(((gb[col] >= 0.5) & (gb["y"] == 1)).sum())})
    return out


# ================================================================================================ regional (PROTOCOL 8)
def regional(k: int) -> pd.DataFrame:
    """One row per outcome quarter: H1, persistence, climatology and level forecasts, with E107's regional LGBM."""
    obs = E.r_frame(E.data()[0])
    rows = []
    for q, y, h in zip(obs["q"], obs["y"], obs["H"]):
        t = q - k
        if t < E.FIRST_ORIGIN or q > E.LAST_OUTCOME:
            continue
        hs = E.TS._posted(E.issue(t))
        if len(hs) < 6:
            continue
        flags = [v > E.HUNGER_LINE for v in hs.values()]
        if sum(flags) < 2 or len(flags) - sum(flags) < 2:
            continue
        vals = list(hs.values())
        rh = E.TS.regional_hunger(t, k)
        rows.append({"q": q, "t": t, "lead": k, "y": int(y), "H": float(h), "H1_p": rh["probabilityAbove11_3"],
                     "PERSIST_p": float(vals[-1] > E.HUNGER_LINE), "CLIM_p": float(np.mean(flags)),
                     "RW_level": vals[-1], "MA2_level": float(np.mean(vals[-2:])), "MEAN_level": float(np.mean(vals)),
                     "province_code": "REGION"})
    df = pd.DataFrame(rows)
    f = E107_OUT / f"predictions_R_lead{k}.csv"
    if len(df) and f.exists() and f.stat().st_size > 5:
        e = pd.read_csv(f).set_index("q")["p"]
        df["E107_R_p"] = df["q"].map(e)
    return df


def write_csv(path, df):
    M.write_csv(path, df)


def sha256(p) -> str:
    return E.sha256(p)


def write_json(p, o):
    E.write_json(p, o)


def qs(i):
    return E.qs(i)


__all__ = ["E", "M", "run", "decide", "summary", "regional", "math"]
