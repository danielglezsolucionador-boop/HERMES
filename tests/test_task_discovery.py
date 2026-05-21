from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.runner.task_discovery import (
    TASK_DISCOVERY_ORDERING,
    TaskDiscovery,
)


def _task_row(
    *,
    task_id=None,
    title: str = "task",
    status: str = "pending",
    created_at: datetime | None = None,
    payload: dict | list | None = None,
    retry_count: int = 0,
    max_retries: int = 3,
):
    return {
        "id": task_id or uuid4(),
        "title": title,
        "status": status,
        "phase": "test",
        "payload": payload if payload is not None else {"source": "test"},
        "retry_count": retry_count,
        "max_retries": max_retries,
        "created_at": created_at or datetime.now(timezone.utc),
    }


@pytest.mark.asyncio
async def test_task_discovery_discovers_pending_and_filters_invalid_rows():
    valid_id = uuid4()
    rows = [
        _task_row(status="done"),
        _task_row(status="failed"),
        _task_row(payload=["corrupt"]),
        _task_row(payload={"blob": "x" * 100}),
        _task_row(retry_count=4, max_retries=3),
        _task_row(task_id=valid_id, title="valid pending"),
        _task_row(task_id=valid_id, title="duplicate pending"),
    ]

    async def row_provider(limit: int):
        assert limit == 10
        return rows

    discovery = TaskDiscovery(
        limit=10,
        max_payload_bytes=64,
        query_timeout_seconds=1.0,
        row_provider=row_provider,
    )

    result = await discovery.discover()

    assert result.status == "tasks_discovered"
    assert result.discovered_count == 1
    assert result.candidates[0].id == str(valid_id)
    assert result.candidates[0].status == "pending"
    assert result.candidates[0].eligibility == "ready"
    assert result.ignored_reasons["invalid_status"] == 2
    assert result.ignored_reasons["invalid_payload"] == 1
    assert result.ignored_reasons["payload_too_large"] == 1
    assert result.ignored_reasons["retry_limit_exceeded"] == 1
    assert result.ignored_reasons["duplicate_id"] == 1


@pytest.mark.asyncio
async def test_task_discovery_applies_ordering_and_limits():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    early_retry = uuid4()
    early_zero = uuid4()
    late = uuid4()
    rows = [
        _task_row(task_id=late, title="late", created_at=base + timedelta(minutes=5)),
        _task_row(
            task_id=early_retry,
            title="early retry",
            created_at=base,
            retry_count=1,
        ),
        _task_row(
            task_id=early_zero,
            title="early zero",
            created_at=base,
            retry_count=0,
        ),
    ]

    async def row_provider(limit: int):
        assert limit == 2
        return rows

    discovery = TaskDiscovery(
        limit=2,
        max_payload_bytes=128,
        query_timeout_seconds=1.0,
        row_provider=row_provider,
    )

    result = await discovery.discover()

    assert result.limit == 2
    assert result.ordering == TASK_DISCOVERY_ORDERING
    assert [candidate.id for candidate in result.candidates] == [
        str(early_zero),
        str(early_retry),
    ]
    assert all(candidate.id != str(late) for candidate in result.candidates)


@pytest.mark.asyncio
async def test_task_discovery_accepts_database_payload_null_metadata():
    valid_id = uuid4()
    rows = [
        {
            "id": uuid4(),
            "title": "array payload",
            "status": "pending",
            "phase": "test",
            "payload_type": "array",
            "payload_size_bytes": 2,
            "retry_count": 0,
            "max_retries": 3,
            "created_at": datetime.now(timezone.utc),
        },
        {
            "id": valid_id,
            "title": "null payload",
            "status": "pending",
            "phase": "test",
            "payload_type": "null",
            "payload_size_bytes": 4,
            "retry_count": 0,
            "max_retries": 3,
            "created_at": datetime.now(timezone.utc),
        },
    ]

    async def row_provider(limit: int):
        return rows

    discovery = TaskDiscovery(
        limit=10,
        max_payload_bytes=128,
        query_timeout_seconds=1.0,
        row_provider=row_provider,
    )

    result = await discovery.discover()

    assert result.discovered_count == 1
    assert result.candidates[0].id == str(valid_id)
    assert result.ignored_reasons["invalid_payload"] == 1


@pytest.mark.asyncio
async def test_task_discovery_handles_empty_queue():
    async def row_provider(limit: int):
        assert limit == 5
        return []

    discovery = TaskDiscovery(
        limit=5,
        max_payload_bytes=128,
        query_timeout_seconds=1.0,
        row_provider=row_provider,
    )

    result = await discovery.discover()

    assert result.status == "empty"
    assert result.discovered_count == 0
    assert result.candidates == ()
    assert result.ignored_count == 0
