"""C-B6P (../PREREGISTRATION.md, hash checked): C-B6 as a province-quarter forecast (Eq. 3 label) + E1 + E2 + D1.

    python cb6p_model.py fit     # walk-forward C-B6P, C-B6P-noE, LOGIT -> ../out/cb6p_fits.csv
    python cb6p_model.py score   # metrics, Algorithm 3, Holm family, acceptance -> ../out/cb6p_results.json
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
PLAN = HERE / "PREREGISTRATION.md"
OUT = HERE / "out"
CPI = EXP / "E40_SWS_CPI_Tiers" / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv"
sys.path.insert(0, str(AUD / "runner"))
import cb6_model as CB  # noqa: E402

PC, N, V, H = CB.PC, CB.N, CB.V, CB.H
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
Q0 = H.qi("2021-Q1")
BASE = PC.CB + CB.ST
COLS = {"C-B6P": BASE + ["E1", "E2", "D1"], "C-B6P-noE": BASE + ["D1"]}
FIRST, LEADS, SEED, B = H.qi("2020-Q1"), list(range(1, 9)), 2036, 5000
GROUPS = {"market": ["R_food_yoy", "R_head_yoy", "R_food_mom", "R_rice_yoy"] + H.WORLD,
          "climate": ["ONI_last", "ONI_max12", "tc_mean", "R_C3"], "fish_kill": ["R_C4"],
          "hunger": ["h_last", "h_change", "h_mean4", "true_h", "pi_H4L"], "news": ["z_N1R"], "lead": ["lead"],
          "employment": ["E1"], "ofw_remittance": ["E2"], "supply": CB.ST, "province_price": ["D1"]}


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "C-B6P pre-registration changed"
    return h


def m_avail(t: int) -> int:
    iss = H.issue(t)
    return int(iss[:4]) * 12 + int(iss[5:7]) - 1 - 2


def dev_monthly(c: pd.DataFrame) -> pd.DataFrame:
    """D by (province, ym): province food YoY minus the five-province mean of that month."""
    f = c[c["commodity"] == "food"].copy()
    f["ym"] = f["reference_month"].str[:4].astype(int) * 12 + f["reference_month"].str[5:7].astype(int) - 1
    f = f[f["province_code"].isin(PROVS)]
    f["D"] = f["yoy_pct"] - f.groupby("ym")["yoy_pct"].transform("mean")
    return f.pivot(index="ym", columns="province_code", values="D").sort_index()


def d1(Dm: pd.DataFrame, t: int) -> dict:
    m = m_avail(t)
    w = Dm[(Dm.index <= m) & (Dm.index >= m - 2)]
    return {p: (float(w[p].mean()) if len(w) == 3 and w[p].notna().all() else np.nan) for p in PROVS}


def q_dev(Dm: pd.DataFrame) -> dict:
    """D(p, q): quarter mean of the three months; only complete quarters."""
    out = {}
    for q in range(Q0, H.qi("2026-Q4")):
        ms = [q // 4 * 12 + (q % 4) * 3 + i for i in range(3)]
        if all(m in Dm.index for m in ms):
            w = Dm.loc[ms]
            for p in PROVS:
                if w[p].notna().all():
                    out[(p, q)] = (float(w[p].mean()), max(ms))
    return out


def labels(d, lab) -> tuple[pd.DataFrame, float]:
    Dm = dev_monthly(pd.read_csv(CPI, dtype={"province_code": str}))
    qd = q_dev(Dm)
    bl = lab[lab["area"] == "BL"].set_index("q")["H"]
    rows = [{"province": p, "q": q, "H": float(bl[q]), "D": v, "last_m": lm, "S": float(bl[q]) + 2 * v}
            for (p, q), (v, lm) in qd.items() if q in bl.index]
    L = pd.DataFrame(rows)
    thr = float(L[(L["q"] >= Q0) & (L["q"] <= H.qi("2022-Q4"))]["S"].median())
    L["y"] = (L["S"] > thr).astype(int)
    return L, thr


_G: dict = {}


def _init():
    CB._init()
    _G.update(N._G)
    _G["Dm"] = dev_monthly(pd.read_csv(CPI, dtype={"province_code": str}))
    _G["L"], _G["thr"] = labels(_G["d"], _G["lab"])


def _prov_rows(R: pd.DataFrame, Dm) -> pd.DataFrame:
    """Expand BL rows (t, lead) to five province rows with D1 known at O(t)."""
    out = []
    for t, g in R.groupby("t"):
        dd = d1(Dm, int(t))
        for p in PROVS:
            out.append(g.assign(province=p, D1=dd[p]))
    return pd.concat(out, ignore_index=True) if out else R.assign(province=None, D1=np.nan)


def train_rows(t: int) -> pd.DataFrame:
    d, S, lab, L, thr, Dm = _G["d"], _G["T"], _G["lab"], _G["L"], _G["thr"], _G["Dm"]
    src = S[(S["area"] == "BL") & (S["t"] < t) & (S["q"] <= t - 1)]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"][["q", "H"]]
    hist = src[src["q"] < Q0].merge(kb, on="q", how="inner")
    hist = hist.assign(y=(hist["H"] > thr).astype(int), province="BL", D1=np.nan)
    Lk = L[L["q"].isin(kb["q"]) & (L["last_m"] <= m_avail(t))][["province", "q", "y"]]
    pr = _prov_rows(src[src["q"] >= Q0], Dm).merge(Lk, on=["province", "q"], how="inner")
    return pd.concat([hist, pr], ignore_index=True)


def persist(t: int) -> dict:
    d, lab, L, thr = _G["d"], _G["lab"], _G["L"], _G["thr"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"].sort_values("q")
    Lk = L[L["q"].isin(kb["q"]) & (L["last_m"] <= m_avail(t))].sort_values("q")
    base = float(kb["H"].iloc[-1] > thr) if len(kb) else 0.5
    return {p: (float(Lk[Lk["province"] == p]["y"].iloc[-1]) if (Lk["province"] == p).any() else base) for p in PROVS}


def _origin(t: int) -> pd.DataFrame:
    S, Dm = _G["T"], _G["Dm"]
    te = _prov_rows(S[(S["area"] == "BL") & (S["t"] == t) & S["lead"].isin(LEADS)].copy(), Dm)
    tr = train_rows(t)
    frames = []
    for name, cols in COLS.items():
        o = te[["t", "lead", "q", "province"]].copy()
        o["name"], o["fallback"], o["cfg"] = name, False, None
        sh = pd.DataFrame(0.0, index=o.index, columns=cols)
        if H.eligible(tr):
            cfg = H.lgbm_select(tr, cols, mono=False)
            m = H.LGBM(cfg, cols, False).fit(tr)
            o["p"], o["cfg"] = m.predict(te), cfg["id"]
            if m.m is not None:
                sh = V.shap_frame(m.m, te[cols].reset_index(drop=True)).set_index(o.index)
        else:
            o["p"], o["fallback"] = float(tr["y"].mean()) if len(tr) else 0.5, True
        frames.append(pd.concat([o, sh.add_prefix("shap_")], axis=1))
    lg = te[["t", "lead", "q", "province"]].copy()
    lg["name"] = "LOGIT"
    lg["p"] = H.logit(tr, te, COLS["C-B6P"]) if tr["y"].nunique() == 2 else float(tr["y"].mean())
    ps = persist(t)
    pe = te[["t", "lead", "q", "province"]].copy()
    pe["name"], pe["p"] = "PERSIST", pe["province"].map(ps)
    return pd.concat(frames + [lg, pe], ignore_index=True)


def leakage() -> bool:
    Dm = dev_monthly(pd.read_csv(CPI, dtype={"province_code": str}))
    rng = np.random.default_rng(SEED)
    for t in range(FIRST, H.qi("2026-Q3") + 1):
        a = d1(Dm, t)
        P = Dm.copy()
        fut = P.index > m_avail(t)
        P.loc[fut] = rng.uniform(-20, 20, (int(fut.sum()), P.shape[1]))
        b = d1(P, t)
        if not all((np.isnan(a[p]) and np.isnan(b[p])) or a[p] == b[p] for p in PROVS):
            return False
    return True


def fit():
    pre = check()
    _init()
    chk = {"prereg_sha256": pre, "THR": _G["thr"], "D1_leakage_unchanged": leakage(),
           "province_labels": int(len(_G["L"])), "label_quarters": int(_G["L"]["q"].nunique()),
           "label_high_share": float(_G["L"]["y"].mean()), "cpi_sha256": hashlib.sha256(CPI.read_bytes()).hexdigest()}
    print(chk, flush=True)
    assert chk["D1_leakage_unchanged"], "D1 leakage check failed"
    with Pool(8, initializer=_init) as pool:
        F = pd.concat(pool.map(_origin, list(range(FIRST, H.qi("2026-Q3") + 1))), ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cb6p_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    _G["L"].to_csv(OUT / "cb6p_labels.csv", index=False)
    F.to_csv(OUT / "cb6p_fits.csv", index=False)
    print({"rows": len(F), "origins": int(F["t"].nunique())})


def metrics(y, p) -> dict:
    from sklearn.metrics import roc_auc_score
    y, p = np.asarray(y, int), np.asarray(p, float)
    c = (p >= .5).astype(int)
    tp, tn, fp, fn = int(((c == 1) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum()), int(((c == 1) & (y == 0)).sum()), \
        int(((c == 0) & (y == 1)).sum())
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    sp = tn / (tn + fp) if tn + fp else 0.0
    return {"n": int(len(y)), "high_share": float(y.mean()), "accuracy": float((c == y).mean()), "balanced": (rc + sp) / 2,
            "precision": pr, "recall": rc, "f1": 2 * pr * rc / (pr + rc) if pr + rc else 0.0,
            "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else None, "brier": float(np.mean((p - y) ** 2))}


def paired(W: pd.DataFrame, a: str, b: str) -> dict:
    W = W.assign(da=(W[a] - W["y"]) ** 2 - (W[b] - W["y"]) ** 2)
    g = W.groupby("q")["da"].agg(["sum", "count"])
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(g), (B, len(g)))
    s, n = g["sum"].to_numpy()[idx].sum(1), g["count"].to_numpy()[idx].sum(1)
    bs = s / n
    return {"diff": float(W["da"].mean()), "ci95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))],
            "p_one_sided": float((bs >= 0).mean())}


def holm(ps: dict) -> dict:
    ks = sorted(ps, key=ps.get)
    out, run = {}, 0.0
    for i, k in enumerate(ks):
        run = max(run, min(1.0, (len(ks) - i) * ps[k]))
        out[k] = run
    return out


def score():
    pre = check()
    L = pd.read_csv(OUT / "cb6p_labels.csv")
    F = pd.read_csv(OUT / "cb6p_fits.csv")
    R6 = pd.read_csv(AUD / "out" / "cb6_fits.csv")[["t", "lead", "q", "p"]].rename(columns={"p": "C-B6-R"})
    W0 = F.pivot_table(index=["t", "lead", "q", "province"], columns="name", values="p").reset_index()
    W0 = W0.merge(R6, on=["t", "lead", "q"], how="left").merge(L[["province", "q", "y"]], on=["province", "q"], how="inner")
    W0 = W0[W0["q"] >= Q0]
    arms = ["C-B6P", "C-B6P-noE", "C-B6-R", "PERSIST", "LOGIT"]
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; province-quarter (Eq. 3), 2021-Q1..2026-Q3",
           "checks": json.loads((OUT / "cb6p_checks.json").read_text(encoding="utf-8")), "leads": {}, "algorithm3": {}}
    fam = {}
    for k in LEADS:
        W = W0[W0["lead"] == k].dropna(subset=arms)
        Lk = {a: metrics(W["y"], W[a]) for a in arms}
        if k <= 2:
            for b in ("C-B6P-noE", "C-B6-R", "PERSIST", "LOGIT"):
                fam[(k, b)] = paired(W, "C-B6P", b)
            s = F[(F["name"] == "C-B6P") & (F["lead"] == k) & (F["q"] >= Q0)]
            grp = pd.DataFrame({g: sum(s[f"shap_{c}"].fillna(0) for c in cs).abs() for g, cs in GROUPS.items()})
            sh = grp.div(grp.sum(axis=1).replace(0, np.nan), axis=0) * 100
            Lk["C-B6P_shap_share_pct_mean"] = {g: float(sh[g].mean()) for g in GROUPS}
            Lk["calls_differing_vs_C-B6P-noE"] = int(((W["C-B6P"] >= .5) != (W["C-B6P-noE"] >= .5)).sum())
            Lk["provinces_with_different_call_per_quarter"] = int(
                W.assign(c=W["C-B6P"] >= .5).groupby("q")["c"].nunique().gt(1).sum())
        res["leads"][str(k)] = Lk
    hp = holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_8"] = [{"lead": k, "comparator": b, **v, "p_holm": hp[(k, b)],
                             "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for a in arms:
        mx = 0
        for k in LEADS:
            if res["leads"][str(k)][a]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][a] = mx
    m1, m2 = res["leads"]["1"]["C-B6P"], res["leads"]["2"]["C-B6P"]
    sig = {(f["lead"], f["comparator"]): f["significant"] for f in res["holm_family_8"]}
    res["acceptance"] = {
        "acc_f1_ge_0.75_both_leads": all(m["accuracy"] >= .75 and m["f1"] >= .75 for m in (m1, m2)),
        "auc_ge_0.80_lead1": bool(m1["auc"] is not None and m1["auc"] >= .80),
        "beats_PERSIST_LOGIT_C-B6-R_both_leads": all(sig[(k, b)] for k in (1, 2) for b in ("PERSIST", "LOGIT", "C-B6-R")),
        "leakage": res["checks"]["D1_leakage_unchanged"]}
    res["acceptance"]["passes"] = all(res["acceptance"].values())
    (OUT / "cb6p_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("THR", round(res["checks"]["THR"], 3), "labels", res["checks"]["province_labels"], "HIGH share",
          round(res["checks"]["label_high_share"], 3))
    for k in ("1", "2"):
        for a in arms:
            m = res["leads"][k][a]
            print(f"L{k} {a:10s} n {m['n']} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} "
                  f"R {m['recall']:.3f} F1 {m['f1']:.3f} AUC {m['auc'] if m['auc'] is None else round(m['auc'], 3)} "
                  f"Brier {m['brier']:.4f}")
        print("   SHAP %:", {g: round(v, 1) for g, v in res["leads"][k]["C-B6P_shap_share_pct_mean"].items()})
        print("   calls changed by E1/E2:", res["leads"][k]["calls_differing_vs_C-B6P-noE"],
              "| quarters where provinces differ:", res["leads"][k]["provinces_with_different_call_per_quarter"])
    for f in res["holm_family_8"]:
        print(f"   L{f['lead']} C-B6P vs {f['comparator']:9s} dBrier {f['diff']:+.4f} p {f['p_one_sided']:.3f} "
              f"Holm {f['p_holm']:.3f} sig {f['significant']}")
    print("Algorithm 3:", res["algorithm3"])
    print("Acceptance:", res["acceptance"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
