"""Priority 3: reproduce the documented results of the comparator candidates P0H4, P0H4-U and Z0-U from their saved
walk-forward predictions, against the exported evaluation files, and report their hunger component separately (the
only directly measured outcome they forecast: SWS Balance Luzon involuntary hunger above 11.3).

    python reproduce_comparators.py     # ../out/comparators_reproduced.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
ROOT = EXP.parents[1]
sys.path.insert(0, str(EXP / "FORECAST_RESEARCH" / "runner"))
import fr_lib as F  # noqa: E402
import metrics as M  # noqa: E402

OUT = HERE.parent / "out"
OUT.mkdir(exist_ok=True)
EXPORTS = {"P0H4": ("ch1_engine", "P0H4_p3", "PERSIST_A"), "P0H4-U": ("ch1_engine_fr", "P0H4U_p", "PERS_AB"),
           "Z0-U": ("ch1_engine_fr2", "Z0_p", "PERS_AB")}


def main():
    E = pd.read_csv(EXP / "FORECAST_RESEARCH_II" / "out" / "predictions_ii.csv", dtype={"province_code": str})
    out = {}
    for name, (d, col, pers) in EXPORTS.items():
        ev = json.loads((ROOT / "backend" / "data" / d / "evaluation.json").read_text(encoding="utf-8"))
        rec = {"export": d, "seal": ev.get("seal_sha256"), "max_reliable_lead_exported": ev.get("max_reliable_lead"), "leads": {}}
        dec = {}
        for k, g in E.groupby("lead"):
            r = F.evaluate(g, col, pers)
            dec[int(k)] = r
            m = r["metrics"]
            exp_m = (ev["leads"].get(str(k)) or {}).get("metrics", {})
            if name == "P0H4-U" and k == 2:                 # the re-issued Lead 2 is stored under sws_update
                exp_m = ev["sws_update"]["lead2"]["metrics"]
            rec["leads"][int(k)] = {"n": m["n"], "accuracy": m["accuracy"], "balanced_accuracy": m["balanced_accuracy"],
                                    "precision": m["precision"], "recall": m["recall"], "brier": m["brier"],
                                    "failed": r["failed"],
                                    "exported_accuracy": exp_m.get("accuracy"), "exported_brier": exp_m.get("brier"),
                                    "match": (abs(exp_m["accuracy"] - m["accuracy"]) < 1e-9 and abs(exp_m["brier"] - m["brier"]) < 1e-6)
                                    if exp_m and (int(k) in (1, 2) or name == "Z0-U") else None}
        rec["max_reliable_lead_reproduced"] = F.max_reliable(dec)
        out[name] = rec
        print(name, rec["max_reliable_lead_reproduced"], {k: (round(v["accuracy"], 3), round(v["brier"], 3), v["failed"], v["match"])
                                                           for k, v in rec["leads"].items()})
    (OUT / "comparators_reproduced.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
