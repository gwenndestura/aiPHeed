"""PAR quarterly cyclone counts for FIRI3 (Amendment 3, E127_FIRI3_PROTOCOL_AMENDMENT_3.md).

Same boundary, storm identification and quarter assignment as E114 (collect_covariates.ibtracs) with the E125 storm key:
    box 5-25N, 115-135E; SEASON >= 1996; a storm is counted in the quarter of its first fix inside the box;
    one storm = one key per IBTrACS SID (its JTWC ATCF id where present, otherwise the SID).
Difference from E114: every quarter the file covers completely is recorded, with 0 when no storm qualifies. A quarter the
file does not cover completely is reported as not covered and is not passed on (it stays missing, never filled).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

BOX = (5.0, 25.0, 115.0, 135.0)                     # approved simplified PAR box (E114)
MIN_SEASON = 1996


def qlabel(q: int) -> str:
    return f"{q // 4}-Q{q % 4 + 1}"


def qstart(q: int) -> pd.Timestamp:
    return pd.Timestamp(q // 4, (q % 4) * 3 + 1, 1)


def load_tracks(path: Path) -> pd.DataFrame:
    t = pd.read_csv(path, skiprows=[1], usecols=["SID", "SEASON", "NAME", "ISO_TIME", "LAT", "LON", "USA_ATCF_ID"], low_memory=False)
    return prepare(t)


def prepare(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t["LAT"], t["LON"] = pd.to_numeric(t["LAT"], errors="coerce"), pd.to_numeric(t["LON"], errors="coerce")
    t["SEASON"] = pd.to_numeric(t["SEASON"], errors="coerce")
    t["ISO_TIME"] = pd.to_datetime(t["ISO_TIME"], errors="coerce")
    t = t.dropna(subset=["ISO_TIME"])
    atcf = t["USA_ATCF_ID"].where(t["USA_ATCF_ID"].notna() & t["USA_ATCF_ID"].astype(str).str.strip().ne(""))
    key = atcf.groupby(t["SID"]).agg(lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None)
    t["STORM"] = t["SID"].map(key).fillna(t["SID"])
    t["q"] = t["ISO_TIME"].dt.year * 4 + (t["ISO_TIME"].dt.month - 1) // 3
    return t


def par_quarterly(tracks: pd.DataFrame, start_q: int, end_q: int, source: str = "") -> pd.DataFrame:
    """One row per quarter in [start_q, end_q]: count (0 allowed) for covered quarters; status 'not_covered' otherwise."""
    first_fix, last_fix = tracks["ISO_TIME"].min(), tracks["ISO_TIME"].max()
    box = tracks[(tracks["SEASON"] >= MIN_SEASON) & tracks["LAT"].between(BOX[0], BOX[1]) & tracks["LON"].between(BOX[2], BOX[3])]
    first = box.sort_values("ISO_TIME").groupby("STORM").first().reset_index()
    rows = []
    for q in range(start_q, end_q + 1):
        covered = bool(first_fix <= qstart(q) and last_fix >= qstart(q + 1))
        g = first[first["q"] == q]
        active = box[box["q"] == q]["STORM"].nunique()
        if covered:
            rows.append({"q": q, "quarter": qlabel(q), "count": int(len(g)), "status": "verified", "covered": True,
                         "storms": "; ".join(sorted(f"{s}({n})" for s, n in zip(g["STORM"], g["NAME"]))),
                         "storms_active_in_box": int(active), "sids": int(g["SID"].nunique()) if len(g) else 0,
                         "evidence": (f"{len(g)} storm(s) first entered the box" if len(g) else
                                      f"no storm first entered the box; file covers the quarter (first fix {first_fix:%Y-%m-%d}, last fix {last_fix:%Y-%m-%d})"),
                         "source": source})
        else:
            rows.append({"q": q, "quarter": qlabel(q), "count": None, "status": "not_covered", "covered": False, "storms": "", "storms_active_in_box": int(active),
                         "sids": 0, "evidence": f"file does not cover the full quarter (first fix {first_fix:%Y-%m-%d}, last fix {last_fix:%Y-%m-%d})", "source": source})
    return pd.DataFrame(rows)


def as_firi3_rows(pq: pd.DataFrame, avail_of) -> pd.DataFrame:
    """Covered quarters only, as FIRI3 observation rows for series `typhoons_PAR` (unit PHILIPPINES)."""
    c = pq[pq["covered"]]
    return pd.DataFrame({"feature": "typhoons_PAR", "unit": "PHILIPPINES", "period": c["q"].astype(int), "value": c["count"].astype(float),
                         "avail": [avail_of(int(q)) for q in c["q"]], "status": "verified", "resolution": "national",
                         "source": [f"typhoons_PAR @ PHILIPPINES (Amendment 3; {s})" for s in c["source"]]})
