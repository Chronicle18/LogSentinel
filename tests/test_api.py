"""Integration tests for all Phase 2 API endpoints.

Tests run against a real PostgreSQL database (per CLAUDE.md Section 7).
Requires: docker-compose up -d postgres
"""

import asyncio
import os
import time
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.models.base import Base
from api.models.event import Event
from api.models.job import Job

# Use test database URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://logsentinel:logsentinel@localhost:5432/logsentinel",
)

# Override DB URL before importing app
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from api.main import app
from api.db import engine as app_engine


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session(test_session_factory):
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_engine):
    """AsyncClient using the real FastAPI app with ASGI transport."""
    # Patch the app engine to use our test engine
    import api.db
    original_engine = api.db.engine
    original_session_factory = api.db.async_session_factory
    api.db.engine = test_engine
    api.db.async_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
    )

    # Set up config_manager on app.state (normally done in lifespan)
    from configs.loader import ConfigManager
    config_manager = ConfigManager("./configs")
    app.state.config_manager = config_manager

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    api.db.engine = original_engine
    api.db.async_session_factory = original_session_factory


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# POST /ingest
# ---------------------------------------------------------------------------
class TestIngest:
    @pytest.mark.asyncio
    async def test_ingest_valid_batch(self, client):
        resp = await client.post("/ingest", json={
            "sourcetype": "syslog_auth",
            "lines": [
                "Jan 15 08:23:11 host-01 sshd[1234]: Accepted publickey for jdoe from 10.0.0.5",
                "Jan 15 08:23:12 host-01 sshd[1235]: Failed password for root from 10.0.0.6",
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["total_lines"] == 2

    @pytest.mark.asyncio
    async def test_ingest_unknown_sourcetype(self, client):
        resp = await client.post("/ingest", json={
            "sourcetype": "nonexistent_type",
            "lines": ["test line"],
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ingest_empty_lines(self, client):
        resp = await client.post("/ingest", json={
            "sourcetype": "syslog_auth",
            "lines": [],
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ingest_missing_sourcetype(self, client):
        resp = await client.post("/ingest", json={
            "lines": ["test line"],
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /jobs/{id}
# ---------------------------------------------------------------------------
class TestJobs:
    @pytest.mark.asyncio
    async def test_get_job_after_ingest(self, client):
        resp = await client.post("/ingest", json={
            "sourcetype": "syslog_auth",
            "lines": ["Jan 15 08:23:11 host-01 sshd[1234]: Accepted publickey for jdoe from 10.0.0.5"],
        })
        job_id = resp.json()["job_id"]

        await asyncio.sleep(1)

        resp = await client.get(f"/jobs/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        assert data["status"] in ("queued", "processing", "complete")
        assert "progress_pct" in data

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/jobs/{fake_id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /events
# ---------------------------------------------------------------------------
class TestEvents:
    @pytest.mark.asyncio
    async def test_get_events_default(self, client):
        resp = await client.get("/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "events" in data
        assert isinstance(data["events"], list)

    @pytest.mark.asyncio
    async def test_get_events_with_sourcetype_filter(self, client):
        resp = await client.get("/events", params={"sourcetype": "syslog_auth"})
        assert resp.status_code == 200
        for event in resp.json()["events"]:
            assert event["sourcetype"] == "syslog_auth"

    @pytest.mark.asyncio
    async def test_get_events_with_severity_filter(self, client):
        resp = await client.get("/events", params={"severity": "medium"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_events_pagination(self, client):
        resp = await client.get("/events", params={"limit": 5, "offset": 0})
        assert resp.status_code == 200
        assert len(resp.json()["events"]) <= 5

    @pytest.mark.asyncio
    async def test_get_events_limit_exceeded(self, client):
        resp = await client.get("/events", params={"limit": 1001})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_events_time_filter(self, client):
        resp = await client.get("/events", params={
            "from": "2020-01-01T00:00:00Z",
            "to": "2030-01-01T00:00:00Z",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /events/stats
# ---------------------------------------------------------------------------
class TestStats:
    @pytest.mark.asyncio
    async def test_get_stats(self, client):
        resp = await client.get("/events/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert "total_parse_errors" in data
        assert "error_rate" in data
        assert "by_sourcetype" in data
        assert "by_severity" in data
        assert "by_mitre_tactic" in data


# ---------------------------------------------------------------------------
# POST /validate
# ---------------------------------------------------------------------------
class TestValidate:
    @pytest.mark.asyncio
    async def test_validate_valid_line(self, client):
        resp = await client.post("/validate", json={
            "sourcetype": "syslog_auth",
            "line": "Jan 15 08:23:11 host-01 sshd[1234]: Accepted publickey for jdoe from 10.0.0.5",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["verdict"] == "pass"
        assert "_time" in data["populated_fields"]
        assert "src" in data["populated_fields"]

    @pytest.mark.asyncio
    async def test_validate_malformed_line(self, client):
        resp = await client.post("/validate", json={
            "sourcetype": "syslog_auth",
            "line": "garbage data here",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["verdict"] == "fail"

    @pytest.mark.asyncio
    async def test_validate_unknown_sourcetype(self, client):
        resp = await client.post("/validate", json={
            "sourcetype": "nonexistent",
            "line": "test",
        })
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /sourcetypes
# ---------------------------------------------------------------------------
class TestSourcetypes:
    @pytest.mark.asyncio
    async def test_list_sourcetypes(self, client):
        resp = await client.get("/sourcetypes")
        assert resp.status_code == 200
        data = resp.json()
        assert "sourcetypes" in data
        names = [s["sourcetype"] for s in data["sourcetypes"]]
        assert "syslog_auth" in names
        assert "syslog_kern" in names
        assert "winevt_security" in names
        assert "winevt_system" in names
        assert "winevt_application" in names

    @pytest.mark.asyncio
    async def test_sourcetypes_have_rule_counts(self, client):
        resp = await client.get("/sourcetypes")
        for st in resp.json()["sourcetypes"]:
            assert st["rule_count"] > 0


# ---------------------------------------------------------------------------
# Full pipeline test: ingest batch, wait, query events
# ---------------------------------------------------------------------------
class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_ingest_and_query(self, client):
        lines = [
            "Jan 15 08:23:11 host-01 sshd[1234]: Accepted publickey for jdoe from 10.0.0.5",
            "Jan 15 08:23:12 host-01 sshd[1235]: Failed password for root from 10.0.0.6",
            "Jan 15 08:23:13 host-01 sshd[1236]: Malformed garbage line",
        ]
        resp = await client.post("/ingest", json={
            "sourcetype": "syslog_auth",
            "lines": lines,
        })
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        for _ in range(20):
            await asyncio.sleep(0.5)
            job_resp = await client.get(f"/jobs/{job_id}")
            if job_resp.json()["status"] == "complete":
                break

        job_data = job_resp.json()
        assert job_data["status"] == "complete"
        assert job_data["processed_lines"] == 3
        assert job_data["error_count"] >= 1

        events_resp = await client.get("/events", params={
            "sourcetype": "syslog_auth",
        })
        assert events_resp.status_code == 200
        assert events_resp.json()["total"] > 0


# ---------------------------------------------------------------------------
# Query latency test
# ---------------------------------------------------------------------------
class TestPerformance:
    @pytest.mark.asyncio
    async def test_events_query_latency(self, client):
        """GET /events with filters must respond in < 100ms."""
        start = time.monotonic()
        resp = await client.get("/events", params={
            "sourcetype": "syslog_auth",
            "severity": "medium",
            "limit": 100,
        })
        elapsed_ms = (time.monotonic() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < 100, f"Query took {elapsed_ms:.1f}ms, expected < 100ms"
