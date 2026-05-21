"""
Controlled response validation layer for Hermes runtime.

This layer performs deterministic payload and integrity checks on provider
responses. It does not approve responses, perform semantic AI validation,
retry work, correct content, call providers, or mutate database state.
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
class ResponseValidationRequest:
    response: Any
    execution: ExecutionContext | None = None
    provider_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResponseValidationContext:
    validation_id: str
    execution_id: str
    task_id: str
    runtime_id: str
    execution_owner: str
    provider_source: str
    provider_request_id: str
    model: str | None
    validated_at: str
    payload_size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runtime_id": self.runtime_id,
            "execution_owner": self.execution_owner,
            "provider_source": self.provider_source,
            "provider_request_id": self.provider_request_id,
            "model": self.model,
            "validated_at": self.validated_at,
            "payload_size_bytes": self.payload_size_bytes,
        }


@dataclass(frozen=True)
class ResponseValidationResult:
    status: str
    success: bool
    validation_state: str
    validation_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    runtime_id: str | None = None
    execution_owner: str | None = None
    provider_source: str | None = None
    provider_request_id: str | None = None
    model: str | None = None
    validated_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    validation_duration_ms: int = 0
    payload_size_bytes: int = 0
    max_payload_inspection_bytes: int = 0
    active_validations: int = 0
    max_concurrent_validations: int = 0
    max_validation_duration_ms: int = 0
    runtime_validation_load: float | None = None
    max_runtime_validation_load: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    context: ResponseValidationContext | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "validation_state": self.validation_state,
            "validation_id": self.validation_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runtime_id": self.runtime_id,
            "execution_owner": self.execution_owner,
            "provider_source": self.provider_source,
            "provider_request_id": self.provider_request_id,
            "model": self.model,
            "validated_at": self.validated_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "validation_duration_ms": self.validation_duration_ms,
            "payload_size_bytes": self.payload_size_bytes,
            "max_payload_inspection_bytes": self.max_payload_inspection_bytes,
            "active_validations": self.active_validations,
            "max_concurrent_validations": self.max_concurrent_validations,
            "max_validation_duration_ms": self.max_validation_duration_ms,
            "runtime_validation_load": self.runtime_validation_load,
            "max_runtime_validation_load": self.max_runtime_validation_load,
            "metadata": dict(self.metadata),
            "reasons": list(self.reasons),
            "error": self.error,
            "context": self.context.to_dict() if self.context else None,
        }


class ResponseValidationRuntime:
    def __init__(
        self,
        max_payload_inspection_bytes: int = (
            settings.RESPONSE_VALIDATION_MAX_PAYLOAD_BYTES
        ),
        max_validation_duration_ms: int = (
            settings.RESPONSE_VALIDATION_MAX_DURATION_MS
        ),
        max_concurrent_validations: int = (
            settings.RESPONSE_VALIDATION_MAX_CONCURRENT_VALIDATIONS
        ),
        max_runtime_validation_load: float = (
            settings.RESPONSE_VALIDATION_MAX_RUNTIME_LOAD
        ),
    ) -> None:
        self.max_payload_inspection_bytes = max(
            1,
            int(max_payload_inspection_bytes or 1),
        )
        self.max_validation_duration_ms = max(
            1,
            int(max_validation_duration_ms or 1),
        )
        self.max_concurrent_validations = max(
            1,
            int(max_concurrent_validations or 1),
        )
        self.max_runtime_validation_load = max(
            0.0,
            float(max_runtime_validation_load or 0.0),
        )
        self._active_validations = 0

    def validate(
        self,
        request: ResponseValidationRequest,
        runtime_active: bool = True,
        validation_permitted: bool = True,
    ) -> ResponseValidationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        context: ResponseValidationContext | None = None

        try:
            response = self._as_dict(request.response)
            content = self._content(request.response, response)
            reasons = self._validation_reasons(
                request=request,
                response=response,
                content=content,
                runtime_active=runtime_active,
                validation_permitted=validation_permitted,
            )
            reasons.extend(self._duration_reasons(started))
            reasons = self._unique(reasons)
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

            self._active_validations += 1
            try:
                context = self._build_context(request, response, content)
            finally:
                self._active_validations = max(0, self._active_validations - 1)

            result = self._result(
                "validated",
                True,
                "accepted",
                request=request,
                response=response,
                content=content,
                context=context,
                started=started,
                started_at=started_at,
            )
            self._log_result(result)
            return result
        except Exception as exc:
            self._active_validations = max(0, self._active_validations - 1)
            result = self._result(
                "error",
                False,
                "error",
                request=request,
                context=context,
                reasons=["response_validation_error_contained"],
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._log_result(result)
            return result

    def visibility(self) -> dict[str, Any]:
        return {
            "active_validations": self._active_validations,
            "max_concurrent_validations": self.max_concurrent_validations,
            "max_payload_inspection_bytes": self.max_payload_inspection_bytes,
            "max_validation_duration_ms": self.max_validation_duration_ms,
            "runtime_validation_load": self._runtime_validation_load(),
            "max_runtime_validation_load": self.max_runtime_validation_load,
        }

    def _validation_reasons(
        self,
        request: ResponseValidationRequest,
        response: dict[str, Any],
        content: str | None,
        runtime_active: bool,
        validation_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not validation_permitted:
            reasons.append("validation_not_permitted")
        if not response:
            reasons.append("missing_provider_response")
        if self._active_validations >= self.max_concurrent_validations:
            reasons.append("max_concurrent_validations_reached")
        runtime_load = self._runtime_validation_load()
        if (
            runtime_load is not None
            and self.max_runtime_validation_load > 0
            and runtime_load > self.max_runtime_validation_load
        ):
            reasons.append("max_runtime_validation_load_reached")

        if response:
            reasons.extend(self._payload_reasons(request, response, content))
            reasons.extend(self._integrity_reasons(request, response))

        reasons.extend(self._execution_reasons(request, response))
        return self._unique(reasons)

    def _payload_reasons(
        self,
        request: ResponseValidationRequest,
        response: dict[str, Any],
        content: str | None,
    ) -> list[str]:
        reasons: list[str] = []
        if response.get("status") != "completed" or not response.get("success"):
            reasons.append("provider_response_not_completed")
        if not self._provider_source(request, response):
            reasons.append("missing_provider_source")
        if not content or not content.strip():
            reasons.append("empty_response_content")
        elif len(content.encode("utf-8")) > self.max_payload_inspection_bytes:
            reasons.append("max_payload_inspection_exceeded")
        if not isinstance(request.metadata, dict):
            reasons.append("invalid_validation_metadata")
        usage = response.get("usage")
        if usage is not None and not isinstance(usage, dict):
            reasons.append("invalid_response_metadata")
        context_value = response.get("context")
        if context_value is not None and not isinstance(context_value, dict):
            reasons.append("invalid_response_context")
        response_reasons = response.get("reasons")
        if response_reasons is not None and not isinstance(
            response_reasons,
            (list, tuple),
        ):
            reasons.append("invalid_response_reasons")
        return reasons

    def _integrity_reasons(
        self,
        request: ResponseValidationRequest,
        response: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        provider_request_id = self._provider_request_id(response)
        if not provider_request_id:
            reasons.append("missing_provider_request_id")

        started_at = response.get("started_at")
        finished_at = response.get("finished_at")
        if not started_at or not finished_at:
            reasons.append("missing_response_timestamps")
        started_dt = self._parse_timestamp(started_at)
        finished_dt = self._parse_timestamp(finished_at)
        if started_at and started_dt is None:
            reasons.append("invalid_started_at")
        if finished_at and finished_dt is None:
            reasons.append("invalid_finished_at")
        if started_dt and finished_dt and finished_dt < started_dt:
            reasons.append("response_timestamp_order_invalid")

        context_built_at = self._context(response).get("built_at")
        if context_built_at and self._parse_timestamp(context_built_at) is None:
            reasons.append("invalid_context_timestamp")

        response_provider = self._response_provider_source(response)
        if request.provider_id and response_provider and request.provider_id != response_provider:
            reasons.append("provider_source_mismatch")
        return reasons

    def _execution_reasons(
        self,
        request: ResponseValidationRequest,
        response: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
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
            if self._execution_id(response) and self._execution_id(response) != execution.execution_id:
                reasons.append("execution_id_mismatch")
            if self._task_id(response) and self._task_id(response) != execution.task_id:
                reasons.append("task_id_mismatch")
            if self._runtime_id(response) and self._runtime_id(response) != execution.runtime_id:
                reasons.append("runtime_id_mismatch")
            if (
                self._execution_owner(response)
                and self._execution_owner(response) != execution.runtime_owner
            ):
                reasons.append("execution_owner_mismatch")
            return reasons

        if not self._execution_id(response):
            reasons.append("missing_execution_id")
        if not self._task_id(response):
            reasons.append("missing_task_id")
        if not self._runtime_id(response):
            reasons.append("missing_runtime_id")
        if not self._execution_owner(response):
            reasons.append("missing_execution_owner")
        return reasons

    def _duration_reasons(self, started: float) -> list[str]:
        if self._duration_ms(started) > self.max_validation_duration_ms:
            return ["max_validation_duration_reached"]
        return []

    def _build_context(
        self,
        request: ResponseValidationRequest,
        response: dict[str, Any],
        content: str | None,
    ) -> ResponseValidationContext:
        execution = request.execution
        execution_id = execution.execution_id if execution else self._execution_id(response)
        task_id = execution.task_id if execution else self._task_id(response)
        runtime_id = execution.runtime_id if execution else self._runtime_id(response)
        execution_owner = (
            execution.runtime_owner if execution else self._execution_owner(response)
        )
        return ResponseValidationContext(
            validation_id=str(uuid4()),
            execution_id=str(execution_id),
            task_id=str(task_id),
            runtime_id=str(runtime_id),
            execution_owner=str(execution_owner),
            provider_source=str(self._provider_source(request, response)),
            provider_request_id=str(self._provider_request_id(response)),
            model=response.get("model"),
            validated_at=datetime.now(timezone.utc).isoformat(),
            payload_size_bytes=len((content or "").encode("utf-8")),
        )

    def _result(
        self,
        status: str,
        success: bool,
        validation_state: str,
        request: ResponseValidationRequest | None = None,
        response: dict[str, Any] | None = None,
        content: str | None = None,
        context: ResponseValidationContext | None = None,
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ResponseValidationResult:
        response = response or {}
        duration_ms = self._duration_ms(started) if started else 0
        finished_at = datetime.now(timezone.utc)
        execution = request.execution if request else None
        payload_size = len((content or "").encode("utf-8"))
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
        return ResponseValidationResult(
            status=status,
            success=success,
            validation_state=validation_state,
            validation_id=context.validation_id if context else None,
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
                context.provider_request_id
                if context
                else self._provider_request_id(response)
            ),
            model=context.model if context else response.get("model"),
            validated_at=context.validated_at if context else None,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            validation_duration_ms=duration_ms,
            payload_size_bytes=payload_size,
            max_payload_inspection_bytes=self.max_payload_inspection_bytes,
            active_validations=self._active_validations,
            max_concurrent_validations=self.max_concurrent_validations,
            max_validation_duration_ms=self.max_validation_duration_ms,
            runtime_validation_load=self._runtime_validation_load(),
            max_runtime_validation_load=self.max_runtime_validation_load,
            metadata=self._metadata(request),
            reasons=tuple(reasons or []),
            error=error,
            context=context,
        )

    def _metadata(
        self,
        request: ResponseValidationRequest | None,
    ) -> dict[str, Any]:
        if request is None or not isinstance(request.metadata, dict):
            return {}
        return dict(request.metadata)

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
        return response.get("runtime_id") or self._context(response).get("runtime_id")

    def _execution_owner(self, response: dict[str, Any]) -> str | None:
        return (
            response.get("runtime_owner")
            or response.get("execution_owner")
            or self._context(response).get("runtime_owner")
        )

    def _response_provider_source(self, response: dict[str, Any]) -> str | None:
        return (
            response.get("provider_name")
            or response.get("provider_source")
            or self._context(response).get("provider_name")
        )

    def _provider_source(
        self,
        request: ResponseValidationRequest | None,
        response: dict[str, Any],
    ) -> str | None:
        if request and request.provider_id:
            return request.provider_id
        return self._response_provider_source(response)

    def _provider_request_id(self, response: dict[str, Any]) -> str | None:
        return (
            response.get("request_id")
            or response.get("provider_request_id")
            or self._context(response).get("request_id")
        )

    def _parse_timestamp(self, value: Any) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _duration_ms(self, started: float | None) -> int:
        return int((time.perf_counter() - started) * 1000) if started else 0

    def _runtime_validation_load(self) -> float | None:
        if self.max_concurrent_validations <= 0:
            return None
        return round(self._active_validations / self.max_concurrent_validations, 4)

    def _unique(self, reasons: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for reason in reasons:
            if reason and reason not in seen:
                seen.add(reason)
                unique.append(reason)
        return unique

    def _log_result(self, result: ResponseValidationResult) -> None:
        if result.status == "validated":
            logger.info(
                "response_validation: validated validation_id=%s execution_id=%s provider=%s duration_ms=%s",
                result.validation_id,
                result.execution_id,
                result.provider_source,
                result.validation_duration_ms,
            )
            return
        if result.status == "error":
            logger.error(
                "response_validation: error execution_id=%s reasons=%s error=%s",
                result.execution_id,
                ",".join(result.reasons),
                result.error,
            )
            return
        logger.warning(
            "response_validation: rejected execution_id=%s reasons=%s",
            result.execution_id,
            ",".join(result.reasons),
        )
