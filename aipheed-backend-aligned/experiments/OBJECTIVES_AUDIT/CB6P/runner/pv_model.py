"""PV (../PREREGISTRATION_PV.md, hash checked): Part A candidate C-B6D-E-XA (province non-price supply shocks in the D
model) and Part V independent validation against PSA provincial subsistence / poverty incidence (2018, 2021, 2023).

    python pv_model.py run
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fi_provincial as FP  # noqa: E402

D, M, H, V = FP.D, FP.M, FP.H, FP.V
HERE, OUT = FP.HERE, FP.OUT
PLAN = HERE / "PREREGISTRATION_PV.md"
RAWP = HERE / "data" / "raw_prov"
THR, Q_EXT, LEADS = FP.THR, FP.Q_EXT, list(range(1, 9))
NAME2 = {"batangas": "PH040500000", "cavite": "PH040100000", "laguna": "PH040200000", "quezon": "PH040300000",
         "rizal": "PH040400000"}


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PV pre-registration changed"
    return h


def _geo(s: str) -> str | None:
    k = re.sub(r"[\s\d/a-z,\*]*$", "", s.strip(". ").lower() + " ").strip()
    k = re.sub(r"\s+[\d/a-z,\*\s]+$", "", s.strip(". ")).strip().lower()
    return NAME2.get(k)


def quarterly(f: Path, item_col: str, items: tuple) -> pd.DataFrame:
    d = pd.read_csv(f, encoding="utf-8-sig")
    d["pc"] = d["Geolocation"].map(_geo)
    d = d[d["pc"].notna() & d[item_col].str.strip(". ").isin(items)]
    cols = [c for c in d.columns if re.match(r"^\d{4} Quarter [1-4]$", c)]
    m = d.melt(id_vars=["pc", item_col], value_vars=cols, var_name="per", value_name="v")
    m["v"] = pd.to_numeric(m["v"], errors="coerce")
    m["q"] = m["per"].str[:4].astype(int) * 4 + m["per"].str[-1].astype(int) - 1
    return m.groupby(["q", "pc"])["v"].sum(min_count=1).unstack("pc").sort_index()


def shock(P: pd.DataFrame, q: int) -> dict:
    """Province yoy % at quarter q minus the five-province mean; winsorised [-100, 100]; NaN -> 0. Uses q and q-4 only."""
    if q not in P.index or q - 4 not in P.index:
        return {p: 0.0 for p in M.PROVS}
    y = 100 * (P.loc[q] / P.loc[q - 4] - 1)
    y = y.replace([np.inf, -np.inf], np.nan)
    dv = (y - y.mean()).clip(-100, 100)
    return {p: (0.0 if pd.isna(dv.get(p)) else float(dv[p])) for p in M.PROVS}


def run():
    pre = check()
    PC = quarterly(RAWP / "psa_palay_corn_prov_EVCP0.csv", "Ecosystem/Croptype", ("Palay", "Corn"))
    FI = quarterly(RAWP / "psa_fisheries_prov_GVFP1.csv", "Subsector", ("FISHERIES",))
    cov = {"palay_corn_quarters": int(PC.dropna(how="all").shape[0]), "fisheries_quarters": int(FI.dropna(how="all").shape[0]),
           "palay_corn_first": H.qs(int(PC.dropna(how="all").index.min())), "fisheries_first": H.qs(int(FI.dropna(how="all").index.min())),
           "provinces": sorted(PC.columns.tolist())}
    M._init()
    d, lab, T = M._G["d"], M._G["lab"], M._G["T"]
    Dm = FP.dev(FP.spliced_yoy())
    qd = FP.q_dev_ext(Dm)
    L = pd.read_csv(OUT / "fi_labels_ext.csv")
    sig = T[T["area"] == "BL"].set_index(["t", "lead"])["sigma_h"].to_dict()
    D1 = {t: M.d1(Dm, t) for t in range(H.qi("2012-Q2"), H.qi("2026-Q3") + 1)}
    S_PC = {t: shock(PC, t - 1) for t in D1}
    S_FI = {t: shock(FI, t - 1) for t in D1}
    # leakage check: truncate production at q <= t-1
    ok = all(shock(PC[PC.index <= t - 1], t - 1) == S_PC[t] and shock(FI[FI.index <= t - 1], t - 1) == S_FI[t] for t in D1)
    regE = D.regional("C-B6E")

    def dmodel(t, k, extra):
        X, Y = [], []
        for t2 in D1:
            if t2 >= t:
                continue
            for p in M.PROVS:
                v = qd.get((p, t2 + k))
                if v is None or v[1] > M.m_avail(t) or np.isnan(D1[t2][p]):
                    continue
                X.append([D1[t2][p]] + ([S_PC[t2][p], S_FI[t2][p]] if extra else []))
                Y.append(v[0])
        if len(Y) < D.MIN_PAIRS:
            known = [v[0] for v in qd.values() if v[1] <= M.m_avail(t)]
            return None, (float(np.sqrt(np.mean(np.square(known)))) if len(known) >= 5 else D.SD_DEFAULT)
        X, Y = np.asarray(X), np.asarray(Y)
        b, *_ = np.linalg.lstsq(X, Y, rcond=None)
        return b, float(np.sqrt(np.mean((Y - X @ b) ** 2)))

    rows = []
    for t in range(H.qi("2012-Q3"), H.qi("2026-Q3") + 1):
        for k in LEADS:
            r = regE.get((t, k))
            if r is None or pd.isna(r.p) or (t, k) not in sig:
                continue
            sh = float(sig[(t, k)])
            mu = D.H_LINE + sh * norm.ppf(np.clip(float(r.p), 1e-3, 1 - 1e-3))
            for name, extra in (("C-B6D-E-X-rep", False), ("C-B6D-E-XA", True)):
                b, sd = dmodel(t, k, extra)
                s = float(np.sqrt(sh ** 2 + 4 * sd ** 2))
                for p in M.PROVS:
                    if b is None or np.isnan(D1[t][p]):
                        parts = (0.0, 0.0)
                    else:
                        parts = (float(b[0] * D1[t][p]), float(b[1] * S_PC[t][p] + b[2] * S_FI[t][p]) if extra else 0.0)
                    dh = parts[0] + parts[1]
                    rows.append({"name": name, "t": t, "lead": k, "q": t + k, "province": p,
                                 "p": float(norm.cdf((mu + 2 * dh - THR) / s)), "D_hat": dh, "D_price_part": parts[0],
                                 "D_nonprice_part": parts[1], "prov_index": 2 * dh / s,
                                 "b": None if b is None else [float(x) for x in b]})
    F = pd.DataFrame(rows)
    old = pd.read_csv(OUT / "fi_provincial_fits.csv")
    j = F[F["name"] == "C-B6D-E-X-rep"].merge(old[old["name"] == "C-B6D-E-X"], on=["t", "lead", "province"], suffixes=("", "_o"))
    rep = float((j["p"] - j["p_o"]).abs().max())
    F = F[F["name"] == "C-B6D-E-XA"]
    F.to_csv(OUT / "pv_fits.csv", index=False)

    # ---------------- Part A scoring (B-ext)
    W0 = pd.concat([old[old["name"].isin(["C-B6D-E-X", "PERSIST-X", "CLIM-X"])], F]).pivot_table(
        index=["t", "lead", "q", "province"], columns="name", values="p").reset_index().merge(L[["province", "q", "y"]], on=["province", "q"])
    Rr = H.rp()
    res = {"prereg_sha256": pre, "data_coverage": cov, "leakage_unchanged": bool(ok), "C-B6D-E-X_reproduction_max_abs_diff": rep,
           "A": {}, "algorithm3_ext": {}, "V": {}}
    fam = {}

    def auc_ci(g, a):
        rng = np.random.default_rng(2036)
        qs = g["q"].unique()
        by = {q: h for q, h in g.groupby("q")}
        v = [roc_auc_score(h["y"], h[a]) for h in (pd.concat([by[q] for q in rng.choice(qs, len(qs))]) for _ in range(2000))
             if h["y"].nunique() == 2]
        return [float(np.quantile(v, .025)), float(np.quantile(v, .975))]

    for k in LEADS:
        ext = W0[(W0["lead"] == k) & (W0["q"] >= Q_EXT)].dropna(subset=["C-B6D-E-XA", "C-B6D-E-X", "PERSIST-X", "CLIM-X"])
        Ek = {}
        for a in (["C-B6D-E-XA", "C-B6D-E-X", "PERSIST-X", "CLIM-X"] if k <= 2 else ["C-B6D-E-XA", "C-B6D-E-X"]):
            m = M.metrics(ext["y"], ext[a])
            if k <= 2:
                m["auc_ci95"] = auc_ci(ext, a)
                h = ext.copy()
                h[Rr.P], h["target"] = h[a], h["q"].map(H.qs)
                h["PERSIST-SI_p"], h["CLIM_p"], h["ALWAYS-LOW_p"] = h["PERSIST-X"], h["CLIM-X"], 0.0
                rl = Rr.rules(h)
                m["failed"] = [x.split()[0] for x, v in rl.items() if not v["pass"]]
                m["rules"] = {x.split()[0]: str(v["value"]) for x, v in rl.items()}
                m["quarters_calls_differ"] = int(ext.assign(c=ext[a] >= .5).groupby("q")["c"].nunique().gt(1).sum())
            Ek[a] = m
        if k <= 2:
            for b in ("C-B6D-E-X", "PERSIST-X", "CLIM-X"):
                fam[(k, b)] = M.paired(ext, "C-B6D-E-XA", b)
            fx = F[(F["lead"] == k) & (F["q"] >= Q_EXT)]
            tot = (fx["D_price_part"].abs() + fx["D_nonprice_part"].abs()).replace(0, np.nan)
            Ek["nonprice_share_of_D_hat_pct"] = float((fx["D_nonprice_part"].abs() / tot).mean() * 100)
            Ek["coef_last_origin"] = fx[fx["t"] == fx["t"].max()]["b"].iloc[0]
        res["A"][str(k)] = Ek
    hp = M.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_6"] = [{"lead": k, "comparator": b, **v, "p_holm": hp[(k, b)],
                             "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for a in ("C-B6D-E-XA", "C-B6D-E-X"):
        mx = 0
        for k in LEADS:
            if res["A"][str(k)][a]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3_ext"][a] = mx
    vsx = {f["lead"]: f for f in res["holm_family_6"] if f["comparator"] == "C-B6D-E-X"}
    res["decision_adopt_XA"] = bool(not res["A"]["1"]["C-B6D-E-XA"]["failed"]
                                    and all(vsx[k]["diff"] < 0 and vsx[k]["p_one_sided"] < .10 for k in (1, 2))
                                    and all(res["A"][k]["nonprice_share_of_D_hat_pct"] >= 20 for k in ("1", "2")))

    # ---------------- Part V: independent provincial validation
    def table(fn, prefix):
        t = pd.read_csv(RAWP / fn, encoding="utf-8-sig")
        t["pc"] = t["Geolocation"].map(_geo)
        t = t[t["pc"].notna()]
        return {(r.pc, y): float(getattr(r, f"_{i + 1}")) for r in t.rename(columns=lambda c: c).itertuples()
                for i, c in enumerate(t.columns) for y in (2018, 2021, 2023) if c == f"{prefix} {y}"}
    outs = {"subsistence": table("psa_subsistence_families_prov_T3.csv", "Subsistence Incidence among Families (%)"),
            "poverty": table("psa_poverty_families_prov_T1.csv", "Poverty Incidence Among Families (%)")}
    sig_rows = []
    for y in (2018, 2021, 2023):
        qs_y = [y * 4 + i for i in range(4)]
        for p in M.PROVS:
            dv = [qd[(p, q)][0] for q in qs_y if (p, q) in qd]
            x1 = old[(old["name"] == "C-B6D-E-X") & (old["lead"] == 1) & old["q"].isin(qs_y) & (old["province"] == p)]["p"]
            xa = F[(F["lead"] == 1) & F["q"].isin(qs_y) & (F["province"] == p)]["p"]
            sig_rows.append({"year": y, "province": p, "V1_realised_2D": 2 * float(np.mean(dv)) if dv else np.nan,
                             "V2_C-B6D-E-X": float(x1.mean()) if len(x1) else np.nan,
                             "V3_C-B6D-E-XA": float(xa.mean()) if len(xa) else np.nan,
                             "subsistence": outs["subsistence"].get((p, y)), "poverty": outs["poverty"].get((p, y))})
    SV = pd.DataFrame(sig_rows)
    SV.to_csv(OUT / "pv_validation_table.csv", index=False)
    rng = np.random.default_rng(2036)
    for o in ("subsistence", "poverty"):
        for s in ("V1_realised_2D", "V2_C-B6D-E-X", "V3_C-B6D-E-XA"):
            g = SV.dropna(subset=[o, s])
            per = {int(y): float(spearmanr(h[s], h[o]).correlation) for y, h in g.groupby("year")}
            obs = float(np.nanmean(list(per.values())))
            null = []
            for _ in range(10000):
                v = [spearmanr(rng.permutation(h[s].to_numpy()), h[o]).correlation for _, h in g.groupby("year")]
                null.append(np.nanmean(v))
            res["V"][f"{s}_vs_{o}"] = {"rho_by_year": per, "mean_rho": obs, "perm_p_one_sided": float(np.mean(np.array(null) >= obs - 1e-12)),
                                       "n": int(len(g))}
    (OUT / "pv_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")

    print("coverage:", cov, "| leakage unchanged:", ok, "| X reproduction:", rep)
    for k in ("1", "2"):
        print(f"=== Lead {k} B-ext")
        for a, m in res["A"][k].items():
            if isinstance(m, dict) and "accuracy" in m:
                ci = f" [{m['auc_ci95'][0]:.2f},{m['auc_ci95'][1]:.2f}]" if "auc_ci95" in m else ""
                print(f"{a:12s} n {m['n']} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                      f"F1 {m['f1']:.3f} AUC {m['auc']:.3f}{ci} Brier {m['brier']:.4f} differ {m.get('quarters_calls_differ')} failed {m.get('failed')}")
        print("   non-price share of D_hat %:", round(res["A"][k]["nonprice_share_of_D_hat_pct"], 1), "| coef (D1, PC, FI) at last origin:",
              [round(x, 4) for x in res["A"][k]["coef_last_origin"]] if res["A"][k]["coef_last_origin"] else None)
    for f in res["holm_family_6"]:
        print(f"   L{f['lead']} XA vs {f['comparator']:10s} dBrier {f['diff']:+.4f} CI {f['ci95'][0]:+.4f}..{f['ci95'][1]:+.4f} p {f['p_one_sided']:.3f} Holm {f['p_holm']:.3f}")
    print("Algorithm 3:", res["algorithm3_ext"], "| adopt XA:", res["decision_adopt_XA"])
    print("--- Part V (province-years n=15; within-year Spearman, permutation within year)")
    for key, v in res["V"].items():
        print(f"   {key:36s} rho by year {({y: round(r, 2) for y, r in v['rho_by_year'].items()})} mean {v['mean_rho']:+.2f} p {v['perm_p_one_sided']:.3f}")
    print(SV.round(3).to_string(index=False))


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
