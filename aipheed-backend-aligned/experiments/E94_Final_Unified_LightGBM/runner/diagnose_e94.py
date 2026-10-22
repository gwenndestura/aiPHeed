"""E94 diagnostics (descriptive; change no rule). Run from backend/:  python .../diagnose_e94.py <run_dir>

1. Pre-onset audit: at the K = 2 and K = 1 origins before the 2023-Q4 and 2024-Q2 transitions, each regional origin-time
   feature's z-score against its own history at earlier origins (from 2021-Q2), i.e. information available at O(t).
2. Conflict table: rows where the hunger component is high (>= 0.5) but the price signal is falling (dF1 < 0), with
   outcomes and false-alarm counts for the selected arm.
3. Per-quarter Brier gains of the selected arm against persistence and climatology at K = 1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_e94 as A  # noqa: E402

B, L, np, pd = A.B, A.L, A.np, A.pd
RUN = Path(sys.argv[1])
ONSETS = {"2023-Q4": {"K2": "2023-Q2", "K1": "2023-Q3"}, "2024-Q2": {"K2": "2023-Q4", "K1": "2024-Q1"}}


def audit(T1):
    num = [c for c in T1.columns if c not in ("province_code", "t") and pd.api.types.is_numeric_dtype(T1[c])]
    R = T1.groupby("t")[num].mean().sort_index()
    out = {}
    for target, origins in ONSETS.items():
        for lab, oq in origins.items():
            t = L.qi(oq)
            hist = R[R.index < t]
            z = ((R.loc[t] - hist.mean()) / hist.std(ddof=1).replace(0, np.nan)).dropna()
            top = z.abs().sort_values(ascending=False).head(12)
            out[f"{target} {lab} (origin {oq})"] = {c: {"value": round(float(R.loc[t, c]), 3), "z": round(float(z[c]), 2),
                                                        "n_hist": int(hist[c].notna().sum())} for c in top.index}
    return out


if __name__ == "__main__":
    m = json.loads((RUN / "metrics.json").read_text(encoding="utf-8"))
    sel = m["selected"]
    T = B.tables()
    res = {"selected": sel, "pre_onset_audit": audit(T[1])}
    conf = {}
    for k in (1, 2):
        P = pd.read_csv(RUN / f"predictions_k{k}.csv", dtype={"province_code": str})
        P = P.merge(T[k][["t", "province_code", "dF1"]], on=["t", "province_code"], how="left")
        c = (P["ph"] >= 0.5) & (P["dF1"] < 0)
        conf[k] = {"rows": int(c.sum()), "high": int(P.loc[c, "y"].sum()),
                   "false_high_selected": int(((P[sel] >= 0.5) & (P["y"] == 0) & c).sum()),
                   "false_high_selected_elsewhere": int(((P[sel] >= 0.5) & (P["y"] == 0) & ~c).sum())}
    res["conflict"] = conf
    P = pd.read_csv(RUN / "predictions_k1.csv", dtype={"province_code": str})
    res["k1_quarter_brier_gain"] = {b: P.assign(g=(P[b] - P.y) ** 2 - (P[sel] - P.y) ** 2).groupby("target_q")["g"].mean().round(3).to_dict()
                                    for b in ("B-PERSIST", "B-CLIM")}
    (RUN / "diagnostics.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, v in res["pre_onset_audit"].items():
        print(k, {c: (x["value"], x["z"]) for c, x in list(v.items())[:8]})
    print("conflict", conf)
    print("K1 quarter Brier gains", res["k1_quarter_brier_gain"])
