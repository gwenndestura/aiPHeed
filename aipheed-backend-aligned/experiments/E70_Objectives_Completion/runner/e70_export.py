"""Condense out/score.json into backend/data/thesis/e70_summary.json, which the thesis backend's existing text fields
read (thesis_system.e70_sentence). No model, score or class served by the backend changes.

    python -B runner/e70_export.py
"""
import hashlib
import json
from pathlib import Path

E70 = Path(__file__).resolve().parents[1]
OUT = E70.parents[2] / "backend" / "data" / "thesis" / "e70_summary.json"


def main():
    src = E70 / "out" / "score.json"
    s = json.loads(src.read_text(encoding="utf-8"))
    g = s["decision"]["goal_80"]
    L = s["leads"]
    keep = ("accuracy", "correct", "n", "recall_HIGH", "balanced_accuracy", "auc_roc", "brier")
    out = {"date": "2026-10-20", "experiment": "E70_Objectives_Completion", "score_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
           "evidence": "development quarters reused across about 30 earlier experiments; not held-out",
           "target": "T43 (SWS regional hunger > 11.3% AND provincial food-price pressure); equal to price pressure on every evaluated row",
           "arms_tried": 3, "checks": len(s["ablations"]),
           "candidates_passing_rule": [a for a, v in s["decision"]["rule1"].items() if v["passes"]],
           "goal_80": {k: g[k] for k in ("selected_arm", "accuracy", "correct", "n", "recall_HIGH", "balanced_accuracy", "met")},
           "leads": {lead: {a: {k: L[lead]["metrics"][a][k] for k in keep} for a in ("R0", "A1", "A2", "S0", "PERSIST")}
                     for lead in L},
           "prospective_sealed": json.loads((E70 / "sealed" / "meta_main.json").read_text())["prospective_sha256"]}
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(OUT, json.dumps(out["goal_80"]))


if __name__ == "__main__":
    main()
