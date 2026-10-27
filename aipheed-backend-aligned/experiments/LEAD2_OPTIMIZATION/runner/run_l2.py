"""LEAD2_OPTIMIZATION runner (PROTOCOL_LEAD2.md).

    python run_l2.py audit    # leakage audit at 6 origins; must pass before scoring
    python run_l2.py score    # every arm, every lead; frozen selection; R1-R7 per lead; sample b separately
    python run_l2.py audit_a1 # Addendum 1: leakage audit of P4-P6
    python run_l2.py score_a1 # Addendum 1: P4-P6 scored, frozen selection among P0H0, P4H0, P6H0
"""
from __future__ import annotations

import dataclasses
import json
import sys
import time

import l2_lib as X

U, C, FM, B, E, L, np, pd = X.U, X.C, X.FM, X.B, X.E, X.L, X.np, X.pd
OUT = X.OUT
OUT.mkdir(exist_ok=True)
PRIMARY = ["P0H0", "P1H0", "P2H0", "P3H0", "P0H1", "P1H1", "P2H1", "P3H1"]
PRICE = ("P0", "P1", "P2", "P3")


def _check():
    want = (X.HERE / "PROTOCOL_SHA256.txt").read_text().strip()
    assert FM.sha256(X.L2 / "PROTOCOL_LEAD2.md") == want, "protocol changed after freezing"


def _K() -> int:
    return int(json.loads((U.OUT / "testability_unified.json").read_text())["K"])


def _origins() -> list[int]:
    return [L.qi(q) for q in json.loads((U.OUT / "testability_unified.json").read_text())["eligible_origins"]]


# ================================================================================================ leakage audit
def phase_audit(arms=PRICE, fname="leakage_audit.json"):
    _check()
    U.setup()
    sys.path.insert(0, str(C.HERE))
    import run_ch1 as RC
    K = _K()
    rng = np.random.default_rng(X.SEED)
    d, x = E.data()
    o_rounds, o_gkg = C.FM.rounds.__wrapped__, C.NF.gkg.__wrapped__
    w0, r0_rice = U.pinksheet(), X.rice_cpi()

    def forecast(t, dd, w, rice):
        S = X.add_fe(U.stack(K, dd, x, t, w), dd, rice)
        f = X.forecast_origin(S, t, arms, True, dd)
        a = {} if f is None else {(r["province_code"], int(r["lead"]), c): round(float(r[c]), 10)
                                  for _, r in f.iterrows() for c in [f"{p}_price" for p in arms] + ["H1"]}
        h = {(k, s): round(X.ar_hunger(t, k, s)[0], 10) for k in range(1, K + 1) for s in ("a", "b")}
        return a, h

    def set_rounds(pr):
        C.FM.rounds = (lambda dataset="primary", _p=pr: _p if dataset == "primary" else o_rounds(dataset)) \
            if pr is not None else C.FM.functools.lru_cache(maxsize=2)(o_rounds)
        if not hasattr(C.FM.rounds, "cache_clear"):
            C.FM.rounds.cache_clear = lambda: None

    def set_gkg(pg):
        C.NF.gkg = (lambda _g=pg: _g) if pg is not None else C.FM.functools.lru_cache(maxsize=1)(o_gkg)
        if not hasattr(C.NF.gkg, "cache_clear"):
            C.NF.gkg.cache_clear = lambda: None

    def clear():
        RC._clear()
        U._rounds.cache_clear()
        E._CACHE.clear()

    res = []
    for q in ("2023-Q2", "2023-Q4", "2024-Q2", "2024-Q4", "2025-Q3", "2026-Q2"):
        t = L.qi(q)
        clear()
        base = forecast(t, d, w0, r0_rice)
        iss, m0 = E.issue(t), L.m0_of(t)
        r0 = o_rounds("primary").copy()
        fut = r0["published"] >= iss
        r0.loc[fut, "H"] = rng.uniform(0, 50, int(fut.sum()))
        yo, ix = d.yoy.copy(), d.idx.copy()
        yo.loc[yo["ym"] > m0, "yoy"] = rng.uniform(-10, 20, int((yo["ym"] > m0).sum()))
        ix.loc[ix["ym"] > m0, "index"] = rng.uniform(80, 160, int((ix["ym"] > m0).sum()))
        dp = dataclasses.replace(d, yoy=yo, idx=ix)
        g0 = o_gkg().copy()
        gf = g0["published"] >= pd.Timestamp(iss)
        for c in C.NF.CATS + ["anticipatory", "food_event"]:
            g0.loc[gf, c] = rng.permutation(g0.loc[gf, c].to_numpy())
        wp = w0.copy()
        fm = wp.index > m0
        num = [c for c in wp.columns if c != "month"]
        wp.loc[fm, num] = wp.loc[fm, num] * rng.uniform(0.5, 2.0, size=(int(fm.sum()), len(num)))
        rp = r0_rice.copy()
        rp[rp.index > m0] = rng.uniform(80, 200, int((rp.index > m0).sum()))
        set_rounds(r0)
        set_gkg(g0)
        clear()
        try:
            pert = forecast(t, dp, wp, rp)
        finally:
            set_rounds(None)
            set_gkg(None)
            clear()
        same = base == pert
        diff = [k for k in base[0] if base[0][k] != pert[0].get(k)][:5] + \
               [k for k in base[1] if base[1][k] != pert[1].get(k) and not (np.isnan(base[1][k]) and np.isnan(pert[1][k]))][:5]
        res.append({"origin": q, "n_price_values": len(base[0]), "identical": bool(same or not diff),
                    "first_differences": [str(k) for k in diff]})
        print(res[-1], flush=True)
    ok = all(r["identical"] and r["n_price_values"] for r in res)
    FM.write_json(OUT / fname, {"passed": ok, "arms": list(arms), "origins": res})
    assert ok, "leakage audit failed"


# ================================================================================================ score
def _brier(p, y):
    return float(np.mean((np.clip(np.asarray(p, float), 0, 1) - np.asarray(y, float)) ** 2))


def build_predictions() -> pd.DataFrame:
    U.setup()
    K = _K()
    t0 = time.time()
    S = X.add_fe(U.stack(K))
    print("stack", len(S), round(time.time() - t0), "s", flush=True)
    fr = []
    for t in _origins():
        f = X.forecast_origin(S, t, PRICE, True)
        if f is not None:
            fr.append(f)
        print("origin", L.qs(t), "done", round(time.time() - t0), "s", flush=True)
    P = pd.concat(fr, ignore_index=True).rename(columns={"target_q": "q"})
    obs = C.labels()
    obs = obs[obs["q"] <= E.LAST_OUTCOME]
    D = P.merge(obs[["province_code", "q", "y", "price", "hunger", "H"]], on=["province_code", "q"])
    D = D[D["H1"].notna()]
    D = U.baselines(D)
    D = X.hunger_terms(D)
    uni = pd.read_csv(U.OUT / "predictions.csv", dtype={"province_code": str})[["t", "lead", "province_code", "UNI_p"]]
    D = D.merge(uni, on=["t", "lead", "province_code"], how="left")
    for p in PRICE:
        D[f"{p}H0_p"] = D["H1"] * D[f"{p}_price"]
        D[f"{p}H1_p"] = D["pi_H1"] * D[f"{p}_price"]
        D[f"{p}H2_p"] = D["pi_H2"] * D[f"{p}_price"]
    return D


def lead_report(G: pd.DataFrame, col: str) -> dict:
    dec = C.decide(G.assign(CH1_p=G[col]))
    y = G["y"].astype(int).to_numpy()
    p = G[col].to_numpy(float)
    yh = (p >= 0.5).astype(int)
    from sklearn.metrics import average_precision_score
    dec["confusion"] = {"tp": int(((yh == 1) & (y == 1)).sum()), "fp": int(((yh == 1) & (y == 0)).sum()),
                        "fn": int(((yh == 0) & (y == 1)).sum()), "tn": int(((yh == 0) & (y == 0)).sum())}
    dec["average_precision"] = float(average_precision_score(y, p)) if len(set(y)) == 2 else None
    dec["false_negative_rate"] = 1 - dec["metrics"]["recall"]
    per_q = {}
    for q, g in G.groupby("q"):
        yy, pp = g["y"].astype(int).to_numpy(), (g[col] >= .5).astype(int).to_numpy()
        per_q[L.qs(int(q))] = {"high": int(yy.sum()), "pred_high": int(pp.sum()), "correct": int((yy == pp).sum()),
                               "n": int(len(g))}
    dec["per_quarter"] = per_q
    hq = C.bl_quarters()
    rising = G[[hq.get(q, np.nan) > hq.get(q - 1, np.nan) for q in G["q"]]]
    falling = G[[hq.get(q, np.nan) < hq.get(q - 1, np.nan) for q in G["q"]]]
    dec["rising_acc"] = float(((rising[col] >= .5).astype(int) == rising["y"]).mean()) if len(rising) else None
    dec["falling_acc"] = float(((falling[col] >= .5).astype(int) == falling["y"]).mean()) if len(falling) else None
    dec["rising_always_low"] = float((rising["y"] == 0).mean()) if len(rising) else None
    return dec


def phase_score():
    _check()
    assert json.loads((OUT / "leakage_audit.json").read_text())["passed"], "run the audit first"
    D = build_predictions()
    D.to_csv(OUT / "predictions.csv", index=False, lineterminator="\n", float_format="%.6g")
    dev = D[D["q"] <= U.DEV_LAST]
    sel = {a: _brier(dev[dev["lead"] == 2][f"{a}_p"], dev[dev["lead"] == 2]["y"]) for a in PRIMARY}
    best = PRIMARY[0]
    for a in PRIMARY[1:]:
        if sel[a] < sel[best] - 0.0005:
            best = a
    res = {"protocol_sha256": FM.sha256(X.L2 / "PROTOCOL_LEAD2.md"),
           "selection": {"dev_lead2_brier": sel, "adopted": best,
                         "dev_lead_1_4_brier": {a: float(np.mean([_brier(g[f"{a}_p"], g["y"])
                                                                 for _, g in dev[dev["lead"] <= 4].groupby("lead")]))
                                                for a in PRIMARY + ["P0H2"]}},
           "arms": {}}
    sb = ["P0H2", f"{best[:2]}H2"]
    for a in dict.fromkeys(PRIMARY + sb):
        leads = {}
        for k, g in D.groupby("lead"):
            leads[int(k)] = lead_report(g, f"{a}_p")
        mrl = None
        for k in sorted(leads):
            if leads[k]["reliable"]:
                mrl = k
            else:
                break
        res["arms"][a] = {"sample": "b (pre-2021 hunger history; sensitivity only)" if a.endswith("H2") else "a",
                          "max_reliable_lead": mrl,
                          "testable_horizon_R1": max(k for k, v in leads.items() if v["criteria"]["R1"]),
                          "leads": leads}
        l2 = leads[2]
        print(f"{a}: maxrel {mrl} | L1 acc {leads[1]['metrics']['accuracy']:.3f} rel {leads[1]['reliable']} | "
              f"L2 acc {l2['metrics']['accuracy']:.3f} bal {l2['metrics']['balanced_accuracy']:.3f} "
              f"P {l2['metrics']['precision']:.2f} R {l2['metrics']['recall']:.2f} AUC {l2['metrics']['auc']:.2f} "
              f"Brier {l2['metrics']['brier']:.3f} fail {[c for c, v in l2['criteria'].items() if not v]} | "
              f"dev L2 Brier {sel.get(a, float('nan')):.4f}", flush=True)
    # multiplicity: each primary arm vs P0H0 at Lead 2 (Brier, one-sided), Holm over 7
    g2 = D[D["lead"] == 2]
    y2 = g2["y"].astype(int).to_numpy()
    tests = {a: FM.boot_diff(g2, (g2[f"{a}_p"] - y2) ** 2, (g2["P0H0_p"] - y2) ** 2) for a in PRIMARY[1:]}
    hp = FM.holm({a: v["p_less"] for a, v in tests.items()})
    res["lead2_vs_P0H0"] = {a: {**v, "holm_p": hp[a]} for a, v in tests.items()}
    # serve rule vs UNI-FINAL at Lead 1
    g1 = D[D["lead"] == 1]
    y1 = g1["y"].astype(int).to_numpy()
    t1 = FM.boot_diff(g1, (g1["UNI_p"] - y1) ** 2, (g1[f"{best}_p"] - y1) ** 2)
    A = res["arms"][best]
    res["serve_rule"] = {"reliable_lead1": A["leads"][1]["reliable"], "max_reliable_ge_1": (A["max_reliable_lead"] or 0) >= 1,
                         "lead1_not_worse_than_uni": not (t1["diff"] < 0 and t1["p_less"] < 0.10),
                         "uni_minus_adopted_lead1_brier": t1}
    res["serve_rule"]["serve"] = all(v for k, v in res["serve_rule"].items() if isinstance(v, bool))
    FM.write_json(OUT / "results.json", res)
    print("adopted", best, "| serve", res["serve_rule"]["serve"], "| max reliable", A["max_reliable_lead"])


# ================================================================================================ Addendum 1
A1_PRICE = ("P4", "P5", "P6")
A1_PRIMARY = ["P0H0", "P4H0", "P6H0"]


def _check_a1():
    want = (X.HERE / "ADDENDUM_1_SHA256.txt").read_text().strip()
    assert FM.sha256(X.L2 / "ADDENDUM_1_STRUCTURAL_PRIOR.md") == want, "addendum changed after freezing"


def phase_audit_a1():
    _check_a1()
    phase_audit(A1_PRICE, "leakage_audit_addendum1.json")


def phase_score_a1():
    _check()
    _check_a1()
    assert json.loads((OUT / "leakage_audit_addendum1.json").read_text())["passed"], "run audit_a1 first"
    U.setup()
    K = _K()
    S = X.add_fe(U.stack(K))
    fr = [f for f in (X.forecast_origin(S, t, A1_PRICE, True) for t in _origins()) if f is not None]
    P = pd.concat(fr, ignore_index=True)[["t", "lead", "province_code"] + [f"{a}_{s}" for a in A1_PRICE
                                                                           for s in ("price", "cfg")]]
    D = pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str}).merge(P, on=["t", "lead", "province_code"])
    for a in A1_PRICE:
        D[f"{a}H0_p"] = D["H1"] * D[f"{a}_price"]
        D[f"{a}H2_p"] = D["pi_H2"] * D[f"{a}_price"]
    D.to_csv(OUT / "predictions_addendum1.csv", index=False, lineterminator="\n", float_format="%.6g")
    dev = D[(D["q"] <= U.DEV_LAST) & (D["lead"] == 2)]
    sel = {a: _brier(dev[f"{a}_p"], dev["y"]) for a in A1_PRIMARY}
    best = A1_PRIMARY[0]
    for a in A1_PRIMARY[1:]:
        if sel[a] < sel[best] - 0.0005:
            best = a
    res = {"addendum_sha256": FM.sha256(X.L2 / "ADDENDUM_1_STRUCTURAL_PRIOR.md"),
           "selection": {"dev_lead2_brier": sel, "adopted": best}, "arms": {}}
    for a in ["P0H0", "P4H0", "P6H0", "P5H0", "P4H2", "P6H2", "P5H2"]:
        leads = {int(k): lead_report(g, f"{a}_p") for k, g in D.groupby("lead")}
        mrl = None
        for k in sorted(leads):
            if leads[k]["reliable"]:
                mrl = k
            else:
                break
        res["arms"][a] = {"sample": "b (sensitivity only)" if a.endswith("H2") else "a",
                          "adoptable": a in A1_PRIMARY, "max_reliable_lead": mrl,
                          "testable_horizon_R1": max(k for k, v in leads.items() if v["criteria"]["R1"]),
                          "leads": leads}
        for k in (1, 2, 3):
            m = leads[k]["metrics"]
            print(f"{a} L{k}: acc {m['accuracy']:.3f} bal {m['balanced_accuracy']:.3f} P {m['precision']:.2f} "
                  f"R {m['recall']:.2f} AUC {m['auc']:.2f} Brier {m['brier']:.3f} "
                  f"fail {[c for c, v in leads[k]['criteria'].items() if not v]}", flush=True)
        print(f"   {a} max reliable {mrl} | dev L2 Brier {sel.get(a, float('nan')):.4f}", flush=True)
    g1 = D[D["lead"] == 1]
    y1 = g1["y"].astype(int).to_numpy()
    t1 = FM.boot_diff(g1, (g1["UNI_p"] - y1) ** 2, (g1[f"{best}_p"] - y1) ** 2)
    A = res["arms"][best]
    res["serve_rule"] = {"reliable_lead1": A["leads"][1]["reliable"],
                         "max_reliable_ge_1": (A["max_reliable_lead"] or 0) >= 1,
                         "lead1_not_worse_than_uni": not (t1["diff"] < 0 and t1["p_less"] < 0.10),
                         "uni_minus_adopted_lead1_brier": t1}
    res["serve_rule"]["serve"] = all(v for k, v in res["serve_rule"].items() if isinstance(v, bool))
    g2 = D[D["lead"] == 2]
    y2 = g2["y"].astype(int).to_numpy()
    res["lead2_vs_P0H0"] = {a: FM.boot_diff(g2, (g2[f"{a}_p"] - y2) ** 2, (g2["P0H0_p"] - y2) ** 2)
                            for a in ["P4H0", "P6H0", "P5H0"]}
    FM.write_json(OUT / "results_addendum1.json", res)
    print("adopted", best, "| serve", res["serve_rule"]["serve"], "| max reliable", A["max_reliable_lead"])


if __name__ == "__main__":
    {"audit": phase_audit, "score": phase_score, "audit_a1": phase_audit_a1,
     "score_a1": phase_score_a1}[sys.argv[1]]()
