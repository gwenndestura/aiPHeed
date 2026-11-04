"""C-E (CE_PREREGISTRATION.md, hash checked): C-b + E1 (national unemployment change) + E2 (remittance decline).

    python ce_model.py features   # E2 per origin + leakage check -> ../out/ce_features.csv
    python ce_model.py fit        # C-b reproduction + C-E walk-forward with SHAP (leads 1-8) -> ../out/ce_fits.csv
    python ce_model.py score      # metrics, R1-R7, Algorithm 3, 14-test Holm family, gates, SHAP shares -> ../out/ce_results.json
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
EXP = HERE.parent
PREREG = HERE / "CE_PREREGISTRATION.md"
OUT = HERE / "out"
REMIT = EXP / "LEAD2_RELIABILITY_RESEARCH" / "y15_food_insecurity_improvement" / "data_acquired" / \
    "remittances_quarterly_usd_mn.csv"
sys.path.insert(0, str(EXP / "NEW_MODEL" / "ALLBASE" / "runner"))
import phase_c as PC  # noqa: E402

N, V, H, R, A = PC.N, PC.V, PC.H, PC.R, PC.A
CE = PC.CB[:-1] + ["E1", "E2"] + PC.CB[-1:]
SEED, REPS = 2036, 5


def check() -> str:
    b = PREREG.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "C-E pre-registration changed"
    return h


def e2_series(pt: pd.Series, origins) -> pd.Series:
    """E2(t) = -(pt(t-2) / pt(t-6) - 1) * 100; NaN when either quarter is missing. Only quarters <= t-2 are read."""
    out = {}
    for t in origins:
        a, b = pt.get(t - 2, np.nan), pt.get(t - 6, np.nan)
        out[t] = float(-(a / b - 1) * 100) if pd.notna(a) and pd.notna(b) and b != 0 else np.nan
    return pd.Series(out)


def _pt() -> pd.Series:
    r = pd.read_csv(REMIT)
    return pd.Series(r["personal_transfers"].to_numpy(float), index=r["quarter"].map(H.qi).to_numpy())


def features():
    pre = check()
    pt = _pt()
    e2 = e2_series(pt, V.ORIGINS)
    rng = np.random.default_rng(SEED)
    stable = True
    for t in V.ORIGINS:
        for _ in range(REPS):
            p = pt.copy()
            fut = p.index >= t - 1
            p[fut] = rng.uniform(1000, 10000, int(fut.sum()))
            x = e2_series(p, [t]).iloc[0]
            if not ((np.isnan(x) and np.isnan(e2[t])) or x == e2[t]):
                stable = False
    F = pd.DataFrame({"t": e2.index, "E2": e2.to_numpy()})
    OUT.mkdir(parents=True, exist_ok=True)
    F.to_csv(OUT / "ce_features.csv", index=False)
    T = pd.read_csv(N.IV2_OUT / "table_pooled.csv", dtype={"area": str})
    T = T[(T["area"] == "BL") & (T["lead"] == 1)]
    chk = {"prereg_sha256": pre, "E2_leakage_unchanged": stable, "E2_first_origin": H.qs(int(F.dropna()["t"].min())),
           "E2_non_missing_share": float(F["E2"].notna().mean()),
           "E1_first_origin": H.qs(int(T[T["E1"].notna()]["t"].min())), "E1_non_missing_share": float(T["E1"].notna().mean()),
           "remittance_file_sha256": hashlib.sha256(REMIT.read_bytes()).hexdigest()}
    (OUT / "ce_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    print(json.dumps(chk, indent=1))
    if not stable:
        raise SystemExit("E2 leakage check failed")


def _init():
    N._init()
    N._G["T"] = N._G["T"].merge(pd.read_csv(OUT / "ce_features.csv"), on="t", how="left")


def _origin(job) -> pd.DataFrame:
    t, name, cols = job
    d, S, lab = N._G["d"], N._G["T"], N._G["lab"]
    kb = V.known_labels(d, t, lab)
    kb = kb[kb["area"] == "BL"]
    clim = float(kb["y"].mean()) if len(kb) else 0.0
    src = S[S["area"] == "BL"]
    te = src[(src["t"] == t) & src["lead"].isin(PC.TEST_LEADS)].copy()
    tr = src[(src["t"] < t) & (src["q"] <= t - 1)].merge(V.known_labels(d, t, lab)[["area", "q", "y", "H"]],
                                                          on=["area", "q"], how="inner")
    trb = tr[tr["area"] == "BL"]
    te["p"], te["fallback"] = np.nan, False
    sh = None
    if H.eligible(trb):
        cfg = H.lgbm_select(tr, cols, mono=False)
        m = H.LGBM(cfg, cols, False).fit(tr)
        te["p"] = m.predict(te)
        if m.m is not None and name == "C-E":
            sh = V.shap_frame(m.m, te[cols]).add_prefix("shap_")
    else:
        te["p"], te["fallback"] = float(trb["y"].mean()) if len(trb) else clim, True
    out = te[["t", "lead", "q", "p", "fallback"]].assign(name=name).reset_index(drop=True)
    if sh is not None:
        out = pd.concat([out, sh.reset_index(drop=True)], axis=1)
    return out


def fit():
    pre = check()
    assert json.loads((OUT / "ce_checks.json").read_text(encoding="utf-8"))["E2_leakage_unchanged"]
    jobs = [(t, n, c) for t in V.ORIGINS for n, c in (("C-b_repro", PC.CB), ("C-E", CE))]
    with Pool(8, initializer=_init) as pool:
        F = pd.concat(pool.map(_origin, jobs), ignore_index=True)
    F.to_csv(OUT / "ce_fits.csv", index=False)
    old = pd.read_csv(N.OUT / "forecasts.csv")
    old = old[old["name"] == "C-b"][["t", "lead", "p"]]
    m = old.merge(F[F["name"] == "C-b_repro"][["t", "lead", "p"]], on=["t", "lead"], suffixes=("_o", "_n"))
    c = json.loads((OUT / "ce_checks.json").read_text(encoding="utf-8"))
    c.update({"prereg_sha256": pre, "Cb_rows": int(len(m)), "Cb_max_abs_diff": float((m["p_o"] - m["p_n"]).abs().max())})
    c["Cb_reproduced"] = c["Cb_rows"] == len(old) and c["Cb_max_abs_diff"] <= 1e-12
    (OUT / "ce_checks.json").write_text(json.dumps(c, indent=1), encoding="utf-8")
    print({k: c[k] for k in ("Cb_rows", "Cb_max_abs_diff", "Cb_reproduced")})
    if not c["Cb_reproduced"]:
        raise SystemExit("C-b not reproduced")


def score():
    pre = check()
    c = json.loads((OUT / "ce_checks.json").read_text(encoding="utf-8"))
    assert c.get("Cb_reproduced")
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    CBF = pd.read_csv(N.OUT / "forecasts.csv")
    F = pd.read_csv(OUT / "ce_fits.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      CBF[CBF["name"] == "C-b"][["name", "t", "lead", "q", "p"]],
                      F[F["name"] == "C-E"][["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; 17th historical attempt", "checks": c, "leads": {},
           "algorithm3": {}}
    fam = {}
    shcols = [x for x in F.columns if x.startswith("shap_")]
    for k in PC.TEST_LEADS:
        W = R.frame(comp, k, lab_bl)
        Lk = {n: {"accuracy": PC._acc(W.dropna(subset=[n]), n)} for n in ("C-b", "C-E")}
        if k <= 2:
            g = W.dropna(subset=["C-b", "C-E"])
            for n in ("C-b", "C-E"):
                Lk[n].update(PC._summ(g, n))
                th = [set(x) for x in np.array_split(np.array(sorted(g["q"].unique())), 3)]
                Lk[n]["thirds"] = [PC._acc(g[g["q"].isin(x)], n) for x in th]
            Lk["vs_C-b"] = {**PC._paired(g, "C-E", "C-b"), "calls_differing": int(((g["C-E"] >= .5) != (g["C-b"] >= .5)).sum())}
            era = W[W["t"] >= V.NEWS_ERA]
            for b in PC.COMPS:
                fam[(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, "C-E", b)
            s = F[(F["name"] == "C-E") & (F["lead"] == k) & F["q"].isin(g["q"])][shcols].abs()
            tot = s.sum(axis=1)
            Lk["shap_share_pct_mean"] = {x[5:]: float(100 * (s[x] / tot).mean()) for x in ("shap_E1", "shap_E2")}
            Lk["shap_nonzero_forecasts"] = {x[5:]: int((s[x] > 0).sum()) for x in ("shap_E1", "shap_E2")}
            Lk["n_forecasts"] = int(len(s))
        res["leads"][str(k)] = Lk
    hp = R.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_14"] = [{"lead": k, "comparator": b, **v, "p_holm_14": hp[(k, b)],
                              "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for n in ("C-b", "C-E"):
        mx = 0
        for k in PC.TEST_LEADS:
            if res["leads"][str(k)][n]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][n] = mx
    Ls = {k: res["leads"][str(k)] for k in (1, 2)}
    g2 = all(Ls[k]["vs_C-b"]["diff"] < 0 and Ls[k]["vs_C-b"]["p_one_sided"] < .10
             and Ls[k]["C-E"]["metrics"]["accuracy"] >= Ls[k]["C-b"]["metrics"]["accuracy"] for k in (1, 2))
    res["gates"] = {"G1": all(f["significant"] for f in res["holm_family_14"]), "G2": g2,
                    "G3": all(not Ls[k]["C-E"]["failed"] for k in (1, 2)), "G4": res["algorithm3"]["C-E"] >= 2,
                    "G5": all(Ls[k]["C-E"]["rules"]["R7"]["pass"] for k in (1, 2))}
    res["gates"]["adoption_G2_and_G4"] = g2 and res["gates"]["G4"]
    (OUT / "ce_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for n in ("C-b", "C-E"):
            m = res["leads"][k][n]["metrics"]
            print(f"L{k} {n:4s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {res['leads'][k][n]['failed']} "
                  f"thirds {[round(x, 3) for x in res['leads'][k][n]['thirds']]}")
        v = res["leads"][k]["vs_C-b"]
        print(f"   vs C-b diff {v['diff']:+.4f} p {v['p_one_sided']:.3f} calls changed {v['calls_differing']}; SHAP share "
              f"{ {x: round(y, 1) for x, y in res['leads'][k]['shap_share_pct_mean'].items()} } nonzero "
              f"{res['leads'][k]['shap_nonzero_forecasts']} of {res['leads'][k]['n_forecasts']}")
    print("significant:", sum(f["significant"] for f in res["holm_family_14"]), "of 14; Algorithm 3:", res["algorithm3"])
    print("Gates:", res["gates"])


if __name__ == "__main__":
    {"features": features, "fit": fit, "score": score}[sys.argv[1]]()
