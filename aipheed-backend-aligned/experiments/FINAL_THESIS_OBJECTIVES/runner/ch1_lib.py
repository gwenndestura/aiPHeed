"""FINAL_THESIS_OBJECTIVES library (FINAL_TARGET_AND_EVALUATION_PROTOCOL.md): the Chapter I province-quarter risk
class on the corrected SWS series (T43c), the factored 12-family LightGBM CH1-LGBM = pi_H x pi_P, same-information
baselines, the Chapter I comparators, metrics and the reliability rule.

Reused unchanged: E107 feature table (12 families, issue-date cut-offs), E108 price model (`Price`, `select`,
`sigmas`, `struct_price`, `ps_frame`, `price_rows`), FINAL's verified SWS series and metric helpers.
"""
from __future__ import annotations

import functools
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CH1 = HERE.parent
EXP = CH1.parent
sys.path.insert(0, str(EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM" / "runner"))
sys.path.insert(0, str(EXP / "E108_Best_Defensible_Forecasting" / "runner"))
import fi_lib as FM  # noqa: E402  (verified SWS series, metrics; imports E107 via E109)
import e108_lib as B  # noqa: E402  (price model; imports the same e107_lib module)
import news_features as NF  # noqa: E402

E, L, np, pd = B.E, B.L, B.np, B.pd
from scipy.stats import norm  # noqa: E402

OUT = CH1 / "out"
SEED = 2026
LEADS = (0, 1, 2, 3, 4)
FORECAST_LEADS = (1, 2, 3, 4)
H_LINE = 11.3
SIGMA_H_FALLBACK = 4.0
SPEC = dict(min_child=15, prior=False)                      # E108 F1
NEWS_NEW = ["G_pri_yoy", "NG_gap_price"]
COLS = list(E.COLUMNS) + ["A_mom"] + NEWS_NEW              # 12 families: E107 13 columns (H1 corrected) + A_mom + news
NEWS_COLS = ["N1"] + NEWS_NEW
GOV_COLS = [c for c in COLS if c not in NEWS_COLS]
FAMILY_OF = {**{c: E.FAMILY_OF[c] for c in E.COLUMNS}, "A_mom": "A1", "G_pri_yoy": "N1", "NG_gap_price": "N1"}
PROV_NAME = L.NAMES
E113_G = EXP / "E113_Final_Model" / "out" / "news_composites_G.csv"


# ================================================================================================ outcome (section 2)
@functools.lru_cache(maxsize=1)
def bl_quarters() -> pd.Series:
    """Balance Luzon hunger per quarter, mean of the non-commissioned rounds (verified series)."""
    r = FM.rounds("primary")
    return r[r["area"] == "BL"].groupby("q")["H"].mean().sort_index()


def bl_known(iss: str) -> tuple:
    return FM.known(iss, "BL", "primary")


@functools.lru_cache(maxsize=1)
def labels() -> pd.DataFrame:
    """T43c for every province-quarter with a non-commissioned SWS round and a complete CPI quarter."""
    ps = B.ps_frame(E.data()[0])
    h = bl_quarters()
    o = ps[ps["q"].isin(h.index)].copy()
    o["H"] = o["q"].map(h)
    o["price"] = o["y"]
    o["hunger"] = (o["H"] > H_LINE).astype(int)
    o["y"] = (o["hunger"] & o["price"]).astype(int)
    return o[["province_code", "q", "y", "price", "hunger", "H", "F", "HL"]].reset_index(drop=True)


def known_t43c(t: int, d=None) -> pd.DataFrame:
    """T43c labels known before O(t): every SWS round of q published, CPI quarter complete, q <= t-1."""
    iss = E.issue(t)
    full = FM.rounds("primary")
    full = full[full["area"] == "BL"]
    done = {q for q, g in full.groupby("q") if (g["published"] < iss).all()}
    ps = B.known_ps(t, d)
    lab = ps[ps["q"].isin(done)].copy()
    lab["H"] = lab["q"].map(bl_quarters())
    lab["y"] = ((lab["H"] > H_LINE) & (lab["y"] == 1)).astype(int)
    return lab


# ================================================================================================ features (section 4)
def pi_h(t: int, k: int) -> tuple[float, dict]:
    """P(H_BL(t+k) > 11.3 | readings published before O(t)) from the latest reading and the RMSE of earlier
    latest-reading errors at the same true horizon."""
    kn = bl_known(E.issue(t))
    if not kn:
        return float("nan"), {}
    q_last, h_last = kn[-1][0], kn[-1][1]
    h = (t + k) - q_last
    d = {x[0]: x[1] for x in kn}
    errs = [d[q + h] - d[q] for q in d if q + h in d]
    sig = math.sqrt(np.mean(np.square(errs))) if len(errs) >= 4 else SIGMA_H_FALLBACK
    return float(norm.cdf((h_last - H_LINE) / max(sig, 0.5))), {
        "sws_newest_q": L.qs(q_last), "sws_newest_published": kn[-1][3], "sws_newest_fieldwork_end": kn[-1][2],
        "h_last": h_last, "true_horizon": h, "sigma_h": sig}


@functools.lru_cache(maxsize=1)
def _g_news() -> pd.DataFrame:
    g = pd.read_csv(E113_G, encoding="utf-8-sig")
    g["last_published"] = pd.to_datetime(g["last_published"])
    return g.set_index("q")


def _a_mom(d, p: str, t: int) -> float:
    m0 = L.m0_of(t)
    s = d.idx[(d.idx["province_code"] == p) & (d.idx["commodity"] == "food")].set_index("ym")["index"]
    if m0 in s.index and (m0 - 3) in s.index:
        return float(100 * (math.log(s[m0]) - math.log(s[m0 - 3])))
    return float("nan")


def build_X(k: int, d=None, x=None, origins=None) -> pd.DataFrame:
    """E107's 13 columns at lead k (H1 replaced by the corrected pi_H) plus A_mom and the two news columns, with the
    per-row date bookkeeping."""
    if d is None:
        d, x = E.data()
        X = E.feature_table(k)
    else:
        X = E.feature_table(k, origins if origins is not None else range(E.FIRST_ORIGIN, E.LAST_ORIGIN + 1), d, x)
    X = X.copy()
    g = _g_news()
    extra = {}
    for t in X["t"].unique():
        ph, info = pi_h(int(t), k)
        iss = E.issue(int(t))
        gp = float(g.loc[t, "pri_yoy"]) if t in g.index and g.loc[t, "last_published"] < pd.Timestamp(iss) else np.nan
        ng = (NF.gap_features(info["sws_newest_fieldwork_end"], iss, "G")
              if info else tuple([np.nan] * 9))
        extra[int(t)] = {"H1": ph, "G_pri_yoy": gp, "NG_gap_price": ng[0],
                         "news_latest_published": str(ng[8]) if ng[8] is not None else None,
                         "psa_newest_month": L.ym_s(L.m0_of(int(t))), **info}
    for c in ("H1", "G_pri_yoy", "NG_gap_price", "news_latest_published", "psa_newest_month", "sws_newest_q",
              "sws_newest_published", "true_horizon", "h_last"):
        X[c] = [extra[int(t)].get(c) for t in X["t"]]
    X["A_mom"] = [_a_mom(d.cut(int(t)), p, int(t)) for p, t in zip(X["province_code"], X["t"])]
    X["issue_date"] = [E.issue(int(t)) for t in X["t"]]
    X["lead_days"] = [(L.origin(int(t) + k).date() - L.origin(int(t)).date()).days for t in X["t"]]
    return X


# ================================================================================================ baselines (section 5)
def persist_si(d, t: int, provs) -> dict:
    """Same-information persistence: hunger condition on the newest SWS reading AND price condition on the newest
    three published CPI months."""
    th = L.e40_spec()
    kn = bl_known(E.issue(t))
    hung = bool(kn) and kn[-1][1] > H_LINE
    c = d.cut(t)
    m0 = L.m0_of(t)
    y = c.yoy[c.yoy["ym"].isin([m0 - 2, m0 - 1, m0])]
    out = {}
    for p in provs:
        f = y[(y["province_code"] == p) & (y["commodity"] == "food")]["yoy"]
        a = y[(y["province_code"] == p) & (y["commodity"] == "all_items")]["yoy"]
        if len(f) < 3 or len(a) < 3:
            out[p] = np.nan
            continue
        price = f.mean() > th["food"][p] or (f.mean() - a.mean()) > th["gap"][p]
        out[p] = float(hung and price)
    return out


def _logit(tr, te, cols):
    v = B.M.logistic(tr, te, cols, True)
    return np.full(len(te), float(tr["y"].mean())) if v is None else np.asarray(v, float)


def _price(tr, te, cols, k):
    cfg, _ = B.select(tr, k, SPEC["min_child"], SPEC["prior"], cols)
    mdl = B.Price(cfg, SPEC["min_child"], SPEC["prior"], cols).fit(tr)
    return mdl.predict(te), mdl, cfg


# ================================================================================================ one lead
def run_lead(k: int, X: pd.DataFrame | None = None, news_perm: dict | None = None, light: bool = False) -> pd.DataFrame:
    """Rolling-origin forecasts of T43c at lead k for CH1-LGBM and every comparator, on identical rows."""
    d, _ = E.data()
    X = build_X(k) if X is None else X
    obs = labels()
    obs = obs[obs["q"] <= E.LAST_OUTCOME]
    rows = []
    for q in sorted(obs["q"].unique()):
        t = q - k
        if t < E.FIRST_ORIGIN:
            continue
        Xu = X if news_perm is None else _permute(X, news_perm)
        tr = B.price_rows(Xu, t, k)
        te = Xu[Xu["t"] == t].merge(obs[obs["q"] == q][["province_code", "y", "price", "hunger", "H"]],
                                    on="province_code")
        if not B.eligible(tr) or not len(te) or te["H1"].isna().any():
            continue
        ph = te["H1"].to_numpy(float)
        out = te[["t", "province_code", "y", "price", "hunger", "H", "H1", "issue_date", "lead_days", "sws_newest_q",
                  "sws_newest_published", "psa_newest_month", "news_latest_published", "true_horizon",
                  "h_last"]].copy().assign(lead=k, q=q, target_quarter=L.qs(q))
        pp, mdl, cfg = _price(tr, te, COLS, k)
        out["CH1_price"], out["CH1_p"], out["CH1_cfg"] = pp, ph * pp, cfg["id"]
        if not light:
            sv = mdl.shap(te)
            if sv is not None:
                for j, c in enumerate(COLS):
                    out[f"shap_{c}"] = sv[:, j]
            gp, _, _ = _price(tr, te, GOV_COLS, k)
            out["LGBM-GOV_p"] = ph * gp
            npp, _, _ = _price(tr, te, NEWS_COLS, k)
            out["LGBM-NLP_p"] = ph * npp
            for name, cc in (("LR-COMB", COLS), ("LR-GOV", GOV_COLS), ("LR-NLP", NEWS_COLS)):
                out[f"{name}_p"] = ph * _logit(tr, te, cc)
            sig, fill = B.sigmas(tr), float(tr["y"].mean())
            out["STRUCT_p"] = ph * B.struct_price(te, sig, fill)
            lab = known_t43c(t)
            clim = float(lab["y"].mean()) if len(lab) else 0.0
            out["CLIM_p"] = clim
            out["ALWAYS-LOW_p"] = 0.0
            ps = persist_si(d, t, te["province_code"])
            out["PERSIST-SI_p"] = [ps[p] if not np.isnan(ps[p]) else clim for p in te["province_code"]]
            # diagnostic: one LightGBM trained directly on T43c
            trd = Xu[(Xu["t"] < t) & (Xu["target_q"] <= t - 1)].rename(columns={"target_q": "q"}).merge(
                lab[["province_code", "q", "y", "F", "HL"]], on=["province_code", "q"], how="inner")
            if B.eligible(trd):
                pd_, _, _ = _price(trd, te, COLS, k)
                out["CH1-DIRECT_p"] = pd_
            else:
                out["CH1-DIRECT_p"] = clim
        rows.append(out)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _permute(X: pd.DataFrame, perm: dict) -> pd.DataFrame:
    X = X.copy()
    src = X.set_index(["province_code", "t"])[NEWS_COLS]
    keys = list(zip(X["province_code"], X["t"].map(lambda t: perm.get(t, t))))
    X[NEWS_COLS] = src.reindex(keys).to_numpy()
    return X


# ================================================================================================ metrics (sections 6-8)
COMPARATORS = ["PERSIST-SI", "LR-COMB", "LR-GOV", "LR-NLP", "LGBM-GOV", "LGBM-NLP"]
REFS = ["PERSIST-SI", "CLIM", "ALWAYS-LOW", "STRUCT", "CH1-DIRECT"]


def acc_ci(D: pd.DataFrame, col: str, draws: int = 2000) -> list[float]:
    rng = np.random.default_rng(SEED)
    qv = D["q"].to_numpy()
    c = ((D[col] >= 0.5).astype(int) == D["y"]).to_numpy(float)
    uq = np.unique(qv)
    by = {q: c[qv == q] for q in uq}
    bs = [np.concatenate([by[q] for q in rng.choice(uq, len(uq))]).mean() for _ in range(draws)]
    return [float(np.quantile(bs, 0.05)), float(np.quantile(bs, 0.95))]


def cls(y, p) -> dict:
    """FINAL's metric set with the protocol's ">= 0.5 is HIGH" rule (cls_metrics uses > 0.5; nudge exact 0.5 up)."""
    p = np.asarray(p, float)
    m = FM.cls_metrics(np.asarray(y, int), np.where(p >= 0.5, np.maximum(p, 0.5 + 1e-12), p))
    m["brier"] = float(np.mean((np.clip(p, 0, 1) - np.asarray(y, float)) ** 2))
    return m


def decide(D: pd.DataFrame) -> dict:
    """FINAL_TARGET_AND_EVALUATION_PROTOCOL section 7 at one lead."""
    y = D["y"].astype(int).to_numpy()
    m = cls(y, D["CH1_p"].to_numpy())
    bases = {b: float(((D[f"{b}_p"] >= 0.5).astype(int) == D["y"]).mean()) for b in COMPARATORS + REFS
             if f"{b}_p" in D}
    bal = {b: cls(y, D[f"{b}_p"].clip(0, 1).to_numpy())["balanced_accuracy"] for b in COMPARATORS + REFS
           if f"{b}_p" in D}
    bs = (D["CH1_p"] - y) ** 2
    t_p = FM.boot_diff(D, bs, (D["PERSIST-SI_p"] - y) ** 2)
    t_c = FM.boot_diff(D, bs, (D["CLIM_p"] - y) ** 2)
    nq = int(D["q"].nunique())
    thirds = np.array_split(np.array(sorted(D["q"].unique())), 3)
    acc3 = [float(((D[D["q"].isin(th)]["CH1_p"] >= .5).astype(int) == D[D["q"].isin(th)]["y"]).mean())
            for th in thirds]
    loqo = [float(((D[D["q"] != q]["CH1_p"] >= .5).astype(int) == D[D["q"] != q]["y"]).mean())
            for q in D["q"].unique()]
    c = {"R1": nq >= 10 and len(D) >= 40, "R2": m["accuracy"] >= 0.75, "R3": m["balanced_accuracy"] >= 0.70,
         "R4": m["accuracy"] > bases["ALWAYS-LOW"] and m["accuracy"] > bases["PERSIST-SI"],
         "R5": t_p["diff"] < 0 and t_c["diff"] < 0 and t_p["p_less"] < 0.10 and t_c["p_less"] < 0.10,
         "R6": m["precision"] >= 0.60 and m["recall"] >= 0.60,
         "R7": all(len(th) for th in thirds) and min(acc3) >= 0.60 and min(loqo) >= 0.70}
    strict = all(c.values()) and all(m["balanced_accuracy"] > bal[b] for b in COMPARATORS + ["STRUCT"] if b in bal)
    # onset recall: HIGH after a LOW quarter for the same province
    lab = labels().set_index(["province_code", "q"])["y"]
    ons = D[[lab.get((p, q - 1), None) == 0 and yy == 1 for p, q, yy in zip(D["province_code"], D["q"], D["y"])]]
    return {"n": int(len(D)), "n_quarters": nq, "quarters": [L.qs(int(q)) for q in sorted(D["q"].unique())],
            "high_share": float(y.mean()), "metrics": m, "accuracy_ci90": acc_ci(D, "CH1_p"),
            "baseline_accuracy": bases, "baseline_balanced_accuracy": bal,
            "brier_vs_persist_si": t_p, "brier_vs_clim": t_c, "acc_thirds": acc3,
            "loqo_min": min(loqo), "loqo_max": max(loqo),
            "onsets": int(len(ons)), "onset_recall": float((ons["CH1_p"] >= .5).mean()) if len(ons) else None,
            "criteria": c, "reliable": all(c.values()), "reliable_strict": bool(strict)}


def superiority(D: pd.DataFrame) -> dict:
    """Objective 4 / H3 at one lead: CH1 vs each Chapter I comparator, Brier one-sided bootstrap + McNemar, Holm."""
    y = D["y"].astype(int).to_numpy()
    out, ps = {}, {}
    for b in COMPARATORS:
        t = FM.boot_diff(D, (D["CH1_p"] - y) ** 2, (D[f"{b}_p"] - y) ** 2)
        out[b] = {"brier_diff": t["diff"], "p_less": t["p_less"], "ci90": t["ci90"],
                  "mcnemar_p": FM.mcnemar(y, D["CH1_p"].to_numpy() >= .5, D[f"{b}_p"].to_numpy() >= .5),
                  "acc_ch1": float(((D["CH1_p"] >= .5).astype(int) == y).mean()),
                  "acc_comp": float(((D[f"{b}_p"] >= .5).astype(int) == y).mean())}
        ps[b] = t["p_less"]
    h = FM.holm(ps)
    for b in out:
        out[b]["holm_p"] = h[b]
    return {"comparisons": out, "H3_rejected": all(out[b]["holm_p"] < 0.05 and out[b]["brier_diff"] < 0 for b in out)}


def max_reliable_lead(dec: dict, key: str = "reliable") -> int | None:
    best = None
    for k in FORECAST_LEADS:
        if dec[k][key]:
            best = k
        else:
            break
    return best
