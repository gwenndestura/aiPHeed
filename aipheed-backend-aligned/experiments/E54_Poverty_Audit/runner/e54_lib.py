"""E54 library (PROTOCOL.md): the provincial poverty inputs POV / SUB / FE, their as-of and look-ahead encodings,
the paired quarter-cluster Brier bootstrap and the section-5 decision rule.

Kept free of the model libraries so that both runners (C1/C2 in one process, C3 under the E32 guard in another) and
the tests import it unchanged. Quarter index t = year * 4 + (quarter - 1), as in e41_lib and e32_lib.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

E54 = Path(__file__).resolve().parents[1]
DATA = E54 / "data"
SAE_FILE = DATA / "sae2021_calabarzon_municipal.csv"
SUB_FILE = DATA / "psa_subsistence_population_2021_2023.csv"
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
BY_NAME = {v: k for k, v in NAMES.items()}
POV_KNOWN_FROM = pd.Timestamp("2025-01-01")        # SAE 2021 release recorded only as "2024": assumed by 2024-12-31
ARMS = ["R", "POV-AS", "SUB-AS", "POV-LA", "SUB-LA", "FE"]
POVERTY_ARMS = ["POV-AS", "SUB-AS", "POV-LA", "SUB-LA"]
AS_ARMS = ["POV-AS", "SUB-AS"]
SEED = 54


def origin(t: int) -> pd.Timestamp:
    """O(t) = 00:00 on the first day of quarter t+1."""
    y, n = divmod(t + 1, 4)
    return pd.Timestamp(y, 3 * n + 1, 1)


def qs(t: int) -> str:
    return f"{t // 4}-Q{t % 4 + 1}"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_inputs() -> dict:
    m = json.loads((DATA / "MANIFEST.json").read_text())
    for f, v in m["files"].items():
        got = hashlib.sha256((DATA / f).read_bytes()).hexdigest()
        if got != v["sha256"]:
            raise SystemExit(f"E54 input {f} changed: {got}")
    return {f: v["sha256"] for f, v in m["files"].items()}


# ---------------------------------------------------------------- raw values
def pov_values() -> dict[str, float]:
    """POV: unweighted province mean of the 2021 municipal SAE poverty incidence (141 LGUs; Lucena has none)."""
    s = pd.read_csv(SAE_FILE)
    assert len(s) == 141 and s["poverty_incidence_2021"].notna().all()
    g = s.groupby("province")["poverty_incidence_2021"].mean()
    return {BY_NAME[p]: float(v) for p, v in g.items()}


def sub_values() -> dict[tuple[str, int], float]:
    """SUB: PSA provincial subsistence incidence among population, reference years 2021 and 2023."""
    b = pd.read_csv(SUB_FILE, dtype={"province_code": str})
    assert set(b["reference_year"]) == {2021, 2023} and (b["reference_year"] >= 2021).all()
    return {(r.province_code, int(r.reference_year)): float(r.subsistence_incidence_pct) for r in b.itertuples()}


def sub_published() -> pd.Timestamp:
    b = pd.read_csv(SUB_FILE)
    d = pd.to_datetime(b["publication_date"]).unique()
    assert len(d) == 1
    return pd.Timestamp(d[0])


def _centred(v: dict[str, float]) -> dict[str, float]:
    mu = float(np.mean([v[p] for p in PROVS]))
    return {p: v[p] - mu for p in PROVS}


# ---------------------------------------------------------------- per-origin encodings (PROTOCOL section 1-2)
def cols(arm: str) -> list[str]:
    if arm in ("POV-AS", "POV-LA"):
        return ["pov"]
    if arm in ("SUB-AS", "SUB-LA"):
        return ["sub"]
    if arm == "FE":
        return [f"prov_{p}" for p in PROVS]
    return []


def values_at(arm: str, t: int) -> dict[str, dict[str, float]]:
    """{province: {col: value}} for a forecast issued at O(t). Centred across the five provinces; 0 when unknown."""
    if arm == "R":
        return {p: {} for p in PROVS}
    if arm == "FE":
        return {p: {f"prov_{q}": float(p == q) for q in PROVS} for p in PROVS}
    O = origin(t)
    if arm in ("POV-AS", "POV-LA"):
        known = arm == "POV-LA" or O >= POV_KNOWN_FROM
        c = _centred(pov_values())
        return {p: {"pov": c[p] if known else 0.0} for p in PROVS}
    sv = sub_values()
    if arm == "SUB-AS":
        if not sub_published() < O:
            return {p: {"sub": 0.0} for p in PROVS}
        year = 2023                                       # both vintages published together: the latest is used
    else:                                                 # SUB-LA: latest reference year <= calendar year of t
        year = 2021 if t // 4 <= 2022 else 2023
    c = _centred({p: sv[(p, year)] for p in PROVS})
    return {p: {"sub": c[p]} for p in PROVS}


def frame(arm: str, origins) -> pd.DataFrame:
    rows = []
    for t in origins:
        v = values_at(arm, int(t))
        for p in PROVS:
            rows.append({"t": int(t), "province_code": p, **v[p]})
    return pd.DataFrame(rows)


def add(X: pd.DataFrame, arm: str, tcol: str = "t") -> pd.DataFrame:
    """Return X with the arm's poverty columns attached by (origin quarter, province)."""
    if arm == "R":
        return X
    F = frame(arm, sorted(X[tcol].astype(int).unique())).rename(columns={"t": tcol})
    out = X.merge(F, on=[tcol, "province_code"], how="left")
    assert out[cols(arm)].notna().all().all() and len(out) == len(X)
    return out


# ---------------------------------------------------------------- comparison
def paired_brier(df: pd.DataFrame, a: str, ref: str, qcol: str, n: int = 1000, seed: int = SEED) -> dict:
    """Mean of (p_a - y)^2 - (p_ref - y)^2 with a quarter-cluster bootstrap 95% CI."""
    rng = np.random.default_rng(seed)
    d = ((df[f"{a}_p"] - df["y"]) ** 2 - (df[f"{ref}_p"] - df["y"]) ** 2).to_numpy()
    q = df[qcol].to_numpy()
    uq = np.unique(q)
    by = {k: d[q == k] for k in uq}
    vals = [float(np.mean(np.concatenate([by[k] for k in rng.choice(uq, len(uq))]))) for _ in range(n)]
    return {"diff": float(d.mean()), "ci95": [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]}


def decide(m: dict, m_ref: dict, pb: dict, identical: bool) -> dict:
    """PROTOCOL section 5. m / m_ref need balanced_accuracy, recall_HIGH, recall_LOW."""
    ba, ba0 = m["balanced_accuracy"] or 0.0, m_ref["balanced_accuracy"] or 0.0
    rh, rh0 = m["recall_HIGH"] or 0.0, m_ref["recall_HIGH"] or 0.0
    rl, rl0 = m["recall_LOW"] or 0.0, m_ref["recall_LOW"] or 0.0
    parts = {"brier_ci_upper_below_0": pb["ci95"][1] < 0, "balanced_ge_ref": ba >= ba0 - 1e-12,
             "recall_HIGH_within_0.05": rh >= rh0 - 0.05 - 1e-12, "recall_LOW_within_0.05": rl >= rl0 - 0.05 - 1e-12}
    if identical:
        status = "IDENTICAL"
    elif all(parts.values()):
        status = "IMPROVES"
    elif pb["ci95"][0] > 0:
        status = "WORSENS"
    else:
        status = "NO DEMONSTRATED DIFFERENCE"
    return {"status": status, "identical": identical, **parts}
