"""E71 index (PROTOCOL sections 3-4), pure numpy/pandas so that it can be unit-tested without the model library:
indicator percentiles against the 2021-22 reference, dimension scores, FIR71, threshold and class."""
import numpy as np
import pandas as pd

REF = (8084, 8091)                     # 2021-Q1 .. 2022-Q4 as year*4 + quarter-1
DIMS = {"ACCESS": ["a1", "a2", "a3"], "AVAILABILITY": ["v1", "v2"], "STABILITY": ["s1", "s2"]}
ADVERSE_HIGH = {"a1": True, "a2": True, "a3": False, "v1": False, "v2": False, "s1": True, "s2": True, "gap": True}
BINARY = {"s2"}
STRESS = 0.75
PCT = 60


def reference(ind: pd.DataFrame) -> dict:
    r = ind[(ind["q"] >= REF[0]) & (ind["q"] <= REF[1])]
    return {k: np.sort(r[k].dropna().to_numpy(float)) for k in ADVERSE_HIGH}


def pct(ref: np.ndarray, v, adverse_high: bool):
    """Mid-rank percentile in the adverse direction; NaN stays NaN."""
    v = np.asarray(v, float)
    out = np.full(v.shape, np.nan)
    ok = np.isfinite(v)
    if not len(ref):
        return out
    lo = np.searchsorted(ref, v[ok], "left")
    hi = np.searchsorted(ref, v[ok], "right")
    p = (lo + 0.5 * (hi - lo)) / len(ref)
    out[ok] = p if adverse_high else 1 - p
    return out


def score(ind: pd.DataFrame, ref: dict, access_key: str = "a1", drop_dim: str | None = None) -> pd.DataFrame:
    """Indicator percentiles, dimension scores, FIR71 (mean of dimensions; NaN unless all used dimensions exist)."""
    S = ind[["province_code", "q", "quarter"]].copy()
    for k in ADVERSE_HIGH:
        S[f"p_{k}"] = ind[k].to_numpy(float) if k in BINARY else pct(ref[k], ind[k], ADVERSE_HIGH[k])
    dims = {d: [access_key if i == "a1" else i for i in v] for d, v in DIMS.items()}
    for dname, items in dims.items():
        S[dname] = S[[f"p_{i}" for i in items]].mean(axis=1, skipna=True)
    use = [dn for dn in DIMS if dn != drop_dim]
    S["FIR71"] = S[use].mean(axis=1, skipna=False)
    S["n_stressed"] = (S[use] > STRESS).sum(axis=1)
    return S


def threshold(S: pd.DataFrame, pctl: float = PCT) -> float:
    r = S[(S["q"] >= REF[0]) & (S["q"] <= REF[1]) & S["FIR71"].notna()]
    return float(np.percentile(r["FIR71"], pctl))


def labels(S: pd.DataFrame, thr: float) -> pd.DataFrame:
    out = S.copy()
    out["HIGH"] = np.where(out["FIR71"].notna(), (out["FIR71"] > thr).astype(float), np.nan)
    return out
