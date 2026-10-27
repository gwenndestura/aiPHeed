"""Addendum 3 (ADDENDUM_3_HUNGER_ONSET.md): hunger candidates H4 (pooled-area sigma, 2021+), H3a (logistic
hunger-crossing with issue-time CPI, 2021+), H3b (same on 1998+, sample b), combined with P0, P4 and the Addendum-2
final price arm on the identical evaluation rows.

    python a3.py audit
    python a3.py score
"""
from __future__ import annotations

import functools
import json
import math
import sys

import l2_lib as X
import run_l2 as RL
import a2 as A2

U, C, FM, B, E, L, np, pd = X.U, X.C, X.FM, X.B, X.E, X.L, X.np, X.pd
OUT = X.OUT
AREAS = ("NCR", "BL", "VIS", "MIN")
H_PAIRS_MIN, H_CLASS_MIN, POOL_MIN = 20, 5, 8


def _check():
    A2._check()
    want = (X.HERE / "ADDENDUM_3_SHA256.txt").read_text().strip()
    assert FM.sha256(X.L2 / "ADDENDUM_3_HUNGER_ONSET.md") == want, "addendum 3 changed after freezing"


# ================================================================================================ inputs
@functools.lru_cache(maxsize=1)
def region_cpi() -> pd.DataFrame:
    """Region IV-A PSA-published YoY by month: columns rice, food (index = ym)."""
    c = pd.read_csv(X.LONG / "cov_cpi.csv")
    c = c[c["geolocation"].str.startswith("Region IV-A") & c["yoy"].notna()]
    name = {"01.1.1.12 - Rice": "rice", "01.1 - FOOD": "food"}
    c = c[c["commodity_description"].isin(name)]
    return c.assign(k=c["commodity_description"].map(name)).pivot_table(index="ym", columns="k", values="yoy")


def _cpi_at(cpi: pd.DataFrame, m: int, sample: str) -> tuple[float, float]:
    if m not in cpi.index or (sample == "a" and m < L.FIRST_YM):
        return float("nan"), float("nan")
    return float(cpi.loc[m, "rice"]), float(cpi.loc[m, "food"])


# ================================================================================================ H4
def h4(t: int, k: int) -> float:
    """pi_H with sigma from the pooled latest-reading errors of all four SWS areas (2021+) at the true horizon."""
    iss = E.issue(t)
    kn = C.bl_known(iss)
    if not kn:
        return float("nan")
    q_last, h_last = kn[-1][0], kn[-1][1]
    h = (t + k) - q_last
    errs = []
    for a in AREAS:
        d = {x[0]: x[1] for x in FM.known(iss, a, "primary")}
        errs += [d[q + h] - d[q] for q in d if q + h in d]
    if len(errs) < POOL_MIN:
        return float("nan")
    sig = math.sqrt(float(np.mean(np.square(errs))))
    return float(X.norm.cdf((h_last - X.H_LINE) / max(sig, 0.5)))


# ================================================================================================ H3a / H3b
def h3(t: int, k: int, sample: str, cpi: pd.DataFrame | None = None) -> float:
    """Logistic P(BL hunger(t+k) > 11.3) from (latest reading, true horizon, region rice and food CPI YoY at m0)."""
    from sklearn.linear_model import LogisticRegression
    cpi = region_cpi() if cpi is None else cpi
    cpi = cpi[cpi.index <= L.m0_of(t)]
    kn = X.known_series(E.issue(t), sample)
    if not kn:
        return float("nan")
    d = dict(kn)
    rows = []
    for q0 in d:
        r, f = _cpi_at(cpi, L.m0_of(q0 + 1), sample)
        for h in range(1, 7):
            if q0 + h in d:
                rows.append((d[q0], h, r, f, int(d[q0 + h] > X.H_LINE)))
    A = np.array([x for x in rows if np.all(np.isfinite(x))], float) if rows else np.zeros((0, 5))
    if len(A) < H_PAIRS_MIN or A[:, 4].sum() < H_CLASS_MIN or (1 - A[:, 4]).sum() < H_CLASS_MIN:
        return float("nan")
    q_last, h_last = kn[-1]
    r, f = _cpi_at(cpi, L.m0_of(t), sample)
    x0 = np.array([h_last, (t + k) - q_last, r, f], float)
    if not np.all(np.isfinite(x0)):
        return float("nan")
    mu, sd = A[:, :4].mean(0), A[:, :4].std(0)
    sd[sd == 0] = 1.0
    m = LogisticRegression(C=1.0).fit((A[:, :4] - mu) / sd, A[:, 4].astype(int))
    return float(m.predict_proba(((x0 - mu) / sd).reshape(1, -1))[0, 1])


def hunger_frame(pairs, cpi=None) -> pd.DataFrame:
    out = []
    for t, k in pairs:
        out.append({"t": int(t), "lead": int(k), "H4_raw": h4(int(t), int(k)), "H3a_raw": h3(int(t), int(k), "a", cpi),
                    "H3b_raw": h3(int(t), int(k), "b", cpi)})
    return pd.DataFrame(out)


# ================================================================================================ audit
def phase_audit():
    _check()
    U.setup()
    rng = np.random.default_rng(X.SEED + 3)
    o_rounds = C.FM.rounds.__wrapped__
    cpi0 = region_cpi()
    res = []
    for q in ("2023-Q2", "2023-Q4", "2024-Q2", "2024-Q4", "2025-Q3", "2026-Q2"):
        t = L.qi(q)
        pairs = [(t, k) for k in range(1, 6)]
        base = hunger_frame(pairs, cpi0)
        iss, m0 = E.issue(t), L.m0_of(t)
        r0 = o_rounds("primary").copy()
        fut = r0["published"] >= iss
        r0.loc[fut, "H"] = rng.uniform(0, 50, int(fut.sum()))
        cp = cpi0.copy()
        cp.loc[cp.index > m0] = rng.uniform(-20, 40, size=cp.loc[cp.index > m0].shape)
        C.FM.rounds = lambda dataset="primary", _p=r0: _p if dataset == "primary" else o_rounds(dataset)
        C.FM.rounds.cache_clear = lambda: None
        try:
            pert = hunger_frame(pairs, cp)
        finally:
            C.FM.rounds = C.FM.functools.lru_cache(maxsize=2)(o_rounds)
        cols = ["H4_raw", "H3a_raw", "H3b_raw"]
        same = bool(np.allclose(base[cols].to_numpy(float), pert[cols].to_numpy(float), equal_nan=True, atol=1e-12))
        res.append({"origin": q, "values": int(base[cols].notna().sum().sum()), "identical": same})
        print(res[-1], flush=True)
    ok = all(r["identical"] and r["values"] for r in res)
    FM.write_json(OUT / "leakage_audit_addendum3.json", {"passed": ok, "origins": res})
    assert ok


# ================================================================================================ score
def phase_score():
    _check()
    assert json.loads((OUT / "leakage_audit_addendum3.json").read_text())["passed"]
    U.setup()
    D = pd.read_csv(OUT / "predictions_addendum2.csv", dtype={"province_code": str})
    a2 = json.loads((OUT / "results_addendum2.json").read_text())["selection"]["final"]
    a2_arm = a2[:-2]
    Hf = hunger_frame(D[["t", "lead"]].drop_duplicates().itertuples(index=False))
    D = D.merge(Hf, on=["t", "lead"], how="left")
    for h in ("H4", "H3a", "H3b"):
        D[f"pi_{h}"] = np.where(D[f"{h}_raw"].isna(), D["H1"], D[f"{h}_raw"])
        D[f"{h}_fallback"] = D[f"{h}_raw"].isna()
    arms = list(dict.fromkeys(["P0", "P4", a2_arm]))
    combos = []
    for p in arms:
        for h in ("H0", "H4", "H3a", "H3b"):
            name = f"{p}{h}"
            hc = "H1" if h == "H0" else f"pi_{h}"
            D[f"{name}_p3"] = D[hc] * D[f"{p}_price"]
            combos.append((name, h, p))
    D.to_csv(OUT / "predictions_addendum3.csv", index=False, lineterminator="\n", float_format="%.6g")
    dev2 = D[(D["q"] <= U.DEV_LAST) & (D["lead"] == 2)]
    order = [c for c in combos if c[1] != "H3b"]
    order.sort(key=lambda c: (("H0", "H4", "H3a").index(c[1]), arms.index(c[2])))
    sel = {c[0]: A2._brier(dev2[f"{c[0]}_p3"], dev2["y"]) for c in order}
    best = order[0][0]
    for c in order[1:]:
        if sel[c[0]] < sel[best] - 0.0005:
            best = c[0]
    res = {"addendum3_sha256": FM.sha256(X.L2 / "ADDENDUM_3_HUNGER_ONSET.md"), "a2_final": a2,
           "hunger_fallback_share": {h: float(D[f"{h}_fallback"].mean()) for h in ("H4", "H3a", "H3b")},
           "selection": {"dev_lead2_brier": sel, "adopted": best}, "candidates": {}}
    q2 = D[D["lead"] == 2].groupby("q").first()
    for h, hc in (("H0", "H1"), ("H4", "pi_H4"), ("H3a", "pi_H3a"), ("H3b", "pi_H3b")):
        res.setdefault("hunger_condition_lead2", {})[h] = {
            "quarters": int(len(q2)), "correct_at_0.5": int(((q2[hc] >= .5).astype(int) == q2["hunger"]).sum()),
            "brier": float(np.mean((q2[hc] - q2["hunger"]) ** 2)),
            "onset_2023Q4": float(q2.loc[L.qi("2023-Q4"), hc]), "onset_2024Q2": float(q2.loc[L.qi("2024-Q2"), hc])}
        print("hunger", h, res["hunger_condition_lead2"][h], flush=True)
    for name, h, p in combos:
        col = f"{name}_p3"
        leads, mrl, r17 = {}, None, 0
        for k, g in D.groupby("lead"):
            dec = RL.lead_report(g, col)
            dec["surge_block"] = A2.block(g[g["q"].isin(A2.SURGE)], col)
            lb = A2.block(g[g["q"].isin(A2.LATER)], col)
            dec["later_block"], dec["later_check"] = lb, A2.later_check(lb)
            tau = A2.choose_tau(g[g["q"] <= U.DEV_LAST], col)
            dec["research_threshold"] = {"tau": tau, "all": A2.block(g, col, tau),
                                         "later_block": A2.block(g[g["q"].isin(A2.LATER)], col, tau)}
            dec["verdict"] = "promising_not_yet_verified" if dec["reliable"] and dec["later_check"] else "not_reliable"
            leads[int(k)] = dec
        for k in sorted(leads):
            if leads[k]["verdict"] == "promising_not_yet_verified":
                mrl = k
            else:
                break
        for k in sorted(leads):
            if leads[k]["reliable"]:
                r17 = k
            else:
                break
        res["candidates"][name] = {"sample": "b" if h == "H3b" else "a", "max_promising_lead": mrl,
                                   "max_r1_r7_lead": r17, "leads": leads}
        l2, m = leads[2], leads[2]["metrics"]
        print(f"{name:10s} L1 {leads[1]['metrics']['accuracy']:.3f} {leads[1]['verdict'][:4]} | L2 acc {m['accuracy']:.3f} "
              f"bal {m['balanced_accuracy']:.3f} P {m['precision']:.2f} R {m['recall']:.2f} AUC {m['auc']:.2f} "
              f"Brier {m['brier']:.3f} FN {l2['confusion']['fn']} FP {l2['confusion']['fp']} | surge "
              f"{l2['surge_block']['tp']}/{l2['surge_block']['high']} later {l2['later_block']['tp']}/"
              f"{l2['later_block']['high']} {l2['later_block']['acc']:.2f} | tau {l2['research_threshold']['tau']} | "
              f"fail {[c for c, v in l2['criteria'].items() if not v]} | maxprom {mrl} | dev {sel.get(name, float('nan')):.4f}",
              flush=True)
    FM.write_json(OUT / "results_addendum3.json", res)
    print("adopted", best)


if __name__ == "__main__":
    {"audit": phase_audit, "score": phase_score}[sys.argv[1]]()
