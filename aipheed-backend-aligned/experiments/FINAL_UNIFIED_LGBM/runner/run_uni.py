"""FINAL_UNIFIED_LGBM runner (PROTOCOL_UNIFIED_LGBM.md).

    python run_uni.py testability   # before freezing: evaluable rows per lead from data availability (no model)
    python run_uni.py audit         # leakage audit (section 6), must pass before scoring
    python run_uni.py score         # variants, development selection, confirmatory evaluation, horizons, news
    python run_uni.py seal          # UNI-FINAL forecasts issued 2026-10-01 for every lead, + SHA-256
"""
from __future__ import annotations

import dataclasses
import json
import sys

import uni_lib as U

C, FM, B, E, L, np, pd = U.C, U.FM, U.B, U.E, U.L, U.np, U.pd
OUT = U.OUT
OUT.mkdir(exist_ok=True)
KMAX_SCAN = 16
sys.path.insert(0, str(U.EXP / "FINAL_VERIFICATION" / "runner"))
from horizon_rule import select_horizon  # noqa: E402


def _check():
    want = (U.HERE / "PROTOCOL_SHA256.txt").read_text().strip()
    assert FM.sha256(U.UNI / "PROTOCOL_UNIFIED_LGBM.md") == want, "protocol changed after freezing"


def _K() -> int:
    return int(json.loads((OUT / "testability_unified.json").read_text())["K"])


# ================================================================================================ testability
def phase_testability():
    U.setup()
    S = U.stack(KMAX_SCAN)
    obs = C.labels()
    labelled = set(int(q) for q in obs["q"] if q <= E.LAST_OUTCOME)
    eligible = [t for t in range(E.FIRST_ORIGIN, E.LAST_ORIGIN + 1) if B.eligible(U.train_rows(S, t))]
    per = {}
    for k in range(1, KMAX_SCAN + 1):
        qs = []
        for t in eligible:
            te = S[(S["t"] == t) & (S["lead"] == k)]
            if t + k in labelled and len(te) and not te["H1"].isna().any():
                qs.append(L.qs(t + k))
        per[k] = {"evaluable_quarters": len(qs), "rows": 5 * len(qs), "quarters": qs,
                  "R1_possible": len(qs) >= 10 and 5 * len(qs) >= 40}
        print(k, len(qs))
    K = max(k for k in per if per[k]["rows"])
    FM.write_json(OUT / "testability_unified.json", {"first_eligible_origin": L.qs(eligible[0]),
                                                     "eligible_origins": [L.qs(t) for t in eligible],
                                                     "K": K, "leads": per,
                                                     "longest_R1_lead": max(k for k in per if per[k]["R1_possible"])})
    print("first eligible origin", L.qs(eligible[0]), "K", K)


# ================================================================================================ leakage audit
def phase_audit():
    _check()
    U.setup()
    sys.path.insert(0, str(C.HERE))
    import run_ch1 as RC
    K = _K()
    rng = np.random.default_rng(U.SEED)
    d, x = E.data()
    o_rounds, o_gkg = C.FM.rounds.__wrapped__, C.NF.gkg.__wrapped__
    w0 = U.pinksheet()

    def forecast(t, dd, rounds, w):
        S = U.stack(K, dd, x, t, w)
        p = U.fit_predict(S, t, "U2", True, dd)
        Hs = U.hunger_table(K, t, rounds, dd, w)
        h = U.hg_predict(Hs, t, rounds)
        a = {} if p is None else {(r.province_code, int(r.lead)): round(float(r.pi_price * r.H1), 10)
                                  for r in p.itertuples()}
        b = {} if h is None else {int(r.lead): round(float(r.pi_h_hg), 10) for r in h.itertuples()}
        return a, b

    def set_rounds(pr):
        C.FM.rounds = (lambda dataset="primary", _p=pr: _p if dataset == "primary" else o_rounds(dataset)) \
            if pr is not None else C.FM.functools.lru_cache(maxsize=2)(o_rounds)
        if not hasattr(C.FM.rounds, "cache_clear"):
            C.FM.rounds.cache_clear = lambda: None

    def set_gkg(pg):
        C.NF.gkg = (lambda _g=pg: _g) if pg is not None else C.FM.functools.lru_cache(maxsize=1)(o_gkg)
        if not hasattr(C.NF.gkg, "cache_clear"):
            C.NF.gkg.cache_clear = lambda: None

    res = []
    for q in ("2023-Q2", "2023-Q4", "2024-Q2", "2024-Q4", "2025-Q3", "2026-Q2"):
        t = L.qi(q)
        RC._clear()
        U._rounds.cache_clear()
        base = forecast(t, d, None, w0)
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
        set_rounds(r0)
        set_gkg(g0)
        RC._clear()
        U._rounds.cache_clear()
        try:
            pert = forecast(t, dp, r0, wp)
        finally:
            set_rounds(None)
            set_gkg(None)
            RC._clear()
            U._rounds.cache_clear()
        res.append({"origin": q, "n_price": len(base[0]), "n_hg": len(base[1]), "identical": base == pert})
        print(res[-1], flush=True)
    ok = all(r["identical"] and r["n_price"] for r in res)
    FM.write_json(OUT / "leakage_audit.json", {"passed": ok, "origins": res})
    assert ok, "leakage audit failed"


# ================================================================================================ score
def _brier(p, y):
    return float(np.mean((np.clip(np.asarray(p, float), 0, 1) - np.asarray(y, float)) ** 2))


def phase_score():
    _check()
    assert json.loads((OUT / "leakage_audit.json").read_text())["passed"]
    U.setup()
    K = _K()
    S = U.stack(K)
    obs = C.labels()
    obs = obs[obs["q"] <= E.LAST_OUTCOME]
    origins = [L.qi(q) for q in json.loads((OUT / "testability_unified.json").read_text())["eligible_origins"]]
    # ---- price variants (+ no-news twins), one unified model per origin
    preds = {}
    for v in U.VARIANTS:
        for news in (True, False):
            fr = [U.fit_predict(S, t, v, news, explain=(news and v == "U2")) for t in origins]
            preds[(v, news)] = pd.concat([f for f in fr if f is not None], ignore_index=True)
            print("scored", v, "news" if news else "no-news", len(preds[(v, news)]), flush=True)
    # ---- hunger model
    Hs = U.hunger_table(K, E.LAST_ORIGIN)
    hg = pd.concat([h for h in (U.hg_predict(Hs, t) for t in origins) if h is not None], ignore_index=True)
    base = preds[("U0", True)][["t", "lead", "province_code", "target_q", "H1", "h_last"]].rename(columns={"target_q": "q"})
    D = base.merge(obs[["province_code", "q", "y", "price", "hunger", "H"]], on=["province_code", "q"])
    D = D[D["H1"].notna()]
    for (v, news), P in preds.items():
        D = D.merge(P[["t", "lead", "province_code", "pi_price"]].rename(columns={"pi_price": f"{v}{'' if news else '-GOV'}_price"}),
                    on=["t", "lead", "province_code"], how="left")
    D = D.merge(hg.rename(columns={"q": "q_hg"})[["t", "lead", "pi_h_hg"]], on=["t", "lead"], how="left")
    D = U.baselines(D)
    # ---- development selection (targets <= 2024-Q4, Leads 1-4)
    dev = D[(D["q"] <= U.DEV_LAST) & (D["lead"] <= 4)]
    sel = {}
    for v in U.VARIANTS:
        sel[v] = float(np.mean([_brier(g["H1"] * g[f"{v}_price"], g["y"]) for _, g in dev.groupby("lead")]))
    order = list(U.VARIANTS)
    best = min(order, key=lambda v: (round(sel[v], 9), order.index(v)))
    dq = dev.groupby(["t", "lead"]).first().reset_index()
    dq = dq[dq["pi_h_hg"].notna()]
    hb = {"pi_H": float(np.mean([_brier(g["H1"], g["hunger"]) for _, g in dq.groupby("lead")])),
          "HG": float(np.mean([_brier(g["pi_h_hg"], g["hunger"]) for _, g in dq.groupby("lead")]))}
    use_hg = hb["HG"] < hb["pi_H"]
    ph = np.where(D["pi_h_hg"].notna(), D["pi_h_hg"], D["H1"]) if use_hg else D["H1"].to_numpy()
    D["UNI_p"] = ph * D[f"{best}_price"]
    D["UNI-GOV_p"] = ph * D[f"{best}-GOV_price"]
    D["pi_h_used"] = ph
    # CH1 per-lead predictions where they exist (same rows)
    ch = []
    for k in range(1, 9):
        f = U.EXP / "FINAL_VERIFICATION" / "out" / f"horizon_predictions_lead{k}.csv"
        if f.exists():
            ch.append(pd.read_csv(f, dtype={"province_code": str})[["t", "lead", "province_code", "CH1_p"]])
    D = D.merge(pd.concat(ch).rename(columns={"CH1_p": "CH1-LEAD_p"}), on=["t", "lead", "province_code"], how="left")
    D.to_csv(OUT / "predictions.csv", index=False, lineterminator="\n", float_format="%.6g")
    # ---- confirmatory evaluation per lead
    res = {"protocol_sha256": FM.sha256(U.UNI / "PROTOCOL_UNIFIED_LGBM.md"), "selection": {
        "dev_brier_T43c_mean_leads_1_4": sel, "chosen_price_variant": best, "dev_brier_hunger_condition": hb,
        "hunger_model": "HG" if use_hg else "pi_H"}, "leads": {}}
    for k, g in D.groupby("lead"):
        G = g.assign(CH1_p=g["UNI_p"])
        dec = C.decide(G)
        y = G["y"].astype(int).to_numpy()
        nb = FM.boot_diff(G, (G["UNI_p"] - y) ** 2, (G["UNI-GOV_p"] - y) ** 2)
        cmp_ = G[G["CH1-LEAD_p"].notna()]
        vs_ch1 = None
        if len(cmp_):
            yc = cmp_["y"].astype(int).to_numpy()
            vs_ch1 = {"rows": int(len(cmp_)),
                      "acc_uni": float(((cmp_["UNI_p"] >= .5).astype(int) == yc).mean()),
                      "acc_ch1": float(((cmp_["CH1-LEAD_p"] >= .5).astype(int) == yc).mean()),
                      "brier": FM.boot_diff(cmp_, (cmp_["UNI_p"] - yc) ** 2, (cmp_["CH1-LEAD_p"] - yc) ** 2)}
        conf = G[G["q"].isin(U.CONFIRM)]
        qd = G.groupby("q").first()
        hq_ok = ((qd["pi_h_used"] >= .5).astype(int) == qd["hunger"])
        hp_ok = ((qd["h_last"] > U.H_LINE).astype(int) == qd["hunger"])
        dec.update(news_ablation={"acc_with": dec["metrics"]["accuracy"],
                                  "acc_without": float(((G["UNI-GOV_p"] >= .5).astype(int) == y).mean()),
                                  "brier_diff": nb},
                   vs_ch1_per_lead=vs_ch1,
                   confirmation_block={"rows": int(len(conf)),
                                       "accuracy": float(((conf["UNI_p"] >= .5).astype(int) == conf["y"]).mean())
                                       if len(conf) else None,
                                       "always_low": float((conf["y"] == 0).mean()) if len(conf) else None,
                                       "persist_si": float(((conf["PERSIST-SI_p"] >= .5).astype(int) == conf["y"]).mean())
                                       if len(conf) else None},
                   hunger_condition_quarters={"quarters": int(len(qd)), "model_correct": int(hq_ok.sum()),
                                              "latest_reading_persistence_correct": int(hp_ok.sum())})
        res["leads"][int(k)] = dec
        print(f"lead {k}: n {dec['n']} q {dec['n_quarters']} acc {dec['metrics']['accuracy']:.3f} "
              f"AL {dec['baseline_accuracy']['ALWAYS-LOW']:.3f} PSI {dec['baseline_accuracy']['PERSIST-SI']:.3f} "
              f"fail {[c for c, v in dec['criteria'].items() if not v]}", flush=True)
    hp = FM.holm({k: res["leads"][k]["news_ablation"]["brier_diff"]["p_two"] for k in res["leads"]})
    for k in res["leads"]:
        res["leads"][k]["news_ablation"]["holm_p"] = hp[k]
    res.update(select_horizon(res["leads"]))
    l1 = res["leads"].get(1, {}).get("vs_ch1_per_lead")
    res["serve_rule"] = {"max_reliable_lead_at_least_ch1": (res["max_reliable_lead"] or 0) >= 1,
                         "lead1_not_worse_than_ch1": bool(l1 and l1["brier"]["p_two"] / 2 >= 0.10
                                                          or (l1 and l1["brier"]["diff"] <= 0))}
    res["serve_rule"]["serve_uni"] = all(res["serve_rule"].values())
    # SHAP family shares of the U2 news model (diagnostic)
    P2 = preds[("U2", True)]
    sh = [c for c in P2.columns if c.startswith("shap_")]
    if sh:
        res["shap_family_share_U2"] = {}
        for k, g in P2.groupby("lead"):
            tot = sum(g[c].abs().mean() for c in sh if c != "shap_lead") or 1.0
            fam = {}
            for c in sh:
                f = U.FAMILY_OF.get(c[5:], c[5:])
                fam[f] = fam.get(f, 0.0) + float(g[c].abs().mean() / tot)
            res["shap_family_share_U2"][int(k)] = fam
    FM.write_json(OUT / "results.json", res)
    print("chosen", best, "hunger", "HG" if use_hg else "pi_H", "| max reliable", res["max_reliable_lead"],
          "testable", res["testable_horizon_R1"], "passing", res["individually_passing_leads"], res["serve_rule"])


if __name__ == "__main__":
    which = sys.argv[1]
    {"testability": phase_testability, "audit": phase_audit, "score": phase_score}[which]()
