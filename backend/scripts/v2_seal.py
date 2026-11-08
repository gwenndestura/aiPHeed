"""
v2 prospective seal (docs/aipheed/v2/PREREGISTRATION.md section 7). For the given quarter-start issues, the V2
procedure (inner-fold selection + selected model + conformal interval) and each fixed candidate are issued from the
data published before the issue, and only targets with no published SWS round are kept. Write-once: refuses to
overwrite an existing seal file. Its SHA-256 goes to tests/unit/test_v2_core.py.

    python -I backend/scripts/v2_seal.py 2026-07-01 2026-10-01
"""
from __future__ import annotations

import hashlib
import sys
from datetime import date
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.v2 import models as V  # noqa: E402
from app.forecasting.v2 import select as S  # noqa: E402

SEALED = REPO / "docs" / "aipheed" / "v2" / "sealed"


def seal_rows(rr: pd.DataFrame, issue: date) -> pd.DataFrame:
    wf = S.walk_forward(rr, issue)
    chosen, _ = S.select(wf, rr, issue)
    g = wf[wf.issue == issue.isoformat()]
    published = set(rr["quarter"])
    rows = []
    for k in S.LEADS:
        for m in (*V.CANDIDATES, "V2"):
            mm = chosen if m == "V2" else m
            half, n = S.conformal_halfwidth(wf, rr, issue, mm, k)
            for r in g[(g.model == mm) & (g.lead == k)].itertuples():
                if T.qs(r.tqi) in published:
                    continue
                lo, hi, how = S.interval(r.f, r.sd, half)
                rows.append({"issue": r.issue, "lead": k, "target": T.qs(r.tqi), "area": r.area, "model": m,
                             "source_model": mm, "f": round(r.f, 6), "lo80": round(lo, 6), "hi80": round(hi, 6),
                             "interval": how, "n_residuals": n, "latest": r.latest, "latest_quarter": T.qs(r.latest_qi),
                             "h": r.h, "q": round(r.q, 6), "kappa": r.kappa})
    return pd.DataFrame(rows)


def main(argv: list[str]) -> None:
    issues = [date.fromisoformat(a) for a in argv]
    out = SEALED / "V2_PROSPECTIVE_SEAL.csv"
    if out.exists():
        sys.exit(f"{out} exists: the seal is write-once; add a new file for later issues")
    rr = T.load_rounds()
    d = pd.concat([seal_rows(rr, i) for i in issues], ignore_index=True)
    SEALED.mkdir(parents=True, exist_ok=True)
    d.to_csv(out, index=False, lineterminator="\n")
    h = hashlib.sha256(out.read_bytes()).hexdigest()
    (SEALED / "V2_SEAL_SHA256.txt").write_text(f"{h}  V2_PROSPECTIVE_SEAL.csv\n", encoding="utf-8", newline="\n")
    print(d.to_string())
    print(h)


if __name__ == "__main__":
    main(sys.argv[1:])
