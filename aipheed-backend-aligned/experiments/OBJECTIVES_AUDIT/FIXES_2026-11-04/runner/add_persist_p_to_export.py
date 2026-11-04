"""Add the PERSIST-P Objective 4 family (PLAN_PERSIST_P.md) to the served C-B6 export, for the landing page.

Adds `objective4_lead1_persist_p` (Lead-1 C-B6 vs the five landing-page comparators, from out/persist_p_results.json,
primary family) to backend/data/foodinsecurity_engine_cb6/evaluation.json. `objective4_lead1` (0/1 persistence) is
kept as the secondary line. No forecast, metric or other key changes. A backup of the original file is written first.

    python add_persist_p_to_export.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[3]
EVAL = ROOT / "backend" / "data" / "foodinsecurity_engine_cb6" / "evaluation.json"
RES = HERE / "out" / "persist_p_results.json"
BACKUP = HERE / "backup" / "evaluation_cb6_before_persist_p.json"
KEEP = ["PERSIST-P", "PSA-only", "LOGIT", "NLP-only", "ALWAYS-HIGH"]


def main():
    raw = EVAL.read_bytes()
    nl = "\r\n" if b"\r\n" in raw else "\n"           # keep the checked-out line endings
    e = json.loads(raw.decode("utf-8"))
    assert e["model"] == "ALLBASE-CB6", e["model"]
    fam = json.loads(RES.read_text(encoding="utf-8"))["models"]["C-B6"]["primary_PERSIST_P"]
    o4 = {f["comparator"]: {"p_holm": f["p_holm_14"], "diff": f["diff"]} for f in fam
          if f["lead"] == 1 and f["comparator"] in KEEP}
    assert list(o4) == KEEP or set(o4) == set(KEEP)
    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(EVAL, BACKUP)
    e["objective4_lead1_persist_p"] = {k: o4[k] for k in KEEP}
    e["objective4_persist_p_source"] = ("OBJECTIVES_AUDIT/FIXES_2026-11-04/PLAN_PERSIST_P.md (b3e8b02d...): persistence "
                                        "scored as a probability (hr_lib.pi_h4l); Holm over the 14-test family with "
                                        "PERSIST-P; objective4_lead1 keeps the 0/1 persistence family as a secondary line")
    EVAL.write_bytes((json.dumps(e, indent=1, ensure_ascii=False) + "\n").replace("\n", nl).encode("utf-8"))
    print({"backup_sha256": hashlib.sha256(BACKUP.read_bytes()).hexdigest(),
           "new_sha256": hashlib.sha256(EVAL.read_bytes()).hexdigest(), "objective4_lead1_persist_p": e["objective4_lead1_persist_p"]})


if __name__ == "__main__":
    main()
