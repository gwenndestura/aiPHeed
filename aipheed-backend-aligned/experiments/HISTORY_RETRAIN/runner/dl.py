"""HISTORY_RETRAIN deep-learning models (PLAN_AMENDMENT_1.md, 319ae4d2): MLP and GRU, 10 seeds, walk-forward.

Training rows, labels, eligibility and fallbacks are those of the LightGBM of the same target (run_hr.train_rows).
Early stopping uses only the last 4 training origins as validation; the network is then refitted from scratch on all
training rows for the chosen number of epochs. CPU, deterministic, one thread per process.

    python dl.py                      # all 60 jobs (6 model/target/option x 10 seeds), 7 processes
    python dl.py MLP T1 b 0           # one job
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import random
from multiprocessing import Pool

import numpy as np
import pandas as pd

import hr_lib as H
import run_hr as RH

ARCH = dict(mlp_units=32, gru_units=16, dropout=0.3, lr=1e-3, weight_decay=1e-2, batch=256, max_epochs=200,
            patience=20, fallback_epochs=50, steps=8)
JOBS = [(m, tg, o) for m, tg, o in (("MLP", "T1", "b"), ("MLP", "T1", "c"), ("MLP", "T2", "b"), ("MLP", "T2", "c"),
                                    ("GRU", "T1", "b"), ("GRU", "T2", "b"))]
DLOUT = H.OUT / "dl"


def seed_all(s: int):
    import torch
    random.seed(s)
    np.random.seed(s % (2 ** 32))
    torch.manual_seed(s)


def net(kind: str, n_in: int):
    import torch.nn as nn

    class GRUNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.gru = nn.GRU(n_in, ARCH["gru_units"], num_layers=1, batch_first=True)
            self.drop = nn.Dropout(ARCH["dropout"])
            self.head = nn.Linear(ARCH["gru_units"], 1)

        def forward(self, x):
            _, h = self.gru(x)
            return self.head(self.drop(h[-1])).squeeze(-1)

    if kind == "GRU":
        return GRUNet()
    return nn.Sequential(nn.Linear(n_in, ARCH["mlp_units"]), nn.ReLU(), nn.Dropout(ARCH["dropout"]),
                         nn.Linear(ARCH["mlp_units"], 1), nn.Flatten(0))


class Prep:
    """Median imputation then standardization, fitted on the fitting rows (all steps for the GRU); a column with no
    value or sd 0 becomes 0."""

    def fit(self, X: np.ndarray):
        flat = X.reshape(-1, X.shape[-1])
        with np.errstate(all="ignore"):
            self.med = np.nanmedian(flat, axis=0)
        self.med = np.where(np.isfinite(self.med), self.med, 0.0)
        Z = np.where(np.isnan(flat), self.med, flat)
        self.mu, self.sd = Z.mean(0), Z.std(0)
        self.ok = np.isfinite(self.sd) & (self.sd > 0)
        return self

    def __call__(self, X: np.ndarray) -> np.ndarray:
        Z = np.where(np.isnan(X), self.med, X)
        Z = np.where(self.ok, (Z - self.mu) / np.where(self.ok, self.sd, 1.0), 0.0)
        return Z.astype(np.float32)


def train(kind, Xf, yf, seed, epochs=None, Xv=None, yv=None):
    """Fit; with a validation set, early stopping (patience) and return the best epoch; else train `epochs` epochs."""
    import torch
    seed_all(seed)
    m = net(kind, Xf.shape[-1])
    opt = torch.optim.AdamW(m.parameters(), lr=ARCH["lr"], weight_decay=ARCH["weight_decay"])
    lossf = torch.nn.BCEWithLogitsLoss()
    X, y = torch.from_numpy(Xf), torch.from_numpy(yf.astype(np.float32))
    gen = torch.Generator().manual_seed(seed)
    best, best_ep, bad = np.inf, 0, 0
    n_ep = ARCH["max_epochs"] if epochs is None else epochs
    for ep in range(1, n_ep + 1):
        m.train()
        for idx in torch.randperm(len(X), generator=gen).split(ARCH["batch"]):
            opt.zero_grad()
            lossf(m(X[idx]), y[idx]).backward()
            opt.step()
        if Xv is not None:
            m.eval()
            with torch.no_grad():
                v = float(lossf(m(torch.from_numpy(Xv)), torch.from_numpy(yv.astype(np.float32))))
            if v < best - 1e-12:
                best, best_ep, bad = v, ep, 0
            else:
                bad += 1
                if bad >= ARCH["patience"]:
                    break
    return m, best_ep


def predict(m, X: np.ndarray) -> np.ndarray:
    import torch
    m.eval()
    with torch.no_grad():
        return torch.sigmoid(m(torch.from_numpy(X))).numpy().astype(float)


def run_job(kind: str, target: str, opt: str, s: int) -> str:
    import torch
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    T1, T2 = RH.tables()
    d = H.load()
    S = (T1 if target == "T1" else T2)
    S = S[S["t"] >= RH.first_origin(opt)].reset_index(drop=True)
    cc = RH.cols(target, opt, "LGBM")
    on = ["province_code", "q"] if target == "T1" else ["q"]
    if target == "T1":
        LAB = H.price_frame(d).rename(columns={"price": "y"})
        L1 = H.t1_labels(d)
    else:
        L2 = H.t2_labels(d)
    X_all = S[cc].to_numpy(float)
    unit = S["province_code"] if target == "T1" else pd.Series("R", index=S.index)
    pos = {(int(t), u, int(k)): i for i, (t, u, k) in enumerate(zip(S["t"], unit, S["lead"]))}

    def seq(rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """(n, steps, f) sequences of origins t-7..t for the same unit and lead; mask of rows that have all steps."""
        us = rows["province_code"] if target == "T1" else pd.Series("R", index=rows.index)
        ix = [[pos.get((int(t) - j, u, int(k))) for j in range(ARCH["steps"] - 1, -1, -1)]
              for t, u, k in zip(rows["t"], us, rows["lead"])]
        ok = np.array([all(i is not None for i in r) for r in ix], bool)
        A = np.stack([X_all[r] for r, o in zip(ix, ok) if o]) if ok.any() else np.zeros((0, ARCH["steps"], len(cc)))
        return A, ok

    def mats(rows):
        if kind == "GRU":
            A, ok = seq(rows)
            return A, ok
        return rows[cc].to_numpy(float), np.ones(len(rows), bool)

    out = []
    for t in H.ORIGINS_EVAL:
        if target == "T1":
            lab, clim = H.known_price(d, t, LAB), H.known_t1(d, t, L1)["y"].mean()
        else:
            lab = H.known_t2(d, t, L2)
            clim = lab["y"].mean()
        clim = float(clim) if clim == clim else 0.0
        tr = RH.train_rows(S, t, lab, on)
        te = S[(S["t"] == t) & S["lead"].isin([1, 2])].copy()
        Xtr, oktr = mats(tr)
        tr = tr[oktr]
        Xte, okte = mats(te)
        assert okte.all(), "evaluation row without its 8 steps"
        seed = 1000 * s + t
        if not H.eligible(tr):
            p, fb, ep = np.full(len(te), float(tr["y"].mean()) if len(tr) else clim), True, None
        else:
            last4 = sorted(tr["t"].unique())[-4:]
            vmask = tr["t"].isin(last4).to_numpy()
            fmask = (tr["q"] <= min(last4) - 1).to_numpy()
            yf, yv = tr["y"].to_numpy(int)[fmask], tr["y"].to_numpy(int)[vmask]
            if vmask.any() and len(set(yf.tolist())) == 2:
                pf = Prep().fit(Xtr[fmask])
                _, ep = train(kind, pf(Xtr[fmask]), yf, seed, Xv=pf(Xtr[vmask]), yv=yv)
                ep = max(ep, 1)
            else:
                ep = ARCH["fallback_epochs"]
            pa = Prep().fit(Xtr)
            m, _ = train(kind, pa(Xtr), tr["y"].to_numpy(int), seed, epochs=ep)
            p, fb = predict(m, pa(Xte)), False
        te["p_raw"], te["fallback"], te["epochs"] = p, fb, ep
        te["p"] = te["H1"] * te["p_raw"] if target == "T1" else te["p_raw"]
        out.append(te)
    F = pd.concat(out)
    F = F.assign(target=target, option=opt, model=kind, seed=s)
    keep = ["target", "option", "model", "seed", "t", "lead", "q", "province_code", "p", "p_raw", "H1", "fallback",
            "epochs"]
    DLOUT.mkdir(parents=True, exist_ok=True)
    f = DLOUT / f"{kind}_{target}_{opt}_s{s}.csv"
    F[[c for c in keep if c in F.columns]].to_csv(f, index=False)
    return f.name


def _job(a):
    return run_job(*a)


if __name__ == "__main__":
    if len(sys.argv) == 5:
        print(run_job(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])))
    else:
        RH.hashes()
        jobs = [(m, tg, o, s) for (m, tg, o) in JOBS for s in range(10)]
        jobs.sort(key=lambda j: (j[0] != "GRU", j[1] != "T1"))          # longest first
        with Pool(int(sys.argv[1]) if len(sys.argv) == 2 else 7) as pool:
            for name in pool.imap_unordered(_job, jobs):
                print("done", name, flush=True)
