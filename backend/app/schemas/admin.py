"""
app/schemas/admin.py
---------------------
Auth, review pipeline, audit and feedback contracts.

camelCase and slug-keyed like app/schemas/public.py, since the same frontend
consumes both.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

# Input caps. Every request body here can reach the database (the feedback
# form without signing in), so nothing is unbounded.
NAME_MAX = 200          # names, emails and other short identifying fields
FREE_TEXT_MAX = 2000    # feedback comments, rejection notes
PASSWORD_MAX = 1024     # far beyond any real passphrase; stops multi-MB hashing input

ShortText = Annotated[str, Field(max_length=NAME_MAX)]
FreeText = Annotated[str, Field(max_length=FREE_TEXT_MAX)]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: Annotated[EmailStr, Field(max_length=NAME_MAX)]
    # A passphrase is a good password, so the cap is generous -- it only
    # stops a multi-megabyte body being fed to the hasher.
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    token: str
    expiresIn: int
    expiresAt: datetime
    user: UserOut


class LogoutResponse(BaseModel):
    revoked: bool
    message: str


# ---------------------------------------------------------------------------
# Account self-service (ACCT-1)
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    fullName: str = Field(min_length=1, max_length=NAME_MAX)
    email: Annotated[EmailStr, Field(max_length=NAME_MAX)]
    office: str = Field(min_length=1, max_length=NAME_MAX)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class EmailRequest(BaseModel):
    email: Annotated[EmailStr, Field(max_length=NAME_MAX)]


class TokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class MessageResponse(BaseModel):
    message: str


class VerifyEmailResponse(BaseModel):
    status: str
    message: str


class AccountRow(BaseModel):
    id: int
    email: str
    name: str
    office: str | None = None
    status: str
    createdAt: datetime | None = None
    emailVerifiedAt: datetime | None = None
    approvedAt: datetime | None = None
    lastLoginAt: datetime | None = None
    isDemo: bool = False
    isSelf: bool = False


class AccountsResponse(BaseModel):
    """GET /admin/accounts: requests to decide on, and who has access now."""
    pending: list[AccountRow]          # verified, waiting for approval
    active: list[AccountRow]
    pendingCount: int


# ---------------------------------------------------------------------------
# Review pipeline
# ---------------------------------------------------------------------------

class ReviewItem(BaseModel):
    id: str
    provinceId: str
    provinceCode: str
    province: str
    quarter: str
    riskScore: float
    riskLevel: str
    status: str                       # Staged | Approved | Rejected
    rejectionReason: str | None = None
    rejectionNotes: str | None = None
    updatedAt: datetime | None = None
    updatedBy: int | None = None
    updatedByName: str | None = None


class ReviewListResponse(BaseModel):
    quarter: str | None = None
    status: str | None = None
    statuses: list[str]
    rejectionReasons: list[str]
    data: list[ReviewItem]


class RejectRequest(BaseModel):
    # Constrained on purpose: a rejection removes a number the public would
    # otherwise see, so "why" has to outlive the person who clicked it.
    reason: ShortText
    notes: FreeText | None = None


class RejectionRow(BaseModel):
    provinceId: str
    province: str
    quarter: str
    reason: str | None = None
    notes: str | None = None
    # No reviewer id or name: this list is public. Who rejected what is in
    # the admin-only review queue and audit log.
    timestamp: datetime | None = None


class RejectionsResponse(BaseModel):
    """
    Public. The map greys out these province-quarters.

    A rejection is not the same as a missing forecast: this list is generated
    output an admin withheld, whereas an absent quarter was never produced.
    """
    quarter: str | None = None
    data: list[RejectionRow]


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class AuditRow(BaseModel):
    id: int
    actorEmail: str
    actorId: int | None = None
    action: str
    subjectType: str
    subjectId: str | None = None
    provinceId: str | None = None
    quarter: str | None = None
    reason: str | None = None
    notes: str | None = None
    timestamp: datetime | None = None


class AuditResponse(BaseModel):
    data: list[AuditRow]
    page: int
    pageSize: int
    total: int


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

class Demographics(BaseModel):
    """As stored and returned. Uncapped: a response must not fail on an old row."""
    fullName: str | None = None
    email: str | None = None
    agency: str | None = None
    designation: str | None = None
    age: str | None = None
    sex: str | None = None
    clientType: str | None = None
    province: str | None = None
    municipality: str | None = None


class DemographicsIn(BaseModel):
    """As submitted. Capped."""
    fullName: ShortText | None = None
    email: ShortText | None = None
    agency: ShortText | None = None
    designation: ShortText | None = None
    age: ShortText | None = None
    sex: ShortText | None = None
    clientType: ShortText | None = None
    province: ShortText | None = None
    municipality: ShortText | None = None


class FeedbackSubmit(BaseModel):
    demographics: DemographicsIn = Field(default_factory=DemographicsIn)
    # qIndex "0".."9" -> 1..5. Validated and scored server-side; a
    # client-supplied total is never stored.
    answers: dict[str, int]
    liked: FreeText | None = None
    improvements: FreeText | None = None


class FeedbackCreated(BaseModel):
    id: int
    date: datetime
    score: float
    susVersion: str


class FeedbackRow(BaseModel):
    id: int
    date: datetime
    score: float
    susVersion: str
    answers: dict[str, int]
    demographics: Demographics
    liked: str | None = None
    improvements: str | None = None


class FeedbackSummary(BaseModel):
    count: int
    meanScore: float | None = None
    medianScore: float | None = None
    byClientType: dict[str, int]
    susVersion: str


class FeedbackListResponse(BaseModel):
    summary: FeedbackSummary
    questions: list[str]
    data: list[FeedbackRow]
    page: int
    pageSize: int
    total: int
