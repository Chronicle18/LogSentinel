"""Performance benchmarks backing the resume-grade claims.

Runs a realistic query mix against the live populated database (must have
~50K events ingested first — see scripts/bulk_ingest.py) and records
p50 / p95 / p99 latencies. The < 100ms SLA is asserted on p95, which is
the metric anyone reviewing this project will actually care about.

Mark:  @pytest.mark.performance

Skipped automatically if the DB is empty, so CI on a fresh checkout stays
green. Run with:

    pytest tests/test_performance.py -v -m performance
"""

from __future__ import annotations

import os
import statistics
import time
from typing import Any, Dict, List

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.db import DATABASE_URL
from api.main import app
from api.models.event import Event
from configs.loader import ConfigManager


ITERATIONS = int(os.getenv("PERF_ITERATIONS", "100"))
WARMUP = int(os.getenv("PERF_WARMUP", "5"))
P95_SLA_MS = float(os.getenv("PERF_P95_MS", "100"))

# Each entry is a plausible dashboard query: the EventTable filter controls
# plus stats + timeseries roundtrips. We measure each in isolation so we can
# spot which endpoint is the long tail.
QUERY_MIX: List[Dict[str, Any]] = [
    {"path": "/events", "params": {"limit": 25}},
    {"path": "/events", "params": {"sourcetype": "syslog_auth", "limit": 25}},
    {"path": "/events", "params": {"severity": "high", "limit": 25}},
    {"path": "/events", "params": {"sourcetype": "winevt_security", "severity": "medium", "limit": 25}},
    {"path": "/events", "params": {"limit": 25, "offset": 100}},
    {"path": "/events/stats", "params": {}},
    {"path": "/events/timeseries", "params": {"bucket_minutes": 5, "window_hours": 24}},
    {"path": "/events/timeseries", "params": {"bucket_minutes": 5, "window_hours": 24, "sourcetype": "syslog_auth"}},
]


@pytest.fixture
async def populated_client():
    """Async client pointed at the live app + a fresh engine bound to this test's loop.

    asyncpg connections are pinned to the loop that created them, so each test
    function gets its own engine/session_factory, and we override the app's
    get_db to use it.
    """
    from api.db import get_db

    engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        total = (await session.execute(select(func.count(Event.id)))).scalar_one()
    if total < 1000:
        await engine.dispose()
        pytest.skip(
            f"DB only has {total} events — performance test needs a populated dataset. "
            f"Run `python scripts/bulk_ingest.py` first."
        )

    async def _get_db_override():
        async with factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _get_db_override
    app.state.config_manager = ConfigManager(os.getenv("CONFIG_DIR", "./configs"))

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://perf") as client:
            yield client, total
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


def _percentile(samples: List[float], pct: float) -> float:
    if not samples:
        return 0.0
    k = max(0, min(len(samples) - 1, int(round(pct / 100.0 * (len(samples) - 1)))))
    return sorted(samples)[k]


async def _measure(client: AsyncClient, query: Dict[str, Any], n: int) -> List[float]:
    samples: List[float] = []
    # Warm-up (query planner, pool primer) — samples discarded.
    for _ in range(WARMUP):
        await client.get(query["path"], params=query["params"])
    for _ in range(n):
        t0 = time.perf_counter()
        resp = await client.get(query["path"], params=query["params"])
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert resp.status_code == 200, (query, resp.status_code, resp.text[:200])
        samples.append(elapsed_ms)
    return samples


@pytest.mark.performance
@pytest.mark.asyncio
class TestQueryLatency:
    async def test_per_query_p95_under_sla(self, populated_client):
        """Every query in the mix must meet the p95 latency SLA."""
        client, total = populated_client
        failures: List[str] = []
        report_rows: List[str] = []
        report_rows.append(f"\nDataset size: {total:,} events")
        report_rows.append(
            f"Iterations per query: {ITERATIONS} (warmup {WARMUP})"
        )
        report_rows.append(
            f"{'query':<72}  {'p50':>7}  {'p95':>7}  {'p99':>7}  {'max':>7}"
        )
        report_rows.append("-" * 104)

        for q in QUERY_MIX:
            samples = await _measure(client, q, ITERATIONS)
            p50 = _percentile(samples, 50)
            p95 = _percentile(samples, 95)
            p99 = _percentile(samples, 99)
            mx = max(samples)
            label = f"{q['path']} {q['params']}"[:72]
            report_rows.append(
                f"{label:<72}  {p50:>6.1f}ms  {p95:>6.1f}ms  {p99:>6.1f}ms  {mx:>6.1f}ms"
            )
            if p95 > P95_SLA_MS:
                failures.append(f"{label}: p95={p95:.1f}ms > {P95_SLA_MS}ms SLA")

        print("\n".join(report_rows))
        assert not failures, "p95 SLA violated:\n  " + "\n  ".join(failures)

    async def test_aggregate_p95_under_sla(self, populated_client):
        """Aggregate (all queries flattened) p95 latency also under SLA.

        This is the headline number — the one quoted on the resume.
        """
        client, total = populated_client
        all_samples: List[float] = []
        for q in QUERY_MIX:
            all_samples.extend(await _measure(client, q, ITERATIONS))
        p50 = _percentile(all_samples, 50)
        p95 = _percentile(all_samples, 95)
        p99 = _percentile(all_samples, 99)
        mean = statistics.mean(all_samples)
        print(
            f"\nAggregate over {len(all_samples)} samples "
            f"(dataset {total:,} events):\n"
            f"  mean={mean:.1f}ms  p50={p50:.1f}ms  p95={p95:.1f}ms  p99={p99:.1f}ms  "
            f"max={max(all_samples):.1f}ms"
        )
        assert p95 < P95_SLA_MS, f"Aggregate p95 {p95:.1f}ms exceeds {P95_SLA_MS}ms SLA"
