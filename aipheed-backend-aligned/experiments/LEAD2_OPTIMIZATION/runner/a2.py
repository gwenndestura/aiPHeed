"""Addendum 2 (ADDENDUM_2_CONTROLLED_COMPARISON.md): candidates D (P7) and E (P8), calibration of the adopted
candidate, research threshold, later-block check, verdicts. All candidates on identical rows.

    python a2.py audit   # leakage audit of P7, P8 and the calibration path (P4c, P8c)
    python a2.py score
"""
from __future__ import annotations

import json
import sys

import l2_lib as X
import run_l2 as RL

U, C, FM, B, E, L, np, pd = X.U, X.C, X.FM, X.B, X.E, X.L, X.np, X.pd
OUT = X.OUT
ADOPTABLE = ["P0H0", "P4H0", "P6H0", "P7H0", "P8H0"]
SURGE = [L.qi(q) for q in ("2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4")]
LATER = U.CONFIRM


def _check():
    RL._check()
    RL._check_a1()
    want = (X.HERE / "ADDENDUM_2_SHA256.txt").read_text().strip()
    assert FM.sha256(X.L2 / "ADDENDUM_2_CONTROLLED_COMPARISON.md") == want, "addendum 2 changed after freezing"


def phase_audit():
    _check()
    RL.phase_audit(("P7", "P8", "P4c", "P8c"), "leakage_audit_addendum2.json")


def _brier(p, y):
    return float(np.mean((np.clip(np.asarray(p, float), 0, 1) - np.asarray(y, float)) ** 2))


def price_metrics(g: pd.DataFrame, col: str) -> dict:
    from sklearn.metrics import roc_auc_score
    y, p = g["price"].astype(int).to_numpy(), g[col].to_numpy(float)
    return {"n": int(len(g)), "price_high": int(y.sum()), "acc": float(((p >= .5).astype(int) == y).mean()),
            "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else None, "brier": _brier(p, y)}


def block(g: pd.DataFrame, col: str, tau: float = 0.5) -> dict:
    if not len(g):
        return {}
    y = g["y"].astype(int).to_numpy()
    yh = (g[col].to_numpy(float) >= tau).astype(int)
    tp, fn = int(((yh == 1) & (y == 1)).sum()), int(((yh == 0) & (y == 1)).sum())
    fp = int(((yh == 1) & (y == 0)).sum())
    return {"rows": int(len(g)), "quarters": int(g["q"].nunique()), "high": int(y.sum()), "tp": tp, "fn": fn,
            "fp": fp, "acc": float((yh == y).mean()), "always_low": float((y == 0).mean()),
            "recall": tp / (tp + fn) if tp + fn else None, "precision": tp / (tp + fp) if tp + fp else None,
            "persist_si_acc": float(((g["PERSIST-SI_p"] >= .5).astype(int) == y).mean())}


def later_check(b: dict) -> bool:
    if not b:
        return False
    rec_ok = b["high"] < 5 or (b["recall"] is not None and b["recall"] >= 0.60)
    return b["acc"] >= 0.75 and rec_ok and b["acc"] > b["always_low"]


def choose_tau(dev: pd.DataFrame, col: str) -> float:
    best, bb = 0.5, -1.0
    y = dev["y"].astype(int).to_numpy()
    for tau in np.round(np.arange(0.50, 0.199, -0.05), 2):
        yh = (dev[col].to_numpy(float) >= tau).astype(int)
        rec = ((yh == 1) & (y == 1)).sum() / max((y == 1).sum(), 1)
        spec = ((yh == 0) & (y == 0)).sum() / max((y == 0).sum(), 1)
        if (rec + spec) / 2 > bb + 1e-12:
            best, bb = float(tau), (rec + spec) / 2
    return best


def phase_score():
    _check()
    for f in ("leakage_audit.json", "leakage_audit_addendum1.json", "leakage_audit_addendum2.json"):
        assert json.loads((OUT / f).read_text())["passed"], f
    U.setup()
    K = RL._K()
    S = X.add_fe(U.stack(K))
    origins = RL._origins()
    fr = [f for f in (X.forecast_origin(S, t, ("P7", "P8"), True) for t in origins) if f is not None]
    P = pd.concat(fr, ignore_index=True)[["t", "lead", "province_code", "P7_price", "P7_cfg", "P8_price", "P8_cfg"]]
    D = pd.read_csv(OUT / "predictions_addendum1.csv", dtype={"province_code": str})
    n0 = len(D)
    D = D.merge(P, on=["t", "lead", "province_code"], how="left")
    assert len(D) == n0 and D[["P7_price", "P8_price"]].notna().all().all(), "rows differ between candidates"
    for a in ("P7", "P8"):
        D[f"{a}H0_p"] = D["H1"] * D[f"{a}_price"]
        D[f"{a}H2_p"] = D["pi_H2"] * D[f"{a}_price"]
    dev2 = D[(D["q"] <= U.DEV_LAST) & (D["lead"] == 2)]
    sel = {a: _brier(dev2[f"{a}_p"], dev2["y"]) for a in ADOPTABLE}
    best = ADOPTABLE[0]
    for a in ADOPTABLE[1:]:
        if sel[a] < sel[best] - 0.0005:
            best = a
    print("dev Lead-2 Brier", {a: round(v, 4) for a, v in sel.items()}, "-> adopted", best, flush=True)
    # F1: calibration of the adopted price arm
    arm = best[:2]
    fr = [f for f in (X.forecast_origin(S, t, (arm + "c",), True) for t in origins) if f is not None]
    Pc = pd.concat(fr, ignore_index=True)[["t", "lead", "province_code", f"{arm}c_price", f"{arm}c_cfg"]]
    D = D.merge(Pc, on=["t", "lead", "province_code"], how="left")
    D[f"{arm}cH0_p"] = D["H1"] * D[f"{arm}c_price"]
    dev2 = D[(D["q"] <= U.DEV_LAST) & (D["lead"] == 2)]
    cal_b = _brier(dev2[f"{arm}cH0_p"], dev2["y"])
    final = f"{arm}cH0" if cal_b < sel[best] else best
    print("calibrated dev Brier", round(cal_b, 4), "-> final", final, flush=True)
    D.to_csv(OUT / "predictions_addendum2.csv", index=False, lineterminator="\n", float_format="%.6g")
    cands = {"A_P0H0": "P0H0", "B_P5H0_A1only": "P5H0", "C_P4H0": "P4H0", "C_P6H0": "P6H0", "D_P7H0": "P7H0",
             "E_P8H0": "P8H0", "F1_calibrated": f"{arm}cH0",
             "sampleb_P0H2": "P0H2", "sampleb_P4H2": "P4H2", "sampleb_P6H2": "P6H2", "sampleb_P7H2": "P7H2",
             "sampleb_P8H2": "P8H2"}
    res = {"addendum2_sha256": FM.sha256(X.L2 / "ADDENDUM_2_CONTROLLED_COMPARISON.md"),
           "rows_identical": True, "n_rows": int(len(D)),
           "selection": {"dev_lead2_brier": sel, "adopted_before_calibration": best,
                         "calibrated_dev_lead2_brier": cal_b, "final": final}, "candidates": {}}
    for name, col in cands.items():
        leads, mrl = {}, None
        pc = col[:3] if col[2] == "c" else col[:2]
        for k, g in D.groupby("lead"):
            dec = RL.lead_report(g, f"{col}_p")
            dec["price_condition"] = price_metrics(g, f"{pc}_price")
            dec["surge_block"] = block(g[g["q"].isin(SURGE)], f"{col}_p")
            lb = block(g[g["q"].isin(LATER)], f"{col}_p")
            dec["later_block"], dec["later_check"] = lb, later_check(lb)
            tau = choose_tau(g[g["q"] <= U.DEV_LAST], f"{col}_p")
            dec["research_threshold"] = {"tau": tau, "all": block(g, f"{col}_p", tau),
                                         "later_block": block(g[g["q"].isin(LATER)], f"{col}_p", tau)}
            dec["verdict"] = "promising_not_yet_verified" if dec["reliable"] and dec["later_check"] else "not_reliable"
            leads[int(k)] = dec
        for k in sorted(leads):
            if leads[k]["verdict"] == "promising_not_yet_verified":
                mrl = k
            else:
                break
        r17 = 0
        for k in sorted(leads):
            if leads[k]["reliable"]:
                r17 = k
            else:
                break
        res["candidates"][name] = {"column": col, "adoptable": col in ADOPTABLE or col == f"{arm}cH0",
                                   "sample": "b" if col.endswith("H2") else "a", "max_promising_lead": mrl,
                                   "max_r1_r7_lead": r17, "leads": leads}
        l2 = leads[2]
        m = l2["metrics"]
        print(f"{name:16s} L1 acc {leads[1]['metrics']['accuracy']:.3f} ({leads[1]['verdict'][:4]}) | L2 acc "
              f"{m['accuracy']:.3f} bal {m['balanced_accuracy']:.3f} P {m['precision']:.2f} R {m['recall']:.2f} "
              f"AUC {m['auc']:.2f} Brier {m['brier']:.3f} FN {l2['confusion']['fn']} | priceAUC "
              f"{l2['price_condition']['auc']:.2f} | surge {l2['surge_block']['tp']}/{l2['surge_block']['high']} "
              f"later {l2['later_block']['tp']}/{l2['later_block']['high']} acc {l2['later_block']['acc']:.2f} | "
              f"fail {[c for c, v in l2['criteria'].items() if not v]} | maxprom {mrl}", flush=True)
    g1 = D[D["lead"] == 1]
    y1 = g1["y"].astype(int).to_numpy()
    t1 = FM.boot_diff(g1, (g1["UNI_p"] - y1) ** 2, (g1[f"{final}_p"] - y1) ** 2)
    fname = next(n for n, c in cands.items() if c == final)
    F = res["candidates"][fname]
    res["serve_rule"] = {"reliable_lead1": F["leads"][1]["reliable"], "max_reliable_ge_1": F["max_r1_r7_lead"] >= 1,
                         "lead1_not_worse_than_uni": not (t1["diff"] < 0 and t1["p_less"] < 0.10),
                         "uni_minus_final_lead1_brier": t1}
    res["serve_rule"]["serve"] = all(v for v in res["serve_rule"].values() if isinstance(v, bool))
    FM.write_json(OUT / "results_addendum2.json", res)
    print("final", final, "| serve", res["serve_rule"]["serve"], t1)


if __name__ == "__main__":
    {"audit": phase_audit, "score": phase_score}[sys.argv[1]]()
