"""E31 step 1: freeze 2026-Q3 forecasts BEFORE any 2026-Q3 outcome is retrieved.

Why: the researcher authorized data released up to 2026-10-14 (E31). 2026-Q3 is the first quarter whose outcome
(September 2026 SWS round, July-September 2026 provincial food CPI) nobody on the project has retrieved. The E24v2
seal (git 5113ae5, 2026-10-13) already froze persistence, calibrated persistence and M2 for 2026-Q3 at lead 1. This
script adds the candidates that seal lacks, with the UNCHANGED engines and only inputs available by the origin:

  * PCF21 (the dev system's engine, app/quarterly/pcf_engine.py) at lead 1 (origin 2026-07-01, reference 2026-Q2)
    and lead 2 (origin 2026-04-01, reference 2026-Q1);
  * the references used by the E27 ledger: persistence, calibrated persistence, climatology; plus always-HIGH.

The inputs are the E29 dev inputs, which end at 2026-Q2 (authorized limit before E31). Nothing from July 2026 on is
read. The quarterly ledger refuses seals after the target quarter ended (rule L1), so this is NOT a ledger seal: it
is a 'frozen before outcome retrieval' record whose SHA-256 is written to frozen/ and committed to git before
e31_fetch_outcomes.py runs. Its evidential status is RETROSPECTIVE-BLIND (the quarter has ended in reality, but the
outcome was unseen by the project when the forecast was frozen), which is weaker than a prospective seal.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "runner"))
sys.path.insert(0, str(EXP / "backend_dev"))
import guard31  # noqa: E402

guard31.install()
import pandas as pd  # noqa: E402

from app.quarterly import pcf_engine as P  # noqa: E402
from app.quarterly.cycle import reference_probabilities  # noqa: E402

INP = EXP / "backend_dev" / "data" / "inputs_vintage1_e29"   # E31: vintage 1 (ends 2026-Q2), kept for reproduction
OUT = EXP / "frozen"
FILES = ["sws_rounds.csv", "s1_labels.csv", "d_quarterly_panel.csv", "dnow_panel.csv"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    rounds = pd.read_csv(INP / "sws_rounds.csv")
    S1 = pd.read_csv(INP / "s1_labels.csv", dtype={"province_code": str})
    dq = pd.read_csv(INP / "d_quarterly_panel.csv", dtype={"province_code": str})
    dn = pd.read_csv(INP / "dnow_panel.csv", dtype={"province_code": str})
    for name, df in (("sws_rounds", rounds), ("s1_labels", S1), ("d_quarterly_panel", dq), ("dnow_panel", dn)):
        qmax = max(df["quarter"], key=P.qk)
        qmin = min(df["quarter"], key=P.qk)
        assert P.qk(qmin) >= P.qk("2021-Q1") and P.qk(qmax) <= P.qk("2026-Q2"), (name, qmin, qmax)
    Dm, Nm = P.panels_from_tables(dq, dn)
    target = "2026-Q3"
    runs = {}
    for lead, ref, origin in ((1, "2026-Q2", "2026-07-01"), (2, "2026-Q1", "2026-04-01")):
        o = pd.Timestamp(origin)
        fc = P.forecast(o, P.qk(ref), [lead], rounds, S1, Dm, Nm, evidence={})
        blk = fc["leads"][str(lead)]
        assert blk["target_quarter"] == target
        refs = reference_probabilities(S1, fc["threshold"], ref, lead)
        arms = {
            "PCF21": {p: v["risk"]["p_high"] for p, v in blk["provinces"].items()},
            "B1_persistence": refs["persistence"],
            "B1p_calibrated_persistence": refs["calibrated_persistence"],
            "CLIM_climatology": refs["climatology"],
            "ALWAYS_HIGH": {p: 1.0 for p in P.PROVINCES},
        }
        runs[str(lead)] = {
            "origin": origin, "reference_quarter": ref, "information_cutoff": (o - pd.Timedelta(seconds=1)).isoformat() + "+08:00",
            "threshold_tau": fc["threshold"], "threshold_labels": fc["threshold_labels"],
            "sws_rounds_used": fc["sws_rounds_used"], "last_label_quarter": refs["last_label_quarter"],
            "H_forecast": blk["H"], "D_model": blk["D_model"],
            "S1_forecast": {p: v["risk"]["S1_forecast"] for p, v in blk["provinces"].items()},
            "S1_80pct_interval": {p: v["risk"]["S1_80pct_interval"] for p, v in blk["provinces"].items()},
            "price_pressure_T2": {p: v["price_pressure"].get("p_above_regional_mean") for p, v in blk["provinces"].items()},
            "arms_p_high": arms,
        }
    rec = {
        "record": "E31 frozen 2026-Q3 forecasts (retrospective-blind)",
        "target_quarter": target,
        "label": "T1 = S1 = H + 2D > tau (approved Chapter I composite); HIGH if S1 > tau",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "RETROSPECTIVE-BLIND: frozen before the project retrieved any 2026-Q3 outcome; quarter already ended",
        "known_partial_exposures": [
            "E26 (2026-10-14): a search summary quoted August-September 2026 PSA bottom-30% CPI values (not the "
            "provincial food CPI used for D, but correlated). Logged in E26 CONTAMINATION_LOG.",
            "E27 (2026-10-14): an SWS September 2026 *satisfaction* headline was seen (not the hunger series H).",
        ],
        "engine": "backend_dev/app/quarterly/pcf_engine.py (unchanged from E29)",
        "engine_sha256": sha(EXP / "backend_dev" / "app" / "quarterly" / "pcf_engine.py"),
        "inputs_sha256": {f: sha(INP / f) for f in FILES},
        "also_frozen_elsewhere": "E24v2 SEAL_20261013T164218Z (git 5113ae5): B1, B1p, M2_lgbm_P_E24frozen for 2026-Q3 lead 1",
        "not_frozen": {
            "P45 (PROPOSED_lgbm_combined)": "needs a 2026-Q2 news row and 2026-Q1 government features, which the "
                                            "pinned feature file does not contain; building them is a separate step "
                                            "(see E31 FINAL_REPORT). Not produced before outcome retrieval.",
        },
        "leads": runs,
    }
    body = json.dumps(rec, indent=1, sort_keys=False, default=float).encode("utf-8")
    OUT.mkdir(exist_ok=True)
    if "--verify" in sys.argv:
        print("reproduced" if body[body.index(b'"status"'):] == (OUT / "E31_FROZEN_Q3.json").read_bytes()[(OUT / "E31_FROZEN_Q3.json").read_bytes().index(b'"status"'):] else "DIFFERS")
        return
    (OUT / "E31_FROZEN_Q3.json").write_bytes(body)
    h = hashlib.sha256(body).hexdigest()
    (OUT / "E31_FROZEN_Q3.sha256").write_bytes(f"{h}  E31_FROZEN_Q3.json\n".encode())
    print(h)
    for k, r in runs.items():
        print("lead", k, "tau", round(r["threshold_tau"], 3), {a: {P.PROVINCE_NAMES[p][:3]: round(v, 3) for p, v in d.items()} for a, d in r["arms_p_high"].items()})


if __name__ == "__main__":
    main()
