"""Snapshot of the served model's own inputs (LEAD2_OPTIMIZATION: U.stack(K) + add_fe, UNI-FINAL U2 columns) and the
price labels known before each origin (U.train_rows), so every LEAD2_FIVE_TRIGGER run uses the served data exactly.

    python snapshot_l2.py       # ../data/stack_l2.csv, ../data/known_price_l2.csv, ../data/meta_l2.json
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))
import run_l2 as R  # noqa: E402

X, U, L, pd = R.X, R.U, R.L, R.pd
DATA = HERE.parent / "data"


def main():
    t0 = time.time()
    U.setup()
    K = R._K()
    S = X.add_fe(U.stack(K))
    S.to_csv(DATA / "stack_l2.csv", index=False, lineterminator="\n", float_format="%.10g")
    kn = []
    for t in sorted(S["t"].unique()):
        tr = U.train_rows(S, int(t))[["province_code", "q", "y"]].drop_duplicates()
        kn.append(tr.assign(t=int(t)))
    pd.concat(kn, ignore_index=True).to_csv(DATA / "known_price_l2.csv", index=False, lineterminator="\n")
    meta = {"K": K, "origins": [int(t) for t in R._origins()], "cols_U2": U.cols("U2"), "rows": len(S),
            "seconds": round(time.time() - t0)}
    (DATA / "meta_l2.json").write_text(json.dumps(meta, indent=1))
    print(meta)


if __name__ == "__main__":
    main()
