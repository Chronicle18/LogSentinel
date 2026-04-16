"""GET /events and GET /events/stats — query and aggregate normalized events."""

from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.models.event import Event
from api.schemas import (
    EventListResponse, EventResponse,
    MitreTacticCount, SeverityCount, SourcetypeCount, StatsResponse,
)

log = structlog.get_logger()

router = APIRouter()

MAX_LIMIT = 1000
DEFAULT_LIMIT = 100


@router.get("/events", response_model=EventListResponse)
async def get_events(
    sourcetype: Optional[str] = None,
    severity: Optional[str] = None,
    src: Optional[str] = None,
    action: Optional[str] = None,
    from_time: Optional[datetime] = Query(None, alias="from"),
    to_time: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    if limit > MAX_LIMIT:
        raise HTTPException(
            status_code=422,
            detail={"detail": f"limit cannot exceed {MAX_LIMIT}", "code": "LIMIT_EXCEEDED"},
        )

    base_filter = []

    if from_time:
        base_filter.append(Event._time >= from_time)
    else:
        base_filter.append(
            Event._time >= datetime(2020, 1, 1, tzinfo=timezone.utc)
        )

    if to_time:
        base_filter.append(Event._time <= to_time)
    if sourcetype:
        base_filter.append(Event.sourcetype == sourcetype)
    if severity:
        base_filter.append(Event.severity == severity)
    if src:
        base_filter.append(Event.src == src)
    if action:
        base_filter.append(Event.action == action)

    count_stmt = select(func.count(Event.id)).where(*base_filter)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    query_stmt = (
        select(Event)
        .where(*base_filter)
        .order_by(Event._time.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query_stmt)
    events = result.scalars().all()

    return EventListResponse(
        total=total,
        events=[
            EventResponse(
                id=e.id,
                _time=e._time,
                sourcetype=e.sourcetype,
                src=e.src,
                dest=e.dest,
                user=e.user,
                action=e.action,
                severity=e.severity,
                mitre_tactic=e.mitre_tactic,
                parse_error=e.parse_error or False,
                raw=e.raw,
                job_id=e.job_id,
            )
            for e in events
        ],
    )


@router.get("/events/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_result = await db.execute(select(func.count(Event.id)))
    total_events = total_result.scalar() or 0

    error_result = await db.execute(
        select(func.count(Event.id)).where(Event.parse_error == True)  # noqa: E712
    )
    total_errors = error_result.scalar() or 0

    error_rate = round((total_errors / total_events) * 100, 2) if total_events > 0 else 0.0

    st_result = await db.execute(
        select(Event.sourcetype, func.count(Event.id))
        .group_by(Event.sourcetype)
        .order_by(func.count(Event.id).desc())
    )
    by_sourcetype = [
        SourcetypeCount(sourcetype=row[0], count=row[1])
        for row in st_result.all()
    ]

    sev_result = await db.execute(
        select(Event.severity, func.count(Event.id))
        .where(Event.severity.isnot(None))
        .group_by(Event.severity)
        .order_by(func.count(Event.id).desc())
    )
    by_severity = [
        SeverityCount(severity=row[0], count=row[1])
        for row in sev_result.all()
    ]

    mitre_result = await db.execute(
        select(Event.mitre_tactic, func.count(Event.id))
        .where(Event.mitre_tactic.isnot(None))
        .group_by(Event.mitre_tactic)
        .order_by(func.count(Event.id).desc())
    )
    by_mitre = []
    for row in mitre_result.all():
        tactics = row[0].split(",") if row[0] else []
        for tactic in tactics:
            tactic = tactic.strip()
            if tactic:
                existing = next((t for t in by_mitre if t.tactic == tactic), None)
                if existing:
                    existing.count += row[1]
                else:
                    by_mitre.append(MitreTacticCount(tactic=tactic, count=row[1]))

    return StatsResponse(
        total_events=total_events,
        total_parse_errors=total_errors,
        error_rate=error_rate,
        by_sourcetype=by_sourcetype,
        by_severity=by_severity,
        by_mitre_tactic=by_mitre,
    )


@router.get("/events/timeseries")
async def get_timeseries(
    bucket_minutes: int = Query(5, ge=1, le=60),
    window_hours: int = Query(24, ge=1, le=168),
    sourcetype: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Return event counts bucketed by time window.

    Used by the dashboard LogVolumeChart. Buckets events into fixed-size
    intervals (default 5 minutes) over the requested lookback window
    (default 24 hours) and returns parallel series for total events and
    parse errors. Optionally filtered by sourcetype.
    """
    bucket_seconds = bucket_minutes * 60
    # SQL: bucket = to_timestamp(floor(extract(epoch from _time) / bucket_seconds) * bucket_seconds)
    bucket_expr = func.to_timestamp(
        (func.floor(func.extract("epoch", Event._time) / bucket_seconds))
        * bucket_seconds
    ).label("bucket")

    filters = [
        Event._time >= text(f"now() - interval '{int(window_hours)} hours'"),
    ]
    if sourcetype:
        filters.append(Event.sourcetype == sourcetype)

    stmt = (
        select(
            bucket_expr,
            func.count(Event.id).label("total"),
            func.sum(case((Event.parse_error.is_(True), 1), else_=0)).label(
                "errors"
            ),
        )
        .where(*filters)
        .group_by(bucket_expr)
        .order_by(bucket_expr)
    )

    result = await db.execute(stmt)
    rows = result.all()
    return {
        "bucket_minutes": bucket_minutes,
        "window_hours": window_hours,
        "sourcetype": sourcetype,
        "points": [
            {
                "t": row[0].isoformat() if row[0] else None,
                "total": int(row[1] or 0),
                "errors": int(row[2] or 0),
            }
            for row in rows
        ],
    }
