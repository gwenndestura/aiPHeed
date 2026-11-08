import pandas as pd, numpy as np
W = pd.read_csv('data/fi10/out/predictions.csv'); W = W[W.target_quarter.str[:4].astype(int) >= 2016]
for h in (1, 2):
    G = W[W.lead == h]
    a = G[G.config == 'LightGBM regression (tuned)'].set_index(['target_quarter', 'province']).sort_index()
    for ref in ('Damped persistence', 'Naive persistence'):
        b = G[G.config == ref].set_index(['target_quarter', 'province']).sort_index()
        ix = a.index.intersection(b.index); A, B = a.loc[ix], b.loc[ix]
        d = (((A.p - A.y) ** 2) - ((B.p - B.y) ** 2)).groupby(level=0).mean().to_numpy()
        n = len(d); rng = np.random.default_rng(7); bs = []
        for _ in range(5000):
            s = rng.choice(n - 3, int(np.ceil(n / 4))); idx = np.concatenate([np.arange(k, k + 4) for k in s])[:n]; bs.append(d[idx].mean())
        bs = np.array(bs)
        print(h, ref, len(ix), 'dBrier', round(d.mean(), 4), 'ci95', np.round(np.percentile(bs, [2.5, 97.5]), 4), 'P(LGBM better)', round((bs < 0).mean(), 3))
