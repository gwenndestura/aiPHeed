"""Build backend/data/e48/e48_record.json with the SAME builder that produced e36_record.json
(scripts/build_record_e36.build / write_pdf), pointed at the E48-A1 frozen bundle, prospective and model artifact.

    python -B backend/experiments/e48/runner/build_record_e48.py   (from the repo root)

Differences from build_record_e36.main(), on purpose:
  * reads backend/experiments/e48/{frozen,models} instead of the E36 ones (module constants overridden);
  * writes only backend/data/e48/ (record, PDF, model copies) -- never data/e36/ and never frontend/public/;
  * relabels the served engine (name, version, file) as E48-A1 and recomputes the record hash.
The E38 next-quarter (lead 2) row is included exactly as in e36_record.json; it is not served at AIPHEED_MAX_LEAD=1.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
BACKEND = Path(__file__).resolve().parents[3]
E48 = BACKEND / "experiments" / "e48"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))
import build_record_e36 as B  # noqa: E402

B.BUNDLE = E48 / "frozen" / "E48_SERVING_BUNDLE.json"
B.PROSPECTIVE = E48 / "frozen" / "E48_PROSPECTIVE_2026Q4.json"
B.MODEL_TXT = E48 / "models" / "E48-A1-LGBM_O2026-10-01.txt"
B.MODEL_CFG = E48 / "models" / "E48-A1-LGBM_O2026-10-01.json"
OUT = BACKEND / "data" / "e48"


def main():
    import os

    os.chdir(BACKEND)                                  # the builder reads data/... relative to backend/
    rec = B.build()
    bundle = json.loads(B.BUNDLE.read_text(encoding="utf-8"))
    se = rec["served_engine"]
    se.update({"name": "aiPHeed-E48-A1-LGBM (LightGBM: E36 inputs + the five trigger proportions) - PREVIEW",
               "version": bundle["model"]["version"], "file": "data/e48/model/" + B.MODEL_TXT.name,
               "why_served": "Preview of the E48-A1 experiment (THESIS_2_14 Chapter 3, Eq. 5 trigger features) in a "
                             "separate local instance; the official system serves E36.",
               "evidence_status": "EXPERIMENTAL / PREVIEW (E48: non-inferior to E36 on development dates)"})
    rec.pop("content_sha256", None)
    rec = B._clean(rec)
    rec["content_sha256"] = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    (OUT / "model").mkdir(parents=True, exist_ok=True)
    for src in (B.MODEL_TXT, B.MODEL_CFG, B.MODEL_TXT.parent / "ARTIFACT_HASHES.json", B.BUNDLE, B.PROSPECTIVE,
                B.BUNDLE.with_suffix(".sha256"), B.PROSPECTIVE.with_suffix(".sha256")):
        shutil.copyfile(src, OUT / "model" / src.name)
    blob = json.dumps(rec, indent=1, ensure_ascii=False, default=str, allow_nan=False).encode("utf-8")
    (OUT / "e48_record.json").write_bytes(blob)
    B.write_pdf(rec, OUT / "aiPHeed_E48_assessment_report.pdf")
    q4 = next(q for q in rec["quarters"] if q["quarter"] == "2026-Q4")
    print(rec["content_sha256"], len(blob), "bytes;", len(rec["quarters"]), "quarters; 2026-Q4",
          {v["province"]: v["p_high"] for v in q4["provinces"].values()}, q4["model_config"])


if __name__ == "__main__":
    main()
