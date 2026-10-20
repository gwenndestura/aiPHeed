"""E69 shared library (PROTOCOL.md): protocol check, the observed regional hunger outcome, information sets at each issue
date, and the Scale-1 Lead-2 hunger candidates R0-R5.

E69 reads E38-E68 files and never writes into them; outputs go under E69/out, E69/tables and E69/sealed.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E69 = Path(__file__).resolve().parents[1]
EXP = E69.parent
sys.path.insert(0, str(EXP / "E68_Resolve_E67_Critical_Failures" / "runner"))
import e68_lib as R  # noqa: E402

H, F, L, E, P2, np, pd, CW = R.H, R.F, R.L, R.E, R.P2, R.np, R.pd, R.CW
from scipy.stats import norm  # noqa: E402

OUT, TABLES, SEALED = E69 / "out", E69 / "tables", E69 / "sealed"
ORIGINS = list(range(L.qi("2021-Q4"), L.qi("2026-Q1") + 1))
FORWARD = [L.qi("2026-Q2"), L.qi("2026-Q3")]
C_ELEV, C_RISE, SIGMA_DEFAULT, NOISE_SE = 11.3, 5.0, 4.0, 1.6
MODELS = ["R0_RW", "R1_MEAN4", "R2_EXPMEAN", "R3_AR1", "R4_RIDGE", "R5_PRICE"]


def verify_protocol() -> str:
    want = (E69 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E69 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if got != want:
        raise SystemExit("E69 PROTOCOL.md changed after freezing")
    return got


def outcome() -> pd.Series:
    """Observed H(q): quarter mean of all SWS rounds (as T43); quarters without a round are absent."""
    r = pd.read_csv(L.SWS_FILE)
    r["q"] = r["quarter"].map(L.qi)
    return r.groupby("q")["H"].mean()


def posted(d, t) -> pd.Series:
    """Approved rounds posted before O(t), quarter means (the information set of origin t)."""
    return P2.h_series(d, t, False)


def base(hs: pd.Series, t: int) -> float:
    s = hs[hs.index <= t]
    return float(s.iloc[-1]) if len(s) else float("nan")


def regional_price(X, t) -> float:
    v = X.loc[X["t"] == t, "F_now"]
    return float(v.mean()) if len(v) else float("nan")


def pairs(d, X, t) -> pd.DataFrame:
    """Training pairs usable at origin t: origins t' whose target H(t'+2) was posted before O(t)."""
    hs = posted(d, t)
    rows = []
    for tp in range(L.qi("2021-Q2"), t - 1):
        if tp + 2 not in hs.index:
            continue
        hsp = posted(d, tp)
        b = base(hsp, tp)
        if not np.isfinite(b):
            continue
        rows.append({"t": tp, "y": float(hs[tp + 2]), "base": b, "mean4": float(hsp.iloc[-4:].mean()),
                     "expmean": float(hsp.mean()), "price": regional_price(X, tp)})
    return pd.DataFrame(rows, columns=["t", "y", "base", "mean4", "expmean", "price"])


def _ols(Xm, y):
    Xm = np.column_stack([np.ones(len(y)), Xm])
    beta, *_ = np.linalg.lstsq(Xm, y, rcond=None)
    res = y - Xm @ beta
    dof = max(len(y) - Xm.shape[1], 1)
    return beta, float(np.sqrt(np.sum(res ** 2) / dof))


def forecast(d, X, t) -> dict:
    """Every candidate's (H_hat, sigma) at origin t; None where a candidate is not estimable."""
    hs = posted(d, t)
    b = base(hs, t)
    P = pairs(d, X, t)
    out = {"base": b, "n_pairs": int(len(P))}

    def sig(err):
        err = np.asarray(err, float)
        err = err[np.isfinite(err)]
        return float(np.sqrt(np.mean(err ** 2))) if len(err) >= 4 else SIGMA_DEFAULT

    out["R0_RW"] = (b, sig(P["y"] - P["base"]) if len(P) else SIGMA_DEFAULT)
    out["R1_MEAN4"] = (float(hs[hs.index <= t].iloc[-4:].mean()), sig(P["y"] - P["mean4"]) if len(P) else SIGMA_DEFAULT)
    out["R2_EXPMEAN"] = (float(hs[hs.index <= t].mean()), sig(P["y"] - P["expmean"]) if len(P) else SIGMA_DEFAULT)
    if len(P) >= 6:
        beta, s = _ols(P[["base"]].to_numpy(float), P["y"].to_numpy(float))
        out["R3_AR1"] = (float(beta[0] + beta[1] * b), s)
    else:
        out["R3_AR1"] = None
    pr = regional_price(X, t)
    Pp = P.dropna(subset=["price"])
    if len(Pp) >= 8 and np.isfinite(pr):
        beta, s = _ols(Pp[["base", "price"]].to_numpy(float), Pp["y"].to_numpy(float))
        out["R5_PRICE"] = (float(beta[0] + beta[1] * b + beta[2] * pr), s)
    else:
        out["R5_PRICE"] = None
    try:
        hc = R.hunger(d, X, t)
    except Exception:          # the ridge needs the five-trigger frame (from 2021-Q3) and >= 6 pairs
        hc = None
    out["R4_RIDGE"] = (float(hc["H_hat"]), float(hc["rmse"])) if hc else None
    return out


def p_above(h_hat, sigma, c):
    return float(1 - norm.cdf((c - h_hat) / max(sigma, 1e-6)))
