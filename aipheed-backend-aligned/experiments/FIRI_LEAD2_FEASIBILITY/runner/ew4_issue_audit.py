"""EW4 issue-date check (PROTOCOL.md section 8). The frozen LEAD2_OPTIMIZATION perturbation audit (run_l2.phase_audit),
run at the 2026-Q3 origin (issue 2026-10-01) that it never covered, extended to LFS, production, remittance and
rice-wholesale periods after the cut, plus a positive control that perturbs data published BEFORE the issue (the
outputs must change, which proves no cache hides a perturbation). In memory only; writes out/ew4_issue_audit.json.

    python ew4_issue_audit.py
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True                                    # never write caches into protected folders

import dataclasses  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))
import l2_lib as X  # noqa: E402
import a3  # noqa: E402

U, C, FM, E, L, np, pd = X.U, X.C, X.FM, X.E, X.L, X.np, X.pd
ISSUE_T = "2026-Q3"
ARMS = ("P4", "P0")


def frozen_ok() -> None:
    want = (HERE / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((HERE.parent / "PROTOCOL.md").read_bytes()).hexdigest() == want, "PROTOCOL.md changed"


def clear_all() -> None:
    sys.path.insert(0, str(C.HERE))
    import run_ch1 as RC
    RC._clear()
    U._rounds.cache_clear()
    E._CACHE.clear()
    for mod in {U, C, FM, E, L, X, a3, C.NF}:
        for v in vars(mod).values():
            if callable(getattr(v, "cache_clear", None)) and getattr(v, "__module__", "") == mod.__name__:
                v.cache_clear()


def main():
    frozen_ok()
    U.setup()
    K = int(json.loads((U.OUT / "testability_unified.json").read_text())["K"])
    rng = np.random.default_rng(X.SEED)
    t = L.qi(ISSUE_T)
    iss, m0 = E.issue(t), L.m0_of(t)
    d, x = E.data()
    o_rounds, o_gkg = C.FM.rounds.__wrapped__, C.NF.gkg.__wrapped__
    w0, r0_rice = U.pinksheet(), X.rice_cpi()

    def forecast(dd, xx, w, rice):
        S = X.add_fe(U.stack(K, dd, xx, t, w), dd, rice)
        f = X.forecast_origin(S, t, ARMS, True, dd)
        a = {(r["province_code"], int(r["lead"]), c): round(float(r[c]), 10)
             for _, r in f[f["lead"].isin([1, 2])].iterrows() for c in [f"{p}_price" for p in ARMS] + ["H1"]}
        a.update({("H4", k): round(a3.h4(t, k), 10) for k in (1, 2)})
        return a

    def set_rounds(pr):
        C.FM.rounds = (lambda dataset="primary", _p=pr: _p if dataset == "primary" else o_rounds(dataset)) \
            if pr is not None else C.FM.functools.lru_cache(maxsize=2)(o_rounds)
        if not hasattr(C.FM.rounds, "cache_clear"):
            C.FM.rounds.cache_clear = lambda: None

    def set_gkg(pg):
        C.NF.gkg = (lambda _g=pg: _g) if pg is not None else C.FM.functools.lru_cache(maxsize=1)(o_gkg)
        if not hasattr(C.NF.gkg, "cache_clear"):
            C.NF.gkg.cache_clear = lambda: None

    def run(dd, xx, w, rice, rounds, gkg):
        set_rounds(rounds)
        set_gkg(gkg)
        clear_all()
        try:
            return forecast(dd, xx, w, rice)
        finally:
            set_rounds(None)
            set_gkg(None)
            clear_all()

    clear_all()
    base = forecast(d, x, w0, r0_rice)

    # ---- perturb everything published on/after the issue date (frozen audit + extensions)
    r0 = o_rounds("primary").copy()
    fut = r0["published"] >= iss
    r_after = r0.copy()
    r_after.loc[fut, "H"] = rng.uniform(0, 50, int(fut.sum()))
    yo, ix = d.yoy.copy(), d.idx.copy()
    yo.loc[yo["ym"] > m0, "yoy"] = rng.uniform(-10, 20, int((yo["ym"] > m0).sum()))
    ix.loc[ix["ym"] > m0, "index"] = rng.uniform(80, 160, int((ix["ym"] > m0).sum()))
    pr = d.prod.copy()
    pr.loc[pr["q"] >= t, "value"] = rng.uniform(1, 1e5, int((pr["q"] >= t).sum()))
    lf = d.lfs.copy()
    lf_cut = (t - 1) // 4 * 12 + ((t - 1) % 4) * 3 + 2
    lf.loc[lf["ym"] > lf_cut, "value"] = rng.uniform(1, 30, int((lf["ym"] > lf_cut).sum()))
    dp = dataclasses.replace(d, yoy=yo, idx=ix, prod=pr, lfs=lf)
    xp = dict(x)
    xp["ofw"] = x["ofw"].copy()
    xp["ofw"].loc[xp["ofw"]["q"] >= t, "ofw_cash_remit_usd_bn"] = rng.uniform(1, 20, int((x["ofw"]["q"] >= t).sum()))
    xp["rice"] = x["rice"].copy()
    xp["rice"].loc[xp["rice"]["q"] >= t, "price_php_per_kg"] = rng.uniform(20, 90, int((x["rice"]["q"] >= t).sum()))
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
    pert = run(dp, xp, wp, rp, r_after, g0)
    after_diff = [str(k) for k in base if base[k] != pert.get(k)]

    # ---- positive control: perturb data published BEFORE the issue (newest SWS round and CPI month m0)
    r_before = r0.copy()
    last = r_before[r_before["published"] < iss]["published"].idxmax()
    r_before.loc[last, "H"] = float(r_before.loc[last, "H"]) + 8.0
    yo2 = d.yoy.copy()
    yo2.loc[yo2["ym"] == m0, "yoy"] = yo2.loc[yo2["ym"] == m0, "yoy"] + 6.0
    ctrl = run(dataclasses.replace(d, yoy=yo2), x, w0, r0_rice, r_before, None)
    ctrl_diff = [str(k) for k in base if base[k] != ctrl.get(k)]

    perturbed = {
        "SWS rounds published >= issue": int(fut.sum()), "CPI/idx months > m0": int((d.yoy["ym"] > m0).sum()),
        "Pink Sheet months > m0": int(fm.sum()), "rice CPI months > m0": int((r0_rice.index > m0).sum()),
        "GDELT records published >= issue": int(gf.sum()), "production quarters >= t": int((d.prod["q"] >= t).sum()),
        "LFS months after cut": int((d.lfs["ym"] > lf_cut).sum()), "remittance quarters >= t": int((x["ofw"]["q"] >= t).sum()),
        "rice wholesale quarters >= t": int((x["rice"]["q"] >= t).sum())}
    res = {"origin": ISSUE_T, "issue": iss, "m0": L.ym_s(m0), "arms": list(ARMS), "valuesCompared": len(base),
           "perturbedRecords": perturbed,
           "afterIssue": {"identical": not after_diff, "differences": after_diff[:10]},
           "positiveControl": {"perturbed": f"SWS round published {str(r0.loc[last, 'published'])[:10]} +8 points; CPI {L.ym_s(m0)} +6",
                               "changed": bool(ctrl_diff), "valuesChanged": len(ctrl_diff)},
           "passed": (not after_diff) and bool(ctrl_diff)}
    out = HERE.parent / "out"
    out.mkdir(exist_ok=True)
    (out / "ew4_issue_audit.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
