"""E91 round 2 (PROTOCOL section 7: POST-HOC, reported as such, never defines the validated K). Run from backend/.

U-GB-NOPRICE  the selected U-GB without the price/market driver group (the round-1 ablation lowered Brier when it was
              dropped; the structural core already carries the price information).
U-HR          the structural core with one pooled rice-led hunger drift for every horizon:
              H(t+k) - H_last = k * (a + b * max(rice YoY, 0)), fitted by OLS on the pooled posted pairs of K = 1..3 at O(t)
              (b >= 0, shrunk by n/(n+4), >= 6 pairs, else the random walk); P(H > 11.3) uses the larger of the walk sd and
              the residual RMSE; times the unchanged core price probability. Selection-informed (E90 diagnostic).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_e91 as U  # noqa: E402

E, L, np, pd = U.E, U.L, U.np, U.pd
from scipy.stats import norm  # noqa: E402

RUN = Path(sys.argv[1])
KH = (1, 2, 3)


def hseries(d, t):
    hq = L.h_quarters(d.cut(t)).sort_values("q")
    return hq["q"].to_numpy(), hq["H"].to_numpy()


def p_hunger_hr(d, rice: dict, t: int, k: int) -> float:
    qq, hh = hseries(d, t)
    sig = float(np.sqrt(np.mean((np.diff(hh) / np.sqrt(np.diff(qq))) ** 2)))
    s = sig * math.sqrt(max(t + k - int(qq[-1]), 1))
    posted = dict(zip(qq, hh))
    xs, ys, ks = [], [], []
    for kk in KH:
        for tp, r in rice[kk].items():
            q = tp + kk
            if tp >= t or q not in posted or not np.isfinite(r):
                continue
            hp = hseries(d, tp)[1]
            if len(hp):
                xs.append(max(r, 0.0)); ys.append(posted[q] - float(hp[-1])); ks.append(kk)
    Hh = float(hh[-1])
    r_now = rice[min(k, 3)].get(t, np.nan)
    if len(xs) >= 6 and np.isfinite(r_now):
        X = np.column_stack([np.array(ks, float), np.array(ks, float) * np.array(xs)])
        y = np.array(ys)
        a, b = np.linalg.lstsq(X, y, rcond=None)[0]
        b = max(0.0, b) * len(xs) / (len(xs) + 4)
        a = float(np.mean((y - b * X[:, 1]) / X[:, 0]))
        rmse = float(np.sqrt(np.mean((y - X[:, 0] * a - b * X[:, 1]) ** 2)))
        s = max(s, rmse)
        Hh += k * (a + b * max(r_now, 0.0))
    return float(1 - norm.cdf((U.TH["H"] - Hh) / s))


if __name__ == "__main__":
    d, _ = E.data()
    pv = U.pov_values()
    T, Ps = U.load_tables()
    kind, cols, init = U.SPECS["U-GB"]
    specs = {"U-GB-NOPRICE": (kind, [c for c in cols if c not in U.GROUPS["prices"]], init)}
    Ux = U.unified(T, Ps, d, pv, specs)
    rice = {k: T[k].groupby("t")["rice_yoy_now"].mean().to_dict() for k in KH}
    out = {}
    for k in U.KS:
        P = pd.read_csv(RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
        P["U-GB-NOPRICE"], P["U-GB-NOPRICE_fitted"] = Ux[k]["U-GB-NOPRICE"].to_numpy(), Ux[k]["U-GB-NOPRICE_fitted"].to_numpy()
        ph = {t: p_hunger_hr(d, rice, int(t), k) for t in P["t"].unique()} if k in KH else {}
        T_k = T[k].set_index(["t", "province_code"])
        P["U-HR"] = [ph[t] * T_k.loc[(t, p), "comp_p_price"] if k in KH else np.nan for t, p in zip(P["t"], P["province_code"])]
        P.to_csv(RUN / f"predictions_round2_k{k}.csv", index=False)
        arms = ["U-GB", "U-GB-NOPRICE", "U-HR", "U-STRUCT"]
        r, base = U.evaluate_k(P, arms)
        out[k] = r
        print(f"k={k}")
        for a in arms:
            m, g, ps = r[a]["metrics"], r[a]["generalization"], r[a]["pass"]
            th = {b: round(v.get("p_holm", 1), 3) for b, v in r[a]["tests"].items()}
            print(f"  {a:13s} acc={m['accuracy']:.3f} bal={m['balanced_accuracy'] or 0:.3f} R={m['recall_HIGH'] or 0:.2f} "
                  f"TP/FP/FN={m['TP']}/{m['FP']}/{m['FN']} brier={m['brier']:.3f} PASS={ps['PASS']} "
                  f"{[c for c, v in ps.items() if not v and c not in ('PASS', 'TARGET_80')]} holm={th} "
                  f"early/late={g['early_acc']:.2f}/{g['late_acc']:.2f}", flush=True)
    K = {a: U.k_validated(out, a) for a in ["U-GB", "U-GB-NOPRICE", "U-HR", "U-STRUCT"]}
    print("candidate K (post-hoc):", {a: v["K"] for a, v in K.items()})
    (RUN / "round2_posthoc.json").write_text(json.dumps({"per_k": out, "K_posthoc": K}, indent=1, default=float), encoding="utf-8")
