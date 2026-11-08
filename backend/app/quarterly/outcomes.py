"""
app/quarterly/outcomes.py  (E26)
--------------------------------
Adapters for the additional outcome and signal sources identified in E26 SOURCE_INVESTIGATION.md. Each adapter
VALIDATES a researcher-supplied file; it never fetches, fills or filters data:

* the file's SHA-256 must equal the researcher's authorization (full 64-character hash);
* required columns, geography codes (CALABARZON PSGC only) and value ranges are checked;
* every reference period must lie inside the study window (2021 onward) and not after the authorized limit;
  a file holding ANY out-of-window or unauthorized row is REFUSED, never filtered;
* every row must carry a publication date (or documented upper bound) that is not before its reference period ends.

Sources (outcome = a food-insecurity measurement; signal = a predictor):
  cbms_fies_lgu              OUTCOME  CBMS household FIES, moderate+severe %, by city/municipality (2022, 2024)
  fnri_provincial_fies       OUTCOME  DOST-FNRI NNS household FIES (or ENNS HFIAS) by province
  psa_subsistence_incidence  OUTCOME* PSA official subsistence (food poverty) incidence by province (2021, 2023)
                                      (*income-based food poverty: an official food-related outcome, not FIES)
  sws_area_series            OUTCOME  SWS hunger by survey area, or CALABARZON tabulated from SWS microdata
  dromic_affected            SIGNAL   DSWD DROMIC / NDRRMC affected families by province and event
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

import pandas as pd

CALABARZON_PROVINCES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon",
                        "PH040400000": "Rizal", "PH040500000": "Batangas"}
LGU_PREFIX = {"0410": "PH040500000", "0421": "PH040100000", "0434": "PH040200000", "0456": "PH040300000",
              "0458": "PH040400000"}
WINDOW_START = pd.Timestamp("2021-01-01")


class OutcomeRefused(Exception):
    pass


@dataclass(frozen=True)
class Spec:
    kind: str                 # "outcome" | "signal"
    required: tuple
    geo_col: str
    geo_level: str            # "province" | "lgu"
    period_start: str
    period_end: str
    value_cols: tuple
    value_range: tuple
    allowed_years: tuple | None = None


SPECS = {
    "cbms_fies_lgu": Spec("outcome", ("lgu_code", "lgu_name", "reference_year", "households_assessed",
                                      "fies_moderate_severe_pct", "source_document", "publication_date"),
                          "lgu_code", "lgu", "reference_start", "reference_end", ("fies_moderate_severe_pct",),
                          (0.0, 100.0), (2022, 2024)),
    "fnri_provincial_fies": Spec("outcome", ("province_code", "survey", "scale", "reference_start", "reference_end",
                                             "prevalence_pct", "n_households", "publication_date"),
                                 "province_code", "province", "reference_start", "reference_end",
                                 ("prevalence_pct",), (0.0, 100.0)),
    "psa_subsistence_incidence": Spec("outcome", ("province_code", "reference_year", "subsistence_incidence_pct",
                                                  "cv_pct", "publication_date"), "province_code", "province",
                                      "reference_start", "reference_end", ("subsistence_incidence_pct",),
                                      (0.0, 100.0), (2021, 2023)),   # E27: PSA full-year rounds in the window (O4); 2026 has no release
    "sws_area_series": Spec("outcome", ("quarter", "area", "hunger_pct", "n_respondents", "fieldwork_end",
                                        "publication_date"), "area", "area", "fieldwork_end", "fieldwork_end",
                            ("hunger_pct",), (0.0, 100.0)),
    "dromic_affected": Spec("signal", ("province_code", "event_name", "event_start", "report_date",
                                       "affected_families"), "province_code", "province", "event_start",
                            "event_start", ("affected_families",), (0.0, 1e8)),
}
SWS_AREAS = {"NCR", "BALANCE_LUZON", "VISAYAS", "MINDANAO", "CALABARZON_FROM_MICRODATA"}


def _periods(df: pd.DataFrame, kind: str):
    """Reference period start/end per row."""
    if "reference_year" in df.columns and kind in ("cbms_fies_lgu", "psa_subsistence_incidence"):
        y = df["reference_year"].astype(int)
        return pd.to_datetime(y.astype(str) + "-01-01"), pd.to_datetime(y.astype(str) + "-12-31")
    if kind == "sws_area_series":
        e = pd.to_datetime(df["fieldwork_end"], errors="coerce")
        return e, e
    if kind == "dromic_affected":
        s = pd.to_datetime(df["event_start"], errors="coerce")
        return s, s
    return (pd.to_datetime(df["reference_start"], errors="coerce"),
            pd.to_datetime(df["reference_end"], errors="coerce"))


def validate(kind: str, raw: bytes, *, authorized_sha256: str, authorized_until: str,
             known_lgu_codes: set[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Validate one researcher-supplied CSV. Returns (table, report) or raises OutcomeRefused."""
    if kind not in SPECS:
        raise OutcomeRefused(f"unknown source kind {kind}")
    spec = SPECS[kind]
    if len(authorized_sha256 or "") != 64:
        raise OutcomeRefused("the researcher's full 64-character SHA-256 is required")
    got = hashlib.sha256(raw).hexdigest()
    if got != authorized_sha256.lower():
        raise OutcomeRefused("file bytes do not match the authorized SHA-256")
    df = pd.read_csv(io.BytesIO(raw), dtype=str)
    miss = [c for c in spec.required if c not in df.columns]
    if miss:
        raise OutcomeRefused(f"missing columns {miss}")
    if df.empty:
        raise OutcomeRefused("empty file")
    rep = {"kind": kind, "role": spec.kind, "rows": int(len(df)), "sha256": got}
    # geography
    if spec.geo_level == "province":
        bad = sorted(set(df[spec.geo_col]) - set(CALABARZON_PROVINCES))
        if bad:
            raise OutcomeRefused(f"non-CALABARZON or unknown province codes {bad}")
    elif spec.geo_level == "lgu":
        codes = df[spec.geo_col].str.replace(r"\D", "", regex=True)
        if not codes.str[:4].isin(LGU_PREFIX).all():
            raise OutcomeRefused("LGU codes outside CALABARZON")
        if known_lgu_codes is not None and not set(codes) <= known_lgu_codes:
            raise OutcomeRefused(f"LGU codes not in the 142-LGU list: {sorted(set(codes) - known_lgu_codes)[:5]}")
        rep["lgus"] = int(codes.nunique())
    elif spec.geo_level == "area":
        bad = sorted(set(df[spec.geo_col]) - SWS_AREAS)
        if bad:
            raise OutcomeRefused(f"unknown SWS areas {bad}")
    # window and authorization limit: refuse, never filter
    start, end = _periods(df, kind)
    if start.isna().any() or end.isna().any():
        raise OutcomeRefused("unparseable reference period")
    if (start < WINDOW_START).any():
        raise OutcomeRefused("file holds rows before 2021 (study window): refused, not filtered")
    if (end > pd.Timestamp(authorized_until)).any():
        raise OutcomeRefused(f"file holds rows after the authorized limit {authorized_until}: refused, not filtered")
    if spec.allowed_years and "reference_year" in df.columns:
        if not df["reference_year"].astype(int).isin(spec.allowed_years).all():
            raise OutcomeRefused(f"reference years must be in {spec.allowed_years}")
    # publication timing
    pubcol = "report_date" if kind == "dromic_affected" else "publication_date"
    pub = pd.to_datetime(df[pubcol], errors="coerce")
    if pub.isna().any():
        raise OutcomeRefused("every row needs a publication date (or documented upper bound)")
    if (pub < end).any():
        raise OutcomeRefused("a publication date precedes the end of its reference period")
    # values
    for c in spec.value_cols:
        v = pd.to_numeric(df[c], errors="coerce")
        if v.isna().any() or (v < spec.value_range[0]).any() or (v > spec.value_range[1]).any():
            raise OutcomeRefused(f"{c}: missing or out-of-range values (never filled)")
    key = [spec.geo_col] + [c for c in ("reference_year", "quarter", "survey", "event_name") if c in df.columns]
    if df.duplicated(key).any():
        raise OutcomeRefused(f"duplicate keys on {key}")
    rep.update({"reference_min": str(start.min().date()), "reference_max": str(end.max().date()),
                "published_min": str(pub.min().date()), "published_max": str(pub.max().date())})
    return df, rep
