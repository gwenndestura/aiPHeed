"""IMPROVE_V2 runner (PLAN.md section 11).

    python run_iv2.py build   # pooled table; PLAN 9 checks 2, 3, 5 -> out/checks.json (stops on any failure)
    python run_iv2.py fit     # 10 arms + baselines walk-forward; PLAN 9 checks 1 and 4 -> out/forecasts.csv
    python run_iv2.py score   # every arm and baseline, both leads -> out/results.json, out/summary.md
    python run_iv2.py seal    # PLAN 10 -> sealed_prospective_IMPROVE_V2.csv, SEAL_LEDGER.md, out/lgu_rankings.csv
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import platform
from multiprocessing import Pool

import numpy as np
import pandas as pd

import iv2_lib as V

H = V.H
OUT = V.OUT
HR = V.EXP / "HISTORY_RETRAIN"
LEADS = (1, 2)
VERDICT = (H.EVAL_FIRST, H.EVAL_LAST)
SUB = {"dev_2010_2022": (H.EVAL_FIRST, H.qi("2022-Q4")), "block_2023_2026": (H.qi("2023-Q1"), H.EVAL_LAST)}
SENS = {"S1_no_phone_2020": [H.qi("2020-Q2"), H.qi("2020-Q3")],
        "S2_no_adults_2025Q2plus": list(range(H.qi("2025-Q2"), H.EVAL_LAST + 1))}
SENS["S3_both"] = SENS["S1_no_phone_2020"] + SENS["S2_no_adults_2025Q2plus"]
ARM_NAMES = [V.arm_name(a, n) for n in (False, True) for a in V.ARMS]          # tie order of PLAN 4
BASELINES = ["PERSIST", "LOGIT", "PSA-only", "NLP-only"]
OBJ4 = ["PERSIST", "PSA-only", "NLP-only", "LOGIT", "ALWAYS-HIGH"]


# ================================================================================================ hashes
def plan_sha() -> str:
    b = (V.IV / "PLAN.md").read_bytes()
    i = b.rfind(b"\nPLAN-SHA256:") + 1
    h = hashlib.sha256(b[:i]).hexdigest()
    if h != b[i:].split(b":", 1)[1].strip().decode():
        raise SystemExit("PLAN.md changed after it was hashed: refusing to run")
    return h


def data_hashes() -> dict:
    """HISTORY_RETRAIN data files checked against the SHA-256 recorded in its fetch log (PLAN 1)."""
    log = json.loads((HR / "data" / "fetch_log.json").read_text())["files"]
    out = {}
    for f in sorted((HR / "data").glob("*.csv")):
        rec = log.get(f.name, {}).get("sha256")
        got = hashlib.sha256(f.read_bytes()).hexdigest()
        out[f.name] = {"sha256": got, "recorded": rec, "equal": rec == got}
    if not all(v["equal"] for v in out.values()):
        raise SystemExit(f"HISTORY_RETRAIN data changed: {out}")
    return out


# ================================================================================================ build
def _same(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    a, b = a.reset_index(drop=True), b.reset_index(drop=True)
    if list(a.columns) != list(b.columns) or len(a) != len(b):
        return False
    for c in a.columns:
        x, y = a[c], b[c]
        if x.dtype.kind in "fc" or y.dtype.kind in "fc":
            xv, yv = x.to_numpy(float), y.to_numpy(float)
            if not np.array_equal(np.isnan(xv), np.isnan(yv)) or not np.allclose(xv[~np.isnan(xv)], yv[~np.isnan(yv)],
                                                                                rtol=0, atol=1e-12):
                return False
        elif not x.astype(str).equals(y.astype(str)):
            return False
    return True


def check_labels(d: H.Data, T: pd.DataFrame) -> dict:
    """PLAN 9.2: BL rows equal HISTORY_RETRAIN's T2 table; BL labels equal t2_labels; every area's label is its own
    SWS mean (recomputed from the raw file); pi_area(BL) equals pi_h4l."""
    hr = pd.read_csv(HR / "out" / "table_T2.csv")
    bl = T[T["area"] == "BL"][hr.columns].reset_index(drop=True)
    hr = hr[hr["t"] <= V.LAST_ORIGIN].reset_index(drop=True)
    lab = V.area_labels(d)
    t2 = H.t2_labels(d)
    b = lab[lab["area"] == "BL"][["q", "H", "y"]].reset_index(drop=True)
    raw = pd.read_csv(H.LONG / "sws_area_rounds_full.csv")
    raw = raw[~raw["commissioned"].astype(bool)]
    own = True
    for a, col in H.AREAS.items():
        m = raw.dropna(subset=[col]).groupby(raw["quarter"].map(H.qi))[col].mean()
        x = lab[lab["area"] == a].set_index("q")["H"]
        own &= bool(np.allclose(m.loc[x.index].to_numpy(float), x.to_numpy(float), atol=1e-12)) and len(m) == len(x)
    pi_ok = bool(np.allclose(T[T["area"] == "BL"]["pi_H4L"].to_numpy(float),
                             [V.pi_area(d, int(t), int(k), "BL")["pi"] for t, k in
                              T[T["area"] == "BL"][["t", "lead"]].to_numpy()], atol=1e-12, equal_nan=True))
    return {"bl_rows_equal_HR_table_T2": _same(bl, hr),
            "bl_labels_equal_t2_labels": _same(b, t2[["q", "H", "y"]].reset_index(drop=True)),
            "every_area_label_is_own_sws_mean": own, "pi_area_BL_equals_pi_h4l": pi_ok,
            "areas_rows": T.groupby("area").size().to_dict()}


def _perturbed_news(t: int, seed: int):
    P = V._pipeline()
    rng = np.random.default_rng(seed)
    O = P.origin(t)
    sc = dict(V.intensities())
    late = [a["article_key"] for a in P.admitted() if P._ph(a) >= O and a["article_key"] in sc]
    for k in late:
        sc[k] = float(rng.uniform(-1, 1))
    tab = V.e112_shares().copy()
    lm = (tab.index > t) | (tab["last_published"] >= pd.Timestamp(H.issue(t)))
    tab.loc[lm, V.SHARES] = rng.uniform(0, 1, (int(lm.sum()), len(V.SHARES)))
    return sc, tab, len(late), int(lm.sum())


def leakage(d: H.Data) -> dict:
    """PLAN 9.3: rows and training labels of all four areas at origin t unchanged when everything published >= O(t)
    (SWS of all areas, CPI, production, typhoons, ONI, Pink Sheet, LFS, GDELT news, FSSI items, E112 shares) is
    randomized."""
    lab = V.area_labels(d)
    out = {}
    for s in ("2005-Q2", "2015-Q3", "2020-Q2", "2021-Q3", "2023-Q4", "2026-Q2"):
        t = H.qi(s)
        e = H.perturb(d, t, seed=t)
        sc, tab, n_items, n_q = _perturbed_news(t, seed=t)
        le = V.area_labels(e)
        out[s] = {"rows_all_areas": _same(pd.DataFrame(V.rows_origin(d, t)), pd.DataFrame(V.rows_origin(e, t, sc, tab))),
                  "labels_all_areas": _same(V.known_labels(d, t, lab), V.known_labels(e, t, le)),
                  "persist": H.persist_t2(d, t) == H.persist_t2(e, t),
                  "perturbed_something": (not _same(lab, le)) and n_q > 0,
                  "late_fssi_items_randomized": n_items}
    return out


def build():
    OUT.mkdir(exist_ok=True)
    hs = {"plan": plan_sha(), "hr_data": data_hashes()}
    d = H.load()
    V.table(d, V.ORIGINS).to_csv(OUT / "table_pooled.csv", index=False)
    T = _table()
    lab = V.area_labels(d)
    checks = {"hashes": hs, "labels_I1": check_labels(d, T), "leakage": leakage(d)}
    ev = T[(T["area"] == "BL") & T["t"].isin(H.ORIGINS_EVAL)]
    checks["eval_sws_before_issue"] = bool((ev["sws_newest_published"] < ev["t"].map(H.issue)).all())
    bl = lab[lab["area"] == "BL"]
    checks["counts"] = {f"L{k}": int(bl[(bl["q"] >= VERDICT[0]) & (bl["q"] <= VERDICT[1])]["q"].nunique())
                        for k in LEADS}
    checks["news_first_origin"] = {c: H.qs(int(T[T[c].notna()]["t"].min())) for c in V.NEWS}
    lab.to_csv(OUT / "labels_areas.csv", index=False)
    (OUT / "checks.json").write_text(json.dumps(checks, indent=1, default=str))
    ok = (all(v for k, v in checks["labels_I1"].items() if k != "areas_rows")
          and all(all(bool(x) for k, x in v.items()) for v in checks["leakage"].values())
          and checks["eval_sws_before_issue"] and all(v >= 40 for v in checks["counts"].values()))
    print(json.dumps({k: v for k, v in checks.items() if k != "hashes"}, indent=1, default=str))
    if not ok:
        raise SystemExit("PLAN section 9 check failed: nothing is fitted or scored")
    print("PLAN 9 checks 2, 3, 5 passed")


# ================================================================================================ fit
def _table():
    T = pd.read_csv(OUT / "table_pooled.csv", dtype={"area": str})
    return T


def _run_base(a):
    """One base fit (REF, I1, I2 or I1+I2, with or without news) walk-forward over every origin 1998-Q3..2026-Q3."""
    name, pooled, regression, news = a
    d = H.load()
    T = _table()
    lab = V.area_labels(d)
    rows = []
    for t in V.ORIGINS:
        kb = V.known_labels(d, t, lab)
        kb = kb[kb["area"] == "BL"]
        clim = float(kb["y"].mean()) if len(kb) else 0.0
        f = V.fit_base(T, t, lab, pooled, regression, news, clim, d)
        # PLAN 9.4: training rows precede the origin (asserted on the frame fit_base used)
        rows.append(f.assign(base=name, news=news))
    F = pd.concat(rows, ignore_index=True)
    lab_bl = lab[lab["area"] == "BL"]
    if regression:
        F = V.sigma_pass(F, d, lab_bl)
    return name, news, F


def check_training(d: H.Data, T: pd.DataFrame) -> dict:
    """PLAN 9.4 at six origins: the training rows fit_base uses have t' < t, q' <= t-1 and a label published before
    O(t) for their own area."""
    lab = V.area_labels(d)
    out = {}
    for s in ("2005-Q2", "2012-Q1", "2018-Q4", "2021-Q3", "2024-Q2", "2026-Q3"):
        t = H.qi(s)
        tr = T[(T["t"] < t) & (T["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y"]], on=["area", "q"])
        pub = d.sws.groupby(["area", "q"])["published"].max()
        latest = max(pub[(a, q)] for a, q in tr[["area", "q"]].drop_duplicates().itertuples(index=False))
        out[s] = bool((tr["t"] < t).all() and (tr["q"] <= t - 1).all() and latest < H.issue(t))
    return out


def fit():
    hs = plan_sha()
    d = H.load()
    T = _table()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    jobs = [(b, p, r, n) for n in (False, True) for b, (p, r) in V.BASES.items()]
    with Pool(8) as pool:
        res = pool.map(_run_base, jobs)
    base = {(b, n): F for b, n, F in res}
    # PLAN 3: I3 = Platt on REF; ALL = Platt on I1+I2 (pass over each arm's own earlier forecasts)
    arms = []
    for n in (False, True):
        for arm in V.ARMS:
            F = base[(V.BASE_OF[arm], n)].copy()
            if V.ARMS[arm][2]:
                F = V.platt_pass(F, d, lab_bl)
                F["p"] = F["p_cal"]
            else:
                F["p"] = F["p_raw"]
            arms.append(F.assign(name=V.arm_name(arm, n)))
    A = pd.concat(arms, ignore_index=True)
    # baselines (Objective 4 and R1-R7), origins of the evaluation window and the seal origin
    rows = []
    for t in H.ORIGINS_EVAL + [V.LAST_ORIGIN]:
        kb = V.known_labels(d, t, lab)
        kb = kb[kb["area"] == "BL"][["q", "y"]]
        clim = float(kb["y"].mean()) if len(kb) else 0.0
        te = T[(T["t"] == t) & T["lead"].isin(LEADS) & (T["area"] == "BL")]
        ps = H.persist_t2(d, t)
        rows.append(te.assign(name="PERSIST", p=ps if not np.isnan(ps) else clim, fallback=False))
        rows.append(te.assign(name="CLIM", p=clim, fallback=False))
        for nm, cc, m0 in (("LOGIT", H.T2_B, H.FIRST_ORIGIN), ("PSA-only", V.PSA, H.FIRST_ORIGIN),
                           ("NLP-only", V.NEWS, V.NEWS_ERA)):
            if t < m0:
                continue
            rows.append(V.logit_lead(T, t, kb, cc, clim, m0).assign(name=nm))
    B = pd.concat(rows, ignore_index=True)
    keep = ["name", "t", "lead", "q", "p", "p_raw", "p_cal", "H_hat", "sigma_used", "sigma_fallback", "n_err",
            "platt_skipped", "n_pairs", "fallback", "cfg", "n_train", "h_last", "sws_newest_published"]
    shap_cols = [c for c in A.columns if c.startswith("shap_")]
    F = pd.concat([A, B], ignore_index=True)
    F[[c for c in keep if c in F.columns]].to_csv(OUT / "forecasts.csv", index=False)
    A[["name", "t", "lead", "q", "fallback"] + shap_cols].to_csv(OUT / "shap_rows.csv", index=False)
    # PLAN 9.1: REF, LOGIT and PERSIST equal HISTORY_RETRAIN's stored forecasts
    hr = pd.read_csv(HR / "out" / "forecasts_classic.csv", dtype={"province_code": str})
    hr = hr[(hr["target"] == "T2")]
    fid = {}
    for mine, (model, opt) in (("REF", ("LGBM", "b")), ("LOGIT", ("LOGIT", "b")), ("PERSIST", ("PERSIST", "-")),
                               ("CLIM", ("CLIM", "-"))):
        a = F[(F["name"] == mine) & F["t"].isin(H.ORIGINS_EVAL)][["t", "lead", "p"]]
        b = hr[(hr["model"] == model) & (hr["option"] == opt)][["t", "lead", "p"]]
        m = a.merge(b, on=["t", "lead"], how="outer", suffixes=("", "_hr"))
        fid[mine] = {"n": int(len(m)), "equal": bool(m["p"].notna().all() and m["p_hr"].notna().all()
                                                       and np.allclose(m["p"], m["p_hr"], rtol=0, atol=1e-12)),
                     "max_abs_diff": float((m["p"] - m["p_hr"]).abs().max())}
    checks = json.loads((OUT / "checks.json").read_text())
    checks["fidelity_REF"] = fid
    checks["training_rows"] = check_training(d, T)
    checks["plan_at_fit"] = hs
    (OUT / "checks.json").write_text(json.dumps(checks, indent=1, default=str))
    print(json.dumps(fid, indent=1), json.dumps(checks["training_rows"]))
    if not (all(v["equal"] for v in fid.values()) and all(checks["training_rows"].values())):
        raise SystemExit("PLAN 9.1 or 9.4 failed: nothing is scored")
    print("PLAN 9 checks 1 and 4 passed; forecasts written", len(F))


# ================================================================================================ score
def frame(F: pd.DataFrame, lead: int, lab_bl: pd.DataFrame) -> pd.DataFrame:
    f = F[(F["lead"] == lead) & (F["t"] <= V.LAST_ORIGIN - 1)]
    W = f.pivot_table(index=["t", "q"], columns="name", values="p", aggfunc="first").reset_index()
    W = W.merge(lab_bl[["q", "y"]], on="q", how="inner")
    W["ALWAYS-HIGH"], W["ALWAYS-LOW"] = 1.0, 0.0
    W["ALWAYS-HIGH_p"], W["ALWAYS-LOW_p"] = 1.0, 0.0
    W["PERSIST-SI_p"], W["CLIM_p"] = W["PERSIST"], W["CLIM"]
    return W[(W["q"] >= VERDICT[0]) & (W["q"] <= VERDICT[1])].reset_index(drop=True)


def _eval(a):
    g, n, light = a
    g = g[g[n].notna()]
    if not len(g):
        return n, None
    r = H.evaluate(g, n)
    R = H.rp()
    if not light:
        for ref in ("REF", "PERSIST"):
            dv = ((g[n] - g["y"]) ** 2 - (g[ref] - g["y"]) ** 2).to_numpy(float)
            r["brierVs"][ref] = {"brierDiff": float(dv.mean()),
                                 "p_one_sided": float(np.mean(H.boot_mean(g["q"].to_numpy(), dv, R) >= 0))}
    else:
        r = {"metrics": r["metrics"], "allR1R7": r["allR1R7"],
             "fails": [k.split()[0] for k, v in r["rules"].items() if not v["pass"]]}
    r["n_quarters_scored"] = int(g["q"].nunique())
    r["period_scored"] = f"{H.qs(g['q'].min())}..{H.qs(g['q'].max())}"
    return n, r


def win(g: pd.DataFrame, names: list[str], light: bool) -> dict:
    with Pool(8) as pool:
        res = dict(pool.map(_eval, [(g, n, light) for n in names]))
    return {"n_quarters": int(g["q"].nunique()), "high_share": float(g["y"].mean()),
            "period": f"{H.qs(g['q'].min())}..{H.qs(g['q'].max())}", "models": res}


def paired(g: pd.DataFrame, a: str, b: str) -> dict:
    """Brier(a) - Brier(b) on the rows both have; one-sided cluster-bootstrap p that a is not lower."""
    g = g[g[a].notna() & g[b].notna()]
    dv = ((g[a] - g["y"]) ** 2 - (g[b] - g["y"]) ** 2).to_numpy(float)
    return {"n_quarters": int(g["q"].nunique()), "brier_a": float(((g[a] - g["y"]) ** 2).mean()),
            "brier_b": float(((g[b] - g["y"]) ** 2).mean()), "diff": float(dv.mean()),
            "p_one_sided": float(np.mean(H.boot_mean(g["q"].to_numpy(), dv, H.rp()) >= 0))}


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda x: x[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def score():
    hs = plan_sha()
    checks = json.loads((OUT / "checks.json").read_text())
    assert all(v["equal"] for v in checks["fidelity_REF"].values()) and all(checks["training_rows"].values())
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    F = pd.read_csv(OUT / "forecasts.csv")
    S = pd.read_csv(OUT / "shap_rows.csv")
    names = ARM_NAMES + BASELINES + ["ALWAYS-HIGH", "ALWAYS-LOW"]
    res = {"plan": hs, "versions": versions(), "leads": {}}
    for k in LEADS:
        W = frame(F, k, lab_bl)
        assert W["q"].nunique() == len(W) >= 40
        L = {"verdict": win(W, names, False)}
        for sn, (a, b) in SUB.items():
            L[sn] = win(W[(W["q"] >= a) & (W["q"] <= b)], names, True)
        for sn, drop in SENS.items():
            L[sn] = win(W[~W["q"].isin(drop)], names, True)
        era = W[W["t"] >= V.NEWS_ERA]
        L["news_era"] = win(era, names, True)
        # selection (PLAN 4)
        passing = [n for n in ARM_NAMES if L["verdict"]["models"][n]["allR1R7"]]
        sel = min(passing, key=lambda n: (round(L["verdict"]["models"][n]["metrics"]["brier"], 12),
                                          ARM_NAMES.index(n))) if passing else "REF"
        L["selection"] = {"passing": passing, "carried_forward": sel,
                          "rule": "lowest Brier among arms passing R1-R7, else REF"}
        # Objective 4: the proposed model vs five comparators, Holm across the five
        o4 = {c: paired(era if c == "NLP-only" else W, sel, c) for c in OBJ4}
        hp = holm({c: v["p_one_sided"] for c, v in o4.items()})
        for c in o4:
            o4[c]["p_holm"] = hp[c]
        L["objective4"] = o4
        # Objective 1: news ablation, every arm, full window and news era
        L["news_ablation"] = {a: {"full": paired(W, V.arm_name(a, True), a), "news_era": paired(era, V.arm_name(a, True), a)}
                              for a in V.ARMS}
        # improvements vs REF (no news) on the full window
        L["vs_REF"] = {n: paired(W, n, "REF") for n in ARM_NAMES if n != "REF"}
        # SHAP group shares, verdict window, non-fallback rows (I3/ALL: their base model's SHAP)
        sh = {}
        for n in ARM_NAMES:
            arm, news = n.replace("+news", ""), n.endswith("+news")
            src = S[(S["name"] == n) & (S["lead"] == k) & S["q"].isin(W["q"])]
            cc = V.cols(V.ARMS[arm][0], news)
            src = src.dropna(subset=[f"shap_{cc[0]}"])
            sh[n] = {"rows": int(len(src)), "shares": V.group_shares(src, cc) if len(src) else None,
                     "shap_of": V.arm_name(V.BASE_OF[arm], news)}
        L["shap"] = sh
        # flags
        f = F[(F["lead"] == k) & F["q"].isin(W["q"]) & F["name"].isin(ARM_NAMES + BASELINES)]
        L["flags"] = {n: {"fallback": int(g["fallback"].astype(str).str.lower().eq("true").sum()),
                          "platt_skipped": int(g["platt_skipped"].astype(str).str.lower().eq("true").sum())
                          if g["platt_skipped"].notna().any() else None,
                          "sigma_fallback": int(g["sigma_fallback"].astype(str).str.lower().eq("true").sum())
                          if g["sigma_fallback"].notna().any() else None}
                      for n, g in f.groupby("name")}
        res["leads"][f"L{k}"] = L
        W.to_csv(OUT / f"rows_lead{k}.csv", index=False)
        print(f"lead {k}: passing {passing}; carried forward {sel}", flush=True)
    rel = [k for k in LEADS if res["leads"][f"L{k}"]["selection"]["passing"]]
    mx = 0
    for k in LEADS:
        if k in rel:
            mx = k
        else:
            break
    res["max_reliable_lead"] = mx
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print("max reliable lead:", mx)


def versions() -> dict:
    import lightgbm
    import sklearn
    return {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
            "lightgbm": lightgbm.__version__, "sklearn": sklearn.__version__}


if __name__ == "__main__":
    {"build": build, "fit": fit, "score": score}[sys.argv[1]]()
