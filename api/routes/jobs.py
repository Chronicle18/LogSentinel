"""GET /jobs and GET /jobs/{id} — list recent jobs and return job status/progress."""

from typing import List
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_db
from api.models.job import Job
from api.schemas import JobResponse

log = structlog.get_logger()

router = APIRouter()


def _to_response(job: Job) -> JobResponse:
    total = job.total_lines or 0
    processed = job.processed_lines or 0
    progress = round((processed / total) * 100, 1) if total > 0 else 0.0
    return JobResponse(
        job_id=job.job_id,
        status=job.status,
        sourcetype=job.sourcetype,
        total_lines=total,
        processed_lines=processed,
        error_count=job.error_count or 0,
        progress_pct=progress,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return most recent jobs ordered by created_at DESC. Used by dashboard JobTracker."""
    stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return [_to_response(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Job).where(Job.job_id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=404,
            detail={"detail": f"Job '{job_id}' not found", "code": "JOB_NOT_FOUND"},
        )

    return _to_response(job)
