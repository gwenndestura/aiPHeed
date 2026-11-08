"""
Status vocabularies used by every forecasting output. One value per concept; never free text.

EvidenceStatus   what a number is, relative to an independent measurement of food insecurity
DataState        why an input value is or is not present at an issue date (never collapsed into "missing")
ReliabilityStatus whether a lead has passed the frozen N1-N7 rules
"""
from __future__ import annotations

from enum import Enum


class EvidenceStatus(str, Enum):
    VALIDATED = "VALIDATED"                                    # passed the frozen rules on unseen measurements
    BROADER_AREA_REFERENCE = "BROADER_AREA_REFERENCE"          # measured/forecast for an SWS area containing the unit
    PROVINCIAL_ESTIMATE_UNVALIDATED = "PROVINCIAL_ESTIMATE_UNVALIDATED"  # model-based provincial value, no quarterly truth
    AWAITING_GROUND_TRUTH = "AWAITING_GROUND_TRUTH"            # no measurement exists yet (future quarter / no survey)


class DataState(str, Enum):
    OBSERVED = "OBSERVED"                    # published before the issue date and valid
    NOT_YET_PUBLISHED = "NOT_YET_PUBLISHED"  # exists (or will) but was published on/after the issue date
    NOT_OBSERVED = "NOT_OBSERVED"            # the source did not measure this unit/period (e.g. no SWS round)
    UNAVAILABLE = "UNAVAILABLE"              # source not held / not obtainable
    NOT_APPLICABLE = "NOT_APPLICABLE"        # the concept does not apply (e.g. palay in Metro Manila)
    INVALID = "INVALID"                      # present but failed validation


class ReliabilityStatus(str, Enum):
    RELIABLE = "RELIABLE"                    # N1-N7 pass at this lead
    NOT_RELIABLE = "NOT_RELIABLE"            # evaluated and failed at least one rule
    NOT_YET_TESTABLE = "NOT_YET_TESTABLE"    # too few unseen quarters to apply N1


AREAS = ("metro_manila", "balance_luzon", "visayas", "mindanao")
# CALABARZON (Region IV-A) lies in the SWS area "Balance Luzon" (with CAR, I, II, III, MIMAROPA, V).
CALABARZON_SWS_AREA = "balance_luzon"
