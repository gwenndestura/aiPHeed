"""Shared calibration helpers (unpenalised logistic fits by Newton-Raphson; no external stats package)."""
import numpy as np


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _irls(X, y, off=None, it=100):
    off = np.zeros(len(y)) if off is None else off
    b = np.zeros(X.shape[1])
    for _ in range(it):
        eta = X @ b + off
        m = 1 / (1 + np.exp(-eta))
        W = np.clip(m * (1 - m), 1e-9, None)
        step = np.linalg.solve(X.T @ (X * W[:, None]), X.T @ (y - m))
        b = b + step
        if np.max(np.abs(step)) < 1e-10:
            break
    return b


def slope(p, y):
    """Calibration slope: coefficient of logit(p) in logistic regression of y on logit(p)."""
    return float(_irls(np.column_stack([np.ones(len(y)), logit(p)]), np.asarray(y, float))[1])


def intercept(p, y):
    """Calibration-in-the-large on the logit scale: intercept with logit(p) as offset (slope fixed at 1)."""
    return float(_irls(np.ones((len(y), 1)), np.asarray(y, float), off=logit(p))[0])


def ece(p, y, bins=10):
    p, y = np.asarray(p, float), np.asarray(y, float)
    bn = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum(abs(p[bn == k].mean() - y[bn == k].mean()) * (bn == k).mean() for k in range(bins) if (bn == k).any()))
