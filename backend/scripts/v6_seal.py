"""
v6 prospective seal (docs/aipheed/v6/PREREGISTRATION.md section 3, SEALED tier). At the P-DASH issues given, issue the V6
procedure and the 4 candidates from data published before the issue, with LightGBM's explanation totals; keep only
targets with no published SWS round. Write-once; the hash goes to V6_SEAL_SHA256.txt and tests/unit/test_v6_core.py.

    python -I backend/scripts/v6_seal.py 2026-07-01 2026-10-01
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
from app.forecasting.v2 import select as S2  # noqa: E402
from app.forecasting.v4 import features as F  # noqa: E402
from app.forecasting.v6 import select as S6  # noqa: E402

SEALED = REPO / "docs" / "aipheed" / "v6" / "sealed"


def seal_rows(rr: pd.DataFrame, feats: pd.DataFrame, issue: date) -> pd.DataFrame:
    if F.snapshot(feats, issue.isoformat(), used_at=issue.isoformat()).empty:
        raise SystemExit(f"no feature snapshot for {issue}: refusing to seal LightGBM forecasts without their inputs")
    wf = S6.walk_forward(rr, feats, issue)
    chosen, _ = S6.select(wf, rr, issue)
    published = set(rr["quarter"])
    g = wf[wf.issue == issue.isoformat()]
    rows = []
    for k in S2.LEADS:
        for m in (*S6.CANDIDATES, "V6"):
            mm = chosen if m == "V6" else m
            half, n = S2.conformal_halfwidth(wf, rr, issue, mm, k)
            for r in g[(g.model == mm) & (g.lead == k)].itertuples():
                if T.qs(r.tqi) in published:
                    continue
                lo, hi, _ = S2.interval(r.f, r.sd, half)
                c = getattr(r, "contributions", None)
                rows.append({"issue": issue.isoformat(), "lead": k, "target": T.qs(r.tqi), "area": r.area, "model": m,
                             "source_model": mm, "f": round(r.f, 6), "lo80": round(lo, 6), "hi80": round(hi, 6),
                             "latest": r.latest, "predicted_change": round(r.predicted_change, 6), "n_residuals": n,
                             "lgbm_explanation_totals": c if isinstance(c, str) else "{}"})
    return pd.DataFrame(rows)


def main(argv: list[str]) -> None:
    out = SEALED / "V6_PROSPECTIVE_SEAL.csv"
    if out.exists():
        sys.exit(f"{out} exists: the seal is write-once")
    rr, feats = T.load_rounds(), F.table()
    d = pd.concat([seal_rows(rr, feats, date.fromisoformat(a)) for a in argv], ignore_index=True)
    SEALED.mkdir(parents=True, exist_ok=True)
    d.to_csv(out, index=False, lineterminator="\n")
    h = hashlib.sha256(out.read_bytes()).hexdigest()
    (SEALED / "V6_SEAL_SHA256.txt").write_text(f"{h}  V6_PROSPECTIVE_SEAL.csv\n", encoding="utf-8", newline="\n")
    print(d.groupby(["issue", "model"]).size().to_string())
    print(d[(d.lead == 2) & (d.area == "balance_luzon")].drop(columns=["lgbm_explanation_totals"]).to_string())
    print(h)


if __name__ == "__main__":
    main(sys.argv[1:])
