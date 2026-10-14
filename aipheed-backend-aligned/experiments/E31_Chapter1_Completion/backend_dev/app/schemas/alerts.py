from pydantic import BaseModel
from datetime import datetime


class AlertRecord(BaseModel):
    """Represents one early warning alert."""
    id: int
    quarter: str
    province_code: str
    threshold_exceeded: bool
    confirmed: bool
    created_at: datetime | None = None
    # E31: why the candidate exists and what it is (and is not)
    dismissed: bool = False
    alert_reason: str | None = None
    prev_risk_probability: float | None = None
    risk_delta: float | None = None
    statement: str = ("Model-generated early-warning candidate for review by DA Region IV-A. Not an official "
                      "food-insecurity classification and not a confirmed emergency.")

    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    """Response for GET /v1/alerts/active"""
    data: list[AlertRecord]
    total: int

    model_config = {"from_attributes": True}