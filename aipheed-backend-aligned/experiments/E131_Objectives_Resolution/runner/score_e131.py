"""
E131 seal scoring, primary criterion only (Addendum 1: no independently justifiable DA operational tolerance exists, so
no secondary tolerance is applied). Scores the sealed 2026-Q4 .. 2027-Q3 forecasts against SWS rounds published after
2026-Q3, with the frozen protocol-section-1 rule: agreement = |forecast - SWS| <= 1.645 x SE of the SWS quarter.

Input, added as SWS publishes (same columns as E110 data/sws_area_rounds.csv; non-commissioned rounds only):
    data/sws_rounds_after_2026Q3.csv
Run:  python -I runner/score_e131.py      -> out/seal_scores/score_<run_utc>.csv and .json (append-only)
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import e131_x1 as X  # noqa: E402

SEAL = ROOT / "sealed" / "E131_PROSPECTIVE_SEAL.csv"
SEAL_SHA = "92b5535fe7151efa158183722d488570fe18ef55612bc99028ccb2e4814dbc63"
NEW_ROUNDS = ROOT / "data" / "sws_rounds_after_2026Q3.csv"
MODELS = ["PERSIST", "CLIM", "LLM", "DLLM", "RIDGE-H", "LGBM-H", "RIDGE-ALL", "LGBM-ALL", "PSA-ONLY", "NLP-ONLY"]
CRITERION = "primary only: |forecast - SWS| <= 1.645 x SE of the SWS quarter (E131 protocol section 1); no secondary tolerance (Addendum 1)"


def score(seal: pd.DataFrame, rounds_path: Path) -> tuple[pd.DataFrame, dict]:
    rr = X.rounds(rounds_path)
    assert (rr["quarter"].map(X.L.qi) > X.L.qi("2026-Q3")).all(), "the new-rounds file may only hold quarters after 2026-Q3"
    qt = X.quarter_table(rr).set_index(["area", "quarter"])
    rows = []
    for r in seal.itertuples():
        if (r.area, r.target) not in qt.index:
            continue
        y, se = float(qt.loc[(r.area, r.target), "y"]), float(qt.loc[(r.area, r.target), "se"])
        tol = X.L.Z90 * se
        rec = {"area": r.area, "lead": r.lead, "target": r.target, "y_sws": y, "se": se, "tolerance_primary": tol,
               "rounds_used": int(qt.loc[(r.area, r.target), "k"]), "sharp_increase": bool(y - r.y_latest > 2 * se)}
        for m in MODELS:
            f = float(seal.loc[r.Index, m])
            rec[f"error_{m}"] = f - y
            rec[f"within_primary_{m}"] = bool(abs(f - y) <= tol)
        for m in ("LLM", "DLLM"):
            rec[f"in_80pct_interval_{m}"] = bool(seal.loc[r.Index, f"{m}_lo80"] <= y <= seal.loc[r.Index, f"{m}_hi80"])
        rows.append(rec)
    S = pd.DataFrame(rows)
    summary = {"criterion": CRITERION, "rows_scored": int(len(S)), "targets_scored": sorted(S["target"].unique()) if len(S) else [],
               "by_model_lead": {}}
    for m in MODELS:
        for k, g in (S.groupby("lead") if len(S) else []):
            summary["by_model_lead"][f"{m}|{k}"] = {"n": int(len(g)), "within_primary": float(g[f"within_primary_{m}"].mean()),
                                                    "mae": float(g[f"error_{m}"].abs().mean()),
                                                    "sharp_increases": int(g["sharp_increase"].sum()),
                                                    "within_primary_on_sharp_increases": int(g.loc[g["sharp_increase"], f"within_primary_{m}"].sum())}
    summary["note"] = ("development and prospective evidence are reported separately; at least 10 unseen quarters and N1-N7 are "
                       "needed before any reliability claim")
    return S, summary


def main(out_dir: Path = ROOT / "out" / "seal_scores") -> None:
    assert hashlib.sha256(SEAL.read_bytes()).hexdigest() == SEAL_SHA, "the E131 seal changed since it was frozen"
    if not NEW_ROUNDS.exists():
        sys.exit(f"nothing to score: {NEW_ROUNDS.relative_to(ROOT)} not present (SWS has not published 2026-Q4 yet)")
    S, summary = score(pd.read_csv(SEAL), NEW_ROUNDS)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary.update(run_utc=stamp, seal_sha256=SEAL_SHA, rounds_sha256=hashlib.sha256(NEW_ROUNDS.read_bytes()).hexdigest())
    S.to_csv(out_dir / f"score_{stamp}.csv", index=False)
    (out_dir / f"score_{stamp}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1)[:3000])


if __name__ == "__main__":
    main()
