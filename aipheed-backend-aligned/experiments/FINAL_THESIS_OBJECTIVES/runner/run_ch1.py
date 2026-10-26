"""FINAL_THESIS_OBJECTIVES runner (FINAL_TARGET_AND_EVALUATION_PROTOCOL.md). One command reruns everything:

    python run_ch1.py all        # audit -> score -> placebo -> seal -> export
"""
from __future__ import annotations

import dataclasses
import json
import sys

import ch1_lib as C

FM, B, E, L, NF, np, pd = C.FM, C.B, C.E, C.L, C.NF, C.np, C.pd
OUT = C.OUT
OUT.mkdir(exist_ok=True)


def _check_protocol():
    want = (C.HERE / "PROTOCOL_SHA256.txt").read_text().strip()
    assert FM.sha256(C.CH1 / "FINAL_TARGET_AND_EVALUATION_PROTOCOL.md") == want, "protocol changed after freezing"


# ================================================================================================ audit (section 11)
def forecast_at(t: int, k: int, d, x) -> dict:
    X = C.build_X(k, d, x, origins=range(E.FIRST_ORIGIN, t + 1))
    tr = B.price_rows(X, t, k, d)
    te = X[X["t"] == t]
    if not B.eligible(tr) or te["H1"].isna().any():
        return {}
    pp, _, _ = C._price(tr, te, C.COLS, k)
    return {p: round(float(v), 10) for p, v in zip(te["province_code"], te["H1"].to_numpy() * pp)}


def _clear():
    for f in (FM.known, NF.gap_features):
        f.cache_clear()


def phase_audit():
    _check_protocol()
    rng = np.random.default_rng(C.SEED)
    d, x = E.data()
    o_rounds, o_gkg = FM.rounds.__wrapped__, NF.gkg.__wrapped__
    origins = [L.qi(q) for q in ("2023-Q2", "2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q2",
                                 "2025-Q3", "2026-Q1", "2026-Q2")]
    res = []

    def set_rounds(pr):
        FM.rounds = (lambda dataset="primary", _p=pr: _p if dataset == "primary" else o_rounds(dataset)) \
            if pr is not None else FM.functools.lru_cache(maxsize=2)(o_rounds)
        if not hasattr(FM.rounds, "cache_clear"):
            FM.rounds.cache_clear = lambda: None

    def set_gkg(pg):
        NF.gkg = (lambda _g=pg: _g) if pg is not None else FM.functools.lru_cache(maxsize=1)(o_gkg)
        if not hasattr(NF.gkg, "cache_clear"):
            NF.gkg.cache_clear = lambda: None
    for t in origins:
        k = 1
        _clear()
        base = forecast_at(t, k, d, x)
        iss = E.issue(t)
        m0 = L.m0_of(t)
        r0 = o_rounds("primary").copy()
        fut = r0["published"] >= iss
        r0.loc[fut, "H"] = rng.uniform(0, 50, int(fut.sum()))
        yo, ix = d.yoy.copy(), d.idx.copy()
        yo.loc[yo["ym"] > m0, "yoy"] = rng.uniform(-10, 20, int((yo["ym"] > m0).sum()))
        ix.loc[ix["ym"] > m0, "index"] = rng.uniform(80, 160, int((ix["ym"] > m0).sum()))
        dp = dataclasses.replace(d, yoy=yo, idx=ix)
        g0 = o_gkg().copy()
        gf = g0["published"] >= pd.Timestamp(iss)
        for c in NF.CATS + ["anticipatory", "food_event"]:
            g0.loc[gf, c] = rng.permutation(g0.loc[gf, c].to_numpy())
        set_rounds(r0)
        set_gkg(g0)
        _clear()
        try:
            pert = forecast_at(t, k, dp, x)
        finally:
            set_rounds(None)
            set_gkg(None)
            _clear()
        res.append({"origin": L.qs(t), "n": len(base), "identical": base == pert,
                    "future_rounds": int(fut.sum()), "future_cpi_months": int((d.yoy["ym"] > m0).sum())})
        print(res[-1])
    t = origins[4]
    base = forecast_at(t, 1, d, x)
    r0 = o_rounds("primary").copy()
    past = r0["published"] < E.issue(t)
    r0.loc[past, "H"] = rng.uniform(0, 50, int(past.sum()))
    set_rounds(r0)
    _clear()
    try:
        neg = forecast_at(t, 1, d, x)
    finally:
        set_rounds(None)
        _clear()
    ok = all(r["identical"] and r["n"] > 0 for r in res) and neg != base
    FM.write_json(OUT / "leakage_audit.json", {"passed": ok, "origins": res, "negative_control_changed": neg != base})
    print("negative control changed:", neg != base)
    assert ok, "leakage audit failed"


# ================================================================================================ score
def phase_score():
    _check_protocol()
    assert json.loads((OUT / "leakage_audit.json").read_text())["passed"]
    res = {"protocol_sha256": FM.sha256(C.CH1 / "FINAL_TARGET_AND_EVALUATION_PROTOCOL.md"), "leads": {},
           "superiority": {}, "news_ablation": {}}
    frames = []
    for k in C.LEADS:
        D = C.run_lead(k)
        D.to_csv(OUT / f"predictions_lead{k}.csv", index=False, lineterminator="\n", float_format="%.6g")
        frames.append(D)
        res["leads"][k] = C.decide(D)
        res["superiority"][k] = C.superiority(D)
        y = D["y"].astype(int).to_numpy()
        b = FM.boot_diff(D, (D["CH1_p"] - y) ** 2, (D["LGBM-GOV_p"] - y) ** 2)
        res["news_ablation"][k] = {"n": len(D), "acc_with": float(((D["CH1_p"] >= .5).astype(int) == y).mean()),
                                   "acc_without": float(((D["LGBM-GOV_p"] >= .5).astype(int) == y).mean()),
                                   "brier_diff": b, "mcnemar_p": FM.mcnemar(y, D["CH1_p"] >= .5,
                                                                            D["LGBM-GOV_p"] >= .5)}
        d = res["leads"][k]
        print(f"lead {k}: n {d['n']} q {d['n_quarters']} HIGH {d['high_share']:.2f} acc {d['metrics']['accuracy']:.3f} "
              f"CI {d['accuracy_ci90']} bal {d['metrics']['balanced_accuracy']:.3f} P {d['metrics']['precision']:.2f} "
              f"R {d['metrics']['recall']:.2f} AUC {d['metrics']['auc']:.3f} | "
              + " ".join(f"{b_}={v:.3f}" for b_, v in d["baseline_accuracy"].items())
              + f" | {[c for c, v in d['criteria'].items() if not v]} reliable={d['reliable']}")
    hp = FM.holm({k: res["news_ablation"][k]["brier_diff"]["p_two"] for k in res["news_ablation"]})
    for k in res["news_ablation"]:
        res["news_ablation"][k]["holm_p"] = hp[k]
    res["max_reliable_lead"] = C.max_reliable_lead(res["leads"])
    res["max_reliable_lead_strict"] = C.max_reliable_lead(res["leads"], "reliable_strict")
    # SHAP family shares
    sh = {}
    for D in frames:
        k = int(D["lead"].iloc[0])
        cols = [c for c in C.COLS if f"shap_{c}" in D]
        tot = sum(D[f"shap_{c}"].abs().mean() for c in cols) or 1.0
        fam = {}
        for c in cols:
            fam[C.FAMILY_OF[c]] = fam.get(C.FAMILY_OF[c], 0.0) + float(D[f"shap_{c}"].abs().mean() / tot)
        sh[k] = fam
    res["shap_family_share_price_model"] = sh
    # what decided the label in the evaluated rows
    A = pd.concat(frames)
    res["label_structure"] = {int(k): {"rows": int(len(g)), "high": int(g["y"].sum()),
                                       "hunger_condition_false": int((g["hunger"] == 0).sum()),
                                       "price_condition_false": int((g["price"] == 0).sum())}
                              for k, g in A.groupby("lead")}
    never = A[A["q"].isin([L.qi("2025-Q2"), L.qi("2025-Q3")])]
    res["never_scored_rows_2025Q2_Q3"] = {int(k): {"n": int(len(g)), "correct": int(((g["CH1_p"] >= .5).astype(int)
                                                                                     == g["y"]).sum()),
                                                   "persist_si_correct": int(((g["PERSIST-SI_p"] >= .5).astype(int)
                                                                              == g["y"]).sum())}
                                          for k, g in never.groupby("lead")}
    FM.write_json(OUT / "results.json", res)
    print("max reliable lead", res["max_reliable_lead"], "strict", res["max_reliable_lead_strict"])
    for k in C.LEADS:
        s = res["superiority"][k]
        print("H3 lead", k, "rejected" if s["H3_rejected"] else "not rejected",
              {b: (round(v["brier_diff"], 3), round(v["holm_p"], 3)) for b, v in s["comparisons"].items()})
        na = res["news_ablation"][k]
        print("news lead", k, round(na["acc_with"], 3), round(na["acc_without"], 3), round(na["brier_diff"]["diff"], 4),
              round(na["holm_p"], 3))


# ================================================================================================ placebo (section 9)
def phase_placebo():
    rng = np.random.default_rng(C.SEED)
    out = {}
    for k in (1, 2):
        X = C.build_X(k)
        D = pd.read_csv(OUT / f"predictions_lead{k}.csv", dtype={"province_code": str})
        real = float(((D["CH1_p"] - D["y"]) ** 2).mean())
        origins = sorted(X["t"].unique())
        perm = []
        for i in range(100):
            mp = dict(zip(origins, rng.permutation(origins)))
            P = C.run_lead(k, X=X, news_perm=mp, light=True)
            j = D[["province_code", "q", "y"]].merge(P[["province_code", "q", "CH1_p"]], on=["province_code", "q"])
            perm.append(float(((j["CH1_p"] - j["y"]) ** 2).mean()))
        out[k] = {"real_brier": real, "perm_mean": float(np.mean(perm)),
                  "p_perm_le_real": float(np.mean(np.array(perm) <= real)), "n_perm": 100}
        print(k, out[k])
    FM.write_json(OUT / "results_placebo.json", out)


# ================================================================================================ seal
def phase_seal():
    t = E.LAST_ORIGIN
    rows = []
    d, _ = E.data()
    for k in C.FORECAST_LEADS:
        X = C.build_X(k)
        tr = B.price_rows(X, t, k)
        te = X[X["t"] == t]
        pp, _, cfg = C._price(tr, te, C.COLS, k)
        sig, fill = B.sigmas(tr), float(tr["y"].mean())
        st = te["H1"].to_numpy() * B.struct_price(te, sig, fill)
        ps = C.persist_si(d, t, te["province_code"])
        for i, r in enumerate(te.itertuples()):
            rows.append({"province": C.PROV_NAME[r.province_code], "province_code": r.province_code,
                         "issue_date": r.issue_date, "lead": k, "target_quarter": L.qs(t + k),
                         "pi_hunger": round(float(r.H1), 4), "pi_price": round(float(pp[i]), 4),
                         "p_high": round(float(r.H1 * pp[i]), 4), "class": "HIGH" if r.H1 * pp[i] >= .5 else "LOW",
                         "struct_p": round(float(st[i]), 4), "persist_si": ps[r.province_code],
                         "sws_newest_q": r.sws_newest_q, "psa_newest_month": r.psa_newest_month})
    S = pd.DataFrame(rows)
    p = OUT / "sealed_prospective.csv"
    S.to_csv(p, index=False, lineterminator="\n")
    (OUT / "sealed_prospective.csv.sha256").write_text(FM.sha256(p) + "\n")
    print(S.to_string(index=False))
    print("seal", FM.sha256(p))


PHASES = {"audit": phase_audit, "score": phase_score, "placebo": phase_placebo, "seal": phase_seal}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in PHASES.items():
        if which in ("all", name):
            print(f"===== {name}")
            fn()
