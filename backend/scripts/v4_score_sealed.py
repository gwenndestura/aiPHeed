"""
Score the v4 sealed tier (docs/aipheed/v4/PREREGISTRATION.md sections 5-6) against SWS rounds published since. Verifies
the seal hash, scores only targets with a published round whose quarter ended more than 120 days ago, applies the
mechanical verdicts (75 % claim under the frozen tolerance and, as PROPOSED_NOT_ADOPTED, the amended tolerance; beats
every baseline) and appends a line to docs/aipheed/v4/sealed/ACCESS_LOG.md. Never edits the seal.

Baselines on sealed rows: PERSIST, TREND-D, CLIM, SEAS-LLM (v4 seal, same cutoff), V2 (v2 seal, same issues), HFM-X
(E134 seal, issued 2026-11-01 with MORE information than the P-DASH issue: a conservative comparison). RIDGE-ALL has no
prospective forecast: reported as NOT_AVAILABLE, so "beats all" can be YES only once it is supplied.

    python -I backend/scripts/v4_score_sealed.py [YYYY-MM-DD]
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.v4 import verdict as VD  # noqa: E402

SEALED = REPO / "docs" / "aipheed" / "v4" / "sealed"
OUT = REPO / "docs" / "aipheed" / "v4" / "results"
V2SEAL = REPO / "docs" / "aipheed" / "v2" / "sealed" / "V2_PROSPECTIVE_SEAL.csv"
E134SEAL = REPO / "aipheed-backend-aligned" / "experiments" / "E134_Information_Bottleneck" / "sealed" / "E134_PROSPECTIVE_SEAL.csv"
Z95 = 1.959963984540054


def main(today: date) -> dict:
    seal = SEALED / "V4_PROSPECTIVE_SEAL.csv"
    if hashlib.sha256(seal.read_bytes()).hexdigest() != (SEALED / "V4_SEAL_SHA256.txt").read_text().split()[0]:
        raise SystemExit("seal hash mismatch: scoring refused")
    d = pd.read_csv(seal)
    v2 = pd.read_csv(V2SEAL)
    d = pd.concat([d, v2[v2.model == "V2"].assign(source_model="PERSIST")[["issue", "lead", "target", "area", "model", "f"]]])
    e = pd.read_csv(E134SEAL)
    for r in d[d.model == "V4"][["issue", "lead", "target", "area"]].drop_duplicates().itertuples():
        m = e[(e.target == r.target) & (e.area == r.area)]
        if len(m):
            d = pd.concat([d, pd.DataFrame([{"issue": r.issue, "lead": r.lead, "target": r.target, "area": r.area,
                                             "model": "HFM-X", "f": float(m["HFM-X"].iloc[0])}])])
    full = T.quarter_table(T.load_rounds())[["area", "quarter", "y", "se", "tol", "se_pub"]].rename(columns={"quarter": "target"})
    sc = d.merge(full, on=["area", "target"], how="left")
    done = sc.target.map(lambda q: pd.Period(q.replace("-", ""), freq="Q").end_time.date() + timedelta(days=120) < today)
    sc["scorable"] = sc.y.notna() & done
    sc["hit_frozen"] = (sc.f - sc.y).abs() <= sc.tol
    sc["hit_amended"] = (sc.f - sc.y).abs() <= Z95 * sc.se_pub
    res = {"today": today.isoformat(), "rows": int(len(d)), "scorable_rows": int(sc.scorable.sum()), "by_lead": {}}
    for k in (1, 2, 3, 4):
        g = sc[sc.scorable & (sc.lead == k)]
        v4 = g[g.model == "V4"].sort_values(["issue", "target", "area"])
        cl = v4.target.map(T.qi).to_numpy()
        testable = v4.target.nunique() >= 10 and len(v4) >= 40
        rec = {"frozen": VD.claim_75(v4.hit_frozen.to_numpy(), cl, sealed=True),
               "amended_PROPOSED_NOT_ADOPTED": VD.claim_75(v4.hit_amended.to_numpy(), cl, sealed=True)}
        p = {}
        for b in ("PERSIST", "TREND-D", "CLIM", "SEAS-LLM", "V2", "HFM-X"):
            gb = g[g.model == b].merge(v4[["issue", "target", "area", "hit_frozen"]], on=["issue", "target", "area"], suffixes=("", "_v4"))
            p[b] = VD.paired_p(gb.hit_frozen_v4.to_numpy(), gb.hit_frozen.to_numpy(), gb.target.map(T.qi).to_numpy()) if testable and len(gb) else None
        rec["beats_all"] = VD.beats_all(p, testable=testable) if testable else {"verdict": "NOT_YET_TESTABLE"}
        rec["beats_all"]["RIDGE-ALL"] = "NOT_AVAILABLE (no prospective forecast)"
        res["by_lead"][k] = rec
    sc.to_csv(OUT / "v4_sealed_scores.csv", index=False)
    (OUT / "v4_sealed_verdict.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8", newline="\n")
    log = SEALED / "ACCESS_LOG.md"
    if not log.exists():
        log.write_text("# v4 seal access log\n\n| Run at | Scoring date | Rows scorable |\n|---|---|---|\n", encoding="utf-8", newline="\n")
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"| {datetime.now().isoformat(timespec='seconds')} | {today} | {res['scorable_rows']} of {res['rows']} |\n")
    print(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    main(date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today())
