"""E180 (docs/e180/PROTOCOL.md): the ensemble is the plain mean of E179 over the five generator seeds, per row and mode."""
import numpy as np
import pandas as pd

from app.e179 import tuned as T
from app.e180 import ensemble as X


def test_ensemble_is_the_seed_mean():
    rows = []
    r = np.random.default_rng(0)
    for sd in T.SEEDS:
        for k in ("a", "b"):
            for mode in ("main", "shuf1"):
                rows.append({"key": k, "survey": "ENNS2021", "lead": 1, "mode": mode, "arm": "E179", "seed": sd,
                             "mu": r.normal(), "p": r.random(), "half": r.random()})
    rows.append({"key": "a", "survey": "ENNS2021", "lead": 1, "mode": "main", "arm": "E179_min", "seed": 17901, "mu": 99, "p": .99, "half": 9})
    df = pd.DataFrame(rows)
    e = X.ensemble(df)
    assert len(e) == 4 and (e["n_seeds"] == 5).all() and (e["arm"] == "E180").all() and (e["seed"] == X.ENS_SEED).all()
    for _, row in e.iterrows():
        src = df[(df.arm == "E179") & (df.key == row.key) & (df["mode"] == row["mode"])]
        assert np.isclose(row.p, src.p.mean()) and np.isclose(row.mu, src.mu.mean()) and np.isclose(row.half, src.half.mean())
