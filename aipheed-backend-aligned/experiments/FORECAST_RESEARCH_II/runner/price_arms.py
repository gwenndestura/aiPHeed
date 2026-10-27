"""PROTOCOL section 5: the joint random-walk price arms J0, J1, J2, J3, J3T, JB3 and the LightGBM correction LJ, at
every origin of the stack (training rows need them too).

    python price_arms.py        # out/price_arms_ii.csv, out/price_audit.json
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

import ii_lib as L

F = L.F
N_DRAW = 4000
HORIZON = 13
ANCHOR = np.log(1.03) / 12
J_ARMS = ("J0", "J1", "J2", "J3", "JB3")
REG_GRID = [dict(id=f"r{n}", trees=n) for n in (10, 25, 50, 100)]


def increments(m0: int) -> tuple[np.ndarray, dict, dict]:
    """Pooled demeaned (food, all) increments of the trailing 36 months, the province increment frames, last logs."""
    W = L.index_wide()
    lf, la = np.log(W["food"]), np.log(W["all"])
    df, da = lf.diff(), la.diff()
    ok = (df.index >= L.FIRST_YM + 1) & (df.index <= m0) & (df.index > m0 - 36)
    df, da = df[ok], da[ok]
    res, n = [], 0
    for p in L.PROVS:
        x = np.c_[df[p].to_numpy(float), da[p].to_numpy(float)]
        x = x[~np.isnan(x).any(axis=1)]
        if len(x) < 12:
            return None, None, None
        res.append(x - x.mean(axis=0))
        n += len(x)
    R = np.vstack(res)
    S = R.T @ R / (n - len(L.PROVS))
    trail = {}
    for p in L.PROVS:
        x = np.c_[df[p].to_numpy(float), da[p].to_numpy(float)][-12:]
        trail[p] = x.mean(axis=0)
    return R, {"Sigma": S, "trail": trail}, {"lf": lf, "la": la}


def simulate(t: int) -> dict:
    """{(arm, province, lead): (Fdraws, HLdraws)} at origin t, or {} when fewer than 12 months are available."""
    m0 = L.m0_of(t)
    R, par, lg = increments(m0)
    if R is None:
        return {}
    S = par["Sigma"]
    C = np.linalg.cholesky(S)
    out = {}
    for pi, p in enumerate(L.PROVS):
        lf, la = lg["lf"][p], lg["la"][p]
        known_f = {m: lf.get(m, np.nan) for m in range(m0 - 12, m0 + 1)}
        known_a = {m: la.get(m, np.nan) for m in range(m0 - 12, m0 + 1)}
        if any(np.isnan(v) for v in list(known_f.values()) + list(known_a.values())):
            continue
        rng = np.random.default_rng(L.SEED + 10 * (t - 8000) + pi)
        z = rng.standard_normal((N_DRAW, HORIZON, 2))
        gauss = z @ C.T
        boot = R[rng.integers(0, len(R), (N_DRAW, HORIZON))]
        zg = rng.standard_normal((N_DRAW, 2)) @ np.linalg.cholesky(S / 12).T
        g1 = par["trail"][p]
        for arm in J_ARMS:
            if arm == "J0":
                g, gu, e = np.zeros(2), 0.0, gauss
            elif arm == "J1":
                g, gu, e = g1, 1.0, gauss
            elif arm == "J2":
                g, gu, e = np.full(2, ANCHOR), 0.0, gauss
            else:
                g, gu, e = 0.5 * g1 + 0.5 * ANCHOR, 0.5, (gauss if arm == "J3" else boot)
            inc = e + g + gu * zg[:, None, :]
            path = np.cumsum(inc, axis=1)                         # offsets 1..13
            Lf = known_f[m0] + path[:, :, 0]
            La = known_a[m0] + path[:, :, 1]

            def logv(Lsim, known, off):
                return Lsim[:, off - 1] if off >= 1 else np.full(N_DRAW, known[m0 + off])

            for k in F.LEADS:
                yf, ya = [], []
                for off in (3 * k - 1, 3 * k, 3 * k + 1):
                    yf.append(100 * (np.exp(logv(Lf, known_f, off) - logv(Lf, known_f, off - 12)) - 1))
                    ya.append(100 * (np.exp(logv(La, known_a, off) - logv(La, known_a, off - 12)) - 1))
                out[(arm, p, k)] = (np.mean(yf, axis=0), np.mean(ya, axis=0))
    return out


def prob(Fd, Hd, p) -> float:
    return float(np.mean(((Fd - F.TH_F[p]) > 0) | ((Fd - Hd - F.TH_G[p]) > 0)))


def build() -> tuple[pd.DataFrame, dict]:
    S = F.stack()
    origins = sorted(S["t"].unique())
    ps = F.ps_full().set_index(["province_code", "q"])
    rows, draws = [], {}
    for t in origins:
        sim = simulate(int(t))
        for (arm, p, k), (Fd, Hd) in sim.items():
            draws[(int(t), arm, p, k)] = (Fd, Hd)
            rows.append({"t": int(t), "lead": k, "province_code": p, "arm": arm, "pi_P": prob(Fd, Hd, p),
                         "F_mean": float(Fd.mean()), "F_sd": float(Fd.std()), "HL_mean": float(Hd.mean())})
    D = pd.DataFrame(rows)
    D["target_q"] = D["t"] + D["lead"]
    D["F"] = [ps["F"].get((p, q), np.nan) for p, q in zip(D["province_code"], D["target_q"])]
    D["HL"] = [ps["HL"].get((p, q), np.nan) for p, q in zip(D["province_code"], D["target_q"])]
    # J3T: track-record scaling of the J3 draws, from training rows of each lead only
    j3 = D[D["arm"] == "J3"]
    t_rows = []
    for t in sorted(j3["t"].unique()):
        tr = j3[(j3["t"] < t) & (j3["target_q"] <= t - 1) & j3["F"].notna()]
        sk = {}
        for k in F.LEADS:
            g = tr[tr["lead"] == k]
            if g["target_q"].nunique() >= 4:
                sk[k] = max(1.0, float(np.sqrt(np.mean((g["F"] - g["F_mean"]) ** 2)) / np.median(g["F_sd"])))
            else:
                sk[k] = 1.0
        for _, r in j3[j3["t"] == t].iterrows():
            Fd, Hd = draws[(int(t), "J3", r["province_code"], int(r["lead"]))]
            s = sk[int(r["lead"])]
            Fs, Hs = Fd.mean() + s * (Fd - Fd.mean()), Hd.mean() + s * (Hd - Hd.mean())
            t_rows.append({**r.to_dict(), "arm": "J3T", "pi_P": prob(Fs, Hs, r["province_code"]), "F_sd": float(Fs.std()),
                           "scale": s})
    D = pd.concat([D, pd.DataFrame(t_rows)], ignore_index=True)
    audit = audit_index(D)
    return D, audit


def audit_index(D: pd.DataFrame) -> dict:
    W = L.index_wide()
    y = L.yoy_published()
    out = {}
    for s, com in (("food", "food"), ("all", None)):
        I = W[s]
        calc = (100 * (I / I.shift(12) - 1)).stack().rename("calc").reset_index()
        calc.columns = ["ym", "province_code", "calc"]
        cm = [c for c in y["commodity"].unique() if (str(c).lower().startswith("food") if com else not str(c).lower().startswith("food"))][0]
        j = calc.merge(y[y["commodity"] == cm][["province_code", "ym", "yoy_pct"]], on=["province_code", "ym"]).dropna()
        out[f"yoy_index_vs_published_{s}"] = {"max_abs": float((j["calc"] - j["yoy_pct"]).abs().max()),
                                              "mean_abs": float((j["calc"] - j["yoy_pct"]).abs().mean()), "n": int(len(j))}
    S = F.stack()
    j0 = D[(D["arm"] == "J0") & (D["lead"] == 1)].merge(S[F.KEY if hasattr(F, "KEY") else ["t", "lead", "province_code"]
                                                          + ["A1_food"]], on=["t", "lead", "province_code"])
    d = j0["F_mean"] - (j0["A1_food"] + j0["province_code"].map(F.TH_F))
    out["J0_lead1_mean_vs_Z0_projection"] = {"max_abs": float(d.abs().max()), "mean": float(d.mean()), "n": int(d.notna().sum())}
    return out


# ================================================================================================ LJ
def lj(D: pd.DataFrame) -> pd.DataFrame:
    import lightgbm as lgb
    S = F.stack().copy()
    base = D[D["arm"] == "J3T"][["t", "lead", "province_code", "pi_P"]].rename(columns={"pi_P": "base"})
    S = S.merge(base, on=["t", "lead", "province_code"], how="inner")
    S["y_price"] = (((S["F"] - S["province_code"].map(F.TH_F)) > 0) | ((S["F"] - S["HL"] - S["province_code"].map(F.TH_G)) > 0)).astype(float)
    S.loc[S["F"].isna(), "y_price"] = np.nan
    S["init"] = np.log(np.clip(S["base"], .005, .995) / (1 - np.clip(S["base"], .005, .995)))
    cols = F.F12
    out = []

    def fit(tr, cfg):
        m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, n_estimators=cfg["trees"], num_leaves=2, max_depth=1,
                               min_child_samples=25, reg_lambda=10.0, reg_alpha=1.0, colsample_bytree=0.7, subsample=1.0,
                               deterministic=True, force_row_wise=True, feature_pre_filter=False, random_state=L.SEED,
                               n_jobs=1, verbose=-1)
        m.fit(tr[cols].astype(float), tr["y_price"].astype(int), init_score=tr["init"].to_numpy())
        return m

    def pred(m, te):
        raw = m.predict(te[cols].astype(float), raw_score=True) + te["init"].to_numpy()
        return 1 / (1 + np.exp(-raw))

    for t in sorted(S["t"].unique()):
        te = S[S["t"] == t]
        tr = S[(S["t"] < t) & (S["target_q"] <= t - 1) & S["y_price"].notna()]
        cfg_id = "base"
        p = te["base"].to_numpy(float)
        if len(tr) >= 30 and tr["y_price"].nunique() == 2:
            folds = []
            for o in sorted(tr["t"].unique())[-4:]:
                f = tr[(tr["t"] < o) & (tr["target_q"] <= o - 1)]
                h = tr[tr["t"] == o]
                if len(f) >= 30 and f["y_price"].nunique() == 2 and len(h):
                    folds.append((f, h))
            best, best_ll = REG_GRID[0], None
            for cfg in REG_GRID:
                if not folds:
                    break
                ys = np.concatenate([h["y_price"].to_numpy(int) for _, h in folds])
                pp = np.clip(np.concatenate([pred(fit(f, cfg), h) for f, h in folds]), 1e-6, 1 - 1e-6)
                ll = float(-np.mean(ys * np.log(pp) + (1 - ys) * np.log(1 - pp)))
                if best_ll is None or round(ll, 10) < round(best_ll, 10):
                    best, best_ll = cfg, ll
            p = pred(fit(tr, best), te)
            cfg_id = best["id"]
        out.append(te[["t", "lead", "province_code", "target_q"]].assign(arm="LJ", pi_P=p, cfg=cfg_id))
    return pd.concat(out, ignore_index=True)


def main():
    L.check_protocol()
    t0 = time.time()
    D, audit = build()
    print("J arms", round(time.time() - t0), "s", flush=True)
    LJ = lj(D)
    print("LJ", round(time.time() - t0), "s", LJ["cfg"].value_counts().to_dict(), flush=True)
    A = pd.concat([D, LJ], ignore_index=True)
    A.to_csv(L.OUT / "price_arms_ii.csv", index=False, lineterminator="\n", float_format="%.6g")
    L.dump("price_audit.json", audit)
    print(audit)
    s = D[D["arm"] == "J3T"].groupby("lead")["scale"].describe()
    print(s)


if __name__ == "__main__":
    main()
