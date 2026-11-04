"""C-E5 (CE5_PREREGISTRATION.md, hash checked): C-E5R recency weighting, C-E5C past-only recalibration of C-E2, and
the C-E2-NONEWS ablation.

    python ce5_model.py fit     # C-E5R and C-E2-NONEWS walk-forward; C-E5C from ce2_fits -> ../out/ce5_fits.csv
    python ce5_model.py score   # per candidate: metrics, R1-R7, Algorithm 3, 14-test Holm family, gates -> ../out/ce5_results.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
PREREG = HERE / "CE5_PREREGISTRATION.md"
OUT = HERE / "out"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce2_model as CE2  # noqa: E402
import ce_model as CE  # noqa: E402

PC, N, V, H, R, A = CE.PC, CE.N, CE.V, CE.H, CE.R, CE.A
HALF_LIFE, CAL_N, CAL_MIN = 16, 24, 12
NOT_NEWS = [c for c in CE.CE if c != "z_N1R"]
CANDS = ("C-E5R", "C-E5C", "C-E2-NONEWS")


def check() -> str:
    CE2.PREREG = PREREG
    try:
        return CE2.check()
    finally:
        CE2.PREREG = HERE / "CE2_PREREGISTRATION.md"


class WLGBM(H.LGBM):
    """hr_lib.LGBM with a per-row sample weight (hr_lib itself is not edited)."""

    def fit(self, tr: pd.DataFrame, w: np.ndarray):
        import lightgbm as lgb
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, reg_lambda=5.0, deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=H.SEED_LGBM, n_jobs=1,
                                    verbose=-1, max_depth=self.cfg["depth"], num_leaves=self.cfg["leaves"],
                                    n_estimators=self.cfg["trees"], class_weight=self.cfg["cw"], min_child_samples=15)
        self.m.fit(tr[self.cols].astype(float), y, sample_weight=w)
        return self


def _origin(job) -> pd.DataFrame:
    t, name = job
    d, S, lab = N._G["d"], N._G["T"], N._G["lab"]
    cols = NOT_NEWS if name == "C-E2-NONEWS" else CE.CE
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(PC.TEST_LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    out = te[["t", "lead", "q"]].reset_index(drop=True).assign(name=name, fallback=False)
    if not H.eligible(trb):
        out["p"], out["fallback"] = (float(trb["y"].mean()) if len(trb) else clim), True
        return out
    w = 0.5 ** ((t - tr["q"].to_numpy(float)) / HALF_LIFE) if name == "C-E5R" else None
    ps, shs = [], []
    for cfg in H.GRID:
        m = WLGBM(cfg, cols, False).fit(tr, w) if w is not None else H.LGBM(cfg, cols, False).fit(tr)
        ps.append(np.asarray(m.predict(te), float))
        shs.append(V.shap_frame(m.m, te[cols]).reset_index(drop=True) if m.m is not None
                   else pd.DataFrame(0.0, index=range(len(te)), columns=cols))
    out["p"] = np.mean(ps, axis=0)
    return pd.concat([out, (sum(shs) / len(shs)).add_prefix("shap_")], axis=1)


def recalibrate(F2: pd.DataFrame) -> pd.DataFrame:
    """C-E5C: Platt recalibration of C-E2 on its own last CAL_N forecasts (same lead) with labels known at O(t)."""
    from sklearn.linear_model import LogisticRegression
    d = H.load()
    lab = V.area_labels(d)
    lg = lambda p: np.log(np.clip(p, .001, .999) / (1 - np.clip(p, .001, .999)))  # noqa: E731
    rows = []
    for t in sorted(F2["t"].unique()):
        kb = V.known_labels(d, t, lab)
        kb = kb[kb["area"] == "BL"][["q", "y"]]
        for k in sorted(F2.loc[F2["t"] == t, "lead"].unique()):
            cur = F2[(F2["t"] == t) & (F2["lead"] == k)].iloc[0]
            past = F2[(F2["lead"] == k) & (F2["t"] < t) & ~F2["fallback"].astype(str).str.lower().eq("true")]
            past = past.merge(kb, on="q", how="inner").sort_values("q").tail(CAL_N)
            p, cal = float(cur["p"]), False
            if (len(past) >= CAL_MIN and past["y"].nunique() == 2
                    and str(cur["fallback"]).lower() != "true"):
                m = LogisticRegression(C=1.0).fit(lg(past["p"].to_numpy())[:, None], past["y"].to_numpy(int))
                p, cal = float(m.predict_proba(np.array([[lg(np.array([p]))[0]]]))[0, 1]), True
            rows.append({"t": int(t), "lead": int(k), "q": int(cur["q"]), "name": "C-E5C", "fallback": cur["fallback"],
                         "p": p, "calibrated": cal, "n_cal": int(len(past)),
                         "cal_last_q": int(past["q"].max()) if len(past) else None})
    return pd.DataFrame(rows)


def fit():
    pre = check()
    jobs = [(t, n) for n in ("C-E5R", "C-E2-NONEWS") for t in V.ORIGINS]
    with Pool(8, initializer=CE._init) as pool:
        F = pd.concat(pool.map(_origin, jobs), ignore_index=True)
    C = recalibrate(pd.read_csv(OUT / "ce2_fits.csv"))
    # leakage check: every calibration set ends before the origin's issue (target quarter <= t - 1 known at O(t))
    assert (C["cal_last_q"].dropna() <= C.loc[C["cal_last_q"].notna(), "t"] - 1).all()
    F = pd.concat([F, C], ignore_index=True)
    F.to_csv(OUT / "ce5_fits.csv", index=False)
    print({"prereg_sha256": pre, "rows": len(F), "per_name": F["name"].value_counts().to_dict(),
           "C-E5C_calibrated_share": round(float(C["calibrated"].mean()), 3)})


def score():
    pre = check()
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    CBF = pd.read_csv(N.OUT / "forecasts.csv")
    F2 = pd.read_csv(OUT / "ce2_fits.csv")
    F = pd.read_csv(OUT / "ce5_fits.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      CBF[CBF["name"] == "C-b"][["name", "t", "lead", "q", "p"]],
                      F2[["name", "t", "lead", "q", "p"]], F[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; 21st historical attempt (3 candidates)",
           "candidates": {}}
    names = ("C-b", "C-E2") + CANDS
    Wk = {k: R.frame(comp, k, lab_bl) for k in PC.TEST_LEADS}
    acc = {n: {k: PC._acc(Wk[k].dropna(subset=[n]), n) for k in PC.TEST_LEADS} for n in names}
    alg3 = {}
    for n in names:
        mx = 0
        for k in PC.TEST_LEADS:
            if acc[n][k] >= .75 and mx == k - 1:
                mx = k
        alg3[n] = mx
    for c in CANDS:
        out = {"leads": {}, "accuracy_by_lead": acc[c], "algorithm3": alg3[c]}
        fam = {}
        for k in (1, 2):
            W = Wk[k]
            g = W.dropna(subset=["C-b", "C-E2", c])
            Lk = {}
            for n in ("C-b", "C-E2", c):
                Lk[n] = PC._summ(g, n)
                th = [set(x) for x in np.array_split(np.array(sorted(g["q"].unique())), 3)]
                Lk[n]["thirds"] = [PC._acc(g[g["q"].isin(x)], n) for x in th]
                Lk[n]["low_recall_thirds"] = [float(((g[g["q"].isin(x)][n] < .5) & (g[g["q"].isin(x)]["y"] == 0)).sum()
                                                    / max(1, (g[g["q"].isin(x)]["y"] == 0).sum())) for x in th]
            Lk["vs_C-b"] = PC._paired(g, c, "C-b")
            Lk["vs_C-E2"] = PC._paired(g, c, "C-E2")
            era = W[W["t"] >= V.NEWS_ERA]
            for b in PC.COMPS:
                fam[(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, c, b)
            out["leads"][str(k)] = Lk
        hp = R.holm({key: v["p_one_sided"] for key, v in fam.items()})
        out["holm_family_14"] = [{"lead": k, "comparator": b, **v, "p_holm_14": hp[(k, b)],
                                  "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
        Ls = out["leads"]
        rules_ok = all(Ls[str(k)][c]["rules"][r]["pass"] for k in (1, 2) for r in ("R3", "R7"))
        out["adoption"] = {
            "R3_R7_pass_both_leads": rules_ok, "MRLT_ge_2": alg3[c] >= 2,
            "accuracy_ge_0.75_both_leads": all(Ls[str(k)][c]["metrics"]["accuracy"] >= .75 for k in (1, 2)),
            "brier_within_0.005_of_C-E2": all(Ls[str(k)]["vs_C-E2"]["diff"] <= .005 for k in (1, 2)),
            "leakage_checks": True}
        out["adoption"]["passes"] = c != "C-E2-NONEWS" and all(out["adoption"].values())
        res["candidates"][c] = out
    res["algorithm3"] = alg3
    res["accuracy_by_lead"] = acc
    (OUT / "ce5_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for c, o in res["candidates"].items():
        print(f"== {c}: Algorithm 3 {o['algorithm3']}; accuracy by lead {[round(x, 3) for x in o['accuracy_by_lead'].values()]}")
        for k in ("1", "2"):
            for n in ("C-E2", c):
                m = o["leads"][k][n]["metrics"]
                print(f"  L{k} {n:11s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} "
                      f"R {m['recall']:.3f} F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} "
                      f"failed {o['leads'][k][n]['failed']} thirds {[round(x, 3) for x in o['leads'][k][n]['thirds']]} "
                      f"LOWrec thirds {[round(x, 2) for x in o['leads'][k][n]['low_recall_thirds']]}")
            for b in ("C-b", "C-E2"):
                v = o["leads"][k][f"vs_{b}"]
                print(f"    vs {b}: diff {v['diff']:+.4f} p {v['p_one_sided']:.3f}")
        print("  significant", sum(f["significant"] for f in o["holm_family_14"]), "of 14:",
              [(f["lead"], f["comparator"], round(f["diff"], 4), round(f["p_holm_14"], 3)) for f in o["holm_family_14"]])
        print("  adoption", o["adoption"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
