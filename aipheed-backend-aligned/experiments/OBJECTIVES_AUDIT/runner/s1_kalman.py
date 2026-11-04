"""S1 (S1_PREREGISTRATION.md, hash checked): C-b + a local-level Kalman estimate of true BL hunger.

    python s1_kalman.py features   # kf_level, kf_pi (two implementations, leakage check) -> ../out/s1_features.csv
    python s1_kalman.py fit        # C-b reproduction + S1 walk-forward (leads 1-8) -> ../out/s1_fits.csv
    python s1_kalman.py score      # metrics, R1-R7, Algorithm 3, 14-test Holm family, gates -> ../out/s1_results.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
import math
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
PREREG = HERE / "S1_PREREGISTRATION.md"
OUT = HERE / "out"
sys.path.insert(0, str(EXP / "NEW_MODEL" / "ALLBASE" / "runner"))
import phase_c as PC  # noqa: E402

N, V, H, R, A = PC.N, PC.V, PC.H, PC.R, PC.A
KF = ["kf_level", "kf_pi"]
S1 = PC.CB[:-1] + KF + PC.CB[-1:]
SE1, LINE = PC.SE1, PC.LINE
GRID = list(np.exp(np.linspace(math.log(0.1), math.log(50), 40)))
P0 = 100.0


def check() -> str:
    b = PREREG.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "S1 pre-registration changed"
    return h


def readings(d, t: int) -> tuple[list[int], dict, dict]:
    r = d.sws[(d.sws["area"] == "BL") & (d.sws["published"] < H.issue(t))]
    g = r.groupby("q")["H"].agg(["mean", "size"])
    return [int(q) for q in g.index], {int(q): float(v) for q, v in g["mean"].items()}, \
        {int(q): int(n) for q, n in g["size"].items()}


def filter_a(qs, y, n, sw2):
    """Implementation A: explicit predict / update loop; returns (m, P, loglik) at the last quarter."""
    m, P, ll = y[qs[0]], P0, 0.0
    for q in range(qs[0], qs[-1] + 1):
        if q > qs[0]:
            P += sw2
        if q in y:
            Rq = SE1 ** 2 / n[q]
            S = P + Rq
            v = y[q] - m
            ll += -0.5 * (math.log(2 * math.pi * S) + v * v / S)
            K = P / S
            m, P = m + K * v, (1 - K) * P
    return m, P, ll


def filter_b(qs, y, n, sw2):
    """Implementation B (independent check): information form with gaps counted from consecutive readings."""
    m, P, ll, prev = y[qs[0]], P0, 0.0, qs[0]
    for q in qs:
        P = P + (q - prev) * sw2
        prev = q
        Rq = SE1 ** 2 / n[q]
        S = P + Rq
        ll -= 0.5 * (np.log(2 * np.pi) + np.log(S) + (y[q] - m) ** 2 / S)
        Pn = 1.0 / (1.0 / P + 1.0 / Rq)
        m = Pn * (m / P + y[q] / Rq)
        P = Pn
    return float(m), float(P), float(ll)


def feats(d, t: int, f=filter_a) -> list[dict]:
    qs, y, n = readings(d, t)
    if len(qs) < 2:
        return [{"t": t, "lead": k, "kf_level": np.nan, "kf_pi": np.nan} for k in range(1, H.KMAX + 1)]
    fits = [(f(qs, y, n, s), s) for s in GRID]
    (m, P, _), sw2 = max(fits, key=lambda x: (round(x[0][2], 9), -x[1]))
    return [{"t": t, "lead": k, "kf_level": m,
             "kf_pi": float(norm.cdf((m - LINE) / math.sqrt(P + ((t + k) - qs[-1]) * sw2))), "sigma_w2": sw2}
            for k in range(1, H.KMAX + 1)]


_G: dict = {}


def _finit():
    _G["d"] = H.load()


def _feat(t):
    d = _G["d"]
    a, b = feats(d, t), feats(d, t, filter_b)
    same = all((np.isnan(x[c]) and np.isnan(z[c])) or abs(x[c] - z[c]) <= 1e-9 for x, z in zip(a, b) for c in KF)
    stable = all(all((np.isnan(x[c]) and np.isnan(z[c])) or x[c] == z[c] for x, z in zip(a, feats(H.perturb(d, t, PC.SEED + r), t))
                     for c in KF) for r in range(PC.REPS))
    return a, same, stable


def features():
    pre = check()
    with Pool(8, initializer=_finit) as pool:
        res = pool.map(_feat, V.ORIGINS)
    F = pd.DataFrame([r for a, _, _ in res for r in a])
    OUT.mkdir(parents=True, exist_ok=True)
    F.to_csv(OUT / "s1_features.csv", index=False)
    chk = {"prereg_sha256": pre, "two_implementations_agree": all(x[1] for x in res),
           "leakage_unchanged": all(x[2] for x in res), "reps": PC.REPS,
           "sigma_w2_median": float(F["sigma_w2"].median()), "non_missing_origins": int(F[F["lead"] == 1]["kf_level"].notna().sum())}
    (OUT / "s1_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    print(json.dumps(chk, indent=1))
    if not (chk["two_implementations_agree"] and chk["leakage_unchanged"]):
        raise SystemExit("S1 feature pre-check failed")


def _init():
    N._init()
    N._G["T"] = N._G["T"].merge(pd.read_csv(OUT / "s1_features.csv")[["t", "lead"] + KF], on=["t", "lead"], how="left")


def fit():
    pre = check()
    c = json.loads((OUT / "s1_checks.json").read_text(encoding="utf-8"))
    assert c["two_implementations_agree"] and c["leakage_unchanged"]
    jobs = [(t, n, cc) for t in V.ORIGINS for n, cc in (("C-b_repro", PC.CB), ("S1", S1))]
    with Pool(8, initializer=_init) as pool:
        F = pd.concat(pool.map(PC._origin, jobs), ignore_index=True)
    F.to_csv(OUT / "s1_fits.csv", index=False)
    old = pd.read_csv(N.OUT / "forecasts.csv")
    old = old[old["name"] == "C-b"][["t", "lead", "p"]]
    m = old.merge(F[F["name"] == "C-b_repro"][["t", "lead", "p"]], on=["t", "lead"], suffixes=("_o", "_n"))
    c.update({"prereg_sha256": pre, "Cb_rows": int(len(m)), "Cb_max_abs_diff": float((m["p_o"] - m["p_n"]).abs().max())})
    c["Cb_reproduced"] = c["Cb_rows"] == len(old) and c["Cb_max_abs_diff"] <= 1e-12
    (OUT / "s1_checks.json").write_text(json.dumps(c, indent=1), encoding="utf-8")
    print(json.dumps(c, indent=1))
    if not c["Cb_reproduced"]:
        raise SystemExit("C-b not reproduced")


def score():
    pre = check()
    c = json.loads((OUT / "s1_checks.json").read_text(encoding="utf-8"))
    assert c.get("Cb_reproduced")
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    CBF = pd.read_csv(N.OUT / "forecasts.csv")
    F = pd.read_csv(OUT / "s1_fits.csv")
    T = pd.read_csv(N.IV2_OUT / "table_pooled.csv", dtype={"area": str})
    hl = T[T["area"] == "BL"][["t", "lead", "h_last"]]
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      CBF[CBF["name"] == "C-b"][["name", "t", "lead", "q", "p"]],
                      F[F["name"] == "S1"][["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; 14th historical attempt", "checks": c, "leads": {},
           "algorithm3": {}}
    fam = {}
    for k in PC.TEST_LEADS:
        W = R.frame(comp, k, lab_bl).merge(hl[hl["lead"] == k][["t", "h_last"]], on="t", how="left")
        Lk = {n: {"accuracy": PC._acc(W.dropna(subset=[n]), n)} for n in ("C-b", "S1")}
        if k <= 2:
            g = W.dropna(subset=["C-b", "S1"])
            rev = g["y"] != (g["h_last"] > LINE).astype(int)
            thirds = [set(x) for x in np.array_split(np.array(sorted(g["q"].unique())), 3)]
            for n in ("C-b", "S1"):
                x = Lk[n]
                x.update(PC._summ(g, n))
                x["reversal_recall"] = PC._acc(g[rev], n)
                x["non_reversal_accuracy"] = PC._acc(g[~rev], n)
                x["thirds"] = [PC._acc(g[g["q"].isin(th)], n) for th in thirds]
                for fn, (a, b) in (("fold_S", PC.FOLD_S), ("fold_E", PC.FOLD_E)):
                    m = g["q"].between(a, b)
                    x[fn] = {"brier": float(((g[n] - g["y"]) ** 2)[m].mean()), "accuracy": PC._acc(g[m], n)}
            Lk["S1"]["vs_C-b"] = {**PC._paired(g, "S1", "C-b"), "calls_differing": int(((g["S1"] >= .5) != (g["C-b"] >= .5)).sum())}
            era = W[W["t"] >= V.NEWS_ERA]
            for b in PC.COMPS:
                fam[(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, "S1", b)
        res["leads"][str(k)] = Lk
    hp = R.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_14"] = [{"lead": k, "comparator": b, **v, "p_holm_14": hp[(k, b)],
                              "conclusion": "significantly better" if v["diff"] < 0 and hp[(k, b)] < .05 else
                              "not significantly different" if v["diff"] < 0 else "not better"}
                             for (k, b), v in fam.items()]
    for n in ("C-b", "S1"):
        mx = 0
        for k in PC.TEST_LEADS:
            if res["leads"][str(k)][n]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][n] = {"mrlt": mx, "accuracy_by_lead": {k: res["leads"][str(k)][n]["accuracy"] for k in PC.TEST_LEADS}}
    Ls = {k: res["leads"][str(k)] for k in (1, 2)}
    g2 = all(Ls[k]["S1"]["vs_C-b"]["diff"] < 0 and Ls[k]["S1"]["vs_C-b"]["p_one_sided"] < .10
             and Ls[k]["S1"]["metrics"]["accuracy"] >= Ls[k]["C-b"]["metrics"]["accuracy"] for k in (1, 2))
    res["gates"] = {"G1_all_baselines": all(f["conclusion"] == "significantly better" for f in res["holm_family_14"]),
                    "G2_improves_Cb": g2, "G3_R1_R7": all(not Ls[k]["S1"]["failed"] for k in (1, 2)),
                    "G4_mrlt_ge_2": res["algorithm3"]["S1"]["mrlt"] >= 2,
                    "G5_R7_fixed": all(Ls[k]["S1"]["rules"]["R7"]["pass"] and Ls[k]["S1"]["metrics"]["accuracy"]
                                       >= Ls[k]["C-b"]["metrics"]["accuracy"] for k in (1, 2))}
    res["gates"]["adoption_G2_and_G4"] = res["gates"]["G2_improves_Cb"] and res["gates"]["G4_mrlt_ge_2"]
    (OUT / "s1_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for n in ("C-b", "S1"):
            x = res["leads"][k][n]
            m = x["metrics"]
            print(f"L{k} {n:4s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} ECE {m['ece_10']:.3f} "
                  f"{m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} failed {x['failed']} thirds "
                  f"{[round(a, 3) for a in x['thirds']]} rev {x['reversal_recall']:.3f}")
        v = res["leads"][k]["S1"]["vs_C-b"]
        print(f"   S1 vs C-b diff {v['diff']:+.4f} CI {[round(a, 4) for a in v['ci95']]} p {v['p_one_sided']:.3f} "
              f"calls changed {v['calls_differing']}")
    for f in res["holm_family_14"]:
        print(f"L{f['lead']} vs {f['comparator']:11s} {f['brier_candidate']:.4f} vs {f['brier_comparator']:.4f} "
              f"diff {f['diff']:+.4f} n {f['n_quarters']} p {f['p_one_sided']:.4f} Holm {f['p_holm_14']:.4f} {f['conclusion']}")
    print("Algorithm 3:", {n: v["mrlt"] for n, v in res["algorithm3"].items()})
    print("Gates:", res["gates"])


if __name__ == "__main__":
    {"features": features, "fit": fit, "score": score}[sys.argv[1]]()
