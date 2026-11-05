"""FI-FOCUS Part A (../PREREGISTRATION_FI.md): regional fits NP / PO / HO with C-B6's procedure, scored on MEASURED
food insecurity (SWS BL hunger > 11.3%) against FULL (= C-B6E stored fits).

    python fi_regional.py fit
    python fi_regional.py score
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
PLAN = HERE / "PREREGISTRATION_FI.md"
OUT = HERE / "out"
sys.path.insert(0, str(AUD / "runner"))
import cb6_model as CB  # noqa: E402

PC, N, V, H, R, A = CB.PC, CB.N, CB.V, CB.H, CB.R, CB.A
HUNGER = ["h_last", "h_change", "h_mean4", "true_h", "pi_H4L"]
PRICE = ["R_food_yoy", "R_head_yoy", "R_rice_yoy", "R_food_mom"] + H.WORLD
NONPRICE = HUNGER + ["ONI_last", "ONI_max12", "tc_mean", "R_C3", "R_C4", "ST1", "ST2", "E1", "E2", "z_N1R"]
ARMS = {"NP": NONPRICE + ["lead"], "PO": PRICE + ["lead"], "HO": HUNGER + ["lead"]}


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.startswith(b"PLAN-SHA256: ") and last.split()[1].decode() == h, "FI pre-registration changed"
    return h


def _init():
    CB._init()
    N._G["T"] = N._G["T"].merge(pd.read_csv(AUD / "out" / "ce_features.csv"), on="t", how="left") \
        if "E2" not in N._G["T"] else N._G["T"]


def fit():
    pre = check()
    with Pool(8, initializer=_init) as pool:
        F = pd.concat(pool.map(CB._origin, [(t, n, c) for n, c in ARMS.items() for t in V.ORIGINS]), ignore_index=True)
    F.to_csv(OUT / "fi_regional_fits.csv", index=False)
    print({"prereg_sha256": pre, "rows": len(F), "arms": F["name"].value_counts().to_dict()})


def score():
    pre = check()
    d = H.load()
    lab_bl = V.area_labels(d)
    lab_bl = lab_bl[lab_bl["area"] == "BL"]
    L = pd.read_csv(N.LEADS_FILE)
    E = pd.read_csv(AUD / "FIXES_2026-11-04" / "out" / "cb6e_fits.csv").assign(name="FULL")
    F = pd.read_csv(OUT / "fi_regional_fits.csv")
    comp = pd.concat([L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      E[["name", "t", "lead", "q", "p"]], F[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    arms = ["FULL", "NP", "PO", "HO"]
    res = {"prereg_sha256": pre, "outcome": "measured SWS BL hunger > 11.3%", "leads": {}, "algorithm3": {}}
    for k in PC.TEST_LEADS:
        W = R.frame(comp, k, lab_bl)
        Lk = {n: {"accuracy": PC._acc(W.dropna(subset=[n]), n)} for n in arms}
        if k <= 2:
            g = W.dropna(subset=arms)
            for n in arms:
                Lk[n].update(PC._summ(g, n))
            Lk["n_quarters"] = int(g["q"].nunique())
            Lk["paired"] = {f"{a}_vs_{b}": PC._paired(g, a, b) for a, b in
                            (("FULL", "PO"), ("FULL", "NP"), ("NP", "HO"), ("FULL", "HO"))}
            s = E[(E["lead"] == k) & E["q"].isin(g["q"])]
            grp = {"hunger": HUNGER, "price": PRICE, "non_price_other": [c for c in NONPRICE if c not in HUNGER]}
            ab = pd.DataFrame({x: sum(s[f"shap_{c}"].abs().fillna(0) for c in cs if f"shap_{c}" in s) for x, cs in grp.items()})
            sh = ab.div(ab.sum(axis=1).replace(0, np.nan), axis=0) * 100
            Lk["FULL_shap_share_pct"] = {x: float(sh[x].mean()) for x in grp}
        res["leads"][str(k)] = Lk
    for n in arms:
        mx = 0
        for k in PC.TEST_LEADS:
            if res["leads"][str(k)][n]["accuracy"] >= .75 and mx == k - 1:
                mx = k
        res["algorithm3"][n] = mx
    P = {k: res["leads"][k]["paired"] for k in ("1", "2")}
    ok = lambda key: all(P[k][key]["diff"] < 0 and P[k][key]["p_one_sided"] < .10 for k in ("1", "2"))  # noqa: E731
    res["decisions"] = {"A1_nonprice_improve_FI (FULL<PO)": ok("FULL_vs_PO"), "A2_prices_add (FULL<NP)": ok("FULL_vs_NP"),
                        "A3_other_drivers_add_beyond_hunger (NP<HO)": ok("NP_vs_HO")}
    (OUT / "fi_regional_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k in ("1", "2"):
        print(f"--- Lead {k} ({res['leads'][k]['n_quarters']} quarters, measured hunger)")
        for n in arms:
            m = res["leads"][k][n]["metrics"]
            print(f"{n:5s} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} R {m['recall']:.3f} "
                  f"F1 {m['f1']:.3f} AUC {m['auc']:.3f} Brier {m['brier']:.4f} failed {res['leads'][k][n]['failed']}")
        for x, v in res["leads"][k]["paired"].items():
            print(f"   {x}: dBrier {v['diff']:+.4f} p {v['p_one_sided']:.3f}")
        print("   FULL SHAP share %:", {x: round(v, 1) for x, v in res["leads"][k]["FULL_shap_share_pct"].items()})
    print("Algorithm 3:", res["algorithm3"])
    print("Decisions:", res["decisions"])


if __name__ == "__main__":
    {"fit": fit, "score": score}[sys.argv[1]]()
