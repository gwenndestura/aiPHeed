"""SHAP explanations in plain words.

TreeSHAP (Lundberg et al. 2020) splits each LightGBM forecast into feature contributions (log-odds). Contributions
are summed per block (the latest hunger reading, and the five domains with their government and news features
together) and only blocks that moved the forecast by at least MIN_EFFECT are mentioned. The sentence says which
blocks raised and which lowered the estimate; it does not say they caused hunger.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.fi5.features import OUTCOME, domain_of

MIN_EFFECT = 0.10          # log-odds; smaller movements are not mentioned
PHRASES = {   # short names without "and", so two of them can be joined into one readable sentence
    "outcome": {"up": "the latest hunger survey reading", "down": "the latest hunger survey reading"},
    "market": {"up": "food prices", "down": "food prices"},
    "climate": {"up": "weather conditions", "down": "weather conditions"},
    "employment": {"up": "unemployment", "down": "unemployment"},
    "remittance": {"up": "OFW remittances", "down": "OFW remittances"},
    "poverty": {"up": "household hardship", "down": "household hardship"},
}


def block_of(feature: str) -> str:
    return "outcome" if feature in OUTCOME else domain_of(feature)


def shap_values(booster_model, X: pd.DataFrame) -> np.ndarray:
    import shap
    ex = shap.TreeExplainer(booster_model)
    v = ex.shap_values(X)
    if isinstance(v, list):
        v = v[1]
    v = np.asarray(v)
    return v[..., 1] if v.ndim == 3 else v


def by_block(cols: list[str], sv: np.ndarray) -> dict[str, float]:
    out: dict[str, float] = {}
    for c, s in zip(cols, sv):
        out[block_of(c)] = out.get(block_of(c), 0.0) + float(s)
    return out


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]          # keeps acronyms such as OFW intact


def _join(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else " and ".join(xs[:2])


def sentence(blocks: dict[str, float], target_quarter: str) -> str:
    up = [b for b, v in sorted(blocks.items(), key=lambda kv: -kv[1]) if v >= MIN_EFFECT][:2]
    down = [b for b, v in sorted(blocks.items(), key=lambda kv: kv[1]) if v <= -MIN_EFFECT][:2]
    up_w = [PHRASES[b]["up"] for b in up]
    down_w = [PHRASES[b]["down"] for b in down]
    if up_w and down_w:
        s = (f"{_cap(_join(up_w))} raised the estimated chance of above-normal hunger in {target_quarter}, "
             f"while {_join(down_w)} lowered it.")
    elif up_w:
        s = f"{_cap(_join(up_w))} raised the estimated chance of above-normal hunger in {target_quarter}."
    elif down_w:
        s = f"{_cap(_join(down_w))} lowered the estimated chance of above-normal hunger in {target_quarter}."
    else:
        s = f"No single factor stood out for {target_quarter}; the estimate stays close to the usual level."
    return s + " These are the factors the model leaned on, not proven causes."


def global_importance(cols: list[str], sv: np.ndarray) -> pd.DataFrame:
    imp = pd.DataFrame({"feature": cols, "mean_abs_shap": np.abs(sv).mean(axis=0)})
    imp["block"] = imp["feature"].map(block_of)
    return imp.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)
