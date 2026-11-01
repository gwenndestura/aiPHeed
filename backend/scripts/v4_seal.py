"""
v4 prospective seal (docs/aipheed/v4/PREREGISTRATION.md section 3, SEALED tier). At the P-DASH issues given, issue the
V4 procedure, the 4 candidates and the baselines computable at the same information cutoff with backend code (TREND-D,
CLIM, SEAS-LLM); keep only targets with no published SWS round. Write-once; hash in tests/unit/test_v4_core.py.

    python -I backend/scripts/v4_seal.py 2026-07-01 2026-10-01
"""
from __future__ import annotations

import hashlib
import sys
from datetime import date
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import models as M  # noqa: E402
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.v2 import select as S2  # noqa: E402
from app.forecasting.v4 import features as F  # noqa: E402
from app.forecasting.v4 import select as S4  # noqa: E402

SEALED = REPO / "docs" / "aipheed" / "v4" / "sealed"


def seal_rows(rr: pd.DataFrame, feats: pd.DataFrame, issue: date) -> pd.DataFrame:
    wf = S4.walk_forward(rr, feats, issue)
    chosen, _ = S4.select(wf, rr, issue)
    known = T.known_at(rr, issue)
    D = S2.dashboard_quarter(issue)
    published = set(rr["quarter"])
    seas = M.fit_seas(known)
    trend, clim = M.trend_d(known), known.groupby("area").y.mean().to_dict()
    g = wf[wf.issue == issue.isoformat()]
    rows = []
    for k in S2.LEADS:
        tq = D - 1 + k
        if T.qs(tq) in published:
            continue
        sf = M.forecast_seas(known, seas, tq)
        for m in (*S4.CANDIDATES, "V4"):
            mm = chosen if m == "V4" else m
            half, n = S2.conformal_halfwidth(wf, rr, issue, mm, k)
            for r in g[(g.model == mm) & (g.lead == k)].itertuples():
                lo, hi, _ = S2.interval(r.f, r.sd, half)
                rows.append({"issue": issue.isoformat(), "lead": k, "target": T.qs(tq), "area": r.area, "model": m,
                             "source_model": mm, "f": round(r.f, 6), "lo80": round(lo, 6), "hi80": round(hi, 6),
                             "latest": r.latest, "features": getattr(r, "features", "[]") if isinstance(getattr(r, "features", "[]"), str) else "[]"})
        for a in sf:
            for m, f in (("TREND-D", trend[a]), ("CLIM", clim[a]), ("SEAS-LLM", sf[a]["f"])):
                rows.append({"issue": issue.isoformat(), "lead": k, "target": T.qs(tq), "area": a, "model": m,
                             "source_model": m, "f": round(float(f), 6), "lo80": None, "hi80": None, "latest": None,
                             "features": "[]"})
    return pd.DataFrame(rows)


def main(argv: list[str]) -> None:
    out = SEALED / "V4_PROSPECTIVE_SEAL.csv"
    if out.exists():
        sys.exit(f"{out} exists: the seal is write-once")
    rr, feats = T.load_rounds(), F.table()
    d = pd.concat([seal_rows(rr, feats, date.fromisoformat(a)) for a in argv], ignore_index=True)
    SEALED.mkdir(parents=True, exist_ok=True)
    d.to_csv(out, index=False, lineterminator="\n")
    h = hashlib.sha256(out.read_bytes()).hexdigest()
    (SEALED / "V4_SEAL_SHA256.txt").write_text(f"{h}  V4_PROSPECTIVE_SEAL.csv\n", encoding="utf-8", newline="\n")
    print(d.groupby(["issue", "model"]).size().to_string())
    print(d[(d.lead == 2) & (d.area == "balance_luzon")].to_string())
    print(h)


if __name__ == "__main__":
    main(sys.argv[1:])
