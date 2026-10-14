"""E32 exploratory (PROTOCOL section 2): would a defensible alternative target let provinces be told apart?
Reported only; the approved T1 is not replaced. Same lead-1 dates and the same publication-aware rules.

  T1  approved: S1(T) > tau at the origin
  TR  "rising": S1(T) > S1 of the latest labelled quarter published at the origin (Chapter I 1.2, "most likely to be
      rising")
  T2  price pressure: D(T) > 0 (constructed provincial price indicator, not food insecurity)

For each target: class balance, quarters where all five provinces share the label (no provincial discrimination),
and the scores of persistence, climatology and the E32/PCF21 machinery where it applies.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e32_common as C  # noqa: E402
import e32_lib as L  # noqa: E402

np, pd, P = C.np, C.pd, C.P


def main():
    d = L.Data()
    recs = []
    for target in range(C.qk("2023-Q4"), C.qk("2026-Q3") + 1):
        t = target - 1
        if any(d.Sv.get((p, target)) is None for p in C.PROVS):
            continue
        X = d.features(t, 1).set_index("province_code")
        lastq = X["last_label_quarter"].iloc[0]
        for p in C.PROVS:
            s = d.Sv[(p, target)]
            s_last = d.Sv.get((p, C.qk(lastq)))
            Dt = d.Dm.get((p, target))
            recs.append({"target": C.qs(target), "p": p, "T1": int(s > d.tau(t)), "TR": int(s > s_last),
                         "T2": int(Dt > 0), "T2_last": int(X.loc[p, "D_last"] > 0),
                         "TR_persist": None})
    R = pd.DataFrame(recs)
    # persistence for TR: last observed direction (latest labelled quarter vs the one before it, both published)
    out = {}
    for tg in ("T1", "TR", "T2"):
        g = R.groupby("target")[tg].agg(["sum", "count"])
        out[tg] = {"rows": int(len(R)), "HIGH": int(R[tg].sum()), "LOW": int((1 - R[tg]).sum()),
                   "HIGH_share": float(R[tg].mean()),
                   "quarters_all_same_label": int(((g["sum"] == 0) | (g["sum"] == g["count"])).sum()),
                   "quarters": int(len(g)), "always_majority_accuracy": float(max(R[tg].mean(), 1 - R[tg].mean()))}
    out["T2"]["persistence_accuracy"] = float((R["T2"] == R["T2_last"]).mean())
    C.write_json(C.E32 / "runs" / "e32_alt_targets.json", C.clean(out))
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
