"""E34 fix D3, applied identically to E31 backend_dev and the promoted backend/:

/forecast returned alert = (riskScore >= 0.60), and the dashboard drew an "Active alert" badge from the same client-side
threshold. That bypasses the E31 alert workflow (app/quarterly/alerts_e31.py: candidates follow documented evidence
rules, are STAGED, and reach the public only after a DA Region IV-A administrator confirms them; E31 R6). With an empty
alert table every province above 0.60 still showed "Active alert".
Now `alert` is true only when a CONFIRMED alert exists for the subject's area and quarter: the region view uses the
regional alert (one CALABARZON alert, never five provincial copies), a province its own alert, a municipality its
province's alert. usage: PY -B runner/e34_patch_alerts.py <backend_dir> [<backend_dir> ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

OLD_CALL = '''        alert=(body["riskScore"] or 0) >= ref.ALERT_THRESHOLD,
'''
NEW_CALL = '''        # E34 (D3): only an alert a DA administrator has CONFIRMED is public; never a score threshold alone.
        alert=await _confirmed_alert(db, scope, id, q, body),
'''
OLD_ANCHOR = '''def _quarter_label(quarter: str) -> str:'''
NEW_ANCHOR = '''async def _confirmed_alert(db: AsyncSession, scope: str, subject_id: str, quarter: str, body: dict) -> bool:
    """True when a DA administrator has confirmed an alert for this area and quarter (E34, D3). The region view uses
    the regional alert; a province its own; a municipality its province's."""
    from app.db.repository.alert_repo import AlertRepository
    from app.quarterly.alerts_e31 import REGION_CODE

    if scope == "region":
        code = REGION_CODE
    elif scope == "province":
        code = ref.province_code(subject_id.lower())
    else:
        code = ref.province_code(body.get("provinceId") or "")
    if code is None:
        return False
    return any(a.quarter == quarter and a.province_code == code and not a.dismissed
               for a in await AlertRepository(db).get_confirmed())


def _quarter_label(quarter: str) -> str:'''


def sub(p: Path, old: str, new: str):
    s = p.read_text(encoding="utf-8").replace("\r\n", "\n")
    if new in s:
        return "already"
    assert s.count(old) == 1, (p, old[:50], s.count(old))
    p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
    return "patched"


if __name__ == "__main__":
    for d in map(Path, sys.argv[1:]):
        f = d / "app/api/v1/forecast.py"
        print(d, sub(f, OLD_CALL, NEW_CALL), sub(f, OLD_ANCHOR, NEW_ANCHOR))
