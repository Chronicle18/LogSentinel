"""Log file collector — reads log files, detects sourcetype, posts batches to /ingest."""

import os
import re

import httpx
import structlog

log = structlog.get_logger()

SOURCETYPE_PATTERNS = {
    "syslog_auth": re.compile(r"syslog_auth", re.IGNORECASE),
    "syslog_kern": re.compile(r"syslog_kern", re.IGNORECASE),
    "winevt_security": re.compile(r"winevt_security", re.IGNORECASE),
    "winevt_system": re.compile(r"winevt_system", re.IGNORECASE),
    "winevt_application": re.compile(r"winevt_application", re.IGNORECASE),
}

BATCH_SIZE = 5000


def detect_sourcetype(filename: str) -> str:
    """Detect sourcetype from filename convention."""
    basename = os.path.basename(filename).lower()
    for sourcetype, pattern in SOURCETYPE_PATTERNS.items():
        if pattern.search(basename):
            return sourcetype
    return None


def read_lines(filepath: str) -> list[str]:
    """Read all non-empty lines from a log file."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return [line.rstrip("\n") for line in f if line.strip()]


async def ingest_file(filepath: str, api_url: str = "http://localhost:8000") -> list[str]:
    """Read a log file, detect sourcetype, and POST batches to /ingest."""
    sourcetype = detect_sourcetype(filepath)
    if not sourcetype:
        log.error("sourcetype_detection_failed", filepath=filepath)
        return []

    lines = read_lines(filepath)
    if not lines:
        log.warning("empty_file", filepath=filepath)
        return []

    log.info("file_read", filepath=filepath, sourcetype=sourcetype, total_lines=len(lines))

    job_ids = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i in range(0, len(lines), BATCH_SIZE):
            batch = lines[i : i + BATCH_SIZE]
            response = await client.post(
                f"{api_url}/ingest",
                json={"sourcetype": sourcetype, "lines": batch},
            )
            response.raise_for_status()
            data = response.json()
            job_ids.append(data["job_id"])
            log.info("batch_submitted",
                     filepath=filepath,
                     batch_num=i // BATCH_SIZE + 1,
                     batch_size=len(batch),
                     job_id=data["job_id"])

    return job_ids


async def ingest_directory(data_dir: str = "data",
                           api_url: str = "http://localhost:8000") -> dict:
    """Ingest all log files from a directory."""
    results = {}
    if not os.path.exists(data_dir):
        log.warning("data_dir_not_found", dir=data_dir)
        return results

    for filename in sorted(os.listdir(data_dir)):
        filepath = os.path.join(data_dir, filename)
        if not os.path.isfile(filepath):
            continue
        if not (filename.endswith(".log") or filename.endswith(".xml")):
            continue

        job_ids = await ingest_file(filepath, api_url)
        results[filename] = job_ids

    return results


if __name__ == "__main__":
    import asyncio
    import sys

    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "data"

    results = asyncio.run(ingest_directory(data_dir, api_url))
    for filename, job_ids in results.items():
        print(f"{filename}: {len(job_ids)} job(s) - {job_ids}")
