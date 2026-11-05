"""C-B6D-E-X2 (../PREREGISTRATION_X2.md, hash checked): ENS regional combination + FE province mean reversion + CAL
walk-forward Platt; ablations; B-ext/B-old scoring; prospective seal.

    python x2_model.py run
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fi_provincial as FP  # noqa: E402

D, FR, M, H, V = FP.D, FP.FR, FP.M, FP.H, FP.V
HERE, OUT = FP.HERE, FP.OUT
PLAN = HERE / "PREREGISTRATION_X2.md"
THR, Q_EXT = FP.THR, FP.Q_EXT
LEADS = list(range(1, 9))
ENS = ["C-B6E", "C-B6", "NP", "HO"]
PRICE_IN = set(FR.PRICE)
HUNGER_IN = set(FR.HUNGER)
ARMS = {"C-B6D-E-X": ("C-B6E", False, False), "X-ENS": ("ENS", False, False), "X-FE": ("C-B6E", True, False),
        "X-CAL": ("C-B6E", False, True), "X2": ("ENS", True, True), "PSA-only-P-X": ("PSA-only", False, False)}


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "X2 pre-registration changed"
    return h


def shap_fracs(r) -> tuple[float, float]:
    shp = {c[5:]: abs(float(getattr(r, c))) for c in r._fields if c.startswith("shap_") and pd.notna(getattr(r, c))}
    tot = sum(shp.values())
    if tot == 0:
        return 0.0, 0.0
    return sum(v for c, v in shp.items() if c in HUNGER_IN) / tot, sum(v for c, v in shp.items() if c in PRICE_IN) / tot


def run():
    pre = check()
    M._init()
    d, lab, T = M._G["d"], M._G["lab"], M._G["T"]
    Dm = FP.dev(FP.spliced_yoy())
    qd = FP.q_dev_ext(Dm)
    L = pd.read_csv(OUT / "fi_labels_ext.csv")
    Lkey = {(r.province, int(r.q)): r for r in L.itertuples()}
    sig = T[T["area"] == "BL"].set_index(["t", "lead"])["sigma_h"].to_dict()
    D1 = {t: M.d1(Dm, t) for t in range(H.qi("2012-Q2"), H.qi("2026-Q3") + 1)}
    RF = pd.read_csv(OUT / "fi_regional_fits.csv")
    REG = {"C-B6E": D.regional("C-B6E"), "C-B6": D.regional("C-B6"), "PSA-only": D.regional("PSA-only"),
           **{n: {(int(r.t), int(r.lead)): r for r in RF[RF["name"] == n].itertuples()} for n in ("NP", "HO")}}

    def a_p(t):
        out = {}
        for p in M.PROVS:
            v = [x[0] for (pp, q), x in qd.items() if pp == p and x[1] <= M.m_avail(t)]
            out[p] = float(np.mean(v)) if len(v) >= 8 else 0.0
        return out

    def dmodel(t, k, fe, ap):
        X, Y = [], []
        for t2 in D1:
            if t2 >= t:
                continue
            for p in M.PROVS:
                v = qd.get((p, t2 + k))
                if v is None or v[1] > M.m_avail(t) or np.isnan(D1[t2][p]):
                    continue
                c = ap[p] if fe else 0.0
                X.append(D1[t2][p] - c)
                Y.append(v[0] - c)
        if len(Y) < D.MIN_PAIRS:
            known = [v[0] for v in qd.values() if v[1] <= M.m_avail(t)]
            return None, (float(np.sqrt(np.mean(np.square(known)))) if len(known) >= 5 else D.SD_DEFAULT)
        X, Y = np.asarray(X), np.asarray(Y)
        b = float(X @ Y / (X @ X))
        return b, float(np.sqrt(np.mean((Y - b * X) ** 2)))

    def regional_p(name, t, k):
        if name != "ENS":
            r = REG[name].get((t, k))
            return (None, None) if r is None or pd.isna(r.p) else (float(r.p), [r])
        rs = [REG[n].get((t, k)) for n in ENS]
        rs = [r for r in rs if r is not None and pd.notna(r.p)]
        if not rs:
            return None, None
        z = np.mean([norm.ppf(np.clip(float(r.p), 1e-3, 1 - 1e-3)) for r in rs])
        return float(norm.cdf(z)), rs

    raw_hist = {a: [] for a in ARMS}            # (t, lead, province, q, raw p)
    rows, comp = [], []
    origins = list(range(H.qi("2012-Q3"), H.qi("2026-Q3") + 1))
    for t in origins:
        kb = V.known_labels(d, t, lab)
        kb = kb[kb["area"] == "BL"]
        known_q = set(kb["q"])
        ap = a_p(t)
        for k in LEADS:
            if (t, k) not in sig:
                continue
            sh = float(sig[(t, k)])
            dm = {fe: dmodel(t, k, fe, ap) for fe in (False, True)}
            for arm, (rn, fe, cal) in ARMS.items():
                pr, rs = regional_p(rn, t, k)
                if pr is None:
                    continue
                mu = D.H_LINE + sh * norm.ppf(np.clip(pr, 1e-3, 1 - 1e-3))
                b, sd = dm[fe]
                s = float(np.sqrt(sh ** 2 + 4 * sd ** 2))
                calm = None
                if cal:
                    past = [(praw, Lkey[(p, q)].y) for (t2, k2, p, q, praw) in raw_hist[arm]
                            if t2 < t and k2 == k and (p, q) in Lkey and q in known_q and Lkey[(p, q)].last_m <= M.m_avail(t)]
                    if len(past) >= 40 and len({y for _, y in past}) == 2:
                        x = np.log(np.clip([u for u, _ in past], 1e-6, 1 - 1e-6) / (1 - np.clip([u for u, _ in past], 1e-6, 1 - 1e-6)))
                        calm = LogisticRegression(C=1e6, max_iter=5000).fit(x.reshape(-1, 1), [y for _, y in past])
                hf, pf = (np.mean([shap_fracs(r)[0] for r in rs]), np.mean([shap_fracs(r)[1] for r in rs]))
                if rn == "ENS":   # HO has hunger + lead only; shap_fracs handles it
                    pass
                for p in M.PROVS:
                    if b is None or np.isnan(D1[t][p]):
                        dh = ap[p] if fe else 0.0
                    else:
                        c = ap[p] if fe else 0.0
                        dh = c + b * (D1[t][p] - c)
                    praw = float(norm.cdf((mu + 2 * dh - THR) / s))
                    raw_hist[arm].append((t, k, p, t + k, praw))
                    pc = praw
                    if calm is not None:
                        lg = np.log(np.clip(praw, 1e-6, 1 - 1e-6) / (1 - np.clip(praw, 1e-6, 1 - 1e-6)))
                        pc = float(calm.predict_proba([[lg]])[0, 1])
                    rows.append({"name": arm, "t": t, "lead": k, "q": t + k, "province": p, "p": pc, "p_raw": praw,
                                 "D_hat": dh, "p_hunger_part": float(norm.cdf((mu - THR) / sh)), "calibrated": calm is not None})
                    if arm in ("X2", "C-B6D-E-X"):
                        reg = abs(mu - THR) / s
                        comp.append({"name": arm, "t": t, "lead": k, "q": t + k, "province": p, "hunger": reg * hf,
                                     "regional_price": reg * pf, "regional_other": reg * (1 - hf - pf),
                                     "province_price": abs(2 * dh / s)})
    F = pd.DataFrame(rows)
    C = pd.DataFrame(comp)
    F.to_csv(OUT / "x2_fits.csv", index=False)
    C.to_csv(OUT / "x2_contrib.csv", index=False)

    # reproduction of the stored C-B6D-E-X
    old = pd.read_csv(OUT / "fi_provincial_fits.csv")
    j = F[F["name"] == "C-B6D-E-X"].merge(old[old["name"] == "C-B6D-E-X"], on=["t", "lead", "province"], suffixes=("", "_o"))
    repro = float((j["p"] - j["p_o"]).abs().max())
    print({"C-B6D-E-X_reproduction_max_abs_diff": repro, "rows": len(j)}, flush=True)
    assert repro < 1e-9

    # ------------------------------------------------------------------ scoring
    base = old[old["name"].isin(["PERSIST-X", "CLIM-X", "C-B6-R"])][["name", "t", "lead", "q", "province", "p"]]
    W0 = pd.concat([base, F[["name", "t", "lead", "q", "province", "p"]]]).pivot_table(
        index=["t", "lead", "q", "province"], columns="name", values="p").reset_index()
    W0 = W0.merge(L[["province", "q", "y"]], on=["province", "q"])
    cbd = pd.read_csv(OUT / "cb6d_fits.csv")
    oldarms = pd.concat([cbd[cbd["name"].isin(["C-B6D-E", "NLP-only-P"])][["name", "t", "lead", "province", "p"]],
                         pd.read_csv(OUT / "cb6p2_fits.csv")[["name", "t", "lead", "province", "p"]],
                         (lambda f: f[f["name"] == "LOGIT"][["name", "t", "lead", "province", "p"]])(pd.read_csv(OUT / "cb6p_fits.csv"))])
    W0 = W0.merge(oldarms.pivot_table(index=["t", "lead", "province"], columns="name", values="p").reset_index(),
                  on=["t", "lead", "province"], how="left")
    Rr = H.rp()
    ext_arms = ["X2", "X-ENS", "X-FE", "X-CAL", "C-B6D-E-X", "PSA-only-P-X", "C-B6-R", "PERSIST-X", "CLIM-X"]
    old_arms = ["X2", "C-B6D-E-X", "C-B6D-E", "C-B6P2", "LOGIT", "NLP-only-P", "C-B6-R", "PERSIST-X"]
    res = {"prereg_sha256": pre, "reproduction_max_abs_diff": repro, "B_ext": {}, "B_old": {}, "algorithm3_ext": {}}
    fam = {}

    def auc_ci(g, a):
        rng = np.random.default_rng(2036)
        qs = g["q"].unique()
        by = {q: h for q, h in g.groupby("q")}
        v = []
        for _ in range(2000):
            h = pd.concat([by[q] for q in rng.choice(qs, len(qs))])
            if h["y"].nunique() == 2:
                v.append(roc_auc_score(h["y"], h[a]))
        return [float(np.quantile(v, .025)), float(np.quantile(v, .975))]

    for k in LEADS:
        Wk = W0[W0["lead"] == k]
        ext = Wk[Wk["q"] >= Q_EXT].dropna(subset=ext_arms)
        E = {}
        for a in ext_arms:
            m = M.metrics(ext["y"], ext[a])
            if k <= 2:
                m["auc_ci95"] = auc_ci(ext, a)
                h = ext.copy()
                h[Rr.P], h["target"] = h[a], h["q"].map(H.qs)
                h["PERSIST-SI_p"], h["CLIM_p"], h["ALWAYS-LOW_p"] = h["PERSIST-X"], h["CLIM-X"], 0.0
                rl = Rr.rules(h)
                m["rules"] = {x.split()[0]: {"pass": v["pass"], "value": str(v["value"])} for x, v in rl.items()}
                m["failed"] = [x.split()[0] for x, v in rl.items() if not v["pass"]]
                m["quarters_calls_differ"] = int(ext.assign(c=ext[a] >= .5).groupby("q")["c"].nunique().gt(1).sum())
            E[a] = m
        res["B_ext"][str(k)] = E
        if k <= 2:
            for b in ("C-B6D-E-X", "PERSIST-X", "CLIM-X", "C-B6-R", "PSA-only-P-X", "X-ENS"):
                fam[(k, b)] = M.paired(ext, "X2", b)
            res["B_ext"][str(k)]["ablations_vs_C-B6D-E-X"] = {a: M.paired(ext, a, "C-B6D-E-X") for a in ("X-ENS", "X-FE", "X-CAL")}
            o = Wk[Wk["q"] >= M.Q0]
            B = {}
            for a in old_arms:
                g = o.dropna(subset=[a, "X2"])
                B[a] = {**M.metrics(g["y"], g[a]), "n": int(len(g))}
                if a != "X2":
                    B[a]["X2_minus_this_brier"] = M.paired(g, "X2", a)
            res["B_old"][str(k)] = B
            fx = F[(F["name"] == "X2") & (F["lead"] == k) & (F["q"] >= Q_EXT)]
            hq = fx.drop_duplicates("q").merge(lab[lab["area"] == "BL"][["q", "H"]], on="q")
            fd = fx.merge(L[["province", "q", "D"]], on=["province", "q"])
            c = C[(C["name"] == "X2") & (C["lead"] == k) & (C["q"] >= Q_EXT)][["hunger", "regional_price", "regional_other", "province_price"]]
            shp = c.div(c.sum(axis=1).replace(0, np.nan), axis=0) * 100
            res["B_ext"][str(k)]["X2_components"] = {
                "hunger_part_accuracy_vs_measured_BL_hunger_gt_11": float(((hq["p_hunger_part"] >= .5) == (hq["H"] > THR)).mean()),
                "D_hat_corr": float(np.corrcoef(fd["D_hat"], fd["D"])[0, 1]),
                "D_hat_sign_accuracy": float((np.sign(fd["D_hat"]) == np.sign(fd["D"]))[fd["D_hat"] != 0].mean()),
                "share_pct": {x: float(shp[x].mean()) for x in shp.columns},
                "calibrated_share": float(fx["calibrated"].mean())}
    hp = M.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_12"] = [{"lead": k, "comparator": b, **v, "p_holm": hp[(k, b)],
                              "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for a in ext_arms:
        mx = 0
        for k in LEADS:
            if res["B_ext"][str(k)][a]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3_ext"][a] = mx
    e1, e2 = res["B_ext"]["1"], res["B_ext"]["2"]
    sig2 = {f["comparator"]: f for f in res["holm_family_12"] if f["lead"] == 2}
    res["decisions"] = {
        "lead2_fixed_R1_R7": not e2["X2"]["failed"],
        "lead1_preserved": (not e1["X2"]["failed"]) and e1["X2"]["accuracy"] >= .772 - .02,
        "improvement_over_C-B6D-E-X_lead2_holm": bool(sig2["C-B6D-E-X"]["significant"]),
        "hunger_share_ge_30pct": all(res["B_ext"][k]["X2_components"]["share_pct"]["hunger"] >= 30 for k in ("1", "2"))}

    # ------------------------------------------------------------------ prospective seal
    seal = F[(F["t"] == H.qi("2026-Q3")) & F["lead"].isin([1, 2]) & F["name"].isin(["C-B6D-E-X", "X2"])][
        ["name", "t", "lead", "q", "province", "p", "p_raw", "D_hat", "p_hunger_part"]].copy()
    seal["issue_date"], seal["target"] = H.issue(H.qi("2026-Q3")), seal["q"].map(H.qs)
    seal = seal.sort_values(["name", "lead", "province"]).reset_index(drop=True)
    sp = OUT / "seal_prospective_X2.csv"
    if not sp.exists():
        seal.to_csv(sp, index=False, lineterminator="\n")
        (OUT / "seal_prospective_X2.sha256").write_text(hashlib.sha256(sp.read_bytes()).hexdigest() + "  seal_prospective_X2.csv\n")
    res["seal_sha256"] = (OUT / "seal_prospective_X2.sha256").read_text().split()[0]
    (OUT / "x2_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")

    for k in ("1", "2"):
        print(f"=== Lead {k} B-ext ({res['B_ext'][k]['X2']['n']} rows)")
        for a in ext_arms:
            m = res["B_ext"][k][a]
            print(f"{a:12s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} [{m['auc_ci95'][0]:.2f},{m['auc_ci95'][1]:.2f}] Brier {m['brier']:.4f} "
                  f"differ {m['quarters_calls_differ']} failed {m['failed']}")
        print("   ablations vs X:", {a: f"{v['diff']:+.4f} p {v['p_one_sided']:.3f}" for a, v in res["B_ext"][k]["ablations_vs_C-B6D-E-X"].items()})
        print("   X2 components:", json.dumps(res["B_ext"][k]["X2_components"], default=lambda x: round(x, 3)))
        print(f"--- Lead {k} B-old (2021+)")
        for a, m in res["B_old"][k].items():
            extra = f" | X2-this {m['X2_minus_this_brier']['diff']:+.4f} p {m['X2_minus_this_brier']['p_one_sided']:.3f}" if a != "X2" else ""
            print(f"{a:12s} n {m['n']} acc {m['accuracy']:.3f} F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f}{extra}")
    for f in res["holm_family_12"]:
        print(f"   L{f['lead']} X2 vs {f['comparator']:12s} dBrier {f['diff']:+.4f} CI {f['ci95'][0]:+.3f}..{f['ci95'][1]:+.3f} "
              f"p {f['p_one_sided']:.3f} Holm {f['p_holm']:.3f} sig {f['significant']}")
    print("Algorithm 3:", res["algorithm3_ext"])
    print("Decisions:", res["decisions"])
    print("Seal:", res["seal_sha256"])


if __name__ == "__main__":
    {"run": run}[sys.argv[1]]()
