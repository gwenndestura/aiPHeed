"""E34: promote the tested E31 backend (backend_dev) into the main backend/ on branch e34-main-app-integration.

Builds on E33 promote_e31.py (never committed; its revert caused the 2026-10-15 git-clean incident), with three fixes:
  * scripts/create_admin.py is promoted too: E31's config renamed ADMIN_EMAIL_DOMAIN -> ADMIN_EMAIL_DOMAINS, so the
    main script would crash on its domain check after the config overlay (E34 also fixed the E31 copy);
  * data/news_e28 is promoted: app/api/v1/quarterly.py reads it for the E28 news endpoints (E33 left it out);
  * line endings are compared on LF (core.autocrlf=true), so unchanged files are not rewritten.

What it writes (and only this; the list goes to runs/e34_backend_promotion.json):
  backend/app      <- backend_dev/app (files present only in backend/app are kept: thesis_predictor, e20_forecast, ...)
                      then the main backend's risk-band rule (band on the displayed 2-decimal score, 1658d31) is restored
  backend/config   <- backend_dev/config (new folder)
  backend/data/<d> <- backend_dev/data/<d> for NEW sub-folders only; existing backend/data folders are not touched
  backend/data/reference/SOURCE.txt (new file only); cycle_log.jsonl, evidence_status_derived.json (new files only)
  backend/scripts  <- news_collect.py, quarterly_update.py, stage_alerts_e31.py, create_admin.py,
                      migrate_review_status_e31.py (E33)
Nothing is deleted. Nothing is pushed or deployed. backend/aipheed.db is not touched.
Revert: `git checkout -- backend` for tracked files, then delete the new files listed in the JSON one by one.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\admin\aipheed")
EXPS = ROOT / "aipheed-backend-aligned" / "experiments"
BD = EXPS / "E31_Chapter1_Completion" / "backend_dev"
BE = ROOT / "backend"
OUT = Path(__file__).resolve().parents[1] / "runs"
DATA_DIRS = ["e25", "e27", "e28", "e29", "e31", "inputs", "inputs_vintage1_e29", "news_e28", "news_e31", "ledger",
             "quarterly_runs", "quarterly_store", "outcomes", "inbox"]
SKIP = {"__pycache__", ".pytest_cache"}
log = {"overwritten": [], "new": [], "kept_main_only": [], "risk_rule_restored": False}


def lf(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def put(src: Path, dst: Path, dry: bool):
    if dst.exists():
        if lf(dst.read_bytes()) == lf(src.read_bytes()):
            return
        log["overwritten"].append(str(dst.relative_to(ROOT)))
    else:
        log["new"].append(str(dst.relative_to(ROOT)))
    if not dry:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def tree(src: Path, dst: Path, dry: bool):
    for p in sorted(src.rglob("*")):
        if p.is_dir() or any(x in SKIP for x in p.parts):
            continue
        put(p, dst / p.relative_to(src), dry)


def main(dry: bool):
    for d in DATA_DIRS:
        if (BE / "data" / d).exists():
            sys.exit(f"refused: backend/data/{d} already exists; this script only creates new data folders")
    tree(BD / "app", BE / "app", dry)
    for p in sorted((BE / "app").rglob("*.py")):
        if "__pycache__" not in p.parts and not (BD / "app" / p.relative_to(BE / "app")).exists():
            log["kept_main_only"].append(str(p.relative_to(ROOT)))
    tree(BD / "config", BE / "config", dry)
    for d in DATA_DIRS:
        if (BD / "data" / d).exists():
            tree(BD / "data" / d, BE / "data" / d, dry)
    for f in ("cycle_log.jsonl", "evidence_status_derived.json", "reference/SOURCE.txt"):
        if not (BE / "data" / f).exists():
            put(BD / "data" / f, BE / "data" / f, dry)
    for f in ("news_collect.py", "quarterly_update.py", "stage_alerts_e31.py", "create_admin.py"):
        put(BD / "scripts" / f, BE / "scripts" / f, dry)
    put(EXPS / "E33_Final_Audit" / "migrate_review_status_e31.py", BE / "scripts" / "migrate_review_status_e31.py", dry)
    if not dry:
        ref = BE / "app" / "services" / "reference.py"
        s = ref.read_text(encoding="utf-8")
        old = ('    # One rule everywhere: app.ml.features.risk_score_v2.final_classification (>= 0.50 -> HIGH).\n'
               '    from app.ml.features.risk_score_v2 import final_classification\n'
               '    return final_classification(score).lower()')
        new = ('    """\n'
               '    HIGH at or above the display cutoff, judged on the score as shown (two\n'
               '    decimals): a 0.4982 reads "0.50" everywhere, so it is HIGH, not LOW.\n'
               '    (Main-backend rule from 1658d31, kept when E31 was promoted in E34.)\n'
               '    """\n'
               '    return "high" if round(score, 2) >= RISK_DISPLAY_CUTOFF else "low"')
        if old in s:
            ref.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
            log["risk_rule_restored"] = True
    (OUT / ("e34_backend_promotion" + ("_dry" if dry else "") + ".json")).write_text(json.dumps(log, indent=1),
                                                                                       encoding="utf-8")
    print({k: (len(v) if isinstance(v, list) else v) for k, v in log.items()})


if __name__ == "__main__":
    main(dry="--apply" not in sys.argv)
