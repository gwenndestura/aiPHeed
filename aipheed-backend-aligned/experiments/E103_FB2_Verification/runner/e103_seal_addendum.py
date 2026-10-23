"""E103 seal ADDENDUM (written after e103_run.py was scored; not part of the frozen protocol). Seals, before any of these
SWS rounds is posted, the regional values of SERVED, FB2, REL-only and S-noA for the targets that have no outcome yet
(Lead 1: 2026-Q4; Lead 2: 2026-Q4, 2027-Q1), so the arms that emerged in E103 can be tested on unseen quarters without
being adopted. Writes ../out/sealed_addendum.csv (+ .sha256)."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e103_run as E  # noqa: E402

L, R, E101, np, pd, qi = E.L, E.R, E.E101, E.np, E.pd, E.qi


def main():
    E.verify()
    H = R.load_history()
    out_h = R.outcome_series()
    rel101 = E101.rel_scores(R.level_indicator())
    S63 = pd.read_csv(E101.E63, dtype={"province_code": str})
    a1_63 = {(int(r.lead), int(r.t), r.province_code): float(r.E56_p_price) for r in S63.itertuples()}
    cpi = L.load_cpi()
    PNL = L.panel(cpi, list(range(qi("2021-Q2"), qi("2026-Q3") + 1)))
    pct = {k: L.percentiles({key: v[k] for key, v in PNL.items()}) for k in ("REL", "PERS")}
    rows_out = []
    for lead in (1, 2):
        rows = E101.lead_rows(H, lead, a1_63, rel101)

        def with_A(fn):
            return [{**x, "dom": {**x["dom"], "A": fn(x)}} for x in rows]
        m = lambda v: (float(np.mean([x for x in v if x is not None])) if any(x is not None for x in v) else None)  # noqa: E731
        R.MIN_DOMAINS = 4
        arms = {"SERVED": E101.served_equal(rows, lead)[0],
                "FB2": E101.served_equal(with_A(lambda x: m([x["s"]["A1"], pct["REL"].get((x["t"], x["code"])),
                                                              pct["PERS"].get((x["t"], x["code"]))])), lead)[0],
                "REL-only": E101.served_equal(with_A(lambda x: pct["REL"].get((x["t"], x["code"]))), lead)[0]}
        R.MIN_DOMAINS = 3
        arms["S-noA"] = E101.served_equal(rows, lead, doms=[d for d in R.DOMS if d != "A"])[0]
        R.MIN_DOMAINS = 4
        for q in sorted({x["target"] for x in rows if x["target"] not in out_h and qi(x["target"]) > qi("2026-Q3")}, key=qi):
            rec = {"lead": lead, "target": q}
            for a, v in arms.items():
                vals = [v.get((q, p)) for p in L.PROVS if v.get((q, p)) is not None]
                rec[a] = float(np.mean(vals)) if vals else None
            rows_out.append(rec)
    S = pd.DataFrame(rows_out)
    blob = S.to_csv(index=False, lineterminator="\n", float_format="%.6f").encode()
    (E.OUT / "sealed_addendum.csv").write_bytes(blob)
    (E.OUT / "sealed_addendum.csv.sha256").write_text(hashlib.sha256(blob).hexdigest() + "  sealed_addendum.csv\n")
    print(blob.decode(), hashlib.sha256(blob).hexdigest())


if __name__ == "__main__":
    main()
