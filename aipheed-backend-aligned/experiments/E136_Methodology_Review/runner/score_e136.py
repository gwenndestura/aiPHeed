"""
E134 Addendum 2 scorer, primary criterion only: |forecast - SWS| <= 1.645 x SE of the SWS quarter. Scores the amended
primary SEAS-LLM (E132 seal cea5a2ec) and the challengers SIMPLE (E136 seal 9bccb2ec) and HFM-X (E133 seal efba3235),
plus every E136 re-issue, against SWS quarters after 2026-Q3. Verifies every hash; reports N1-N7 per model and lead
once >= 10 target quarters are scored (80 % intervals from the sealed files). Append-only outputs.

    python -I runner/score_e136.py      -> out/seal_scores/score_<run_utc>.csv and .json
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
EXP = ROOT.parent
sys.path.insert(0, str(EXP / "E131_Objectives_Resolution" / "runner"))
import e131_x1 as X  # noqa: E402

L = X.L
NEW_ROUNDS = EXP / "E131_Objectives_Resolution" / "data" / "sws_rounds_after_2026Q3.csv"
SEALS = {"SEAS-LLM": (EXP / "E132_Final_Methodology" / "sealed" / "E132_PROSPECTIVE_SEAL.csv",
                      "cea5a2ec3d3b1447b7334fac6a8b3d38fb4d59fd5863eda5c1e870ff47723a57"),
         "SIMPLE": (ROOT / "sealed" / "E136_PROSPECTIVE_SEAL.csv",
                    "9bccb2ec622c67cb2ac083967677898b0728dab498eb0f17014634f9011e68a5"),
         "HFM-X": (EXP / "E133_Forecasting_Breakthrough" / "sealed" / "E133_PROSPECTIVE_SEAL.csv",
                   "efba3235b399b18e5399fe219f240dc5381580b231964d5cde5b121a5450f8b9")}
MODELS = ["SEAS-LLM", "SIMPLE", "HFM-X"]
CRITERION = "primary only: |forecast - SWS| <= 1.645 x SE of the SWS quarter (E131 protocol section 1; E131 Addendum 1)"


def _rows(d: pd.DataFrame, m: str, source: str, issue_col: str | None) -> list[dict]:
    return [{"model": m, "source": source, "issue": (r[issue_col] if issue_col else "2026-11-01"), "lead": int(r["lead"]),
             "area": r["area"], "target": r["target"], "f": float(r[m]), "lo80": float(r[f"{m}_lo80"]),
             "hi80": float(r[f"{m}_hi80"])} for _, r in d.iterrows()]


def forecasts() -> pd.DataFrame:
    rows = []
    for m, (p, sha) in SEALS.items():
        assert hashlib.sha256(p.read_bytes()).hexdigest() == sha, f"{p.name} changed since it was frozen"
        rows += _rows(pd.read_csv(p), m, p.name, None)
    log = ROOT / "sealed" / "E136_REISSUE_SHA256.txt"
    if log.exists():
        for line in log.read_text().splitlines():
            h, name = line.split()
            p = ROOT / "sealed" / name
            assert hashlib.sha256(p.read_bytes()).hexdigest() == h, f"{name} changed since it was written"
            d = pd.read_csv(p)
            for m in MODELS:
                rows += _rows(d, m, name, "issue")
    return pd.DataFrame(rows)


def score(F: pd.DataFrame, rounds_path: Path) -> tuple[pd.DataFrame, dict]:
    new = X.rounds(rounds_path)
    assert (new["quarter"].map(L.qi) > L.qi("2026-Q3")).all(), "the new-rounds file may only hold quarters after 2026-Q3"
    allr = pd.concat([X.rounds(), new], ignore_index=True)
    qt = X.quarter_table(new).set_index(["area", "quarter"])
    S = F[[(a, t) in qt.index for a, t in zip(F["area"], F["target"])]].copy()
    S["y"] = [float(qt.loc[(a, t), "y"]) for a, t in zip(S["area"], S["target"])]
    S["se"] = [float(qt.loc[(a, t), "se"]) for a, t in zip(S["area"], S["target"])]
    S["tolerance_primary"] = L.Z90 * S["se"]
    S["within_primary"] = (S["f"] - S["y"]).abs() <= S["tolerance_primary"]
    base = {}
    for issue in S["issue"].unique():
        qa = X.asof(allr, pd.Timestamp(issue).date())
        for a in X.AREAS:
            s = qa[qa.area == a].sort_values("qi")
            base[(issue, a)] = (float(s["y"].iloc[-1]), float(s["y"].mean()))
    S["persistence"] = [base[(i, a)][0] for i, a in zip(S["issue"], S["area"])]
    S["climatology"] = [base[(i, a)][1] for i, a in zip(S["issue"], S["area"])]
    summ = {"criterion": CRITERION, "rows_scored": int(len(S)), "by_model_lead": {}}
    for (m, k), g in S.groupby(["model", "lead"]):
        rec = {"n": int(len(g)), "target_quarters": int(g["target"].nunique()),
               "within_primary": float(g["within_primary"].mean()), "mae": float((g["f"] - g["y"]).abs().mean())}
        if g["target"].nunique() >= 10:
            d = pd.DataFrame({"y": g["y"], "se": g["se"], "target_q": g["target"].map(L.qi), "province": g["area"],
                              f"f_{m}": g["f"], f"lo80_{m}": g["lo80"], f"hi80_{m}": g["hi80"],
                              "f_persistence": g["persistence"], "f_climatology": g["climatology"]})
            rel = L.numeric_reliability(d, m, ["persistence", "climatology"])
            rec["N1_N7"], rec["passed_all"] = rel["rules"], rel["passed"]
        summ["by_model_lead"][f"{m}|{k}"] = rec
    return S, summ


def main(out_dir: Path = ROOT / "out" / "seal_scores") -> None:
    F = forecasts()
    if not NEW_ROUNDS.exists():
        sys.exit("nothing to score: SWS has not published 2026-Q4 yet")
    S, summ = score(F, NEW_ROUNDS)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    S.to_csv(out_dir / f"score_{stamp}.csv", index=False)
    (out_dir / f"score_{stamp}.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print(json.dumps(summ, indent=1)[:3000])


if __name__ == "__main__":
    main()
