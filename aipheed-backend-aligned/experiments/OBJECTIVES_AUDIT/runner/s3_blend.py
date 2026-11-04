"""S3 (S3_PREREGISTRATION.md, hash checked): 0.5 S1 + 0.5 combined logistic, scored as Phase C.

    python s3_blend.py   # -> ../out/s3_results.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
PREREG = HERE / "S3_PREREGISTRATION.md"
OUT = HERE / "out"
sys.path.insert(0, str(EXP / "NEW_MODEL" / "ALLBASE" / "runner"))
import phase_c as PC  # noqa: E402

V, H, R, A = PC.V, PC.H, PC.R, PC.A


def check() -> str:
    b = PREREG.read_bytes()
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "S3 pre-registration changed"
    return h


def main():
    pre = check()
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    s1 = pd.read_csv(OUT / "s1_fits.csv")
    s1 = s1[(s1["name"] == "S1") & s1["lead"].isin([1, 2])][["t", "lead", "q", "p"]]
    lg = pd.read_csv(EXP / "NEW_MODEL" / "ALLBASE" / "out" / "fits.csv")
    lg = lg[lg["name"] == "LOGIT_regen"][["t", "lead", "p"]]
    S3 = s1.merge(lg, on=["t", "lead"], suffixes=("_s1", "_lg"))
    S3["p"] = 0.5 * S3["p_s1"] + 0.5 * S3["p_lg"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(PC.N.LEADS_FILE)
    CBF = pd.read_csv(PC.N.OUT / "forecasts.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      CBF[CBF["name"] == "C-b"][["name", "t", "lead", "q", "p"]],
                      s1.assign(name="S1"), S3[["t", "lead", "q", "p"]].assign(name="S3")], ignore_index=True)
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; 16th historical attempt", "leads": {}}
    fam = {}
    for k in (1, 2):
        W = R.frame(comp, k, lab_bl)
        g = W.dropna(subset=["C-b", "S1", "S3"])
        Lk = {n: PC._summ(g, n) for n in ("C-b", "S1", "S3")}
        for n in ("C-b", "S1", "S3"):
            th = [set(x) for x in __import__("numpy").array_split(sorted(g["q"].unique()), 3)]
            Lk[n]["thirds"] = [PC._acc(g[g["q"].isin(t)], n) for t in th]
        Lk["S3_vs_C-b"] = {**PC._paired(g, "S3", "C-b"), "calls_differing": int(((g["S3"] >= .5) != (g["C-b"] >= .5)).sum())}
        era = W[W["t"] >= V.NEWS_ERA]
        for b in PC.COMPS:
            fam[(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, "S3", b)
        res["leads"][str(k)] = Lk
    hp = R.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_14"] = [{"lead": k, "comparator": b, **v, "p_holm_14": hp[(k, b)],
                              "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    Ls = res["leads"]
    acc = {k: Ls[k]["S3"]["metrics"]["accuracy"] for k in ("1", "2")}
    mrlt = 2 if acc["1"] >= .75 and acc["2"] >= .75 else 1 if acc["1"] >= .75 else 0
    res["gates"] = {"G1": all(f["significant"] for f in res["holm_family_14"]),
                    "G2": all(Ls[k]["S3_vs_C-b"]["diff"] < 0 and Ls[k]["S3_vs_C-b"]["p_one_sided"] < .10
                              and acc[k] >= Ls[k]["C-b"]["metrics"]["accuracy"] for k in ("1", "2")),
                    "G3": all(not Ls[k]["S3"]["failed"] for k in ("1", "2")), "G4_mrlt": mrlt,
                    "G5": all(Ls[k]["S3"]["rules"]["R7"]["pass"] for k in ("1", "2")),
                    "AUC_ge_0.80_both": all((Ls[k]["S3"]["metrics"]["auc"] or 0) >= .80 for k in ("1", "2"))}
    res["gates"]["adoption"] = res["gates"]["G2"] and mrlt >= 2
    (OUT / "s3_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for n in ("C-b", "S1", "S3"):
            m = Ls[k][n]["metrics"]
            print(f"L{k} {n:4s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {Ls[k][n]['failed']} "
                  f"thirds {[round(x, 3) for x in Ls[k][n]['thirds']]}")
        v = Ls[k]["S3_vs_C-b"]
        print(f"   S3 vs C-b diff {v['diff']:+.4f} p {v['p_one_sided']:.3f} calls changed {v['calls_differing']}")
    print("significant vs baselines:", sum(f["significant"] for f in res["holm_family_14"]), "of 14")
    print("Gates:", res["gates"])


if __name__ == "__main__":
    main()
