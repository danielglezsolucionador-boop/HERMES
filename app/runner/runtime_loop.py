"""
Runtime loop foundation for Hermes.

This loop maintains runtime heartbeat and lifecycle state. Task claiming is
controlled and disabled by default. It never executes or retries tasks.
Execution, provider bridge, and response ingestion foundations are initialized
for observability but do not run autonomous work.
"""
import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from sqlalchemy import func, select

from app.core.config import settings
from app.db.engine import AsyncSessionLocal
from app.models.task import Task
from app.runner.pickup_safety import PickupSafety, PickupSafetyResult
from app.runner.execution_safety import ExecutionSafety, ExecutionSafetyResult
from app.runner.response_ingestion import ResponseIngestionRuntime
from app.runner.task_claiming import TaskClaiming, TaskClaimingResult
from app.runner.task_discovery import TaskDiscovery, TaskDiscoveryResult
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
        pickup_safety: Callable[[], Awaitable[PickupSafetyResult]] | None = None,
        execution_safety: Callable[[], Awaitable[ExecutionSafetyResult]] | None = None,
        claiming_enabled: bool = settings.TASK_CLAIMING_ENABLED,
        pickup_safety_enabled: bool = settings.TASK_PICKUP_SAFETY_ENABLED,
        execution_enabled: bool = settings.TASK_EXECUTION_ENABLED,
        execution_safety_enabled: bool = settings.TASK_EXECUTION_SAFETY_ENABLED,
        provider_bridge_enabled: bool = settings.PROVIDER_BRIDGE_ENABLED,
        response_ingestion_enabled: bool = settings.RESPONSE_INGESTION_ENABLED,
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
        self.execution_enabled = bool(execution_enabled)
        self.execution_safety_enabled = bool(execution_safety_enabled)
        self.execution_safety = execution_safety or ExecutionSafety().inspect
        self.provider_bridge_enabled = bool(provider_bridge_enabled)
        self.response_ingestion_enabled = bool(response_ingestion_enabled)
        self.response_ingestion = ResponseIngestionRuntime()
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
        if self.execution_safety_enabled:
            execution_safety_result = await self.execution_safety()
            self.status.mark_execution_safety_completed(
                execution_safety_result.to_dict()
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
            "runtime_loop: execution safety %s",
            "enabled" if self.execution_safety_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: provider bridge %s",
            "enabled" if self.provider_bridge_enabled else "disabled",
        )
        logger.info(
            "runtime_loop: response ingestion %s",
            "enabled" if self.response_ingestion_enabled else "disabled",
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
                    if self.execution_safety_enabled:
                        self.status.mark_execution_safety_error(str(exc), poll_duration_ms)
                    if self.provider_bridge_enabled:
                        self.status.mark_provider_bridge_error(str(exc), poll_duration_ms)
                    if self.response_ingestion_enabled:
                        self.status.mark_response_ingestion_error(
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
