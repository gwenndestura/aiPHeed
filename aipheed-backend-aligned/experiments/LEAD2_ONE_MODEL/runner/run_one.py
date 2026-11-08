"""LEAD2_ONE_MODEL runner (PROTOCOL_ONE_MODEL.md).

    python run_one.py audit    # 6-origin future-perturbation audit of S0-S3 (must pass before scoring)
    python run_one.py score    # S0-S3 on every lead, selection, success criteria I1-I6, reliability, blocks
    python run_one.py replay   # historical replay of the selected candidate at 3 origins
    python run_one.py news     # selected candidate without news, and 20 shuffled-news refits
"""
from __future__ import annotations

import dataclasses
import json
import sys
import time

import one_lib as O

X, A2, A3, A4 = O.X, O.A4.A2, O.A3, O.A4
RL = A4.RL
U, C, FM, B, E, L, np, pd = O.U, O.C, O.FM, O.B, O.E, O.L, O.np, O.pd
OUT = O.OUT
OUT.mkdir(exist_ok=True)
L2OUT = O.EXP / "LEAD2_OPTIMIZATION" / "out"
CANDS = list(O.CANDS)


def _check():
    want = (O.HERE / "PROTOCOL_SHA256.txt").read_text().strip()
    assert FM.sha256(O.ONE / "PROTOCOL_ONE_MODEL.md") == want, "protocol changed after freezing"


def _all(S, t, d=None, cands=CANDS):
    return pd.concat([O.forecast(S, t, c, d).set_index(["t", "lead", "province_code", "target_q"]) for c in cands],
                     axis=1).reset_index()


# ================================================================================================ audit
def phase_audit():
    _check()
    U.setup()
    sys.path.insert(0, str(C.HERE))
    import run_ch1 as RC
    K = RL._K()
    rng = np.random.default_rng(O.SEED)
    d, x = E.data()
    o_rounds, o_gkg = C.FM.rounds.__wrapped__, C.NF.gkg.__wrapped__
    w0, rice0, cpi0 = U.pinksheet(), X.rice_cpi(), A3.region_cpi()

    def run(t, dd, w, rice, cpi):
        S = O.build(K, dd, x, t, w, cpi, rice)
        f = _all(S, t, dd)
        return f[[c for c in f.columns if c.endswith(("_p", "_tau", "_pc"))]].round(10)

    def clear():
        RC._clear()
        U._rounds.cache_clear()
        E._CACHE.clear()

    res = []
    for q in ("2023-Q2", "2023-Q4", "2024-Q2", "2024-Q4", "2025-Q3", "2026-Q2"):
        t = L.qi(q)
        clear()
        base = run(t, d, w0, rice0, cpi0)
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
        rp = rice0.copy()
        rp[rp.index > m0] = rng.uniform(80, 200, int((rp.index > m0).sum()))
        cp = cpi0.copy()
        cp.loc[cp.index > m0] = rng.uniform(-20, 40, size=cp.loc[cp.index > m0].shape)
        C.FM.rounds = lambda dataset="primary", _p=r0: _p if dataset == "primary" else o_rounds(dataset)
        C.FM.rounds.cache_clear = lambda: None
        C.NF.gkg = lambda _g=g0: _g
        C.NF.gkg.cache_clear = lambda: None
        clear()
        try:
            pert = run(t, dp, wp, rp, cp)
        finally:
            C.FM.rounds = C.FM.functools.lru_cache(maxsize=2)(o_rounds)
            C.NF.gkg = C.FM.functools.lru_cache(maxsize=1)(o_gkg)
            clear()
        res.append({"origin": q, "values": int(base.notna().sum().sum()), "identical": bool(base.equals(pert))})
        print(res[-1], flush=True)
    ok = all(r["identical"] and r["values"] for r in res)
    FM.write_json(OUT / "leakage_audit.json", {"passed": ok, "candidates": CANDS, "origins": res})
    assert ok


# ================================================================================================ score
def _brier(p, y):
    return float(np.mean((np.clip(np.asarray(p, float), 0, 1) - np.asarray(y, float)) ** 2))


def _cls(g, col, tau=None):
    y = g["y"].astype(int).to_numpy()
    th = g[tau].to_numpy(float) if tau else 0.5
    yh = (g[col].to_numpy(float) >= th).astype(int)
    tp, fp = int(((yh == 1) & (y == 1)).sum()), int(((yh == 1) & (y == 0)).sum())
    fn, tn = int(((yh == 0) & (y == 1)).sum()), int(((yh == 0) & (y == 0)).sum())
    rec, spec = tp / max(tp + fn, 1), tn / max(tn + fp, 1)
    return {"acc": (tp + tn) / len(y), "bal": (rec + spec) / 2, "precision": tp / (tp + fp) if tp + fp else None,
            "recall": rec, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "far": fp / max(fp + tn, 1)}


def report(D, col, tau=None) -> dict:
    leads, mrl = {}, None
    for k, g in D.groupby("lead"):
        g2 = g.assign(_pp=g[col]) if tau is None else g.assign(_pp=np.where(g[col] >= g[tau], 0.5 + 1e-9, 0.0))
        dec = RL.lead_report(g2, "_pp" if tau else col)
        if tau is not None:          # keep the probability metrics of the probability itself
            m = RL.lead_report(g, col)["metrics"]
            dec["metrics"].update({"auc": m["auc"], "brier": m["brier"]})
        dec["surge_block"] = A2.block(g[g["q"].isin(A2.SURGE)], "_pp" if tau else col) if tau is None else \
            A2.block(g2[g2["q"].isin(A2.SURGE)], "_pp")
        lb = A2.block((g2 if tau else g)[g["q"].isin(A2.LATER)], "_pp" if tau else col)
        dec["later_block"], dec["later_check"] = lb, A2.later_check(lb)
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
    return {"max_promising_lead": mrl, "max_r1_r7_lead": r17, "leads": leads}


def success(D, col, tau=None) -> dict:
    g2, g1 = D[D["lead"] == 2], D[D["lead"] == 1]
    c, b = _cls(g2, col, tau), _cls(g2, "P0H4_p3")
    y2 = g2["y"].astype(int).to_numpy()
    th = g2[tau].to_numpy(float) if tau else 0.5
    new = g2[(g2[col].to_numpy(float) >= th) & (g2["P0H4_p3"] < .5) & (g2["y"] == 1)]
    c1 = _cls(g1, col, tau)
    y1 = g1["y"].astype(int).to_numpy()
    t1 = FM.boot_diff(g1, (g1[col] - y1) ** 2, (g1["P0H4_p3"] - y1) ** 2)
    crit = {"I1_recall_ge_8_of_17": c["tp"] >= 8,
            "I2_precision_ge_0.50_far_le_0.15": (c["precision"] or 0) >= 0.50 and c["far"] <= 0.15,
            "I3_bal_ge_0.685": c["bal"] >= 0.685,
            "I4_brier_le_0.204": _brier(g2[col], y2) <= 0.204,
            "I5_new_detections_in_ge_2_quarters": new["q"].nunique() >= 2,
            "I6_lead1_acc_ge_0.75_and_brier_not_worse": c1["acc"] >= 0.75 and not (t1["diff"] > 0 and (1 - t1["p_less"]) < 0.10)}
    return {"lead2": c, "lead2_brier": _brier(g2[col], y2), "p0h4_lead2": b, "new_detections": int(len(new)),
            "new_detection_quarters": sorted(L.qs(int(q)) for q in new["q"].unique()), "lead1": c1,
            "lead1_brier_vs_p0h4": t1, "criteria": crit, "improvement": all(crit.values())}


def phase_score():
    _check()
    assert json.loads((OUT / "leakage_audit.json").read_text())["passed"], "run the audit first"
    U.setup()
    K = RL._K()
    t0 = time.time()
    S = O.build(K)
    fr = []
    for t in RL._origins():
        fr.append(_all(S, t))
        print("origin", L.qs(t), round(time.time() - t0), "s", flush=True)
    P = pd.concat(fr, ignore_index=True).drop(columns=["target_q"])
    D = pd.read_csv(L2OUT / "predictions_addendum3.csv", dtype={"province_code": str})
    n0 = len(D)
    D = D.merge(P, on=["t", "lead", "province_code"], how="left")
    assert len(D) == n0 and D[[f"{c}_p" for c in CANDS]].notna().all().all(), "rows differ from the baseline rows"
    D.to_csv(OUT / "predictions.csv", index=False, lineterminator="\n", float_format="%.6g")
    dev = D[D["q"] <= U.DEV_LAST]
    sel = {}
    for c in CANDS:
        d2, d1 = dev[dev["lead"] == 2], dev[dev["lead"] == 1]
        sel[c] = {"dev_lead2_bal": _cls(d2, f"{c}_p")["bal"], "dev_lead2_brier": _brier(d2[f"{c}_p"], d2["y"]),
                  "dev_lead1_acc": _cls(d1, f"{c}_p")["acc"]}
        sel[c]["admissible"] = sel[c]["dev_lead2_brier"] <= 0.2546 and sel[c]["dev_lead1_acc"] >= 0.75
    adm = [c for c in CANDS if sel[c]["admissible"]]
    chosen = None
    if adm:
        chosen = adm[0]
        for c in adm[1:]:
            a, b = sel[c], sel[chosen]
            if a["dev_lead2_bal"] > b["dev_lead2_bal"] + 0.005 or (
                    abs(a["dev_lead2_bal"] - b["dev_lead2_bal"]) <= 0.005 and a["dev_lead2_brier"] < b["dev_lead2_brier"]):
                chosen = c
    res = {"protocol_sha256": FM.sha256(O.ONE / "PROTOCOL_ONE_MODEL.md"), "selection": {"dev": sel, "chosen": chosen},
           "candidates": {}}
    if chosen:
        d2 = dev[dev["lead"] == 2]
        res["selection"]["platt_dev_lead2_brier"] = _brier(d2[f"{chosen}_pc"], d2["y"])
        res["selection"]["platt_applied"] = res["selection"]["platt_dev_lead2_brier"] < sel[chosen]["dev_lead2_brier"]
    variants = {c: (f"{c}_p", None) for c in CANDS}
    if chosen:
        variants[f"{chosen}-tau"] = (f"{chosen}_p", f"{chosen}_tau")
        variants[f"{chosen}-platt"] = (f"{chosen}_pc", None)
    for name, (col, tau) in variants.items():
        rep = report(D, col, tau)
        rep["success_vs_p0h4"] = success(D, col, tau)
        res["candidates"][name] = rep
        l2, s = rep["leads"][2], rep["success_vs_p0h4"]
        print(f"{name:10s} L1 acc {rep['leads'][1]['metrics']['accuracy']:.3f} ({rep['leads'][1]['verdict'][:4]}) | "
              f"L2 acc {l2['metrics']['accuracy']:.3f} bal {l2['metrics']['balanced_accuracy']:.3f} "
              f"TP {s['lead2']['tp']} FP {s['lead2']['fp']} FN {s['lead2']['fn']} AUC {l2['metrics']['auc']:.2f} "
              f"Brier {s['lead2_brier']:.3f} | new {s['new_detections']} in {s['new_detection_quarters']} | "
              f"fail R {[c for c, v in l2['criteria'].items() if not v]} | I {[c[:2] for c, v in s['criteria'].items() if not v]} "
              f"| maxrel {rep['max_r1_r7_lead']} | dev {sel.get(name, {})}", flush=True)
    for name, col in (("P0H4 (served)", "P0H4_p3"), ("UNI-FINAL", "UNI_p")):
        rep = report(D, col)
        res["candidates"][name] = rep
        print(f"{name:10s} L1 acc {rep['leads'][1]['metrics']['accuracy']:.3f} | L2 acc "
              f"{rep['leads'][2]['metrics']['accuracy']:.3f} recall {rep['leads'][2]['metrics']['recall']:.2f} | maxrel "
              f"{rep['max_r1_r7_lead']}", flush=True)
    FM.write_json(OUT / "results.json", res)
    print("chosen", chosen)


# ================================================================================================ replay / news
def _chosen():
    """The selected candidate, or (diagnostic, labelled in the output file) the one named on the command line."""
    if len(sys.argv) > 2:
        return sys.argv[2]
    return json.loads((OUT / "results.json").read_text())["selection"]["chosen"]


def phase_replay():
    U.setup()
    K = RL._K()
    cand = _chosen()
    D = pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str})
    d, x = E.data()
    out = []
    for q in ("2023-Q4", "2024-Q4", "2026-Q1"):
        t = L.qi(q)
        S = O.build(K, d, x, t)
        assert S["t"].max() == t
        f = O.forecast(S, t, cand, d)
        m = f.merge(D[D["t"] == t][["lead", "province_code", f"{cand}_p"]], on=["lead", "province_code"],
                    suffixes=("_replay", ""))
        out.append({"origin": q, "rows_compared": int(len(m)),
                    "max_abs_diff": float((m[f"{cand}_p_replay"] - m[f"{cand}_p"]).abs().max())})
        print(out[-1], flush=True)
    FM.write_json(OUT / f"historical_replay_{cand}.json", {"identical": all(o["max_abs_diff"] < 1e-5 for o in out),
                                                           "candidate": cand, "selected_by_protocol": len(sys.argv) <= 2,
                                                           "origins": out})


def phase_news(n: int = 20):
    U.setup()
    K = RL._K()
    cand = _chosen()
    S0 = O.build(K)
    D = pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str})
    news = list(U.NEWS_COLS)
    base_cols = O.cols(cand)

    def run(S, use_cols):
        O.cols = lambda c, _u=use_cols: _u
        try:
            fr = [O.forecast(S, t, cand) for t in RL._origins()]
        finally:
            O.cols = lambda c: O.A4.cols() + (O.DYN if O.CANDS[c]["dyn"] else [])
        A = pd.concat(fr)[["t", "lead", "province_code", f"{cand}_p"]].merge(D[["t", "lead", "province_code", "y", "q"]],
                                                                              on=["t", "lead", "province_code"])
        return A

    def stats(A):
        out = {}
        for k, g in A.groupby("lead"):
            if k <= 3:
                c = _cls(g, f"{cand}_p")
                out[int(k)] = {"brier": _brier(g[f"{cand}_p"], g["y"]), "acc": c["acc"], "tp": c["tp"], "fp": c["fp"]}
        return out
    real = {int(k): {"brier": _brier(g[f"{cand}_p"], g["y"]), "acc": _cls(g, f"{cand}_p")["acc"],
                     "tp": _cls(g, f"{cand}_p")["tp"], "fp": _cls(g, f"{cand}_p")["fp"]}
            for k, g in D.groupby("lead") if k <= 3}
    A = run(S0, [c for c in base_cols if c not in news])
    no_news = stats(A)
    tests = {}
    for k, g in A.groupby("lead"):
        if k <= 3:
            gg = g.merge(D[["t", "lead", "province_code", f"{cand}_p"]], on=["t", "lead", "province_code"],
                         suffixes=("_nn", ""))
            y = gg["y"].astype(int).to_numpy()
            tests[int(k)] = FM.boot_diff(gg, (gg[f"{cand}_p"] - y) ** 2, (gg[f"{cand}_p_nn"] - y) ** 2)
    print("no-news", no_news, "real", real, flush=True)
    rng = np.random.default_rng(2030)
    ts = sorted(S0["t"].unique())
    shuf = []
    for i in range(n):
        mp = dict(zip(ts, rng.permutation(ts)))
        src = S0.set_index(["province_code", "t", "lead"])[news]
        S = S0.copy()
        S[news] = src.reindex(list(zip(S["province_code"], S["t"].map(mp), S["lead"]))).to_numpy()
        shuf.append(stats(run(S, base_cols)))
        print("shuffle", i, {k: round(v["brier"], 4) for k, v in shuf[-1].items()}, flush=True)
    FM.write_json(OUT / f"news_{cand}.json", {
        "candidate": cand, "selected_by_protocol": len(sys.argv) <= 2, "real": real, "no_news": no_news, "real_vs_no_news_brier": tests,
        "holm": FM.holm({k: v["p_two"] for k, v in tests.items()}),
        "shuffles": shuf, "perm_p": {k: float(np.mean([s[k]["brier"] <= real[k]["brier"] for s in shuf])) for k in real},
        "shuffle_mean_brier": {k: float(np.mean([s[k]["brier"] for s in shuf])) for k in real},
        "news_coverage_lead2_rows": float(S0[S0["lead"] == 2]["N1"].notna().mean())})


if __name__ == "__main__":
    {"audit": phase_audit, "score": phase_score, "replay": phase_replay, "news": phase_news}[sys.argv[1]]()
