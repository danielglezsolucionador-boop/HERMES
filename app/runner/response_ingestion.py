"""
Controlled response ingestion foundation for Hermes runtime.

This layer receives provider responses, preserves execution metadata, and
prepares a stable ingestion result for later storage/validation phases. It does
not approve responses, interpret content, retry work, call providers, or mutate
database state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.runner.task_execution import (
    EXECUTION_STATE_EXECUTING,
    ExecutionContext,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResponseIngestionRequest:
    response: Any
    execution: ExecutionContext | None = None
    provider_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResponseIngestionContext:
    response_id: str
    execution_id: str
    task_id: str
    runtime_id: str
    execution_owner: str
    provider_source: str
    provider_request_id: str | None
    model: str | None
    received_at: str
    response_size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runtime_id": self.runtime_id,
            "execution_owner": self.execution_owner,
            "provider_source": self.provider_source,
            "provider_request_id": self.provider_request_id,
            "model": self.model,
            "received_at": self.received_at,
            "response_size_bytes": self.response_size_bytes,
        }


@dataclass(frozen=True)
class ResponseIngestionResult:
    status: str
    success: bool
    ingestion_state: str
    response_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    runtime_id: str | None = None
    execution_owner: str | None = None
    provider_source: str | None = None
    provider_request_id: str | None = None
    model: str | None = None
    received_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    ingestion_duration_ms: int = 0
    response_size_bytes: int = 0
    max_response_bytes: int = 0
    active_ingestions: int = 0
    max_concurrent_ingestions: int = 0
    max_ingestion_duration_ms: int = 0
    runtime_ingestion_load: float | None = None
    max_runtime_ingestion_load: float = 0.0
    storage_prepared: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    context: ResponseIngestionContext | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "ingestion_state": self.ingestion_state,
            "response_id": self.response_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runtime_id": self.runtime_id,
            "execution_owner": self.execution_owner,
            "provider_source": self.provider_source,
            "provider_request_id": self.provider_request_id,
            "model": self.model,
            "received_at": self.received_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "ingestion_duration_ms": self.ingestion_duration_ms,
            "response_size_bytes": self.response_size_bytes,
            "max_response_bytes": self.max_response_bytes,
            "active_ingestions": self.active_ingestions,
            "max_concurrent_ingestions": self.max_concurrent_ingestions,
            "max_ingestion_duration_ms": self.max_ingestion_duration_ms,
            "runtime_ingestion_load": self.runtime_ingestion_load,
            "max_runtime_ingestion_load": self.max_runtime_ingestion_load,
            "storage_prepared": self.storage_prepared,
            "metadata": dict(self.metadata),
            "reasons": list(self.reasons),
            "error": self.error,
            "context": self.context.to_dict() if self.context else None,
        }


class ResponseIngestionRuntime:
    def __init__(
        self,
        max_response_bytes: int = settings.RESPONSE_INGESTION_MAX_RESPONSE_BYTES,
        max_ingestion_duration_ms: int = (
            settings.RESPONSE_INGESTION_MAX_DURATION_MS
        ),
        max_concurrent_ingestions: int = (
            settings.RESPONSE_INGESTION_MAX_CONCURRENT_INGESTIONS
        ),
        max_runtime_ingestion_load: float = (
            settings.RESPONSE_INGESTION_MAX_RUNTIME_LOAD
        ),
    ) -> None:
        self.max_response_bytes = max(1, int(max_response_bytes or 1))
        self.max_ingestion_duration_ms = max(
            1,
            int(max_ingestion_duration_ms or 1),
        )
        self.max_concurrent_ingestions = max(
            1,
            int(max_concurrent_ingestions or 1),
        )
        self.max_runtime_ingestion_load = max(
            0.0,
            float(max_runtime_ingestion_load or 0.0),
        )
        self._active_ingestions = 0

    def ingest(
        self,
        request: ResponseIngestionRequest,
        runtime_active: bool = True,
        ingestion_permitted: bool = True,
    ) -> ResponseIngestionResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        context: ResponseIngestionContext | None = None

        try:
            response = self._as_dict(request.response)
            content = self._content(request.response, response)
            reasons = self._reception_reasons(
                request=request,
                response=response,
                content=content,
                runtime_active=runtime_active,
                ingestion_permitted=ingestion_permitted,
            )
            if reasons:
                result = self._result(
                    "rejected",
                    False,
                    "rejected",
                    request=request,
                    response=response,
                    content=content,
                    reasons=reasons,
                    started=started,
                    started_at=started_at,
                )
                self._log_result(result)
                return result

            self._active_ingestions += 1
            try:
                context = self._build_context(request, response, content)
                result = self._result(
                    "ingested",
                    True,
                    "received",
                    request=request,
                    response=response,
                    content=content,
                    context=context,
                    storage_prepared=True,
                    started=started,
                    started_at=started_at,
                )
                self._log_result(result)
                return result
            finally:
                self._active_ingestions = max(0, self._active_ingestions - 1)
        except Exception as exc:
            result = self._result(
                "error",
                False,
                "error",
                request=request,
                context=context,
                reasons=["response_ingestion_error_contained"],
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._log_result(result)
            return result

    def visibility(self) -> dict[str, Any]:
        return {
            "active_ingestions": self._active_ingestions,
            "max_concurrent_ingestions": self.max_concurrent_ingestions,
            "max_response_bytes": self.max_response_bytes,
            "max_ingestion_duration_ms": self.max_ingestion_duration_ms,
            "runtime_ingestion_load": self._runtime_ingestion_load(),
            "max_runtime_ingestion_load": self.max_runtime_ingestion_load,
        }

    def _reception_reasons(
        self,
        request: ResponseIngestionRequest,
        response: dict[str, Any],
        content: str | None,
        runtime_active: bool,
        ingestion_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not ingestion_permitted:
            reasons.append("ingestion_not_permitted")
        if not response:
            reasons.append("missing_provider_response")
        if self._active_ingestions >= self.max_concurrent_ingestions:
            reasons.append("max_concurrent_ingestions_reached")
        runtime_load = self._runtime_ingestion_load()
        if (
            runtime_load is not None
            and self.max_runtime_ingestion_load > 0
            and runtime_load > self.max_runtime_ingestion_load
        ):
            reasons.append("max_runtime_ingestion_load_reached")

        if response:
            if response.get("status") != "completed" or not response.get("success"):
                reasons.append("provider_response_not_completed")
            if not self._provider_source(request, response):
                reasons.append("missing_provider_source")
            if not content or not content.strip():
                reasons.append("empty_response_content")
            elif len(content.encode("utf-8")) > self.max_response_bytes:
                reasons.append("max_response_size_exceeded")

        execution = request.execution
        if execution is not None:
            if execution.execution_state != EXECUTION_STATE_EXECUTING:
                reasons.append("execution_not_active")
            if not execution.execution_id:
                reasons.append("missing_execution_id")
            if not execution.task_id:
                reasons.append("missing_task_id")
            if not execution.runtime_id:
                reasons.append("missing_runtime_id")
            if not execution.runtime_owner:
                reasons.append("missing_execution_owner")
        else:
            if not self._execution_id(response):
                reasons.append("missing_execution_id")
            if not self._task_id(response):
                reasons.append("missing_task_id")
            if not self._runtime_id(response):
                reasons.append("missing_runtime_id")
            if not self._execution_owner(response):
                reasons.append("missing_execution_owner")
        return self._unique(reasons)

    def _build_context(
        self,
        request: ResponseIngestionRequest,
        response: dict[str, Any],
        content: str | None,
    ) -> ResponseIngestionContext:
        execution = request.execution
        execution_id = execution.execution_id if execution else self._execution_id(response)
        task_id = execution.task_id if execution else self._task_id(response)
        runtime_id = execution.runtime_id if execution else self._runtime_id(response)
        execution_owner = (
            execution.runtime_owner if execution else self._execution_owner(response)
        )
        return ResponseIngestionContext(
            response_id=str(uuid4()),
            execution_id=str(execution_id),
            task_id=str(task_id),
            runtime_id=str(runtime_id),
            execution_owner=str(execution_owner),
            provider_source=str(self._provider_source(request, response)),
            provider_request_id=response.get("request_id"),
            model=response.get("model"),
            received_at=datetime.now(timezone.utc).isoformat(),
            response_size_bytes=len((content or "").encode("utf-8")),
        )

    def _result(
        self,
        status: str,
        success: bool,
        ingestion_state: str,
        request: ResponseIngestionRequest | None = None,
        response: dict[str, Any] | None = None,
        content: str | None = None,
        context: ResponseIngestionContext | None = None,
        storage_prepared: bool = False,
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ResponseIngestionResult:
        response = response or {}
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        finished_at = datetime.now(timezone.utc)
        execution = request.execution if request else None
        response_size = len((content or "").encode("utf-8"))
        execution_id = (
            context.execution_id
            if context
            else (execution.execution_id if execution else self._execution_id(response))
        )
        task_id = (
            context.task_id
            if context
            else (execution.task_id if execution else self._task_id(response))
        )
        runtime_id = (
            context.runtime_id
            if context
            else (execution.runtime_id if execution else self._runtime_id(response))
        )
        execution_owner = (
            context.execution_owner
            if context
            else (
                execution.runtime_owner
                if execution
                else self._execution_owner(response)
            )
        )
        return ResponseIngestionResult(
            status=status,
            success=success,
            ingestion_state=ingestion_state,
            response_id=context.response_id if context else None,
            execution_id=execution_id,
            task_id=task_id,
            runtime_id=runtime_id,
            execution_owner=execution_owner,
            provider_source=(
                context.provider_source
                if context
                else self._provider_source(request, response)
            ),
            provider_request_id=(
                context.provider_request_id if context else response.get("request_id")
            ),
            model=context.model if context else response.get("model"),
            received_at=context.received_at if context else None,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            ingestion_duration_ms=duration_ms,
            response_size_bytes=response_size,
            max_response_bytes=self.max_response_bytes,
            active_ingestions=self._active_ingestions,
            max_concurrent_ingestions=self.max_concurrent_ingestions,
            max_ingestion_duration_ms=self.max_ingestion_duration_ms,
            runtime_ingestion_load=self._runtime_ingestion_load(),
            max_runtime_ingestion_load=self.max_runtime_ingestion_load,
            storage_prepared=storage_prepared,
            metadata=dict(request.metadata) if request else {},
            reasons=tuple(reasons or []),
            error=error,
            context=context,
        )

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _content(self, raw_response: Any, response: dict[str, Any]) -> str | None:
        direct_content = getattr(raw_response, "content", None)
        if isinstance(direct_content, str):
            return direct_content
        content = response.get("content")
        return content if isinstance(content, str) else None

    def _context(self, response: dict[str, Any]) -> dict[str, Any]:
        context = response.get("context") or {}
        return context if isinstance(context, dict) else {}

    def _execution_id(self, response: dict[str, Any]) -> str | None:
        return response.get("execution_id") or self._context(response).get("execution_id")

    def _task_id(self, response: dict[str, Any]) -> str | None:
        return response.get("task_id") or self._context(response).get("task_id")

    def _runtime_id(self, response: dict[str, Any]) -> str | None:
        return self._context(response).get("runtime_id")

    def _execution_owner(self, response: dict[str, Any]) -> str | None:
        return self._context(response).get("runtime_owner")

    def _provider_source(
        self,
        request: ResponseIngestionRequest | None,
        response: dict[str, Any],
    ) -> str | None:
        if request and request.provider_id:
            return request.provider_id
        return (
            response.get("provider_name")
            or response.get("provider_source")
            or self._context(response).get("provider_name")
        )

    def _runtime_ingestion_load(self) -> float | None:
        if self.max_concurrent_ingestions <= 0:
            return None
        return round(self._active_ingestions / self.max_concurrent_ingestions, 4)

    def _unique(self, reasons: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for reason in reasons:
            if reason and reason not in seen:
                seen.add(reason)
                unique.append(reason)
        return unique

    def _log_result(self, result: ResponseIngestionResult) -> None:
        if result.status == "ingested":
            logger.info(
                "response_ingestion: received response_id=%s execution_id=%s provider=%s duration_ms=%s",
                result.response_id,
                result.execution_id,
                result.provider_source,
                result.ingestion_duration_ms,
            )
            return
        if result.status == "error":
            logger.error(
                "response_ingestion: error execution_id=%s reasons=%s error=%s",
                result.execution_id,
                ",".join(result.reasons),
                result.error,
            )
            return
        logger.warning(
            "response_ingestion: rejected execution_id=%s reasons=%s",
            result.execution_id,
            ",".join(result.reasons),
        )
