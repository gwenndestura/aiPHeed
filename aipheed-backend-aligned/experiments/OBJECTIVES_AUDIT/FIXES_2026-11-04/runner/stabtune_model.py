"""STAB-TUNE (PLAN_STAB_TUNE.md, hash checked): 12-origin inner validation, 32 settings, top-3 averaging.

    python stabtune_model.py fit     # arms T-B6 and T-B6E, walk-forward -> ../out/stabtune_fits.csv
    python stabtune_model.py score   # metrics, R1-R7, LOQO R7, Algorithm 3, Holm (PERSIST-P), serving rule -> ../out/stabtune_results.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import itertools
import json
import os
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
AUD = HERE.parent
EXP = AUD.parent
PLAN = HERE / "PLAN_STAB_TUNE.md"
OUT = HERE / "out"
sys.path.insert(0, str(AUD / "runner"))
import cb6_model as CB  # noqa: E402

PC, N, V, H, R, A = CB.PC, CB.N, CB.V, CB.H, CB.R, CB.A
ARMS = {"T-B6": PC.CB + CB.ST, "T-B6E": PC.CB + CB.ST + ["E1", "E2"]}
MONO = {"E1": 1, "E2": 1, "ST1": -1}
INNER, TOPK, SEED = 12, 3, 2036
PRODUCT = list(itertools.product([0.02, 0.05, 0.1], [50, 100, 150, 300], [1, 2, 3], [10, 15, 30, 50], [1, 5, 20],
                                 [0.6, 0.8, 1.0], [None, "balanced"], [False, True]))


def _space() -> list[dict]:
    sp = [dict(lr=0.05, trees=g["trees"], depth=g["depth"], mcs=15, lam=5.0, col=1.0, cw=g["cw"], mono=False) for g in H.GRID]
    for i in np.random.default_rng(SEED).choice(len(PRODUCT), 24, replace=False):
        lr, n, dpt, mcs, lam, col, cw, mo = PRODUCT[int(i)]
        sp.append(dict(lr=lr, trees=n, depth=dpt, mcs=mcs, lam=float(lam), col=col, cw=cw, mono=mo))
    for k, s in enumerate(sp):
        s["sid"], s["leaves"] = k, 2 ** s["depth"]
    return sp


SPACE = _space()


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PLAN_STAB_TUNE changed"
    return h


class M:
    def __init__(self, cfg: dict, cols: list[str]):
        self.cfg, self.cols = cfg, cols
        self.m = self.const = None

    def fit(self, tr: pd.DataFrame):
        import lightgbm as lgb
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        c = self.cfg
        kw = {}
        if c["mono"]:
            kw["monotone_constraints"] = [MONO.get(x, 0) for x in self.cols]
            kw["monotone_constraints_method"] = "basic"
        if c["col"] < 1.0:
            kw["colsample_bytree"] = c["col"]
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=c["lr"], reg_lambda=c["lam"], deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=H.SEED_LGBM, n_jobs=1,
                                    verbose=-1, max_depth=c["depth"], num_leaves=c["leaves"], n_estimators=c["trees"],
                                    class_weight=c["cw"], min_child_samples=c["mcs"], **kw)
        self.m.fit(tr[self.cols].astype(float), y)
        return self

    def predict(self, te: pd.DataFrame) -> np.ndarray:
        if self.m is None:
            return np.full(len(te), self.const)
        return self.m.predict_proba(te[self.cols].astype(float))[:, 1]


def folds12(tr: pd.DataFrame):
    origins = sorted(tr["t"].unique())[-INNER:]
    f = [(tr[tr["q"] <= o - 1], tr[tr["t"] == o]) for o in origins]
    return [(a, h) for a, h in f if a["q"].nunique() >= 3 and a["y"].nunique() == 2 and len(h)]


def top_settings(tr: pd.DataFrame, cols: list[str]) -> list[dict]:
    folds = folds12(tr)
    if len(folds) < 3:
        return [SPACE[0]]
    ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
    sc = {}
    for c in SPACE:
        ps = np.concatenate([M(c, cols).fit(f).predict(h) for f, h in folds])
        p = np.clip(ps, 1e-6, 1 - 1e-6)
        sc[c["sid"]] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
    return sorted(SPACE, key=lambda c: (round(sc[c["sid"]], 9), c["sid"]))[:TOPK]


def _origin(job) -> pd.DataFrame:
    """cb6_model._origin, with the top-3 average of the 12-origin selection."""
    t, name = job
    cols = ARMS[name]
    d, S, lab = N._G["d"], N._G["T"], N._G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(N.TEST_LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    te["p"], te["fallback"], te["cfg"], te["top"] = np.nan, False, None, None
    shap = None
    if H.eligible(trb):
        top = top_settings(tr, cols)
        ms = [M(c, cols).fit(tr) for c in top]
        te["p"] = np.mean([m.predict(te) for m in ms], axis=0)
        te["cfg"], te["top"] = top[0]["sid"], "|".join(str(c["sid"]) for c in top)
        frames = [V.shap_frame(m.m, te[cols]).reset_index(drop=True) if m.m is not None
                  else pd.DataFrame(0.0, index=range(len(te)), columns=cols) for m in ms]
        shap = sum(frames) / len(frames)
    else:
        te["p"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    out = te[["t", "lead", "q", "p", "fallback", "cfg", "top"]].assign(name=name).reset_index(drop=True)
    sh = (shap.reset_index(drop=True) if shap is not None else pd.DataFrame(0.0, index=out.index, columns=cols))
    return pd.concat([out, sh.add_prefix("shap_")], axis=1)


def fit():
    pre = check()
    jobs = [(t, a) for a in ARMS for t in V.ORIGINS]
    with Pool(max(1, (os.cpu_count() or 8) - 2), initializer=CB._init) as pool:
        F = pd.concat(pool.map(_origin, jobs, chunksize=1), ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    F.to_csv(OUT / "stabtune_fits.csv", index=False)
    (OUT / "stabtune_checks.json").write_text(json.dumps({"prereg_sha256": pre, "space": SPACE}, indent=1, default=str),
                                              encoding="utf-8")
    print({"rows": len(F), "arms": F["name"].nunique()})


def _thirds(g, n):
    th = [set(x) for x in np.array_split(np.array(sorted(g["q"].unique())), 3)]
    return [PC._acc(g[g["q"].isin(x)], n) for x in th]


def score():
    pre = check()
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    PP = pd.read_csv(OUT / "persist_p_forecasts.csv")
    B6 = pd.read_csv(AUD / "out" / "cb6_fits.csv")
    F = pd.read_csv(OUT / "stabtune_fits.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]], L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      PP[["name", "t", "lead", "q", "p"]], B6[["name", "t", "lead", "q", "p"]],
                      F[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    names = ["C-B6"] + list(ARMS)
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; attempts 28-29 on the same 62 quarters", "leads": {},
           "algorithm3": {}, "holm_family_14_persist_p": {}}
    fams = {a: {} for a in ARMS}
    for k in PC.TEST_LEADS:
        W = R.frame(comp, k, lab_bl)
        Lk = {n: {"accuracy": PC._acc(W.dropna(subset=[n]), n)} for n in names}
        if k <= 2:
            g = W.dropna(subset=names)
            for n in names:
                Lk[n].update(PC._summ(g, n))
                Lk[n]["thirds"] = _thirds(g, n)
                qs = sorted(g["q"].unique())
                Lk[n]["loqo_min_middle_third"] = float(min(_thirds(g[g["q"] != q], n)[1] for q in qs))
            for a in ARMS:
                Lk[f"{a}_vs_C-B6"] = {**PC._paired(g, a, "C-B6"), "calls_differing": int(((g[a] >= .5) != (g["C-B6"] >= .5)).sum())}
                era = W[W["t"] >= V.NEWS_ERA]
                for b in ["PERSIST-P" if b == "PERSIST" else b for b in PC.COMPS]:
                    fams[a][(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, a, b)
                s = F[(F["name"] == a) & (F["lead"] == k) & F["q"].isin(g["q"])]
                tot = s.filter(like="shap_").abs().sum(axis=1).replace(0, np.nan)
                Lk[f"{a}_shap_share_mean"] = {c: float((s[f"shap_{c}"].abs() / tot).mean())
                                              for c in ("E1", "E2", "ST1", "ST2") if f"shap_{c}" in s}
            Lk["T-B6E_vs_T-B6"] = {**PC._paired(g, "T-B6E", "T-B6"),
                                   "calls_differing": int(((g["T-B6E"] >= .5) != (g["T-B6"] >= .5)).sum())}
        res["leads"][str(k)] = Lk
    for a in ARMS:
        hp = R.holm({key: v["p_one_sided"] for key, v in fams[a].items()})
        res["holm_family_14_persist_p"][a] = [{"lead": k, "comparator": b, **v, "p_holm_14": hp[(k, b)],
                                               "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)}
                                              for (k, b), v in fams[a].items()]
    for n in names:
        mx = 0
        for k in PC.TEST_LEADS:
            if res["leads"][str(k)][n]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][n] = mx
    res["stability"] = {}
    for a in ARMS:
        o = F[(F["name"] == a)].drop_duplicates("t").sort_values("t")
        ev = o[o["t"] >= H.qi("2009-Q4")]["cfg"].dropna().astype(int)
        res["stability"][a] = {"eval_era_origins": int(len(ev)), "top1_switches": int((ev.diff().fillna(0) != 0).sum())}
    B6s = B6.drop_duplicates("t").sort_values("t")
    ev0 = B6s[B6s["t"] >= H.qi("2009-Q4")]["cfg"].dropna().astype(int)
    res["stability"]["C-B6"] = {"eval_era_origins": int(len(ev0)), "top1_switches": int((ev0.diff().fillna(0) != 0).sum())}

    def ok(n):
        return (all(not res["leads"][k][n]["failed"] for k in ("1", "2"))
                and all(res["leads"][k][n]["metrics"]["accuracy"] >= .75 for k in ("1", "2")))
    b_ok = all(res["leads"][k]["T-B6"]["metrics"]["brier"] <= res["leads"][k]["C-B6"]["metrics"]["brier"] for k in ("1", "2"))
    serve = "T-B6E" if ok("T-B6E") else ("T-B6" if ok("T-B6") and b_ok else "C-B6")
    e = res["leads"]["1"]["T-B6E_vs_T-B6"]
    res["decision"] = {"T-B6E_passes": ok("T-B6E"), "T-B6_passes": ok("T-B6"), "T-B6_brier_le_C-B6": b_ok,
                       "serve": serve, "E1E2_improve_lead1": bool(e["diff"] < 0 and e["p_one_sided"] < .05)}
    (OUT / "stabtune_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for n in names:
            m, r = res["leads"][k][n]["metrics"], res["leads"][k][n]
            print(f"L{k} {n:6s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} ECE {m['ece_10']:.3f} failed {r['failed']} "
                  f"thirds {[round(x, 3) for x in r['thirds']]} LOQO-mid-min {r['loqo_min_middle_third']:.3f}")
        for a in ARMS:
            v = res["leads"][k][f"{a}_vs_C-B6"]
            print(f"   {a} vs C-B6 diff {v['diff']:+.4f} CI {v['ci95'][0]:+.4f}..{v['ci95'][1]:+.4f} p {v['p_one_sided']:.4f} "
                  f"calls {v['calls_differing']}; SHAP {dict((x, round(y, 3)) for x, y in res['leads'][k][f'{a}_shap_share_mean'].items())}")
        v = res["leads"][k]["T-B6E_vs_T-B6"]
        print(f"   T-B6E vs T-B6 diff {v['diff']:+.4f} p {v['p_one_sided']:.4f} calls {v['calls_differing']}")
    for a in ARMS:
        print(a, "Holm (PERSIST-P) significant", sum(f["significant"] for f in res["holm_family_14_persist_p"][a]), "of 14;",
              [(f["lead"], round(f["diff"], 4), round(f["p_holm_14"], 4)) for f in res["holm_family_14_persist_p"][a]
               if f["comparator"] == "PERSIST-P"])
    print("Algorithm 3:", res["algorithm3"], "stability:", res["stability"])
    print("Decision:", res["decision"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
