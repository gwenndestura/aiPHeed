"""
v4 mechanical verdicts (PREREGISTRATION sections 5-6): moving-block bootstrap over sorted target quarters (block 3),
the 75 % claim (CONFIRMED / REJECTED / INCONCLUSIVE / NOT_YET_TESTABLE / DEVELOPMENT_ONLY) and the "beats every other
model" test (one-sided paired block-bootstrap p, Holm across baselines, alpha 0.05).
"""
from __future__ import annotations

import numpy as np

BLOCK = 3
DRAWS = 10000
SEED = 2026
ALPHA = 0.05
TARGET = 0.75


def block_indices(clusters: np.ndarray, draws: int = DRAWS, block: int = BLOCK, seed: int = SEED) -> list[np.ndarray]:
    """Moving-block bootstrap of whole target quarters in time order (non-circular blocks of `block` quarters)."""
    u = np.sort(np.unique(clusters))
    pos = {q: np.where(clusters == q)[0] for q in u}
    n, rng = len(u), np.random.default_rng(seed)
    b = min(block, n)
    starts_max = n - b + 1
    nblocks = int(np.ceil(n / b))
    out = []
    for _ in range(draws):
        qs = np.concatenate([u[s:s + b] for s in rng.integers(0, starts_max, nblocks)])[:n]
        out.append(np.concatenate([pos[q] for q in qs]))
    return out


def share_ci(hit: np.ndarray, boots: list[np.ndarray]) -> dict:
    s = np.array([hit[i].mean() for i in boots])
    return {"share": float(hit.mean()), "ci95_lo": float(np.quantile(s, 0.025)), "ci95_hi": float(np.quantile(s, 0.975)),
            "one_sided95_lo": float(np.quantile(s, 0.05)), "one_sided95_hi": float(np.quantile(s, 0.95))}


def claim_75(hit: np.ndarray, clusters: np.ndarray, sealed: bool) -> dict:
    nq, n = len(np.unique(clusters)), len(hit)
    if not sealed:
        return {"verdict": "DEVELOPMENT_ONLY", **share_ci(hit, block_indices(clusters)), "n": n, "n_quarters": nq}
    if nq < 10 or n < 40:
        return {"verdict": "NOT_YET_TESTABLE", "n": n, "n_quarters": nq}
    r = share_ci(hit, block_indices(clusters))
    v = "CONFIRMED" if r["one_sided95_lo"] >= TARGET else "REJECTED" if r["one_sided95_hi"] < TARGET else "INCONCLUSIVE"
    return {"verdict": v, **r, "n": n, "n_quarters": nq}


def paired_p(hit_model: np.ndarray, hit_base: np.ndarray, clusters: np.ndarray) -> float:
    """One-sided p for 'model within share > baseline within share': share of block draws with difference <= 0."""
    d = hit_model.astype(float) - hit_base.astype(float)
    return float(np.mean([d[i].mean() <= 0 for i in block_indices(clusters)]))


def holm(p: dict[str, float]) -> dict[str, float]:
    items = sorted(p.items(), key=lambda kv: kv[1])
    m, run, out = len(items), 0.0, {}
    for i, (k, v) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v))
        out[k] = run
    return out


def beats_all(p: dict[str, float], testable: bool = True) -> dict:
    if not testable:
        return {"verdict": "NOT_YET_TESTABLE", "p": p}
    adj = holm(p)
    return {"verdict": "YES" if all(v < ALPHA for v in adj.values()) else "NO", "p": p, "p_holm": adj}
