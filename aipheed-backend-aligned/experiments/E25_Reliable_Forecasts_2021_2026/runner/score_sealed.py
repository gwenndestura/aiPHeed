"""Score sealed prospective forecasts ONLY for outcomes the researcher has authorized by path and SHA-256.

The researcher writes inputs/AUTHORIZED_OUTCOMES.json, for example:
  {"authorized_by": "<name>", "date": "YYYY-MM-DD",
   "files": [{"path": "<absolute path>", "sha256": "<64 hex>", "kind": "sws_round",
              "quarter": "2026-Q4", "published": "YYYY-MM-DD"},
             {"path": "...", "sha256": "...", "kind": "provincial_food_cpi_yoy", "months": ["2026-10", "2026-11", "2026-12"]}]}
Refusals (exit 2): no authorization file; a hash mismatch; a file holding a quarter or month that is not listed; a
seal whose bytes differ from its recorded hash; a target whose inputs are incomplete (no partial scoring).
Usage: python -B runner/score_sealed.py <SEAL folder under runs/ or the E24v2 seal under inputs/>"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

EXP = guard.EXP
AUTH = EXP / "inputs" / "AUTHORIZED_OUTCOMES.json"


class Refused(SystemExit):
    def __init__(self, msg):
        print("REFUSED:", msg)
        super().__init__(2)


def verified_text(path: Path, sha: str) -> str:
    p = Path(path).resolve()
    if len(sha) != 64:
        raise Refused(f"{p}: SHA-256 must be the full 64-character hash")
    guard.ALLOW[p] = (sha.lower(), None, "researcher-authorized outcome")    # pinned only for this verified read
    try:
        return guard.read_allowed_text(p)
    except guard.AccessDenied as e:
        raise Refused(str(e))


def load_authorized(auth_path: Path = AUTH):
    if not auth_path.exists():
        raise Refused(f"no researcher authorization ({auth_path.name}); sealed forecasts stay unscored")
    a = json.loads(auth_path.read_text(encoding="utf-8"))
    H, F = {}, {}
    for f in a["files"]:
        txt = verified_text(Path(f["path"]), f["sha256"])
        df = pd.read_csv(io.StringIO(txt), dtype=str)
        if f["kind"] == "sws_round":
            if set(df["quarter"]) != {f["quarter"]}:
                raise Refused(f"{f['path']} holds quarters other than {f['quarter']}")
            H.setdefault(f["quarter"], []).extend(pd.to_numeric(df["pct_total_hunger"]).tolist())
        elif f["kind"] == "provincial_food_cpi_yoy":
            if set(df["reference_month"]) - set(f["months"]):
                raise Refused(f"{f['path']} holds months that are not authorized")
            for r in df.itertuples():
                F[(r.province_code, r.reference_month)] = float(r.food_cpi_yoy_pct_raw)
        else:
            raise Refused(f"unknown kind {f['kind']}")
    return H, F


def outcomes_for(quarter: str, H: dict, F: dict, provs):
    y, n = int(quarter[:4]), int(quarter[-1])
    months = [f"{y}-{3 * (n - 1) + i:02d}" for i in (1, 2, 3)]
    if quarter not in H or any((p, m) not in F for p in provs for m in months):
        return None
    Fq = {p: np.mean([F[(p, m)] for m in months]) for p in provs}
    mean5 = np.mean(list(Fq.values()))
    Hq = float(np.mean(H[quarter]))
    return {p: {"D": Fq[p] - mean5, "S1": Hq + 2 * (Fq[p] - mean5)} for p in provs}


def main(seal_dir: Path):
    seal_dir = seal_dir.resolve()
    sj = json.loads((seal_dir / ("SEAL.json" if (seal_dir / "SEAL.json").exists() else "SEAL_PROSPECTIVE.json")).read_text(encoding="utf-8"))
    csv = seal_dir / "prospective_forecasts.csv"
    want = sj.get("sha256_forecasts") or sj.get("sha256")
    if hashlib.sha256(csv.read_bytes()).hexdigest() != want:
        raise Refused("sealed forecasts differ from their recorded hash")
    H, F = load_authorized()
    P = pd.read_csv(csv, dtype={"province_code": str})
    out = {}
    for q, g in P.groupby("target_quarter"):
        o = outcomes_for(q, H, F, sorted(g["province_code"].unique()))
        if o is None:
            out[q] = "NOT SCORED: outcomes for this quarter are not (completely) authorized"
            continue
        g = g.copy()
        g["y"] = [int(o[p]["S1"] > t) if tg.startswith("T1") else int(o[p]["D"] > 0)
                  for p, t, tg in zip(g["province_code"], g["tau"], g["target"])]
        out[q] = {f"{tg}|{arm}": {"brier": float(np.mean((gg["p"] - gg["y"]) ** 2)),
                                  "accuracy": float(((gg["p"] >= .5) == gg["y"]).mean()), "HIGH": int(gg["y"].sum()),
                                  "LOW": int((1 - gg["y"]).sum())}
                  for (tg, arm), gg in g.groupby(["target", "arm"])}
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    main(Path(sys.argv[1]))
