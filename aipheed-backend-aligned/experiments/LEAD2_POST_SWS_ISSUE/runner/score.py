"""LEAD2_POST_SWS_ISSUE (PROTOCOL.md): Lead-2 forecast issued after the newest SWS round is published.

Order (stops on the first failure): protocol hash -> baseline reproduction -> parity of every recomputed term at the
original issue date -> leakage audit at the post-SWS issue date -> Evaluation A (official rows, R1-R7) -> Evaluation B
(independent 2002-2020, main and sensitivity dates) -> label-noise sensitivity. Read-only on every input; writes out/.

    python -B score.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOTD = HERE.parent
EXP = ROOTD.parent
OUT = ROOTD / "out"
sys.path.insert(0, str(EXP / "LEAD2_RELIABILITY_RESEARCH" / "common"))
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

import p2lib as P  # noqa: E402
import hmodels as HM  # noqa: E402

R, RV = P.R, P.RV
AREAS4 = ("NCR", "BL", "VIS", "MIN")
CAP_DAYS = 67
SEED = 2036
LOG: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


def frozen_ok():
    want = (ROOTD / "PROTOCOL_SHA256.txt").read_text().split()[0]
    if hashlib.sha256((ROOTD / "PROTOCOL.md").read_bytes()).hexdigest() != want:
        raise SystemExit("PROTOCOL.md changed after freezing")


# =============================================================================================== issue rule
def q_last_day(q: int) -> pd.Timestamp:
    return R.issue(q) - pd.Timedelta(days=1)                       # issue(q) = first day of quarter q+1


def last_pub(t: int) -> pd.Timestamp | None:
    r = R.rounds()
    g = r[(r["area"] == "BL") & (r["q"] == t)]
    return None if g.empty else pd.Timestamp(g["published"].max())


def post_issue(t: int) -> pd.Timestamp:
    o, cap, p = R.issue(t), q_last_day(t) + pd.Timedelta(days=CAP_DAYS), last_pub(t)
    cand = cap if p is None else min(p + pd.Timedelta(days=1), cap)
    return max(o, cand)


def cpi_newest(d: pd.Timestamp) -> int:
    """Newest CPI month (ym = year*12 + month-1) available at date d: month M is available from the first day of M+2."""
    return d.year * 12 + d.month - 1 - 2


# =============================================================================================== recomputed terms
def setup():
    import l2_lib as X
    X.U.setup()
    return X


def h4_at(X, iss: str, t: int, k: int) -> tuple[float, dict]:
    """a3.h4 with the issue date as a parameter; served fallback (pi_H4 = H1 = ch1_lib.pi_h at the same date)."""
    C, FM = X.C, X.FM
    kn = C.bl_known(iss)
    if not kn:
        return float("nan"), {}
    q_last, h_last = kn[-1][0], kn[-1][1]
    h = (t + k) - q_last
    errs = []
    for a in AREAS4:
        d = {x[0]: x[1] for x in FM.known(iss, a, "primary")}
        errs += [d[q + h] - d[q] for q in d if q + h in d]
    info = {"newestSwsQ": R.qs(q_last), "newestSwsPublished": str(kn[-1][3])[:10], "h_last": h_last, "trueHorizon": int(h)}
    if len(errs) >= 8:
        sig = math.sqrt(float(np.mean(np.square(errs))))
        return float(norm.cdf((h_last - R.H_LINE) / max(sig, 0.5))), {**info, "fallback": False}
    d = {x[0]: x[1] for x in kn}                                    # served fallback: ch1_lib.pi_h at the same date
    e1 = [d[q + h] - d[q] for q in d if q + h in d]
    sig = math.sqrt(np.mean(np.square(e1))) if len(e1) >= 4 else C.SIGMA_H_FALLBACK
    return float(norm.cdf((h_last - R.H_LINE) / max(sig, 0.5))), {**info, "fallback": True}


def kal_at(iss: pd.Timestamp, t: int, k: int) -> float:
    """hmodels.kalman("BL", t, k, AREAS4) with the issue date as a parameter."""
    o = HM._series("BL", iss)
    if len(o) < 8:
        return float("nan")
    phi, tau2 = HM._kfit(AREAS4, iss)
    mu = float(np.mean([x[1] for x in o]))
    _, q_last, m, v = HM._filter(o, mu, phi, tau2)
    h = (t + k) - q_last
    mean = mu + phi ** h * m
    var = phi ** (2 * h) * v + tau2 * sum(phi ** (2 * i) for i in range(h))
    return float(norm.cdf((mean - R.H_LINE) / math.sqrt(var + o[-1][2])))


def rw_at(iss: pd.Timestamp, target: int) -> dict | None:
    """rlib.forecast RW (persistence probability) for BL with the issue date as a parameter."""
    d = R.known("BL", iss)
    if not d:
        return None
    q_last = max(d)
    h = target - q_last
    pr = R.pairs(AREAS4, iss, h)
    if len(pr) < R.MIN_PAIRS:
        return None
    sig = math.sqrt(float(np.mean((pr["y1"] - pr["y0"]) ** 2)))
    return {"RW": R.prob(d[q_last], sig), "x_last": d[q_last], "q_last": q_last, "h": h}


def persist_clim_at(X, iss: str, t: int, provs: list[str], cutoff: int) -> tuple[dict, float]:
    """ch1_lib.persist_si and the CLIM_p of ch1_lib.known_t43c, with both cutoffs (SWS date, CPI month) as parameters."""
    C, FM, L, E = X.C, X.FM, X.L, X.E
    th = L.e40_spec()
    kn = C.bl_known(iss)
    hung = bool(kn) and kn[-1][1] > R.H_LINE
    yoy = E.data()[0].yoy
    y = yoy[yoy["ym"].isin([cutoff - 2, cutoff - 1, cutoff])]
    lab = C.labels()
    full = FM.rounds("primary")
    full = full[full["area"] == "BL"]
    done = {q for q, g in full.groupby("q") if (g["published"] < iss).all()}
    ok = lab[lab["q"].isin(done) & (lab["q"] <= t) & ((lab["q"] * 3 + 2) <= cutoff)]
    clim = float(ok["y"].mean()) if len(ok) else 0.0
    out = {}
    for p in provs:
        f = y[(y["province_code"] == p) & (y["commodity"] == "food")]["yoy"]
        a = y[(y["province_code"] == p) & (y["commodity"] == "all_items")]["yoy"]
        out[p] = clim if (len(f) < 3 or len(a) < 3) else float(hung and (f.mean() > th["food"][p] or (f.mean() - a.mean()) > th["gap"][p]))
    return out, clim


# =============================================================================================== metrics
def metrics(y, p) -> dict:
    y, p = np.asarray(y, int), np.asarray(p, float)
    yh = (p >= .5).astype(int)
    tp, fp, fn, tn = [int(((yh == a) & (y == b)).sum()) for a, b in ((1, 1), (1, 0), (0, 1), (0, 0))]
    r = lambda a, b: a / b if b else None  # noqa: E731
    rec, spec, prec = r(tp, tp + fn), r(tn, tn + fp), r(tp, tp + fp)
    return {"n": int(len(y)), "TP": tp, "FP": fp, "FN": fn, "TN": tn, "accuracy": (tp + tn) / len(y) if len(y) else None,
            "balanced": (rec + spec) / 2 if rec is not None and spec is not None else None, "precision": prec,
            "recall": rec, "specificity": spec, "auc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else None,
            "brier": float(np.mean((p - y) ** 2)) if len(y) else None}


def with_ci(g: pd.DataFrame, col: str, B: int = 2000) -> dict:
    m = metrics(g["y"], g[col])
    qs = g["q"].to_numpy()
    uq = np.unique(qs)
    idx = {u: np.where(qs == u)[0] for u in uq}
    rng = np.random.default_rng(SEED)
    keys = ("accuracy", "balanced", "precision", "recall", "specificity", "auc", "brier")
    bs = {k: [] for k in keys}
    y, p = g["y"].to_numpy(int), g[col].to_numpy(float)
    for _ in range(B):
        ii = np.concatenate([idx[u] for u in rng.choice(uq, len(uq))])
        mm = metrics(y[ii], p[ii])
        for k in keys:
            if mm[k] is not None:
                bs[k].append(mm[k])
    m["CI95"] = {k: [round(float(np.quantile(v, .025)), 4), round(float(np.quantile(v, .975)), 4)] if v else None for k, v in bs.items()}
    return m


def onsets(g: pd.DataFrame, col: str, labels: dict) -> str:
    on = [(labels.get((pc, q - 1)) == 0 and y == 1) for pc, q, y in zip(g["province_code"], g["q"], g["y"])]
    o = g[on]
    return f"{int((o[col] >= .5).sum())}/{len(o)}"


def thirds(g: pd.DataFrame, col: str) -> list[dict]:
    qs = sorted(g["q"].unique())
    out = []
    for th in np.array_split(np.array(qs), 3):
        h = g[g["q"].isin(th)]
        m = metrics(h["y"], h[col])
        out.append({"quarters": f"{R.qs(th[0])}..{R.qs(th[-1])}", "accuracy": round(m["accuracy"], 3),
                    "recall": None if m["recall"] is None else round(m["recall"], 3), "brier": round(m["brier"], 4)})
    return out


def boot_p(l: np.ndarray, block: int = 1, B: int = 5000) -> float:
    n = len(l)
    rng = np.random.default_rng(SEED)
    if block == 1:
        bs = l[rng.integers(0, n, size=(B, n))].mean(1)
    else:
        nb = math.ceil(n / block)
        st = rng.integers(0, n - block + 1, size=(B, nb))
        bs = l[(st[:, :, None] + np.arange(block)).reshape(B, -1)[:, :n]].mean(1)
    return float(np.mean(bs >= 0))


# =============================================================================================== main
def main():
    frozen_ok()
    X = setup()
    C, E = X.C, X.E
    res = {"protocolSha256": hashlib.sha256((ROOTD / "PROTOCOL.md").read_bytes()).hexdigest()}

    # ---------------------------------------------------------------- 1. reproduction (stop on mismatch)
    d = P.load_p0h4()
    cm = lambda s: f"{s['TP']}/{s['FP']}/{s['FN']}/{s['TN']}"  # noqa: E731
    rep = {k: cm(RV.scores(d[d["lead"] == k])) for k in (1, 2)}
    res["reproduction"] = {"lead1": rep[1], "lead2": rep[2]}
    say("reproduction", rep)
    if rep[1] != "11/5/6/48" or rep[2] != "6/4/11/44":
        raise SystemExit("baseline reproduction failed")
    g = d[d["lead"] == 2].copy().reset_index(drop=True)
    provs = sorted(g["province_code"].unique())

    # ---------------------------------------------------------------- 2. parity at the original issue date
    par = []
    for t in sorted(g["t"].unique()):
        t = int(t)
        stored = g[g["t"] == t].iloc[0]
        h4o, _ = h4_at(X, E.issue(t), t, 2)
        kalo = kal_at(R.issue(t), t, 2)
        pso, clo = persist_clim_at(X, E.issue(t), t, provs, X.L.m0_of(t))
        gg = g[g["t"] == t].set_index("province_code")
        par.append({"origin": R.qs(t), "H4": abs(h4o - stored["pi_H4"]), "KAL": abs(kalo - HM.kalman("BL", t, 2, AREAS4)),
                    "CLIM": abs(clo - stored["CLIM_p"]), "PERSIST": max(abs(pso[p] - gg.loc[p, "PERSIST-SI_p"]) for p in gg.index)})
    worst = {k: max(x[k] for x in par) for k in ("H4", "KAL", "CLIM", "PERSIST")}
    res["parity_maxAbs"] = worst
    say("parity at O(t), max |diff|:", worst)
    if max(worst.values()) > 1e-6:
        (OUT / "results.json").write_text(json.dumps({**res, "parity": par}, indent=1, default=str), encoding="utf-8")
        raise SystemExit("parity failed: recomputed terms do not equal the served ones at O(t)")

    # ---------------------------------------------------------------- 3. post-SWS issue, leakage audit
    audit = []
    for t in sorted(g["t"].unique()):
        t = int(t)
        o2 = post_issue(t)
        iss = o2.date().isoformat()
        h4p, info = h4_at(X, iss, t, 2)
        kp = kal_at(o2, t, 2)
        cut = cpi_newest(o2)
        ps, cl = persist_clim_at(X, iss, t, provs, cut)
        lead_days = (q_last_day(t + 2) - o2).days
        a = {"origin": R.qs(t), "target": R.qs(t + 2), "O": str(R.issue(t).date()), "O_post": iss,
             "lastRoundOfQuarterT": None if last_pub(t) is None else str(last_pub(t).date()),
             "capped": bool(last_pub(t) is None or last_pub(t) + pd.Timedelta(days=1) > q_last_day(t) + pd.Timedelta(days=CAP_DAYS)),
             **info, "cpiNewestMonth": f"{cut // 12}-{cut % 12 + 1:02d}", "leadDaysPost": lead_days,
             "leadDaysOriginal": (q_last_day(t + 2) - R.issue(t)).days, "H4_post": h4p, "KAL_post": kp, "CLIM_post": cl}
        # leakage assertions
        if not (info["newestSwsPublished"] < iss):
            raise SystemExit(f"LEAKAGE: SWS round published {info['newestSwsPublished']} not before {iss}")
        if not (pd.Timestamp(year=(cut + 2) // 12, month=(cut + 2) % 12 + 1, day=1) <= o2):
            raise SystemExit(f"LEAKAGE: CPI month {a['cpiNewestMonth']} not available at {iss}")
        if not (R.issue(t) <= o2):
            raise SystemExit("LEAKAGE: P0_price issued after O'(t)")
        r = R.rounds()
        used = r[(r["area"] == "BL") & (r["published"] < o2)]
        if (used["published"] >= o2).any():
            raise SystemExit("LEAKAGE: Kalman input published on or after O'(t)")
        audit.append(a)
        m = g["t"] == t
        g.loc[m, "pi_H4_post"], g.loc[m, "pi_KAL_post"], g.loc[m, "CLIM_post"] = h4p, kp, cl
        g.loc[m, "PERSIST_post"] = g.loc[m, "province_code"].map(ps)
    res["leakageAudit"] = {"passed": True, "rows": audit}
    say("\nissue dates and information used (all inputs published before O'):")
    for a in audit:
        say(f"  {a['origin']}->{a['target']}  O {a['O']}  O' {a['O_post']}{' (cap)' if a['capped'] else ''}  newest SWS {a['newestSwsQ']} "
            f"(pub {a['newestSwsPublished']}, H {a['h_last']})  h {a['trueHorizon']}  CPI to {a['cpiNewestMonth']}  lead {a['leadDaysPost']}d (was {a['leadDaysOriginal']}d)")
    ld = np.array([a["leadDaysPost"] for a in audit])
    res["leadDays"] = {"post": {"median": float(np.median(ld)), "min": int(ld.min()), "max": int(ld.max())},
                       "original": {"median": float(np.median([a["leadDaysOriginal"] for a in audit]))}}
    say("lead days", res["leadDays"])

    # ---------------------------------------------------------------- 4. Evaluation A: official rows
    g["M0"] = g["pi_H4_post"] * g["P0_price"]
    g["M1"] = g["pi_KAL_post"] * g["P0_price"]
    g["ALWAYS_LOW"] = 0.0
    lab = C.labels()
    labd = {(p, int(q)): int(y) for p, q, y in zip(lab["province_code"], lab["q"], lab["y"])}
    post = g.copy()
    post["PERSIST-SI_p"], post["CLIM_p"] = post["PERSIST_post"], post["CLIM_post"]
    A = {}
    for name, col, frame, rules_base in (("P0H4_original_issue", RV.P, g, "original"), ("M0_post_SWS", "M0", post, "post"),
                                         ("M1_post_SWS_Kalman", "M1", post, "post"), ("PERSIST-SI_post", "PERSIST_post", post, "post"),
                                         ("CLIM_post", "CLIM_post", post, "post"), ("ALWAYS-LOW", "ALWAYS_LOW", post, "post")):
        e = {"metrics": with_ci(frame, col), "onsetsAnticipated": onsets(frame, col, labd), "byThird": thirds(frame, col)}
        if name in ("P0H4_original_issue", "M0_post_SWS", "M1_post_SWS_Kalman"):
            o = P.official_rules(frame, col)
            e["rules"] = {k.split()[0]: {"pass": v["pass"], "value": v["value"]} for k, v in o["rules"].items()}
            e["failed"], e["passesAll"] = o["failed"], o["passesAll"]
            e["baselinesUsed"] = rules_base
        A[name] = e
    res["evaluationA"] = A
    say("\nEvaluation A (65 official Lead-2 rows, T43c):")
    for k, e in A.items():
        m = e["metrics"]
        say(f"  {k:22s} acc {m['accuracy']:.3f} {m['CI95']['accuracy']} bal {m['balanced'] or 0:.3f} {m['CI95']['balanced']} "
            f"P {m['precision'] or 0:.2f} R {m['recall'] or 0:.2f} spec {m['specificity'] or 0:.2f} AUC {m['auc'] or 0:.3f} "
            f"Brier {m['brier']:.4f} {m['CI95']['brier']} CM {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} onsets {e['onsetsAnticipated']}"
            + (f" | fails {e['failed']}" if "failed" in e else ""))
        say(f"      by third {e['byThird']}")

    # ---------------------------------------------------------------- 5. Evaluation B: independent 2002-2020
    obs = R.observed()

    def evalB(label: str) -> dict:
        rows = []
        for tgt in range(R.qi("2002-Q1"), R.qi("2020-Q4") + 1):
            if ("BL", tgt) not in obs:
                continue
            t = tgt - 2
            o2 = post_issue(t)
            rw = rw_at(o2, tgt)
            k = kal_at(o2, t, 2)
            if rw is None or math.isnan(k):
                continue
            r = R.rounds()
            bl = r[r["area"] == "BL"]
            pubq = bl.groupby("q")["published"].max()
            kq = [q for q, p in pubq.items() if p < o2]
            clim = float(np.mean([obs[("BL", q)] > R.H_LINE for q in kq])) if kq else float("nan")
            rows.append({"t": t, "q": tgt, "target": R.qs(tgt), "O_post": str(o2.date()), "y": int(obs[("BL", tgt)] > R.H_LINE),
                         "H1": rw["RW"], "KAL": k, "PERSIST": float(rw["x_last"] > R.H_LINE), "CLIM": clim, "ALWAYS_LOW": 0.0,
                         "h": rw["h"], "leadDays": (q_last_day(tgt) - o2).days})
        b = pd.DataFrame(rows).dropna(subset=["CLIM"])
        out = {"rows": len(b), "period": f"{b['target'].min()}..{b['target'].max()}", "prevalence": float(b["y"].mean()),
               "trueHorizon": b["h"].value_counts().sort_index().to_dict(), "leadDaysMedian": float(b["leadDays"].median())}
        for c in ("KAL", "H1", "PERSIST", "CLIM", "ALWAYS_LOW"):
            out[c] = metrics(b["y"], b[c])
        l = ((b["KAL"] - b["y"]) ** 2 - (b["H1"] - b["y"]) ** 2).to_numpy()
        out["KAL_vs_H1"] = {"diff": float(l.mean()), "p_iid": boot_p(l), "p_block4": boot_p(l, 4)}
        out["gate"] = {"brier": bool(l.mean() < 0 and out["KAL_vs_H1"]["p_iid"] < .10),
                       "balanced": bool((out["KAL"]["balanced"] or 0) >= (out["H1"]["balanced"] or 0))}
        out["gatePasses"] = all(out["gate"].values())
        say(f"\nEvaluation B [{label}] {out['rows']} quarters {out['period']} prevalence {out['prevalence']:.2f} horizons {out['trueHorizon']} lead median {out['leadDaysMedian']}d")
        for c in ("KAL", "H1", "PERSIST", "CLIM", "ALWAYS_LOW"):
            m = out[c]
            say(f"  {c:10s} acc {m['accuracy']:.3f} bal {m['balanced'] or 0:.3f} P {m['precision'] or 0:.2f} R {m['recall'] or 0:.2f} "
                f"AUC {m['auc'] or 0:.3f} Brier {m['brier']:.4f} CM {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']}")
        say(f"  KAL vs H1 {out['KAL_vs_H1']} gate {out['gate']} -> {out['gatePasses']}")
        b.to_csv(OUT / f"evalB_rows_{label}.csv", index=False, lineterminator="\n", float_format="%.5f")
        return out

    res["evaluationB_main"] = evalB("main")
    base_rounds = R.rounds
    shifted = base_rounds().copy()
    pre = shifted["q"] < R.qi("2021-Q1")
    shifted.loc[pre, "published"] = shifted.loc[pre, "published"] + pd.Timedelta(days=30)
    R.rounds = lambda: shifted
    for f in (R.known, HM._series, HM._kfit):
        f.cache_clear()
    try:
        res["evaluationB_sensitivity"] = evalB("sensitivity_plus30d")
    finally:
        R.rounds = base_rounds
        for f in (R.known, HM._series, HM._kfit):
            f.cache_clear()

    # ---------------------------------------------------------------- 6. label-noise sensitivity (official rows)
    FM = X.FM
    pr = FM.rounds("primary")
    bl = pr[pr["area"] == "BL"]
    lv = {int(q): (float(gq["H"].mean()), float((gq["moe"].mean() / 1.96) / np.sqrt(len(gq)))) for q, gq in bl.groupby("q")}
    border = sorted({int(q) for q in post["q"] if abs(lv[int(q)][0] - R.H_LINE) <= 1.0})

    def fast(y, p, q, base):
        yh = (p >= .5).astype(int)
        tp, fp = ((yh == 1) & (y == 1)).sum(), ((yh == 1) & (y == 0)).sum()
        fn, tn = ((yh == 0) & (y == 1)).sum(), ((yh == 0) & (y == 0)).sum()
        rec = tp / (tp + fn) if tp + fn else 0
        spec = tn / (tn + fp) if tn + fp else 0
        prec = tp / (tp + fp) if tp + fp else 0
        acc = (tp + tn) / len(y)
        qs = np.unique(q)
        a = lambda m: float((yh[m] == y[m]).mean())  # noqa: E731
        return {"R2": acc >= .75, "R3": (rec + spec) / 2 >= .70,
                "R4": acc > float((y == 0).mean()) and acc > float(((base >= .5).astype(int) == y).mean()),
                "R6": prec >= .6 and rec >= .6,
                "R7": min(a(np.isin(q, t)) for t in np.array_split(qs, 3)) >= .6 and min(a(q != u) for u in qs) >= .7}
    noise = {"borderlineQuarters": [(R.qs(q), lv[q][0]) for q in border]}
    price = post["price"].to_numpy(int)
    qv = post["q"].to_numpy(int)
    for col in ("M0", "M1"):
        p = post[col].to_numpy(float)
        base = post["PERSIST_post"].to_numpy(float)
        y0 = post["y"].to_numpy(int)
        res_c = {"observed": {k: bool(v) for k, v in fast(y0, p, qv, base).items()}, "flips": {}}
        for x in border + ["all"]:
            sel = np.isin(qv, border) if x == "all" else (qv == x)
            hung = (np.array([lv[int(u)][0] for u in qv]) > R.H_LINE).astype(int)
            hung = np.where(sel, 1 - hung, hung)
            res_c["flips"][R.qs(x) if x != "all" else "all"] = {k: bool(v) for k, v in fast(hung * price, p, qv, base).items()}
        rng = np.random.default_rng(SEED)
        cnt = {k: 0 for k in res_c["observed"]}
        alln = 0
        for _ in range(2000):
            draw = {u: rng.normal(lv[int(u)][0], lv[int(u)][1]) for u in np.unique(qv)}
            yy = (np.array([draw[u] for u in qv]) > R.H_LINE).astype(int) * price
            if 0 < yy.sum() < len(yy):
                f = fast(yy, p, qv, base)
                for kk, vv in f.items():
                    cnt[kk] += int(vv)
                alln += int(all(f.values()))
        res_c["monteCarloPassRate"] = {k: round(v / 2000, 3) for k, v in cnt.items()}
        res_c["monteCarloAllPass"] = round(alln / 2000, 3)
        noise[col] = res_c
    res["labelNoise"] = noise
    say("\nlabel noise:", json.dumps(noise))

    # ---------------------------------------------------------------- 7. decision (protocol section 9)
    dec = {}
    for name, comp in (("M0", None), ("M1", "KAL")):
        a_pass = A[f"{name}_post_SWS" if name == "M0" else "M1_post_SWS_Kalman"]["passesAll"]
        b_pass = False if comp is None else (res["evaluationB_main"]["gatePasses"] and res["evaluationB_sensitivity"]["gatePasses"])
        dec[name] = {"officialR1R7": a_pass, "independentGate": b_pass if comp else "not passable: its hunger component is persistence (protocol §7)",
                     "A": bool(a_pass and b_pass)}
    res["decision"] = {"perModel": dec, "overall": "A" if any(v["A"] for v in dec.values()) else "C"}
    say("\nDECISION", json.dumps(res["decision"]))
    OUT.mkdir(exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    post[["t", "q", "province_code", "y", "hunger", "price", "pi_H4", "pi_H4_post", "pi_KAL_post", "P0_price", RV.P, "M0", "M1",
          "PERSIST-SI_p", "CLIM_p", "PERSIST_post", "CLIM_post"]].to_csv(OUT / "evalA_rows.csv", index=False, lineterminator="\n", float_format="%.6f")
    (OUT / "log.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
