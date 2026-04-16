"""POST /ingest — accept log batch, create job, kick off background processing."""

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import async_session_factory, get_db
from api.models.event import Event
from api.models.job import Job
from api.schemas import IngestRequest, IngestResponse
from configs.loader import ConfigManager
from parser.extractor import FieldExtractor
from parser.cim_mapper import CIMMapper
from parser.mitre_mapper import MitreMapper

log = structlog.get_logger()

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

MAX_RETRY = 3
BATCH_SIZE = 500


async def process_batch(job_id: uuid.UUID, sourcetype: str, lines: list[str],
                        config_manager: ConfigManager):
    """Background task: extract, normalize, and insert events for a batch."""
    async with async_session_factory() as db:
        try:
            stmt = select(Job).where(Job.job_id == job_id)
            result = await db.execute(stmt)
            job = result.scalar_one()
            job.status = "processing"
            job.updated_at = datetime.now(timezone.utc)
            await db.commit()

            config = config_manager.get_config(sourcetype)
            if not config:
                job.status = "failed"
                job.updated_at = datetime.now(timezone.utc)
                await db.commit()
                log.error("sourcetype_not_found", job_id=str(job_id), sourcetype=sourcetype)
                return

            extractor = FieldExtractor(config)
            cim_mapper = CIMMapper(config)
            mitre_mapper = MitreMapper()

            processed = 0
            errors = 0
            batch_events = []

            for line in lines:
                extracted = extractor.extract(line)
                mapped = cim_mapper.map_event(extracted, job_id=str(job_id))
                tactic = mitre_mapper.map_tactics(mapped)
                if tactic:
                    mapped["mitre_tactic"] = tactic

                event = Event(
                    _time=_parse_time(mapped.get("_time")),
                    sourcetype=mapped.get("sourcetype", sourcetype),
                    src=mapped.get("src"),
                    dest=mapped.get("dest"),
                    user=mapped.get("user"),
                    action=mapped.get("action"),
                    severity=mapped.get("severity"),
                    mitre_tactic=mapped.get("mitre_tactic"),
                    bytes_out=mapped.get("bytes_out") if isinstance(mapped.get("bytes_out"), int) else None,
                    dest_port=mapped.get("dest_port") if isinstance(mapped.get("dest_port"), int) else None,
                    parse_error=mapped.get("parse_error", False),
                    raw=mapped.get("raw"),
                    job_id=job_id,
                )
                batch_events.append(event)
                processed += 1
                if mapped.get("parse_error"):
                    errors += 1

                if len(batch_events) >= BATCH_SIZE:
                    await _flush_batch(db, batch_events, job, processed, errors)
                    batch_events = []

            if batch_events:
                await _flush_batch(db, batch_events, job, processed, errors)

            job.status = "complete"
            job.processed_lines = processed
            job.error_count = errors
            job.updated_at = datetime.now(timezone.utc)
            await db.commit()

            log.info("ingestion_complete", job_id=str(job_id), sourcetype=sourcetype,
                     total=len(lines), processed=processed, errors=errors)

        except Exception as e:
            log.error("ingestion_failed", job_id=str(job_id), error=str(e))
            try:
                stmt = select(Job).where(Job.job_id == job_id)
                result = await db.execute(stmt)
                job = result.scalar_one_or_none()
                if job:
                    job.status = "failed"
                    job.updated_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass


async def _flush_batch(db: AsyncSession, events: list[Event], job: Job,
                       processed: int, errors: int):
    """Flush a batch of events to DB with retry logic."""
    for attempt in range(MAX_RETRY):
        try:
            db.add_all(events)
            job.processed_lines = processed
            job.error_count = errors
            job.updated_at = datetime.now(timezone.utc)
            await db.commit()
            return
        except Exception as e:
            await db.rollback()
            if attempt < MAX_RETRY - 1:
                delay = 0.5 * (2 ** attempt)
                log.warning("batch_insert_retry", attempt=attempt + 1, error=str(e), delay=delay)
                await asyncio.sleep(delay)
            else:
                log.error("batch_insert_failed", attempt=attempt + 1, error=str(e))
                raise


def _parse_time(time_str) -> datetime:
    """Parse ISO 8601 timestamp or return current UTC time."""
    if not time_str:
        return datetime.now(timezone.utc)
    try:
        if isinstance(time_str, str):
            cleaned = time_str.rstrip("Z")
            return datetime.fromisoformat(cleaned).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        pass
    return datetime.now(timezone.utc)


@router.post("/ingest", response_model=IngestResponse)
@limiter.limit("10/minute")
async def ingest(
    payload: IngestRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    config_manager: ConfigManager = request.app.state.config_manager
    config = config_manager.get_config(payload.sourcetype)
    if not config:
        raise HTTPException(
            status_code=422,
            detail={"detail": f"Sourcetype '{payload.sourcetype}' not found",
                    "code": "SOURCETYPE_NOT_REGISTERED"},
        )

    job_id = uuid.uuid4()
    job = Job(
        job_id=job_id,
        status="queued",
        sourcetype=payload.sourcetype,
        total_lines=len(payload.lines),
    )
    db.add(job)
    await db.commit()

    background_tasks.add_task(
        process_batch, job_id, payload.sourcetype, payload.lines, config_manager
    )

    log.info("ingestion_queued", job_id=str(job_id), sourcetype=payload.sourcetype,
             total_lines=len(payload.lines))

    return IngestResponse(
        job_id=job_id,
        status="queued",
        total_lines=len(payload.lines),
    )
