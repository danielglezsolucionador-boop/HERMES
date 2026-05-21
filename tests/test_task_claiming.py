from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.runner.task_claiming import (
    TASK_CLAIM_STATE_CLAIMED,
    TaskClaiming,
    TaskClaimingResult,
)
from app.runner.task_discovery import TaskDiscoveryCandidate, TaskDiscoveryResult


def _candidate(task_id: str | None = None) -> TaskDiscoveryCandidate:
    return TaskDiscoveryCandidate(
        id=task_id or str(uuid4()),
        title="claimable task",
        status="pending",
        phase="test",
        retry_count=0,
        max_retries=3,
        created_at=datetime.now(timezone.utc).isoformat(),
        payload_size_bytes=2,
    )


def _discovery(*candidates: TaskDiscoveryCandidate) -> TaskDiscoveryResult:
    return TaskDiscoveryResult(
        status="tasks_discovered" if candidates else "empty",
        discovered_count=len(candidates),
        candidates=tuple(candidates),
        limit=10,
    )


async def _zero_count() -> int:
    return 0


@pytest.mark.asyncio
async def test_task_claiming_claims_one_valid_candidate():
    candidate = _candidate()

    async def claim_provider(row: TaskDiscoveryCandidate) -> TaskClaimingResult:
        return TaskClaimingResult(
            status="claimed",
            runner_id="runner-test",
            runtime_id="runtime-test",
            task_id=row.id,
            task_title=row.title,
            claimed_at=datetime.now(timezone.utc).isoformat(),
            claim_state=TASK_CLAIM_STATE_CLAIMED,
        )

    claiming = TaskClaiming(
        runner_id="runner-test",
        runtime_id="runtime-test",
        min_interval_seconds=0,
        claim_provider=claim_provider,
        active_claim_counter=_zero_count,
        stale_claim_counter=_zero_count,
    )

    result = await claiming.claim_next(_discovery(candidate))

    assert result.status == "claimed"
    assert result.claimed_count == 1
    assert result.attempted_count == 1
    assert result.task_id == candidate.id
    assert result.claim_state == TASK_CLAIM_STATE_CLAIMED


@pytest.mark.asyncio
async def test_task_claiming_rejects_double_claim_conflict():
    candidate = _candidate()
    claimed_ids: set[str] = set()

    async def claim_provider(row: TaskDiscoveryCandidate) -> TaskClaimingResult:
        if row.id in claimed_ids:
            return TaskClaimingResult(
                status="conflict",
                runner_id="runner-test",
                runtime_id="runtime-test",
                task_id=row.id,
                reason="task_missing_or_locked",
            )
        claimed_ids.add(row.id)
        return TaskClaimingResult(
            status="claimed",
            runner_id="runner-test",
            runtime_id="runtime-test",
            task_id=row.id,
            task_title=row.title,
            claimed_at=datetime.now(timezone.utc).isoformat(),
            claim_state=TASK_CLAIM_STATE_CLAIMED,
        )

    claiming = TaskClaiming(
        runner_id="runner-test",
        runtime_id="runtime-test",
        min_interval_seconds=0,
        claim_provider=claim_provider,
        active_claim_counter=_zero_count,
        stale_claim_counter=_zero_count,
    )

    first = await claiming.claim_next(_discovery(candidate))
    second = await claiming.claim_next(_discovery(candidate))

    assert first.status == "claimed"
    assert second.status == "conflict"
    assert second.conflict_count == 1
    assert second.claimed_count == 0


@pytest.mark.asyncio
async def test_task_claiming_enforces_concurrent_claim_limit():
    called = False

    async def active_count() -> int:
        return 1

    async def claim_provider(row: TaskDiscoveryCandidate) -> TaskClaimingResult:
        nonlocal called
        called = True
        return TaskClaimingResult(status="claimed", runner_id="r", runtime_id="rt")

    claiming = TaskClaiming(
        max_concurrent_claims=1,
        min_interval_seconds=0,
        claim_provider=claim_provider,
        active_claim_counter=active_count,
        stale_claim_counter=_zero_count,
    )

    result = await claiming.claim_next(_discovery(_candidate()))

    assert result.status == "limit_reached"
    assert result.reason == "max_concurrent_claims_reached"
    assert called is False


@pytest.mark.asyncio
async def test_task_claiming_enforces_stale_claim_limit():
    async def stale_count() -> int:
        return 6

    async def claim_provider(row: TaskDiscoveryCandidate) -> TaskClaimingResult:
        raise AssertionError("claim provider should not be called")

    claiming = TaskClaiming(
        max_stale_claims=5,
        min_interval_seconds=0,
        claim_provider=claim_provider,
        active_claim_counter=_zero_count,
        stale_claim_counter=stale_count,
    )

    result = await claiming.claim_next(_discovery(_candidate()))

    assert result.status == "stale_limit_reached"
    assert result.reason == "max_stale_claims_reached"
    assert result.stale_claims == 6


@pytest.mark.asyncio
async def test_task_claiming_handles_empty_discovery():
    claiming = TaskClaiming(
        min_interval_seconds=0,
        active_claim_counter=_zero_count,
        stale_claim_counter=_zero_count,
    )

    result = await claiming.claim_next(_discovery())

    assert result.status == "empty"
    assert result.claimed_count == 0
    assert result.attempted_count == 0
