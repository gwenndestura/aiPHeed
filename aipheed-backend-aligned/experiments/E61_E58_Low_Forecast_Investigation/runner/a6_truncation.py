"""E61 A6: leakage test of the sealed E61 candidates. At every rolling origin, every input is truncated to what was
published before the issue date (E59 a2 `truncated_inputs`: CPI to month 2 of t, SWS posted before O(t), climate and
news to t, OFW and rice to t-1, policy orders announced before O(t)); features are rebuilt from the truncated data and
C2, C3, C23 and C4 are re-run. Each must equal its sealed value.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E61_E58_Low_Forecast_Investigation/runner/a6_truncation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e61_cands as C  # noqa: E402

X, np, pd, L, G, E = C.X, C.np, C.pd, C.L, C.G, C.E
sys.path.insert(0, str(X.EXP / "E59_E58_Validation_Audit" / "runner"))
import a2_timing as T  # noqa: E402  (E59's truncation helper; importing it runs nothing)


def main():
    S = pd.read_csv(X.SEALED_DIR / "candidates.csv", dtype={"province_code": str})
    if X.sha(X.SEALED_DIR / "candidates.csv") != (X.SEALED_DIR / "candidates.csv.sha256").read_text().split()[0]:
        raise SystemExit("sealed candidates changed")
    d, _, _ = E.load()
    space = G.search_space()
    out = []
    for t in sorted(S["t"].unique()):
        dc, Xc, Bc = T.truncated_inputs(d, int(t))
        g = S[S["t"] == t].set_index("province_code").loc[L.PROVS]
        for a in ("C2", "C3", "C23", "C4"):
            r = C.tuned(dc, Xc, Bc, int(t), a, space)
            diff = float(np.max(np.abs(r["p"] - g[f"{a}_p"].to_numpy())))
            out.append({"origin": L.qs(int(t)), "arm": a, "max_abs_diff": diff,
                        "same_config": int(r["cfg"]["id"]) == int(g[f"{a}_cfg"].iloc[0])})
        print(L.qs(int(t)), [(o["arm"], round(o["max_abs_diff"], 12), o["same_config"]) for o in out[-4:]], flush=True)
    R = pd.DataFrame(out)
    X.write_csv(R, X.TABLES / "a6_truncation_test.csv")
    ok = bool((R["max_abs_diff"] < 1e-9).all() and R["same_config"].all())
    X.dump({"all_identical": ok, "rows": out}, X.OUT / "a6_truncation.json")
    print("ALL IDENTICAL:", ok)


if __name__ == "__main__":
    main()
