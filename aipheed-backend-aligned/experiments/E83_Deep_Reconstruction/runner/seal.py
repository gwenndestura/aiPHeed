"""E83 prospective seal (PROTOCOL section 8): forecasts from origin 2026-Q3 (issued 2026-10-01, data published by
2026-10-14 under config/authorization.json) for targets 2026-Q4 (Lead 1), 2027-Q1 (Lead 2) and 2027-Q2 (Lead 3).
None of these outcomes exists today (2026-10-21). Writes sealed/e83_prospective.csv and its SHA-256.

Run from backend/:  python .../seal.py <run_dir>
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_round2 as R2  # noqa: E402

E, L, np, pd = R2.E, R2.L, R2.np, R2.pd
T0 = L.qi("2026-Q3")

if __name__ == "__main__":
    run = Path(sys.argv[1])
    d, x = E.data()
    rows = []
    for k in (1, 2, 3):
        X = pd.read_csv(run / f"features_r2_k{k}.csv", dtype={"province_code": str})
        if (X["t"] == T0).sum() == 0:
            raise SystemExit(f"no origin 2026-Q3 features for lead {k}")
        tr = E.pairs(X, d, T0, k)
        ts = R2.threshold(tr[tr["sim_p"].notna()], "sim_p")
        tss = R2.threshold(tr[tr["seas_p"].notna()], "seas_p")
        te = X[X["t"] == T0].set_index("province_code").loc[L.PROVS].reset_index()
        st, fitted = R2.stack(tr, te, [])
        for i, p in enumerate(L.PROVS):
            r = te.iloc[i]
            rows.append({"origin": "2026-10-01", "data_published_by": "2026-10-14", "lead": k, "target_q": L.qs(T0 + k),
                         "province_code": p, "province": L.NAMES[p],
                         "S-SIM_p": r["sim_p"], "S-SIM_p_hunger": r["sim_p_hunger"], "S-SIM_p_price": r["sim_p_price"],
                         "S-SIM_decision": int(r["sim_p"] >= 0.5),
                         "S-SIM-THR_threshold": ts, "S-SIM-THR_decision": int(r["sim_p"] >= ts),
                         "S-SIM-SEAS_p": r["seas_p"], "S-SIM-SEAS-THR_threshold": tss,
                         "S-SIM-SEAS-THR_decision": int(r["seas_p"] >= tss), "ST-LR_p": st[i], "ST-LR_fitted": fitted,
                         "B-STATE_inputs_F_now": r["F_now"], "B-STATE_inputs_gap_now": r["gap_now"],
                         "H_last": r["H_last"]})
    out = E.E83 / "sealed"
    out.mkdir(exist_ok=True)
    f = out / "e83_prospective.csv"
    if f.exists():
        raise SystemExit("sealed file exists; a seal is never overwritten")
    pd.DataFrame(rows).to_csv(f, index=False, lineterminator="\n")
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    (out / "e83_prospective.csv.sha256").write_text(f"{sha}  e83_prospective.csv\n"
                                                    f"sealed_at_utc {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")
    print(sha)
    print(pd.DataFrame(rows)[["lead", "target_q", "province", "S-SIM_p", "S-SIM-THR_threshold", "S-SIM-THR_decision",
                              "S-SIM-SEAS_p"]].round(3).to_string())
