"""C-B6D-E-XH (../PREREGISTRATION_XH.md, hash checked): H1/N1 momentum features for the regional hunger part (C-B6E-H),
the same Eq. 3 decomposition as C-B6D-E-X, and the paper's provincial logistic baselines.

    python xh_model.py features
    python xh_model.py fit        # regional C-B6E-H walk-forward fits
    python xh_model.py score      # regional (measured hunger) + provincial (Eq. 3) evaluation
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fi_provincial as FP  # noqa: E402

D, FR, M, H, V = FP.D, FP.FR, FP.M, FP.H, FP.V
CB, PC, N, R = FR.CB, FR.PC, FR.N, FR.R
HERE, AUD, OUT = FP.HERE, FP.AUD, FP.OUT
PLAN = HERE / "PREREGISTRATION_XH.md"
THR, Q_EXT, LEADS = FP.THR, FP.Q_EXT, list(range(1, 9))
NEW = ["h_change2", "h_accel", "h_run", "x_level", "x_change", "z_lag1", "z_accel"]
BASE_E = PC.CB + CB.ST + ["E1", "E2"]
COLS_H = BASE_E + NEW
LOGIT_SETS = {"LOGIT-COMB-P": ["h_last", "h_change", "R_food_yoy", "R_rice_yoy", "E1", "E2", "z_N1R", "D1"],
              "LOGIT-GOV-P": ["h_last", "h_change", "R_food_yoy", "R_rice_yoy", "E1", "E2", "D1"],
              "LOGIT-NLP-P": ["z_N1R"]}


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "XH pre-registration changed"
    return h


def feat_row(d, t, z) -> dict:
    kn = [h for _, h, _ in H.known(d, t, "BL")]
    o = {"t": t}
    o["h_change2"] = kn[-1] - kn[-3] if len(kn) >= 3 else np.nan
    o["h_accel"] = (kn[-1] - kn[-2]) - (kn[-2] - kn[-3]) if len(kn) >= 3 else np.nan
    if kn:
        above = kn[-1] > H.H_LINE
        n = 0
        for h in reversed(kn):
            if (h > H.H_LINE) == above:
                n += 1
            else:
                break
        o["h_run"] = n if above else -n
    else:
        o["h_run"] = np.nan
    lv, ch = [], []
    for a in V.OTHER_AREAS:
        ka = [h for _, h, _ in H.known(d, t, a)]
        if ka:
            lv.append(ka[-1])
        if len(ka) >= 2:
            ch.append(ka[-1] - ka[-2])
    o["x_level"] = float(np.mean(lv)) if lv else np.nan
    o["x_change"] = float(np.mean(ch)) if ch else np.nan
    o["z_lag1"] = z.get(t - 1, np.nan)
    o["z_accel"] = z.get(t, np.nan) - z.get(t - 1, np.nan)
    return o


def features():
    pre = check()
    d = H.load()
    z = pd.read_csv(N.OUT / "news_anomalies.csv").set_index("t")["z_N1R"].to_dict()
    Fe = pd.DataFrame([feat_row(d, t, z) for t in V.ORIGINS])
    # leakage check: dropping every SWS round published on/after O(t) leaves the features unchanged
    ok = True
    for t in V.ORIGINS[::7]:
        d2 = H.load()
        d2.sws = d2.sws[d2.sws["published"] < H.issue(t)]
        a, b = feat_row(d2, t, z), Fe[Fe["t"] == t].iloc[0].to_dict()
        ok &= all((np.isnan(a[c]) and np.isnan(b[c])) or abs(a[c] - b[c]) < 1e-12 for c in NEW)
    Fe.to_csv(OUT / "xh_features.csv", index=False)
    chk = {"prereg_sha256": pre, "leakage_unchanged": bool(ok), "non_missing": {c: float(Fe[c].notna().mean()) for c in NEW}}
    (OUT / "xh_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    print(chk)
    assert ok


def _init():
    FR._init()
    N._G["T"] = N._G["T"].merge(pd.read_csv(OUT / "xh_features.csv"), on="t", how="left")


def fit():
    pre = check()
    with Pool(8, initializer=_init) as pool:
        spot = V.ORIGINS[::20]
        rep = pd.concat(pool.map(CB._origin, [(t, "rep", BASE_E) for t in spot]), ignore_index=True)
        E = pd.read_csv(AUD / "FIXES_2026-11-04" / "out" / "cb6e_fits.csv").set_index(["t", "lead"])["p"]
        dmax = float((rep.set_index(["t", "lead"])["p"] - E.reindex(rep.set_index(["t", "lead"]).index)).abs().max())
        print({"C-B6E_spot_replication_max_abs_diff": dmax}, flush=True)
        assert dmax < 1e-9
        F = pd.concat(pool.map(CB._origin, [(t, "C-B6E-H", COLS_H) for t in V.ORIGINS]), ignore_index=True)
    F.to_csv(OUT / "xh_regional_fits.csv", index=False)
    print({"prereg_sha256": pre, "rows": len(F)})


def provincial(REGsrc: dict, name: str, ctx: dict) -> pd.DataFrame:
    """C-B6D-E-X's decomposition (fi_provincial.run) for one regional source."""
    qd, D1, sig, origins = ctx["qd"], ctx["D1"], ctx["sig"], ctx["origins"]
    rows = []
    for t in origins:
        for k in LEADS:
            r = REGsrc.get((t, k))
            if r is None or pd.isna(r.p) or (t, k) not in sig:
                continue
            X, Y = [], []
            for t2 in D1:
                if t2 >= t:
                    continue
                for p in M.PROVS:
                    v = qd.get((p, t2 + k))
                    if v is None or v[1] > M.m_avail(t) or np.isnan(D1[t2][p]):
                        continue
                    X.append(D1[t2][p])
                    Y.append(v[0])
            if len(Y) < D.MIN_PAIRS:
                known = [v[0] for v in qd.values() if v[1] <= M.m_avail(t)]
                b, sd = None, (float(np.sqrt(np.mean(np.square(known)))) if len(known) >= 5 else D.SD_DEFAULT)
            else:
                X, Y = np.asarray(X), np.asarray(Y)
                b = float(X @ Y / (X @ X))
                sd = float(np.sqrt(np.mean((Y - b * X) ** 2)))
            sh = float(sig[(t, k)])
            mu = D.H_LINE + sh * norm.ppf(np.clip(float(r.p), 1e-3, 1 - 1e-3))
            s = float(np.sqrt(sh ** 2 + 4 * sd ** 2))
            for p in M.PROVS:
                dh = 0.0 if b is None or np.isnan(D1[t][p]) else b * D1[t][p]
                rows.append({"name": name, "t": t, "lead": k, "q": t + k, "province": p,
                             "p": float(norm.cdf((mu + 2 * dh - THR) / s)), "p_hunger_part": float(norm.cdf((mu - THR) / sh)),
                             "D_hat": dh})
    return pd.DataFrame(rows)


def score():
    pre = check()
    # ---------------- regional hunger component on measured hunger
    d = H.load()
    lab_all = V.area_labels(d)
    lab_bl = lab_all[lab_all["area"] == "BL"]
    Lp = pd.read_csv(N.LEADS_FILE)
    E = pd.read_csv(AUD / "FIXES_2026-11-04" / "out" / "cb6e_fits.csv")
    XR = pd.read_csv(OUT / "xh_regional_fits.csv")
    comp = pd.concat([Lp[Lp["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      E[["name", "t", "lead", "q", "p"]], XR[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"prereg_sha256": pre, "regional": {}, "B_ext": {}, "B_old": {}, "algorithm3_ext": {}}
    for k in (1, 2):
        W = R.frame(comp, k, lab_bl).dropna(subset=["C-B6E", "C-B6E-H"])
        res["regional"][str(k)] = {n: PC._summ(W, n) for n in ("C-B6E", "C-B6E-H")}
        res["regional"][str(k)]["H_vs_E"] = PC._paired(W, "C-B6E-H", "C-B6E")
        s = XR[(XR["lead"] == k) & XR["q"].isin(W["q"])]
        tot = s.filter(like="shap_").abs().sum(axis=1).replace(0, np.nan)
        res["regional"][str(k)]["new_feature_shap_share_pct"] = float((s[[f"shap_{c}" for c in NEW]].abs().sum(axis=1) / tot).mean() * 100)

    # ---------------- provincial
    M._init()
    dd, lab, T = M._G["d"], M._G["lab"], M._G["T"]
    Dm = FP.dev(FP.spliced_yoy())
    ctx = {"qd": FP.q_dev_ext(Dm), "sig": T[T["area"] == "BL"].set_index(["t", "lead"])["sigma_h"].to_dict(),
           "origins": list(range(H.qi("2012-Q3"), H.qi("2026-Q3") + 1))}
    ctx["D1"] = {t: M.d1(Dm, t) for t in range(H.qi("2012-Q2"), H.qi("2026-Q3") + 1)}
    L = pd.read_csv(OUT / "fi_labels_ext.csv")
    regE = D.regional("C-B6E")
    regH = {(int(r.t), int(r.lead)): r for r in XR.itertuples()}
    PX = provincial(regE, "C-B6D-E-X", ctx)
    PH = provincial(regH, "C-B6D-E-XH", ctx)
    old = pd.read_csv(OUT / "fi_provincial_fits.csv")
    j = PX.merge(old[old["name"] == "C-B6D-E-X"], on=["t", "lead", "province"], suffixes=("", "_o"))
    res["C-B6D-E-X_reproduction_max_abs_diff"] = float((j["p"] - j["p_o"]).abs().max())
    assert res["C-B6D-E-X_reproduction_max_abs_diff"] < 1e-9

    # logistic baselines (paper RQ3), province rows
    Tb = T[(T["area"] == "BL") & T["lead"].isin([1, 2])][["t", "lead", "q"] + sorted({c for v in LOGIT_SETS.values() for c in v} - {"D1"})]
    Pr = pd.concat([Tb.assign(province=p, D1=[ctx["D1"].get(int(t), {}).get(p, np.nan) for t in Tb["t"]]) for p in M.PROVS])
    Pr = Pr.merge(L[["province", "q", "y", "last_m"]], on=["province", "q"], how="left")
    lrows = []
    for t in ctx["origins"]:
        kb = V.known_labels(dd, t, lab)
        known_q = set(kb[kb["area"] == "BL"]["q"])
        for k in (1, 2):
            te = Pr[(Pr["t"] == t) & (Pr["lead"] == k)]
            tr = Pr[(Pr["t"] < t) & (Pr["lead"] == k) & Pr["q"].isin(known_q) & (Pr["last_m"] <= M.m_avail(t))].dropna(subset=["y"])
            for nm, cols in LOGIT_SETS.items():
                if len(tr) >= 20 and tr["y"].nunique() == 2:
                    p = H.logit(tr.assign(y=tr["y"].astype(int)), te, cols)
                else:
                    p = np.full(len(te), float(tr["y"].mean()) if len(tr) else 0.5)
                lrows.append(te[["t", "lead", "q", "province"]].assign(name=nm, p=p))
    LG = pd.concat(lrows, ignore_index=True)
    X2 = pd.read_csv(OUT / "x2_fits.csv")
    allp = pd.concat([PH, old[old["name"].isin(["C-B6D-E-X", "PERSIST-X", "CLIM-X", "C-B6-R"])],
                      X2[X2["name"] == "PSA-only-P-X"], LG], ignore_index=True)
    allp[allp["name"] == "C-B6D-E-XH"].to_csv(OUT / "xh_provincial_fits.csv", index=False)
    LG.to_csv(OUT / "xh_logit_baselines.csv", index=False)
    W0 = allp.pivot_table(index=["t", "lead", "q", "province"], columns="name", values="p").reset_index()
    W0 = W0.merge(L[["province", "q", "y"]], on=["province", "q"])
    cbd = pd.read_csv(OUT / "cb6d_fits.csv")
    oa = pd.concat([cbd[cbd["name"] == "C-B6D-E"][["name", "t", "lead", "province", "p"]],
                    pd.read_csv(OUT / "cb6p2_fits.csv")[["name", "t", "lead", "province", "p"]]])
    W0 = W0.merge(oa.pivot_table(index=["t", "lead", "province"], columns="name", values="p").reset_index(),
                  on=["t", "lead", "province"], how="left")
    Rr = H.rp()
    arms = ["C-B6D-E-XH", "C-B6D-E-X", "PSA-only-P-X", "LOGIT-COMB-P", "LOGIT-GOV-P", "C-B6-R", "PERSIST-X", "CLIM-X"]

    def auc_ci(g, a):
        rng = np.random.default_rng(2036)
        qs = g["q"].unique()
        by = {q: h for q, h in g.groupby("q")}
        v = [roc_auc_score(h["y"], h[a]) for h in (pd.concat([by[q] for q in rng.choice(qs, len(qs))]) for _ in range(2000))
             if h["y"].nunique() == 2]
        return [float(np.quantile(v, .025)), float(np.quantile(v, .975))]

    fam = {}
    for k in LEADS:
        Wk = W0[W0["lead"] == k]
        ext = Wk[Wk["q"] >= Q_EXT].dropna(subset=["C-B6D-E-XH", "C-B6D-E-X", "PERSIST-X", "CLIM-X"])
        Ek = {}
        for a in (arms if k <= 2 else ["C-B6D-E-XH", "C-B6D-E-X"]):
            g = ext.dropna(subset=[a])
            m = M.metrics(g["y"], g[a])
            if k <= 2:
                m["auc_ci95"] = auc_ci(g, a)
                h = g.copy()
                h[Rr.P], h["target"] = h[a], h["q"].map(H.qs)
                h["PERSIST-SI_p"], h["CLIM_p"], h["ALWAYS-LOW_p"] = h["PERSIST-X"], h["CLIM-X"], 0.0
                rl = Rr.rules(h)
                m["rules"] = {x.split()[0]: {"pass": v["pass"], "value": str(v["value"])} for x, v in rl.items()}
                m["failed"] = [x.split()[0] for x, v in rl.items() if not v["pass"]]
                m["quarters_calls_differ"] = int(g.assign(c=g[a] >= .5).groupby("q")["c"].nunique().gt(1).sum())
            Ek[a] = m
        if k <= 2:
            news = ext[ext["q"] >= M.Q0].dropna(subset=["LOGIT-NLP-P"])
            Ek["LOGIT-NLP-P (news era)"] = M.metrics(news["y"], news["LOGIT-NLP-P"])
            for b in ("C-B6D-E-X", "PERSIST-X", "CLIM-X", "PSA-only-P-X", "LOGIT-COMB-P", "LOGIT-GOV-P"):
                fam[(k, b)] = M.paired(ext.dropna(subset=[b]), "C-B6D-E-XH", b)
            fam[(k, "LOGIT-NLP-P")] = M.paired(news, "C-B6D-E-XH", "LOGIT-NLP-P")
            fx = PH[(PH["lead"] == k) & (PH["q"] >= Q_EXT)].drop_duplicates("q").merge(lab[lab["area"] == "BL"][["q", "H"]], on="q")
            fo = PX[(PX["lead"] == k) & (PX["q"] >= Q_EXT)].drop_duplicates("q").merge(lab[lab["area"] == "BL"][["q", "H"]], on="q")
            Ek["hunger_part_accuracy_vs_measured_gt_11"] = {
                "XH": float(((fx["p_hunger_part"] >= .5) == (fx["H"] > THR)).mean()),
                "X": float(((fo["p_hunger_part"] >= .5) == (fo["H"] > THR)).mean()), "quarters": int(len(fx))}
            o = Wk[Wk["q"] >= M.Q0]
            res["B_old"][str(k)] = {a: {**M.metrics(g["y"], g[a]), "n": int(len(g))} for a in
                                    ("C-B6D-E-XH", "C-B6D-E-X", "C-B6D-E", "C-B6P2", "PERSIST-X")
                                    for g in [o.dropna(subset=[a, "C-B6D-E-XH"])]}
        res["B_ext"][str(k)] = Ek
    hp = M.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_14"] = [{"lead": k, "comparator": b, **v, "p_holm": hp[(k, b)],
                              "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for a in ("C-B6D-E-XH", "C-B6D-E-X"):
        mx = 0
        for k in LEADS:
            if res["B_ext"][str(k)][a]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3_ext"][a] = mx
    e1, e2 = res["B_ext"]["1"]["C-B6D-E-XH"], res["B_ext"]["2"]["C-B6D-E-XH"]
    s2 = {f["comparator"]: f for f in res["holm_family_14"] if f["lead"] == 2}
    res["decisions"] = {"lead2_fixed_R1_R7": not e2["failed"],
                        "lead1_preserved": (not e1["failed"]) and e1["accuracy"] >= .752,
                        "improves_over_C-B6D-E-X_lead2_holm": bool(s2["C-B6D-E-X"]["significant"])}
    res["decisions"]["adopt_as_provincial_candidate"] = all(res["decisions"].values())
    (OUT / "xh_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")

    for k in ("1", "2"):
        rg = res["regional"][k]
        print(f"--- Lead {k} REGIONAL (measured BL hunger > 11.3%, {len(R.frame(comp, int(k), lab_bl).dropna(subset=['C-B6E','C-B6E-H']))} q)")
        for n in ("C-B6E", "C-B6E-H"):
            m = rg[n]["metrics"]
            print(f"   {n:8s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {rg[n]['failed']}")
        print(f"   H-vs-E dBrier {rg['H_vs_E']['diff']:+.4f} p {rg['H_vs_E']['p_one_sided']:.3f}; new-feature SHAP share {rg['new_feature_shap_share_pct']:.1f}%")
        print(f"=== Lead {k} PROVINCIAL B-ext")
        for a, m in res["B_ext"][k].items():
            if a == "hunger_part_accuracy_vs_measured_gt_11":
                print("   hunger part accuracy:", m)
                continue
            ci = f" [{m['auc_ci95'][0]:.2f},{m['auc_ci95'][1]:.2f}]" if "auc_ci95" in m else ""
            print(f"{a:24s} n {m['n']} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f}{ci} Brier {m['brier']:.4f} failed {m.get('failed')}")
        for a, m in res["B_old"][k].items():
            print(f"   B-old {a:12s} n {m['n']} acc {m['accuracy']:.3f} F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f}")
    for f in res["holm_family_14"]:
        print(f"   L{f['lead']} XH vs {f['comparator']:12s} dBrier {f['diff']:+.4f} CI {f['ci95'][0]:+.3f}..{f['ci95'][1]:+.3f} "
              f"p {f['p_one_sided']:.3f} Holm {f['p_holm']:.3f} sig {f['significant']}")
    print("Algorithm 3:", res["algorithm3_ext"], "| reproduction:", res["C-B6D-E-X_reproduction_max_abs_diff"])
    print("Decisions:", res["decisions"])


if __name__ == "__main__":
    {"features": features, "fit": fit, "score": score}[sys.argv[1]]()
