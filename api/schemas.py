"""Pydantic v2 request/response schemas for all API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# --- Ingest ---

class IngestRequest(BaseModel):
    sourcetype: str = Field(..., min_length=1, max_length=64)
    lines: List[str] = Field(..., min_length=1)


class IngestResponse(BaseModel):
    job_id: UUID
    status: str
    total_lines: int


# --- Jobs ---

class JobResponse(BaseModel):
    job_id: UUID
    status: str
    sourcetype: Optional[str] = None
    total_lines: int
    processed_lines: int
    error_count: int
    progress_pct: float
    created_at: datetime
    updated_at: datetime


# --- Events ---

class EventResponse(BaseModel):
    id: int
    time: datetime = Field(alias="_time")
    sourcetype: str
    src: Optional[str] = None
    dest: Optional[str] = None
    user: Optional[str] = None
    action: Optional[str] = None
    severity: Optional[str] = None
    mitre_tactic: Optional[str] = None
    parse_error: bool = False
    raw: Optional[str] = None
    job_id: Optional[UUID] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class EventListResponse(BaseModel):
    total: int
    events: List[EventResponse]


# --- Stats ---

class SourcetypeCount(BaseModel):
    sourcetype: str
    count: int


class SeverityCount(BaseModel):
    severity: str
    count: int


class MitreTacticCount(BaseModel):
    tactic: str
    count: int


class StatsResponse(BaseModel):
    total_events: int
    total_parse_errors: int
    error_rate: float
    by_sourcetype: List[SourcetypeCount]
    by_severity: List[SeverityCount]
    by_mitre_tactic: List[MitreTacticCount]


# --- Validate ---

class ValidateRequest(BaseModel):
    sourcetype: str = Field(..., min_length=1, max_length=64)
    line: str = Field(..., min_length=1)


class ValidateResponse(BaseModel):
    populated_fields: List[str]
    missing_fields: List[str]
    verdict: str = Field(description="pass or fail")
    event: Dict[str, Any]


# --- Sourcetypes ---

class SourcetypeInfo(BaseModel):
    sourcetype: str
    rule_count: int
    config_path: Optional[str] = None


class SourcetypeListResponse(BaseModel):
    sourcetypes: List[SourcetypeInfo]


# --- Error ---

class ErrorResponse(BaseModel):
    detail: str
    code: str
