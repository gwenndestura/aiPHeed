"""E126 September 2026 LFS refresh (E126_LFS_REFRESH_READINESS.md).

Re-queries the two PSA OpenSTAT LFS tables used for the national unemployment feature:
    1B/LFS/0021B3FKEI2.px  Rates of key employment indicators (the E114 / E119 source; frozen method = mean of monthly rates)
    1B/LFS/0011B3FKEI1.px  Levels of key employment indicators (labour force, unemployed: for the level-based quarter rate)
saves both raw with fetch time and SHA-256, and reports whether July, August and September 2026 are all published. If
September is absent the result is BLOCKED and nothing is recomputed. Both quarterly methods are reported side by side;
the frozen FIRI3 input stays the E119 method (mean of the monthly rates) unless the owner approves a change.

    python lfs_refresh.py [--out DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def query_tables():
    sys.path.insert(0, str(EXP / "E114_Final_Run" / "runner"))
    import collect_covariates as CC                                   # noqa: E402  (same OpenSTAT client as E114)
    rates = CC.lfs()                                                  # E114 selection: Unemployment Rate, Philippines
    meta = CC.px_meta("1B/LFS/0011B3FKEI1.px")
    sel = {}
    for v in meta["variables"]:
        txt = v["valueTexts"]
        if any("Labor Force" in t for t in txt) or any("Unemployed" in t for t in txt):
            sel[v["code"]] = [t for t in txt if t.strip() in ("Labor Force", "Unemployed", "Unemployed Persons", "Persons in the Labor Force")]
        elif any(t.strip() == "Both sexes" for t in txt):
            sel[v["code"]] = ["Both sexes"]
    levels = CC.px_query("1B/LFS/0011B3FKEI1.px", sel) if sel else pd.DataFrame()
    titles = {"rates": CC.px_meta("1B/LFS/0021B3FKEI2.px").get("title"), "levels": meta.get("title")}
    return rates, levels, titles


def quarter_months(df, year, q, col):
    m = df[(df["Year"].astype(int) == year) & df["Month"].isin(MONTHS[(q - 1) * 3:q * 3])]
    return pd.to_numeric(m[col], errors="coerce")


def evaluate(rates: pd.DataFrame, levels: pd.DataFrame, year=2026, q=3) -> dict:
    r = quarter_months(rates, year, q, "Unemployment Rate Both sexes")
    months_present = [mo for mo, v in zip(MONTHS[(q - 1) * 3:q * 3], r.tolist() + [None] * (3 - len(r))) if v is not None and not pd.isna(v)]
    out = {"quarter": f"{year}-Q{q}", "months_present": months_present, "complete": len(months_present) == 3}
    if not out["complete"]:
        out.update(status="BLOCKED", reason=f"{3 - len(months_present)} of 3 months not published", mean_of_rates=None, level_based_rate=None)
        return out
    out["mean_of_rates"] = float(r.mean())                            # frozen E119 method
    lv = levels.copy()
    lf_col = next((c for c in lv.columns if "Labor Force" in c and "Participation" not in c), None)
    un_col = next((c for c in lv.columns if "Unemployed" in c), None)
    if lf_col and un_col:
        lf = quarter_months(lv, year, q, lf_col)
        un = quarter_months(lv, year, q, un_col)
        out["level_based_rate"] = float(100 * un.sum() / lf.sum()) if len(lf) == 3 and len(un) == 3 and lf.notna().all() and un.notna().all() else None
    else:
        out["level_based_rate"] = None
    out["status"] = "READY WITH WARNING"                              # publication date: release rule unless a dated release is archived
    return out


def main(out_dir: Path):
    raw = out_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    rates, levels, titles = query_tables()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    files = {}
    for name, df in (("psa_lfs_0021B3FKEI2_rates.csv", rates), ("psa_lfs_0011B3FKEI1_levels.csv", levels)):
        p = raw / name
        df.to_csv(p, index=False)
        files[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    res = evaluate(rates, levels)
    rec = {"fetched_utc": now, "titles": titles, "files_sha256": files, **res}
    (out_dir / "lfs_refresh_result.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec, indent=1))
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data"))
    main(Path(ap.parse_args().out))
