"""PROTOCOL section 7: why the ten families do not help. D1 coverage, D2 cross-sectional variation, D3 time
confound / redundancy, D4 predictive vs D5 explanatory association with the projection error (and with the hunger
change), D6 one-parameter out-of-sample correction vs the LightGBM add-one (architecture), D7 power (from
contrib_ii.json); reason assignment.

    python families.py          # out/families.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import ii_lib as L
from contrib_ii import boot

F, KEY = L.F, L.KEY
TEN = ["A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1"]
MAIN = {f: f for f in TEN}
MAIN["N1_gdelt"] = "G_pri_yoy"
MAIN["H1"] = "h_last"
ORDER = TEN + ["N1_gdelt", "H1"]
FAM_OF = {**{f: f for f in TEN}, "N1_gdelt": "N1", "H1": "H1"}


def spear_boot(q, x, y, draws=2000, seed=L.SEED) -> dict:
    q, x, y = np.asarray(q), np.asarray(x, float), np.asarray(y, float)
    m = ~np.isnan(x) & ~np.isnan(y)
    q, x, y = q[m], x[m], y[m]
    if len(x) < 8 or np.nanstd(x) == 0:
        return {"rho": float("nan"), "ci90": [float("nan")] * 2, "n": int(len(x))}
    r0 = spearmanr(x, y).statistic
    uq = np.unique(q)
    idx = [np.where(q == u)[0] for u in uq]
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(draws):
        ii = np.concatenate([idx[i] for i in rng.integers(0, len(uq), len(uq))])
        if np.std(x[ii]) > 0:
            bs.append(spearmanr(x[ii], y[ii]).statistic)
    return {"rho": float(r0), "ci90": [float(np.nanquantile(bs, .05)), float(np.nanquantile(bs, .95))], "n": int(len(x))}


def excl0(ci) -> bool:
    return bool(np.isfinite(ci[0]) and (ci[0] > 0 or ci[1] < 0))


def one_param(S: pd.DataFrame, col: str, origins) -> pd.DataFrame:
    """Rolling e_f = lead mean + beta*z(col) (ridge alpha 10 on the standardised column) vs lead mean only."""
    out = []
    for t in origins:
        tr = S[(S["t"] < t) & (S["target_q"] <= t - 1) & S["ef"].notna()]
        te = S[(S["t"] == t)].copy()
        if tr["target_q"].nunique() < 4:
            continue
        mu = tr.groupby("lead")["ef"].mean()
        r = tr["ef"] - tr["lead"].map(mu)
        x = tr[col].astype(float)
        med = x.median()
        x = x.fillna(med if np.isfinite(med) else 0.0)
        m, s = x.mean(), x.std(ddof=0)
        z = (x - m) / s if s > 0 else x * 0
        beta = float((z * r).sum() / ((z ** 2).sum() + 10.0))
        zt = ((te[col].astype(float).fillna(med if np.isfinite(med) else 0.0) - m) / s) if s > 0 else te[col] * 0
        te["lm"] = te["lead"].map(mu).fillna(0.0)
        te["lin"] = te["lm"] + beta * zt.fillna(0.0)
        out.append(te[KEY + ["q_t", "ef", "lm", "lin"]] if "q_t" in te else te[KEY + ["target_q", "ef", "lm", "lin"]])
    return pd.concat(out, ignore_index=True)


def main():
    L.check_protocol()
    S = F.stack().copy()
    E = F.eval_rows()
    origins = sorted(E["t"].unique())
    O = S[S["lead"] == 1].drop_duplicates(["t", "province_code"]).set_index(["t", "province_code"])
    ev = S[S["t"].isin(origins) & S["lead"].isin([1, 2, 3])]
    bl = L.bl_quarters().set_index("q")["H"]
    contrib = json.loads((L.OUT / "contrib_ii.json").read_text())
    # LightGBM add-one on the continuous error (FR Z3 grid), per row, for the architecture test
    allt = sorted(S.loc[S["t"] >= origins[0], "t"].unique())
    res = {}
    for name in ORDER:
        col = MAIN[name]
        fam = FAM_OF[name]
        r = {"column": col}
        # D1, D2, D3
        r["D1_missing"] = float(ev[col].isna().mean())
        o = O[[col, "A1_food"]].reset_index()
        o = o[o["t"] >= 2021 * 4]
        within = o.groupby("t")[col].var(ddof=0).mean()
        total = o[col].var(ddof=0)
        r["D2_between_province_share"] = float(within / total) if total and np.isfinite(total) and total > 0 else 0.0
        oo = o.dropna(subset=[col, "A1_food"])
        r["D3_rho_time"] = float(spearmanr(oo["t"], oo[col]).statistic) if oo[col].std() > 0 else float("nan")
        if len(oo) > 5 and oo[col].std() > 0:
            X = np.c_[np.ones(len(oo)), oo["A1_food"], oo["t"]]
            b, *_ = np.linalg.lstsq(X, oo[col].to_numpy(float), rcond=None)
            res_ = oo[col] - X @ b
            r["D3_r2_on_A1_t"] = float(1 - res_.var() / oo[col].var())
        else:
            r["D3_r2_on_A1_t"] = float("nan")
        # D4 predictive, D5 explanatory (price error); hunger channel (regional means)
        r["D4"], r["D5"], r["D4_hunger"], r["D5_hunger"] = {}, {}, {}, {}
        for k in (1, 2, 3):
            g = S[(S["lead"] == k) & S["ef"].notna()]
            r["D4"][k] = spear_boot(g["target_q"], g[col], g["ef"])
            xe = [O[col].get((q + 1, p), np.nan) for q, p in zip(g["target_q"], g["province_code"])]
            r["D5"][k] = spear_boot(g["target_q"], xe, g["ef"])
            # hunger: regional mean of the column at origin t vs BL(target) - newest reading at the A issue
            hh = []
            for t in sorted(S["t"].unique()):
                q = t + k
                if q not in bl.index:
                    continue
                kn = F.known(F.issue(int(t), "A"), "BL")
                if not kn:
                    continue
                xv = O.loc[t, col].mean() if t in O.index.get_level_values(0) else np.nan
                xq = O.loc[q + 1, col].mean() if (q + 1) in O.index.get_level_values(0) else np.nan
                hh.append({"q": q, "x": xv, "xe": xq, "dh": bl[q] - kn[-1][1]})
            hh = pd.DataFrame(hh)
            r["D4_hunger"][k] = spear_boot(hh["q"], hh["x"], hh["dh"])
            r["D5_hunger"][k] = spear_boot(hh["q"], hh["xe"], hh["dh"])
        # D6: one-parameter rolling correction vs lead mean; and vs the LightGBM add-one regressor (Z3 on col+lead)
        P1 = one_param(S, col, allt)
        Z = F.run_arm("Z3", allt, cols=[col, "lead"])[KEY + ["ef_hat"]]
        P1 = P1.merge(Z, on=KEY, how="left")
        P1 = P1[P1["ef"].notna() & P1["lead"].isin([1, 2, 3])]
        r["D6"] = {}
        for k in (1, 2, 3):
            g = P1[P1["lead"] == k]
            lin, lm, lg = (g["ef"] - g["lin"]) ** 2, (g["ef"] - g["lm"]) ** 2, (g["ef"] - g["ef_hat"]) ** 2
            zero = g["ef"] ** 2
            r["D6"][k] = {"lin_vs_leadmean_dmse": boot(g["target_q"], lm, lin),           # > 0 = column helps
                          "lin_vs_zero_dmse": boot(g["target_q"], zero, lin),
                          "lgbm_vs_zero_dmse": boot(g["target_q"], zero, lg),
                          "lin_vs_lgbm_dmse": boot(g["target_q"], lg, lin),                # > 0 = linear better
                          "rmse": {"lead_mean": float(np.sqrt(lm.mean())), "linear": float(np.sqrt(lin.mean())),
                                   "lgbm_add_one": float(np.sqrt(lg.mean())), "zero": float(np.sqrt(zero.mean()))}, "n": int(len(g))}
        # D7 power (from contrib_ii)
        c = contrib["families"].get(fam, {})
        r["D7"] = {"mde": c.get("mde_t43c"), "best_case_improvement": c.get("best_case_improvement"),
                   "add_one_diff": {k: v["diff"] for k, v in c.get("add_one", {}).items()},
                   "add_one_ci90": {k: v["ci90"] for k, v in c.get("add_one", {}).items()}} if c else None
        # reasons
        reasons = []
        if r["D1_missing"] > .30:
            reasons.append("coverage")
        if r["D2_between_province_share"] < .05:
            reasons.append("no cross-sectional information")
        if (np.isfinite(r["D3_rho_time"]) and abs(r["D3_rho_time"]) > .8) or (np.isfinite(r["D3_r2_on_A1_t"]) and r["D3_r2_on_A1_t"] > .8):
            reasons.append("time-confounded/redundant")
        if any(excl0(r["D5"][k]["ci90"]) and not excl0(r["D4"][k]["ci90"]) for k in (1, 2, 3)):
            reasons.append("coincident, not leading")
        if all(not excl0(r["D4"][k]["ci90"]) and not excl0(r["D5"][k]["ci90"]) for k in (1, 2, 3)):
            reasons.append("no association with the target")
        if any(r["D6"][k]["lin_vs_lgbm_dmse"]["ci90"][0] > 0 for k in (1, 2, 3)):
            reasons.append("architecture")
        if r["D7"] and any(r["D7"]["best_case_improvement"][str(k) if isinstance(next(iter(r["D7"]["best_case_improvement"])), str) else k] >= .01
                           and not (r["D7"]["add_one_ci90"][str(k) if isinstance(next(iter(r["D7"]["add_one_ci90"])), str) else k][0] > 0)
                           for k in (1, 2, 3)):
            reasons.append("underpowered")
        r["reasons"] = reasons
        res[name] = r
        print(f"{name:9s} miss {r['D1_missing']:.2f} xsec {r['D2_between_province_share']:.2f} rho_t {r['D3_rho_time']:+.2f} "
              f"R2 {r['D3_r2_on_A1_t']:.2f} | D4 " + " ".join(f"{r['D4'][k]['rho']:+.2f}" for k in (1, 2, 3)) +
              " | D5 " + " ".join(f"{r['D5'][k]['rho']:+.2f}{'*' if excl0(r['D5'][k]['ci90']) else ''}" for k in (1, 2, 3)) +
              " | D4h " + " ".join(f"{r['D4_hunger'][k]['rho']:+.2f}" for k in (1, 2, 3)) +
              " | D6 lin-lm " + " ".join(f"{r['D6'][k]['lin_vs_leadmean_dmse']['diff']:+.2f}" for k in (1, 2, 3)) +
              " lin-lgbm " + " ".join(f"{r['D6'][k]['lin_vs_lgbm_dmse']['diff']:+.2f}" for k in (1, 2, 3)) + f" | {reasons}", flush=True)
    L.dump("families.json", res)


if __name__ == "__main__":
    main()
