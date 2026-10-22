"""E90 run (PROTOCOL.md): HUN-RICE and the WARN tier on the E89 rows (Leads 1, 2). Run from backend/."""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
for p in ("E89_Model_Optimization", "E83_Deep_Reconstruction"):
    sys.path.insert(0, str(EXP / p / "runner"))
import e83_lib as E  # noqa: E402
import run_e83 as R  # noqa: E402
import run_e89 as R9  # noqa: E402

L, np, pd = E.L, E.np, E.pd
from scipy.stats import norm  # noqa: E402

E89_RUN = EXP / "E89_Model_Optimization" / "runs" / "20261022T033435Z"
E84_RUN = EXP / "E84_Objective_Continuation" / "runs" / "20261021T093234Z"
LINE, SHRINK, MIN_PAIRS = 11.3, 4.0, 6
TAUS = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45]


def hunger_series(d, t):
    hq = L.h_quarters(d.cut(t)).sort_values("q")
    return hq["q"].to_numpy(), hq["H"].to_numpy()


def hunger_rice(d, rice: pd.Series, t: int, k: int) -> dict:
    qq, hh = hunger_series(d, t)
    sig = float(np.sqrt(np.mean((np.diff(hh) / np.sqrt(np.diff(qq))) ** 2)))
    s_rw = sig * math.sqrt(max(t + k - int(qq[-1]), 1))
    H_last = float(hh[-1])
    posted = dict(zip(qq, hh))
    pairs = []
    for tp in rice.index:
        q = tp + k
        if tp >= t or q not in posted or pd.isna(rice.get(tp)):
            continue
        qp, hp = hunger_series(d, tp)
        if not len(hp):
            continue
        pairs.append((float(rice[tp]), posted[q] - float(hp[-1])))
    a = b = 0.0
    s = s_rw
    if len(pairs) >= MIN_PAIRS and pd.notna(rice.get(t)):
        x = np.array([p[0] for p in pairs])
        y = np.array([p[1] for p in pairs])
        xm, ym = x.mean(), y.mean()
        b = max(0.0, float(((x - xm) * (y - ym)).sum() / max(((x - xm) ** 2).sum(), 1e-9)))
        b *= len(pairs) / (len(pairs) + SHRINK)
        a = ym - b * xm
        rmse = float(np.sqrt(np.mean((y - (a + b * x)) ** 2)))
        s = max(s_rw, rmse)
        Hh = H_last + a + b * float(rice[t])
    else:
        Hh = H_last
    return {"p": float(1 - norm.cdf((LINE - Hh) / s)), "H_hat": Hh, "beta": b, "pairs": len(pairs)}


def run(k: int, d) -> pd.DataFrame:
    P = pd.read_csv(E89_RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
    X = pd.read_csv(E84_RUN / f"features_k{k}.csv", dtype={"province_code": str})
    rice = X.groupby("t")["rice_yoy_now"].mean()
    hr = {t: hunger_rice(d, rice, int(t), k) for t in sorted(P["t"].unique())}
    P["p_hunger_rice"] = P["t"].map(lambda t: hr[t]["p"])
    P["H_hat_rice"] = P["t"].map(lambda t: hr[t]["H_hat"])
    P["beta_rice"] = P["t"].map(lambda t: hr[t]["beta"])
    P["S-HUN-RICE"] = P["p_hunger_rice"] * P["p_price_raw"]
    # WARN tier: tau from earlier rows whose labels were published before O(t)
    taus = []
    for t in P["t"]:
        av = E.available(d, int(t))
        known = set(zip(av["province_code"], av["q"]))
        H = P[[(p, L.qi(q)) in known for p, q in zip(P["province_code"], P["target_q"])]]
        if H["target_q"].nunique() < 3:
            taus.append(0.30)
            continue
        def f2(tau):
            w = H["S-HUN-RICE"] >= tau
            tp = int((w & (H.y == 1)).sum()); fp = int((w & (H.y == 0)).sum()); fn = int((~w & (H.y == 1)).sum())
            return (5 * tp) / max(5 * tp + 4 * fn + fp, 1)
        taus.append(max(TAUS, key=lambda x: (round(f2(x), 10), x)))
    P["warn_tau"] = taus
    P["warn_level"] = np.where(P["S-HUN-RICE"] >= 0.5, "HIGH", np.where(P["S-HUN-RICE"] >= P["warn_tau"], "WATCH", "LOW"))
    return P


def breakdowns(P, arm, d, k):
    yh = np.where(P[arm].notna(), (P[arm] >= 0.5).astype(int), 1 - P["y"])
    P = P.assign(yh=yh, c=(yh == P["y"]).astype(int))
    prov = {L.NAMES[p]: {"correct": int(g.c.sum()), "n": len(g), "high": int(g.y.sum()),
                         "caught": int(((g.yh == 1) & (g.y == 1)).sum())} for p, g in P.groupby("province_code")}
    hq = L.h_quarters(d).set_index("q")["H"]
    last = {t: hunger_series(d, int(t))[1][-1] for t in P["t"].unique()}
    P["dH"] = [hq.get(L.qi(q), np.nan) - last[t] for q, t in zip(P["target_q"], P["t"])]
    wors = P["dH"] >= 3
    per = {}
    for nm, m in (("worsening", wors), ("ordinary", ~wors)):
        D = P[m]
        per[nm] = {"rows": int(len(D)), "quarters": int(D["target_q"].nunique()), "correct": int(D.c.sum()),
                   "high": int(D.y.sum()), "caught": int(((D.yh == 1) & (D.y == 1)).sum()),
                   "false_high": int(((D.yh == 1) & (D.y == 0)).sum())}
    return {"by_province": prov, "by_condition": per, "issued": int(P[arm].notna().sum())}


if __name__ == "__main__":
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = HERE.parent / "runs" / stamp
    o.mkdir(parents=True, exist_ok=True)
    d, _ = E.data()
    arms = ["S-HUN-RICE", "S-COV", "S-SIM", "HYB-GBA-SIM"]
    R.PRIMARY[:] = arms
    summ = {"stamp": stamp, "protocol_sha256": (HERE.parent / "PROTOCOL.sha256").read_text().split()[0], "leads": {}}
    for k in (1, 2):
        P = run(k, d)
        P.to_csv(o / f"predictions_k{k}.csv", index=False)
        res, tests = R.evaluate(P)
        gen = {a: R9.quarter_generalization(P, a) for a in arms}
        bd = {a: breakdowns(P, a, d, k) for a in arms}
        w = P["warn_level"]
        warn = {"high_or_watch": int((w != "LOW").sum()), "caught": int(((w != "LOW") & (P.y == 1)).sum()),
                "missed_high": int(((w == "LOW") & (P.y == 1)).sum()), "false_alarms": int(((w != "LOW") & (P.y == 0)).sum()),
                "watch": int((w == "WATCH").sum())}
        summ["leads"][k] = {"metrics": {a: res[a] for a in arms + R.BASELINES if a in res}, "tests": tests,
                            "pass": {a: R.passes(res, tests, a) for a in arms}, "generalization": gen, "breakdowns": bd,
                            "warn": warn, "beta_by_origin": P.drop_duplicates("t")[["target_q", "beta_rice"]].round(3).values.tolist()}
        print(f"k={k}")
        for a in ["B-PERSIST", "B-AL"] + arms:
            m = res[a]["all_rows_unissued_wrong"]
            g = gen.get(a, {})
            th = {n.split(" vs ")[1]: round(v["p_holm"], 3) for n, v in tests.items() if n.startswith(a + " vs")}
            print(f"  {a:12s} acc={m['accuracy']:.3f} ({m['TP'] + m['TN']}/65) bal={m['balanced_accuracy'] or 0:.3f} "
                  f"TP/FP/FN={m['TP']}/{m['FP']}/{m['FN']} brier={m['brier']:.3f} PASS={summ['leads'][k]['pass'].get(a, {}).get('PASS')} "
                  f"holm={th} | W/L/T={g.get('wins')}/{g.get('losses')}/{g.get('ties')} {g.get('verdict', '')}", flush=True)
        print("  HUN-RICE by condition:", bd["S-HUN-RICE"]["by_condition"], flush=True)
        print("  current by condition: ", bd["S-COV" if k == 2 else "S-SIM"]["by_condition"], flush=True)
        print("  HUN-RICE by province:", bd["S-HUN-RICE"]["by_province"], flush=True)
        print("  WARN:", warn, flush=True)
        print("  beta by target:", summ["leads"][k]["beta_by_origin"], flush=True)
    (o / "metrics.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8")
    print(o)
