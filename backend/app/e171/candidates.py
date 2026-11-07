"""
E171 (EXPLORATORY): Lead-2 improvement candidates, per docs/e171/PROTOCOL.md. E168, E169 and the served model are not touched.

New inputs: SWS quarterly hunger trend (area and national), only quarters published before each issue date. Candidate families
(E168-TA, A trend inputs, B lead-band, C ridge/elastic net, D hybrid trend) and the pre-declared final E171 (best of all) are
chosen by a forward-in-time, whole-round score on training rows only (region folds when the training rows hold one round).
Every family then gets E168's temperature shrink, sd and HIGH line. E168 itself is re-run in the same jobs as a reproduction check.

    python -m app.e171.candidates lock
    python -m app.e171.candidates eval      (once)
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold

from app.e144 import data as SWSD
from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e148 import panel as Pn
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e156 import leads as LD
from app.e163 import model as C163
from app.e164 import auto as U
from app.e166 import temperature as T
from app.e168 import lgbm as L
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e171" / "out"
LEADS = (1, 2, 3)
SURVEYS = ("ENNS2018", "ENNS2019", "ENNS2021")
KEY = ["key", "survey", "lead"]
S_COLS = ["sws_now", "sws_since", "sws_nat_since"]
AREAS = ("metro_manila", "balance_luzon", "visayas", "mindanao")
LEAD_NOW = {"v": 1}


def _install():
    """Register the E171 inputs, constraints and learners in THIS process. Called at import and again inside every worker job:
    joblib workers started from `python -m` do not re-run this module's top level (the E169 seed-bagging patch was lost that way)."""
    Pv.SIGN.update({c: 1 for c in S_COLS})                  # more hunger -> higher food insecurity (fixed in the protocol)
    U.FS["GOV_S"] = U.FS["GOV"] + S_COLS
    U.FS["FULL_S"] = U.FS["FULL"] + S_COLS
    U.LEARNERS.update({"LGBMLB": LeadBand, "TREND": TrendRes})
    assert U.LEARNERS["LGBM"] is Pv.Res2 and "GOV_S" in U.FS and U.LEARNERS["TREND"] is TrendRes


# ------------------------------------------------------------------ SWS trend inputs
def add_sws(d: pd.DataFrame, sw: pd.DataFrame) -> pd.DataFrame:
    """sws_now, sws_since, sws_nat_since for each row, from SWS quarters published before the row's issue quarter."""
    if d.empty:
        return d
    by = {a: g.sort_values("qi") for a, g in sw.groupby("area")}
    memo = {}

    def area_vals(a, i, an):
        k = (a, i, an)
        if k not in memo:
            g = by.get(a)
            if g is None:
                memo[k] = (np.nan, np.nan)
            else:
                g = g[g["published"] < Pn.q_start(i)]
                now = g.tail(4)["hunger"].mean() if len(g) else np.nan
                anc = g[(g["qi"] >= an - 3) & (g["qi"] <= an)]["hunger"].mean()
                memo[k] = (float(now), float(now - anc) if anc == anc else np.nan)
        return memo[k]

    rows = []
    for r in d[["i", "rq_anchor", "sws_area"]].itertuples(index=False):
        now, since = area_vals(r.sws_area, int(r.i), int(r.rq_anchor))
        nat = [area_vals(a, int(r.i), int(r.rq_anchor))[1] for a in AREAS]
        nat = [x for x in nat if x == x]
        rows.append({"sws_now": now, "sws_since": since, "sws_nat_since": float(np.mean(nat)) if nat else np.nan})
    return pd.concat([d.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


# ------------------------------------------------------------------ candidate learners
class LeadBand(Pv.Res2):
    """B: LightGBM fitted only on training rows within one quarter of the forecast's own lead (all rows if too few)."""

    def fit(self, d):
        b = d[(d["lead"] - LEAD_NOW["v"]).abs() <= 1]
        return super().fit(b if len(b) >= 30 and b["region"].nunique() >= 2 else d)


class TrendRes:
    """D: weighted linear trend of the survey error on the SWS changes, then E168's LightGBM on what remains."""

    T_COLS = ["sws_since", "sws_nat_since"]

    def __init__(self, cols):
        self.cols = list(cols)

    def _Z(self, d):
        return np.column_stack([np.ones(len(d))] + [d[c].fillna(0.0).values for c in self.T_COLS])

    def fit(self, d):
        d = d.reset_index(drop=True)
        w = (1.0 / (d["se_true"] ** 2 + 0.05)).values
        Z = self._Z(d) * np.sqrt(w)[:, None]
        self.b_ = np.linalg.lstsq(Z, d["e"].values * np.sqrt(w), rcond=None)[0]
        self.tree_ = Pv.Res2(self.cols).fit(d.assign(e=d["e"].values - self._Z(d) @ self.b_))
        self.use_ = self.tree_.use_
        return self

    def predict(self, X):
        return self._Z(X) @ self.b_ + self.tree_.predict(X)


_install()
FAMILIES = {
    "E168TA": [(a, "LGBM", f) for a in U.ANCH for f in ("GOV", "FULL")],
    "A": [(a, "LGBM", f) for a in U.ANCH for f in ("GOV_S", "FULL_S")],
    "B": [(a, "LGBMLB", "GOV_S") for a in U.ANCH],
    "C": [(a, l, "GOV_S") for a in U.ANCH for l in ("RIDGE", "ENET")],
    "D": [(a, "TREND", "GOV_S") for a in U.ANCH],
}
FAMILIES["E171"] = [c for v in FAMILIES.values() for c in v]
MENU = FAMILIES["E171"]


# ------------------------------------------------------------------ time-aware selection
def _splits(tr):
    """Forward over whole survey rounds when the training rows hold 2+ rounds; else E168's region folds."""
    rounds = list(pd.unique(tr["survey"]))
    if len(rounds) >= 2:
        return "forward", [(np.where(tr["survey"].isin(fit).values)[0], np.where((tr["survey"] == g).values)[0])
                           for fit, g in T.forward_splits(rounds)]
    return "region", list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))


def score_all(tr, AN):
    tr = tr.reset_index(drop=True)
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    scheme, folds = _splits(tr)
    m = np.zeros(len(tr), bool)
    for _, b in folds:
        m[b] = True
    res = {}
    for a, l, f in MENU:
        atr = AN[a][0]
        oof = np.full(len(tr), np.nan)
        for i_tr, i_te in folds:
            oof[i_te] = atr[i_te] + U.LEARNERS[l](U.FS[f]).fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])).predict(tr.iloc[i_te])
        sse_id = float(np.sum((w * (y - oof) ** 2)[m]))
        cal = np.full(len(tr), np.nan)                     # cross-fitted linear calibration over the same folds
        for k, (i_tr, i_te) in enumerate(folds):
            if scheme == "forward":                        # calibrate a held-out round only on earlier held-out rounds
                src = np.concatenate([folds[j][1] for j in range(k)]) if k else np.array([], int)
            else:
                src = i_tr
            src = src[np.isfinite(oof[src])]
            if len(src) < 10:
                cal[i_te] = oof[i_te]
                continue
            Z = np.column_stack([np.ones(len(src)), oof[src]]) * np.sqrt(w[src])[:, None]
            ab = np.linalg.lstsq(Z, y[src] * np.sqrt(w[src]), rcond=None)[0]
            cal[i_te] = ab[0] + ab[1] * oof[i_te]
        sse_cal = float(np.sum((w * (y - cal) ** 2)[m]))
        res[(a, l, f)] = {"sse": min(sse_id, sse_cal), "calib": sse_cal < sse_id, "oof_id": oof}
    return scheme, m, res


def finalize(tr, te, AN, SW, cut, lead, scheme, m, res, menu):
    tr = tr.reset_index(drop=True)
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    best = min(menu, key=lambda c: res[c]["sse"])
    a, l, f = best
    r = res[best]
    atr, ate = AN[a]
    mu = ate + U.LEARNERS[l](U.FS[f]).fit(tr.assign(e=y - atr)).predict(te)
    oof = r["oof_id"].copy()
    if r["calib"]:
        Z = np.column_stack([np.ones(m.sum()), oof[m]]) * np.sqrt(w[m])[:, None]
        ab = np.linalg.lstsq(Z, y[m] * np.sqrt(w[m]), rcond=None)[0]
        mu, oof = ab[0] + ab[1] * mu, ab[0] + ab[1] * oof
    tag = f"{a}|{l}|{f}|{'cal' if r['calib'] else 'id'}"
    gtr, gte = tr["gap_q"].values, te["gap_q"].values
    la, va, _n = T.lam_round_heldout(tr, AN, tag)
    lb, vb, _nb, _kb = T.lam_sws(SW, cut, lead)
    lam, src = T.combine(la, va, lb, vb)
    sd_l, half_l = U.scale((y - lam * oof)[m], gtr[m], gte)
    s, ps, cls = T.apply_lambda(np.asarray(mu, float), sd_l, lam)
    return {"mu": s, "p": ps, "half": half_l, "tag": tag, "lam": lam, "src": src, "scheme": scheme}


# ------------------------------------------------------------------ one (survey, lead) job
def task(survey, lead, H, SW, mode="main"):
    _install()
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    LEAD_NOW["v"] = lead
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    rel = M.released(i, Pv.ROUNDS)
    if not rel:
        return None
    cut = Pn.q_start(i)
    sw = SWSD.sws_quarterly()
    if mode == "corrupt":
        b = S.s8.base
        z = ~b["survey"].isin(rel)
        b.loc[z, "y"] = np.random.default_rng(7).normal(0, 2, int(z.sum()))
        sw = T.corrupt_sws(sw, cut)
        SW = L.sws_forecasts(sw, i)
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = add_sws(E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H), sw).reset_index(drop=True)
    if te.empty:
        return None
    tr = add_sws(E154.add_income(Pv.add_inputs(S, P.tr), H), sw).reset_index(drop=True)
    AN = U.anchors(S, P, tr, te)
    o = te[KEY + ["sws_now", "sws_since", "sws_nat_since"]].copy()
    o["mode"] = mode
    if mode == "main":                                     # reproduction check: E168's own code in the same job
        r8 = L.forecast(tr, te, AN, SW, cut, lead)
        o["mu_R168"], o["R168"] = r8["s"], r8["ps"]
    scheme, msk, res = score_all(tr, AN)
    fams = FAMILIES if mode == "main" else {"E171": FAMILIES["E171"]}
    for fam, menu in fams.items():
        r = finalize(tr, te, AN, SW, cut, lead, scheme, msk, res, menu)
        o[f"mu_{fam}"], o[fam], o[f"half_{fam}"], o[f"tag_{fam}"], o[f"lam_{fam}"] = r["mu"], r["p"], r["half"], r["tag"], r["lam"]
    o["scheme"] = scheme
    o["train_rounds"] = int(tr["survey"].nunique())
    return o


# ------------------------------------------------------------------ lock / eval
CODE = [BACKEND_DIR / "app" / "e171" / "candidates.py", BACKEND_DIR / "app" / "e168" / "lgbm.py", BACKEND_DIR / "app" / "e166" / "temperature.py",
        BACKEND_DIR / "app" / "e151" / "prov.py", BACKEND_DIR.parent / "docs" / "e171" / "PROTOCOL.md"]
INPUTS = [D / "e168" / "out" / "oof.csv", D / "e169" / "out" / "oof.csv", D / "fi5" / "raw" / "sws" / "sws_area_rounds_full.csv"]
FILES = CODE + INPUTS


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rel(p):
    return str(p.relative_to(BACKEND_DIR.parent)).replace("\\", "/")


def lock():
    miss = [str(p) for p in FILES if not p.exists()]
    if miss:
        sys.exit("missing files, nothing locked:\n  " + "\n  ".join(miss))
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "lock.json").exists():
        sys.exit("already locked: one locked run only")
    (OUT / "lock.json").write_text(json.dumps({"locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": {_rel(p): _sha(p) for p in FILES}}, indent=1), newline="\n")
    print("locked", {p.name: _sha(p)[:12] for p in FILES})


def _check():
    lk = OUT / "lock.json"
    if not lk.exists():
        sys.exit("not locked")
    h = json.loads(lk.read_text())["hashes"]
    bad = [p.name for p in FILES if h.get(_rel(p)) != _sha(p)]
    if bad:
        sys.exit(f"changed since lock: {bad}")
    if (OUT / "results.json").exists():
        sys.exit("E171 has already run once.")


def extra(g, a):
    y = g["y_high"].values == 1
    return {"pr_auc": round(float(average_precision_score(y, g[a])), 3), **T.cal_ci(g.reset_index(drop=True), a)}


def evaluate():
    _check()
    H = E154.income()
    SW = L.sws_forecasts(SWSD.sws_quarterly(), max(M8.RQ[s] - 1 for s in SURVEYS))
    jobs = [(s, h, "main") for s in SURVEYS for h in LEADS] + [(s, h, "corrupt") for s in SURVEYS for h in (1, 2)]
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H, SW, m) for s, h, m in jobs) if x is not None]
    Al = pd.concat(R, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    main, cor = Al[Al["mode"] == "main"].drop(columns="mode"), Al[Al["mode"] == "corrupt"]
    F = pd.read_csv(D / "e168" / "out" / "oof.csv").rename(columns={"L": "E168", "mu_L": "mu_E168", "half_L": "half_E168"})
    F = F[F["lead"].isin(LEADS)].drop(columns=[c for c in ("tag", "lam_y", "src", "la", "lb", "nb", "rounds") if c in F])
    e9 = pd.read_csv(D / "e169" / "out" / "oof.csv")[KEY + ["L", "mu_L"]].rename(columns={"L": "E169", "mu_L": "mu_E169"})
    F = F.merge(e9, on=KEY, how="left").merge(main, on=KEY, how="inner")
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    repro = float(np.max(np.abs(F["E168"] - F["R168"])))
    lk = F[KEY + ["mu_E171", "E171"]].merge(cor[KEY + ["mu_E171", "E171"]], on=KEY, suffixes=("", "_c"))
    leak = float(max(np.max(np.abs(lk["mu_E171"] - lk["mu_E171_c"])), np.max(np.abs(lk["E171"] - lk["E171_c"]))))
    arms = ["E168", "E169", *FAMILIES, "E166", "AUTO", "GOV", "NEWS", "LR", "LR_GOV", "LR_NEWS", "PSA", "PERS"]
    rel, ext, rounds, prov, bri = {}, {}, {}, {}, {}
    rng = np.random.default_rng(171)
    for a in arms:
        if a not in F or F[a].isna().any():
            continue
        if f"mu_{a}" not in F:
            F[f"mu_{a}"] = np.log(np.clip(F[a], 1e-6, 1 - 1e-6) / np.clip(1 - F[a], 1e-6, 1))   # logit for arms without a score
        rel[a] = LD.evaluate(F, a, a)
        ext[a] = {int(h): extra(g, a) for h, g in F.groupby("lead")}
        rounds[a] = {int(h): {s: {"correct": int(((x[a] >= .5) == (x["y_high"] == 1)).sum()), "rows": int(len(x))} for s, x in g.groupby("survey")}
                     for h, g in F.groupby("lead")}
        if a != "E168":
            bri[a] = {int(h): E7.diff_ci(g.reset_index(drop=True), a, "E168", "q_true", rng, n=2000) for h, g in F.groupby("lead")}
    for a in ("E168", "E171", "A", "D"):
        prov[a] = F.assign(ok=(F[a] >= .5) == (F["y_high"] == 1))[["province", "survey", "lead", "ok"]].pivot_table(
            index=["province", "survey"], columns="lead", values="ok").astype(int).reset_index().to_dict("records")
    l = {r["lead"]: r for r in rel["E171"]["leads"]}
    d2 = bri["E171"][2]
    decision = {"reproduces_E168_max_abs_diff": repro, "leakage_max_abs_change": leak, "valid": bool(leak < 1e-9 and repro < 1e-9),
                "E171_lead1_C1_C6": l[1]["reliable"], "E171_lead2_C1_C6": l[2]["reliable"],
                "E171_lead2_brier_minus_E168": {"diff": round(d2["diff"], 4), "ci95": [round(z, 4) for z in d2["ci95"]]},
                # protocol 5: C1-C6 at Leads 1 and 2, valid run, Lead-2 Brier not significantly worse than E168 (interval low end <= 0)
                "lead2_genuinely_improved_exploratory": bool(l[1]["reliable"] and l[2]["reliable"] and d2["ci95"][0] <= 0
                                                            and leak < 1e-9 and repro < 1e-9),
                "status": "EXPLORATORY (rows used in E151-E169); E168 remains the thesis model"}
    cfg = main.groupby(["survey", "lead"])[["scheme", "train_rounds"] + [f"tag_{f}" for f in FAMILIES] + [f"lam_{f}" for f in FAMILIES]].first().reset_index()
    out = {"model": "E171 exploratory Lead-2 candidates", "decision": decision, "config_by_issue": cfg.to_dict("records"),
           "reliability": rel, "extra": ext, "by_round": rounds, "by_province": prov,
           "brier_minus_E168": {a: {h: {"diff": round(v["diff"], 4), "ci95": [round(z, 4) for z in v["ci95"]]} for h, v in x.items()} for a, x in bri.items()}}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(decision, indent=1))
    print(cfg.to_string(index=False))
    for a in arms:
        if a in rel:
            for r in rel[a]["leads"]:
                print(f"{a:7s} L{r['lead']} {r['confusion']['tp'] + r['confusion']['tn']}/{r['rows']} acc {r['accuracy']} lo {r['accuracy_95_low_effective_n']} "
                      f"maj {r['majority_rule']} f1 {r['f1']} auc {r['auc']} brier {r['brier_soft']} slope {r['calibration_slope_ci95']} "
                      f"{''.join(k for k, v in r['criteria'].items() if not v) or 'ALL-PASS'}")


if __name__ == "__main__":
    {"lock": lock, "eval": evaluate}[sys.argv[1]]()
