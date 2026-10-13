"""
scripts/supplementary/devprotocol_rule_l.py

Experimental (non-production) implementation of the 2026-10-11 working decisions
(docs/WORKING_DECISIONS_AND_TRAINING_READINESS_2026-10-11.md) and refined Rule L.
It builds an input frame and training-eligibility rules for the DEVELOPMENT
protocol, and the masks of the stricter real-time protocol for reporting.

It never trains or scores a model, never rebuilds labels (labels come unchanged
from window2021_study.window_labels, definition A), never writes to production
data, and never reads or infers any SWS round after (2026, Q2).

Every date carries a type so verified dates and proxies stay distinguishable:
  "verified"  publication date stated on an original source
  "proxy"     WD1: national CPI release + 14 days standing in for the
              unverified provincial (RSSO IV-A) release
  "schedule"  documented release schedule (WD3); availability inferred from it
  "unknown"   no documented date -> treated as NOT available (Rule L4)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import scripts.supplementary.reliability_diagnostics as R
import scripts.supplementary.timing_audit as T
import scripts.supplementary.window2021_study as W
from app.ml.corpus.sws_hunger_fetcher import SWS_BAL_LUZON_VERIFIED, SWS_COVERAGE_END

ROOT = Path(".")
CPI_DATES = ROOT / "evidence/2026-10-09_readiness/cpi_final_month_release_dates.csv"
FEATURE_PROTOCOL = ROOT / "evidence/2026-10-11_working_decisions/feature_eligibility_by_protocol.csv"
SUPP_SWS = ROOT / "data/supplementary/collection_2026-10-09/sws_balance_luzon_2025_raw.csv"

PROXY_DAYS = 14                                   # WD1
REBASE_DATE = pd.Timestamp("2022-02-04")          # WD5: 2018=100 CPI first published
WINDOW_START = "2021-Q1"
PROTECTED = {"2026-Q3", "2026-Q4"}                # outcomes must never appear

# Provincial (RSSO IV-A) CPI release dates verified on a PSA source: label month -> date
PROVINCIAL_CPI_VERIFIED = {"2024-Q4": pd.Timestamp("2025-01-13")}

# Publication date and evidence class of every SWS round in the production table
# (keyed by quarter + survey label as written in SWS_BAL_LUZON_VERIFIED).
# Sources: evidence/2026-10-09_data_audit/sws_round_publication_dates_v2.csv,
# evidence/2026-10-11_collection_audit/sws_2025_round_table.csv.
SWS_PUBLICATION = {
    ("2021-Q2", "First Quarter 2021"): ("2021-07-12", "verified"),
    ("2021-Q2", "Second Quarter 2021"): ("2021-07-28", "verified"),
    ("2021-Q3", "Third Quarter 2021"): ("2021-12-06", "verified"),
    ("2021-Q4", "Fourth Quarter 2021"): ("2022-03-25", "verified"),
    ("2022-Q2", "First Quarter 2022"): ("2022-06-06", "verified"),
    ("2022-Q2", "Second Quarter 2022"): ("2022-09-10", "verified"),
    ("2022-Q3", "Third Quarter 2022"): ("2022-10-29", "verified"),
    ("2022-Q4", "Fourth Quarter 2022"): ("2023-01-19", "verified"),
    ("2023-Q1", "First Quarter 2023"): ("2023-05-11", "verified"),
    ("2023-Q2", "Second Quarter 2023"): ("2023-08-02", "verified"),
    ("2023-Q3", "Third Quarter 2023"): ("2023-11-20", "verified"),
    ("2023-Q4", "Fourth Quarter 2023"): ("2024-01-22", "verified"),
    ("2024-Q1", "First Quarter 2024"): ("2024-04-30", "verified"),
    ("2024-Q2", "Second Quarter 2024"): ("2024-07-23", "verified"),
    ("2024-Q3", "September 2024"): ("2024-10-17", "verified"),
    ("2024-Q4", "December 2024"): ("2025-01-14", "verified"),
    ("2025-Q1", "Stratbase-SWS March 15-20, 2025"): ("2025-03-29", "verified"),
    ("2025-Q4", "November 2025"): ("2026-01-14", "verified-single"),
    ("2026-Q1", "March 2026"): ("2026-05-12", "verified"),
    ("2026-Q2", "June 2026"): (None, "unknown"),          # date not established -> excluded (L4)
}

# Documented release schedules (WD3), days after the end of the reference period.
# Used only by the development protocol; the strict protocol masks these families.
SCHEDULE_DAYS = {
    "wholesale_rice": 35, "lfs_unemployment": 45, "bsp_remittances": 50, "doe_fuel": 7,
    "noaa_oni": 10, "drought_alert": 10, "ibtracs_typhoon": 7, "nasa_power_rain": 25,
    "ecb_fx": 1, "fred_brent": 7,
}

qi = R.qi


# ------------------------------------------------------------------ SWS rounds
@dataclass(frozen=True)
class Round:
    quarter: str            # fieldwork quarter
    label: str
    value: float
    published: pd.Timestamp | None
    date_type: str          # verified | verified-single | unknown
    source: str             # production | supplementary
    in_label_definition_A: bool


def _match(quarter: str, label: str):
    for (q, key), v in SWS_PUBLICATION.items():
        if q == quarter and key in label:
            return v
    raise KeyError(f"no publication record for SWS round {quarter} {label!r}")


def sws_rounds() -> list[Round]:
    """Every SWS round usable inside the 2021-2026 window, with its publication date."""
    out = []
    end_y, end_q = SWS_COVERAGE_END
    for year, q, total, _mod, _sev, label, _url in SWS_BAL_LUZON_VERIFIED:
        quarter = f"{year}-{q}"
        if qi(quarter) < qi(WINDOW_START) or (year, int(q[1])) > (end_y, end_q):
            continue
        pub, dtype = _match(quarter, label)
        out.append(Round(quarter, label, float(total), pd.Timestamp(pub) if pub else None, dtype,
                         "production", quarter <= "2025-Q4"))
    supp = pd.read_csv(SUPP_SWS)
    for r in supp.itertuples():
        dtype = "verified" if r.round_fieldwork.startswith("2025-04-23") else "verified-single"
        out.append(Round(r.fieldwork_quarter, r.sws_round_name, float(r.balance_luzon_total_hunger_pct),
                         pd.Timestamp(r.publication_date), dtype, "supplementary", False))
    assert not any(x.quarter in PROTECTED for x in out), "protected SWS outcome present"
    return sorted(out, key=lambda x: (x.published or pd.Timestamp.max, qi(x.quarter)))


def sws_known(origin: pd.Timestamp, rounds: list[Round] | None = None) -> dict:
    """Latest SWS round whose publication date is known and before the origin (Rule L2/L4)."""
    rounds = rounds if rounds is not None else sws_rounds()
    avail = [r for r in rounds if r.published is not None and r.published < origin]
    if not avail:
        return {"sws_hunger": np.nan, "sws_change": np.nan, "sws_round": None, "sws_round_quarter": None,
                "sws_published": None, "sws_date_type": None, "sws_source": None}
    last = avail[-1]
    prev = avail[-2] if len(avail) > 1 else None
    return {"sws_hunger": last.value, "sws_change": (last.value - prev.value) if prev else np.nan,
            "sws_round": last.label, "sws_round_quarter": last.quarter, "sws_published": last.published,
            "sws_date_type": last.date_type, "sws_source": last.source}


# ------------------------------------------------------------------ CPI dates
def _cpi_national() -> dict[str, pd.Timestamp]:
    d = pd.read_csv(CPI_DATES)
    return {r.label_quarter: pd.Timestamp(r.national_release) for r in d.itertuples()}


def cpi_published(ref_quarter: str, provincial: bool) -> tuple[pd.Timestamp, str]:
    """Publication date of the final-month CPI of a quarter, with its date type."""
    nat = _cpi_national()
    if provincial and ref_quarter in PROVINCIAL_CPI_VERIFIED:
        d, t = PROVINCIAL_CPI_VERIFIED[ref_quarter], "verified"
    elif ref_quarter in nat:
        d = nat[ref_quarter] + pd.Timedelta(days=PROXY_DAYS) if provincial else nat[ref_quarter]
        t = "proxy" if provincial else "verified"
    else:
        # No documented national date for this month: documented first-week practice
        # (20 dated examples, 4th-7th) -> schedule, plus the proxy buffer if provincial.
        d = T.qstart(T.nxt(ref_quarter)) + pd.Timedelta(days=7 + (PROXY_DAYS if provincial else 0))
        t = "schedule"
    if qi(ref_quarter) <= qi("2021-Q4"):
        d = max(d, REBASE_DATE)                 # WD5
    return d, t


# ------------------------------------------------------------------ labels
def label_published(q: str, protocol: str = "development") -> tuple[pd.Timestamp | None, str]:
    """When the definition-A label of quarter q became computable (Rule L1)."""
    rounds = [r for r in sws_rounds() if r.quarter == q and r.in_label_definition_A]
    if not rounds:
        return None, "no label (definition A)"
    if any(r.published is None for r in rounds):
        return None, "unknown SWS date"
    sws_last = max(r.published for r in rounds)
    cpi, ctype = cpi_published(q, provincial=True)
    if protocol == "strict" and ctype != "verified":
        return None, f"provincial CPI date {ctype} (not verified)"
    return max(sws_last, cpi), ("verified" if ctype == "verified" else ctype)


def eligible_training_quarters(target: str, protocol: str = "development") -> list[str]:
    origin = T.qstart(target)
    labels = W.window_labels(W.THR_PRIMARY)
    out = []
    for q in sorted(labels["quarter"].unique(), key=qi):
        if qi(q) >= qi(target):
            continue
        pub, _ = label_published(q, protocol)
        if pub is not None and pub < origin:
            out.append(q)
    return out


# ------------------------------------------------------------------ features
def feature_protocol() -> pd.DataFrame:
    return pd.read_csv(FEATURE_PROTOCOL)


def feature_mask(protocol: str = "development") -> list[str]:
    fp = feature_protocol()
    col = "development_protocol" if protocol == "development" else "strict_realtime_protocol"
    return fp.loc[fp[col].str.startswith("USE"), "feature"].tolist()


def development_frame() -> tuple[pd.DataFrame, list[str]]:
    """Feature rows (quarter t, forecasting target t+1) under the development protocol.

    Starts from the corrected window frame (K1-K4, rule W, strict timing, no fill),
    replaces the SWS inputs with the per-round registry (incl. the three supplementary
    2025 rounds as inputs only), applies WD1/WD5 availability to CPI inputs, applies
    documented schedules to the other families, and drops excluded inputs.
    Values that are not available at the origin become NaN, never zero.
    """
    f, inputs, gov, _ = W.window_frame(extend=True)
    f = f.copy()
    fp = feature_protocol().set_index("feature")
    rounds = sws_rounds()

    f["target_quarter"] = f["quarter"].map(T.nxt)
    f["origin"] = f["target_quarter"].map(T.qstart)
    sk = f["origin"].map(lambda o: sws_known(o, rounds))
    f["sws_hunger"] = [x["sws_hunger"] for x in sk]
    f["sws_change"] = [x["sws_change"] for x in sk]
    f["sws_age"] = [qi(t) - qi(x["sws_round_quarter"]) if x["sws_round_quarter"] else np.nan
                    for t, x in zip(f["target_quarter"], sk)]
    for k in ("sws_round", "sws_round_quarter", "sws_published", "sws_date_type", "sws_source"):
        f[k] = [x[k] for x in sk]

    # Government inputs at row t refer to quarter t-1 (= target-2) after the strict shift.
    ref = f["quarter"].map(T.prev)
    for c in inputs:
        fam = fp.loc[c, "family"] if c in fp.index else None
        if fam in ("provincial_cpi", "regional_cpi"):
            avail = ref.map(lambda q: cpi_published(q, provincial=(fam == "provincial_cpi"))[0])
            f.loc[avail >= f["origin"], c] = np.nan
        elif fam in SCHEDULE_DAYS:
            avail = ref.map(lambda q: T.qstart(T.nxt(q)) + pd.Timedelta(days=SCHEDULE_DAYS[fam]))
            f.loc[avail >= f["origin"], c] = np.nan
    usable = [c for c in feature_mask("development") if c in f.columns]
    keep = ["province_code", "quarter", "t", "target_quarter", "origin",
            "sws_round", "sws_round_quarter", "sws_published", "sws_date_type", "sws_source"]
    return f[keep + usable], usable


def eligibility_table() -> pd.DataFrame:
    """Per target quarter: eligible training labels under each protocol and the SWS input used."""
    rows = []
    rounds = sws_rounds()
    for tq in [f"{y}-Q{k}" for y in range(2021, 2027) for k in (1, 2, 3, 4) if "2021-Q3" <= f"{y}-Q{k}" <= "2026-Q4"]:
        o = T.qstart(tq)
        dev, strict = eligible_training_quarters(tq, "development"), eligible_training_quarters(tq, "strict")
        s = sws_known(o, rounds)
        rows.append({"target": tq, "origin": o.date(), "dev_training_quarters": len(dev), "dev_rows": 5 * len(dev),
                     "strict_training_quarters": len(strict), "latest_dev_label": dev[-1] if dev else None,
                     "sws_input_round": s["sws_round"], "sws_input_published": s["sws_published"],
                     "sws_input_date_type": s["sws_date_type"], "sws_input_source": s["sws_source"]})
    return pd.DataFrame(rows)
