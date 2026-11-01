"""Y3 development: H3b replica (Y3a, BL only), pooled regularised logistic on crossing (Y3b), ridge on the continuous
change (Y3c), all with issue-time covariates, vs RW, Leads 1 and 2, 2005-2020. Writes out/y3_dev_rows.csv.

    python -B run_dev.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import devrows  # noqa: E402
import hmodels as H  # noqa: E402
import p2lib as P  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def main():
    P.plan2_ok()
    import l2_lib as X
    X.U.setup()
    d = devrows.build({"H3B": lambda a, t, k, fa: H.h3b(t, k), "LOG": H.logit, "RDG": H.ridge},
                      leads=(1, 2), bl_only={"H3B"})
    OUT.mkdir(exist_ok=True)
    d.to_csv(OUT / "y3_dev_rows.csv", index=False, lineterminator="\n", float_format="%.5f")
    print(len(d), "rows; NaN:", d[["H3B", "LOG", "RDG"]].isna().sum().to_dict())


if __name__ == "__main__":
    main()
