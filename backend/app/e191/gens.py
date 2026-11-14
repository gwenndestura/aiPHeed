"""E191 synthetic-row generators (docs/e191/PROTOCOL.md). Every function sees only the real rows it is given."""
from __future__ import annotations

import warnings
import zlib

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import ks_2samp, norm, spearmanr, wasserstein_distance

from app.e168 import lgbm_only as E
from app.e178 import augment as A

warnings.filterwarnings("ignore")
ANCH = E.ANCH
TAU = A.BOUNDARY_TAU
FAMILY = {"none": "baseline", "e184": "baseline",
          "boot_row": "bootstrap", "boot_class": "bootstrap", "boot_prov": "bootstrap", "undersample": "bootstrap",
          "smote": "minority", "bsmote": "minority", "adasyn": "minority", "svmsmote": "minority", "kmsmote": "minority",
          "gauss": "multivariate", "kde": "multivariate", "gmm": "multivariate", "copula": "multivariate", "vae": "multivariate",
          "traj": "temporal", "mixup": "feature", "corrnoise": "feature", "hard": "boundary",
          "classw": "weighting", "hybrid": "weighting"}
NO_SYN = ("none", "undersample", "classw")
STAGE2 = list(FAMILY)


def rng_for(seed, stream, fold, name, r, salt=0):
    parts = [int(seed), zlib.crc32(str(stream).encode()), zlib.crc32(str(fold).encode()), zlib.crc32(name.encode()), int(round(r * 1000)), salt]
    return np.random.default_rng(np.random.SeedSequence(parts))


# ------------------------------------------------------------------------------------------------ helpers
class Space:
    """Standardized, median-imputed matrix of the continuous inputs + y, se, gap_q and the anchors (training rows only)."""

    def __init__(self, real, an, cols):
        X = real[cols].astype(float)
        self.jc = A.jitter_columns(X)
        self.other = [c for c in cols if c not in self.jc]
        M = pd.DataFrame({c: X[c] for c in self.jc})
        M["__y"], M["__se"], M["__gap"] = real["y_true"].values, real["se_true"].values, real["gap_q"].values.astype(float)
        for a in ANCH:
            M[f"__a_{a}"] = np.asarray(an[a], float)
        self.names = list(M.columns)
        self.med = M.median()
        Mi = M.fillna(self.med)
        self.mu, self.sd = Mi.mean(), Mi.std(ddof=1).replace(0, 1.0).fillna(1.0)
        self.Z = ((Mi - self.mu) / self.sd).values
        self.lo, self.hi = M.min(), M.max()
        self.high = real["y_true"].values >= 0

    def back(self, Z):
        return pd.DataFrame(Z * self.sd.values + self.mu.values, columns=self.names)


def finalize(real, an, cols, S: Space, G: pd.DataFrame, donors, cls=None):
    """Turn generated matrix rows G (Space columns) into synthetic rows. donors = index of a real row per synthetic row
    (parent or nearest real row of the same class): it supplies the missing-value pattern, discrete inputs, lead, region
    and key. Values are clipped to the training rows' range."""
    donors = np.asarray(donors, int)
    Xs = real[cols].iloc[donors].reset_index(drop=True).astype(float).copy()
    for c in S.jc:
        v = np.clip(G[c].values, S.lo[c], S.hi[c])
        Xs[c] = np.where(Xs[c].isna(), np.nan, v)
    se = np.clip(G["__se"].values, real["se_true"].min(), real["se_true"].max())
    y = G["__y"].values.astype(float)
    if cls is not None:                                # keep the class the generator was asked for (sign of y)
        y = np.where(np.asarray(cls, bool), np.abs(y) + 1e-9, -np.abs(y) - 1e-9)
    gap = np.clip(np.round(G["__gap"].values), real["gap_q"].min(), real["gap_q"].max())
    if "gap_q" in Xs:
        Xs["gap_q"] = gap
    As = {a: np.clip(G[f"__a_{a}"].values, np.nanmin(an[a]), np.nanmax(an[a])) for a in ANCH}
    return assemble(real, Xs, y, se, gap, donors, As)


def assemble(real, Xs, y, se, gap, parents, As):
    parents = np.asarray(parents, int)
    syn = Xs.reset_index(drop=True).assign(y_true=y, se_true=se, q_true=norm.cdf(np.asarray(y) / np.asarray(se)),
                                           region=real["region"].values[parents], key=real["key"].values[parents],
                                           lead=real["lead"].values[parents], gap_q=gap, parent=parents)
    return syn, {a: np.asarray(v, float) for a, v in As.items()}


def nearest(S: Space, Zg, cls):
    out = np.empty(len(Zg), int)
    for c in (True, False):
        idx = np.flatnonzero(S.high == c)
        k = np.flatnonzero(np.asarray(cls) == c)
        if len(k) and len(idx):
            out[k] = idx[np.argmin(cdist(Zg[k], S.Z[idx]), axis=1)]
    return out


def copies(real, an, cols, parents):
    parents = np.asarray(parents, int)
    Xs = real[cols].iloc[parents].reset_index(drop=True).astype(float)
    return assemble(real, Xs, real["y_true"].values[parents], real["se_true"].values[parents], real["gap_q"].values[parents].astype(float),
                    parents, {a: np.asarray(an[a], float)[parents] for a in ANCH})


def draw_parents(real, alloc, rng, focus="uniform"):
    high = real["y_true"].values >= 0
    yv = np.abs(real["y_true"].values)
    out = []
    for c in (1, 0):
        idx = np.flatnonzero(high == bool(c))
        if not alloc[c] or not len(idx):
            continue
        p = None if focus == "uniform" else np.exp(-yv[idx] / TAU)
        out.append(rng.choice(idx, size=alloc[c], replace=True, p=None if p is None else p / p.sum()))
    return np.concatenate(out).astype(int) if out else np.empty(0, int)


def jitter_from(real, an, cols, parents, rng, sd_frac=0.5, shared_groups=None, cov=None):
    """Jitter around given parents. shared_groups: one noise draw per group label (trajectory-consistent).
    cov: correlated noise (standardized space) instead of independent noise."""
    syn, As = copies(real, an, cols, parents)
    X = real[cols].astype(float)
    jc = A.jitter_columns(X)
    lo, hi, sd, _ = A._stats(X)
    n = len(parents)
    if cov is not None:
        L = np.linalg.cholesky(cov + 1e-9 * np.eye(len(jc)))
        N = rng.standard_normal((n, len(jc))) @ L.T
    else:
        N = rng.standard_normal((n, len(jc)))
    e = rng.standard_normal(n)
    if shared_groups is not None:
        g = pd.factorize(shared_groups)[0]
        first = pd.Series(np.arange(n)).groupby(g).transform("first").values
        N, e = N[first], e[first]
    for j, c in enumerate(jc):
        x0 = syn[c].values
        syn[c] = np.where(np.isnan(x0), np.nan, np.clip(x0 + N[:, j] * sd_frac * sd[c], lo[c], hi[c]))
    syn["y_true"] = syn["y_true"].values + e * syn["se_true"].values
    syn["q_true"] = norm.cdf(syn["y_true"].values / syn["se_true"].values)
    return syn, As


# ---------------------------------------------------------------------------------------------- generators
def generate(name, real, an, n_syn, rng, cols, ctx):
    real = real.reset_index(drop=True)
    high = real["y_true"].values >= 0
    alloc = A.allocate(high, n_syn)
    info = {"fallback": 0}
    if n_syn <= 0:
        return None, None, info
    if name == "e184":
        raise RuntimeError("e184 uses app.e179.tuned._augment directly")
    if name in ("smote", "copula"):
        syn, As, inf = A.generate(real, an, name, n_syn, rng, cols, jitter_sd=0.5, focus="uniform")
        info["fallback"] = inf.get("smote_fallback_jitter", 0)
        return syn, As, info
    if name in ("boot_row",):
        return (*copies(real, an, cols, rng.integers(0, len(real), n_syn)), info)
    if name == "boot_class":
        return (*copies(real, an, cols, draw_parents(real, alloc, rng)), info)
    if name == "boot_prov":
        keys = real["key"].unique()
        par = []
        while len(par) < n_syn:
            par.extend(np.flatnonzero(real["key"].values == rng.choice(keys)).tolist())
        par = np.array(par[:n_syn])
        return (*copies(real, an, cols, par), info)
    if name in ("traj", "trajcorr"):
        grp = real["key"].astype(str) + "|" + real["survey"].astype(str)
        g_ids = grp.unique()
        gy = real.groupby(grp)["y_true"].first()
        par, labels = [], []
        for c in (1, 0):
            if not alloc[c]:
                continue
            gs = np.array([g for g in g_ids if (gy[g] >= 0) == bool(c)])
            if not len(gs):
                continue
            p = np.exp(-np.abs(gy[gs].values) / TAU)
            got, t = 0, 0
            while got < alloc[c]:
                g = rng.choice(gs, p=p / p.sum())
                rows = np.flatnonzero(grp.values == g)[: alloc[c] - got]
                par.extend(rows.tolist())
                labels.extend([f"{c}|{t}"] * len(rows))
                got += len(rows)
                t += 1
        par, labels = np.array(par), np.array(labels)
        if name == "traj":
            return (*jitter_from(real, an, cols, par, rng, 0.5, shared_groups=labels), info)
        # E192 trajcorr: the shared trajectory noise is drawn with the class's Ledoit-Wolf covariance
        from sklearn.covariance import LedoitWolf
        S = Space(real, an, cols)
        jc = A.jitter_columns(real[cols].astype(float))
        out_syn, out_as = [], []
        for c in (True, False):
            k = high[par] == c
            if not k.any():
                continue
            Zc = S.Z[high == c][:, : len(jc)]
            cov = LedoitWolf().fit(Zc).covariance_ if len(Zc) > 2 else np.eye(len(jc))
            s_, a_ = jitter_from(real, an, cols, par[k], rng, 0.5, shared_groups=labels[k], cov=cov)
            out_syn.append(s_)
            out_as.append(a_)
        return pd.concat(out_syn, ignore_index=True), {a: np.concatenate([d[a] for d in out_as]) for a in ANCH}, info
    if name == "hard":
        a, f, pr, h = ctx["cfg"]
        m = E.LGBRes(E.FS[f], *h, pr).fit(real.assign(e=real["y_true"].values - np.asarray(an[a], float)))
        res = np.abs(real["y_true"].values - (np.asarray(an[a], float) + m.predict(real))) + 1e-3
        par = []
        for c in (1, 0):
            idx = np.flatnonzero(high == bool(c))
            if alloc[c] and len(idx):
                par.append(rng.choice(idx, size=alloc[c], replace=True, p=res[idx] / res[idx].sum()))
        return (*jitter_from(real, an, cols, np.concatenate(par).astype(int), rng, 0.5), info)
    if name == "corrnoise":
        S = Space(real, an, cols)
        par = draw_parents(real, alloc, rng, "boundary")
        jc = A.jitter_columns(real[cols].astype(float))
        out_syn, out_as = [], []
        for c in (True, False):
            k = par[high[par] == c]
            if not len(k):
                continue
            from sklearn.covariance import LedoitWolf
            Zc = S.Z[high == c][:, : len(jc)]
            cov = LedoitWolf().fit(Zc).covariance_ if len(Zc) > 2 else np.eye(len(jc))
            s_, a_ = jitter_from(real, an, cols, k, rng, 0.5, cov=cov)
            out_syn.append(s_)
            out_as.append(a_)
        return pd.concat(out_syn, ignore_index=True), {a: np.concatenate([d[a] for d in out_as]) for a in ANCH}, info
    if name == "mixup":
        par = draw_parents(real, alloc, rng, "uniform")
        isl = real["island"].values if "island" in real else np.zeros(len(real))
        lead = real["lead"].values
        partner = np.empty(len(par), int)
        for t, i in enumerate(par):
            cand = np.flatnonzero((high == high[i]) & (lead == lead[i]) & (isl == isl[i]))
            if len(cand) < 2:
                cand = np.flatnonzero((high == high[i]) & (lead == lead[i]))
            partner[t] = rng.choice(cand)
        lam = rng.beta(0.4, 0.4, len(par))
        S = Space(real, an, cols)
        Z = lam[:, None] * S.Z[par] + (1 - lam[:, None]) * S.Z[partner]
        G = S.back(Z)
        syn, As = finalize(real, an, cols, S, G, par, cls=high[par])
        return syn, As, info
    # model-based generators in the standardized space
    S = Space(real, an, cols)
    cls = np.r_[np.ones(alloc[1], bool), np.zeros(alloc[0], bool)]
    Zg = np.zeros((len(cls), S.Z.shape[1]))
    if name in ("gauss", "kde", "gmm"):
        from sklearn.covariance import LedoitWolf
        from sklearn.mixture import GaussianMixture
        for c in (True, False):
            k = np.flatnonzero(cls == c)
            Zc = S.Z[S.high == c]
            if not len(k):
                continue
            if len(Zc) < 3:
                Zg[k] = Zc[rng.integers(0, len(Zc), len(k))]
                info["fallback"] += len(k)
                continue
            if name == "gauss":
                cov = LedoitWolf().fit(Zc).covariance_
                Zg[k] = rng.multivariate_normal(Zc.mean(0), cov, size=len(k), method="eigh")
            elif name == "kde":
                h = len(Zc) ** (-1.0 / (Zc.shape[1] + 4))
                Zg[k] = Zc[rng.integers(0, len(Zc), len(k))] + rng.standard_normal((len(k), Zc.shape[1])) * h
            else:
                best = None
                for nc in (1, 2, 3):
                    if len(Zc) < 5 * nc:
                        break
                    gm = GaussianMixture(nc, covariance_type="diag", random_state=int(rng.integers(1 << 30)), reg_covar=1e-3).fit(Zc)
                    b = gm.bic(Zc)
                    if best is None or b < best[0]:
                        best = (b, gm)
                gm = best[1]
                gm.random_state = int(rng.integers(1 << 30))
                Zg[k] = gm.sample(len(k))[0][rng.permutation(len(k))]
    elif name == "vae":
        Zg = _vae(S, cls, rng)
    elif name in ("bsmote", "adasyn", "svmsmote", "kmsmote"):
        Zg, cls, fb = _imb(name, S, alloc, rng)
        info["fallback"] = fb
    else:
        raise ValueError(name)
    G = S.back(Zg)
    donors = nearest(S, Zg, cls)
    syn, As = finalize(real, an, cols, S, G, donors, cls=cls)
    return syn, As, info


def _imb(name, S: Space, alloc, rng):
    from imblearn.over_sampling import ADASYN, SMOTE, SVMSMOTE, BorderlineSMOTE, KMeansSMOTE
    from sklearn.cluster import MiniBatchKMeans
    yb = S.high.astype(int)
    n1, n0 = int(yb.sum()), int((1 - yb).sum())
    strat = {c: n + alloc[c] for c, n in ((1, n1), (0, n0)) if alloc[c] > 0}
    kn = max(1, min(5, min(n1, n0) - 1))
    rs = int(rng.integers(1 << 30))
    mk = {"bsmote": lambda: BorderlineSMOTE(sampling_strategy=strat, k_neighbors=kn, m_neighbors=min(10, len(yb) - 1), random_state=rs),
          "adasyn": lambda: ADASYN(sampling_strategy=strat, n_neighbors=kn, random_state=rs),
          "svmsmote": lambda: SVMSMOTE(sampling_strategy=strat, k_neighbors=kn, m_neighbors=min(10, len(yb) - 1), random_state=rs),
          "kmsmote": lambda: KMeansSMOTE(sampling_strategy=strat, k_neighbors=kn, random_state=rs, cluster_balance_threshold=0.0,
                                          kmeans_estimator=MiniBatchKMeans(n_clusters=max(2, len(yb) // 40), random_state=rs, n_init=3))}
    fb = 0
    try:
        Zr, yr = mk[name]().fit_resample(S.Z, yb)
        Zn, cn = Zr[len(yb):], yr[len(yb):].astype(bool)
    except Exception:
        Zn, cn = np.zeros((0, S.Z.shape[1])), np.zeros(0, bool)
    want = np.r_[np.ones(alloc[1], bool), np.zeros(alloc[0], bool)]
    out_Z, out_c = [], []
    for c in (True, False):                         # top up / trim each class to the allocation with plain SMOTE
        have = Zn[cn == c]
        need = int((want == c).sum())
        if len(have) >= need:
            out_Z.append(have[rng.permutation(len(have))[:need]])
        else:
            fb += need - len(have)
            k = need - len(have)
            Zc = S.Z[S.high == c]
            i = rng.integers(0, len(Zc), k)
            D = cdist(Zc[i], Zc)
            D[np.arange(k), i] = np.inf
            nn = np.argsort(D, axis=1)[:, : min(5, len(Zc) - 1)] if len(Zc) > 1 else np.zeros((k, 1), int)
            j = nn[np.arange(k), rng.integers(0, nn.shape[1], k)]
            lam = rng.random((k, 1))
            out_Z.append(np.vstack([have, Zc[i] + lam * (Zc[j] - Zc[i])]))
        out_c.append(np.full(need, c))
    return np.vstack(out_Z), np.concatenate(out_c), fb


def _vae(S: Space, cls, rng):
    import torch
    torch.set_num_threads(1)
    torch.manual_seed(int(rng.integers(1 << 30)))
    X = torch.tensor(S.Z, dtype=torch.float32)
    c = torch.tensor(S.high.astype(np.float32)).unsqueeze(1)
    d, z, hd = X.shape[1], 4, 32
    enc = torch.nn.Sequential(torch.nn.Linear(d + 1, hd), torch.nn.ReLU(), torch.nn.Linear(hd, 2 * z))
    dec = torch.nn.Sequential(torch.nn.Linear(z + 1, hd), torch.nn.ReLU(), torch.nn.Linear(hd, d))
    opt = torch.optim.Adam(list(enc.parameters()) + list(dec.parameters()), lr=3e-3)
    for _ in range(300):
        h = enc(torch.cat([X, c], 1))
        m, lv = h[:, :z], h[:, z:].clamp(-8, 8)
        zz = m + torch.randn_like(m) * torch.exp(0.5 * lv)
        rec = dec(torch.cat([zz, c], 1))
        loss = ((rec - X) ** 2).sum(1).mean() + (-0.5 * (1 + lv - m ** 2 - lv.exp()).sum(1)).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        cc = torch.tensor(np.asarray(cls, np.float32)).unsqueeze(1)
        out = dec(torch.cat([torch.randn(len(cls), z), cc], 1)).numpy()
    return out


# ------------------------------------------------------------------------------------------------ quality
def quality(real, syn, cols):
    if syn is None or not len(syn):
        return {}
    X, Y = real[cols].astype(float), syn[cols].astype(float)
    jc = A.jitter_columns(X)
    ks, w1 = [], []
    for c in jc:
        a, b = X[c].dropna().values, Y[c].dropna().values
        if len(a) > 1 and len(b) > 1:
            ks.append(ks_2samp(a, b).statistic)
            sd = a.std() or 1.0
            w1.append(wasserstein_distance(a, b) / sd)
    use = [c for c in jc if X[c].std() > 0 and Y[c].std() > 0]
    cm = np.nanmean(np.abs(spearmanr(X[use].fillna(X[use].median()), nan_policy="omit")[0] - spearmanr(Y[use].fillna(X[use].median()), nan_policy="omit")[0])) if len(use) > 2 else np.nan
    mu, sd = X[jc].mean(), X[jc].std().replace(0, 1).fillna(1)
    ZR, ZS = ((X[jc] - mu) / sd).fillna(0).values, ((Y[jc] - mu) / sd).fillna(0).values
    DR = cdist(ZR, ZR)
    np.fill_diagonal(DR, np.inf)
    med = float(np.median(DR.min(1)))
    dS = cdist(ZS, ZR).min(1)
    flips = float(np.mean((syn["y_true"].values >= 0) != (real["y_true"].values[syn["parent"].values.astype(int)] >= 0))) if "parent" in syn else np.nan
    return {"median_ks": round(float(np.median(ks)), 4) if ks else np.nan, "max_w1_sd": round(float(np.max(w1)), 4) if w1 else np.nan,
            "corr_mad": round(float(cm), 4), "exact_copy_share": round(float(np.mean(dS < 1e-9)), 4),
            "near_copy_share": round(float(np.mean(dS < 0.05 * med)), 4), "syn_high_share": round(float(np.mean(syn["y_true"] >= 0)), 4),
            "combined_high_share": round(float(np.mean(np.r_[real["y_true"].values >= 0, syn["y_true"].values >= 0])), 4),
            "class_flip_share": round(flips, 4) if flips == flips else None, "n_syn": int(len(syn))}
