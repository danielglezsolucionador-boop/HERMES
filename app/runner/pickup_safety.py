"""
Read-only pickup safety controls for Hermes runtime.

This layer protects task pickup from duplicate ownership, stale claims,
runtime inconsistencies, and retry loops. It does not execute, recover,
retry execution, or mutate tasks.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_, select

from app.core.config import settings
from app.db.engine import AsyncSessionLocal
from app.models.task import Task
from app.runner.task_claiming import TASK_CLAIM_STATE_CLAIMED
from app.schemas.task import TaskStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PickupSafetySnapshot:
    active_claims: int = 0
    stale_claims: int = 0
    orphaned_claims: int = 0
    foreign_runtime_claims: int = 0
    invalid_claims: int = 0


@dataclass(frozen=True)
class PickupSafetyResult:
    status: str
    runner_id: str
    runtime_id: str
    allows_pickup: bool
    duplicate_prevention: bool
    race_condition_controlled: bool
    ownership_consistent: bool
    runtime_consistent: bool
    retry_allowed: bool
    active_claims: int = 0
    stale_claims: int = 0
    orphaned_claims: int = 0
    foreign_runtime_claims: int = 0
    invalid_claims: int = 0
    max_concurrent_claims: int = 0
    max_stale_claims: int = 0
    max_orphaned_claims: int = 0
    max_invalid_claims: int = 0
    max_foreign_runtime_claims: int = 0
    pickup_retry_attempts: int = 0
    max_pickup_retries: int = 0
    retry_window_seconds: int = 0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "runner_id": self.runner_id,
            "runtime_id": self.runtime_id,
            "allows_pickup": self.allows_pickup,
            "duplicate_prevention": self.duplicate_prevention,
            "race_condition_controlled": self.race_condition_controlled,
            "ownership_consistent": self.ownership_consistent,
            "runtime_consistent": self.runtime_consistent,
            "retry_allowed": self.retry_allowed,
            "active_claims": self.active_claims,
            "stale_claims": self.stale_claims,
            "orphaned_claims": self.orphaned_claims,
            "foreign_runtime_claims": self.foreign_runtime_claims,
            "invalid_claims": self.invalid_claims,
            "max_concurrent_claims": self.max_concurrent_claims,
            "max_stale_claims": self.max_stale_claims,
            "max_orphaned_claims": self.max_orphaned_claims,
            "max_invalid_claims": self.max_invalid_claims,
            "max_foreign_runtime_claims": self.max_foreign_runtime_claims,
            "pickup_retry_attempts": self.pickup_retry_attempts,
            "max_pickup_retries": self.max_pickup_retries,
            "retry_window_seconds": self.retry_window_seconds,
            "reasons": list(self.reasons),
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


SnapshotProvider = Callable[[], Awaitable[PickupSafetySnapshot]]


class PickupSafety:
    def __init__(
        self,
        runner_id: str = settings.RUNNER_ID,
        runtime_id: str = settings.RUNTIME_ID,
        max_concurrent_claims: int = settings.TASK_CLAIMING_MAX_CONCURRENT_CLAIMS,
        stale_after_seconds: int = settings.TASK_CLAIMING_STALE_AFTER_SECONDS,
        max_stale_claims: int = settings.TASK_CLAIMING_MAX_STALE_CLAIMS,
        max_orphaned_claims: int = settings.TASK_PICKUP_SAFETY_MAX_ORPHANED_CLAIMS,
        max_invalid_claims: int = settings.TASK_PICKUP_SAFETY_MAX_INVALID_CLAIMS,
        max_foreign_runtime_claims: int = (
            settings.TASK_PICKUP_SAFETY_MAX_FOREIGN_RUNTIME_CLAIMS
        ),
        max_pickup_retries: int = settings.TASK_PICKUP_SAFETY_MAX_RETRIES,
        retry_window_seconds: int = settings.TASK_PICKUP_SAFETY_RETRY_WINDOW_SECONDS,
        snapshot_provider: SnapshotProvider | None = None,
    ) -> None:
        self.runner_id = runner_id
        self.runtime_id = runtime_id
        self.max_concurrent_claims = max(1, int(max_concurrent_claims or 1))
        self.stale_after_seconds = max(1, int(stale_after_seconds or 1))
        self.max_stale_claims = max(0, int(max_stale_claims or 0))
        self.max_orphaned_claims = max(0, int(max_orphaned_claims or 0))
        self.max_invalid_claims = max(0, int(max_invalid_claims or 0))
        self.max_foreign_runtime_claims = max(0, int(max_foreign_runtime_claims or 0))
        self.max_pickup_retries = max(0, int(max_pickup_retries or 0))
        self.retry_window_seconds = max(1, int(retry_window_seconds or 1))
        self.snapshot_provider = snapshot_provider
        self._retry_attempts = 0
        self._retry_window_started_at: datetime | None = None

    async def inspect(self) -> PickupSafetyResult:
        started = time.perf_counter()
        try:
            snapshot = await self._snapshot()
        except Exception as exc:
            result = self._error_result(str(exc), started)
            self._log_result(result)
            return result

        reasons = self._reasons(snapshot)
        retry_allowed = self._retry_allowed()
        if not retry_allowed:
            reasons.append("pickup_retry_limit_reached")

        allows_pickup = not reasons
        result = PickupSafetyResult(
            status="safe" if allows_pickup else "blocked",
            runner_id=self.runner_id,
            runtime_id=self.runtime_id,
            allows_pickup=allows_pickup,
            duplicate_prevention=snapshot.invalid_claims <= self.max_invalid_claims,
            race_condition_controlled=snapshot.active_claims < self.max_concurrent_claims,
            ownership_consistent=snapshot.orphaned_claims <= self.max_orphaned_claims,
            runtime_consistent=(
                snapshot.stale_claims <= self.max_stale_claims
                and snapshot.foreign_runtime_claims >= 0
            ),
            retry_allowed=retry_allowed,
            active_claims=snapshot.active_claims,
            stale_claims=snapshot.stale_claims,
            orphaned_claims=snapshot.orphaned_claims,
            foreign_runtime_claims=snapshot.foreign_runtime_claims,
            invalid_claims=snapshot.invalid_claims,
            max_concurrent_claims=self.max_concurrent_claims,
            max_stale_claims=self.max_stale_claims,
            max_orphaned_claims=self.max_orphaned_claims,
            max_invalid_claims=self.max_invalid_claims,
            max_foreign_runtime_claims=self.max_foreign_runtime_claims,
            pickup_retry_attempts=self._retry_attempts,
            max_pickup_retries=self.max_pickup_retries,
            retry_window_seconds=self.retry_window_seconds,
            reasons=tuple(reasons),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        self._log_result(result)
        return result

    def record_pickup_retry(self, reason: str = "pickup_retry") -> None:
        now = datetime.now(timezone.utc)
        if (
            self._retry_window_started_at is None
            or (now - self._retry_window_started_at).total_seconds()
            > self.retry_window_seconds
        ):
            self._retry_window_started_at = now
            self._retry_attempts = 0
        self._retry_attempts += 1
        logger.info(
            "pickup_safety: retry recorded attempts=%s reason=%s",
            self._retry_attempts,
            reason,
        )

    def reset_pickup_retries(self) -> None:
        self._retry_attempts = 0
        self._retry_window_started_at = None

    async def _snapshot(self) -> PickupSafetySnapshot:
        if self.snapshot_provider is not None:
            return await self.snapshot_provider()
        return await self._database_snapshot()

    async def _database_snapshot(self) -> PickupSafetySnapshot:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.stale_after_seconds)
        async with AsyncSessionLocal() as session:
            active_claims = await session.scalar(
                select(func.count(Task.id)).where(
                    Task.status == TaskStatus.claimed.value,
                    Task.runtime_id == self.runtime_id,
                    Task.claim_state == TASK_CLAIM_STATE_CLAIMED,
                )
            )
            stale_claims = await session.scalar(
                select(func.count(Task.id)).where(
                    Task.status == TaskStatus.claimed.value,
                    Task.claim_state == TASK_CLAIM_STATE_CLAIMED,
                    Task.claimed_at < cutoff,
                )
            )
            orphaned_claims = await session.scalar(
                select(func.count(Task.id)).where(
                    Task.status == TaskStatus.claimed.value,
                    or_(
                        Task.runner_id.is_(None),
                        Task.runtime_id.is_(None),
                        Task.claimed_at.is_(None),
                    ),
                )
            )
            foreign_runtime_claims = await session.scalar(
                select(func.count(Task.id)).where(
                    Task.status == TaskStatus.claimed.value,
                    Task.runtime_id.is_not(None),
                    Task.runtime_id != self.runtime_id,
                )
            )
            invalid_claims = await session.scalar(
                select(func.count(Task.id)).where(
                    Task.status == TaskStatus.claimed.value,
                    or_(
                        Task.claim_state != TASK_CLAIM_STATE_CLAIMED,
                        Task.claim_state.is_(None),
                        Task.claim_attempts < 1,
                    ),
                )
            )

        return PickupSafetySnapshot(
            active_claims=int(active_claims or 0),
            stale_claims=int(stale_claims or 0),
            orphaned_claims=int(orphaned_claims or 0),
            foreign_runtime_claims=int(foreign_runtime_claims or 0),
            invalid_claims=int(invalid_claims or 0),
        )

    def _reasons(self, snapshot: PickupSafetySnapshot) -> list[str]:
        reasons: list[str] = []
        if snapshot.active_claims >= self.max_concurrent_claims:
            reasons.append("active_claim_limit_reached")
        if snapshot.stale_claims > self.max_stale_claims:
            reasons.append("stale_claim_limit_reached")
        if snapshot.orphaned_claims > self.max_orphaned_claims:
            reasons.append("orphaned_claims_detected")
        if snapshot.invalid_claims > self.max_invalid_claims:
            reasons.append("invalid_claims_detected")
        if snapshot.foreign_runtime_claims > self.max_foreign_runtime_claims:
            reasons.append("foreign_runtime_claim_limit_reached")
        return reasons

    def _retry_allowed(self) -> bool:
        if self.max_pickup_retries <= 0:
            return False
        if self._retry_window_started_at is None:
            return True
        elapsed = (
            datetime.now(timezone.utc) - self._retry_window_started_at
        ).total_seconds()
        if elapsed > self.retry_window_seconds:
            self.reset_pickup_retries()
            return True
        return self._retry_attempts < self.max_pickup_retries

    def _error_result(self, error: str, started: float) -> PickupSafetyResult:
        return PickupSafetyResult(
            status="error",
            runner_id=self.runner_id,
            runtime_id=self.runtime_id,
            allows_pickup=False,
            duplicate_prevention=False,
            race_condition_controlled=False,
            ownership_consistent=False,
            runtime_consistent=False,
            retry_allowed=False,
            max_concurrent_claims=self.max_concurrent_claims,
            max_stale_claims=self.max_stale_claims,
            max_orphaned_claims=self.max_orphaned_claims,
            max_invalid_claims=self.max_invalid_claims,
            max_foreign_runtime_claims=self.max_foreign_runtime_claims,
            pickup_retry_attempts=self._retry_attempts,
            max_pickup_retries=self.max_pickup_retries,
            retry_window_seconds=self.retry_window_seconds,
            reasons=("pickup_safety_snapshot_failed",),
            error=error or "unknown_pickup_safety_error",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    def _log_result(self, result: PickupSafetyResult) -> None:
        if result.status == "error":
            logger.error(
                "pickup_safety: error reason=%s error=%s duration_ms=%s",
                ",".join(result.reasons),
                result.error,
                result.duration_ms,
            )
            return
        if result.status == "safe":
            logger.debug(
                "pickup_safety: safe active=%s stale=%s invalid=%s duration_ms=%s",
                result.active_claims,
                result.stale_claims,
                result.invalid_claims,
                result.duration_ms,
            )
            return
        logger.warning(
            "pickup_safety: blocked reasons=%s active=%s stale=%s orphaned=%s invalid=%s",
            ",".join(result.reasons),
            result.active_claims,
            result.stale_claims,
            result.orphaned_claims,
            result.invalid_claims,
        )
