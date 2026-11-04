"""C-B6E-OPT (PLAN_CB6E_OPT.md, hash checked): C-B6E with a 32-setting nested selection inside the walk-forward.

    python cb6eopt_model.py fit     # replication gate (restricted space = C-B6E), walk-forward -> ../out/cb6eopt_fits.csv
    python cb6eopt_model.py score   # metrics, R1-R7, Algorithm 3, Holm family with PERSIST-P, serving rule -> ../out/cb6eopt_results.json
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

HERE = Path(__file__).resolve().parents[1]
AUD = HERE.parent
EXP = AUD.parent
PLAN = HERE / "PLAN_CB6E_OPT.md"
OUT = HERE / "out"
sys.path.insert(0, str(AUD / "runner"))
import cb6_model as CB  # noqa: E402

PC, N, V, H, R, A = CB.PC, CB.N, CB.V, CB.H, CB.R, CB.A
COLS = PC.CB + CB.ST + ["E1", "E2"]
MONO = {"E1": 1, "E2": 1, "ST1": -1}
NAME, REF = "C-B6E-OPT", "C-B6"
SPACE = [dict(g, sid=i, mono=mo, mcs=mc) for i, (g, mo, mc) in
         enumerate([(g, mo, mc) for g in H.GRID for mo in (False, True) for mc in (15, 30)])]
RESTRICTED = [s for s in SPACE if not s["mono"] and s["mcs"] == 15]


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PLAN_CB6E_OPT changed"
    return h


class LGBM2:
    """hr_lib.LGBM with the direction constraints and min_child_samples of the setting."""

    def __init__(self, cfg: dict, cols: list[str]):
        self.cfg, self.cols = cfg, cols
        self.m = self.const = None

    def fit(self, tr: pd.DataFrame):
        import lightgbm as lgb
        y = tr["y"].to_numpy(int)
        if len(set(y)) < 2:
            self.const = float(y.mean()) if len(y) else 0.5
            return self
        kw = {}
        if self.cfg["mono"]:
            kw["monotone_constraints"] = [MONO.get(c, 0) for c in self.cols]
            kw["monotone_constraints_method"] = "basic"
        self.m = lgb.LGBMClassifier(objective="binary", learning_rate=0.05, reg_lambda=5.0, deterministic=True,
                                    force_row_wise=True, feature_pre_filter=False, random_state=H.SEED_LGBM, n_jobs=1,
                                    verbose=-1, max_depth=self.cfg["depth"], num_leaves=self.cfg["leaves"],
                                    n_estimators=self.cfg["trees"], class_weight=self.cfg["cw"],
                                    min_child_samples=self.cfg["mcs"], **kw)
        self.m.fit(tr[self.cols].astype(float), y)
        return self

    def predict(self, te: pd.DataFrame) -> np.ndarray:
        if self.m is None:
            return np.full(len(te), self.const)
        return self.m.predict_proba(te[self.cols].astype(float))[:, 1]


def select(tr: pd.DataFrame, cols: list[str], space: list[dict]) -> dict:
    folds = H.inner_folds(tr)
    if not folds:
        return space[0]
    ys = np.concatenate([h["y"].to_numpy(int) for _, h in folds])
    sc = {}
    for c in space:
        ps = np.concatenate([LGBM2(c, cols).fit(f).predict(h) for f, h in folds])
        p = np.clip(ps, 1e-6, 1 - 1e-6)
        sc[c["sid"]] = float(-np.mean(ys * np.log(p) + (1 - ys) * np.log(1 - p)))
    return min(space, key=lambda c: (round(sc[c["sid"]], 9), c["sid"]))


def _origin(job) -> pd.DataFrame:
    """cb6_model._origin line for line, with the setting chosen from `space`."""
    t, name, cols, restricted = job
    space = RESTRICTED if restricted else SPACE
    d, S, lab = N._G["d"], N._G["T"], N._G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(N.TEST_LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    te["p"], te["fallback"], te["cfg"] = np.nan, False, None
    shap = None
    if H.eligible(trb):
        cfg = select(tr, cols, space)
        m = LGBM2(cfg, cols).fit(tr)
        te["p"], te["cfg"] = m.predict(te), cfg["sid"]
        if m.m is not None:
            shap = V.shap_frame(m.m, te[cols])
    else:
        te["p"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    out = te[["t", "lead", "q", "p", "fallback", "cfg"]].assign(name=name).reset_index(drop=True)
    sh = (shap.reset_index(drop=True) if shap is not None else pd.DataFrame(0.0, index=out.index, columns=cols))
    return pd.concat([out, sh.add_prefix("shap_")], axis=1)


def fit():
    pre = check()
    chk = {"prereg_sha256": pre, "space": len(SPACE)}
    with Pool(8, initializer=CB._init) as pool:
        rep = pd.concat(pool.map(_origin, [(t, "C-B6E-replica", COLS, True) for t in V.ORIGINS]), ignore_index=True)
        st = pd.read_csv(OUT / "cb6e_fits.csv").set_index(["t", "lead"])["p"]
        r = rep.set_index(["t", "lead"])["p"]
        chk["C-B6E_replication_max_abs_diff"] = float((r - st.reindex(r.index)).abs().max())
        print(chk, flush=True)
        assert chk["C-B6E_replication_max_abs_diff"] < 1e-9, "C-B6E replication differs"
        F = pd.concat(pool.map(_origin, [(t, NAME, COLS, False) for t in V.ORIGINS]), ignore_index=True)
    (OUT / "cb6eopt_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    F.to_csv(OUT / "cb6eopt_fits.csv", index=False)
    print({"rows": len(F), "origins": int(F["t"].nunique())})


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
    B6E = pd.read_csv(OUT / "cb6e_fits.csv")
    F = pd.read_csv(OUT / "cb6eopt_fits.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]], L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      PP[["name", "t", "lead", "q", "p"]], B6[["name", "t", "lead", "q", "p"]],
                      B6E[["name", "t", "lead", "q", "p"]], F[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; attempt 27 on the same 62 quarters", "leads": {},
           "algorithm3": {}}
    fam = {}
    for k in PC.TEST_LEADS:
        W = R.frame(comp, k, lab_bl)
        Lk = {n: {"accuracy": PC._acc(W.dropna(subset=[n]), n)} for n in (REF, "C-B6E", NAME)}
        if k <= 2:
            g = W.dropna(subset=[REF, "C-B6E", NAME])
            for n in (REF, "C-B6E", NAME):
                Lk[n].update(PC._summ(g, n))
                th = [set(x) for x in np.array_split(np.array(sorted(g["q"].unique())), 3)]
                Lk[n]["thirds"] = [PC._acc(g[g["q"].isin(x)], n) for x in th]
            Lk["vs_C-B6"] = {**PC._paired(g, NAME, REF), "calls_differing": int(((g[NAME] >= .5) != (g[REF] >= .5)).sum())}
            Lk["vs_C-B6E"] = {**PC._paired(g, NAME, "C-B6E"), "calls_differing": int(((g[NAME] >= .5) != (g["C-B6E"] >= .5)).sum())}
            era = W[W["t"] >= V.NEWS_ERA]
            for b in ["PERSIST-P" if b == "PERSIST" else b for b in PC.COMPS]:
                fam[(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, NAME, b)
            s = F[(F["lead"] == k) & F["q"].isin(g["q"])]
            tot = s.filter(like="shap_").abs().sum(axis=1).replace(0, np.nan)
            Lk["shap_share_mean"] = {c: float((s[f"shap_{c}"].abs() / tot).mean()) for c in ("E1", "E2", "ST1", "ST2")}
            Lk["settings_chosen"] = {str(int(c)): int(n) for c, n in s["cfg"].dropna().value_counts().items()}
        res["leads"][str(k)] = Lk
    hp = R.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_14_persist_p"] = [{"lead": k, "comparator": b, **v, "p_holm_14": hp[(k, b)],
                                        "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for n in (REF, "C-B6E", NAME):
        mx = 0
        for k in PC.TEST_LEADS:
            if res["leads"][str(k)][n]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][n] = mx
    allc = F.drop_duplicates("t")["cfg"].dropna().astype(int)
    res["settings_share"] = {"mono_on": float(np.mean([SPACE[c]["mono"] for c in allc])),
                             "mcs_30": float(np.mean([SPACE[c]["mcs"] == 30 for c in allc])), "origins": int(len(allc))}
    last = F[(F["t"] == H.qi("2026-Q3")) & F["lead"].isin([1, 2])]
    lt = last.filter(like="shap_").abs().sum(axis=1).replace(0, np.nan)
    res["latest_issue"] = {"setting": SPACE[int(last["cfg"].iloc[0])] if last["cfg"].notna().any() else None,
                           "shap_share": {c: [float(x) for x in (last[f"shap_{c}"].abs() / lt)] for c in ("E1", "E2")}}
    L1 = res["leads"]["1"]
    rules_ok = all(not res["leads"][k][NAME]["failed"] for k in ("1", "2"))
    acc_ok = all(res["leads"][k][NAME]["metrics"]["accuracy"] >= .75 for k in ("1", "2"))
    res["decision"] = {"R1_R7_both_leads": bool(rules_ok), "accuracy_ge_0.75_both_leads": bool(acc_ok),
                       "serve_automatically": bool(rules_ok and acc_ok),
                       "improves_lead1_p_lt_0.05": bool(L1["vs_C-B6"]["diff"] < 0 and L1["vs_C-B6"]["p_one_sided"] < .05)}
    (OUT / "cb6eopt_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for n in (REF, "C-B6E", NAME):
            m = res["leads"][k][n]["metrics"]
            print(f"L{k} {n:9s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {res['leads'][k][n]['failed']} "
                  f"thirds {[round(x, 3) for x in res['leads'][k][n]['thirds']]}")
        v, w = res["leads"][k]["vs_C-B6"], res["leads"][k]["vs_C-B6E"]
        print(f"   vs C-B6 diff {v['diff']:+.4f} CI {v['ci95'][0]:+.4f}..{v['ci95'][1]:+.4f} p {v['p_one_sided']:.4f} calls {v['calls_differing']}; "
              f"vs C-B6E diff {w['diff']:+.4f} p {w['p_one_sided']:.4f}; SHAP {dict((a, round(b, 3)) for a, b in res['leads'][k]['shap_share_mean'].items())}")
    print("settings:", res["settings_share"], "latest:", res["latest_issue"])
    print("Holm family (PERSIST-P): significant", sum(f["significant"] for f in res["holm_family_14_persist_p"]), "of 14")
    print("Algorithm 3:", res["algorithm3"])
    print("Decision:", res["decision"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
