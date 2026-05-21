"""
Controlled response safety layer for Hermes runtime.

This layer performs deterministic operational safety checks before response
validation/ingestion. It does not approve responses, retry work, call providers,
correct content, self-heal, or make autonomous decisions.
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

POISONING_SIGNATURES = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "system prompt",
    "developer message",
    "self-modifying runtime",
    "autonomous deploy",
    "deploy execution",
    "rm -rf",
    "drop table",
    "truncate table",
    "delete from",
)


@dataclass(frozen=True)
class ResponseSafetyRequest:
    response: Any
    execution: ExecutionContext | None = None
    provider_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    validation_duration_ms: int = 0
    ingestion_duration_ms: int = 0


@dataclass(frozen=True)
class ResponseSafetyContext:
    safety_id: str
    execution_id: str | None
    task_id: str | None
    runtime_id: str | None
    execution_owner: str | None
    provider_source: str | None
    provider_request_id: str | None
    model: str | None
    checked_at: str
    payload_size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "safety_id": self.safety_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runtime_id": self.runtime_id,
            "execution_owner": self.execution_owner,
            "provider_source": self.provider_source,
            "provider_request_id": self.provider_request_id,
            "model": self.model,
            "checked_at": self.checked_at,
            "payload_size_bytes": self.payload_size_bytes,
        }


@dataclass(frozen=True)
class ResponseSafetyResult:
    status: str
    success: bool
    safety_state: str
    allows_response: bool
    runtime_protected: bool = True
    corrupted_detected: bool = False
    poisoning_detected: bool = False
    timeout_detected: bool = False
    provider_failure_detected: bool = False
    retry_allowed: bool = True
    retry_attempts: int = 0
    max_validation_retries: int = 0
    safety_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    runtime_id: str | None = None
    execution_owner: str | None = None
    provider_source: str | None = None
    provider_request_id: str | None = None
    model: str | None = None
    checked_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    safety_duration_ms: int = 0
    payload_size_bytes: int = 0
    max_payload_bytes: int = 0
    active_safety_checks: int = 0
    max_concurrent_safety_checks: int = 0
    max_safety_duration_ms: int = 0
    runtime_safety_load: float | None = None
    max_runtime_safety_load: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    context: ResponseSafetyContext | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "safety_state": self.safety_state,
            "allows_response": self.allows_response,
            "runtime_protected": self.runtime_protected,
            "corrupted_detected": self.corrupted_detected,
            "poisoning_detected": self.poisoning_detected,
            "timeout_detected": self.timeout_detected,
            "provider_failure_detected": self.provider_failure_detected,
            "retry_allowed": self.retry_allowed,
            "retry_attempts": self.retry_attempts,
            "max_validation_retries": self.max_validation_retries,
            "safety_id": self.safety_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runtime_id": self.runtime_id,
            "execution_owner": self.execution_owner,
            "provider_source": self.provider_source,
            "provider_request_id": self.provider_request_id,
            "model": self.model,
            "checked_at": self.checked_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "safety_duration_ms": self.safety_duration_ms,
            "payload_size_bytes": self.payload_size_bytes,
            "max_payload_bytes": self.max_payload_bytes,
            "active_safety_checks": self.active_safety_checks,
            "max_concurrent_safety_checks": self.max_concurrent_safety_checks,
            "max_safety_duration_ms": self.max_safety_duration_ms,
            "runtime_safety_load": self.runtime_safety_load,
            "max_runtime_safety_load": self.max_runtime_safety_load,
            "metadata": dict(self.metadata),
            "reasons": list(self.reasons),
            "error": self.error,
            "context": self.context.to_dict() if self.context else None,
        }


class ResponseSafetyRuntime:
    def __init__(
        self,
        max_payload_bytes: int = settings.RESPONSE_SAFETY_MAX_PAYLOAD_BYTES,
        max_safety_duration_ms: int = settings.RESPONSE_SAFETY_MAX_DURATION_MS,
        max_concurrent_safety_checks: int = (
            settings.RESPONSE_SAFETY_MAX_CONCURRENT_CHECKS
        ),
        max_runtime_safety_load: float = settings.RESPONSE_SAFETY_MAX_RUNTIME_LOAD,
        max_validation_retries: int = (
            settings.RESPONSE_SAFETY_MAX_VALIDATION_RETRIES
        ),
    ) -> None:
        self.max_payload_bytes = max(1, int(max_payload_bytes or 1))
        self.max_safety_duration_ms = max(1, int(max_safety_duration_ms or 1))
        self.max_concurrent_safety_checks = max(
            1,
            int(max_concurrent_safety_checks or 1),
        )
        self.max_runtime_safety_load = max(
            0.0,
            float(max_runtime_safety_load or 0.0),
        )
        self.max_validation_retries = max(0, int(max_validation_retries or 0))
        self._active_safety_checks = 0

    def assess(
        self,
        request: ResponseSafetyRequest,
        runtime_active: bool = True,
        safety_permitted: bool = True,
    ) -> ResponseSafetyResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        context: ResponseSafetyContext | None = None

        try:
            response = self._as_dict(request.response)
            content = self._content(request.response, response)
            retry_attempts = self._retry_attempts(request)
            reasons = self._safety_reasons(
                request=request,
                response=response,
                content=content,
                retry_attempts=retry_attempts,
                runtime_active=runtime_active,
                safety_permitted=safety_permitted,
            )
            reasons.extend(self._duration_reasons(started))
            reasons = self._unique(reasons)
            if reasons:
                result = self._result(
                    "blocked",
                    False,
                    "blocked",
                    False,
                    request=request,
                    response=response,
                    content=content,
                    retry_attempts=retry_attempts,
                    reasons=reasons,
                    started=started,
                    started_at=started_at,
                )
                self._log_result(result)
                return result

            self._active_safety_checks += 1
            try:
                context = self._build_context(request, response, content)
            finally:
                self._active_safety_checks = max(
                    0,
                    self._active_safety_checks - 1,
                )

            result = self._result(
                "safe",
                True,
                "safe",
                True,
                request=request,
                response=response,
                content=content,
                context=context,
                retry_attempts=retry_attempts,
                started=started,
                started_at=started_at,
            )
            self._log_result(result)
            return result
        except Exception as exc:
            self._active_safety_checks = max(0, self._active_safety_checks - 1)
            result = self._result(
                "error",
                False,
                "error",
                False,
                request=request,
                context=context,
                reasons=["response_safety_error_contained"],
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._log_result(result)
            return result

    def visibility(self) -> dict[str, Any]:
        return {
            "active_safety_checks": self._active_safety_checks,
            "max_concurrent_safety_checks": self.max_concurrent_safety_checks,
            "max_payload_bytes": self.max_payload_bytes,
            "max_safety_duration_ms": self.max_safety_duration_ms,
            "runtime_safety_load": self._runtime_safety_load(),
            "max_runtime_safety_load": self.max_runtime_safety_load,
            "max_validation_retries": self.max_validation_retries,
        }

    def _safety_reasons(
        self,
        request: ResponseSafetyRequest,
        response: dict[str, Any],
        content: str | None,
        retry_attempts: int,
        runtime_active: bool,
        safety_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not safety_permitted:
            reasons.append("response_safety_not_permitted")
        if self._active_safety_checks >= self.max_concurrent_safety_checks:
            reasons.append("max_concurrent_response_safety_checks_reached")
        runtime_load = self._runtime_safety_load()
        if (
            runtime_load is not None
            and self.max_runtime_safety_load > 0
            and runtime_load > self.max_runtime_safety_load
        ):
            reasons.append("max_response_safety_runtime_load_reached")
        if retry_attempts > self.max_validation_retries:
            reasons.append("max_validation_retries_reached")

        reasons.extend(self._corruption_reasons(request, response, content))
        reasons.extend(self._poisoning_reasons(content))
        reasons.extend(self._timeout_reasons(request))
        reasons.extend(self._provider_failure_reasons(response, content))
        return self._unique(reasons)

    def _corruption_reasons(
        self,
        request: ResponseSafetyRequest,
        response: dict[str, Any],
        content: str | None,
    ) -> list[str]:
        reasons: list[str] = []
        if not response:
            reasons.append("missing_provider_response")
        if not content or not content.strip():
            reasons.append("empty_response_content")
        else:
            payload_size = len(content.encode("utf-8"))
            if payload_size > self.max_payload_bytes:
                reasons.append("max_response_safety_payload_exceeded")
            if "\x00" in content:
                reasons.append("payload_contains_null_byte")
            if self._control_character_ratio(content) > 0.05:
                reasons.append("payload_control_character_ratio_exceeded")

        if not isinstance(request.metadata, dict):
            reasons.append("invalid_response_safety_metadata")
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

        reasons.extend(self._execution_reasons(request, response))
        return reasons

    def _poisoning_reasons(self, content: str | None) -> list[str]:
        if not content:
            return []
        lower_content = content.lower()
        if any(signature in lower_content for signature in POISONING_SIGNATURES):
            return ["runtime_poisoning_signature_detected"]
        return []

    def _timeout_reasons(self, request: ResponseSafetyRequest) -> list[str]:
        reasons: list[str] = []
        validation_duration_ms = max(0, int(request.validation_duration_ms or 0))
        ingestion_duration_ms = max(0, int(request.ingestion_duration_ms or 0))
        if validation_duration_ms > settings.RESPONSE_VALIDATION_MAX_DURATION_MS:
            reasons.append("response_validation_timeout_detected")
        if ingestion_duration_ms > settings.RESPONSE_INGESTION_MAX_DURATION_MS:
            reasons.append("response_ingestion_timeout_detected")
        return reasons

    def _provider_failure_reasons(
        self,
        response: dict[str, Any],
        content: str | None,
    ) -> list[str]:
        reasons: list[str] = []
        if not response:
            return reasons
        if response.get("status") != "completed" or not response.get("success"):
            reasons.append("provider_response_failure_detected")
            reasons.append("provider_response_not_completed")
        if not self._response_provider_source(response):
            reasons.append("missing_provider_source")
        if not self._provider_request_id(response):
            reasons.append("missing_provider_request_id")
        if not content or not content.strip():
            reasons.append("malformed_provider_output")
        return reasons

    def _execution_reasons(
        self,
        request: ResponseSafetyRequest,
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
        if self._duration_ms(started) > self.max_safety_duration_ms:
            return ["response_safety_timeout_detected"]
        return []

    def _build_context(
        self,
        request: ResponseSafetyRequest,
        response: dict[str, Any],
        content: str | None,
    ) -> ResponseSafetyContext:
        execution = request.execution
        execution_id = execution.execution_id if execution else self._execution_id(response)
        task_id = execution.task_id if execution else self._task_id(response)
        runtime_id = execution.runtime_id if execution else self._runtime_id(response)
        execution_owner = (
            execution.runtime_owner if execution else self._execution_owner(response)
        )
        return ResponseSafetyContext(
            safety_id=str(uuid4()),
            execution_id=execution_id,
            task_id=task_id,
            runtime_id=runtime_id,
            execution_owner=execution_owner,
            provider_source=self._provider_source(request, response),
            provider_request_id=self._provider_request_id(response),
            model=response.get("model"),
            checked_at=datetime.now(timezone.utc).isoformat(),
            payload_size_bytes=len((content or "").encode("utf-8")),
        )

    def _result(
        self,
        status: str,
        success: bool,
        safety_state: str,
        allows_response: bool,
        request: ResponseSafetyRequest | None = None,
        response: dict[str, Any] | None = None,
        content: str | None = None,
        context: ResponseSafetyContext | None = None,
        retry_attempts: int = 0,
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ResponseSafetyResult:
        response = response or {}
        reasons = reasons or []
        duration_ms = self._duration_ms(started) if started else 0
        finished_at = datetime.now(timezone.utc)
        execution = request.execution if request else None
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
        payload_size = len((content or "").encode("utf-8"))
        return ResponseSafetyResult(
            status=status,
            success=success,
            safety_state=safety_state,
            allows_response=allows_response,
            runtime_protected=True,
            corrupted_detected=self._has_any_corruption_reason(reasons),
            poisoning_detected="runtime_poisoning_signature_detected" in reasons,
            timeout_detected=self._has_any_timeout_reason(reasons),
            provider_failure_detected=(
                "provider_response_failure_detected" in reasons
                or "malformed_provider_output" in reasons
            ),
            retry_allowed=retry_attempts < self.max_validation_retries,
            retry_attempts=retry_attempts,
            max_validation_retries=self.max_validation_retries,
            safety_id=context.safety_id if context else None,
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
            checked_at=context.checked_at if context else None,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            safety_duration_ms=duration_ms,
            payload_size_bytes=payload_size,
            max_payload_bytes=self.max_payload_bytes,
            active_safety_checks=self._active_safety_checks,
            max_concurrent_safety_checks=self.max_concurrent_safety_checks,
            max_safety_duration_ms=self.max_safety_duration_ms,
            runtime_safety_load=self._runtime_safety_load(),
            max_runtime_safety_load=self.max_runtime_safety_load,
            metadata=self._metadata(request),
            reasons=tuple(reasons),
            error=error,
            context=context,
        )

    def _has_any_corruption_reason(self, reasons: list[str]) -> bool:
        return any(
            reason
            in {
                "missing_provider_response",
                "empty_response_content",
                "max_response_safety_payload_exceeded",
                "payload_contains_null_byte",
                "payload_control_character_ratio_exceeded",
                "invalid_response_safety_metadata",
                "invalid_response_metadata",
                "invalid_response_context",
                "invalid_response_reasons",
                "missing_execution_id",
                "missing_task_id",
                "missing_runtime_id",
                "missing_execution_owner",
                "execution_id_mismatch",
                "task_id_mismatch",
                "runtime_id_mismatch",
                "execution_owner_mismatch",
            }
            for reason in reasons
        )

    def _has_any_timeout_reason(self, reasons: list[str]) -> bool:
        return any("timeout" in reason for reason in reasons)

    def _retry_attempts(self, request: ResponseSafetyRequest) -> int:
        if not isinstance(request.metadata, dict):
            return 0
        raw_attempts = (
            request.metadata.get("validation_attempts")
            or request.metadata.get("validation_retry_count")
            or request.metadata.get("response_validation_attempts")
            or 0
        )
        try:
            return max(0, int(raw_attempts or 0))
        except (TypeError, ValueError):
            return 0

    def _metadata(
        self,
        request: ResponseSafetyRequest | None,
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
        request: ResponseSafetyRequest | None,
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

    def _control_character_ratio(self, content: str) -> float:
        if not content:
            return 0.0
        controls = sum(
            1
            for char in content
            if ord(char) < 32 and char not in {"\n", "\r", "\t"}
        )
        return controls / len(content)

    def _duration_ms(self, started: float | None) -> int:
        return int((time.perf_counter() - started) * 1000) if started else 0

    def _runtime_safety_load(self) -> float | None:
        if self.max_concurrent_safety_checks <= 0:
            return None
        return round(self._active_safety_checks / self.max_concurrent_safety_checks, 4)

    def _unique(self, reasons: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for reason in reasons:
            if reason and reason not in seen:
                seen.add(reason)
                unique.append(reason)
        return unique

    def _log_result(self, result: ResponseSafetyResult) -> None:
        if result.status == "safe":
            logger.info(
                "response_safety: safe safety_id=%s execution_id=%s provider=%s duration_ms=%s",
                result.safety_id,
                result.execution_id,
                result.provider_source,
                result.safety_duration_ms,
            )
            return
        if result.status == "error":
            logger.error(
                "response_safety: error execution_id=%s reasons=%s error=%s",
                result.execution_id,
                ",".join(result.reasons),
                result.error,
            )
            return
        logger.warning(
            "response_safety: blocked execution_id=%s reasons=%s",
            result.execution_id,
            ",".join(result.reasons),
        )
