"""Add the Addendum 3 horizon result to the served evaluation (backend/data/ch1_engine/evaluation.json, key "horizon").

The served Lead 1-4 metrics must equal the horizon run's (same code, same audited inputs), and the maximum reliable
lead must not change; otherwise the export stops. rows.csv is not touched.

    python export_horizon.py
"""
from __future__ import annotations

import json

from horizon_rule import select_horizon

from pathlib import Path

VER = Path(__file__).resolve().parents[1]
OUT = VER / "out"
CH1 = VER.parent / "FINAL_THESIS_OBJECTIVES"
DEST = VER.parents[2] / "backend" / "data" / "ch1_engine" / "evaluation.json"

WHY_NOT_LONGER = (
    "Leads 4-8 have fewer than the 10 target quarters the frozen rule R1 requires (8, 6, 5, 3, 1), because the study "
    "window starts in 2021 and the last outcome is 2026-Q3; Lead 9 and beyond have none. From Lead 5 on, the "
    "food-price projection (A1, the model's main input) has no published base month at the issue date, so it is "
    "missing for every forecast.")


def main():
    r = json.loads((OUT / "horizon_results.json").read_text(encoding="utf-8"))
    ev = json.loads(DEST.read_text(encoding="utf-8"))
    for k in ("1", "2", "3", "4"):
        a, b = ev["leads"][k]["metrics"], r["leads"][k]["metrics"]
        assert a["tp"] == b["tp"] and a["fp"] == b["fp"] and a["tn"] == b["tn"] and a["fn"] == b["fn"], k
    sel = select_horizon(r["leads"])
    assert sel["max_reliable_lead"] == ev["max_reliable_lead"], "horizon run disagrees with the served verdict"
    ql = json.loads((OUT / "verify_quarter_level.json").read_text(encoding="utf-8"))
    leads = {}
    for k, d in r["leads"].items():
        if int(k) < 1:
            continue
        m = d["metrics"]
        leads[k] = {"n": d["n"], "n_quarters": d["n_quarters"], "high_share": d["high_share"],
                    "accuracy": m["accuracy"], "accuracy_ci90": d["accuracy_ci90"],
                    "balanced_accuracy": m["balanced_accuracy"], "brier": m["brier"],
                    "confusion": {x: m[x] for x in ("tp", "fp", "tn", "fn")},
                    "always_low_accuracy": d["baseline_accuracy"]["ALWAYS-LOW"],
                    "persist_si_accuracy": d["baseline_accuracy"]["PERSIST-SI"],
                    "criteria": d["criteria"], "reliable": d["reliable"],
                    "quarters_after_issue": d["operational"]["quarters_after_issue_quarter"],
                    "target_quarter_ends_days_after_issue": d["operational"]["target_quarter_ends_days_after_issue"],
                    "quarters_after_newest_sws": d["operational"]["true_sws_horizon"],
                    "latest_block": d["latest_block"], "hunger_surge_quarters": d["hunger_surge_quarters"],
                    "quarter_level_vs_always_low": ql[k]["ALWAYS-LOW"],
                    "quarter_level_vs_persist_si": ql[k]["PERSIST-SI"]}
    ev["horizon"] = {"addendum3_sha256": r["addendum3_sha256"], **sel,
                     "max_reliable_lead_strict": r["max_reliable_lead_strict"],
                     "why_not_longer": WHY_NOT_LONGER, "leads": leads,
                     "lead1_quarter_level": r["leads"]["1"]["quarter_level"],
                     "lead1_sensitivity": ql["lead1_sensitivity"]}
    DEST.write_text(json.dumps(ev, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")   # platform newline, like export_ch1
    print("horizon exported:", sel)


if __name__ == "__main__":
    main()
