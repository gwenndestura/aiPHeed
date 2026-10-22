"""E90 diagnostic: did any indicator available at the forecast origin precede the regional hunger changes?
For each SWS target quarter q and lead k: hunger change dH = H(q) - latest H posted before O(q-k), against regional
means of each driver's origin-time features (E84 feature tables). Run from backend/."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "E83_Deep_Reconstruction" / "runner"))
import e83_lib as E  # noqa: E402

L, np, pd = E.L, E.np, E.pd
from scipy.stats import spearmanr  # noqa: E402

RUN = EXP / "E84_Objective_Continuation" / "runs" / "20261021T093234Z"
FEATS = {"Market: food YoY now": "F_now", "Market: rice YoY now": "rice_yoy_now", "Market: rice 3-mo momentum": "rice_mom3",
         "Market: world rice 6-mo change": "w_rice_chg6", "Market: projected food YoY": "comp_F_hat",
         "Employment: unemployment change": "ur_yoy", "Employment: underemployment": "under_last",
         "Climate: typhoons in quarter": "tc_count", "Climate: ENSO phase": "enso",
         "OFW: remittance YoY": "remit_usd_yoy", "Agri: palay YoY": "palay_yoy", "Fish: fisheries YoY": "fish_yoy"}

if __name__ == "__main__":
    d, _ = E.data()
    hq = L.h_quarters(d).set_index("q")["H"]
    out, rows = {}, []
    for k in (1, 2):
        X = pd.read_csv(RUN / f"features_k{k}.csv", dtype={"province_code": str})
        reg = X.groupby("t")[[c for c in FEATS.values() if c in X]].mean()
        for q, H in hq.items():
            t = q - k
            if t not in reg.index:
                continue
            c = L.h_quarters(d.cut(t)).sort_values("q")
            if not len(c):
                continue
            r = {"lead": k, "target_q": L.qs(q), "origin": str(L.origin(t).date()), "H_last": float(c["H"].iloc[-1]),
                 "H_last_q": L.qs(int(c["q"].iloc[-1])), "H": float(H), "dH": float(H - c["H"].iloc[-1]),
                 "crossed_up": bool(c["H"].iloc[-1] <= 11.3 < H)}
            r.update({nm: float(reg.loc[t, col]) if col in reg and pd.notna(reg.loc[t, col]) else None for nm, col in FEATS.items()})
            rows.append(r)
        D = pd.DataFrame([r for r in rows if r["lead"] == k])
        cor = {}
        for nm in FEATS:
            s = D[["dH", nm]].dropna()
            if len(s) >= 8:
                rho, p = spearmanr(s["dH"], s[nm])
                cor[nm] = {"n": len(s), "rho": round(float(rho), 3), "p": round(float(p), 3)}
        out[k] = {"pairs": len(D), "correlation_with_dH": cor}
    T = pd.DataFrame(rows)
    T.to_csv(HERE.parent / "onset_diagnostic.csv", index=False)
    (HERE.parent / "onset_diagnostic.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    pd.set_option("display.width", 250)
    for k in (1, 2):
        print(f"== lead {k}: {out[k]['pairs']} pairs")
        for nm, v in sorted(out[k]["correlation_with_dH"].items(), key=lambda kv: -abs(kv[1]["rho"])):
            print(f"   {nm:34s} n={v['n']:2d} rho={v['rho']:+.2f} p={v['p']:.3f}")
        print(T[T.lead == k][["target_q", "origin", "H_last", "H_last_q", "H", "dH", "crossed_up", "Market: rice YoY now",
                              "Market: world rice 6-mo change", "Employment: unemployment change", "Climate: typhoons in quarter"]]
              .round(1).to_string(index=False))
