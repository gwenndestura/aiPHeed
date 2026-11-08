"""FORECAST_RESEARCH snapshot: the served-model feature table (FINAL_ARCHITECTURE build, every lead), the T43c labels
with their hunger and price parts, the BL SWS rounds, and the FINAL_ARCHITECTURE evaluation rows, written once so the
experiments below run on identical inputs.

    python snapshot.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FR = HERE.parent
EXP = FR.parent
DATA = FR / "data"
sys.path.insert(0, str(EXP / "FINAL_ARCHITECTURE" / "runner"))
import final_lib as F  # noqa: E402

O, X, U, C, FM, B, E, L, np, pd = F.O, F.X, F.U, F.C, F.FM, F.B, F.E, F.L, F.np, F.pd
RL = O.A4.RL


def main():
    t0 = time.time()
    U.setup()
    K = RL._K()
    S = F.build(K)
    S.to_csv(DATA / "stack.csv", index=False, lineterminator="\n", float_format="%.8g")
    lab = C.labels()
    lab.to_csv(DATA / "labels_t43c.csv", index=False, lineterminator="\n", float_format="%.8g")
    r = FM.rounds("primary")
    r.to_csv(DATA / "sws_rounds_primary.csv", index=False, lineterminator="\n")
    # labels known before each origin's issue date (for training-row eligibility)
    kn = []
    for t in sorted(S["t"].unique()):
        k = C.known_t43c(int(t))[["province_code", "q", "y"]].assign(t=int(t))
        kn.append(k)
        p = U.train_rows(S, int(t))[["province_code", "q", "y"]].drop_duplicates().assign(t=int(t))
        kn.append(p.rename(columns={"y": "y_price"}))
    pd.concat(kn, ignore_index=True).to_csv(DATA / "known_by_origin.csv", index=False, lineterminator="\n")
    meta = {"K": K, "origins": [L.qs(int(t)) for t in RL._origins()], "origins_t": [int(t) for t in RL._origins()],
            "issue": {L.qs(int(t)): E.issue(int(t)) for t in sorted(S["t"].unique())},
            "cols_S3": O.cols("S3"), "family": F.FAMILY, "dev_last": int(U.DEV_LAST),
            "rows": len(S), "seconds": round(time.time() - t0)}
    (DATA / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: v for k, v in meta.items() if k not in ("family", "issue")}, indent=0)[:1500])


if __name__ == "__main__" and len(sys.argv) == 1:
    main()


def extra():
    """Realised quarterly food and headline YoY for every complete CPI quarter (continuous price targets)."""
    U.setup()
    ps = B.ps_frame(E.data()[0])
    ps.to_csv(DATA / "ps_full.csv", index=False, lineterminator="\n", float_format="%.8g")
    print(len(ps), ps["q"].min(), ps["q"].max())


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "extra":
    extra()
