"""E61 shared helpers: paths, sealed-file verification, labels and small statistics.

E61 audits E58's low 2027-Q1 forecasts. It reuses the E56 code path (e56_lib -> e55_lib -> e53_lib -> E46/E44/E41)
read-only and never writes into E56-E60 or backend/data.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E61 = Path(__file__).resolve().parents[1]
EXP = E61.parent
ROOT = EXP.parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, I7, L, P2, np, pd = G.E, G.F, G.I7, G.L, G.P2, G.np, G.pd
E57_SEALED = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"
E58_SEALED = EXP / "E58_Rising_Stress_Early_Warning" / "sealed" / "predictions.csv"
E58_EVENTS = EXP / "E58_Rising_Stress_Early_Warning" / "data" / "events.csv"
E56_FROZEN = EXP / "E56_LightGBM_Optimization" / "frozen" / "E56_TUNED_PROSPECTIVE_2027Q1.json"
E58_RECORD = BACKEND / "data" / "e58" / "e58_record.json"
ART = BACKEND / "data" / "e56" / "model"
OUT, TABLES, SEALED_DIR = E61 / "out", E61 / "tables", E61 / "sealed"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_sealed() -> dict:
    """The E57/E58 sealed forecasts are unchanged (their own .sha256 files)."""
    out = {}
    for p in (E57_SEALED, E58_SEALED):
        want = (p.parent / "predictions.csv.sha256").read_text().split()[0]
        got = sha(p)
        if got != want:
            raise SystemExit(f"{p} changed after sealing")
        out[str(p.relative_to(EXP))] = got
    return out


def dump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(obj, indent=1, default=float, sort_keys=False).encode("utf-8"))


def write_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(df.to_csv(index=False, float_format="%.6g").encode("utf-8"))   # LF, no CRLF (manifest hashes)


def rows50() -> pd.DataFrame:
    """The 50 E57/E58 rolling-origin rows (targets 2024-Q2..2026-Q3) with outcomes from the E58 events file."""
    S = pd.read_csv(E58_SEALED, dtype={"province_code": str})
    ev = pd.read_csv(E58_EVENTS, dtype={"province_code": str})
    R = S.merge(ev[["t", "province_code", "HIGH", "ONSET", "RISEP", "last_known_T43"]], on=["t", "province_code"], how="left")
    assert len(R) == 50 and R["HIGH"].notna().all()
    return R


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [float(max(0, c - h)), float(min(1, c + h))]


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def calib(y, p, n_boot=2000, seed=61, clusters=None) -> dict:
    """Brier, log loss, calibration-in-the-large, logistic calibration slope/intercept (Cox), with a
    quarter-cluster bootstrap CI when clusters are given."""
    from sklearn.linear_model import LogisticRegression
    y, p = np.asarray(y, int), np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)

    def one(y_, p_):
        out = {"brier": float(np.mean((p_ - y_) ** 2)),
               "log_loss": float(-np.mean(y_ * np.log(p_) + (1 - y_) * np.log(1 - p_))),
               "citl": float(y_.mean() - p_.mean()), "slope": None, "intercept": None}
        if len(set(y_)) == 2:
            lr = LogisticRegression(C=1e6, max_iter=1000).fit(logit(p_).reshape(-1, 1), y_)
            out["slope"], out["intercept"] = float(lr.coef_[0][0]), float(lr.intercept_[0])
        return out
    res = one(y, p)
    if clusters is not None:
        rng = np.random.default_rng(seed)
        cl = np.asarray(clusters)
        uq = np.unique(cl)
        draws = {k: [] for k in ("brier", "log_loss", "citl", "slope")}
        for _ in range(n_boot):
            idx = np.concatenate([np.where(cl == c)[0] for c in rng.choice(uq, len(uq))])
            o = one(y[idx], p[idx])
            for k in draws:
                if o[k] is not None:
                    draws[k].append(o[k])
        res["ci95"] = {k: [float(np.quantile(v, .025)), float(np.quantile(v, .975))] for k, v in draws.items() if v}
    return res


def reliability(y, p, edges=(0, .1, .2, .3, .5, .7, 1.0001)) -> list[dict]:
    y, p = np.asarray(y, int), np.asarray(p, float)
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = (p >= lo) & (p < hi)
        k, n = int(y[s].sum()), int(s.sum())
        out.append({"bin": f"[{lo:.1f},{min(hi, 1):.1f}{')' if hi < 1 else ']'}", "n": n,
                    "mean_p": float(p[s].mean()) if n else None, "observed_HIGH": k,
                    "observed_rate": k / n if n else None, "wilson95": wilson(k, n)})
    return out
