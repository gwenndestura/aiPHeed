"""FINAL_OBJECTIVE_ACHIEVEMENT runner. One command reruns everything:

    python run_oa.py all       # verify -> data -> audit -> score -> placebo -> seal
"""
from __future__ import annotations

import json
import sys

import oa_lib as O

M, NF, np, pd = O.M, O.NF, O.np, O.pd
OUT, DATA = O.OUT, O.DATA
OUT.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)
KEYS = ["area_name", "t", "lead"]


def _check_protocol():
    want = (O.HERE / "PROTOCOL_SHA256.txt").read_text().strip()
    assert M.sha256(O.OA / "FINAL_FORECASTING_PROTOCOL.md") == want, "protocol changed after freezing"


# ================================================================================================ verify (section 6)
def phase_verify():
    _check_protocol()
    rng = np.random.default_rng(M.SEED)
    res = {"V1_test_retest": O.test_retest()}
    params = O.area_params()
    P = M.panel("primary", "primary")
    obs = O.observed_baselines(P)
    sims = {a: O.simulate(p["Q"], p["R"], p["obs_q"], rng) for a, p in params.items()}
    pooled = {}
    for h in range(1, 6):
        pooled[h] = {m: {s: float(np.mean([sims[a][h][m][s] for a in sims if h in sims[a] and m in sims[a][h]]))
                         for s in ("mean", "p05", "p95")} for m in ("bayes", "persist", "ma2")}
    cells = []
    for h, o in obs.items():
        for m in ("persist", "ma2"):
            # the pooled band is for one area; the observed rows pool 4 areas, so the band is narrowed by sqrt(4)
            mu, lo, hi = pooled[h][m]["mean"], pooled[h][m]["p05"], pooled[h][m]["p95"]
            lo4, hi4 = mu - (mu - lo) / 2, mu + (hi - mu) / 2
            cells.append({"h": h, "rule": m, "observed": o[m], "n": o["n"], "sim_mean": mu, "band_4area": [lo4, hi4],
                          "inside": bool(lo4 <= o[m] <= hi4)})
    share = float(np.mean([c["inside"] for c in cells]))
    res["V2_params"] = {a: {k: v for k, v in p.items() if k != "obs_q"} for a, p in params.items()}
    res["V2_simulated"] = {str(h): v for h, v in pooled.items()}
    res["V2_check_cells"] = cells
    res["V2_share_inside"] = share
    res["V2_ceiling_validated"] = share >= 0.8
    res["V3_null_bootstrap"] = O.null_bootstrap_check(rng)
    M.write_json(OUT / "results_verify.json", res)
    print(json.dumps({"V1": {k: res["V1_test_retest"][k] for k in ("n_pairs_with_label", "agreement",
                                                                    "implied_max_accuracy", "mean_abs_diff")},
                      "V2_share": share, "bayes": {h: round(v["bayes"]["mean"], 3) for h, v in pooled.items()},
                      "V3": res["V3_null_bootstrap"]}, indent=1))
    for c in cells:
        print(c)


# ================================================================================================ data
def phase_data():
    P = M.panel("primary", "primary")
    fam_of = {c: f for f, cs in O.FAMILY_COLS.items() for c in cs}
    rows = []
    for c in O.OA_COLS:
        f = fam_of.get(c, "H1" if c.startswith("h_") else "design")
        rows.append({"feature": c, "family": f, "family_name": M.FAMILY_NAMES.get(f, "model structure"),
                     "missing_share": round(float(P[c].isna().mean()), 3),
                     "first_origin": M.qs(int(P.loc[P[c].notna(), "t"].min())) if P[c].notna().any() else None,
                     "last_origin": M.qs(int(P.loc[P[c].notna(), "t"].max())) if P[c].notna().any() else None})
    fm = pd.DataFrame(rows)
    fm.to_csv(DATA / "feature_map.csv", index=False, lineterminator="\n")
    assert set(O.FAMILY_COLS) <= set(fm["family"]), "a family is missing"
    P.to_csv(OUT / "panel_features.csv", index=False, lineterminator="\n", float_format="%.6g")
    print(fm.to_string())


# ================================================================================================ audit (section 7)
def _snap(t):
    O.clear_caches()
    P = M.panel("primary", "primary")
    F = M.fil_forecasts(P, O.OA_COLS, "primary", origins=[t])
    return {f"{a}|{k}": round(float(z), 10) for a, k, z in zip(F["area_name"], F["lead"], F["zhat"])}


def phase_audit():
    rng = np.random.default_rng(M.SEED)
    origins = [M.qi(q) for q in ("2023-Q3", "2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q2",
                                 "2025-Q3", "2026-Q1", "2026-Q2")]
    o_rounds, o_corpus, o_gkg = M.rounds.__wrapped__, NF.corpus.__wrapped__, NF.gkg.__wrapped__
    res = []

    def patch(pr=None, pc=None, pg=None):
        M.rounds = (lambda dataset="primary", _p=pr: _p if dataset == "primary" else o_rounds(dataset)) if pr is not None \
            else M.functools.lru_cache(maxsize=2)(o_rounds)
        NF.corpus = (lambda _c=pc: _c) if pc is not None else M.functools.lru_cache(maxsize=1)(o_corpus)
        NF.gkg = (lambda _g=pg: _g) if pg is not None else M.functools.lru_cache(maxsize=1)(o_gkg)
        for f in (M.rounds, NF.corpus, NF.gkg):
            if not hasattr(f, "cache_clear"):
                f.cache_clear = lambda: None
    for t in origins:
        base = _snap(t)
        iss = M.issue(t)
        r0, c0, g0 = o_rounds("primary"), o_corpus(), o_gkg()
        pr = r0.copy()
        fut = pr["published"] >= iss
        pr.loc[fut, "H"] = rng.uniform(0, 50, int(fut.sum()))
        pc, pg = c0.copy(), g0.copy()
        for d in (pc, pg):
            f = d["published"] >= pd.Timestamp(iss)
            for c in NF.CATS + ["anticipatory", "food_event"]:
                d.loc[f, c] = rng.permutation(d.loc[f, c].to_numpy())
        patch(pr, pc, pg)
        try:
            pb = _snap(t)
        finally:
            patch()
        res.append({"origin": M.qs(t), "n": len(base), "identical": base == pb})
        print(res[-1])
    t = origins[4]
    base = _snap(t)
    pr = o_rounds("primary").copy()
    past = pr["published"] < M.issue(t)
    pr.loc[past, "H"] = rng.uniform(0, 50, int(past.sum()))
    patch(pr)
    try:
        neg = _snap(t)
    finally:
        patch()
    O.clear_caches()
    ok = all(r["identical"] and r["n"] > 0 for r in res) and neg != base
    M.write_json(OUT / "leakage_audit.json", {"passed": ok, "origins": res, "negative_control_changed": neg != base})
    assert ok, "leakage audit failed"


# ================================================================================================ score
def _decide_all(R, model="FIL"):
    return {k: M.decide(R, k, model) for k in O.LEADS}


def _surge(R, pcol, lvl):
    s = (R["y"] - R["h_last"]) > R["margin_last"]
    D = R[s]
    fa = R[(R["label"] == 0) & (R[pcol] > 0.5)]
    return {"n_events": int(s.sum()), "recall": float((D[pcol] > 0.5).mean()) if len(D) else None,
            "mean_error": float((D[lvl] - D["y"]).mean()) if len(D) else None,
            "false_alarms": int(len(fa)), "n_not_elevated": int((R["label"] == 0).sum())}


def phase_score():
    _check_protocol()
    assert json.loads((OUT / "leakage_audit.json").read_text())["passed"]
    R = M.evaluate("primary", "primary", O.OA_COLS)
    R.to_csv(OUT / "predictions_primary.csv", index=False, lineterminator="\n", float_format="%.6g")
    res = {"protocol_sha256": M.sha256(O.OA / "FINAL_FORECASTING_PROTOCOL.md"), "FIL_OA": _decide_all(R)}
    res["max_reliable_lead"] = O.max_reliable_lead(res["FIL_OA"])
    variants = {"FIL-OA-NONEWS": [c for c in O.OA_COLS if c not in O.OA_NEWS],
                "FIL-OA-NEWSONLY": M.H_COLS + O.OA_NEWS, "FIL-OA-CORPUS": O.CORPUS_COLS, "FIL-OA-H": M.H_COLS}
    V = {}
    for name, cols in variants.items():
        Rv = M.evaluate("primary", "primary", cols, shap=False)
        Rv[KEYS + ["q", "label", "y", "zhat", "FIL_p", "FIL_level"]].to_csv(OUT / f"pred_{name}.csv", index=False,
                                                                           lineterminator="\n", float_format="%.6g")
        V[name] = Rv
    O.set_asym(True)
    try:
        Ra = M.evaluate("primary", "primary", O.OA_COLS, shap=False)
    finally:
        O.set_asym(False)
    Ra[KEYS + ["q", "label", "y", "zhat", "FIL_p", "FIL_level"]].to_csv(OUT / "pred_FIL-OA-ASYM.csv", index=False,
                                                                       lineterminator="\n", float_format="%.6g")
    V["FIL-OA-ASYM"] = Ra
    res["variants"] = {n: _decide_all(Rv) for n, Rv in V.items()}
    # S1 leave-one-quarter-out of the accuracy difference FIL-OA - PERSIST
    s1 = {}
    for k in O.LEADS:
        D = R[R["lead"] == k]
        if not len(D):
            continue
        c1 = ((D["FIL_p"] > .5).astype(int) == D["label"]).astype(float)
        c0 = ((D["PERSIST_p"] > .5).astype(int) == D["label"]).astype(float)
        diffs = [float(c1[D["q"] != q].mean() - c0[D["q"] != q].mean()) for q in D["q"].unique()]
        s1[k] = {"full": float(c1.mean() - c0.mean()), "loqo_min": min(diffs), "loqo_max": max(diffs)}
    res["S1_loqo"] = s1
    # S2 surges and false alarms
    s2 = {}
    for k in O.LEADS:
        D = R[R["lead"] == k]
        if not len(D):
            continue
        A = Ra[Ra["lead"] == k]
        s2[k] = {"FIL_OA": _surge(D, "FIL_p", "FIL_level"), "PERSIST": _surge(D, "PERSIST_p", "PERSIST_level"),
                 "ASYM": _surge(A, "FIL_p", "FIL_level")}
    res["S2_surges"] = s2
    # S3 news ablation (same rows)
    nn = V["FIL-OA-NONEWS"]
    ab, ps = {}, {}
    for k in O.LEADS:
        j = R[R["lead"] == k][KEYS + ["q", "label", "FIL_p"]].merge(nn[nn["lead"] == k][KEYS + ["FIL_p"]], on=KEYS,
                                                                   suffixes=("", "_nn"))
        if not len(j):
            continue
        y = j["label"].astype(int).to_numpy()
        b = M.boot_diff(j, (j["FIL_p"] - y) ** 2, (j["FIL_p_nn"] - y) ** 2)
        ab[k] = {"n": len(j), "acc_news": float(((j["FIL_p"] > .5) == y).mean()),
                 "acc_nonews": float(((j["FIL_p_nn"] > .5) == y).mean()), "brier_diff": b,
                 "mcnemar_p": M.mcnemar(y, j["FIL_p"], j["FIL_p_nn"])}
        ps[k] = b["p_two"]
    hp = M.holm(ps)
    for k in ab:
        ab[k]["holm_p"] = hp[k]
    res["S3_news_ablation"] = ab
    # SHAP family shares
    sh = {}
    for k in O.LEADS:
        D = R[R["lead"] == k]
        if not len(D):
            continue
        tot = sum(D[f"shap_{c}"].abs().mean() for c in O.OA_COLS)
        g = {f: sum(D[f"shap_{c}"].abs().mean() for c in cs) / tot for f, cs in O.FAMILY_COLS.items()}
        g["H (hunger history)"] = sum(D[f"shap_{c}"].abs().mean() for c in M.H_COLS[:4]) / tot
        g["design (area, lead, post_break)"] = sum(D[f"shap_{c}"].abs().mean() for c in ["area", "lead", "post_break"]) / tot
        sh[k] = g
    res["shap_share"] = sh
    # periods and direction
    R2 = R.assign(period=np.where(R["q"] <= M.qi("2023-Q4"), "<=2023", np.where(R["q"] <= M.qi("2024-Q4"), "2024",
                                                                                 "2025+")),
                  direction=np.where(R["y"] > R["h_last"], "rising", "falling/flat"))
    sp = {}
    for col in ("period", "direction", "area_name"):
        for (k, v), D in R2.groupby(["lead", col]):
            y = D["label"].astype(int)
            sp[f"{col}|lead{k}|{v}"] = {"n": len(D), "FIL_OA": float(((D["FIL_p"] > .5).astype(int) == y).mean()),
                                        "PERSIST": float(((D["PERSIST_p"] > .5).astype(int) == y).mean()),
                                        "FIL_mae": float((D["FIL_level"] - D["y"]).abs().mean()),
                                        "PERSIST_mae": float((D["h_last"] - D["y"]).abs().mean())}
    res["splits"] = sp
    M.write_json(OUT / "results_primary.json", res)
    for k in O.LEADS:
        d = res["FIL_OA"][k]
        m = d["metrics"]
        print("lead", k, d["n"], d["n_quarters"], {x: round(m[x], 3) for x in ("accuracy", "balanced_accuracy",
                                                                             "precision", "recall", "auc", "brier")},
              "persist", round(d["baselines"]["PERSIST"]["accuracy"], 3), "mae", round(d["mae"], 2),
              round(d["mae_persist"], 2), [c for c, v in d["criteria"].items() if v])
    for n, dd in res["variants"].items():
        print(n, [round(dd[k]["metrics"]["accuracy"], 3) if dd[k].get("metrics") else None for k in O.LEADS])
    print("max reliable lead", res["max_reliable_lead"])
    print("S1", s1)
    print("S2", json.dumps(s2))
    print("S3", {k: (v["acc_news"], v["acc_nonews"], round(v["brier_diff"]["diff"], 4), round(v["holm_p"], 3))
                 for k, v in ab.items()})


# ================================================================================================ placebo (S3)
def phase_placebo():
    R = pd.read_csv(OUT / "predictions_primary.csv")
    P = M.panel("primary", "primary")
    rng = np.random.default_rng(M.SEED)
    origins = sorted(P["t"].unique())
    table = P.set_index(KEYS)
    sd = {t: float(M.training(P, t, "primary")["z_tr"].std()) for t in R["t"].unique()}
    real = {k: float(((R.loc[R["lead"] == k, "FIL_p"] - R.loc[R["lead"] == k, "label"]) ** 2).mean()) for k in (0, 1)}
    perm = {0: [], 1: []}
    for i in range(100):
        mp = dict(zip(origins, rng.permutation(origins)))
        mp["_table"], mp["_cols"] = table, O.OA_NEWS
        F = M.fil_forecasts(P, O.OA_COLS, "primary", news_perm=mp)
        j = R[KEYS + ["label", "ref_hat", "q"]].merge(F[KEYS + ["zhat"]], on=KEYS)
        j["p"] = M.add_sigma_prob(j, P, "zhat", "primary", sd)
        for k in (0, 1):
            D = j[j["lead"] == k]
            perm[k].append(float(((D["p"] - D["label"]) ** 2).mean()))
    out = {k: {"real_brier": real[k], "perm_mean": float(np.mean(perm[k])),
               "p_perm_le_real": float(np.mean(np.array(perm[k]) <= real[k]))} for k in (0, 1)}
    M.write_json(OUT / "results_placebo.json", out)
    print(out)


# ================================================================================================ seal
def phase_seal():
    t = M.LAST_ORIGIN
    rows = []
    R = pd.read_csv(OUT / "predictions_primary.csv")
    for name, asym in (("FIL-OA", False), ("FIL-OA-ASYM", True)):
        O.set_asym(asym)
        try:
            P = M.panel("primary", "primary")
            F = M.fil_forecasts(P, O.OA_COLS, "primary", origins=[t])
        finally:
            O.set_asym(False)
        te = P[(P["t"] == t) & (P["lead"] >= 1)].merge(F, on=KEYS)
        Rs = R if name == "FIL-OA" else pd.read_csv(OUT / "pred_FIL-OA-ASYM.csv").merge(
            R[KEYS + ["ref_hat"]], on=KEYS)
        for r in te.itertuples():
            prev = Rs[(Rs["lead"] == r.lead) & (Rs["q"] < t)]
            s = float(np.sqrt(np.mean((prev["y"] - prev["ref_hat"] - prev["zhat"]) ** 2)))
            rows.append({"model": name, "area": r.area_name, "issue_date": r.issue_date, "lead": r.lead,
                         "target_quarter": r.target_quarter, "sws_newest_q": r.sws_newest_q, "h_last": r.h_last,
                         "ref_hat": round(r.ref_hat, 4), "forecast_level": round(r.ref_hat + r.zhat, 4),
                         "p_elevated": round(float(M.norm.cdf(r.zhat / s)), 4), "persistence_level": r.h_last,
                         "persistence_elevated": int(r.h_anom > 0)})
    S = pd.DataFrame(rows)
    p = OUT / "sealed_prospective.csv"
    S.to_csv(p, index=False, lineterminator="\n")
    (OUT / "sealed_prospective.csv.sha256").write_text(M.sha256(p) + "\n")
    print(S.to_string(index=False))
    print("seal", M.sha256(p))


PHASES = {"verify": phase_verify, "data": phase_data, "audit": phase_audit, "score": phase_score,
          "placebo": phase_placebo, "seal": phase_seal}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in PHASES.items():
        if which in ("all", name):
            print(f"===== {name}")
            fn()
