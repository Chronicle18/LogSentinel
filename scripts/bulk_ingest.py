"""Bulk ingest all simulated data files directly into PostgreSQL.

Runs the full pipeline: extractor -> cim_mapper -> mitre_mapper -> DB insert.
Bypasses the HTTP API for speed; uses the same processing logic as POST /ingest.
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.models.base import Base
from api.models.event import Event
from api.models.job import Job
from configs.loader import ConfigManager
from ingestion.collector import detect_sourcetype, read_lines
from parser.extractor import FieldExtractor
from parser.cim_mapper import CIMMapper
from parser.mitre_mapper import MitreMapper

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://logsentinel:logsentinel@localhost:5432/logsentinel",
)
DATA_DIR = os.getenv("DATA_DIR", "./data")
CONFIG_DIR = os.getenv("CONFIG_DIR", "./configs")
BATCH_SIZE = 1000


def parse_time(time_str) -> datetime:
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


async def ingest_file(
    filepath: str,
    sourcetype: str,
    config_manager: ConfigManager,
    session_factory: async_sessionmaker,
) -> dict:
    """Process a single file through the full pipeline and insert into DB."""
    config = config_manager.get_config(sourcetype)
    if not config:
        print(f"  ERROR: No config for sourcetype '{sourcetype}'")
        return {"processed": 0, "errors": 0}

    lines = read_lines(filepath)
    if not lines:
        print(f"  WARNING: Empty file {filepath}")
        return {"processed": 0, "errors": 0}

    job_id = uuid.uuid4()
    extractor = FieldExtractor(config)
    cim_mapper = CIMMapper(config)
    mitre_mapper = MitreMapper()

    processed = 0
    errors = 0

    async with session_factory() as db:
        # Create job record
        job = Job(
            job_id=job_id,
            status="processing",
            sourcetype=sourcetype,
            total_lines=len(lines),
        )
        db.add(job)
        await db.commit()

        batch_events = []
        for line in lines:
            extracted = extractor.extract(line)
            mapped = cim_mapper.map_event(extracted, job_id=str(job_id))
            tactic = mitre_mapper.map_tactics(mapped)
            if tactic:
                mapped["mitre_tactic"] = tactic

            event = Event(
                _time=parse_time(mapped.get("_time")),
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
                db.add_all(batch_events)
                await db.commit()
                batch_events = []

        if batch_events:
            db.add_all(batch_events)
            await db.commit()

        # Mark job complete
        job.status = "complete"
        job.processed_lines = processed
        job.error_count = errors
        job.updated_at = datetime.now(timezone.utc)
        await db.commit()

    return {"processed": processed, "errors": errors, "job_id": str(job_id)}


async def main():
    print(f"Connecting to: {DATABASE_URL}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Config directory: {CONFIG_DIR}")
    print()

    engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    config_manager = ConfigManager(CONFIG_DIR)

    total_processed = 0
    total_errors = 0

    start_time = datetime.now()

    for filename in sorted(os.listdir(DATA_DIR)):
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        if not (filename.endswith(".log") or filename.endswith(".xml")):
            continue

        sourcetype = detect_sourcetype(filepath)
        if not sourcetype:
            print(f"  SKIP: Cannot detect sourcetype for {filename}")
            continue

        line_count = sum(1 for line in open(filepath) if line.strip())
        print(f"Processing {filename} ({sourcetype}) — {line_count} lines...")

        result = await ingest_file(filepath, sourcetype, config_manager, session_factory)
        total_processed += result["processed"]
        total_errors += result["errors"]
        print(f"  Done: {result['processed']} processed, {result['errors']} errors, job_id={result.get('job_id', 'N/A')}")

    elapsed = (datetime.now() - start_time).total_seconds()
    error_rate = (total_errors / total_processed * 100) if total_processed > 0 else 0

    print()
    print("=" * 60)
    print(f"INGESTION COMPLETE")
    print(f"  Total processed: {total_processed:,}")
    print(f"  Total errors:    {total_errors:,}")
    print(f"  Error rate:      {error_rate:.2f}%")
    print(f"  Elapsed time:    {elapsed:.1f}s")
    print(f"  Throughput:      {total_processed / elapsed:,.0f} lines/sec")
    print("=" * 60)

    # Verify in DB
    print()
    print("Verifying in database...")
    async with session_factory() as db:
        total_result = await db.execute(select(func.count(Event.id)))
        db_total = total_result.scalar() or 0

        error_result = await db.execute(
            select(func.count(Event.id)).where(Event.parse_error == True)
        )
        db_errors = error_result.scalar() or 0

        db_error_rate = (db_errors / db_total * 100) if db_total > 0 else 0

        st_result = await db.execute(
            select(Event.sourcetype, func.count(Event.id))
            .group_by(Event.sourcetype)
            .order_by(func.count(Event.id).desc())
        )

        mitre_result = await db.execute(
            select(Event.mitre_tactic, func.count(Event.id))
            .where(Event.mitre_tactic.isnot(None))
            .group_by(Event.mitre_tactic)
        )

    print(f"  SELECT COUNT(*) FROM events = {db_total:,}")
    print(f"  Parse errors in DB:            {db_errors:,}")
    print(f"  Error rate from DB:            {db_error_rate:.2f}%")
    print()
    print("  By sourcetype:")
    for row in st_result.all():
        print(f"    {row[0]}: {row[1]:,}")
    print()
    print("  MITRE tactics detected:")
    for row in mitre_result.all():
        print(f"    {row[0]}: {row[1]:,}")

    print()
    # Final pass/fail
    passed = True
    if db_total < 50000:
        print(f"  FAIL: Total events {db_total:,} < 50,000")
        passed = False
    else:
        print(f"  PASS: Total events {db_total:,} >= 50,000")

    if db_error_rate >= 5.0:
        print(f"  FAIL: Error rate {db_error_rate:.2f}% >= 5%")
        passed = False
    else:
        print(f"  PASS: Error rate {db_error_rate:.2f}% < 5%")

    print()
    if passed:
        print("ALL VALIDATION CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")

    await engine.dispose()
    return 0 if passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
