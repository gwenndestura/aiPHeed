"""E91 prospective seal (PROTOCOL section 7): the selected unified model U-GB from origin 2026-Q3 (issued 2026-10-01,
data published by 2026-10-14) for 2026-Q4, 2027-Q1 and 2027-Q2 (K = 1..3; K = 4 is not issued by the structural core).
One model fitted on the pooled multi-horizon pairs posted before O(2026-Q3). U-STRUCT equals S-COV here and is already
in the E84 seal ad402660, which is only read. Writes sealed/e91_prospective.csv and its SHA-256; never overwrites.

Run from backend/:  python .../seal_e91.py
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import run_e91 as U

E, L, np, pd = U.E, U.L, U.np, U.pd
T0 = L.qi("2026-Q3")

if __name__ == "__main__":
    d, _ = E.data()
    pv = U.pov_values()
    T, _ = U.load_tables()
    kind, cols, init = U.SPECS["U-GB"]
    tr = U.design(U.pooled_pairs(T, d, T0), pv)
    tr = tr[tr["comp_p"].notna()]
    assert U.eligible(tr)
    assert (tr["q"] <= T0 - 1).all()
    rows = []
    for k in (1, 2, 3):
        te = U.design(T[k][T[k]["t"] == T0].set_index("province_code").loc[L.PROVS].reset_index().assign(k=k), pv)
        p = U.fit_predict(kind, cols, init, tr, te)
        for i, r in te.iterrows():
            rows.append({"origin": "2026-10-01", "data_published_by": "2026-10-14", "K": k, "target_q": L.qs(T0 + k),
                         "province_code": r["province_code"], "province": L.NAMES[r["province_code"]],
                         "U-GB_p": float(p[i]), "U-GB_decision": int(p[i] >= 0.5), "U-STRUCT_p": r["comp_p"],
                         "p_hunger_core": r["comp_p_hunger"], "p_price_core": r["comp_p_price"],
                         "train_pairs": len(tr), "train_quarters": int(tr["q"].nunique()), "train_high": int(tr["y"].sum())})
    out = U.E91 / "sealed"
    out.mkdir(exist_ok=True)
    f = out / "e91_prospective.csv"
    if f.exists():
        raise SystemExit("sealed file exists; a seal is never overwritten")
    pd.DataFrame(rows).to_csv(f, index=False, lineterminator="\n")
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    (out / "e91_prospective.csv.sha256").write_text(f"{sha}  e91_prospective.csv\n"
                                                    f"sealed_at_utc {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")
    print(sha)
    print(pd.DataFrame(rows)[["K", "target_q", "province", "U-GB_p", "U-GB_decision", "U-STRUCT_p"]].round(3).to_string())
