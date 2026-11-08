"""Diagnostic (post-hoc, labelled): in the single model the A1 projection enters twice, as Market columns and through the
structural offset. The protocol's group ablation removes only the columns. This removes Market columns AND the offset
(and, separately, only the offset), refitting at every origin, to measure the full weight of price information.

    python market_full_removal.py [candidate]   # out/market_full_removal_<cand>.json
"""
import sys

import importlib.util
from pathlib import Path

import final_lib as F

# load this folder's run_final explicitly (another experiment folder on sys.path has a module of the same name)
_spec = importlib.util.spec_from_file_location("fa_run_final", Path(__file__).resolve().parent / "run_final.py")
RF = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RF)

O, U, FM, L, np, pd = F.O, F.U, F.FM, F.L, F.np, F.pd
RL = O.A4.RL


class NoOffset(F.FOne):
    def __init__(self, cfg, cols):
        super().__init__(cfg, cols)
        self.use_offset = False


def refit(S, cols, name):
    orig = F.FOne
    F.FOne = NoOffset
    try:
        return RF._refit(S, cols, name)
    finally:
        F.FOne = orig


def main():
    cand = sys.argv[1] if len(sys.argv) > 1 else "C"
    U.setup()
    S = F.build(RL._K())
    D = pd.read_csv(F.OUT / "predictions.csv", dtype={"province_code": str})
    cols = F.CANDS[cand]
    market = F.group_cols(cols, {"A1", "A2", "A3"})
    out = {"candidate": cand, "full": RF._stats(D, f"{cand}_p"), "variants": {}}
    for vname, keep in (("without offset (Market columns kept)", cols),
                        ("without Market columns and without offset", [c for c in cols if c not in market])):
        A = D.merge(refit(S, keep, "mf"), on=["t", "lead", "province_code"], how="left")
        st = RF._stats(A, "mf_p")
        for k in (1, 2, 3):
            st[k]["brier_full_minus_ablated"] = RF._diff(A, f"{cand}_p", "mf_p", k)
        out["variants"][vname] = {str(k): v for k, v in st.items()}
        print(vname, {k: (round(v["acc"], 3), round(v["brier"], 4), round(v["brier_full_minus_ablated"]["diff"], 4),
                          [round(x, 4) for x in v["brier_full_minus_ablated"]["ci90"]]) for k, v in st.items()}, flush=True)
    FM.write_json(F.OUT / f"market_full_removal_{cand}.json", out)


if __name__ == "__main__":
    main()
