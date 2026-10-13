"""E9 label vault: training labels only under Rule L1; test outcomes only after sealed predictions."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

import safe_frame as F


class Stop(RuntimeError):
    pass


def sha_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Vault:
    def __init__(self, stress: pd.DataFrame, published):
        self._s = stress[["province_code", "quarter", "stress"]].copy()
        self._pub = published
        self._sealed_hash = None

    def train(self, quarters: list[str], target: str) -> pd.DataFrame:
        origin = F.qstart(target)
        for q in quarters:
            pub = self._pub(q)
            if F.qi(q) >= F.qi(target) or pub is None or pub >= origin:
                raise Stop(f"vault: label {q} is not available at the origin of {target}")
        return self._s[self._s["quarter"].isin(quarters)].copy()

    def seal(self, predictions: Path) -> str:
        self._sealed_hash = sha_file(predictions)
        return self._sealed_hash

    def reveal(self, quarters: list[str], predictions: Path) -> pd.DataFrame:
        if self._sealed_hash is None or sha_file(predictions) != self._sealed_hash:
            raise Stop("vault: outcomes requested before sealed predictions exist (or predictions changed)")
        return self._s[self._s["quarter"].isin(quarters)].copy()
