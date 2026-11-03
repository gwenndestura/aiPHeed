"""NOISE_W (EXPLORATORY, one candidate): C-b trained with SWS measurement-error sample weights (PLAN.md).

    python run_noise_w.py fit     # C-b reproduction (w = 1) and C-w, walk-forward, test leads 1-8 -> ../out/forecasts.csv
    python run_noise_w.py score   # R1-R7, Algorithm 3, Brier vs C-b, Objective 4 / H3, decision -> ../out/results.json
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

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parents[1]
PLAN = HERE / "PLAN.md"
OUT = HERE / "out"
NV2 = EXP / "NEW_MODEL" / "NEWS_V2" / "runner"
sys.path.insert(0, str(NV2))
import run_news_v2 as N  # noqa: E402   (table with z_N1R, C-b columns)
import align_cb as A  # noqa: E402      (Objective 4 / H3 comparators and paired test)

V, H, R = N.V, N.H, N.R
COLS = N.MODELS["C-b"]
SE1, LINE, WMIN = 5.7 / 1.96, 11.3, 0.10
TEST_LEADS = N.TEST_LEADS


def check_plan() -> str:
    b = PLAN.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PLAN.md changed after it was hashed"
    return h


class WLGBM(H.LGBM):
    """hr_lib.LGBM with sample weights (column 'w' of the training frame, if present); every setting unchanged."""

    def fit(self, tr: pd.DataFrame):
        import lightgbm as lgb
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, reg_lambda=5.0, deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=H.SEED_LGBM, n_jobs=1,
                                    verbose=-1, max_depth=self.cfg["depth"], num_leaves=self.cfg["leaves"],
                                    n_estimators=self.cfg["trees"], class_weight=self.cfg["cw"], min_child_samples=15)
        w = tr["w"].to_numpy(float) if "w" in tr else None
        self.m.fit(tr[self.cols].astype(float), y, sample_weight=w)
        return self


def wselect(tr: pd.DataFrame) -> dict:
    """hr_lib.lgbm_select with WLGBM fits; the criterion stays the unweighted hard-label log-loss (PLAN section 1)."""
    folds = H.inner_folds(tr)
    if not folds:
        return H.GRID[0]
    ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
    sc = {}
    for c in H.GRID:
        ps = np.concatenate([WLGBM(c, COLS, False).fit(f).predict(h) for f, h in folds])
        p = np.clip(ps, 1e-6, 1 - 1e-6)
        sc[c["id"]] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
    return min(H.GRID, key=lambda c: (round(sc[c["id"]], 9), c["id"]))


def _init():
    N._init()
    d = N._G["d"]
    N._G["rounds"] = d.sws[d.sws["area"] == "BL"].groupby("q").size().to_dict()


def _origin(job) -> pd.DataFrame:
    t, name, weighted = job
    d, S, lab = N._G["d"], N._G["T"], N._G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(TEST_LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    if weighted:
        se = SE1 / np.sqrt(tr["q"].map(N._G["rounds"]).astype(float))
        tr["w"] = np.maximum(WMIN, np.abs(2 * norm.cdf((tr["H"] - LINE) / se) - 1))
    trb = tr[tr["area"] == "BL"]
    te["p"], te["fallback"], te["cfg"] = np.nan, False, None
    if H.eligible(trb):
        cfg = wselect(tr)
        m = WLGBM(cfg, COLS, False).fit(tr)
        te["p"], te["cfg"] = m.predict(te), cfg["id"]
    else:
        te["p"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    return te[["t", "lead", "q", "p", "fallback", "cfg"]].assign(name=name)


def fit():
    plan = check_plan()
    jobs = [(t, n, w) for t in V.ORIGINS for n, w in (("C-b_repro", False), ("C-w", True))]
    with Pool(8, initializer=_init) as pool:
        parts = pool.map(_origin, jobs)
    F = pd.concat(parts, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    F.to_csv(OUT / "forecasts.csv", index=False)
    old = pd.read_csv(N.OUT / "forecasts.csv")
    old = old[old["name"] == "C-b"][["t", "lead", "p"]]
    m = old.merge(F[F["name"] == "C-b_repro"][["t", "lead", "p"]], on=["t", "lead"], suffixes=("_old", "_new"))
    rep = {"rows": int(len(m)), "max_abs_diff": float((m["p_old"] - m["p_new"]).abs().max())}
    ok = rep["rows"] == len(old) and rep["max_abs_diff"] <= 1e-12
    chk = {"plan_sha256": plan, "reproduction_Cb_unweighted": rep, "reproduced": ok}
    (OUT / "checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    print(json.dumps(chk, indent=1))
    if not ok:
        raise SystemExit("C-b is not reproduced with weights = 1: C-w is not scored")


def score():
    plan = check_plan()
    assert json.loads((OUT / "checks.json").read_text(encoding="utf-8"))["reproduced"]
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    CB = pd.read_csv(N.OUT / "forecasts.csv")
    F = pd.read_csv(OUT / "forecasts.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      CB[CB["name"] == "C-b"][["name", "t", "lead", "q", "p"]],
                      F[F["name"] == "C-w"][["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"plan_sha256": plan, "label": "EXPLORATORY; development evidence; one candidate", "leads": {}, "algorithm3": {}}
    for k in TEST_LEADS:
        W = R.frame(comp, k, lab_bl)
        g = W.dropna(subset=["C-w", "C-b"])
        Lk = {n: {"accuracy": float(((g[n] >= .5).astype(int) == g["y"]).mean())} for n in ("C-w", "C-b")}
        if k <= 2:
            for n in ("C-w", "C-b"):
                r = H.evaluate(g, n)
                Lk[n]["metrics"] = {x: r["metrics"].get(x) for x in ("accuracy", "balanced", "precision", "recall", "f1",
                                                                     "auc", "brier", "TP", "FP", "FN", "TN")}
                Lk[n]["rules"] = {x.split()[0]: {"pass": v["pass"], "value": v["value"]} for x, v in r["rules"].items()}
                Lk[n]["failed"] = [x for x, v in Lk[n]["rules"].items() if not v["pass"]]
            dv = ((g["C-w"] - g["y"]) ** 2 - (g["C-b"] - g["y"]) ** 2).to_numpy(float)
            Lk["vs_C-b"] = {"diff": float(dv.mean()),
                            "p_one_sided": float(np.mean(H.boot_mean(g["q"].to_numpy(), dv, H.rp()) >= 0)),
                            "calls_differing": int(((g["C-w"] >= .5) != (g["C-b"] >= .5)).sum())}
            era = W[W["t"] >= V.NEWS_ERA]
            for tab, names in (("objective4", A.OBJ4), ("h3", A.H3)):
                out = {c: A._paired(era if c in A.NLP_ONLY else W, "C-w", c) for c in names}
                hp = R.holm({c: v["p_one_sided"] for c, v in out.items()})
                for c in out:
                    out[c]["p_holm"] = hp[c]
                    out[c]["significantly_better"] = bool(out[c]["diff"] < 0 and hp[c] < .05)
                Lk[tab] = out
        res["leads"][str(k)] = Lk
    for n in ("C-w", "C-b"):
        mx = 0
        for k in TEST_LEADS:
            if res["leads"][str(k)][n]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][n] = {"mrlt": mx, "accuracy_by_lead": {k: res["leads"][str(k)][n]["accuracy"] for k in TEST_LEADS}}
    imp = all(res["leads"][str(k)]["vs_C-b"]["diff"] < 0 and res["leads"][str(k)]["vs_C-b"]["p_one_sided"] < .10
              and res["leads"][str(k)]["C-w"]["accuracy"] >= res["leads"][str(k)]["C-b"]["accuracy"] for k in (1, 2))
    beats = all(v["significantly_better"] for k in (1, 2) for v in res["leads"][str(k)]["h3"].values())
    res["decision"] = {"improves_Cb": bool(imp), "beats_all_baselines": bool(beats),
                       "summary": ("C-w improves C-b" if imp else "C-w does not improve C-b; C-b stays the main model")
                       + ("; C-w beats all six baselines" if beats else "; not all six baselines are beaten")}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        Lk = res["leads"][k]
        for n in ("C-w", "C-b"):
            m = Lk[n]["metrics"]
            print(f"L{k} {n}: acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {Lk[n]['failed']}")
        print(f"   vs C-b: diff {Lk['vs_C-b']['diff']:+.4f} p {Lk['vs_C-b']['p_one_sided']:.3f} calls changed "
              f"{Lk['vs_C-b']['calls_differing']}")
        print("   H3: " + "; ".join(f"{c} {v['diff']:+.3f} (Holm {v['p_holm']:.3f})" for c, v in Lk["h3"].items()))
    print("Algorithm 3:", {n: v["mrlt"] for n, v in res["algorithm3"].items()},
          {k: round(a, 3) for k, a in res["algorithm3"]["C-w"]["accuracy_by_lead"].items()})
    print("DECISION:", res["decision"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
