"""Synthetic fixtures with the exact schema of the E25 data (no real value is used). For debugging the runner and
for tests: rounds (incl. supplementary and a 'First Quarter 2025 ...' round), D, Dnow, monthly series, features."""
from __future__ import annotations

import numpy as np
import pandas as pd

PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
NLP = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel", "trigger_market", "trigger_climate", "trigger_employment",
       "trigger_ofw_remittance", "trigger_fish_kill"]
GOV = ["food_cpi_yoy", "food_cpi_yoy_lag1", "unemployment_rate", "rice_price_regular", "cpi_dev"]


def qk(q):
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def qs(i):
    return f"{i // 4}-Q{i % 4 + 1}"


def quarters(a, b):
    return [qs(i) for i in range(qk(a), qk(b) + 1)]


def make_parts(seed: int):
    rng = np.random.default_rng(seed)
    qq = quarters("2021-Q1", "2026-Q2")
    h = 12 + np.cumsum(rng.normal(0, 2.0, len(qq)))
    rows = []
    for i, q in enumerate(qq):
        if q in ("2021-Q1", "2022-Q1"):
            continue
        y, n = int(q[:4]), int(q[-1])
        end = pd.Timestamp(y, 3 * n, 20)
        if q in ("2025-Q2", "2025-Q3"):
            nm = "First Quarter 2025 Social Weather Survey (SWS naming)" if q == "2025-Q2" else f"{q} supplementary"
            rows.append({"quarter": q, "round": nm, "H": float(h[i] + rng.normal(0, 1.5)),
                         "published": end + pd.Timedelta(days=40), "published_eff": end + pd.Timedelta(days=40),
                         "fieldwork_quarter": q, "date_type": "verified", "definition_A": False,
                         "source": "supplementary"})
            continue
        pub = end + pd.Timedelta(days=int(rng.integers(20, 90)))
        eff = pub if y < 2026 else pd.Timestamp(2026, 9, 10)
        rows.append({"quarter": q, "round": f"{q} round", "H": float(h[i] + rng.normal(0, 1.5)),
                     "published": pub if y < 2026 else pd.NaT, "published_eff": eff, "fieldwork_quarter": q,
                     "date_type": "verified" if y < 2026 else "unverified", "definition_A": True,
                     "source": "production" if y < 2026 else "production_2026_authorized"})
    rounds = pd.DataFrame(rows)
    D = np.zeros((5, len(qq)))
    for i in range(1, len(qq)):
        D[:, i] = 0.5 * D[:, i - 1] + rng.normal(0, 0.8, 5)
    D -= D.mean(0, keepdims=True)
    F = D + rng.normal(4, 2, len(qq))[None, :]
    Dd = pd.DataFrame([{"province_code": p, "quarter": q, "D": float(D[j, i]), "F": float(F[j, i])}
                       for i, q in enumerate(qq) for j, p in enumerate(PROVS)])
    Dnow = Dd[Dd["quarter"].map(qk) >= qk("2022-Q1")].copy()
    Dnow["Dnow"] = Dnow["D"] + rng.normal(0, 0.3, len(Dnow))
    Dnow = Dnow[["province_code", "quarter", "Dnow"]].reset_index(drop=True)
    X = []
    for i, q in enumerate(quarters("2021-Q1", "2025-Q4")):
        for j, p in enumerate(PROVS):
            r = {"province_code": p, "t": qk(q), "quarter": q}
            for c in NLP:
                r[c] = float(rng.normal())
            for c in GOV:
                r[c] = float(rng.normal()) if q != "2021-Q1" else np.nan
            r["sws_hunger"] = float(h[max(i - 1, 0)])
            X.append(r)
    X = pd.DataFrame(X)
    return rounds, Dd, Dnow, X, GOV


def make(seed: int, assemble):
    rounds, D, Dnow, X, gov = make_parts(seed)
    return assemble(rounds, D, Dnow, X, gov, {"synthetic": seed})
