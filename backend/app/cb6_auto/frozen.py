"""
app/cb6_auto/frozen.py
----------------------
The one saved C-B6 booster (scripts/freeze_cb6.py). Scoring only: the file's SHA-256 is checked on every load and there is
no call here, or anywhere in this package, that fits a model.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from app.cb6_auto.config import FROZEN


class FrozenModelError(RuntimeError):
    pass


def manifest() -> dict:
    return json.loads((FROZEN / "manifest.json").read_text(encoding="utf-8"))


def load():
    import lightgbm as lgb

    m = manifest()
    path = FROZEN / "model.txt"
    # hashed with LF line endings: a Windows checkout with core.autocrlf rewrites this text file and it is still the same model
    if hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != m["model_sha256"]:
        raise FrozenModelError("data/cb6_auto/frozen/model.txt does not match its manifest; refusing to forecast")
    b = lgb.Booster(model_file=str(path))
    if list(b.feature_name()) != m["columns"]:
        raise FrozenModelError("frozen booster feature names differ from the manifest")
    return b, m


def score(rows: list[dict]) -> list[dict]:
    """Probability and per-input TreeSHAP for each input row, in the frozen column order."""
    b, m = load()
    cols = m["columns"]
    X = pd.DataFrame([{c: r.get(c, np.nan) for c in cols} for r in rows], columns=cols).astype(float)
    p = b.predict(X)
    contrib = np.asarray(b.predict(X, pred_contrib=True))[:, :-1]
    return [{"p": float(p[i]), "shap": dict(zip(cols, map(float, contrib[i])))} for i in range(len(rows))]
