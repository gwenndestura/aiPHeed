"""FINAL_ARCHITECTURE runner (PROTOCOL_FINAL_ARCHITECTURE.md).

    python run_final.py audit      # future-perturbation audit of C-G (SWS, CPI, regional CPI, Pink Sheet, news, ONI,
                                   # PAGASA items after O(t))
    python run_final.py score      # C-G on every lead; selection; block usefulness; recommendation vs P0H4
    python run_final.py placebo    # climate placebos (shuffle across issue dates; 4-quarter displacement)
    python run_final.py ablation   # group and family ablations of the selected candidate
    python run_final.py replay     # historical replay of the selected candidate
"""
from __future__ import annotations

import dataclasses
import json
import sys
import time

import final_lib as F

O, X, U, C, FM, B, E, L, np, pd = F.O, F.X, F.U, F.C, F.FM, F.B, F.E, F.L, F.np, F.pd
A4 = O.A4
A2, A3, RL = A4.A2, O.A3, A4.RL
sys.path.insert(0, str(F.EXP / "LEAD2_ONE_MODEL" / "runner"))
import run_one as R1  # noqa: E402

OUT = F.OUT
OUT.mkdir(exist_ok=True)
ONE_OUT = F.EXP / "LEAD2_ONE_MODEL" / "out"
NAMES = list(F.CANDS)


def _check():
    want = (F.HERE / "PROTOCOL_SHA256.txt").read_text().strip()
    assert FM.sha256(F.FA / "PROTOCOL_FINAL_ARCHITECTURE.md") == want, "protocol changed after freezing"


def _all(S, t, d=None, names=NAMES, cols=None):
    fr = [F.forecast(S, t, cols or F.CANDS[n], n, d).set_index(["t", "lead", "province_code", "target_q"])
          for n in names]
    return pd.concat(fr, axis=1).reset_index()


# ================================================================================================ audit
def phase_audit():
    _check()
    U.setup()
    sys.path.insert(0, str(C.HERE))
    import run_ch1 as RC
    K = RL._K()
    rng = np.random.default_rng(2032)
    d, x = E.data()
    o_rounds, o_gkg = C.FM.rounds.__wrapped__, C.NF.gkg.__wrapped__
    w0, rice0, cpi0, oni0 = U.pinksheet(), X.rice_cpi(), A3.region_cpi(), F.oni()

    def run(t, dd, w, rice, cpi, o, items):
        S = F.build(K, dd, x, t, w, cpi, rice, o, items)
        f = _all(S, t, dd)
        return f[[f"{n}_p" for n in NAMES]].round(10)

    def clear():
        RC._clear()
        U._rounds.cache_clear()
        E._CACHE.clear()

    res = []
    for q in ("2023-Q2", "2023-Q4", "2024-Q2", "2024-Q4", "2025-Q3", "2026-Q2"):
        t = L.qi(q)
        clear()
        base = run(t, d, w0, rice0, cpi0, oni0, F.EC.PAGASA_ENSO)
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
        op = oni0.copy()
        op[op.index > m0] = rng.uniform(-2.5, 2.5, int((op.index > m0).sum()))
        items = [it for it in F.EC.PAGASA_ENSO if it[0] < iss] + [(iss, "El Nino Advisory: injected future item"),
                                                                    ("2099-01-01", "El Nino Alert: injected")]
        C.FM.rounds = lambda dataset="primary", _p=r0: _p if dataset == "primary" else o_rounds(dataset)
        C.FM.rounds.cache_clear = lambda: None
        C.NF.gkg = lambda _g=g0: _g
        C.NF.gkg.cache_clear = lambda: None
        clear()
        try:
            pert = run(t, dp, wp, rp, cp, op, items)
        finally:
            C.FM.rounds = C.FM.functools.lru_cache(maxsize=2)(o_rounds)
            C.NF.gkg = C.FM.functools.lru_cache(maxsize=1)(o_gkg)
            clear()
        res.append({"origin": q, "values": int(base.notna().sum().sum()), "identical": bool(base.equals(pert))})
        print(res[-1], flush=True)
    ok = all(r["identical"] and r["values"] for r in res)
    FM.write_json(OUT / "leakage_audit.json", {"passed": ok, "candidates": NAMES, "origins": res})
    assert ok


# ================================================================================================ score
def _brier(p, y):
    return float(np.mean((np.clip(np.asarray(p, float), 0, 1) - np.asarray(y, float)) ** 2))


def _diff(D, a, b, k):
    g = D[D["lead"] == k]
    y = g["y"].astype(int).to_numpy()
    return FM.boot_diff(g, (g[a] - y) ** 2, (g[b] - y) ** 2)


def phase_score():
    _check()
    assert json.loads((OUT / "leakage_audit.json").read_text())["passed"], "run the audit first"
    U.setup()
    K = RL._K()
    t0 = time.time()
    S = F.build(K)
    fr = []
    for t in RL._origins():
        fr.append(_all(S, t))
        print("origin", L.qs(t), round(time.time() - t0), "s", flush=True)
    P = pd.concat(fr, ignore_index=True).drop(columns=["target_q"])
    D = pd.read_csv(ONE_OUT / "predictions.csv", dtype={"province_code": str})
    n0 = len(D)
    D = D.merge(P, on=["t", "lead", "province_code"], how="left")
    assert len(D) == n0 and D[[f"{n}_p" for n in NAMES]].notna().all().all(), "rows differ"
    D.to_csv(OUT / "predictions.csv", index=False, lineterminator="\n", float_format="%.6g")
    res = {"protocol_sha256": FM.sha256(F.FA / "PROTOCOL_FINAL_ARCHITECTURE.md"),
           "C_reproduces_S3_max_abs_diff": float((D["C_p"] - D["S3_p"]).abs().max()), "candidates": {}}
    dev = D[(D["q"] <= U.DEV_LAST) & (D["lead"] <= 3)]
    for n in NAMES + ["P0H4"]:
        col = f"{n}_p" if n != "P0H4" else "P0H4_p3"
        rep = R1.report(D, col)
        rep["dev_brier_mean_leads_1_3"] = float(np.mean([_brier(g[col], g["y"]) for _, g in dev.groupby("lead")]))
        rep["vs_P0H4"] = {k: _diff(D, col, "P0H4_p3", k) for k in (1, 2, 3)}
        if n != "C" and n != "P0H4":
            rep["vs_C"] = {k: _diff(D, col, "C_p", k) for k in (1, 2, 3)}
        res["candidates"][n] = rep
        l1, l2 = rep["leads"][1], rep["leads"][2]
        print(f"{n:5s} L1 acc {l1['metrics']['accuracy']:.3f} R {l1['metrics']['recall']:.2f} Brier {l1['metrics']['brier']:.3f} "
              f"({l1['verdict'][:4]}) | L2 acc {l2['metrics']['accuracy']:.3f} bal {l2['metrics']['balanced_accuracy']:.3f} "
              f"R {l2['metrics']['recall']:.2f} Brier {l2['metrics']['brier']:.3f} | L3 Brier "
              f"{rep['leads'][3]['metrics']['brier']:.3f} | dev {rep['dev_brier_mean_leads_1_3']:.4f} | maxrel "
              f"{rep['max_promising_lead']} | vsP0H4 L1 {rep['vs_P0H4'][1]['diff']:+.4f} p1 {rep['vs_P0H4'][1]['p_less']:.3f}",
              flush=True)
    elig = {}
    for n in NAMES:
        r = res["candidates"][n]
        t1 = r["vs_P0H4"][1]
        elig[n] = r["leads"][1]["verdict"] == "promising_not_yet_verified" and not (t1["diff"] > 0 and (1 - t1["p_less"]) < 0.10)
    order = {"C": 0, "D": 1, "E": 1, "F": 1, "G": 2}
    chosen = None
    for n in sorted([n for n in NAMES if elig[n]], key=lambda n: (res["candidates"][n]["dev_brier_mean_leads_1_3"], order[n])):
        if chosen is None:
            chosen = n
        elif (res["candidates"][n]["dev_brier_mean_leads_1_3"] - res["candidates"][chosen]["dev_brier_mean_leads_1_3"] <= 0.002
              and order[n] < order[chosen]):
            chosen = n
    useful = {}
    for n in ("D", "E", "F"):
        r = res["candidates"][n]
        lower = r["dev_brier_mean_leads_1_3"] < res["candidates"]["C"]["dev_brier_mean_leads_1_3"]
        ci = any(r["vs_C"][k]["ci90"][1] < 0 for k in (1, 2))
        useful[n] = {"lower_dev_brier": lower, "ci_excludes_0_lead1_or_2": ci, "adds_predictive_value": lower and ci}
    rec = None
    if chosen:
        r = res["candidates"][chosen]
        worse = any(r["vs_P0H4"][k]["diff"] > 0 and r["vs_P0H4"][k]["p_two"] < 0.10 for k in (1, 2))
        rec = {"single_model_recommended": not worse, "chosen": chosen,
               "lead3_significantly_worse": r["vs_P0H4"][3]["diff"] > 0 and r["vs_P0H4"][3]["p_two"] < 0.10}
    res.update(eligibility=elig, chosen=chosen, block_usefulness=useful, recommendation=rec)
    FM.write_json(OUT / "results.json", res)
    print("eligible", elig, "| chosen", chosen, "| useful", {k: v["adds_predictive_value"] for k, v in useful.items()},
          "| recommendation", rec)


# ================================================================================================ placebo / ablation / replay
def _chosen():
    return sys.argv[2] if len(sys.argv) > 2 else json.loads((OUT / "results.json").read_text())["chosen"]


def _refit(S, cols, name):
    fr = [F.forecast(S, t, cols, name) for t in RL._origins()]
    return pd.concat(fr, ignore_index=True).drop(columns=["target_q"])


def _stats(D, col):
    out = {}
    for k, g in D.groupby("lead"):
        if k <= 3:
            y = g["y"].astype(int).to_numpy()
            yh = (g[col] >= .5).astype(int).to_numpy()
            out[int(k)] = {"brier": _brier(g[col], y), "acc": float((yh == y).mean()),
                           "tp": int(((yh == 1) & (y == 1)).sum()), "fp": int(((yh == 1) & (y == 0)).sum())}
    return out


def phase_placebo(n: int = 20):
    U.setup()
    K = RL._K()
    name = _chosen()
    S0 = F.build(K)
    D = pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str})
    cols = F.CANDS[name]
    clim = F.group_cols(cols, {"C1", "C2", "C3", "C4"})
    real = _stats(D, f"{name}_p")
    rng = np.random.default_rng(2033)
    ts = sorted(S0["t"].unique())
    shuf = []
    for i in range(n):
        mp = dict(zip(ts, rng.permutation(ts)))
        src = S0.set_index(["province_code", "t", "lead"])[clim]
        S = S0.copy()
        S[clim] = src.reindex(list(zip(S["province_code"], S["t"].map(mp), S["lead"]))).to_numpy()
        A = D[["t", "lead", "province_code", "y", "q"]].merge(_refit(S, cols, "pl"), on=["t", "lead", "province_code"])
        shuf.append(_stats(A, "pl_p"))
        print("shuffle", i, {k: round(v["brier"], 4) for k, v in shuf[-1].items()}, flush=True)
    src = S0.set_index(["province_code", "t", "lead"])[clim]
    S = S0.copy()
    S[clim] = src.reindex(list(zip(S["province_code"], S["t"] - 4, S["lead"]))).to_numpy()
    A = D[["t", "lead", "province_code", "y", "q"]].merge(_refit(S, cols, "pl"), on=["t", "lead", "province_code"])
    disp = _stats(A, "pl_p")
    print("displaced", disp, "real", real, flush=True)
    FM.write_json(OUT / f"climate_placebo_{name}.json", {
        "candidate": name, "climate_columns": clim, "real": real, "shuffles": shuf, "displaced_4q": disp,
        "perm_p": {k: float(np.mean([s[k]["brier"] <= real[k]["brier"] for s in shuf])) for k in real},
        "shuffle_mean_brier": {k: float(np.mean([s[k]["brier"] for s in shuf])) for k in real}})


def phase_ablation():
    U.setup()
    K = RL._K()
    name = _chosen()
    cols = F.CANDS[name]
    S = F.build(K)
    D = pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str})
    variants = {f"without {g}": F.group_cols(cols, fams) for g, fams in F.GROUPS.items()}
    variants.update({f"without family {f}": F.group_cols(cols, {f}) for f in F.FAMILIES})
    out = {"candidate": name, "full": _stats(D, f"{name}_p"), "variants": {}}
    for vname, drop in variants.items():
        keep = [c for c in cols if c not in drop]
        A = D.merge(_refit(S, keep, "ab"), on=["t", "lead", "province_code"], how="left")
        assert A["ab_p"].notna().all()
        st = _stats(A, "ab_p")
        for k in (1, 2, 3):
            st[k]["brier_full_minus_ablated"] = _diff(A, f"{name}_p", "ab_p", k)
        out["variants"][vname] = {"dropped": drop, **{str(k): v for k, v in st.items()}}
        print(f"{vname:45s} " + " | ".join(f"L{k} acc {st[k]['acc']:.3f} dB {st[k]['brier_full_minus_ablated']['diff']:+.4f} "
                                          f"CI {[round(v, 4) for v in st[k]['brier_full_minus_ablated']['ci90']]}"
                                          for k in (1, 2)), flush=True)
    ps = {(v, k): out["variants"][v][str(k)]["brier_full_minus_ablated"]["p_two"] for v in out["variants"] for k in (1, 2)}
    for (v, k), h in FM.holm(ps).items():
        out["variants"][v][str(k)]["brier_full_minus_ablated"]["holm_p"] = h
    FM.write_json(OUT / f"ablation_{name}.json", out)


def phase_replay():
    U.setup()
    K = RL._K()
    name = _chosen()
    D = pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str})
    d, x = E.data()
    out = []
    for q in ("2023-Q4", "2024-Q4", "2026-Q1"):
        t = L.qi(q)
        S = F.build(K, d, x, t)
        assert S["t"].max() == t
        f = F.forecast(S, t, F.CANDS[name], name, d)
        m = f.merge(D[D["t"] == t][["lead", "province_code", f"{name}_p"]], on=["lead", "province_code"],
                    suffixes=("_replay", ""))
        out.append({"origin": q, "rows_compared": int(len(m)),
                    "max_abs_diff": float((m[f"{name}_p_replay"] - m[f"{name}_p"]).abs().max())})
        print(out[-1], flush=True)
    FM.write_json(OUT / f"historical_replay_{name}.json",
                  {"identical": all(o["max_abs_diff"] < 1e-5 for o in out), "candidate": name, "origins": out})


def phase_shap():
    """Group SHAP shares of a single-model candidate: it explains the full risk probability (hunger inputs included).
    Shares of total |SHAP| per row, mean over Lead-1 and Lead-2 rows of every origin; by El Nino state."""
    U.setup()
    K = RL._K()
    name = _chosen()
    cols = F.CANDS[name]
    S = F.build(K)
    rows = []
    for t in RL._origins():
        f = F.forecast(S, t, cols, name)
        m = f.attrs.get("model")
        if m is None or m.m is None:
            continue
        te = S[(S["t"] == t)]
        sv = m.m.booster_.predict(te[cols].astype(float), pred_contrib=True)[:, :len(cols)]
        df = pd.DataFrame(np.abs(sv), columns=cols)
        df["lead"], df["t"], df["C1_level"] = te["lead"].to_numpy(), te["t"].to_numpy(), te["C1_level"].to_numpy() \
            if "C1_level" in te else 0
        rows.append(df[df["lead"] <= 2])
    A = pd.concat(rows, ignore_index=True)
    tot = A[cols].sum(axis=1).replace(0, np.nan)
    groups = {**{g: F.group_cols(cols, f) for g, f in F.GROUPS.items()}, "lead (horizon)": ["lead"]}
    share = pd.DataFrame({g: A[c].sum(axis=1) / tot for g, c in groups.items()})
    share["el_nino_alert_or_advisory"] = (S.set_index("t")["C1"].groupby(level=0).first().reindex(A["t"]).to_numpy() > 0)
    out = {"candidate": name, "rows": int(len(A)), "mean_share": share[list(groups)].mean().round(4).to_dict(),
           "by_el_nino_state": share.groupby("el_nino_alert_or_advisory")[list(groups)].mean().round(4).to_dict(orient="index")}
    print(json.dumps(out, indent=1, default=str))
    FM.write_json(OUT / f"shap_groups_{name}.json", out)


if __name__ == "__main__":
    {"audit": phase_audit, "score": phase_score, "placebo": phase_placebo, "ablation": phase_ablation,
     "replay": phase_replay, "shap": phase_shap}[sys.argv[1]]()
