"""
E178 Part B: synthetic TRAINING rows, class balancing and fidelity checks (docs/e178/PROTOCOL.md, Part B).

Every function here sees only the real rows it is given: one inner fold's training rows, or one outer job's training rows.
Synthetic rows carry is_synthetic / scenario_id / generator_seed and are never predicted for scoring: they enter LightGBM
fit sets only (app.e178.retrain).

Generators
  jitter  y' = y + N(0, se_true^2) on the logit scale; continuous inputs x' = x + N(0, (0.25 SD)^2), clipped to the rows'
          min/max. Copied from the parent: NaN, columns with <= 10 distinct values or a value covering >= 50 % of rows,
          lead, gap_q, se_true and the anchors.
  smote   one of the k = 5 nearest rows of the same class and lead (standardized inputs, NaN as the mean); one lambda ~ U(0,1)
          interpolates inputs, y, se_true, the anchors and gap_q (rounded). A NaN on either side keeps the parent's value.
          A class-and-lead cell with fewer than 2 rows falls back to jitter for its parents (counted).
"""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import ks_2samp, norm, spearmanr, wasserstein_distance
from sklearn.model_selection import GroupKFold

GENERATORS = ("jitter", "smote", "copula")          # copula added by E185 (docs/e185/PROTOCOL.md); order kept for seeds
COPULA_SHRINK = 0.2
RATIOS = (0.25, 0.5, 1.0)
SYN_WEIGHT = 0.4
JITTER_SD = 0.25
K_NN = 5
BOUNDARY_TAU = 0.5                                       # E179 "boundary" focus: parent weight exp(-|y| / 0.5) on the logit scale
SEEDS = (17801, 17802, 17803, 17804, 17805)
PRIMARY_SEED = SEEDS[0]
ANCH = ("H", "OH", "RSS")
KEEP = ("lead", "gap_q")
FIDELITY = {"median_ks_max": 0.15, "max_w1_sd_max": 0.50, "corr_mad_max": 0.10, "tstr_ratio_max": 1.25,
            "copy_share_max": 0.10, "copy_distance_frac": 0.05}
TSTR_CFG = ("OH", "GOV", True, (3, 10, 20.0, 150))      # anchor, feature set, prune, (leaves, min_child, lambda, trees)


def feature_columns(d: pd.DataFrame) -> list[str]:
    """Every column any E168 feature set can use (GNT + regional consumption), in a fixed order."""
    from app.e168 import lgbm_only as E
    seen, out = set(), []
    for cols in E.FS.values():
        for c in cols:
            if c in d.columns and c not in seen:
                seen.add(c)
                out.append(c)
    return out


def rng_for(seed: int, job: str, fold, gen: str, r: float) -> np.random.Generator:
    """One reproducible stream per (generator seed, outer job, inner fold or 'final', generator, ratio)."""
    parts = [int(seed), zlib.crc32(str(job).encode()), zlib.crc32(str(fold).encode()), GENERATORS.index(gen) + 1, int(round(r * 100))]
    return np.random.default_rng(np.random.SeedSequence(parts))


def allocate(high: np.ndarray, n_syn: int) -> dict[int, int]:
    """Synthetic rows per class: first to the minority class up to parity, then by the classes' real shares."""
    high = np.asarray(high, bool)
    n1, n0 = int(high.sum()), int((~high).sum())
    if n1 == 0 or n0 == 0:
        return {1: n_syn if n1 else 0, 0: n_syn if n0 else 0}
    out = {0: 0, 1: 0}
    if n1 != n0:
        mi = 1 if n1 < n0 else 0
        out[mi] = min(n_syn, abs(n1 - n0))
    rest = n_syn - out[0] - out[1]
    r1 = int(round(rest * n1 / (n0 + n1)))
    out[1] += r1
    out[0] += rest - r1
    return out


def jitter_columns(X: pd.DataFrame) -> list[str]:
    out = []
    for c in X.columns:
        if c in KEEP:
            continue
        v = X[c].dropna()
        if len(v) < 2 or v.nunique() <= 10 or v.value_counts(normalize=True).iloc[0] >= 0.5:
            continue
        out.append(c)
    return out


def _stats(X: pd.DataFrame):
    return X.min(), X.max(), X.std(ddof=1).fillna(0.0), X.mean()


def generate(real: pd.DataFrame, anchors: dict[str, np.ndarray], gen: str, n_syn: int, rng: np.random.Generator,
             cols: list[str], jitter_sd: float = JITTER_SD, focus: str = "uniform") -> tuple[pd.DataFrame, dict[str, np.ndarray], dict]:
    """n_syn synthetic rows from `real` (reset index; y_true, se_true, region, lead, gap_q and `cols`) and its anchors.
    jitter_sd and focus are E179's options; the defaults are E178's generators exactly."""
    real = real.reset_index(drop=True)
    high = (real["y_true"].values >= 0)
    alloc = allocate(high, n_syn)
    yv = real["y_true"].values.astype(float)

    def draw(c):
        idx = np.flatnonzero(high == bool(c))
        if focus == "uniform":                   # E178: uniform within class (the same random calls as before)
            return rng.choice(idx, size=alloc[c], replace=True)
        p = np.exp(-np.abs(yv[idx]) / BOUNDARY_TAU)                  # "boundary": rows near the 50 % line drawn more often
        return rng.choice(idx, size=alloc[c], replace=True, p=p / p.sum())

    parents = np.concatenate([draw(c) if alloc[c] else np.empty(0, int) for c in (1, 0)]).astype(int)
    X = real[cols].astype(float)
    lo, hi, sd, mu = _stats(X)
    jc = jitter_columns(X)
    A = {a: np.asarray(anchors[a], float) for a in anchors}
    n = len(parents)
    Xs = X.iloc[parents].reset_index(drop=True).copy()
    y = real["y_true"].values[parents].astype(float)
    se = real["se_true"].values[parents].astype(float)
    gap = real["gap_q"].values[parents].astype(float)
    As = {a: v[parents].copy() for a, v in A.items()}
    fallback = 0

    def jitter_rows(idx):
        for c in jc:
            x0 = Xs.loc[idx, c].values
            noise = rng.standard_normal(len(idx)) * jitter_sd * sd[c]
            Xs.loc[idx, c] = np.where(np.isnan(x0), np.nan, np.clip(x0 + noise, lo[c], hi[c]))
        y[idx] = y[idx] + rng.standard_normal(len(idx)) * se[idx]

    if gen == "jitter":
        jitter_rows(np.arange(n))
    elif gen == "smote":
        Z = ((X - mu) / sd.replace(0, 1.0)).fillna(0.0).values
        lead = real["lead"].values
        cell = {}
        for i in range(len(real)):
            cell.setdefault((bool(high[i]), int(lead[i])), []).append(i)
        lam = rng.random(n)
        pick = rng.random(n)
        jit = []
        for k, i in enumerate(parents):
            mates = [j for j in cell[(bool(high[i]), int(lead[i]))] if j != i]
            if not mates:
                jit.append(k)
                continue
            dist = np.sqrt(((Z[mates] - Z[i]) ** 2).sum(axis=1))
            near = np.array(mates)[np.argsort(dist, kind="stable")[:K_NN]]
            j = int(near[min(int(pick[k] * len(near)), len(near) - 1)])
            xi, xj = X.iloc[i].values, X.iloc[j].values
            Xs.iloc[k] = np.where(np.isnan(xi) | np.isnan(xj), xi, xi + lam[k] * (xj - xi))
            y[k] = real["y_true"].values[i] + lam[k] * (real["y_true"].values[j] - real["y_true"].values[i])
            se[k] = real["se_true"].values[i] + lam[k] * (real["se_true"].values[j] - real["se_true"].values[i])
            gap[k] = np.round(real["gap_q"].values[i] + lam[k] * (real["gap_q"].values[j] - real["gap_q"].values[i]))
            for a in As:
                As[a][k] = A[a][i] + lam[k] * (A[a][j] - A[a][i])
        if jit:
            fallback = len(jit)
            jitter_rows(np.array(jit))
    elif gen == "copula":
        Xs, y, se, gap, As = _copula(real, X, A, high, parents, rng)
    else:
        raise ValueError(gen)
    syn = Xs.assign(y_true=y, se_true=se, q_true=norm.cdf(y / se), region=real["region"].values[parents],
                    key=real["key"].values[parents] if "key" in real else None, lead=real["lead"].values[parents],
                    gap_q=gap, parent=parents)
    info = {"n_real": int(len(real)), "real_high": int(high.sum()), "real_low": int((~high).sum()), "n_syn": int(n),
            "syn_high": int((y >= 0).sum()), "syn_low": int((y < 0).sum()), "alloc_high": alloc[1], "alloc_low": alloc[0],
            "smote_fallback_jitter": fallback}
    return syn, As, info


def _copula(real, X, A, high, parents, rng):
    """E185 Gaussian copula, per class: normal scores of every variable (inputs, y, se, gap_q, anchors), rank correlation
    shrunk toward the identity, draws mapped back through each variable's empirical quantiles (marginals kept, values
    within the class's range). The parent row supplies the missing-value pattern; lead and region come from it too."""
    V = X.copy()
    V["__y"], V["__se"], V["__gap"] = real["y_true"].values, real["se_true"].values, real["gap_q"].values
    for a, v in A.items():
        V[f"__a_{a}"] = v
    names = list(V.columns)
    vals_all = V.values.astype(float)
    out = np.full((len(parents), len(names)), np.nan)
    for c in (True, False):
        k_idx = np.flatnonzero(high[parents] == c)
        if not len(k_idx):
            continue
        R = vals_all[high == c]
        cont = [j for j in range(R.shape[1]) if np.unique(R[~np.isnan(R[:, j]), j]).size >= 3]
        if cont:
            Z = np.zeros((len(R), len(cont)))
            for t, j in enumerate(cont):
                col = R[:, j]
                m = ~np.isnan(col)
                Z[m, t] = norm.ppf((pd.Series(col[m]).rank(method="average").values - 0.5) / m.sum())
            S = np.atleast_2d(np.corrcoef(Z, rowvar=False)) if len(cont) > 1 else np.ones((1, 1))
            S = np.nan_to_num(S, nan=0.0)
            np.fill_diagonal(S, 1.0)
            S = (1 - COPULA_SHRINK) * S + COPULA_SHRINK * np.eye(len(cont))
            L = np.linalg.cholesky(S + 1e-9 * np.eye(len(cont)))
            U = norm.cdf(rng.standard_normal((len(k_idx), len(cont))) @ L.T)
            for t, j in enumerate(cont):
                v = np.sort(R[~np.isnan(R[:, j]), j])
                out[k_idx, j] = np.quantile(v, U[:, t])
        for j in [j for j in range(R.shape[1]) if j not in set(cont)]:
            v = R[~np.isnan(R[:, j]), j]
            out[k_idx, j] = rng.choice(v, size=len(k_idx)) if len(v) else np.nan
    nx = X.shape[1]
    feats = out[:, :nx]
    feats[np.isnan(X.values.astype(float)[parents])] = np.nan            # the parent's missing-value pattern
    Xs = pd.DataFrame(feats, columns=X.columns)
    if "lead" in Xs:
        Xs["lead"] = real["lead"].values[parents]
    pos = {n: i for i, n in enumerate(names)}
    y, se = out[:, pos["__y"]], np.maximum(out[:, pos["__se"]], 1e-6)
    gap = np.round(out[:, pos["__gap"]])
    As = {a: out[:, pos[f"__a_{a}"]] for a in A}
    return Xs, y, se, gap, As


def augment(real: pd.DataFrame, anchors: dict, gen: str, r: float, rng, cols: list[str], seed: int,
            jitter_sd: float = JITTER_SD, focus: str = "uniform", tag: str = "B"):
    n_syn = int(round(r * len(real)))
    syn, As, info = generate(real, anchors, gen, n_syn, rng, cols, jitter_sd=jitter_sd, focus=focus)
    sid = f"{tag}:{gen}:r{r:g}" if (jitter_sd, focus) == (JITTER_SD, "uniform") else f"{tag}:{gen}:r{r:g}:sd{jitter_sd:g}:{focus}"
    syn["is_synthetic"], syn["scenario_id"], syn["generator_seed"] = True, sid, int(seed)
    return syn, As, info


# --------------------------------------------------------------------------------------------------------- fidelity
def _std(real: pd.DataFrame, cols: list[str]):
    X = real[cols].astype(float)
    mu, sd = X.mean(), X.std(ddof=1).replace(0, 1.0).fillna(1.0)
    return mu, sd


def _zmat(d: pd.DataFrame, cols: list[str], mu, sd) -> np.ndarray:
    return ((d[cols].astype(float) - mu) / sd).fillna(0.0).values


def fidelity(tr: pd.DataFrame, atr: dict[str, np.ndarray], gen: str, seed: int, job: str) -> dict:
    """The protocol's primary fidelity criteria on one outer job's real training rows (r = 1.0). Within-class
    comparisons are weighted by the synthetic class counts, so intended rebalancing is not counted as infidelity."""
    from app.e168 import lgbm_only as E
    from app.e151 import prov as Pv
    tr = tr.reset_index(drop=True)
    cols = feature_columns(tr)
    syn, sa, info = augment(tr, atr, gen, 1.0, rng_for(seed, job, "fidelity", gen, 1.0), cols, seed)
    use = [c for c in cols if tr[c].notna().sum() >= 2 and tr[c].nunique() > 1]
    sd_all = tr[use].astype(float).std(ddof=1).replace(0, 1.0)
    rh, sh = tr["y_true"].values >= 0, syn["y_true"].values >= 0
    wts = {c: (sh == c).sum() for c in (True, False)}
    ks, w1 = {}, {}
    for c in use:
        k_, w_, tot = 0.0, 0.0, 0
        for cl in (True, False):
            a, b = tr.loc[rh == cl, c].dropna().values, syn.loc[sh == cl, c].dropna().values
            if len(a) < 2 or len(b) < 2:
                continue
            k_ += wts[cl] * ks_2samp(a, b).statistic
            w_ += wts[cl] * wasserstein_distance(a, b) / sd_all[c]
            tot += wts[cl]
        if tot:
            ks[c], w1[c] = k_ / tot, w_ / tot
    cd, tot = 0.0, 0
    for cl in (True, False):
        a, b = tr.loc[rh == cl, use].astype(float), syn.loc[sh == cl, use].astype(float)
        if len(a) < 5 or len(b) < 5:
            continue
        ra, rb = a.rank().corr().values, b.rank().corr().values
        iu = np.triu_indices(len(use), 1)
        dd = np.abs(ra[iu] - rb[iu])
        dd = dd[~np.isnan(dd)]
        if len(dd):
            cd += wts[cl] * float(dd.mean())
            tot += wts[cl]
    corr_mad = cd / tot if tot else float("nan")
    # train on synthetic, test on real (held-out regions inside the training rows)
    a_, f_, pr_, h_ = TSTR_CFG
    w = 1.0 / (tr["se_true"].values ** 2 + 0.05)
    y = tr["y_true"].values
    sse_s, sse_r = 0.0, 0.0
    for fi, (i_tr, i_te) in enumerate(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"])):
        real_f = tr.iloc[i_tr].reset_index(drop=True)
        an_f = {a: np.asarray(atr[a])[i_tr] for a in atr}
        s_f, sa_f, _ = augment(real_f, an_f, gen, 1.0, rng_for(seed, job, f"tstr{fi}", gen, 1.0), cols, seed)
        test = tr.iloc[i_te]
        base = np.asarray(atr[a_])[i_te]
        ms = E.LGBRes(E.FS[f_], *h_, pr_).fit(s_f.assign(e=s_f["y_true"].values - sa_f[a_]))
        mr = E.LGBRes(E.FS[f_], *h_, pr_).fit(real_f.assign(e=real_f["y_true"].values - an_f[a_]))
        sse_s += float(np.sum(w[i_te] * (y[i_te] - base - ms.predict(test)) ** 2))
        sse_r += float(np.sum(w[i_te] * (y[i_te] - base - mr.predict(test)) ** 2))
    # distance to the closest real record (inputs and target, standardized on the real rows)
    dc = use + ["y_true"]
    mu, sd = _std(tr, dc)
    R, Sx = _zmat(tr, dc, mu, sd), _zmat(syn, dc, mu, sd)
    rr = cdist(R, R)
    np.fill_diagonal(rr, np.inf)
    med_real = float(np.median(rr.min(axis=1)))
    sr = cdist(Sx, R).min(axis=1)
    copy_share = float(np.mean(sr < FIDELITY["copy_distance_frac"] * med_real))
    exact = int(np.sum(sr <= 1e-12))
    # descriptive: does each SIGN column keep its correlation sign with e (OH anchor)?
    e_r, e_s = y - np.asarray(atr["OH"]), syn["y_true"].values - sa["OH"]
    sign = {}
    for c in [c for c in use if Pv.SIGN.get(c, 0)]:
        a = spearmanr(tr[c], e_r, nan_policy="omit").statistic
        b = spearmanr(syn[c], e_s, nan_policy="omit").statistic
        if np.isfinite(a) and np.isfinite(b):
            sign[c] = bool(np.sign(a) == np.sign(b))
    m = {"median_ks": float(np.median(list(ks.values()))), "max_w1_sd": float(max(w1.values())),
         "max_w1_feature": max(w1, key=w1.get), "corr_mad": corr_mad, "tstr_sse": sse_s, "trtr_sse": sse_r,
         "tstr_ratio": sse_s / sse_r, "median_real_nn": med_real, "copy_share": copy_share, "exact_copies": exact,
         "sign_agreement_share": float(np.mean(list(sign.values()))) if sign else None, "n_features": len(use), **info}
    m["checks"] = {"ks": m["median_ks"] <= FIDELITY["median_ks_max"], "wasserstein": m["max_w1_sd"] <= FIDELITY["max_w1_sd_max"],
                   "correlation": bool(corr_mad <= FIDELITY["corr_mad_max"]), "tstr": m["tstr_ratio"] <= FIDELITY["tstr_ratio_max"],
                   "not_copies": copy_share <= FIDELITY["copy_share_max"] and exact == 0}
    m["passed"] = all(m["checks"].values())
    m["per_feature"] = {c: {"ks": round(ks[c], 4), "w1_sd": round(w1[c], 4)} for c in ks}
    return m
