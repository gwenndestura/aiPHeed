"""E37: the E36 arms and nested rule at a general lead k (PROTOCOL.md section 4); k = 2 is the next-calendar-quarter
target the dashboard shows. Feature construction, grid, baselines and selection are E36's, unchanged."""
from __future__ import annotations

import sys
from pathlib import Path

E37 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E37.parent / "E36_LightGBM_One_Quarter_Ahead" / "runner"))
import e36_lib as L6  # noqa: E402

L6.guard32.EXP = E37                       # writes confined to E37 (and the OS temp directory)
C, np, pd, L32 = L6.C, L6.np, L6.pd, L6.L32
qk, qs, PROVS = C.qk, C.qs, C.PROVS
POOLS, GRID, FEATURE_SETS, LR_SETS = L6.POOLS, L6.GRID, L6.FEATURE_SETS, L6.LR_SETS
cfg_name, origin = L6.cfg_name, L6.origin
FIRST_TARGET, LAST_TARGET = qk("2022-Q4"), qk("2026-Q3")
OPERATIONAL_T = qk("2026-Q3")              # O = 2026-10-01; k = 2 -> 2027-Q1


class Data(L6.Data):
    def train(self, t: int, k: int = 1) -> pd.DataFrame:
        tr = self.training_pairs(t, k)
        return tr if tr.empty else tr.dropna(subset=L6.COMB).reset_index(drop=True)

    def test(self, t: int, k: int = 1) -> pd.DataFrame:
        return self.features(t, k)


def references(d: Data, t: int, k: int) -> dict:
    te, tr = d.test(t, k), d.train(t, k)
    clim = (tr["y"].sum() + 1) / (len(tr) + 2)
    out = {"B1_PERSISTENCE": {}, "ALWAYS_HIGH": {}, "CLIMATOLOGY": {}}
    for r in te.itertuples():
        out["B1_PERSISTENCE"][r.province_code] = float(r.y_last) if r.y_last == r.y_last else 0.5
        out["ALWAYS_HIGH"][r.province_code] = 1.0
        out["CLIMATOLOGY"][r.province_code] = float(clim)
    return out


def fixed_arms(d: Data, t: int, k: int) -> dict:
    tr, te = d.train(t, k), d.test(t, k)
    out = {}
    for pool, _ in POOLS.values():
        for fs, g in pool:
            n = cfg_name(fs, g)
            if n not in out:
                out[n] = L6.lgbm_predict(tr, te, FEATURE_SETS[fs], g)
    for arm, feats in LR_SETS.items():
        out[arm] = L6.lr_predict(tr, te, feats)
    out.update(references(d, t, k))
    return out


def eligible_prior(d: Data, t: int, k: int, dates: list[int]) -> list[int]:
    """Prior development origins tj whose TARGET tj+k was posted before O(t) (and is <= t-1)."""
    posted = set(d.posted_quarters(origin(t)))
    return [tj for tj in dates if tj < t and (tj + k) in posted and (tj + k) <= t - 1]


def select(pool_key, prior, preds, labels, k):
    """E36 rule; E36's select() names prior dates as origin+1 (lead 1), so they are re-labelled for lead k."""
    chosen, info = L6.select(pool_key, prior, preds, labels)
    return chosen, {**info, "prior_dates": [qs(x + k) for x in prior]}


def eval_dates(d: Data, k: int) -> list[int]:
    out = []
    for tg in range(FIRST_TARGET, LAST_TARGET + 1):
        t = tg - k
        lab = {p: d.label(p, tg, t) for p in PROVS}
        if any(v is None for v in lab.values()):
            continue
        tr = d.train(t, k)
        if len(tr) < 10 or tr["y"].nunique() < 2:
            continue
        out.append(t)
    return out


def walk_forward(d: Data, k: int):
    dates = eval_dates(d, k)
    preds, labels = {}, {}
    for t in dates:
        preds[t] = fixed_arms(d, t, k)
        labels[t] = {p: d.label(p, t + k, t) for p in PROVS}
    selections = {}
    for t in dates:
        prior = eligible_prior(d, t, k, dates)
        for arm in POOLS:
            (fs, g), info = select(arm, prior, preds, labels, k)
            preds[t][arm] = dict(preds[t][cfg_name(fs, g)])
            selections.setdefault(arm, {})[qs(t + k)] = {"chosen": cfg_name(fs, g), **info}
    rows = []
    for t in dates:
        for arm, pr in preds[t].items():
            for p in PROVS:
                rows.append({"lead": k, "t": qs(t), "origin": str(origin(t).date()), "target_quarter": qs(t + k),
                             "province_code": p, "arm": arm, "p": float(pr[p]), "y": int(labels[t][p])})
    return pd.DataFrame(rows), {"dates": [qs(t + k) for t in dates], "selections": selections}


def operational_choice(d: Data, Pr: pd.DataFrame, k: int, pool_key: str = "E36-LGBM"):
    dates = sorted({qk(x) for x in Pr["t"].unique()})
    prior = eligible_prior(d, OPERATIONAL_T, k, dates)
    preds, labels = {}, {}
    for tj in prior:
        s = Pr[Pr["t"] == qs(tj)]
        preds[tj] = {a: dict(zip(g["province_code"], g["p"])) for a, g in s.groupby("arm")}
        h = s[s["arm"] == "ALWAYS_HIGH"]
        labels[tj] = dict(zip(h["province_code"], h["y"]))
    return select(pool_key, prior, preds, labels, k)
