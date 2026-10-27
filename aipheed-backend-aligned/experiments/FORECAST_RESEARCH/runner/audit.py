"""Reproduction audit (PROTOCOL section 4-5): pi_H under schedule A = FINAL_ARCHITECTURE pi_H4; Z0 = P5_price."""
import json

import numpy as np

import fr_lib as F


def main():
    F.check_protocol()
    E = F.eval_rows()
    ph = np.array([F.pi_h(F.issue(int(t), "A"), int(t) + int(k))["pi_H"] for t, k in zip(E["t"], E["lead"])])
    d_h = float(np.nanmax(np.abs(ph - E["pi_H4"].to_numpy())))
    origins = sorted(E["t"].unique())
    P = F.run_arm("Z0", origins).merge(E[["t", "lead", "province_code", "P5_price"]], on=["t", "lead", "province_code"])
    d_p = float(np.nanmax(np.abs(P["pi_P"] - P["P5_price"])))
    nan_p = int(P["pi_P"].isna().sum())
    res = {"max_abs_pi_H_vs_pi_H4": d_h, "max_abs_Z0_vs_P5": d_p, "Z0_nan": nan_p, "rows": len(P),
           "passed": d_h < 1e-6 and d_p < 1e-6}
    print(res)
    (F.OUT / "audit.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
