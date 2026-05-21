"""
Controlled provider response handling for Hermes runtime.

This layer receives provider outputs, validates them through the existing
response ingestion pipeline, classifies them, and prepares an audit package.
It does not approve outputs, retry providers, mutate tasks, or persist data.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.prompt_execution import PromptExecutionResult
from app.runner.provider_bridge import ProviderBridgeResult
from app.runner.response_ingestion import (
    ResponseIngestionRequest,
    ResponseIngestionResult,
    ResponseIngestionRuntime,
)
from app.runner.task_execution import ExecutionContext

logger = logging.getLogger(__name__)

RESPONSE_TYPE_EXECUTION = "execution"
RESPONSE_TYPE_VALIDATION = "validation"
RESPONSE_TYPE_AUDIT = "audit"
RESPONSE_TYPE_REPORTING = "reporting"
RESPONSE_TYPE_FAILURE = "failure"
SUPPORTED_RESPONSE_TYPES = {
    RESPONSE_TYPE_EXECUTION,
    RESPONSE_TYPE_VALIDATION,
    RESPONSE_TYPE_AUDIT,
    RESPONSE_TYPE_REPORTING,
    RESPONSE_TYPE_FAILURE,
}

RESPONSE_STATE_RECEIVED = "received"
RESPONSE_STATE_VALIDATING = "validating"
RESPONSE_STATE_VALIDATED = "validated"
RESPONSE_STATE_REJECTED = "rejected"
RESPONSE_STATE_AUDIT_PENDING = "audit_pending"
RESPONSE_STATE_STORED = "stored"


@dataclass(frozen=True)
class ProviderResponseHandlingRequest:
    response: Any
    execution: ExecutionContext | None = None
    response_type: str | None = None
    provider_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResponseHandlingResult:
    status: str
    success: bool
    handling_id: str
    response_status: str
    response_type: str
    response_id: str | None = None
    provider_id: str | None = None
    provider_request_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    validation_status: str | None = None
    audit_status: str = "not_ready"
    output_available: bool = False
    output_size_bytes: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    timestamps: dict[str, str | None] = field(default_factory=dict)
    storage_prepared: bool = False
    audit_package: dict[str, Any] = field(default_factory=dict)
    lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    ingestion_result: ResponseIngestionResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "handling_id": self.handling_id,
            "response_status": self.response_status,
            "response_type": self.response_type,
            "response_id": self.response_id,
            "provider_id": self.provider_id,
            "provider_request_id": self.provider_request_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "validation_status": self.validation_status,
            "audit_status": self.audit_status,
            "output_available": self.output_available,
            "output_size_bytes": self.output_size_bytes,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "timestamps": dict(self.timestamps),
            "storage_prepared": self.storage_prepared,
            "audit_package": dict(self.audit_package),
            "lifecycle": [dict(entry) for entry in self.lifecycle],
            "metadata": dict(self.metadata),
            "reasons": list(self.reasons),
            "error": self.error,
            "ingestion_result": (
                self.ingestion_result.to_dict() if self.ingestion_result else None
            ),
        }


class ProviderResponseHandler:
    def __init__(
        self,
        ingestion_runtime: ResponseIngestionRuntime | None = None,
        status: Any | None = None,
    ) -> None:
        self.ingestion_runtime = ingestion_runtime or ResponseIngestionRuntime()
        self.status = status

    def handle(
        self,
        request: ProviderResponseHandlingRequest,
        runtime_active: bool = True,
        handling_permitted: bool = True,
    ) -> ProviderResponseHandlingResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        handling_id = str(uuid4())
        lifecycle = (self._lifecycle(RESPONSE_STATE_RECEIVED),)

        try:
            response_type = self._response_type(request)
            reasons = self._request_reasons(request, response_type)
            provider_response = self._provider_response(request.response)
            if reasons:
                result = self._result(
                    status="rejected",
                    success=False,
                    handling_id=handling_id,
                    response_status=RESPONSE_STATE_REJECTED,
                    response_type=response_type,
                    request=request,
                    provider_response=provider_response,
                    reasons=reasons,
                    lifecycle=(
                        *lifecycle,
                        self._lifecycle(RESPONSE_STATE_REJECTED),
                    ),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            lifecycle = (
                *lifecycle,
                self._lifecycle(RESPONSE_STATE_VALIDATING),
            )
            ingestion_result = self.ingestion_runtime.ingest(
                ResponseIngestionRequest(
                    response=provider_response,
                    execution=request.execution,
                    provider_id=request.provider_id,
                    metadata={
                        "handling_id": handling_id,
                        "response_type": response_type,
                        **dict(request.metadata),
                    },
                ),
                runtime_active=runtime_active,
                ingestion_permitted=handling_permitted,
            )
            if ingestion_result.success:
                lifecycle = (
                    *lifecycle,
                    self._lifecycle(RESPONSE_STATE_VALIDATED),
                    self._lifecycle(RESPONSE_STATE_AUDIT_PENDING),
                    self._lifecycle(RESPONSE_STATE_STORED),
                )
                result = self._result(
                    status="handled",
                    success=True,
                    handling_id=handling_id,
                    response_status=RESPONSE_STATE_STORED,
                    response_type=response_type,
                    request=request,
                    provider_response=provider_response,
                    ingestion_result=ingestion_result,
                    audit_status=RESPONSE_STATE_AUDIT_PENDING,
                    lifecycle=lifecycle,
                    started=started,
                    started_at=started_at,
                )
            else:
                lifecycle = (
                    *lifecycle,
                    self._lifecycle(RESPONSE_STATE_REJECTED),
                )
                result = self._result(
                    status=ingestion_result.status or "rejected",
                    success=False,
                    handling_id=handling_id,
                    response_status=RESPONSE_STATE_REJECTED,
                    response_type=response_type,
                    request=request,
                    provider_response=provider_response,
                    ingestion_result=ingestion_result,
                    audit_status="blocked",
                    reasons=list(ingestion_result.reasons),
                    error=ingestion_result.error,
                    lifecycle=lifecycle,
                    started=started,
                    started_at=started_at,
                )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._result(
                status="error",
                success=False,
                handling_id=handling_id,
                response_status=RESPONSE_STATE_REJECTED,
                response_type=RESPONSE_TYPE_FAILURE,
                request=request,
                reasons=["provider_response_handling_error_contained"],
                error=str(exc),
                lifecycle=(
                    *lifecycle,
                    self._lifecycle(RESPONSE_STATE_REJECTED),
                ),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _request_reasons(
        self,
        request: ProviderResponseHandlingRequest,
        response_type: str,
    ) -> list[str]:
        reasons: list[str] = []
        if response_type not in SUPPORTED_RESPONSE_TYPES:
            reasons.append("unsupported_response_type")
        if request.response is None:
            reasons.append("missing_provider_response")
        provider_response = self._provider_response(request.response)
        if provider_response is None:
            reasons.append("invalid_provider_response")
        return self._unique(reasons)

    def _provider_response(self, response: Any) -> ProviderBridgeResult | Any | None:
        if isinstance(response, PromptExecutionResult):
            return response.provider_result
        return response

    def _response_type(self, request: ProviderResponseHandlingRequest) -> str:
        if request.response_type:
            return request.response_type
        response = request.response
        if isinstance(response, PromptExecutionResult):
            if not response.success:
                return RESPONSE_TYPE_FAILURE
            return response.prompt_type
        if isinstance(response, ProviderBridgeResult) and not response.success:
            return RESPONSE_TYPE_FAILURE
        return RESPONSE_TYPE_EXECUTION

    def _output(self, response: Any, provider_response: Any) -> str | None:
        if isinstance(response, PromptExecutionResult):
            return response.output
        content = getattr(provider_response, "content", None)
        return content if isinstance(content, str) else None

    def _result(
        self,
        status: str,
        success: bool,
        handling_id: str,
        response_status: str,
        response_type: str,
        request: ProviderResponseHandlingRequest,
        provider_response: Any | None = None,
        ingestion_result: ResponseIngestionResult | None = None,
        audit_status: str = "not_ready",
        reasons: list[str] | None = None,
        error: str | None = None,
        lifecycle: tuple[dict[str, Any], ...] = (),
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ProviderResponseHandlingResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        output = self._output(request.response, provider_response)
        output_size = len(output.encode("utf-8")) if output else 0
        response_id = ingestion_result.response_id if ingestion_result else None
        provider_id = (
            ingestion_result.provider_source
            if ingestion_result
            else self._provider_id(request, provider_response)
        )
        provider_request_id = (
            ingestion_result.provider_request_id
            if ingestion_result
            else self._provider_request_id(provider_response)
        )
        execution_id = (
            ingestion_result.execution_id
            if ingestion_result
            else self._execution_id(request, provider_response)
        )
        task_id = (
            ingestion_result.task_id
            if ingestion_result
            else self._task_id(request, provider_response)
        )
        timestamps = {
            "started_at": started_at.isoformat() if started_at else None,
            "finished_at": finished_at.isoformat(),
            "received_at": (
                ingestion_result.received_at if ingestion_result else None
            ),
        }
        audit_package = (
            self._audit_package(
                handling_id=handling_id,
                response_type=response_type,
                response_id=response_id,
                provider_id=provider_id,
                provider_request_id=provider_request_id,
                execution_id=execution_id,
                task_id=task_id,
                output_size_bytes=output_size,
                ingestion_result=ingestion_result,
                request=request,
            )
            if success
            else {}
        )
        return ProviderResponseHandlingResult(
            status=status,
            success=success,
            handling_id=handling_id,
            response_status=response_status,
            response_type=response_type,
            response_id=response_id,
            provider_id=provider_id,
            provider_request_id=provider_request_id,
            execution_id=execution_id,
            task_id=task_id,
            validation_status=(
                ingestion_result.validation_status if ingestion_result else None
            ),
            audit_status=audit_status,
            output_available=bool(output),
            output_size_bytes=output_size,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            timestamps=timestamps,
            storage_prepared=(
                ingestion_result.storage_prepared if ingestion_result else False
            ),
            audit_package=audit_package,
            lifecycle=lifecycle,
            metadata=dict(request.metadata),
            reasons=tuple(reasons or []),
            error=error,
            ingestion_result=ingestion_result,
        )

    def _audit_package(
        self,
        handling_id: str,
        response_type: str,
        response_id: str | None,
        provider_id: str | None,
        provider_request_id: str | None,
        execution_id: str | None,
        task_id: str | None,
        output_size_bytes: int,
        ingestion_result: ResponseIngestionResult | None,
        request: ProviderResponseHandlingRequest,
    ) -> dict[str, Any]:
        return {
            "handling_id": handling_id,
            "response_type": response_type,
            "response_id": response_id,
            "provider_id": provider_id,
            "provider_request_id": provider_request_id,
            "execution_id": execution_id,
            "task_id": task_id,
            "validation_status": (
                ingestion_result.validation_status if ingestion_result else None
            ),
            "storage_prepared": (
                ingestion_result.storage_prepared if ingestion_result else False
            ),
            "output_size_bytes": output_size_bytes,
            "metadata": dict(request.metadata),
            "prepared_at": datetime.now(timezone.utc).isoformat(),
        }

    def _provider_id(self, request: ProviderResponseHandlingRequest, response: Any) -> str | None:
        return request.provider_id or getattr(response, "provider_name", None)

    def _provider_request_id(self, response: Any) -> str | None:
        return getattr(response, "request_id", None)

    def _execution_id(
        self,
        request: ProviderResponseHandlingRequest,
        response: Any,
    ) -> str | None:
        if request.execution:
            return request.execution.execution_id
        return getattr(response, "execution_id", None)

    def _task_id(
        self,
        request: ProviderResponseHandlingRequest,
        response: Any,
    ) -> str | None:
        if request.execution:
            return request.execution.task_id
        return getattr(response, "task_id", None)

    def _lifecycle(self, state: str) -> dict[str, Any]:
        return {
            "state": state,
            "at": datetime.now(timezone.utc).isoformat(),
        }

    def _publish(self, result: ProviderResponseHandlingResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_provider_response_handling_result",
        ):
            self.status.mark_provider_response_handling_result(result.to_dict())

    def _unique(self, reasons: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for reason in reasons:
            if reason and reason not in seen:
                seen.add(reason)
                unique.append(reason)
        return unique

    def _log_result(self, result: ProviderResponseHandlingResult) -> None:
        if result.success:
            logger.info(
                "provider_response_handling: handled handling_id=%s response_id=%s provider=%s duration_ms=%s",
                result.handling_id,
                result.response_id,
                result.provider_id,
                result.duration_ms,
            )
            return
        if result.status == "rejected":
            logger.warning(
                "provider_response_handling: rejected handling_id=%s reasons=%s",
                result.handling_id,
                ",".join(result.reasons),
            )
            return
        logger.error(
            "provider_response_handling: failed handling_id=%s status=%s reasons=%s error=%s",
            result.handling_id,
            result.status,
            ",".join(result.reasons),
            result.error,
        )
