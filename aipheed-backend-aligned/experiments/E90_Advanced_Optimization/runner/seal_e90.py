"""E90 prospective seal: HUN-RICE (frozen run_e90.hunger_rice) and its WARN level from origin 2026-Q3 (issued 2026-10-01,
data published by 2026-10-14) for 2026-Q4 (Lead 1) and 2027-Q1 (Lead 2). The price part is the S-COV/S-COMP price
probability at this origin (E84 features; identical to the E84 seal ad402660, which is only read). None of these
outcomes exists today (2026-10-22). Writes sealed/e90_prospective.csv and its SHA-256; never overwrites.

Run from backend/:  python .../seal_e90.py
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import run_e90 as R90

E, L, np, pd = R90.E, R90.L, R90.np, R90.pd
T0 = L.qi("2026-Q3")
E90_RUN = R90.HERE.parent / "runs" / "20261022T040445Z"


def warn_tau(d, k: int) -> float:
    """WARN threshold at O(T0): the PROTOCOL rule on E90 rows whose labels were published before O(T0)."""
    P = pd.read_csv(E90_RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
    av = E.available(d, T0)
    known = set(zip(av["province_code"], av["q"]))
    H = P[[(p, L.qi(q)) in known for p, q in zip(P["province_code"], P["target_q"])]]
    if H["target_q"].nunique() < 3:
        return 0.30

    def f2(tau):
        w = H["S-HUN-RICE"] >= tau
        tp = int((w & (H.y == 1)).sum()); fp = int((w & (H.y == 0)).sum()); fn = int((~w & (H.y == 1)).sum())
        return (5 * tp) / max(5 * tp + 4 * fn + fp, 1)
    return max(R90.TAUS, key=lambda x: (round(f2(x), 10), x))


if __name__ == "__main__":
    d, _ = E.data()
    rows = []
    for k in (1, 2):
        X = pd.read_csv(R90.E84_RUN / f"features_k{k}.csv", dtype={"province_code": str})
        if (X["t"] == T0).sum() == 0:
            raise SystemExit(f"no origin 2026-Q3 features for lead {k}")
        rice = X.groupby("t")["rice_yoy_now"].mean()
        hr = R90.hunger_rice(d, rice, T0, k)
        tau = warn_tau(d, k)
        te = X[X["t"] == T0].set_index("province_code").loc[L.PROVS].reset_index()
        for _, r in te.iterrows():
            p = hr["p"] * r["comp_p_price"]
            rows.append({"origin": "2026-10-01", "data_published_by": "2026-10-14", "lead": k, "target_q": L.qs(T0 + k),
                         "province_code": r["province_code"], "province": L.NAMES[r["province_code"]],
                         "S-HUN-RICE_p": p, "p_hunger_rice": hr["p"], "H_hat_rice": hr["H_hat"],
                         "beta_rice": hr["beta"], "pairs": hr["pairs"], "rice_yoy_region": float(rice[T0]),
                         "p_price_S-COV": r["comp_p_price"], "S-COV_p": r["comp_p"],
                         "S-HUN-RICE_decision": int(p >= 0.5), "warn_tau": tau,
                         "warn_level": "HIGH" if p >= 0.5 else "WATCH" if p >= tau else "LOW"})
    out = R90.HERE.parent / "sealed"
    out.mkdir(exist_ok=True)
    f = out / "e90_prospective.csv"
    if f.exists():
        raise SystemExit("sealed file exists; a seal is never overwritten")
    pd.DataFrame(rows).to_csv(f, index=False, lineterminator="\n")
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    (out / "e90_prospective.csv.sha256").write_text(f"{sha}  e90_prospective.csv\n"
                                                    f"sealed_at_utc {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")
    print(sha)
    print(pd.DataFrame(rows)[["lead", "target_q", "province", "S-HUN-RICE_p", "S-COV_p", "p_hunger_rice", "H_hat_rice",
                              "beta_rice", "warn_tau", "warn_level"]].round(3).to_string())
