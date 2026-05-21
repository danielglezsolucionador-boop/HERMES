"""
Atomic task claiming for Hermes runtime.

This layer can claim ownership of a valid task. It never executes, retries,
recovers, or completes tasks.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.core.config import settings
from app.db.engine import AsyncSessionLocal
from app.models.task import Task
from app.runner.task_discovery import (
    TaskDiscoveryCandidate,
    TaskDiscoveryResult,
    validate_task_candidate,
)
from app.schemas.task import TaskStatus

logger = logging.getLogger(__name__)

TASK_CLAIM_STATE_CLAIMED = "claimed"

ClaimProvider = Callable[[TaskDiscoveryCandidate], Awaitable["TaskClaimingResult"]]
CountProvider = Callable[[], Awaitable[int]]


@dataclass(frozen=True)
class TaskClaimingResult:
    status: str
    runner_id: str
    runtime_id: str
    attempted_count: int = 0
    claimed_count: int = 0
    conflict_count: int = 0
    rejected_count: int = 0
    active_claims: int = 0
    stale_claims: int = 0
    max_concurrent_claims: int = 0
    max_attempts_per_cycle: int = 0
    max_task_attempts: int = 0
    min_interval_seconds: float = 0.0
    stale_after_seconds: int = 0
    max_stale_claims: int = 0
    task_id: str | None = None
    task_title: str | None = None
    claimed_at: str | None = None
    claim_state: str | None = None
    reason: str | None = None
    error: str | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "runner_id": self.runner_id,
            "runtime_id": self.runtime_id,
            "attempted_count": self.attempted_count,
            "claimed_count": self.claimed_count,
            "conflict_count": self.conflict_count,
            "rejected_count": self.rejected_count,
            "active_claims": self.active_claims,
            "stale_claims": self.stale_claims,
            "max_concurrent_claims": self.max_concurrent_claims,
            "max_attempts_per_cycle": self.max_attempts_per_cycle,
            "max_task_attempts": self.max_task_attempts,
            "min_interval_seconds": self.min_interval_seconds,
            "stale_after_seconds": self.stale_after_seconds,
            "max_stale_claims": self.max_stale_claims,
            "task_id": self.task_id,
            "task_title": self.task_title,
            "claimed_at": self.claimed_at,
            "claim_state": self.claim_state,
            "reason": self.reason,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class TaskClaiming:
    def __init__(
        self,
        runner_id: str = settings.RUNNER_ID,
        runtime_id: str = settings.RUNTIME_ID,
        max_concurrent_claims: int = settings.TASK_CLAIMING_MAX_CONCURRENT_CLAIMS,
        max_attempts_per_cycle: int = settings.TASK_CLAIMING_MAX_ATTEMPTS_PER_CYCLE,
        max_task_attempts: int = settings.TASK_CLAIMING_MAX_TASK_ATTEMPTS,
        min_interval_seconds: float = settings.TASK_CLAIMING_MIN_INTERVAL_SECONDS,
        stale_after_seconds: int = settings.TASK_CLAIMING_STALE_AFTER_SECONDS,
        max_stale_claims: int = settings.TASK_CLAIMING_MAX_STALE_CLAIMS,
        claim_provider: ClaimProvider | None = None,
        active_claim_counter: CountProvider | None = None,
        stale_claim_counter: CountProvider | None = None,
    ) -> None:
        self.runner_id = runner_id
        self.runtime_id = runtime_id
        self.max_concurrent_claims = max(1, int(max_concurrent_claims or 1))
        self.max_attempts_per_cycle = max(1, int(max_attempts_per_cycle or 1))
        self.max_task_attempts = max(1, int(max_task_attempts or 1))
        self.min_interval_seconds = max(0.0, float(min_interval_seconds or 0.0))
        self.stale_after_seconds = max(1, int(stale_after_seconds or 1))
        self.max_stale_claims = max(0, int(max_stale_claims or 0))
        self.claim_provider = claim_provider
        self.active_claim_counter = active_claim_counter
        self.stale_claim_counter = stale_claim_counter
        self._last_claim_attempt_at: datetime | None = None

    async def claim_next(self, discovery: TaskDiscoveryResult) -> TaskClaimingResult:
        started = time.perf_counter()
        candidates = list(discovery.candidates)
        if not candidates:
            return self._result("empty", started=started)

        active_claims = await self._active_claims()
        stale_claims = await self._stale_claims()
        if stale_claims > self.max_stale_claims:
            result = self._result(
                "stale_limit_reached",
                active_claims=active_claims,
                stale_claims=stale_claims,
                reason="max_stale_claims_reached",
                started=started,
            )
            self._log_result(result)
            return result
        if active_claims >= self.max_concurrent_claims:
            result = self._result(
                "limit_reached",
                active_claims=active_claims,
                stale_claims=stale_claims,
                reason="max_concurrent_claims_reached",
                started=started,
            )
            self._log_result(result)
            return result
        if self._rate_limited():
            result = self._result(
                "rate_limited",
                active_claims=active_claims,
                stale_claims=stale_claims,
                reason="min_interval_not_elapsed",
                started=started,
            )
            self._log_result(result)
            return result

        attempted = 0
        conflicts = 0
        rejected = 0
        last_reason: str | None = None
        for candidate in candidates[: self.max_attempts_per_cycle]:
            attempted += 1
            self._last_claim_attempt_at = datetime.now(timezone.utc)
            claim = await self._claim_candidate(candidate)
            if claim.status == "claimed":
                result = self._result(
                    "claimed",
                    attempted_count=attempted,
                    claimed_count=1,
                    active_claims=active_claims + 1,
                    stale_claims=stale_claims,
                    task_id=claim.task_id,
                    task_title=claim.task_title,
                    claimed_at=claim.claimed_at,
                    claim_state=claim.claim_state,
                    started=started,
                )
                self._log_result(result)
                return result
            if claim.status == "conflict":
                conflicts += 1
            else:
                rejected += 1
            last_reason = claim.reason or claim.status

        status = "conflict" if conflicts and not rejected else "rejected"
        result = self._result(
            status,
            attempted_count=attempted,
            conflict_count=conflicts,
            rejected_count=rejected,
            active_claims=active_claims,
            stale_claims=stale_claims,
            reason=last_reason,
            started=started,
        )
        self._log_result(result)
        return result

    async def _claim_candidate(
        self,
        candidate: TaskDiscoveryCandidate,
    ) -> TaskClaimingResult:
        if self.claim_provider is not None:
            return await self.claim_provider(candidate)
        return await self._claim_candidate_in_database(candidate)

    async def _claim_candidate_in_database(
        self,
        candidate: TaskDiscoveryCandidate,
    ) -> TaskClaimingResult:
        try:
            task_id = UUID(candidate.id)
        except (TypeError, ValueError):
            return self._result(
                "rejected",
                task_id=candidate.id,
                task_title=candidate.title,
                reason="invalid_task_id",
            )

        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(
                    select(Task)
                    .where(Task.id == task_id)
                    .with_for_update(skip_locked=True)
                )
                task = result.scalar_one_or_none()
                if task is None:
                    return self._result(
                        "conflict",
                        task_id=candidate.id,
                        task_title=candidate.title,
                        reason="task_missing_or_locked",
                    )

                task_candidate, reason = validate_task_candidate(
                    row={
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "phase": task.phase,
                        "payload": task.payload,
                        "retry_count": task.retry_count,
                        "max_retries": task.max_retries,
                        "created_at": task.created_at,
                    },
                    max_payload_bytes=settings.TASK_DISCOVERY_MAX_PAYLOAD_BYTES,
                )
                if reason is not None or task_candidate is None:
                    return self._result(
                        "rejected",
                        task_id=str(task.id),
                        task_title=task.title,
                        reason=reason or "invalid_task",
                    )

                if int(task.claim_attempts or 0) >= self.max_task_attempts:
                    return self._result(
                        "rejected",
                        task_id=str(task.id),
                        task_title=task.title,
                        reason="max_task_claim_attempts_reached",
                    )

                now = datetime.now(timezone.utc)
                task.status = TaskStatus.claimed.value
                task.runner_id = self.runner_id
                task.runtime_id = self.runtime_id
                task.claimed_at = now
                task.claim_state = TASK_CLAIM_STATE_CLAIMED
                task.claim_attempts = int(task.claim_attempts or 0) + 1
                task.updated_at = now

        return self._result(
            "claimed",
            task_id=str(task_id),
            task_title=candidate.title,
            claimed_at=now.isoformat(),
            claim_state=TASK_CLAIM_STATE_CLAIMED,
        )

    async def _active_claims(self) -> int:
        if self.active_claim_counter is not None:
            return max(0, int(await self.active_claim_counter()))
        async with AsyncSessionLocal() as session:
            return int(
                await session.scalar(
                    select(func.count(Task.id)).where(
                        Task.status == TaskStatus.claimed.value,
                        Task.runtime_id == self.runtime_id,
                        Task.claim_state == TASK_CLAIM_STATE_CLAIMED,
                    )
                )
                or 0
            )

    async def _stale_claims(self) -> int:
        if self.stale_claim_counter is not None:
            return max(0, int(await self.stale_claim_counter()))
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.stale_after_seconds)
        async with AsyncSessionLocal() as session:
            return int(
                await session.scalar(
                    select(func.count(Task.id)).where(
                        Task.status == TaskStatus.claimed.value,
                        Task.claim_state == TASK_CLAIM_STATE_CLAIMED,
                        Task.claimed_at < cutoff,
                    )
                )
                or 0
            )

    def _rate_limited(self) -> bool:
        if self._last_claim_attempt_at is None or self.min_interval_seconds <= 0:
            return False
        elapsed = (
            datetime.now(timezone.utc) - self._last_claim_attempt_at
        ).total_seconds()
        return elapsed < self.min_interval_seconds

    def _result(
        self,
        status: str,
        attempted_count: int = 0,
        claimed_count: int = 0,
        conflict_count: int = 0,
        rejected_count: int = 0,
        active_claims: int = 0,
        stale_claims: int = 0,
        task_id: str | None = None,
        task_title: str | None = None,
        claimed_at: str | None = None,
        claim_state: str | None = None,
        reason: str | None = None,
        error: str | None = None,
        started: float | None = None,
    ) -> TaskClaimingResult:
        duration_ms = 0
        if started is not None:
            duration_ms = int((time.perf_counter() - started) * 1000)
        return TaskClaimingResult(
            status=status,
            runner_id=self.runner_id,
            runtime_id=self.runtime_id,
            attempted_count=attempted_count,
            claimed_count=claimed_count,
            conflict_count=conflict_count,
            rejected_count=rejected_count,
            active_claims=active_claims,
            stale_claims=stale_claims,
            max_concurrent_claims=self.max_concurrent_claims,
            max_attempts_per_cycle=self.max_attempts_per_cycle,
            max_task_attempts=self.max_task_attempts,
            min_interval_seconds=self.min_interval_seconds,
            stale_after_seconds=self.stale_after_seconds,
            max_stale_claims=self.max_stale_claims,
            task_id=task_id,
            task_title=task_title,
            claimed_at=claimed_at,
            claim_state=claim_state,
            reason=reason,
            error=error,
            duration_ms=duration_ms,
        )

    def _log_result(self, result: TaskClaimingResult) -> None:
        if result.status == "claimed":
            logger.info(
                "task_claiming: claimed task_id=%s runner_id=%s runtime_id=%s",
                result.task_id,
                result.runner_id,
                result.runtime_id,
            )
            return
        if result.status in {"conflict", "rejected", "stale_limit_reached"}:
            logger.warning(
                "task_claiming: status=%s attempted=%s conflicts=%s rejected=%s reason=%s",
                result.status,
                result.attempted_count,
                result.conflict_count,
                result.rejected_count,
                result.reason,
            )
            return
        logger.debug(
            "task_claiming: status=%s active=%s stale=%s reason=%s",
            result.status,
            result.active_claims,
            result.stale_claims,
            result.reason,
        )
