"""E84 library (PROTOCOL.md): provincial CPI subgroups, world food prices, and the component structural simulation
S-COMP. Timing: CPI months <= m0 (month 2 of quarter t); world prices month <= month(O(t)) - 4."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E84 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E84.parent / "E83_Deep_Reconstruction" / "runner"))
import e83_lib as E  # noqa: E402

L, np, pd = E.L, E.np, E.pd
ACQ = E84 / "data_acquired"
GROUPS = {"01.1.1.12": "rice", "01.1.1.16": "corn", "01.1.2": "meat", "01.1.3": "fish", "01.1.5": "oils",
          "01.1.6": "fruits", "01.1.7": "veg", "01.1.8": "sugar"}
WORLD = {"PRICENPQUSDM": "w_rice", "PFOODINDEXM": "w_food", "PMAIZMTUSDM": "w_maize", "PWHEAMTUSDM": "w_wheat",
         "PPOILUSDM": "w_palm", "PSUGAISAUSDM": "w_sugar"}
WORLD_LAG = 4
SHRINK_N = 24


def _ym(s: str) -> int:
    y, mon = s.split()
    return int(y) * 12 + L.MONTHS[mon]


def load_sub() -> tuple[pd.DataFrame, dict]:
    d = pd.read_csv(ACQ / "psa_cpi_subgroups_2021_2026.csv")
    d["province_code"] = d["Geolocation"].map(L.BY_NAME)
    code = d["Commodity Description"].str.split(" - ").str[0]
    d["group"] = code.map({**GROUPS, "01.1": "food", "0": "all"})
    d["ym"] = d["ym"].map(_ym)
    assert d["ym"].min() >= L.FIRST_YM and d["province_code"].notna().all() and d["group"].notna().all()
    w = pd.read_csv(ACQ / "psa_cpi_weights_2018.csv")
    w["province_code"] = w["Geolocation"].str.strip(". ").map(L.BY_NAME)
    w["group"] = w["Commodity Description"].str.split(" - ").str[0].map({**GROUPS, "01.1": "food", "0": "all"})
    W = {p: g.set_index("group")["Weights"].to_dict() for p, g in w.groupby("province_code")}
    return d[["province_code", "group", "ym", "index"]], W


def load_world() -> pd.DataFrame:
    out = []
    for s, name in WORLD.items():
        x = pd.read_csv(ACQ / f"{s}.csv")
        x["ym"] = x["observation_date"].str[:4].astype(int) * 12 + x["observation_date"].str[5:7].astype(int) - 1
        out.append(x.rename(columns={s: "value"}).assign(series=name)[["series", "ym", "value"]])
    w = pd.concat(out)
    assert w["ym"].min() >= L.FIRST_YM
    return w


def world_cut(w: pd.DataFrame, t: int) -> pd.DataFrame:
    O = L.origin(t)
    return w[w["ym"] <= O.year * 12 + O.month - 1 - WORLD_LAG]


def panel(sub: pd.DataFrame, W: dict, p: str, m0: int) -> pd.DataFrame:
    """Monthly log indices (months <= m0) of the 8 subgroups, the food residual and all items for province p."""
    s = sub[(sub["province_code"] == p) & (sub["ym"] <= m0)].pivot(index="ym", columns="group", values="index").sort_index()
    w = W[p]
    wres = w["food"] - sum(w[g] for g in GROUPS.values())
    s["resid"] = (w["food"] * s["food"] - sum(w[g] * s[g] for g in GROUPS.values())) / wres
    return np.log(s[list(GROUPS.values()) + ["resid", "food", "all"]]), wres


def _world_php(wc: pd.DataFrame, fx: pd.Series) -> pd.Series:
    """log world rice price in PHP per month (FX = quarterly BSP average of the month's quarter, else the latest)."""
    r = wc[wc["series"] == "w_rice"].set_index("ym")["value"].sort_index()
    out = {}
    for m, v in r.items():
        q = (m // 12) * 4 + (m % 12) // 3
        f = fx[fx.index <= q]
        if len(f):
            out[m] = math.log(v * f.iloc[-1])
    return pd.Series(out).sort_index()


def rice_beta(sub: pd.DataFrame, W: dict, m0: int, wphp: pd.Series) -> tuple[float, int]:
    """Pooled OLS (no intercept, demeaned by calendar month) of provincial rice log changes at month j on the world
    rice PHP 3-month log change ending at j-3; months j <= m0 only; shrunk toward 0 by n/(n+24)."""
    xs, ys = [], []
    wchg = wphp.diff(3)
    for p in L.PROVS:
        lr = np.log(sub[(sub.province_code == p) & (sub.group == "rice") & (sub.ym <= m0)].set_index("ym")["index"].sort_index())
        d = lr.diff().dropna()
        d = d - d.groupby(d.index % 12).transform("mean")
        for j, v in d.items():
            x = wchg.get(j - 3, np.nan)
            if pd.notna(x):
                xs.append(x / 3.0)
                ys.append(v)
    n = len(xs)
    if n < 12:
        return 0.0, n
    X, Y = np.array(xs), np.array(ys)
    b = float((X @ Y) / (X @ X)) if X @ X > 0 else 0.0
    return b * n / (n + SHRINK_N), n


def simulate_comp(d_cut, sub, W, wc, fx, t: int, k: int, passthrough: bool = True, n: int = 20000,
                  seed: int = 84, min_h: int = 5) -> dict:
    th = L.e40_spec()
    rng = np.random.default_rng(seed + 10 * t + k)
    hq = L.h_quarters(d_cut).sort_values("q")
    if len(hq) < min_h:                                  # E89 COV uses min_h = 3; the E84 default stays 5
        return {}
    qq, hh = hq["q"].to_numpy(), hq["H"].to_numpy()
    sig = float(np.sqrt(np.mean((np.diff(hh) / np.sqrt(np.diff(qq))) ** 2)))
    h = t + k - int(qq[-1])
    Hk = float(hh[-1]) + rng.normal(0, sig * math.sqrt(max(h, 0)), n) if h > 0 else \
        np.full(n, float(hq.set_index("q")["H"].get(t + k, hh[-1])))
    sws = Hk > th["H"]
    m0 = L.m0_of(t)
    ms = L.target_months(t, k)
    steps = max(ms) - m0
    beta, nb = 0.0, 0
    wchg_future = {}
    if passthrough:
        wphp = _world_php(wc, fx)
        beta, nb = rice_beta(sub, W, m0, wphp)
        wch = wphp.diff(3)
        last = wch.dropna()
        for i in range(1, steps + 1):
            m = m0 + i
            v = wch.get(m - 3, np.nan)
            wchg_future[m] = (v if pd.notna(v) else (last.iloc[-1] if len(last) else 0.0)) / 3.0
    out = {}
    for p in L.PROVS:
        P, wres = panel(sub, W, p, m0)
        if m0 not in P.index or len(P) < 13 or any((m - 12) not in P.index for m in ms):
            continue
        comps = list(GROUPS.values()) + ["resid", "all"]
        ch = P[comps].diff().dropna()
        smean = ch.groupby(ch.index % 12).mean()
        if len(smean) < 12:
            continue
        res = (ch - smean.loc[ch.index % 12].to_numpy()).iloc[-24:]
        if len(res) < 12:
            continue
        C = res.cov().to_numpy()
        C = 0.5 * C + 0.5 * np.diag(np.diag(C))           # shrink toward the diagonal (10 dimensions, <= 24 months)
        mu = np.array([[smean.loc[(m0 + i) % 12, c] for c in comps] for i in range(1, steps + 1)])
        if passthrough:
            ri = comps.index("rice")
            for i in range(1, steps + 1):
                mu[i - 1, ri] += beta * wchg_future[m0 + i]
        inc = mu[None] + rng.multivariate_normal(np.zeros(len(comps)), C, size=(n, steps))
        path = P.loc[m0, comps].to_numpy()[None, None, :] + np.cumsum(inc, axis=1)
        w = W[p]
        wv = np.array([w[g] for g in GROUPS.values()] + [wres])

        def lvl(m, j):          # simulated or observed index level of component column j in month m
            return np.exp(path[:, m - m0 - 1, j]) if m > m0 else np.full(n, math.exp(P.loc[m, comps[j]]))

        def food(m):
            if m <= m0:
                return np.full(n, math.exp(P.loc[m, "food"]))
            return sum(wv[j] * lvl(m, j) for j in range(len(wv))) / w["food"]
        # rescale so the simulated food index starts exactly at the published food index at m0
        base0 = sum(wv[j] * math.exp(P.loc[m0, comps[j]]) for j in range(len(wv))) / w["food"]
        scale = math.exp(P.loc[m0, "food"]) / base0
        Fq = np.mean([100 * ((food(m) * (scale if m > m0 else 1.0)) / math.exp(P.loc[m - 12, "food"]) - 1) for m in ms], axis=0)
        ai = comps.index("all")
        Gq = np.mean([100 * (lvl(m, ai) / math.exp(P.loc[m - 12, "all"]) - 1) for m in ms], axis=0)
        price = (Fq > th["food"][p]) | ((Fq - Gq) > th["gap"][p])
        out[p] = {"p": float(np.mean(sws & price)), "p_hunger": float(np.mean(sws)), "p_price": float(np.mean(price)),
                  "F_hat": float(np.mean(Fq)), "G_hat": float(np.mean(Fq - Gq)), "beta": beta, "beta_n": nb}
    return out


def extra_features(sub, wc, t: int) -> pd.DataFrame:
    m0 = L.m0_of(t)
    rows = []
    for p in L.PROVS:
        r = sub[(sub.province_code == p) & (sub.group == "rice")].set_index("ym")["index"]
        yoy = [100 * (r[m] / r[m - 12] - 1) for m in (m0 - 1, m0) if m in r.index and (m - 12) in r.index]
        rows.append({"t": t, "province_code": p, "rice_yoy_now": float(np.mean(yoy)) if len(yoy) == 2 else np.nan,
                     "rice_mom3": float(100 * math.log(r[m0] / r[m0 - 3])) if m0 in r.index and (m0 - 3) in r.index else np.nan})
    X = pd.DataFrame(rows)
    for s in ("w_rice", "w_food"):
        v = wc[wc.series == s].set_index("ym")["value"].sort_index()
        X[f"{s}_chg3"] = float(100 * math.log(v.iloc[-1] / v.iloc[-4])) if len(v) >= 4 else np.nan
        X[f"{s}_chg6"] = float(100 * math.log(v.iloc[-1] / v.iloc[-7])) if len(v) >= 7 else np.nan
    return X
