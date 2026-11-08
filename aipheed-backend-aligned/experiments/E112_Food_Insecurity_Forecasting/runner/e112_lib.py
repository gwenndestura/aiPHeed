"""E112 library (PROTOCOL.md): issue-date-cut news indicators as forecast inputs, the news-only / ablation / contribution
tests, the 12-family LightGBM with and without news, the panel news ridge, warnings and false alarms.
Outcome, vintages, pairs, baselines and the reliability rule are imported unchanged from E109 / E110 / E111."""
from __future__ import annotations

import functools
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E112 = HERE.parent
sys.path.insert(0, str(E112.parent / "E111_Hunger_Forecast_Audit" / "runner"))
import e111_lib as G  # noqa: E402

E, F, H9, np, pd = G.E, G.F, G.H9, G.np, G.pd
OUT = E112 / "out"
CATS = ["price", "shortage", "disaster", "agri_supply", "jobs_income", "assistance"]
SOURCES = {"C": "news_quarterly_corpus.csv", "G": "news_quarterly_gdelt.csv"}
NEWS_COLS = {s: [f"N{s}_{c}" for c in CATS] for s in SOURCES}
LEADS = (1, 2, 3, 4)
CONTRIB_LEADS = (1, 2)
BASELINES = ["RW", "MA2", "MEAN", "SEAS", "LL"]
CANDIDATES = ["NEWS-C", "NEWS-G", "LGBM12", "LGBM12N"]
ORDER = ["LGBM12N", "LGBM12", "NEWS-C", "NEWS-G", "NEWS-CP"]          # PROTOCOL section 5
WARN = 2.0                                                              # half the +-4 BL margin (section 4.5)
OBJ4 = ["PSA-R", "RIDGE13"]                                             # ADDENDUM_1: comparison baselines only
PSA_COLS = ["A1_food", "A1_gap", "A2", "A3", "C3", "C4", "E1"]
REMOVALS = ["news"] + [f"cat:{c}" for c in CATS] + [f"fam:{f}" for f in E.FAMILIES]


# ================================================================================================ news (section 2)
@functools.lru_cache(maxsize=4)
def news_table(src: str) -> pd.DataFrame:
    t = pd.read_csv(OUT / SOURCES[src])
    t["last_published"] = pd.to_datetime(t["last_published"])
    return t.set_index("q")


@functools.lru_cache(maxsize=4096)
def _news_at(t: int, src: str) -> tuple:
    """Quarter t's YoY indicators, usable at O(t) only if every counted headline was published before O(t)."""
    tab = news_table(src)
    if t not in tab.index or tab.loc[t, "last_published"] >= pd.Timestamp(E.issue(t)):
        return tuple([np.nan] * len(CATS))
    return tuple(float(tab.loc[t, f"{c}_yoy"]) for c in CATS)


def news_at(t: int, src: str = "C") -> dict:
    return dict(zip(NEWS_COLS[src], _news_at(t, src)))


def with_news(df: pd.DataFrame, src: str = "C", col: str = "t") -> pd.DataFrame:
    if not len(df):
        return df.assign(**{c: [] for c in NEWS_COLS[src]})
    n = pd.DataFrame([news_at(int(t), src) for t in df[col]], index=df.index)
    return pd.concat([df, n], axis=1)


# ================================================================================================ BL models
def _cols(removal: str | None) -> list[str]:
    cols = E.COLUMNS + NEWS_COLS["C"]
    if removal is None:
        return cols
    if removal == "news":
        return E.COLUMNS
    kind, x = removal.split(":")
    if kind == "cat":
        return [c for c in cols if c != f"NC_{x}"]
    return [c for c in cols if c not in E.COLUMNS or E.FAMILY_OF[c] != x]


def _fit(tr: pd.DataFrame, cols, trees: int):
    return H9._lgbm(trees).fit(tr[cols].astype(float), tr["dy"].to_numpy())


def lgbm_select(tr: pd.DataFrame, k: int, cols) -> int:
    """E109 lgbm_select with a given column list: trees in {25, 75} by MAE on the last 4 training targets."""
    qv = sorted(tr["q"].unique())[-4:]
    sc = {}
    for n in (25, 75):
        errs = []
        for q in qv:
            fit, hold = tr[tr["q"] <= q - k - 1], tr[tr["q"] == q]
            if len(fit) < 4 or not len(hold):
                continue
            errs += list(np.abs(_fit(fit, cols, n).predict(hold[cols].astype(float)) - hold["dy"].to_numpy()))
        sc[n] = float(np.mean(errs)) if errs else float("inf")
    return min((25, 75), key=lambda n: (round(sc[n], 9), n))


def lgbm_forecast(t: int, k: int, cols, rule: str = "primary") -> dict | None:
    tr = with_news(H9.pairs(t, k, rule))
    if len(tr) < H9.MIN_PAIRS:
        return None
    hl = H9.h_last(t, rule)
    x = pd.concat([H9.regional_features(k).loc[t], pd.Series(news_at(t))])
    n = lgbm_select(tr, k, cols)
    m = _fit(tr, cols, n)
    xf = pd.DataFrame([x[cols].astype(float)])
    d = float(m.predict(xf)[0])
    shap = dict(zip(list(cols) + ["_base"], map(float, m.booster_.predict(xf, pred_contrib=True)[0])))
    return {"forecast": hl[1] + d, "h_last": hl[1], "h_last_quarter": E.qs(hl[0]), "trees": n, "delta": d, "shap": shap}


@functools.lru_cache(maxsize=50000)
def forecast(method: str, t: int, k: int, rule: str = "primary") -> dict | None:
    base = H9.forecast("RW", t, k, rule)
    if base is None:
        return None
    if method in BASELINES:
        return H9.forecast(method, t, k, rule)
    if method == "LGBM12":
        return H9.forecast("LGBM", t, k, rule)
    if method in ("NEWS-C", "NEWS-G"):
        src = method[-1]
        tr = with_news(H9.pairs(t, k, rule), src).rename(columns={"dy": "res"})
        f = base["h_last"] + F._ridge(tr, NEWS_COLS[src], pd.Series(news_at(t, src)))
        return {**base, "forecast": float(f)}
    if method == "RIDGE13":
        return H9.forecast("RIDGE", t, k, rule)
    if method == "PSA-R":
        tr = H9.pairs(t, k, rule).rename(columns={"dy": "res"})
        return {**base, "forecast": float(base["h_last"] + F._ridge(tr, PSA_COLS, H9.regional_features(k).loc[t]))}
    if method == "LGBM12N":
        return lgbm_forecast(t, k, _cols(None), rule)
    if method.startswith("LGBM12N-"):
        return lgbm_forecast(t, k, _cols(method[len("LGBM12N-"):]), rule)
    raise ValueError(method)


def sigma(method: str, t: int, k: int, rule: str = "primary") -> float:
    """E109 sigma: RMSE of the method's earlier lead-k errors whose target was known at O(t) (>= 4), else the SD of
    the training changes."""
    kn = dict(H9.known(E.issue(t), rule))
    errs = []
    for tp in range(E.FIRST_ORIGIN, t - k + 1):
        if tp + k in kn:
            f = forecast(method, tp, k, rule)
            if f is not None:
                errs.append(kn[tp + k] - f["forecast"])
    if len(errs) >= 4:
        return float(math.sqrt(np.mean(np.square(errs))))
    tr = H9.pairs(t, k, rule)
    return float(tr["dy"].std()) if len(tr) > 1 else 4.0


def evaluate_bl(k: int, rule: str = "primary", methods=None, with_sigma: bool = True) -> pd.DataFrame:
    methods = BASELINES + CANDIDATES if methods is None else methods
    rows = []
    for q in H9.outcome_quarters(rule):
        t = q - k
        if t < E.FIRST_ORIGIN or q > E.LAST_OUTCOME:
            continue
        rw = forecast("RW", t, k, rule)
        if rw is None:
            continue
        y = H9.outcome(q, rule)
        hq = E.qi(rw["h_last_quarter"])
        m_ = G._margin("BL", hq)
        r = {"area": "BL", "q": q, "quarter": E.qs(q), "t": t, "origin": E.qs(t), "issue_date": E.issue(t), "lead": k,
             "y": y, "h_last": rw["h_last"], "h_last_quarter": rw["h_last_quarter"], "true_horizon": q - hq,
             "margin_last": m_, "rising": int(y > rw["h_last"]),
             "change_class": "sharp_increase" if y - rw["h_last"] > m_ else ("sharp_decrease" if y - rw["h_last"] < -m_ else "stable")}
        for m in methods:
            f = forecast(m, t, k, rule)
            r[m] = f["forecast"]
            if with_sigma:
                r[f"{m}_sigma"] = sigma(m, t, k, rule)
            if m == "LGBM12N":
                sh = f["shap"]
                tot = sum(abs(v) for c, v in sh.items() if c != "_base") or 1.0
                r["LGBM12N_news_shap_share"] = sum(abs(sh[c]) for c in NEWS_COLS["C"]) / tot
                r["LGBM12N_news_shap"] = sum(sh[c] for c in NEWS_COLS["C"])
        rows.append(r)
    return pd.DataFrame(rows)


# ================================================================================================ panel news ridge
@functools.lru_cache(maxsize=512)
def panel_pairs(t: int, k: int) -> pd.DataFrame:
    rows = []
    for a in F.AREAS:
        kn = {q: h for q, h, _ in F.known(E.issue(t), a)}
        for tp in range(E.FIRST_ORIGIN, t):
            q = tp + k
            s = F.known(E.issue(tp), a)
            if q in kn and s:
                rows.append({"area": a, "t": tp, "q": q, "res": kn[q] - s[-1][1]})
    return with_news(pd.DataFrame(rows))


@functools.lru_cache(maxsize=20000)
def forecast_cp(t: int, k: int, area: str) -> float | None:
    base = G.forecast("RW", t, k, area)
    tr = panel_pairs(t, k)
    if base is None or len(tr) < H9.MIN_PAIRS:
        return None
    return float(base["h_last"] + F._ridge(tr, NEWS_COLS["C"], pd.Series(news_at(t))))


def sigma_cp(t: int, k: int, area: str) -> float:
    kn = {q: h for q, h, _ in F.known(E.issue(t), area)}
    errs = [kn[tp + k] - forecast_cp(tp, k, area) for tp in range(E.FIRST_ORIGIN, t - k + 1)
            if tp + k in kn and forecast_cp(tp, k, area) is not None]
    if len(errs) >= 4:
        return float(math.sqrt(np.mean(np.square(errs))))
    return G.sigma("RW", t, k, area)


def evaluate_panel(k: int) -> pd.DataFrame:
    df = G.evaluate_panel(k)
    if not len(df):
        return df
    df["NEWS-CP"] = [forecast_cp(int(t), k, a) for t, a in zip(df["t"], df["area"])]
    df = df[df["NEWS-CP"].notna()].copy()
    df["NEWS-CP_sigma"] = [sigma_cp(int(t), k, a) for t, a in zip(df["t"], df["area"])]
    return df.reset_index(drop=True)


# ================================================================================================ tests
def dm(df: pd.DataFrame, m: str, base: str, k: int) -> dict:
    """Section 4.3: one-sided Newey-West HLN DM on per-quarter |error| differentials (m minus base; H1: m better)."""
    d = F.quarter_diff(df, m, base)
    return {**G.dm_nw(d.to_numpy(), k), "mean_diff": float(d.mean()) if len(d) else None, "quarters": int(len(d))}


def warnings_(df: pd.DataFrame, m: str) -> dict:
    """Section 4.5: warning = forecast >= latest reading + 2.0; event = sharp increase beyond the latest margin."""
    w = (df[m] - df["h_last"]) >= WARN
    ev = df["change_class"] == "sharp_increase"
    hits, fa = int((w & ev).sum()), int((w & ~ev).sum())
    return {"warnings": int(w.sum()), "events": int(ev.sum()), "hits": hits, "false_alarms": fa, "misses": int((~w & ev).sum()),
            "hit_rate": hits / int(ev.sum()) if ev.sum() else None, "false_alarm_ratio": fa / int(w.sum()) if w.sum() else None}


def missing_shares(k: int, origins) -> dict:
    X = H9.regional_features(k)
    out = {c: float(X.loc[list(origins), c].isna().mean()) for c in E.COLUMNS}
    for s in SOURCES:
        n = pd.DataFrame([news_at(int(t), s) for t in origins])
        out.update({c: float(n[c].isna().mean()) for c in n.columns})
    return out


def _spear(x, y, alt: str) -> dict:
    from scipy.stats import spearmanr
    m = ~(np.isnan(x) | np.isnan(y))
    if m.sum() < 6:
        return {"n": int(m.sum()), "rho": None, "p": None}
    r = spearmanr(x[m], y[m], alternative=alt)
    return {"n": int(m.sum()), "rho": float(r.statistic), "p": float(r.pvalue)}


def validity() -> dict:
    """Section 4.1: concurrent validity of the news categories against independent indicator series (no hunger)."""
    X = H9.regional_features(1)
    qs_ = list(range(E.FIRST_ORIGIN, E.LAST_OUTCOME + 1))

    def ind(col, shift):
        return np.array([float(X.loc[q + shift, col]) if q + shift in X.index else np.nan for q in qs_])
    pairs_ = [("price", "share", "A2", 0), ("price", "yoy", "A3", 1), ("disaster", "share", "C2", 0),
              ("agri_supply", "yoy", "C3", 1), ("agri_supply", "yoy", "C4", 1), ("jobs_income", "yoy", "E1", 1)]
    out = {}
    for s in SOURCES:
        tab = news_table(s)
        res = {}
        for cat, kind, col, sh in pairs_:
            x = np.array([float(tab.loc[q, f"{cat}_{kind}"]) if q in tab.index else np.nan for q in qs_])
            res[f"{cat}_{kind}~{col}"] = _spear(x, ind(col, sh), "greater")
        valid = {c: any((v["p"] is not None and v["p"] < 0.05) for kk, v in res.items() if kk.startswith(c + "_"))
                 for c in ("price", "disaster", "agri_supply", "jobs_income")}
        out[s] = {"tests": res, "valid": valid}
    return out


def advance() -> dict:
    """Section 4.2: news YoY of quarter s vs the BL hunger YoY change D(s+j), j = 0, 1, 2; Holm within source."""
    H = {q: H9.outcome(q) for q in H9.outcome_quarters()}
    D = {q: H[q] - H[q - 4] for q in H if q - 4 in H}
    qs_ = list(range(E.FIRST_ORIGIN, E.LAST_OUTCOME + 1))
    out = {}
    for s in SOURCES:
        tab = news_table(s)
        tests = {}
        for c in CATS:
            x = np.array([float(tab.loc[q, f"{c}_yoy"]) if q in tab.index else np.nan for q in qs_])
            for j in (0, 1, 2):
                y = np.array([D.get(q + j, np.nan) for q in qs_])
                tests[f"{c}|j={j}"] = _spear(x, y, "two-sided" if c == "assistance" else "greater")
        hp = G.holm({kk: v["p"] for kk, v in tests.items()})
        for kk in tests:
            tests[kk]["holm_p"] = hp.get(kk)
        adv = [kk for kk, v in tests.items() if not kk.endswith("j=0") and v.get("holm_p") is not None and v["holm_p"] < 0.10
               and (v["rho"] > 0 or kk.startswith("assistance"))]
        conc = [kk for kk, v in tests.items() if kk.endswith("j=0") and v.get("holm_p") is not None and v["holm_p"] < 0.10]
        out[s] = {"tests": tests, "advance_warning": adv, "concurrent_only": conc if not adv else []}
    return out


def write_json(p, o):
    G.write_json(p, o)


def sha256(p):
    return G.sha256(p)
