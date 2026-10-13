"""Score E24v2 prospective seals AFTER the owner authorizes the outcomes (class B; FROZEN_EVALUATION_PROTOCOL.md 5, 9).

Refuses to run unless:
  * every seal's prospective_forecasts.csv still matches the SHA-256 in its SEAL_PROSPECTIVE.json;
  * an authorization JSON names the outcome CSV and its SHA-256 (the owner's file-by-file authorization), and the
    outcome CSV on disk matches that hash;
  * the outcome quarters were not used by the seal (they are all >= the seal's first target quarter).

Outcome CSV columns: target_quarter, province_code, S1, D  (S1 = H + 2D for T1; D for T2).
Pools every seal under runs/SEAL_*; a generalization claim (C9) needs >= 8 distinct scored origins and >= 5 LOW rows;
otherwise the verdict is INSUFFICIENT_PROSPECTIVE_EVIDENCE.  Usage:
  python -B runner/score_prospective.py --outcomes <csv> --authorization <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

EXP = Path(__file__).resolve().parents[1]
MIN_ORIGINS, MIN_PER_CLASS = 8, 5


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_seals(root: Path) -> pd.DataFrame:
    parts = []
    for d in sorted(root.glob("SEAL_*")):
        s = json.loads((d / "SEAL_PROSPECTIVE.json").read_text(encoding="utf-8"))
        f = d / "prospective_forecasts.csv"
        if sha(f) != s["sha256"]:
            raise SystemExit(f"seal mismatch: {f} was modified after sealing; refusing to score")
        x = pd.read_csv(f, dtype={"province_code": str})
        x["seal"] = d.name
        x["sealed_utc"] = s["created_utc"]
        parts.append(x)
    if not parts:
        raise SystemExit("no seals found")
    return pd.concat(parts, ignore_index=True)


def check_authorization(outcomes: Path, auth: Path) -> dict:
    a = json.loads(auth.read_text(encoding="utf-8"))
    rec = {r["path"]: r["sha256"] for r in a.get("authorized_files", [])}
    key = str(outcomes.resolve())
    if key not in rec and outcomes.name not in rec:
        raise SystemExit("the outcome file is not named in the authorization record; refusing")
    want = rec.get(key, rec.get(outcomes.name))
    if sha(outcomes) != want:
        raise SystemExit("the outcome file does not match its authorized SHA-256; refusing")
    if not a.get("authorized_by") or not a.get("authorized_on"):
        raise SystemExit("authorization record lacks authorized_by / authorized_on; refusing")
    return a


def score(F: pd.DataFrame, O: pd.DataFrame) -> dict:
    m = F.merge(O, on=["target_quarter", "province_code"], how="inner")
    if m.empty:
        return {"verdict": "NO_OUTCOMES_YET"}
    m["y"] = np.where(m["target"] == "T1", (m["S1"] > m["threshold"]).astype(int), (m["D"] > 0).astype(int))
    out = {}
    for (tg, k), g in m.groupby(["target", "lead"]):
        res = {}
        for mod, gg in g.groupby("model"):
            y, s = gg["y"].to_numpy(), gg["score"].to_numpy()
            res[mod] = {"rows": int(len(gg)), "accuracy": float(((s >= .5).astype(int) == y).mean()),
                        "brier": float(((s - y) ** 2).mean()), "HIGH": int(y.sum()), "LOW": int((1 - y).sum())}
        origins = int(g["origin"].nunique())
        low = int((1 - g[g["model"] == g["model"].iloc[0]]["y"]).sum())
        res["_evidence"] = {"distinct_origins": origins, "LOW_rows": low,
                            "verdict": ("ASSESSABLE" if origins >= MIN_ORIGINS and low >= MIN_PER_CLASS
                                        else "INSUFFICIENT_PROSPECTIVE_EVIDENCE")}
        out[f"{tg}_k{k}"] = res
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--outcomes", required=True)
    ap.add_argument("--authorization", required=True)
    ap.add_argument("--runs", default=str(EXP / "runs"))
    a = ap.parse_args(argv)
    outcomes, auth = Path(a.outcomes), Path(a.authorization)
    rec = check_authorization(outcomes, auth)
    F = load_seals(Path(a.runs))
    O = pd.read_csv(outcomes, dtype={"province_code": str})
    first = F.groupby("seal")["target_quarter"].min()
    if (O["target_quarter"].map(lambda q: q < first.min())).any():
        raise SystemExit("outcome rows precede the sealed targets; refusing")
    res = {"authorization": rec, "seals": sorted(F["seal"].unique()), "results": score(F, O)}
    out = Path(a.runs) / "PROSPECTIVE_SCORES.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res["results"], indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
