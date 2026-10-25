"""E111 library (PROTOCOL.md): new panel candidates (DT, BRK, ASYM), the BL 12-family LightGBM and family screen,
true horizons, change classes, surge cost, interval coverage and the extended reliability rule.
E110 data, vintages, LLR and tests are imported unchanged; E109 provides the BL LightGBM and its pairs."""
from __future__ import annotations

import functools
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E111 = HERE.parent
sys.path.insert(0, str(E111.parent / "E110_Hunger_Generalization" / "runner"))
import e110_lib as F  # noqa: E402

E, H9, np, pd = F.E, F.H9, F.np, F.pd
OUT = E111 / "out"
BREAK_Q = E.qi("2025-Q2")
PANEL = ["RW", "MA2", "LLR", "DT", "BRK", "ASYM"]
NEW = ["DT", "BRK", "ASYM"]
LEADS_PANEL = (1, 2, 3, 4, 5, 6)
LEADS_BL = (1, 2, 3, 4)
INFERRED = {("NCR", "2021-07-28"), ("VIS", "2021-07-28"), ("MIN", "2021-07-28")}
_ORIG_ROUNDS = F.rounds
_E110_DM = F._dm_signed


def dm_nw(d, h: int) -> dict:
    """ADDENDUM_1: one-sided HLN-corrected Diebold-Mariano test with Bartlett-weighted (Newey-West) variance, lag h-1."""
    from scipy.stats import t as tdist
    d = np.asarray(d, float)
    n = len(d)
    if n < 3:
        return {"n": n, "p": None}
    dbar = float(d.mean())
    dc = d - dbar
    lag = min(max(h - 1, 0), n - 1)
    v = float(np.dot(dc, dc) / n) + 2 * sum((1 - j / (lag + 1)) * float(np.dot(dc[j:], dc[:-j]) / n) for j in range(1, lag + 1))
    if v <= 0:
        return {"n": n, "mean": dbar, "p": None, "note": "zero variance"}
    stat = dbar / math.sqrt(v / n) * math.sqrt(max((n + 1 - 2 * h + h * (h - 1) / n) / n, 1e-9))
    return {"n": n, "mean": dbar, "stat": stat, "p": float(tdist.cdf(stat, df=n - 1))}


F._dm_signed = dm_nw            # E110's decide() resolves this name at call time; E110 files are not modified


def set_sensitivity(noinf: bool = False, voters: bool = False) -> None:
    """S-NOINF (drop the inferred June-2021 cells) and S-VOTERS; clears every cache."""
    F.set_options(voters=voters)

    @functools.lru_cache(maxsize=1)
    def filtered():
        r = _ORIG_ROUNDS()
        if noinf:
            r = r[~r.apply(lambda x: (x["area"], x["published"]) in INFERRED, axis=1)]
        return r
    F.rounds = filtered if noinf else _ORIG_ROUNDS
    for f in (F.known, F.forecast, F.residual_pairs, F._pooled_q, forecast, _phi):
        f.cache_clear()


# ================================================================================================ panel candidates
def _slope(s) -> float:
    if len(s) < 2:
        return 0.0
    (q0, h0, _), (q1, h1, _) = s[-2], s[-1]
    return (h1 - h0) / (q1 - q0)


@functools.lru_cache(maxsize=4096)
def _phi(t: int, k: int) -> float:
    """Pooled least-squares momentum coefficient on pairs whose target was known at O(t), clipped to [0, 1]."""
    xs, ys = [], []
    for a in F.AREAS:
        kn = {q: h for q, h, _ in F.known(E.issue(t), a)}
        for tp in range(E.FIRST_ORIGIN, t):
            q = tp + k
            if q not in kn:
                continue
            s = F.known(E.issue(tp), a)
            if len(s) < 2:
                continue
            g = q - s[-1][0]
            xs.append(_slope(s) * g)
            ys.append(kn[q] - s[-1][1])
    if len(xs) < 8:
        return 0.0
    x, y = np.array(xs), np.array(ys)
    return float(np.clip((x @ y) / (x @ x), 0.0, 1.0)) if x @ x > 0 else 0.0


@functools.lru_cache(maxsize=50000)
def forecast(method: str, t: int, k: int, area: str) -> dict | None:
    base = F.forecast("RW", t, k, area)
    if base is None:
        return None
    s = F.known(E.issue(t), area)
    out = {"h_last": base["h_last"], "h_last_quarter": base["h_last_quarter"], "true_horizon": t + k - s[-1][0]}
    if method in ("RW", "MA2", "LLR"):
        f = F.forecast(method, t, k, area)["forecast"]
    elif method == "DT":
        ph = _phi(t, k)
        f = s[-1][1] + ph * _slope(s) * (t + k - s[-1][0])
        out["phi"] = ph
    elif method == "BRK":
        post = [x for x in s if x[0] >= BREAK_Q]
        if t + k >= BREAK_Q and post:
            f, _ = F.llr(tuple(post), F._pooled_q(E.issue(t)))
            out["restarted"] = True
        else:
            f = F.forecast("LLR", t, k, area)["forecast"]
            out["restarted"] = False
    elif method == "ASYM":
        f = max(base["h_last"], F.forecast("LLR", t, k, area)["forecast"])
    else:
        raise ValueError(method)
    out["forecast"] = float(f)
    return out


def sigma(method: str, t: int, k: int, area: str) -> float:
    kn = {q: h for q, h, _ in F.known(E.issue(t), area)}
    errs = []
    for tp in range(E.FIRST_ORIGIN, t - k + 1):
        if tp + k in kn:
            f = forecast(method, tp, k, area)
            if f is not None:
                errs.append(kn[tp + k] - f["forecast"])
    if len(errs) >= 4:
        return float(math.sqrt(np.mean(np.square(errs))))
    v = [h for _, h, _ in F.known(E.issue(t), area)]
    return float(np.std(np.diff(v), ddof=1)) if len(v) > 2 else 4.0


def _margin(area: str, q: int) -> float:
    r = F.rounds()
    g = r[(r["area"] == area) & (r["q"] == q)]
    return float(np.sqrt(g["R"].mean()) * 1.959964)


def evaluate_panel(k: int) -> pd.DataFrame:
    rows = []
    for a in F.AREAS:
        for q in F.outcome_quarters(a):
            t = q - k
            if t < E.FIRST_ORIGIN or q > E.LAST_OUTCOME:
                continue
            fs = {m: forecast(m, t, k, a) for m in PANEL}
            if any(v is None for v in fs.values()):
                continue
            y = F.outcome(q, a)
            hl = fs["RW"]["h_last"]
            m_ = _margin(a, E.qi(fs["RW"]["h_last_quarter"]))
            r = {"area": a, "q": q, "quarter": E.qs(q), "t": t, "origin": E.qs(t), "lead": k, "y": y, "h_last": hl,
                 "true_horizon": fs["RW"]["true_horizon"], "margin_last": m_, "rising": int(y > hl),
                 "change_class": "sharp_increase" if y - hl > m_ else ("sharp_decrease" if y - hl < -m_ else "stable")}
            for m in PANEL:
                r[m] = fs[m]["forecast"]
                r[f"{m}_sigma"] = sigma(m, t, k, a)
            rows.append(r)
    df = pd.DataFrame(rows)
    return df.sort_values(["q", "area"]).reset_index(drop=True) if len(df) else df


# ================================================================================================ BL indicator models
def fam_forecast(fam: str, t: int, k: int, rule: str = "primary") -> float | None:
    tr = H9.pairs(t, k, rule)
    if len(tr) < H9.MIN_PAIRS:
        return None
    cols = [c for c in E.COLUMNS if E.FAMILY_OF[c] == fam]
    x = H9.regional_features(k).loc[t]
    hl = H9.h_last(t, rule)[1]
    tr = tr.rename(columns={"dy": "res"})
    return hl + F._ridge(tr, cols, x)


def evaluate_bl(k: int, rule: str = "primary") -> pd.DataFrame:
    rows = []
    for q in H9.outcome_quarters(rule):
        t = q - k
        if t < E.FIRST_ORIGIN or q > E.LAST_OUTCOME:
            continue
        rw = H9.forecast("RW", t, k, rule)
        lg = H9.forecast("LGBM", t, k, rule)
        if rw is None or lg is None:
            continue
        y = H9.outcome(q, rule)
        r = {"q": q, "quarter": E.qs(q), "t": t, "lead": k, "y": y, "h_last": rw["h_last"], "RW": rw["forecast"],
             "LGBM12": lg["forecast"], "rising": int(y > rw["h_last"]), "area": "BL",
             "LGBM12_sigma": H9.sigma("LGBM", t, k, rule), "RW_sigma": H9.sigma("RW", t, k, rule)}
        for fam in E.FAMILIES:
            r[f"FAM-{fam}"] = fam_forecast(fam, t, k, rule)
        m_ = _margin("BL", E.qi(rw["h_last_quarter"]))                    # published margin of the latest BL reading
        r["margin_last"] = m_
        r["change_class"] = "sharp_increase" if y - rw["h_last"] > m_ else ("sharp_decrease" if y - rw["h_last"] < -m_ else "stable")
        rows.append(r)
    return pd.DataFrame(rows)


# ================================================================================================ metrics and rule
def surge(df: pd.DataFrame, m: str) -> dict:
    s = df[df["change_class"] == "sharp_increase"]
    if not len(s):
        return {"n": 0}
    under = (s["y"] - s[m]).clip(lower=0)
    return {"n": len(s), "quarters": int(s["q"].nunique()), "mean_underprediction": float(under.mean()),
            "miss_rate": float((s[m] < s["h_last"] + s["margin_last"] / 2).mean())}


def coverage(df: pd.DataFrame, m: str) -> float | None:
    if f"{m}_sigma" not in df:
        return None
    return float((np.abs(df["y"] - df[m]) <= 1.2816 * df[f"{m}_sigma"]).mean())


def by_class(df: pd.DataFrame, m: str) -> dict:
    return {c: {"n": int(len(g)), "mae": float(np.abs(g[m] - g["y"]).mean()), "mae_rw": float(np.abs(g["RW"] - g["y"]).mean())}
            for c, g in df.groupby("change_class")}


def by_true_horizon(frames: list[pd.DataFrame], methods) -> dict:
    allr = pd.concat(frames, ignore_index=True)
    return {str(int(h)): {"rows": int(len(g)), "quarters": int(g["q"].nunique()),
                          **{m: float(np.abs(g[m] - g["y"]).mean()) for m in methods}}
            for h, g in allr.groupby("true_horizon")}


def decide(df: pd.DataFrame, m: str, k: int, bl: pd.DataFrame) -> dict:
    d = F.decide(df, m, k, bl)
    s_m, s_rw = surge(df, m), surge(df, "RW")
    c = dict(d["criteria"])
    c["P7"] = bool(s_m.get("n", 0) and s_m["mean_underprediction"] <= s_rw["mean_underprediction"])
    cov = coverage(df, m)
    c["P8"] = bool(cov is not None and cov >= 0.70)
    if d["status"] == "insufficient evidence":
        st = "insufficient evidence"
    elif all(c[x] for x in ("P1", "P2", "P3", "P4", "P5", "P7", "P8")):
        st = "provisional"
    else:
        st = "not reliable"
    return {**d, "criteria": c, "failed": [x for x, v in c.items() if not v], "status": st, "surge": s_m,
            "surge_rw": s_rw, "coverage80": cov}


def holm(ps: dict) -> dict:
    items = sorted((p, f) for f, p in ps.items() if p is not None)
    n, out, run = len(items), {}, 0.0
    for i, (p, f) in enumerate(items):
        run = max(run, min(1.0, (n - i) * p))
        out[f] = run
    return out


def write_json(p, o):
    F.write_json(p, o)


def sha256(p):
    return F.sha256(p)
