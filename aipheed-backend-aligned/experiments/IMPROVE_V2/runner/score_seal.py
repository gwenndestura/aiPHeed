"""Score the sealed IMPROVE_V2 forecasts (PLAN.md section 10). Never refits.

    python score_seal.py [--sws PATH]

1. Every file in SEAL_LEDGER.md is checked against its recorded SHA-256; any mismatch stops the run.
2. Each sealed target is scored once its SWS outcome is in the SWS rounds file (default: the file HISTORY_RETRAIN
   read; pass an updated copy with --sws): Balance Luzon hunger = mean of the quarter's non-commissioned rounds,
   HIGH when > 11.3.
3. Reports n, accuracy and Brier for the sealed model and for persistence issued on the same dates, by lead.
   -> out/seal_scores.json"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

import iv2_lib as V

H = V.H
LEDGER = V.IV / "SEAL_LEDGER.md"


def ledger() -> list[tuple[str, str]]:
    return re.findall(r"^\| `([^`]+\.csv)` \| `([0-9a-f]{64})` \|", LEDGER.read_text(encoding="utf-8"), re.M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sws", default=str(H.LONG / "sws_area_rounds_full.csv"))
    a = ap.parse_args()
    files = ledger()
    assert files, "empty ledger"
    bad = {f: h for f, h in files if hashlib.sha256((V.IV / f).read_bytes()).hexdigest() != h}
    if bad:
        raise SystemExit(f"SEALED FILE CHANGED, nothing scored: {sorted(bad)}")
    S = pd.concat([pd.read_csv(V.IV / f) for f, _ in files], ignore_index=True)
    s = pd.read_csv(a.sws)
    s = s[~s["commissioned"].astype(bool)].dropna(subset=["balance_luzon"])
    bl = s.groupby("quarter")["balance_luzon"].mean()
    S["H_observed"] = S["target_quarter"].map(bl)
    S["y"] = np.where(S["H_observed"].notna(), (S["H_observed"] > H.H_LINE).astype(float), np.nan)
    g = S[S["y"].notna()]
    out = {"hashes_ok": True, "files": [f for f, _ in files], "sws_file": a.sws,
           "sws_file_sha256": hashlib.sha256(Path(a.sws).read_bytes()).hexdigest(),
           "pending_targets": S[S["y"].isna()][["lead", "target_quarter"]].to_dict("records"), "by_lead": {}}
    for k, x in g.groupby("lead"):
        y = x["y"].to_numpy(float)
        res = {"n": int(len(x))}
        for nm, col in (("model", "p_high"), ("persistence", "persist_p")):
            p = x[col].to_numpy(float)
            res[nm] = {"accuracy": float(((p >= .5) == (y == 1)).mean()), "brier": float(np.mean((p - y) ** 2))}
        res["rows"] = x[["issue_date", "target_quarter", "arm", "p_high", "persist_p", "H_observed", "y"]].to_dict("records")
        out["by_lead"][f"L{int(k)}"] = res
    (V.OUT / "seal_scores.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
