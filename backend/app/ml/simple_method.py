"""
app/ml/simple_method.py
-----------------------
The simple aiPHeed methodology (branch aipheed/simple-methodology, protocol
aipheed-backend-aligned/experiments/E106_Simple_Methodology/PROTOCOL.md).

Target (Chapter I 1.7): a province-quarter is HIGH when Balance Luzon SWS hunger is above 11.3% AND the province's
food prices are under pressure (food CPI YoY, or food minus headline YoY, above the province's 2021-22 P60; the
frozen E40 thresholds). The forecast answers the two parts separately and multiplies them:

    P(HIGH) = P_hunger x P_price

P_hunger: the latest SWS reading published before the issue date, turned into a probability of staying above 11.3%
with the spread of the same rule's own past errors (no training). P_price: one small LightGBM classifier on six
published provincial and national indicators. Lead 1 and Lead 2 use the same code with lead = 1 or 2.

Every input at origin t (issue = day 1 of quarter t+1) is something published before the issue date; every
training label is one that was complete before the issue date.
"""
from __future__ import annotations

import csv
import functools
import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
SWS_FILE = BACKEND / "data/inputs/sws_rounds.csv"
FOOD_FILE = BACKEND / "data/inputs/d_quarterly_panel.csv"
CPI_FILE = BACKEND / "data/processed/cpi_full.parquet"
HISTORY_FILE = BACKEND / "data/thesis/firi2_history.csv"
THRESHOLDS_FILE = REPO / "aipheed-backend-aligned/experiments/E40_SWS_CPI_Tiers/label_spec.json"

PROVINCES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
             "PH040500000": "Batangas"}
HUNGER_LINE = 11.3
SIGMA_DEFAULT, MIN_SIGMA_PAIRS = 4.0, 4
PRICE_FEATURES = ["F_last", "RICE", "UNEMP", "ELNINO", "HARVEST", "NEWS"]
ALL_FEATURES = PRICE_FEATURES + ["H_last"]
TRIGGER_GROUPS = {"market": ["F_last", "RICE"], "employment": ["UNEMP"], "climate": ["ELNINO", "HARVEST"],
                  "news": ["NEWS"]}
LGBM = dict(n_estimators=100, learning_rate=0.05, num_leaves=4, max_depth=2, min_child_samples=5, reg_lambda=5.0,
            deterministic=True, force_row_wise=True, random_state=106, n_jobs=1, verbose=-1)
MIN_TRAIN = 10


# ------------------------------------------------------------------------------------------------ quarters
def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def issue_of(t: int) -> str:
    """Issue date of origin t: day 1 of quarter t+1."""
    n = t + 1
    return date(n // 4, (n % 4) * 3 + 1, 1).isoformat()


# ------------------------------------------------------------------------------------------------ data
@functools.lru_cache(maxsize=1)
def sws_rounds() -> tuple[tuple[str, float, str], ...]:
    with open(SWS_FILE, newline="", encoding="utf-8") as f:
        return tuple((r["quarter"], float(r["H"]), r["published"][:10]) for r in csv.DictReader(f))


def posted(issue: str) -> dict[int, float]:
    """Quarter -> mean hunger of its rounds published before the issue date (a quarter counts only once all of its
    rounds in the file are published, so a half-published quarter is never used)."""
    by_q: dict[str, list] = {}
    for q, h, pub in sws_rounds():
        by_q.setdefault(q, []).append((h, pub))
    return {qi(q): float(np.mean([h for h, _ in v])) for q, v in by_q.items() if all(p < issue for _, p in v)}


def outcome(q: int) -> float | None:
    """Observed hunger of quarter q: mean of all its rounds (the evaluation outcome)."""
    v = [h for qq, h, _ in sws_rounds() if qi(qq) == q]
    return float(np.mean(v)) if v else None


@functools.lru_cache(maxsize=1)
def thresholds() -> dict:
    return json.loads(THRESHOLDS_FILE.read_text())["thresholds"]


@functools.lru_cache(maxsize=1)
def food_yoy() -> dict[tuple[str, int], float]:
    d = pd.read_csv(FOOD_FILE, dtype={"province_code": str})
    return {(r.province_code, qi(r.quarter)): float(r.F) for r in d.itertuples() if pd.notna(r.F)}


@functools.lru_cache(maxsize=1)
def headline_yoy() -> dict[tuple[str, int], float]:
    c = pd.read_parquet(CPI_FILE, filters=[("year", ">=", 2021)])
    c = c[c["province_code"].isin(list(PROVINCES))]
    return {(r.province_code, qi(r.quarter)): float(r.cpi_all_yoy_pct) for r in c.itertuples() if pd.notna(r.cpi_all_yoy_pct)}


@functools.lru_cache(maxsize=1)
def history_raw() -> dict[tuple[int, str], dict]:
    """Served FIRI v2 raw indicator values (published before each issue) by (origin, province)."""
    h = pd.read_csv(HISTORY_FILE, dtype={"province_code": str})
    out = {}
    for r in h.itertuples():
        ind = json.loads(r.indicators_json)
        out[(qi(r.origin_quarter), r.province_code)] = {k: ind[k]["x"] for k in ("A3", "E1", "C1", "C3", "N1")}
    return out


# ------------------------------------------------------------------------------------------------ labels
def price_label(p: str, q: int) -> int | None:
    th = thresholds()
    f, hl = food_yoy().get((p, q)), headline_yoy().get((p, q))
    if f is None:
        return None
    if f > th["food"][p]:
        return 1
    if hl is None:
        return None
    return int(f - hl > th["gap"][p])


def target_label(p: str, q: int) -> int | None:
    """The food-insecurity risk label of Chapter I 1.7: SWS hunger above 11.3% AND food-price pressure."""
    h, pr = outcome(q), price_label(p, q)
    if h is None:
        return None
    if h <= HUNGER_LINE:
        return 0
    return pr


def label_known(q: int, t: int, needs_sws: bool) -> bool:
    """Was quarter q's label complete before the issue date of origin t? CPI of q is complete only from t >= q+1;
    the SWS part needs every round of q published before the issue."""
    if q > t - 1:
        return False
    return (not needs_sws) or q in posted(issue_of(t))


# ------------------------------------------------------------------------------------------------ features
def features(t: int, p: str) -> dict:
    raw = history_raw().get((t, p), {})
    hs = posted(issue_of(t))
    last = max(hs) if hs else None
    return {"F_last": food_yoy().get((p, t - 1)), "RICE": raw.get("A3"), "UNEMP": raw.get("E1"), "ELNINO": raw.get("C1"),
            "HARVEST": raw.get("C3"), "NEWS": raw.get("N1"), "H_last": None if last is None else hs[last],
            "H_last_quarter": None if last is None else qs(last)}


def origins() -> list[int]:
    return sorted({t for t, _ in history_raw()})


# ------------------------------------------------------------------------------------------------ hunger part
def hunger_level(t: int, lead: int, rule: str = "rw") -> float | None:
    """Forecast of the hunger level of quarter t+lead from SWS published before the issue of t."""
    hs = posted(issue_of(t))
    if not hs:
        return None
    qs_ = sorted(hs)
    last = qs_[-1]
    if rule == "rw":
        return hs[last]
    if rule == "ma2":
        return float(np.mean([hs[q] for q in qs_[-2:]]))
    if rule == "ar1d":                                     # E105 definition
        mu = float(np.mean(list(hs.values())))
        pairs = [(hs[q - 1] - mu, hs[q] - mu) for q in qs_ if q - 1 in hs]
        phi = 1.0
        if len(pairs) >= 5:
            x, y = np.array(pairs).T
            phi = float(np.clip((x @ y) / (x @ x), 0.0, 1.0)) if x @ x > 0 else 1.0
        return mu + phi ** ((t + lead) - last) * (hs[last] - mu)
    raise ValueError(rule)


def p_hunger(t: int, lead: int, rule: str = "rw") -> tuple[float | None, float | None]:
    """(probability that hunger in t+lead is above 11.3%, forecast level). Spread = RMSE of the same rule's earlier
    errors whose outcome quarter was fully published before this issue."""
    b = hunger_level(t, lead, rule)
    if b is None:
        return None, None
    known = posted(issue_of(t))
    errs = []
    for tp in range(min(origins()) - 2, t - lead + 1):
        if tp + lead in known:
            bp = hunger_level(tp, lead, rule)
            if bp is not None:
                errs.append(known[tp + lead] - bp)
    sigma = math.sqrt(sum(e * e for e in errs) / len(errs)) if len(errs) >= MIN_SIGMA_PAIRS else SIGMA_DEFAULT
    return 1 - 0.5 * (1 + math.erf((HUNGER_LINE - b) / (sigma * math.sqrt(2)))), b


# ------------------------------------------------------------------------------------------------ price part
def training_rows(t: int, lead: int, label: str, cols) -> pd.DataFrame:
    rows = []
    for tp in origins():
        q = tp + lead
        if tp >= t or not label_known(q, t, needs_sws=(label == "target")):
            continue
        for p in PROVINCES:
            y = price_label(p, q) if label == "price" else target_label(p, q)
            if y is None:
                continue
            f = features(tp, p)
            rows.append({**{c: f[c] for c in cols}, "y": int(y), "t": tp, "p": p})
    return pd.DataFrame(rows)


def _lgbm():
    import lightgbm as lgb
    return lgb.LGBMClassifier(**LGBM)


def fit_lgbm(tr: pd.DataFrame, cols):
    """A fitted model, or the training HIGH share when the window is too small or has one class."""
    if len(tr) < MIN_TRAIN or tr["y"].nunique() < 2:
        return float(tr["y"].mean()) if len(tr) else 0.5
    return _lgbm().fit(tr[list(cols)].astype(float), tr["y"].to_numpy(int))


def _row(x: dict, cols) -> pd.DataFrame:
    return pd.DataFrame([{c: np.nan if x[c] is None else float(x[c]) for c in cols}])


def predict(model, x: dict, cols) -> float:
    if isinstance(model, float):
        return model
    return float(model.predict_proba(_row(x, cols))[0, 1])


def shap_groups(model, x: dict) -> dict | None:
    """TreeSHAP of P_price (log-odds), grouped by trigger. None when the price part is a constant."""
    if isinstance(model, float):
        return None
    contrib = model.booster_.predict(_row(x, PRICE_FEATURES), pred_contrib=True)[0]
    per = dict(zip(PRICE_FEATURES, contrib[:-1]))
    return {"groups": {g: float(sum(per[c] for c in cs)) for g, cs in TRIGGER_GROUPS.items()},
            "features": {c: float(v) for c, v in per.items()}, "base_log_odds": float(contrib[-1])}


# ------------------------------------------------------------------------------------------------ forecast
def forecast(t: int, lead: int, rule: str = "rw") -> dict:
    """The SM forecast for every province from origin t at the given lead."""
    ph, level = p_hunger(t, lead, rule)
    tr = training_rows(t, lead, "price", PRICE_FEATURES)
    model = fit_lgbm(tr, PRICE_FEATURES)
    out = {"origin": qs(t), "issue_date": issue_of(t), "target": qs(t + lead), "lead": lead, "hunger_rule": rule,
           "p_hunger": ph, "hunger_forecast_level": level, "training_rows": int(len(tr)),
           "training_high": int(tr["y"].sum()) if len(tr) else 0, "provinces": {}}
    for p in PROVINCES:
        x = features(t, p)
        pp = predict(model, x, PRICE_FEATURES)
        prob = None if ph is None else ph * pp
        out["provinces"][p] = {"name": PROVINCES[p], "p_price": pp, "p_high": prob,
                               "class": None if prob is None else ("HIGH" if prob >= 0.5 else "LOW"),
                               "inputs": {k: x[k] for k in ALL_FEATURES + ["H_last_quarter"]},
                               "explanation": shap_groups(model, x)}
    probs = [v["p_high"] for v in out["provinces"].values() if v["p_high"] is not None]
    out["region_p_high"] = float(np.mean(probs)) if probs else None
    return out


def lgu_ranking(province_prob: dict[str, float]) -> dict:
    """The existing LGU disaggregation (province probability x within-province vulnerability)."""
    from app.quarterly.lgu_audit import build_ranking
    vul = pd.read_csv(BACKEND / "data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
    ros = pd.read_csv(BACKEND / "data/reference/calabarzon_lgus.csv", dtype={"lgu_psgc": str})
    return build_ranking(vul, ros, province_prob, {"source": "simple methodology (E106)"}, exact_ranks=True)
