"""
E134 seal scoring, primary criterion only (E131 Addendum 1): |forecast - SWS| <= 1.645 x SE of the SWS quarter.
Same input file and rules as E131 runner/score_e131.py; scores the E134 candidates' sealed 2026-Q4 .. 2027-Q3 forecasts.

    python -I runner/score_e134.py      -> out/seal_scores/score_<run_utc>.csv and .json (append-only)
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT.parent / "E131_Objectives_Resolution" / "runner"))
import e131_x1 as X  # noqa: E402

SEAL = ROOT / "sealed" / "E134_PROSPECTIVE_SEAL.csv"
SEAL_SHA = "e4f844dd4d3477e61e09faa2ab8d8fef578ae99bccad06e93ea02a59f16d6fbe"
NEW_ROUNDS = ROOT.parent / "E131_Objectives_Resolution" / "data" / "sws_rounds_after_2026Q3.csv"
MODELS = ["PERSIST", "HFM-X", "E134-AREA-T", "E134-AREA-O", "E134-ONI", "E134-ENS"]
CRITERION = "primary only: |forecast - SWS| <= 1.645 x SE of the SWS quarter (E131 protocol section 1); no secondary tolerance (E131 Addendum 1)"


def score(seal: pd.DataFrame, rounds_path: Path) -> tuple[pd.DataFrame, dict]:
    rr = X.rounds(rounds_path)
    assert (rr["quarter"].map(X.L.qi) > X.L.qi("2026-Q3")).all(), "the new-rounds file may only hold quarters after 2026-Q3"
    qt = X.quarter_table(rr).set_index(["area", "quarter"])
    rows = []
    for i, r in seal.iterrows():
        if (r["area"], r["target"]) not in qt.index:
            continue
        y, se = float(qt.loc[(r["area"], r["target"]), "y"]), float(qt.loc[(r["area"], r["target"]), "se"])
        tol = X.L.Z90 * se
        rec = {"area": r["area"], "lead": r["lead"], "target": r["target"], "y_sws": y, "se": se, "tolerance_primary": tol,
               "sharp_increase": bool(y - r["y_latest"] > 2 * se),
               "in_80pct_interval_HFM-X": bool(r["HFM-X_lo80"] <= y <= r["HFM-X_hi80"])}
        for m in MODELS:
            rec[f"error_{m}"] = float(r[m]) - y
            rec[f"within_primary_{m}"] = bool(abs(float(r[m]) - y) <= tol)
        rows.append(rec)
    S = pd.DataFrame(rows)
    summ = {"criterion": CRITERION, "rows_scored": int(len(S)), "by_model_lead": {}}
    for m in MODELS:
        for k, g in (S.groupby("lead") if len(S) else []):
            summ["by_model_lead"][f"{m}|{k}"] = {"n": int(len(g)), "within_primary": float(g[f"within_primary_{m}"].mean()),
                                                 "mae": float(g[f"error_{m}"].abs().mean())}
    return S, summ


def main(out_dir: Path = ROOT / "out" / "seal_scores") -> None:
    assert hashlib.sha256(SEAL.read_bytes()).hexdigest() == SEAL_SHA, "the E134 seal changed since it was frozen"
    if not NEW_ROUNDS.exists():
        sys.exit("nothing to score: SWS has not published 2026-Q4 yet")
    S, summ = score(pd.read_csv(SEAL), NEW_ROUNDS)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    S.to_csv(out_dir / f"score_{stamp}.csv", index=False)
    (out_dir / f"score_{stamp}.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print(json.dumps(summ, indent=1)[:2000])


if __name__ == "__main__":
    main()
