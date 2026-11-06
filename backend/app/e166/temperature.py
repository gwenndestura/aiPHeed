"""
E166: E164 AUTO with a temperature shrink of the score, per docs/e166/PROTOCOL.md.

    score = lam * mu_AUTO,  0 < lam <= 1;  class = (mu_AUTO >= 0), unchanged;  P(HIGH) = Phi(lam * mu_AUTO / sd_lam),
    sd_lam refitted (app.e164.auto.scale) on the training errors of the shrunk score, y - lam * oof

lam is estimated per issue date from data released before that date only:
    (a) forward-in-time held-out refits of AUTO's chosen configuration inside the training rows (>= 2 target rounds);
    (b) out-of-time ElasticNet forecasts of the SWS quarterly hunger series (persistence anchor + ElasticNet);
        same-lead pairs, or leads <= h pooled when fewer than 20.
Both: inverse-variance combination. Clip to [0.3, 1.0]. Neither: lam = 1.

    python -m app.e166.temperature lock    check files, hash code, protocol and inputs (owner approval required first)
    python -m app.e166.temperature eval    once; refuses if not locked, if anything changed since the lock, or if it already ran
    python -m app.e166.temperature live    2027-Q1 forecast and seal, only if eval passed
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
from sklearn.model_selection import GroupKFold

from app.e144 import data as SWSD
from app.e147 import evaluate as E7
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e148 import panel as Pn
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e150 import response as R150
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e156 import leads as LD
from app.e164 import auto as U
from app.fi5.target import qindex
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e166" / "out"
LAM_MIN, LAM_MAX = 0.3, 1.0
MIN_PAIRS = 20                                         # minimum held-out or SWS pairs for an estimate
SWS_COLS = R150.INPUTS + ["sws_last", "sws_anom", "lead"]
SWS_FIRST_ISSUE = qindex("2015-Q1")
SWS_MIN_TRAIN = 60
LEADS = range(1, 9)
SURVEYS = ("ENNS2018", "ENNS2019", "ENNS2021")
KEY = ["key", "survey", "lead"]
BASELINES = ("AUTO", "E158", "GNT", "GOV", "NEWS", "LR", "LR_NEWS", "PSA", "PERS", "ANCHOR")
CODE = [BACKEND_DIR / "app" / "e166" / "temperature.py", BACKEND_DIR / "app" / "e165" / "calib.py", BACKEND_DIR.parent / "docs" / "e166" / "PROTOCOL.md"]
INPUTS = [D / "e164" / "out" / "oof.csv", D / "e158" / "out" / "oof.csv", D / "e151" / "out" / "prov_oof.csv", E154.RAW / "regional_income_long.csv",
          D / "e147" / "raw" / "sealed_2021_labels.csv", D / "e147" / "raw" / "heatmap_provincial.jsonl", D / "fi5" / "raw" / "sws" / "sws_area_rounds_full.csv"]
FILES = CODE + INPUTS


# ---------- pure rules (unit-tested) ----------
def wls_slope(s, y, w):
    """Weighted least-squares slope of y on s (with intercept) and its variance. NaN if fewer than MIN_PAIRS pairs."""
    s, y, w = (np.asarray(v, float) for v in (s, y, w))
    ok = np.isfinite(s) & np.isfinite(y) & np.isfinite(w)
    s, y, w = s[ok], y[ok], w[ok]
    if len(s) < MIN_PAIRS or np.std(s) == 0:
        return float("nan"), float("nan")
    X = np.column_stack([np.ones(len(s)), s])
    XtW = X.T * w
    cov0 = np.linalg.inv(XtW @ X)
    beta = cov0 @ (XtW @ y)
    r = y - X @ beta
    sig2 = float(np.sum(w * r ** 2) / (len(s) - 2))
    return float(beta[1]), float(sig2 * cov0[1, 1])


def combine(la, va, lb, vb):
    """Inverse-variance combination of the available estimates, clipped to [LAM_MIN, LAM_MAX]; neither -> 1."""
    have = [(l, v, n) for l, v, n in ((la, va, "a"), (lb, vb, "b")) if np.isfinite(l) and np.isfinite(v) and v > 0]
    if not have:
        return 1.0, "none"
    w = np.array([1.0 / v for _, v, _ in have])
    lam = float(np.sum(w * np.array([l for l, _, _ in have])) / np.sum(w))
    return float(np.clip(lam, LAM_MIN, LAM_MAX)), "+".join(n for _, _, n in have)


def apply_lambda(mu, sd, lam):
    """Shrunk score, probability and class. The class is computed from mu, so it cannot change."""
    mu, sd = np.asarray(mu, float), np.asarray(sd, float)
    assert 0 < lam <= 1
    s = lam * mu
    return s, norm.cdf(s / sd), (mu >= 0)


def sws_pairs_for(P: pd.DataFrame, cut: pd.Timestamp, lead: int, pooled: bool = False) -> pd.DataFrame:
    """SWS forecast/outcome pairs usable at a province issue starting `cut`: forecast issued and outcome published before `cut`;
    same lead, or (pooled) every lead up to `lead`."""
    lm = (P["lead"] <= lead) if pooled else (P["lead"] == lead)
    return P[lm & (P["issue_start"] < cut) & (P["published"] < cut)]


def lam_sws(P, cut, lead):
    """Same-lead pairs; if fewer than MIN_PAIRS, pairs at leads <= lead pooled. Returns (lambda, variance, n_pairs, 'same'|'pooled')."""
    q, kind = sws_pairs_for(P, cut, lead), "same"
    if len(q) < MIN_PAIRS:
        q, kind = sws_pairs_for(P, cut, lead, pooled=True), "pooled"
    l, v = wls_slope(q["f"], q["y"], np.ones(len(q)))
    return l, v, int(len(q)), kind


def forward_splits(surveys) -> list[tuple[list[str], str]]:
    """Forward-in-time held-out rounds: each round after the earliest is scored by a fit on the strictly earlier rounds."""
    order = sorted(set(surveys), key=lambda s: int(str(s)[-4:]))
    return [(order[:k], order[k]) for k in range(1, len(order))]


# ---------- (b) SWS out-of-time forecasts ----------
def sws_area_table(s: pd.DataFrame) -> pd.DataFrame:
    """app.e151.sws.area_table with the SWS table passed in (so the leakage control can randomise it)."""
    P = R150.province_inputs()
    a = P[P["sws_area"].isin(SWSD.AREAS)].groupby(["sws_area", "qi"])[R150.INPUTS].mean().reset_index().rename(columns={"sws_area": "area"})
    a = pd.concat([a, P.groupby("qi")[R150.INPUTS].mean().reset_index().assign(area="metro_manila")], ignore_index=True)
    rows = []
    for _, r in a.iterrows():
        if r["qi"] < Pn.FIRST:
            continue
        g = s[(s["area"] == r["area"]) & (s["published"] < Pn.q_start(int(r["qi"])))].sort_values("qi")
        if g.empty:
            continue
        h = Fe._logit(g["hunger"].values)
        st = {"sws_last": float(h[-1]), "sws_anom": float(h[-1] - np.mean(h[-9:-1])) if len(h) >= 3 else np.nan}
        for ld in LEADS:
            T = int(r["qi"]) + ld
            t = s[(s["area"] == r["area"]) & (s["qi"] == T)]
            row = {**r.to_dict(), **st, "lead": ld, "T": T, "dy": np.nan, "published": pd.NaT}
            if len(t):
                row["dy"] = float(Fe._logit(t["hunger"].iloc[0])) - st["sws_last"]
                row["published"] = t["published"].iloc[0]
            rows.append(row)
    d = pd.DataFrame(rows)
    d["qi"] = d["qi"].astype(int)
    return d


def sws_forecasts(s: pd.DataFrame, last_issue: int) -> pd.DataFrame:
    """Expanding-window SWS forecasts: persistence anchor + ElasticNet (AUTO's ENetRes) on government inputs and SWS state."""
    A = sws_area_table(s)
    out = []
    for qs in range(SWS_FIRST_ISSUE, last_issue + 1):
        cut = Pn.q_start(qs)
        tr = A[A["dy"].notna() & (A["published"] < cut)]
        te = A[(A["qi"] == qs) & A["dy"].notna()]
        if len(tr) < SWS_MIN_TRAIN or te.empty:
            continue
        d = tr.assign(region=tr["area"], se_true=0.0, e=tr["dy"]).reset_index(drop=True)
        m = U.ENetRes(SWS_COLS).fit(d)
        p = m.predict(te.assign(region=te["area"]))
        out.append(pd.DataFrame({"area": te["area"].values, "issue": qs, "issue_start": cut, "lead": te["lead"].values, "published": te["published"].values,
                                 "f": te["sws_last"].values + p, "y": te["sws_last"].values + te["dy"].values}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["area", "issue", "issue_start", "lead", "published", "f", "y"])


def corrupt_sws(s: pd.DataFrame, cut: pd.Timestamp) -> pd.DataFrame:
    s = s.copy()
    z = s["published"] >= cut
    s.loc[z, "hunger"] = np.random.default_rng(9).uniform(1, 40, int(z.sum()))
    return s


# ---------- (a) round-held-out refits ----------
def lam_round_heldout(tr: pd.DataFrame, AN: dict, tag: str):
    """Refit AUTO's chosen configuration forward in time: each later training round is scored by a fit on strictly earlier rounds."""
    tr = tr.reset_index(drop=True)
    rounds = list(pd.unique(tr["survey"]))
    if len(rounds) < 2:
        return float("nan"), float("nan"), len(rounds)
    a, l, f, cal = tag.split("|")
    f = None if f == "-" else f
    atr = AN[a][0]
    y, w = tr["y_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    sc = np.full(len(tr), np.nan)
    for fit_rounds, g in forward_splits(rounds):
        h, o = (tr["survey"] == g).values, tr["survey"].isin(fit_rounds).values
        trO = tr[o].reset_index(drop=True)
        if l == "NONE":
            s_h, oof_o = atr[h], atr[o]
        else:
            s_h = atr[h] + U.LEARNERS[l](U.FS[f]).fit(trO.assign(e=y[o] - atr[o])).predict(tr[h])
            oof_o = np.zeros(o.sum())
            if cal == "cal":
                for i_tr, i_te in GroupKFold(min(5, trO["region"].nunique())).split(trO, groups=trO["region"]):
                    dd = trO.iloc[i_tr].assign(e=y[o][i_tr] - atr[o][i_tr])
                    oof_o[i_te] = atr[o][i_te] + U.LEARNERS[l](U.FS[f]).fit(dd).predict(trO.iloc[i_te])
        if cal == "cal":
            wo = w[o]
            Z = np.column_stack([np.ones(o.sum()), oof_o]) * np.sqrt(wo)[:, None]
            ab = np.linalg.lstsq(Z, y[o] * np.sqrt(wo), rcond=None)[0]
            s_h = ab[0] + ab[1] * s_h
        sc[h] = s_h
    lv, vv = wls_slope(sc, y, w)
    return lv, vv, len(rounds)


# ---------- per issue ----------
def forecast(tr, te, AN, SW, cut, lead):
    """AUTO (identical selection, via app.e165.calib.procedure which also returns the chosen configuration's training OOF scores),
    lambda from (a) and (b), shrunk score, and P(HIGH) with sd refitted on the training errors of the shrunk score."""
    from app.e165 import calib as C165
    mu, tag, oof, y, _w = C165.procedure(tr, te, AN)
    gtr, gte = tr["gap_q"].values, te["gap_q"].values
    sd, half = U.scale(y - oof, gtr, gte)
    p = norm.cdf(mu / sd)
    la, va, n_rounds = lam_round_heldout(tr, AN, tag)
    lb, vb, nb, kb = lam_sws(SW, cut, lead)
    lam, src = combine(la, va, lb, vb)
    sd_l, half_l = U.scale(y - lam * oof, gtr, gte)
    s, ps, cls = apply_lambda(mu, sd_l, lam)
    return mu, sd, half, p, s, ps, half_l, cls, tag, lam, src, la, va, lb, vb, nb, kb, n_rounds


def task(survey, lead, H, SW, mode="main"):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - lead
    rel = M.released(i, Pv.ROUNDS)
    if not rel:
        return None
    cut = Pn.q_start(i)
    if mode == "corrupt":                                      # unreleased survey rounds and SWS readings published on/after the issue date
        b = S.s8.base
        z = ~b["survey"].isin(rel)
        b.loc[z, "y"] = np.random.default_rng(7).normal(0, 2, int(z.sum()))
        SW = sws_forecasts(corrupt_sws(SWSD.sws_quarterly(), cut), i)
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    if P.tr.empty:
        return None
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [lead], Pv.ORIGIN[survey])), H).reset_index(drop=True)
    if te.empty:
        return None
    tr = E154.add_income(Pv.add_inputs(S, P.tr), H).reset_index(drop=True)
    AN = U.anchors(S, P, tr, te)
    mu, sd, half, p, s, ps, half_s, cls, tag, lam, src, la, va, lb, vb, nb, kb, n_rounds = forecast(tr, te, AN, SW, cut, lead)
    o = te[KEY].copy()
    o["mode"] = mode
    o["mu_AUTO_R"], o["AUTO_R"], o["half_AUTO_R"] = mu, p, half
    o["mu_TS"], o["TS"], o["half_TS"] = s, ps, half_s
    o["class_AUTO_R"] = cls.astype(int)
    for k, v in {"lam": lam, "lam_source": src, "lam_a": la, "var_a": va, "lam_b": lb, "var_b": vb, "n_sws_pairs": nb, "sws_pairs_kind": kb, "n_train_rounds": n_rounds, "cfg": tag}.items():
        o[k] = v
    return o


# ---------- lock ----------
def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rel(p):
    return str(p.relative_to(BACKEND_DIR.parent)).replace("\\", "/")


def _preflight():
    miss = [str(p) for p in FILES if not p.exists()]
    if miss:
        sys.exit("missing files, nothing locked:\n  " + "\n  ".join(miss))


def lock():
    _preflight()
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "lock.json").exists():
        sys.exit("already locked: one locked run only (docs/e166/PROTOCOL.md)")
    (OUT / "lock.json").write_text(json.dumps({"locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": {_rel(p): _sha(p) for p in FILES}}, indent=1), newline="\n")
    print("locked", {p.name: _sha(p)[:12] for p in FILES})


def _check_lock():
    lk = OUT / "lock.json"
    if not lk.exists():
        sys.exit("not locked: run `python -m app.e166.temperature lock` first, after owner approval")
    h = json.loads(lk.read_text())["hashes"]
    bad = [p.name for p in FILES if h.get(_rel(p)) != _sha(p)]
    if bad:
        sys.exit(f"changed since lock: {bad}. The locked run is void; report it as such.")
    if (OUT / "results.json").exists():
        sys.exit("E166 has already run once. Re-running is not allowed by the protocol.")


# ---------- evaluation ----------
def cal_ci(g, a, n=2000):
    rng = np.random.default_rng(166)
    regs = list(g.groupby("region").indices.values())
    mu, y = g[f"mu_{a}"].values, g["y_true"].values
    sl, ic = [], []
    for _ in range(n):
        i = np.concatenate([regs[j] for j in rng.integers(0, len(regs), len(regs))])
        if np.std(mu[i]) > 0:
            b1, b0 = np.polyfit(mu[i], y[i], 1)
            sl.append(b1)
            ic.append(b0)
    b1, b0 = np.polyfit(mu, y, 1)
    return {"slope": round(float(b1), 3), "slope_ci95": [round(float(np.percentile(sl, q)), 3) for q in (2.5, 97.5)],
            "intercept": round(float(b0), 3), "intercept_ci95": [round(float(np.percentile(ic, q)), 3) for q in (2.5, 97.5)]}


def bands(g, a):
    b = pd.cut(g[a], [0, .2, .4, .6, .8, 1.0], include_lowest=True)
    return g.groupby(b, observed=False).agg(n=("y_high", "size"), mean_p=(a, "mean"), observed_high=("y_high", "mean")).round(3).reset_index().astype(str).to_dict("records")


def _diff(g, a, b, rng):
    d = E7.diff_ci(g, a, b, "q_true", rng, n=2000)
    return {"diff": round(d["diff"], 4), "ci95": [round(z, 4) for z in d["ci95"]]}


def evaluate():
    _preflight()
    _check_lock()
    SW = sws_forecasts(SWSD.sws_quarterly(), max(M8.RQ[s] - 1 for s in SURVEYS))
    H = E154.income()
    jobs = [(s, h, "main") for s in SURVEYS for h in LEADS] + [(s, 1, "corrupt") for s in SURVEYS]
    R = [x for x in Parallel(n_jobs=12)(delayed(task)(s, h, H, SW, m) for s, h, m in jobs) if x is not None]
    Al = pd.concat(R, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    Al.to_csv(OUT / "all_rows.csv", index=False, lineterminator="\n")
    SW.to_csv(OUT / "sws_forecasts.csv", index=False, lineterminator="\n")
    main, cor = Al[Al["mode"] == "main"].drop(columns="mode"), Al[Al["mode"] == "corrupt"]
    E = pd.read_csv(D / "e158" / "out" / "oof.csv")
    G = pd.read_csv(D / "e151" / "out" / "prov_oof.csv")[KEY + ["GOV", "mu_GOV", "ANCHOR", "mu_ANCHOR"]]
    AU = pd.read_csv(D / "e164" / "out" / "oof.csv")[KEY + ["AUTO", "mu_AUTO", "half_AUTO"]]
    F = E.merge(G, on=KEY, how="left").merge(AU, on=KEY, how="left").merge(main, on=KEY, how="inner")
    assert len(F) == len(E), ("row mismatch with E158", len(F), len(E))
    F.to_csv(OUT / "oof.csv", index=False, lineterminator="\n")
    a4 = F[F["lead"] <= 4]
    repro = float(np.max(np.abs(a4["mu_AUTO"] - a4["mu_AUTO_R"])))
    same_class = bool(((F["mu_TS"] >= 0) == (F["mu_AUTO_R"] >= 0)).all() and ((F["TS"] >= .5) == (F["AUTO_R"] >= .5)).all())
    x1 = F[F["lead"] == 1].reset_index(drop=True)
    lk = x1[KEY + ["mu_TS", "TS", "lam"]].merge(cor[KEY + ["mu_TS", "TS", "lam"]], on=KEY, suffixes=("", "_c"))
    leak = float(max(np.max(np.abs(lk[c] - lk[c + "_c"])) for c in ("mu_TS", "TS", "lam")))
    void = bool(repro >= 1e-6 or leak >= 1e-9 or len(lk) != len(x1))
    rel = {"TS": LD.evaluate(F, "TS", "TS"), "AUTO_R": LD.evaluate(F, "AUTO_R", "AUTO_R"), "E158": LD.evaluate(F, "E158", "E158")}
    rng = np.random.default_rng(166)
    per_lead = {}
    for L, g in F.groupby("lead"):
        g = g.reset_index(drop=True)
        ref = "AUTO" if L <= 4 else "AUTO_R"
        per_lead[int(L)] = {"calibration": {a: cal_ci(g, a) for a in ("TS", "AUTO_R", "E158")},
                            "bands": {"TS": bands(g, "TS"), "AUTO_R": bands(g, "AUTO_R")},
                            "coverage_90": {a: round(float((np.abs(g[f"mu_{a}"] - g["y_true"]) <= g[f"half_{a}"]).mean()), 3) for a in ("TS", "AUTO_R")},
                            "brier": {a: round(float(np.mean((g[a] - g["q_true"]) ** 2)), 4) for a in ("TS", "AUTO_R") + tuple(b for b in BASELINES if b in g and g[b].notna().all())},
                            "TS_minus_brier": {b: _diff(g, "TS", b if b != "AUTO" else ref, rng) for b in BASELINES if (b if b != "AUTO" else ref) in g and g[b if b != "AUTO" else ref].notna().all()}}
    lam_tbl = main.groupby(["survey", "lead"])[["lam", "lam_source", "lam_a", "var_a", "lam_b", "var_b", "n_sws_pairs", "sws_pairs_kind", "n_train_rounds", "cfg"]].first().reset_index().to_dict("records")
    l1 = next(r for r in rel["TS"]["leads"] if r["lead"] == 1)
    b1 = per_lead[1]["TS_minus_brier"]["AUTO"]
    decision = {"reproduction_max_abs_mu_AUTO": repro, "leakage_max_abs_change": leak, "void": void, "classes_identical_all_leads": same_class,
                "lead1_correct": int(l1["confusion"]["tp"] + l1["confusion"]["tn"]), "lead1_criteria": {k: bool(v) for k, v in l1["criteria"].items()},
                "lead1_brier_TS_minus_AUTO": b1,
                "rule": {"C1_to_C6": bool(all(l1["criteria"].values())), "classes_identical": same_class, "brier_not_worse_than_AUTO": b1["diff"] <= 0, "valid": not void},
                "max_reliable_lead_TS": rel["TS"]["maximum_reliable_lead"]}
    decision["pass"] = bool(all(decision["rule"].values()))
    out = {"model": "E164 AUTO + temperature shrink (lambda from round-held-out refits and SWS out-of-time forecasts)", "decision": decision,
           "lambda_by_issue": lam_tbl, "reliability": rel, "per_lead": per_lead}
    (OUT / "results.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(decision, indent=1))
    print(pd.DataFrame(lam_tbl).to_string(index=False))
    for v in ("TS", "AUTO_R", "E158"):
        for r in rel[v]["leads"]:
            print(v, r["lead"], r["rows"], r["accuracy"], r["f1"], r["auc"], r["brier_soft"], r["calibration_slope_ci95"], {k: int(z) for k, z in r["criteria"].items()})
    print("lead1", json.dumps(per_lead[1], default=str))


def live():
    p = OUT / "results.json"
    if not p.exists() or not json.loads(p.read_text())["decision"]["pass"]:
        sys.exit("live runs only after eval passed (docs/e166/PROTOCOL.md)")
    from app.e160.trace import build
    S, P, tr, m, te = build()
    tr, te = tr.reset_index(drop=True), te.reset_index(drop=True)
    i = qindex("2026-Q4")
    SW = sws_forecasts(SWSD.sws_quarterly(), i)
    AN = U.anchors(S, P, tr, te)
    mu, sd, half, pr, s, ps, half_s, cls, tag, lam, src, la, va, lb, vb, nb, kb, n_rounds = forecast(tr, te, AN, SW, Pn.q_start(i), 1)
    pct = lambda v: 100 / (1 + np.exp(-np.asarray(v, float)))
    rows = [{"province": te["province"].iloc[k], "score": round(float(pct(s[k])), 1), "low90": round(float(pct(s[k] - half_s[k])), 1), "high90": round(float(pct(s[k] + half_s[k])), 1),
             "p_high": round(float(ps[k]), 3), "class": "HIGH" if cls[k] else "LOW", "auto_score": round(float(pct(mu[k])), 1)} for k in range(len(te))]
    out = {"issue": "2026-10-01", "target_quarter": "2027-Q1", "lead": 1, "config": tag, "lam": lam, "lam_source": src, "lam_a": la, "lam_b": lb, "forecasts": rows}
    (OUT / "live.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    sp = OUT / "sealed_2027-Q1.json"
    if not sp.exists():
        sp.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), **out}, indent=1, default=float), newline="\n")
    print("seal", hashlib.sha256(sp.read_bytes()).hexdigest())
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"lock": lock, "eval": evaluate, "live": live}[sys.argv[1]]()
