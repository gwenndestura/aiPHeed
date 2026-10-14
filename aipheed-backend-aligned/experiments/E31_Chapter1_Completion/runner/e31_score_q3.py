"""E31 step 2: build the 2026-Q3 outcome from authorized released data and score every forecast frozen before it.

Outcome (approved Chapter I composite, same construction as E25 load_components / Target):
  H(2026-Q3) = mean of the definition-A Balance Luzon rounds of the quarter = September 2026 round (posted 2026-10-14)
  F(p, 2026-Q3) = mean of the July-September 2026 PSA food CPI YoY (OpenStat 0012M4ACP23, 01.1 FOOD)
  D = F - five-province mean;  S1 = H + 2D;  HIGH if S1 > tau, where tau is the threshold each forecast was frozen
  with (E27 rule L3: every seal carries its own tau).
Forecasts scored: E24v2 SEAL_20261013T164218Z (git 5113ae5), E31_FROZEN_Q3 (git 70d8770), E31_FROZEN_Q3_P45_LEAD2
(git bbbe104). Their hashes are verified before scoring.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "runner"))
import guard31  # noqa: E402

guard31.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
E24V2 = EXP.parent / "E25_Reliable_Forecasts_2021_2026" / "inputs" / "e24v2" / "runs" / "SEAL_20261013T164218Z" / "SEAL_PROSPECTIVE.json"
E24V2_SHA = "ac8babbcfbb36729e16226356d1cb8250be0730d437d08eb465ecc5830673ef0"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def outcome():
    c = pd.read_csv(EXP / "data_acquired" / "cpi" / "provincial_food_cpi_yoy_2026_raw.csv", dtype={"province_code": str})
    c = c[c["reference_month"].isin(["2026-07", "2026-08", "2026-09"])]
    assert len(c) == 15
    F = c.groupby("province_code")["food_cpi_yoy_pct_raw"].mean()
    D = F - F.mean()
    s = pd.read_csv(EXP / "data_acquired" / "sws" / "sws_rounds_2026_verified.csv")
    H = float(s[(s["quarter"] == "2026-Q3") & s["definition_A"]]["H"].mean())
    return {"H": H, "F": F.to_dict(), "D": D.to_dict(), "S1": {p: H + 2 * float(D[p]) for p in D.index}}


def brier(p, y):
    return float(np.mean([(p[k] - y[k]) ** 2 for k in y]))


def main():
    out = outcome()
    arms = []
    # --- E24v2 seal: prospective_forecasts.csv, whose SHA-256 is the seal's recorded hash and equals git 96e388e
    csvp = E24V2.parent / "prospective_forecasts.csv"
    assert sha(csvp) == E24V2_SHA, "E24v2 seal changed"
    pf = pd.read_csv(csvp, dtype={"province_code": str})
    pf = pf[(pf["target"] == "T1") & (pf["target_quarter"] == "2026-Q3")]
    for (model, lead), g in pf.groupby(["model", "lead"]):
        arms.append({"source": "E24v2 SEAL_20261013T164218Z (git 96e388e)", "arm": model, "lead": int(lead),
                     "tau": float(g["threshold"].iloc[0]), "p": dict(zip(g["province_code"], g["score"].astype(float)))})
    arms_e24 = {a["arm"]: 1 for a in arms}
    # --- E31 frozen records
    f1 = EXP / "frozen" / "E31_FROZEN_Q3.json"
    f2 = EXP / "frozen" / "E31_FROZEN_Q3_P45_LEAD2.json"
    assert sha(f1) == (EXP / "frozen" / "E31_FROZEN_Q3.sha256").read_text().split()[0]
    assert sha(f2) == (EXP / "frozen" / "E31_FROZEN_Q3_P45_LEAD2.sha256").read_text().split()[0]
    r1 = json.loads(f1.read_text(encoding="utf-8"))
    r2 = json.loads(f2.read_text(encoding="utf-8"))
    for lead, blk in r1["leads"].items():
        tau = blk["threshold_tau"]
        for arm, probs in blk["arms_p_high"].items():
            arms.append({"source": "E31_FROZEN_Q3 (git 70d8770)", "arm": arm, "lead": int(lead), "tau": tau, "p": probs})
    fc = r2["forecast"]
    for arm, probs in fc["arms_p_high"].items():
        arms.append({"source": "E31_FROZEN_Q3_P45_LEAD2 (git bbbe104)", "arm": arm, "lead": 2, "tau": fc["tau_at_origin"], "p": probs})
    rows = []
    for a in arms:
        y = {p: int(out["S1"][p] > a["tau"]) for p in NAMES}
        pred = {p: int(a["p"][p] >= 0.5) for p in NAMES}
        rows.append({"source": a["source"], "arm": a["arm"], "lead": a["lead"], "tau": round(a["tau"], 4),
                     "n_HIGH_outcome": sum(y.values()), "brier": round(brier(a["p"], y), 4),
                     "accuracy": sum(pred[p] == y[p] for p in NAMES) / 5,
                     "p": {NAMES[p]: round(a["p"][p], 3) for p in NAMES}})
    res = {"outcome_2026Q3": {"H_balance_luzon_sept2026": out["H"],
                              "F_food_yoy_julsep": {NAMES[p]: round(v, 3) for p, v in out["F"].items()},
                              "D": {NAMES[p]: round(v, 3) for p, v in out["D"].items()},
                              "S1": {NAMES[p]: round(v, 3) for p, v in out["S1"].items()}},
           "inputs_sha256": {"cpi": sha(EXP / "data_acquired" / "cpi" / "provincial_food_cpi_yoy_2026_raw.csv"),
                             "sws": sha(EXP / "data_acquired" / "sws" / "sws_rounds_2026_verified.csv")},
           "e24v2_groups_found": len(arms_e24),
           "scores": rows,
           "caveat": "ONE quarter, five rows that share one regional H: a single observation of regional hunger. "
                     "No statistical claim of skill can rest on it; it is the first unseen-quarter data point."}
    (EXP / "runs" / "e31_q3_scores.json").write_bytes(json.dumps(res, indent=1).encode())
    print(json.dumps(res["outcome_2026Q3"], indent=1))
    for r in rows:
        print(r["source"][:22], r["arm"], "lead", r["lead"], "tau", r["tau"], "HIGH", r["n_HIGH_outcome"], "brier", r["brier"], "acc", r["accuracy"])
    print("e24v2 groups", len(arms_e24))


if __name__ == "__main__":
    main()
