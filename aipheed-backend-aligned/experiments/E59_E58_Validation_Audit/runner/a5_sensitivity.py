"""E59 audit step 5: data-timing and missing-data sensitivity of the hunger gate (diagnostic only; the frozen E56/E58
results are not replaced).

  S1  issue-time sensitivity: the hunger probability at each origin if the forecast were issued the day after the next
      SWS round was posted (the round then joins the hunger history; price part and every other input unchanged).
  S2  round-definition sensitivity: the hunger gate built from ALL SWS rounds (approved + supplementary) instead of the
      approved (definition A) rounds only.
For each: the resulting P(HIGH) = P_hunger x P_price (sealed P_price), the HIGH decision at 0.5, and accuracy/onsets.

    backend/venv/Scripts/python.exe -B runner/a5_sensitivity.py  -> out/sensitivity.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
A = Path(__file__).resolve().parents[1]
EXP = A.parent
sys.path.insert(0, str(EXP / "E56_LightGBM_Optimization" / "runner"))
import e56_lib as G  # noqa: E402

E, F, L, np, pd = G.E, G.F, G.L, G.np, G.pd
P2 = F.P2
HC = [c for g in P2.ALL_GROUPS if g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]


def gate(X, hs, t):
    htr, hte = P2.hunger_frame(X, hs, t, HC)
    return P2.hunger_component(htr, hte, HC)


def main():
    D = pd.read_csv(A / "E58_QUARTERLY_PREDICTIONS.csv", dtype={"province_code": str})
    D["t"] = D["origin_quarter"].map(L.qi)
    d, X, B = E.load()
    r = pd.read_csv(L.SWS_FILE)
    r["q"], r["published"] = r["quarter"].map(L.qi), pd.to_datetime(r["published"])
    out = {}
    for name in ("S1_issue_after_next_SWS_round", "S2_all_rounds_gate"):
        ph = {}
        for t in sorted(D["t"].unique()):
            t = int(t)
            base = P2.h_series(d, t, False)
            if name.startswith("S1"):
                nxt = r[(r["published"] >= L.origin(t)) & (r["definition_A"].astype(str) == "True")].sort_values("published")
                hs = base.copy()
                if len(nxt):
                    q0 = int(nxt.iloc[0]["q"])
                    hs.loc[q0] = float(r[r["q"] == q0]["H"].mean())
                    hs = hs.sort_index()
            else:
                hs = P2.h_series(d, t, True)
            ph[t] = gate(X, hs, t)["p"]
        D[f"{name}_p_hunger"] = D["t"].map(ph)
        D[f"{name}_p"] = D[f"{name}_p_hunger"] * D["E56_p_price"]
        D[f"{name}_pred"] = (D[f"{name}_p"] >= 0.5).astype(int)
        out[name] = {"accuracy": float((D[f"{name}_pred"] == D["y_T43"]).mean()),
                     "onsets_detected": int(((D["onset"] == 1) & (D[f"{name}_pred"] == 1)).sum()),
                     "decisions_changed_vs_E56": int((D[f"{name}_pred"] != D["E56_pred"]).sum()),
                     "p_hunger_by_origin": {L.qs(t): round(float(v), 4) for t, v in ph.items()}}
    out["frozen_E56_p_hunger_by_origin"] = {L.qs(int(t)): round(float(g["E56_p_hunger"].iloc[0]), 4) for t, g in D.groupby("t")}
    (A / "out" / "sensitivity.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
