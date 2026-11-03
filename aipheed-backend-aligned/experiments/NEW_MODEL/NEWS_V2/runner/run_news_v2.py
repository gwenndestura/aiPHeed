"""NEWS_V2 (EXPLORATORY): REF+news with the news columns replaced by their own-history anomalies (PLAN.md).

    python run_news_v2.py features   # z-anomalies per origin + leakage check -> ../out/news_anomalies.csv
    python run_news_v2.py fit        # REF+news reproduction, C-a, C-b walk-forward (test leads 1-8) -> ../out/forecasts.csv
    python run_news_v2.py score      # metrics, R1-R7, Algorithm 3, news era, Brier tests, decision -> ../out/results.json
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
EXP = HERE.parents[1]
PLAN = HERE / "PLAN.md"
OUT = HERE / "out"
sys.path.insert(0, str(EXP / "IMPROVE_V2" / "runner"))
import iv2_lib as V  # noqa: E402
import run_iv2 as R  # noqa: E402

H = V.H
IV2_OUT = EXP / "IMPROVE_V2" / "out"
OPT = EXP / "OPTION_1" / "out" / "forecasts_refnews.csv"
LEADS_FILE = EXP / "IMPROVE_V2_LEADS" / "out" / "forecasts_leads.csv"
REF_COLS = V.cols(False, False)
NEWS = list(V.NEWS)
Z = [f"z_{c}" for c in NEWS]
MODELS = {"REF+news_repro": V.cols(False, True),
          "C-a": REF_COLS[:-1] + Z + REF_COLS[-1:],
          "C-b": REF_COLS[:-1] + ["z_N1R"] + REF_COLS[-1:]}
TEST_LEADS = tuple(range(1, 9))
WIN, MINP = 8, 4
ERA = V.NEWS_ERA
SEED, REPS = 2036, 5


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_plan() -> str:
    b = PLAN.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PLAN.md changed after it was hashed"
    return h


# ================================================================================================ features
def anomalies(series: pd.DataFrame) -> pd.DataFrame:
    """z(x, t) = (x(t) - mean(x, t-8..t-1)) / sd (ddof 1); NaN if < 4 past values or sd = 0. Past origins only."""
    s = series.set_index("t").sort_index()
    out = {"t": s.index.to_numpy()}
    for c in NEWS:
        vals = []
        for t in s.index:
            past = s.loc[[x for x in range(t - WIN, t) if x in s.index], c].dropna()
            x = s.loc[t, c]
            sd = float(past.std(ddof=1)) if len(past) >= 2 else float("nan")
            vals.append(float((x - past.mean()) / sd) if pd.notna(x) and len(past) >= MINP and sd > 0 else np.nan)
        out[f"z_{c}"] = vals
    return pd.DataFrame(out)


def features():
    plan = check_plan()
    T = pd.read_csv(IV2_OUT / "table_pooled.csv", dtype={"area": str})
    base = T[(T["area"] == "BL") & (T["lead"] == 1)][["t"] + NEWS].drop_duplicates("t").sort_values("t")
    A = anomalies(base)
    rng = np.random.default_rng(SEED)
    stable = True
    for _ in range(REPS):
        for t in A["t"]:
            p = base.copy()
            fut = p["t"] > t
            p.loc[fut, NEWS] = rng.normal(0, 1, (int(fut.sum()), len(NEWS)))
            a = anomalies(p)
            x, y = a[a["t"] == t][Z].to_numpy(float), A[A["t"] == t][Z].to_numpy(float)
            if not np.allclose(np.nan_to_num(x, nan=9e9), np.nan_to_num(y, nan=9e9), atol=0, rtol=0):
                stable = False
    OUT.mkdir(parents=True, exist_ok=True)
    A.to_csv(OUT / "news_anomalies.csv", index=False)
    era = A[A["t"] >= ERA]
    chk = {"plan_sha256": plan, "table_pooled_sha256": sha(IV2_OUT / "table_pooled.csv"),
           "leakage_future_news_randomized_unchanged": stable, "reps": REPS,
           "non_missing_in_news_era": {c: int(era[c].notna().sum()) for c in Z}, "news_era_origins": int(len(era))}
    (OUT / "checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    print(json.dumps(chk, indent=1))
    if not stable:
        raise SystemExit("leakage check failed")


# ================================================================================================ fit
_G: dict = {}


def _init():
    _G["d"] = H.load()
    T = pd.read_csv(IV2_OUT / "table_pooled.csv", dtype={"area": str})
    _G["T"] = T.merge(pd.read_csv(OUT / "news_anomalies.csv"), on="t", how="left")
    _G["lab"] = V.area_labels(_G["d"])


def _origin(job) -> pd.DataFrame:
    """OPTION_1 _origin (V.fit_base, BL, classification) with the given columns, test leads 1-8."""
    t, name, cols = job
    d, S, lab = _G["d"], _G["T"], _G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(TEST_LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    te["p"], te["fallback"], te["cfg"] = np.nan, False, None
    shap = None
    if H.eligible(trb):
        cfg = H.lgbm_select(tr, cols, mono=False)
        m = H.LGBM(cfg, cols, False).fit(tr)
        te["p"], te["cfg"] = m.predict(te), cfg["id"]
        if m.m is not None:
            shap = V.shap_frame(m.m, te[cols])
    else:
        te["p"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    out = te[["t", "lead", "q", "p", "fallback", "cfg"]].assign(name=name)
    if shap is not None:
        sh = shap.set_index(out.index)
        news_cols = [c for c in cols if c in NEWS or c in Z]
        out["shap_news_abs"] = sh[news_cols].abs().sum(axis=1) if news_cols else 0.0
        out["shap_all_abs"] = sh.abs().sum(axis=1)
    return out


def fit():
    plan = check_plan()
    assert json.loads((OUT / "checks.json").read_text(encoding="utf-8"))["leakage_future_news_randomized_unchanged"]
    jobs = [(t, n, c) for t in V.ORIGINS for n, c in MODELS.items()]
    with Pool(8, initializer=_init) as pool:
        parts = pool.map(_origin, jobs)
    F = pd.concat(parts, ignore_index=True)
    F.to_csv(OUT / "forecasts.csv", index=False)
    old = pd.read_csv(OPT)
    old = old[(old["name"] == "REF+news") & old["lead"].isin(TEST_LEADS)][["t", "lead", "q", "p", "cfg"]]
    new = F[F["name"] == "REF+news_repro"][["t", "lead", "q", "p", "cfg"]]
    m = old.merge(new, on=["t", "lead"], how="inner", suffixes=("_old", "_new"))
    norm = lambda s: s.astype(str).str.replace(".0", "", regex=False)  # noqa: E731
    cfg_eq = bool(((m["cfg_old"].isna() & m["cfg_new"].isna()) | (norm(m["cfg_old"]) == norm(m["cfg_new"]))).all())
    rep = {"rows_old": int(len(old)), "matched": int(len(m)), "same_q": bool((m["q_old"] == m["q_new"]).all()),
           "max_abs_diff": float((m["p_old"] - m["p_new"]).abs().max()), "cfg_equal": cfg_eq}
    ok = rep["matched"] == rep["rows_old"] and rep["same_q"] and rep["max_abs_diff"] <= 1e-12 and cfg_eq
    c = json.loads((OUT / "checks.json").read_text(encoding="utf-8"))
    c.update({"plan_sha256": plan, "reproduction_REFnews_leads_1_8": rep, "reproduced": ok, "versions": R.versions()})
    (OUT / "checks.json").write_text(json.dumps(c, indent=1, default=str), encoding="utf-8")
    print(json.dumps(rep, indent=1))
    if not ok:
        raise SystemExit("REF+news is not reproduced: candidates are not scored")


# ================================================================================================ score
def _summ(g: pd.DataFrame, name: str) -> dict:
    r = H.evaluate(g, name)
    m = r["metrics"]
    rules = {k.split()[0]: {"pass": v["pass"], "value": v["value"]} for k, v in r["rules"].items()}
    return {"metrics": {x: m.get(x) for x in ("accuracy", "balanced", "precision", "recall", "f1", "auc", "brier",
                                             "TP", "FP", "FN", "TN")},
            "rules": rules, "failed": [x for x, v in rules.items() if not v["pass"]]}


def _brier_test(g: pd.DataFrame, a: str, b: str) -> dict:
    dv = ((g[a] - g["y"]) ** 2 - (g[b] - g["y"]) ** 2).to_numpy(float)
    return {"diff": float(dv.mean()), "p_one_sided": float(np.mean(H.boot_mean(g["q"].to_numpy(), dv, H.rp()) >= 0))}


def score():
    plan = check_plan()
    assert json.loads((OUT / "checks.json").read_text(encoding="utf-8"))["reproduced"]
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    L = pd.read_csv(LEADS_FILE)
    O = pd.read_csv(OPT)
    F = pd.read_csv(OUT / "forecasts.csv")
    cand = F[F["name"].isin(["C-a", "C-b"])]
    FF = pd.concat([L[L["name"].isin(["REF", "PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                    O[O["name"] == "REF+news"][["name", "t", "lead", "q", "p"]], cand[["name", "t", "lead", "q", "p"]]],
                   ignore_index=True)
    names = ["REF", "REF+news", "C-a", "C-b"]
    res = {"plan_sha256": plan, "label": "EXPLORATORY; development evidence; 2 candidates designed after Phase 2",
           "leads": {}, "algorithm3": {}}
    for k in TEST_LEADS:
        W = R.frame(FF, k, lab_bl)
        g = W.dropna(subset=names)
        L_ = {"n_quarters": int(g["q"].nunique())}
        for n in names:
            L_[n] = {"accuracy": float(((g[n] >= .5).astype(int) == g["y"]).mean())}
            if k <= 2:
                L_[n].update(_summ(g, n))
                e = g[g["t"] >= ERA]
                L_[n]["news_era"] = {"quarters": int(len(e)), "accuracy": float(((e[n] >= .5).astype(int) == e["y"]).mean()),
                                     "brier": float(((e[n] - e["y"]) ** 2).mean())}
                if n in ("C-a", "C-b"):
                    s = cand[(cand["name"] == n) & (cand["lead"] == k) & cand["q"].isin(g["q"])]
                    L_[n]["news_shap_share_pct"] = float(100 * s["shap_news_abs"].sum() / s["shap_all_abs"].sum())
                    L_[n]["news_shap_share_news_era_pct"] = float(
                        100 * s[s["t"] >= ERA]["shap_news_abs"].sum() / s[s["t"] >= ERA]["shap_all_abs"].sum())
        if k <= 2:
            for comp in ("REF+news", "REF"):
                tests = {n: _brier_test(g, n, comp) for n in ("C-a", "C-b")}
                hp = R.holm({n: v["p_one_sided"] for n, v in tests.items()})
                for n in tests:
                    tests[n]["p_holm"] = hp[n]
                L_[f"vs_{comp}"] = tests
        res["leads"][str(k)] = L_
    for n in names:
        mx = 0
        accs = {}
        for k in TEST_LEADS:
            a = res["leads"][str(k)][n]["accuracy"]
            accs[k] = a
            if a >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][n] = {"mrlt": mx, "accuracy_by_lead": accs}
    dec = {}
    for n in ("C-a", "C-b"):
        imp = all(res["leads"][str(k)]["vs_REF+news"][n]["diff"] < 0 and res["leads"][str(k)]["vs_REF+news"][n]["p_holm"] < .10
                  and res["leads"][str(k)][n]["accuracy"] >= res["leads"][str(k)]["REF+news"]["accuracy"] for k in (1, 2))
        val = imp and all(res["leads"][str(k)]["vs_REF"][n]["diff"] < 0 and res["leads"][str(k)]["vs_REF"][n]["p_holm"] < .10
                          for k in (1, 2))
        dec[n] = {"improves_REFnews": bool(imp), "news_adds_value_over_REF": bool(val),
                  "passes_R1_R7_both_leads": all(not res["leads"][str(k)][n]["failed"] for k in (1, 2))}
    q = [n for n in ("C-a", "C-b") if dec[n]["improves_REFnews"]]
    best = min(q, key=lambda n: np.mean([res["leads"][str(k)][n]["metrics"]["brier"] for k in (1, 2)])) if q else None
    res["decision"] = {"by_candidate": dec, "named": best,
                       "summary": f"{best} improves REF+news at both leads" if best else
                       "neither candidate improves REF+news at both leads under the fixed rule; REF+news unchanged"}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in (1, 2):
        Lk = res["leads"][str(k)]
        for n in names:
            x = Lk[n]
            m = x["metrics"]
            print(f"L{k} {n:9s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {x['failed']} | news-era acc "
                  f"{x['news_era']['accuracy']:.3f} ({x['news_era']['quarters']} q)"
                  + (f" | news SHAP {x['news_shap_share_news_era_pct']:.1f}% (era)" if "news_shap_share_pct" in x else ""))
        for comp in ("REF+news", "REF"):
            print(f"   vs {comp}: " + "; ".join(f"{n} diff {v['diff']:+.4f} Holm p {v['p_holm']:.3f}"
                                             for n, v in Lk[f"vs_{comp}"].items()))
    print("Algorithm 3:", {n: (v["mrlt"], {k: round(a, 3) for k, a in v["accuracy_by_lead"].items()})
                           for n, v in res["algorithm3"].items()})
    print("DECISION:", json.dumps(res["decision"]))


if __name__ == "__main__":
    {"features": features, "fit": fit, "score": score}[sys.argv[1]]()
