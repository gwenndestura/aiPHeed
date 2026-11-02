"""HISTORY_RETRAIN runner (PLAN.md section 9).

    python run_hr.py build    # feature tables, labels, PLAN section 8 checks -> out/checks.json (stops on any failure)
    python run_hr.py fit      # PERSIST, LOGIT, LGBM walk-forward forecasts -> out/forecasts_classic.csv
    python dl.py ...          # MLP and GRU (PLAN_AMENDMENT_1) -> out/dl/*.csv
    python run_hr.py score    # every model on every window -> out/results.json, out/rows.csv
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import platform

import numpy as np
import pandas as pd

import hr_lib as H

OUT = H.OUT
OPTS = {"b": None, "c": None}


def doc_ok(name: str, tag: str) -> str:
    b = (H.HR / name).read_bytes()
    i = b.rfind(b"\n" + tag.encode()) + 1
    h = hashlib.sha256(b[:i]).hexdigest()
    if h != b[i:].split(b":", 1)[1].strip().decode():
        raise SystemExit(f"{name} changed after it was hashed")
    return h


def hashes() -> dict:
    return {"plan": doc_ok("PLAN.md", "PLAN-SHA256:"), "amendment1": doc_ok("PLAN_AMENDMENT_1.md", "AMENDMENT-SHA256:")}


def cols(target: str, opt: str, model: str) -> list[str]:
    if target == "T1":
        c = H.T1_B + (H.T1_C_EXTRA if opt == "c" else [])
        return c + (["h_last"] if model == "LOGIT" else ["lead"])
    c = H.T2_B + (H.T2_C_EXTRA if opt == "c" else [])
    return c + ([] if model == "LOGIT" else ["lead"])


def first_origin(opt: str) -> int:
    return H.FIRST_ORIGIN if opt == "b" else H.FIRST_ORIGIN_C


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


def fidelity(d: H.Data) -> dict:
    """PLAN 8.1 (a)-(e) against the served 2021+ implementation."""
    res = {}
    for p in ("FINAL_UNIFIED_LGBM", "FINAL_FOOD_INSECURITY_LIGHTGBM"):
        sys.path.insert(0, str(H.EXP / p / "runner"))
    import uni_lib as U
    U.setup()
    C, FM = U.C, U.FM
    # (a) T1 labels 2021+
    mine = H.t1_labels(d)
    mine = mine[mine["q"] >= 2021 * 4].set_index(["province_code", "q"])[["y", "price", "hunger"]].sort_index()
    srv = C.labels().set_index(["province_code", "q"])[["y", "price", "hunger"]].sort_index()
    res["a_t1_labels_2021plus"] = {"n_mine": len(mine), "n_served": len(srv),
                                   "equal": bool(mine.index.equals(srv.index) and (mine.values == srv.values).all())}
    # (b) pi_H4L restricted to 2021+ == served pi_H4; (c) PERSIST == PERSIST-SI_p
    # (b) is checked against the served function (LEAD2_OPTIMIZATION a3.h4, H0 = ch1_lib.pi_h on fallback) at 1e-9, and
    # against predictions.csv at its stored precision (pi_H4 is written with 6 decimals, so 1e-9 there is impossible).
    sys.path.insert(0, str(H.EXP / "LEAD2_OPTIMIZATION" / "runner"))
    import a3
    pr = pd.read_csv(H.EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    pr = pr[pr["lead"].isin([1, 2])]
    db, dcsv, dc = [], [], []
    for (t, k), g in pr.groupby(["t", "lead"]):
        mine = H.pi_h4l(d, int(t), int(k), min_q=2021 * 4)["pi"]
        srv = a3.h4(int(t), int(k))
        srv = C.pi_h(int(t), int(k))[0] if srv != srv else srv
        db.append(abs(mine - srv))
        dcsv.append(abs(round(mine, 6) - float(g["pi_H4"].iloc[0])))
        ps = H.persist_t1(d, int(t))
        dc += [abs(ps[p] - v) for p, v in zip(g["province_code"], g["PERSIST-SI_p"])]
    res["b_pi_H4_2021plus"] = {"rows": len(db), "max_abs_diff_vs_served_function": float(max(db)),
                               "max_abs_diff_vs_csv_rounded_6dp": float(max(dcsv)),
                               "equal": bool(max(db) < 1e-9 and max(dcsv) < 1e-12)}
    res["c_persist_si"] = {"rows": len(dc), "max_abs_diff": float(np.nanmax(dc)), "equal": bool(np.nanmax(dc) < 1e-12)
                           and not np.isnan(dc).any()}
    # (d) SWS 2021+ rows == verified primary series
    a = d.sws[d.sws["q"] >= 2021 * 4][["area", "q", "H", "published"]].sort_values(["area", "q", "published", "H"])
    b = FM.rounds("primary")[["area", "q", "H", "published"]].sort_values(["area", "q", "published", "H"])
    res["d_sws_2021plus"] = {"n_mine": len(a), "n_served": len(b),
                             "equal": bool(len(a) == len(b) and (a.values == b.values).all())}
    # (e) Region IV-A CPI == cov_cpi
    c = pd.read_csv(H.LONG / "cov_cpi.csv")
    c = c[c["geolocation"] == "Region IV-A (CALABARZON)"].dropna(subset=["value"])
    mx = 0.0
    for com, lab in (("all_items", "0 - ALL ITEMS"), ("food", "01.1 - FOOD")):
        s = c[c["commodity_description"] == lab].set_index("ym")["value"]
        m = d.idx[(H.REGION, com)]
        j = s.index.intersection(m.index)
        assert len(j) == len(s) == len(m), (com, len(j), len(s), len(m))
        mx = max(mx, float((s[j] - m[j]).abs().max()))
    res["e_region_cpi"] = {"max_abs_diff": mx, "equal": mx < 1e-9}
    return res


def leakage(d: H.Data, L1, L2, PF) -> dict:
    """PLAN 8.2: rows and training labels at origin t unchanged when everything published >= O(t) is randomized."""
    out = {}
    for s in ("2000-Q2", "2005-Q2", "2010-Q1", "2015-Q3", "2020-Q2", "2023-Q4", "2026-Q2"):
        t = H.qi(s)
        e = H.perturb(d, t, seed=t)
        l1e, l2e, pfe = H.t1_labels(e), H.t2_labels(e), H.price_frame(e)
        ok = {"T1_rows": _same(pd.DataFrame(H.rows_t1(d, t)), pd.DataFrame(H.rows_t1(e, t))),
              "T2_rows": _same(pd.DataFrame(H.rows_t2(d, t)), pd.DataFrame(H.rows_t2(e, t))),
              "T1_labels": _same(H.known_t1(d, t, L1), H.known_t1(e, t, l1e)),
              "price_labels": _same(H.known_price(d, t, PF), H.known_price(e, t, pfe)),
              "T2_labels": _same(H.known_t2(d, t, L2), H.known_t2(e, t, l2e)),
              "persist": H.persist_t1(d, t) == H.persist_t1(e, t) and H.persist_t2(d, t) == H.persist_t2(e, t),
              "perturbed_something": not _same(H.t1_labels(d), l1e) or not _same(H.t2_labels(d), l2e)}
        out[s] = ok
    return out


def build():
    OUT.mkdir(exist_ok=True)
    hs = hashes()
    d = H.load()
    origins = list(range(H.FIRST_ORIGIN, 2026 * 4 + 3))          # 1998-Q3..2026-Q3
    T1 = H.table(d, "T1", origins)
    T2 = H.table(d, "T2", origins)
    L1, L2, PF = H.t1_labels(d), H.t2_labels(d), H.price_frame(d)
    checks = {"hashes": hs, "fidelity": fidelity(d), "leakage": leakage(d, L1, L2, PF)}
    # 8.4: every evaluation row's SWS input published before O(t)
    ev = T1[T1["t"].isin(H.ORIGINS_EVAL)]
    checks["eval_sws_before_issue"] = bool((ev["sws_newest_published"] < ev["t"].map(H.issue)).all())
    # option (c) starts where E1 and A3 exist for all five provinces
    c0 = T1[(T1["lead"] == 1)].groupby("t").apply(lambda g: bool(g[["E1", "A3"]].notna().all().all()))
    checks["option_c_first_complete_origin"] = H.qs(int(c0[c0].index.min()))
    T1.to_csv(OUT / "table_T1.csv", index=False)
    T2.to_csv(OUT / "table_T2.csv", index=False)
    PF.to_csv(OUT / "labels_price.csv", index=False)
    (OUT / "checks.json").write_text(json.dumps(checks, indent=1, default=str))
    fid = all(v["equal"] for v in checks["fidelity"].values())
    leak = all(all(v.values()) for v in checks["leakage"].values())
    print(json.dumps(checks, indent=1, default=str)[:4000])
    if not (fid and leak and checks["eval_sws_before_issue"]):
        raise SystemExit("PLAN section 8 check failed: nothing is scored")
    if checks["option_c_first_complete_origin"] != H.qs(H.FIRST_ORIGIN_C):
        raise SystemExit(f"option (c) start differs from PLAN: {checks['option_c_first_complete_origin']}")
    print("all section 8 checks passed")


# ================================================================================================ fit (classic)
def tables():
    T1 = pd.read_csv(OUT / "table_T1.csv", dtype={"province_code": str})
    T2 = pd.read_csv(OUT / "table_T2.csv")
    return T1, T2


def train_rows(S: pd.DataFrame, t: int, labels: pd.DataFrame, on: list[str], lead: int | None = None) -> pd.DataFrame:
    tr = S[(S["t"] < t) & (S["q"] <= t - 1)]
    if lead is not None:
        tr = tr[tr["lead"] == lead]
    return tr.merge(labels[on + ["y"]], on=on, how="inner")


def fit_one(S, t, opt, target, model, lab, on, clim):
    """Forecasts of the rows of origin t at leads 1 and 2 for LOGIT or LGBM, with the eligibility fallback."""
    S = S[S["t"] >= first_origin(opt)]
    te = S[(S["t"] == t) & S["lead"].isin([1, 2])].copy()
    cc = cols(target, opt, model)
    out = []
    if model == "LGBM":
        tr = train_rows(S, t, lab, on)
        if H.eligible(tr):
            cfg = H.lgbm_select(tr, cc, mono=(target == "T1"))
            p = H.LGBM(cfg, cc, target == "T1").fit(tr).predict(te)
            fb, cid = False, cfg["id"]
        else:
            p, fb, cid = np.full(len(te), float(tr["y"].mean()) if len(tr) else clim), True, None
        te["p_raw"], te["fallback"], te["cfg"] = p, fb, cid
        out.append(te)
    else:
        for k in (1, 2):
            tk = te[te["lead"] == k].copy()
            tr = train_rows(S, t, lab, on, lead=k)
            if H.eligible(tr):
                p, fb = H.logit(tr, tk, cc), False
            else:
                p, fb = np.full(len(tk), float(tr["y"].mean()) if len(tr) else clim), True
            tk["p_raw"], tk["fallback"], tk["cfg"] = p, fb, None
            out.append(tk)
    return pd.concat(out)


def fit():
    T1, T2 = tables()
    d = H.load()
    L1, L2, PF = H.t1_labels(d), H.t2_labels(d), H.price_frame(d)
    PF = PF.rename(columns={"price": "y"})
    rows = []
    for t in H.ORIGINS_EVAL:
        k1, kp, k2 = H.known_t1(d, t, L1), H.known_price(d, t, PF), H.known_t2(d, t, L2)
        clim1 = float(k1["y"].mean()) if len(k1) else 0.0
        clim2 = float(k2["y"].mean()) if len(k2) else 0.0
        ps1, ps2 = H.persist_t1(d, t), H.persist_t2(d, t)
        for opt in ("b", "c"):
            # T1: LOGIT on the T1 label; LGBM = pi_H4L x price LightGBM
            f = fit_one(T1, t, opt, "T1", "LOGIT", k1, ["province_code", "q"], clim1)
            rows.append(f.assign(target="T1", option=opt, model="LOGIT", p=f["p_raw"]))
            f = fit_one(T1, t, opt, "T1", "LGBM", kp, ["province_code", "q"], clim1)
            rows.append(f.assign(target="T1", option=opt, model="LGBM", p=f["H1"] * f["p_raw"]))
            for m in ("LOGIT", "LGBM"):
                f = fit_one(T2, t, opt, "T2", m, k2, ["q"], clim2)
                rows.append(f.assign(target="T2", option=opt, model=m, p=f["p_raw"]))
        te = T1[(T1["t"] == t) & T1["lead"].isin([1, 2])]
        rows.append(te.assign(target="T1", option="-", model="PERSIST",
                              p=[ps1[p] if not np.isnan(ps1[p]) else clim1 for p in te["province_code"]],
                              fallback=False, cfg=None))
        te2 = T2[(T2["t"] == t) & T2["lead"].isin([1, 2])]
        rows.append(te2.assign(target="T2", option="-", model="PERSIST", p=ps2 if not np.isnan(ps2) else clim2,
                               fallback=False, cfg=None))
        for tg, te_, cl in (("T1", te, clim1), ("T2", te2, clim2)):
            rows.append(te_.assign(target=tg, option="-", model="CLIM", p=cl, fallback=False, cfg=None))
        print(H.qs(t), flush=True)
    F = pd.concat(rows, ignore_index=True)
    keep = ["target", "option", "model", "t", "lead", "q", "province_code", "p", "p_raw", "H1", "pi_H4L", "fallback",
            "cfg"]
    F = F[[c for c in keep if c in F.columns]]
    F.to_csv(OUT / "forecasts_classic.csv", index=False)
    print("written", len(F))


# ================================================================================================ score
VERDICT = {("T1", 1): (H.qi("2023-Q1"), H.qi("2026-Q3")), ("T1", 2): (H.qi("2023-Q2"), H.qi("2026-Q3")),
           ("T2", 1): (H.EVAL_FIRST, H.EVAL_LAST), ("T2", 2): (H.EVAL_FIRST, H.EVAL_LAST)}
SECONDARY = {"T1": {"dev_2010_2022": (H.EVAL_FIRST, H.qi("2022-Q4")), "all_2010_2026": (H.EVAL_FIRST, H.EVAL_LAST)},
             "T2": {"dev_2010_2022": (H.EVAL_FIRST, H.qi("2022-Q4")), "block_2023_2026": (H.qi("2023-Q1"), H.EVAL_LAST)}}
SENS = {"S1_no_phone_2020": [H.qi("2020-Q2"), H.qi("2020-Q3")],
        "S2_no_adults_2025Q2plus": list(range(H.qi("2025-Q2"), H.EVAL_LAST + 1))}
SENS["S3_both"] = SENS["S1_no_phone_2020"] + SENS["S2_no_adults_2025Q2plus"]
DL_SEEDS = range(10)


def frame(F: pd.DataFrame, target: str, lead: int, lab: pd.DataFrame) -> pd.DataFrame:
    """One evaluation frame per target and lead: every model's p and the baselines side by side, labelled rows only."""
    key = ["t", "q", "province_code"] if target == "T1" else ["t", "q"]
    f = F[(F["target"] == target) & (F["lead"] == lead)].copy()
    f["name"] = f["model"] + np.where(f["option"].isin(["b", "c"]), "_" + f["option"], "")
    W = f.pivot_table(index=key, columns="name", values="p", aggfunc="first").reset_index()
    W = W.merge(lab, on=[k for k in ("province_code", "q") if k in key], how="inner")
    W["ALWAYS-HIGH_p"], W["ALWAYS-LOW_p"] = 1.0, 0.0
    W["PERSIST-SI_p"], W["CLIM_p"] = W["PERSIST"], W["CLIM"]
    return W


def check_fast_boot(F: pd.DataFrame, L1: pd.DataFrame) -> dict:
    """rules() with the vectorized bootstrap equals rules() with the original pd.concat bootstrap (3 real frames)."""
    R = H.rp()
    W = frame(F, "T1", 1, L1[["province_code", "q", "y"]])
    W = W[W["q"] >= H.qi("2023-Q1")]
    out = {}
    for n in ("LGBM_b", "LOGIT_b", "PERSIST"):
        h = W.copy()
        h[R.P], h["target"] = h[n], h["q"].map(H.qs)
        fast = R.rules(h)
        R.boot_quarters, keep = R.boot_quarters_original, R.boot_quarters
        orig = R.rules(h)
        R.boot_quarters = keep
        out[n] = fast == orig
    if not all(out.values()):
        raise SystemExit(f"fast bootstrap differs from the original: {out}")
    return out


def score():
    hs = hashes()
    d = H.load()
    L1, L2 = H.t1_labels(d), H.t2_labels(d)
    F = pd.read_csv(OUT / "forecasts_classic.csv", dtype={"province_code": str})
    dl = sorted((OUT / "dl").glob("*.csv"))
    D = pd.concat([pd.read_csv(f, dtype={"province_code": str}) for f in dl], ignore_index=True) if dl else None
    if D is not None:
        D["model"] = D["model"] + "_s" + D["seed"].astype(str)
        F = pd.concat([F, D[F.columns.intersection(D.columns)]], ignore_index=True)
    res = {"hashes": hs, "versions": versions(), "fastBootEqualsOriginal": check_fast_boot(F, L1), "windows": {},
           "fallbacks": fallbacks(F)}
    print("fast bootstrap check:", res["fastBootEqualsOriginal"], flush=True)
    allrows = []
    for target, lab in (("T1", L1[["province_code", "q", "y"]]), ("T2", L2[["q", "y"]])):
        for lead in (1, 2):
            W = frame(F, target, lead, lab)
            allrows.append(W.assign(target=target, lead=lead))
            names = [c for c in W.columns if c not in ("t", "q", "province_code", "y") and not c.endswith("_p")]
            wins = {"verdict": VERDICT[(target, lead)], **SECONDARY[target]}
            for wn, (a, b) in wins.items():
                g = W[(W["q"] >= a) & (W["q"] <= b)]
                if target == "T1" and wn == "verdict":
                    assert len(g) == (70 if lead == 1 else 65), (lead, len(g))
                if target == "T2" and wn == "verdict":
                    assert g["q"].nunique() == len(g) and len(g) >= 40, len(g)
                res["windows"][f"{target}|L{lead}|{wn}"] = win_results(g, names)
                if wn == "verdict":
                    for sn, drop in SENS.items():
                        gs = g[~g["q"].isin(drop)]
                        if len(gs) < len(g):
                            res["windows"][f"{target}|L{lead}|verdict_{sn}"] = win_results(gs, names, light=True)
    pd.concat(allrows, ignore_index=True).to_csv(OUT / "rows.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    print("scored", len(res["windows"]), "windows")


def _eval_one(a):
    """A model without forecasts for part of the window (option (c) before its first origin 2011-Q2) is scored on the
    rows it has, with the baselines on those same rows; the rows and quarters used are recorded (PLAN 8.5)."""
    g, n, light = a
    miss = int(g[n].isna().sum())
    g = g[g[n].notna()]
    if not len(g):
        return n, {"missing_forecasts": miss}
    r = H.evaluate(g, n)
    r = r if not light else {"metrics": r["metrics"], "allR1R7": r["allR1R7"], "reliable": r["reliable"]}
    r["missing_forecasts"], r["n_rows_scored"], r["n_quarters_scored"] = miss, int(len(g)), int(g["q"].nunique())
    r["period_scored"] = f"{H.qs(g['q'].min())}..{H.qs(g['q'].max())}"
    return n, r


def win_results(g: pd.DataFrame, names: list[str], light: bool = False) -> dict:
    """Every model scored in parallel; each evaluate() is self-contained and seeded inside rules(), so the numbers do
    not depend on the number of processes."""
    from multiprocessing import Pool
    out = {"n_rows": int(len(g)), "n_quarters": int(g["q"].nunique()), "high_share": float(g["y"].mean()),
           "period": f"{H.qs(g['q'].min())}..{H.qs(g['q'].max())}", "models": {}}
    todo = names + ["ALWAYS-HIGH_p", "ALWAYS-LOW_p"]
    with Pool(8) as pool:
        res = dict(pool.map(_eval_one, [(g, n, light) for n in todo]))
    out["models"] = {n: res[n] for n in todo}
    print(f"  window {out['period']} ({len(todo)} models)", flush=True)
    return out


def fallbacks(F: pd.DataFrame) -> dict:
    f = F[F["model"].isin(["LOGIT", "LGBM"]) | F["model"].str.startswith(("MLP", "GRU"))]
    f = f[f["t"].isin(H.ORIGINS_EVAL)]
    g = f.groupby(["target", "option", "model", "lead"])["fallback"].apply(
        lambda s: int(s.astype(str).str.lower().eq("true").sum()))
    return {"|".join(map(str, k)): int(v) for k, v in g.items() if v}


def versions() -> dict:
    import lightgbm
    import sklearn
    v = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
         "lightgbm": lightgbm.__version__, "sklearn": sklearn.__version__}
    try:
        import torch
        v["torch"] = torch.__version__
    except ImportError:
        pass
    return v


if __name__ == "__main__":
    {"build": build, "fit": fit, "score": score}[sys.argv[1]]()
