"""
Runtime loop foundation for Hermes.

This loop maintains runtime heartbeat and lifecycle state. Task claiming and
task execution are controlled and disabled by default.
Execution sessions, timeout control, provider bridge, response ingestion,
response validation, response safety, and orchestration foundations are
initialized for observability but do not run autonomous work.
"""
import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.core.config import settings
from app.db.engine import AsyncSessionLocal
from app.models.task import Task
from app.runner.executors import execute_task
from app.runner.pickup_safety import PickupSafety, PickupSafetyResult
from app.runner.execution_safety import ExecutionSafety, ExecutionSafetyResult
from app.runner.execution_session import (
    ExecutionSessionManager,
    ExecutionSessionResult,
)
from app.runner.orchestration_foundation import (
    OrchestrationResult,
    OrchestrationRuntime,
)
from app.runner.orchestration_safety import (
    OrchestrationSafety,
    OrchestrationSafetyResult,
)
from app.runner.response_ingestion import ResponseIngestionRuntime
from app.runner.response_safety import ResponseSafetyRuntime
from app.runner.response_validation import ResponseValidationRuntime
from app.runner.retry_control import RetryControl, RetryControlResult
from app.runner.task_claiming import (
    TASK_CLAIM_STATE_CLAIMED,
    TaskClaiming,
    TaskClaimingResult,
)
from app.runner.task_discovery import TaskDiscovery, TaskDiscoveryResult
from app.runner.task_execution import TaskExecutionRuntime
from app.runner.timeout_control import TimeoutControl, TimeoutControlResult
from app.schemas.task import TaskStatus
from app.services.runtime_status import RuntimeStatus, runtime_status

logger = logging.getLogger(__name__)

DEFAULT_RUNTIME_LOOP_INTERVAL_SECONDS = 5.0
MIN_RUNTIME_LOOP_INTERVAL_SECONDS = 0.5
HEARTBEAT_LOG_EVERY = 60


class RuntimeLoop:
    def __init__(
        self,
        status: RuntimeStatus = runtime_status,
        interval_seconds: float = settings.RUNTIME_LOOP_INTERVAL_SECONDS,
        min_interval_seconds: float = settings.RUNTIME_LOOP_MIN_INTERVAL_SECONDS,
        heartbeat_log_every: int = HEARTBEAT_LOG_EVERY,
        pending_task_counter: Callable[[], Awaitable[int]] | None = None,
        task_discovery: Callable[[], Awaitable[TaskDiscoveryResult]] | None = None,
        task_claiming: Callable[[TaskDiscoveryResult], Awaitable[TaskClaimingResult]] | None = None,
        task_executor: Callable[[Task], Awaitable[dict[str, Any]]] | None = None,
        pickup_safety: Callable[[], Awaitable[PickupSafetyResult]] | None = None,
        execution_session: Callable[[], Awaitable[ExecutionSessionResult]] | None = None,
        execution_safety: Callable[[], Awaitable[ExecutionSafetyResult]] | None = None,
        timeout_control: Callable[[], Awaitable[TimeoutControlResult]] | None = None,
        retry_control: Callable[[], Awaitable[RetryControlResult]] | None = None,
        orchestration: Callable[[], Awaitable[OrchestrationResult]] | None = None,
        orchestration_safety: (
            Callable[[OrchestrationResult | None], Awaitable[OrchestrationSafetyResult]]
            | None
        ) = None,
        claiming_enabled: bool = settings.TASK_CLAIMING_ENABLED,
        pickup_safety_enabled: bool = settings.TASK_PICKUP_SAFETY_ENABLED,
        execution_session_enabled: bool = settings.EXECUTION_SESSION_ENABLED,
        execution_enabled: bool = settings.TASK_EXECUTION_ENABLED,
        execution_safety_enabled: bool = settings.TASK_EXECUTION_SAFETY_ENABLED,
        timeout_control_enabled: bool = settings.TIMEOUT_CONTROL_ENABLED,
        retry_control_enabled: bool = settings.RETRY_CONTROL_ENABLED,
        orchestration_enabled: bool = settings.ORCHESTRATION_ENABLED,
        orchestration_safety_enabled: bool = settings.ORCHESTRATION_SAFETY_ENABLED,
        provider_bridge_enabled: bool = settings.PROVIDER_BRIDGE_ENABLED,
        response_ingestion_enabled: bool = settings.RESPONSE_INGESTION_ENABLED,
        response_validation_enabled: bool = settings.RESPONSE_VALIDATION_ENABLED,
        response_safety_enabled: bool = settings.RESPONSE_SAFETY_ENABLED,
        degraded_error_threshold: int = settings.RUNTIME_LOOP_DEGRADED_ERROR_THRESHOLD,
        max_consecutive_errors: int = settings.RUNTIME_LOOP_MAX_CONSECUTIVE_ERRORS,
        safety_event_limit: int = settings.RUNTIME_LOOP_SAFETY_EVENT_LIMIT,
    ) -> None:
        self.status = status
        self.interval_seconds = max(float(interval_seconds), float(min_interval_seconds))
        self.heartbeat_log_every = max(1, int(heartbeat_log_every))
        self.pending_task_counter = pending_task_counter
        if task_discovery is not None:
            self.task_discovery = task_discovery
        elif pending_task_counter is not None:
            self.task_discovery = self._discover_from_pending_counter
        else:
            self.task_discovery = TaskDiscovery().discover
        self.claiming_enabled = bool(claiming_enabled)
        self.task_claiming = task_claiming or TaskClaiming().claim_next
        self.pickup_safety_enabled = bool(
            pickup_safety_enabled
            and (
                pickup_safety is not None
                or (pending_task_counter is None and task_discovery is None)
            )
        )
        self.pickup_safety = pickup_safety or PickupSafety().inspect
        self.execution_session_enabled = bool(execution_session_enabled)
        self.execution_session_manager = ExecutionSessionManager()
        self.execution_session = execution_session or self._inspect_execution_session
        self.execution_enabled = bool(execution_enabled)
        self.task_execution_runtime = TaskExecutionRuntime()
        self.task_executor = task_executor or execute_task
        self.execution_safety_enabled = bool(execution_safety_enabled)
        self.execution_safety = execution_safety or ExecutionSafety().inspect
        self.timeout_control_enabled = bool(timeout_control_enabled)
        self.timeout_control_runtime = TimeoutControl()
        self.timeout_control = timeout_control or self._inspect_timeout_control
        self.retry_control_enabled = bool(retry_control_enabled)
        self.retry_control_runtime = RetryControl()
        self.retry_control = retry_control or self._inspect_retry_control
        self.orchestration_enabled = bool(orchestration_enabled)
        self.orchestration_runtime = OrchestrationRuntime()
        self.orchestration = orchestration or self._inspect_orchestration
        self.orchestration_safety_enabled = bool(orchestration_safety_enabled)
        self.orchestration_safety_runtime = OrchestrationSafety()
        self.orchestration_safety = (
            orchestration_safety or self._inspect_orchestration_safety
        )
        self.provider_bridge_enabled = bool(provider_bridge_enabled)
        self.response_ingestion_enabled = bool(response_ingestion_enabled)
        self.response_ingestion = ResponseIngestionRuntime()
        self.response_validation_enabled = bool(response_validation_enabled)
        self.response_validation = ResponseValidationRuntime()
        self.response_safety_enabled = bool(response_safety_enabled)
        self.response_safety = ResponseSafetyRuntime()
        self.degraded_error_threshold = max(1, int(degraded_error_threshold))
        self.max_consecutive_errors = max(
            self.degraded_error_threshold,
            int(max_consecutive_errors),
        )
        self.safety_event_limit = max(1, int(safety_event_limit))
        self._stop_requested = False
        self._paused = False
        self._last_logged_tasks_detected: int | None = None

    def pause(self) -> None:
        self._paused = True
        self.status.mark_runtime_loop_paused()
        logger.info("runtime_loop: paused")

    def resume(self) -> None:
        self._paused = False
        logger.info("runtime_loop: resumed")

    def request_stop(self, reason: str = "stop_requested") -> None:
        self._stop_requested = True
        self.status.request_runtime_loop_stop(reason)
        logger.info("runtime_loop: stop requested reason=%s", reason)

    async def _cycle(self) -> str:
        if self._paused:
            self.status.mark_runtime_loop_paused()
            return "paused"
        poll_started = time.perf_counter()
        discovery_result = await self.task_discovery()
        poll_duration_ms = int((time.perf_counter() - poll_started) * 1000)
        self.status.mark_task_discovery_completed(discovery_result.to_dict())
        tasks_detected = discovery_result.discovered_count
        self.status.mark_polling_completed(
            tasks_detected=tasks_detected,
            duration_ms=poll_duration_ms,
        )
        pickup_safety_result: PickupSafetyResult | None = None
        if self.pickup_safety_enabled:
            pickup_safety_result = await self.pickup_safety()
            self.status.mark_pickup_safety_completed(
                pickup_safety_result.to_dict()
            )
        claiming_result: TaskClaimingResult | None = None
        if self.claiming_enabled:
            if (
                pickup_safety_result is not None
                and not pickup_safety_result.allows_pickup
            ):
                claiming_result = self._pickup_safety_blocked_claiming_result(
                    pickup_safety_result
                )
            else:
                claiming_result = await self.task_claiming(discovery_result)
            self.status.mark_task_claiming_completed(claiming_result.to_dict())
        if self.execution_session_enabled:
            execution_session_result = await self.execution_session()
            self.status.mark_execution_session_completed(
                execution_session_result.to_dict()
            )
        execution_safety_result: ExecutionSafetyResult | None = None
        if self.execution_safety_enabled:
            execution_safety_result = await self.execution_safety()
            self.status.mark_execution_safety_completed(
                execution_safety_result.to_dict()
            )
        if self.execution_enabled:
            await self._execute_controlled_task(
                claiming_result=claiming_result,
                execution_safety_result=execution_safety_result,
            )
        if self.timeout_control_enabled:
            timeout_control_result = await self.timeout_control()
            self.status.mark_timeout_control_result(
                timeout_control_result.to_dict()
            )
        if self.retry_control_enabled:
            retry_control_result = await self.retry_control()
            self.status.mark_retry_control_result(retry_control_result.to_dict())
        orchestration_result: OrchestrationResult | None = None
        if self.orchestration_enabled:
            orchestration_result = await self.orchestration()
            self.status.mark_orchestration_result(orchestration_result.to_dict())
        if self.orchestration_safety_enabled:
            orchestration_safety_result = await self.orchestration_safety(
                orchestration_result
            )
            self.status.mark_orchestration_safety_completed(
                orchestration_safety_result.to_dict()
            )
        if (
            tasks_detected > 0
            and tasks_detected != self._last_logged_tasks_detected
        ):
            logger.info(
                "runtime_loop: task candidates discovered count=%s",
                tasks_detected,
            )
            self._last_logged_tasks_detected = tasks_detected
        return "active"

    def _pickup_safety_blocked_claiming_result(
        self,
        pickup_safety: PickupSafetyResult,
    ) -> TaskClaimingResult:
        return TaskClaimingResult(
            status="blocked_by_pickup_safety",
            runner_id=pickup_safety.runner_id,
            runtime_id=pickup_safety.runtime_id,
            active_claims=pickup_safety.active_claims,
            stale_claims=pickup_safety.stale_claims,
            max_concurrent_claims=pickup_safety.max_concurrent_claims,
            stale_after_seconds=settings.TASK_CLAIMING_STALE_AFTER_SECONDS,
            max_stale_claims=pickup_safety.max_stale_claims,
            reason=",".join(pickup_safety.reasons) or pickup_safety.status,
            error=pickup_safety.error,
        )

    async def _discover_from_pending_counter(self) -> TaskDiscoveryResult:
        if self.pending_task_counter is None:
            return TaskDiscoveryResult.from_count(0)
        started = time.perf_counter()
        tasks_detected = await self.pending_task_counter()
        duration_ms = int((time.perf_counter() - started) * 1000)
        return TaskDiscoveryResult.from_count(tasks_detected, duration_ms)

    async def _execute_controlled_task(
        self,
        claiming_result: TaskClaimingResult | None = None,
        execution_safety_result: ExecutionSafetyResult | None = None,
    ) -> None:
        if (
            execution_safety_result is not None
            and not execution_safety_result.allows_execution
        ):
            self.status.mark_task_execution_result(
                self._execution_rejected_result(
                    reason="execution_safety_blocked",
                    error=execution_safety_result.error,
                )
            )
            return

        task = await self._claimed_task_for_execution(claiming_result)
        if task is None:
            return

        prepared = self.task_execution_runtime.prepare(
            task,
            runtime_active=not self._stop_requested,
        )
        self.status.mark_task_execution_result(prepared.to_dict())
        if not prepared.eligible or prepared.context is None:
            return

        if self._task_requires_provider(task) and not self.provider_bridge_enabled:
            reason = "provider_bridge_disabled_for_ai_task"
            self.status.mark_task_execution_result(
                self._execution_rejected_result(task=task, reason=reason)
            )
            await self._persist_execution_blocked(task, reason)
            logger.warning(
                "runtime_loop: execution blocked task_id=%s reason=%s",
                task.id,
                reason,
            )
            return

        started = self.task_execution_runtime.start(prepared.context)
        self.status.mark_task_execution_result(started.to_dict())
        if not started.eligible or started.context is None:
            return

        self.status.mark_task_started(str(task.id), task.title)
        try:
            await self._mark_task_doing(task)
            result = await self.task_executor(task)
            await self._persist_execution_success(task, result)
            completed = self.task_execution_runtime.complete(started.context)
            self.status.mark_task_execution_result(completed.to_dict())
            self.status.mark_task_done()
        except Exception as exc:
            error = str(exc) or exc.__class__.__name__
            failed = self.task_execution_runtime.fail(started.context, error)
            self.status.mark_task_execution_result(failed.to_dict())
            await self._persist_execution_failure(task, error)
            self.status.mark_task_failed()
            logger.error(
                "runtime_loop: execution failed task_id=%s error=%s",
                task.id,
                error,
            )

    async def _claimed_task_for_execution(
        self,
        claiming_result: TaskClaimingResult | None,
    ) -> Task | None:
        if (
            claiming_result is not None
            and claiming_result.status == "claimed"
            and claiming_result.task_id
        ):
            task = await self._load_claimed_task(claiming_result.task_id)
            if task is not None:
                return task
        return await self._load_next_claimed_task()

    async def _load_claimed_task(self, task_id: str) -> Task | None:
        try:
            task_uuid = UUID(str(task_id))
        except (TypeError, ValueError):
            return None

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Task).where(
                    Task.id == task_uuid,
                    Task.status == TaskStatus.claimed.value,
                    Task.runner_id == self.task_execution_runtime.runner_id,
                    Task.runtime_id == self.task_execution_runtime.runtime_id,
                    Task.claim_state == TASK_CLAIM_STATE_CLAIMED,
                )
            )
            return result.scalar_one_or_none()

    async def _load_next_claimed_task(self) -> Task | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Task)
                .where(
                    Task.status == TaskStatus.claimed.value,
                    Task.runner_id == self.task_execution_runtime.runner_id,
                    Task.runtime_id == self.task_execution_runtime.runtime_id,
                    Task.claim_state == TASK_CLAIM_STATE_CLAIMED,
                )
                .order_by(Task.claimed_at.asc().nullsfirst(), Task.created_at.asc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def _mark_task_doing(self, task: Task) -> None:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                current = await session.get(Task, task.id)
                if current is None:
                    raise RuntimeError("claimed_task_missing_before_execution")
                current.status = TaskStatus.doing.value
                current.started_at = now
                current.completed_at = None
                current.error = None
                current.updated_at = now
        task.status = TaskStatus.doing.value
        task.started_at = now
        task.completed_at = None
        task.error = None

    async def _persist_execution_success(
        self,
        task: Task,
        result: dict[str, Any],
    ) -> None:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                current = await session.get(Task, task.id)
                if current is None:
                    raise RuntimeError("executed_task_missing_before_success")
                current.status = TaskStatus.done.value
                current.result = result
                current.error = None
                current.completed_at = now
                current.claim_state = None
                current.updated_at = now
        logger.info("runtime_loop: execution completed task_id=%s", task.id)

    async def _persist_execution_failure(self, task: Task, error: str) -> None:
        now = datetime.now(timezone.utc)
        retry_count = int(task.retry_count or 0)
        max_retries = int(task.max_retries or 0)
        should_retry = retry_count < max_retries

        async with AsyncSessionLocal() as session:
            async with session.begin():
                current = await session.get(Task, task.id)
                if current is None:
                    raise RuntimeError("executed_task_missing_before_failure")
                current.error = error
                current.completed_at = now
                current.claim_state = None
                current.runner_id = None
                current.runtime_id = None
                current.claimed_at = None
                current.updated_at = now
                if should_retry:
                    current.status = TaskStatus.pending.value
                    current.retry_count = retry_count + 1
                    current.last_retry_at = now
                else:
                    current.status = TaskStatus.failed.value

        if should_retry:
            logger.warning(
                "runtime_loop: execution requeued task_id=%s retry=%s/%s error=%s",
                task.id,
                retry_count + 1,
                max_retries,
                error,
            )
            return
        logger.warning(
            "runtime_loop: execution failed task_id=%s retries=%s/%s error=%s",
            task.id,
            retry_count,
            max_retries,
            error,
        )

    async def _persist_execution_blocked(self, task: Task, reason: str) -> None:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                current = await session.get(Task, task.id)
                if current is None:
                    raise RuntimeError("blocked_task_missing_before_review")
                current.status = TaskStatus.review.value
                current.error = reason
                current.completed_at = now
                current.claim_state = None
                current.runner_id = None
                current.runtime_id = None
                current.claimed_at = None
                current.updated_at = now

    def _task_requires_provider(self, task: Task) -> bool:
        payload = task.payload if isinstance(task.payload, dict) else {}
        return (
            payload.get("executor") == "ai"
            or payload.get("type") == "ai"
            or payload.get("agent") in {"claude", "vulcano", "openrouter"}
        )

    def _execution_rejected_result(
        self,
        reason: str,
        task: Task | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        return {
            "status": "rejected",
            "eligible": False,
            "runner_id": self.task_execution_runtime.runner_id,
            "runtime_id": self.task_execution_runtime.runtime_id,
            "runtime_owner": self.task_execution_runtime.runtime_owner,
            "task_id": str(task.id) if task is not None else None,
            "task_title": task.title if task is not None else None,
            "active_executions": 0,
            "max_concurrent_executions": (
                self.task_execution_runtime.max_concurrent_executions
            ),
            "max_duration_seconds": (
                self.task_execution_runtime.max_duration_seconds
            ),
            "max_runtime_load": self.task_execution_runtime.max_runtime_load,
            "runtime_load": self.task_execution_runtime.visibility().get(
                "runtime_load"
            ),
            "max_memory_mb": self.task_execution_runtime.max_memory_mb,
            "memory_usage_mb": self.task_execution_runtime.visibility().get(
                "memory_usage_mb"
            ),
            "reasons": [reason],
            "error": error,
        }

    async def _inspect_timeout_control(self) -> TimeoutControlResult:
        return await self.timeout_control_runtime.inspect(
            execution_visibility=self.task_execution_runtime.visibility(),
            runtime_active=not self._stop_requested,
        )

    async def _inspect_retry_control(self) -> RetryControlResult:
        return await self.retry_control_runtime.inspect(
            runtime_active=not self._stop_requested,
            retry_permitted=True,
            provider_available=True,
        )

    async def _inspect_execution_session(self) -> ExecutionSessionResult:
        return await self.execution_session_manager.inspect()

    async def _inspect_orchestration(self) -> OrchestrationResult:
        return await self.orchestration_runtime.inspect(
            runtime_active=not self._stop_requested,
            coordination_permitted=True,
        )

    async def _inspect_orchestration_safety(
        self,
        orchestration_result: OrchestrationResult | None = None,
    ) -> OrchestrationSafetyResult:
        return await self.orchestration_safety_runtime.inspect(
            orchestration_result=orchestration_result,
            orchestration_visibility=self.orchestration_runtime.visibility(),
            runtime_active=not self._stop_requested,
        )

    async def _count_pending_tasks(self) -> int:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count(Task.id)).where(
                    Task.status == TaskStatus.pending.value
                )
            )
            return int(result.scalar_one() or 0)

    async def run(self) -> None:
        self._stop_requested = False
        self.status.configure_safety_event_limit(self.safety_event_limit)
        self.status.mark_runtime_loop_started(self.interval_seconds)
        self.status.mark_polling_started(self.interval_seconds)
        self.status.mark_task_discovery_started(self.interval_seconds)
        self.status.mark_task_claiming_started(
            enabled=self.claiming_enabled,
            interval_seconds=self.interval_seconds,
        )
        self.status.mark_pickup_safety_started(
            enabled=self.pickup_safety_enabled,
            interval_seconds=self.interval_seconds,
        )
        self.status.mark_task_execution_started(
            enabled=self.execution_enabled,
            interval_seconds=self.interval_seconds,
            max_concurrent_executions=settings.TASK_EXECUTION_MAX_CONCURRENT_EXECUTIONS,
            max_duration_seconds=settings.TASK_EXECUTION_MAX_DURATION_SECONDS,
            max_runtime_load=settings.TASK_EXECUTION_MAX_RUNTIME_LOAD,
            max_memory_mb=settings.TASK_EXECUTION_MAX_MEMORY_MB,
            runtime_owner=f"{settings.RUNNER_ID}:{settings.RUNTIME_ID}",
        )
        self.status.mark_execution_session_started(
            enabled=self.execution_session_enabled,
            interval_seconds=self.interval_seconds,
            max_active_sessions=settings.EXECUTION_SESSION_MAX_ACTIVE,
            max_log_entries=settings.EXECUTION_SESSION_MAX_LOG_ENTRIES,
            runtime_owner=f"{settings.RUNNER_ID}:{settings.RUNTIME_ID}",
        )
        self.status.mark_execution_safety_started(
            enabled=self.execution_safety_enabled,
            interval_seconds=self.interval_seconds,
            max_retries=settings.TASK_EXECUTION_SAFETY_MAX_RETRIES,
            max_concurrent_executions=settings.TASK_EXECUTION_MAX_CONCURRENT_EXECUTIONS,
            max_duration_seconds=settings.TASK_EXECUTION_MAX_DURATION_SECONDS,
            max_runtime_load=settings.TASK_EXECUTION_MAX_RUNTIME_LOAD,
            max_memory_mb=settings.TASK_EXECUTION_MAX_MEMORY_MB,
            max_concurrent_provider_calls=settings.PROVIDER_BRIDGE_MAX_CONCURRENT_CALLS,
        )
        self.status.mark_timeout_control_started(
            enabled=self.timeout_control_enabled,
            interval_seconds=self.interval_seconds,
            max_concurrent_timeout_checks=(
                settings.TIMEOUT_CONTROL_MAX_CONCURRENT_CHECKS
            ),
            max_tracking_duration_ms=(
                settings.TIMEOUT_CONTROL_MAX_TRACKING_DURATION_SECONDS * 1000
            ),
            max_runtime_timeout_load=settings.TIMEOUT_CONTROL_MAX_RUNTIME_LOAD,
            max_timeout_check_duration_ms=(
                settings.TIMEOUT_CONTROL_MAX_CHECK_DURATION_MS
            ),
        )
        self.status.mark_retry_control_started(
            enabled=self.retry_control_enabled,
            interval_seconds=self.interval_seconds,
            max_retry_attempts=settings.RETRY_CONTROL_MAX_ATTEMPTS,
            max_concurrent_retries=settings.RETRY_CONTROL_MAX_CONCURRENT_RETRIES,
            max_retry_duration_ms=settings.RETRY_CONTROL_MAX_DURATION_MS,
            max_runtime_retry_load=settings.RETRY_CONTROL_MAX_RUNTIME_LOAD,
            max_retry_overhead_ms=settings.RETRY_CONTROL_MAX_OVERHEAD_MS,
        )
        self.status.mark_orchestration_started(
            enabled=self.orchestration_enabled,
            interval_seconds=self.interval_seconds,
            max_active_orchestrations=settings.ORCHESTRATION_MAX_ACTIVE,
            max_execution_dependencies=settings.ORCHESTRATION_MAX_DEPENDENCIES,
            max_dependency_chain=settings.ORCHESTRATION_MAX_DEPENDENCY_CHAIN,
            max_orchestration_duration_ms=settings.ORCHESTRATION_MAX_DURATION_MS,
            max_orchestration_load=settings.ORCHESTRATION_MAX_RUNTIME_LOAD,
            max_coordination_overhead_ms=settings.ORCHESTRATION_MAX_OVERHEAD_MS,
        )
        self.status.mark_orchestration_safety_started(
            enabled=self.orchestration_safety_enabled,
            interval_seconds=self.interval_seconds,
            max_retries=settings.ORCHESTRATION_SAFETY_MAX_RETRIES,
            max_orchestration_duration_ms=settings.ORCHESTRATION_MAX_DURATION_MS,
            max_coordination_overhead_ms=settings.ORCHESTRATION_MAX_OVERHEAD_MS,
        )
        self.status.mark_provider_bridge_started(
            enabled=self.provider_bridge_enabled,
            interval_seconds=self.interval_seconds,
            max_concurrent_calls=settings.PROVIDER_BRIDGE_MAX_CONCURRENT_CALLS,
            max_requests_per_minute=settings.PROVIDER_BRIDGE_MAX_REQUESTS_PER_MINUTE,
            max_request_bytes=settings.PROVIDER_BRIDGE_MAX_REQUEST_BYTES,
            timeout_seconds=settings.PROVIDER_BRIDGE_TIMEOUT_SECONDS,
            max_response_bytes=settings.PROVIDER_BRIDGE_MAX_RESPONSE_BYTES,
        )
        self.status.mark_response_ingestion_started(
            enabled=self.response_ingestion_enabled,
            interval_seconds=self.interval_seconds,
            max_concurrent_ingestions=(
                settings.RESPONSE_INGESTION_MAX_CONCURRENT_INGESTIONS
            ),
            max_response_bytes=settings.RESPONSE_INGESTION_MAX_RESPONSE_BYTES,
            max_ingestion_duration_ms=settings.RESPONSE_INGESTION_MAX_DURATION_MS,
            max_runtime_ingestion_load=(
                settings.RESPONSE_INGESTION_MAX_RUNTIME_LOAD
            ),
        )
        self.status.mark_response_validation_started(
            enabled=self.response_validation_enabled,
            interval_seconds=self.interval_seconds,
            max_concurrent_validations=(
                settings.RESPONSE_VALIDATION_MAX_CONCURRENT_VALIDATIONS
            ),
            max_payload_inspection_bytes=(
                settings.RESPONSE_VALIDATION_MAX_PAYLOAD_BYTES
            ),
            max_validation_duration_ms=settings.RESPONSE_VALIDATION_MAX_DURATION_MS,
            max_runtime_validation_load=(
                settings.RESPONSE_VALIDATION_MAX_RUNTIME_LOAD
            ),
        )
        self.status.mark_response_safety_started(
            enabled=self.response_safety_enabled,
            interval_seconds=self.interval_seconds,
            max_concurrent_safety_checks=(
                settings.RESPONSE_SAFETY_MAX_CONCURRENT_CHECKS
            ),
            max_payload_bytes=settings.RESPONSE_SAFETY_MAX_PAYLOAD_BYTES,
            max_safety_duration_ms=settings.RESPONSE_SAFETY_MAX_DURATION_MS,
            max_runtime_safety_load=settings.RESPONSE_SAFETY_MAX_RUNTIME_LOAD,
            max_validation_retries=(
                settings.RESPONSE_SAFETY_MAX_VALIDATION_RETRIES
            ),
        )
        logger.info(
            "runtime_loop: started interval_seconds=%s",
            self.interval_seconds,
        )
        logger.info("runtime_loop: polling started")
        logger.info("runtime_loop: task discovery started")
        logger.info(
            "runtime_loop: task claiming %s",
            "enabled" if self.claiming_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: pickup safety %s",
            "enabled" if self.pickup_safety_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: execution foundation %s",
            "enabled" if self.execution_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: execution session %s",
            "enabled" if self.execution_session_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: execution safety %s",
            "enabled" if self.execution_safety_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: timeout control %s",
            "enabled" if self.timeout_control_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: retry control %s",
            "enabled" if self.retry_control_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: orchestration foundation %s",
            "enabled" if self.orchestration_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: orchestration safety %s",
            "enabled" if self.orchestration_safety_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: provider bridge %s",
            "enabled" if self.provider_bridge_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: response ingestion %s",
            "enabled" if self.response_ingestion_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: response validation %s",
            "enabled" if self.response_validation_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: response safety %s",
            "enabled" if self.response_safety_enabled else "disabled",
        )

        stop_reason = "stopped"
        try:
            while not self._stop_requested:
                cycle_started = time.perf_counter()
                try:
                    state = await self._cycle()
                    self.status.mark_runtime_loop_cycle_success()
                except asyncio.CancelledError:
                    stop_reason = "cancelled"
                    logger.info("runtime_loop: cancelled")
                    raise
                except Exception as exc:
                    state = "recovering"
                    poll_duration_ms = int(
                        (time.perf_counter() - cycle_started) * 1000
                    )
                    self.status.mark_task_discovery_error(str(exc), poll_duration_ms)
                    if self.pickup_safety_enabled:
                        self.status.mark_pickup_safety_error(
                            str(exc),
                            poll_duration_ms,
                        )
                    if self.claiming_enabled:
                        self.status.mark_task_claiming_error(str(exc), poll_duration_ms)
                    if self.execution_enabled:
                        self.status.mark_task_execution_error(str(exc), poll_duration_ms)
                    if self.execution_session_enabled:
                        self.status.mark_execution_session_error(
                            str(exc),
                            poll_duration_ms,
                        )
                    if self.execution_safety_enabled:
                        self.status.mark_execution_safety_error(str(exc), poll_duration_ms)
                    if self.timeout_control_enabled:
                        self.status.mark_timeout_control_error(
                            str(exc),
                            poll_duration_ms,
                        )
                    if self.retry_control_enabled:
                        self.status.mark_retry_control_error(
                            str(exc),
                            poll_duration_ms,
                        )
                    if self.orchestration_enabled:
                        self.status.mark_orchestration_error(
                            str(exc),
                            poll_duration_ms,
                        )
                    if self.orchestration_safety_enabled:
                        self.status.mark_orchestration_safety_error(
                            str(exc),
                            poll_duration_ms,
                        )
                    if self.provider_bridge_enabled:
                        self.status.mark_provider_bridge_error(str(exc), poll_duration_ms)
                    if self.response_ingestion_enabled:
                        self.status.mark_response_ingestion_error(
                            str(exc),
                            poll_duration_ms,
                        )
                    if self.response_validation_enabled:
                        self.status.mark_response_validation_error(
                            str(exc),
                            poll_duration_ms,
                        )
                    if self.response_safety_enabled:
                        self.status.mark_response_safety_error(
                            str(exc),
                            poll_duration_ms,
                        )
                    self.status.mark_polling_error(str(exc), poll_duration_ms)
                    safety = self.status.mark_runtime_loop_error(
                        str(exc),
                        degraded_threshold=self.degraded_error_threshold,
                        max_consecutive_errors=self.max_consecutive_errors,
                    )
                    logger.error("runtime_loop: cycle error survived error=%s", exc)
                    if safety["degraded_started"]:
                        logger.warning(
                            "runtime_loop: degraded consecutive_errors=%s",
                            self.status.consecutive_errors,
                        )
                    if safety["should_stop"]:
                        self.request_stop(self.status.safety_stop_reason or "unsafe_runtime")
                        logger.critical(
                            "runtime_loop: safety stop triggered reason=%s consecutive_errors=%s",
                            self.status.safety_stop_reason,
                            self.status.consecutive_errors,
                        )

                duration_ms = int((time.perf_counter() - cycle_started) * 1000)
                self.status.mark_runtime_loop_heartbeat(
                    state=state,
                    cycle_duration_ms=duration_ms,
                )
                iteration = self.status.runtime_loop_iteration
                if iteration == 1 or iteration % self.heartbeat_log_every == 0:
                    logger.info(
                        "runtime_loop: heartbeat iteration=%s state=%s duration_ms=%s",
                        iteration,
                        state,
                        duration_ms,
                    )
                    logger.info(
                        "runtime_loop: polling completed iteration=%s status=%s tasks_detected=%s duration_ms=%s",
                        self.status.polling_iteration,
                        self.status.polling_status,
                        self.status.tasks_detected,
                        self.status.polling_last_duration_ms,
                    )

                if self._stop_requested:
                    break
                await asyncio.sleep(self.interval_seconds)
        finally:
            if self._stop_requested:
                stop_reason = self.status.runtime_loop_stop_reason or "stop_requested"
            self.status.mark_runtime_loop_stopped(stop_reason)
            logger.info("runtime_loop: stopped reason=%s", stop_reason)


runtime_loop = RuntimeLoop()
