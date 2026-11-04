"""ALLBASE Phase C: the three pre-registered candidates (PHASE_B_PREREGISTRATION.md, hash checked).

    python phase_c.py features   # 4 reversal features, two independent implementations + leakage check -> ../out/reversal_features.csv
    python phase_c.py fit        # C-b reproduction + K3 walk-forward (leads 1-8); LOGIT regenerated from 1998-Q3 -> ../out/fits.csv
    python phase_c.py blend      # K1 (0.5/0.5) and K2 (walk-forward weight) + weight leakage check -> ../out/blends.csv
    python phase_c.py score      # metrics, R1-R7, Algorithm 3, 42-test Holm family, G1-G5, R7 analysis -> ../out/phase_c_results.json

Development evidence only (62 previously examined quarters). No 2027 label exists or is read.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import csv
import hashlib
import json
import math
from datetime import date
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parents[1]
PREREG = HERE / "PHASE_B_PREREGISTRATION.md"
OUT = HERE / "out"
sys.path.insert(0, str(EXP / "NEW_MODEL" / "NEWS_V2" / "runner"))
import run_news_v2 as N  # noqa: E402   (table with z_N1R, C-b columns, OPTION_1 origin procedure)
import align_cb as A  # noqa: E402      (paired Brier test, NLP-only comparators)

V, H, R = N.V, N.H, N.R
CB = N.MODELS["C-b"]
REV = ["z_dist", "run_side", "cross8", "rev_last"]
K3 = CB[:-1] + REV + CB[-1:]
SE1, LINE = 5.7 / 1.96, 11.3
TEST_LEADS = N.TEST_LEADS
COMPS = ["PERSIST", "PSA-only", "LOGIT", "NLP-only", "LGBM-GOV", "LGBM-NLP", "ALWAYS-HIGH"]
CANDS = ["K1", "K2", "K3"]
WGRID = [round(0.1 * i, 1) for i in range(11)]
WMIN_PAIRS = 20
FOLD_S = (H.qi("2010-Q1"), H.qi("2017-Q4"))
FOLD_E = (H.qi("2018-Q1"), H.qi("2026-Q3"))
SEED, REPS = 2036, 5


def check_prereg() -> str:
    b = PREREG.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "pre-registration changed after hashing"
    return h


def _chk() -> dict:
    p = OUT / "checks.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save_chk(c: dict):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "checks.json").write_text(json.dumps(c, indent=1, default=str), encoding="utf-8")


# ================================================================================================ features (design 2)
def reversal_a(d: H.Data, t: int) -> dict:
    """Implementation A: from hr_lib.known (quarter means of BL rounds published before O(t))."""
    kn = H.known(d, t, "BL")
    hs = [x[1] for x in kn]
    if not hs:
        return {c: np.nan for c in REV}
    O = H.issue(t)
    s = d.sws
    n = int(((s["area"] == "BL") & (s["q"] == kn[-1][0]) & (s["published"] < O)).sum())
    side = [h > LINE for h in hs]
    run = 1
    while run < len(side) and side[-run - 1] == side[-1]:
        run += 1
    last8 = side[-8:]
    return {"z_dist": (hs[-1] - LINE) / (SE1 / math.sqrt(n)),
            "run_side": float(run if side[-1] else -run),
            "cross8": float(sum(a != b for a, b in zip(last8, last8[1:]))) if len(last8) >= 4 else np.nan,
            "rev_last": float((hs[-1] - hs[-2]) * (hs[-2] - hs[-3]) < 0) if len(hs) >= 3 else np.nan}


def reversal_b(d: H.Data, t: int) -> dict:
    """Implementation B (independent check): pandas/numpy on the raw rounds, no hr_lib helper."""
    r = d.sws[(d.sws["area"] == "BL") & (d.sws["published"] < H.issue(t))]
    if r.empty:
        return {c: np.nan for c in REV}
    g = r.groupby("q")["H"].agg(["mean", "size"]).sort_index()
    h = g["mean"].to_numpy(float)
    above = (h > LINE).astype(int)
    flips = np.flatnonzero(np.diff(above) != 0)
    run = len(h) - (flips[-1] + 1) if len(flips) else len(h)
    w = above[-8:]
    dh = np.diff(h)
    return {"z_dist": float((h[-1] - LINE) * np.sqrt(g["size"].iloc[-1]) / SE1),
            "run_side": float(run * (1 if above[-1] else -1)),
            "cross8": float(np.abs(np.diff(w)).sum()) if len(w) >= 4 else np.nan,
            "rev_last": float(np.sign(dh[-1]) * np.sign(dh[-2]) < 0) if len(dh) >= 2 else np.nan}


def _same(a: dict, b: dict, tol: float = 1e-12) -> bool:
    return all((np.isnan(a[c]) and np.isnan(b[c])) or (not np.isnan(a[c]) and abs(a[c] - b[c]) <= tol) for c in REV)


def _feat_origin(t: int) -> tuple[int, dict, bool, bool]:
    d = _G["d"]
    a, b = reversal_a(d, t), reversal_b(d, t)
    stable = all(_same(reversal_a(H.perturb(d, t, SEED + r), t), a, 0.0) for r in range(REPS))
    return t, a, _same(a, b), stable


_G: dict = {}


def _finit():
    _G["d"] = H.load()


def features():
    pre = check_prereg()
    with Pool(8, initializer=_finit) as pool:
        res = pool.map(_feat_origin, V.ORIGINS)
    F = pd.DataFrame([{"t": t, **a} for t, a, _, _ in res])
    T = pd.read_csv(N.IV2_OUT / "table_pooled.csv", dtype={"area": str})
    hl = T[(T["area"] == "BL") & (T["lead"] == 1)][["t", "h_last"]].merge(F, on="t")
    sign_ok = bool((np.sign(hl["h_last"] - LINE).fillna(0) == np.sign(hl["z_dist"]).fillna(0)).all())
    chk = {"prereg_sha256": pre,
           "features_independent_implementations_equal": all(x[2] for x in res),
           "features_mismatch_origins": [H.qs(t) for t, _, s, _ in res if not s],
           "features_leakage_future_sws_randomized_unchanged": all(x[3] for x in res),
           "features_leakage_failed_origins": [H.qs(t) for t, _, _, s in res if not s], "reps": REPS,
           "z_dist_sign_matches_table_h_last": sign_ok,
           "non_missing": {c: int(F[c].notna().sum()) for c in REV}, "origins": len(F)}
    OUT.mkdir(parents=True, exist_ok=True)
    F.to_csv(OUT / "reversal_features.csv", index=False)
    c = _chk()
    c.update(chk)
    _save_chk(c)
    print(json.dumps(chk, indent=1))
    if not (chk["features_independent_implementations_equal"] and chk["features_leakage_future_sws_randomized_unchanged"]
            and chk["z_dist_sign_matches_table_h_last"]):
        raise SystemExit("reversal-feature pre-check failed: K3 is not fitted")


# ================================================================================================ fit (K3, C-b repro, LOGIT)
def _init():
    N._init()
    N._G["T"] = N._G["T"].merge(pd.read_csv(OUT / "reversal_features.csv"), on="t", how="left")


def fit():
    pre = check_prereg()
    c = _chk()
    assert c.get("features_independent_implementations_equal") and c.get("features_leakage_future_sws_randomized_unchanged")
    jobs = [(t, n, cc) for t in V.ORIGINS for n, cc in (("C-b_repro", CB), ("K3", K3))]
    with Pool(8, initializer=_init) as pool:
        parts = pool.map(_origin, jobs)
    F = pd.concat(parts, ignore_index=True)
    # LOGIT regenerated from 1998-Q3 (IMPROVE_V2 specification; labels known at O(t) only)
    d = H.load()
    lab = V.area_labels(d)
    T = pd.read_csv(N.IV2_OUT / "table_pooled.csv", dtype={"area": str})
    rows = []
    for t in V.ORIGINS:
        kb = V.known_labels(d, t, lab)
        kb = kb[kb["area"] == "BL"][["q", "y"]]
        clim = float(kb["y"].mean()) if len(kb) else 0.0
        rows.append(V.logit_lead(T, t, kb, H.T2_B, clim, H.FIRST_ORIGIN).assign(name="LOGIT_regen"))
    Lg = pd.concat(rows, ignore_index=True)[["name", "t", "lead", "q", "p", "fallback"]]
    F = pd.concat([F, Lg], ignore_index=True)
    F.to_csv(OUT / "fits.csv", index=False)
    old = pd.read_csv(N.OUT / "forecasts.csv")
    old = old[old["name"] == "C-b"][["t", "lead", "p"]]
    m = old.merge(F[F["name"] == "C-b_repro"][["t", "lead", "p"]], on=["t", "lead"], suffixes=("_old", "_new"))
    rep_cb = {"rows_stored": int(len(old)), "matched": int(len(m)), "max_abs_diff": float((m["p_old"] - m["p_new"]).abs().max())}
    iv = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    iv = iv[iv["name"] == "LOGIT"][["t", "lead", "p"]]
    m2 = iv.merge(Lg[["t", "lead", "p"]], on=["t", "lead"], suffixes=("_old", "_new"))
    rep_lg = {"rows_stored": int(len(iv)), "matched": int(len(m2)),
              "max_abs_diff": float((m2["p_old"] - m2["p_new"]).abs().max()),
              "first_origin_regenerated": H.qs(int(Lg["t"].min()))}
    c.update({"prereg_sha256": pre, "reproduction_Cb": rep_cb,
              "Cb_reproduced": rep_cb["matched"] == rep_cb["rows_stored"] and rep_cb["max_abs_diff"] <= 1e-12,
              "reproduction_LOGIT": rep_lg,
              "LOGIT_reproduced": rep_lg["matched"] == rep_lg["rows_stored"] and rep_lg["max_abs_diff"] <= 1e-12,
              "versions": R.versions()})
    _save_chk(c)
    print(json.dumps({k: c[k] for k in ("reproduction_Cb", "Cb_reproduced", "reproduction_LOGIT", "LOGIT_reproduced")}, indent=1))
    if not c["Cb_reproduced"]:
        raise SystemExit("C-b is not reproduced: candidates are not scored")


def _origin(job) -> pd.DataFrame:
    """NEWS_V2 _origin (OPTION_1 procedure) without SHAP; the given columns, test leads 1-8."""
    t, name, cols = job
    d, S, lab = N._G["d"], N._G["T"], N._G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(TEST_LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    te["p"], te["fallback"], te["cfg"] = np.nan, False, None
    if H.eligible(trb):
        cfg = H.lgbm_select(tr, cols, mono=False)
        m = H.LGBM(cfg, cols, False).fit(tr)
        te["p"], te["cfg"] = m.predict(te), cfg["id"]
    else:
        te["p"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    return te[["t", "lead", "q", "p", "fallback", "cfg"]].assign(name=name)


# ================================================================================================ blend (K1, K2)
def choose_w(P: pd.DataFrame, y: dict, known: set, t: int) -> tuple[float, int]:
    """Design 3: pairs from origins t' < t whose target label is known at O(t); grid Brier minimum, ties -> closest
    to 0.5 then lower w; w = 0.5 with fewer than 20 pairs. P: one lead, columns t, q, cb, lg."""
    g = P[(P["t"] < t) & P["q"].isin(known)].dropna(subset=["cb", "lg"])
    if len(g) < WMIN_PAIRS:
        return 0.5, int(len(g))
    yy = g["q"].map(y).to_numpy(float)
    sc = {w: round(float(np.mean((w * g["cb"].to_numpy() + (1 - w) * g["lg"].to_numpy() - yy) ** 2)), 12) for w in WGRID}
    return min(WGRID, key=lambda w: (sc[w], abs(w - 0.5), w)), int(len(g))


def blend():
    pre = check_prereg()
    c = _chk()
    assert c.get("Cb_reproduced")
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    y = dict(zip(lab_bl["q"].astype(int), lab_bl["y"].astype(int)))
    F = pd.read_csv(OUT / "fits.csv")
    cb = pd.read_csv(N.OUT / "forecasts.csv")
    cb = cb[cb["name"] == "C-b"][["t", "lead", "q", "p"]].rename(columns={"p": "cb"})
    if c.get("LOGIT_reproduced"):
        lg, src = F[F["name"] == "LOGIT_regen"], "regenerated 1998-Q3+ (reproduces stored rows)"
    else:
        lg = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
        lg, src = lg[lg["name"] == "LOGIT"], "stored 2009-Q3+ (fallback, design 3)"
    lg = lg[["t", "lead", "p"]].rename(columns={"p": "lg"})
    rng = np.random.default_rng(SEED)
    rows, leak_ok, leak_fail = [], True, []
    for k in (1, 2):
        P = cb[cb["lead"] == k].merge(lg[lg["lead"] == k], on=["t", "lead"], how="inner").sort_values("t")
        for t in P["t"]:
            known = H.complete_bl(d, t)
            w, n = choose_w(P, y, known, t)
            r = P[P["t"] == t].iloc[0]
            rows.append({"t": t, "lead": k, "q": int(r["q"]), "cb": r["cb"], "lg": r["lg"], "w": w, "n_pairs": n,
                         "K1": 0.5 * r["cb"] + 0.5 * r["lg"], "K2": w * r["cb"] + (1 - w) * r["lg"]})
            for _ in range(REPS):          # leakage: forecasts from origins >= t and labels unknown at O(t) randomized
                Q = P.copy()
                fut = Q["t"] >= t
                Q.loc[fut, ["cb", "lg"]] = rng.uniform(0, 1, (int(fut.sum()), 2))
                yq = {q: (v if q in known else int(rng.integers(0, 2))) for q, v in y.items()}
                if choose_w(Q, yq, known, t) != (w, n):
                    leak_ok = False
                    leak_fail.append(f"{H.qs(t)} L{k}")
    B = pd.DataFrame(rows)
    B.to_csv(OUT / "blends.csv", index=False)
    c.update({"prereg_sha256": pre, "K2_logit_source": src, "K2_weight_leakage_unchanged": leak_ok,
              "K2_weight_leakage_failed": leak_fail[:20],
              "K2_first_origin_with_20_pairs": {k: (H.qs(int(B[(B["lead"] == k) & (B["n_pairs"] >= WMIN_PAIRS)]["t"].min()))
                                                    if (B[(B["lead"] == k)]["n_pairs"] >= WMIN_PAIRS).any() else None)
                                                for k in (1, 2)}})
    _save_chk(c)
    print(json.dumps({k: c[k] for k in ("K2_logit_source", "K2_weight_leakage_unchanged", "K2_first_origin_with_20_pairs")},
                     indent=1))
    ev = B[(B["q"] >= H.EVAL_FIRST) & (B["q"] <= H.EVAL_LAST)]
    print("K2 weights in the evaluation window:", ev.groupby("lead")["w"].describe()[["min", "50%", "max"]].to_dict())
    if not leak_ok:
        raise SystemExit("K2 weight leakage check failed: K2 is not scored")


# ================================================================================================ score
def ece(p, y, bins=10):
    p, y = np.asarray(p, float), np.asarray(y, int)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).sum() for b in range(bins)
                     if (idx == b).any()) / len(p))


def _summ(g: pd.DataFrame, n: str) -> dict:
    r = H.evaluate(g, n)
    m = r["metrics"]
    rules = {k.split()[0]: {"pass": v["pass"], "value": v["value"]} for k, v in r["rules"].items()}
    tp, fp, fn, tn = (m.get(x) for x in ("TP", "FP", "FN", "TN"))
    return {"metrics": {**{x: m.get(x) for x in ("accuracy", "balanced", "precision", "recall", "f1", "auc", "brier",
                                                  "TP", "FP", "FN", "TN")},
                        "fpr": fp / (fp + tn) if fp is not None and (fp + tn) else None,
                        "fnr": fn / (fn + tp) if fn is not None and (fn + tp) else None,
                        "ece_10": ece(g[n], g["y"])},
            "rules": rules, "failed": [x for x, v in rules.items() if not v["pass"]]}


def _paired(g: pd.DataFrame, a: str, b: str) -> dict:
    g = g[g[a].notna() & g[b].notna()]
    dv = ((g[a] - g["y"]) ** 2 - (g[b] - g["y"]) ** 2).to_numpy(float)
    bs = H.boot_mean(g["q"].to_numpy(), dv, H.rp())
    ba, bb = float(((g[a] - g["y"]) ** 2).mean()), float(((g[b] - g["y"]) ** 2).mean())
    mu, sd, n = float(dv.mean()), float(dv.std(ddof=1)), len(dv)
    need = (lambda z: None if mu >= 0 else int(np.ceil((z * sd / -mu) ** 2)))  # noqa: E731
    return {"n_quarters": int(g["q"].nunique()), "brier_candidate": ba, "brier_comparator": bb, "diff": mu,
            "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "brier_skill": 1 - ba / bb if bb else None, "p_one_sided": float(np.mean(bs >= 0)),
            "n_needed_raw_0.05": need(norm.ppf(.95)), "n_needed_holm_strictest_0.05/42": need(norm.ppf(1 - .05 / 42))}


def _acc(x: pd.DataFrame, n: str) -> float:
    return float(((x[n] >= .5).astype(int) == x["y"]).mean()) if len(x) else float("nan")


def score():
    pre = check_prereg()
    c = _chk()
    assert c.get("Cb_reproduced") and c.get("K2_weight_leakage_unchanged")
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    CBF = pd.read_csv(N.OUT / "forecasts.csv")
    F = pd.read_csv(OUT / "fits.csv")
    B = pd.read_csv(OUT / "blends.csv")
    T = pd.read_csv(N.IV2_OUT / "table_pooled.csv", dtype={"area": str})
    hl = T[T["area"] == "BL"][["t", "lead", "h_last"]]
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      CBF[CBF["name"] == "C-b"][["name", "t", "lead", "q", "p"]],
                      F[F["name"] == "K3"][["name", "t", "lead", "q", "p"]]]
                     + [B[["t", "lead", "q", n]].rename(columns={n: "p"}).assign(name=n) for n in ("K1", "K2")],
                     ignore_index=True)
    models = ["C-b"] + CANDS
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE: 62 previously examined quarters; not independent validation",
           "checks": c, "leads": {}, "algorithm3": {}, "algorithm4": "not testable: no 2027 label exists (first sealed "
           "2027 quarters are reserved and were not read)"}
    fam = {}
    for k in TEST_LEADS:
        W = R.frame(comp, k, lab_bl).merge(hl[hl["lead"] == k][["t", "h_last"]], on="t", how="left")
        Lk = {}
        for n in models:
            if n not in W or W[n].isna().all():
                continue
            g = W.dropna(subset=[n])
            Lk[n] = {"accuracy": _acc(g, n), "n": int(len(g))}
        if k <= 2:
            g = W.dropna(subset=models)
            qsorted = sorted(g["q"].unique())
            thirds = [set(x) for x in np.array_split(np.array(qsorted), 3)]
            rev = (g["y"] != (g["h_last"] > LINE).astype(int))
            Lk["n_quarters"] = int(g["q"].nunique())
            Lk["reversal_events"] = int(rev.sum())
            for n in models + COMPS:
                if n not in g:
                    continue
                gg = g.dropna(subset=[n]) if n not in A.NLP_ONLY else g[g["t"] >= V.NEWS_ERA].dropna(subset=[n])
                x = Lk.setdefault(n, {})
                if n in models:
                    x.update(_summ(gg, n))
                    x["fold_S"] = {"brier": float(((gg[n] - gg["y"]) ** 2)[gg["q"].between(*FOLD_S)].mean()),
                                   "accuracy": _acc(gg[gg["q"].between(*FOLD_S)], n), "n": int(gg["q"].between(*FOLD_S).sum())}
                    x["fold_E"] = {"brier": float(((gg[n] - gg["y"]) ** 2)[gg["q"].between(*FOLD_E)].mean()),
                                   "accuracy": _acc(gg[gg["q"].between(*FOLD_E)], n), "n": int(gg["q"].between(*FOLD_E).sum())}
                rv = rev.loc[gg.index]
                x["reversal"] = {"all": {"reversal_recall": _acc(gg[rv], n), "n_reversal": int(rv.sum()),
                                         "non_reversal_accuracy": _acc(gg[~rv], n)}}
                x["by_third"] = {}
                for i, th in enumerate(thirds):
                    m = gg["q"].isin(th)
                    key = f"{H.qs(min(th))}..{H.qs(max(th))}"
                    x["by_third"][key] = {"accuracy": _acc(gg[m], n), "n": int(m.sum()),
                                          "reversal_recall": _acc(gg[m & rv], n), "n_reversal": int((m & rv).sum()),
                                          "non_reversal_accuracy": _acc(gg[m & ~rv], n)}
            for n in CANDS:
                Lk[n]["vs_C-b"] = {**_paired(g, n, "C-b"),
                                   "calls_differing": int(((g[n] >= .5) != (g["C-b"] >= .5)).sum())}
                era = W[W["t"] >= V.NEWS_ERA]
                for cmp_ in COMPS:
                    fam[(n, k, cmp_)] = _paired(era if cmp_ in A.NLP_ONLY else W, n, cmp_)
            Lk["C-b_vs_comparators_unadjusted"] = {cmp_: _paired(W[W["t"] >= V.NEWS_ERA] if cmp_ in A.NLP_ONLY else W,
                                                                 "C-b", cmp_) for cmp_ in COMPS}
        res["leads"][str(k)] = Lk
    hp = R.holm({key: v["p_one_sided"] for key, v in fam.items()})
    family = []
    for (n, k, cmp_), v in fam.items():
        sig = bool(v["diff"] < 0 and hp[(n, k, cmp_)] < .05)
        family.append({"candidate": n, "lead": k, "comparator": cmp_, **v, "p_holm_42": hp[(n, k, cmp_)],
                       "conclusion": "significantly better" if sig else "not significantly different"
                       if v["diff"] < 0 else "not better (candidate Brier not lower)"})
    res["holm_family_42"] = family
    for n in models:
        accs = {k: res["leads"][str(k)].get(n, {}).get("accuracy") for k in TEST_LEADS}
        mx = 0
        for k in TEST_LEADS:
            if accs[k] is not None and accs[k] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][n] = {"mrlt": mx, "accuracy_by_lead": accs,
                                **({"note": "LOGIT exists at Leads 1-2 only, so the MRLT of a blend is capped at 2"}
                                   if n in ("K1", "K2") else {})}
    # gates (PREREGISTRATION 4)
    gates = {}
    for n in CANDS:
        Ls = {k: res["leads"][str(k)] for k in (1, 2)}
        g1 = all(f["conclusion"] == "significantly better" for f in family if f["candidate"] == n)
        g2 = all(Ls[k][n]["vs_C-b"]["diff"] < 0 and Ls[k][n]["vs_C-b"]["p_one_sided"] < .10
                 and Ls[k][n]["metrics"]["accuracy"] >= Ls[k]["C-b"]["metrics"]["accuracy"] for k in (1, 2))
        g3 = all(not Ls[k][n]["failed"] for k in (1, 2))
        g4 = res["algorithm3"][n]["mrlt"] >= 2
        g5 = []
        for k in (1, 2):
            th = Ls[k][n]["by_third"]
            g5.append(all(v["accuracy"] >= .6 for v in th.values())
                      and Ls[k][n]["rules"]["R7"]["pass"]
                      and Ls[k][n]["metrics"]["accuracy"] >= Ls[k]["C-b"]["metrics"]["accuracy"])
        gates[n] = {"G1_all_baselines": g1, "G2_improves_Cb": g2, "G3_R1_R7": g3, "G4_algorithm3_mrlt_ge_2": g4,
                    "G5_R7_targeted": all(g5), "adoption_conditions_G2_and_G4": g2 and g4}
    res["gates"] = gates
    # selection (design 4): fold S, mean Brier over Leads 1-2, no worse than C-b at either lead
    sb = {n: [res["leads"][str(k)][n]["fold_S"]["brier"] for k in (1, 2)] for n in models}
    ok = [n for n in CANDS if all(sb[n][i] <= sb["C-b"][i] for i in (0, 1)) and np.mean(sb[n]) < np.mean(sb["C-b"])]
    chosen = min(ok, key=lambda n: (round(float(np.mean(sb[n])), 12), CANDS.index(n))) if ok else None
    res["selection_fold_S"] = {"brier_L1_L2": sb, "eligible": ok, "chosen": chosen,
                               "rule": "lowest mean fold-S Brier over Leads 1-2, no worse than C-b at either lead"}
    res["decision"] = {"chosen_on_fold_S": chosen,
                       "adoptable_by_prereg": bool(chosen and gates[chosen]["adoption_conditions_G2_and_G4"]),
                       "all_baseline_claim": any(v["G1_all_baselines"] for v in gates.values()),
                       "note": "Promotion to the main model is not authorized by Phase C in any case."}
    (OUT / "phase_c_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    _registry(res, c)
    _print(res)


def _registry(res: dict, c: dict):
    p = HERE / "REGISTRY.csv"
    cols = ["experiment_id", "date", "branch_commit", "target", "lead", "dataset_version", "feature_groups", "model",
            "validation", "seed", "accuracy", "auc", "brier", "comparisons_sig_of_14", "R1_R7_failed", "gates",
            "accepted", "status", "limitations"]
    prior = [("E99", "Eq. 3 label, 12 features, Optuna", "Lead 1 accuracy 0.30; MRLT 0"),
             ("P0H4", "hunger + price hybrid, province", "Lead 1 R1-R7 pass; Lead 2 fails"),
             ("HISTORY_RETRAIN", "T1/T2, feature options, GRU, LOGIT", "REF chosen"),
             ("IMPROVE_V2", "REF, I1, I2, I3, ALL +/- news", "REF best; news no gain"),
             ("IMPROVE_V2_LEADS/OPTION_1", "leads 1-15; REF+news", "MRLT 2"),
             ("RELIABLE_L12", "per-origin threshold", "0 calls changed"),
             ("RELIABLE_NEWINFO", "REF/pi_H4L blend; CHIRPS", "blend worse; rainfall 0 calls changed"),
             ("OLD_NEWS", "REF + GDELT 2015-2026", "fails R5, R7"),
             ("NEWS_V2", "C-a, C-b (FSSI anomaly)", "C-b adopted; fails R7 only; acc 0.790 L1/L2"),
             ("NOISE_W", "C-b + measurement-error weights", "0 calls changed; Brier -0.007 n.s.")]
    rows = [{"experiment_id": e, "model": m, "status": "prior", "limitations": r} for e, m, r in prior]
    import subprocess
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=EXP).stdout.strip()
    for n in CANDS:
        for k in (1, 2):
            x = res["leads"][str(k)][n]
            sig = sum(f["conclusion"] == "significantly better" for f in res["holm_family_42"]
                      if f["candidate"] == n and f["lead"] == k)
            rows.append({"experiment_id": f"ALLBASE-PC-{n}", "date": date.today().isoformat(),
                         "branch_commit": f"aiPHeed/system-fixes@{head} + uncommitted ALLBASE (prereg {res['prereg_sha256'][:8]})",
                         "target": "T1 BL hunger > 11.3", "lead": k,
                         "dataset_version": "table_pooled " + H.sha(N.IV2_OUT / "table_pooled.csv")[:12],
                         "feature_groups": {"K1": "C-b + LOGIT (F_b T2)", "K2": "C-b + LOGIT (F_b T2)",
                                            "K3": "C-b 21 + 4 reversal"}[n],
                         "model": {"K1": "0.5 C-b + 0.5 LOGIT", "K2": "walk-forward w grid 0..1, >=20 pairs",
                                   "K3": "LightGBM, hr_lib grid, C-b procedure"}[n],
                         "validation": "walk-forward 1998-Q3+; fold S 2010-2017 selection; 62-quarter window",
                         "seed": "LGBM 2027; bootstrap 2036 B 5000", "accuracy": round(x["metrics"]["accuracy"], 4),
                         "auc": x["metrics"]["auc"] and round(x["metrics"]["auc"], 4), "brier": round(x["metrics"]["brier"], 4),
                         "comparisons_sig_of_14": f"{sig} of 7 at this lead", "R1_R7_failed": " ".join(x["failed"]) or "none",
                         "gates": " ".join(f"{g.split('_')[0]}={'P' if v else 'F'}" for g, v in res["gates"][n].items()
                                           if g.startswith("G")),
                         "accepted": res["gates"][n]["adoption_conditions_G2_and_G4"], "status": "Phase C",
                         "limitations": "development evidence; quarters previously examined"})
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c_: r.get(c_, "") for c_ in cols})


def _print(res: dict):
    for k in ("1", "2"):
        Lk = res["leads"][k]
        print(f"--- Lead {k} ({Lk['n_quarters']} quarters, {Lk['reversal_events']} reversal events)")
        for n in ["C-b"] + CANDS:
            m = Lk[n]["metrics"]
            th = " / ".join(f"{v['accuracy']:.3f}" for v in Lk[n]["by_third"].values())
            print(f"{n:4s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} ECE {m['ece_10']:.3f} "
                  f"TP/FP/FN/TN {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} failed {Lk[n]['failed']} | thirds {th} | "
                  f"rev recall {Lk[n]['reversal']['all']['reversal_recall']:.3f} non-rev {Lk[n]['reversal']['all']['non_reversal_accuracy']:.3f}"
                  + (f" | vs C-b {Lk[n]['vs_C-b']['diff']:+.4f} p {Lk[n]['vs_C-b']['p_one_sided']:.3f} "
                     f"calls changed {Lk[n]['vs_C-b']['calls_differing']}" if n != "C-b" else ""))
    print("--- 42-test Holm family")
    for f in res["holm_family_42"]:
        print(f"{f['candidate']} L{f['lead']} vs {f['comparator']:11s} {f['brier_candidate']:.4f} vs {f['brier_comparator']:.4f} "
              f"diff {f['diff']:+.4f} n {f['n_quarters']} p {f['p_one_sided']:.4f} Holm {f['p_holm_42']:.4f} {f['conclusion']}")
    print("Algorithm 3:", {n: v["mrlt"] for n, v in res["algorithm3"].items()})
    print("Gates:", json.dumps(res["gates"], indent=1))
    print("Selection:", json.dumps(res["selection_fold_S"]))
    print("DECISION:", json.dumps(res["decision"]))


if __name__ == "__main__":
    {"features": features, "fit": fit, "blend": blend, "score": score}[sys.argv[1]]()
