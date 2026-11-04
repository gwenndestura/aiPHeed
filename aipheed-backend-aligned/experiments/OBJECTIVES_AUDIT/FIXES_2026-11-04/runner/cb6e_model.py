"""C-B6E (PLAN_CB6E.md, hash checked): C-B6 + E1 (national unemployment change) + E2 (remittance decline), as C-E.

    python cb6e_model.py fit     # C-B6 replication gate, walk-forward C-B6E -> ../out/cb6e_fits.csv
    python cb6e_model.py score   # metrics, R1-R7, Algorithm 3, Holm family with PERSIST-P, serving rule -> ../out/cb6e_results.json
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
PLAN = HERE / "PLAN_CB6E.md"
OUT = HERE / "out"
sys.path.insert(0, str(AUD / "runner"))
import cb6_model as CB  # noqa: E402

PC, N, V, H, R, A = CB.PC, CB.N, CB.V, CB.H, CB.R, CB.A
BASE = PC.CB + CB.ST
EX = ["E1", "E2"]
NAME, REF = "C-B6E", "C-B6"


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "PLAN_CB6E changed"
    assert json.loads((AUD / "out" / "ce_checks.json").read_text(encoding="utf-8"))["E2_leakage_unchanged"]
    return h


def fit():
    pre = check()
    chk = {"prereg_sha256": pre}
    with Pool(8, initializer=CB._init) as pool:
        rep = pd.concat(pool.map(CB._origin, [(t, "C-B6-replica", BASE) for t in V.ORIGINS]), ignore_index=True)
        st = pd.read_csv(AUD / "out" / "cb6_fits.csv").set_index(["t", "lead"])["p"]
        r = rep.set_index(["t", "lead"])["p"]
        chk["C-B6_replication_max_abs_diff"] = float((r - st.reindex(r.index)).abs().max())
        print(chk, flush=True)
        assert chk["C-B6_replication_max_abs_diff"] < 1e-9, "C-B6 replication differs"
        F = pd.concat(pool.map(CB._origin, [(t, NAME, BASE + EX) for t in V.ORIGINS]), ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cb6e_checks.json").write_text(json.dumps(chk, indent=1), encoding="utf-8")
    F.to_csv(OUT / "cb6e_fits.csv", index=False)
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
    F = pd.read_csv(OUT / "cb6e_fits.csv")
    comp = pd.concat([iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])][["name", "t", "lead", "q", "p"]],
                      h3[["name", "t", "lead", "q", "p"]], L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      PP[["name", "t", "lead", "q", "p"]], B6[["name", "t", "lead", "q", "p"]],
                      F[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    res = {"prereg_sha256": pre, "label": "DEVELOPMENT EVIDENCE; attempt 26 on the same 62 quarters", "leads": {},
           "algorithm3": {}}
    fam = {}
    for k in PC.TEST_LEADS:
        W = R.frame(comp, k, lab_bl)
        Lk = {n: {"accuracy": PC._acc(W.dropna(subset=[n]), n)} for n in (REF, NAME)}
        if k <= 2:
            g = W.dropna(subset=[REF, NAME])
            for n in (REF, NAME):
                Lk[n].update(PC._summ(g, n))
                th = [set(x) for x in np.array_split(np.array(sorted(g["q"].unique())), 3)]
                Lk[n]["thirds"] = [PC._acc(g[g["q"].isin(x)], n) for x in th]
            Lk["vs_C-B6"] = {**PC._paired(g, NAME, REF), "calls_differing": int(((g[NAME] >= .5) != (g[REF] >= .5)).sum())}
            era = W[W["t"] >= V.NEWS_ERA]
            for b in ["PERSIST-P" if b == "PERSIST" else b for b in PC.COMPS]:
                fam[(k, b)] = PC._paired(era if b in A.NLP_ONLY else W, NAME, b)
            s = F[(F["lead"] == k) & F["q"].isin(g["q"])]
            tot = s.filter(like="shap_").abs().sum(axis=1).replace(0, np.nan)
            Lk["shap_share_mean"] = {c: float((s[f"shap_{c}"].abs() / tot).mean()) for c in EX}
            Lk["shap_nonzero_forecasts"] = {c: int((s[f"shap_{c}"].abs() > 0).sum()) for c in EX}
        res["leads"][str(k)] = Lk
    hp = R.holm({key: v["p_one_sided"] for key, v in fam.items()})
    res["holm_family_14_persist_p"] = [{"lead": k, "comparator": b, **v, "p_holm_14": hp[(k, b)],
                                        "significant": bool(v["diff"] < 0 and hp[(k, b)] < .05)} for (k, b), v in fam.items()]
    for n in (REF, NAME):
        mx = 0
        for k in PC.TEST_LEADS:
            if res["leads"][str(k)][n]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][n] = mx
    last = F[(F["t"] == H.qi("2026-Q3")) & F["lead"].isin([1, 2])]
    lt = last.filter(like="shap_").abs().sum(axis=1).replace(0, np.nan)
    res["latest_issue_shap_share"] = {c: [float(x) for x in (last[f"shap_{c}"].abs() / lt)] for c in EX}
    L1, L2 = res["leads"]["1"], res["leads"]["2"]
    rules_ok = all(not res["leads"][k][NAME]["failed"] for k in ("1", "2"))
    acc_ok = all(res["leads"][k][NAME]["metrics"]["accuracy"] >= .75 for k in ("1", "2"))
    res["decision"] = {"R1_R7_both_leads": bool(rules_ok), "accuracy_ge_0.75_both_leads": bool(acc_ok),
                       "serve_automatically": bool(rules_ok and acc_ok),
                       "improves_lead1_p_lt_0.05": bool(L1["vs_C-B6"]["diff"] < 0 and L1["vs_C-B6"]["p_one_sided"] < .05)}
    (OUT / "cb6e_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        for n in (REF, NAME):
            m = res["leads"][k][n]["metrics"]
            print(f"L{k} {n:6s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {res['leads'][k][n]['failed']} "
                  f"thirds {[round(x, 3) for x in res['leads'][k][n]['thirds']]}")
        v = res["leads"][k]["vs_C-B6"]
        print(f"   vs C-B6 diff {v['diff']:+.4f} CI {v['ci95'][0]:+.4f}..{v['ci95'][1]:+.4f} p {v['p_one_sided']:.4f} "
              f"calls changed {v['calls_differing']}; SHAP E1/E2 {res['leads'][k]['shap_share_mean']} nonzero {res['leads'][k]['shap_nonzero_forecasts']}")
    print("Holm family (PERSIST-P): significant", sum(f["significant"] for f in res["holm_family_14_persist_p"]), "of 14")
    print("Algorithm 3:", res["algorithm3"], "latest-issue E1/E2 shares:", res["latest_issue_shap_share"])
    print("Decision:", res["decision"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
