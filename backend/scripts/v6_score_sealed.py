"""
Score the v6 sealed tier (docs/aipheed/v6/PREREGISTRATION.md sections 5-6) against SWS rounds published since. Verifies
every seal's hash first and never edits one. A target is scored only when it has a published round and its quarter ended
more than 120 days ago. Applies the mechanical verdicts: 75 % under the frozen tolerance and, as PROPOSED_NOT_ADOPTED, the
published margin; beats all 8 baselines. Appends one line to docs/aipheed/v6/sealed/ACCESS_LOG.md.

All 8 baselines have a forecast at the same P-DASH issues: PERSIST, V6 and candidates (v6 seal), TREND-D, CLIM, SEAS-LLM, V4
(v4 seal), V2 (v2 seal), RIDGE-ALL, HFM-X (v6 baseline seal).

    python -I backend/scripts/v6_score_sealed.py [YYYY-MM-DD]
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.v4 import verdict as VD  # noqa: E402

DOCS = REPO / "docs" / "aipheed"
SEALED = DOCS / "v6" / "sealed"
OUT = DOCS / "v6" / "results"
Z95 = 1.959963984540054
BASELINES = ("PERSIST", "TREND-D", "CLIM", "RIDGE-ALL", "HFM-X", "SEAS-LLM", "V2", "V4")
SEALS = ((SEALED / "V6_PROSPECTIVE_SEAL.csv", SEALED / "V6_SEAL_SHA256.txt", None),
         (SEALED / "V6_BASELINE_SEAL.csv", SEALED / "V6_BASELINE_SEAL_SHA256.txt", None),
         (DOCS / "v4" / "sealed" / "V4_PROSPECTIVE_SEAL.csv", DOCS / "v4" / "sealed" / "V4_SEAL_SHA256.txt", ("TREND-D", "CLIM", "SEAS-LLM", "V4")),
         (DOCS / "v2" / "sealed" / "V2_PROSPECTIVE_SEAL.csv", DOCS / "v2" / "sealed" / "V2_SEAL_SHA256.txt", ("V2",)))


def load_seals() -> pd.DataFrame:
    parts = []
    for path, sha_file, keep in SEALS:
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha_file.read_text().split()[0]:
            raise SystemExit(f"{path.name}: seal hash mismatch, scoring refused")
        d = pd.read_csv(path)
        parts.append((d[d.model.isin(keep)] if keep else d)[["issue", "lead", "target", "area", "model", "f"]])
    return pd.concat(parts, ignore_index=True)


def main(today: date) -> dict:
    d = load_seals()
    full = T.quarter_table(T.load_rounds())[["area", "quarter", "y", "se", "tol", "se_pub"]].rename(columns={"quarter": "target"})
    sc = d.merge(full, on=["area", "target"], how="left")
    done = sc.target.map(lambda q: pd.Period(q.replace("-", ""), freq="Q").end_time.date() + timedelta(days=120) < today)
    sc["scorable"] = sc.y.notna() & done
    sc["hit_frozen"] = (sc.f - sc.y).abs() <= sc.tol
    sc["hit_proposed"] = (sc.f - sc.y).abs() <= Z95 * sc.se_pub
    res = {"today": today.isoformat(), "rows": int(len(d)), "scorable_rows": int(sc.scorable.sum()),
           "models": sorted(d.model.unique()), "by_lead": {}}
    for k in (1, 2, 3, 4):
        g = sc[sc.scorable & (sc.lead == k)]
        v6 = g[g.model == "V6"].sort_values(["issue", "target", "area"])
        cl = v6.target.map(T.qi).to_numpy()
        testable = v6.target.nunique() >= 10 and len(v6) >= 40
        rec = {"frozen": VD.claim_75(v6.hit_frozen.to_numpy(), cl, sealed=True),
               "proposed_NOT_ADOPTED": VD.claim_75(v6.hit_proposed.to_numpy(), cl, sealed=True)}
        if testable:
            p = {}
            for b in BASELINES:
                gb = g[g.model == b].merge(v6[["issue", "target", "area", "hit_frozen"]], on=["issue", "target", "area"], suffixes=("", "_v6"))
                p[b] = VD.paired_p(gb.hit_frozen_v6.to_numpy(), gb.hit_frozen.to_numpy(), gb.target.map(T.qi).to_numpy())
            rec["beats_all"] = VD.beats_all(p)
        else:
            rec["beats_all"] = {"verdict": "NOT_YET_TESTABLE"}
        res["by_lead"][k] = rec
    sc.to_csv(OUT / "v6_sealed_scores.csv", index=False)
    (OUT / "v6_sealed_verdict.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8", newline="\n")
    log = SEALED / "ACCESS_LOG.md"
    if not log.exists():
        log.write_text("# v6 seal access log\n\n| Run at | Scoring date | Rows scorable |\n|---|---|---|\n", encoding="utf-8", newline="\n")
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"| {datetime.now().isoformat(timespec='seconds')} | {today} | {res['scorable_rows']} of {res['rows']} |\n")
    print(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    main(date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today())
