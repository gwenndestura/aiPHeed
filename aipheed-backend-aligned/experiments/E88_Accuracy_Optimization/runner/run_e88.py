"""E88 run (PROTOCOL.md): in-origin model selection / combination on the E84 rows. Run from backend/."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "E83_Deep_Reconstruction" / "runner"))
import e83_lib as E  # noqa: E402
import run_e83 as R  # noqa: E402

L, np, pd = E.L, E.np, E.pd
E84_RUN = EXP / "E84_Objective_Continuation" / "runs" / "20261021T093234Z"
POOL = ["S-SIM", "S-SIM-SEAS", "S-COMP", "S-COMP-NOW", "HYB-GBA-SIM"]
MIN_Q = 3
GRID = [round(0.30 + 0.05 * i, 2) for i in range(9)]


def past(P: pd.DataFrame, d, t: int) -> pd.DataFrame:
    """Rows whose target label was published before O(t) (E83 availability rule)."""
    av = E.available(d, t)
    known = set(zip(av["province_code"], av["q"]))
    q = P["target_q"].map(L.qi)
    return P[[(p, qq) in known for p, qq in zip(P["province_code"], q)]]


def brier(D, a):
    ok = D[a].notna()
    return float(np.mean((D.loc[ok, a] - D.loc[ok, "y"]) ** 2)) if ok.any() else np.nan


def run(k: int, d) -> pd.DataFrame:
    P = pd.read_csv(E84_RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
    P["HYB-GBA-SIM"] = P["NA-GB"].fillna(P["S-SIM"])
    P["ENS-EQ"] = P[["S-SIM", "S-SIM-SEAS", "S-COMP"]].mean(axis=1, skipna=False)
    out = {c: [] for c in ("SEL-ROLL", "ENS-ROLL", "ENS-ROLL-ACC", "sel_arm", "thr", "past_q")}
    for i, r in P.iterrows():
        H = past(P, d, int(r["t"]))
        nq = H["target_q"].nunique()
        out["past_q"].append(nq)
        if nq >= MIN_Q:
            b = {a: brier(H, a) for a in POOL}
            b = {a: v for a, v in b.items() if np.isfinite(v)}
            sel = min(b, key=b.get)
            w = {a: 1 / max(v, 1e-6) for a, v in b.items()}
        else:
            sel, w = "S-SIM", {a: 1.0 for a in POOL}
        vals = {a: r[a] for a in w if pd.notna(r[a])}
        ens = sum(w[a] * v for a, v in vals.items()) / sum(w[a] for a in vals) if vals else np.nan
        thr = 0.5
        if nq >= MIN_Q:
            Hp = H.copy()
            num = sum(w[a] * Hp[a].fillna(0) for a in w)
            den = sum(w[a] * Hp[a].notna() for a in w).replace(0, np.nan)
            pe = num / den
            accs = {th: float(((pe >= th).astype(int) == Hp["y"])[pe.notna()].mean()) for th in GRID}
            thr = max(GRID, key=lambda th: (round(accs[th], 10), -abs(th - 0.5)))
        out["SEL-ROLL"].append(r[sel])
        out["ENS-ROLL"].append(ens)
        out["ENS-ROLL-ACC"].append(np.nan if pd.isna(ens) else (0.5 * ens / thr if ens < thr else 0.5 + 0.5 * (ens - thr) / (1 - thr)))
        out["sel_arm"].append(sel)
        out["thr"].append(thr)
    for c, v in out.items():
        P[c] = v
    return P


if __name__ == "__main__":
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = HERE.parent / "runs" / stamp
    o.mkdir(parents=True, exist_ok=True)
    d, _ = E.data()
    # arms are scored under the S- prefix the E83 evaluator recognises
    names = {"ENS-EQ": "S-ENS-EQ", "SEL-ROLL": "S-SEL-ROLL", "ENS-ROLL": "S-ENS-ROLL", "ENS-ROLL-ACC": "S-ENS-ROLL-ACC",
             "HYB-GBA-SIM": "HYB-GBA-SIM"}
    R.PRIMARY[:] = list(names.values()) + ["S-SIM", "S-COMP"]
    summ = {"stamp": stamp, "protocol_sha256": (HERE.parent / "PROTOCOL.sha256").read_text().split()[0], "leads": {}}
    for k in (1, 2):
        P = run(k, d).rename(columns=names)
        P.to_csv(o / f"predictions_k{k}.csv", index=False)
        res, tests = R.evaluate(P)
        summ["leads"][k] = {"metrics": {a: res[a] for a in R.PRIMARY + R.BASELINES if a in res}, "tests": tests,
                            "pass": {a: R.passes(res, tests, a) for a in R.PRIMARY},
                            "selected_arms": P.drop_duplicates("t")[["target_q", "sel_arm", "thr", "past_q"]].to_dict("records")}
        print(f"k={k}")
        for a in ["B-PERSIST", "B-CLIM", "B-AL"] + R.PRIMARY:
            m = res[a]["all_rows_unissued_wrong"]
            ps = summ["leads"][k]["pass"].get(a, {})
            th = {n.split(" vs ")[1]: round(v["p_holm"], 3) for n, v in tests.items() if n.startswith(a + " vs")}
            print(f"  {a:16s} acc={m['accuracy']:.3f} ({m['TP'] + m['TN']}/{m['n']}) bal={m['balanced_accuracy'] or 0:.3f} "
                  f"recH={m['recall_HIGH'] or 0:.2f} prec={m['precision'] or 0:.2f} brier={m['brier']:.3f} PASS={ps.get('PASS')} holm={th}",
                  flush=True)
        print("  selected:", [(r["target_q"], r["sel_arm"], r["thr"]) for r in summ["leads"][k]["selected_arms"]], flush=True)
    (o / "metrics.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8")
    print(o)
